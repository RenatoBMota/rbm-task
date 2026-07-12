"use client";

import { useMemo, useRef, useState } from "react";
import { addDays, differenceInCalendarDays, format, isWeekend, startOfDay, subDays } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ZoomIn, ZoomOut, Link2, Plus } from "lucide-react";
import { clsx } from "clsx";
import { PRIORITY_COLORS, DEPENDENCY_TYPE_SHORT } from "@/lib/types";
import type { Task, GanttDependency, GanttBaselineTaskData } from "@/lib/types";

const LEFT_WIDTH = 260;
const ROW_H = 36;
const HEADER_H = 44;
const MIN_DAY_WIDTH = 14;
const MAX_DAY_WIDTH = 72;

interface Row {
  task: Task;
  depth: number;
}

function buildRows(tasks: Task[]): Row[] {
  const byParent = new Map<number | null, Task[]>();
  for (const t of tasks) {
    const key = t.parent_id;
    if (!byParent.has(key)) byParent.set(key, []);
    byParent.get(key)!.push(t);
  }
  for (const list of byParent.values()) list.sort((a, b) => a.position - b.position);

  const rows: Row[] = [];
  const visited = new Set<number>();
  function visit(parentId: number | null, depth: number) {
    for (const t of byParent.get(parentId) ?? []) {
      if (visited.has(t.id)) continue;
      visited.add(t.id);
      rows.push({ task: t, depth });
      visit(t.id, depth + 1);
    }
  }
  visit(null, 0);
  // tasks whose parent isn't in this task set (shouldn't normally happen) still get shown
  for (const t of tasks) {
    if (!visited.has(t.id)) {
      visited.add(t.id);
      rows.push({ task: t, depth: 0 });
    }
  }
  return rows;
}

function computeRange(tasks: Task[]): { start: Date; end: Date } {
  const dates = tasks
    .flatMap((t) => [t.start_date, t.due_date])
    .filter((d): d is string => !!d)
    .map((d) => new Date(d));
  const today = startOfDay(new Date());
  if (dates.length === 0) {
    return { start: subDays(today, 3), end: addDays(today, 30) };
  }
  const min = new Date(Math.min(...dates.map((d) => d.getTime()), today.getTime()));
  const max = new Date(Math.max(...dates.map((d) => d.getTime()), today.getTime()));
  return { start: subDays(startOfDay(min), 2), end: addDays(startOfDay(max), 5) };
}

type DragMode = "move" | "resize-start" | "resize-end";

interface DragState {
  taskId: number;
  mode: DragMode;
  startX: number;
  originalStart: Date;
  originalDue: Date;
}

interface LinkState {
  fromTaskId: number;
  x: number;
  y: number;
}

