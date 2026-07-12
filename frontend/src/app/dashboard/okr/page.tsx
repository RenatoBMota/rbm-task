"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Target, Plus, AlertTriangle, ListChecks, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { StatTile } from "@/components/ui/StatTile";
import type { Objective, OkrExecutiveSummary, OkrAlert } from "@/lib/types";

const EMPTY_OBJECTIVES: Objective[] = [];
const EMPTY_ALERTS: OkrAlert[] = [];

export default function OkrPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", start_date: "", end_date: "" });

  const { data: summary } = useQuery<OkrExecutiveSummary>({
    queryKey: ["okr", "executive-summary", currentWorkspaceId],
    queryFn: () => api.get(`/okr/workspaces/${currentWorkspaceId}/executive-summary`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: alerts = EMPTY_ALERTS } = useQuery<OkrAlert[]>({
    queryKey: ["okr", "alerts", currentWorkspaceId],
    queryFn: () => api.get(`/okr/workspaces/${currentWorkspaceId}/alerts`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: objectives = EMPTY_OBJECTIVES } = useQuery<Objective[]>({
    queryKey: ["okr", "objectives", currentWorkspaceId],
    queryFn: () => api.get("/okr/objectives", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post(
        "/okr/objectives",
        {
          title: form.title,
          description: form.description || null,
          start_date: new Date(form.start_date).toISOString(),
          end_date: new Date(form.end_date).toISOString(),
        },
        { params: { workspace_id: currentWorkspaceId } }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "objectives", currentWorkspaceId] });
      qc.invalidateQueries({ queryKey: ["okr", "executive-summary", currentWorkspaceId] });
      setShowForm(false);
      setForm({ title: "", description: "", start_date: "", end_date: "" });
    },
  });

  const isFormReady = !!form.title && !!form.start_date && !!form.end_date;

  return (
    <div>
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Target size={22} className="text-primary-600" /> OKRs & Execução
          </h1>
          <p className="text-slate-500 text-sm mt-0.5">Objetivos, resultados-chave e execução operacional</p>
        </div>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={18} /> Novo Objetivo
        </button>
      </div>

      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 mb-5">
          <StatTile label="Objetivos" value={summary.objectives_count} icon={Target} tone="neutral" />
          <StatTile label="KRs" value={summary.key_results_count} icon={ListChecks} tone="neutral" />
          <StatTile label="Iniciativas" value={summary.initiatives_count} icon={ListChecks} tone="neutral" />
          <StatTile label="Tarefas" value={summary.tasks_count} icon={ListChecks} tone="neutral" />
          <StatTile label="Ações" value={summary.actions_count} icon={ListChecks} tone="neutral" />
          <StatTile
            label="Performance geral"
            value={`${summary.overall_performance_percent}%`}
            icon={Target}
            tone={summary.overall_performance_percent >= summary.expected_performance_percent ? "good" : "warning"}
          />
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <StatTile label="Meta prevista" value={`${summary.expected_performance_percent}%`} tone="neutral" />
          <StatTile
            label="No prazo"
            value={`${summary.on_time_percent}%`}
            tone={summary.on_time_percent >= 80 ? "good" : "warning"}
          />
          <StatTile label="Concluídas" value={`${summary.completed_percent}%`} tone="good" />
        </div>
      )}

      {showForm && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold mb-4 text-slate-900 dark:text-white">Novo Objetivo</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <input
              className="input lg:col-span-2"
              placeholder="Título do objetivo"
              value={form.title}
              onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
            />
            <textarea
              className="input lg:col-span-2"
              placeholder="Descrição (opcional)"
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
            />
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Início</label>
              <input
                type="date"
                className="input"
                value={form.start_date}
                onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Fim</label>
              <input
                type="date"
                className="input"
                value={form.end_date}
                onChange={(e) => setForm((p) => ({ ...p, end_date: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              className="btn-primary"
              disabled={!isFormReady || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Criando..." : "Criar"}
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {alerts.length > 0 && (
        <div className="card mb-6">
          <div className="panel-header">
            <span className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <AlertTriangle size={16} className="text-status-warning" /> Alertas Inteligentes ({alerts.length})
            </span>
          </div>
          <div className="p-4 space-y-1.5 max-h-72 overflow-y-auto">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span
                  className={clsx(
                    "mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0",
                    a.level === "critical" ? "bg-status-critical" : "bg-status-warning"
                  )}
                />
                <span className="text-slate-600 dark:text-slate-300">
                  <span className="font-medium text-slate-800 dark:text-slate-100">{a.entity_title}</span> — {a.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {objectives.length === 0 ? (
        <div className="card p-10 text-center text-slate-400">
          <Target size={40} className="mx-auto mb-3 opacity-30" />
          <p>Nenhum objetivo cadastrado ainda.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {objectives.map((o) => (
            <Link
              key={o.id}
              href={`/dashboard/okr/${o.id}`}
              className="card p-4 flex items-center justify-between hover:border-primary-400 dark:hover:border-primary-500 transition-colors"
            >
              <div className="min-w-0">
                <p className="font-semibold text-slate-900 dark:text-white truncate">{o.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {new Date(o.start_date).toLocaleDateString("pt-BR")} — {new Date(o.end_date).toLocaleDateString("pt-BR")}
                </p>
              </div>
              <ChevronRight size={18} className="text-slate-300 flex-shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
