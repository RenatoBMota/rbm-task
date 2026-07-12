"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Folder, Trash2 } from "lucide-react";
import api from "@/lib/api";

interface Project {
  id: number;
  name: string;
  description: string | null;
  color: string;
  icon: string;
  task_count: number;
}

export default function ProjectsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", color: "#6366f1" });

  const { data: projects = [], isLoading } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => api.get("/projects/").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => api.post("/projects/", data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setForm({ name: "", description: "", color: "#6366f1" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/projects/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projects"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Projetos</h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={18} /> Novo Projeto
        </button>
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
            <div className="flex items-center gap-2">
              <label className="text-sm text-slate-600">Cor:</label>
              <input
                type="color"
                value={form.color}
                onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))}
                className="w-8 h-8 rounded cursor-pointer"
              />
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
            <div key={p.id} className="card p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: p.color + "20" }}
                  >
                    <Folder size={20} style={{ color: p.color }} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900">{p.name}</h3>
                    {p.description && (
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{p.description}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => deleteMutation.mutate(p.id)}
                  className="text-slate-300 hover:text-red-500 transition-colors p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
