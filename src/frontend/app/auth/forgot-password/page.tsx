"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { authApi } from "@/lib/api";
import { ArrowLeft, Mail } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Vui lòng nhập địa chỉ email."
      });
      return;
    }    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Vui lòng nhập địa chỉ email hợp lệ."
      });
      return;
    }

    try {
      setLoading(true);
      // Create redirect URL for the password reset link
      const redirectUrl = `${window.location.origin}/auth/reset-password`;
      
      await authApi.forgotPassword(email, redirectUrl);
      
      setSent(true);
      toast({
        title: "Email đã được gửi!",
        description: "Vui lòng kiểm tra hộp thư của bạn để đặt lại mật khẩu.",
      });
    } catch (error: any) {
      console.error("Lỗi quên mật khẩu:", error);
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: error.message || "Có lỗi xảy ra khi gửi email đặt lại mật khẩu. Vui lòng thử lại."
      });
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-8rem)]">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader className="space-y-1 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <Mail className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-2xl font-bold">Email đã được gửi!</CardTitle>
            <CardDescription>
              Chúng tôi đã gửi liên kết đặt lại mật khẩu đến địa chỉ email:
              <br />
              <strong>{email}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-blue-50 p-4 text-sm text-blue-800">
              <p className="font-medium mb-2">Vui lòng kiểm tra:</p>
              <ul className="list-disc list-inside space-y-1 text-blue-700">
                <li>Hộp thư đến</li>
                <li>Thư mục spam/rác</li>
                <li>Thư mục khuyến mãi (nếu có)</li>
              </ul>
            </div>
            <p className="text-sm text-muted-foreground text-center">
              Không nhận được email? Vui lòng kiểm tra địa chỉ email và thử lại.
            </p>
          </CardContent>
          <CardFooter className="flex flex-col space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                setSent(false);
                setEmail("");
              }}
            >
              Gửi lại email
            </Button>
            <Link href="/auth/login" className="w-full">
              <Button variant="ghost" className="w-full">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Quay lại đăng nhập
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center min-h-[calc(100vh-8rem)]">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Quên mật khẩu</CardTitle>
          <CardDescription className="text-center">
            Nhập địa chỉ email của bạn và chúng tôi sẽ gửi liên kết đặt lại mật khẩu
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Địa chỉ email</Label>
              <Input
                id="email"
                type="email"
                placeholder="email@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Đang gửi email..." : "Gửi liên kết đặt lại mật khẩu"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center">
          <Link href="/auth/login" className="text-sm text-primary hover:underline flex items-center">
            <ArrowLeft className="mr-1 h-3 w-3" />
            Quay lại đăng nhập
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
