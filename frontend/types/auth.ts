// Auth related types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface ForgotPasswordRequest {
  email: string;
  redirect_url?: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  user: {
    id: string;
    email: string;
    name?: string;
    avatar_url?: string;
  };
}

export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ForgotPasswordResponse {
  status: "success";
  message: string;
}

export interface ApiErrorResponse {
  error: string;
  message: string;
  details?: any;
}
