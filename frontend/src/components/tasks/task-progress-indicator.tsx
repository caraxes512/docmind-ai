"use client";

import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { useTask } from "@/hooks/use-tasks";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

export function TaskProgressIndicator({ taskId, label }: { taskId: string; label: string }) {
  const { data: task } = useTask(taskId);

  if (!task) return null;

  if (task.status === "succeeded") {
    return (
      <div className="flex items-center gap-2 text-sm text-success">
        <CheckCircle2 className="h-4 w-4" /> {label} complete
      </div>
    );
  }

  if (task.status === "failed" || task.status === "cancelled") {
    return (
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-sm text-danger">
          <XCircle className="h-4 w-4" />
          {label} {task.status}
        </div>
        {task.error_message && <p className="text-xs text-paper-dim">{task.error_message}</p>}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between text-sm text-paper-dim">
        <span className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin text-blueprint" />
          {label}
        </span>
        <Badge variant="default">{task.status}</Badge>
      </div>
      <Progress value={task.progress} />
    </div>
  );
}
