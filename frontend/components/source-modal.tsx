"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileIcon, ExternalLink, Copy } from "lucide-react"

// Import hoặc định nghĩa lại interface SourceDetail
interface SourceDetail {
  id: string
  title: string
  page: string
  content: string
  highlight: string
  relevance: number
}

interface SourceModalProps {
  isOpen: boolean
  onClose: () => void
  source: SourceDetail | null
}

export function SourceModal({ isOpen, onClose, source }: SourceModalProps) {
  const [highlightedContent, setHighlightedContent] = useState<string>("")
  
  // Reset highlighted content when source changes or modal closes
  useEffect(() => {
    if (source && source.content && isOpen) {
      setHighlightedContent(source.content);
    } else {
      setHighlightedContent("");
    }
  }, [source, isOpen]);
  
  // Hàm sao chép nội dung vào clipboard
  const copyToClipboard = () => {
    if (source && source.content) {
      navigator.clipboard.writeText(source.content)
        .then(() => {
          console.log("Đã sao chép nội dung vào clipboard");
        })
        .catch(err => {
          console.error("Không thể sao chép nội dung:", err);
        });
    }
  };

  // If no source or modal is closed, don't render
  if (!source || !isOpen) return null

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-start gap-3">
            <div className="bg-primary/10 p-2 rounded-md">
              <FileIcon className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1">
              <DialogTitle className="text-xl">{source.title}</DialogTitle>
              <div className="flex items-center gap-2 mt-1">
                <DialogDescription>Trang {source.page}</DialogDescription>
                <Badge variant="outline" className="ml-2">
                  Độ liên quan: {Math.round(source.relevance * 100)}%
                </Badge>
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="border rounded-md p-4 bg-muted/30 my-2">
          <ScrollArea className="h-[300px] rounded-md">
            <div className="raw-content">
              <pre>{highlightedContent}</pre>
            </div>
          </ScrollArea>
        </div>

        <div className="flex justify-between items-center">
          <div className="text-sm text-muted-foreground">Trích dẫn từ nguồn tài liệu</div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="gap-1" onClick={copyToClipboard}>
              <Copy className="h-3.5 w-3.5" />
              <span>Sao chép</span>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
