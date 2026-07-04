"use client";

import { useCallback, useRef, useState } from "react";

import { API_BASE, createConversation, streamMessage } from "@/lib/api";
import type {
  AgentStatus,
  AuditEntry,
  Citation,
  Conflicts,
  Grounding,
  RetrievalChunk,
  WebSource,
} from "@/lib/types";

export interface PipelineStep {
  agent: string;
  status: AgentStatus;
}

export interface Source {
  chunk_id: string;
  document_id: string;
  page: number;
  snippet: string;
}

export interface Trace {
  resolvedQuestion?: string;
  intent?: string | null;
  strategy?: string | null;
  strategyReason?: string;
  steps: PipelineStep[];
  retrieval: RetrievalChunk[];
  grounding?: Grounding | null;
  conflicts?: Conflicts | null;
  audit: AuditEntry[];
  sources: Source[];
  webSources: WebSource[];
  cached?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  streaming: boolean;
  error?: boolean;
  trace: Trace;
}

const newTrace = (): Trace => ({ steps: [], retrieval: [], audit: [], sources: [], webSources: [] });

let counter = 0;
const uid = () => `m${Date.now().toString(36)}${(counter++).toString(36)}`;

// Nodes that represent real work in the graph. "orchestrator" is just the start
// marker and isn't rendered as its own pipeline node.
function pushStep(steps: PipelineStep[], agent: string, status: AgentStatus): PipelineStep[] {
  const next = steps.map((s) => (s.status === "running" ? { ...s, status: "done" as AgentStatus } : s));
  next.push({ agent, status });
  return next;
}

export function useConversation() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const convoRef = useRef<string | null>(null);

  const patch = useCallback((id: string, fn: (m: ChatMessage) => ChatMessage) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  }, []);

  const handleEvent = useCallback(
    (id: string, name: string, data: any) => {
      patch(id, (m) => {
        const t = m.trace;
        switch (name) {
          case "agent_step": {
            const agent = data.agent as string;
            if (agent === "orchestrator") return m;
            const status: AgentStatus = data.status === "revising" ? "revising" : "running";
            return { ...m, trace: { ...t, steps: pushStep(t.steps, agent, status) } };
          }
          case "resolved":
            return { ...m, trace: { ...t, resolvedQuestion: data.resolved_question } };
          case "strategy_selected":
            return {
              ...m,
              trace: {
                ...t,
                intent: data.intent ?? t.intent,
                strategy: data.strategy ?? t.strategy,
                strategyReason: data.reason ?? t.strategyReason,
              },
            };
          case "retrieval":
            return { ...m, trace: { ...t, retrieval: data.chunks ?? [] } };
          case "token":
            return { ...m, content: (m.content || "") + (data.delta || "") };
          case "answer":
            // Authoritative full text — replaces whatever streamed token-by-token.
            return { ...m, content: data.text ?? m.content, citations: data.citations ?? m.citations };
          case "conflict":
            return { ...m, trace: { ...t, conflicts: data as Conflicts } };
          case "web":
            return { ...m, trace: { ...t, webSources: data.sources ?? [] } };
          case "grounding":
            return { ...m, trace: { ...t, grounding: data as Grounding } };
          case "cached":
            return { ...m, trace: { ...t, cached: true } };
          case "error":
            return { ...m, streaming: false, error: true, content: data.message ?? "Something went wrong." };
          case "done": {
            const steps = t.steps.map((s) =>
              s.status === "running" ? { ...s, status: "done" as AgentStatus } : s,
            );
            return {
              ...m,
              streaming: false,
              content: m.content || data.answer || "",
              citations: m.citations.length ? m.citations : data.citations ?? [],
              trace: {
                ...t,
                steps,
                intent: t.intent ?? data.intent,
                strategy: t.strategy ?? data.strategy,
                grounding: t.grounding ?? data.grounding ?? null,
                conflicts: t.conflicts ?? (data.conflicts?.positions?.length ? data.conflicts : null),
                audit: data.audit ?? t.audit,
                sources: data.sources ?? t.sources,
                webSources: t.webSources.length ? t.webSources : data.web_sources ?? [],
                cached: t.cached || data.cached,
              },
            };
          }
          default:
            return m;
        }
      });
    },
    [patch],
  );

  const send = useCallback(
    async (question: string, activeRole: string | null, allowWeb = false) => {
      const q = question.trim();
      if (!q || streaming) return;
      setApiError(null);

      let convo = convoRef.current;
      if (!convo) {
        try {
          const res = (await createConversation()) as { id: string };
          convo = res.id;
          convoRef.current = convo;
          setConversationId(convo);
        } catch {
          setApiError(`Couldn't reach the Praxis API at ${API_BASE}. Is the backend running?`);
          return;
        }
      }

      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: q,
        citations: [],
        streaming: false,
        trace: newTrace(),
      };
      const assistantId = uid();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        citations: [],
        streaming: true,
        trace: newTrace(),
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setStreaming(true);

      await streamMessage(
        convo,
        q,
        activeRole,
        {
          onEvent: (name, data) => handleEvent(assistantId, name, data),
          onError: () => {
            patch(assistantId, (m) => ({
              ...m,
              streaming: false,
              error: true,
              content: m.content || "The assistant lost its connection. Please try again.",
            }));
            setStreaming(false);
          },
          onClose: () => {
            patch(assistantId, (m) => ({ ...m, streaming: false }));
            setStreaming(false);
          },
        },
        allowWeb,
      );
    },
    [streaming, handleEvent, patch],
  );

  const reset = useCallback(() => {
    convoRef.current = null;
    setConversationId(null);
    setMessages([]);
    setStreaming(false);
    setApiError(null);
  }, []);

  return { messages, streaming, apiError, send, reset, conversationId };
}
