import { Avatar, AvatarFallback } from "./ui/avatar"
import { Database, Loader2 } from "lucide-react"

interface LoadingMessageProps {
  elapsedTime: number
}

export function LoadingMessage({ elapsedTime }: LoadingMessageProps) {
  return (
    <div className="flex justify-start animate-in">
      <div className="flex gap-3 max-w-[80%]">
        <Avatar className="h-8 w-8 mt-1">
          <AvatarFallback className="bg-primary/10 text-primary">
            <Database className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="rounded-lg p-4 shadow-md transition-all bg-card text-card-foreground border border-border/30 hover:border-border/60">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Đang truy xuất nguồn dữ liệu ... {elapsedTime.toFixed(1)}s
            </span>
          </div>
        </div>
      </div>
    </div>
  )
} 