"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Folder, Trash2, Archive, ArchiveRestore, Copy } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import type { Project } from "@/lib/types";

export default function ProjectsPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [showForm, setShowForm] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", color: "#6366f1", is_template: false });

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ["projects", currentWorkspaceId, showArchived],
    queryFn: () =>
      api
        .get("/projects", { params: { workspace_id: currentWorkspaceId, include_archived: showArchived } })
        .then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => api.post("/projects", { ...data, workspace_id: currentWorkspaceId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects", currentWorkspaceId] });
      setShowForm(false);
      setForm({ name: "", description: "", color: "#6366f1", is_template: false });
    },
  });

  const archiveMutation = useMutation({
    mutationFn: ({ id, is_archived }: { id: number; is_archived: boolean }) =>
      api.put(`/projects/${id}`, { is_archived }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", currentWorkspaceId] }),
  });

  const duplicateMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.post(`/projects/${id}/duplicate`, { name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", currentWorkspaceId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/projects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects", currentWorkspaceId] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Projetos</h1>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-500">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => setShowArchived(e.target.checked)}
            />
            Mostrar arquivados
          </label>
          <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
            <Plus size={18} /> Novo Projeto
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold mb-4">Novo Projeto</h2>
          <div className="space-y-3">
            <input
              className="input"
              placeholder="Nome do projeto"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
            <input
              className="input"
              placeholder="Descrição (opcional)"
              value={form.description}
              onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
            />
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-600">Cor:</label>
                <input
                  type="color"
                  value={form.color}
                  onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))}
                  className="w-8 h-8 rounded cursor-pointer"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={form.is_template}
                  onChange={(e) => setForm((p) => ({ ...p, is_template: e.target.checked }))}
                />
                Salvar como template
              </label>
            </div>
            <div className="flex gap-2">
              <button
                className="btn-primary"
                onClick={() => createMutation.mutate(form)}
                disabled={!form.name || createMutation.isPending}
              >
                {createMutation.isPending ? "Criando..." : "Criar"}
              </button>
              <button className="btn-secondary" onClick={() => setShowForm(false)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <p className="text-slate-400">Carregando...</p>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <Folder size={48} className="mx-auto mb-3 opacity-30" />
          <p>Nenhum projeto ainda. Crie o primeiro!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((p) => (
            <div
              key={p.id}
              className={clsx("card p-5 hover:shadow-md transition-shadow", p.is_archived && "opacity-60")}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: p.color + "20" }}
                  >
                    <Folder size={20} style={{ color: p.color }} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-slate-900 truncate flex items-center gap-2">
                      {p.name}
                      {p.is_template && (
                        <span className="text-xs font-normal px-1.5 py-0.5 rounded bg-primary-50 text-primary-600">
                          template
                        </span>
                      )}
                    </h3>
                    {p.description && (
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{p.description}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button
                    title="Duplicar"
                    onClick={() => duplicateMutation.mutate({ id: p.id, name: `${p.name} (cópia)` })}
                    className="text-slate-300 hover:text-primary-600 transition-colors p-1"
                  >
                    <Copy size={15} />
                  </button>
                  <button
                    title={p.is_archived ? "Reativar" : "Arquivar"}
                    onClick={() => archiveMutation.mutate({ id: p.id, is_archived: !p.is_archived })}
                    className="text-slate-300 hover:text-amber-600 transition-colors p-1"
                  >
                    {p.is_archived ? <ArchiveRestore size={15} /> : <Archive size={15} />}
                  </button>
                  <button
                    onClick={() => deleteMutation.mutate(p.id)}
                    className="text-slate-300 hover:text-red-500 transition-colors p-1"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
