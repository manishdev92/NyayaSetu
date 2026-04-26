import type { Metadata } from "next";
import Link from "next/link";
import { MarketingHeroBrand } from "@/components/marketing/MarketingHeroBrand";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "NyayaSetu — AI legal companion for India",
  description:
    "Structured guidance, drafting, and next steps for everyday Indian legal questions. Not a law firm—verify with official sources.",
};

export default function MarketingHomePage() {
  const b = marketingBundle("en");
  return (
    <MarketingShell locale="en" pathSuffix="">
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
        <div className="mx-auto max-w-3xl">
          <MarketingHeroBrand bundle={b} />
        </div>
        <h1 className="mt-10 text-center text-4xl font-semibold tracking-tight text-stone-900 sm:mt-12 sm:text-5xl lg:text-6xl">
          {b.hero.title}
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-center text-lg leading-relaxed text-stone-600 sm:text-xl">
          {b.hero.subtitle}
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/chat"
            className="inline-flex w-full max-w-xs items-center justify-center rounded-2xl bg-amber-800 px-6 py-3.5 text-base font-semibold text-white shadow-md transition hover:bg-amber-900 sm:w-auto"
          >
            {b.hero.primaryCta}
          </Link>
          <Link
            href="/how-it-works"
            className="inline-flex w-full max-w-xs items-center justify-center rounded-2xl border border-stone-300 bg-white px-6 py-3.5 text-base font-semibold text-stone-800 shadow-sm transition hover:bg-stone-50 sm:w-auto"
          >
            {b.hero.secondaryCta}
          </Link>
        </div>
        <p className="mx-auto mt-8 max-w-3xl text-center text-sm leading-relaxed text-stone-500">{b.disclaimerShort}</p>
      </section>

      <section className="border-y border-stone-200/80 bg-white/60 py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-center text-2xl font-semibold text-stone-900 sm:text-3xl">{b.home.trustH2}</h2>
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {b.trustPoints.map((item) => (
              <div key={item.title} className="rounded-2xl border border-stone-200/90 bg-stone-50/50 p-6 shadow-sm">
                <h3 className="text-lg font-semibold text-stone-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-stone-600">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
        <h2 className="text-center text-2xl font-semibold text-stone-900 sm:text-3xl">{b.home.pillarsH2}</h2>
        <p className="mx-auto mt-3 max-w-2xl text-center text-sm text-stone-600">{b.home.pillarsSub}</p>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {b.featureBlocks.map((f) => (
            <div
              key={f.title}
              className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:border-amber-200/60 hover:shadow-md"
            >
              <h3 className="text-base font-semibold text-stone-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-stone-600">{f.body}</p>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <Link href="/features" className="text-sm font-semibold text-amber-900 underline decoration-amber-800/30">
            {b.home.fullFeatureLink}
          </Link>
        </div>
      </section>

      <section className="bg-amber-950 py-16 text-amber-50 sm:py-20">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <h2 className="text-2xl font-semibold sm:text-3xl">{b.home.ctaH2}</h2>
          <p className="mt-4 text-sm leading-relaxed text-amber-100/90">{b.home.ctaSub}</p>
          <Link
            href="/chat"
            className="mt-8 inline-flex rounded-2xl bg-white px-6 py-3.5 text-base font-semibold text-amber-950 shadow-md hover:bg-amber-50"
          >
            {b.home.ctaButton}
          </Link>
        </div>
      </section>
    </MarketingShell>
  );
}
