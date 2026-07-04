"use client";

import { motion } from "framer-motion";
import type { ComponentType, SVGProps } from "react";

import {
  AlertIcon,
  CheckIcon,
  GlobeIcon,
  RotateIcon,
  RouteIcon,
  SearchIcon,
  ShieldIcon,
  SparkIcon,
} from "@/components/icons";
import type { PipelineStep } from "@/lib/useConversation";

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

const META: Record<string, { label: string; icon: IconType; hint: string }> = {
  resolver: { label: "Resolver", icon: SparkIcon, hint: "Resolves follow-up references" },
  router: { label: "Router", icon: RouteIcon, hint: "Picks intent + retrieval strategy" },
  retriever: { label: "Retriever", icon: SearchIcon, hint: "Hybrid search, role-filtered" },
  conflict_detector: { label: "Conflict Detector", icon: AlertIcon, hint: "Compares stances across docs" },
  synthesizer: { label: "Synthesizer", icon: SparkIcon, hint: "Writes the cited answer" },
  verifier: { label: "Verifier", icon: ShieldIcon, hint: "Grounding check before release" },
  reviser: { label: "Reviser", icon: RotateIcon, hint: "Bounded re-write on weak grounding" },
  web: { label: "Web Augment", icon: GlobeIcon, hint: "Labeled public-web fallback" },
};

function StatusDot({ status }: { status: PipelineStep["status"] }) {
  if (status === "done")
    return (
      <span className="grid h-5 w-5 place-items-center rounded-full bg-trust/15 text-trust">
        <CheckIcon width={12} height={12} />
      </span>
    );
  if (status === "revising")
    return (
      <motion.span
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1.1, ease: "linear" }}
        className="grid h-5 w-5 place-items-center rounded-full bg-conflict/15 text-conflict"
      >
        <RotateIcon width={12} height={12} />
      </motion.span>
    );
  return (
    <span className="relative grid h-5 w-5 place-items-center">
      <motion.span
        animate={{ scale: [1, 1.6, 1], opacity: [0.7, 0, 0.7] }}
        transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
        className="absolute h-3 w-3 rounded-full bg-trust"
      />
      <span className="h-2.5 w-2.5 rounded-full bg-trust" />
    </span>
  );
}

export function AgentPipeline({
  steps,
  variant = "inline",
}: {
  steps: PipelineStep[];
  variant?: "inline" | "panel";
}) {
  if (!steps.length) {
    return (
      <p className="text-[12px] text-ink-faint">
        The pipeline will light up here as the agents work.
      </p>
    );
  }

  if (variant === "panel") {
    return (
      <ol className="relative ml-2 space-y-1 border-l border-white/10 pl-5">
        {steps.map((s, i) => {
          const meta = META[s.agent] ?? { label: s.agent, icon: SparkIcon, hint: "" };
          const Icon = meta.icon;
          return (
            <motion.li
              key={`${s.agent}-${i}`}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              className="relative py-1.5"
            >
              <span className="absolute -left-[26px] top-1.5">
                <StatusDot status={s.status} />
              </span>
              <div className="flex items-center gap-2">
                <Icon
                  width={14}
                  height={14}
                  className={s.status === "done" ? "text-ink-muted" : "text-trust"}
                />
                <span className="text-[13px] font-medium text-ink">{meta.label}</span>
              </div>
              {meta.hint && <p className="mt-0.5 text-[11px] text-ink-faint">{meta.hint}</p>}
            </motion.li>
          );
        })}
      </ol>
    );
  }

  // inline (compact, shown inside the streaming bubble)
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {steps.map((s, i) => {
        const meta = META[s.agent] ?? { label: s.agent, icon: SparkIcon, hint: "" };
        const Icon = meta.icon;
        const active = s.status !== "done";
        return (
          <motion.span
            key={`${s.agent}-${i}`}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
              active
                ? "border-trust/40 bg-trust/10 text-trust-bright"
                : "border-white/10 bg-white/[0.03] text-ink-muted"
            }`}
          >
            <Icon width={12} height={12} />
            {meta.label}
            {s.status === "done" && <CheckIcon width={11} height={11} className="text-trust" />}
            {active && s.status === "running" && (
              <motion.span
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1.1 }}
                className="h-1.5 w-1.5 rounded-full bg-trust"
              />
            )}
          </motion.span>
        );
      })}
    </div>
  );
}
