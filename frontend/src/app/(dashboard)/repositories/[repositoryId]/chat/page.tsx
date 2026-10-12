"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, MessageSquarePlus } from "lucide-react";
import { useChats, useCreateChat, useMessages, useAskQuestion } from "@/hooks/use-chat";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessageBubble } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";
import { cn } from "@/lib/utils";

export default function RepositoryChatPage() {
  const params = useParams<{ repositoryId: string }>();
  const { data: chats, isLoading: areChatsLoading } = useChats(params.repositoryId);
  const createChat = useCreateChat(params.repositoryId);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);

  useEffect(() => {
    const firstChat = chats?.[0];
    if (!activeChatId && firstChat) {
      setActiveChatId(firstChat.id);
    }
  }, [chats, activeChatId]);

  const handleNewChat = async () => {
    const chat = await createChat.mutateAsync(undefined);
    setActiveChatId(chat.id);
  };

  return (
    <div className="flex h-screen">
      <aside className="flex w-64 shrink-0 flex-col border-r border-ink-700 bg-ink-800">
        <div className="flex items-center justify-between p-4">
          <Link
            href={`/repositories/${params.repositoryId}/documentation`}
            className="inline-flex items-center gap-1.5 text-sm text-paper-dim hover:text-paper"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
        </div>
        <div className="px-4">
          <Button size="sm" variant="outline" className="w-full" onClick={handleNewChat} disabled={createChat.isPending}>
            <MessageSquarePlus className="h-3.5 w-3.5" /> New chat
          </Button>
        </div>
        <div className="mt-3 flex flex-col gap-0.5 px-2">
          {areChatsLoading && <Skeleton className="mx-2 h-9" />}
          {chats?.map((chat) => (
            <button
              key={chat.id}
              onClick={() => setActiveChatId(chat.id)}
              className={cn(
                "truncate rounded px-3 py-2 text-left text-sm transition-colors hover:bg-ink-700",
                activeChatId === chat.id ? "bg-ink-700 text-paper" : "text-paper-dim"
              )}
            >
              {chat.title || "Untitled chat"}
            </button>
          ))}
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        {activeChatId ? (
          <ChatThread chatId={activeChatId} />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <p className="text-sm text-paper-dim">Start a new chat to ask questions about this repository.</p>
            <Button onClick={handleNewChat} disabled={createChat.isPending}>
              <MessageSquarePlus className="h-4 w-4" /> New chat
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function ChatThread({ chatId }: { chatId: string }) {
  const { data: messages, isLoading } = useMessages(chatId);
  const askQuestion = useAskQuestion(chatId);
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <div className="mx-auto flex max-w-2xl flex-col gap-6">
          {isLoading && <Skeleton className="h-16" />}
          {messages?.length === 0 && (
            <p className="text-center text-sm text-paper-dim">
              Try: &quot;Explain the user registration flow&quot; or &quot;Which files implement authentication?&quot;
            </p>
          )}
          {messages?.map((message) => (
            <ChatMessageBubble key={message.id} message={message} />
          ))}
          {askQuestion.isPending && <p className="text-sm text-paper-dim">Thinking…</p>}
          <div ref={scrollAnchorRef} />
        </div>
      </div>
      <div className="border-t border-ink-700 px-8 py-4">
        <div className="mx-auto max-w-2xl">
          <ChatInput onSend={(content) => askQuestion.mutate(content)} isSending={askQuestion.isPending} />
        </div>
      </div>
    </>
  );
}
