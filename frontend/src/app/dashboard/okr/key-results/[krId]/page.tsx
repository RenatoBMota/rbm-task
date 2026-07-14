"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Plus, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronRight, Trash2, Target, Pencil, Check, X,
} from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { clsx } from "clsx";
import api from "@/lib/api";
import { StatTile } from "@/components/ui/StatTile";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { INDICATOR_TYPE_LABELS, KR_CADENCE_LABELS } from "@/lib/types";
import type { KeyResultDetail, InitiativeDetail, OkrTaskDetail, IndicatorType, KRDirection, KRCadence, WorkspaceMember } from "@/lib/types";

const EMPTY_MEMBERS: WorkspaceMember[] = [];

const TREND_ICON = { up: TrendingUp, down: TrendingDown, flat: Minus };

function ActionRow({ action, taskId, krId }: { action: OkrTaskDetail["actions"][number]; taskId: number; krId: number }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(action.title);
  const [weight, setWeight] = useState(action.weight_percent);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["okr", "initiative-tasks", taskId] });
    qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
  };

  const toggleMutation = useMutation({
    mutationFn: () => api.put(`/okr/actions/${action.id}`, { is_completed: !action.is_completed }),
    onSuccess: invalidate,
  });
  const updateMutation = useMutation({
    mutationFn: () => api.put(`/okr/actions/${action.id}`, { title, weight_percent: weight }),
    onSuccess: () => {
      invalidate();
      setEditing(false);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/okr/actions/${action.id}`),
    onSuccess: invalidate,
  });

  if (editing) {
    return (
      <div className="flex items-center gap-2 py-1.5 pl-8">
        <input className="input py-1 text-xs flex-1" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input type="number" className="input py-1 text-xs w-16" value={weight || ""} onChange={(e) => setWeight(Number(e.target.value))} />
        <button onClick={() => updateMutation.mutate()} className="text-status-good p-1">
          <Check size={14} />
        </button>
        <button onClick={() => setEditing(false)} className="text-slate-400 p-1">
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 py-1.5 pl-8 text-sm">
      <input type="checkbox" checked={action.is_completed} onChange={() => toggleMutation.mutate()} className="w-4 h-4 accent-primary-600" />
      <span className={clsx("flex-1", action.is_completed && "line-through text-slate-400")}>{action.title}</span>
      <span className="text-xs text-slate-400 w-10 text-right tabular-nums">{action.weight_percent}%</span>
      <button onClick={() => setEditing(true)} className="text-slate-300 hover:text-primary-600 p-1">
        <Pencil size={13} />
      </button>
      <button onClick={() => deleteMutation.mutate()} className="text-slate-300 hover:text-red-500 p-1">
        <Trash2 size={13} />
      </button>
    </div>
  );
}

function TaskRow({ task, initiativeId, krId }: { task: OkrTaskDetail; initiativeId: number; krId: number }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showActionForm, setShowActionForm] = useState(false);
  const [actionTitle, setActionTitle] = useState("");
  const [actionWeight, setActionWeight] = useState(0);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(task.title);
  const [weight, setWeight] = useState(task.weight_percent);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["okr", "initiative-tasks", initiativeId] });
    qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
  };

  const toggleMutation = useMutation({
    mutationFn: () => api.put(`/okr/tasks/${task.id}`, { is_completed: !task.is_completed }),
    onSuccess: invalidate,
  });
  const updateMutation = useMutation({
    mutationFn: () => api.put(`/okr/tasks/${task.id}`, { title, weight_percent: weight }),
    onSuccess: () => {
      invalidate();
      setEditing(false);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/okr/tasks/${task.id}`),
    onSuccess: invalidate,
  });
  const createActionMutation = useMutation({
    mutationFn: () => api.post(`/okr/tasks/${task.id}/actions`, { title: actionTitle, weight_percent: actionWeight }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "initiative-tasks", initiativeId] });
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setShowActionForm(false);
      setActionTitle("");
      setActionWeight(0);
    },
  });

  if (editing) {
    return (
      <div className="pl-4 border-l border-surface-100 dark:border-slate-800 ml-4">
        <div className="flex items-center gap-2 py-1.5">
          <input className="input py-1 text-sm flex-1" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input type="number" className="input py-1 text-sm w-16" value={weight || ""} onChange={(e) => setWeight(Number(e.target.value))} />
          <button onClick={() => updateMutation.mutate()} className="text-status-good p-1">
            <Check size={14} />
          </button>
          <button onClick={() => setEditing(false)} className="text-slate-400 p-1">
            <X size={14} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="pl-4 border-l border-surface-100 dark:border-slate-800 ml-4">
      <div className="flex items-center gap-2 py-1.5 text-sm cursor-pointer" role="button" onClick={() => setExpanded((v) => !v)}>
        <span className="text-slate-400">{expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</span>
        <input
          type="checkbox"
          checked={task.is_completed}
          onClick={(e) => e.stopPropagation()}
          onChange={() => toggleMutation.mutate()}
          className="w-4 h-4 accent-primary-600"
        />
        <span className={clsx("flex-1", task.is_completed && "line-through text-slate-400")}>{task.title}</span>
        {task.actions.length === 0 && <span className="text-xs text-slate-400 tabular-nums">{task.progress_percent}%</span>}
        <span className="text-xs text-slate-400 w-10 text-right tabular-nums">{task.weight_percent}%</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            setEditing(true);
          }}
          className="text-slate-300 hover:text-primary-600 p-1"
        >
          <Pencil size={13} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            deleteMutation.mutate();
          }}
          className="text-slate-300 hover:text-red-500 p-1"
        >
          <Trash2 size={13} />
        </button>
      </div>
      {expanded && (
        <div className="pb-2">
          {task.actions.map((a) => (
            <ActionRow key={a.id} action={a} taskId={task.id} krId={krId} />
          ))}
          {showActionForm ? (
            <div className="flex items-center gap-2 pl-8 py-1">
              <input className="input py-1 text-xs flex-1" placeholder="Nova ação" value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} />
              <input
                type="number"
                className="input py-1 text-xs w-16"
                placeholder="Peso %"
                value={actionWeight || ""}
                onChange={(e) => setActionWeight(Number(e.target.value))}
              />
              <button className="btn-primary py-1 text-xs" disabled={!actionTitle} onClick={() => createActionMutation.mutate()}>
                Add
              </button>
              <button className="btn-secondary py-1 text-xs" onClick={() => setShowActionForm(false)}>
                X
              </button>
            </div>
          ) : (
            <button onClick={() => setShowActionForm(true)} className="ml-8 text-xs text-primary-600 flex items-center gap-1 py-1">
              <Plus size={12} /> Ação
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function InitiativeRow({ initiative, krId }: { initiative: KeyResultDetail["initiatives"][number]; krId: number }) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskWeight, setTaskWeight] = useState(0);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(initiative.title);
  const [weight, setWeight] = useState(initiative.weight_percent);

  const { data: detail } = useQuery<InitiativeDetail>({
    queryKey: ["okr", "initiative-tasks", initiative.id],
    queryFn: () => api.get(`/okr/initiatives/${initiative.id}`).then((r) => r.data),
    enabled: expanded,
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.delete(`/okr/initiatives/${initiative.id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["okr", "kr", krId] }),
  });
  const updateMutation = useMutation({
    mutationFn: () => api.put(`/okr/initiatives/${initiative.id}`, { title, weight_percent: weight }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setEditing(false);
    },
  });
  const createTaskMutation = useMutation({
    mutationFn: () => api.post(`/okr/initiatives/${initiative.id}/tasks`, { title: taskTitle, weight_percent: taskWeight }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "initiative-tasks", initiative.id] });
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setShowTaskForm(false);
      setTaskTitle("");
      setTaskWeight(0);
    },
  });

  if (editing) {
    return (
      <div className="border-b border-surface-100 dark:border-slate-800 last:border-0 py-2">
        <div className="flex items-center gap-2">
          <input className="input py-1 text-sm flex-1" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input type="number" className="input py-1 text-sm w-20" value={weight || ""} onChange={(e) => setWeight(Number(e.target.value))} />
          <button onClick={() => updateMutation.mutate()} className="text-status-good p-1">
            <Check size={15} />
          </button>
          <button onClick={() => setEditing(false)} className="text-slate-400 p-1">
            <X size={15} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-b border-surface-100 dark:border-slate-800 last:border-0 py-2">
      <div
        className="flex items-center gap-2 cursor-pointer"
        role="button"
        onClick={() => setExpanded((v) => !v)}
      >
        <span className="text-slate-400">{expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</span>
        <span className="flex-1 text-sm font-medium text-slate-800 dark:text-slate-100">{initiative.title}</span>
        <span className="text-xs text-slate-400 w-16">Peso {initiative.weight_percent}%</span>
        <span className="text-xs text-slate-400 w-20">Prog. {initiative.progress_percent}%</span>
        <span className="text-xs font-semibold text-primary-600 w-24 text-right">Contrib. {initiative.contribution_percent}%</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            setEditing(true);
          }}
          className="text-slate-300 hover:text-primary-600 p-1"
        >
          <Pencil size={14} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            deleteMutation.mutate();
          }}
          className="text-slate-300 hover:text-red-500 p-1"
        >
          <Trash2 size={14} />
        </button>
      </div>
      {expanded && (
        <div className="mt-1.5">
          {!detail ? (
            <p className="text-xs text-slate-400 pl-4">Carregando...</p>
          ) : (
            detail.tasks.map((t) => <TaskRow key={t.id} task={t} initiativeId={initiative.id} krId={krId} />)
          )}
          {showTaskForm ? (
            <div className="flex items-center gap-2 pl-4 py-1">
              <input className="input py-1 text-xs flex-1" placeholder="Nova tarefa" value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} />
              <input
                type="number"
                className="input py-1 text-xs w-16"
                placeholder="Peso %"
                value={taskWeight || ""}
                onChange={(e) => setTaskWeight(Number(e.target.value))}
              />
              <button className="btn-primary py-1 text-xs" disabled={!taskTitle} onClick={() => createTaskMutation.mutate()}>
                Add
              </button>
              <button className="btn-secondary py-1 text-xs" onClick={() => setShowTaskForm(false)}>
                X
              </button>
            </div>
          ) : (
            <button onClick={() => setShowTaskForm(true)} className="ml-4 text-xs text-primary-600 flex items-center gap-1 py-1">
              <Plus size={12} /> Tarefa
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function KeyResultDetailPage() {
  const params = useParams();
  const router = useRouter();
  const krId = Number(params.krId);
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [showCheckinForm, setShowCheckinForm] = useState(false);
  const [checkin, setCheckin] = useState({ period_start: "", period_end: "", value: 0, comment: "" });
  const [showInitiativeForm, setShowInitiativeForm] = useState(false);
  const [initiativeForm, setInitiativeForm] = useState({ title: "", weight_percent: 0 });
  const [showKrEditForm, setShowKrEditForm] = useState(false);
  const [krForm, setKrForm] = useState({
    code: "",
    title: "",
    indicator_type: "quantity" as IndicatorType,
    direction: "increase" as KRDirection,
    cadence: "weekly" as KRCadence,
    baseline_value: 0,
    target_value: 0,
    owner_id: null as number | null,
  });

  const { data: kr } = useQuery<KeyResultDetail>({
    queryKey: ["okr", "kr", krId],
    queryFn: () => api.get(`/okr/key-results/${krId}`).then((r) => r.data),
    enabled: !!krId,
  });

  const { data: members = EMPTY_MEMBERS } = useQuery<WorkspaceMember[]>({
    queryKey: ["workspace-members", currentWorkspaceId],
    queryFn: () => api.get(`/workspaces/${currentWorkspaceId}/members`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const updateKrMutation = useMutation({
    mutationFn: () => api.put(`/okr/key-results/${krId}`, krForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setShowKrEditForm(false);
    },
  });

  const deleteKrMutation = useMutation({
    mutationFn: () => api.delete(`/okr/key-results/${krId}`),
    onSuccess: () => kr && router.push(`/dashboard/okr/${kr.objective_id}`),
  });

  function openEditKr() {
    if (!kr) return;
    setKrForm({
      code: kr.code,
      title: kr.title,
      indicator_type: kr.indicator_type,
      direction: kr.direction,
      cadence: kr.cadence,
      baseline_value: kr.baseline_value,
      target_value: kr.target_value,
      owner_id: kr.owner_id,
    });
    setShowKrEditForm(true);
  }

  const createCheckinMutation = useMutation({
    mutationFn: () =>
      api.post(`/okr/key-results/${krId}/checkins`, {
        period_start: new Date(checkin.period_start).toISOString(),
        period_end: new Date(checkin.period_end).toISOString(),
        value: checkin.value,
        comment: checkin.comment || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setShowCheckinForm(false);
      setCheckin({ period_start: "", period_end: "", value: 0, comment: "" });
    },
  });

  const createInitiativeMutation = useMutation({
    mutationFn: () => api.post(`/okr/key-results/${krId}/initiatives`, initiativeForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["okr", "kr", krId] });
      setShowInitiativeForm(false);
      setInitiativeForm({ title: "", weight_percent: 0 });
    },
  });

  if (!kr) return <p className="text-slate-400 text-sm p-4">Carregando...</p>;

  const TrendIcon = TREND_ICON[kr.trend_direction];
  const isFormReady = !!checkin.period_start && !!checkin.period_end;
  const weightSum = kr.initiatives.reduce((s, i) => s + i.weight_percent, 0);

  return (
    <div>
      <Link href={`/dashboard/okr/${kr.objective_id}`} className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 mb-3">
        <ArrowLeft size={15} /> Voltar ao objetivo
      </Link>

      <div className="mb-5 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Target size={20} className="text-primary-600" /> {kr.code} — {kr.title}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {INDICATOR_TYPE_LABELS[kr.indicator_type]} · Cadência {KR_CADENCE_LABELS[kr.cadence]} · Responsável:{" "}
            {members.find((m) => m.user_id === kr.owner_id)?.full_name ?? "sem responsável"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={openEditKr} className="text-slate-400 hover:text-primary-600 p-2">
            <Pencil size={16} />
          </button>
          <button onClick={() => deleteKrMutation.mutate()} className="text-slate-400 hover:text-red-500 p-2">
            <Trash2 size={16} />
          </button>
          <button className="btn-primary flex items-center gap-1.5 text-sm" onClick={() => setShowCheckinForm(true)}>
            <Plus size={14} /> Lançamento
          </button>
        </div>
      </div>

      {showKrEditForm && (
        <div className="card p-4 mb-6">
          <h3 className="font-semibold mb-3 text-sm text-slate-900 dark:text-white">Editar KR</h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            <input className="input" placeholder="Código (ex: 8.1)" value={krForm.code} onChange={(e) => setKrForm((p) => ({ ...p, code: e.target.value }))} />
            <input className="input lg:col-span-2" placeholder="Título do KR" value={krForm.title} onChange={(e) => setKrForm((p) => ({ ...p, title: e.target.value }))} />
            <select className="input" value={krForm.indicator_type} onChange={(e) => setKrForm((p) => ({ ...p, indicator_type: e.target.value as IndicatorType }))}>
              {Object.entries(INDICATOR_TYPE_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <select className="input" value={krForm.direction} onChange={(e) => setKrForm((p) => ({ ...p, direction: e.target.value as KRDirection }))}>
              <option value="increase">Quanto maior, melhor</option>
              <option value="decrease">Quanto menor, melhor</option>
            </select>
            <select className="input" value={krForm.cadence} onChange={(e) => setKrForm((p) => ({ ...p, cadence: e.target.value as KRCadence }))}>
              {Object.entries(KR_CADENCE_LABELS).map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <input
              type="number"
              className="input"
              placeholder="Valor inicial (baseline)"
              value={krForm.baseline_value || ""}
              onChange={(e) => setKrForm((p) => ({ ...p, baseline_value: Number(e.target.value) }))}
            />
            <input
              type="number"
              className="input"
              placeholder="Meta"
              value={krForm.target_value || ""}
              onChange={(e) => setKrForm((p) => ({ ...p, target_value: Number(e.target.value) }))}
            />
            <select
              className="input"
              value={krForm.owner_id ?? ""}
              onChange={(e) => setKrForm((p) => ({ ...p, owner_id: e.target.value ? Number(e.target.value) : null }))}
            >
              <option value="">Sem responsável</option>
              {members.map((m) => (
                <option key={m.user_id} value={m.user_id}>{m.full_name}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="btn-primary" disabled={updateKrMutation.isPending} onClick={() => updateKrMutation.mutate()}>
              {updateKrMutation.isPending ? "Salvando..." : "Salvar"}
            </button>
            <button className="btn-secondary" onClick={() => setShowKrEditForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      {showCheckinForm && (
        <div className="card p-4 mb-6">
          <h3 className="font-semibold mb-3 text-sm text-slate-900 dark:text-white">Novo Lançamento</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Início do período</label>
              <input type="date" className="input" value={checkin.period_start} onChange={(e) => setCheckin((p) => ({ ...p, period_start: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Fim do período</label>
              <input type="date" className="input" value={checkin.period_end} onChange={(e) => setCheckin((p) => ({ ...p, period_end: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Resultado</label>
              <input type="number" className="input" value={checkin.value || ""} onChange={(e) => setCheckin((p) => ({ ...p, value: Number(e.target.value) }))} />
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Comentário (opcional)</label>
              <input className="input" value={checkin.comment} onChange={(e) => setCheckin((p) => ({ ...p, comment: e.target.value }))} />
            </div>
          </div>
          <div className="flex gap-2 mt-3">
            <button className="btn-primary" disabled={!isFormReady || createCheckinMutation.isPending} onClick={() => createCheckinMutation.mutate()}>
              {createCheckinMutation.isPending ? "Salvando..." : "Salvar"}
            </button>
            <button className="btn-secondary" onClick={() => setShowCheckinForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <StatTile label="Meta" value={kr.target_value} tone="neutral" />
        <StatTile label="Resultado Atual" value={kr.current_value ?? "—"} tone="neutral" />
        <StatTile label="Progresso" value={`${kr.progress_percent}%`} tone={kr.progress_percent >= 80 ? "good" : kr.progress_percent >= 50 ? "warning" : "critical"} />
        <StatTile label="Score" value={kr.score} tone="neutral" />
      </div>

      <div className="card p-4 mb-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Resultado Anterior</p>
            <p className="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{kr.previous_value ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Comparativo</p>
            <p className={clsx("font-semibold tabular-nums", kr.trend_label === "positive" ? "text-status-good" : kr.trend_label === "negative" ? "text-status-critical" : "text-slate-500")}>
              {kr.variation_pct !== null ? `${kr.variation_pct > 0 ? "+" : ""}${kr.variation_pct}%` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Diferença Meta</p>
            <p className="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{kr.gap_to_target !== null ? (kr.gap_to_target > 0 ? `+${kr.gap_to_target}` : kr.gap_to_target) : "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Média até hoje</p>
            <p className="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{kr.average_to_date ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Melhor Resultado</p>
            <p className="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{kr.best_value ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Pior Resultado</p>
            <p className="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{kr.worst_value ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Tendência</p>
            <p className={clsx("font-semibold flex items-center gap-1", kr.trend_label === "positive" ? "text-status-good" : kr.trend_label === "negative" ? "text-status-critical" : "text-slate-500")}>
              <TrendIcon size={15} /> {kr.trend_label === "positive" ? "Positiva" : kr.trend_label === "negative" ? "Negativa" : "Estável"}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Previsão de Fechamento</p>
            <p className={clsx("font-semibold tabular-nums", kr.forecast_hits_target === true ? "text-status-good" : kr.forecast_hits_target === false ? "text-status-critical" : "text-slate-500")}>
              {kr.forecast_value ?? "—"}
            </p>
          </div>
        </div>
      </div>

      {kr.history.length > 0 && (
        <div className="card p-4 mb-6">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Histórico</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={kr.history} margin={{ left: 8, right: 16, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" />
              <XAxis dataKey="period_label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="value" name="Resultado" stroke="#2a78d6" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="target" name="Meta" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="5 4" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card">
        <div className="panel-header">
          <span className="font-semibold text-slate-900 dark:text-white">
            Iniciativas {kr.initiatives.length > 0 && <span className="text-slate-400 font-normal text-sm">(soma dos pesos: {weightSum}%)</span>}
          </span>
          <button className="btn-secondary flex items-center gap-1.5 py-1.5 text-sm" onClick={() => setShowInitiativeForm(true)}>
            <Plus size={14} /> Iniciativa
          </button>
        </div>

        {showInitiativeForm && (
          <div className="p-4 border-b border-surface-100 dark:border-slate-800 flex items-center gap-2">
            <input
              className="input flex-1"
              placeholder="Título da iniciativa"
              value={initiativeForm.title}
              onChange={(e) => setInitiativeForm((p) => ({ ...p, title: e.target.value }))}
            />
            <input
              type="number"
              className="input w-24"
              placeholder="Peso %"
              value={initiativeForm.weight_percent || ""}
              onChange={(e) => setInitiativeForm((p) => ({ ...p, weight_percent: Number(e.target.value) }))}
            />
            <button className="btn-primary" disabled={!initiativeForm.title} onClick={() => createInitiativeMutation.mutate()}>
              Add
            </button>
            <button className="btn-secondary" onClick={() => setShowInitiativeForm(false)}>
              Cancelar
            </button>
          </div>
        )}

        {kr.initiatives.length === 0 ? (
          <p className="text-slate-400 text-sm p-4">Nenhuma iniciativa cadastrada ainda.</p>
        ) : (
          <div className="px-4">
            {kr.initiatives.map((i) => (
              <InitiativeRow key={i.id} initiative={i} krId={krId} />
            ))}
            <div className="flex items-center justify-end py-2 text-sm">
              <span className="text-slate-400 mr-2">Resultado da iniciativa</span>
              <span className="font-bold text-primary-600">{kr.initiatives_rollup_percent}%</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
