"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  startOfMonth,
  endOfMonth,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  format,
  isSameMonth,
  isSameDay,
  addMonths,
  subMonths,
} from "date-fns";
import { ptBR } from "date-fns/locale";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { PRIORITY_COLORS } from "@/lib/types";
import type { Task } from "@/lib/types";
import { TaskDetailModal } from "@/components/tasks/TaskDetailModal";
import { useWorkspaces } from "@/hooks/useWorkspaces";

const WEEKDAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

export default function CalendarPage() {
  const [cursor, setCursor] = useState(new Date());
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const { currentWorkspaceId } = useWorkspaces();

  const { data: tasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks", "calendar", currentWorkspaceId],
    queryFn: () =>
      api.get("/tasks", { params: { limit: 500, workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const monthStart = startOfMonth(cursor);
  const gridStart = startOfWeek(monthStart);
  const gridEnd = endOfWeek(endOfMonth(cursor));
  const days = eachDayOfInterval({ start: gridStart, end: gridEnd });

  const tasksForDay = (day: Date) =>
    tasks.filter((t) => t.due_date && isSameDay(new Date(t.due_date), day));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Calendário</h1>
        <div className="flex items-center gap-3">
          <button className="btn-secondary p-2" onClick={() => setCursor((d) => subMonths(d, 1))}>
            <ChevronLeft size={16} />
          </button>
          <span className="font-medium text-slate-700 dark:text-slate-300 w-36 text-center capitalize">
            {format(cursor, "MMMM yyyy", { locale: ptBR })}
          </span>
          <button className="btn-secondary p-2" onClick={() => setCursor((d) => addMonths(d, 1))}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="grid grid-cols-7 border-b border-surface-200 dark:border-slate-700">
          {WEEKDAYS.map((day) => (
            <div key={day} className="text-xs font-semibold text-slate-500 text-center py-2">
              {day}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {days.map((day) => {
            const dayTasks = tasksForDay(day);
            return (
              <div
                key={day.toISOString()}
                className={clsx(
                  "min-h-[110px] border-b border-r border-surface-100 dark:border-slate-800 p-2",
                  !isSameMonth(day, cursor) && "bg-surface-50 dark:bg-surface-800"
                )}
              >
                <span
                  className={clsx(
                    "text-xs font-medium",
                    isSameDay(day, new Date()) ? "text-primary-600" : "text-slate-400",
                    !isSameMonth(day, cursor) && "text-slate-300"
                  )}
                >
                  {format(day, "d")}
                </span>
                <div className="space-y-1 mt-1">
                  {dayTasks.slice(0, 3).map((task) => (
                    <button
                      key={task.id}
                      onClick={() => setSelectedTaskId(task.id)}
                      className={clsx(
                        "block w-full text-left text-xs px-1.5 py-0.5 rounded border truncate",
                        PRIORITY_COLORS[task.priority]
                      )}
                    >
                      {task.title}
                    </button>
                  ))}
                  {dayTasks.length > 3 && (
                    <span className="text-xs text-slate-400">+{dayTasks.length - 3} mais</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {selectedTaskId && (
        <TaskDetailModal taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      )}
    </div>
  );
}
