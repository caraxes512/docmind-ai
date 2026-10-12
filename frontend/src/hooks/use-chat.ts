import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Chat, ChatMessage } from "@/lib/types";

export function useChats(repositoryId: string | undefined) {
  return useQuery({
    queryKey: ["repositories", repositoryId, "chats"],
    queryFn: () => apiClient.get<Chat[]>(`/repositories/${repositoryId}/chats`),
    enabled: Boolean(repositoryId),
  });
}

export function useMessages(chatId: string | undefined) {
  return useQuery({
    queryKey: ["chats", chatId, "messages"],
    queryFn: () => apiClient.get<ChatMessage[]>(`/chats/${chatId}/messages`),
    enabled: Boolean(chatId),
  });
}

export function useCreateChat(repositoryId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => apiClient.post<Chat>(`/repositories/${repositoryId}/chats`, { title }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories", repositoryId, "chats"] });
    },
  });
}

export function useAskQuestion(chatId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      apiClient.post<{ user_message: ChatMessage; assistant_message: ChatMessage }>(
        `/chats/${chatId}/messages`,
        { content }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chats", chatId, "messages"] });
    },
  });
}
