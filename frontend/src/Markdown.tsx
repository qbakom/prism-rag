import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renderer markdownu dla odpowiedzi LLM (nagłówki, **bold**, listy, kod, tabele).
// Stylujemy elementy jawnie - brak pluginu @tailwindcss/typography w projekcie.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="text-sm leading-relaxed text-slate-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: (p) => <h1 className="mt-4 mb-2 text-lg font-bold text-slate-800" {...p} />,
          h2: (p) => <h2 className="mt-4 mb-2 text-base font-bold text-slate-800" {...p} />,
          h3: (p) => <h3 className="mt-3 mb-1.5 text-sm font-bold text-slate-800" {...p} />,
          p: (p) => <p className="mb-3" {...p} />,
          strong: (p) => <strong className="font-semibold text-slate-900" {...p} />,
          em: (p) => <em className="italic" {...p} />,
          ul: (p) => <ul className="mb-3 list-disc space-y-1 pl-5" {...p} />,
          ol: (p) => <ol className="mb-3 list-decimal space-y-1 pl-5" {...p} />,
          li: (p) => <li className="pl-1" {...p} />,
          code: (p) => (
            <code
              className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.85em] text-indigo-700"
              {...p}
            />
          ),
          pre: (p) => (
            <pre
              className="mb-3 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100"
              {...p}
            />
          ),
          blockquote: (p) => (
            <blockquote className="mb-3 border-l-2 border-indigo-200 pl-3 text-slate-600" {...p} />
          ),
          a: (p) => <a className="text-indigo-600 underline" {...p} />,
          table: (p) => (
            <div className="mb-3 overflow-x-auto">
              <table className="w-full border-collapse text-xs" {...p} />
            </div>
          ),
          th: (p) => <th className="border border-slate-200 bg-slate-50 px-2 py-1 text-left" {...p} />,
          td: (p) => <td className="border border-slate-200 px-2 py-1" {...p} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
