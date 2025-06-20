"use client"

import { Button } from "@/components/ui/button"
import { Menu, Database, Moon, Sun, Code, PanelLeftClose, PanelLeft, Search, X, Loader2, MessageSquare } from "lucide-react"
import { useTheme } from "next-themes"
import { useMobile } from "@/hooks/use-mobile"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { UserDropdown } from "@/components/user-dropdown"
import { Input } from "@/components/ui/input"
import { useState, useCallback } from "react"
import { conversationsApi } from "@/lib/api"
import { debounce } from "@/lib/utils"

interface HeaderProps {
  onMenuClick?: () => void
  onSqlClick?: () => void
  sqlPanelOpen?: boolean
  onSidebarToggle?: () => void
  isSidebarOpen?: boolean
  onSearch?: (query: string, results: any[]) => void
  onSelectConversation?: (conversationId: string) => void
}

export function Header({ onMenuClick, onSqlClick, sqlPanelOpen, onSidebarToggle, isSidebarOpen, onSearch, onSelectConversation }: HeaderProps) {
  const { theme, setTheme } = useTheme()
  const isMobile = useMobile()
  const [searchQuery, setSearchQuery] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])

  // Tìm kiếm realtime khi nhập
  const performSearch = useCallback(async (query: string) => {
    if (!query || query.trim() === "") {
      onSearch?.("", [])
      setIsSearching(false)
      return
    }
    
    setIsSearching(true)
    try {
      const response = await conversationsApi.searchConversations({
        query: query.trim(),
        page: 1,
        pageSize: 10
      })
      
      if (response && response.conversations) {
        onSearch?.(query, response.conversations)
        setSearchResults(response.conversations)
        
        if (response.conversations.length === 0) {
          console.log("Không tìm thấy kết quả nào cho:", query)
        } else {
          console.log(`Tìm thấy ${response.conversations.length} kết quả cho: ${query}`)
        }
      }
    } catch (error) {
      console.error("Lỗi khi tìm kiếm:", error)
      onSearch?.(query, [])
    } finally {
      setIsSearching(false)
    }
  }, [onSearch])
  
  // Debounce tìm kiếm để tránh gọi API quá nhiều
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      performSearch(query)
    }, 300),
    [performSearch]
  )
  
  // Xử lý thay đổi input tìm kiếm
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value
    setSearchQuery(query)
    debouncedSearch(query)
  }, [debouncedSearch])
  
  // Xóa tìm kiếm
  const handleClearSearch = useCallback(() => {
    setSearchQuery("")
    onSearch?.("", [])
  }, [onSearch])

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-subtle relative z-50">
      <div className="flex h-16 items-center px-4">
        {isMobile ? (
          <Button variant="ghost" size="icon" onClick={onMenuClick} className="mr-2">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Mở menu</span>
          </Button>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onSidebarToggle}
                  className="mr-2"
                >
                  {isSidebarOpen ? (
                    <PanelLeftClose className="h-5 w-5" />
                  ) : (
                    <PanelLeft className="h-5 w-5" />
                  )}
                  <span className="sr-only">
                    {isSidebarOpen ? "Thu gọn sidebar" : "Mở rộng sidebar"}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent className="z-[100]">
                <p>{isSidebarOpen ? "Thu gọn sidebar" : "Mở rộng sidebar"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        <div className="flex items-center gap-2 font-semibold">
          <div className="bg-primary/10 p-1.5 rounded-md">
            <Database className="h-5 w-5 text-primary" />
          </div>
          <span>Hệ thống RAG - Cơ sở dữ liệu</span>
          {/* <Badge variant="outline" className="ml-1 font-normal">
            Beta
          </Badge> */}
        </div>
        
        {/* Ô tìm kiếm ở giữa header */}
        <div className="flex-1 max-w-xl mx-auto px-4">
          <div className="relative">
            <Input
              placeholder="Tìm kiếm hội thoại..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="pl-8 pr-8 h-9"
            />
            <Search className="h-4 w-4 absolute left-2.5 top-2.5 text-muted-foreground" />
            {searchQuery && (
              <button 
                onClick={handleClearSearch}
                className="absolute right-2.5 top-2.5 text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            )}
            {isSearching && (
              <Loader2 className="h-4 w-4 absolute right-2.5 top-2.5 animate-spin" />
            )}
            
            {/* Dropdown kết quả tìm kiếm */}
            {searchQuery && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-background border rounded-md shadow-lg z-50 max-h-[60vh] overflow-auto">
                <div className="p-2">
                  <div className="text-xs text-muted-foreground px-2 py-1 flex justify-between">
                    <span>Kết quả tìm kiếm ({searchResults.length})</span>
                  </div>
                  
                  {isSearching ? (
                    <div className="flex items-center justify-center p-4">
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      <span className="text-xs text-muted-foreground">Đang tìm kiếm...</span>
                    </div>
                  ) : searchResults.length > 0 ? (
                    <div className="space-y-1">
                      {searchResults.map((conversation) => (
                        <div
                          key={conversation.conversation_id}
                          className="group relative flex items-center gap-3 p-2 rounded-md cursor-pointer transition-all duration-200 hover:bg-accent"
                          onClick={() => onSearch?.("", []) || onSelectConversation?.(conversation.conversation_id)}
                        >
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0 bg-muted/60 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary">
                            <MessageSquare className="h-3.5 w-3.5" />
                          </div>
                          <div className="flex-1 min-w-0 space-y-0.5">
                            <div className="font-medium text-xs leading-tight truncate">
                              {conversation.first_message || "Hội thoại không có tiêu đề"}
                            </div>
                            {conversation.matching_content && (
                              <div className="text-xs text-muted-foreground truncate">
                                {conversation.matching_content.substring(0, 50)}...
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-4 text-center">
                      <Search className="h-8 w-8 text-muted-foreground/40 mb-2" />
                      <p className="text-sm text-muted-foreground">Không tìm thấy hội thoại nào</p>
                      <p className="text-xs text-muted-foreground/60 mt-1">Thử tìm kiếm với từ khóa khác</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {!isMobile && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={sqlPanelOpen ? "secondary" : "outline"}
                    size="sm"
                    onClick={onSqlClick}
                    className="gap-1.5"
                  >
                    <Code className="h-4 w-4" />
                    <span>SQL Playground</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{sqlPanelOpen ? "Đóng" : "Mở"} SQL Playground</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  aria-label="Chuyển đổi chế độ sáng/tối"
                >
                  <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                  <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  <span className="sr-only">Chuyển đổi chế độ sáng/tối</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Chuyển đổi chế độ sáng/tối</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <UserDropdown />
        </div>
      </div>
    </header>
  )
}
