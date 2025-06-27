import { AdminUser, AdminUserListResponse, CreateUserData, UpdateUserData, BanUserData } from "./admin-types";
import { fetchApi } from "@/lib/api";

// Interfaces cho Conversation Management
export interface AdminConversation {
  conversation_id: string;
  user_id: string;
  user_email: string;
  created_at: string;
  last_updated: string;
  message_count: number;
  first_message: string;
}

export interface AdminConversationListResponse {
  conversations: AdminConversation[];
  total_count: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface AdminMessage {
  message_id: string;
  role: string;
  content: string;
  created_at: string;
  sequence: number;
}

export interface AdminMessageListResponse {
  conversation_id: string;
  messages: AdminMessage[];
  total_messages: number;
  user_info: {
    id: string;
    email: string;
    created_at: string;
  };
}

export interface AdminMessageSearchParams {
  query: string;
  conversation_id?: string;
  user_email?: string;  // Đổi từ user_id thành user_email
  date_from?: string;
  date_to?: string;
  page?: number;
  per_page?: number;
}

export interface AdminMessageSearchResponse {
  messages: Array<{
    message_id: string;
    conversation_id: string;
    user_id: string | null;
    user_email: string;
    role: string;
    content: string;
    created_at: string;
  }>;
  total_count: number;
  page: number;
  per_page: number;
  search_query: string;
}

export interface AdminConversationStats {
  total_conversations: number;
  total_messages: number;
  total_users: number;
  conversations_by_date: Array<{
    date: string;
    count: number;
  }>;
  messages_by_role: {
    user: number;
    assistant: number;
  };
  top_users: Array<{
    user_id: string;
    email: string;
    conversation_count: number;
  }>;
}



// API Functions
export class AdminAPI {
  // User Management APIs
  async fetchUsers(page = 1, perPage = 10): Promise<AdminUserListResponse> {
    return fetchApi(`/admin/users?page=${page}&per_page=${perPage}`);
  }

  async createUser(userData: CreateUserData): Promise<AdminUser> {
    return fetchApi("/admin/users", {
      method: "POST",
      body: JSON.stringify(userData)
    });
  }

  async updateUser(userId: string, userData: UpdateUserData): Promise<AdminUser> {
    return fetchApi(`/admin/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(userData)
    });
  }

  async banUser(userId: string, banData: BanUserData): Promise<void> {
    return fetchApi(`/admin/users/${userId}/ban`, {
      method: "POST",
      body: JSON.stringify(banData)
    });
  }

  async unbanUser(userId: string): Promise<void> {
    return fetchApi(`/admin/users/${userId}/unban`, {
      method: "POST"
    });
  }

  async deleteUser(userId: string, hard = true): Promise<void> {
    return fetchApi(`/admin/users/${userId}?hard=${hard}`, {
      method: "DELETE"
    });
  }

  // Conversation Management APIs
  async fetchConversations(params?: {
    page?: number;
    per_page?: number;
    user_email?: string;  // Đổi từ user_id thành user_email
    date_from?: string;
    date_to?: string;
  }): Promise<AdminConversationListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.page) queryParams.append("page", params.page.toString());
    if (params?.per_page) queryParams.append("per_page", params.per_page.toString());
    if (params?.user_email) queryParams.append("user_email", params.user_email);  // Đổi parameter
    if (params?.date_from) queryParams.append("date_from", params.date_from);
    if (params?.date_to) queryParams.append("date_to", params.date_to);

    return fetchApi(`/admin/conversations?${queryParams.toString()}`);
  }

  async getConversationMessages(conversationId: string): Promise<AdminMessageListResponse> {
    return fetchApi(`/admin/conversations/${conversationId}/messages`);
  }

  async searchMessages(params: AdminMessageSearchParams): Promise<AdminMessageSearchResponse> {
    return fetchApi("/admin/messages/search", {
      method: "POST",
      body: JSON.stringify(params)
    });
  }

  async deleteConversation(conversationId: string): Promise<{ status: string; message: string }> {
    return fetchApi(`/admin/conversations/${conversationId}`, {
      method: "DELETE"
    });
  }

  async getConversationStats(days = 7): Promise<AdminConversationStats> {
    try {
      return await fetchApi(`/admin/conversations/stats?days=${days}`);
    } catch (error) {
      console.error("Error fetching conversation stats:", error);
      // Trả về dữ liệu giả để tránh lỗi khi render
      return {
        total_conversations: 0,
        total_messages: 0,
        total_users: 0,
        conversations_by_date: [],
        messages_by_role: { user: 0, assistant: 0 },
        top_users: []
      };
    }
  }

  async getFilesStats(): Promise<{
    total_files: number;
    total_size: number;
    file_types: Record<string, number>;
    file_categories: Record<string, number>;
    last_7_days: number;
    last_30_days: number;
  }> {
    try {
      return await fetchApi(`/admin/files/stats`);
    } catch (error) {
      console.error("Error fetching files stats:", error);
      // Trả về dữ liệu giả để tránh lỗi khi render
      return {
        total_files: 0,
        total_size: 0,
        file_types: {},
        file_categories: {},
        last_7_days: 0,
        last_30_days: 0
      };
    }
  }

  // File Management APIs
  async getFiles(): Promise<{ total_files: number; files: Array<{
    filename: string;
    path: string;
    size: number;
    upload_date: string | null;
    extension: string;
    category: string | null;
    id: string | null;
  }> }> {
    try {
      return await fetchApi("/files");
    } catch (error) {
      console.error("Error fetching files:", error);
      // Trả về dữ liệu giả để tránh lỗi khi render
      return {
        total_files: 0,
        files: []
      };
    }
  }
}

export const adminAPI = new AdminAPI(); 