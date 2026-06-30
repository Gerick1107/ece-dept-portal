import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders assistant answers as clean markdown. The RAG prompt asks for plain
 * prose with light structure (short paragraphs / simple bullet lists), but this
 * also degrades gracefully if the model emits headings, emphasis, or a table.
 */
export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="text-sm text-slate-800 space-y-2 leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
          li: ({ children }) => <li>{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          h1: ({ children }) => <h4 className="font-semibold text-slate-900">{children}</h4>,
          h2: ({ children }) => <h4 className="font-semibold text-slate-900">{children}</h4>,
          h3: ({ children }) => <h5 className="font-semibold text-slate-900">{children}</h5>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-teal-700 underline">
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="bg-slate-100 rounded px-1 py-0.5 text-xs font-mono">{children}</code>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="text-xs border-collapse my-1">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border border-slate-200 px-2 py-1 bg-slate-50 text-left">{children}</th>,
          td: ({ children }) => <td className="border border-slate-200 px-2 py-1">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
