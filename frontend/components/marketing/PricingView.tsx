import Link from "next/link";
import { LiveDeploymentCaps } from "@/components/marketing/LiveDeploymentCaps";
import { mpath, marketingBundle, type MarketingLocale } from "@/lib/marketingBundles";

function IconCheck({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path
        fillRule="evenodd"
        d="M16.707 5.293a1 1 0 0 1 0 1.414l-8 8a1 1 0 0 1-1.414 0l-4-4a1 1 0 0 1 1.414-1.414L8 12.586l7.293-7.293a1 1 0 0 1 1.414 0z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/** Full marketing pricing page (`/pricing` redirects to home `#pricing`). Use `embedded` on the homepage. */
export function PricingView({
  locale,
  embedded = false,
}: {
  locale: MarketingLocale;
  embedded?: boolean;
}) {
  const b = marketingBundle(locale);
  const pn = b.pricingNotes;
  const chatHref = mpath(locale, "/chat");
  const liveCopy = { ...b.liveCaps, title: pn.livePanelTitle };

  const plansCompareAndLive = (
    <>
      <h2 className="text-2xl font-semibold text-stone-900">{pn.sectionPlans}</h2>
      <p className="mt-2 max-w-3xl text-pretty text-sm leading-relaxed text-stone-600 sm:text-base">{pn.sectionPlansSub}</p>
      <div className="mt-8 grid gap-5 lg:mt-9 lg:grid-cols-3 lg:items-stretch lg:gap-6">
        {pn.tiers.map((tier) => {
          const isHighlight = tier.highlight === true;
          return (
            <div
              key={tier.name}
              className={`relative flex flex-col overflow-hidden rounded-2xl p-6 sm:p-7 ${
                isHighlight
                  ? "border-2 border-amber-500/80 bg-gradient-to-b from-amber-50/90 via-white to-amber-50/30 shadow-xl shadow-amber-900/10 ring-1 ring-amber-300/40"
                  : "border border-stone-200/90 bg-white shadow-sm"
              }`}
            >
              {tier.badge ? (
                <span
                  className={`absolute right-3 top-3 rounded-full px-2.5 py-0.5 text-[11px] font-semibold sm:right-4 sm:top-4 sm:text-xs ${
                    isHighlight ? "bg-amber-800 text-white shadow" : "bg-stone-200/90 text-stone-800"
                  }`}
                >
                  {tier.badge}
                </span>
              ) : null}
              <p className="pr-16 text-xs font-semibold uppercase tracking-wider text-stone-500 sm:pr-20">{tier.name}</p>
              <p className="mt-3 text-3xl font-bold tabular-nums tracking-tight text-stone-900 sm:text-[2rem]">{tier.price}</p>
              {tier.priceSub ? <p className="mt-1.5 text-xs leading-relaxed text-stone-500">{tier.priceSub}</p> : null}
              <p className="mt-4 text-sm leading-relaxed text-stone-600 sm:text-[0.95rem]">{tier.blurb}</p>
              <ul className="mt-5 flex-1 space-y-2.5 text-sm text-stone-800">
                {tier.bullets.map((bl) => (
                  <li key={bl} className="flex gap-2.5">
                    <IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span className="leading-snug">{bl}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={chatHref}
                className={`mt-7 inline-flex w-full items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold transition sm:py-3.5 ${
                  isHighlight
                    ? "bg-amber-800 text-white shadow-md hover:bg-amber-900"
                    : "border border-stone-300/90 bg-white text-stone-900 shadow-sm hover:border-amber-400/70 hover:bg-amber-50/60"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          );
        })}
      </div>

      <h2 className="mt-16 text-2xl font-semibold text-stone-900 sm:mt-20">{pn.sectionCompare}</h2>
      <p className="mt-2 max-w-3xl text-pretty text-sm leading-relaxed text-stone-600 sm:text-base">{pn.compareSub}</p>
      <div className="mt-6 overflow-x-auto rounded-2xl border border-stone-200/80 bg-white shadow-sm ring-1 ring-stone-100/80">
        <table className="w-full min-w-[640px] text-left text-sm text-stone-700">
          <thead>
            <tr className="border-b border-amber-100/90 bg-gradient-to-r from-amber-50/50 to-stone-50/80">
              <th className="px-4 py-3.5 pl-5 text-xs font-semibold uppercase tracking-wider text-stone-500" scope="col">
                {pn.compareColFeature}
              </th>
              {pn.tiers.map((t) => (
                <th key={t.name} className="px-4 py-3.5 text-left text-sm font-semibold text-stone-900" scope="col">
                  {t.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pn.compareRows.map((row) => (
              <tr key={row.label} className="border-b border-stone-100/90 last:border-0">
                <th
                  className="whitespace-nowrap bg-stone-50/50 px-4 py-3 pl-5 text-left text-sm font-medium text-stone-800"
                  scope="row"
                >
                  {row.label}
                </th>
                <td className="px-4 py-3.5 text-stone-600">{row.guest}</td>
                <td className="px-4 py-3.5 text-stone-600">{row.signed}</td>
                <td className="pr-5 py-3.5 pl-4 text-stone-600">{row.pro}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="mt-16 text-2xl font-semibold text-stone-900 sm:mt-20">{pn.sectionLive}</h2>
      <p className="mt-2 max-w-3xl text-pretty text-sm leading-relaxed text-stone-600 sm:text-base">{pn.sectionLiveSub}</p>
      <div className="mt-5 max-w-2xl">
        <LiveDeploymentCaps copy={liveCopy} locale={locale} />
      </div>
      <p className="mt-4 max-w-3xl text-pretty text-sm leading-relaxed text-stone-500">{pn.liveSectionFootnote}</p>

      <p className="mt-10 max-w-2xl text-pretty text-sm text-stone-500">{b.disclaimerShort}</p>
    </>
  );

  if (embedded) {
    return (
      <section
        id="pricing"
        className="scroll-mt-24 border-t border-stone-200/80 bg-gradient-to-b from-stone-50/90 via-white to-amber-50/20 pb-14 pt-12 sm:pb-16 sm:pt-14"
      >
        <div className="mx-auto max-w-6xl px-4 sm:px-6">{plansCompareAndLive}</div>
      </section>
    );
  }

  return (
    <div>
      <section className="relative overflow-hidden border-b border-amber-200/50 bg-gradient-to-b from-amber-100/50 via-amber-50/40 to-white">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(180,83,9,0.12),transparent)]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-3xl px-4 py-12 text-center sm:px-6 sm:py-20">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-900/85">{pn.kicker}</p>
          <h1 className="mt-4 text-balance text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl sm:leading-[1.15] lg:text-[2.4rem]">
            {pn.title}
          </h1>
          <p className="mt-5 text-pretty text-base leading-relaxed text-stone-600 sm:text-lg">{pn.intro}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-2.5 sm:mt-9">
            {pn.heroPills.map((p) => (
              <span
                key={p}
                className="rounded-full border border-amber-200/80 bg-white/80 px-3.5 py-1.5 text-xs font-medium text-amber-950 shadow-sm sm:text-sm"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-12">{plansCompareAndLive}</div>
    </div>
  );
}
