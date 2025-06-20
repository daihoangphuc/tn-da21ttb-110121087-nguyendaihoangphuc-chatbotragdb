"use client";

import { useEffect, useRef } from "react";

interface MessageContentProps {
  content: string;
}

export function MessageContent({ content }: MessageContentProps) {
  return (
    <div className="raw-content">
      <pre>{content}</pre>
    </div>
  );
} 