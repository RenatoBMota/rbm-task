import express from "express";
import qrcode from "qrcode";
import axios from "axios";
import pino from "pino";
import { Boom } from "@hapi/boom";
import baileys, { useMultiFileAuthState, DisconnectReason } from "@whiskeysockets/baileys";

const makeWASocket = baileys.default ?? baileys;

const PORT = process.env.PORT || 4000;
const SESSIONS_DIR = process.env.SESSIONS_DIR || "/app/sessions";
const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const WEBHOOK_SECRET = process.env.WHATSAPP_WEBHOOK_SECRET || "";

const logger = pino({ level: process.env.LOG_LEVEL || "warn" });

/** userId (string) -> { sock, status, qr, phone, chats: Map<jid, name> } */
const sessions = new Map();

function getSession(userId) {
  return sessions.get(String(userId));
}

function chatDisplayName(jid, pushName) {
  if (jid.endsWith("@g.us")) return pushName || jid.split("@")[0];
  return pushName || jid.split("@")[0];
}

async function forwardMessage(userId, chatJid, chatName, sender, text, timestamp, fromMe) {
  if (!text) return;
  try {
    await axios.post(
      `${BACKEND_URL}/api/v1/whatsapp/webhook/message`,
      {
        user_id: Number(userId),
        chat_jid: chatJid,
        chat_name: chatName,
        sender,
        text,
        timestamp,
        from_me: fromMe,
      },
      { headers: { "X-Webhook-Secret": WEBHOOK_SECRET }, timeout: 10000 }
    );
  } catch (err) {
    logger.error({ err: err.message }, "failed to forward message to backend");
  }
}

async function startSession(userId) {
  const key = String(userId);
  const existing = sessions.get(key);
  // Also guard "connecting": a second concurrent socket sharing the same
  // auth-state files makes WhatsApp see two devices authenticating as one
  // and kill the session with a "device_removed" conflict.
  if (existing && (existing.status === "connected" || existing.status === "connecting" || existing.status === "qr_pending")) {
    return existing;
  }

  const session = { sock: null, status: "connecting", qr: null, phone: null, chats: new Map() };
  sessions.set(key, session);

  const { state, saveCreds } = await useMultiFileAuthState(`${SESSIONS_DIR}/${key}`);
  const sock = makeWASocket({ auth: state, logger, printQRInTerminal: false });
  session.sock = sock;

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      session.status = "qr_pending";
      session.qr = await qrcode.toDataURL(qr);
    }

    if (connection === "open") {
      session.status = "connected";
      session.qr = null;
      session.phone = sock.user?.id?.split(":")[0] ?? null;
      console.log(`[wa:${key}] connected as ${session.phone}`);
    }

    if (connection === "close") {
      const statusCode = lastDisconnect?.error instanceof Boom ? lastDisconnect.error.output?.statusCode : null;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      session.status = "disconnected";
      session.qr = null;
      if (!loggedOut) {
        startSession(key).catch((err) => logger.error({ err: err.message }, "reconnect failed"));
      } else {
        sessions.delete(key);
      }
    }
  });

  sock.ev.on("chats.upsert", (chats) => {
    console.log(`[wa:${key}] chats.upsert: ${chats.length} chat(s)`);
    for (const chat of chats) {
      if (chat.id && (chat.name || !session.chats.has(chat.id))) {
        session.chats.set(chat.id, chat.name || chatDisplayName(chat.id));
      }
    }
  });

  // The bulk list of a user's existing conversations arrives here (not via
  // chats.upsert, which only fires for individual chat updates) right after
  // the QR scan, as WhatsApp syncs recent chat history to this device.
  sock.ev.on("messaging-history.set", ({ chats, contacts }) => {
    console.log(`[wa:${key}] messaging-history.set: ${chats?.length ?? 0} chat(s), ${contacts?.length ?? 0} contact(s)`);
    const nameByJid = new Map((contacts || []).map((c) => [c.id, c.name || c.notify]));
    for (const chat of chats || []) {
      if (!chat.id) continue;
      const name = chat.name || nameByJid.get(chat.id);
      if (name || !session.chats.has(chat.id)) {
        session.chats.set(chat.id, name || chatDisplayName(chat.id));
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || !msg.key.remoteJid) continue;
      const chatJid = msg.key.remoteJid;
      const text =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        msg.message.imageMessage?.caption ||
        "";
      if (!text) continue;

      const fromMe = !!msg.key.fromMe;
      const sender = fromMe ? "Você" : msg.pushName || "Desconhecido";
      if (!session.chats.has(chatJid)) {
        session.chats.set(chatJid, chatDisplayName(chatJid, chatJid.endsWith("@g.us") ? null : sender));
      }
      const chatName = session.chats.get(chatJid);

      await forwardMessage(key, chatJid, chatName, sender, text, msg.messageTimestamp, fromMe);
    }
  });

  return session;
}

const app = express();
app.use(express.json());

app.post("/connect/:userId", async (req, res) => {
  try {
    await startSession(req.params.userId);
    res.json({ ok: true });
  } catch (err) {
    logger.error({ err: err.message }, "connect failed");
    res.status(500).json({ error: "failed to start session" });
  }
});

app.get("/status/:userId", (req, res) => {
  const session = getSession(req.params.userId);
  if (!session) return res.json({ status: "disconnected", phone: null });
  res.json({ status: session.status, phone: session.phone });
});

app.get("/qr/:userId", (req, res) => {
  const session = getSession(req.params.userId);
  res.json({ qr: session?.qr ?? null });
});

app.get("/chats/:userId", (req, res) => {
  const session = getSession(req.params.userId);
  if (!session) return res.json({ chats: [] });
  const chats = Array.from(session.chats.entries()).map(([jid, name]) => ({ jid, name }));
  res.json({ chats });
});

app.post("/send/:userId", async (req, res) => {
  const session = getSession(req.params.userId);
  const { jid, text } = req.body || {};
  if (!session?.sock || session.status !== "connected") {
    return res.status(409).json({ error: "session not connected" });
  }
  if (!jid || !text) {
    return res.status(400).json({ error: "jid and text are required" });
  }
  try {
    await session.sock.sendMessage(jid, { text });
    res.json({ ok: true });
  } catch (err) {
    logger.error({ err: err.message }, "send message failed");
    res.status(502).json({ error: "failed to send message" });
  }
});

app.post("/disconnect/:userId", async (req, res) => {
  const key = req.params.userId;
  const session = getSession(key);
  if (session?.sock) {
    try {
      await session.sock.logout();
    } catch (err) {
      logger.warn({ err: err.message }, "logout error (ignoring)");
    }
  }
  sessions.delete(key);
  res.json({ ok: true });
});

app.get("/health", (_req, res) => res.json({ status: "ok" }));

app.listen(PORT, () => {
  logger.info(`whatsapp-service listening on ${PORT}`);
});
