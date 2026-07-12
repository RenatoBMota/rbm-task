"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Zap, Power } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";

type TriggerEvent = "task_created" | "task_status_changed" | "task_completed" | "task_overdue" | "sla_breach";
type ActionType = "change_status" | "change_priority" | "notify_user" | "add_comment" | "send_email" | "webhook" | "whatsapp";

interface AutomationAction {
  type: ActionType;
  [key: string]: unknown;
}

interface AutomationRule {
  id: number;
  name: string;
  is_active: boolean;
  trigger_event: TriggerEvent;
  conditions: Record<string, unknown>;
  actions: AutomationAction[];
}

const TRIGGER_LABELS: Record<TriggerEvent, string> = {
  task_created: "Tarefa criada",
  task_status_changed: "Status alterado",
  task_completed: "Tarefa concluída",
  task_overdue: "Tarefa atrasada",
  sla_breach: "SLA estourado",
};

const ACTION_LABELS: Record<ActionType, string> = {
  change_status: "Mudar status",
  change_priority: "Mudar prioridade",
  notify_user: "Notificar responsável",
  add_comment: "Adicionar comentário",
  send_email: "Enviar e-mail",
  webhook: "Chamar webhook",
  whatsapp: "Enviar WhatsApp (em breve)",
};

function emptyAction(type: ActionType): AutomationAction {
  switch (type) {
    case "change_status":
      return { type, status: "in_progress" };
    case "change_priority":
      return { type, priority: "P1" };
    case "notify_user":
      return { type, message: "" };
    case "add_comment":
      return { type, content: "" };
    case "send_email":
      return { type, to: "", subject: "", body: "" };
    case "webhook":
      return { type, url: "" };
    case "whatsapp":
      return { type };
  }
}

