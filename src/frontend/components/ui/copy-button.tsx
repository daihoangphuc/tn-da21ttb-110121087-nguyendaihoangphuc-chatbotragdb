"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CopyButtonProps {
  text: string;
}

export function CopyButton({ text }: CopyButtonProps) {
  const [isCopied, setIsCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(text);
    setIsCopied(true);

    setTimeout(() => {
      setIsCopied(false);
    }, 2000);
  };

  return (
    <button
      className={`copy-button-icon p-1.5 rounded-md hover:bg-secondary/80 transition-all ${
        isCopied ? "bg-success/20 text-success" : "bg-secondary/50 text-foreground"
      }`}
      onClick={copy}
      title={isCopied ? "Đã sao chép!" : "Sao chép"}
      aria-label={isCopied ? "Đã sao chép!" : "Sao chép code"}
    >
      {isCopied ? (
        <Check className="h-4 w-4" />
      ) : (
        <Copy className="h-4 w-4" />
      )}
    </button>
  );
} 