import { Sparkles, User as UserIcon } from "lucide-react";
import { MarkdownRenderer } from "@/components/documentation/markdown-renderer";
import { CitationPill } from "@/components/chat/citation-pill";
import type { ChatMessage } from "@/lib/types";

export function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isUser ? "bg-ink-700 text-paper" : "bg-annotation/15 text-annotation"
        }`}
      >
        {isUser ? <UserIcon className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
      </div>
      <div className={`flex max-w-2xl flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
        <div className={`rounded px-4 py-3 ${isUser ? "bg-ink-700" : "bg-ink-800"}`}>
          {isUser ? (
            <p className="text-sm text-paper">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>
        {message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.citations.map((citation, i) => (
              <CitationPill key={i} citation={citation} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
