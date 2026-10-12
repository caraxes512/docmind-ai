import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { DocumentationVersion, DocumentType, GeneratedDocument, Task } from "@/lib/types";

export function useCurrentDocumentation(repositoryId: string | undefined) {
  return useQuery({
    queryKey: ["repositories", repositoryId, "documentation", "current"],
    queryFn: () => apiClient.get<DocumentationVersion>(`/repositories/${repositoryId}/documentation`),
    enabled: Boolean(repositoryId),
    retry: false, // a 404 here just means "no documentation generated yet" — don't retry that
  });
}

export function useDocumentationVersions(repositoryId: string | undefined) {
  return useQuery({
    queryKey: ["repositories", repositoryId, "documentation", "versions"],
    queryFn: () =>
      apiClient.get<DocumentationVersion[]>(`/repositories/${repositoryId}/documentation/versions`),
    enabled: Boolean(repositoryId),
  });
}

export function useDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => apiClient.get<GeneratedDocument>(`/documentation/${documentId}`),
    enabled: Boolean(documentId),
  });
}

export function useGenerateDocumentation(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docTypes?: DocumentType[]) =>
      apiClient.post<Task>(`/repositories/${repositoryId}/documentation/generate`, {
        doc_types: docTypes ?? null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories", repositoryId, "documentation"] });
    },
  });
}

export function useRegenerateDocumentation(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { docTypes?: DocumentType[]; forceFullRegeneration?: boolean }) =>
      apiClient.post<Task>(`/repositories/${repositoryId}/documentation/regenerate`, {
        doc_types: input.docTypes ?? null,
        force_full_regeneration: input.forceFullRegeneration ?? false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories", repositoryId, "documentation"] });
    },
  });
}

export function useUpdateDocument(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      apiClient.patch<GeneratedDocument>(`/documentation/${documentId}`, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", documentId] });
    },
  });
}
