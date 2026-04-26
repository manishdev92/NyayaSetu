"use client";

import Link from "next/link";
import { RedirectToSignIn, useAuth, UserButton } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import {
  createDashboardCase,
  deleteDashboardCase,
  fetchDashboardCases,
  type DashboardCase,
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
