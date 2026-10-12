import { FileCode } from "lucide-react";
import type { Citation } from "@/lib/types";

export function CitationPill({ citation }: { citation: Citation }) {
  const lineInfo = citation.start_line ? `:${citation.start_line}${citation.end_line ? `-${citation.end_line}` : ""}` : "";
  return (
    <span className="inline-flex items-center gap-1 rounded border border-ink-600 bg-ink-800 px-2 py-1 font-mono text-xs text-blueprint">
      <FileCode className="h-3 w-3" />
      {citation.file_path}
      {lineInfo}
    </span>
  );
}
