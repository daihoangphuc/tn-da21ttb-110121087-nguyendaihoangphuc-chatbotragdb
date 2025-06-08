"use client";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Database, User, Copy, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState, useEffect } from "react";
import type { ReactNode } from "react";
import { StreamingContent } from "./streaming-content"

// Define Message type locally to avoid import issues
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    id: string;
    title: string;
    page: string;
    relevance: number;
  }>;
  citations?: Array<{
    id: string;
    text: string;
    sourceId: string;
  }>;
}

interface ChatMessageProps {
  message: Message;
  isLastMessage?: boolean;
  isTyping?: boolean;
  relatedQuestions?: Array<{ id: string; text: string; query: string }>;
  onRelatedQuestionClick?: (query: string) => void;
}

export function ChatMessage({ 
  message, 
  isLastMessage = false, 
  isTyping = false,
  relatedQuestions = [],
  onRelatedQuestionClick 
}: ChatMessageProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const copyToClipboard = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  };

  return (
    <div
      className={cn(
        "flex gap-3",
        message.role === "user" ? "flex-row-reverse ml-auto" : "",
        message.role === "user" ? "max-w-[800px]" : "max-w-[850px]"
      )}
    >
      <Avatar className="h-8 w-8 mt-1 flex-shrink-0">
        {message.role === "assistant" ? (
          <>
            <AvatarImage src="/images/bot-avatar.svg" alt="Bot" />
            <AvatarFallback className="bg-primary/10 text-primary">
              <Database className="h-4 w-4" />
            </AvatarFallback>
          </>
        ) : (
          <>
            <AvatarImage src="/images/user-avatar.svg" alt="User" />
            <AvatarFallback className="bg-secondary text-secondary-foreground">
              <User className="h-4 w-4" />
            </AvatarFallback>
          </>
        )}
      </Avatar>
      <div
        className={cn(
          message.role === "assistant"
            ? "bg-white/70 dark:bg-background/80 rounded-xl border shadow-md p-4 w-full backdrop-blur-sm"
            : "bg-primary text-primary-foreground inline-block p-4 rounded-lg shadow-md overflow-hidden"
        )}
      >
        {message.role === "user" ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <>
            <div className="markdown-content overflow-hidden">
              <StreamingContent content={message.content} />
            </div>

            {/* Hiển thị các câu hỏi liên quan */}
            {message.role === "assistant" && 
              isLastMessage && 
              !isTyping && 
              relatedQuestions.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/40">
                <div className="text-sm font-medium mb-2 flex items-center gap-1.5 text-foreground">
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    width="16" 
                    height="16" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2" 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    className="text-primary"
                  >
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12" y2="8"/>
                  </svg>
                  <span>Có thể bạn cũng quan tâm:</span>
                </div>

                <div className="grid gap-2 sm:grid-cols-1 md:grid-cols-3">
                  {relatedQuestions.map((question) => (
                    <button
                      key={question.id}
                      className="text-sm text-left px-3 py-2 rounded-lg border border-border/50 hover:border-primary/50 hover:bg-primary/10 transition-all text-muted-foreground hover:text-foreground flex items-start gap-2 group relative overflow-hidden"
                      onClick={() => onRelatedQuestionClick?.(question.query)}
                    >
                      <span className="absolute inset-0 bg-primary/5 dark:bg-primary/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></span>
                      <span className="relative z-10">
                        {question.text}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
} 