"use client";

import { Sun, Moon, Monitor } from "lucide-react";
import { clsx } from "clsx";
import { useThemeStore } from "@/store/theme";

const OPTIONS = [
  { mode: "light" as const, icon: Sun, label: "Claro" },
  { mode: "dark" as const, icon: Moon, label: "Escuro" },
  { mode: "system" as const, icon: Monitor, label: "Sistema" },
];

export function ThemeToggle({ className }: { className?: string }) {
  const { mode, setMode } = useThemeStore();

  return (
    <div className={clsx("flex items-center rounded-lg border border-surface-200 dark:border-slate-700 p-0.5", className)}>
      {OPTIONS.map(({ mode: m, icon: Icon, label }) => (
        <button
          key={m}
          title={label}
          onClick={() => setMode(m)}
          className={clsx(
            "p-1.5 rounded-md transition-colors",
            mode === m
              ? "bg-primary-600 text-white"
              : "text-slate-400 hover:text-slate-700 hover:dark:text-slate-300 dark:hover:text-slate-200"
          )}
        >
          <Icon size={14} />
        </button>
      ))}
    </div>
  );
}
