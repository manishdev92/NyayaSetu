"use client";

import { segmentFormalLetter, type LetterSegment } from "@/lib/formalLetterParse";

function BodyBlocks({ text }: { text: string }) {
  const paras = text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="space-y-4 text-stone-900">
      {paras.map((para, i) => {
        const lines = para.split("\n").map((l) => l.trimEnd());
        const nonEmpty = lines.filter((l) => l.length > 0);
        const allNumbered =
          nonEmpty.length >= 2 && nonEmpty.every((l) => /^\d+\.\s*/.test(l));
        if (allNumbered) {
          return (
            <ol
              key={i}
              className="list-decimal space-y-2.5 pl-5 text-stone-900 [list-style-position:outside] marker:font-medium marker:text-amber-900/90"
            >
              {nonEmpty.map((line, j) => (
                <li key={j} className="pl-1 leading-[1.75]">
                  {line.replace(/^\d+\.\s*/, "")}
                </li>
              ))}
            </ol>
          );
        }
        return (
          <p key={i} className="whitespace-pre-line leading-[1.75] text-stone-900">
            {para}
          </p>
        );
      })}
    </div>
  );
}

function PartBlock({ part }: { part: LetterSegment }) {
  if (part.type === "fallback") {
    return (
      <div className="whitespace-pre-line leading-[1.75] text-stone-900">
        {part.content}
      </div>
    );
  }
  if (part.type === "header") {
    return (
      <div
        className="rounded-lg border border-dashed border-stone-300/90 bg-stone-50/90 px-4 py-3.5 text-[0.98rem] leading-relaxed text-stone-800 shadow-inner sm:px-5"
        role="region"
        aria-label="Print and fill"
      >
        <p className="text-xs font-medium uppercase tracking-wide text-stone-500">Print &amp; fill</p>
        <div className="mt-2 whitespace-pre-line font-[ui-monospace,ui-serif,Georgia,serif] text-stone-800">
          {part.content}
        </div>
      </div>
    );
  }
  if (part.type === "addressee") {
    return (
      <div className="border-l-[3px] border-amber-800/45 bg-gradient-to-r from-amber-50/50 to-transparent py-2 pl-4 pr-2 sm:pl-5">
        <div className="whitespace-pre-line text-base leading-[1.75] text-stone-900 sm:text-[1.08rem]">
          {part.content}
        </div>
      </div>
    );
  }
  if (part.type === "subject") {
    return (
      <p className="border-b border-stone-200 pb-2 text-base font-semibold text-stone-900 sm:text-[1.05rem]">
        {part.content}
      </p>
    );
  }
  return <BodyBlocks text={part.content} />;
}

export function FormattedLetter({ text, emptyLabel }: { text: string; emptyLabel: string }) {
  const trimmed = text?.trim() ?? "";
  if (!trimmed) {
    return <p className="text-base text-stone-600">{emptyLabel}</p>;
  }

  const parts = segmentFormalLetter(trimmed);
  if (parts.length === 1 && parts[0].type === "fallback") {
    return (
      <div className="legal-letter-body text-stone-900">
        <div className="whitespace-pre-line leading-[1.75]">{parts[0].content}</div>
      </div>
    );
  }

  return (
    <div className="legal-letter-body max-w-[52rem] space-y-6 text-stone-900">
      {parts.map((p, i) => (
        <PartBlock key={i} part={p} />
      ))}
    </div>
  );
}
