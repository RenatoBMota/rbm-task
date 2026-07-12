"use client";

import { useMemo } from "react";
import { format } from "date-fns";
import { clsx } from "clsx";
import { PRIORITY_COLORS } from "@/lib/types";
import type { Task, GanttDependency } from "@/lib/types";

const NODE_W = 190;
const NODE_H = 76;
const COL_GAP = 90;
const ROW_GAP = 24;

function computeLevels(tasks: Task[], dependencies: GanttDependency[]): Map<number, number> {
  const ids = new Set(tasks.map((t) => t.id));
  const predecessors = new Map<number, number[]>();
  for (const t of tasks) predecessors.set(t.id, []);
  for (const d of dependencies) {
    if (!predecessors.has(d.task_id)) predecessors.set(d.task_id, []);
    predecessors.get(d.task_id)!.push(d.depends_on_id);
  }

  const level = new Map<number, number>();
  const visiting = new Set<number>();
  function computeLevel(id: number): number {
    if (level.has(id)) return level.get(id)!;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const preds = (predecessors.get(id) ?? []).filter((p) => ids.has(p));
    const lvl = preds.length === 0 ? 0 : Math.max(...preds.map(computeLevel)) + 1;
    visiting.delete(id);
    level.set(id, lvl);
    return lvl;
  }
  for (const t of tasks) computeLevel(t.id);
  return level;
}

export function PertChart({
  tasks,
  dependencies,
  criticalTaskIds,
  onTaskClick,
}: {
  tasks: Task[];
  dependencies: GanttDependency[];
  criticalTaskIds: number[];
  onTaskClick: (taskId: number) => void;
}) {
  const criticalSet = useMemo(() => new Set(criticalTaskIds), [criticalTaskIds]);
  const parentIds = useMemo(() => new Set(tasks.filter((t) => t.parent_id != null).map((t) => t.parent_id!)), [tasks]);

  const { positions, columns, width, height } = useMemo(() => {
    const levels = computeLevels(tasks, dependencies);
    const byLevel = new Map<number, Task[]>();
    for (const t of tasks) {
      const lvl = levels.get(t.id) ?? 0;
      if (!byLevel.has(lvl)) byLevel.set(lvl, []);
      byLevel.get(lvl)!.push(t);
    }
    const cols = [...byLevel.keys()].sort((a, b) => a - b);
    const pos = new Map<number, { x: number; y: number }>();
    let maxRows = 0;
    for (const col of cols) {
      const items = byLevel.get(col)!;
      items.sort((a, b) => a.position - b.position);
      maxRows = Math.max(maxRows, items.length);
      items.forEach((t, i) => {
        pos.set(t.id, { x: col * (NODE_W + COL_GAP), y: i * (NODE_H + ROW_GAP) });
      });
    }
    return {
      positions: pos,
      columns: cols.length,
      width: cols.length * (NODE_W + COL_GAP),
      height: Math.max(maxRows * (NODE_H + ROW_GAP), NODE_H),
    };
  }, [tasks, dependencies]);

  const edges = useMemo(() => {
    return dependencies
      .map((dep) => {
        const from = positions.get(dep.depends_on_id);
        const to = positions.get(dep.task_id);
        if (!from || !to) return null;
        const sourceX = from.x + NODE_W;
        const sourceY = from.y + NODE_H / 2;
        const targetX = to.x;
        const targetY = to.y + NODE_H / 2;
        const midX = (sourceX + targetX) / 2;
        const isCritical = criticalSet.has(dep.task_id) && criticalSet.has(dep.depends_on_id);
        return {
          id: dep.id,
          d: `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`,
          isCritical,
        };
      })
      .filter((e): e is NonNullable<typeof e> => e !== null);
  }, [dependencies, positions, criticalSet]);

  if (tasks.length === 0 || columns === 0) {
    return <p className="text-slate-400">Nenhuma tarefa para exibir.</p>;
  }

  return (
    <div className="card overflow-auto p-6" style={{ maxHeight: "70vh" }}>
      <div className="relative" style={{ width: width + 20, height: height + 20 }}>
        <svg className="absolute pointer-events-none" style={{ left: NODE_W / 2, top: NODE_H / 2, width, height }}>
          <defs>
            <marker id="pert-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
            </marker>
            <marker id="pert-arrow-critical" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#dc2626" />
            </marker>
          </defs>
          {edges.map((e) => (
            <path
              key={e.id}
              d={e.d}
              fill="none"
              stroke={e.isCritical ? "#dc2626" : "#cbd5e1"}
              strokeWidth={e.isCritical ? 2 : 1.5}
              markerEnd={e.isCritical ? "url(#pert-arrow-critical)" : "url(#pert-arrow)"}
            />
          ))}
        </svg>

        {tasks.map((t) => {
          const pos = positions.get(t.id);
          if (!pos) return null;
          const isCritical = criticalSet.has(t.id);
          const isParent = parentIds.has(t.id);
          return (
            <button
              key={t.id}
              onClick={() => onTaskClick(t.id)}
              className={clsx(
                "absolute rounded-lg border-2 bg-white dark:bg-surface-900 p-2.5 text-left shadow-sm hover:shadow-md transition-shadow",
                isCritical ? "border-red-500" : isParent ? "border-slate-400" : "border-surface-200 dark:border-slate-700",
                isParent && "border-dashed"
              )}
              style={{ left: pos.x, top: pos.y, width: NODE_W, height: NODE_H }}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span
                  className={clsx("text-[9px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0", PRIORITY_COLORS[t.priority])}
                >
                  {t.priority}
                </span>
                {isCritical && <span className="text-[9px] font-medium text-red-600">Crítico</span>}
              </div>
              <p className={clsx("text-xs font-medium truncate", t.is_completed ? "line-through text-slate-400" : "text-slate-800 dark:text-slate-100")}>
                {t.title}
              </p>
              <p className="text-[10px] text-slate-400 mt-1">
                {t.start_date ? format(new Date(t.start_date), "dd/MM") : "—"} → {t.due_date ? format(new Date(t.due_date), "dd/MM") : "—"}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
