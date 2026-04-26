import type { Metadata } from "next";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "Contact — NyayaSetu",
  description: "Reach the team behind your NyayaSetu deployment.",
};

export default function ContactPage() {
  const b = marketingBundle("en");
  const email = process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim();

  return (
    <MarketingShell locale="en" pathSuffix="/contact">
      <div className="mx-auto max-w-2xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.contactTitle}</h1>
        <p className="mt-4 text-base leading-relaxed text-stone-600">{b.contactIntro}</p>
        {email ? (
          <p className="mt-8">
            <span className="text-sm font-medium text-stone-500">{b.contactEmailLabel}: </span>
            <a href={`mailto:${email}`} className="font-semibold text-amber-900 underline">
              {email}
            </a>
          </p>
        ) : (
          <p className="mt-8 rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-700">
            {b.contactNoEmail}
          </p>
        )}
        <p className="mt-8 text-sm text-stone-600">{b.contactNote}</p>
      </div>
    </MarketingShell>
  );
}
