import type { ReactNode } from "react";
import type { MarketingLocale } from "@/lib/marketingBundles";
import { MarketingFooter } from "./MarketingFooter";
import { MarketingHeader } from "./MarketingHeader";

export function MarketingShell({
  locale = "en",
  pathSuffix = "",
  children,
}: {
  locale?: MarketingLocale;
  /** Path without locale prefix, e.g. `/faq` or `` for home */
  pathSuffix?: string;
  children: ReactNode;
}) {
  return (
    <div
      className="flex min-h-full flex-col bg-gradient-to-b from-stone-50 via-white to-stone-100/80 text-stone-900"
      lang={locale === "hi" ? "hi" : "en"}
    >
      <MarketingHeader locale={locale} pathSuffix={pathSuffix} />
      <main className="flex-1">{children}</main>
      <MarketingFooter locale={locale} />
    </div>
  );
}
