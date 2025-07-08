"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Sidebar } from "@/components/sidebar"
import { Header } from "@/components/header"
import { ChatInterface } from "@/components/chat-interface"
import { MobileNav } from "@/components/mobile-nav"
import { SqlPlayground } from "@/components/sql-playground"
import { useMobile } from "@/hooks/use-mobile"
import { Button } from "@/components/ui/button"
import { Database, Shield, Settings } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable"
import { AuthGuard } from "@/components/auth-guard"
import { useAuth } from "@/hooks/useAuth"
import { conversationsApi } from "@/lib/api"
import { toast } from "@/components/ui/use-toast"
import { cn } from "@/lib/utils"

// Hàm tiện ích để truy cập localStorage an toàn
const getLocalStorage = (key: string): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(key);
  }
  return null;
};

export function MainLayout() {
  const searchParams = useSearchParams();
  const forceStudentMode = searchParams.get('student') === 'true';
  
  // Khởi tạo trạng thái sidebar từ localStorage hoặc mặc định là true
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const stored = getLocalStorage('sidebarOpen');
    return stored === null ? true : stored === 'true';
  });
  const [sqlPanelOpen, setSqlPanelOpen] = useState(false)
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [conversationMessages, setConversationMessages] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([])
  // Thêm state cho tìm kiếm
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  
  const isMobile = useMobile()
  const { user } = useAuth()

  const handleNewConversation = () => {
    setLoading(true);
    setCurrentConversationId(null);
    setConversationMessages([
      {
        id: "welcome-message-" + Date.now(),
        role: "assistant",
        content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
        sources: [],
        citations: []
      }
    ]);
    setSelectedFileIds([]);
    setLoading(false);
  }

  // Lưu trạng thái sidebar vào localStorage khi thay đổi
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('sidebarOpen', sidebarOpen.toString());
    }
  }, [sidebarOpen]);

  // Xử lý kết quả tìm kiếm từ header
  const handleSearch = (query: string, results: any[]) => {
    setSearchQuery(query)
    setSearchResults(results)
    
    // Nếu đang ở mobile và có kết quả tìm kiếm, mở sidebar
    if (isMobile && query && results.length > 0) {
      setSidebarOpen(true)
    }
  }

  // Khi mount chỉ load danh sách hội thoại, không load messages
  // Xử lý khi chọn một cuộc hội thoại
  const handleSelectConversation = async (conversationId: string) => {
    if (!conversationId || conversationId === currentConversationId) return;
    setLoading(true);
    setCurrentConversationId(conversationId);
    try {
      const response = await conversationsApi.getConversation(conversationId);
      if (response && response.status === "success") {
        if (response.data && response.data.messages && Array.isArray(response.data.messages) && response.data.messages.length > 0) {
          setConversationMessages(response.data.messages);
        } else {
          setConversationMessages([
            {
              id: "welcome-message-" + Date.now(),
              role: "assistant",
              content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
              sources: [],
              citations: []
            }
          ]);
        }
      } else {
        setConversationMessages([]);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể tải tin nhắn của hội thoại này."
        });
      }
    } catch (error) {
      console.error("Lỗi khi tải hội thoại:", error);
      setConversationMessages([
        {
          id: "welcome-message-" + Date.now(),
          role: "assistant",
          content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
          sources: [],
          citations: []
        }
      ]);
    } finally {
      setLoading(false);
      if (isMobile) {
        setSidebarOpen(false);
      }
    }
  };

  return (
    <AuthGuard>
      <div className="flex h-screen bg-background">
        {/* Desktop Sidebar */}
        {!isMobile && (
          <div className={cn(
            "fixed left-0 top-0 h-full w-[300px] transition-transform duration-300 ease-in-out z-40",
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}>
            <Sidebar
              className="h-full border-r bg-background"
              onSelectConversation={handleSelectConversation}
              onNewConversation={handleNewConversation}
              currentConversationId={currentConversationId}
              onSelectedFilesChange={setSelectedFileIds}
              searchQuery={searchQuery}
              searchResults={searchResults}
            />
          </div>
        )}

        {/* Mobile Navigation */}
        {isMobile && (
          <MobileNav
            open={sidebarOpen}
            onOpenChange={setSidebarOpen}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            currentConversationId={currentConversationId}
            searchQuery={searchQuery}
            searchResults={searchResults}
          />
        )}

        {/* Main Content Area */}
        <div className={cn(
          "flex flex-col flex-1 overflow-hidden transition-all duration-300 ease-in-out",
          !isMobile && sidebarOpen ? "ml-[300px]" : "ml-0"
        )}>
          {/* Admin Banner - chỉ hiển thị khi admin đang ở chế độ student */}
          {user?.role === 'admin' && forceStudentMode && (
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-2 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4" />
                <span className="text-sm font-medium">
                  Chế độ Student (Admin: {user.email})
                </span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => window.location.href = "/admin"}
                className="flex items-center gap-2 text-xs"
              >
                <Settings className="h-3 w-3" />
                Quản lý Admin
              </Button>
            </div>
          )}
          
          <Header
            onMenuClick={() => setSidebarOpen(true)}
            onSqlClick={() => setSqlPanelOpen(!sqlPanelOpen)}
            sqlPanelOpen={sqlPanelOpen}
            onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}
            isSidebarOpen={sidebarOpen}
            onSearch={handleSearch}
            onNewConversation={handleNewConversation}
          />

          <main className="flex-1 overflow-hidden flex">
            <ResizablePanelGroup direction="horizontal" className="flex-1">
              <ResizablePanel defaultSize={sqlPanelOpen ? 60 : 100} minSize={30} className="overflow-auto">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="w-10 h-10 border-t-2 border-b-2 border-primary rounded-full animate-spin"></div>
                  </div>
                ) : (
                  <ChatInterface
                    initialMessages={conversationMessages}
                    conversationId={currentConversationId}
                    selectedFileIds={selectedFileIds}
                  />
                )}
              </ResizablePanel>

              {sqlPanelOpen && (
                <>
                  <ResizableHandle withHandle />
                  <ResizablePanel defaultSize={40} minSize={30} className="overflow-auto">
                    <SqlPlayground onClose={() => setSqlPanelOpen(false)} />
                  </ResizablePanel>
                </>
              )}
            </ResizablePanelGroup>

            {!sqlPanelOpen && !isMobile && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute right-4 bottom-4 h-10 w-10 rounded-full shadow-md bg-primary text-primary-foreground hover:bg-primary/90 z-10"
                      onClick={() => setSqlPanelOpen(true)}
                    >
                      <Database className="h-5 w-5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="left">
                    <p>Mở SQL Playground</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  )
}
