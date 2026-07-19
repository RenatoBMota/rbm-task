"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Loader2, Check, Trash2, FolderOpen } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { PRIORITY_OPTIONS } from "@/lib/taskOptions";
import type { Project, TaskSuggestion, TaskPriority } from "@/lib/types";

const EMPTY_PROJECTS: Project[] = [];

interface ReviewItem {
  key: string;
  selected: boolean;
  title: string;
  description: string | null;
  priority: TaskPriority;
  due_date: string;
  estimated_minutes: number | "";
  project_id: number | "";
}

function toReviewItems(suggestions: TaskSuggestion[]): ReviewItem[] {
  return suggestions.map((s, i) => ({
    key: `${i}-${s.title}`,
    selected: true,
    title: s.title,
    description: s.description,
    priority: s.priority,
    due_date: s.due_date ?? "",
    estimated_minutes: s.estimated_minutes ?? "",
    project_id: s.suggested_project_id ?? "",
  }));
}

export default function AiTasksPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [text, setText] = useState("");
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [createdCount, setCreatedCount] = useState<number | null>(null);

  const { data: projects = EMPTY_PROJECTS } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: currentWorkspaceId } }).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.post<TaskSuggestion[]>("/ai/extract-tasks", { text, workspace_id: currentWorkspaceId }).then((r) => r.data),
    onSuccess: (suggestions) => {
      setItems(toReviewItems(suggestions));
      setCreatedCount(null);
    },
  });

  const createMutation = useMutation({
    mutationFn: async (selected: ReviewItem[]) => {
      for (const item of selected) {
        await api.post("/tasks", {
          title: item.title,
          description: item.description || null,
          priority: item.priority,
          due_date: item.due_date ? new Date(`${item.due_date}T23:59:00`).toISOString() : null,
          estimated_minutes: item.estimated_minutes === "" ? null : item.estimated_minutes,
          project_id: item.project_id === "" ? null : item.project_id,
        });
      }
      return selected.length;
    },
    onSuccess: (count) => {
      setCreatedCount(count);
      setItems(null);
      setText("");
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const analyzeError = (analyzeMutation.error as { response?: { data?: { detail?: string } } })?.response?.data
    ?.detail;

  function updateItem(key: string, patch: Partial<ReviewItem>) {
    setItems((prev) => prev?.map((it) => (it.key === key ? { ...it, ...patch } : it)) ?? null);
  }

  function removeItem(key: string) {
    setItems((prev) => prev?.filter((it) => it.key !== key) ?? null);
  }

  const selectedItems = items?.filter((i) => i.selected) ?? [];

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Sparkles size={22} className="text-primary-600" /> Tarefas por IA
        </h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Cole um resumo de reunião ou anotação e a IA sugere tarefas para você revisar e criar
        </p>
      </div>

      {!items && (
        <div className="card p-4 mb-6">
          <textarea
            className="input w-full"
            rows={10}
            placeholder="Cole aqui o resumo da reunião, ata ou anotação..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          {analyzeError && <p className="text-sm text-red-600 mt-2">{analyzeError}</p>}
          <div className="flex justify-end mt-3">
            <button
              className="btn-primary flex items-center gap-2"
              disabled={!text.trim() || analyzeMutation.isPending || !currentWorkspaceId}
              onClick={() => analyzeMutation.mutate()}
            >
              {analyzeMutation.isPending ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Analisando...
                </>
              ) : (
                <>
                  <Sparkles size={16} /> Analisar com IA
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {createdCount !== null && (
        <div className="card p-4 mb-6 flex items-center justify-between">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            <Check size={15} className="inline text-status-good mr-1" />
            {createdCount} tarefa(s) criada(s) com sucesso.
          </p>
          <button className="btn-secondary text-sm" onClick={() => setCreatedCount(null)}>
            Nova análise
          </button>
        </div>
      )}

      {items && (
        <div className="card">
          <div className="panel-header">
            <span className="font-semibold text-slate-900 dark:text-white">
              Sugestões ({items.length}) — {selectedItems.length} selecionada(s)
            </span>
            <div className="flex items-center gap-2">
              <button className="btn-secondary text-sm" onClick={() => setItems(null)}>
                Cancelar
              </button>
              <button
                className="btn-primary text-sm"
                disabled={selectedItems.length === 0 || createMutation.isPending}
                onClick={() => createMutation.mutate(selectedItems)}
              >
                {createMutation.isPending ? "Criando..." : `Criar ${selectedItems.length} tarefa(s)`}
              </button>
            </div>
          </div>

          {items.length === 0 ? (
            <p className="text-slate-400 text-sm p-4">A IA não encontrou nenhuma tarefa acionável nesse texto.</p>
          ) : (
            <div className="divide-y divide-surface-100 dark:divide-slate-800">
              {items.map((item) => (
                <div key={item.key} className="p-4 flex flex-col lg:flex-row gap-3">
                  <input
                    type="checkbox"
                    checked={item.selected}
                    onChange={(e) => updateItem(item.key, { selected: e.target.checked })}
                    className="w-4 h-4 accent-primary-600 mt-2 flex-shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <input
                      className="input font-medium"
                      value={item.title}
                      onChange={(e) => updateItem(item.key, { title: e.target.value })}
                    />
                    {item.description && <p className="text-xs text-slate-400 mt-1.5">{item.description}</p>}
                  </div>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 lg:w-[520px] flex-shrink-0">
                    <select
                      className="input py-1.5 text-sm"
                      value={item.priority}
                      onChange={(e) => updateItem(item.key, { priority: e.target.value as TaskPriority })}
                    >
                      {PRIORITY_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>{p.value}</option>
                      ))}
                    </select>
                    <input
                      type="date"
                      className="input py-1.5 text-sm"
                      value={item.due_date}
                      onChange={(e) => updateItem(item.key, { due_date: e.target.value })}
                    />
                    <input
                      type="number"
                      className="input py-1.5 text-sm"
                      placeholder="Min."
                      value={item.estimated_minutes}
                      onChange={(e) =>
                        updateItem(item.key, { estimated_minutes: e.target.value ? Number(e.target.value) : "" })
                      }
                    />
                    <select
                      className="input py-1.5 text-sm"
                      value={item.project_id}
                      onChange={(e) => updateItem(item.key, { project_id: e.target.value ? Number(e.target.value) : "" })}
                    >
                      <option value="">Agenda diária</option>
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  <button
                    onClick={() => removeItem(item.key)}
                    className="text-slate-300 hover:text-red-500 p-1.5 self-start flex-shrink-0"
                    title="Descartar sugestão"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!items && !currentWorkspaceId && (
        <p className="text-slate-400 text-sm mt-4 flex items-center gap-1.5">
          <FolderOpen size={14} /> Selecione uma área de trabalho para continuar.
        </p>
      )}
    </div>
  );
}
