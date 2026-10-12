"use client";

import { cn } from "@/lib/utils";
import { DOCUMENT_TYPE_LABELS } from "@/lib/types";
import type { GeneratedDocumentSummary } from "@/lib/types";
import { QualityScoreBadge } from "@/components/documentation/quality-score-badge";

export function DocSidebarNav({
  documents,
  activeDocumentId,
  onSelect,
  scoresByDocumentId,
}: {
  documents: GeneratedDocumentSummary[];
  activeDocumentId: string | null;
  onSelect: (documentId: string) => void;
  scoresByDocumentId?: Record<string, number>;
}) {
  return (
    <nav className="flex w-56 shrink-0 flex-col gap-0.5">
      {documents.map((doc) => {
        const score = scoresByDocumentId?.[doc.id];
        return (
          <button
            key={doc.id}
            onClick={() => onSelect(doc.id)}
            className={cn(
              "flex items-center justify-between rounded px-3 py-2 text-left text-sm transition-colors hover:bg-ink-700",
              activeDocumentId === doc.id ? "bg-ink-700 text-paper" : "text-paper-dim"
            )}
          >
            <span className="truncate">{DOCUMENT_TYPE_LABELS[doc.doc_type]}</span>
            {score !== undefined && (
              <span className="ml-2 shrink-0">
                <QualityScoreBadge score={score} />
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
