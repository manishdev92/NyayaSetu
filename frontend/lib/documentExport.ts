/**
 * Client-side export for formal letter / application text — no extra npm deps.
 * Produces Word-friendly HTML (lists, headings, markdown ## / **, segmented letters).
 */

import { segmentFormalLetter, type LetterSegment } from "./formalLetterParse";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Inline **bold** (ASCII stars only) after escaping other text. */
function formatInline(s: string): string {
  if (!s) return "";
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts
    .map((part) => {
      if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
        return `<strong>${escapeHtml(part.slice(2, -2))}</strong>`;
      }
      return escapeHtml(part);
    })
    .join("");
}

function pStyle(): string {
  return "margin:0 0 10pt 0;line-height:1.58;white-space:normal;font-family:'Times New Roman',Times,serif;font-size:12.5pt;color:#111;";
}

const HR_LINE = /^(---|—{3,}|\*{3,}|_{3,})\s*$/;

function isNumberedListLine(s: string): boolean {
  return /^\d+[\.\)]\s+/.test(s.trim()) || /^\(\d+\)\s+/.test(s.trim());
}

function isBulletListLine(s: string): boolean {
  const t = s.trim();
  if (!t) return false;
  if (/^[-*•]\s+/.test(t)) return true;
  if (/^[–—·]\s+/.test(t)) return true;
  return false;
}

function listItemInner(line: string, numbered: boolean): string {
  const t = line.trim();
  if (numbered) {
    if (/^\(\d+\)\s+/.test(t.trim())) {
      return formatInline(t.replace(/^\(\d+\)\s+/, "").trim());
    }
    return formatInline(t.replace(/^\d+[\.\)]\s+/, "").trim());
  }
  return formatInline(t.replace(/^[-*•–—·]\s+/, ""));
}

/** Splits a section into stanzas (double newline). */
function stanzaSplit(text: string): string[] {
  return text
    .replace(/\r\n/g, "\n")
    .trim()
    .split(/\n\s*\n+/)
    .map((b) => b.trim())
    .filter(Boolean);
}

/**
 * Renders a block of free-form text: lists, ## headings, paragraphs, **bold**, horizontal rules.
 */
function flowBodyTextToHtml(content: string): string {
  const stanzas = stanzaSplit(content);
  if (stanzas.length === 0) return "";

  const out: string[] = [];
  for (const stanza of stanzas) {
    out.push(stanzaToHtmlBlock(stanza));
  }
  return out.join("\n");
}

function stanzaToHtmlBlock(stanza: string): string {
  const lines = stanza.split("\n");
  const nonEmpty = lines.map((l) => l.trimEnd());
  const meaningful = nonEmpty.map((l) => l.trim()).filter((l) => l.length > 0);
  if (meaningful.length === 0) return "";

  if (meaningful.length >= 1 && meaningful.every((l) => isNumberedListLine(l))) {
    const items = nonEmpty
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    if (items.length < 1) {
      return "";
    }
    return `<ol style="margin:0 0 10pt 0;padding-left:22pt;line-height:1.58;">${items
      .map((l) => `<li style="margin:0 0 4pt 0;">${listItemInner(l, true)}</li>`)
      .join("")}</ol>`;
  }
  if (meaningful.length >= 1 && meaningful.every((l) => isBulletListLine(l))) {
    const items = nonEmpty
      .map((l) => l.trim())
      .filter((l) => l.length > 0);
    return `<ul style="margin:0 0 10pt 0;padding-left:22pt;line-height:1.58;list-style-type:disc;">${items
      .map((l) => `<li style="margin:0 0 4pt 0;">${listItemInner(l, false)}</li>`)
      .join("")}</ul>`;
  }

  return lineFlowToHtml(nonEmpty);
}

/**
 * One stanza: walk lines, emit h2/h3, hr, paragraphs with <br> inside the same line group.
 */
