import type { Metadata } from "next";
import Link from "next/link";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "Features — NyayaSetu",
  description: "Chat, drafting, authority context, uploads, and optional research hints for Indian legal workflows.",
};

export default function FeaturesPage() {
  const b = marketingBundle("en");
  return (
    <MarketingShell locale="en" pathSuffix="/features">
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.featuresTitle}</h1>
        <p className="mt-4 text-base leading-relaxed text-stone-600">{b.featuresIntro}</p>
        <ul className="mt-10 space-y-8">
          {b.featureBlocks.map((f) => (
            <li key={f.title} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-stone-900">{f.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-stone-600">{f.body}</p>
            </li>
          ))}
        </ul>
        <p className="mt-10 text-sm text-stone-500">{b.disclaimerShort}</p>
        <p className="mt-6">
          <Link href="/chat" className="font-semibold text-amber-900 underline">
            {b.featuresLaunch}
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
