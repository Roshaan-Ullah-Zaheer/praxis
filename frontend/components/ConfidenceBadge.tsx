import { CheckIcon, AlertIcon } from "@/components/icons";
import type { Grounding } from "@/lib/types";

export function ConfidenceBadge({
  grounding,
  size = "sm",
}: {
  grounding: Grounding | null | undefined;
  size?: "sm" | "lg";
}) {
  if (!grounding) return null;
  const grounded = grounding.grounded;
  const pct = Math.round((grounding.confidence ?? 0) * 100);
  const Icon = grounded ? CheckIcon : AlertIcon;
  const tone = grounded
    ? "border-trust/30 bg-trust/10 text-trust-bright"
    : "border-conflict-red/30 bg-conflict-red/10 text-conflict-red";

  if (size === "lg") {
    return (
      <div className={`rounded-xl border px-3.5 py-3 ${tone}`}>
        <div className="flex items-center gap-2">
          <Icon width={16} height={16} />
          <span className="text-sm font-semibold">
            {grounded ? "Grounded answer" : "Insufficient support"}
          </span>
          <span className="ml-auto font-mono text-sm">{pct}%</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className={`h-full rounded-full ${grounded ? "bg-trust" : "bg-conflict-red"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        {grounding.unsupported?.length > 0 && (
          <ul className="mt-2.5 space-y-1">
            {grounding.unsupported.map((u, i) => (
              <li key={i} className="text-[12px] text-conflict">
                • {u}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${tone}`}
      title={grounded ? "Verifier confirmed every claim is supported" : "The verifier flagged unsupported claims"}
    >
      <Icon width={12} height={12} />
      {grounded ? "Grounded" : "Unsupported"}
      <span className="font-mono opacity-80">{pct}%</span>
    </span>
  );
}
