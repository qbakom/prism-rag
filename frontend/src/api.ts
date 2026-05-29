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

export const api = {
  collections: () => request<Collection[]>("/collections/"),

  topics: (collection: string) =>
    request<Topic[]>(`/study/topics?collection=${q(collection)}`),

  read: (collection: string, chapter: string | null) => {
    const ch = chapter ? `&chapter=${q(chapter)}` : "";
    return request<ReadResult>(`/study/read?collection=${q(collection)}${ch}`);
  },

  quiz: (body: { collection: string; chapter: string | null; num_questions: number }) =>
    request<QuizResult>("/study/quiz", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
