"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, TrendingUp, TrendingDown, Minus, Pencil, Trash2 } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { INDICATOR_TYPE_LABELS, KR_CADENCE_LABELS } from "@/lib/types";
import type { ObjectiveDetail, IndicatorType, KRDirection, KRCadence, KeyResultDetail } from "@/lib/types";

const TREND_ICON = { up: TrendingUp, down: TrendingDown, flat: Minus };

export default function ObjectiveDetailPage() {
  const params = useParams();
  const router = useRouter();
  const objectiveId = Number(params.objectiveId);
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingKrId, setEditingKrId] = useState<number | null>(null);
  const [form, setForm] = useState({
    code: "",
    title: "",
    indicator_type: "quantity" as IndicatorType,
    direction: "increase" as KRDirection,
    cadence: "weekly" as KRCadence,
    baseline_value: 0,
    target_value: 0,
  });

  const [showObjectiveForm, setShowObjectiveForm] = useState(false);
  const [objectiveForm, setObjectiveForm] = useState({ title: "", description: "", start_date: "", end_date: "" });

  const { data: objective } = useQuery<ObjectiveDetail>({
    queryKey: ["okr", "objective", objectiveId],
    queryFn: () => api.get(`/okr/objectives/${objectiveId}`).then((r) => r.data),
    enabled: !!objectiveId,
  });

  const createMutation = useMutation({
    mutationFn: () => api.post(`/okr/objectives/${objectiveId}/key-results`, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "objective", objectiveId] });
      closeKrForm();
    },
  });

  const updateKrMutation = useMutation({
    mutationFn: () => api.put(`/okr/key-results/${editingKrId}`, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "objective", objectiveId] });
      closeKrForm();
    },
  });

  const deleteKrMutation = useMutation({
    mutationFn: (krId: number) => api.delete(`/okr/key-results/${krId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["okr", "objective", objectiveId] }),
  });

  function closeKrForm() {
    setShowForm(false);
    setEditingKrId(null);
    setForm({ code: "", title: "", indicator_type: "quantity", direction: "increase", cadence: "weekly", baseline_value: 0, target_value: 0 });
  }

  async function openEditKr(krId: number) {
    const { data } = await api.get<KeyResultDetail>(`/okr/key-results/${krId}`);
    setForm({
      code: data.code,
      title: data.title,
      indicator_type: data.indicator_type,
      direction: data.direction,
      cadence: data.cadence,
      baseline_value: data.baseline_value,
      target_value: data.target_value,
    });
    setEditingKrId(krId);
    setShowForm(true);
  }

  const updateObjectiveMutation = useMutation({
    mutationFn: () =>
      api.put(`/okr/objectives/${objectiveId}`, {
        title: objectiveForm.title,
        description: objectiveForm.description || null,
        start_date: new Date(objectiveForm.start_date).toISOString(),
        end_date: new Date(objectiveForm.end_date).toISOString(),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "objective", objectiveId] });
      setShowObjectiveForm(false);
    },
  });

  const deleteObjectiveMutation = useMutation({
    mutationFn: () => api.delete(`/okr/objectives/${objectiveId}`),
    onSuccess: () => router.push("/dashboard/okr"),
  });

  function openEditObjective() {
    if (!objective) return;
    setObjectiveForm({
      title: objective.title,
      description: objective.description ?? "",
      start_date: objective.start_date.slice(0, 10),
      end_date: objective.end_date.slice(0, 10),
    });
    setShowObjectiveForm(true);
  }

  if (!objective) return <p className="text-slate-400 text-sm p-4">Carregando...</p>;

  const isFormReady = !!form.code && !!form.title && form.target_value !== 0;
  const performanceTone =
    objective.performance_percent >= 80 ? "bg-status-good" : objective.performance_percent >= 50 ? "bg-status-warning" : "bg-status-critical";

  return (
    <div>
      <Link href="/dashboard/okr" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3">
        <ArrowLeft size={15} /> Voltar aos objetivos
      </Link>

      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">{objective.title}</h1>
          {objective.description && <p className="text-slate-500 text-sm mt-1">{objective.description}</p>}
          <p className="text-xs text-slate-400 mt-1">
            {new Date(objective.start_date).toLocaleDateString("pt-BR")} até {new Date(objective.end_date).toLocaleDateString("pt-BR")}
          </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button onClick={openEditObjective} className="text-slate-400 hover:text-primary-600 p-1.5">
            <Pencil size={16} />
          </button>
          <button onClick={() => deleteObjectiveMutation.mutate()} className="text-slate-400 hover:text-red-500 p-1.5">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {showObjectiveForm && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold mb-4 text-slate-900 dark:text-white">Editar Objetivo</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <input
              className="input lg:col-span-2"
              placeholder="Título do objetivo"
              value={objectiveForm.title}
              onChange={(e) => setObjectiveForm((p) => ({ ...p, title: e.target.value }))}
            />
            <textarea
              className="input lg:col-span-2"
              placeholder="Descrição (opcional)"
              value={objectiveForm.description}
              onChange={(e) => setObjectiveForm((p) => ({ ...p, description: e.target.value }))}
            />
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Início</label>
              <input
                type="date"
                className="input"
                value={objectiveForm.start_date}
                onChange={(e) => setObjectiveForm((p) => ({ ...p, start_date: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Fim</label>
              <input
                type="date"
                className="input"
                value={objectiveForm.end_date}
                onChange={(e) => setObjectiveForm((p) => ({ ...p, end_date: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn-primary" disabled={updateObjectiveMutation.isPending} onClick={() => updateObjectiveMutation.mutate()}>
              {updateObjectiveMutation.isPending ? "Salvando..." : "Salvar"}
            </button>
            <button className="btn-secondary" onClick={() => setShowObjectiveForm(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

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
          <button
            className="btn-primary flex items-center gap-1.5 py-1.5 text-sm"
            onClick={() => {
              setEditingKrId(null);
              setShowForm(true);
            }}
          >
            <Plus size={14} /> Novo KR
          </button>
        </div>

        {showForm && (
          <div className="p-4 border-b border-surface-100 dark:border-slate-800">
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">{editingKrId ? "Editar KR" : "Novo KR"}</h3>
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
              <button
                className="btn-primary"
                disabled={!isFormReady || createMutation.isPending || updateKrMutation.isPending}
                onClick={() => (editingKrId ? updateKrMutation.mutate() : createMutation.mutate())}
              >
                {createMutation.isPending || updateKrMutation.isPending ? "Salvando..." : editingKrId ? "Salvar" : "Criar"}
              </button>
              <button className="btn-secondary" onClick={closeKrForm}>Cancelar</button>
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
                  <th></th>
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
                      <td>
                        <div className="flex items-center gap-1">
                          <button onClick={() => openEditKr(kr.id)} className="text-slate-300 hover:text-primary-600 p-1">
                            <Pencil size={14} />
                          </button>
                          <button onClick={() => deleteKrMutation.mutate(kr.id)} className="text-slate-300 hover:text-red-500 p-1">
                            <Trash2 size={14} />
                          </button>
                        </div>
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
