"use client";

import { useState } from "react";

import { AgentPipeline } from "@/components/AgentPipeline";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { ClockIcon, LayersIcon, RouteIcon, ShieldIcon } from "@/components/icons";
import type { ChatMessage } from "@/lib/useConversation";

type Tab = "pipeline" | "retrieval" | "grounding" | "audit";

const TABS: { key: Tab; label: string; icon: typeof RouteIcon }[] = [
  { key: "pipeline", label: "Pipeline", icon: RouteIcon },
  { key: "retrieval", label: "Retrieval", icon: LayersIcon },
  { key: "grounding", label: "Grounding", icon: ShieldIcon },
  { key: "audit", label: "Audit", icon: ClockIcon },
];

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="px-1 py-6 text-center text-[12px] text-ink-faint">{children}</p>;
}

function kindColor(kind: string) {
  if (kind === "table") return "text-info";
  if (kind === "ocr") return "text-conflict";
  return "text-ink-faint";
}

export function Inspector({ message }: { message: ChatMessage | null }) {
  const [tab, setTab] = useState<Tab>("pipeline");
  const trace = message?.trace;

  return (
    <div className="flex h-full flex-col">
      <header className="px-4 py-3">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-ink-muted">
          Glass-box
        </h2>
      </header>

      <div className="flex gap-1 px-3">
        {TABS.map((t) => {
          const Icon = t.icon;
          const on = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-[11.5px] font-medium transition-colors ${
                on ? "bg-white/[0.06] text-ink" : "text-ink-faint hover:text-ink-muted"
              }`}
            >
              <Icon width={13} height={13} className={on ? "text-trust" : ""} />
              {t.label}
            </button>
          );
        })}
      </div>

      <div className="mt-2 flex-1 overflow-y-auto px-4 pb-4">
        {!trace ? (
          <Empty>Ask a question, then select an answer to inspect how it was produced.</Empty>
        ) : tab === "pipeline" ? (
          <div className="space-y-4">
            {(trace.intent || trace.strategy) && (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                <div className="flex items-center gap-2">
                  {trace.intent && (
                    <span className="chip border-white/10 capitalize text-ink-muted">{trace.intent}</span>
                  )}
                  {trace.strategy && (
                    <span className="chip border-info/25 bg-info/10 capitalize text-info">
                      {trace.strategy}
                    </span>
                  )}
                </div>
                {trace.strategyReason && (
                  <p className="mt-2 text-[12px] leading-relaxed text-ink-muted">
                    {trace.strategyReason}
                  </p>
                )}
              </div>
            )}
            {trace.resolvedQuestion && (
              <div className="rounded-xl border border-trust/15 bg-trust/[0.04] p-3">
                <p className="text-[11px] font-medium uppercase tracking-wide text-trust">
                  Resolved question
                </p>
                <p className="mt-1 text-[12.5px] text-ink-muted">{trace.resolvedQuestion}</p>
              </div>
            )}
            <div>
              <p className="mb-2.5 text-[11px] font-medium uppercase tracking-wide text-ink-faint">
                Agent pipeline
              </p>
              <AgentPipeline steps={trace.steps} variant="panel" />
            </div>
          </div>
        ) : tab === "retrieval" ? (
          trace.retrieval.length === 0 ? (
            <Empty>No passages were retrieved for this answer.</Empty>
          ) : (
            <ul className="space-y-1.5">
              {trace.retrieval.map((c, i) => (
                <li key={i} className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] text-ink-faint">{i + 1}</span>
                    <span className="truncate text-[12.5px] font-medium text-ink" title={c.filename}>
                      {c.filename}
                    </span>
                    <span className="ml-auto font-mono text-[10px] text-ink-faint">p.{c.page}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className={`text-[10px] uppercase ${kindColor(c.kind)}`}>{c.kind}</span>
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full bg-trust/70"
                        style={{ width: `${Math.max(6, Math.min(100, c.score * 100))}%` }}
                      />
                    </div>
                    <span className="font-mono text-[10px] text-ink-faint">{c.score.toFixed(3)}</span>
                  </div>
                </li>
              ))}
            </ul>
          )
        ) : tab === "grounding" ? (
          !trace.grounding ? (
            <Empty>No grounding verdict for this answer.</Empty>
          ) : (
            <div className="space-y-3">
              <ConfidenceBadge grounding={trace.grounding} size="lg" />
              <p className="text-[12px] leading-relaxed text-ink-faint">
                The verifier re-checks every claim against the cited passages before the answer is
                released. Unsupported claims trigger one bounded revision, then an honest “the
                documents don’t support this.”
              </p>
            </div>
          )
        ) : trace.audit.length === 0 ? (
          <Empty>No audit entries recorded for this answer.</Empty>
        ) : (
          <ul className="space-y-1">
            {trace.audit.map((a, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2"
              >
                <span className="mt-0.5 rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] capitalize text-ink-muted">
                  {a.actor}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[12px] text-ink">
                    <span className="capitalize text-trust">{a.action}</span> {a.target}
                  </p>
                  {a.role_context && (
                    <p className="text-[10.5px] text-ink-faint">role: {a.role_context}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
