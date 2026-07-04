"use client";

import { EyeIcon } from "@/components/icons";
import type { RoleInfo } from "@/lib/types";

/**
 * "View as…" segmented control. Flipping the active role re-filters which
 * documents the agents can see — answers and the corpus change live.
 */
export function RoleSwitcher({
  roles,
  active,
  onChange,
}: {
  roles: RoleInfo[];
  active: string | null;
  onChange: (role: string | null) => void;
}) {
  const options: { key: string | null; label: string; count?: number }[] = [
    { key: null, label: "All access" },
    ...roles.map((r) => ({ key: r.role, label: r.role, count: r.document_count })),
  ];

  return (
    <div className="flex items-center gap-2">
      <span className="hidden items-center gap-1 text-[11px] font-medium text-ink-faint sm:flex">
        <EyeIcon width={13} height={13} /> View as
      </span>
      <div className="flex items-center gap-0.5 rounded-lg border border-white/10 bg-canvas/60 p-0.5">
        {options.map((opt) => {
          const selected = opt.key === active;
          return (
            <button
              key={opt.key ?? "all"}
              type="button"
              onClick={() => onChange(opt.key)}
              className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] font-medium capitalize transition-colors ${
                selected
                  ? "bg-trust/15 text-trust-bright shadow-[inset_0_0_0_1px_rgba(16,185,129,0.3)]"
                  : "text-ink-muted hover:bg-white/[0.04] hover:text-ink"
              }`}
            >
              {opt.label}
              {typeof opt.count === "number" && (
                <span className="font-mono text-[10px] text-ink-faint">{opt.count}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
