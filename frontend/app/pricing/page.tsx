import type { Metadata } from "next";
import Link from "next/link";

import { PricingTable } from "@/components/PricingTable";
import { ChevronRightIcon, LogoMark } from "@/components/icons";

export const metadata: Metadata = {
  title: "Pricing — Praxis",
  description: "Plans for Praxis, the governed multi-agent document intelligence workspace.",
};

export default function PricingPage() {
  return (
    <div className="min-h-[100dvh] px-6 py-10">
      <div className="mx-auto max-w-5xl">
        <header className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-xl border border-trust/30 bg-trust/10 text-trust-bright shadow-glow">
              <LogoMark width={18} height={18} />
            </span>
            <span className="font-display text-[15px] font-semibold tracking-tight text-ink">Praxis</span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
          >
            Open workspace
            <ChevronRightIcon width={14} height={14} />
          </Link>
        </header>

        <div className="mx-auto mt-14 max-w-2xl text-center">
          <span className="chip border-trust/25 bg-trust/[0.07] text-trust-bright">Plans</span>
          <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-ink">
            Govern your documents at any scale
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-ink-muted">
            Start free with the sample corpus. Upgrade when you need the full agent suite,
            cross-document contradiction detection, and live role-based governance.
          </p>
        </div>

        <div className="mt-12">
          <PricingTable />
        </div>

        <p className="mt-10 text-center text-[12px] text-ink-faint">
          Subscriptions run through Stripe in test mode for this demo — no real charges. The public
          demo needs no account to try the sample corpus.
        </p>
      </div>
    </div>
  );
}
