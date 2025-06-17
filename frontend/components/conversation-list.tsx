"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import { MessageSquare, Trash2, Loader2 } from "lucide-react"
import { useState, useEffect } from "react"
import { useToast } from "@/components/ui/use-toast"
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
import { conversationsApi } from "@/lib/api"

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
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const { toast } = useToast()
  const pageSize = 5 // Giảm số lượng hội thoại tải về mỗi lần xuống 5

  // Tải danh sách hội thoại từ API
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await conversationsApi.getConversations(page, pageSize)
        
        if (response && response.status === 'success') {
          const conversationData = response.data || [];
          
          if (page === 1) {
            setConversations(conversationData)
            
            // Nếu refreshKey thay đổi và có hội thoại mới (hội thoại đầu tiên trong danh sách)
            // và không có hội thoại nào được chọn, tự động chọn hội thoại mới nhất
            if (refreshKey > 0 && conversationData.length > 0 && !currentConversationId) {
              // Sắp xếp theo thời gian cập nhật mới nhất
              const sortedConversations = [...conversationData].sort(
                (a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime()
              );
              
              // Chọn hội thoại mới nhất
              if (sortedConversations.length > 0) {
                onSelectConversation && onSelectConversation(sortedConversations[0].conversation_id);
              }
            }
          } else {
            setConversations(prev => [...prev, ...conversationData])
          }
          
          // Kiểm tra xem có trang tiếp theo không
          const pagination = response.pagination
          if (pagination) {
            setHasMore(pagination.page < pagination.total_pages)
          } else {
            setHasMore(false)
          }
        } else {
          setError('Không thể tải danh sách hội thoại')
          toast({
            variant: "destructive",
            title: "Lỗi",
            description: "Không thể tải danh sách hội thoại. Vui lòng thử lại sau."
          })
        }
      } catch (error) {
        console.error('Lỗi khi tải danh sách hội thoại:', error)
        setError('Đã xảy ra lỗi khi tải danh sách hội thoại')
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Đã xảy ra lỗi khi tải danh sách hội thoại. Vui lòng thử lại sau."
        })
      } finally {
        setLoading(false)
      }
    }

    // Reset về trang đầu tiên khi refreshKey thay đổi
    if (refreshKey > 0) {
      setPage(1)
    }

    fetchConversations()
  }, [page, toast, refreshKey, onSelectConversation, currentConversationId, pageSize])

  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }

  const handleDeleteClick = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setConversationToDelete(id)
  }

  const handleConfirmDelete = async () => {
    if (conversationToDelete) {
      try {
        const response = await conversationsApi.deleteConversation(conversationToDelete)
        
        if (response && response.status === 'success') {
          setConversations(conversations.filter((conv) => conv.conversation_id !== conversationToDelete))
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
      } finally {
      setConversationToDelete(null)
      }
    }
  }

  const handleCancelDelete = () => {
    setConversationToDelete(null)
  }

  // Hàm định dạng thời gian
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      
      if (isToday(date)) {
        return `Hôm nay, ${format(date, 'HH:mm', { locale: vi })}`
      } else if (isYesterday(date)) {
        return `Hôm qua, ${format(date, 'HH:mm', { locale: vi })}`
      } else if (date > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)) {
        // Trong vòng 1 tuần
        return formatDistanceToNow(date, { addSuffix: true, locale: vi })
      } else {
        return format(date, 'dd/MM/yyyy', { locale: vi })
      }
    } catch (e) {
      return dateString
    }
  }

  // Hàm rút gọn tin nhắn đầu tiên
  const truncateMessage = (message: string) => {
    if (!message) return "Hội thoại mới"
    return message.length > 40 ? message.substring(0, 40) + "..." : message
  }

  return (
    <div className="flex flex-col gap-2 p-4">
      {loading && page === 1 ? (
        <div className="flex justify-center items-center p-8">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </div>
      ) : error && conversations.length === 0 ? (
        <div className="text-center p-4 text-muted-foreground">
          <p>{error}</p>
          <Button 
            variant="outline" 
            className="mt-2"
            onClick={() => setPage(1)}
          >
            Thử lại
          </Button>
        </div>
      ) : conversations.length === 0 ? (
        <div className="text-center p-4 text-muted-foreground">
          <p>Chưa có hội thoại nào.</p>
          <p className="mt-2">Bắt đầu cuộc trò chuyện mới để tạo hội thoại.</p>
        </div>
      ) : (
        <>
      {conversations.map((conversation) => (
        <div
              key={conversation.conversation_id}
          className={`group flex items-center justify-between rounded-md border p-3 text-sm transition-colors hover:bg-muted cursor-pointer ${
                currentConversationId === conversation.conversation_id ? "bg-muted border-primary/50" : ""
          }`}
              onClick={() => onSelectConversation && onSelectConversation(conversation.conversation_id)}
        >
          <div className="flex items-start gap-3">
            <MessageSquare
              className={`mt-px h-4 w-4 ${
                    currentConversationId === conversation.conversation_id ? "text-primary" : "text-muted-foreground"
              }`}
            />
            <div className="grid gap-1">
                  <div className="font-medium">{truncateMessage(conversation.first_message)}</div>
                  <div className="text-xs text-muted-foreground">
                    {formatDate(conversation.last_updated)} • {conversation.message_count} tin nhắn
                  </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-100"
            aria-label="Xóa hội thoại"
                onClick={(e) => handleDeleteClick(conversation.conversation_id, e)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}

          {hasMore && (
            <div className="flex justify-center mt-4">
              <Button 
                variant="outline" 
                className="px-4 py-2 flex items-center gap-2"
                onClick={loadMore}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Đang tải...
                  </>
                ) : (
                  <>
                    <span>Tải thêm hội thoại</span>
                  </>
                )}
              </Button>
            </div>
          )}
        </>
      )}

      {/* Modal xác nhận xóa */}
      <AlertDialog open={!!conversationToDelete} onOpenChange={(open) => !open && setConversationToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn xóa hội thoại này? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelDelete}>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmDelete} className="bg-destructive text-destructive-foreground">
              Xóa
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
