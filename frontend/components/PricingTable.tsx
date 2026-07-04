import Link from "next/link";

import { CheckoutButton } from "@/components/CheckoutButton";
import { CheckIcon, ChevronRightIcon } from "@/components/icons";

interface Tier {
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  highlight?: boolean;
  cta: { label: string; href?: string; checkoutTier?: string };
  features: string[];
}

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "$0",
    cadence: "forever",
    blurb: "Explore the workspace and the sample corpus.",
    cta: { label: "Open workspace", href: "/" },
    features: [
      "Up to 5 documents (10 MB)",
      "15 queries / day",
      "Lightweight + multi-step retrieval",
      "Single role + audit view",
      "Grounding check on every answer",
      "Sample corpus included",
    ],
  },
  {
    name: "Pro",
    price: "$29",
    cadence: "/ month",
    highlight: true,
    blurb: "The full agent suite for serious corpora.",
    cta: { label: "Get Pro", checkoutTier: "pro" },
    features: [
      "Up to 50 documents (50 MB)",
      "300 queries / day",
      "All strategies incl. graph + hierarchical",
      "All roles + live role switcher",
      "Cross-document + contradiction detection",
      "Sourced export + web augmentation",
      "Priority processing",
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    cadence: "",
    blurb: "Scale, custom roles, and API access.",
    cta: { label: "Contact sales", href: "mailto:roshaanullahzaheer6262@gmail.com?subject=Praxis%20Enterprise" },
    features: [
      "Up to 500 documents",
      "High query volume",
      "Custom roles + permissions",
      "API access",
      "Dedicated keep-warm",
      "SSO (on request)",
    ],
  },
];

export function PricingTable() {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      {TIERS.map((tier) => (
        <div
          key={tier.name}
          className={`relative flex flex-col rounded-2xl border p-6 ${
            tier.highlight
              ? "border-trust/40 bg-trust/[0.04] shadow-glow"
              : "border-white/10 bg-surface/60"
          }`}
        >
          {tier.highlight && (
            <span className="absolute -top-3 left-6 rounded-full border border-trust/40 bg-canvas px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-trust-bright">
              Most popular
            </span>
          )}
          <h3 className="font-display text-lg font-semibold text-ink">{tier.name}</h3>
          <p className="mt-1 text-[13px] text-ink-muted">{tier.blurb}</p>
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="font-display text-3xl font-semibold text-ink">{tier.price}</span>
            {tier.cadence && <span className="text-[13px] text-ink-faint">{tier.cadence}</span>}
          </div>

          <ul className="mt-5 flex-1 space-y-2.5">
            {tier.features.map((f) => (
              <li key={f} className="flex items-start gap-2 text-[13px] text-ink-muted">
                <span className="mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full bg-trust/15 text-trust">
                  <CheckIcon width={11} height={11} />
                </span>
                {f}
              </li>
            ))}
          </ul>

          {tier.cta.checkoutTier ? (
            <CheckoutButton
              tier={tier.cta.checkoutTier}
              label={tier.cta.label}
              highlight={tier.highlight}
            />
          ) : (
            <Link
              href={tier.cta.href ?? "/"}
              className={`mt-6 inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2.5 text-[13px] font-semibold transition-colors ${
                tier.highlight
                  ? "bg-trust text-canvas hover:bg-trust-bright"
                  : "border border-white/15 text-ink hover:border-white/30"
              }`}
            >
              {tier.cta.label}
              <ChevronRightIcon width={14} height={14} />
            </Link>
          )}
        </div>
      ))}
    </div>
  );
}
