"use client";

import { useState } from "react";

import { ChevronRightIcon } from "@/components/icons";
import { startCheckout } from "@/lib/api";

export function CheckoutButton({
  tier,
  label,
  highlight,
}: {
  tier: string;
  label: string;
  highlight?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const go = async () => {
    setLoading(true);
    setMessage(null);
    const res = await startCheckout(tier);
    if (res.url) {
      window.location.href = res.url;
      return;
    }
    setMessage(res.error ?? "Something went wrong.");
    setLoading(false);
  };

  return (
    <div className="mt-6">
      <button
        type="button"
        onClick={go}
        disabled={loading}
        className={`inline-flex w-full items-center justify-center gap-1.5 rounded-xl px-4 py-2.5 text-[13px] font-semibold transition-colors disabled:opacity-60 ${
          highlight
            ? "bg-trust text-canvas hover:bg-trust-bright"
            : "border border-white/15 text-ink hover:border-white/30"
        }`}
      >
        {loading ? "Redirecting…" : label}
        {!loading && <ChevronRightIcon width={14} height={14} />}
      </button>
      {message && <p className="mt-2 text-center text-[11px] text-ink-faint">{message}</p>}
    </div>
  );
}
