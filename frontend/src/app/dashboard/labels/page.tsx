"use client";

import { useState } from "react";
import { Plus, Trash2, Tag } from "lucide-react";
import { useLabels } from "@/hooks/useLabels";

const LABEL_COLORS = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#6366f1", "#a855f7", "#ec4899"];

export default function LabelsPage() {
  const { labels, createLabel, updateLabel, deleteLabel } = useLabels();
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState(LABEL_COLORS[0]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");

  const handleCreate = () => {
    if (!newName.trim()) return;
    createLabel.mutate(
      { name: newName.trim(), color: newColor },
      {
        onSuccess: () => {
          setNewName("");
          setNewColor(LABEL_COLORS[(labels.length + 1) % LABEL_COLORS.length]);
        },
      }
    );
  };

  const startEdit = (id: number, name: string) => {
    setEditingId(id);
    setEditName(name);
  };

  const saveEdit = (id: number) => {
    if (editName.trim()) {
      updateLabel.mutate({ id, name: editName.trim() });
    }
    setEditingId(null);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Etiquetas</h1>
        <p className="text-slate-500 mt-1">Crie, renomeie ou exclua etiquetas usadas nas tarefas.</p>
      </div>

      <div className="card p-6 mb-6">
        <h2 className="font-semibold mb-4 flex items-center gap-2">
          <Plus size={16} /> Nova etiqueta
        </h2>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            {LABEL_COLORS.map((c) => (
              <button
                key={c}
                onClick={() => setNewColor(c)}
                className="w-6 h-6 rounded-full flex-shrink-0"
                style={{ backgroundColor: c, outline: newColor === c ? `2px solid ${c}` : "none", outlineOffset: 2 }}
              />
            ))}
          </div>
          <input
            className="input flex-1"
            placeholder="Nome da etiqueta"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            className="btn-primary"
            disabled={!newName.trim() || createLabel.isPending}
            onClick={handleCreate}
          >
            Adicionar
          </button>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="font-semibold mb-4">Etiquetas ({labels.length})</h2>
        {labels.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <Tag size={40} className="mx-auto mb-3 opacity-30" />
            <p>Nenhuma etiqueta ainda.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {labels.map((l) => (
              <div key={l.id} className="flex items-center gap-3 py-2 border-b border-surface-100 last:border-0">
                <div className="flex gap-1.5 flex-shrink-0">
                  {LABEL_COLORS.map((c) => (
                    <button
                      key={c}
                      onClick={() => updateLabel.mutate({ id: l.id, color: c })}
                      className="w-4 h-4 rounded-full"
                      style={{
                        backgroundColor: c,
                        outline: l.color === c ? `2px solid ${c}` : "none",
                        outlineOffset: 2,
                      }}
                    />
                  ))}
                </div>
                {editingId === l.id ? (
                  <input
                    autoFocus
                    className="input flex-1 py-1"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => saveEdit(l.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") saveEdit(l.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                  />
                ) : (
                  <span
                    className="flex-1 text-sm text-slate-700 cursor-text hover:bg-surface-50 rounded px-1 -mx-1"
                    onClick={() => startEdit(l.id, l.name)}
                  >
                    {l.name}
                  </span>
                )}
                <button
                  onClick={() => deleteLabel.mutate(l.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors p-1"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