export default function AutomationsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [triggerEvent, setTriggerEvent] = useState<TriggerEvent>("task_created");
  const [priorityCondition, setPriorityCondition] = useState("");
  const [actions, setActions] = useState<AutomationAction[]>([]);

  const { data: rules = [] } = useQuery<AutomationRule[]>({
    queryKey: ["automations"],
    queryFn: () => api.get("/automations/").then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.post("/automations/", {
        name,
        trigger_event: triggerEvent,
        conditions: priorityCondition ? { priority: priorityCondition } : {},
        actions,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["automations"] });
      setShowForm(false);
      setName("");
      setPriorityCondition("");
      setActions([]);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      api.put(`/automations/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/automations/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automations"] }),
  });

  const updateAction = (index: number, patch: Partial<AutomationAction>) => {
    setActions((prev) => prev.map((a, i) => (i === index ? { ...a, ...patch } : a)));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Automações</h1>
        <button className="btn-primary flex items-center gap-2" onClick={() => setShowForm(true)}>
          <Plus size={18} /> Nova Automação
        </button>
      </div>

      {showForm && (
        <div className="card p-6 mb-6 space-y-4">
          <h2 className="font-semibold">Nova regra: Se X acontecer → Faz Y</h2>
          <input
            className="input"
            placeholder="Nome da automação"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-xs text-slate-500 mb-1">Quando (gatilho)</label>
              <select
                className="input"
                value={triggerEvent}
                onChange={(e) => setTriggerEvent(e.target.value as TriggerEvent)}
              >
                {Object.entries(TRIGGER_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs text-slate-500 mb-1">Condição: prioridade (opcional)</label>
              <select
                className="input"
                value={priorityCondition}
                onChange={(e) => setPriorityCondition(e.target.value)}
              >
                <option value="">Qualquer prioridade</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
                <option value="P3">P3</option>
                <option value="P4">P4</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-2">Ações</label>
            <div className="space-y-2">
              {actions.map((action, index) => (
                <div key={index} className="flex items-center gap-2 bg-surface-50 rounded-lg p-2">
                  <span className="text-xs font-medium text-slate-600 w-40 flex-shrink-0">
                    {ACTION_LABELS[action.type]}
                  </span>
                  <ActionFields action={action} onChange={(patch) => updateAction(index, patch)} />
                  <button
                    onClick={() => setActions((prev) => prev.filter((_, i) => i !== index))}
                    className="text-slate-300 hover:text-red-500 ml-auto"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
            <select
              className="input mt-2"
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  setActions((prev) => [...prev, emptyAction(e.target.value as ActionType)]);
                }
              }}
            >
              <option value="">+ Adicionar ação</option>
              {Object.entries(ACTION_LABELS).map(([value, label]) => (
                <option key={value} value={value} disabled={value === "whatsapp"}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            <button
              className="btn-primary"
              disabled={!name || actions.length === 0 || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? "Criando..." : "Criar automação"}
            </button>
            <button className="btn-secondary" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
          </div>
        </div>
      )}

      {rules.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <Zap size={48} className="mx-auto mb-3 opacity-30" />
          <p>Nenhuma automação criada ainda.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="card p-4 flex items-center gap-4">
              <button
                onClick={() => toggleMutation.mutate({ id: rule.id, is_active: !rule.is_active })}
                className={clsx(
                  "p-2 rounded-lg flex-shrink-0",
                  rule.is_active ? "text-green-600 bg-green-50" : "text-slate-400 bg-surface-100"
                )}
              >
                <Power size={16} />
              </button>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-slate-900 truncate">{rule.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {TRIGGER_LABELS[rule.trigger_event]} → {rule.actions.map((a) => ACTION_LABELS[a.type]).join(", ")}
                </p>
              </div>
              <button
                onClick={() => deleteMutation.mutate(rule.id)}
                className="text-slate-300 hover:text-red-500 p-1"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ActionFields({
  action,
  onChange,
}: {
  action: AutomationAction;
  onChange: (patch: Partial<AutomationAction>) => void;
}) {
  switch (action.type) {
    case "change_status":
      return (
        <select
          className="input flex-1"
          value={action.status as string}
          onChange={(e) => onChange({ status: e.target.value })}
        >
          <option value="todo">A Fazer</option>
          <option value="in_progress">Em Progresso</option>
          <option value="in_review">Em Revisão</option>
          <option value="done">Concluído</option>
          <option value="cancelled">Cancelado</option>
        </select>
      );
    case "change_priority":
      return (
        <select
          className="input flex-1"
          value={action.priority as string}
          onChange={(e) => onChange({ priority: e.target.value })}
        >
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
          <option value="P4">P4</option>
        </select>
      );
    case "notify_user":
      return (
        <input
          className="input flex-1"
          placeholder="Mensagem da notificação"
          value={action.message as string}
          onChange={(e) => onChange({ message: e.target.value })}
        />
      );
    case "add_comment":
      return (
        <input
          className="input flex-1"
          placeholder="Conteúdo do comentário"
          value={action.content as string}
          onChange={(e) => onChange({ content: e.target.value })}
        />
      );
    case "send_email":
      return (
        <div className="flex-1 grid grid-cols-3 gap-2">
          <input
            className="input"
            placeholder="Para (e-mail)"
            value={action.to as string}
            onChange={(e) => onChange({ to: e.target.value })}
          />
          <input
            className="input"
            placeholder="Assunto"
            value={action.subject as string}
            onChange={(e) => onChange({ subject: e.target.value })}
          />
          <input
            className="input"
            placeholder="Corpo"
            value={action.body as string}
            onChange={(e) => onChange({ body: e.target.value })}
          />
        </div>
      );
    case "webhook":
      return (
        <input
          className="input flex-1"
          placeholder="https://..."
          value={action.url as string}
          onChange={(e) => onChange({ url: e.target.value })}
        />
      );
    case "whatsapp":
      return <span className="text-xs text-slate-400 flex-1">Configure o provedor de WhatsApp para habilitar</span>;
  }
}
