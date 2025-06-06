"use client"

import { Sheet, SheetContent } from "@/components/ui/sheet"
import { Sidebar } from "@/components/sidebar"

interface MobileNavProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelectConversation?: (conversationId: string) => void
  currentConversationId?: string | null
}

export function MobileNav({ open, onOpenChange, onSelectConversation, currentConversationId }: MobileNavProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="p-0 w-[320px]">
        <Sidebar onSelectConversation={onSelectConversation} currentConversationId={currentConversationId} />
      </SheetContent>
    </Sheet>
  )
}
