"use client";

import { motion } from "framer-motion";

import { AgentPipeline } from "@/components/AgentPipeline";
import { CitationChip } from "@/components/CitationChip";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { ContradictionView } from "@/components/ContradictionView";
import { DatabaseIcon, GlobeIcon, LinkIcon, LogoMark } from "@/components/icons";
import { RichText } from "@/lib/markdown";
import type { ChatMessage } from "@/lib/useConversation";

export function MessageBubble({
  message,
  active,
  onInspect,
}: {
  message: ChatMessage;
  active?: boolean;
  onInspect?: () => void;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md border border-trust/20 bg-trust/[0.07] px-4 py-2.5 text-[14px] leading-relaxed text-ink">
          {message.content}
        </div>
      </div>
    );
  }

  const { trace } = message;
  const citeFor = (n: number) => {
    const citation = message.citations.find((c) => c.n === n);
    const source = citation
      ? trace.sources.find((s) => s.chunk_id === citation.chunk_id)
      : undefined;
    return <CitationChip n={n} citation={citation} source={source} />;
  };

  const showInlinePipeline = message.streaming && !message.content;

  return (
    <div className="flex gap-3">
      <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-trust/25 bg-trust/10 text-trust-bright">
        <LogoMark width={15} height={15} />
      </span>

      <div className="min-w-0 flex-1">
        <div
          role="button"
          tabIndex={0}
          onClick={onInspect}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onInspect?.();
            }
          }}
          className={`group block w-full cursor-pointer rounded-2xl rounded-tl-md border px-4 py-3 text-left transition-colors ${
            active
              ? "border-trust/30 bg-surface-raised"
              : "border-white/10 bg-surface hover:border-white/20"
          }`}
        >
          {showInlinePipeline ? (
            <div className="py-1">
              <AgentPipeline steps={trace.steps} variant="inline" />
            </div>
          ) : message.error ? (
            <p className="text-[14px] text-conflict-red">{message.content}</p>
          ) : (
            <RichText text={message.content} renderCite={citeFor} />
          )}

          {trace.conflicts && (trace.conflicts.conflicts.length > 0 || trace.conflicts.positions.length > 0) && (
            <ContradictionView conflicts={trace.conflicts} />
          )}

          {trace.webSources.length > 0 && (
            <div className="mt-3 rounded-xl border border-info/25 bg-info/[0.05] p-3">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-info">
                <GlobeIcon width={13} height={13} /> Augmented from the web
              </div>
              <p className="mt-1 text-[11px] text-ink-faint">
                Your corpus didn’t cover this — these are public web sources, not your documents.
              </p>
              <ul className="mt-2 space-y-1">
                {trace.webSources.map((s, i) => (
                  <li key={i}>
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1.5 text-[12px] text-info hover:underline"
                    >
                      <LinkIcon width={11} height={11} />
                      <span className="truncate">{s.title}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {!message.streaming && !message.error && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/[0.06] pt-2.5">
              <ConfidenceBadge grounding={trace.grounding} />
              {trace.strategy && (
                <span className="chip border-info/25 bg-info/10 text-info">
                  {trace.strategy}
                </span>
              )}
              {trace.cached && (
                <span className="chip border-white/10 text-ink-faint">
                  <DatabaseIcon width={11} height={11} /> cached
                </span>
              )}
              {trace.retrieval.length > 0 && (
                <span className="text-[11px] text-ink-faint">
                  {trace.retrieval.length} passage{trace.retrieval.length > 1 ? "s" : ""}
                </span>
              )}
              <span className="ml-auto text-[11px] text-ink-faint opacity-0 transition-opacity group-hover:opacity-100">
                view trace →
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ThinkingCursor() {
  return (
    <motion.span
      animate={{ opacity: [0.2, 1, 0.2] }}
      transition={{ repeat: Infinity, duration: 1.1 }}
      className="ml-0.5 inline-block h-3.5 w-1.5 translate-y-0.5 rounded-sm bg-trust"
    />
  );
}
