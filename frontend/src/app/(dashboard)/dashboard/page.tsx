"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Plus, FolderGit2 } from "lucide-react";
import { useProjects, useCreateProject } from "@/hooks/use-projects";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription,
} from "@/components/ui/dialog";
import { formatRelativeTime } from "@/lib/utils";

export default function DashboardPage() {
  const { data, isLoading } = useProjects();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  return (
    <div className="mx-auto max-w-5xl px-8 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-medium text-paper">Projects</h1>
          <p className="mt-1 text-sm text-paper-dim">Your documented repositories, organized by project.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4" /> New project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <CreateProjectForm onCreated={() => setIsDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {!isLoading && data?.items.length === 0 && (
        <Card className="flex flex-col items-center gap-3 border-dashed py-16 text-center">
          <FolderGit2 className="h-8 w-8 text-paper-dim" />
          <CardTitle>No projects yet</CardTitle>
          <CardDescription>Create a project to start uploading or connecting a repository.</CardDescription>
          <Button className="mt-2" onClick={() => setIsDialogOpen(true)}>
            <Plus className="h-4 w-4" /> New project
          </Button>
        </Card>
      )}

      {!isLoading && data && data.items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((project) => (
            <Link key={project.id} href={`/projects/${project.id}`}>
              <Card className="h-full transition-colors hover:border-blueprint/60">
                <CardHeader>
                  <CardTitle>{project.name}</CardTitle>
                  <CardDescription>{project.description || "No description"}</CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between text-xs text-paper-dim">
                  <span>
                    {project.repository_count} repositor{project.repository_count === 1 ? "y" : "ies"}
                  </span>
                  <span>Updated {formatRelativeTime(project.updated_at)}</span>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateProjectForm({ onCreated }: { onCreated: () => void }) {
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    await createProject.mutateAsync({ name, description: description || undefined });
    onCreated();
  };

  return (
    <>
      <DialogHeader>
        <DialogTitle>New project</DialogTitle>
        <DialogDescription>Group one or more repositories under a shared workspace.</DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="project-name">Name</Label>
          <Input id="project-name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="My API service" />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="project-description">Description (optional)</Label>
          <Input
            id="project-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this project do?"
          />
        </div>
        <Button type="submit" disabled={createProject.isPending}>
          {createProject.isPending ? "Creating…" : "Create project"}
        </Button>
      </form>
    </>
  );
}
