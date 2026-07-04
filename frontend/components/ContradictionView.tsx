"use client";

import { motion } from "framer-motion";

import { AlertIcon, DocIcon, ScaleIcon } from "@/components/icons";
import type { Conflicts, DocPosition } from "@/lib/types";

function PositionCard({ pos, side }: { pos: DocPosition | undefined; side: "a" | "b" }) {
  if (!pos) return <div className="flex-1 rounded-lg border border-white/10 bg-white/[0.02] p-3" />;
  const accent = side === "a" ? "border-conflict/40" : "border-conflict-red/40";
  return (
    <div className={`flex-1 rounded-lg border ${accent} bg-white/[0.03] p-3`}>
      <div className="flex items-center gap-1.5 text-[12px] font-semibold text-ink">
        <DocIcon width={13} height={13} className="text-ink-muted" />
        <span className="truncate">{pos.filename}</span>
        {pos.page ? <span className="ml-auto font-mono text-[10px] text-ink-faint">p.{pos.page}</span> : null}
      </div>
      <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-muted">{pos.position}</p>
      {pos.quote && (
        <p className="mt-2 border-l-2 border-conflict/50 pl-2 text-[11.5px] italic text-conflict">
          “{pos.quote}”
        </p>
      )}
    </div>
  );
}

export function ContradictionView({ conflicts }: { conflicts: Conflicts }) {
  const byName = new Map(conflicts.positions.map((p) => [p.filename, p]));
  const hasConflicts = conflicts.conflicts.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 overflow-hidden rounded-xl border border-conflict/25 bg-conflict-dim/30"
    >
      <div className="flex items-center gap-2 border-b border-conflict/20 bg-conflict/[0.06] px-3.5 py-2.5">
        <ScaleIcon width={15} height={15} className="text-conflict" />
        <span className="text-[13px] font-semibold text-ink">
          {hasConflicts ? `${conflicts.conflicts.length} contradiction${conflicts.conflicts.length > 1 ? "s" : ""} found` : "No contradictions found"}
        </span>
        {conflicts.topic && (
          <span className="ml-auto truncate text-[11px] text-ink-faint">on “{conflicts.topic}”</span>
        )}
      </div>

      <div className="space-y-3 p-3.5">
        {conflicts.summary && <p className="text-[13px] leading-relaxed text-ink-muted">{conflicts.summary}</p>}

        {conflicts.conflicts.map((c, i) => (
          <div key={i} className="rounded-xl border border-white/10 bg-canvas/40 p-3">
            <div className="mb-2.5 flex items-center gap-2 text-[12px] font-medium text-conflict">
              <AlertIcon width={13} height={13} />
              <span className="text-ink-muted">{c.nature}</span>
            </div>
            <div className="flex flex-col gap-2.5 sm:flex-row sm:items-stretch">
              <PositionCard pos={byName.get(c.document_a)} side="a" />
              <div className="grid place-items-center px-1">
                <span className="rounded-full border border-conflict/40 bg-conflict/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-conflict">
                  vs
                </span>
              </div>
              <PositionCard pos={byName.get(c.document_b)} side="b" />
            </div>
          </div>
        ))}

        {!hasConflicts && conflicts.positions.length > 0 && (
          <div className="grid gap-2 sm:grid-cols-2">
            {conflicts.positions.map((p, i) => (
              <PositionCard key={i} pos={p} side="a" />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
