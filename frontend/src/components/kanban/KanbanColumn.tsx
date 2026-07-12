"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Plus } from "lucide-react";
import { clsx } from "clsx";
import { KanbanCard } from "./KanbanCard";
import type { Task, TaskStatus } from "@/lib/types";

const WIP_LIMIT = 8;

export function KanbanColumn({
  status,
  label,
  tasks,
  onCardClick,
  onAddClick,
}: {
  status: TaskStatus;
  label: string;
  tasks: Task[];
  onCardClick: (taskId: number) => void;
  onAddClick: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const overLimit = tasks.length > WIP_LIMIT;

  return (
    <div className="flex flex-col w-72 flex-shrink-0">
      <div className="flex items-center justify-between mb-3 px-1">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{label}</h3>
        <span
          className={clsx(
            "text-xs font-medium px-2 py-0.5 rounded-full",
            overLimit ? "bg-red-100 text-red-600" : "bg-surface-100 text-slate-500"
          )}
        >
          {tasks.length}
        </span>
      </div>
      <div
        ref={setNodeRef}
        className={clsx(
          "flex-1 space-y-2 min-h-[120px] rounded-lg p-2 transition-colors",
          isOver ? "bg-primary-50" : "bg-transparent"
        )}
      >
        <SortableContext items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map((task) => (
            <KanbanCard key={task.id} task={task} onClick={() => onCardClick(task.id)} />
          ))}
        </SortableContext>
      </div>
      <button
        onClick={onAddClick}
        className="mt-2 flex items-center gap-1.5 text-xs text-slate-400 hover:text-primary-600 hover:bg-surface-50 hover:dark:bg-surface-800 px-2 py-1.5 rounded-md w-full transition-colors"
      >
        <Plus size={14} /> Adicionar tarefa
      </button>
    </div>
  );
}
