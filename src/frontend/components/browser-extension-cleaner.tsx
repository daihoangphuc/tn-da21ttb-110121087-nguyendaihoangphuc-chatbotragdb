"use client";

import { useEffect } from 'react';
import { useBrowserExtensionCleaner } from '@/lib/utils';

/**
 * Component để clean browser extension attributes và tránh hydration mismatch
 * Nên được đặt trong root layout để chạy toàn ứng dụng
 */
export function BrowserExtensionCleaner() {
  const cleanupExtensions = useBrowserExtensionCleaner();
  
  useEffect(() => {
    // Clean extension attributes ngay khi component mount
    return cleanupExtensions();
  }, [cleanupExtensions]);
  
  // Component này không render gì cả
  return null;
} 