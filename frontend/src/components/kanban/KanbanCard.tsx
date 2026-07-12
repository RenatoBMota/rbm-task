"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { clsx } from "clsx";
import { CheckSquare } from "lucide-react";
import { PRIORITY_COLORS } from "@/lib/types";
import type { Task } from "@/lib/types";

export function KanbanCard({ task, onClick }: { task: Task; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="card p-3 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex items-center justify-between mb-2">
        <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full border", PRIORITY_COLORS[task.priority])}>
          {task.priority}
        </span>
      </div>
      <p className="text-sm text-slate-800 leading-snug">{task.title}</p>
      {task.due_date && (
        <p className="text-xs text-slate-400 mt-2">
          {new Date(task.due_date).toLocaleDateString("pt-BR")}
        </p>
      )}
      <div className="flex items-center gap-3 mt-2 text-slate-400">
        {task.subtask_count > 0 && (
          <span className="text-xs flex items-center gap-1">
            <CheckSquare size={12} /> {task.subtask_count}
          </span>
        )}
      </div>
    </div>
  );
}
