const redisUrl = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const redisToken = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const { randomUUID } = require("crypto");

const maxNotesPerLesson = 100;
const maxTextLength = 4000;

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.end(JSON.stringify(payload));
}

function getStorageKey(key) {
  return `teacher-hub:notes:${key}`;
}

function assertStorageConfigured() {
  if (!redisUrl || !redisToken) {
    const error = new Error("Teacher notes storage is not configured.");
    error.statusCode = 503;
    throw error;
  }
}

function validateLessonKey(key) {
  if (!key || typeof key !== "string" || key.length > 160 || !/^[a-z0-9:_-]+$/i.test(key)) {
    const error = new Error("Invalid lesson key.");
    error.statusCode = 400;
    throw error;
  }
  return key;
}

function validateNoteText(text) {
  if (!text || typeof text !== "string" || !text.trim()) {
    const error = new Error("Note text is required.");
    error.statusCode = 400;
    throw error;
  }
  return text.trim().slice(0, maxTextLength);
}

async function readRequestBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") return JSON.parse(req.body || "{}");

  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

async function redisCommand(command) {
  assertStorageConfigured();

  const response = await fetch(redisUrl, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${redisToken}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(command)
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.error) {
    const error = new Error(payload.error || "Redis command failed.");
    error.statusCode = 502;
    throw error;
  }
  return payload.result;
}

async function readNotes(key) {
  const result = await redisCommand(["GET", getStorageKey(key)]);
  if (!result) return [];
  if (Array.isArray(result)) return result;

  try {
    const notes = JSON.parse(result);
    return Array.isArray(notes) ? notes : [];
  } catch {
    return [];
  }
}

async function writeNotes(key, notes) {
  await redisCommand(["SET", getStorageKey(key), JSON.stringify(notes.slice(-maxNotesPerLesson))]);
}

function formatCreatedAt() {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow"
  }).format(new Date());
}

module.exports = async function handler(req, res) {
  try {
    if (req.method === "GET") {
      const key = validateLessonKey(req.query.key);
      const notes = await readNotes(key);
      return sendJson(res, 200, { notes });
    }

    if (req.method === "POST") {
      const body = await readRequestBody(req);
      const key = validateLessonKey(body.key);
      const text = validateNoteText(body.text);
      const notes = await readNotes(key);
      notes.push({
        id: randomUUID(),
        text,
        createdAt: formatCreatedAt()
      });
      await writeNotes(key, notes);
      return sendJson(res, 200, { notes: notes.slice(-maxNotesPerLesson) });
    }

    if (req.method === "DELETE") {
      const body = await readRequestBody(req);
      const key = validateLessonKey(body.key);
      const noteId = typeof body.noteId === "string" ? body.noteId : "";
      const notes = (await readNotes(key)).filter(note => note.id !== noteId);
      await writeNotes(key, notes);
      return sendJson(res, 200, { notes });
    }

    res.setHeader("Allow", "GET, POST, DELETE");
    return sendJson(res, 405, { error: "Method not allowed." });
  } catch (error) {
    return sendJson(res, error.statusCode || 500, { error: error.message || "Unexpected server error." });
  }
};
