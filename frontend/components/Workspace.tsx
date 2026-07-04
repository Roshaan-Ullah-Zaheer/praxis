"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ConversationPanel } from "@/components/ConversationPanel";
import { DocumentsPanel } from "@/components/DocumentsPanel";
import { Inspector } from "@/components/Inspector";
import { Topbar } from "@/components/Topbar";
import { getRoles, listDocuments } from "@/lib/api";
import type { DocumentOut, RoleInfo } from "@/lib/types";
import { useConversation } from "@/lib/useConversation";

const BUSY = new Set(["queued", "parsing", "ocr", "embedding"]);

export function Workspace() {
  const { messages, streaming, apiError, send, reset, conversationId } = useConversation();

  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [activeRole, setActiveRole] = useState<string | null>(null);

  const [showDocs, setShowDocs] = useState(true);
  const [showInspector, setShowInspector] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [docs, roleList] = await Promise.all([listDocuments(), getRoles()]);
      setDocuments(docs);
      setRoles(roleList);
    } catch {
      /* backend may be warming up; keep prior state */
    } finally {
      setDocsLoading(false);
    }
  }, []);

  // Initial load + adaptive polling while any document is still processing.
  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (pollRef.current) clearTimeout(pollRef.current);
    if (documents.some((d) => BUSY.has(d.status))) {
      pollRef.current = setTimeout(refresh, 2500);
    }
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [documents, refresh]);

  // Default the inspector to the most recent assistant answer.
  const lastAssistant = useMemo(
    () => [...messages].reverse().find((m) => m.role === "assistant"),
    [messages],
  );
  const inspected = useMemo(
    () => messages.find((m) => m.id === selectedId) ?? lastAssistant ?? null,
    [messages, selectedId, lastAssistant],
  );

  // If the active role no longer exists in the corpus, fall back to All.
  useEffect(() => {
    if (activeRole && !roles.some((r) => r.role === activeRole)) setActiveRole(null);
  }, [roles, activeRole]);

  return (
    <div className="flex h-[100dvh] flex-col bg-canvas text-ink">
      <Topbar
        roles={roles}
        activeRole={activeRole}
        onRole={setActiveRole}
        showDocs={showDocs}
        showInspector={showInspector}
        onToggleDocs={() => setShowDocs((v) => !v)}
        onToggleInspector={() => setShowInspector((v) => !v)}
      />

      <div className="flex min-h-0 flex-1 gap-2 p-2">
        {showDocs && (
          <aside className="glass hidden w-[290px] shrink-0 rounded-2xl md:block">
            <DocumentsPanel documents={documents} loading={docsLoading} onChanged={refresh} />
          </aside>
        )}

        <main className="glass min-w-0 flex-1 rounded-2xl">
          <ConversationPanel
            messages={messages}
            streaming={streaming}
            apiError={apiError}
            activeRole={activeRole}
            selectedId={inspected?.id ?? null}
            conversationId={conversationId}
            onSend={(q, allowWeb) => send(q, activeRole, allowWeb ?? false)}
            onInspect={setSelectedId}
            onReset={() => {
              reset();
              setSelectedId(null);
            }}
          />
        </main>

        {showInspector && (
          <aside className="glass hidden w-[360px] shrink-0 rounded-2xl lg:block">
            <Inspector message={inspected} />
          </aside>
        )}
      </div>
    </div>
  );
}
