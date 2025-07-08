import React from 'react'
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "@/lib/utils"
import { CopyButton } from "@/components/ui/copy-button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface StreamingContentProps {
  content: string
}

interface Citation {
  index: number;
  text: string;
}

export const StreamingContent = React.memo(({ content }: StreamingContentProps) => {
  const citations: Citation[] = [];
  let citationIndex = 0;

  // Regex mạnh hơn để tìm cả hai loại trích dẫn
  // 1. (trang X, file.pdf)
  // 2. (file file.pdf)
  // Nó sẽ capture nội dung bên trong dấu ngoặc đơn
  let processedContent = content.replace(
    /\(((?:trang \d+,\s*|file\s+)[^)]+\.pdf)\)/g,
    (match, citationText) => {
      citationIndex++;
      citations.push({
        index: citationIndex,
        text: citationText
      });
      // Thay thế trích dẫn bằng một placeholder duy nhất
      return `[citation:${citationIndex}]`;
    }
  );

  // Component hiển thị trích dẫn với tooltip
  const CitationComponent = ({ index }: { index: number }) => {
    const citation = citations.find(c => c.index === index);
    if (!citation) return null;

    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span 
            className="text-[#3B82F6] hover:text-[#2563EB] font-medium cursor-pointer text-[13px]"
            style={{ textDecoration: 'none' }}
          >
            [{citation.index}]
          </span>
        </TooltipTrigger>
        <TooltipContent
          side="top"
          sideOffset={5}
          className="bg-zinc-800 text-zinc-200 text-[13px] px-3 py-1.5 rounded-md shadow-lg border-0 max-w-xs"
        >
          <span>({citation.text})</span>
        </TooltipContent>
      </Tooltip>
    );
  };

  // Hàm tiện ích để xử lý nội dung có trích dẫn
  const processWithCitations = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, child => {
      if (typeof child === 'string') {
        const parts = child.split(/(\[citation:\d+\])/g);
        return parts.map((part, i) => {
          if (part.startsWith('[citation:')) {
            const match = part.match(/\[citation:(\d+)\]/);
            if (match) {
              const index = parseInt(match[1], 10);
              return <CitationComponent key={i} index={index} />;
            }
          }
          return part;
        });
      }
      if (React.isValidElement(child) && child.props.children) {
        return React.cloneElement(child, {
          ...child.props,
          children: processWithCitations(child.props.children)
        });
      }
      return child;
    });
  };
  
  const markdownComponents = {
    // Tiêu đề
    h1: ({node, children, ...props}) => <h1 className="text-xl font-bold mt-4 mb-2" {...props}>{processWithCitations(children)}</h1>,
    h2: ({node, children, ...props}) => <h2 className="text-lg font-bold mt-3 mb-1.5" {...props}>{processWithCitations(children)}</h2>,
    h3: ({node, children, ...props}) => <h3 className="text-base font-semibold mt-2 mb-1" {...props}>{processWithCitations(children)}</h3>,
    h4: ({node, children, ...props}) => <h4 className="text-sm font-semibold mt-1 mb-0.5" {...props}>{processWithCitations(children)}</h4>,
    
    // Đoạn văn - Sử dụng <div> thay vì <p> để tránh lỗi hydration
    p: ({node, children, ...props}) => (
      <div className="break-words mb-4" {...props}>
        {processWithCitations(children)}
      </div>
    ),
    
    // Danh sách
    ul: ({node, ...props}) => <ul className="list-disc pl-6 my-2 space-y-1" {...props} />,
    ol: ({node, ...props}) => <ol className="list-decimal pl-6 my-2 space-y-1" {...props} />,
    li: ({node, children, ...props}) => (
      <li className="pl-2" {...props}>
        {processWithCitations(children)}
      </li>
    ),

    // Bảng
    table: ({node, ...props}) => (
      <div className="my-4 w-full overflow-x-auto border rounded-lg">
        <table className="min-w-full divide-y divide-gray-200" {...props} />
      </div>
    ),
    thead: ({node, ...props}) => (
      <thead className="bg-gray-50/50" {...props} />
    ),
    tbody: ({node, ...props}) => (
      <tbody className="divide-y divide-gray-200 bg-white" {...props} />
    ),
    tr: ({node, ...props}) => (
      <tr className="hover:bg-gray-50" {...props} />
    ),
    th: ({node, children, ...props}) => (
      <th 
        className="px-6 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider" 
        {...props}
      >
        {processWithCitations(children)}
      </th>
    ),
    td: ({node, children, ...props}) => (
      <td 
        className="px-6 py-4 whitespace-normal text-sm text-gray-900" 
        {...props}
      >
        {processWithCitations(children)}
      </td>
    ),
    
    // Định dạng văn bản
    strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
    em: ({node, ...props}) => <em {...props} />,
    
    // Liên kết
    a: ({node, href, ...props}) => (
      <a 
        href={href} 
        target="_blank" 
        rel="noopener noreferrer"
        className="text-blue-500 hover:underline"
        {...props} 
      />
    ),
    
    // Code
    pre: ({node, children, ...props}) => {
      const codeElement = React.Children.toArray(children)[0] as React.ReactElement;
      const value = codeElement?.props?.children || "";
      return (
        <pre className="relative group bg-muted/50 rounded p-4 text-sm font-mono overflow-x-auto my-4 max-w-full" {...props}>
          {children}
          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <CopyButton text={typeof value === 'string' ? value : Array.isArray(value) ? value.join('') : ''} />
          </div>
        </pre>
      )
    },
    code: ({node, inline, className, children, ...props}) => {
      if (!inline) {
        return <code className={className} {...props}>{children}</code>;
      }
      return (
        <code className="px-1.5 py-0.5 bg-muted/70 rounded text-xs font-mono" {...props}>
          {children}
        </code>
      )
    }
  };

  return (
    <TooltipProvider delayDuration={100}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {processedContent}
      </ReactMarkdown>
    </TooltipProvider>
  )
})

StreamingContent.displayName = 'StreamingContent' 