import { Metadata } from "next";
import { AuthProvider } from "@/hooks/useAuth";

export const metadata: Metadata = {
  title: "Đặt lại mật khẩu | RAG System",
  description: "Đang chuyển hướng đến trang đặt lại mật khẩu",
};

export default function ResetPasswordCallbackLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      <main className="flex-1">
        <AuthProvider>{children}</AuthProvider>
      </main>
    </div>
  );
} 