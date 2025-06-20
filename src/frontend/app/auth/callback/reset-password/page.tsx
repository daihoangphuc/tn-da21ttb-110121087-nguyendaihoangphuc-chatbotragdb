"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";

export default function ResetPasswordCallback() {
  const router = useRouter();

  useEffect(() => {
    // Lấy toàn bộ URL hiện tại
    const currentUrl = window.location.href;
    
    // Kiểm tra xem URL có chứa hash fragment không
    if (currentUrl.includes("#access_token=")) {
      // Lấy phần hash fragment
      const hashFragment = window.location.hash;
      
      // Chuyển hướng đến trang reset-password với hash fragment
      window.location.href = `/auth/reset-password${hashFragment}`;
    } else {
      // Nếu không có token, chuyển hướng đến trang quên mật khẩu
      router.push("/auth/forgot-password");
    }
  }, [router]);

  return (
    <div className="flex justify-center items-center min-h-screen">
      <Card className="w-full max-w-md p-6">
        <CardContent className="flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="mt-4 text-center">Đang chuyển hướng...</p>
        </CardContent>
      </Card>
    </div>
  );
} 