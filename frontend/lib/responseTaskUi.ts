/**
 * P2-4: Q&A / letter / consumer / both task selector in chat (not authentication).
 * When `NEXT_PUBLIC_RESPONSE_TASK_UI=1`, the extra style buttons are shown. `task_type` is
 * still sent for quick-start chips and persisted choice even when this flag is off.
 */
export function isResponseTaskUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_RESPONSE_TASK_UI ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
