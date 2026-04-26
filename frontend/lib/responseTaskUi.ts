/**
 * P2-4: Q&A vs letter-drafting task selector in chat (not authentication).
 * Requires `NEXT_PUBLIC_RESPONSE_TASK_UI=1` at build time; sends `task_type` on generate JSON.
 */
export function isResponseTaskUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_RESPONSE_TASK_UI ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
