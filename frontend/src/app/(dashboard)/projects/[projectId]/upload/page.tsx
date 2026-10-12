"use client";

import { useCallback, useState, type DragEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, UploadCloud, Github } from "lucide-react";
import { useUploadRepository, useCloneRepository } from "@/hooks/use-repositories";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ApiError } from "@/lib/auth-context";
import { formatBytes } from "@/lib/utils";

export default function RepositoryUploadPage() {
  const params = useParams<{ projectId: string }>();
  const router = useRouter();

  return (
    <div className="mx-auto max-w-2xl px-8 py-10">
      <Link
        href={`/projects/${params.projectId}`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to project
      </Link>

      <h1 className="font-display text-2xl font-medium text-paper">Add a repository</h1>
      <p className="mt-1 text-sm text-paper-dim">Upload a ZIP archive, or connect a GitHub repository.</p>

      <Tabs defaultValue="upload" className="mt-8">
        <TabsList>
          <TabsTrigger value="upload">ZIP upload</TabsTrigger>
          <TabsTrigger value="github">GitHub</TabsTrigger>
        </TabsList>

        <TabsContent value="upload">
          <ZipUploadForm
            projectId={params.projectId}
            onUploaded={(repositoryId) => router.push(`/repositories/${repositoryId}/documentation`)}
          />
        </TabsContent>

        <TabsContent value="github">
          <GitHubCloneForm
            projectId={params.projectId}
            onCloned={(repositoryId) => router.push(`/repositories/${repositoryId}/documentation`)}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ZipUploadForm({
  projectId,
  onUploaded,
}: {
  projectId: string;
  onUploaded: (repositoryId: string) => void;
}) {
  const uploadRepository = useUploadRepository(projectId);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
    const file = event.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  }, []);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setError(null);
    try {
      const result = await uploadRepository.mutateAsync(selectedFile);
      onUploaded(result.repository.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    }
  };

  return (
    <div className="mt-6 flex flex-col gap-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDraggingOver(true);
        }}
        onDragLeave={() => setIsDraggingOver(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center gap-3 rounded border-2 border-dashed p-12 text-center transition-colors ${
          isDraggingOver ? "border-blueprint bg-blueprint/5" : "border-ink-600"
        }`}
      >
        <UploadCloud className="h-8 w-8 text-paper-dim" />
        {selectedFile ? (
          <div>
            <p className="font-mono text-sm text-paper">{selectedFile.name}</p>
            <p className="text-xs text-paper-dim">{formatBytes(selectedFile.size)}</p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-paper">Drag and drop a .zip archive here</p>
            <p className="text-xs text-paper-dim">or click below to browse — max 200MB</p>
          </div>
        )}
        <label>
          <input
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />
          <Button variant="outline" size="sm" asChild>
            <span>Browse files</span>
          </Button>
        </label>
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      <Button onClick={handleUpload} disabled={!selectedFile || uploadRepository.isPending}>
        {uploadRepository.isPending ? "Uploading…" : "Upload and analyze"}
      </Button>
    </div>
  );
}

function GitHubCloneForm({
  projectId,
  onCloned,
}: {
  projectId: string;
  onCloned: (repositoryId: string) => void;
}) {
  const cloneRepository = useCloneRepository(projectId);
  const [githubUrl, setGithubUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleClone = async () => {
    setError(null);
    try {
      const result = await cloneRepository.mutateAsync({
        github_url: githubUrl,
        branch: branch || undefined,
      });
      onCloned(result.repository.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Clone failed. Please try again.");
    }
  };

  return (
    <Card className="mt-6">
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="flex items-center gap-2 text-sm text-paper-dim">
          <Github className="h-4 w-4" />
          Public repositories clone directly. Private repositories require connecting GitHub in{" "}
          <Link href="/settings" className="text-blueprint hover:underline">
            Settings
          </Link>
          .
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="github-url">Repository URL</Label>
          <Input
            id="github-url"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            placeholder="https://github.com/owner/repo"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="branch">Branch (optional)</Label>
          <Input id="branch" value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="main" />
        </div>
        {error && <p className="text-sm text-danger">{error}</p>}
        <Button onClick={handleClone} disabled={!githubUrl || cloneRepository.isPending}>
          {cloneRepository.isPending ? "Cloning…" : "Clone and analyze"}
        </Button>
      </CardContent>
    </Card>
  );
}
