"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import { MessageSquare, Trash2, Loader2, Clock } from "lucide-react"
import { useState, useEffect, useMemo, useCallback } from "react"
import { format, isToday, isYesterday, formatDistanceToNow } from "date-fns"
import { vi } from "date-fns/locale"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"
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
import { cn } from "@/lib/utils"

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

  // Refresh khi refreshKey thay đổi (chỉ khi thành công)
  useEffect(() => {
    if (refreshKey > 0 && !loading && !error) {
      console.log('Refreshing conversations due to refreshKey change:', refreshKey)
      refresh()
      
      // Auto-select conversation mới nhất nếu cần
      setTimeout(() => {
      if (conversations.length > 0 && !currentConversationId) {
        const sortedConversations = [...conversations].sort(
                (a, b) => new Date(b.last_updated).getTime() - new Date(a.last_updated).getTime()
        )
        
              if (sortedConversations.length > 0) {
          onSelectConversation?.(sortedConversations[0].conversation_id)
              }
            }
      }, 100)
    }
  }, [refreshKey]) // Chỉ theo dõi refreshKey, không theo dõi conversations để tránh loop

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

  const truncateMessage = useMemo(() => (message: string, maxLength: number = 15): string => {
    if (!message) return "Hội thoại mới"
    // Trim whitespace và check độ dài
    const trimmed = message.trim()
    if (trimmed.length <= maxLength) return trimmed
    
    // Tìm vị trí space gần nhất để cắt word boundary
    let cutIndex = maxLength
    const lastSpaceIndex = trimmed.lastIndexOf(' ', maxLength)
    
    // Nếu có space trong phạm vi hợp lý, cắt tại đó
    if (lastSpaceIndex > maxLength * 0.7) {
      cutIndex = lastSpaceIndex
    }
    
    return trimmed.substring(0, cutIndex).trim() + "..."
  }, [])

  // Memoized conversation items để tránh re-render không cần thiết
  const conversationItems = useMemo(() => {
    return conversations.map((conversation) => {
      const isActive = currentConversationId === conversation.conversation_id
      const fullMessage = conversation.first_message || "Hội thoại mới"
      const truncatedMessage = truncateMessage(fullMessage)
      const needsTooltip = fullMessage.length > 25
      
      return (
        <TooltipProvider key={conversation.conversation_id}>
          <div
            className={cn(
              "group relative flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 border border-transparent",
              "hover:bg-accent/80 hover:border-accent-foreground/10 hover:shadow-sm",
              isActive && "bg-primary/5 border-primary/20 shadow-sm"
            )}
        onClick={() => onSelectConversation?.(conversation.conversation_id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelectConversation?.(conversation.conversation_id)
              }
            }}
            aria-label={`Chọn hội thoại: ${fullMessage}`}
          >
            {/* Icon */}
            <div className={cn(
              "flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0 transition-colors",
              isActive 
                ? "bg-primary/15 text-primary" 
                : "bg-muted/60 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
            )}>
              <MessageSquare className="h-4 w-4" />
        </div>

            {/* Content */}
            <div className="flex-1 min-w-0 space-y-1">
              {/* Title Row (removed Message Count Badge) */}
              <div className="flex items-center gap-2">
        <div className="flex-1 min-w-0 overflow-hidden">
                  {needsTooltip ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className={cn(
                          "font-medium text-sm leading-tight truncate",
                          isActive ? "text-primary" : "text-foreground"
                        )}
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          width: '100%'
                        }}
                        >
                          {truncatedMessage}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent 
                        side="top" 
                        className="max-w-xs z-[100] bg-popover border shadow-lg"
                        sideOffset={8}
                      >
                        <p className="text-sm break-words">{fullMessage}</p>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <div className={cn(
                      "font-medium text-sm leading-tight truncate",
                      isActive ? "text-primary" : "text-foreground"
                    )}
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      width: '100%'
                    }}
                    >
                      {truncatedMessage}
                    </div>
                  )}
                </div>
          </div>

              {/* Date */}
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
            {formatDate(conversation.last_updated)}
          </div>
          </div>

            {/* Delete Button */}
            <Tooltip>
              <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
                  className={cn(
                    "h-8 w-8 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-all duration-200",
                    "text-muted-foreground hover:text-destructive hover:bg-destructive/10",
                    isActive && "opacity-60"
                  )}
          onClick={(e) => handleDeleteClick(conversation.conversation_id, e)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
              </TooltipTrigger>
              <TooltipContent 
                side="left" 
                className="z-[100] bg-popover border shadow-lg"
                sideOffset={8}
              >
                <p className="text-sm">Xóa hội thoại</p>
              </TooltipContent>
            </Tooltip>
      </div>
        </TooltipProvider>
      )
    })
  }, [conversations, currentConversationId, onSelectConversation, truncateMessage, formatDate, handleDeleteClick])

  return (
    <div className="flex flex-col gap-1 p-3">
      {loading && conversations.length === 0 ? (
        <div className="flex justify-center items-center p-12">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Đang tải hội thoại...</p>
          </div>
        </div>
      ) : error && conversations.length === 0 ? (
        <div className="text-center p-8 space-y-4">
          <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mx-auto">
            <MessageSquare className="h-6 w-6 text-destructive" />
          </div>
          <div className="space-y-2">
            <p className="font-medium text-sm">Không thể tải hội thoại</p>
            <p className="text-xs text-muted-foreground">{error}</p>
          </div>
          <Button 
            variant="outline" 
            size="sm"
            onClick={refresh}
            className="mt-3"
          >
            Thử lại
          </Button>
        </div>
      ) : conversations.length === 0 ? (
        <div className="text-center p-12 space-y-4">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
            <MessageSquare className="h-8 w-8 text-primary/50" />
          </div>
          <div className="space-y-2">
            <p className="font-medium">Chưa có hội thoại nào</p>
            <p className="text-sm text-muted-foreground">
              Nhấp vào "Hội thoại mới" để bắt đầu
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="space-y-1">
          {conversationItems}
          </div>

          {hasMore && (
            <div className="flex justify-center p-4 mt-2">
              <Button 
                variant="outline" 
                onClick={loadMore}
                disabled={loading}
                className="w-full h-9 text-sm"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Đang tải...
                  </>
                ) : (
                  <>
                    <MessageSquare className="mr-2 h-4 w-4" />
                    Tải thêm hội thoại
                  </>
                )}
              </Button>
            </div>
          )}
        </>
      )}

      <AlertDialog open={!!conversationToDelete} onOpenChange={handleCancelDelete}>
        <AlertDialogContent className="z-[110]">
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
