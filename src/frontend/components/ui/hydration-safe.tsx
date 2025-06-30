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
  const [hasMounted, setHasMounted] = useState(false);

  useEffect(() => {
    // Đảm bảo component đã mount hoàn toàn
    setHasMounted(true);
    
    // Delay một chút để đảm bảo browser extensions đã chạy xong
    const timer = setTimeout(() => {
      setIsClient(true);
    }, 10);
    
    return () => clearTimeout(timer);
  }, []);

  // Trong lúc đang hydrate - render fallback hoặc placeholder
  if (!hasMounted || !isClient) {
    if (fallback) {
      return (
        <div 
          className={className} 
          suppressHydrationWarning={true}
          style={{ suppressHydrationWarning: true } as any}
        >
          {fallback}
        </div>
      );
    }
    
    // Nếu không có fallback, render empty div để tránh layout shift
    return (
      <div 
        className={className} 
        suppressHydrationWarning={true}
        style={{ suppressHydrationWarning: true } as any}
      />
    );
  }

  // Sau khi hydration hoàn tất và stable, render children thật
  return (
    <div 
      className={className} 
      suppressHydrationWarning={true}
      style={{ suppressHydrationWarning: true } as any}
    >
      {children}
    </div>
  );
} 