export function GanttChart({
  tasks,
  dependencies,
  criticalTaskIds,
  baselineTasks,
  onTaskClick,
  onReschedule,
  onCreateDependency,
  onSelectDependency,
  onAddTask,
}: {
  tasks: Task[];
  dependencies: GanttDependency[];
  criticalTaskIds: number[];
  baselineTasks?: GanttBaselineTaskData[] | null;
  onTaskClick: (taskId: number) => void;
  onReschedule: (taskId: number, startDate: Date, dueDate: Date) => void;
  onCreateDependency: (taskId: number, dependsOnId: number) => void;
  onSelectDependency: (dep: GanttDependency, x: number, y: number) => void;
  onAddTask: () => void;
}) {
  const [dayWidth, setDayWidth] = useState(28);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [dragDeltaPx, setDragDeltaPx] = useState(0);
  const [link, setLink] = useState<LinkState | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const rows = useMemo(() => buildRows(tasks), [tasks]);
  const range = useMemo(() => computeRange(tasks), [tasks]);
  const totalDays = Math.max(differenceInCalendarDays(range.end, range.start), 1);
  const timelineWidth = totalDays * dayWidth;
  const criticalSet = useMemo(() => new Set(criticalTaskIds), [criticalTaskIds]);
  const rowIndexByTaskId = useMemo(() => {
    const map = new Map<number, number>();
    rows.forEach((r, i) => map.set(r.task.id, i));
    return map;
  }, [rows]);

  const dayColumns = useMemo(() => {
    const cols: { date: Date; offset: number }[] = [];
    for (let i = 0; i < totalDays; i++) {
      cols.push({ date: addDays(range.start, i), offset: i * dayWidth });
    }
    return cols;
  }, [range, totalDays, dayWidth]);

  const todayOffset = differenceInCalendarDays(startOfDay(new Date()), range.start) * dayWidth;

  const geometryForDates = (startStr: string | null, dueStr: string | null, isMilestone = false) => {
    if (!startStr && !dueStr) return null;
    const start = startStr ? new Date(startStr) : new Date(dueStr!);
    const due = dueStr ? new Date(dueStr) : new Date(startStr!);
    const left = differenceInCalendarDays(start, range.start) * dayWidth;
    const durationDays = isMilestone ? 0 : Math.max(differenceInCalendarDays(due, start), 0);
    const width = isMilestone ? dayWidth : Math.max(durationDays * dayWidth, dayWidth * 0.6);
    return { left, width, start, due };
  };

  const barGeometry = (task: Task) => geometryForDates(task.start_date, task.due_date, task.is_milestone);

  const baselineByTaskId = useMemo(() => {
    if (!baselineTasks) return null;
    const map = new Map<number, GanttBaselineTaskData>();
    for (const bt of baselineTasks) {
      if (bt.task_id != null) map.set(bt.task_id, bt);
    }
    return map;
  }, [baselineTasks]);

  const handleBarPointerDown = (e: React.PointerEvent, task: Task, mode: DragMode) => {
    e.stopPropagation();
    const geo = barGeometry(task);
    if (!geo) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    setDrag({ taskId: task.id, mode, startX: e.clientX, originalStart: geo.start, originalDue: geo.due });
    setDragDeltaPx(0);
  };

  const handleContainerPointerMove = (e: React.PointerEvent) => {
    if (drag) {
      setDragDeltaPx(e.clientX - drag.startX);
    }
    if (link && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setLink({ ...link, x: e.clientX - rect.left + containerRef.current.scrollLeft, y: e.clientY - rect.top + containerRef.current.scrollTop });
    }
  };

  const handleContainerPointerUp = (e: React.PointerEvent) => {
    if (drag) {
      const deltaDays = Math.round(dragDeltaPx / dayWidth);
      if (deltaDays !== 0) {
        let newStart = drag.originalStart;
        let newDue = drag.originalDue;
        if (drag.mode === "move") {
          newStart = addDays(drag.originalStart, deltaDays);
          newDue = addDays(drag.originalDue, deltaDays);
        } else if (drag.mode === "resize-end") {
          newDue = addDays(drag.originalDue, deltaDays);
          if (newDue < newStart) newDue = newStart;
        } else {
          newStart = addDays(drag.originalStart, deltaDays);
          if (newStart > newDue) newStart = newDue;
        }
        onReschedule(drag.taskId, newStart, newDue);
      }
      setDrag(null);
      setDragDeltaPx(0);
    }
    if (link && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const y = e.clientY - rect.top + containerRef.current.scrollTop;
      const rowIndex = Math.floor((y - HEADER_H) / ROW_H);
      const targetRow = rows[rowIndex];
      if (targetRow && targetRow.task.id !== link.fromTaskId) {
        onCreateDependency(targetRow.task.id, link.fromTaskId);
      }
      setLink(null);
    }
  };

  const dependencyPaths = useMemo(() => {
    return dependencies
      .map((dep) => {
        const predIndex = rowIndexByTaskId.get(dep.depends_on_id);
        const succIndex = rowIndexByTaskId.get(dep.task_id);
        if (predIndex === undefined || succIndex === undefined) return null;
        const predTask = rows[predIndex].task;
        const succTask = rows[succIndex].task;
        const predGeo = barGeometry(predTask);
        const succGeo = barGeometry(succTask);
        if (!predGeo || !succGeo) return null;

        const sourceX = dep.dependency_type.startsWith("finish") ? predGeo.left + predGeo.width : predGeo.left;
        const targetX = dep.dependency_type.endsWith("start") ? succGeo.left : succGeo.left + succGeo.width;
        const sourceY = predIndex * ROW_H + ROW_H / 2;
        const targetY = succIndex * ROW_H + ROW_H / 2;
        const midX = (sourceX + targetX) / 2;
        const isCritical = criticalSet.has(dep.task_id) && criticalSet.has(dep.depends_on_id);
        return {
          dep,
          d: `M ${sourceX} ${sourceY} C ${midX} ${sourceY}, ${midX} ${targetY}, ${targetX} ${targetY}`,
          isCritical,
          midX,
          midY: (sourceY + targetY) / 2,
        };
      })
      .filter((p): p is NonNullable<typeof p> => p !== null);
  }, [dependencies, rowIndexByTaskId, rows, criticalSet, dayWidth, range]);

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-surface-100 dark:border-slate-800">
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-3 h-1.5 rounded-sm bg-primary-600 inline-block" /> Tarefa
          </span>
          <span className="flex items-center gap-1">
            <span
              className="w-3 h-1.5 rounded-sm inline-block"
              style={{ background: "repeating-linear-gradient(45deg, #dc2626, #dc2626 3px, #f87171 3px, #f87171 6px)" }}
            />
            Caminho crítico
          </span>
          {baselineByTaskId && (
            <span className="flex items-center gap-1">
              <span className="w-3 h-1 rounded-sm bg-slate-300 inline-block opacity-60" /> Baseline (verde = adiantado, vermelho = atrasado)
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary flex items-center gap-1.5 text-sm py-1.5" onClick={onAddTask}>
            <Plus size={14} /> Nova tarefa
          </button>
          <button
            className="p-1.5 rounded hover:bg-surface-100 hover:dark:bg-surface-800 text-slate-500"
            onClick={() => setDayWidth((w) => Math.max(w - 6, MIN_DAY_WIDTH))}
          >
            <ZoomOut size={16} />
          </button>
          <button
            className="p-1.5 rounded hover:bg-surface-100 hover:dark:bg-surface-800 text-slate-500"
            onClick={() => setDayWidth((w) => Math.min(w + 6, MAX_DAY_WIDTH))}
          >
            <ZoomIn size={16} />
          </button>
        </div>
      </div>

      <div
        ref={containerRef}
        className="overflow-auto select-none"
        style={{ maxHeight: "65vh" }}
        onPointerMove={handleContainerPointerMove}
        onPointerUp={handleContainerPointerUp}
      >
        <div style={{ width: LEFT_WIDTH + timelineWidth, position: "relative" }}>
          {/* header */}
          <div className="flex sticky top-0 z-30 bg-white dark:bg-surface-900">
            <div
              className="sticky left-0 z-40 bg-white dark:bg-surface-900 border-r border-b border-surface-200 dark:border-slate-700 flex items-center px-3 text-xs font-semibold text-slate-500"
              style={{ width: LEFT_WIDTH, height: HEADER_H, flexShrink: 0 }}
            >
              Tarefa
            </div>
            <div className="relative border-b border-surface-200 dark:border-slate-700" style={{ width: timelineWidth, height: HEADER_H }}>
              {dayColumns.map((col) => (
                <div
                  key={col.offset}
                  className={clsx(
                    "absolute top-0 h-full flex flex-col items-center justify-center text-[10px] border-r border-surface-100 dark:border-slate-800",
                    isWeekend(col.date) && "bg-surface-50 dark:bg-surface-800"
                  )}
                  style={{ left: col.offset, width: dayWidth }}
                >
                  <span className="text-slate-400">{format(col.date, "EEEEEE", { locale: ptBR })}</span>
                  <span className="text-slate-600 dark:text-slate-400 font-medium">{format(col.date, "d")}</span>
                </div>
              ))}
            </div>
          </div>

          {/* rows */}
          {rows.map((row, index) => {
            const geo = barGeometry(row.task);
            const isCritical = criticalSet.has(row.task.id);
            const isDraggingThis = drag?.taskId === row.task.id;
            let renderLeft = geo?.left ?? 0;
            let renderWidth = geo?.width ?? 0;
            if (isDraggingThis && geo) {
              if (drag!.mode === "move") {
                renderLeft = geo.left + dragDeltaPx;
              } else if (drag!.mode === "resize-end") {
                renderWidth = Math.max(geo.width + dragDeltaPx, 6);
              } else {
                renderLeft = geo.left + dragDeltaPx;
                renderWidth = Math.max(geo.width - dragDeltaPx, 6);
              }
            }
            return (
              <div key={row.task.id} className="flex border-b border-surface-50" style={{ height: ROW_H }}>
                <div
                  className="sticky left-0 z-20 bg-white dark:bg-surface-900 border-r border-surface-200 dark:border-slate-700 flex items-center gap-1.5 px-3 overflow-hidden"
                  style={{ width: LEFT_WIDTH, flexShrink: 0, paddingLeft: 12 + row.depth * 14 }}
                >
                  <span
                    className={clsx(
                      "text-[10px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0",
                      PRIORITY_COLORS[row.task.priority]
                    )}
                  >
                    {row.task.priority}
                  </span>
                  <button
                    className={clsx(
                      "text-sm truncate text-left hover:underline",
                      row.task.is_completed ? "line-through text-slate-400" : "text-slate-700 dark:text-slate-300"
                    )}
                    onClick={() => onTaskClick(row.task.id)}
                    title={row.task.title}
                  >
                    {row.task.title}
                  </button>
                </div>
                <div className="relative" style={{ width: timelineWidth, flexShrink: 0 }}>
                  {dayColumns.map((col) => (
                    <div
                      key={col.offset}
                      className={clsx("absolute top-0 h-full border-r border-surface-50", isWeekend(col.date) && "bg-surface-50 dark:bg-surface-800/70")}
                      style={{ left: col.offset, width: dayWidth }}
                    />
                  ))}
                  {index === 0 && (
                    <div
                      className="absolute top-0 w-px bg-red-400 z-10"
                      style={{ left: todayOffset, height: rows.length * ROW_H }}
                    />
                  )}
                  {baselineByTaskId && baselineByTaskId.has(row.task.id) && (() => {
                    const bt = baselineByTaskId.get(row.task.id)!;
                    const bgeo = geometryForDates(bt.start_date, bt.due_date, row.task.is_milestone);
                    if (!bgeo) return null;
                    const baselineDue = bt.due_date ? new Date(bt.due_date) : null;
                    const currentDue = row.task.due_date ? new Date(row.task.due_date) : null;
                    const isLate = baselineDue && currentDue && currentDue > baselineDue;
                    const isEarly = baselineDue && currentDue && currentDue < baselineDue;
                    return (
                      <div
                        className={clsx(
                          "absolute rounded-sm opacity-60",
                          isLate ? "bg-red-300" : isEarly ? "bg-green-300" : "bg-slate-300"
                        )}
                        style={{ left: bgeo.left, width: bgeo.width, top: 2, height: 4 }}
                        title={`Baseline: ${format(bgeo.start, "dd/MM")} → ${format(bgeo.due, "dd/MM")}`}
                      />
                    );
                  })()}
                  {geo && row.task.is_milestone && (
                    <div
                      className={clsx(
                        "absolute rounded-sm rotate-45 cursor-pointer",
                        isCritical ? "bg-red-500" : "bg-primary-600"
                      )}
                      style={{
                        left: renderLeft + dayWidth / 2 - 7,
                        top: ROW_H / 2 - 7,
                        width: 14,
                        height: 14,
                      }}
                      onClick={() => onTaskClick(row.task.id)}
                    />
                  )}
                  {geo && !row.task.is_milestone && (
                    <div
                      className={clsx(
                        "absolute rounded flex items-center group cursor-grab active:cursor-grabbing",
                        isCritical ? "bg-red-500" : "bg-primary-600"
                      )}
                      style={{
                        left: renderLeft,
                        width: renderWidth,
                        top: 6,
                        height: ROW_H - 12,
                        backgroundImage: isCritical
                          ? "repeating-linear-gradient(45deg, rgba(255,255,255,0.25) 0, rgba(255,255,255,0.25) 4px, transparent 4px, transparent 8px)"
                          : undefined,
                      }}
                      onPointerDown={(e) => handleBarPointerDown(e, row.task, "move")}
                    >
                      <div
                        className="absolute left-0 top-0 h-full w-1.5 cursor-ew-resize"
                        onPointerDown={(e) => handleBarPointerDown(e, row.task, "resize-start")}
                      />
                      <div
                        className="h-1 bg-black/25 rounded-full mx-1"
                        style={{ width: `${row.task.is_completed ? 100 : 0}%` }}
                      />
                      <div
                        className="absolute right-0 top-0 h-full w-1.5 cursor-ew-resize"
                        onPointerDown={(e) => handleBarPointerDown(e, row.task, "resize-end")}
                      />
                      <button
                        className="absolute -right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 rounded-full bg-white dark:bg-surface-900 border-2 border-primary-600 opacity-0 group-hover:opacity-100 cursor-crosshair"
                        onPointerDown={(e) => {
                          e.stopPropagation();
                          if (containerRef.current) {
                            const rect = containerRef.current.getBoundingClientRect();
                            setLink({
                              fromTaskId: row.task.id,
                              x: e.clientX - rect.left + containerRef.current.scrollLeft,
                              y: e.clientY - rect.top + containerRef.current.scrollTop,
                            });
                          }
                        }}
                      >
                        <Link2 size={8} className="text-primary-600" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* dependency arrows overlay */}
          <svg
            className="absolute pointer-events-none"
            style={{ left: LEFT_WIDTH, top: HEADER_H, width: timelineWidth, height: rows.length * ROW_H }}
          >
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
              </marker>
              <marker id="arrow-critical" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#dc2626" />
              </marker>
            </defs>
            {dependencyPaths.map(({ dep, d, isCritical, midX, midY }) => (
              <g key={dep.id} className="pointer-events-auto cursor-pointer">
                <path d={d} fill="none" stroke="transparent" strokeWidth={10} />
                <path
                  d={d}
                  fill="none"
                  stroke={isCritical ? "#dc2626" : "#94a3b8"}
                  strokeWidth={1.5}
                  strokeDasharray={dep.hardness === "rubber" ? "4 3" : undefined}
                  markerEnd={isCritical ? "url(#arrow-critical)" : "url(#arrow)"}
                />
                <rect
                  x={midX - 12}
                  y={midY - 7}
                  width={24}
                  height={14}
                  rx={3}
                  fill="white"
                  stroke={isCritical ? "#dc2626" : "#cbd5e1"}
                  className="pointer-events-auto"
                  onClick={(e) => {
                    const rect = containerRef.current?.getBoundingClientRect();
                    onSelectDependency(dep, (rect?.left ?? 0) + LEFT_WIDTH + midX, (rect?.top ?? 0) + HEADER_H + midY);
                  }}
                />
                <text
                  x={midX}
                  y={midY + 3}
                  textAnchor="middle"
                  fontSize={9}
                  fill={isCritical ? "#dc2626" : "#64748b"}
                  className="pointer-events-none select-none"
                >
                  {DEPENDENCY_TYPE_SHORT[dep.dependency_type]}
                </text>
              </g>
            ))}
            {link && (
              <line
                x1={(() => {
                  const idx = rowIndexByTaskId.get(link.fromTaskId);
                  if (idx === undefined) return 0;
                  const geo = barGeometry(rows[idx].task);
                  return geo ? geo.left + geo.width : 0;
                })()}
                y1={(() => {
                  const idx = rowIndexByTaskId.get(link.fromTaskId);
                  return idx === undefined ? 0 : idx * ROW_H + ROW_H / 2;
                })()}
                x2={link.x - LEFT_WIDTH}
                y2={link.y - HEADER_H}
                stroke="#4f46e5"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
            )}
          </svg>
        </div>
      </div>
    </div>
  );
}
