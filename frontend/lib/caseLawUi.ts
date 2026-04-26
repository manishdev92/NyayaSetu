/**
 * Sprint 6: show case-law (research) panel for lawyer mode when the API advertises
 * `case_law_research_mode` !== `off` and this build flag is on.
 */
export function isCaseLawUiEnabled(): boolean {
  const v = (process.env.NEXT_PUBLIC_CASE_LAW_UI ?? "").trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
