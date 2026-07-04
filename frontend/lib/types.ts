export interface DocumentOut {
  id: string;
  filename: string;
  mime: string;
  size: number;
  page_count: number;
  status: string;
  roles: string[];
  summary: string;
  chunk_count: number;
  created_at: string;
}

export interface Citation {
  n: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page: number;
}

export interface Grounding {
  grounded: boolean;
  confidence: number;
  unsupported: string[];
}

export interface ConflictPair {
  document_a: string;
  document_b: string;
  nature: string;
}

export interface DocPosition {
  filename: string;
  document_id: string;
  position: string;
  quote: string;
  page: number;
}

export interface Conflicts {
  topic: string;
  positions: DocPosition[];
  conflicts: ConflictPair[];
  summary: string;
}

export interface AuditEntry {
  actor: string;
  action: string;
  target: string;
  role_context?: string | null;
  ts?: string;
}

export interface RetrievalChunk {
  filename: string;
  page: number;
  kind: string;
  score: number;
}

export type AgentStatus = "idle" | "running" | "done" | "revising";

export interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  grounding?: Grounding | null;
  strategy?: string | null;
  intent?: string | null;
  conflicts?: Conflicts | null;
  cached?: boolean;
  streaming?: boolean;
}

export interface RoleInfo {
  role: string;
  document_count: number;
}

export interface WebSource {
  title: string;
  url: string;
}
