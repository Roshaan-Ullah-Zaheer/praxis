"use client";

import { useRef, useState } from "react";

import {
  CheckIcon,
  CloseIcon,
  DocIcon,
  PlusIcon,
  ShieldIcon,
  SparkIcon,
  TrashIcon,
  UploadIcon,
} from "@/components/icons";
import { deleteDocument, loadSampleCorpus, setRoles, uploadDocument } from "@/lib/api";
import type { DocumentOut } from "@/lib/types";

const ROLE_PRESETS = ["public", "legal", "finance", "hr"];

function StatusPill({ status }: { status: string }) {
  if (status === "ready")
    return (
      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-trust">
        <CheckIcon width={11} height={11} /> ready
      </span>
    );
  if (status === "failed")
    return <span className="text-[11px] font-medium text-conflict-red">failed</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-info">
      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info" />
      {status}
    </span>
  );
}

function RoleTags({ doc, onSet }: { doc: DocumentOut; onSet: (roles: string[]) => void }) {
  const [editing, setEditing] = useState(false);
  const roles = doc.roles ?? [];
  const toggle = (role: string) => {
    const next = roles.includes(role) ? roles.filter((r) => r !== role) : [...roles, role];
    onSet(next.length ? next : ["public"]);
  };
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1">
      {roles.map((r) => (
        <span key={r} className="chip border-trust/20 bg-trust/[0.07] capitalize text-trust-bright">
          <ShieldIcon width={10} height={10} /> {r}
        </span>
      ))}
      <button
        type="button"
        onClick={() => setEditing((e) => !e)}
        className="grid h-[18px] w-[18px] place-items-center rounded-full border border-white/10 text-ink-faint hover:border-white/25 hover:text-ink"
      >
        {editing ? <CloseIcon width={10} height={10} /> : <PlusIcon width={10} height={10} />}
      </button>
      {editing && (
        <div className="mt-1 flex w-full flex-wrap gap-1">
          {ROLE_PRESETS.map((r) => {
            const on = roles.includes(r);
            return (
              <button
                key={r}
                type="button"
                onClick={() => toggle(r)}
                className={`chip capitalize ${
                  on ? "border-trust/40 bg-trust/15 text-trust-bright" : "border-white/10 text-ink-muted"
                }`}
              >
                {r}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function DocumentsPanel({
  documents,
  loading,
  onChanged,
}: {
  documents: DocumentOut[];
  loading: boolean;
  onChanged: () => void;
}) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadSample = async () => {
    setLoadingSample(true);
    try {
      await loadSampleCorpus();
      // Ingestion runs in the background; nudge a few refreshes so the new docs
      // appear, after which the parent's status polling takes over.
      for (let i = 0; i < 6; i += 1) {
        await new Promise((r) => setTimeout(r, 1500));
        onChanged();
      }
    } catch {
      /* surfaced by the empty corpus staying empty */
    } finally {
      setLoadingSample(false);
    }
  };

  const handleFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(file, "public").catch(() => null);
      }
      onChanged();
    } finally {
      setUploading(false);
    }
  };

  const remove = async (id: string) => {
    await deleteDocument(id).catch(() => null);
    onChanged();
  };

  const updateRoles = async (id: string, roles: string[]) => {
    await setRoles(id, roles).catch(() => null);
    onChanged();
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between px-4 py-3">
        <h2 className="flex items-center gap-2 font-display text-[13px] font-semibold uppercase tracking-wider text-ink-muted">
          <DocIcon width={14} height={14} /> Corpus
        </h2>
        <span className="font-mono text-[11px] text-ink-faint">{documents.length}</span>
      </header>

      <div className="px-3">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={`flex w-full flex-col items-center gap-1.5 rounded-xl border border-dashed px-3 py-5 text-center transition-colors ${
            dragging ? "border-trust/60 bg-trust/[0.06]" : "border-white/15 hover:border-white/30"
          }`}
        >
          <UploadIcon width={18} height={18} className={dragging ? "text-trust" : "text-ink-faint"} />
          <span className="text-[12.5px] font-medium text-ink-muted">
            {uploading ? "Uploading…" : "Drop files or click to upload"}
          </span>
          <span className="text-[11px] text-ink-faint">PDF · Word · txt</span>
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.txt,.md"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <button
          type="button"
          onClick={loadSample}
          disabled={loadingSample}
          className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-lg border border-trust/25 bg-trust/[0.06] py-2 text-[12px] font-medium text-trust-bright transition-colors hover:bg-trust/10 disabled:opacity-60"
        >
          <SparkIcon width={13} height={13} />
          {loadingSample ? "Loading sample corpus…" : "Load sample corpus"}
        </button>
      </div>

      <div className="mt-2 flex-1 space-y-1.5 overflow-y-auto px-3 pb-3">
        {documents.length === 0 && !loading && (
          <div className="mt-6 px-2 text-center">
            <p className="text-[13px] text-ink-muted">Your corpus is empty.</p>
            <p className="mt-1 text-[12px] text-ink-faint">
              Load the sample corpus above, or upload your own contracts, policies, and manuals to
              start cross-referencing them.
            </p>
          </div>
        )}

        {documents.map((doc) => (
          <div
            key={doc.id}
            className="group rounded-xl border border-white/[0.07] bg-white/[0.02] p-3 transition-colors hover:border-white/15"
          >
            <div className="flex items-start gap-2.5">
              <DocIcon width={16} height={16} className="mt-0.5 shrink-0 text-ink-faint" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[13px] font-medium text-ink" title={doc.filename}>
                  {doc.filename}
                </p>
                <div className="mt-0.5 flex items-center gap-2">
                  <StatusPill status={doc.status} />
                  {doc.page_count > 0 && (
                    <span className="text-[11px] text-ink-faint">{doc.page_count}p</span>
                  )}
                  {doc.chunk_count > 0 && (
                    <span className="text-[11px] text-ink-faint">· {doc.chunk_count} chunks</span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => remove(doc.id)}
                className="opacity-0 transition-opacity hover:text-conflict-red group-hover:opacity-100"
                aria-label="Delete document"
              >
                <TrashIcon width={14} height={14} />
              </button>
            </div>
            {doc.summary && (
              <p className="mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed text-ink-faint">
                {doc.summary}
              </p>
            )}
            <RoleTags doc={doc} onSet={(roles) => updateRoles(doc.id, roles)} />
          </div>
        ))}
      </div>
    </div>
  );
}
