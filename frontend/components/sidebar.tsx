"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileUploader } from "@/components/file-uploader"
import { ConversationList } from "@/components/conversation-list"
import { PlusCircle, MessageSquare, FileText, Loader2 } from "lucide-react"
import { useState } from "react"
import { conversationsApi } from "@/lib/api"
import { useToast } from "@/components/ui/use-toast"

interface SidebarProps {
  className?: string
  onSelectConversation?: (conversationId: string) => void
  currentConversationId?: string | null
  onSelectedFilesChange?: (selectedIds: string[]) => void
}

export function Sidebar({ className, onSelectConversation, currentConversationId, onSelectedFilesChange }: SidebarProps) {
  const [activeTab, setActiveTab] = useState("documents")
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const { toast } = useToast()

  const handleCreateNewConversation = async () => {
    if (creatingConversation) return
    
    try {
      setCreatingConversation(true)
      const response = await conversationsApi.createConversation()
      
      if (response && response.conversation_id) {
        // Chuyển hướng đến hội thoại mới
        onSelectConversation && onSelectConversation(response.conversation_id)
        
        // Thêm hội thoại mới vào đầu danh sách
        const newConversation = {
          conversation_id: response.conversation_id,
          user_id: response.user_id || "",
          created_at: new Date().toISOString(),
          last_updated: new Date().toISOString(),
          first_message: "Hội thoại mới",
          message_count: 0
        };
        
        // Tăng refreshKey để kích hoạt việc tải lại danh sách hội thoại
        setRefreshKey(prev => prev + 1)
        
        toast({
          title: "Tạo hội thoại mới thành công",
        })
      } else {
        toast({
          variant: "destructive",
          title: "Lỗi",
          description: "Không thể tạo hội thoại mới. Vui lòng thử lại sau."
        })
      }
    } catch (error) {
      console.error('Lỗi khi tạo hội thoại mới:', error)
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Đã xảy ra lỗi khi tạo hội thoại mới. Vui lòng thử lại sau."
      })
    } finally {
      setCreatingConversation(false)
    }
  }

  return (
    <div className={cn("flex flex-col border-r bg-background", className)}>
      <div className="p-4">
        <Button 
          className="w-full justify-start gap-2" 
          onClick={handleCreateNewConversation}
          disabled={creatingConversation}
        >
          {creatingConversation ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <PlusCircle className="h-4 w-4" />
          )}
          <span>{creatingConversation ? "Đang tạo..." : "Hội thoại mới"}</span>
        </Button>
      </div>
      <Tabs defaultValue="conversations" value={activeTab} onValueChange={setActiveTab} className="flex-1">
        <div className="px-4">
          <TabsList className="w-full">
          <TabsTrigger value="documents" className="flex-1">
              <FileText className="mr-2 h-4 w-4" />
              Tài liệu
            </TabsTrigger>
            <TabsTrigger value="conversations" className="flex-1">
              <MessageSquare className="mr-2 h-4 w-4" />
              Hội thoại
            </TabsTrigger>

          </TabsList>
        </div>
        <TabsContent value="conversations" className="flex-1">
          <ScrollArea className="h-[calc(100vh-8rem)]">
            <ConversationList
              onSelectConversation={onSelectConversation}
              currentConversationId={currentConversationId}
              refreshKey={refreshKey}
            />
          </ScrollArea>
        </TabsContent>
        <TabsContent value="documents" className="flex-1">
          <ScrollArea className="h-[calc(100vh-8rem)] p-4">
            <FileUploader onSelectedFilesChange={onSelectedFilesChange} />
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  )
}
