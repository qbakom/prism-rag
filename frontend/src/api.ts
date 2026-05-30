// Cienki klient HTTP do FastAPI. Adres backendu konfigurowalny przez
// VITE_API_URL (domyślnie localhost:8000) - nic nie jest zahardkodowane na sztywno.
import type {
  AskResult,
  Collection,
  FileInfo,
  IngestResult,
  QuizResult,
  ReadResult,
  Source,
  Topic,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

const q = (v: string) => encodeURIComponent(v);

// Treść rozdziału jest niezmienna w obrębie kolekcji - cache'ujemy w pamięci,
// żeby powrót do raz przeczytanego rozdziału nie wołał backendu ponownie.
const readCache = new Map<string, Promise<ReadResult>>();

export const api = {
  collections: () => request<Collection[]>("/collections/"),

  files: (collection: string) =>
    request<FileInfo[]>(`/collections/${q(collection)}/files`),

  deleteFile: (collection: string, filename: string) =>
    request<{ message: string; deleted: number }>(
      `/collections/${q(collection)}/files?filename=${q(filename)}`,
      { method: "DELETE" },
    ),

  deleteCollection: (collection: string) =>
    request<{ message: string }>(`/collections/${q(collection)}`, { method: "DELETE" }),

  topics: (collection: string) =>
    request<Topic[]>(`/study/topics?collection=${q(collection)}`),

  read: (collection: string, chapter: string | null) => {
    const key = `${collection}||${chapter ?? ""}`;
    const cached = readCache.get(key);
    if (cached) return cached;

    const ch = chapter ? `&chapter=${q(chapter)}` : "";
    const p = request<ReadResult>(`/study/read?collection=${q(collection)}${ch}`);
    // Odrzuconej obietnicy nie trzymamy w cache - błąd ma być ponawialny.
    p.catch(() => readCache.delete(key));
    readCache.set(key, p);
    return p;
  },

  // Wgraj PDF do podanej kolekcji (tworzy ją gdy nie istnieje).
  // Multipart - własny fetch, bo `request` wymusza Content-Type: application/json.
  upload: async (collection: string, file: File): Promise<IngestResult> => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("collection", collection);
    const res = await fetch(`${BASE}/ingest/`, { method: "POST", body: fd });
    if (!res.ok) {
      throw new Error(`Upload ${res.status}: ${await res.text()}`);
    }
    return res.json() as Promise<IngestResult>;
  },

  // Wyczyść cache czytania (np. po ponownym imporcie materiałów).
  clearReadCache: (collection?: string) => {
    if (!collection) return readCache.clear();
    for (const key of readCache.keys()) {
      if (key.startsWith(`${collection}||`)) readCache.delete(key);
    }
  },

  quiz: (body: { collection: string; chapter: string | null; num_questions: number }) =>
    request<QuizResult>("/study/quiz", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Wolne pytanie o całą książkę (RAG): odpowiedź + cytowane źródła.
  ask: (collection: string, question: string) =>
    request<AskResult>("/query/", {
      method: "POST",
      body: JSON.stringify({ question, collection, top_k: 6 }),
    }),

  // Tryby nauki explain/connect zwracają {content, sources} - normalizujemy do AskResult.
  study: async (
    collection: string,
    question: string,
    mode: "explain" | "connect",
    chapter: string | null,
  ): Promise<AskResult> => {
    const r = await request<{ content: string; sources: Source[] }>("/study/", {
      method: "POST",
      body: JSON.stringify({ question, collection, mode, chapter }),
    });
    return { answer: r.content, sources: r.sources };
  },
};
