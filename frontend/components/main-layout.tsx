"use client"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/sidebar"
import { Header } from "@/components/header"
import { ChatInterface } from "@/components/chat-interface"
import { MobileNav } from "@/components/mobile-nav"
import { SqlPlayground } from "@/components/sql-playground"
import { useMobile } from "@/hooks/use-mobile"
import { Button } from "@/components/ui/button"
import { Database } from "lucide-react"
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
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sqlPanelOpen, setSqlPanelOpen] = useState(false)
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [conversationMessages, setConversationMessages] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>([])
  const isMobile = useMobile()
  const { user } = useAuth()

  // Tải cuộc hội thoại gần đây nhất khi component mount
  useEffect(() => {
    const loadConversation = async () => {
      if (!user) return;
      
      setLoading(true);
      try {
        // Kiểm tra xem có conversation_id được lưu trong localStorage không
        const savedConversationId = getLocalStorage("current_conversation_id");
        
        if (savedConversationId) {
          // Nếu có, sử dụng conversation_id đó
          setCurrentConversationId(savedConversationId);
          
          try {
            // Tải hội thoại với ID đã lưu
            const response = await conversationsApi.getConversation(savedConversationId);
            if (response && response.status === "success") {
              if (response.data && response.data.messages && Array.isArray(response.data.messages) && response.data.messages.length > 0) {
                // Có tin nhắn, hiển thị chúng
                setConversationMessages(response.data.messages);
              } else {
                // Hội thoại mới, hiển thị tin nhắn chào mừng
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
              
              // Xóa conversation_id khỏi localStorage sau khi đã sử dụng
              if (typeof window !== 'undefined') {
                localStorage.removeItem("current_conversation_id");
              }
              
              return; // Thoát khỏi hàm vì đã tìm thấy và tải hội thoại
            }
          } catch (error) {
            console.error("Lỗi khi tải hội thoại đã lưu:", error);
            // Tiếp tục với getLatestConversation nếu có lỗi
          }
        }
        
        // Nếu không có ID đã lưu hoặc có lỗi khi tải, sử dụng getLatestConversation
        const response = await conversationsApi.getLatestConversation();
        if (response && response.found && response.conversation_info) {
          setCurrentConversationId(response.conversation_info.conversation_id);
          // Đảm bảo messages là một mảng
          const messages = Array.isArray(response.messages) ? response.messages : [];
          setConversationMessages(messages);
        } else {
          // Nếu không có hội thoại nào, khởi tạo với một tin nhắn chào mừng
          setConversationMessages([
            {
              id: "welcome-message",
              role: "assistant",
              content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
              sources: [],
              citations: []
            }
          ]);
        }
      } catch (error) {
        console.error("Lỗi khi tải hội thoại:", error);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể tải hội thoại. Vui lòng thử lại sau."
        });
        // Khởi tạo với tin nhắn chào mừng trong trường hợp lỗi
        setConversationMessages([
          {
            id: "welcome-message",
            role: "assistant",
            content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
            sources: [],
            citations: []
          }
        ]);
      } finally {
        setLoading(false);
      }
    };

    loadConversation();
  }, [user]);

  // Xử lý khi chọn một cuộc hội thoại
  const handleSelectConversation = async (conversationId: string) => {
    if (!conversationId || conversationId === currentConversationId) return;
    
    setLoading(true);
    setCurrentConversationId(conversationId);

    try {
      const response = await conversationsApi.getConversation(conversationId);
      
      // Hội thoại tồn tại nhưng có thể không có tin nhắn (hội thoại mới)
      if (response && response.status === "success") {
        if (response.data && response.data.messages && Array.isArray(response.data.messages) && response.data.messages.length > 0) {
          // Có tin nhắn, hiển thị chúng
          setConversationMessages(response.data.messages);
        } else {
          // Hội thoại mới, hiển thị tin nhắn chào mừng
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
        // Nếu không tìm thấy hội thoại hoặc có lỗi, hiển thị thông báo
        setConversationMessages([]);
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể tải tin nhắn của hội thoại này."
        });
      }
    } catch (error) {
      console.error("Lỗi khi tải hội thoại:", error);
      
      // Hiển thị tin nhắn chào mừng cho hội thoại mới
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
      // Đóng sidebar trên mobile sau khi chọn hội thoại
      if (isMobile) {
        setSidebarOpen(false);
      }
    }
  };

  return (
    <AuthGuard>
      <div className="flex h-screen bg-background">
        {!isMobile ? (
          <Sidebar
            className={cn(
              "fixed inset-y-0 z-50 w-[300px] border-r bg-background transition-transform duration-300 lg:static lg:translate-x-0",
              sidebarOpen ? "translate-x-0" : "-translate-x-[300px]"
            )}
            onSelectConversation={handleSelectConversation}
            currentConversationId={currentConversationId}
            onSelectedFilesChange={setSelectedFileIds}
          />
        ) : (
          <MobileNav
            open={sidebarOpen}
            onOpenChange={setSidebarOpen}
            onSelectConversation={handleSelectConversation}
            currentConversationId={currentConversationId}
          />
        )}

        <div className="flex flex-col flex-1 overflow-hidden">
          <Header
            onMenuClick={() => setSidebarOpen(true)}
            onSqlClick={() => setSqlPanelOpen(!sqlPanelOpen)}
            sqlPanelOpen={sqlPanelOpen}
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
                      className="absolute right-4 bottom-4 h-10 w-10 rounded-full shadow-md bg-primary text-primary-foreground hover:bg-primary/90"
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
