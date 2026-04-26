import type { Metadata } from "next";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "ब्लॉग — NyayaSetu",
};

export default function BlogHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="/blog">
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6 sm:py-20">
        <h1 className="text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">{b.blogTitle}</h1>
        <p className="mt-4 text-base leading-relaxed text-stone-600">{b.blogIntro}</p>
        <div className="mt-10 rounded-2xl border border-dashed border-stone-300 bg-white/80 px-6 py-10 text-center text-sm text-stone-600">
          {b.blogSoon}
        </div>
      </div>
    </MarketingShell>
  );
}
