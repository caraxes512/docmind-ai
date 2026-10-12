"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Plus, FileText, MessageSquare, ArrowLeft } from "lucide-react";
import { useProject } from "@/hooks/use-projects";
import { useRepositories } from "@/hooks/use-repositories";
import { Button } from "@/components/ui/button";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RepositoryStatusBadge } from "@/components/repository-status-badge";
import { formatRelativeTime } from "@/lib/utils";

export default function ProjectDetailPage() {
  const params = useParams<{ projectId: string }>();
  const { data: project, isLoading: isProjectLoading } = useProject(params.projectId);
  const { data: repositories, isLoading: areRepositoriesLoading } = useRepositories(params.projectId);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <Link href="/dashboard" className="mb-6 inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper">
        <ArrowLeft className="h-3.5 w-3.5" /> All projects
      </Link>

      <div className="mb-8 flex items-center justify-between">
        <div>
          {isProjectLoading ? (
            <Skeleton className="h-8 w-56" />
          ) : (
            <h1 className="font-display text-2xl font-medium text-paper">{project?.name}</h1>
          )}
          {project?.description && <p className="mt-1 text-sm text-paper-dim">{project.description}</p>}
        </div>
        <Button asChild>
          <Link href={`/projects/${params.projectId}/upload`}>
            <Plus className="h-4 w-4" /> Add repository
          </Link>
        </Button>
      </div>

      {areRepositoriesLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}

      {!areRepositoriesLoading && repositories?.items.length === 0 && (
        <Card className="flex flex-col items-center gap-3 border-dashed py-16 text-center">
          <CardTitle>No repositories yet</CardTitle>
          <p className="max-w-sm text-sm text-paper-dim">
            Upload a ZIP archive or connect a GitHub repository to generate documentation.
          </p>
          <Button asChild className="mt-2">
            <Link href={`/projects/${params.projectId}/upload`}>
              <Plus className="h-4 w-4" /> Add repository
            </Link>
          </Button>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {repositories?.items.map((repo) => (
          <Card key={repo.id}>
            <CardContent className="flex items-center justify-between p-5">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className="truncate font-mono text-sm text-paper">
                    {repo.github_url ? repo.github_url.replace("https://github.com/", "") : "Uploaded repository"}
                  </span>
                  <RepositoryStatusBadge status={repo.status} />
                </div>
                <p className="mt-1 text-xs text-paper-dim">
                  {repo.source_type === "zip_upload" ? "ZIP upload" : "GitHub"} · Added{" "}
                  {formatRelativeTime(repo.created_at)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button variant="outline" size="sm" asChild>
                  <Link href={`/repositories/${repo.id}/chat`}>
                    <MessageSquare className="h-3.5 w-3.5" /> Chat
                  </Link>
                </Button>
                <Button size="sm" asChild disabled={repo.status !== "ready"}>
                  <Link href={`/repositories/${repo.id}/documentation`}>
                    <FileText className="h-3.5 w-3.5" /> Documentation
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
