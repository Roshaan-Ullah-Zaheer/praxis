"use client";

import { useEffect, useRef, useState } from "react";

import { MessageBubble } from "@/components/MessageBubble";
import { AlertIcon, DownloadIcon, GlobeIcon, PlusIcon, SendIcon, SparkIcon } from "@/components/icons";
import { exportConversation } from "@/lib/api";
import type { ChatMessage } from "@/lib/useConversation";

const SUGGESTIONS = [
  "Which documents contradict each other on payment terms?",
  "Compare the termination notice periods across all contracts.",
  "Extract every party, effective date, and dollar amount.",
  "Summarize the data-retention obligations.",
];

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center px-6 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl border border-trust/25 bg-trust/10 text-trust-bright shadow-glow">
        <SparkIcon width={24} height={24} />
      </span>
      <h2 className="mt-5 font-display text-2xl font-semibold text-ink">Ask across your whole corpus</h2>
      <p className="mt-2 text-[14px] leading-relaxed text-ink-muted">
        A team of agents fans out across every accessible document, cross-references them, and
        answers with citations, a grounding check, and a full audit trail.
      </p>
      <div className="mt-6 grid w-full gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="group flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.02] px-3.5 py-2.5 text-left text-[13px] text-ink-muted transition-colors hover:border-trust/30 hover:bg-trust/[0.04] hover:text-ink"
          >
            <SparkIcon
              width={14}
              height={14}
              className="shrink-0 text-ink-faint transition-colors group-hover:text-trust"
            />
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ConversationPanel({
  messages,
  streaming,
  apiError,
  activeRole,
  selectedId,
  conversationId,
  onSend,
  onInspect,
  onReset,
}: {
  messages: ChatMessage[];
  streaming: boolean;
  apiError: string | null;
  activeRole: string | null;
  selectedId: string | null;
  conversationId: string | null;
  onSend: (q: string, allowWeb?: boolean) => void;
  onInspect: (id: string) => void;
  onReset: () => void;
}) {
  const [draft, setDraft] = useState("");
  const [webOn, setWebOn] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const q = draft.trim();
    if (!q || streaming) return;
    onSend(q, webOn);
    setDraft("");
    if (taRef.current) taRef.current.style.height = "auto";
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
        <div className="min-w-0">
          <h1 className="font-display text-[15px] font-semibold text-ink">Conversation</h1>
          <p className="text-[11.5px] text-ink-faint">
            {activeRole ? (
              <>
                viewing as <span className="capitalize text-trust">{activeRole}</span>
              </>
            ) : (
              "full access · all documents"
            )}
          </p>
        </div>
        {!empty && (
          <div className="flex items-center gap-1.5">
            {conversationId && messages.some((m) => m.role === "assistant" && !m.streaming) && (
              <button
                type="button"
                onClick={() => exportConversation(conversationId).catch(() => null)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[12px] font-medium text-ink-muted transition-colors hover:border-white/25 hover:text-ink"
                title="Download a sourced Markdown report"
              >
                <DownloadIcon width={13} height={13} /> Export
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                onReset();
                setDraft("");
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 px-2.5 py-1.5 text-[12px] font-medium text-ink-muted transition-colors hover:border-white/25 hover:text-ink"
            >
              <PlusIcon width={13} height={13} /> New
            </button>
          </div>
        )}
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {empty ? (
          <EmptyState onPick={(q) => onSend(q)} />
        ) : (
          <div className="mx-auto max-w-3xl space-y-5 px-5 py-6">
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                active={m.id === selectedId}
                onInspect={() => onInspect(m.id)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-white/[0.06] px-5 py-3.5">
        {apiError && (
          <div className="mb-2.5 flex items-center gap-2 rounded-lg border border-conflict-red/25 bg-conflict-red/[0.08] px-3 py-2 text-[12px] text-conflict-red">
            <AlertIcon width={13} height={13} /> {apiError}
          </div>
        )}
        <div className="flex items-end gap-2 rounded-2xl border border-white/12 bg-canvas/60 px-3 py-2 focus-within:border-trust/40">
          <textarea
            ref={taRef}
            rows={1}
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Ask anything across your documents…"
            className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-[14px] text-ink outline-none placeholder:text-ink-faint"
          />
          <button
            type="button"
            onClick={submit}
            disabled={streaming || !draft.trim()}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-trust text-canvas transition-opacity disabled:cursor-not-allowed disabled:opacity-30"
            aria-label="Send"
          >
            <SendIcon width={16} height={16} />
          </button>
        </div>
        <div className="mt-1.5 flex items-center justify-between px-1">
          <button
            type="button"
            onClick={() => setWebOn((v) => !v)}
            title="When the corpus can't answer, fall back to a labeled web search"
            className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
              webOn
                ? "border-info/40 bg-info/10 text-info"
                : "border-white/10 text-ink-faint hover:text-ink-muted"
            }`}
          >
            <GlobeIcon width={12} height={12} />
            Web fallback {webOn ? "on" : "off"}
          </button>
          <span className="text-[10.5px] text-ink-faint">Enter to send · Shift+Enter for newline</span>
        </div>
      </div>
    </div>
  );
}
