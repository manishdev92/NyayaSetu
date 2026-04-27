"use client";

import { useEffect } from "react";

/** Pricing lives on the Hindi homepage (`/hi#pricing`). */
export default function PricingHiRedirectPage() {
  useEffect(() => {
    window.location.replace("/hi#pricing");
  }, []);
  return null;
}
