import type { DocumentOut, RoleInfo } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ── Documents ────────────────────────────────────────────────────────────────
export function listDocuments(): Promise<DocumentOut[]> {
  return fetch(`${API_BASE}/api/documents`, { cache: "no-store" }).then(json<DocumentOut[]>);
}

export function uploadDocument(
  file: File,
  roles: string,
): Promise<{ id: string; filename: string; status: string }> {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("roles", roles);
  return fetch(`${API_BASE}/api/documents`, { method: "POST", body: fd }).then(
    json<{ id: string; filename: string; status: string }>,
  );
}

export function deleteDocument(id: string): Promise<void> {
  return fetch(`${API_BASE}/api/documents/${id}`, { method: "DELETE" }).then(() => undefined);
}

export function loadSampleCorpus(): Promise<{ status: string; count: number }> {
  return fetch(`${API_BASE}/api/sample/load`, { method: "POST" }).then(
    json<{ status: string; count: number }>,
  );
}

export function setRoles(id: string, roles: string[]): Promise<DocumentOut> {
  return fetch(`${API_BASE}/api/documents/${id}/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ roles }),
  }).then(json<DocumentOut>);
}

// ── Billing ──────────────────────────────────────────────────────────────────
export interface SubscriptionInfo {
  tier: string;
  limits: { name: string; max_documents: number; max_queries_per_day: number };
  billing_enabled: boolean;
  enforced: boolean;
}

export function getSubscription(): Promise<SubscriptionInfo> {
  return fetch(`${API_BASE}/api/billing/subscription`, { cache: "no-store" })
    .then(json<SubscriptionInfo>)
    .catch(
      () =>
        ({
          tier: "free",
          limits: { name: "Free", max_documents: 5, max_queries_per_day: 15 },
          billing_enabled: false,
          enforced: false,
        }) as SubscriptionInfo,
    );
}

export async function startCheckout(tier: string): Promise<{ url?: string; error?: string }> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/billing/checkout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier }),
    });
  } catch {
    return { error: "Couldn't reach the billing service." };
  }
  if (res.status === 503) return { error: "Billing isn't enabled in this demo deployment yet." };
  if (!res.ok) return { error: `Checkout failed (${res.status}).` };
  const data = await res.json();
  return { url: data.url };
}

// ── Governance ───────────────────────────────────────────────────────────────
export function getRoles(): Promise<RoleInfo[]> {
  return fetch(`${API_BASE}/api/governance/roles`, { cache: "no-store" })
    .then(json<RoleInfo[]>)
    .catch(() => [] as RoleInfo[]);
}

// ── Conversations ────────────────────────────────────────────────────────────
export function createConversation(title = "New conversation"): Promise<{ id: string }> {
  return fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  }).then(json<{ id: string }>);
}

export function getAudit(conversationId: string) {
  return fetch(`${API_BASE}/api/conversations/${conversationId}/audit`, { cache: "no-store" }).then(
    json,
  );
}

export async function exportConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}/export`);
  if (!res.ok) throw new Error(`export failed (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `praxis-report-${conversationId.slice(0, 8)}.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ── Streaming chat (POST SSE parsed manually) ────────────────────────────────
export interface StreamHandlers {
  onEvent: (name: string, data: any) => void;
  onError?: (err: unknown) => void;
  onClose?: () => void;
}

export async function streamMessage(
  conversationId: string,
  question: string,
  activeRole: string | null,
  handlers: StreamHandlers,
  allowWeb = false,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, active_role: activeRole, allow_web: allowWeb }),
    });
  } catch (err) {
    handlers.onError?.(err);
    return;
  }
  if (!resp.ok || !resp.body) {
    handlers.onError?.(new Error(`stream failed (${resp.status})`));
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event = "message";
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) {
        try {
          handlers.onEvent(event, JSON.parse(data));
        } catch {
          /* ignore malformed frame */
        }
      }
    }
  }
  handlers.onClose?.();
}
