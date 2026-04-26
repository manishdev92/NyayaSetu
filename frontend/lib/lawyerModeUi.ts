/**
 * P1-4: gate the lawyer / citizen toggle in the chat UI.
 * Requires `NEXT_PUBLIC_LAWYER_MODE_UI=1` at build time AND `lawyer` in `GET /config` → `client_modes_supported`.
 */
export function isLawyerModeUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_LAWYER_MODE_UI ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
