"use client";

import { useEffect } from "react";

/** Pricing lives on the homepage (`/#pricing`). Server redirects omit fragments; navigate client-side. */
export default function PricingRedirectPage() {
  useEffect(() => {
    window.location.replace("/#pricing");
  }, []);
  return null;
}
