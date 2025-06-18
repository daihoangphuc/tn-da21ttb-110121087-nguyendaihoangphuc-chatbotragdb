import { useState, useEffect, useCallback, useRef } from 'react'
import { conversationsApi } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

interface Conversation {
  conversation_id: string
  user_id: string
  created_at: string
  last_updated: string
  first_message: string
  message_count: number
}

interface ConversationCache {
  data: Conversation[]
  timestamp: number
  totalPages: number
  totalItems: number
}

interface UseConversationsOptions {
  pageSize?: number
  cacheDuration?: number
  debounceDelay?: number
}

interface UseConversationsReturn {
  conversations: Conversation[]
  loading: boolean
  error: string | null
  hasMore: boolean
  page: number
  loadMore: () => void
  refresh: () => void
  deleteConversation: (id: string) => Promise<void>
}

// Global cache
const conversationCache = new Map<string, ConversationCache>()

export function useConversations(options: UseConversationsOptions = {}): UseConversationsReturn {
  const {
    pageSize = 10,
    cacheDuration = 30000, // 30 seconds
    debounceDelay = 300
  } = options

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  
  const { toast } = useToast()
  const loadingRef = useRef(false)
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Helper functions
  const getCacheKey = useCallback((pageNum: number): string => {
    return `conversations_page_${pageNum}_size_${pageSize}`
  }, [pageSize])

  const isCacheValid = useCallback((cacheKey: string): boolean => {
    const cached = conversationCache.get(cacheKey)
    if (!cached) return false
    return Date.now() - cached.timestamp < cacheDuration
  }, [cacheDuration])

  // Main fetch function
  const fetchConversations = useCallback(async (pageNum: number, isRefresh = false): Promise<void> => {
    if (loadingRef.current && !isRefresh) return
    
    try {
      loadingRef.current = true
      setLoading(true)
      setError(null)

      const cacheKey = getCacheKey(pageNum)
      
      // Check cache if not refreshing
      if (!isRefresh && isCacheValid(cacheKey)) {
        const cached = conversationCache.get(cacheKey)!
        if (pageNum === 1) {
          setConversations(cached.data)
        } else {
          setConversations(prev => [...prev, ...cached.data])
        }
        setHasMore(pageNum < cached.totalPages)
        setLoading(false)
        loadingRef.current = false
        return
      }

      const response = await conversationsApi.getConversations(pageNum, pageSize)
      
      if (response && response.status === 'success') {
        const conversationData = response.data || []
        
        // Save to cache
        conversationCache.set(cacheKey, {
          data: conversationData,
          timestamp: Date.now(),
          totalPages: response.pagination?.total_pages || 0,
          totalItems: response.pagination?.total_items || 0
        })
        
        if (pageNum === 1) {
          setConversations(conversationData)
        } else {
          setConversations(prev => [...prev, ...conversationData])
        }
        
        const pagination = response.pagination
        if (pagination) {
          setHasMore(pagination.page < pagination.total_pages)
        } else {
          setHasMore(false)
        }
      } else {
        setError('Không thể tải danh sách hội thoại')
        if (!isRefresh) {
          toast({
            variant: "destructive",
            title: "Lỗi",
            description: "Không thể tải danh sách hội thoại. Vui lòng thử lại sau."
          })
        }
      }
    } catch (error) {
      console.error('Lỗi khi tải danh sách hội thoại:', error)
      setError('Đã xảy ra lỗi khi tải danh sách hội thoại')
      if (!isRefresh) {
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Đã xảy ra lỗi khi tải danh sách hội thoại. Vui lòng thử lại sau."
        })
      }
    } finally {
      setLoading(false)
      loadingRef.current = false
    }
  }, [pageSize, getCacheKey, isCacheValid, toast])

  // Debounced fetch
  const debouncedFetch = useCallback((pageNum: number, isRefresh = false): void => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchConversations(pageNum, isRefresh)
    }, debounceDelay)
  }, [fetchConversations, debounceDelay])

  // TỐI ỦU HÓA: Load initial data với flag để tránh duplicate calls
  useEffect(() => {
    if (!loadingRef.current) {
      debouncedFetch(1)
    }
    
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, []) // Bỏ debouncedFetch khỏi dependency để chỉ chạy 1 lần

  // Public methods
  const loadMore = useCallback(() => {
    if (!loading && hasMore && !loadingRef.current) {
      const nextPage = page + 1
      setPage(nextPage)
      debouncedFetch(nextPage)
    }
  }, [loading, hasMore, page, debouncedFetch])

  const refresh = useCallback(() => {
    setPage(1)
    conversationCache.clear()
    debouncedFetch(1, true)
  }, [debouncedFetch])

  const deleteConversation = useCallback(async (id: string): Promise<void> => {
    try {
      const response = await conversationsApi.deleteConversation(id)
      
      if (response && response.status === 'success') {
        // Update local state
        setConversations(prev => prev.filter((conv) => conv.conversation_id !== id))
        
        // Clear cache to force refresh
        conversationCache.clear()
        
        toast({
          title: "Xóa thành công",
          description: "Hội thoại đã được xóa."
        })
      } else {
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể xóa hội thoại. Vui lòng thử lại sau."
        })
      }
    } catch (error) {
      console.error('Lỗi khi xóa hội thoại:', error)
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Đã xảy ra lỗi khi xóa hội thoại. Vui lòng thử lại sau."
      })
      throw error
    }
  }, [toast])

  return {
    conversations,
    loading,
    error,
    hasMore,
    page,
    loadMore,
    refresh,
    deleteConversation
  }
} 