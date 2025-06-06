"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { MainLayout } from "@/components/main-layout";
import { useAuth } from "@/hooks/useAuth";
import { HydrationSafe } from "@/components/ui/hydration-safe";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/auth/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <HydrationSafe fallback={
        <div className="flex items-center justify-center h-screen">
          <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
        </div>
      }>
        <div className="flex items-center justify-center h-screen">
          <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
        </div>
      </HydrationSafe>
    );
  }

  if (!user) {
    return null; // Sẽ được chuyển hướng bởi useEffect
  }

  return <MainLayout />;
}
