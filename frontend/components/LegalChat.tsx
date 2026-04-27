"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import {
  IngestRequestError,
  ingestDocument,
  streamGenerateLegalResponse,
  StreamNetworkFailed,
  transcribeAudio,
  createChatThread,
  fetchThreadMessages,
  patchChatThreadTitle,
  postChatMessage,
  type ChatHistoryMessage,
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

function threadStorageKey(clerkUserId: string): string {
  return `nyaya-chat-active-thread-${clerkUserId}`;
}

function titleFromFirstLine(text: string): string {
  const line = text.split(/\n/)[0]?.trim() || text.trim();
  const t = line.slice(0, 80).trim();
  return t || "Chat";
}

function assistantMetaFromMsg(m: ChatMsg): Record<string, unknown> | undefined {
  const o: Record<string, unknown> = {};
  if (m.options && m.options.length > 0) o.options = m.options;
  if (m.clarificationPoints && m.clarificationPoints.length > 0) o.clarificationPoints = m.clarificationPoints;
  if (m.clarifyingQuestions && m.clarifyingQuestions.length > 0) o.clarifyingQuestions = m.clarifyingQuestions;
  if (m.clarificationAgentQuestions && m.clarificationAgentQuestions.length > 0)
    o.clarificationAgentQuestions = m.clarificationAgentQuestions;
  if (m.clarificationOptional === true) o.clarificationOptional = true;
  if (m.clarificationNeeded === true) o.clarificationNeeded = true;
  return Object.keys(o).length > 0 ? o : undefined;
}

function chatRowToMsg(row: ChatHistoryMessage): ChatMsg {
  const base: ChatMsg = {
    id: row.id,
    role: row.role,
    content: row.content,
  };
  if (row.role !== "assistant" || !row.meta || typeof row.meta !== "object") return base;
  const meta = row.meta as Record<string, unknown>;
  const opts = meta.options;
  const cq = meta.clarifyingQuestions;
  const cp = meta.clarificationPoints;
  const caq = meta.clarificationAgentQuestions;
  return {
    ...base,
    options: Array.isArray(opts) ? opts.map(String) : undefined,
    clarifyingQuestions: Array.isArray(cq) ? cq.map(String) : undefined,
    clarificationPoints: Array.isArray(cp) ? (cp as ClarificationPoint[]) : undefined,
    clarificationAgentQuestions: Array.isArray(caq) ? (caq as ClarificationAgentQuestion[]) : undefined,
    clarificationOptional: meta.clarificationOptional === true,
    clarificationNeeded: meta.clarificationNeeded === true,
  };
}

