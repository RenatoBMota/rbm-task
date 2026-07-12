"use client";

import { X, Trash2 } from "lucide-react";
import { DEPENDENCY_TYPE_LABELS } from "@/lib/types";
import type { GanttDependency, DependencyType, DependencyHardness } from "@/lib/types";

export function DependencyPopover({
  dependency,
  x,
  y,
  onUpdate,
  onDelete,
  onClose,
}: {
  dependency: GanttDependency;
  x: number;
  y: number;
  onUpdate: (data: { dependency_type?: DependencyType; lag_days?: number; hardness?: DependencyHardness }) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-40" onClick={onClose}>
      <div
        className="fixed z-50 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-3 w-64 space-y-2"
        style={{ left: Math.max(x - 128, 8), top: y + 8 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-500">Dependência</span>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 hover:dark:text-slate-300">
            <X size={14} />
          </button>
        </div>
        <div>
          <label className="block text-xs text-slate-400 mb-1">Tipo</label>
          <select
            className="input text-sm py-1"
            value={dependency.dependency_type}
            onChange={(e) => onUpdate({ dependency_type: e.target.value as DependencyType })}
          >
            {Object.entries(DEPENDENCY_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="block text-xs text-slate-400 mb-1">Atraso (dias)</label>
            <input
              type="number"
              className="input text-sm py-1"
              value={dependency.lag_days}
              onChange={(e) => onUpdate({ lag_days: Number(e.target.value) })}
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-slate-400 mb-1">Rigidez</label>
            <select
              className="input text-sm py-1"
              value={dependency.hardness}
              onChange={(e) => onUpdate({ hardness: e.target.value as DependencyHardness })}
            >
              <option value="strong">Rígida</option>
              <option value="rubber">Flexível</option>
            </select>
          </div>
        </div>
        <button className="flex items-center gap-1.5 text-xs text-red-500 hover:underline pt-1" onClick={onDelete}>
          <Trash2 size={12} /> Remover dependência
        </button>
      </div>
    </div>
  );
}
