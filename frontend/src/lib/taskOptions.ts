import type { TaskPriority, TaskRecurrence } from "./types";

export const PRIORITY_OPTIONS: { value: TaskPriority; label: string; dot: string }[] = [
  { value: "P1", label: "Prioridade 1 — Urgente", dot: "bg-red-500" },
  { value: "P2", label: "Prioridade 2 — Alta", dot: "bg-orange-500" },
  { value: "P3", label: "Prioridade 3 — Média", dot: "bg-blue-500" },
  { value: "P4", label: "Prioridade 4 — Baixa", dot: "bg-slate-400" },
];

export const RECURRENCE_OPTIONS: { value: TaskRecurrence; label: string }[] = [
  { value: "none", label: "Não repetir" },
  { value: "daily", label: "Todo dia" },
  { value: "weekly", label: "Toda semana" },
  { value: "monthly", label: "Todo mês" },
];

export const LABEL_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#6366f1", "#a855f7", "#ec4899"];
