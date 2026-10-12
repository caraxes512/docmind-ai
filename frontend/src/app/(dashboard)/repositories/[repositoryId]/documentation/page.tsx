"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Edit3, History, MessageSquare, RefreshCw, Sparkles } from "lucide-react";
import {
  useCurrentDocumentation,
  useDocument,
  useGenerateDocumentation,
  useRegenerateDocumentation,
} from "@/hooks/use-documentation";
import { useRepository } from "@/hooks/use-repositories";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent, CardTitle, CardDescription } from "@/components/ui/card";
import { DocSidebarNav } from "@/components/documentation/doc-sidebar-nav";
import { MarkdownRenderer } from "@/components/documentation/markdown-renderer";
import { QualityScoreBadge } from "@/components/documentation/quality-score-badge";
import { TaskProgressIndicator } from "@/components/tasks/task-progress-indicator";

export default function DocumentationViewerPage() {
  const params = useParams<{ repositoryId: string }>();
  const { data: repository } = useRepository(params.repositoryId);
  const { data: version, isLoading: isVersionLoading } = useCurrentDocumentation(params.repositoryId);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const generateDocs = useGenerateDocumentation(params.repositoryId);
  const regenerateDocs = useRegenerateDocumentation(params.repositoryId);
  const { data: activeDocument, isLoading: isDocumentLoading } = useDocument(activeDocumentId ?? undefined);

  useEffect(() => {
    const firstDoc = version?.documents?.[0];
    if (!activeDocumentId && firstDoc) {
      setActiveDocumentId(firstDoc.id);
    }
  }, [version, activeDocumentId]);

  const handleGenerate = async () => {
    const task = await generateDocs.mutateAsync(undefined);
    setActiveTaskId(task.id);
  };

  const handleRegenerate = async () => {
    const task = await regenerateDocs.mutateAsync({});
    setActiveTaskId(task.id);
  };

  if (isVersionLoading) {
    return (
      <div className="mx-auto max-w-5xl px-8 py-10">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-6 h-96" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-8 py-10">
      <Link
        href={`/projects`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </Link>

      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-medium text-paper">Documentation</h1>
          {version && (
            <p className="mt-1 text-sm text-paper-dim">
              Version {version.version_number} · {version.documents.length} documents
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href={`/repositories/${params.repositoryId}/documentation/versions`}>
              <History className="h-3.5 w-3.5" /> Versions
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/repositories/${params.repositoryId}/chat`}>
              <MessageSquare className="h-3.5 w-3.5" /> Ask a question
            </Link>
          </Button>
          {version ? (
            <Button size="sm" onClick={handleRegenerate} disabled={regenerateDocs.isPending}>
              <RefreshCw className="h-3.5 w-3.5" /> Regenerate changed docs
            </Button>
          ) : (
            <Button size="sm" onClick={handleGenerate} disabled={generateDocs.isPending}>
              <Sparkles className="h-3.5 w-3.5" /> Generate documentation
            </Button>
          )}
        </div>
      </div>

      {activeTaskId && (
        <Card className="mb-6">
          <CardContent className="p-4">
            <TaskProgressIndicator taskId={activeTaskId} label="Documentation generation" />
          </CardContent>
        </Card>
      )}

      {!version && !activeTaskId && (
        <Card className="flex flex-col items-center gap-3 border-dashed py-16 text-center">
          <Sparkles className="h-8 w-8 text-annotation" />
          <CardTitle>No documentation yet</CardTitle>
          <CardDescription>
            Generate documentation for {repository?.default_branch ?? "this repository"} to get started.
          </CardDescription>
          <Button className="mt-2" onClick={handleGenerate} disabled={generateDocs.isPending}>
            <Sparkles className="h-3.5 w-3.5" /> Generate documentation
          </Button>
        </Card>
      )}

      {version && (
        <div className="flex gap-8">
          <DocSidebarNav
            documents={version.documents}
            activeDocumentId={activeDocumentId}
            onSelect={setActiveDocumentId}
          />

          <div className="min-w-0 flex-1">
            {isDocumentLoading && <Skeleton className="h-96" />}
            {activeDocument && (
              <>
                <div className="mb-4 flex items-center justify-between border-b border-ink-700 pb-4">
                  {activeDocument.review_result && (
                    <QualityScoreBadge score={activeDocument.review_result.quality_score} />
                  )}
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/repositories/${params.repositoryId}/documentation/${activeDocument.id}/edit`}>
                      <Edit3 className="h-3.5 w-3.5" /> Edit
                    </Link>
                  </Button>
                </div>
                <MarkdownRenderer content={activeDocument.content} />
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
