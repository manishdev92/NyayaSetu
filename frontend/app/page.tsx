import type { Metadata } from "next";
import { LandingChatHero } from "@/components/marketing/LandingChatHero";
import { MarketingShell } from "@/components/marketing/MarketingShell";
import { PricingView } from "@/components/marketing/PricingView";
import { marketingBundle } from "@/lib/marketingBundles";

export const metadata: Metadata = {
  title: "NyayaSetu — AI legal companion for India",
  description:
    "Start in chat: plain-language guidance and drafts for everyday Indian legal questions. Then review transparent plans and limits.",
};

export default function MarketingHomePage() {
  const b = marketingBundle("en");
  return (
    <MarketingShell locale="en" pathSuffix="">
      <LandingChatHero bundle={b} />
      <PricingView locale="en" embedded />
    </MarketingShell>
  );
}
