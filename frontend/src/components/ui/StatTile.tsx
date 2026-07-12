import type { LucideIcon } from "lucide-react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { clsx } from "clsx";

export function StatTile({
  label,
  value,
  icon: Icon,
  delta,
  deltaLabel,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  icon?: LucideIcon;
  delta?: number;
  deltaLabel?: string;
  tone?: "neutral" | "good" | "warning" | "critical";
}) {
  const toneClass = {
    neutral: "text-slate-400 dark:text-slate-500",
    good: "text-status-good",
    warning: "text-status-warning",
    critical: "text-status-critical",
  }[tone];

  return (
    <div className="stat-tile">
      <div className="flex items-center justify-between">
        <span className="stat-tile-label">
          {Icon && <Icon size={13} className={toneClass} />}
          {label}
        </span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <span className="stat-value">{value}</span>
        {typeof delta === "number" && (
          <span
            className={clsx(
              "flex items-center gap-0.5 text-xs font-semibold pb-0.5",
              delta >= 0 ? "stat-delta-up" : "stat-delta-down"
            )}
          >
            {delta >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
            {Math.abs(delta)}
            {deltaLabel && <span className="text-slate-400 dark:text-slate-500 font-normal ml-0.5">{deltaLabel}</span>}
          </span>
        )}
      </div>
    </div>
  );
}
