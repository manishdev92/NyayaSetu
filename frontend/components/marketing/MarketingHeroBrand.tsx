import { NyayaSetuLogo, NyayaWordmark } from "./NyayaSetuLogo";
import type { MarketingBundle } from "@/lib/marketingBundles";

/** Centered logo + wordmark + NyayGuru-style tagline for marketing home heroes. */
export function MarketingHeroBrand({ bundle }: { bundle: MarketingBundle }) {
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center sm:gap-5">
      <NyayaSetuLogo className="h-14 w-14 shrink-0 sm:h-16 sm:w-16" aria-hidden />
      <div className="max-w-xl text-center sm:text-left">
        <NyayaWordmark className="text-2xl sm:text-3xl" />
        <p className="mt-1.5 text-sm font-medium leading-snug text-stone-600 sm:text-base">{bundle.brandTagline}</p>
      </div>
    </div>
  );
}
