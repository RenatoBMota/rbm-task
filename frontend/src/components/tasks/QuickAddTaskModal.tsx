"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Calendar, Flag, Bell, Tag, MapPin, Repeat, Plus, Check, Paperclip, X } from "lucide-react";
import { format, addDays, startOfDay, endOfDay } from "date-fns";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useLabels } from "@/hooks/useLabels";
import { useOutsideClick } from "@/hooks/useOutsideClick";
import { Chip } from "@/components/tasks/Chip";
import { PRIORITY_OPTIONS, RECURRENCE_OPTIONS, LABEL_COLORS } from "@/lib/taskOptions";
import type { Project, TaskPriority, TaskRecurrence, TaskStatus } from "@/lib/types";

type PopoverKey = "date" | "priority" | "reminder" | "labels" | "location" | null;

function toLocalInputValue(date: Date) {
  return format(date, "yyyy-MM-dd'T'HH:mm");
}

export function QuickAddTaskModal({
  onClose,
  projects,
  defaultProjectId,
  defaultStatus,
}: {
  onClose: () => void;
  projects: Project[];
  defaultProjectId?: number | null;
  defaultStatus?: TaskStatus;
}) {
  const qc = useQueryClient();
  const titleRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [openPopover, setOpenPopover] = useState<PopoverKey>(null);
  const chipsRef = useOutsideClick<HTMLDivElement>(() => setOpenPopover(null));

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("P4");
  const [dueDate, setDueDate] = useState("");
  const [recurrence, setRecurrence] = useState<TaskRecurrence>("none");
  const [reminderAt, setReminderAt] = useState("");
  const [location, setLocation] = useState("");
  const [labelIds, setLabelIds] = useState<number[]>([]);
  const [projectId, setProjectId] = useState<number | null>(defaultProjectId ?? null);
  const [newLabelName, setNewLabelName] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);

  const { labels, createLabel } = useLabels();

  useEffect(() => {
    titleRef.current?.focus();
  }, []);

  const createTask = useMutation({
    mutationFn: async () => {
      const { data: task } = await api.post("/tasks", {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        status: defaultStatus ?? "todo",
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        recurrence,
        location: location.trim() || null,
        project_id: projectId,
      });
      if (reminderAt) {
        await api.post(`/tasks/${task.id}/reminders`, {
          remind_at: new Date(reminderAt).toISOString(),
        });
      }
      for (const labelId of labelIds) {
        await api.post(`/tasks/${task.id}/labels/${labelId}`);
      }
      if (attachedFile) {
        const formData = new FormData();
        formData.append("file", attachedFile);
        await api.post(`/tasks/${task.id}/attachments`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      return task;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
  });

  const toggle = (key: Exclude<PopoverKey, null>) => setOpenPopover((p) => (p === key ? null : key));

  const submit = () => {
    if (title.trim() && !createTask.isPending) createTask.mutate();
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-start justify-center pt-24 px-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-surface-900 w-full max-w-lg rounded-xl shadow-xl border border-surface-200 dark:border-slate-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4">
          <textarea
            ref={titleRef}
            rows={1}
            placeholder="Nome da tarefa"
            className="w-full resize-none border-none text-base font-medium text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-0 p-0"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <textarea
            rows={2}
            placeholder="Descrição"
            className="w-full resize-none border-none text-sm text-slate-600 dark:text-slate-400 placeholder:text-slate-400 focus:outline-none focus:ring-0 p-0 mt-1"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <div ref={chipsRef} className="flex flex-wrap gap-2 mt-3">
            <div className="relative">
              <Chip
                icon={<Calendar size={13} />}
                label={dueDate ? format(new Date(dueDate), "dd/MM HH:mm") : "Data"}
                active={!!dueDate}
                onClick={() => toggle("date")}
              />
              {openPopover === "date" && (
                <div className="absolute z-20 mt-1 w-64 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-3 space-y-2">
                  <div className="grid grid-cols-1 gap-0.5">
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800 flex items-center gap-2"
                      onClick={() => {
                        setDueDate(toLocalInputValue(endOfDay(new Date())));
                        setOpenPopover(null);
                      }}
                    >
                      <Calendar size={14} className="text-green-600" /> Hoje
                    </button>
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800 flex items-center gap-2"
                      onClick={() => {
                        setDueDate(toLocalInputValue(endOfDay(addDays(new Date(), 1))));
                        setOpenPopover(null);
                      }}
                    >
                      <Calendar size={14} className="text-orange-500" /> Amanhã
                    </button>
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800 flex items-center gap-2"
                      onClick={() => {
                        setDueDate(toLocalInputValue(endOfDay(addDays(new Date(), 7))));
                        setOpenPopover(null);
                      }}
                    >
                      <Calendar size={14} className="text-blue-500" /> Próxima semana
                    </button>
                  </div>
                  <div className="border-t border-surface-100 dark:border-slate-800 pt-2">
                    <label className="block text-xs text-slate-400 mb-1">Data e hora personalizada</label>
                    <input
                      type="datetime-local"
                      className="input text-sm py-1"
                      value={dueDate}
                      onChange={(e) => setDueDate(e.target.value)}
                    />
                  </div>
                  <div className="border-t border-surface-100 dark:border-slate-800 pt-2">
                    <label className="text-xs text-slate-400 mb-1 flex items-center gap-1">
                      <Repeat size={12} /> Repetir
                    </label>
                    <select
                      className="input text-sm py-1"
                      value={recurrence}
                      onChange={(e) => setRecurrence(e.target.value as TaskRecurrence)}
                    >
                      {RECURRENCE_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="flex justify-between items-center pt-1">
                    {dueDate ? (
                      <button
                        className="text-xs text-red-500 hover:underline"
                        onClick={() => {
                          setDueDate("");
                          setRecurrence("none");
                        }}
                      >
                        Remover data
                      </button>
                    ) : (
                      <span />
                    )}
                    <button className="text-xs text-primary-600 hover:underline" onClick={() => setOpenPopover(null)}>
                      Concluir
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="relative">
              <Chip
                icon={<Flag size={13} />}
                label={priority === "P4" ? "Prioridade" : priority}
                active={priority !== "P4"}
                onClick={() => toggle("priority")}
              />
              {openPopover === "priority" && (
                <div className="absolute z-20 mt-1 w-52 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-1">
                  {PRIORITY_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-surface-50 hover:dark:bg-surface-800"
                      onClick={() => {
                        setPriority(opt.value);
                        setOpenPopover(null);
                      }}
                    >
                      <span className={clsx("w-2.5 h-2.5 rounded-full flex-shrink-0", opt.dot)} />
                      <span className="flex-1 text-left">{opt.label}</span>
                      {priority === opt.value && <Check size={14} className="text-primary-600" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="relative">
              <Chip
                icon={<Bell size={13} />}
                label={reminderAt ? format(new Date(reminderAt), "dd/MM HH:mm") : "Lembrete"}
                active={!!reminderAt}
                onClick={() => toggle("reminder")}
              />
              {openPopover === "reminder" && (
                <div className="absolute z-20 mt-1 w-64 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-3 space-y-2">
                  <div className="grid grid-cols-1 gap-0.5">
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800"
                      onClick={() => {
                        const d = new Date();
                        d.setHours(d.getHours() + 1);
                        setReminderAt(toLocalInputValue(d));
                        setOpenPopover(null);
                      }}
                    >
                      Daqui a 1 hora
                    </button>
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800"
                      onClick={() => {
                        const d = startOfDay(addDays(new Date(), 1));
                        d.setHours(9);
                        setReminderAt(toLocalInputValue(d));
                        setOpenPopover(null);
                      }}
                    >
                      Amanhã de manhã (9h)
                    </button>
                    <button
                      className="text-left text-sm px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800"
                      onClick={() => {
                        const d = startOfDay(addDays(new Date(), 7));
                        d.setHours(9);
                        setReminderAt(toLocalInputValue(d));
                        setOpenPopover(null);
                      }}
                    >
                      Semana que vem
                    </button>
                  </div>
                  <div className="border-t border-surface-100 dark:border-slate-800 pt-2">
                    <label className="block text-xs text-slate-400 mb-1">Data e hora personalizada</label>
                    <input
                      type="datetime-local"
                      className="input text-sm py-1"
                      value={reminderAt}
                      onChange={(e) => setReminderAt(e.target.value)}
                    />
                  </div>
                  <div className="flex justify-between items-center pt-1">
                    {reminderAt ? (
                      <button className="text-xs text-red-500 hover:underline" onClick={() => setReminderAt("")}>
                        Remover lembrete
                      </button>
                    ) : (
                      <span />
                    )}
                    <button className="text-xs text-primary-600 hover:underline" onClick={() => setOpenPopover(null)}>
                      Concluir
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="relative">
              <Chip
                icon={<Tag size={13} />}
                label={labelIds.length > 0 ? `${labelIds.length} etiqueta(s)` : "Etiquetas"}
                active={labelIds.length > 0}
                onClick={() => toggle("labels")}
              />
              {openPopover === "labels" && (
                <div className="absolute z-20 mt-1 w-56 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-2 space-y-1 max-h-64 overflow-y-auto">
                  {labels.length === 0 && (
                    <p className="text-xs text-slate-400 px-2 py-1">Nenhuma etiqueta ainda.</p>
                  )}
                  {labels.map((l) => (
                    <label
                      key={l.id}
                      className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-50 hover:dark:bg-surface-800 text-sm cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={labelIds.includes(l.id)}
                        onChange={(e) => {
                          setLabelIds((prev) =>
                            e.target.checked ? [...prev, l.id] : prev.filter((id) => id !== l.id)
                          );
                        }}
                      />
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: l.color }} />
                      <span className="flex-1 truncate">{l.name}</span>
                    </label>
                  ))}
                  <div className="border-t border-surface-100 dark:border-slate-800 pt-2 mt-1 flex gap-1 items-center">
                    <input
                      className="input text-sm flex-1 py-1"
                      placeholder="Nova etiqueta"
                      value={newLabelName}
                      onChange={(e) => setNewLabelName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && newLabelName.trim()) {
                          createLabel.mutate(
                            {
                              name: newLabelName.trim(),
                              color: LABEL_COLORS[labels.length % LABEL_COLORS.length],
                            },
                            {
                              onSuccess: (label) => {
                                setLabelIds((prev) => [...prev, label.id]);
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
                              setLabelIds((prev) => [...prev, label.id]);
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
                icon={<MapPin size={13} />}
                label={location || "Local"}
                active={!!location}
                onClick={() => toggle("location")}
              />
              {openPopover === "location" && (
                <div className="absolute z-20 mt-1 w-56 bg-white dark:bg-surface-900 border border-surface-200 dark:border-slate-700 rounded-lg shadow-lg p-3">
                  <input
                    autoFocus
                    className="input text-sm py-1"
                    placeholder="Endereço ou local"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") setOpenPopover(null);
                    }}
                  />
                </div>
              )}
            </div>

            <div className="flex items-center gap-1">
              <Chip
                icon={<Paperclip size={13} />}
                label={attachedFile ? attachedFile.name : "Anexo"}
                active={!!attachedFile}
                onClick={() => fileInputRef.current?.click()}
              />
              {attachedFile && (
                <button
                  type="button"
                  className="text-slate-300 hover:text-red-500"
                  onClick={() => {
                    setAttachedFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                >
                  <X size={14} />
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={(e) => setAttachedFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-surface-100 dark:border-slate-800">
          <select
            className="text-sm text-slate-600 dark:text-slate-400 bg-transparent border-none focus:outline-none focus:ring-0 cursor-pointer"
            value={projectId ?? ""}
            onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">📅 Agenda diária (sem projeto)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <div className="flex flex-col items-end gap-1">
            <div className="flex gap-2">
              <button className="btn-secondary" onClick={onClose}>
                Cancelar
              </button>
              <button className="btn-primary" disabled={!title.trim() || createTask.isPending} onClick={submit}>
                {createTask.isPending ? "Adicionando..." : "Adicionar tarefa"}
              </button>
            </div>
            {createTask.isError && (
              <p className="text-xs text-red-500">
                {(createTask.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
                  "Não foi possível salvar a tarefa. Tente novamente."}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
