import type { Metadata } from "next";
import Link from "next/link";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "सामान्य प्रश्न — NyayaSetu",
};

export default function FaqHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="/faq">
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.faqTitle}</h1>
        <p className="mt-4 text-sm text-stone-600">{b.disclaimerShort}</p>
        <dl className="mt-10 space-y-8">
          {b.faqItems.map((item) => (
            <div key={item.q} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <dt className="text-base font-semibold text-stone-900">{item.q}</dt>
              <dd className="mt-2 text-sm leading-relaxed text-stone-600">{item.a}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-10">
          <Link href="/chat" className="font-semibold text-amber-900 underline">
            {b.faqBack}
          </Link>
        </p>
      </div>
    </MarketingShell>
  );
}
