import { clsx } from "clsx";

export function Chip({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-full border transition-colors max-w-[180px]",
        active
          ? "bg-primary-50 border-primary-200 text-primary-700"
          : "bg-white dark:bg-surface-900 border-surface-200 dark:border-slate-700 text-slate-500 hover:border-surface-300"
      )}
    >
      {icon}
      <span className="truncate">{label}</span>
    </button>
  );
}
