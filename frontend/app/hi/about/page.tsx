import type { Metadata } from "next";
import Link from "next/link";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "हमारे बारे में — NyayaSetu",
};

export default function AboutHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="/about">
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.aboutTitle}</h1>
        <div className="mt-8 space-y-6 text-base leading-relaxed text-stone-600">
          {b.aboutParagraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
        <p className="mt-10 text-sm font-medium text-stone-800">{b.disclaimerShort}</p>
        <p className="mt-6">
          <Link href="/chat" className="font-semibold text-amber-900 underline">
            {b.aboutCta}
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
