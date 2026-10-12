"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import { useDocument, useUpdateDocument } from "@/hooks/use-documentation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownRenderer } from "@/components/documentation/markdown-renderer";
import { DOCUMENT_TYPE_LABELS } from "@/lib/types";

export default function DocumentationEditorPage() {
  const params = useParams<{ repositoryId: string; documentId: string }>();
  const { data: document, isLoading } = useDocument(params.documentId);
  const updateDocument = useUpdateDocument(params.documentId);
  const [content, setContent] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (document && !hasUnsavedChanges) {
      setContent(document.content);
    }
  }, [document, hasUnsavedChanges]);

  const handleSave = async () => {
    await updateDocument.mutateAsync(content);
    setHasUnsavedChanges(false);
  };

  if (isLoading || !document) {
    return (
      <div className="mx-auto max-w-6xl px-8 py-10">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-6 h-[600px]" />
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between border-b border-ink-700 px-8 py-4">
        <div className="flex items-center gap-4">
          <Link
            href={`/repositories/${params.repositoryId}/documentation`}
            className="inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <span className="font-display text-lg font-medium text-paper">
            Editing {DOCUMENT_TYPE_LABELS[document.doc_type]}
          </span>
          {hasUnsavedChanges && <span className="text-xs text-annotation">Unsaved changes</span>}
        </div>
        <Button size="sm" onClick={handleSave} disabled={!hasUnsavedChanges || updateDocument.isPending}>
          <Save className="h-3.5 w-3.5" /> {updateDocument.isPending ? "Saving…" : "Save"}
        </Button>
      </div>

      <div className="grid flex-1 grid-cols-2 divide-x divide-ink-700 overflow-hidden">
        <Textarea
          value={content}
          onChange={(e) => {
            setContent(e.target.value);
            setHasUnsavedChanges(true);
          }}
          className="h-full resize-none rounded-none border-none bg-ink-900 p-6 text-sm"
        />
        <div className="h-full overflow-y-auto p-6">
          <MarkdownRenderer content={content} />
        </div>
      </div>
    </div>
  );
}
