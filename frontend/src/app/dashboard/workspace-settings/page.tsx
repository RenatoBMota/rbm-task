"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Trash2, Shield } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import type { WorkspaceMember, WorkspaceRole } from "@/lib/types";

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Membro",
};

export default function WorkspaceSettingsPage() {
  const qc = useQueryClient();
  const { currentWorkspace, currentWorkspaceId } = useWorkspaces();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("member");

  const { data: members = [] } = useQuery<WorkspaceMember[]>({
    queryKey: ["workspace-members", currentWorkspaceId],
    queryFn: () => api.get(`/workspaces/${currentWorkspaceId}/members`).then((r) => r.data),
    enabled: !!currentWorkspaceId,
  });

  const addMember = useMutation({
    mutationFn: () => api.post(`/workspaces/${currentWorkspaceId}/members`, { email, role }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace-members", currentWorkspaceId] });
      setEmail("");
    },
  });

  const changeRole = useMutation({
    mutationFn: ({ memberId, role }: { memberId: number; role: WorkspaceRole }) =>
      api.put(`/workspaces/${currentWorkspaceId}/members/${memberId}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace-members", currentWorkspaceId] }),
  });

  const removeMember = useMutation({
    mutationFn: (memberId: number) =>
      api.delete(`/workspaces/${currentWorkspaceId}/members/${memberId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace-members", currentWorkspaceId] }),
  });

  const canManage = currentWorkspace?.my_role === "owner" || currentWorkspace?.my_role === "admin";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Configurações da Área de Trabalho</h1>
        <p className="text-slate-500 mt-1">{currentWorkspace?.name}</p>
      </div>

      {canManage && (
        <div className="card p-6 mb-6">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <UserPlus size={16} /> Convidar membro
          </h2>
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="E-mail do usuário já cadastrado"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <select
              className="input w-40"
              value={role}
              onChange={(e) => setRole(e.target.value as WorkspaceRole)}
            >
              <option value="member">Membro</option>
              <option value="admin">Admin</option>
            </select>
            <button
              className="btn-primary"
              disabled={!email.trim() || addMember.isPending}
              onClick={() => addMember.mutate()}
            >
              Adicionar
            </button>
          </div>
          {addMember.isError && (
            <p className="text-sm text-red-600 mt-2">Usuário não encontrado (precisa já ter uma conta no RBM TASK).</p>
          )}
        </div>
      )}

      <div className="card p-6">
        <h2 className="font-semibold mb-4">Membros ({members.length})</h2>
        <div className="space-y-2">
          {members.map((m) => (
            <div key={m.id} className="flex items-center gap-3 py-2 border-b border-surface-100 last:border-0">
              <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-sm font-semibold flex-shrink-0">
                {m.full_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{m.full_name}</p>
                <p className="text-xs text-slate-400 truncate">{m.email}</p>
              </div>
              {canManage && m.role !== "owner" ? (
                <select
                  className="input w-32 text-sm py-1"
                  value={m.role}
                  onChange={(e) => changeRole.mutate({ memberId: m.id, role: e.target.value as WorkspaceRole })}
                >
                  <option value="member">Membro</option>
                  <option value="admin">Admin</option>
                </select>
              ) : (
                <span
                  className={clsx(
                    "text-xs font-medium px-2 py-1 rounded-full flex items-center gap-1",
                    m.role === "owner" ? "bg-primary-100 text-primary-700" : "bg-surface-100 text-slate-600"
                  )}
                >
                  <Shield size={12} /> {ROLE_LABELS[m.role]}
                </span>
              )}
              {canManage && m.role !== "owner" && (
                <button
                  onClick={() => removeMember.mutate(m.id)}
                  className="text-slate-300 hover:text-red-500 p-1"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
