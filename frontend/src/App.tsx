import { useEffect, useState } from "react";
import { api } from "./api";
import { Markdown } from "./Markdown";
import type { AskMode, AskResult, Collection, QuizQuestion, Source, Topic } from "./types";

export default function App() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [activeTopic, setActiveTopic] = useState<Topic | null>(null);
  const [content, setContent] = useState("");
  const [loadingContent, setLoadingContent] = useState(false);
  const [quiz, setQuiz] = useState<QuizQuestion[] | null>(null);
  const [loadingQuiz, setLoadingQuiz] = useState(false);
  // Mapuje index pytania -> czy odpowiedź była poprawna. Pozwala policzyć wynik
  // i pokazać domknięcie pętli nauki (wynik + przejście do kolejnego tematu).
  const [answers, setAnswers] = useState<Record<number, boolean>>({});
  // Panel "Zapytaj książkę" - wolne pytanie/wyjaśnienie/połączenie (niezależne od ścieżki).
  const [askQ, setAskQ] = useState("");
  const [askMode, setAskMode] = useState<AskMode>("ask");
  const [askResult, setAskResult] = useState<AskResult | null>(null);
  const [loadingAsk, setLoadingAsk] = useState(false);
  // Uploader nowej/istniejącej tematyki.
  const [uploaderOpen, setUploaderOpen] = useState(false);
  const [uploaderMode, setUploaderMode] = useState<"new" | "current">("new");
  const [newSubjectName, setNewSubjectName] = useState("");
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [fileStatus, setFileStatus] = useState<
    Record<string, "pending" | "uploading" | "done" | "error">
  >({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const topicIndex = activeTopic
    ? topics.findIndex((t) => t.title === activeTopic.title)
    : -1;
  const nextTopic =
    topicIndex >= 0 && topicIndex < topics.length - 1 ? topics[topicIndex + 1] : null;

  const total = quiz?.length ?? 0;
  const score = Object.values(answers).filter(Boolean).length;
  const allAnswered = total > 0 && Object.keys(answers).length === total;

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
    setAnswers({});
    setAskResult(null);
    setError("");
    api.topics(collection).then(setTopics).catch((e) => setError(String(e)));
  }, [collection]);

  async function openTopic(t: Topic) {
    setActiveTopic(t);
    setQuiz(null);
    setAnswers({});
    setContent("");
    setError("");
    setLoadingContent(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
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
    setAnswers({});
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

  async function runAsk() {
    const question = askQ.trim();
    if (!question || !collection) return;
    setError("");
    setAskResult(null);
    setLoadingAsk(true);
    try {
      // explain/connect mogą być zawężone do otwartego tematu; "ask" = cała książka.
      const r =
        askMode === "ask"
          ? await api.ask(collection, question)
          : await api.study(collection, question, askMode, activeTopic?.chapter ?? null);
      setAskResult(r);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingAsk(false);
    }
  }

  function slugifySubject(s: string): string {
    return s
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  function openNewSubjectUploader() {
    setUploaderMode("new");
    setNewSubjectName("");
    setUploadFiles([]);
    setFileStatus({});
    setUploaderOpen(true);
    setError("");
  }

  function openAddToCurrentUploader() {
    if (!collection) return;
    setUploaderMode("current");
    setNewSubjectName(collection);
    setUploadFiles([]);
    setFileStatus({});
    setUploaderOpen(true);
    setError("");
  }

  async function doUpload() {
    const target =
      uploaderMode === "new" ? slugifySubject(newSubjectName) : collection;
    if (!target) {
      setError("Podaj nazwę tematyki.");
      return;
    }
    if (!uploadFiles.length) {
      setError("Wybierz przynajmniej jeden plik PDF.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      for (const f of uploadFiles) {
        setFileStatus((s) => ({ ...s, [f.name]: "uploading" }));
        try {
          await api.upload(target, f);
          setFileStatus((s) => ({ ...s, [f.name]: "done" }));
        } catch (e) {
          setFileStatus((s) => ({ ...s, [f.name]: "error" }));
          setError(`Nieudany upload ${f.name}: ${String(e)}`);
        }
      }
      // Odśwież listę tematyk i przełącz na docelową (cache czytania też wyczyść).
      const cs = await api.collections();
      setCollections(cs);
      api.clearReadCache(target);
      if (target !== collection) setCollection(target);
      // Zamknij panel jak nic się nie wywaliło.
      const anyError = Object.values({ ...fileStatus }).includes("error");
      if (!anyError) setUploaderOpen(false);
    } finally {
      setUploading(false);
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
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Tematyka:</span>
            <select
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
              value={collection}
              onChange={(e) => setCollection(e.target.value)}
            >
              {collections.length === 0 && <option value="">(brak tematyki)</option>}
              {collections.map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.documents_count})
                </option>
              ))}
            </select>
            <button
              onClick={openNewSubjectUploader}
              className="rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-100"
              title="Wgraj PDF-y do nowej tematyki (np. metody numeryczne)"
            >
              + Nowy temat
            </button>
          </div>
        </div>
      </header>

      {uploaderOpen && (
        <UploaderPanel
          mode={uploaderMode}
          name={newSubjectName}
          setName={setNewSubjectName}
          files={uploadFiles}
          setFiles={setUploadFiles}
          fileStatus={fileStatus}
          uploading={uploading}
          slug={uploaderMode === "new" ? slugifySubject(newSubjectName) : collection}
          onCancel={() => setUploaderOpen(false)}
          onSubmit={doUpload}
        />
      )}

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
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
              Ścieżka nauki
            </h2>
            {collection && (
              <button
                onClick={openAddToCurrentUploader}
                className="text-xs font-medium text-indigo-600 hover:underline"
                title={`Dodaj PDF do tematyki "${collection}"`}
              >
                + Dodaj PDF
              </button>
            )}
          </div>
          {!collection ? (
            <div className="space-y-2">
              <p className="text-sm text-slate-400">
                Nie masz jeszcze żadnej tematyki.
              </p>
              <button
                onClick={openNewSubjectUploader}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700"
              >
                + Stwórz pierwszą tematykę
              </button>
            </div>
          ) : topics.length === 0 ? (
            <p className="text-sm text-slate-400">
              Brak tematów — wgraj PDF do tej tematyki.
            </p>
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

        {/* Prawy panel: zapytaj + treść + quiz */}
        <section className="space-y-6">
          {/* Panel "Zapytaj książkę" - zawsze dostępny, niezależny od ścieżki */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <h2 className="mr-1 text-sm font-semibold text-slate-700">Zapytaj książkę</h2>
              {(
                [
                  ["ask", "Pytanie"],
                  ["explain", "Wyjaśnij"],
                  ["connect", "Połącz"],
                ] as [AskMode, string][]
              ).map(([m, label]) => (
                <button
                  key={m}
                  onClick={() => setAskMode(m)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    askMode === m
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={askQ}
                onChange={(e) => setAskQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runAsk()}
                placeholder={
                  askMode === "connect"
                    ? "np. jak fairness łączy się z kalibracją?"
                    : askMode === "explain"
                      ? "np. wyjaśnij demographic parity"
                      : "zapytaj o cokolwiek z tej książki…"
                }
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
              <button
                onClick={runAsk}
                disabled={loadingAsk || !askQ.trim()}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
              >
                {loadingAsk ? "…" : "Zapytaj"}
              </button>
            </div>
            {activeTopic && askMode !== "ask" && (
              <p className="mt-2 text-xs text-slate-400">
                Zawężone do tematu: {activeTopic.title}
              </p>
            )}
            {askResult && <AnswerBlock result={askResult} />}
          </div>

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
                    <QuizCard
                      key={i}
                      index={i}
                      question={question}
                      onAnswer={(correct) =>
                        setAnswers((a) => ({ ...a, [i]: correct }))
                      }
                    />
                  ))}

                  {allAnswered && (
                    <ResultCard
                      score={score}
                      total={total}
                      nextTitle={nextTopic?.title ?? null}
                      onNext={() => nextTopic && openTopic(nextTopic)}
                      onRetry={startQuiz}
                    />
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

function UploaderPanel({
  mode,
  name,
  setName,
  files,
  setFiles,
  fileStatus,
  uploading,
  slug,
  onCancel,
  onSubmit,
}: {
  mode: "new" | "current";
  name: string;
  setName: (s: string) => void;
  files: File[];
  setFiles: (fs: File[]) => void;
  fileStatus: Record<string, "pending" | "uploading" | "done" | "error">;
  uploading: boolean;
  slug: string;
  onCancel: () => void;
  onSubmit: () => void;
}) {
  return (
    <div className="mx-auto mt-4 max-w-6xl px-6">
      <div className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-indigo-800">
            {mode === "new" ? "Nowa tematyka" : `Dodaj PDF → ${name}`}
          </h2>
          <button
            onClick={onCancel}
            disabled={uploading}
            className="text-xs text-slate-500 hover:text-slate-700 disabled:opacity-40"
          >
            ✕ Zamknij
          </button>
        </div>

        {mode === "new" && (
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Nazwa tematyki (np. „metody numeryczne")
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={uploading}
              placeholder="metody numeryczne"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none disabled:bg-slate-50"
            />
            {name.trim() && (
              <p className="mt-1 text-xs text-slate-500">
                Zapisana jako: <code className="font-mono text-indigo-700">{slug}</code>
              </p>
            )}
          </div>
        )}

        <div className="mb-3">
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Pliki PDF (możesz wybrać kilka)
          </label>
          <input
            type="file"
            accept="application/pdf,.pdf"
            multiple
            disabled={uploading}
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-indigo-700 disabled:opacity-50"
          />
        </div>

        {files.length > 0 && (
          <ul className="mb-3 space-y-1">
            {files.map((f) => {
              const st = fileStatus[f.name];
              const icon =
                st === "done"
                  ? "✅"
                  : st === "error"
                    ? "❌"
                    : st === "uploading"
                      ? "⏳"
                      : "•";
              return (
                <li key={f.name} className="flex items-center gap-2 text-xs text-slate-600">
                  <span>{icon}</span>
                  <span className="truncate">{f.name}</span>
                  <span className="text-slate-400">
                    ({(f.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </li>
              );
            })}
          </ul>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={onSubmit}
            disabled={uploading || !files.length || (mode === "new" && !slug)}
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700 disabled:opacity-50"
          >
            {uploading
              ? "Wgrywam…"
              : `Wgraj ${files.length || ""} ${files.length === 1 ? "plik" : "plików"} →`}
          </button>
          <p className="text-xs text-slate-500">
            Wgranie i zaindeksowanie ~10 MB PDF zajmuje ~30-60s (chunking + embedding na GPU).
          </p>
        </div>
      </div>
    </div>
  );
}

function AnswerBlock({ result }: { result: AskResult }) {
  const [showSources, setShowSources] = useState(false);
  return (
    <div className="mt-4 border-t border-slate-100 pt-4">
      <Markdown>{result.answer}</Markdown>
      {result.sources.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowSources((s) => !s)}
            className="text-xs font-medium text-indigo-600 hover:underline"
          >
            {showSources ? "Ukryj źródła" : `Źródła (${result.sources.length})`}
          </button>
          {showSources && (
            <div className="mt-2 space-y-2">
              {result.sources.map((s: Source, i: number) => (
                <div
                  key={i}
                  className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600"
                >
                  <span className="font-semibold text-slate-500">
                    {s.filename}
                    {s.page != null ? `, s. ${s.page}` : ""}
                  </span>
                  <p className="mt-1 line-clamp-3">{s.chunk_text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResultCard({
  score,
  total,
  nextTitle,
  onNext,
  onRetry,
}: {
  score: number;
  total: number;
  nextTitle: string | null;
  onNext: () => void;
  onRetry: () => void;
}) {
  const pct = Math.round((score / total) * 100);
  const { emoji, msg } =
    pct === 100
      ? { emoji: "🏆", msg: "Komplet! Masz ten temat opanowany." }
      : pct >= 60
        ? { emoji: "👍", msg: "Dobra robota — większość jasna." }
        : { emoji: "📖", msg: "Warto wrócić do materiału i spróbować ponownie." };

  return (
    <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-6">
      <div className="flex items-center gap-3">
        <span className="text-3xl">{emoji}</span>
        <div>
          <p className="text-lg font-bold text-indigo-800">
            Wynik: {score}/{total} ({pct}%)
          </p>
          <p className="text-sm text-indigo-700">{msg}</p>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        {nextTitle ? (
          <button
            onClick={onNext}
            className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-700"
          >
            Następny temat → <span className="opacity-80">{nextTitle}</span>
          </button>
        ) : (
          <span className="rounded-xl bg-white px-5 py-2.5 text-sm font-medium text-indigo-700">
            🎉 To był ostatni temat w tej książce!
          </span>
        )}
        <button
          onClick={onRetry}
          className="rounded-xl border border-indigo-300 bg-white px-5 py-2.5 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-100"
        >
          Jeszcze raz
        </button>
      </div>
    </div>
  );
}

function QuizCard({
  index,
  question,
  onAnswer,
}: {
  index: number;
  question: QuizQuestion;
  onAnswer: (correct: boolean) => void;
}) {
  const [picked, setPicked] = useState<number | null>(null);
  const answered = picked !== null;

  function pick(i: number) {
    if (answered) return;
    setPicked(i);
    onAnswer(i === question.correct_index);
  }

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
              onClick={() => pick(i)}
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
        <div className="mt-3 rounded-lg bg-slate-50 px-4 py-2">
          <Markdown>{question.explanation}</Markdown>
        </div>
      )}
    </div>
  );
}
