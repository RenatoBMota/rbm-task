"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  X,
  Plus,
  Trash2,
  Paperclip,
  Download,
  Circle,
  CheckCircle2,
  MoreHorizontal,
  Calendar,
  Flag,
  Tag,
  MapPin,
  Repeat,
  Check,
  Users,
  Copy,
  Archive,
  ArchiveRestore,
  Share2,
  FolderInput,
  Users2,
  Coins,
} from "lucide-react";
import { format, addDays, startOfDay, differenceInCalendarDays } from "date-fns";
import { clsx } from "clsx";
import api from "@/lib/api";
import { PRIORITY_COLORS, TASK_STATUSES } from "@/lib/types";
import type {
  Task,
  ChecklistItem,
  Comment,
  Attachment,
  Project,
  WorkspaceMember,
  Resource,
  ResourceAssignment,
  TaskPriority,
  TaskRecurrence,
  TaskStatus,
} from "@/lib/types";
import { PRIORITY_OPTIONS, RECURRENCE_OPTIONS, LABEL_COLORS } from "@/lib/taskOptions";
import { useLabels } from "@/hooks/useLabels";
import { useOutsideClick } from "@/hooks/useOutsideClick";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import { Chip } from "@/components/tasks/Chip";

const EMPTY_MEMBERS: WorkspaceMember[] = [];
const EMPTY_PROJECTS: Project[] = [];
const EMPTY_RESOURCES: Resource[] = [];
const EMPTY_ASSIGNMENTS: ResourceAssignment[] = [];

function toLocalInputValue(date: Date) {
  return format(date, "yyyy-MM-dd'T'HH:mm");
}

type PropKey = "members" | "labels" | "date" | "priority" | "location" | null;

interface TaskUpdatePayload {
  title?: string;
  description?: string | null;
  priority?: TaskPriority;
  status?: TaskStatus;
  due_date?: string | null;
  start_date?: string | null;
  is_milestone?: boolean;
  recurrence?: TaskRecurrence;
  location?: string | null;
  assignee_id?: number | null;
  project_id?: number | null;
  is_archived?: boolean;
}

