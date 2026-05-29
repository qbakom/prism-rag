import { useEffect, useState } from "react";
import { api } from "./api";
import type { Collection, QuizQuestion, Topic } from "./types";

export default function App() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
  const [content, setContent] = useState("");
  const [loadingContent, setLoadingContent] = useState(false);
  const [quiz, setQuiz] = useState<QuizQuestion[] | null>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(false);
  const [error, setError] = useState("");

  // Wczytaj kolekcje na starcie
  useEffect(() => {
    api
      .collections()
      .then((cs) => {
        setCollections(cs);
        if (cs.length) setCollection((c) => c || cs[0].name);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // Po wyborze kolekcji - pobierz ścieżkę tematów i wyczyść prawy panel
  useEffect(() => {
    if (!collection) return;
    setTopics([]);
    setActiveTopic(null);
    setContent("");
    setQuiz(null);
    setError("");
    api.topics(collection).then(setTopics).catch((e) => setError(String(e)));
  }, [collection]);

  async function openTopic(t: Topic) {
    setActiveTopic(t);
    setQuiz(null);
    setContent("");
    setError("");
    setLoadingContent(true);
    try {
      const r = await api.read(collection, t.chapter);
      setContent(r.content.trim() || "(brak treści dla tego tematu)");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingContent(false);
    }
  }

  async function startQuiz() {
    if (!activeTopic) return;
    setError("");
    setLoadingQuiz(true);
    try {
      const r = await api.quiz({
        collection,
        chapter: activeTopic.chapter,
        num_questions: 4,
      });
      setQuiz(r.questions);
      if (r.questions.length === 0) {
        setError("Nie udało się wygenerować pytań (LLM niedostępny lub za mało materiału).");
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingQuiz(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Pasek górny */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-indigo-700">PRISM</h1>
            <p className="text-sm text-slate-500">Nauka z książek — klikasz, nie piszesz</p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Książka:</span>
            <select
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
            >
              {collections.length === 0 && <option value="">(brak kolekcji)</option>}
              {collections.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.documents_count})
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {error && (
        <div className="mx-auto mt-4 max-w-6xl px-6">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
            {error}
          </div>
        </div>
      )}

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-6 py-6 md:grid-cols-[300px_1fr]">
        {/* Lewy panel: ścieżka nauki */}
        <aside className="h-fit rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Ścieżka nauki
          </h2>
          {topics.length === 0 ? (
            <p className="text-sm text-slate-400">Brak tematów — wgraj książkę do tej kolekcji.</p>
          ) : (
            <ol className="space-y-1">
              {topics.map((t, i) => {
                const active = activeTopic?.title === t.title;
                return (
                  <li key={`${t.chapter}-${t.title}`}>
                    <button
                      onClick={() => openTopic(t)}
                      className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${
                        active
                          ? "bg-indigo-600 text-white"
                          : "text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      <span
                        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                          active ? "bg-white/20" : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {i + 1}
                      </span>
                      <span className="line-clamp-2">{t.title}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          )}
        </aside>

        {/* Prawy panel: treść + quiz */}
        <section className="space-y-6">
          {!activeTopic ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
              Wybierz temat ze ścieżki po lewej, żeby zacząć.
            </div>
          ) : (
            <>
              <article className="rounded-2xl border border-slate-200 bg-white p-6">
                <h2 className="mb-4 text-lg font-bold text-slate-800">{activeTopic.title}</h2>
                {loadingContent ? (
                  <p className="text-slate-400">Wczytuję materiał…</p>
                ) : (
                  <div className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                    {content}
                  </div>
                )}
                <button
                  onClick={startQuiz}
                  disabled={loadingQuiz || loadingContent}
                  className="mt-5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loadingQuiz ? "Generuję pytania…" : "Sprawdź się ✓"}
                </button>
              </article>

              {quiz && quiz.length > 0 && (
                <div className="space-y-4">
                  {quiz.map((question, i) => (
                    <QuizCard key={i} index={i} question={question} />
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

function QuizCard({ index, question }: { index: number; question: QuizQuestion }) {
  const [picked, setPicked] = useState<number | null>(null);
  const answered = picked !== null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <p className="mb-3 font-medium text-slate-800">
        <span className="mr-2 text-indigo-600">{index + 1}.</span>
        {question.question}
      </p>
      <div className="space-y-2">
        {question.options.map((opt, i) => {
          const isCorrect = i === question.correct_index;
          const isPicked = i === picked;
          let cls = "border-slate-200 bg-white hover:bg-slate-50";
          if (answered && isCorrect) cls = "border-green-400 bg-green-50 text-green-800";
          else if (answered && isPicked) cls = "border-red-400 bg-red-50 text-red-800";
          else if (answered) cls = "border-slate-200 bg-white opacity-60";
          return (
            <button
              key={i}
              disabled={answered}
              onClick={() => setPicked(i)}
              className={`flex w-full items-center gap-3 rounded-lg border px-4 py-2.5 text-left text-sm transition ${cls}`}
            >
              <span className="font-semibold text-slate-400">
                {String.fromCharCode(65 + i)}
              </span>
              <span>{opt}</span>
              {answered && isCorrect && <span className="ml-auto">✅</span>}
              {answered && isPicked && !isCorrect && <span className="ml-auto">❌</span>}
            </button>
          );
        })}
      </div>
      {answered && question.explanation && (
        <p className="mt-3 rounded-lg bg-slate-50 px-4 py-2 text-sm text-slate-600">
          {question.explanation}
        </p>
      )}
    </div>
  );
}
