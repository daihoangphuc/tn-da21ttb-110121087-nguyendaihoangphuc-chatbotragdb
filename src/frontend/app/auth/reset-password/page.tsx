"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/use-toast";
import { z } from "zod";
import { useAuth } from "@/hooks/useAuth";

// Schema for password validation
const passwordSchema = z.string()
  .min(8, "Mật khẩu phải có ít nhất 8 ký tự")
  .regex(/[A-Z]/, "Mật khẩu phải có ít nhất một chữ hoa")
  .regex(/[a-z]/, "Mật khẩu phải có ít nhất một chữ thường")
  .regex(/[0-9]/, "Mật khẩu phải có ít nhất một chữ số");

export default function ResetPasswordPage() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenProcessed, setTokenProcessed] = useState(false); // Add this flag
  const router = useRouter();
  const { resetPassword } = useAuth();

  useEffect(() => {
    // Only process token once
    if (tokenProcessed) return;
    
    // Add a small delay to ensure the page has fully loaded
    const timer = setTimeout(() => {
      const getAccessTokenFromUrl = (): string | null => {
        if (typeof window === 'undefined') return null;

        console.log('Full URL:', window.location.href);
        console.log('Hash:', window.location.hash);
        console.log('Search:', window.location.search);

        // First try to get from hash fragment (#access_token=...)
        const hash = window.location.hash.substring(1);
        if (hash) {
          console.log('Processing hash:', hash);

          // Parse the hash as URL parameters
          const hashParams = new URLSearchParams(hash);
          const tokenFromHash = hashParams.get('access_token');
          if (tokenFromHash) {
            console.log('Found access_token in hash fragment:', tokenFromHash);
            return tokenFromHash;
          }

          // Also try to parse manually in case URLSearchParams doesn't work with hash
          const hashParts = hash.split('&');
          for (const part of hashParts) {
            const [key, value] = part.split('=');
            if (key === 'access_token' && value) {
              console.log('Found access_token manually from hash:', value);
              return decodeURIComponent(value);
            }
          }
        }

        // Then try to get from query parameters
        const searchParams = new URLSearchParams(window.location.search);

        const accessToken = searchParams.get('access_token');
        if (accessToken) {
          console.log('Found access_token in query parameters:', accessToken);
          return accessToken;
        }

        const token = searchParams.get('token');
        if (token) {
          console.log('Found token in query parameters:', token);
          return token;
        }

        console.log('No token found in URL');
        return null;
      };

      const token = getAccessTokenFromUrl();
      if (token) {
        setAccessToken(token);
        setTokenProcessed(true); // Mark as processed
        // Clean the URL by removing the hash fragment and query params after extracting the token
        if (typeof window !== 'undefined') {
          window.history.replaceState({}, document.title, window.location.pathname);
        }
      } else {
        setError("Không tìm thấy token xác thực trong URL. Vui lòng kiểm tra liên kết hoặc yêu cầu liên kết mới.");
        setTokenProcessed(true); // Mark as processed even if no token found
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [tokenProcessed]); // Add tokenProcessed to dependencies

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!accessToken) {
      toast({
        variant: "warning",
        title: "Cảnh báo",
        description: "Không tìm thấy token xác thực. Vui lòng yêu cầu liên kết đặt lại mật khẩu mới."
      });
      return;
    }

    // Validate password
    try {
      passwordSchema.parse(password);
    } catch (error: any) {
      if (error instanceof z.ZodError) {
        toast({
          variant: "warning",
          title: "Cảnh báo",
          description: error.errors[0].message
        });
      } else {
        toast({
          variant: "warning",
          title: "Cảnh báo",
          description: "Mật khẩu không hợp lệ"
        });
      }
      return;
    }

    // Check if passwords match
    if (password !== confirmPassword) {
      toast({
        variant: "warning",
        title: "Cảnh báo",
        description: "Mật khẩu xác nhận không khớp"
      });
      return;
    }

    try {
      setLoading(true);

      // Call resetPassword method from useAuth hook
      await resetPassword(accessToken, password);

      // Show success toast
      toast({
        title: "Thành công",
        description: "Mật khẩu của bạn đã được đặt lại thành công."
      });

      // Redirect immediately to login page
      router.push("/auth/login");
      
    } catch (error: any) {
      // Handle errors
      let errorMessage = "Không thể đặt lại mật khẩu";

      if (error instanceof Error && error.message) {
        errorMessage = error.message;

        if (error.message.includes("Mật khẩu mới phải khác mật khẩu cũ")) {
          router.replace("/auth/login");
          return;
        }
      }

      toast({
        variant: "destructive",
        title: "Lỗi",
        description: errorMessage
      });
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-[calc(100vh-8rem)]">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold text-center">Đặt lại mật khẩu</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="p-4 bg-red-50 text-red-700 rounded-md">
              <p className="text-center">{error}</p>
            </div>
            <div className="mt-4">
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push("/auth/forgot-password")}
              >
                Yêu cầu liên kết mới
              </Button>
            </div>
          </CardContent>
          <CardFooter className="flex justify-center">
            <p className="text-sm text-muted-foreground">
              <Link href="/auth/login" className="text-primary hover:underline">
                Quay lại đăng nhập
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center min-h-[calc(100vh-8rem)]">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Đặt lại mật khẩu</CardTitle>
          <CardDescription className="text-center">
            Nhập mật khẩu mới cho tài khoản của bạn
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!success ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password">Mật khẩu mới</Label>
                <PasswordInput
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường và số.
                  Mật khẩu mới phải khác mật khẩu cũ của bạn.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Xác nhận mật khẩu</Label>
                <PasswordInput
                  id="confirmPassword"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={loading}
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Đang xử lý..." : "Đặt lại mật khẩu"}
              </Button>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 text-green-700 rounded-md">
                <p className="text-center">
                  Mật khẩu của bạn đã được đặt lại thành công.
                  Bạn sẽ được chuyển hướng đến trang đăng nhập trong vài giây.
                </p>
              </div>
              <Button
                className="w-full"
                onClick={() => router.push("/auth/login")}
              >
                Đăng nhập ngay
              </Button>
            </div>
          )}
        </CardContent>
        <CardFooter className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            <Link href="/auth/login" className="text-primary hover:underline">
              Quay lại đăng nhập
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
} 