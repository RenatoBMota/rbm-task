"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Loader2, Unplug, Sparkles } from "lucide-react";
import api from "@/lib/api";
import type { WhatsAppStatus, WhatsAppChat, TaskSuggestion } from "@/lib/types";

const EMPTY_CHATS: WhatsAppChat[] = [];

export function WhatsAppPanel({
  workspaceId,
  onSuggestions,
}: {
  workspaceId: number | null;
  onSuggestions: (suggestions: TaskSuggestion[]) => void;
}) {
  const qc = useQueryClient();
  const [analyzeError, setAnalyzeError] = useState("");

  const { data: status } = useQuery<WhatsAppStatus>({
    queryKey: ["whatsapp-status"],
    queryFn: () => api.get("/whatsapp/status").then((r) => r.data),
    refetchInterval: (query) => {
      const current = query.state.data?.status;
      return current === "connecting" || current === "qr_pending" ? 2000 : false;
    },
  });

  const { data: qr } = useQuery<{ qr: string | null }>({
    queryKey: ["whatsapp-qr"],
    queryFn: () => api.get("/whatsapp/qr").then((r) => r.data),
    enabled: status?.status === "connecting" || status?.status === "qr_pending",
    refetchInterval: 3000,
  });

  const { data: chats = EMPTY_CHATS } = useQuery<WhatsAppChat[]>({
    queryKey: ["whatsapp-chats"],
    queryFn: () => api.get("/whatsapp/chats").then((r) => r.data),
    enabled: status?.status === "connected",
    refetchInterval: status?.status === "connected" && !status.monitored_chat_jid ? 3000 : false,
  });

  const connectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/connect"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["whatsapp-status"] }),
  });

  const monitorMutation = useMutation({
    mutationFn: (chat: WhatsAppChat) =>
      api.post("/whatsapp/monitor", { chat_jid: chat.jid, chat_name: chat.name }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["whatsapp-status"] }),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/disconnect"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
      qc.removeQueries({ queryKey: ["whatsapp-chats"] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.post<TaskSuggestion[]>("/whatsapp/analyze", { workspace_id: workspaceId }),
    onSuccess: (res) => {
      setAnalyzeError("");
      onSuggestions(res.data);
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
    onError: (error: unknown) => {
      const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setAnalyzeError(msg || "Não foi possível analisar as mensagens do WhatsApp.");
    },
  });

  if (!status || status.status === "disconnected") {
    return (
      <div className="card p-4 mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <MessageCircle size={18} className="text-green-600" />
          Conecte o WhatsApp para sugerir tarefas a partir de uma conversa
        </div>
        <button
          className="btn-secondary text-sm flex items-center gap-1.5"
          disabled={connectMutation.isPending}
          onClick={() => connectMutation.mutate()}
        >
          {connectMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <MessageCircle size={14} />}
          Conectar WhatsApp
        </button>
      </div>
    );
  }

  if (status.status === "connecting" || status.status === "qr_pending") {
    return (
      <div className="card p-4 mb-4 flex flex-col items-center gap-3 text-center">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Abra o WhatsApp no celular → Aparelhos conectados → Conectar um aparelho, e escaneie o código abaixo
        </p>
        {qr?.qr ? (
          <img src={qr.qr} alt="QR code do WhatsApp" className="w-48 h-48 rounded-lg border border-surface-200" />
        ) : (
          <div className="w-48 h-48 flex items-center justify-center text-slate-400">
            <Loader2 size={24} className="animate-spin" />
          </div>
        )}
      </div>
    );
  }

  if (status.status === "connected" && !status.monitored_chat_jid) {
    return (
      <div className="card p-4 mb-4">
        <p className="text-sm text-slate-600 dark:text-slate-300 mb-3">
          WhatsApp conectado{status.phone_number ? ` (${status.phone_number})` : ""}. Escolha qual conversa a IA
          deve acompanhar:
        </p>
        {chats.length === 0 ? (
          <p className="text-slate-400 text-sm flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" /> Aguardando mensagens para listar as conversas...
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {chats.map((chat) => (
              <button
                key={chat.jid}
                className="btn-secondary text-sm"
                disabled={monitorMutation.isPending}
                onClick={() => monitorMutation.mutate(chat)}
              >
                {chat.name}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="card p-4 mb-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <MessageCircle size={16} className="text-green-600" />
          <span>
            <strong className="text-slate-900 dark:text-white">{status.monitored_chat_name}</strong>
            {" · "}
            {status.pending_message_count} mensagem(ns) nova(s)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="btn-primary text-sm flex items-center gap-1.5"
            disabled={status.pending_message_count === 0 || !workspaceId || analyzeMutation.isPending}
            onClick={() => analyzeMutation.mutate()}
          >
            {analyzeMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Sparkles size={14} />
            )}
            Analisar mensagens do WhatsApp
          </button>
          <button
            className="text-slate-300 hover:text-red-500 p-1.5"
            title="Desconectar WhatsApp"
            onClick={() => disconnectMutation.mutate()}
          >
            <Unplug size={16} />
          </button>
        </div>
      </div>
      {analyzeError && <p className="text-sm text-red-600 mt-2">{analyzeError}</p>}
    </div>
  );
}
