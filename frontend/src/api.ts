// Cienki klient HTTP do FastAPI. Adres backendu konfigurowalny przez
// VITE_API_URL (domyślnie localhost:8000) - nic nie jest zahardkodowane na sztywno.
import type { Collection, QuizResult, ReadResult, Topic } from "./types";

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
};
