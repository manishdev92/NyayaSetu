"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  IngestRequestError,
  ingestDocument,
  streamGenerateLegalResponse,
  StreamNetworkFailed,
  transcribeAudio,
  type ClarificationAgentQuestion,
  type ClarificationPoint,
  type GenerateRequestPayload,
  type GenerateResponse,
  type GenerateTaskType,
  type StreamEvent,
} from "@/services/api";
import {
  type QueuedGenerate,
  clearQueuedGeneratesAsync,
  enqueueFailedGenerateAsync,
  getQueuedGenerateCountAsync,
  peekOldestQueuedGenerateAsync,
  removeQueuedGenerateByIdAsync,
} from "@/lib/offlineGenerateQueue";
import { formatApiThrowable, formatStreamErrorEvent } from "@/lib/apiErrorMessages";
import {
  INGEST_SERVER_WARN_NO_TEXT_PDF,
  localizeIngestServerWarning,
  messageForIngestError,
  t,
  type AppLocale,
} from "@/lib/i18n";

export type UserProfileFields = {
  fullName: string;
  address: string;
  city: string;
  phone: string;
  email: string;
};

type ChatMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  options?: string[];
  clarificationPoints?: ClarificationPoint[];
  clarifyingQuestions?: string[];
  clarificationAgentQuestions?: ClarificationAgentQuestion[];
  clarificationOptional?: boolean;
  clarificationNeeded?: boolean;
};

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const CLIENT_MODE_STORAGE_KEY = "nyaya-client-mode";
const TASK_TYPE_STORAGE_KEY = "nyaya-task-type";

function formatMaxUploadMbLabel(bytes: number): string {
  const m = bytes / 1_000_000;
  if (!Number.isFinite(m) || m <= 0) return "0";
  const s = m % 1 < 0.01 ? m.toFixed(0) : m.toFixed(1);
  return s.replace(/\.0$/, "");
}

function supportedRecordingMime(): string | undefined {
  if (typeof window === "undefined" || typeof MediaRecorder === "undefined") return undefined;
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  for (const t of candidates) {
    try {
      if (MediaRecorder.isTypeSupported(t)) return t;
    } catch {
      /* ignore */
    }
  }
  return undefined;
}

