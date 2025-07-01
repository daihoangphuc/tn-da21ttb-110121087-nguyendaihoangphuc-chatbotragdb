"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { user, loading, checkAuth } = useAuth();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const verifyAuth = async () => {
      if (!loading) {
        const authenticated = await checkAuth();
        setIsAuthenticated(authenticated);
        
        if (!authenticated) {
          router.push("/auth/login");
        }
      }
    };

    verifyAuth();
  }, [loading, router, checkAuth]);

  // Hiển thị loading khi đang kiểm tra xác thực hoặc chưa mount
  if (!mounted || loading || isAuthenticated === null) {
    return (
      <div className="flex items-center justify-center h-screen" suppressHydrationWarning={true}>
        <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin" suppressHydrationWarning={true}></div>
      </div>
    );
  }

  // Nếu đã xác thực, hiển thị nội dung
  return isAuthenticated ? <div suppressHydrationWarning={true}>{children}</div> : null;
} 