"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import { MessageSquare, Trash2, Loader2 } from "lucide-react"
import { useState, useEffect, useMemo, useCallback } from "react"
import { format, isToday, isYesterday, formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useConversations } from "@/hooks/useConversations"

interface Conversation {
  conversation_id: string
  user_id: string
  created_at: string
  last_updated: string
  first_message: string
  message_count: number
}

interface ConversationListProps {
  onSelectConversation?: (conversationId: string) => void
  currentConversationId?: string | null
  refreshKey?: number
}

export function ConversationList({ onSelectConversation, currentConversationId, refreshKey = 0 }: ConversationListProps) {
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null)
  
  // Sử dụng custom hook để quản lý conversations
  const {
    conversations,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    deleteConversation
  } = useConversations({
    pageSize: 10,
    cacheDuration: 30000, // 30 giây
    debounceDelay: 300
  })

  // Refresh khi refreshKey thay đổi
  useEffect(() => {
    if (refreshKey > 0) {
      refresh()
      
      // Auto-select conversation mới nhất nếu cần
      if (conversations.length > 0 && !currentConversationId) {
        const sortedConversations = [...conversations].sort(
          (a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime()
        )
        
        if (sortedConversations.length > 0) {
          onSelectConversation?.(sortedConversations[0].conversation_id)
        }
      }
    }
  }, [refreshKey, refresh, conversations, currentConversationId, onSelectConversation])

  // Event handlers
  const handleDeleteClick = useCallback((id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setConversationToDelete(id)
  }, [])

  const handleConfirmDelete = useCallback(async () => {
    if (conversationToDelete) {
      try {
        await deleteConversation(conversationToDelete)
      } catch (error) {
        // Error is already handled in the hook
      } finally {
        setConversationToDelete(null)
      }
    }
  }, [conversationToDelete, deleteConversation])

  const handleCancelDelete = useCallback(() => {
    setConversationToDelete(null)
  }, [])

  // Memoized formatting functions
  const formatDate = useMemo(() => (dateString: string): string => {
    try {
      const date = new Date(dateString)
      
      if (isToday(date)) {
        return `Hôm nay, ${format(date, 'HH:mm', { locale: vi })}`
      } else if (isYesterday(date)) {
        return `Hôm qua, ${format(date, 'HH:mm', { locale: vi })}`
      } else if (date > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)) {
        return formatDistanceToNow(date, { addSuffix: true, locale: vi })
      } else {
        return format(date, 'dd/MM/yyyy', { locale: vi })
      }
    } catch (e) {
      return dateString
    }
  }, [])

  const truncateMessage = useMemo(() => (message: string): string => {
    if (!message) return "Hội thoại mới"
    return message.length > 40 ? message.substring(0, 40) + "..." : message
  }, [])

  // Memoized conversation items để tránh re-render không cần thiết
  const conversationItems = useMemo(() => {
    return conversations.map((conversation) => (
      <div
        key={conversation.conversation_id}
        className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
          currentConversationId === conversation.conversation_id
            ? "bg-accent text-accent-foreground"
            : "hover:bg-accent/50"
        }`}
        onClick={() => onSelectConversation?.(conversation.conversation_id)}
      >
        <div className="bg-primary/10 p-2 rounded-md flex-shrink-0">
          <MessageSquare className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm mb-1">
            {truncateMessage(conversation.first_message)}
          </div>
          <div className="text-xs text-muted-foreground mb-1">
            {formatDate(conversation.last_updated)}
          </div>
          <div className="text-xs text-muted-foreground">
            {conversation.message_count} tin nhắn
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-destructive flex-shrink-0"
          onClick={(e) => handleDeleteClick(conversation.conversation_id, e)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    ))
  }, [conversations, currentConversationId, onSelectConversation, truncateMessage, formatDate, handleDeleteClick])

  return (
    <div className="flex flex-col gap-2 p-4">
      {loading && conversations.length === 0 ? (
        <div className="flex justify-center items-center p-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : error && conversations.length === 0 ? (
        <div className="text-center p-4 text-muted-foreground">
          <p>{error}</p>
          <Button 
            variant="outline" 
            className="mt-2"
            onClick={refresh}
          >
            Thử lại
          </Button>
        </div>
      ) : conversations.length === 0 ? (
        <div className="text-center p-4 text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-2 opacity-50" />
          <p>Chưa có hội thoại nào</p>
        </div>
      ) : (
        <>
          {conversationItems}
          
          {hasMore && (
            <div className="flex justify-center p-4">
              <Button
                variant="outline"
                onClick={loadMore}
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang tải...
                  </>
                ) : (
                  "Tải thêm"
                )}
              </Button>
            </div>
          )}
        </>
      )}

      <AlertDialog open={!!conversationToDelete} onOpenChange={handleCancelDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa hội thoại</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn xóa hội thoại này? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelDelete}>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete}>Xóa</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
