"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Camera, Download, X } from "lucide-react";
import { format } from "date-fns";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { GanttChart } from "@/components/gantt/GanttChart";
import { PertChart } from "@/components/gantt/PertChart";
import { DependencyPopover } from "@/components/gantt/DependencyPopover";
import { TaskDetailModal } from "@/components/tasks/TaskDetailModal";
import { QuickAddTaskModal } from "@/components/tasks/QuickAddTaskModal";
import type { GanttData, DependencyType, DependencyHardness, Project, GanttBaselineSummary, GanttBaseline } from "@/lib/types";

const EMPTY_PROJECTS: Project[] = [];
const EMPTY_BASELINES: GanttBaselineSummary[] = [];

export default function GanttPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [selectedDep, setSelectedDep] = useState<{ id: number; x: number; y: number } | null>(null);
  const [view, setView] = useState<"gantt" | "pert">("gantt");
  const [baselineId, setBaselineId] = useState<number | "">("");
  const [showBaselineForm, setShowBaselineForm] = useState(false);
  const [baselineName, setBaselineName] = useState("");

  const { data: projects = EMPTY_PROJECTS } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  useEffect(() => {
    setProjectId(null);
  }, [currentWorkspaceId]);

  useEffect(() => {
    if (!projectId && projects.length > 0) setProjectId(projects[0].id);
  }, [projects, projectId]);

  const { data: gantt } = useQuery<GanttData>({
    queryKey: ["gantt", projectId],
    queryFn: () => api.get(`/projects/${projectId}/gantt`).then((r) => r.data),
    enabled: !!projectId,
  });

  useEffect(() => {
    setBaselineId("");
  }, [projectId]);

  const { data: baselines = EMPTY_BASELINES } = useQuery<GanttBaselineSummary[]>({
    queryKey: ["baselines", projectId],
    queryFn: () => api.get(`/projects/${projectId}/baselines`).then((r) => r.data),
    enabled: !!projectId,
  });

  const { data: activeBaseline } = useQuery<GanttBaseline>({
    queryKey: ["baseline", projectId, baselineId],
    queryFn: () => api.get(`/projects/${projectId}/baselines/${baselineId}`).then((r) => r.data),
    enabled: !!projectId && baselineId !== "",
  });

  const invalidateGantt = () => qc.invalidateQueries({ queryKey: ["gantt", projectId] });

  const createBaselineMutation = useMutation({
    mutationFn: (name: string) => api.post(`/projects/${projectId}/baselines`, { name }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["baselines", projectId] });
      setShowBaselineForm(false);
      setBaselineName("");
      setBaselineId(res.data.id);
    },
  });

  const deleteBaselineMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/projects/${projectId}/baselines/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["baselines", projectId] });
      setBaselineId("");
    },
  });

  const handleExportCsv = async () => {
    const res = await api.get(`/projects/${projectId}/gantt/export.csv`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `gantt-projeto-${projectId}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, start_date, due_date }: { id: number; start_date: string; due_date: string }) =>
      api.put(`/tasks/${id}`, { start_date, due_date }),
    onSuccess: invalidateGantt,
  });

  const createDependencyMutation = useMutation({
    mutationFn: ({ taskId, dependsOnId }: { taskId: number; dependsOnId: number }) =>
      api.post(`/tasks/${taskId}/dependencies`, { depends_on_id: dependsOnId }),
    onSuccess: invalidateGantt,
  });

  const updateDependencyMutation = useMutation({
    mutationFn: ({
      taskId,
      depId,
      data,
    }: {
      taskId: number;
      depId: number;
      data: { dependency_type?: DependencyType; lag_days?: number; hardness?: DependencyHardness };
    }) => api.put(`/tasks/${taskId}/dependencies/${depId}`, data),
    onSuccess: invalidateGantt,
  });

  const deleteDependencyMutation = useMutation({
    mutationFn: ({ taskId, depId }: { taskId: number; depId: number }) =>
      api.delete(`/tasks/${taskId}/dependencies/${depId}`),
    onSuccess: () => {
      invalidateGantt();
      setSelectedDep(null);
    },
  });

  const selectedDependency = selectedDep && gantt ? gantt.dependencies.find((d) => d.id === selectedDep.id) : undefined;

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Gantt</h1>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-surface-200 dark:border-slate-700 overflow-hidden text-sm">
            <button
              className={clsx("px-3 py-1.5", view === "gantt" ? "bg-primary-600 text-white" : "text-slate-500 hover:bg-surface-50 hover:dark:bg-surface-800")}
              onClick={() => setView("gantt")}
            >
              Gantt
            </button>
            <button
              className={clsx("px-3 py-1.5", view === "pert" ? "bg-primary-600 text-white" : "text-slate-500 hover:bg-surface-50 hover:dark:bg-surface-800")}
              onClick={() => setView("pert")}
            >
              PERT
            </button>
          </div>
          <select
            className="input w-56"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(Number(e.target.value))}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {projectId && (
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2 text-sm">
          <div className="flex items-center gap-2">
            <select
              className="input w-56 py-1.5"
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Sem baseline</option>
              {baselines.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({format(new Date(b.created_at), "dd/MM/yy")})
                </option>
              ))}
            </select>
            {baselineId !== "" && (
              <button
                className="p-1.5 rounded hover:bg-surface-100 text-slate-400 hover:text-red-500"
                title="Excluir baseline"
                onClick={() => deleteBaselineMutation.mutate(baselineId as number)}
              >
                <X size={14} />
              </button>
            )}
            {!showBaselineForm ? (
              <button
                className="btn-secondary flex items-center gap-1.5 py-1.5"
                onClick={() => setShowBaselineForm(true)}
              >
                <Camera size={14} /> Salvar baseline
              </button>
            ) : (
              <>
                <input
                  className="input py-1.5 w-44"
                  placeholder="Nome da baseline"
                  value={baselineName}
                  onChange={(e) => setBaselineName(e.target.value)}
                  autoFocus
                />
                <button
                  className="btn-primary py-1.5"
                  disabled={!baselineName || createBaselineMutation.isPending}
                  onClick={() => createBaselineMutation.mutate(baselineName)}
                >
                  Salvar
                </button>
                <button className="btn-secondary py-1.5" onClick={() => setShowBaselineForm(false)}>
                  Cancelar
                </button>
              </>
            )}
          </div>
          <button className="btn-secondary flex items-center gap-1.5 py-1.5" onClick={handleExportCsv}>
            <Download size={14} /> Exportar CSV
          </button>
        </div>
      )}

      {!projectId ? (
        <p className="text-slate-400">Crie um projeto para usar o Gantt.</p>
      ) : !gantt ? (
        <p className="text-slate-400">Carregando...</p>
      ) : gantt.tasks.length === 0 ? (
        <div className="card p-10 text-center text-slate-400">
          <p>Nenhuma tarefa neste projeto ainda.</p>
          <button className="btn-primary mt-4" onClick={() => setShowQuickAdd(true)}>
            Criar tarefa
          </button>
        </div>
      ) : view === "pert" ? (
        <PertChart
          tasks={gantt.tasks}
          dependencies={gantt.dependencies}
          criticalTaskIds={gantt.critical_task_ids}
          onTaskClick={setSelectedTaskId}
        />
      ) : (
        <GanttChart
          tasks={gantt.tasks}
          dependencies={gantt.dependencies}
          criticalTaskIds={gantt.critical_task_ids}
          baselineTasks={activeBaseline?.tasks}
          onTaskClick={setSelectedTaskId}
          onReschedule={(id, start, due) =>
            rescheduleMutation.mutate({ id, start_date: start.toISOString(), due_date: due.toISOString() })
          }
          onCreateDependency={(taskId, dependsOnId) => createDependencyMutation.mutate({ taskId, dependsOnId })}
          onSelectDependency={(dep, x, y) => setSelectedDep({ id: dep.id, x, y })}
          onAddTask={() => setShowQuickAdd(true)}
        />
      )}

      {selectedTaskId && (
        <TaskDetailModal
          taskId={selectedTaskId}
          onClose={() => {
            setSelectedTaskId(null);
            invalidateGantt();
          }}
        />
      )}

      {showQuickAdd && (
        <QuickAddTaskModal
          projects={projects}
          defaultProjectId={projectId}
          onClose={() => {
            setShowQuickAdd(false);
            invalidateGantt();
          }}
        />
      )}

      {selectedDep && selectedDependency && (
        <DependencyPopover
          dependency={selectedDependency}
          x={selectedDep.x}
          y={selectedDep.y}
          onUpdate={(data) =>
            updateDependencyMutation.mutate({ taskId: selectedDependency.task_id, depId: selectedDependency.id, data })
          }
          onDelete={() =>
            deleteDependencyMutation.mutate({ taskId: selectedDependency.task_id, depId: selectedDependency.id })
          }
          onClose={() => setSelectedDep(null)}
        />
      )}
    </div>
  );
}
