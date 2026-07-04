"use client";

import { useEffect, useRef, useState } from "react";

import { DocIcon } from "@/components/icons";
import type { Citation } from "@/lib/types";
import type { Source } from "@/lib/useConversation";

/**
 * Inline `[n]` citation. Click to reveal the source document, page, and the exact
 * passage the answer was grounded on.
 */
export function CitationChip({
  n,
  citation,
  source,
}: {
  n: number;
  citation?: Citation;
  source?: Source;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <span ref={ref} className="relative inline-block align-baseline">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
        className={`mx-0.5 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] border px-1 align-[1px] text-[10px] font-semibold transition-colors ${
          open
            ? "border-trust bg-trust/20 text-trust-bright"
            : "border-trust/30 bg-trust/10 text-trust-bright hover:bg-trust/20"
        }`}
      >
        {n}
      </button>
      {open && (
        <span className="glass absolute bottom-full left-1/2 z-30 mb-1.5 block w-64 -translate-x-1/2 rounded-xl p-3 shadow-panel">
          <span className="flex items-center gap-1.5 text-[12px] font-semibold text-ink">
            <DocIcon width={13} height={13} className="text-trust" />
            {citation?.filename ?? "Source"}
            {citation?.page ? (
              <span className="ml-auto font-mono text-[11px] text-ink-faint">p. {citation.page}</span>
            ) : null}
          </span>
          {source?.snippet ? (
            <span className="mt-2 block border-l-2 border-trust/40 pl-2 text-[12px] leading-relaxed text-ink-muted">
              {source.snippet}
              {source.snippet.length >= 240 ? "…" : ""}
            </span>
          ) : (
            <span className="mt-2 block text-[12px] text-ink-faint">
              Passage from this source supported the cited claim.
            </span>
          )}
        </span>
      )}
    </span>
  );
}