function IconPaperclip({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

function IconMic({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function IconArrowUp({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </svg>
  );
}

function IconLineSpinner({ className, variant = "subtle" }: { className?: string; variant?: "subtle" | "onDark" }) {
  const base =
    variant === "onDark"
      ? "h-4 w-4 border-white/30 border-t-white"
      : "h-4 w-4 border-stone-200 border-t-amber-800";
  return (
    <span
      className={`inline-block shrink-0 animate-spin rounded-full border-2 ${base} ${className ?? ""}`}
      role="status"
      aria-hidden
    />
  );
}

function IconInfo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </svg>
  );
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
  /** P2-4: `NEXT_PUBLIC_RESPONSE_TASK_UI` at build time — show letter/Q&A/consumer style buttons (task is always sent when set, including from quick starts). */
  responseTaskUiEnabled?: boolean;
}) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  /** Server-backed thread id when signed in (SQLite via API). */
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
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
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
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
  const messagesRef = useRef<ChatMsg[]>([]);
  messagesRef.current = messages;
  const activeThreadIdRef = useRef<string | null>(null);
  activeThreadIdRef.current = activeThreadId;
  const ensureThreadPromiseRef = useRef<Promise<string | null> | null>(null);
  const needsThreadTitleRef = useRef(false);

  const ensureThread = useCallback(async (): Promise<string | null> => {
    const uid = userId?.trim();
    if (!uid) return null;
    if (activeThreadIdRef.current) return activeThreadIdRef.current;
    if (ensureThreadPromiseRef.current) return ensureThreadPromiseRef.current;
    const p = (async () => {
      const t = await createChatThread(uid);
      activeThreadIdRef.current = t.id;
      setActiveThreadId(t.id);
      needsThreadTitleRef.current = true;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(threadStorageKey(uid), t.id);
      }
      return t.id;
    })();
    ensureThreadPromiseRef.current = p;
    try {
      return await p;
    } finally {
      ensureThreadPromiseRef.current = null;
    }
  }, [userId]);

  const startNewConversation = useCallback(() => {
    setMessages([]);
    activeThreadIdRef.current = null;
    setActiveThreadId(null);
    needsThreadTitleRef.current = false;
    const uid = userId?.trim();
    if (uid && typeof window !== "undefined") {
      window.localStorage.removeItem(threadStorageKey(uid));
    }
  }, [userId]);

  const persistSignedInUserTurn = useCallback(
    async (displayedUserText: string) => {
      const uidStr = userId?.trim();
      if (!uidStr) return;
      const tid = await ensureThread();
      if (!tid) return;
      await postChatMessage(uidStr, tid, { role: "user", content: displayedUserText }).catch(() => {});
      if (needsThreadTitleRef.current) {
        needsThreadTitleRef.current = false;
        await patchChatThreadTitle(uidStr, tid, titleFromFirstLine(displayedUserText)).catch(() => {});
      }
    },
    [userId, ensureThread],
  );
  const canSelectLawyer =
    (!lawyerModeRequiresSignIn || Boolean(userId?.trim())) &&
    (!lawyerProGateActive || proEntitled);
  const needLawyerProHint = Boolean(lawyerProGateActive && !proEntitled);
  const needLawyerSignInHint = Boolean(lawyerModeRequiresSignIn && !userId?.trim());

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(TASK_TYPE_STORAGE_KEY);
    if (
      raw === "qa_only" ||
      raw === "draft_with_qa" ||
      raw === "draft_letter" ||
      raw === "consumer_complaint_filing"
    ) {
      setTaskType(raw);
    }
  }, []);

  const persistTaskType = useCallback((next: GenerateTaskType) => {
    setTaskType(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(TASK_TYPE_STORAGE_KEY, next);
    }
  }, []);

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

  useEffect(() => {
    if (!userId?.trim()) {
      setActiveThreadId(null);
      activeThreadIdRef.current = null;
      return;
    }
    if (typeof window === "undefined") return;
    const key = threadStorageKey(userId);
    const saved = window.localStorage.getItem(key);
    if (!saved) return;
    let cancelled = false;
    void fetchThreadMessages(userId, saved)
      .then((rows) => {
        if (cancelled) return;
        activeThreadIdRef.current = saved;
        setActiveThreadId(saved);
        needsThreadTitleRef.current = false;
        if (rows.length > 0) setMessages(rows.map(chatRowToMsg));
      })
      .catch(() => {
        window.localStorage.removeItem(key);
      });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus({ preventScroll: true });
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }, 100);
    return () => window.clearTimeout(id);
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
        payload.task_type = taskType;
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

      let assistantPlain = "";
      const appendToStream = (chunk: string) => {
        assistantPlain = assistantPlain ? `${assistantPlain}\n\n${chunk}` : chunk;
        appendAssistantChunk(assistantId, chunk);
      };

      const onEvent = (ev: StreamEvent) => {
        if (ev.type === "phase") {
          appendToStream(ev.message);
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
            appendToStream(ev.question || t(locale, "clarFastQuestions"));
          } else if (ev.question) {
            appendToStream(`❓ ${ev.question}`);
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
            appendToStream(t(locale, "streamDone"));
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
        const persistAssistant = () => {
          const uidStr = userId?.trim();
          const tid = activeThreadIdRef.current;
          if (!uidStr || !tid || !assistantPlain.trim()) return;
          const am = messagesRef.current.find((m) => m.id === assistantId);
          const meta = am?.role === "assistant" ? assistantMetaFromMsg(am) : undefined;
          void postChatMessage(uidStr, tid, { role: "assistant", content: assistantPlain, meta }).catch(() => {});
        };
        if (typeof window !== "undefined") {
          window.setTimeout(persistAssistant, 0);
        } else {
          persistAssistant();
        }
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

  async function handleSend(e?: FormEvent) {
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
    await persistSignedInUserTurn(text);
    await runStream(merged, { skipClarification: Boolean(mergeClarification) });
  }

  async function handleOptionClick(option: string) {
    const base = lastUserIssueRef.current.trim();
    const follow = `${base}\n\n${t(locale, "mergeMyChoice")} ${option}`;
    setLoading(true);
    setMessages((prev) => [...prev, { id: uid(), role: "user", content: follow }]);
    await persistSignedInUserTurn(follow);
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
    await persistSignedInUserTurn(follow);
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
    await persistSignedInUserTurn(follow);
    await runStream(follow, { skipClarification: true });
  }

  async function handleSkipOptionalClarification() {
    const base = lastUserIssueRef.current.trim();
    if (!base || loading) return;
    setLoading(true);
    await runStream(base, { skipClarification: true });
  }

  const lastAssistantId = [...messages].reverse().find((x) => x.role === "assistant")?.id;
  const lastAssistantMsg = messages.find((x) => x.id === lastAssistantId);
  const clarificationPtsForStructured = lastAssistantMsg?.clarificationPoints;
  const structuredReady =
    !!clarificationPtsForStructured &&
    clarificationPtsForStructured.length > 0 &&
    clarificationPtsForStructured.every((p) => structuredSelections[p.label]?.trim());
  const agentQsForReady = lastAssistantMsg?.clarificationAgentQuestions;
  const agentClarificationReady =
    !!agentQsForReady &&
    agentQsForReady.length > 0 &&
    agentQsForReady.every((q) => agentAnswerSelections[q.id]?.trim());

  const emptyThread = messages.length === 0;

  return (
    <section
      className={
        emptyThread
          ? "rounded-3xl border border-amber-200/35 bg-gradient-to-b from-amber-50/50 via-white to-stone-50/40 p-4 shadow-lg shadow-amber-950/10 ring-1 ring-amber-900/15 sm:p-6"
          : "rounded-2xl border border-stone-200/80 bg-gradient-to-b from-stone-50/50 to-white p-4 shadow-sm ring-1 ring-stone-200/40 sm:p-5"
      }
      aria-label={String(t(locale, "chatSectionAria"))}
    >
      {userId?.trim() ? (
        <div className="mb-3 flex justify-end">
          <button
            type="button"
            disabled={loading}
            onClick={() => startNewConversation()}
            className="rounded-xl border border-stone-300/90 bg-white px-3 py-2 text-sm font-semibold text-stone-800 shadow-sm transition hover:border-amber-400/70 hover:bg-amber-50/60 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t(locale, "chatNewThread")}
          </button>
        </div>
      ) : null}
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

      {messages.length > 0 ? (
      <div className="mt-3 max-h-[min(560px,62vh)] space-y-4 overflow-y-auto rounded-xl border border-stone-200/70 bg-white/60 p-3 sm:p-4">
        {messages.map((m) => {
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
          })}
      </div>
      ) : null}

      <form
        onSubmit={handleSend}
        className={`flex flex-col gap-2 ${messages.length > 0 ? "mt-3" : "mt-0"}`}
      >
        {emptyThread ? (
          <div className="order-1 mb-1 rounded-2xl border border-amber-200/50 bg-gradient-to-br from-white to-amber-50/60 px-4 py-4 shadow-sm ring-1 ring-amber-800/15 sm:px-5 sm:py-5">
            <p className="text-lg font-semibold tracking-tight text-stone-900 sm:text-xl">
              {t(locale, "composerHeroTitle")}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-stone-600">{t(locale, "composerHeroSub")}</p>
          </div>
        ) : null}
        <div className={`flex flex-col gap-2 ${emptyThread ? "order-3" : "order-1"}`}>
        {lawyerModeAvailable ? (
          <fieldset className="rounded-lg border border-indigo-200/50 bg-indigo-50/20 px-2.5 py-2 sm:px-3 sm:py-2.5">
            <legend className="flex w-full items-center gap-1.5 text-xs font-medium text-indigo-950/90 sm:text-sm">
              <span>{t(locale, "clientModeLabel")}</span>
              <button
                type="button"
                className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-indigo-800/50 transition hover:bg-indigo-100/90 hover:text-indigo-950"
                title={String(t(locale, "clientModeHint"))}
                aria-label={String(t(locale, "clientModeHint"))}
              >
                <IconInfo className="h-3.5 w-3.5" />
              </button>
            </legend>
            {needLawyerSignInHint ? (
              <p className="mb-1.5 text-xs font-medium text-indigo-950/90">{t(locale, "clientModeLawyerNeedsSignIn")}</p>
            ) : needLawyerProHint ? (
              <p className="mb-1.5 text-xs font-medium text-indigo-950/90">{t(locale, "clientModeLawyerNeedsPro")}</p>
            ) : null}
            <div className="mt-0 flex flex-wrap gap-1.5" role="group" aria-label={String(t(locale, "clientModeLabel"))}>
              <button
                type="button"
                aria-pressed={clientMode === "citizen"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistClientMode("citizen")}
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
          <fieldset className="rounded-lg border border-emerald-200/50 bg-emerald-50/20 px-2.5 py-2 sm:px-3 sm:py-2.5">
            <legend className="flex w-full items-center gap-1.5 text-xs font-medium text-emerald-950/90 sm:text-sm">
              <span>{t(locale, "taskTypeLabel")}</span>
              <button
                type="button"
                className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-emerald-800/50 transition hover:bg-emerald-100/90 hover:text-emerald-950"
                title={String(t(locale, "taskTypeHint"))}
                aria-label={String(t(locale, "taskTypeHint"))}
              >
                <IconInfo className="h-3.5 w-3.5" />
              </button>
            </legend>
            <div className="mt-0 flex flex-wrap gap-1.5" role="group" aria-label={String(t(locale, "taskTypeLabel"))}>
              <button
                type="button"
                aria-pressed={taskType === "draft_letter"}
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => persistTaskType("draft_letter")}
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
                className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition disabled:opacity-50 sm:px-3 sm:py-1.5 sm:text-sm ${
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
        </div>
        <div className="order-2 w-full max-w-4xl mx-auto">
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
        <div
          className={
            emptyThread
              ? "overflow-hidden rounded-2xl border-2 border-amber-400/40 bg-white shadow-lg shadow-amber-950/10 ring-2 ring-amber-500/20 transition focus-within:border-amber-600/70 focus-within:ring-amber-500/35"
              : "overflow-hidden rounded-2xl border border-stone-200/90 bg-white shadow-sm ring-1 ring-stone-200/30 transition focus-within:border-amber-500/45 focus-within:ring-2 focus-within:ring-amber-500/20"
          }
        >
          <label htmlFor="nyaya-composer" className="sr-only">
            {t(locale, "yourMessage")}
          </label>
          <textarea
            id="nyaya-composer"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e: KeyboardEvent<HTMLTextAreaElement>) => {
              if (e.key !== "Enter" || e.shiftKey) return;
              e.preventDefault();
              if (loading || ingesting || voiceTranscribing || !e.currentTarget.value.trim()) return;
              void handleSend();
            }}
            rows={emptyThread ? 4 : 1}
            disabled={loading || ingesting || voiceTranscribing}
            placeholder={t(locale, "msgPlaceholder")}
            title={String(t(locale, "composerSendShortcutHint"))}
            className={`max-h-[min(40vh,20rem)] w-full resize-y border-0 bg-transparent px-3 py-2.5 text-base leading-relaxed text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-0 sm:px-3.5 sm:py-3 ${
              emptyThread
                ? "min-h-[7.5rem] text-[1.05rem] placeholder:text-stone-500 sm:min-h-[8rem]"
                : "min-h-[2.75rem]"
            }`}
          />
          <div className="flex items-center justify-between gap-2 border-t border-stone-100/90 bg-stone-50/50 px-2 py-1.5 pl-1.5">
            <div className="flex min-w-0 items-center gap-0.5">
              <button
                type="button"
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100/90 hover:text-amber-900 disabled:cursor-not-allowed disabled:opacity-40"
                title={ingesting ? String(t(locale, "readFile")) : String(t(locale, "attach"))}
                aria-label={ingesting ? String(t(locale, "readFile")) : String(t(locale, "attach"))}
              >
                {ingesting ? <IconLineSpinner variant="subtle" /> : <IconPaperclip className="h-5 w-5" />}
              </button>
              <button
                type="button"
                disabled={loading || ingesting || voiceTranscribing}
                onClick={() => void handleVoiceToggle()}
                aria-pressed={voiceRecording}
                title={String(
                  voiceTranscribing
                    ? t(locale, "voiceTranscribing")
                    : voiceRecording
                      ? t(locale, "voiceStop")
                      : t(locale, "voiceHint"),
                )}
                aria-label={
                  voiceTranscribing
                    ? String(t(locale, "voiceTranscribing"))
                    : voiceRecording
                      ? String(t(locale, "voiceStop"))
                      : String(t(locale, "voiceRecord"))
                }
                className={`inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition disabled:cursor-not-allowed disabled:opacity-40 ${
                  voiceTranscribing
                    ? "text-amber-800/90"
                    : voiceRecording
                      ? "bg-rose-100 text-rose-700 ring-1 ring-rose-300/80 hover:bg-rose-200/80"
                      : "text-stone-500 hover:bg-stone-100/90 hover:text-amber-900"
                }`}
              >
                {voiceTranscribing ? <IconLineSpinner variant="subtle" /> : <IconMic className="h-5 w-5" />}
              </button>
            </div>
            <button
              type="submit"
              disabled={loading || ingesting || voiceTranscribing || !input.trim()}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-800 text-white shadow-sm transition hover:bg-amber-900 disabled:cursor-not-allowed disabled:bg-stone-200 disabled:text-stone-400"
              title={loading ? String(t(locale, "working")) : String(t(locale, "send"))}
              aria-label={loading ? String(t(locale, "working")) : String(t(locale, "send"))}
            >
              {loading ? <IconLineSpinner variant="onDark" /> : <IconArrowUp className="h-5 w-5" />}
            </button>
          </div>
        </div>
        </div>
        {maxUploadBytes != null || ingestOcrReady ? (
          <p className="order-4 text-center text-xs leading-snug text-stone-500 sm:text-left">
            {maxUploadBytes != null
              ? t(locale, "attachSizeHint")(formatMaxUploadMbLabel(maxUploadBytes))
              : null}
            {maxUploadBytes != null && ingestOcrReady ? (
              <span className="whitespace-nowrap" aria-hidden>
                {" "}
                ·{" "}
              </span>
            ) : null}
            {ingestOcrReady ? t(locale, "attachOcrHint") : null}
          </p>
        ) : null}
        {ingestNote ? <p className="order-4 text-sm text-stone-600">{ingestNote}</p> : null}
      </form>
    </section>
  );
}
