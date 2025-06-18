import { AdminUser, AdminUserListResponse, CreateUserData, UpdateUserData, BanUserData } from "./admin-types";
import { fetchApi } from "@/lib/api";

// API Functions
export class AdminAPI {
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
}

export const adminAPI = new AdminAPI(); 