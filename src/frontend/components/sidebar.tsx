"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileUploader } from "@/components/file-uploader"
import { ConversationList } from "@/components/conversation-list"
import { Input } from "@/components/ui/input"
import { PlusCircle, MessageSquare, FileText, Loader2, Search, X } from "lucide-react"
import { useState, useCallback, useEffect } from "react"
import { conversationsApi } from "@/lib/api"
import { useToast } from "@/components/ui/use-toast"
import { useAuth } from "@/hooks/useAuth"
import { debounce } from "@/lib/utils"

interface SidebarProps {
  className?: string
  onSelectConversation?: (conversationId: string) => void
  onNewConversation?: () => void
  currentConversationId?: string | null
  onSelectedFilesChange?: (selectedIds: string[]) => void
  searchQuery?: string
  searchResults?: any[]
}

export function Sidebar({ 
  className, 
  onSelectConversation, 
  onNewConversation,
  currentConversationId, 
  onSelectedFilesChange,
  searchQuery = "",
  searchResults = []
}: SidebarProps) {
  const { user } = useAuth()
  const isAdmin = user?.role === "admin"
  
  // Đặt tab mặc định là "conversations" cho tất cả người dùng
  const [activeTab, setActiveTab] = useState("conversations")
  const [creatingConversation, setCreatingConversation] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)
  const { toast } = useToast()
  
  return (
    <div className={cn("flex flex-col border-r bg-background relative z-10", className)}>
      <div className="p-4">
        <Button 
          className="w-full justify-start gap-2" 
          onClick={onNewConversation}
        >
          <PlusCircle className="h-4 w-4" />
          <span>Hội thoại mới</span>
        </Button>
      </div>
      
      <Tabs defaultValue="conversations" value={activeTab} onValueChange={setActiveTab} className="flex-1">
        <div className="px-4">
          <TabsList className="w-full">
            {isAdmin && (
              <TabsTrigger value="documents" className="flex-1">
                <FileText className="mr-2 h-4 w-4" />
                Tài liệu
              </TabsTrigger>
            )}
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
        {isAdmin && (
          <TabsContent value="documents" className="flex-1">
            <ScrollArea className="h-[calc(100vh-8rem)] p-4">
              <FileUploader onSelectedFilesChange={onSelectedFilesChange} />
            </ScrollArea>
          </TabsContent>
        )}
      </Tabs>
    </div>
  )
}