export function LegalChat({
  userId,
  profile,
  onComplete,
  onError,
  locale,
  responseLanguage,
  maxUploadBytes,
  ingestOcrReady = false,
  lawyerModeAvailable = false,
  lawyerModeRequiresSignIn = false,
  lawyerProGateActive = false,
  proEntitled = false,
  responseTaskUiEnabled = false,
}: {
  userId: string | null;
  profile: UserProfileFields;
  onComplete: (response: GenerateResponse) => void;
  onError: (message: string) => void;
  locale: AppLocale;
  responseLanguage: "en" | "hi" | "hi_latn";
  /** From `GET /config` (`max_upload_bytes`); when set, attach UI shows the cap and pre-validates. */
  maxUploadBytes?: number | null;
  /** From `GET /config` — show short OCR hint when the API advertises OCR as ready. */
  ingestOcrReady?: boolean;
  /** P1-4: `NEXT_PUBLIC_LAWYER_MODE_UI` + API lists `lawyer` in `client_modes_supported`. */
  lawyerModeAvailable?: boolean;
  /** P1-1: from `GET /config` (`lawyer_mode_requires_sign_in`) — lawyer segment needs Clerk user id. */
  lawyerModeRequiresSignIn?: boolean;
  /** P1-1: from `GET /config` — lawyer requires active Pro (Stripe) when true. */
  lawyerProGateActive?: boolean;
  /** From `GET /billing/entitlements` when `billing_mode` is stripe — Pro subscription active. */
  proEntitled?: boolean;
  /** P2-4: `NEXT_PUBLIC_RESPONSE_TASK_UI` at build time — `task_type` on generate body. */
  responseTaskUiEnabled?: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingAssistantId, setStreamingAssistantId] = useState<string | null>(null);
  const lastUserIssueRef = useRef<string>("");
  const activeClarificationPointsRef = useRef<ClarificationPoint[] | null>(null);
  const activeAgentQuestionsRef = useRef<ClarificationAgentQuestion[] | null>(null);
  const awaitingClarificationReplyRef = useRef(false);
  const [structuredSelections, setStructuredSelections] = useState<Record<string, string>>({});
  const [agentAnswerSelections, setAgentAnswerSelections] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [voiceRecording, setVoiceRecording] = useState(false);
  const [voiceTranscribing, setVoiceTranscribing] = useState(false);
  const voiceChunksRef = useRef<BlobPart[]>([]);
  const voiceMimeRef = useRef<string>("");
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const voiceMaxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [ingestNote, setIngestNote] = useState<string | null>(null);
  const [pendingQueueCount, setPendingQueueCount] = useState(0);
  const [onlineHint, setOnlineHint] = useState(false);
  const [clientMode, setClientMode] = useState<"citizen" | "lawyer">("citizen");
  const [taskType, setTaskType] = useState<GenerateTaskType>("draft_letter");
  const loadingRef = useRef(false);
  const canSelectLawyer =
    (!lawyerModeRequiresSignIn || Boolean(userId?.trim())) &&
    (!lawyerProGateActive || proEntitled);
  const needLawyerProHint = Boolean(lawyerProGateActive && !proEntitled);
  const needLawyerSignInHint = Boolean(lawyerModeRequiresSignIn && !userId?.trim());

  useEffect(() => {
    if (!responseTaskUiEnabled || typeof window === "undefined") return;
    const raw = window.localStorage.getItem(TASK_TYPE_STORAGE_KEY);
    if (
      raw === "qa_only" ||
      raw === "draft_with_qa" ||
      raw === "draft_letter" ||
      raw === "consumer_complaint_filing"
    ) {
      setTaskType(raw);
    }
  }, [responseTaskUiEnabled]);

  useEffect(() => {
    if (!responseTaskUiEnabled) {
      setTaskType("draft_letter");
    }
  }, [responseTaskUiEnabled]);

  const persistTaskType = useCallback(
    (t: GenerateTaskType) => {
      setTaskType(t);
      if (typeof window !== "undefined" && responseTaskUiEnabled) {
        window.localStorage.setItem(TASK_TYPE_STORAGE_KEY, t);
      }
    },
    [responseTaskUiEnabled],
  );

  useEffect(() => {
    if (!lawyerModeAvailable || typeof window === "undefined") return;
    const raw = window.localStorage.getItem(CLIENT_MODE_STORAGE_KEY);
    if (raw === "lawyer" || raw === "citizen") {
      setClientMode(raw);
    }
  }, [lawyerModeAvailable]);

  useEffect(() => {
    if (!lawyerModeAvailable) {
      setClientMode("citizen");
    }
  }, [lawyerModeAvailable]);

  useEffect(() => {
    if (!lawyerModeAvailable || canSelectLawyer) return;
    if (clientMode !== "lawyer") return;
    setClientMode("citizen");
    if (typeof window !== "undefined") {
      window.localStorage.setItem(CLIENT_MODE_STORAGE_KEY, "citizen");
    }
  }, [lawyerModeAvailable, canSelectLawyer, clientMode]);

  const persistClientMode = useCallback(
    (mode: "citizen" | "lawyer") => {
      setClientMode(mode);
      if (typeof window !== "undefined" && lawyerModeAvailable) {
        window.localStorage.setItem(CLIENT_MODE_STORAGE_KEY, mode);
      }
    },
    [lawyerModeAvailable],
  );
  loadingRef.current = loading;

  useEffect(() => {
    void getQueuedGenerateCountAsync().then(setPendingQueueCount);
  }, []);

  const stopVoiceStream = useCallback(() => {
    if (voiceMaxTimerRef.current) {
      clearTimeout(voiceMaxTimerRef.current);
      voiceMaxTimerRef.current = null;
    }
    mediaStreamRef.current?.getTracks().forEach((tr) => tr.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      if (voiceMaxTimerRef.current) clearTimeout(voiceMaxTimerRef.current);
      mediaStreamRef.current?.getTracks().forEach((tr) => tr.stop());
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        try {
          mediaRecorderRef.current.stop();
        } catch {
          /* ignore */
        }
      }
    };
  }, []);

  const handleVoiceToggle = useCallback(async () => {
    if (voiceTranscribing || ingesting || loading) return;
    if (voiceRecording && mediaRecorderRef.current) {
      if (mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
      setVoiceRecording(false);
      return;
    }
    const mime = supportedRecordingMime();
    if (!mime || !navigator.mediaDevices?.getUserMedia) {
      onError(t(locale, "voiceNotSupported"));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      voiceChunksRef.current = [];
      voiceMimeRef.current = mime;
      const mr = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) voiceChunksRef.current.push(ev.data);
      };
      mr.onerror = () => {
        stopVoiceStream();
        setVoiceRecording(false);
        onError(t(locale, "requestFailed"));
      };
      mr.onstop = () => {
        setVoiceRecording(false);
        stopVoiceStream();
        const finalMime = voiceMimeRef.current || mime;
        const blob = new Blob(voiceChunksRef.current, { type: finalMime });
        voiceChunksRef.current = [];
        mediaRecorderRef.current = null;
        void (async () => {
          if (blob.size < 256) {
            if (blob.size > 0) onError(t(locale, "voiceTooShort"));
            return;
          }
          setVoiceTranscribing(true);
          try {
            const name = finalMime.includes("mp4") ? "recording.m4a" : "recording.webm";
            const r = await transcribeAudio(blob, {
              userId,
              responseLanguage,
              filename: name,
            });
            const piece = r.text.trim();
            if (!piece) {
              onError(t(locale, "transcribeNoSpeech"));
              return;
            }
            setInput((prev) => {
              const p = prev.trim();
              if (!p) return piece;
              return `${p}\n\n${piece}`;
            });
          } catch (e: unknown) {
            onError(formatApiThrowable(locale, e));
          } finally {
            setVoiceTranscribing(false);
          }
        })();
      };
      mr.start(400);
      setVoiceRecording(true);
      voiceMaxTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
        }
        voiceMaxTimerRef.current = null;
      }, 120_000);
    } catch (e: unknown) {
      stopVoiceStream();
      setVoiceRecording(false);
      const name =
        e && typeof e === "object" && "name" in e ? String((e as { name: string }).name) : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        onError(t(locale, "voiceMicDenied"));
        return;
      }
      onError(t(locale, "voiceNotSupported"));
    }
  }, [
    voiceRecording,
    voiceTranscribing,
    ingesting,
    loading,
    locale,
    onError,
    responseLanguage,
    stopVoiceStream,
    userId,
  ]);

  const appendAssistantChunk = useCallback((assistantId: string, chunk: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === assistantId ? { ...m, content: m.content ? `${m.content}\n\n${chunk}` : chunk } : m,
      ),
    );
  }, []);

  const runStream = useCallback(
    async (
      userText: string,
      streamOpts?: { skipClarification?: boolean; fromQueueItem?: QueuedGenerate },
    ) => {
      const fromQueueItem = streamOpts?.fromQueueItem;
      const payload: GenerateRequestPayload = fromQueueItem
        ? { ...fromQueueItem.payload }
        : {
            user_input: userText.trim(),
            userId,
            full_name: profile.fullName.trim() || undefined,
            address: profile.address.trim() || undefined,
            city: profile.city.trim() || undefined,
            phone: profile.phone.trim() || undefined,
            email: profile.email.trim() || undefined,
            skip_clarification: streamOpts?.skipClarification === true,
            response_language: responseLanguage,
          };
      if (lawyerModeAvailable) {
        payload.client_mode = clientMode;
      }
      if (!fromQueueItem) {
        if (responseTaskUiEnabled) {
          payload.task_type = taskType;
        } else {
          delete (payload as { task_type?: GenerateTaskType }).task_type;
        }
      }
      if (!payload.user_input.trim()) {
        setLoading(false);
        return;
      }

      lastUserIssueRef.current = payload.user_input;
      const assistantId = uid();
      setStreamingAssistantId(assistantId);
      setStructuredSelections({});
      setAgentAnswerSelections({});
      activeClarificationPointsRef.current = null;
      activeAgentQuestionsRef.current = null;
      setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "" }]);

      let finalPayload: GenerateResponse | null = null;
      const streamOutcome: { last: GenerateResponse | null } = { last: null };

      const onEvent = (ev: StreamEvent) => {
        if (ev.type === "phase") {
          appendAssistantChunk(assistantId, ev.message);
        } else if (ev.type === "clarification") {
          const agentQ = (ev.clarification_agent_questions ?? []).filter((q) => q.question && q.options.length > 0);
          const cqqRaw = ev.clarifying_questions?.filter((s) => s.trim()) ?? [];
          const cqq =
            cqqRaw.length > 0
              ? cqqRaw
              : agentQ.length > 0
                ? agentQ.map((q) => q.question)
                : [];
          activeAgentQuestionsRef.current = agentQ.length > 0 ? agentQ : null;
          if (agentQ.length > 0 || cqq.length >= 2) {
            appendAssistantChunk(assistantId, ev.question || t(locale, "clarFastQuestions"));
          } else if (ev.question) {
            appendAssistantChunk(assistantId, `❓ ${ev.question}`);
          }
          const pts = ev.points && ev.points.length > 0 ? ev.points : undefined;
          activeClarificationPointsRef.current = pts ?? null;
          if (ev.clarification_needed) {
            awaitingClarificationReplyRef.current = true;
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    options: ev.options?.length ? ev.options : undefined,
                    clarificationPoints: pts,
                    clarifyingQuestions: cqq.length > 0 ? cqq : undefined,
                    clarificationAgentQuestions: agentQ.length > 0 ? agentQ : undefined,
                    clarificationOptional: ev.clarification_optional === true,
                    clarificationNeeded: ev.clarification_needed,
                  }
                : m,
            ),
          );
        } else if (ev.type === "result") {
          finalPayload = ev.payload;
          streamOutcome.last = ev.payload;
          if (ev.payload.clarification_needed) {
            awaitingClarificationReplyRef.current = true;
            const pp = ev.payload.clarification_points;
            const cqq = (ev.payload.clarifying_questions ?? []).map(String).filter((s) => s.trim());
            const agentQ = (ev.payload.clarification_agent_questions ?? []).filter(
              (q) => q.question && q.options.length > 0,
            );
            activeAgentQuestionsRef.current = agentQ.length > 0 ? agentQ : null;
            if (pp && pp.length > 0) {
              activeClarificationPointsRef.current = pp;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        clarificationPoints: pp,
                        options:
                          ev.payload.clarification_options && ev.payload.clarification_options.length > 0
                            ? ev.payload.clarification_options
                            : undefined,
                        clarifyingQuestions: undefined,
                        clarificationAgentQuestions: undefined,
                        clarificationOptional: false,
                        clarificationNeeded: true,
                      }
                    : m,
                ),
              );
            } else if (agentQ.length > 0 || cqq.length >= 1) {
              activeClarificationPointsRef.current = null;
              const cqqOut =
                cqq.length > 0 ? cqq : agentQ.length > 0 ? agentQ.map((q) => q.question) : [];
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        clarifyingQuestions: cqqOut.length > 0 ? cqqOut : undefined,
                        clarificationAgentQuestions: agentQ.length > 0 ? agentQ : undefined,
                        clarificationOptional: ev.payload.clarification_optional === true,
                        clarificationPoints: undefined,
                        options: undefined,
                        clarificationNeeded: true,
                      }
                    : m,
                ),
              );
            }
          }
          if (!ev.payload.clarification_needed && ev.payload.document?.trim()) {
            appendAssistantChunk(assistantId, t(locale, "streamDone"));
          }
        } else if (ev.type === "error") {
          onError(formatStreamErrorEvent(locale, ev));
        }
      };

      try {
        await streamGenerateLegalResponse(payload, onEvent);
        if (finalPayload) {
          onComplete(finalPayload);
          if (fromQueueItem) {
            await removeQueuedGenerateByIdAsync(fromQueueItem.id);
            setPendingQueueCount(await getQueuedGenerateCountAsync());
          }
        }
      } catch (e) {
        if (e instanceof StreamNetworkFailed) {
          await enqueueFailedGenerateAsync(e.payload);
          setPendingQueueCount(await getQueuedGenerateCountAsync());
          setMessages((prev) => prev.filter((m) => m.id !== assistantId));
          onError(t(locale, "offlineQueuedMessage"));
        } else {
          onError(formatApiThrowable(locale, e));
        }
      } finally {
        setStreamingAssistantId(null);
        setLoading(false);
        if (streamOutcome.last?.clarification_needed !== true) {
          awaitingClarificationReplyRef.current = false;
        }
      }
    },
    [
      appendAssistantChunk,
      onComplete,
      onError,
      profile,
      userId,
      locale,
      responseLanguage,
      lawyerModeAvailable,
      clientMode,
      responseTaskUiEnabled,
      taskType,
    ],
  );

  useEffect(() => {
    const onOnline = () => {
      void (async () => {
        const n = await getQueuedGenerateCountAsync();
        setPendingQueueCount(n);
        if (n > 0) {
          setOnlineHint(true);
          window.setTimeout(() => setOnlineHint(false), 8000);
          if (process.env.NEXT_PUBLIC_AUTO_RETRY_QUEUE_ONLINE === "1" && !loadingRef.current) {
            const oldest = await peekOldestQueuedGenerateAsync();
            if (oldest) {
              setLoading(true);
              void runStream("", { fromQueueItem: oldest });
            }
          }
        }
      })();
    };
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [runStream]);

  async function retryOldestQueued() {
    const oldest = await peekOldestQueuedGenerateAsync();
    if (!oldest || loading) return;
    setLoading(true);
    await runStream("", { fromQueueItem: oldest });
  }

  async function handleSend(e?: React.FormEvent) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setLoading(true);
    const mergeClarification = awaitingClarificationReplyRef.current && lastUserIssueRef.current.trim();
    const merged = mergeClarification
      ? `${lastUserIssueRef.current.trim()}\n\n${t(locale, "mergeAdditional")} ${text}`
      : text;
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: text }]);
    await runStream(merged, { skipClarification: Boolean(mergeClarification) });
  }

  async function handleOptionClick(option: string) {
    const base = lastUserIssueRef.current.trim();
    const follow = `${base}\n\n${t(locale, "mergeMyChoice")} ${option}`;
    setLoading(true);
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: follow }]);
    await runStream(follow, { skipClarification: true });
  }

  async function handleStructuredSubmit() {
    const base = lastUserIssueRef.current.trim();
    const pts = activeClarificationPointsRef.current;
    if (!pts || pts.length === 0) return;
    const missing = pts.some((p) => !structuredSelections[p.label]?.trim());
    if (missing) return;
    const parts = pts.map((p) => `${p.label}: ${structuredSelections[p.label]}`);
    const follow = `${base}\n\n${t(locale, "mergeStructured")}\n${parts.join(", ")}`;
    setLoading(true);
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: follow }]);
    setStructuredSelections({});
    activeClarificationPointsRef.current = null;
    await runStream(follow, { skipClarification: true });
  }

  async function handleAgentClarificationSubmit() {
    const qs = activeAgentQuestionsRef.current;
    const base = lastUserIssueRef.current.trim();
    if (!qs || qs.length === 0 || !base) return;
    const missing = qs.some((q) => !agentAnswerSelections[q.id]?.trim());
    if (missing) return;
    const parts = qs.map((q) => `${q.question}: ${agentAnswerSelections[q.id]}`);
    const follow = `${base}\n\n${t(locale, "mergeAdditional")} ${parts.join("; ")}`;
    setLoading(true);
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: follow }]);
    setAgentAnswerSelections({});
    activeAgentQuestionsRef.current = null;
    await runStream(follow, { skipClarification: true });
  }

  async function handleSkipOptionalClarification() {
    const base = lastUserIssueRef.current.trim();
    if (!base || loading) return;
    setLoading(true);
    await runStream(base, { skipClarification: true });
  }

  const structuredReady =
    activeClarificationPointsRef.current &&
    activeClarificationPointsRef.current.length > 0 &&
    activeClarificationPointsRef.current.every((p) => structuredSelections[p.label]?.trim());

  const lastAssistantId = [...messages].reverse().find((x) => x.role === "assistant")?.id;
  const lastAssistantMsg = messages.find((x) => x.id === lastAssistantId);
  const agentQsForReady = lastAssistantMsg?.clarificationAgentQuestions;
  const agentClarificationReady =
    !!agentQsForReady &&
    agentQsForReady.length > 0 &&
    agentQsForReady.every((q) => agentAnswerSelections[q.id]?.trim());

  return (
    <section className="rounded-2xl border border-stone-200/90 bg-gradient-to-br from-white via-stone-50/40 to-amber-50/15 p-5 shadow-md ring-1 ring-stone-200/50 sm:p-7">
      <h2 className="text-xl font-semibold tracking-tight text-stone-900">{t(locale, "chatH2")}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-stone-600 sm:text-base">{t(locale, "chatIntro")}</p>

      {pendingQueueCount > 0 ? (
        <div
          role="status"
          className="mt-3 rounded-xl border border-amber-200 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
        >
          <p>{t(locale, "pendingGenerateBanner")(pendingQueueCount)}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={
                loading ||
                (typeof navigator !== "undefined" &&
                  typeof navigator.onLine === "boolean" &&
                  !navigator.onLine)
              }
              onClick={() => void retryOldestQueued()}
              className="rounded-lg bg-amber-800 px-3 py-1.5 font-medium text-white hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t(locale, "retryPendingGenerate")}
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void (async () => {
                  await clearQueuedGeneratesAsync();
                  setPendingQueueCount(await getQueuedGenerateCountAsync());
                  setOnlineHint(false);
                })();
              }}
              className="rounded-lg border border-amber-800/40 px-3 py-1.5 font-medium text-amber-950 hover:bg-amber-100 disabled:opacity-50"
            >
              {t(locale, "clearPendingGenerate")}
            </button>
          </div>
          {onlineHint ? (
            <p className="mt-2 text-emerald-800">{t(locale, "backOnlinePendingHint")}</p>
          ) : null}
        </div>
      ) : null}

      <div className="mt-5 max-h-[min(480px,58vh)] space-y-4 overflow-y-auto rounded-2xl border border-stone-200/80 bg-stone-50/90 p-4 shadow-inner sm:p-5">
        {messages.length === 0 ? (
          <p className="text-base text-stone-600">{t(locale, "emptyChat")}</p>
        ) : (
          messages.map((m) => {
            const showClarifyControls = m.role === "assistant" && m.id === lastAssistantId;
            return (
            <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[min(92%,40rem)] rounded-2xl px-4 py-3 text-base leading-relaxed shadow-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-amber-800 to-amber-900 text-white shadow-amber-900/20"
                    : "border border-stone-200/90 bg-white text-stone-800 shadow-md"
                }`}
              >
                <p className="whitespace-pre-wrap">
                  {m.content || (loading && m.id === streamingAssistantId ? t(locale, "streamLoadingEllipsis") : "")}
                </p>
                {showClarifyControls && m.clarificationOptional ? (
                  <p className="mt-2 rounded-lg border border-dashed border-amber-700/40 bg-amber-50/50 px-2 py-1.5 text-sm text-amber-950">
                    {t(locale, "optionalChips")}
                  </p>
                ) : null}
                {showClarifyControls &&
                m.clarificationAgentQuestions &&
                m.clarificationAgentQuestions.length > 0 &&
                !(m.clarificationPoints && m.clarificationPoints.length > 0) ? (
                  <div className="mt-3 space-y-3">
                    {m.clarificationAgentQuestions.map((aq) => (
                      <div key={aq.id}>
                        <p className="text-sm font-medium text-stone-700 sm:text-base">{aq.question}</p>
                        <div className="mt-1.5 flex flex-wrap gap-2">
                          {aq.options.map((opt) => {
                            const sel = agentAnswerSelections[aq.id] === opt;
                            return (
                              <button
                                key={`${aq.id}-${opt}`}
                                type="button"
                                disabled={loading}
                                onClick={() =>
                                  setAgentAnswerSelections((s) => ({
                                    ...s,
                                    [aq.id]: opt,
                                  }))
                                }
                                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                                  sel
                                    ? "border-amber-800 bg-amber-100 text-amber-950 ring-2 ring-amber-700/30"
                                    : "border-amber-800/40 bg-amber-50 text-amber-950 hover:bg-amber-100"
                                }`}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      disabled={loading || !agentClarificationReady}
                      onClick={() => void handleAgentClarificationSubmit()}
                      className="mt-2 w-full rounded-lg bg-amber-800 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {t(locale, "sendAnswers")}
                    </button>
                    {m.clarificationOptional ? (
                      <button
                        type="button"
                        disabled={loading}
                        onClick={() => void handleSkipOptionalClarification()}
                        className="mt-2 w-full rounded-lg border border-stone-300 bg-white py-2.5 text-sm font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50"
                      >
                        {t(locale, "skipContinue")}
                      </button>
                    ) : null}
                  </div>
                ) : null}
                {showClarifyControls &&
                m.clarifyingQuestions &&
                m.clarifyingQuestions.length >= 2 &&
                !(m.clarificationPoints && m.clarificationPoints.length > 0) &&
                !(m.clarificationAgentQuestions && m.clarificationAgentQuestions.length > 0) ? (
                  <div className="mt-3 space-y-2">
                    {m.clarifyingQuestions.map((cq, i) => (
                      <div
                        key={`cq-${i}`}
                        className="rounded-xl border border-amber-900/15 bg-amber-50/90 px-3 py-2 text-sm leading-snug text-stone-800"
                      >
                        {cq}
                      </div>
                    ))}
                    <p className="text-sm text-stone-600">{t(locale, "answerBelow")}</p>
                  </div>
                ) : null}
                {showClarifyControls && m.clarificationPoints && m.clarificationPoints.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {m.clarificationPoints.map((pt) => (
                      <div key={pt.label}>
                        <p className="text-sm font-medium text-stone-700 sm:text-base">{pt.label}</p>
                        <div className="mt-1.5 flex flex-wrap gap-2">
                          {pt.options.map((opt) => {
                            const sel = structuredSelections[pt.label] === opt;
                            return (
                              <button
                                key={`${pt.label}-${opt}`}
                                type="button"
                                disabled={loading}
                                onClick={() =>
                                  setStructuredSelections((s) => ({
                                    ...s,
                                    [pt.label]: opt,
                                  }))
                                }
                                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                                  sel
                                    ? "border-amber-800 bg-amber-100 text-amber-950 ring-2 ring-amber-700/30"
                                    : "border-amber-800/40 bg-amber-50 text-amber-950 hover:bg-amber-100"
                                }`}
                              >
                                {opt}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                    <button
                      type="button"
                      disabled={loading || !structuredReady}
                      onClick={() => void handleStructuredSubmit()}
                      className="mt-2 w-full rounded-lg bg-amber-800 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {t(locale, "structReply")}
                    </button>
                  </div>
                ) : null}
                {showClarifyControls && m.options && m.options.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {m.options.map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        disabled={loading}
                        onClick={() => void handleOptionClick(opt)}
                        className="rounded-lg border border-amber-800/40 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100 disabled:opacity-50"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
            );
          })
        )}
      </div>

      <form onSubmit={handleSend} className="mt-4 flex flex-col gap-2">
        {lawyerModeAvailable ? (
          <fieldset className="rounded-xl border border-indigo-200/80 bg-indigo-50/40 px-3 py-3 sm:px-4">
            <legend className="px-1 text-sm font-semibold text-indigo-950">{t(locale, "clientModeLabel")}</legend>
            <p className="mt-1 text-xs leading-relaxed text-indigo-950/80">{t(locale, "clientModeHint")}</p>
            {needLawyerSignInHint ? (
              <p className="mt-1 text-xs font-medium text-indigo-950/90">{t(locale, "clientModeLawyerNeedsSignIn")}</p>
            ) : needLawyerProHint ? (
              <p className="mt-1 text-xs font-medium text-indigo-950/90">{t(locale, "clientModeLawyerNeedsPro")}</p>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={String(t(locale, "clientModeLabel"))}>
              <button
                type="button"
                aria-pressed={clientMode === "citizen"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistClientMode("citizen")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  clientMode === "citizen"
                    ? "border-indigo-800 bg-indigo-800 text-white shadow-sm"
                    : "border-indigo-800/35 bg-white text-indigo-950 hover:bg-indigo-100/80"
                }`}
              >
                {t(locale, "clientModeCitizen")}
              </button>
              <button
                type="button"
                aria-pressed={clientMode === "lawyer"}
                disabled={loading || ingesting || voiceTranscribing || !canSelectLawyer}
                title={
                  !canSelectLawyer
                    ? String(
                        t(
                          locale,
                          needLawyerSignInHint ? "clientModeLawyerNeedsSignIn" : "clientModeLawyerNeedsPro",
                        ),
                      )
                    : undefined
                }
                onClick={() => persistClientMode("lawyer")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  clientMode === "lawyer"
                    ? "border-indigo-800 bg-indigo-800 text-white shadow-sm"
                    : "border-indigo-800/35 bg-white text-indigo-950 hover:bg-indigo-100/80"
                }`}
              >
                {t(locale, "clientModeLawyer")}
              </button>
            </div>
          </fieldset>
        ) : null}
        {responseTaskUiEnabled ? (
          <fieldset className="rounded-xl border border-emerald-200/80 bg-emerald-50/40 px-3 py-3 sm:px-4">
            <legend className="px-1 text-sm font-semibold text-emerald-950">{t(locale, "taskTypeLabel")}</legend>
            <p className="mt-1 text-xs leading-relaxed text-emerald-950/80">{t(locale, "taskTypeHint")}</p>
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label={String(t(locale, "taskTypeLabel"))}>
              <button
                type="button"
                aria-pressed={taskType === "draft_letter"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistTaskType("draft_letter")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  taskType === "draft_letter"
                    ? "border-emerald-800 bg-emerald-800 text-white shadow-sm"
                    : "border-emerald-800/35 bg-white text-emerald-950 hover:bg-emerald-100/80"
                }`}
              >
                {t(locale, "taskTypeLetter")}
              </button>
              <button
                type="button"
                aria-pressed={taskType === "qa_only"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistTaskType("qa_only")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  taskType === "qa_only"
                    ? "border-emerald-800 bg-emerald-800 text-white shadow-sm"
                    : "border-emerald-800/35 bg-white text-emerald-950 hover:bg-emerald-100/80"
                }`}
              >
                {t(locale, "taskTypeQa")}
              </button>
              <button
                type="button"
                aria-pressed={taskType === "draft_with_qa"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistTaskType("draft_with_qa")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  taskType === "draft_with_qa"
                    ? "border-emerald-800 bg-emerald-800 text-white shadow-sm"
                    : "border-emerald-800/35 bg-white text-emerald-950 hover:bg-emerald-100/80"
                }`}
              >
                {t(locale, "taskTypeBoth")}
              </button>
              <button
                type="button"
                aria-pressed={taskType === "consumer_complaint_filing"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistTaskType("consumer_complaint_filing")}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${
                  taskType === "consumer_complaint_filing"
                    ? "border-emerald-800 bg-emerald-800 text-white shadow-sm"
                    : "border-emerald-800/35 bg-white text-emerald-950 hover:bg-emerald-100/80"
                }`}
              >
                {t(locale, "taskTypeConsumerFiling")}
              </button>
            </div>
          </fieldset>
        ) : null}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.text,.png,.jpg,.jpeg,.jfif,.webp,.gif,.heic,.bmp,.tiff,.tif,application/pdf,text/plain,text/markdown,image/png,image/jpeg,image/gif,image/webp,image/heic,image/bmp,image/tiff"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (!f) return;
            if (maxUploadBytes != null && f.size > maxUploadBytes) {
              onError(t(locale, "ingestFileTooLarge")(formatMaxUploadMbLabel(maxUploadBytes)));
              e.target.value = "";
              return;
            }
            setIngesting(true);
            setIngestNote(null);
            void ingestDocument(f, userId)
              .then((r) => {
                const block = r.extracted_text?.trim() ? r.extracted_text : "";
                if (!block) {
                  const rawWarn = (r.warning || "").trim();
                  const localized = localizeIngestServerWarning(locale, r.warning);
                  if (rawWarn === INGEST_SERVER_WARN_NO_TEXT_PDF) {
                    onError(`${localized}\n\n${t(locale, "ingestExplainScanHint")}`);
                  } else {
                    onError(localized || t(locale, "ingestEmptyExtract"));
                  }
                  return;
                }
                setInput((prev) => {
                  const p = prev.trim();
                  if (!p) return `${t(locale, "fromFileOnly")(r.filename)}${block}`;
                  return `${p}\n\n${t(locale, "fromFileAfterText")(r.filename)}${block}`;
                });
                setIngestNote(
                  (r.warning
                    ? localizeIngestServerWarning(locale, r.warning)
                    : r.format === "pdf"
                      ? t(locale, "ingestAfterPdf")
                      : r.format === "image"
                        ? t(locale, "ingestAfterImage")
                        : t(locale, "ingestAfterText")) + t(locale, "ingestAfterUsage")(r.usage.remaining, r.usage.limit),
                );
              })
              .catch((err: unknown) => {
                if (err instanceof IngestRequestError) {
                  onError(
                    messageForIngestError(
                      locale,
                      { message: err.message, errorCode: err.errorCode, status: err.status },
                      maxUploadBytes,
                      formatMaxUploadMbLabel
                    )
                  );
                  return;
                }
                onError(err instanceof Error ? err.message : t(locale, "uploadFailed"));
              })
              .finally(() => {
                setIngesting(false);
                e.target.value = "";
              });
          }}
        />
        <label className="block flex-1 text-sm font-medium text-stone-700 sm:text-base">
          {t(locale, "yourMessage")}
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={4}
            disabled={loading || ingesting || voiceTranscribing}
            placeholder={t(locale, "msgPlaceholder")}
            className="mt-2 min-h-[8.5rem] w-full resize-y rounded-xl border border-stone-200 bg-white px-3.5 py-3 text-base leading-relaxed text-stone-900 shadow-sm outline-none ring-amber-700/15 focus:border-amber-600 focus:ring-2 sm:min-h-[9rem]"
          />
        </label>
        <div className="flex shrink-0 flex-col gap-1.5 sm:items-stretch">
          <button
            type="button"
            disabled={loading || ingesting || voiceTranscribing}
            onClick={() => fileInputRef.current?.click()}
            className="rounded-xl border border-amber-800/35 bg-amber-50/90 px-4 py-3 text-base font-medium text-amber-950 shadow-sm hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {ingesting ? t(locale, "readFile") : t(locale, "attach")}
          </button>
          <button
            type="button"
            disabled={loading || ingesting || voiceTranscribing}
            onClick={() => void handleVoiceToggle()}
            aria-pressed={voiceRecording}
            className={`rounded-xl border px-4 py-3 text-base font-medium shadow-sm disabled:cursor-not-allowed disabled:opacity-50 ${
              voiceRecording
                ? "border-rose-700/50 bg-rose-600 text-white hover:bg-rose-700"
                : "border-amber-800/35 bg-white text-amber-950 hover:bg-amber-50/90"
            }`}
          >
            {voiceTranscribing
              ? t(locale, "voiceTranscribing")
              : voiceRecording
                ? t(locale, "voiceStop")
                : t(locale, "voiceRecord")}
          </button>
          <button
            type="submit"
            disabled={loading || ingesting || voiceTranscribing || !input.trim()}
            className="rounded-xl bg-amber-800 px-6 py-3 text-base font-semibold text-white shadow-md hover:bg-amber-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? t(locale, "working") : t(locale, "send")}
          </button>
        </div>
        </div>
        <p className="text-sm leading-relaxed text-stone-600">{t(locale, "voiceHint")}</p>
        {maxUploadBytes != null ? (
          <p className="text-sm text-stone-600">
            {t(locale, "attachSizeHint")(formatMaxUploadMbLabel(maxUploadBytes))}
          </p>
        ) : null}
        {ingestOcrReady ? (
          <p className="text-sm text-stone-600">{t(locale, "attachOcrHint")}</p>
        ) : null}
        {ingestNote ? <p className="text-sm text-stone-700">{ingestNote}</p> : null}
      </form>
    </section>
  );
}
