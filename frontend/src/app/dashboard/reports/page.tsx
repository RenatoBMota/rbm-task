"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileBarChart,
  Download,
  TrendingUp,
  AlertTriangle,
  Coins,
  ShieldAlert,
  ListChecks,
  Plus,
} from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList } from "recharts";
import { clsx } from "clsx";
import { format } from "date-fns";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { StatTile } from "@/components/ui/StatTile";
import { TASK_STATUSES } from "@/lib/types";
import type { Project, ExecutiveReport, Recap, RecapPeriod } from "@/lib/types";

const EMPTY_PROJECTS: Project[] = [];

const STATUS_LABEL = Object.fromEntries(TASK_STATUSES.map((s) => [s.value, s.label]));

const RISK_TONE: Record<string, "good" | "warning" | "critical"> = {
  low: "good",
  medium: "warning",
  high: "critical",
};

const RISK_LABEL: Record<string, string> = { low: "Baixo", medium: "Médio", high: "Alto" };

const PERIOD_OPTIONS: { value: RecapPeriod; label: string }[] = [
  { value: "daily", label: "Diário" },
  { value: "weekly", label: "Semanal" },
  { value: "monthly", label: "Mensal" },
  { value: "custom", label: "Personalizado" },
];

export default function ReportsPage() {
  const { currentWorkspaceId } = useWorkspaces();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [period, setPeriod] = useState<RecapPeriod>("weekly");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const { data: projects = EMPTY_PROJECTS } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const effectiveProjectId = projectId ?? projects[0]?.id ?? null;

  const { data: report } = useQuery<ExecutiveReport>({
    queryKey: ["reports", "executive", effectiveProjectId],
    queryFn: () => api.get(`/reports/projects/${effectiveProjectId}/executive`).then((r) => r.data),
    enabled: !!effectiveProjectId,
  });

  const isCustomReady = period !== "custom" || (!!customStart && !!customEnd);

  const { data: recap, error: recapError } = useQuery<Recap>({
    queryKey: ["reports", "recap", currentWorkspaceId, period, customStart, customEnd],
    queryFn: () => {
      let params: Record<string, string> = { period };
      if (period === "custom") {
        const endOfDay = new Date(customEnd);
        endOfDay.setHours(23, 59, 59, 999);
        params = { period, start: new Date(customStart).toISOString(), end: endOfDay.toISOString() };
      }
      return api.get(`/reports/workspaces/${currentWorkspaceId}/recap`, { params }).then((r) => r.data);
    },
    enabled: !!currentWorkspaceId && isCustomReady,
  });

  const recapErrorMessage = (recapError as { response?: { data?: { detail?: string } } })?.response?.data?.detail;

  const downloadExecutivePdf = async () => {
    if (!effectiveProjectId) return;
    const res = await api.get(`/reports/projects/${effectiveProjectId}/executive.pdf`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio-executivo-${report?.project_name ?? effectiveProjectId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const statusChartData = (report?.status_breakdown ?? []).map((s) => ({
    name: STATUS_LABEL[s.status] ?? s.status,
    count: s.count,
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <FileBarChart size={22} className="text-primary-600" /> Relatórios
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">Visão executiva por projeto e resumo periódico da equipe</p>
        </div>
      </div>

      {/* Executive report */}
      <section className="card mb-6">
        <div className="panel-header flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-900 dark:text-white">Relatório Executivo</span>
            <select
              className="input w-56 py-1.5"
              value={effectiveProjectId ?? ""}
              onChange={(e) => setProjectId(Number(e.target.value))}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn-secondary flex items-center gap-1.5 py-1.5 text-sm"
            onClick={downloadExecutivePdf}
            disabled={!effectiveProjectId}
          >
            <Download size={14} /> Exportar PDF
          </button>
        </div>

        {!effectiveProjectId ? (
          <p className="text-slate-400 text-sm p-4">Crie um projeto para ver o relatório executivo.</p>
        ) : !report ? (
          <p className="text-slate-400 text-sm p-4">Carregando...</p>
        ) : (
          <div className="p-4">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-5">
              <StatTile
                label="Progresso"
                value={`${report.progress_percent}%`}
                icon={ListChecks}
                tone={report.on_schedule ? "good" : "warning"}
              />
              <StatTile
                label="Prazo esperado"
                value={`${report.expected_progress_percent}%`}
                icon={TrendingUp}
                tone="neutral"
              />
              <StatTile
                label="Custo total"
                value={`R$ ${report.total_cost.toFixed(2)}`}
                icon={Coins}
                tone="neutral"
              />
              <StatTile
                label="Risco"
                value={RISK_LABEL[report.risk_level]}
                icon={ShieldAlert}
                tone={RISK_TONE[report.risk_level]}
              />
              <StatTile
                label="Atrasadas"
                value={report.overdue_tasks}
                icon={AlertTriangle}
                tone={report.overdue_tasks > 0 ? "critical" : "good"}
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Tarefas por status</h3>
                {statusChartData.length === 0 ? (
                  <p className="text-sm text-slate-400">Sem tarefas neste projeto.</p>
                ) : (
                  <ResponsiveContainer width="100%" height={Math.max(statusChartData.length * 40, 120)}>
                    <BarChart data={statusChartData} layout="vertical" margin={{ left: 8, right: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e1e0d9" />
                      <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#2a78d6" radius={[0, 4, 4, 0]} barSize={18}>
                        <LabelList dataKey="count" position="right" fontSize={11} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
                <p className="text-xs text-slate-400 mt-2">
                  Caminho crítico: {report.critical_task_count} tarefa(s) · {report.completed_tasks}/{report.total_tasks} concluídas
                </p>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Carga da equipe</h3>
                {report.team.length === 0 ? (
                  <p className="text-sm text-slate-400">Nenhuma tarefa atribuída ainda.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="table-dense">
                      <thead>
                        <tr>
                          <th>Membro</th>
                          <th>Ativas</th>
                          <th>Concluídas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.team.map((m) => (
                          <tr key={m.user_id}>
                            <td>{m.full_name}</td>
                            <td>{m.active_task_count}</td>
                            <td>{m.completed_task_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Periodic recap */}
      <section className="card">
        <div className="panel-header flex-wrap gap-2">
          <span className="font-semibold text-slate-900 dark:text-white">Resumo Periódico</span>
          <div className="flex items-center gap-2 flex-wrap">
            {period === "custom" && (
              <div className="flex items-center gap-1.5 text-sm">
                <input
                  type="date"
                  className="input py-1.5 w-36"
                  value={customStart}
                  onChange={(e) => setCustomStart(e.target.value)}
                />
                <span className="text-slate-400">até</span>
                <input
                  type="date"
                  className="input py-1.5 w-36"
                  value={customEnd}
                  onChange={(e) => setCustomEnd(e.target.value)}
                />
              </div>
            )}
            <div className="flex rounded-lg border border-surface-200 dark:border-slate-700 overflow-hidden text-sm">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={clsx(
                    "px-3 py-1.5",
                    period === opt.value
                      ? "bg-primary-600 text-white"
                      : "text-slate-500 dark:text-slate-400 hover:bg-surface-50 dark:hover:bg-surface-800"
                  )}
                  onClick={() => setPeriod(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {period === "custom" && !isCustomReady ? (
          <p className="text-slate-400 text-sm p-4">Selecione as datas de início e fim.</p>
        ) : recapErrorMessage ? (
          <p className="text-sm text-red-600 p-4">{recapErrorMessage}</p>
        ) : !recap ? (
          <p className="text-slate-400 text-sm p-4">Carregando...</p>
        ) : (
          <div className="p-4">
            <p className="text-xs text-slate-400 mb-3">
              {format(new Date(recap.period_start), "dd/MM/yyyy HH:mm")} — {format(new Date(recap.period_end), "dd/MM/yyyy HH:mm")}
            </p>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
              <StatTile label="Criadas" value={recap.tasks_created} icon={Plus} tone="neutral" />
              <StatTile
                label="Concluídas"
                value={recap.tasks_completed}
                icon={ListChecks}
                tone="good"
                delta={recap.completed_delta}
                deltaLabel="vs período anterior"
              />
              <StatTile label="Atrasadas" value={recap.tasks_overdue} icon={AlertTriangle} tone={recap.tasks_overdue > 0 ? "critical" : "good"} />
            </div>

            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Top contribuidores</h3>
            {recap.top_contributors.length === 0 ? (
              <p className="text-sm text-slate-400">Nenhuma tarefa concluída neste período.</p>
            ) : (
              <div className="space-y-1.5">
                {recap.top_contributors.map((c, i) => (
                  <div key={c.user_id} className="flex items-center gap-3 text-sm">
                    <span className="w-5 text-slate-400 font-medium">{i + 1}.</span>
                    <span className="flex-1 text-slate-700 dark:text-slate-300">{c.full_name}</span>
                    <span className="text-slate-500 dark:text-slate-400 tabular-nums">{c.completed_count} concluídas</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
