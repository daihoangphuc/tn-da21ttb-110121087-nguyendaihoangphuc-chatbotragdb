import { Avatar, AvatarFallback } from "./ui/avatar"
import { Database, Loader2, Globe, Sparkles, FileSearch } from "lucide-react"

interface LoadingMessageProps {
  elapsedTime: number
  status?: {
    type: string
    message: string
    details?: string
  }
}

export function LoadingMessage({ elapsedTime, status }: LoadingMessageProps) {
  let icon = <Database className="h-4 w-4" />
  let text = status?.message || "Đang truy xuất nguồn dữ liệu ..."
  if (status) {
    if (status.type === "searching_docs") {
      icon = <Database className="h-4 w-4" />
      text = status.message
    } else if (status.type === "searching_web") {
      icon = <Globe className="h-4 w-4" />
      text = status.message
    } else if (status.type === "processing_sql") {
      icon = <Sparkles className="h-4 w-4" />
      text = status.message
    } else if (status.type === "fallback") {
      icon = <FileSearch className="h-4 w-4" />
      text = status.message
      if (status.details) text += ` (${status.details})`
    } else if (status.type === "analyzing") {
      icon = <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
      text = status.message
    }
  }
  return (
    <div className="flex justify-start animate-in">
      <div className="flex gap-3 max-w-[80%]">
        <Avatar className="h-8 w-8 mt-1">
          <AvatarFallback className="bg-primary/10 text-primary">
            {icon}
          </AvatarFallback>
        </Avatar>
        <div className="rounded-lg p-4 shadow-md transition-all bg-card text-card-foreground border border-border/30 hover:border-border/60">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              {text} {elapsedTime.toFixed(1)}s
            </span>
          </div>
        </div>
      </div>
    </div>
  )
} 