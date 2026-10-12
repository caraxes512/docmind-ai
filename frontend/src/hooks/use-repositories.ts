import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Page, Repository, RepositoryFile } from "@/lib/types";

export function useRepositories(projectId: string | undefined) {
  return useQuery({
    queryKey: ["projects", projectId, "repositories"],
    queryFn: () => apiClient.get<Page<Repository>>(`/projects/${projectId}/repositories?limit=50`),
    enabled: Boolean(projectId),
  });
}

export function useRepository(repositoryId: string | undefined) {
  return useQuery({
    queryKey: ["repositories", repositoryId],
    queryFn: () => apiClient.get<Repository>(`/repositories/${repositoryId}`),
    enabled: Boolean(repositoryId),
    // Repository status changes as ingestion proceeds (pending -> scanning ->
    // ready/failed) — poll while it's still in a transitional state so the
    // upload page's status indicator updates without a manual refresh.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && !["ready", "failed"].includes(status) ? 3000 : false;
    },
  });
}

export function useRepositoryFiles(repositoryId: string | undefined) {
  return useQuery({
    queryKey: ["repositories", repositoryId, "files"],
    queryFn: () => apiClient.get<Page<RepositoryFile>>(`/repositories/${repositoryId}/files?limit=100`),
    enabled: Boolean(repositoryId),
  });
}

export function useUploadRepository(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiClient.postForm<{ repository: Repository; task_id: string }>(
        `/projects/${projectId}/repositories/upload`,
        formData
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "repositories"] });
    },
  });
}

export function useCloneRepository(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { github_url: string; branch?: string }) =>
      apiClient.post<{ repository: Repository; task_id: string }>(
        `/projects/${projectId}/repositories/clone`,
        input
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "repositories"] });
    },
  });
}
