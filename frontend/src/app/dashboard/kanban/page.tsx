"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { Plus } from "lucide-react";
import api from "@/lib/api";
import { TASK_STATUSES } from "@/lib/types";
import type { Task, TaskStatus, Project } from "@/lib/types";
import { KanbanColumn } from "@/components/kanban/KanbanColumn";
import { KanbanCard } from "@/components/kanban/KanbanCard";
import { TaskDetailModal } from "@/components/tasks/TaskDetailModal";
import { QuickAddTaskModal } from "@/components/tasks/QuickAddTaskModal";
import { useWorkspaces } from "@/hooks/useWorkspaces";

const EMPTY_PROJECTS: Project[] = [];
const EMPTY_TASKS: Task[] = [];

function groupByStatus(tasks: Task[]): Record<TaskStatus, Task[]> {
  const grouped = Object.fromEntries(TASK_STATUSES.map((s) => [s.value, [] as Task[]])) as Record<
    TaskStatus,
    Task[]
  >;
  for (const task of tasks) {
    grouped[task.status]?.push(task);
  }
  for (const status of Object.keys(grouped) as TaskStatus[]) {
    grouped[status].sort((a, b) => a.position - b.position);
  }
  return grouped;
}

const AGENDA = "agenda" as const;
type BoardSelection = number | typeof AGENDA | null;

export default function KanbanPage() {
  const qc = useQueryClient();
  const [projectId, setProjectId] = useState<BoardSelection>(null);
  const [columns, setColumns] = useState<Record<TaskStatus, Task[]>>(groupByStatus([]));
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [quickAddStatus, setQuickAddStatus] = useState<TaskStatus | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const { currentWorkspaceId } = useWorkspaces();

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

  const { data: tasks = EMPTY_TASKS } = useQuery<Task[]>({
    queryKey: ["tasks", "board", projectId],
    queryFn: () =>
      api
        .get("/tasks/board", { params: projectId === AGENDA ? {} : { project_id: projectId } })
        .then((r) => r.data),
    enabled: projectId !== null,
  });

  useEffect(() => {
    setColumns(groupByStatus(tasks));
  }, [tasks]);

  const moveMutation = useMutation({
    mutationFn: ({ id, status, position }: { id: number; status: TaskStatus; position: number }) =>
      api.patch(`/tasks/${id}/move`, { status, position }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks", "board", projectId] }),
  });

  const findColumnOf = (id: number | string): TaskStatus | undefined => {
    return (Object.keys(columns) as TaskStatus[]).find((status) =>
      columns[status].some((t) => t.id === id)
    );
  };

  const handleDragStart = (event: DragStartEvent) => {
    const task = tasks.find((t) => t.id === event.active.id);
    setActiveTask(task ?? null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);
    if (!over) return;

    const activeId = active.id as number;
    const sourceStatus = findColumnOf(activeId);
    if (!sourceStatus) return;

    const isOverColumn = TASK_STATUSES.some((s) => s.value === over.id);
    const targetStatus = isOverColumn ? (over.id as TaskStatus) : findColumnOf(over.id as number);
    if (!targetStatus) return;

    const sourceItems = [...columns[sourceStatus]];
    const activeIndex = sourceItems.findIndex((t) => t.id === activeId);
    const [movedTask] = sourceItems.splice(activeIndex, 1);

    const targetItems = sourceStatus === targetStatus ? sourceItems : [...columns[targetStatus]];
    const overIndex = isOverColumn
      ? targetItems.length
      : targetItems.findIndex((t) => t.id === over.id);
    const insertIndex = overIndex === -1 ? targetItems.length : overIndex;
    targetItems.splice(insertIndex, 0, { ...movedTask, status: targetStatus });

    setColumns((prev) => ({
      ...prev,
      [sourceStatus]: sourceStatus === targetStatus ? targetItems : sourceItems,
      [targetStatus]: targetItems,
    }));

    moveMutation.mutate({ id: activeId, status: targetStatus, position: insertIndex });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Kanban</h1>
        <div className="flex items-center gap-3">
          <select
            className="input w-56"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value === AGENDA ? AGENDA : Number(e.target.value))}
          >
            <option value={AGENDA}>📅 Agenda diária (sem projeto)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {projectId !== null && (
            <button
              className="btn-primary flex items-center gap-2"
              onClick={() => setQuickAddStatus("todo")}
            >
              <Plus size={18} /> Nova Tarefa
            </button>
          )}
        </div>
      </div>

      {projectId === null ? (
        <p className="text-slate-400">Selecione um projeto ou a Agenda diária para usar o quadro Kanban.</p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 overflow-x-auto pb-4">
            {TASK_STATUSES.map(({ value, label }) => (
              <KanbanColumn
                key={value}
                status={value}
                label={label}
                tasks={columns[value]}
                onCardClick={setSelectedTaskId}
                onAddClick={() => setQuickAddStatus(value)}
              />
            ))}
          </div>
          <DragOverlay>
            {activeTask && <KanbanCard task={activeTask} onClick={() => {}} />}
          </DragOverlay>
        </DndContext>
      )}

      {selectedTaskId && (
        <TaskDetailModal taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      )}

      {quickAddStatus && (
        <QuickAddTaskModal
          projects={projects}
          defaultProjectId={typeof projectId === "number" ? projectId : null}
          defaultStatus={quickAddStatus}
          onClose={() => setQuickAddStatus(null)}
        />
      )}
    </div>
  );
}
