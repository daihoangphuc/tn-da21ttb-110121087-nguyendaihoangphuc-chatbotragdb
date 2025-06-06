"use client";

import React, { useEffect, useState } from "react";

interface HydrationSafeProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Một component wrapper để tránh lỗi hydration bằng cách chỉ render children
 * sau khi hydration đã hoàn tất trên client
 */
export function HydrationSafe({ children, fallback }: HydrationSafeProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Nếu chưa ở client, render fallback hoặc null
  if (!isClient) {
    return fallback || null;
  }

  // Sau khi hydration hoàn tất, render children
  return <>{children}</>;
} 