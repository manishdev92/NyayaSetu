import type { Metadata } from "next";
import Link from "next/link";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "यह कैसे काम करता है — NyayaSetu",
};

export default function HowItWorksHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="/how-it-works">
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.howTitle}</h1>
        <p className="mt-4 text-base leading-relaxed text-stone-600">{b.howIntro}</p>
        <ol className="mt-12 space-y-10">
          {b.howItWorksSteps.map((s) => (
            <li key={s.step} className="flex gap-4">
              <span
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-950"
                aria-hidden
              >
                {s.step}
              </span>
              <div>
                <h2 className="text-lg font-semibold text-stone-900">{s.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-stone-600">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="mt-10 text-sm text-stone-500">{b.disclaimerShort}</p>
        <Link
          href="/chat"
          className="mt-6 inline-flex rounded-xl bg-amber-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-900"
        >
          {b.howTry}
        </Link>
      </div>
    </MarketingShell>
  );
}
