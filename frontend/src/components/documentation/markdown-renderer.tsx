import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MermaidDiagram } from "@/components/documentation/mermaid-diagram";

export function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose-docmind">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const languageMatch = /language-(\w+)/.exec(className || "");
            const codeText = String(children).replace(/\n$/, "");

            if (languageMatch?.[1] === "mermaid") {
              return <MermaidDiagram source={codeText} />;
            }

            const isBlock = Boolean(languageMatch);
            if (!isBlock) {
              return (
                <code className="rounded bg-ink-700 px-1.5 py-0.5 font-mono text-[0.85em] text-blueprint" {...props}>
                  {children}
                </code>
              );
            }

            return (
              <pre className="overflow-x-auto rounded bg-ink-800 p-4 font-mono text-sm">
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
          h1: (props) => <h1 className="mt-8 font-display text-2xl font-medium text-paper first:mt-0" {...props} />,
          h2: (props) => <h2 className="mt-6 font-display text-xl font-medium text-paper" {...props} />,
          h3: (props) => <h3 className="mt-5 font-display text-lg font-medium text-paper" {...props} />,
          p: (props) => <p className="mt-3 text-sm leading-relaxed text-paper-dim" {...props} />,
          a: (props) => <a className="text-blueprint hover:underline" {...props} />,
          ul: (props) => <ul className="mt-3 list-disc pl-5 text-sm text-paper-dim" {...props} />,
          ol: (props) => <ol className="mt-3 list-decimal pl-5 text-sm text-paper-dim" {...props} />,
          table: (props) => (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full border-collapse text-sm" {...props} />
            </div>
          ),
          th: (props) => <th className="border border-ink-700 bg-ink-800 px-3 py-2 text-left text-paper" {...props} />,
          td: (props) => <td className="border border-ink-700 px-3 py-2 text-paper-dim" {...props} />,
          blockquote: (props) => (
            <blockquote className="mt-3 border-l-2 border-annotation pl-4 text-sm italic text-paper-dim" {...props} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
