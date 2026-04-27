import Link from "next/link";
import type { MarketingBundle } from "@/lib/marketingBundles";
import { NyayaSetuLogo, NyayaWordmark } from "./NyayaSetuLogo";

/** Chat-first home hero — minimal copy, comfortable spacing, single primary action. */
export function LandingChatHero({ bundle: b }: { bundle: MarketingBundle }) {
  const { landing } = b;
  return (
    <section className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_85%_55%_at_50%_-15%,rgba(245,158,11,0.14),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-24 top-1/3 h-72 w-72 rounded-full bg-amber-200/25 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-20 bottom-0 h-64 w-64 rounded-full bg-stone-300/20 blur-3xl"
        aria-hidden
      />

      <div className="relative mx-auto flex min-h-[min(78vh,720px)] max-w-6xl flex-col justify-center px-4 py-14 sm:px-6 sm:py-20">
        <div className="mx-auto w-full max-w-lg">
          <div className="rounded-[1.75rem] border border-white/90 bg-white/85 p-8 shadow-[0_24px_60px_-12px_rgba(28,25,23,0.12)] ring-1 ring-stone-200/70 backdrop-blur-md sm:p-10">
            <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:items-center sm:justify-center sm:gap-5 sm:text-left">
              <NyayaSetuLogo className="h-12 w-12 shrink-0 sm:h-14 sm:w-14" aria-hidden />
              <div>
                <NyayaWordmark className="text-xl sm:text-2xl" />
                <p className="mt-1 text-sm font-medium text-stone-500">{b.brandTagline}</p>
              </div>
            </div>

            <h1 className="mt-8 text-center text-[1.65rem] font-semibold leading-snug tracking-tight text-stone-900 sm:text-3xl md:text-[2rem]">
              {landing.headline}
            </h1>
            <p className="mx-auto mt-4 max-w-md text-center text-base leading-relaxed text-stone-600">{landing.subline}</p>

            <div className="mt-10 flex flex-col items-stretch gap-3 sm:mx-auto sm:max-w-sm">
              <Link
                href="/chat"
                className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-br from-amber-800 to-amber-950 px-6 py-4 text-center text-base font-semibold text-white shadow-lg shadow-amber-900/25 transition hover:shadow-xl hover:shadow-amber-900/30"
              >
                {landing.openChat}
              </Link>
              <a
                href="#pricing"
                className="inline-flex items-center justify-center rounded-2xl border border-stone-200/90 bg-stone-50/80 px-6 py-3.5 text-center text-sm font-semibold text-stone-800 transition hover:border-amber-300/80 hover:bg-amber-50/50"
              >
                {landing.seePricing}
              </a>
            </div>

            <p className="mt-8 text-center text-xs leading-relaxed text-stone-500">{landing.legalNote}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
