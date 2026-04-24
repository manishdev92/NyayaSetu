"use client";

import { useEffect } from "react";

/**
 * Registers `/sw.js` in production only (P7-01). Dev uses fast refresh; use `next build && next start` to test SW.
 * Set `NEXT_PUBLIC_DISABLE_SW=1` to skip registration in prod builds.
 */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    if (process.env.NEXT_PUBLIC_DISABLE_SW === "1") return;
    if (process.env.NODE_ENV !== "production") return;

    void navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* ignore registration failures (HTTP, private mode, etc.) */
    });
  }, []);

  return null;
}
