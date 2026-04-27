"use client";

import Link from "next/link";
import { RedirectToSignIn, useAuth, UserButton } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import {
  createDashboardCase,
  deleteDashboardCase,
  fetchDashboardCases,
  fetchResponseFeedbackSummary,
  type DashboardCase,
  type ResponseFeedbackSummary,
} from "@/services/api";
import { formatApiThrowable } from "@/lib/apiErrorMessages";
import {
  authorityStatusLabel,
  getStoredLocale,
  t,
  type AppLocale,
} from "@/lib/i18n";

function labelFromSavedAuthority(
  locale: AppLocale,
  result: Record<string, unknown> | null,
): string | null {
  if (!result) return null;
  const raw = result.authority;
  if (!raw || typeof raw !== "object") return null;
  const st = (raw as { status?: unknown }).status;
  return typeof st === "string" ? authorityStatusLabel(locale, st) : null;
}

function shortDayLabel(isoDay: string): string {
  try {
    const d = new Date(`${isoDay}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return isoDay.slice(5);
    return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
  } catch {
    return isoDay.slice(5);
  }
}

function feedbackBarTooltip(
  locale: AppLocale,
  day: string,
  positive: number,
  total: number,
): string {
  const pct = total > 0 ? (positive / total) * 100 : 0;
  const dayLabel = shortDayLabel(day);
  if (locale === "hi") {
    return `${dayLabel}: ${positive}/${total} उपयोगी (${pct.toFixed(1)}%)`;
  }
  return `${dayLabel}: ${positive}/${total} helpful (${pct.toFixed(1)}%)`;
}

/**
 * P8-01 — signed-in dashboard with saved cases (`GET|POST|DELETE /dashboard/cases`).
 * Product notes: `docs/P8_DASHBOARD_SPEC.md`
 */
export default function LawyerDashboardPage() {
  const { isLoaded, isSignedIn, userId } = useAuth();
  const [locale, setLocale] = useState<AppLocale>("en");
  const [cases, setCases] = useState<DashboardCase[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [listErr, setListErr] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [saveBusy, setSaveBusy] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [feedbackSummary, setFeedbackSummary] = useState<ResponseFeedbackSummary | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackErr, setFeedbackErr] = useState<string | null>(null);
  const [feedbackDays, setFeedbackDays] = useState<7 | 30>(7);

  const analyticsAllowlist = (process.env.NEXT_PUBLIC_FEEDBACK_ANALYTICS_USERS || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  const canViewFeedbackAnalytics = Boolean(userId && analyticsAllowlist.includes(userId));

  useEffect(() => {
    setLocale(getStoredLocale());
    const onStorage = (e: StorageEvent) => {
      if (e.key === "nyaya-locale") setLocale(getStoredLocale());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const refresh = useCallback(async () => {
    if (!userId) return;
    setListLoading(true);
    setListErr(null);
    try {
      const rows = await fetchDashboardCases(userId);
      setCases(rows);
    } catch (e) {
      setListErr(formatApiThrowable(locale, e));
    } finally {
      setListLoading(false);
    }
  }, [userId, locale]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !userId) return;
    void refresh();
  }, [isLoaded, isSignedIn, userId, refresh]);

  useEffect(() => {
    if (!isLoaded || !isSignedIn || !canViewFeedbackAnalytics) return;
    let cancelled = false;
    setFeedbackLoading(true);
    setFeedbackErr(null);
    void fetchResponseFeedbackSummary(feedbackDays)
      .then((sum) => {
        if (cancelled) return;
        setFeedbackSummary(sum);
        if (!sum) setFeedbackErr("Could not load feedback summary.");
      })
      .catch((e) => {
        if (cancelled) return;
        setFeedbackErr(formatApiThrowable(locale, e));
      })
      .finally(() => {
        if (!cancelled) setFeedbackLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, canViewFeedbackAnalytics, locale, feedbackDays]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!userId || !title.trim()) return;
    setSaveBusy(true);
    setSaveErr(null);
    try {
      await createDashboardCase(userId, { title: title.trim(), summary: summary.trim() || undefined });
      setTitle("");
      setSummary("");
      await refresh();
    } catch (err) {
      setSaveErr(formatApiThrowable(locale, err));
    } finally {
      setSaveBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!userId) return;
    setDeletingId(id);
    setListErr(null);
    try {
      await deleteDashboardCase(userId, id);
      setCases((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setListErr(formatApiThrowable(locale, err));
    } finally {
      setDeletingId(null);
    }
  }

  if (!isLoaded) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50 text-sm text-stone-600">
        {t(locale, "dashboardLoading")}
      </div>
    );
  }

  if (!isSignedIn) {
    return <RedirectToSignIn />;
  }

  return (
    <div className="min-h-screen bg-stone-50 px-4 py-8 text-stone-900">
      <header className="mx-auto flex max-w-3xl flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-amber-900/80">{t(locale, "heroBrand")}</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">{t(locale, "dashboardTitle")}</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-stone-600">{t(locale, "dashboardIntro")}</p>
        </div>
        <UserButton />
      </header>

      <main className="mx-auto mt-10 max-w-3xl space-y-8">
        <section className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-stone-900">{t(locale, "dashboardSaveCase")}</h2>
          <form className="mt-4 space-y-4" onSubmit={onSave}>
            <div>
              <label className="mb-1 block text-xs font-medium text-stone-600" htmlFor="dash-title">
                {t(locale, "dashboardCaseTitleLabel")}
              </label>
              <input
                id="dash-title"
                className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none ring-amber-900/20 focus:ring-2"
                value={title}
                onChange={(ev) => setTitle(ev.target.value)}
                placeholder={t(locale, "dashboardCaseTitlePh")}
                maxLength={500}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-stone-600" htmlFor="dash-summary">
                {t(locale, "dashboardCaseSummaryLabel")}
              </label>
              <textarea
                id="dash-summary"
                rows={4}
                className="w-full resize-y rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none ring-amber-900/20 focus:ring-2"
                value={summary}
                onChange={(ev) => setSummary(ev.target.value)}
                placeholder={t(locale, "dashboardCaseSummaryPh")}
                maxLength={4000}
              />
            </div>
            {saveErr ? (
              <p className="text-sm text-red-800" role="alert">
                {saveErr}
              </p>
            ) : null}
            <button
              type="submit"
              disabled={saveBusy || !title.trim()}
              className="rounded-lg bg-amber-900 px-4 py-2 text-sm font-medium text-white hover:bg-amber-950 disabled:opacity-50"
            >
              {saveBusy ? t(locale, "working") : t(locale, "dashboardSaveCase")}
            </button>
          </form>
        </section>

        <section className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold text-stone-900">{t(locale, "dashboardTitle")}</h2>
            {listLoading ? <span className="text-xs text-stone-500">{t(locale, "working")}</span> : null}
          </div>
          {listErr ? (
            <p className="mt-3 text-sm text-red-800" role="alert">
              {listErr}
            </p>
          ) : null}
          {!listLoading && cases.length === 0 && !listErr ? (
            <p className="mt-4 text-sm leading-relaxed text-stone-600">{t(locale, "dashboardEmptyCases")}</p>
          ) : null}
          <ul className="mt-4 divide-y divide-stone-100">
            {cases.map((c) => {
              const authLine = labelFromSavedAuthority(locale, c.result);
              return (
              <li key={c.id} className="flex flex-col gap-2 py-4 first:pt-0 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-stone-900">{c.title}</p>
                  {c.summary ? <p className="mt-1 text-sm text-stone-600">{c.summary}</p> : null}
                  {authLine ? <p className="mt-2 text-xs text-stone-500">{authLine}</p> : null}
                  <p className="mt-1 text-xs text-stone-400">
                    {t(locale, "dashboardUpdated")}: {new Date(c.updated_at).toLocaleString()}
                  </p>
                </div>
                <button
                  type="button"
                  className="shrink-0 text-sm font-medium text-red-800 underline decoration-red-800/30 underline-offset-2 hover:text-red-950 disabled:opacity-50"
                  disabled={deletingId === c.id}
                  onClick={() => void onDelete(c.id)}
                >
                  {deletingId === c.id ? t(locale, "working") : t(locale, "dashboardDeleteCase")}
                </button>
              </li>
              );
            })}
          </ul>
        </section>

        {canViewFeedbackAnalytics ? (
          <section className="rounded-2xl border border-indigo-200/70 bg-indigo-50/40 p-6 shadow-sm">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold text-indigo-950">{t(locale, "dashboardFeedbackTitle")}</h2>
              <div className="flex items-center gap-2">
                <div className="inline-flex rounded-md border border-indigo-200 bg-white p-0.5">
                  <button
                    type="button"
                    onClick={() => setFeedbackDays(7)}
                    className={`rounded px-2 py-1 text-xs font-semibold ${
                      feedbackDays === 7 ? "bg-indigo-700 text-white" : "text-indigo-900 hover:bg-indigo-50"
                    }`}
                  >
                    7d
                  </button>
                  <button
                    type="button"
                    onClick={() => setFeedbackDays(30)}
                    className={`rounded px-2 py-1 text-xs font-semibold ${
                      feedbackDays === 30 ? "bg-indigo-700 text-white" : "text-indigo-900 hover:bg-indigo-50"
                    }`}
                  >
                    30d
                  </button>
                </div>
                <span className="text-xs text-indigo-800/80">
                  {(t(locale, "dashboardFeedbackWindow") as (days: number) => string)(feedbackDays)}
                </span>
              </div>
            </div>
            <p className="mt-1 text-sm leading-relaxed text-indigo-900/85">{t(locale, "dashboardFeedbackIntro")}</p>
            {feedbackErr ? (
              <p className="mt-3 text-sm text-red-800" role="alert">
                {feedbackErr}
              </p>
            ) : null}
            {feedbackLoading ? <p className="mt-3 text-xs text-indigo-800/70">{t(locale, "working")}</p> : null}
            {feedbackSummary ? (
              <div className="mt-4 space-y-4">
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-2">
                    <p className="text-xs text-indigo-800/75">{t(locale, "dashboardFeedbackTotal")}</p>
                    <p className="mt-1 text-lg font-semibold text-indigo-950">{feedbackSummary.total}</p>
                  </div>
                  <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-2">
                    <p className="text-xs text-indigo-800/75">{t(locale, "dashboardFeedbackPositive")}</p>
                    <p className="mt-1 text-lg font-semibold text-indigo-950">{feedbackSummary.positive}</p>
                  </div>
                  <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-2">
                    <p className="text-xs text-indigo-800/75">{t(locale, "dashboardFeedbackPositiveRate")}</p>
                    <p className="mt-1 text-lg font-semibold text-indigo-950">
                      {(feedbackSummary.positive_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
                <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-3">
                  <p className="text-xs font-semibold text-indigo-900">{t(locale, "dashboardFeedbackTrend")}</p>
                  <div className="mt-2 overflow-x-auto pb-1">
                    <div className="flex min-w-[300px] items-end gap-1.5">
                    {feedbackSummary.by_day.slice(-feedbackDays).map((d) => {
                      const ratio = d.total > 0 ? d.positive / d.total : 0;
                      const h = 18 + Math.round(ratio * 34);
                      const tip = feedbackBarTooltip(locale, d.day, d.positive, d.total);
                      return (
                        <div key={d.day} className="flex min-w-0 flex-1 flex-col items-center gap-1">
                          <div
                            className={`w-full rounded-t ${
                              d.total === 0 ? "bg-stone-200" : ratio >= 0.75 ? "bg-emerald-500" : ratio >= 0.5 ? "bg-amber-500" : "bg-rose-500"
                            }`}
                            style={{ height: `${h}px` }}
                            title={tip}
                            aria-label={tip}
                          />
                          <span className="truncate text-[10px] text-indigo-800/80">{shortDayLabel(d.day)}</span>
                        </div>
                      );
                    })}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-indigo-900/80">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden />
                      {t(locale, "dashboardFeedbackLegendHigh")}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden />
                      {t(locale, "dashboardFeedbackLegendMid")}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-rose-500" aria-hidden />
                      {t(locale, "dashboardFeedbackLegendLow")}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-stone-200" aria-hidden />
                      {t(locale, "dashboardFeedbackLegendNoData")}
                    </span>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-3">
                    <p className="text-xs font-semibold text-indigo-900">{t(locale, "dashboardFeedbackByMode")}</p>
                    <ul className="mt-2 space-y-1.5 text-sm text-indigo-950">
                      {feedbackSummary.by_mode.map((m) => (
                        <li key={m.client_mode} className="flex items-center justify-between gap-2">
                          <span>{m.client_mode}</span>
                          <span className="text-indigo-900/80">
                            {m.positive}/{m.total}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="rounded-lg border border-indigo-200/80 bg-white/90 px-3 py-3">
                    <p className="text-xs font-semibold text-indigo-900">{t(locale, "dashboardFeedbackByTask")}</p>
                    <ul className="mt-2 space-y-1.5 text-sm text-indigo-950">
                      {feedbackSummary.by_task_type.map((m) => (
                        <li key={m.task_type} className="flex items-center justify-between gap-2">
                          <span className="truncate">{m.task_type}</span>
                          <span className="text-indigo-900/80">
                            {m.positive}/{m.total}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        <Link
          href="/chat"
          className="inline-block text-sm font-medium text-amber-900 underline decoration-amber-800/40 underline-offset-2 hover:text-amber-950"
        >
          {t(locale, "dashboardBackHome")}
        </Link>
      </main>
    </div>
  );
}
