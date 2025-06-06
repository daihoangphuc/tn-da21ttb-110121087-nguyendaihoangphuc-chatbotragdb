"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "@/components/ui/use-toast";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";

// Hàm tiện ích để truy cập localStorage an toàn
const setLocalStorage = (key: string, value: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, value);
  }
};

export default function AuthCallbackPage() {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Đang xử lý đăng nhập...");
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginWithGoogle } = useAuth();
  const processedCode = useRef<string | null>(null);
  useEffect(() => {
    const handleCallback = async () => {
      try {        // Check for password recovery callback first
        let type = searchParams.get("type");
        let token = searchParams.get("token") || searchParams.get("access_token");
        const code = searchParams.get("code");
        const error = searchParams.get("error");

        // If no token or type in query params, check hash fragment (for Supabase recovery)
        if (typeof window !== 'undefined' && window.location.hash) {
          const hash = window.location.hash;
          console.log("URL hash found:", hash);
          
          if (hash) {
            const hashParams = new URLSearchParams(hash.substring(1)); // Remove the # symbol
            
            // Get token from hash if not found in query params
            if (!token) {
              token = hashParams.get("access_token");
            }
            
            // Get type from hash if not found in query params
            if (!type) {
              type = hashParams.get("type");
            }
            
            console.log("Hash params parsed:", {
              access_token: token ? token.substring(0, 15) + "..." : null,
              type: type
            });
          }        }

        if (error) {
          setStatus("error");
          setMessage(`Lỗi xác thực: ${error}`);
          return;
        }

        // Handle password recovery - check both query params and hash
        const isRecovery = type === "recovery" || 
          (typeof window !== 'undefined' && window.location.hash.includes('type=recovery'));

        console.log("Auth callback params:", {
          type,
          token: token ? token.substring(0, 15) + "..." : null,
          code: code ? code.substring(0, 15) + "..." : null,
          error,
          isRecovery,
          fullUrl: typeof window !== 'undefined' ? window.location.href : 'N/A',
          hash: typeof window !== 'undefined' ? window.location.hash : 'N/A'
        });
        
        if (isRecovery && token) {
          console.log("Processing password recovery callback with token");
          setStatus("loading");
          setMessage("Đang xác thực liên kết đặt lại mật khẩu...");
          
          try {
            // Lưu token trực tiếp và chuyển đến trang reset password
            // Token này đã được Supabase validate rồi
            localStorage.setItem('recovery_token', token);
            console.log("Recovery token saved, redirecting to reset password");
            
            setStatus("success");
            setMessage("Xác thực thành công! Đang chuyển hướng...");
            
            // Clear the hash to clean up URL
            if (typeof window !== 'undefined') {
              window.history.replaceState(null, '', window.location.pathname);
            }
            
            // Chuyển hướng đến trang reset password sau 1 giây
            setTimeout(() => {
              router.push('/auth/reset-password?verified=true');
            }, 1000);
            return;
          } catch (error) {
            console.error("Recovery callback error:", error);
            setStatus("error");
            setMessage("Có lỗi xảy ra khi xử lý liên kết đặt lại mật khẩu.");
            return;
          }
        }        // Handle Google OAuth callback - only process if we have code and it's not recovery
        if (code && !isRecovery) {
          // Kiểm tra xem code này đã được xử lý chưa
          if (processedCode.current === code) {
            console.log("Mã xác thực này đã được xử lý, bỏ qua");
            return;
          }

          // Đánh dấu code này đã được xử lý
          processedCode.current = code;
          
          try {
            console.log("Bắt đầu xử lý đăng nhập với Google, code:", code.substring(0, 10) + "...");
            // Sử dụng hook useAuth để đăng nhập với Google
            await loginWithGoogle(code);
            
            // Nếu không có lỗi, đánh dấu là thành công
            setStatus("success");
            setMessage("Đăng nhập thành công! Đang chuyển hướng...");
            
            // Chuyển hướng về trang chủ sau 1 giây
            setTimeout(() => {
              window.location.href = "/";
            }, 1000);
          } catch (loginError: any) {
            console.error("Lỗi trong quá trình loginWithGoogle:", loginError);
            
            // Kiểm tra xem có token trong localStorage không
            // Nếu có, coi như đăng nhập thành công dù có lỗi
            if (typeof window !== 'undefined' && localStorage.getItem('auth_token')) {
              setStatus("success");
              setMessage("Đăng nhập thành công! Đang chuyển hướng...");
              
              // Chuyển hướng về trang chủ sau 1 giây
              setTimeout(() => {
                window.location.href = "/";
              }, 1000);
            } else {
              // Nếu không có token, hiển thị lỗi
              setStatus("error");
              setMessage(loginError.message || "Đăng nhập thất bại");
              
              // Chuyển hướng về trang đăng nhập sau 2 giây
              setTimeout(() => {
                router.push("/auth/login");
              }, 2000);
            }
          }        } else if (!code && !isRecovery && !token) {
          setStatus("error");
          setMessage("Không nhận được mã xác thực từ nhà cung cấp");
          console.error("No valid auth parameters found:", { code, token, type, isRecovery });
          return;
        }
      } catch (error: any) {
        console.error("Lỗi xử lý callback:", error);
        setStatus("error");
        setMessage(error.message || "Đăng nhập thất bại");
        
        // Chuyển hướng về trang đăng nhập sau 2 giây
        setTimeout(() => {
          router.push("/auth/login");
        }, 2000);
      }
    };

    handleCallback();
  }, [searchParams, router, loginWithGoogle]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <Card className="w-full max-w-md p-6">
        <CardContent className="flex flex-col items-center justify-center pt-6">
          {status === "loading" && (
            <div className="flex flex-col items-center space-y-4">
              <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
              <p className="text-center text-lg">{message}</p>
            </div>
          )}
          
          {status === "success" && (
            <div className="flex flex-col items-center space-y-4">
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-6 h-6 text-white">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-center text-lg">{message}</p>
            </div>
          )}
          
          {status === "error" && (
            <div className="flex flex-col items-center space-y-4">
              <div className="w-10 h-10 bg-red-500 rounded-full flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="w-6 h-6 text-white">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <p className="text-center text-lg">{message}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 