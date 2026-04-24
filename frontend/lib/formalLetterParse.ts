/**
 * Splits a formal police letter `document` into header / addressee / subject / body
 * when the model follows "To," + "Subject:" conventions. Falls back to single block.
 */

export type LetterSegment =
  | { type: "header" | "addressee" | "subject" | "body"; content: string }
  | { type: "fallback"; content: string };

const TO_LINE = /^To[,]?\s*$/i;

function normalizeNewlines(s: string): string {
  return s.replace(/\r\n/g, "\n").trim();
}

export function segmentFormalLetter(text: string): LetterSegment[] {
  const raw = normalizeNewlines(text);
  if (!raw) return [{ type: "fallback", content: "" }];

  const lines = raw.split("\n");
  const toIndex = lines.findIndex(
    (l) => TO_LINE.test(l.trim()) || l.trim().startsWith("To,")
  );
  if (toIndex < 0) {
    return [{ type: "fallback", content: raw }];
  }

  const header = toIndex > 0 ? lines.slice(0, toIndex).join("\n").trim() : "";
  const fromTo = lines.slice(toIndex);
  const subIdx = fromTo.findIndex(
    (l) => /^Subject:\s*/i.test(l) || /^विषय:\s*/.test(l.trim())
  );
  if (subIdx < 0) {
    return [{ type: "fallback", content: raw }];
  }

  const addressee = fromTo.slice(0, subIdx).join("\n").trim();
  const subject = fromTo[subIdx].trim();
  const body = fromTo.slice(subIdx + 1).join("\n").trim();

  const out: LetterSegment[] = [];
  if (header) out.push({ type: "header", content: header });
  if (addressee) out.push({ type: "addressee", content: addressee });
  if (subject) out.push({ type: "subject", content: subject });
  if (body) out.push({ type: "body", content: body });
  if (out.length === 0) return [{ type: "fallback", content: raw }];
  return out;
}
