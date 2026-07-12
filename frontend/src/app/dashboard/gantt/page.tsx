"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { GanttChart } from "@/components/gantt/GanttChart";
import { DependencyPopover } from "@/components/gantt/DependencyPopover";
import { TaskDetailModal } from "@/components/tasks/TaskDetailModal";
import { QuickAddTaskModal } from "@/components/tasks/QuickAddTaskModal";
import type { GanttData, DependencyType, DependencyHardness, Project } from "@/lib/types";

const EMPTY_PROJECTS: Project[] = [];

export default function GanttPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [selectedDep, setSelectedDep] = useState<{ id: number; x: number; y: number } | null>(null);

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

  const invalidateGantt = () => qc.invalidateQueries({ queryKey: ["gantt", projectId] });

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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Gantt</h1>
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
      ) : (
        <GanttChart
          tasks={gantt.tasks}
          dependencies={gantt.dependencies}
          criticalTaskIds={gantt.critical_task_ids}
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
