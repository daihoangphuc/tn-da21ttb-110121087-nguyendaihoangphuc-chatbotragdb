"use client"

import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { Sidebar } from "@/components/sidebar"

interface MobileNavProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectConversation?: (conversationId: string) => void
  currentConversationId?: string | null
  searchQuery?: string
  searchResults?: any[]
}

export function MobileNav({ 
  open, 
  onOpenChange, 
  onSelectConversation, 
  currentConversationId,
  searchQuery = "",
  searchResults = []
}: MobileNavProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="p-0 w-[320px]">
        <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
        <Sidebar 
          onSelectConversation={onSelectConversation} 
          currentConversationId={currentConversationId}
          searchQuery={searchQuery}
          searchResults={searchResults}
        />
      </SheetContent>
    </Sheet>
  )
}
