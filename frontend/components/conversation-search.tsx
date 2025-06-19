"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"
import { 
  Search, 
  Calendar, 
  MessageSquare, 
  X, 
  Filter,
  Clock,
  FileText,
  Loader2
} from "lucide-react"
import { useState, useEffect, useCallback, useMemo } from "react"
import { format, isToday, isYesterday } from "date-fns"
import { vi } from "date-fns/locale"
import { cn } from "@/lib/utils"
import { conversationsApi } from "@/lib/api"
import { useToast } from "@/components/ui/use-toast"

interface SearchResult {
  conversation_id: string
  user_id: string
  last_updated: string
  first_message: string
  message_count: number
  matching_content?: string | null
}

interface ConversationSearchProps {
  onSelectConversation?: (conversationId: string) => void
  currentConversationId?: string | null
  className?: string
}

export function ConversationSearch({ 
  onSelectConversation, 
  currentConversationId, 
  className 
}: ConversationSearchProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchMetadata, setSearchMetadata] = useState<any>(null)

  const { toast } = useToast()

  // Format date function
  const formatDate = useCallback((dateString: string) => {
    try {
      const date = new Date(dateString)
      if (isToday(date)) {
        return `Hôm nay, ${format(date, 'HH:mm', { locale: vi })}`
      } else if (isYesterday(date)) {
        return `Hôm qua, ${format(date, 'HH:mm', { locale: vi })}`
      } else {
        return format(date, 'dd/MM/yyyy, HH:mm', { locale: vi })
      }
    } catch {
      return dateString
    }
  }, [])

  // Truncate message function
  const truncateMessage = useCallback((message: string, maxLength: number = 50) => {
    if (message.length <= maxLength) return message
    return message.substring(0, maxLength) + "..."
  }, [])

  // Search function
  const performSearch = useCallback(async (page: number = 1) => {
    // Kiểm tra nếu không có điều kiện tìm kiếm nào
    if (!searchQuery.trim() && !dateFrom && !dateTo) {
      toast({
        title: "Thiếu điều kiện tìm kiếm",
        description: "Vui lòng nhập từ khóa hoặc chọn khoảng thời gian để tìm kiếm.",
        variant: "destructive"
      })
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await conversationsApi.searchConversations({
        query: searchQuery.trim() || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        page,
        pageSize: 10
      })

      if (response.conversations) {
        setResults(response.conversations)
        setTotalCount(response.total_count)
        setCurrentPage(response.page)
        setTotalPages(response.total_pages)
        setSearchMetadata(response.search_metadata)
        setHasSearched(true)

        if (response.conversations.length === 0) {
          toast({
            title: "Không tìm thấy kết quả",
            description: "Không có hội thoại nào phù hợp với điều kiện tìm kiếm.",
          })
        } else {
          toast({
            title: "Tìm kiếm thành công",
            description: `Tìm thấy ${response.total_count} hội thoại phù hợp.`,
          })
        }
      } else {
        setError("Không thể lấy kết quả tìm kiếm")
      }
    } catch (err: any) {
      const errorMessage = err.message || "Lỗi khi tìm kiếm hội thoại"
      setError(errorMessage)
      toast({
        title: "Lỗi tìm kiếm",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }, [searchQuery, dateFrom, dateTo, toast])

  // Handle search button click
  const handleSearch = useCallback(() => {
    setCurrentPage(1)
    performSearch(1)
  }, [performSearch])

  // Handle clear search
  const handleClear = useCallback(() => {
    setSearchQuery("")
    setDateFrom("")
    setDateTo("")
    setResults([])
    setError(null)
    setTotalCount(0)
    setCurrentPage(1)
    setTotalPages(0)
    setHasSearched(false)
    setSearchMetadata(null)
  }, [])

  // Handle load more
  const handleLoadMore = useCallback(() => {
    if (currentPage < totalPages && !loading) {
      performSearch(currentPage + 1)
    }
  }, [currentPage, totalPages, loading, performSearch])

  // Handle conversation click
  const handleConversationClick = useCallback((conversationId: string) => {
    onSelectConversation?.(conversationId)
  }, [onSelectConversation])

  // Handle Enter key
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }, [handleSearch])

  // Memoized search results
  const searchResultItems = useMemo(() => {
    return results.map((result) => {
      const isActive = currentConversationId === result.conversation_id
      const fullMessage = result.first_message || "Hội thoại không có tiêu đề"
      const truncatedMessage = truncateMessage(fullMessage)
      const needsTooltip = fullMessage.length > 50

      return (
        <TooltipProvider key={result.conversation_id}>
          <Card
            className={cn(
              "cursor-pointer transition-all duration-200 hover:shadow-md border",
              isActive ? "border-primary/50 bg-primary/5" : "border-border hover:border-border/60"
            )}
            onClick={() => handleConversationClick(result.conversation_id)}
          >
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-lg flex-shrink-0",
                  isActive 
                    ? "bg-primary/15 text-primary" 
                    : "bg-muted/60 text-muted-foreground"
                )}>
                  <MessageSquare className="h-4 w-4" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-2">
                  {/* Title and Message Count */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      {needsTooltip ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className={cn(
                              "font-medium text-sm leading-tight truncate",
                              isActive ? "text-primary" : "text-foreground"
                            )}>
                              {truncatedMessage}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-xs">
                            <p className="text-sm break-words">{fullMessage}</p>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <div className={cn(
                          "font-medium text-sm leading-tight",
                          isActive ? "text-primary" : "text-foreground"
                        )}>
                          {truncatedMessage}
                        </div>
                      )}
                    </div>
                    <Badge variant="secondary" className="text-xs flex-shrink-0">
                      {result.message_count} tin nhắn
                    </Badge>
                  </div>

                  {/* Matching Content */}
                  {result.matching_content && (
                    <div className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                      <span className="font-medium">Nội dung khớp:</span> {result.matching_content}
                    </div>
                  )}

                  {/* Date */}
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatDate(result.last_updated)}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TooltipProvider>
      )
    })
  }, [results, currentConversationId, truncateMessage, formatDate, handleConversationClick])

  return (
    <div className={cn("space-y-4", className)}>
      {/* Search Form */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Search className="h-5 w-5" />
            Tìm kiếm hội thoại
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search Query */}
          <div className="space-y-2">
            <Label htmlFor="search-query">Từ khóa tìm kiếm</Label>
            <Input
              id="search-query"
              placeholder="Nhập từ khóa để tìm trong nội dung hội thoại..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full"
            />
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="date-from">Từ ngày</Label>
              <Input
                id="date-from"
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="date-to">Đến ngày</Label>
              <Input
                id="date-to"
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button 
              onClick={handleSearch} 
              disabled={loading}
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Đang tìm...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Tìm kiếm
                </>
              )}
            </Button>
            <Button 
              variant="outline" 
              onClick={handleClear}
              disabled={loading}
            >
              <X className="mr-2 h-4 w-4" />
              Xóa
            </Button>
          </div>

          {/* Search Metadata */}
          {searchMetadata && hasSearched && (
            <div className="text-xs text-muted-foreground space-y-1">
              <div className="flex items-center gap-2">
                <Filter className="h-3 w-3" />
                <span>
                  {searchMetadata.has_query && `Từ khóa: "${searchQuery}"`}
                  {searchMetadata.has_query && searchMetadata.has_date_filter && " • "}
                  {searchMetadata.has_date_filter && `Thời gian: ${searchMetadata.date_range}`}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Search Results */}
      {hasSearched && (
        <div className="space-y-3">
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-sm text-muted-foreground">
              Kết quả tìm kiếm ({totalCount} hội thoại)
            </h3>
            {totalPages > 1 && (
              <span className="text-xs text-muted-foreground">
                Trang {currentPage}/{totalPages}
              </span>
            )}
          </div>

          {/* Loading State */}
          {loading && results.length === 0 && (
            <div className="flex justify-center items-center p-8">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Đang tìm kiếm...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <Card className="border-destructive/20 bg-destructive/5">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 text-destructive">
                  <X className="h-4 w-4" />
                  <span className="text-sm">{error}</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results List */}
          {!loading && !error && results.length === 0 && hasSearched && (
            <Card>
              <CardContent className="p-8 text-center">
                <div className="space-y-3">
                  <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto">
                    <FileText className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium text-sm">Không tìm thấy kết quả</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Thử thay đổi từ khóa hoặc khoảng thời gian tìm kiếm
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results */}
          {results.length > 0 && (
            <>
              <div className="space-y-2">
                {searchResultItems}
              </div>

              {/* Load More Button */}
              {currentPage < totalPages && (
                <div className="flex justify-center pt-4">
                  <Button 
                    variant="outline" 
                    onClick={handleLoadMore}
                    disabled={loading}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Đang tải...
                      </>
                    ) : (
                      <>
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Tải thêm kết quả ({currentPage}/{totalPages})
                      </>
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
} 