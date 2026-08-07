"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Loader2, Unplug, Sparkles } from "lucide-react";
import api from "@/lib/api";
import type { WhatsAppStatus, WhatsAppChat, WhatsAppMessage, TaskSuggestion } from "@/lib/types";

const EMPTY_CHATS: WhatsAppChat[] = [];
const EMPTY_MESSAGES: WhatsAppMessage[] = [];

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

export function WhatsAppPanel({
  workspaceId,
  onSuggestions,
}: {
  workspaceId: number | null;
  onSuggestions: (suggestions: TaskSuggestion[]) => void;
}) {
  const qc = useQueryClient();
  const [error, setError] = useState("");

  function extractErrorMessage(err: unknown, fallback: string): string {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    return msg || fallback;
  }

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

  const { data: messages = EMPTY_MESSAGES } = useQuery<WhatsAppMessage[]>({
    queryKey: ["whatsapp-messages"],
    queryFn: () => api.get("/whatsapp/messages").then((r) => r.data),
    enabled: status?.status === "connected" && !!status.monitored_chat_jid,
    refetchInterval: status?.status === "connected" && status.monitored_chat_jid ? 4000 : false,
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const connectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/connect"),
    onSuccess: () => {
      setError("");
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível conectar ao WhatsApp.")),
  });

  const monitorMutation = useMutation({
    mutationFn: (chat: WhatsAppChat) =>
      api.post("/whatsapp/monitor", { chat_jid: chat.jid, chat_name: chat.name }),
    onSuccess: () => {
      setError("");
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível selecionar essa conversa.")),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/disconnect"),
    onSuccess: () => {
      setError("");
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
      qc.removeQueries({ queryKey: ["whatsapp-chats"] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível desconectar o WhatsApp.")),
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.post<TaskSuggestion[]>("/whatsapp/analyze", { workspace_id: workspaceId }),
    onSuccess: (res) => {
      setError("");
      onSuggestions(res.data);
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
      qc.invalidateQueries({ queryKey: ["whatsapp-messages"] });
    },
    onError: (err: unknown) =>
      setError(extractErrorMessage(err, "Não foi possível analisar as mensagens do WhatsApp.")),
  });

  const errorBanner = error ? (
    <div className="card p-3 mb-4 flex items-center justify-between text-sm text-red-600 bg-red-50">
      <span>{error}</span>
      <button onClick={() => setError("")} className="text-red-400 hover:text-red-600 text-xs font-medium">
        Fechar
      </button>
    </div>
  ) : null;

  if (!status || status.status === "disconnected") {
    return (
      <>
        {errorBanner}
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
            {connectMutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <MessageCircle size={14} />
            )}
            Conectar WhatsApp
          </button>
        </div>
      </>
    );
  }

  if (status.status === "connecting" || status.status === "qr_pending") {
    return (
      <>
        {errorBanner}
        <div className="card p-4 mb-4 flex flex-col items-center gap-3 text-center">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Abra o WhatsApp no celular → Aparelhos conectados → Conectar um aparelho, e escaneie o código abaixo
          </p>
          {qr?.qr ? (
            <img src={qr.qr} alt="QR code do WhatsApp" className="w-48 h-48 rounded-lg border border-surface-200" />
          ) : (
            <div className="w-48 h-48 flex flex-col items-center justify-center gap-2 text-slate-400 text-xs text-center px-4">
              <Loader2 size={24} className="animate-spin" />
              Gerando código... isso pode levar alguns segundos
            </div>
          )}
        </div>
      </>
    );
  }

  if (status.status === "connected" && !status.monitored_chat_jid) {
    return (
      <>
        {errorBanner}
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
      </>
    );
  }

  return (
    <>
      {errorBanner}
      <div className="card mb-4 overflow-hidden">
        <div className="flex items-center justify-between gap-2 px-4 py-3 bg-[#075e54] text-white">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-full bg-white/15 flex items-center justify-center text-sm font-semibold shrink-0">
              {initials(status.monitored_chat_name || "?")}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate">{status.monitored_chat_name}</div>
              <div className="text-xs text-white/70">
                {status.phone_number ? `conectado como ${status.phone_number}` : "conectado"}
              </div>
            </div>
          </div>
          <button
            className="text-white/70 hover:text-white p-1.5 shrink-0"
            title="Desconectar WhatsApp"
            onClick={() => disconnectMutation.mutate()}
          >
            <Unplug size={16} />
          </button>
        </div>

        <div
          ref={scrollRef}
          className="h-72 overflow-y-auto px-4 py-3 flex flex-col gap-2 bg-[#e5ddd5] dark:bg-slate-900"
          style={{
            backgroundImage:
              "radial-gradient(rgba(0,0,0,0.04) 1px, transparent 1px)",
            backgroundSize: "16px 16px",
          }}
        >
          {messages.length === 0 ? (
            <p className="m-auto text-slate-500 text-sm flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Aguardando novas mensagens...
            </p>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className="flex">
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-1.5 shadow-sm text-sm ${
                    msg.is_processed
                      ? "bg-white/80 dark:bg-slate-700/80"
                      : "bg-white dark:bg-slate-700 ring-1 ring-green-400/60"
                  }`}
                >
                  <div className="text-xs font-semibold text-[#075e54] dark:text-green-400">
                    {msg.sender_name}
                  </div>
                  <div className="text-slate-800 dark:text-slate-100 whitespace-pre-wrap break-words">
                    {msg.text}
                  </div>
                  <div className="text-[10px] text-slate-400 text-right mt-0.5">
                    {formatTime(msg.whatsapp_timestamp)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between gap-2 px-4 py-2.5 bg-surface-50 dark:bg-slate-800 border-t border-surface-200 dark:border-slate-700">
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {status.pending_message_count} mensagem(ns) nova(s) para analisar
          </span>
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
        </div>
      </div>
    </>
  );
}
