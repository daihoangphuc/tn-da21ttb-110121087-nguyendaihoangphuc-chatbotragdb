import React from 'react'
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"

interface StreamingContentProps {
  content: string
}

export const StreamingContent = React.memo(({ content }: StreamingContentProps) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Tiêu đề
        h1: ({node, ...props}) => <h1 className="text-xl font-bold" {...props} />,
        h2: ({node, ...props}) => <h2 className="text-lg font-bold" {...props} />,
        h3: ({node, ...props}) => <h3 className="text-base font-semibold" {...props} />,
        h4: ({node, ...props}) => <h4 className="text-sm font-semibold" {...props} />,
        
        // Đoạn văn
        p: ({node, ...props}) => <p className="break-words" {...props} />,
        
        // Danh sách
        ul: ({node, ...props}) => <ul {...props} />,
        ol: ({node, ...props}) => <ol {...props} />,
        li: ({node, ...props}) => <li {...props} />,
        
        // Định dạng văn bản
        strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
        em: ({node, ...props}) => <em {...props} />,
        
        // Liên kết
        a: ({node, href, ...props}) => (
          <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            {...props} 
          />
        ),
        
        // Code
        code: ({node, inline, className, children, ...props}) => {
          const match = /language-(\w+)/.exec(className || "")
          const language = match ? match[1] : ""
          const value = String(children).replace(/\n$/, "")
          
          if (!inline && language) {
            return (
              <div className="overflow-x-auto my-2 max-w-full">
                <pre className={cn(
                  "relative group",
                  language.toLowerCase() === "sql" ? "language-sql" : "bg-muted/50 rounded"
                )}>
                  <code className={className} {...props}>
                    {value}
                  </code>
                </pre>
              </div>
            )
          }
          
          return (
            <code 
              className="px-1.5 py-0.5 bg-muted/70 rounded text-xs font-mono" 
              {...props}
            >
              {children}
            </code>
          )
        }
      }}
    >
      {content}
    </ReactMarkdown>
  )
}) 