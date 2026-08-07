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

// A real name always overwrites whatever's stored (including the raw-JID
// fallback set by an earlier, name-less sync); without a name, only fill in
// the fallback if the chat has no entry at all yet.
function setChatName(session, jid, name) {
  if (!jid) return;
  if (name) {
    session.chats.set(jid, name);
  } else if (!session.chats.has(jid)) {
    session.chats.set(jid, chatDisplayName(jid));
  }
}

// WhatsApp is migrating 1:1 identities to an opaque "@lid" address in
// parallel with the phone-number "@s.whatsapp.net" one, and can deliver the
// same conversation under both - Baileys sees them as two unrelated chats.
// Resolve @lid back to the phone-number jid via WhatsApp's own contact
// lookup so messages land in the one real chat instead of a duplicate.
async function resolveCanonicalJid(sock, session, jid) {
  if (!jid || !jid.endsWith("@lid")) return jid;
  if (session.lidToPhone.has(jid)) return session.lidToPhone.get(jid);
  let resolved = jid;
  try {
    const results = await sock.onWhatsApp(jid);
    const match = results?.find((r) => r.jid && !r.jid.endsWith("@lid"));
    if (match?.jid) resolved = match.jid;
  } catch (err) {
    logger.warn({ err: err.message, jid }, "failed to resolve @lid to a phone-number jid");
  }
  session.lidToPhone.set(jid, resolved);
  return resolved;
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

async function forwardMessagesBulk(userId, entries) {
  if (entries.length === 0) return;
  try {
    await axios.post(
      `${BACKEND_URL}/api/v1/whatsapp/webhook/messages/bulk`,
      entries.map((e) => ({ user_id: Number(userId), ...e })),
      { headers: { "X-Webhook-Secret": WEBHOOK_SECRET }, timeout: 30000 }
    );
  } catch (err) {
    logger.error({ err: err.message }, "failed to forward historical messages to backend");
  }
}

function extractText(msg) {
  return (
    msg.message?.conversation ||
    msg.message?.extendedTextMessage?.text ||
    msg.message?.imageMessage?.caption ||
    ""
  );
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

  const session = {
    sock: null,
    status: "connecting",
    qr: null,
    phone: null,
    chats: new Map(),
    sentMessageIds: new Set(),
    lidToPhone: new Map(),
  };
  sessions.set(key, session);

  const { state, saveCreds } = await useMultiFileAuthState(`${SESSIONS_DIR}/${key}`);
  // Without syncFullHistory, Baileys never requests the existing chat list
  // from WhatsApp on pairing - messaging-history.set simply never fires and
  // the sidebar only ever picks up chats that receive a message afterwards.
  const sock = makeWASocket({ auth: state, logger, printQRInTerminal: false, syncFullHistory: true });
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
      setChatName(session, chat.id, chat.name);
    }
  });

  // The bulk list of a user's existing conversations arrives here (not via
  // chats.upsert, which only fires for individual chat updates) right after
  // the QR scan, as WhatsApp syncs recent chat history to this device. Names
  // are frequently missing from this first batch - they trickle in later via
  // contacts.upsert / groups.upsert, which are allowed to overwrite the
  // raw-JID fallback set here. This same event also carries each chat's
  // recent message history (only with syncFullHistory enabled), which is
  // what lets opened conversations show past messages instead of starting
  // empty from the moment of connecting.
  sock.ev.on("messaging-history.set", async ({ chats, contacts, messages }) => {
    console.log(
      `[wa:${key}] messaging-history.set: ${chats?.length ?? 0} chat(s), ${contacts?.length ?? 0} contact(s), ${messages?.length ?? 0} message(s)`
    );
    const nameByJid = new Map((contacts || []).map((c) => [c.id, c.name || c.notify]));

    // 1:1 chats rarely get a name via `contacts` - WhatsApp doesn't share the
    // phone's contact book with a linked device, only push names, which show
    // up reliably as the sender's pushName on their own historical messages.
    const pushNameByJid = new Map();
    for (const msg of messages || []) {
      const jid = msg.key?.remoteJid;
      if (jid && !msg.key.fromMe && !jid.endsWith("@g.us") && msg.pushName && !pushNameByJid.has(jid)) {
        pushNameByJid.set(jid, msg.pushName);
      }
    }

    for (const chat of chats || []) {
      const canonicalJid = await resolveCanonicalJid(sock, session, chat.id);
      setChatName(session, canonicalJid, chat.name || nameByJid.get(chat.id) || pushNameByJid.get(chat.id));
    }
    for (const [jid, name] of pushNameByJid) {
      const canonicalJid = await resolveCanonicalJid(sock, session, jid);
      setChatName(session, canonicalJid, name);
    }

    const entries = [];
    for (const msg of (messages || []).slice(0, 5000)) {
      if (!msg.message || !msg.key.remoteJid) continue;
      const text = extractText(msg);
      if (!text) continue;
      // Merge WhatsApp's @lid-addressed copy of a 1:1 conversation into the
      // same phone-number-based chat instead of a duplicate.
      const chatJid = await resolveCanonicalJid(sock, session, msg.key.remoteJid);
      const fromMe = !!msg.key.fromMe;
      const sender = fromMe ? "Você" : msg.pushName || pushNameByJid.get(msg.key.remoteJid) || "Desconhecido";
      entries.push({
        chat_jid: chatJid,
        chat_name: session.chats.get(chatJid) || chatDisplayName(chatJid),
        sender,
        text,
        timestamp: msg.messageTimestamp,
        from_me: fromMe,
      });
    }
    forwardMessagesBulk(key, entries);
  });

  sock.ev.on("contacts.upsert", (contacts) => {
    for (const contact of contacts) {
      setChatName(session, contact.id, contact.name || contact.notify);
    }
  });

  sock.ev.on("contacts.update", (contacts) => {
    for (const contact of contacts) {
      setChatName(session, contact.id, contact.name || contact.notify);
    }
  });

  sock.ev.on("groups.upsert", (groups) => {
    for (const group of groups) {
      setChatName(session, group.id, group.subject);
    }
  });

  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || !msg.key.remoteJid) continue;
      // Messages we sent through POST /send are stored synchronously there
      // already - skip WhatsApp's own echo of them to avoid duplicates.
      if (msg.key.id && session.sentMessageIds.has(msg.key.id)) {
        session.sentMessageIds.delete(msg.key.id);
        continue;
      }
      const text = extractText(msg);
      if (!text) continue;

      // Merge WhatsApp's @lid-addressed copy of a 1:1 conversation into the
      // same phone-number-based chat instead of a duplicate.
      const chatJid = await resolveCanonicalJid(sock, session, msg.key.remoteJid);
      const fromMe = !!msg.key.fromMe;
      const sender = fromMe ? "Você" : msg.pushName || "Desconhecido";
      // A sender's pushName is a real name only for 1:1 chats - for groups
      // it's just who's talking, not the group's name.
      const realChatName = !chatJid.endsWith("@g.us") && !fromMe ? msg.pushName : undefined;
      setChatName(session, chatJid, realChatName);
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

app.delete("/chats/:userId/:jid", (req, res) => {
  const session = getSession(req.params.userId);
  session?.chats.delete(decodeURIComponent(req.params.jid));
  res.json({ ok: true });
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
    const sent = await session.sock.sendMessage(jid, { text });
    if (sent?.key?.id) session.sentMessageIds.add(sent.key.id);
    const chatName = session.chats.get(jid) || chatDisplayName(jid);
    await forwardMessage(req.params.userId, jid, chatName, "Você", text, Math.floor(Date.now() / 1000), true);
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
