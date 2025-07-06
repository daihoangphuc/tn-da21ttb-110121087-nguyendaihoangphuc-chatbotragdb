import { AdminConversation } from "@/components/admin-api";

interface ConversationCache {
  data: AdminConversation[];
  timestamp: number;
  isLoading: boolean;
}

class AdminConversationsCache {
  private cache: ConversationCache | null = null;
  private readonly CACHE_DURATION = 5 * 60 * 1000; // 5 phút
  private fetchPromise: Promise<AdminConversation[]> | null = null;

  // Kiểm tra cache có hợp lệ không
  private isCacheValid(): boolean {
    if (!this.cache) return false;
    return Date.now() - this.cache.timestamp < this.CACHE_DURATION;
  }

  // Lấy dữ liệu từ cache hoặc fetch mới
  async getConversations(fetchFunction: () => Promise<AdminConversation[]>): Promise<AdminConversation[]> {
    // Nếu cache hợp lệ, trả về ngay
    if (this.isCacheValid() && this.cache) {
      return this.cache.data;
    }

    // Nếu đang fetch, chờ kết quả
    if (this.fetchPromise) {
      return this.fetchPromise;
    }

    // Fetch dữ liệu mới
    this.fetchPromise = this.fetchData(fetchFunction);
    return this.fetchPromise;
  }

  private async fetchData(fetchFunction: () => Promise<AdminConversation[]>): Promise<AdminConversation[]> {
    try {
      const data = await fetchFunction();
      
      // Validate và deduplicate dữ liệu
      const validData = data.filter(conv => conv.conversation_id && conv.conversation_id.trim() !== '');
      const uniqueData = validData.filter((conv, index, arr) => 
        arr.findIndex(c => c.conversation_id === conv.conversation_id) === index
      );
      
      if (validData.length !== uniqueData.length) {
        console.warn('Removed duplicate conversations:', validData.length - uniqueData.length);
      }
      
      // Lưu vào cache
      this.cache = {
        data: uniqueData,
        timestamp: Date.now(),
        isLoading: false
      };

      return uniqueData;
    } catch (error) {
      throw error;
    } finally {
      this.fetchPromise = null;
    }
  }

  // Xóa cache (khi có thay đổi dữ liệu)
  invalidateCache(): void {
    this.cache = null;
    this.fetchPromise = null;
  }

  // Cập nhật cache sau khi xóa conversation
  removeConversation(conversationId: string): void {
    if (this.cache) {
      this.cache.data = this.cache.data.filter(conv => conv.conversation_id !== conversationId);
    }
  }

  // Lấy dữ liệu từ cache nếu có (không fetch)
  getCachedData(): AdminConversation[] | null {
    if (this.isCacheValid() && this.cache) {
      return this.cache.data;
    }
    return null;
  }

  // Kiểm tra trạng thái cache
  getCacheStatus(): { hasCache: boolean; isValid: boolean; age: number } {
    return {
      hasCache: !!this.cache,
      isValid: this.isCacheValid(),
      age: this.cache ? Date.now() - this.cache.timestamp : 0
    };
  }
}

// Singleton instance
export const adminConversationsCache = new AdminConversationsCache(); 