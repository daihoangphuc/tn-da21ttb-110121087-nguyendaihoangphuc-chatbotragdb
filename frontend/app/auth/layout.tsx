"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  // Nếu đang ở trang callback, hiển thị nội dung ngay lập tức
  if (pathname === "/auth/callback") {
    return <>{children}</>;
  }

  // Hiển thị loading khi đang kiểm tra xác thực
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8">
        <div className="flex justify-center mb-8">
          <Link href="/" className="text-2xl font-bold text-primary">
            Hệ thống RAG
          </Link>
        </div>
        {children}
      </div>
    </div>
  );
} 