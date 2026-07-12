"use client";

import { useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Plus, Trash2, Paperclip, Download, Circle, CheckCircle2 } from "lucide-react";
import api from "@/lib/api";
import { clsx } from "clsx";
import { PRIORITY_COLORS } from "@/lib/types";
import type { Task, ChecklistItem, Comment, Attachment } from "@/lib/types";

export function TaskDetailModal({ taskId, onClose }: { taskId: number; onClose: () => void }) {
  const qc = useQueryClient();
  const [newChecklistTitle, setNewChecklistTitle] = useState("");
  const [newComment, setNewComment] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    queryFn: () => api.get(`/tasks/${taskId}/checklist/`).then((r) => r.data),
  });

  const { data: comments = [] } = useQuery<Comment[]>({
    queryKey: ["task", taskId, "comments"],
    queryFn: () => api.get(`/tasks/${taskId}/comments/`).then((r) => r.data),
  });

  const { data: attachments = [] } = useQuery<Attachment[]>({
    queryKey: ["task", taskId, "attachments"],
    queryFn: () => api.get(`/tasks/${taskId}/attachments/`).then((r) => r.data),
  });

  const invalidate = (key: string) => qc.invalidateQueries({ queryKey: ["task", taskId, key] });

  const addChecklistItem = useMutation({
    mutationFn: (title: string) => api.post(`/tasks/${taskId}/checklist/`, { title }),
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
    mutationFn: (content: string) => api.post(`/tasks/${taskId}/comments/`, { content }),
    onSuccess: () => {
      invalidate("comments");
      setNewComment("");
    },
  });

  const uploadAttachment = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return api.post(`/tasks/${taskId}/attachments/`, formData, {
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

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex justify-end" onClick={onClose}>
      <div
        className="bg-white w-full max-w-xl h-full overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b border-surface-200 px-6 py-4 flex items-start justify-between">
          <div>
            {task && (
              <span className={clsx("text-xs font-medium px-2 py-0.5 rounded-full border", PRIORITY_COLORS[task.priority])}>
                {task.priority}
              </span>
            )}
            <h2 className="font-semibold text-lg text-slate-900 mt-1">{task?.title}</h2>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-8">
          {task?.description && <p className="text-sm text-slate-600">{task.description}</p>}

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
