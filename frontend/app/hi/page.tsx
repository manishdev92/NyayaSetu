import type { Metadata } from "next";
import { LandingChatHero } from "@/components/marketing/LandingChatHero";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { PricingView } from "@/components/marketing/PricingView";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "NyayaSetu — भारत के लिए AI कानूनी साथी",
  description:
    "चैट से शुरू करें—सादी भाषा में मार्गदर्शन और मसौदा। फिर योजना और सीमाएँ देखें।",
};

export default function MarketingHomeHiPage() {
  const b = marketingBundle("hi");
  return (
    <MarketingShell locale="hi" pathSuffix="">
      <LandingChatHero bundle={b} />
      <PricingView locale="hi" embedded />
    </MarketingShell>
  );
}
