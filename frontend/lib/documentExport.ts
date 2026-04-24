/** Client-side export for formal letter text — no extra npm deps. */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function letterBlocks(plainText: string): string[] {
  return plainText
    .trim()
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);
}

function plainTextToHtmlParagraphs(plainText: string, variant: "word" | "print"): string {
  const blocks = letterBlocks(plainText);
  if (blocks.length === 0) return "<p></p>";
  const style =
    variant === "word"
      ? "margin:0 0 12pt 0;line-height:1.58;white-space:pre-wrap;font-family:'Times New Roman',serif;font-size:12.5pt;"
      : "margin:0 0 10pt 0;line-height:1.58;white-space:pre-wrap;";
  return blocks.map((b) => `<p style="${style}">${escapeHtml(b)}</p>`).join("");
}

/**
 * Downloads HTML as `.doc` so Microsoft Word / LibreOffice can open and save as .docx.
 */
export function downloadDocumentAsWord(plainText: string, baseFilename: string): void {
  const safe = baseFilename.replace(/[^\w\u0900-\u0FFF-]+/g, "-").replace(/^-|-$/g, "") || "NyayaSetu-draft";
  const html = `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
<head><meta charset="utf-8"><title>${escapeHtml(safe)}</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View><w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->
<style>body{font-family:'Times New Roman',Times,serif;font-size:12.5pt;line-height:1.58;margin:24pt;color:#111;}</style>
</head><body>${plainTextToHtmlParagraphs(plainText, "word")}</body></html>`;
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
  const body = plainTextToHtmlParagraphs(plainText, "print");
  const docHtml = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>${safeTitle}</title>
<style>
@page { size: A4; margin: 18mm; }
html, body { margin: 0; padding: 0; }
body { font-family: ui-serif, Georgia, 'Times New Roman', Times, serif; font-size: 12.5pt; line-height: 1.58; color: #111; padding: 12mm; box-sizing: border-box; }
@media print { body { padding: 0; } }
</style></head><body>${body}</body></html>`;
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
