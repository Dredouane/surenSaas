"use client";

import { useState, useRef, useEffect, memo, useCallback } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  sending: boolean;
}

export const ChatInput = memo(function ChatInput({ onSend, sending }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    if (!value.trim() || sending) return;
    onSend(value);
    setValue("");
  }, [value, sending, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  useEffect(() => {
    if (!sending && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [sending]);

  return (
    <div className="flex gap-2">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Écrivez votre message..."
        className={`flex-1 min-h-[60px] max-h-[120px] resize-none text-base ${sending ? "opacity-50" : ""}`}
        readOnly={sending}
      />
      <Button
        onClick={handleSend}
        disabled={!value.trim() || sending}
        className="self-end"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
});
