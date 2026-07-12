"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Users2, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import type { Resource, ResourceUtilization } from "@/lib/types";

const EMPTY_RESOURCES: Resource[] = [];
const EMPTY_UTILIZATION: ResourceUtilization[] = [];

export default function ResourcesPage() {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", role: "", email: "", standard_rate: 0 });

  const { data: resources = EMPTY_RESOURCES } = useQuery<Resource[]>({
    queryKey: ["resources", currentWorkspaceId],
    queryFn: () => api.get(`/workspaces/${currentWorkspaceId}/resources`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const { data: utilization = EMPTY_UTILIZATION } = useQuery<ResourceUtilization[]>({
    queryKey: ["resources", "utilization", currentWorkspaceId],
    queryFn: () => api.get(`/workspaces/${currentWorkspaceId}/resources/utilization`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const utilizationByResource = new Map(utilization.map((u) => [u.resource_id, u]));

  const createMutation = useMutation({
    mutationFn: () => api.post(`/workspaces/${currentWorkspaceId}/resources`, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["resources", currentWorkspaceId] });
      setShowForm(false);
      setForm({ name: "", role: "", email: "", standard_rate: 0 });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/workspaces/${currentWorkspaceId}/resources/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["resources", currentWorkspaceId] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Recursos</h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={18} /> Novo Recurso
        </button>
      </div>

      {showForm && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold mb-4">Novo Recurso</h2>
          <div className="grid grid-cols-2 gap-3">
            <input
              className="input"
              placeholder="Nome"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
            <input
              className="input"
              placeholder="Papel (ex: Desenvolvedor)"
              value={form.role}
              onChange={(e) => setForm((p) => ({ ...p, role: e.target.value }))}
            />
            <input
              className="input"
              placeholder="E-mail (opcional)"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
            />
            <input
              type="number"
              className="input"
              placeholder="Taxa diária (R$)"
              value={form.standard_rate || ""}
              onChange={(e) => setForm((p) => ({ ...p, standard_rate: Number(e.target.value) }))}
            />
          </div>
          <div className="flex gap-2 mt-4">
            <button
              className="btn-primary"
              disabled={!form.name || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Criando..." : "Criar"}
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {resources.length === 0 ? (
        <div className="card p-10 text-center text-slate-400">
          <Users2 size={40} className="mx-auto mb-3 opacity-30" />
          <p>Nenhum recurso cadastrado ainda.</p>
        </div>
      ) : (
        <div className="card p-6">
          <h2 className="font-semibold mb-4">Recursos ({resources.length})</h2>
          <div className="space-y-2">
            {resources.map((r) => {
              const util = utilizationByResource.get(r.id);
              const pct = util?.total_allocation_percent ?? 0;
              const isOverloaded = pct > 100;
              return (
                <div key={r.id} className="flex items-center gap-3 py-2 border-b border-surface-100 last:border-0">
                  <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-sm font-semibold flex-shrink-0">
                    {r.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{r.name}</p>
                    <p className="text-xs text-slate-400 truncate">
                      {r.role || "Sem papel"} {r.standard_rate > 0 && `· R$ ${r.standard_rate}/dia`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 w-40">
                    <div className="flex-1 h-1.5 bg-surface-100 rounded-full overflow-hidden">
                      <div
                        className={clsx(
                          "h-full rounded-full",
                          isOverloaded ? "bg-red-500" : pct === 100 ? "bg-slate-400" : "bg-green-500"
                        )}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                    </div>
                    <span
                      className={clsx(
                        "text-xs font-medium flex items-center gap-1 w-14",
                        isOverloaded ? "text-red-600" : "text-slate-500"
                      )}
                    >
                      {isOverloaded && <AlertTriangle size={11} />}
                      {pct}%
                    </span>
                  </div>
                  <button
                    onClick={() => deleteMutation.mutate(r.id)}
                    className="text-slate-300 hover:text-red-500 p-1"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
