// Types for Admin API
export interface AdminUser {
  id: string;
  email: string;
  created_at: string;
  email_confirmed_at?: string;
  last_sign_in_at?: string;
  role?: string;
  metadata?: any;
  banned_until?: string;
}

export interface AdminUserListResponse {
  users: AdminUser[];
  total_count: number;
  page: number;
  per_page: number;
}

export interface CreateUserData {
  email: string;
  password: string;
  role: string;
  metadata?: any;
}

export interface UpdateUserData {
  email?: string;
  password?: string;
  role?: string;
  metadata?: any;
}

export interface BanUserData {
  duration: string;
  reason?: string;
} 