"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { INDICATOR_TYPE_LABELS, KR_CADENCE_LABELS } from "@/lib/types";
import type { ObjectiveDetail, IndicatorType, KRDirection, KRCadence } from "@/lib/types";

const TREND_ICON = { up: TrendingUp, down: TrendingDown, flat: Minus };

export default function ObjectiveDetailPage() {
  const params = useParams();
  const objectiveId = Number(params.objectiveId);
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    code: "",
    title: "",
    indicator_type: "quantity" as IndicatorType,
    direction: "increase" as KRDirection,
    cadence: "weekly" as KRCadence,
    baseline_value: 0,
    target_value: 0,
  });

  const { data: objective } = useQuery<ObjectiveDetail>({
    queryKey: ["okr", "objective", objectiveId],
    queryFn: () => api.get(`/okr/objectives/${objectiveId}`).then((r) => r.data),
    enabled: !!objectiveId,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post(`/okr/objectives/${objectiveId}/key-results`, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "objective", objectiveId] });
      setShowForm(false);
      setForm({ code: "", title: "", indicator_type: "quantity", direction: "increase", cadence: "weekly", baseline_value: 0, target_value: 0 });
    },
  });

  if (!objective) return <p className="text-slate-400 text-sm p-4">Carregando...</p>;

  const isFormReady = !!form.code && !!form.title && form.target_value !== 0;
  const performanceTone =
    objective.performance_percent >= 80 ? "bg-status-good" : objective.performance_percent >= 50 ? "bg-status-warning" : "bg-status-critical";

  return (
    <div>
      <Link href="/dashboard/okr" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3">
        <ArrowLeft size={15} /> Voltar aos objetivos
      </Link>

      <div className="mb-5">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">{objective.title}</h1>
        {objective.description && <p className="text-slate-500 text-sm mt-1">{objective.description}</p>}
        <p className="text-xs text-slate-400 mt-1">
          {new Date(objective.start_date).toLocaleDateString("pt-BR")} até {new Date(objective.end_date).toLocaleDateString("pt-BR")}
        </p>
      </div>

      <div className="card p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Performance Geral</span>
          <span className="text-lg font-bold text-slate-900 dark:text-white tabular-nums">{objective.performance_percent}%</span>
        </div>
        <div className="h-3 bg-surface-100 dark:bg-surface-800 rounded-full overflow-hidden">
          <div className={clsx("h-full rounded-full", performanceTone)} style={{ width: `${Math.min(objective.performance_percent, 100)}%` }} />
        </div>
      </div>

      <div className="card mb-6">
        <div className="panel-header">
          <span className="font-semibold text-slate-900 dark:text-white">Key Results</span>
          <button className="btn-primary flex items-center gap-1.5 py-1.5 text-sm" onClick={() => setShowForm(true)}>
            <Plus size={14} /> Novo KR
          </button>
        </div>

        {showForm && (
          <div className="p-4 border-b border-surface-100 dark:border-slate-800">
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              <input className="input" placeholder="Código (ex: 8.1)" value={form.code} onChange={(e) => setForm((p) => ({ ...p, code: e.target.value }))} />
              <input className="input lg:col-span-2" placeholder="Título do KR" value={form.title} onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))} />
              <select className="input" value={form.indicator_type} onChange={(e) => setForm((p) => ({ ...p, indicator_type: e.target.value as IndicatorType }))}>
                {Object.entries(INDICATOR_TYPE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
              <select className="input" value={form.direction} onChange={(e) => setForm((p) => ({ ...p, direction: e.target.value as KRDirection }))}>
                <option value="increase">Quanto maior, melhor</option>
                <option value="decrease">Quanto menor, melhor</option>
              </select>
              <select className="input" value={form.cadence} onChange={(e) => setForm((p) => ({ ...p, cadence: e.target.value as KRCadence }))}>
                {Object.entries(KR_CADENCE_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
              <input
                type="number"
                className="input"
                placeholder="Valor inicial (baseline)"
                value={form.baseline_value || ""}
                onChange={(e) => setForm((p) => ({ ...p, baseline_value: Number(e.target.value) }))}
              />
              <input
                type="number"
                className="input"
                placeholder="Meta"
                value={form.target_value || ""}
                onChange={(e) => setForm((p) => ({ ...p, target_value: Number(e.target.value) }))}
              />
            </div>
            <div className="flex gap-2 mt-3">
              <button className="btn-primary" disabled={!isFormReady || createMutation.isPending} onClick={() => createMutation.mutate()}>
                {createMutation.isPending ? "Criando..." : "Criar"}
              </button>
              <button className="btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
            </div>
          </div>
        )}

        {objective.key_results.length === 0 ? (
          <p className="text-slate-400 text-sm p-4">Nenhum KR cadastrado ainda.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="table-dense">
              <thead>
                <tr>
                  <th>KR</th>
                  <th>Atual</th>
                  <th>Meta</th>
                  <th>Progresso</th>
                  <th>Tendência</th>
                </tr>
              </thead>
              <tbody>
                {objective.key_results.map((kr) => {
                  const TrendIcon = TREND_ICON[kr.trend_direction];
                  const isFavorable =
                    (kr.direction === "increase" && kr.trend_direction === "up") ||
                    (kr.direction === "decrease" && kr.trend_direction === "down");
                  return (
                    <tr key={kr.id}>
                      <td>
                        <Link href={`/dashboard/okr/key-results/${kr.id}`} className="text-primary-600 hover:underline font-medium">
                          {kr.code} — {kr.title}
                        </Link>
                      </td>
                      <td className="tabular-nums">{kr.current_value ?? "—"}</td>
                      <td className="tabular-nums">{kr.target_value}</td>
                      <td className="tabular-nums">{kr.progress_percent}%</td>
                      <td>
                        <TrendIcon
                          size={16}
                          className={kr.trend_direction === "flat" ? "text-slate-400" : isFavorable ? "text-status-good" : "text-status-critical"}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
