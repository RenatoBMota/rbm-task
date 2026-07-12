"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, AlertCircle, FolderOpen, Sparkles, ShieldAlert } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { StatTile } from "@/components/ui/StatTile";

interface PrioritySuggestion {
  task_id: number;
  title: string;
  score: number;
  reason: string;
}

interface RiskTask {
  task_id: number;
  title: string;
  risk: "at_risk" | "breached";
  deadline: string;
}

interface Task {
  id: number;
  title: string;
  priority: string;
  status: string;
  due_date: string | null;
  is_completed: boolean;
}

interface Project {
  id: number;
  name: string;
  color: string;
}

const priorityColors: Record<string, string> = {
  P1: "bg-red-100 text-red-700",
  P2: "bg-orange-100 text-orange-700",
  P3: "bg-blue-100 text-blue-700",
  P4: "bg-slate-100 text-slate-600 dark:text-slate-400",
};

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { currentWorkspaceId } = useWorkspaces();

  const { data: todayTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", "today", currentWorkspaceId],
    queryFn: () => api.get("/tasks/today", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: overdueTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", "overdue", currentWorkspaceId],
    queryFn: () => api.get("/tasks/overdue", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: allTasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", currentWorkspaceId],
    queryFn: () => api.get("/tasks", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: suggestions = [] } = useQuery<PrioritySuggestion[]>({
    queryKey: ["ai", "priority-suggestions"],
    queryFn: () => api.get("/ai/priority-suggestions", { params: { limit: 5 } }).then((r) => r.data),
  });

  const { data: riskTasks = [] } = useQuery<RiskTask[]>({
    queryKey: ["ai", "risk-tasks"],
    queryFn: () => api.get("/ai/risk-tasks").then((r) => r.data),
  });

  const completedToday = allTasks.filter((t) => t.is_completed).length;

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">
          Bom dia, {user?.full_name?.split(" ")[0]} 👋
        </h1>
        <p className="text-slate-500 text-sm mt-0.5">Aqui está o resumo do seu dia</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        <StatTile label="Para hoje" value={todayTasks.length} icon={Clock} tone="neutral" />
        <StatTile label="Atrasadas" value={overdueTasks.length} icon={AlertCircle} tone={overdueTasks.length > 0 ? "critical" : "neutral"} />
        <StatTile label="Concluídas" value={completedToday} icon={CheckCircle2} tone="good" />
        <StatTile label="Projetos ativos" value={projects.length} icon={FolderOpen} tone="neutral" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <TaskList title="Tarefas de Hoje" tasks={todayTasks} emptyMsg="Nenhuma tarefa para hoje" />
        <TaskList title="Tarefas Atrasadas" tasks={overdueTasks} emptyMsg="Nenhuma tarefa atrasada" urgent />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h2 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Sparkles size={16} className="text-primary-600" /> Sugestões de prioridade (IA)
          </h2>
          {suggestions.length === 0 ? (
            <p className="text-slate-400 text-sm">Nenhuma sugestão no momento</p>
          ) : (
            <ul className="space-y-2">
              {suggestions.map((s) => (
                <li key={s.task_id} className="py-2 border-b border-surface-100 dark:border-slate-800 last:border-0">
                  <p className="text-sm text-slate-700 dark:text-slate-300 truncate">{s.title}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{s.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card p-5">
          <h2 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <ShieldAlert size={16} className="text-amber-600" /> Tarefas em risco de SLA
          </h2>
          {riskTasks.length === 0 ? (
            <p className="text-slate-400 text-sm">Nenhuma tarefa em risco</p>
          ) : (
            <ul className="space-y-2">
              {riskTasks.map((t) => (
                <li key={t.task_id} className="flex items-center gap-3 py-2 border-b border-surface-100 dark:border-slate-800 last:border-0">
                  <span
                    className={clsx(
                      "text-xs font-medium px-2 py-0.5 rounded-full",
                      t.risk === "breached" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                    )}
                  >
                    {t.risk === "breached" ? "Estourado" : "Em risco"}
                  </span>
                  <span className="text-sm text-slate-700 dark:text-slate-300 flex-1 truncate">{t.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function TaskList({
  title,
  tasks,
  emptyMsg,
  urgent,
}: {
  title: string;
  tasks: { id: number; title: string; priority: string }[];
  emptyMsg: string;
  urgent?: boolean;
}) {
  return (
    <div className="card p-5">
      <h2 className={`font-semibold mb-3 ${urgent ? "text-red-700" : "text-slate-900 dark:text-white"}`}>{title}</h2>
      {tasks.length === 0 ? (
        <p className="text-slate-400 text-sm">{emptyMsg}</p>
      ) : (
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li key={t.id} className="flex items-center gap-3 py-2 border-b border-surface-100 dark:border-slate-800 last:border-0">
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColors[t.priority]}`}>
                {t.priority}
              </span>
              <span className="text-sm text-slate-700 dark:text-slate-300 flex-1 truncate">{t.title}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