export function TaskDetailModal({ taskId, onClose }: { taskId: number; onClose: () => void }) {
  const qc = useQueryClient();
  const { currentWorkspaceId } = useWorkspaces();
  const [newChecklistTitle, setNewChecklistTitle] = useState("");
  const [newComment, setNewComment] = useState("");
  const [newLabelName, setNewLabelName] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [editingDescription, setEditingDescription] = useState(false);
  const [descDraft, setDescDraft] = useState("");

  const [openProp, setOpenProp] = useState<PropKey>(null);
  const propsRef = useOutsideClick<HTMLDivElement>(() => setOpenProp(null));

  const [menuOpen, setMenuOpen] = useState(false);
  const [menuView, setMenuView] = useState<"main" | "move" | "delete">("main");
  const [moveProjectId, setMoveProjectId] = useState<number | null>(null);
  const [moveStatus, setMoveStatus] = useState<TaskStatus>("todo");
  const [shareMessage, setShareMessage] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const menuRef = useOutsideClick<HTMLDivElement>(() => {
    setMenuOpen(false);
    setMenuView("main");
  });

  const { data: task } = useQuery<Task>({
    queryKey: ["task", taskId],
    queryFn: () => api.get(`/tasks/${taskId}`).then((r) => r.data),
  });

  const { data: subtasks = [] } = useQuery<Task[]>({
    queryKey: ["task", taskId, "subtasks"],
    queryFn: () => api.get(`/tasks/${taskId}/subtasks`).then((r) => r.data),
  });

  const { data: checklist = [] } = useQuery<ChecklistItem[]>({
    queryKey: ["task", taskId, "checklist"],
    queryFn: () => api.get(`/tasks/${taskId}/checklist`).then((r) => r.data),
  });

  const { data: comments = [] } = useQuery<Comment[]>({
    queryKey: ["task", taskId, "comments"],
    queryFn: () => api.get(`/tasks/${taskId}/comments`).then((r) => r.data),
  });

  const { data: attachments = [] } = useQuery<Attachment[]>({
    queryKey: ["task", taskId, "attachments"],
    queryFn: () => api.get(`/tasks/${taskId}/attachments`).then((r) => r.data),
  });

  const { data: project } = useQuery<Project>({
    queryKey: ["project", task?.project_id],
    queryFn: () => api.get(`/projects/${task!.project_id}`).then((r) => r.data),
    enabled: !!task?.project_id,
  });

  const effectiveWorkspaceId = project?.workspace_id ?? currentWorkspaceId;

  const { data: members = EMPTY_MEMBERS } = useQuery<WorkspaceMember[]>({
    queryKey: ["workspace-members", effectiveWorkspaceId],
    queryFn: () => api.get(`/workspaces/${effectiveWorkspaceId}/members`).then((r) => r.data),
    enabled: !!effectiveWorkspaceId,
  });

  const { data: moveProjects = EMPTY_PROJECTS } = useQuery<Project[]>({
    queryKey: ["projects", effectiveWorkspaceId],
    queryFn: () => api.get("/projects", { params: { workspace_id: effectiveWorkspaceId } }).then((r) => r.data),
    enabled: !!effectiveWorkspaceId,
  });

  const { labels, createLabel } = useLabels();

  const { data: workspaceResources = EMPTY_RESOURCES } = useQuery<Resource[]>({
    queryKey: ["resources", effectiveWorkspaceId],
    queryFn: () => api.get(`/workspaces/${effectiveWorkspaceId}/resources`).then((r) => r.data),
    enabled: !!effectiveWorkspaceId,
  });

  const { data: taskResources = EMPTY_ASSIGNMENTS } = useQuery<ResourceAssignment[]>({
    queryKey: ["task", taskId, "resources"],
    queryFn: () => api.get(`/tasks/${taskId}/resources`).then((r) => r.data),
  });

  const invalidate = (key: string) => qc.invalidateQueries({ queryKey: ["task", taskId, key] });
  const invalidateTask = () => {
    qc.invalidateQueries({ queryKey: ["task", taskId] });
    qc.invalidateQueries({ queryKey: ["tasks"] });
  };

  const updateTask = useMutation({
    mutationFn: (data: TaskUpdatePayload) => api.put(`/tasks/${taskId}`, data),
    onSuccess: invalidateTask,
  });

  const duplicateTask = useMutation({
    mutationFn: () => api.post(`/tasks/${taskId}/duplicate`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteTask = useMutation({
    mutationFn: () => api.delete(`/tasks/${taskId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDeleteError(msg || "Não foi possível excluir a tarefa. Tente novamente.");
    },
  });

  const attachLabel = useMutation({
    mutationFn: (labelId: number) => api.post(`/tasks/${taskId}/labels/${labelId}`),
    onSuccess: invalidateTask,
  });

  const detachLabel = useMutation({
    mutationFn: (labelId: number) => api.delete(`/tasks/${taskId}/labels/${labelId}`),
    onSuccess: invalidateTask,
  });

  const assignResource = useMutation({
    mutationFn: (resourceId: number) => api.post(`/tasks/${taskId}/resources`, { resource_id: resourceId }),
    onSuccess: () => invalidate("resources"),
  });

  const updateResourceAssignment = useMutation({
    mutationFn: ({ id, allocation_percent }: { id: number; allocation_percent: number }) =>
      api.put(`/tasks/${taskId}/resources/${id}`, { allocation_percent }),
    onSuccess: () => invalidate("resources"),
  });

  const removeResourceAssignment = useMutation({
    mutationFn: (id: number) => api.delete(`/tasks/${taskId}/resources/${id}`),
    onSuccess: () => invalidate("resources"),
  });

  const addChecklistItem = useMutation({
    mutationFn: (title: string) => api.post(`/tasks/${taskId}/checklist`, { title }),
    onSuccess: () => {
      invalidate("checklist");
      setNewChecklistTitle("");
    },
  });

  const toggleChecklistItem = useMutation({
    mutationFn: ({ id, is_completed }: { id: number; is_completed: boolean }) =>
      api.put(`/tasks/${taskId}/checklist/${id}`, { is_completed }),
    onSuccess: () => invalidate("checklist"),
  });

  const deleteChecklistItem = useMutation({
    mutationFn: (id: number) => api.delete(`/tasks/${taskId}/checklist/${id}`),
    onSuccess: () => invalidate("checklist"),
  });

  const addComment = useMutation({
    mutationFn: (content: string) => api.post(`/tasks/${taskId}/comments`, { content }),
    onSuccess: () => {
      invalidate("comments");
      setNewComment("");
    },
  });

  const uploadAttachment = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.post(`/tasks/${taskId}/attachments`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    },
    onSuccess: () => invalidate("attachments"),
  });

  const deleteAttachment = useMutation({
    mutationFn: (id: number) => api.delete(`/tasks/${taskId}/attachments/${id}`),
    onSuccess: () => invalidate("attachments"),
  });

  const downloadAttachment = async (id: number) => {
    const { data } = await api.get(`/tasks/${taskId}/attachments/${id}/download-url`);
    window.open(data.url, "_blank");
  };

  const completedCount = checklist.filter((c) => c.is_completed).length;
  const toggleProp = (key: Exclude<PropKey, null>) => setOpenProp((p) => (p === key ? null : key));

  const taskDurationDays =
    task?.start_date && task?.due_date && !task.is_milestone
      ? Math.max(differenceInCalendarDays(new Date(task.due_date), new Date(task.start_date)), 1)
      : 0;
  const totalResourceCost = taskResources.reduce(
    (sum, a) => sum + taskDurationDays * a.standard_rate * (a.allocation_percent / 100),
    0
  );
  const unassignedResources = workspaceResources.filter(
    (r) => !taskResources.some((a) => a.resource_id === r.id)
  );

  const saveTitle = () => {
    setEditingTitle(false);
    if (titleDraft.trim() && titleDraft.trim() !== task?.title) {
      updateTask.mutate({ title: titleDraft.trim() });
    }
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/dashboard/tasks/${taskId}`;
    try {
      await navigator.clipboard.writeText(url);
      setShareMessage("Link copiado!");
    } catch {
      setShareMessage("Não foi possível copiar o link.");
    }
    setMenuOpen(false);
    setTimeout(() => setShareMessage(""), 2500);
  };

  const handleMove = () => {
    updateTask.mutate({ project_id: moveProjectId, status: moveStatus });
    setMenuOpen(false);
    setMenuView("main");
  };

  const menuItemClass =
    "w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-surface-50 text-slate-700 text-left";

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex justify-end" onClick={onClose}>
      <div
        className="bg-white w-full max-w-xl h-full overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-30 bg-white border-b border-surface-200 px-6 py-4">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {task && (
                <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full border", PRIORITY_COLORS[task.priority])}>
                  {task.priority}
                </span>
              )}
              {editingTitle ? (
                <input
                  autoFocus
                  className="input mt-1 text-lg font-semibold"
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onBlur={saveTitle}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") saveTitle();
                    if (e.key === "Escape") setEditingTitle(false);
                  }}
                />
              ) : (
                <h2
                  className="font-semibold text-lg text-slate-900 mt-1 cursor-text hover:bg-surface-50 rounded px-1 -mx-1"
                  onClick={() => {
                    setTitleDraft(task?.title ?? "");
                    setEditingTitle(true);
                  }}
                >
                  {task?.title}
                </h2>
              )}
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setMenuOpen((v) => !v)}
                  className="text-slate-400 hover:text-slate-700 p-1.5 rounded hover:bg-surface-50"
                >
                  <MoreHorizontal size={18} />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 z-20 mt-1 w-56 bg-white border border-surface-200 rounded-lg shadow-lg p-1">
                    {menuView === "main" ? (
                      <>
                        <button
                          className={menuItemClass}
                          onClick={() => {
                            duplicateTask.mutate();
                            setMenuOpen(false);
                          }}
                        >
                          <Copy size={14} /> Duplicar
                        </button>
                        <button
                          className={menuItemClass}
                          onClick={() => {
                            setMoveProjectId(task?.project_id ?? null);
                            setMoveStatus(task?.status ?? "todo");
                            setMenuView("move");
                          }}
                        >
                          <FolderInput size={14} /> Mover
                        </button>
                        <button
                          className={menuItemClass}
                          onClick={() => {
                            updateTask.mutate({ is_archived: !task?.is_archived });
                            setMenuOpen(false);
                          }}
                        >
                          {task?.is_archived ? <ArchiveRestore size={14} /> : <Archive size={14} />}
                          {task?.is_archived ? "Desarquivar" : "Arquivar"}
                        </button>
                        <button className={menuItemClass} onClick={handleShare}>
                          <Share2 size={14} /> Compartilhar link
                        </button>
                        <div className="border-t border-surface-100 my-1" />
                        <button
                          className={clsx(menuItemClass, "text-red-600 hover:bg-red-50")}
                          onClick={() => setMenuView("delete")}
                        >
                          <Trash2 size={14} /> Excluir
                        </button>
                      </>
                    ) : menuView === "move" ? (
                      <div className="p-2 space-y-2">
                        <label className="block text-xs text-slate-400">Projeto</label>
                        <select
                          className="input text-sm py-1"
                          value={moveProjectId ?? ""}
                          onChange={(e) => setMoveProjectId(e.target.value ? Number(e.target.value) : null)}
                        >
                          <option value="">Sem projeto</option>
                          {moveProjects.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name}
                            </option>
                          ))}
                        </select>
                        <label className="block text-xs text-slate-400">Status</label>
                        <select
                          className="input text-sm py-1"
                          value={moveStatus}
                          onChange={(e) => setMoveStatus(e.target.value as TaskStatus)}
                        >
                          {TASK_STATUSES.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                        <div className="flex gap-2 pt-1">
                          <button className="btn-secondary flex-1 text-sm py-1" onClick={() => setMenuView("main")}>
                            Voltar
                          </button>
                          <button className="btn-primary flex-1 text-sm py-1" onClick={handleMove}>
                            Confirmar
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="p-3 space-y-3">
                        <p className="text-sm text-slate-700">Excluir esta tarefa permanentemente?</p>
                        {deleteError && (
                          <p className="text-xs text-red-600 bg-red-50 px-2 py-1.5 rounded">{deleteError}</p>
                        )}
                        <div className="flex gap-2">
                          <button
                            className="btn-secondary flex-1 text-sm py-1"
                            onClick={() => {
                              setMenuView("main");
                              setDeleteError("");
                            }}
                          >
                            Cancelar
                          </button>
                          <button
                            className="flex-1 text-sm py-1 rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
                            disabled={deleteTask.isPending}
                            onClick={() => {
                              setDeleteError("");
                              deleteTask.mutate();
                            }}
                          >
                            {deleteTask.isPending ? "Excluindo..." : "Excluir"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1.5">
                <X size={20} />
              </button>
            </div>
          </div>
          {shareMessage && <p className="text-xs text-green-600 mt-1">{shareMessage}</p>}
        </div>

        <div ref={propsRef} className="px-6 pt-4 flex flex-wrap gap-2">
          {task?.project_id && (
            <div className="relative">
              <Chip
                icon={<Users size={13} />}
                label={members.find((m) => m.user_id === task.assignee_id)?.full_name ?? "Membros"}
                active={!!task.assignee_id}
                onClick={() => toggleProp("members")}
              />
              {openProp === "members" && (
                <div className="absolute z-20 mt-1 w-56 bg-white border border-surface-200 rounded-lg shadow-lg p-1 max-h-64 overflow-y-auto">
                  {task.assignee_id && (
                    <button
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-surface-50 text-red-500 text-left"
                      onClick={() => {
                        updateTask.mutate({ assignee_id: null });
                        setOpenProp(null);
                      }}
                    >
                      Remover responsável
                    </button>
                  )}
                  {members.map((m) => (
                    <button
                      key={m.id}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-surface-50"
                      onClick={() => {
                        updateTask.mutate({ assignee_id: m.user_id });
                        setOpenProp(null);
                      }}
                    >
                      <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                        {m.full_name.charAt(0).toUpperCase()}
                      </span>
                      <span className="flex-1 text-left truncate">{m.full_name}</span>
                      {task.assignee_id === m.user_id && <Check size={14} className="text-primary-600" />}
                    </button>
                  ))}
                  {members.length === 0 && (
                    <p className="text-xs text-slate-400 px-3 py-2">Nenhum membro na área de trabalho.</p>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="relative">
            <Chip
              icon={<Tag size={13} />}
              label={task && task.labels.length > 0 ? `${task.labels.length} etiqueta(s)` : "Etiquetas"}
              active={!!task && task.labels.length > 0}
              onClick={() => toggleProp("labels")}
            />
            {openProp === "labels" && (
              <div className="absolute z-20 mt-1 w-56 bg-white border border-surface-200 rounded-lg shadow-lg p-2 space-y-1 max-h-64 overflow-y-auto">
                {labels.length === 0 && <p className="text-xs text-slate-400 px-2 py-1">Nenhuma etiqueta ainda.</p>}
                {labels.map((l) => {
                  const checked = task?.labels.some((tl) => tl.id === l.id) ?? false;
                  return (
                    <label
                      key={l.id}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-50 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => (checked ? detachLabel.mutate(l.id) : attachLabel.mutate(l.id))}
                      />
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: l.color }} />
                      <span className="flex-1 truncate">{l.name}</span>
                    </label>
                  );
                })}
                <div className="border-t border-surface-100 pt-2 mt-1 flex gap-1">
                  <input
                    className="input text-sm flex-1 py-1"
                    placeholder="Nova etiqueta"
                    value={newLabelName}
                    onChange={(e) => setNewLabelName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && newLabelName.trim()) {
                        createLabel.mutate(
                          { name: newLabelName.trim(), color: LABEL_COLORS[labels.length % LABEL_COLORS.length] },
                          {
                            onSuccess: (label) => {
                              attachLabel.mutate(label.id);
                              setNewLabelName("");
                            },
                          }
                        );
                      }
                    }}
                  />
                  <button
                    className="btn-secondary px-2 py-1"
                    disabled={!newLabelName.trim() || createLabel.isPending}
                    onClick={() =>
                      createLabel.mutate(
                        { name: newLabelName.trim(), color: LABEL_COLORS[labels.length % LABEL_COLORS.length] },
                        {
                          onSuccess: (label) => {
                            attachLabel.mutate(label.id);
                            setNewLabelName("");
                          },
                        }
                      )
                    }
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="relative">
            <Chip
              icon={<Calendar size={13} />}
              label={task?.due_date ? format(new Date(task.due_date), "dd/MM HH:mm") : "Data"}
              active={!!task?.due_date}
              onClick={() => toggleProp("date")}
            />
            {openProp === "date" && (
              <div className="absolute z-20 mt-1 w-64 bg-white border border-surface-200 rounded-lg shadow-lg p-3 space-y-2">
                <div className="grid grid-cols-1 gap-0.5">
                  <button
                    className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 flex items-center gap-2"
                    onClick={() => {
                      updateTask.mutate({ due_date: startOfDay(new Date()).toISOString() });
                      setOpenProp(null);
                    }}
                  >
                    <Calendar size={14} className="text-green-600" /> Hoje
                  </button>
                  <button
                    className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 flex items-center gap-2"
                    onClick={() => {
                      updateTask.mutate({ due_date: startOfDay(addDays(new Date(), 1)).toISOString() });
                      setOpenProp(null);
                    }}
                  >
                    <Calendar size={14} className="text-orange-500" /> Amanhã
                  </button>
                  <button
                    className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 flex items-center gap-2"
                    onClick={() => {
                      updateTask.mutate({ due_date: startOfDay(addDays(new Date(), 7)).toISOString() });
                      setOpenProp(null);
                    }}
                  >
                    <Calendar size={14} className="text-blue-500" /> Próxima semana
                  </button>
                </div>
                <div className="border-t border-surface-100 pt-2">
                  <label className="block text-xs text-slate-400 mb-1">Data e hora personalizada (fim)</label>
                  <input
                    type="datetime-local"
                    className="input text-sm py-1"
                    defaultValue={task?.due_date ? toLocalInputValue(new Date(task.due_date)) : ""}
                    onBlur={(e) =>
                      updateTask.mutate({ due_date: e.target.value ? new Date(e.target.value).toISOString() : null })
                    }
                  />
                </div>
                <div className="border-t border-surface-100 pt-2">
                  <label className="block text-xs text-slate-400 mb-1">Data de início (Gantt)</label>
                  <input
                    type="datetime-local"
                    className="input text-sm py-1"
                    defaultValue={task?.start_date ? toLocalInputValue(new Date(task.start_date)) : ""}
                    onBlur={(e) =>
                      updateTask.mutate({ start_date: e.target.value ? new Date(e.target.value).toISOString() : null })
                    }
                  />
                </div>
                <div className="border-t border-surface-100 pt-2">
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={task?.is_milestone ?? false}
                      onChange={(e) => updateTask.mutate({ is_milestone: e.target.checked })}
                    />
                    É um marco (milestone)
                  </label>
                </div>
                <div className="border-t border-surface-100 pt-2">
                  <label className="text-xs text-slate-400 mb-1 flex items-center gap-1">
                    <Repeat size={12} /> Repetir
                  </label>
                  <select
                    className="input text-sm py-1"
                    value={task?.recurrence ?? "none"}
                    onChange={(e) => updateTask.mutate({ recurrence: e.target.value as TaskRecurrence })}
                  >
                    {RECURRENCE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-between items-center pt-1">
                  {task?.due_date ? (
                    <button
                      className="text-xs text-red-500 hover:underline"
                      onClick={() => {
                        updateTask.mutate({ due_date: null, recurrence: "none" });
                        setOpenProp(null);
                      }}
                    >
                      Remover data
                    </button>
                  ) : (
                    <span />
                  )}
                  <button className="text-xs text-primary-600 hover:underline" onClick={() => setOpenProp(null)}>
                    Concluir
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="relative">
            <Chip
              icon={<Flag size={13} />}
              label={task?.priority ?? "P4"}
              active={!!task && task.priority !== "P4"}
              onClick={() => toggleProp("priority")}
            />
            {openProp === "priority" && (
              <div className="absolute z-20 mt-1 w-52 bg-white border border-surface-200 rounded-lg shadow-lg p-1">
                {PRIORITY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-surface-50"
                    onClick={() => {
                      updateTask.mutate({ priority: opt.value });
                      setOpenProp(null);
                    }}
                  >
                    <span className={clsx("w-2.5 h-2.5 rounded-full flex-shrink-0", opt.dot)} />
                    <span className="flex-1 text-left">{opt.label}</span>
                    {task?.priority === opt.value && <Check size={14} className="text-primary-600" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="relative">
            <Chip
              icon={<MapPin size={13} />}
              label={task?.location || "Local"}
              active={!!task?.location}
              onClick={() => toggleProp("location")}
            />
            {openProp === "location" && (
              <div className="absolute z-20 mt-1 w-56 bg-white border border-surface-200 rounded-lg shadow-lg p-3">
                <input
                  autoFocus
                  className="input text-sm py-1"
                  placeholder="Endereço ou local"
                  defaultValue={task?.location ?? ""}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      updateTask.mutate({ location: (e.target as HTMLInputElement).value.trim() || null });
                      setOpenProp(null);
                    }
                  }}
                  onBlur={(e) => updateTask.mutate({ location: e.target.value.trim() || null })}
                />
              </div>
            )}
          </div>
        </div>

        <div className="p-6 space-y-8">
          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Descrição</h3>
            {editingDescription ? (
              <div className="space-y-2">
                <textarea
                  autoFocus
                  rows={4}
                  className="input text-sm"
                  value={descDraft}
                  onChange={(e) => setDescDraft(e.target.value)}
                />
                <div className="flex gap-2">
                  <button
                    className="btn-primary text-sm py-1"
                    onClick={() => {
                      updateTask.mutate({ description: descDraft.trim() || null });
                      setEditingDescription(false);
                    }}
                  >
                    Salvar
                  </button>
                  <button className="btn-secondary text-sm py-1" onClick={() => setEditingDescription(false)}>
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <p
                className={clsx(
                  "text-sm rounded px-2 py-1.5 -mx-2 cursor-text hover:bg-surface-50",
                  task?.description ? "text-slate-600" : "text-slate-400"
                )}
                onClick={() => {
                  setDescDraft(task?.description ?? "");
                  setEditingDescription(true);
                }}
              >
                {task?.description || "Adicionar descrição..."}
              </p>
            )}
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <Users2 size={14} /> Recursos {taskResources.length > 0 && `(${taskResources.length})`}
              {totalResourceCost > 0 && (
                <span className="text-xs font-normal text-slate-400 flex items-center gap-1 ml-auto">
                  <Coins size={12} /> R$ {totalResourceCost.toFixed(2)}
                </span>
              )}
            </h3>
            {taskResources.length === 0 ? (
              <p className="text-sm text-slate-400 mb-2">Nenhum recurso atribuído.</p>
            ) : (
              <div className="space-y-2 mb-3">
                {taskResources.map((a) => (
                  <div key={a.id} className="flex items-center gap-2 text-sm">
                    <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                      {a.resource_name.charAt(0).toUpperCase()}
                    </span>
                    <span className="flex-1 truncate">{a.resource_name}</span>
                    <input
                      type="number"
                      min={0}
                      max={200}
                      className="input w-16 text-xs py-1"
                      value={a.allocation_percent}
                      onChange={(e) =>
                        updateResourceAssignment.mutate({ id: a.id, allocation_percent: Number(e.target.value) })
                      }
                    />
                    <span className="text-xs text-slate-400">%</span>
                    <button
                      onClick={() => removeResourceAssignment.mutate(a.id)}
                      className="text-slate-300 hover:text-red-500 p-1"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {unassignedResources.length > 0 && (
              <select
                className="input text-sm"
                value=""
                onChange={(e) => {
                  if (e.target.value) assignResource.mutate(Number(e.target.value));
                }}
              >
                <option value="">+ Atribuir recurso...</option>
                {unassignedResources.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            )}
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Checklist {checklist.length > 0 && `(${completedCount}/${checklist.length})`}
            </h3>
            <div className="space-y-1.5">
              {checklist.map((item) => (
                <div key={item.id} className="flex items-center gap-2 group">
                  <button
                    onClick={() => toggleChecklistItem.mutate({ id: item.id, is_completed: !item.is_completed })}
                    className="text-slate-400 hover:text-primary-600 flex-shrink-0"
                  >
                    {item.is_completed ? <CheckCircle2 size={18} className="text-green-500" /> : <Circle size={18} />}
                  </button>
                  <span className={clsx("flex-1 text-sm", item.is_completed && "line-through text-slate-400")}>
                    {item.title}
                  </span>
                  <button
                    onClick={() => deleteChecklistItem.mutate(item.id)}
                    className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3">
              <input
                className="input flex-1"
                placeholder="Adicionar item..."
                value={newChecklistTitle}
                onChange={(e) => setNewChecklistTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newChecklistTitle.trim()) {
                    addChecklistItem.mutate(newChecklistTitle.trim());
                  }
                }}
              />
              <button
                className="btn-secondary px-3"
                disabled={!newChecklistTitle.trim()}
                onClick={() => addChecklistItem.mutate(newChecklistTitle.trim())}
              >
                <Plus size={16} />
              </button>
            </div>
          </section>

          {subtasks.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Subtarefas ({subtasks.length})</h3>
              <div className="space-y-1.5">
                {subtasks.map((s) => (
                  <div key={s.id} className="flex items-center gap-2 text-sm">
                    {s.is_completed ? (
                      <CheckCircle2 size={16} className="text-green-500" />
                    ) : (
                      <Circle size={16} className="text-slate-400" />
                    )}
                    <span className={clsx(s.is_completed && "line-through text-slate-400")}>{s.title}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Anexos ({attachments.length})</h3>
            <div className="space-y-1.5">
              {attachments.map((a) => (
                <div key={a.id} className="flex items-center gap-2 text-sm group">
                  <Paperclip size={14} className="text-slate-400 flex-shrink-0" />
                  <span className="flex-1 truncate">{a.filename}</span>
                  <button onClick={() => downloadAttachment(a.id)} className="text-slate-400 hover:text-primary-600">
                    <Download size={14} />
                  </button>
                  <button
                    onClick={() => deleteAttachment.mutate(a.id)}
                    className="text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadAttachment.mutate(file);
                e.target.value = "";
              }}
            />
            <button
              className="btn-secondary mt-3 flex items-center gap-2"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadAttachment.isPending}
            >
              <Paperclip size={14} /> {uploadAttachment.isPending ? "Enviando..." : "Anexar arquivo"}
            </button>
          </section>

          <section>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Comentários ({comments.length})</h3>
            <div className="space-y-3">
              {comments.map((c) => (
                <div key={c.id} className="bg-surface-50 rounded-lg p-3 text-sm">
                  <p className="text-slate-700 whitespace-pre-wrap">{c.content}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    {new Date(c.created_at).toLocaleString("pt-BR")}
                  </p>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-3">
              <input
                className="input flex-1"
                placeholder="Escreva um comentário... (@email para mencionar)"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && newComment.trim()) {
                    addComment.mutate(newComment.trim());
                  }
                }}
              />
              <button
                className="btn-primary px-3"
                disabled={!newComment.trim() || addComment.isPending}
                onClick={() => addComment.mutate(newComment.trim())}
              >
                Enviar
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
