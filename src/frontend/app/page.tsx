"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MainLayout } from "@/components/main-layout";
import { useAuth } from "@/hooks/useAuth";
import { HydrationSafe } from "@/components/ui/hydration-safe";

function HomeContent() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Kiểm tra xem có param student=true không
  const forceStudentMode = searchParams.get('student') === 'true';

  useEffect(() => {
    if (!loading && !user) {
      router.push("/auth/login");
    } else if (!loading && user && user.role === 'admin' && !forceStudentMode) {
      // Nếu user là admin và không force student mode, chuyển hướng đến trang quản lý admin
      router.push("/admin");
    }
  }, [loading, user, router, forceStudentMode]);

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

  if (!user) {
    return null; // Sẽ được chuyển hướng bởi useEffect
  }

  // Nếu user là admin nhưng chưa redirect và không force student mode (tránh hiển thị MainLayout)
  if (user.role === 'admin' && !forceStudentMode) {
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

  return (
    <HydrationSafe>
      <MainLayout />
    </HydrationSafe>
  );
}

export default function Home() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen">
        <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
      </div>
    }>
      <HomeContent />
    </Suspense>
  );
}
