"use client";

import { useEffect, useState } from "react";
import { fetchPublicConfig, type PublicConfig } from "@/services/api";
import type { MarketingBundle } from "@/lib/marketingBundles";

export function LiveDeploymentCaps({ copy }: { copy: MarketingBundle["liveCaps"] }) {
  const [cfg, setCfg] = useState<PublicConfig | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    void fetchPublicConfig().then((c) => {
      if (!cancelled) setCfg(c);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (cfg === undefined) {
    return (
      <div
        className="rounded-2xl border border-stone-200 bg-stone-50/80 px-4 py-3 text-sm text-stone-600"
        role="status"
      >
        {copy.loading}
      </div>
    );
  }

  if (cfg === null) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50/80 px-4 py-3 text-sm text-amber-950" role="status">
        {copy.offline}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-emerald-200/80 bg-emerald-50/40 px-5 py-4 shadow-sm">
      <h2 className="text-sm font-semibold text-emerald-950">{copy.title}</h2>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-stone-500">{copy.dailyAuth}</dt>
          <dd className="font-medium text-stone-900">{cfg.daily_limit_authenticated}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.dailyPro}</dt>
          <dd className="font-medium text-stone-900">{cfg.daily_limit_pro}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.billingMode}</dt>
          <dd className="font-medium text-stone-900">{cfg.billing_mode}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.paywall}</dt>
          <dd className="font-medium text-stone-900">{cfg.paywall_visible ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.rag}</dt>
          <dd className="font-medium text-stone-900">{cfg.rag_vector_store}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.stripeCheckout}</dt>
          <dd className="font-medium text-stone-900">{cfg.stripe_checkout_ready ? "yes" : "no"}</dd>
        </div>
        <div>
          <dt className="text-stone-500">{copy.stripePortal}</dt>
          <dd className="font-medium text-stone-900">{cfg.stripe_portal_ready ? "yes" : "no"}</dd>
        </div>
      </dl>
    </div>
  );
}
