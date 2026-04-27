"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { SignInButton, useAuth } from "@clerk/nextjs";
import { marketingBundle, mpath, type MarketingLocale } from "@/lib/marketingBundles";
import { NyayaSetuLogo, NyayaWordmark } from "./NyayaSetuLogo";

/** Highlights the nav item that matches this marketing page (`/` vs `/hi`, hash for `#pricing`). */
function marketingNavItemActive(
  pathname: string,
  hash: string,
  locale: MarketingLocale,
  itemPath: string,
): boolean {
  const onMarketingHome = pathname === "/" || pathname === "/hi";

  if (itemPath === "/" || itemPath === "") {
    return onMarketingHome && hash !== "#pricing";
  }
  if (itemPath.includes("#pricing")) {
    return onMarketingHome && hash === "#pricing";
  }

  const hrefBase = mpath(locale, itemPath).split("#")[0];
  return pathname === hrefBase || pathname.startsWith(`${hrefBase}/`);
}

function navItemClass(active: boolean): string {
  return active
    ? "rounded-lg px-3 py-2 text-sm font-semibold text-amber-950 ring-1 ring-amber-300/70 bg-amber-50"
    : "rounded-lg px-3 py-2 text-sm font-medium text-stone-700 transition hover:bg-stone-100 hover:text-stone-900";
}

export function MarketingHeader({
  locale,
  pathSuffix,
}: {
  locale: MarketingLocale;
  /** e.g. `/#pricing` or `` for home (used for locale switch) */
  pathSuffix: string;
}) {
  const pathname = usePathname();
  const { isSignedIn, isLoaded } = useAuth();
  const [open, setOpen] = useState(false);
  const [routeHash, setRouteHash] = useState("");
  const b = marketingBundle(locale);
  const other: MarketingLocale = locale === "en" ? "hi" : "en";
  const switchHref = mpath(other, pathSuffix);

  useEffect(() => {
    const syncHash = () => setRouteHash(typeof window !== "undefined" ? window.location.hash : "");
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-stone-200/80 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link
          href={mpath(locale, "/")}
          className="flex min-w-0 max-w-[min(100%,14rem)] items-center gap-2.5 rounded-xl outline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-600/80 sm:max-w-none md:gap-3"
          aria-label={`NyayaSetu — ${b.chrome.home}`}
          title={b.chrome.home}
        >
          <NyayaSetuLogo className="h-9 w-9 shrink-0" aria-hidden />
          <span className="flex min-w-0 flex-col leading-tight">
            <NyayaWordmark className="text-base sm:text-lg" />
            <span className="hidden truncate text-[11px] font-medium text-stone-500 sm:block sm:text-xs">
              {b.brandTagline}
            </span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {b.nav.map((item) => {
            const active = marketingNavItemActive(pathname, routeHash, locale, item.path);
            return (
              <Link
                key={`${item.path}-${item.label}`}
                href={mpath(locale, item.path)}
                className={navItemClass(active)}
                aria-current={active ? "page" : undefined}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <Link
            href={switchHref}
            className="rounded-lg px-2 py-2 text-xs font-semibold uppercase tracking-wide text-amber-900 hover:bg-amber-50"
            hrefLang={other === "hi" ? "hi" : "en"}
          >
            {locale === "en" ? "हिंदी" : "EN"}
          </Link>
          {isLoaded && !isSignedIn ? (
            <SignInButton mode="modal">
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100"
              >
                {b.chrome.signIn}
              </button>
            </SignInButton>
          ) : null}
          <Link
            href="/chat"
            className="rounded-xl bg-amber-800 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-amber-900"
          >
            {b.chrome.openApp}
          </Link>
        </div>

        <button
          type="button"
          className="rounded-lg p-2 text-stone-800 md:hidden"
          aria-expanded={open}
          aria-label={b.chrome.menu}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="sr-only">{b.chrome.menu}</span>
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
            {open ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {open ? (
        <div className="border-t border-stone-200 bg-white px-4 py-3 md:hidden">
          <nav className="flex flex-col gap-1" aria-label="Mobile">
            <Link
              href={switchHref}
              className="rounded-lg px-3 py-2 text-sm font-semibold text-amber-900"
              onClick={() => setOpen(false)}
              hrefLang={other === "hi" ? "hi" : "en"}
            >
              {locale === "en" ? "हिंदी" : "English"}
            </Link>
            {b.nav.map((item) => {
              const active = marketingNavItemActive(pathname, routeHash, locale, item.path);
              return (
                <Link
                  key={`${item.path}-${item.label}`}
                  href={mpath(locale, item.path)}
                  className={`rounded-lg px-3 py-2 text-sm ${active ? "bg-amber-50 font-semibold text-amber-950 ring-1 ring-amber-200/80" : "font-medium text-stone-800"}`}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setOpen(false)}
                >
                  {item.label}
                </Link>
              );
            })}
            <Link
              href="/chat"
              className="mt-2 rounded-xl bg-amber-800 px-3 py-2.5 text-center text-sm font-semibold text-white"
              onClick={() => setOpen(false)}
            >
              {b.chrome.openApp}
            </Link>
            {isLoaded && !isSignedIn ? (
              <div className="mt-2 flex justify-center">
                <SignInButton mode="modal">
                  <button type="button" className="text-sm font-medium text-amber-900 underline">
                    {b.chrome.signIn}
                  </button>
                </SignInButton>
              </div>
            ) : null}
          </nav>
        </div>
      ) : null}
    </header>
  );
}
