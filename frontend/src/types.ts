// Typy odpowiedzi z API PRISM (lustro modeli Pydantic w backendzie).

export interface Collection {
  name: string;
  documents_count: number;
}

export interface Topic {
  chapter: string | null;
  title: string;
  chunk_count: number;
}

export interface ReadResult {
  chapter: string | null;
  content: string;
  filename: string | null;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface QuizResult {
  chapter: string | null;
  questions: QuizQuestion[];
}

export interface Source {
  filename: string;
  page: number | null;
  chunk_text: string;
}

export interface AskResult {
  answer: string;
  sources: Source[];
}

export type AskMode = "ask" | "explain" | "connect";
