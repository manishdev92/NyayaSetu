import type { Metadata } from "next";
import Link from "next/link";
import { LiveDeploymentCaps } from "@/components/marketing/LiveDeploymentCaps";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "मूल्य निर्धारण — NyayaSetu",
};

export default function PricingHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="/pricing">
      <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.pricingNotes.title}</h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-stone-600">{b.pricingNotes.intro}</p>
        <div className="mt-10 max-w-2xl">
          <LiveDeploymentCaps copy={b.liveCaps} />
        </div>
        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {b.pricingNotes.tiers.map((tier) => (
            <div
              key={tier.name}
              className="flex flex-col rounded-2xl border border-stone-200 bg-white p-6 shadow-sm"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{tier.name}</p>
              <p className="mt-2 text-2xl font-semibold text-stone-900">{tier.price}</p>
              <p className="mt-2 text-sm text-stone-600">{tier.blurb}</p>
              <ul className="mt-4 flex-1 list-disc space-y-2 pl-5 text-sm text-stone-700">
                {tier.bullets.map((bl) => (
                  <li key={bl}>{bl}</li>
                ))}
              </ul>
              <Link
                href="/chat"
                className="mt-6 inline-flex justify-center rounded-xl bg-amber-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-amber-900"
              >
                {b.pricingNotes.openApp}
              </Link>
            </div>
          ))}
        </div>
        <p className="mt-12 text-sm text-stone-500">{b.disclaimerShort}</p>
      </div>
    </MarketingShell>
  );
}
