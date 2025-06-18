"use client";

import React, { useEffect, useState } from "react";

interface HydrationSafeProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  className?: string;
}

/**
 * Một component wrapper để tránh lỗi hydration bằng cách chỉ render children
 * sau khi hydration đã hoàn tất trên client. Đây là giải pháp cho các vấn đề:
 * - Browser extensions thêm attributes (như bis_skin_checked)
 * - Server/client HTML mismatch
 * - Dynamic content render khác nhau
 */
export function HydrationSafe({ children, fallback, className }: HydrationSafeProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    // Chỉ set isClient = true sau khi component đã mount hoàn toàn
    setIsClient(true);
  }, []);

  // Trong lúc đang hydrate (server-side hoặc client chưa ready)
  if (!isClient) {
    return fallback ? (
      <div className={className} suppressHydrationWarning>
        {fallback}
      </div>
    ) : (
      <div className={className} suppressHydrationWarning />
    );
  }

  // Sau khi hydration hoàn tất, render children thật
  return (
    <div className={className} suppressHydrationWarning>
      {children}
    </div>
  );
} 