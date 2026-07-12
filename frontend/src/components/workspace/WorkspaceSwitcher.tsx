"use client";

import { useState } from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { ChevronDown, Plus, Briefcase, Settings } from "lucide-react";
import Link from "next/link";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import api from "@/lib/api";

export function WorkspaceSwitcher() {
  const qc = useQueryClient();
  const { workspaces, currentWorkspace, currentWorkspaceId, setCurrentWorkspaceId } = useWorkspaces();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  const createMutation = useMutation({
    mutationFn: (name: string) => api.post("/workspaces", { name }),
    onSuccess: ({ data }) => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
      setCurrentWorkspaceId(data.id);
      setCreating(false);
      setNewName("");
      setOpen(false);
    },
  });

  return (
    <div className="relative px-3 py-3 border-b border-slate-700">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-slate-700 transition-colors text-left"
      >
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: currentWorkspace?.color ?? "#0079bf" }}
        >
          <Briefcase size={14} className="text-white" />
        </div>
        <span className="flex-1 min-w-0 truncate text-sm font-medium text-white">
          {currentWorkspace?.name ?? "Carregando..."}
        </span>
        <ChevronDown size={16} className="text-slate-400 flex-shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-3 right-3 mt-1 bg-white dark:bg-surface-900 rounded-lg shadow-xl border border-surface-200 dark:border-slate-700 z-20 py-1 max-h-80 overflow-y-auto">
            {workspaces.map((w) => (
              <div key={w.id} className="flex items-center group">
                <button
                  onClick={() => {
                    setCurrentWorkspaceId(w.id);
                    setOpen(false);
                  }}
                  className={`flex-1 flex items-center gap-2 px-3 py-2 text-sm hover:bg-surface-50 hover:dark:bg-surface-800 transition-colors ${
                    w.id === currentWorkspaceId ? "text-primary-600 font-medium" : "text-slate-700 dark:text-slate-300"
                  }`}
                >
                  <div
                    className="w-5 h-5 rounded flex-shrink-0"
                    style={{ backgroundColor: w.color }}
                  />
                  <span className="truncate">{w.name}</span>
                </button>
                <Link
                  href="/dashboard/workspace-settings"
                  onClick={() => {
                    setCurrentWorkspaceId(w.id);
                    setOpen(false);
                  }}
                  className="p-2 text-slate-300 hover:text-slate-600 hover:dark:text-slate-400 opacity-0 group-hover:opacity-100"
                >
                  <Settings size={14} />
                </Link>
              </div>
            ))}

            <div className="border-t border-surface-100 dark:border-slate-800 mt-1 pt-1 px-2">
              {creating ? (
                <div className="flex gap-1 p-1">
                  <input
                    autoFocus
                    className="input flex-1 text-sm py-1"
                    placeholder="Nome da área"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newName.trim()) createMutation.mutate(newName.trim());
                    }}
                  />
                  <button
                    className="btn-primary text-sm px-2"
                    disabled={!newName.trim() || createMutation.isPending}
                    onClick={() => createMutation.mutate(newName.trim())}
                  >
                    Criar
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setCreating(true)}
                  className="w-full flex items-center gap-2 px-2 py-2 text-sm text-slate-500 hover:text-slate-800 hover:dark:text-slate-100 rounded-md hover:bg-surface-50 hover:dark:bg-surface-800"
                >
                  <Plus size={14} /> Nova área de trabalho
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
