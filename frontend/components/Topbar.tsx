"use client";

import Link from "next/link";

import { RoleSwitcher } from "@/components/RoleSwitcher";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ColumnsIcon, DocIcon, LogoMark } from "@/components/icons";
import type { RoleInfo } from "@/lib/types";

export function Topbar({
  roles,
  activeRole,
  onRole,
  showDocs,
  showInspector,
  onToggleDocs,
  onToggleInspector,
}: {
  roles: RoleInfo[];
  activeRole: string | null;
  onRole: (role: string | null) => void;
  showDocs: boolean;
  showInspector: boolean;
  onToggleDocs: () => void;
  onToggleInspector: () => void;
}) {
  return (
    <header className="flex items-center gap-3 border-b border-white/[0.07] bg-surface/40 px-4 py-2.5 backdrop-blur">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-xl border border-trust/30 bg-trust/10 text-trust-bright shadow-glow">
          <LogoMark width={18} height={18} />
        </span>
        <div className="leading-tight">
          <p className="font-display text-[15px] font-semibold tracking-tight text-ink">Praxis</p>
          <p className="hidden text-[10.5px] text-ink-faint sm:block">
            Governed document intelligence
          </p>
        </div>
      </div>

      <div className="mx-auto">
        <RoleSwitcher roles={roles} active={activeRole} onChange={onRole} />
      </div>

      <div className="flex items-center gap-1">
        <Link
          href="/pricing"
          className="mr-1 hidden rounded-lg px-2.5 py-1.5 text-[12.5px] font-medium text-ink-muted transition-colors hover:text-ink sm:block"
        >
          Pricing
        </Link>
        <ThemeToggle />
        <span className="mx-1 hidden h-5 w-px bg-white/10 sm:block" />
        <button
          type="button"
          onClick={onToggleDocs}
          title="Toggle documents panel"
          className={`grid h-8 w-8 place-items-center rounded-lg border transition-colors ${
            showDocs ? "border-trust/30 bg-trust/10 text-trust" : "border-white/10 text-ink-faint hover:text-ink"
          }`}
        >
          <DocIcon width={15} height={15} />
        </button>
        <button
          type="button"
          onClick={onToggleInspector}
          title="Toggle glass-box inspector"
          className={`grid h-8 w-8 place-items-center rounded-lg border transition-colors ${
            showInspector
              ? "border-trust/30 bg-trust/10 text-trust"
              : "border-white/10 text-ink-faint hover:text-ink"
          }`}
        >
          <ColumnsIcon width={15} height={15} />
        </button>
      </div>
    </header>
  );
}
