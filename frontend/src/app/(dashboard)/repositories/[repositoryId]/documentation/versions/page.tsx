"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CheckCircle2, FileText } from "lucide-react";
import { useDocumentationVersions } from "@/hooks/use-documentation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { formatRelativeTime } from "@/lib/utils";

export default function VersionHistoryPage() {
  const params = useParams<{ repositoryId: string }>();
  const { data: versions, isLoading } = useDocumentationVersions(params.repositoryId);

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <Link
        href={`/repositories/${params.repositoryId}/documentation`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to documentation
      </Link>

      <h1 className="mb-1 font-display text-2xl font-medium text-paper">Version history</h1>
      <p className="mb-8 text-sm text-paper-dim">
        Each version corresponds to a commit. Incremental regenerations only replace affected documents —
        unaffected ones carry over unchanged.
      </p>

      {isLoading && (
        <div className="flex flex-col gap-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      )}

      <div className="relative flex flex-col gap-4 border-l border-ink-700 pl-6">
        {versions?.map((version) => (
          <div key={version.id} className="relative">
            <div
              className={`absolute -left-[29px] top-5 h-3 w-3 rounded-full border-2 ${
                version.is_current ? "border-annotation bg-annotation" : "border-ink-600 bg-ink-900"
              }`}
            />
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-display text-base font-medium text-paper">
                      Version {version.version_number}
                    </span>
                    {version.is_current && (
                      <Badge variant="success">
                        <CheckCircle2 className="mr-1 h-3 w-3" /> Current
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-paper-dim">{formatRelativeTime(version.created_at)}</span>
                </div>
                <p className="mt-1 font-mono text-xs text-paper-dim">
                  {version.commit_hash ? version.commit_hash.slice(0, 12) : "no commit hash"}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {version.documents.map((doc) => (
                    <Badge key={doc.id} variant="neutral">
                      <FileText className="mr-1 h-3 w-3" /> {doc.doc_type}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        ))}
      </div>

      {!isLoading && versions?.length === 0 && (
        <p className="text-sm text-paper-dim">No documentation has been generated for this repository yet.</p>
      )}
    </div>
  );
}
