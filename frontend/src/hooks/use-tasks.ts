import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Task } from "@/lib/types";

export function useTask(taskId: string | undefined) {
  return useQuery({
    queryKey: ["tasks", taskId],
    queryFn: () => apiClient.get<Task>(`/tasks/${taskId}`),
    enabled: Boolean(taskId),
    // Progress polling — the core mechanism behind Step 1's "display progress"
    // requirement. Stops polling once the task reaches a terminal state.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["queued", "running", "retrying"].includes(status) ? 2000 : false;
    },
  });
}