function lineFlowToHtml(rawLines: string[]): string {
  const lines = rawLines;
  const chunks: string[] = [];
  const paraBuf: string[] = [];
  const flushP = () => {
    if (paraBuf.length === 0) return;
    const inner = paraBuf.map((l) => formatInline(l)).join("<br/>");
    chunks.push(`<p style="${pStyle()}">${inner}</p>`);
    paraBuf.length = 0;
  };

  for (const line of lines) {
    if (line.trim() === "") {
      flushP();
      continue;
    }
    if (HR_LINE.test(line.trim())) {
      flushP();
      chunks.push('<hr style="border:none;border-top:1pt solid #ccc;margin:8pt 0;"/>');
      continue;
    }
    const t = line.trim();
    if (/^###\s+/.test(t)) {
      flushP();
      const title = t.replace(/^###\s+/, "");
      chunks.push(
        `<h3 style="margin:10pt 0 4pt 0;font-size:13pt;font-weight:bold;font-family:'Times New Roman',Times,serif;">${formatInline(title)}</h3>`,
      );
      continue;
    }
    if (/^##\s+/.test(t)) {
      flushP();
      const title = t.replace(/^##\s+/, "");
      chunks.push(
        `<h2 style="margin:12pt 0 6pt 0;font-size:14pt;font-weight:bold;font-family:'Times New Roman',Times,serif;">${formatInline(title)}</h2>`,
      );
      continue;
    }
    paraBuf.push(line.trimEnd());
  }
  flushP();
  return chunks.join("\n");
}

function partToWordHtml(part: LetterSegment): string {
  if (part.type === "header") {
    const inner = part.content
      .split("\n")
      .map((l) => formatInline(l))
      .join("<br/>");
    return `<div class="ns-printfill" style="border:1pt solid #d6d3d1;background:#fafaf9;padding:10pt;margin:0 0 12pt 0;font-size:11.5pt;line-height:1.5;font-family:'Consolas','Courier New',monospace;">${inner}</div>`;
  }
  if (part.type === "addressee") {
    const inner = part.content
      .split("\n")
      .map((l) => formatInline(l))
      .join("<br/>");
    return `<div class="ns-addressee" style="border-left:3.5pt solid #92400e33;padding:6pt 0 6pt 10pt;margin:0 0 10pt 0;">${inner}</div>`;
  }
  if (part.type === "subject") {
    return `<p class="ns-subject" style="margin:0 0 10pt 0;padding:0 0 6pt 0;border-bottom:1pt solid #d6d3d1;font-weight:700;font-size:12.5pt;line-height:1.4;font-family:'Times New Roman',Times,serif;">${formatInline(
      part.content,
    )}</p>`;
  }
  if (part.type === "body" || part.type === "fallback") {
    return part.type === "fallback" ? lineFlowOrStanzaHtml(part.content) : flowBodyTextToHtml(part.content);
  }
  return "";
}

/** For fallback, try stanza split first; if a single long blob with few newlines, also run line flow. */
function lineFlowOrStanzaHtml(text: string): string {
  const t = text.replace(/\r\n/g, "\n").trim();
  if (!t) return "";
  if (t.includes("\n\n")) {
    return flowBodyTextToHtml(t);
  }
  if (t.includes("\n") && !t.startsWith("##") && t.split("\n").length > 1) {
    return lineFlowToHtml(t.split("\n"));
  }
  return lineFlowToHtml(t.split("\n"));
}

/**
 * Formatted like the in-app `FormattedLetter`: addressee / subject blocks when the model
 * used To + Subject; otherwise full-document headings, lists, and paragraphs.
 */
export function documentToExportHtml(plainText: string): string {
  const trimmed = plainText.replace(/\r\n/g, "\n").trim();
  if (!trimmed) return "<p style=\"" + pStyle() + '"></p>';

  const parts = segmentFormalLetter(trimmed);
  if (parts.length === 1 && parts[0].type === "fallback") {
    return lineFlowOrStanzaHtml(parts[0].content);
  }
  return parts.map((p) => partToWordHtml(p)).filter(Boolean).join("\n");
}

/**
 * Downloads HTML as `.doc` so Microsoft Word / LibreOffice can open and save as .docx.
 */
export function downloadDocumentAsWord(plainText: string, baseFilename: string): void {
  const safe = baseFilename.replace(/[^\w\u0900-\u0FFF-]+/g, "-").replace(/^-|-$/g, "") || "NyayaSetu-draft";
  const bodyInner = documentToExportHtml(plainText);
  const html = `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"><title>${escapeHtml(safe)}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View><w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->
<style>
body{font-family:'Times New Roman',Times,serif;font-size:12.5pt;line-height:1.58;margin:24pt;color:#111;}
@page { size: A4; margin: 18mm; }
</style>
</head><body>${bodyInner}</body></html>`;
  const blob = new Blob(["\ufeff", html], { type: "application/msword;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${safe}.doc`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Opens a print dialog on a minimal page — user can choose "Save as PDF".
 * Returns false if pop-ups are blocked.
 */
export function printDocumentForPdf(plainText: string, title: string): boolean {
  const w = window.open("", "_blank");
  if (!w) return false;
  const safeTitle = escapeHtml(title.replace(/</g, ""));
  const bodyInner = documentToExportHtml(plainText);
  const docHtml = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>${safeTitle}</title>
<style>
@page { size: A4; margin: 18mm; }
html, body { margin: 0; padding: 0; }
body { font-family: 'Times New Roman', Times, serif; font-size: 12.5pt; line-height: 1.58; color: #111; padding: 12mm; box-sizing: border-box; }
h2, h3, p, div, li { color: #111; }
@media print { body { padding: 0; } }
</style></head><body>${bodyInner}</body></html>`;
  w.document.open();
  w.document.write(docHtml);
  w.document.close();
  const runPrint = () => {
    try {
      w.focus();
      w.print();
    } catch {
      /* ignore */
    }
  };
  if (w.document.readyState === "complete") {
    window.setTimeout(runPrint, 250);
  } else {
    w.onload = () => window.setTimeout(runPrint, 100);
  }
  return true;
}
