"use client";

import { useState, type FormEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function ChatInput({ onSend, isSending }: { onSend: (content: string) => void; isSending: boolean }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim()) return;
    onSend(value.trim());
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about this repository — e.g. 'Where is JWT implemented?'"
        disabled={isSending}
      />
      <Button type="submit" size="icon" disabled={isSending || !value.trim()} aria-label="Send">
        <Send className="h-4 w-4" />
      </Button>
    </form>
  );
}
