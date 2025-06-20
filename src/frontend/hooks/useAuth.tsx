"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, conversationsApi } from "@/lib/api";
import { toast } from "@/components/ui/use-toast";
import type { AuthResponse, ForgotPasswordResponse } from "@/types/auth";
import { fetchApi } from "@/lib/api";

// Định nghĩa kiểu dữ liệu cho User
export interface User {
  id: string;
  email: string;
  created_at?: string;
  name?: string;
  avatar_url?: string;
  role?: string; // 'admin' or 'student'
}

// Định nghĩa kiểu dữ liệu cho AuthContext
interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthResponse>;
  signup: (email: string, password: string) => Promise<AuthResponse>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
  loginWithGoogle: (code: string) => Promise<void>;
  forgotPassword: (email: string, redirectUrl?: string) => Promise<ForgotPasswordResponse>;
  resetPassword: (access_token: string, password: string) => Promise<{ status: string; message: string }>;
}

// Hàm tiện ích để truy cập localStorage an toàn
const getLocalStorage = (key: string): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(key);
  }
  return null;
};

const setLocalStorage = (key: string, value: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, value);
  }
};

const removeLocalStorage = (key: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(key);
  }
};

// Tạo context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  // Kiểm tra trạng thái xác thực khi component mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const token = getLocalStorage("auth_token");
        if (!token) {
          setLoading(false);
          return;
        }

        try {
          const userData = await authApi.getUser();
          console.log("User data from API:", userData);
          
          // Kiểm tra xem userData có trường role không
          if (userData) {
            console.log("User role from API:", userData.role);
            setUser(userData);
            
            // Cập nhật lại localStorage nếu có thông tin mới
            const storedUserInfo = getLocalStorage("user_info");
            if (storedUserInfo) {
              try {
                const parsedUserInfo = JSON.parse(storedUserInfo);
                console.log("Stored user info:", parsedUserInfo);
                
                // Cập nhật lại thông tin user trong localStorage nếu thiếu trường role
                if (userData.role && !parsedUserInfo.role) {
                  console.log("Updating stored user info with role:", userData.role);
                  setLocalStorage("user_info", JSON.stringify({
                    ...parsedUserInfo,
                    role: userData.role
                  }));
                }
              } catch (e) {
                console.error("Error parsing stored user info:", e);
              }
            }
          }
        } catch (error: any) {
          // Xóa token nếu không hợp lệ
          removeLocalStorage("auth_token");
          removeLocalStorage("user_info");
          
          // Không hiển thị toast cho lỗi này vì đây là quá trình tự động kiểm tra
          // và có thể gây phiền nhiễu cho người dùng
        }
      } catch (error) {
        // Không cần xử lý lỗi ở đây
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  // Hàm đăng nhập
  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await authApi.login({ email, password });
      
      // Debug: Log thông tin user và role
      console.log("Login response:", response);
      console.log("User info:", response.user);
      console.log("User role:", response.user.role);
      
      // Lưu token và thông tin người dùng
      setLocalStorage("auth_token", response.access_token);
      setLocalStorage("user_info", JSON.stringify(response.user));
      
      setUser(response.user);
      
      // Tạo hội thoại mới sau khi đăng nhập thành công
      try {
        // Chỉ tạo conversation mới khi user không phải là admin
        if (response.user.role !== "admin") {
          const conversationResponse = await conversationsApi.createConversation();
          if (conversationResponse && conversationResponse.conversation_id) {
            // Lưu conversation_id vào localStorage để MainLayout có thể sử dụng
            setLocalStorage("current_conversation_id", conversationResponse.conversation_id);
            console.log("Đã tạo hội thoại mới:", conversationResponse.conversation_id);
          }
        } else {
          console.log("Bỏ qua việc tạo hội thoại mới vì người dùng có vai trò admin");
        }
      } catch (error) {
        console.log("Không thể tạo hội thoại mới sau khi đăng nhập, sẽ tạo khi cần thiết");
      }
      
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đăng nhập thành công. Chào mừng bạn quay trở lại!",
      });

      // Chuyển hướng trực tiếp sau khi đăng nhập thành công
      // Bọc trong setTimeout để đảm bảo toast message được hiển thị
      setTimeout(() => {
        // Nếu là admin, chuyển tới trang admin dashboard
        if (response.user.role === "admin") {
          window.location.href = "/admin";
        } else {
          // Nếu là student hoặc vai trò khác, chuyển về trang chủ
          window.location.href = "/";
        }
      }, 0);
      
      return response;
    } catch (error: any) {
      // Xử lý lỗi từ backend
      let errorMessage = "Vui lòng kiểm tra lại email và mật khẩu";
      
      // Kiểm tra nếu có thông báo lỗi cụ thể từ backend
      if (error instanceof Error && error.message) {
        errorMessage = error.message;
      }
      
      // Hiển thị toast thông báo lỗi - đảm bảo toast hiển thị
      setTimeout(() => {
      toast({
        variant: "destructive",
        title: "Đăng nhập thất bại",
          description: errorMessage,
      });
      }, 0);
      
      // Ném lỗi để component gọi có thể xử lý
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Hàm đăng ký
  const signup = async (email: string, password: string) => {
    setLoading(true);
    try {
      const response = await authApi.signup(email, password);
      
      // Lưu token và thông tin người dùng
      setLocalStorage("auth_token", response.access_token);
      setLocalStorage("user_info", JSON.stringify(response.user));
      
      setUser(response.user);
      
      // Tạo hội thoại mới sau khi đăng ký thành công
      try {
        // Chỉ tạo conversation mới khi user không phải là admin
        if (response.user.role !== "admin") {
          const conversationResponse = await conversationsApi.createConversation();
          if (conversationResponse && conversationResponse.conversation_id) {
            // Lưu conversation_id vào localStorage để MainLayout có thể sử dụng
            setLocalStorage("current_conversation_id", conversationResponse.conversation_id);
            console.log("Đã tạo hội thoại mới sau khi đăng ký:", conversationResponse.conversation_id);
          }
        } else {
          console.log("Bỏ qua việc tạo hội thoại mới vì người dùng có vai trò admin");
        }
      } catch (error) {
        console.log("Không thể tạo hội thoại mới sau khi đăng ký, sẽ tạo khi cần thiết");
      }
      
      toast({
        variant: "success",
        title: "Thành công",
        description: "Tài khoản của bạn đã được tạo thành công!",
      });
      
      return response;
    } catch (error: any) {
      // Xử lý các loại lỗi cụ thể
      let errorMessage = "Vui lòng thử lại sau";
      let errorTitle = "Đăng ký thất bại";
      
      if (error.message) {
        errorMessage = error.message;
        
        // Xử lý trường hợp email đã tồn tại
        if (error.message.includes("Email này đã được đăng ký")) {
          errorTitle = "Email đã tồn tại";
        } else if (error.message.includes("Email không hợp lệ")) {
          errorTitle = "Email không hợp lệ";
        } else if (error.message.includes("Mật khẩu quá yếu")) {
          errorTitle = "Mật khẩu không đủ mạnh";
        }
      }
      
      toast({
        variant: "destructive",
        title: errorTitle,
        description: errorMessage,
      });
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Hàm đăng xuất
  const logout = async () => {
    setLoading(true);
    try {
      await authApi.logout();
      
      // Xóa token và thông tin người dùng
      removeLocalStorage("auth_token");
      removeLocalStorage("user_info");
      
      setUser(null);
      
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đăng xuất thành công",
      });
      
      // Chuyển hướng về trang đăng nhập
      router.push("/auth/login");
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Đăng xuất thất bại",
        description: error.message || "Có lỗi xảy ra khi đăng xuất",
      });
    } finally {
      setLoading(false);
    }
  };

  // Hàm kiểm tra trạng thái xác thực
  const checkAuth = async (): Promise<boolean> => {
    try {
      const token = getLocalStorage("auth_token");
      if (!token) {
        return false;
      }
      
      const response = await authApi.checkSession();
      return response.is_authenticated === true;
    } catch (error) {
      return false;
    }
  };

  // Hàm đăng nhập với Google
  const loginWithGoogle = async (code: string) => {
    setLoading(true);
    try {
      const payload = { code, provider: 'google' };
      const data = await fetchApi('/auth/google', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      // Không cần gọi response.json(), fetchApi đã trả về data
      if (!data.access_token) {
        throw new Error(data.message || "Lỗi xác thực với Google");
      }
      // Nếu có access_token, coi như đăng nhập thành công
      if (data.access_token) {
        setLocalStorage("auth_token", data.access_token);
        if (data.user) {
          setLocalStorage("user_info", JSON.stringify(data.user));
          setUser(data.user);
        }
        
        // Tạo hội thoại mới sau khi đăng nhập Google thành công
        try {
          const conversationResponse = await conversationsApi.createConversation();
          if (conversationResponse && conversationResponse.conversation_id) {
            setLocalStorage("current_conversation_id", conversationResponse.conversation_id);
            console.log("Đã tạo hội thoại mới cho Google login:", conversationResponse.conversation_id);
          }
        } catch (error) {
          console.log("Không thể tạo hội thoại mới sau khi đăng nhập Google, sẽ tạo khi cần thiết");
        }
        
        toast({
          title: "Đăng nhập thành công",
          description: "Chào mừng bạn quay trở lại!",
        });
        return data;
      } else {
        throw new Error("Không nhận được token xác thực");
      }
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Đăng nhập thất bại",
        description: error.message || "Không thể đăng nhập với Google. Vui lòng thử lại sau.",
      });
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Hàm quên mật khẩu
  const forgotPassword = async (email: string, redirectUrl?: string) => {
    setLoading(true);
    try {
      const response = await authApi.forgotPassword(email, redirectUrl);
      
      toast({
        variant: "success",
        title: "Thành công",
        description: "Vui lòng kiểm tra email của bạn để đặt lại mật khẩu.",
      });
      
      return response;
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: error.message || "Không thể gửi yêu cầu đặt lại mật khẩu. Vui lòng thử lại sau.",
      });
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // Hàm đặt lại mật khẩu
  const resetPassword = async (access_token: string, password: string) => {
    setLoading(true);
    try {
      const response = await authApi.resetPassword(access_token, password);
      
      toast({
        variant: "success",
        title: "Thành công",
        description: "Mật khẩu của bạn đã được đặt lại thành công.",
      });
      
      return response;
    } catch (error: any) {
      let errorMessage = "Không thể đặt lại mật khẩu. Vui lòng thử lại sau.";
      let variant: "destructive" | "warning" = "destructive";
      let title = "Lỗi";
      
      if (error instanceof Error && error.message) {
        errorMessage = error.message;
        
        // Xử lý trường hợp mật khẩu mới giống mật khẩu cũ
        if (errorMessage.includes("Mật khẩu mới phải khác mật khẩu cũ")) {
          variant = "warning";
          title = "Cảnh báo";
        }
      }
      
      toast({
        variant,
        title,
        description: errorMessage,
      });
      
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const value = {
        user,
        loading,
        login,
        signup,
        logout,
        checkAuth,
        loginWithGoogle,
    forgotPassword,
    resetPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Hook để sử dụng AuthContext
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
} 