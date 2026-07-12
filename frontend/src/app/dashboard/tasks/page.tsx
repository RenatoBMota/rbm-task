"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, CheckCircle2, Circle, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { clsx } from "clsx";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { QuickAddTaskModal } from "@/components/tasks/QuickAddTaskModal";
import { TaskDetailModal } from "@/components/tasks/TaskDetailModal";
import type { Project } from "@/lib/types";

interface Task {
  id: number;
  title: string;
  description: string | null;
  priority: "P1" | "P2" | "P3" | "P4";
  status: string;
  due_date: string | null;
  is_completed: boolean;
  project_id: number | null;
}

const EMPTY_PROJECTS: Project[] = [];

const priorityColors: Record<string, string> = {
  P1: "bg-red-100 text-red-700 border-red-200",
  P2: "bg-orange-100 text-orange-700 border-orange-200",
  P3: "bg-blue-100 text-blue-700 border-blue-200",
  P4: "bg-slate-100 text-slate-600 dark:text-slate-400 border-slate-200",
};

export default function TasksPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const { currentWorkspaceId } = useWorkspaces();

  const { data: projects = EMPTY_PROJECTS } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: tasks = [], isLoading } = useQuery<Task[]>({
    queryKey: ["tasks", currentWorkspaceId],
    queryFn: () => api.get("/tasks", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_completed }: { id: number; is_completed: boolean }) =>
      api.put(`/tasks/${id}`, { is_completed }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/tasks/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const pending = tasks.filter((t) => !t.is_completed);
  const completed = tasks.filter((t) => t.is_completed);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Tarefas</h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowModal(true)}>
          <Plus size={18} /> Nova Tarefa
        </button>
      </div>

      {showModal && (
        <QuickAddTaskModal
          projects={projects}
          onClose={() => {
            setShowModal(false);
            qc.invalidateQueries({ queryKey: ["tasks"] });
          }}
        />
      )}

      {isLoading ? (
        <p className="text-slate-400">Carregando...</p>
      ) : (
        <div className="space-y-6">
          <TaskGroup
            title={`Pendentes (${pending.length})`}
            tasks={pending}
            onToggle={(id) => toggleMutation.mutate({ id, is_completed: true })}
            onDelete={(id) => deleteMutation.mutate(id)}
            onSelect={setSelectedTaskId}
          />
          {completed.length > 0 && (
            <TaskGroup
              title={`Concluídas (${completed.length})`}
              tasks={completed}
              onToggle={(id) => toggleMutation.mutate({ id, is_completed: false })}
              onDelete={(id) => deleteMutation.mutate(id)}
              onSelect={setSelectedTaskId}
              dimmed
            />
          )}
        </div>
      )}

      {selectedTaskId && (
        <TaskDetailModal taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      )}
    </div>
  );
}

function TaskGroup({
  title,
  tasks,
  onToggle,
  onDelete,
  onSelect,
  dimmed,
}: {
  title: string;
  tasks: Task[];
  onToggle: (id: number) => void;
  onDelete: (id: number) => void;
  onSelect: (id: number) => void;
  dimmed?: boolean;
}) {
  return (
    <div>
      <h2 className={clsx("text-sm font-semibold mb-3", dimmed ? "text-slate-400" : "text-slate-700 dark:text-slate-300")}>
        {title}
      </h2>
      <div className="space-y-2">
        {tasks.map((t) => (
          <div
            key={t.id}
            onClick={() => onSelect(t.id)}
            className={clsx(
              "card flex items-center gap-3 px-4 py-3 transition-all cursor-pointer hover:border-primary-200",
              dimmed && "opacity-60"
            )}
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggle(t.id);
              }}
              className="text-slate-400 hover:text-primary-600 transition-colors flex-shrink-0"
            >
              {t.is_completed ? (
                <CheckCircle2 size={20} className="text-green-500" />
              ) : (
                <Circle size={20} />
              )}
            </button>
            <span
              className={clsx(
                "text-xs font-medium px-2 py-0.5 rounded-full border",
                priorityColors[t.priority]
              )}
            >
              {t.priority}
            </span>
            <span className={clsx("flex-1 text-sm", t.is_completed && "line-through text-slate-400")}>
              {t.title}
            </span>
            {t.project_id === null && (
              <span className="text-xs font-normal px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 flex-shrink-0">
                📅 Agenda diária
              </span>
            )}
            {t.due_date && (
              <span className="text-xs text-slate-400">
                {new Date(t.due_date).toLocaleDateString("pt-BR")}
              </span>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(t.id);
              }}
              className="text-slate-300 hover:text-red-500 transition-colors p-1"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
