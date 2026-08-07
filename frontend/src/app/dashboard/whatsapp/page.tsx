"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Loader2, Unplug, Sparkles, Send, ArrowLeft, FolderOpen } from "lucide-react";
import { clsx } from "clsx";
import api from "@/lib/api";
import { useWorkspaces } from "@/hooks/useWorkspaces";
import type { WhatsAppStatus, WhatsAppChatSummary, WhatsAppMessage, TaskSuggestion } from "@/lib/types";

const EMPTY_CHATS: WhatsAppChatSummary[] = [];
const EMPTY_MESSAGES: WhatsAppMessage[] = [];
const SUGGESTIONS_KEY = "whatsapp_suggestions";

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

function extractErrorMessage(err: unknown, fallback: string): string {
  const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return msg || fallback;
}

export default function WhatsAppPage() {
  const qc = useQueryClient();
  const router = useRouter();
  const { currentWorkspaceId } = useWorkspaces();
  const [error, setError] = useState("");
  const [selectedChat, setSelectedChat] = useState<WhatsAppChatSummary | null>(null);
  const [mobileShowThread, setMobileShowThread] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

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

  const { data: chats = EMPTY_CHATS } = useQuery<WhatsAppChatSummary[]>({
    queryKey: ["whatsapp-chats"],
    queryFn: () => api.get("/whatsapp/chats").then((r) => r.data),
    enabled: status?.status === "connected",
    refetchInterval: status?.status === "connected" ? 4000 : false,
  });

  const { data: messages = EMPTY_MESSAGES } = useQuery<WhatsAppMessage[]>({
    queryKey: ["whatsapp-messages", selectedChat?.jid],
    queryFn: () => api.get("/whatsapp/messages", { params: { chat_jid: selectedChat!.jid } }).then((r) => r.data),
    enabled: status?.status === "connected" && !!selectedChat,
    refetchInterval: status?.status === "connected" && selectedChat ? 3000 : false,
  });

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    setSelectedIds(new Set());
  }, [selectedChat?.jid]);

  const connectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/connect"),
    onSuccess: () => {
      setError("");
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível conectar ao WhatsApp.")),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => api.post("/whatsapp/disconnect"),
    onSuccess: () => {
      setError("");
      setSelectedChat(null);
      setMobileShowThread(false);
      qc.invalidateQueries({ queryKey: ["whatsapp-status"] });
      qc.removeQueries({ queryKey: ["whatsapp-chats"] });
      qc.removeQueries({ queryKey: ["whatsapp-messages"] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível desconectar o WhatsApp.")),
  });

  const sendMutation = useMutation({
    mutationFn: (text: string) => api.post("/whatsapp/send", { chat_jid: selectedChat!.jid, text }),
    onSuccess: () => {
      setError("");
      setDraft("");
      qc.invalidateQueries({ queryKey: ["whatsapp-messages", selectedChat?.jid] });
    },
    onError: (err: unknown) => setError(extractErrorMessage(err, "Não foi possível enviar a mensagem.")),
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api
        .post<TaskSuggestion[]>("/whatsapp/analyze", {
          workspace_id: currentWorkspaceId,
          message_ids: Array.from(selectedIds),
        })
        .then((r) => r.data),
    onSuccess: (suggestions) => {
      setError("");
      sessionStorage.setItem(SUGGESTIONS_KEY, JSON.stringify(suggestions));
      qc.invalidateQueries({ queryKey: ["whatsapp-chats"] });
      qc.invalidateQueries({ queryKey: ["whatsapp-messages", selectedChat?.jid] });
      router.push("/dashboard/ai-tasks");
    },
    onError: (err: unknown) =>
      setError(extractErrorMessage(err, "Não foi possível analisar as mensagens selecionadas.")),
  });

  const sortedChats = useMemo(
    () =>
      [...chats].sort((a, b) => {
        const at = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const bt = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return bt - at;
      }),
    [chats]
  );

  function toggleMessage(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function openChat(chat: WhatsAppChatSummary) {
    setSelectedChat(chat);
    setMobileShowThread(true);
  }

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
      <div>
        <PageHeader />
        {errorBanner}
        <div className="card p-8 flex flex-col items-center gap-3 text-center">
          <MessageCircle size={32} className="text-green-600" />
          <p className="text-sm text-slate-600 dark:text-slate-300 max-w-sm">
            Conecte seu WhatsApp para ler suas conversas, responder e transformar mensagens em tarefas com IA.
          </p>
          <button
            className="btn-primary text-sm flex items-center gap-1.5 mt-1"
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
      </div>
    );
  }

  if (status.status === "connecting" || status.status === "qr_pending") {
    return (
      <div>
        <PageHeader />
        {errorBanner}
        <div className="card p-8 flex flex-col items-center gap-3 text-center">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Abra o WhatsApp no celular → Aparelhos conectados → Conectar um aparelho, e escaneie o código abaixo
          </p>
          {qr?.qr ? (
            <img src={qr.qr} alt="QR code do WhatsApp" className="w-56 h-56 rounded-lg border border-surface-200" />
          ) : (
            <div className="w-56 h-56 flex flex-col items-center justify-center gap-2 text-slate-400 text-xs text-center px-4">
              <Loader2 size={24} className="animate-spin" />
              Gerando código... isso pode levar alguns segundos
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader onDisconnect={() => disconnectMutation.mutate()} />
      {errorBanner}

      <div className="card overflow-hidden flex" style={{ height: "calc(100vh - 220px)", minHeight: 480 }}>
        <div
          className={clsx(
            "w-full lg:w-80 flex-shrink-0 border-r border-surface-200 dark:border-slate-700 overflow-y-auto",
            mobileShowThread ? "hidden lg:block" : "block"
          )}
        >
          {sortedChats.length === 0 ? (
            <p className="text-slate-400 text-sm p-4 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Aguardando conversas...
            </p>
          ) : (
            sortedChats.map((chat) => (
              <button
                key={chat.jid}
                onClick={() => openChat(chat)}
                className={clsx(
                  "w-full flex items-center gap-3 px-4 py-3 text-left border-b border-surface-100 dark:border-slate-800 hover:bg-surface-50 dark:hover:bg-slate-800/60 transition-colors",
                  selectedChat?.jid === chat.jid && "bg-surface-50 dark:bg-slate-800"
                )}
              >
                <div className="w-10 h-10 rounded-full bg-[#075e54] text-white flex items-center justify-center text-sm font-semibold shrink-0">
                  {initials(chat.name)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-slate-900 dark:text-white truncate">{chat.name}</span>
                    {chat.last_message_at && (
                      <span className="text-[10px] text-slate-400 shrink-0">{formatTime(chat.last_message_at)}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-slate-500 dark:text-slate-400 truncate">
                      {chat.last_message_text || "Sem mensagens ainda"}
                    </span>
                    {chat.pending_count > 0 && (
                      <span className="bg-green-600 text-white text-[10px] font-semibold rounded-full min-w-[18px] h-[18px] px-1 flex items-center justify-center shrink-0">
                        {chat.pending_count}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        <div className={clsx("flex-1 flex flex-col min-w-0", !mobileShowThread && "hidden lg:flex")}>
          {!selectedChat ? (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
              Selecione uma conversa para começar
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3 px-4 py-3 bg-[#075e54] text-white shrink-0">
                <button className="lg:hidden text-white/80" onClick={() => setMobileShowThread(false)}>
                  <ArrowLeft size={18} />
                </button>
                <div className="w-9 h-9 rounded-full bg-white/15 flex items-center justify-center text-sm font-semibold shrink-0">
                  {initials(selectedChat.name)}
                </div>
                <span className="text-sm font-semibold truncate">{selectedChat.name}</span>
              </div>

              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-2 bg-[#e5ddd5] dark:bg-slate-900"
                style={{ backgroundImage: "radial-gradient(rgba(0,0,0,0.04) 1px, transparent 1px)", backgroundSize: "16px 16px" }}
              >
                {messages.length === 0 ? (
                  <p className="m-auto text-slate-500 text-sm">Nenhuma mensagem ainda nessa conversa.</p>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className={clsx("flex items-end gap-2", msg.is_from_me && "justify-end")}>
                      {!msg.is_from_me && (
                        <input
                          type="checkbox"
                          className="w-4 h-4 accent-primary-600 mb-1 shrink-0"
                          checked={selectedIds.has(msg.id)}
                          onChange={() => toggleMessage(msg.id)}
                          title="Selecionar para criar tarefa"
                        />
                      )}
                      <div
                        className={clsx(
                          "max-w-[75%] rounded-lg px-3 py-1.5 shadow-sm text-sm",
                          msg.is_from_me
                            ? "bg-[#dcf8c6] dark:bg-green-700/40"
                            : selectedIds.has(msg.id)
                              ? "bg-white dark:bg-slate-700 ring-2 ring-primary-500"
                              : "bg-white dark:bg-slate-700"
                        )}
                      >
                        {!msg.is_from_me && (
                          <div className="text-xs font-semibold text-[#075e54] dark:text-green-400">
                            {msg.sender_name}
                          </div>
                        )}
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

              {selectedIds.size > 0 && (
                <div className="flex items-center justify-between gap-2 px-4 py-2 bg-primary-50 dark:bg-primary-600/10 border-t border-surface-200 dark:border-slate-700 shrink-0">
                  <span className="text-xs text-primary-700 dark:text-primary-400 font-medium">
                    {selectedIds.size} mensagem(ns) selecionada(s)
                  </span>
                  <button
                    className="btn-primary text-sm flex items-center gap-1.5"
                    disabled={!currentWorkspaceId || analyzeMutation.isPending}
                    onClick={() => analyzeMutation.mutate()}
                  >
                    {analyzeMutation.isPending ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Sparkles size={14} />
                    )}
                    Criar tarefas com IA
                  </button>
                </div>
              )}

              <form
                className="flex items-center gap-2 px-3 py-2.5 bg-surface-50 dark:bg-slate-800 border-t border-surface-200 dark:border-slate-700 shrink-0"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (draft.trim()) sendMutation.mutate(draft.trim());
                }}
              >
                <input
                  className="input flex-1 py-2"
                  placeholder="Digite uma mensagem..."
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={sendMutation.isPending}
                />
                <button
                  type="submit"
                  className="btn-primary p-2.5"
                  disabled={!draft.trim() || sendMutation.isPending}
                  title="Enviar"
                >
                  {sendMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
              </form>
            </>
          )}
        </div>
      </div>

      {!currentWorkspaceId && (
        <p className="text-slate-400 text-sm mt-4 flex items-center gap-1.5">
          <FolderOpen size={14} /> Selecione uma área de trabalho para criar tarefas a partir das mensagens.
        </p>
      )}
    </div>
  );
}

function PageHeader({ onDisconnect }: { onDisconnect?: () => void }) {
  return (
    <div className="mb-5 flex items-center justify-between">
      <div>
        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <MessageCircle size={22} className="text-green-600" /> WhatsApp
        </h1>
        <p className="text-slate-500 text-sm mt-0.5">
          Leia suas conversas, responda e escolha mensagens para virar tarefa com IA
        </p>
      </div>
      {onDisconnect && (
        <button
          className="text-slate-400 hover:text-red-500 p-2"
          title="Desconectar WhatsApp"
          onClick={onDisconnect}
        >
          <Unplug size={18} />
        </button>
      )}
    </div>
  );
}
