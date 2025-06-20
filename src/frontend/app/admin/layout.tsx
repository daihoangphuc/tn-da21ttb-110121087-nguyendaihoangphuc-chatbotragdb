"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { HydrationSafe } from "@/components/ui/hydration-safe";
import { AdminLayout } from "@/components/admin-layout";

export default function AdminAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user) {
        // Chưa đăng nhập, chuyển về trang login
        router.push("/auth/login");
      } else if (user.role !== "admin") {
        // Không phải admin, chuyển về trang chủ
        router.push("/");
      }
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <HydrationSafe 
        className="flex items-center justify-center h-screen"
        fallback={
          <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
        }
      >
        <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
      </HydrationSafe>
    );
  }

  if (!user || user.role !== "admin") {
    return null; // Sẽ được chuyển hướng bởi useEffect
  }

  return (
    <HydrationSafe>
      <AdminLayout>
        {children}
      </AdminLayout>
    </HydrationSafe>
  );
} 