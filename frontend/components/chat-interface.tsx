"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { SearchResults } from "@/components/search-results"
import { SourceModal } from "@/components/source-modal"
import { FileUploader } from "@/components/file-uploader"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Send,
  Bot,
  User,
  Search,
  FileSearch,
  Database,
  ThumbsUp,
  ThumbsDown,
  Copy,
  RotateCcw,
  Filter,
  FileIcon,
  Sparkles,
  Loader2,
  BookOpen,
  File,
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { filesApi, questionsApi, fetchApi, fetchApiStream } from "@/lib/api"
import React from 'react'
import { ChatMessage } from "@/components/chat-message"
import { LoadingMessage } from "./loading-message"

// Định nghĩa interface cho Source
interface Source {
  id: string
  title: string
  page: string
  relevance: number
}

// Định nghĩa interface cho SourceDetail mở rộng từ Source
interface SourceDetail extends Source {
  content: string
  highlight: string
}

// Định nghĩa interface cho RelatedQuestion
interface RelatedQuestion {
  id: string
  text: string
  query: string
}

// Định nghĩa interface cho Message
interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources: Source[]
  citations: {
    id: string
    text: string
    sourceId: string
  }[]
}

// Định nghĩa interface cho File từ API
interface FileResponse {
  filename: string;
  path: string;
  size: number;
  upload_date: string;
  extension: string;
  category: string;
  id: string;
}

// Thêm props mới vào interface
interface ChatInterfaceProps {
  initialMessages?: Message[]
  conversationId?: string | null
  selectedFileIds?: string[]
}

export function ChatInterface({ initialMessages = [], conversationId = null, selectedFileIds = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>(
    initialMessages.length > 0
      ? initialMessages
      : [
          {
            id: "1",
            role: "assistant",
            content:
              "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
            sources: [],
            citations: [],
          },
        ],
  )

  // Cập nhật messages khi initialMessages thay đổi
  useEffect(() => {
    if (initialMessages && Array.isArray(initialMessages) && initialMessages.length > 0) {
      // Đảm bảo mỗi message có đủ các trường cần thiết và key duy nhất
      const validMessages = initialMessages.map(msg => ({
        id: msg.id || `msg-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        role: msg.role || "assistant",
        content: msg.content || "",
        sources: Array.isArray(msg.sources) ? msg.sources : [],
        citations: Array.isArray(msg.citations) ? msg.citations : []
      }));
      setMessages(validMessages);
    } else {
      // Nếu không có tin nhắn, hiển thị tin nhắn chào mừng
      setMessages([
        {
          id: "welcome-message",
          role: "assistant",
          content: "Xin chào! Tôi là trợ lý RAG chuyên về cơ sở dữ liệu. Bạn có thể hỏi tôi bất kỳ câu hỏi nào về SQL, thiết kế cơ sở dữ liệu, hoặc các khái niệm liên quan.",
          sources: [],
          citations: []
        }
      ]);
    }
  }, [initialMessages]);

  const [input, setInput] = useState("")
  const [showSources, setShowSources] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isSending, setIsSending] = useState(false)
  
  // Thêm state để lưu trữ dữ liệu nguồn thực tế
  const [sourcesData, setSourcesData] = useState<Record<string, SourceDetail>>({})
  
  // Thêm state để lưu danh sách files từ API
  const [availableFiles, setAvailableFiles] = useState<FileResponse[]>([])
  // Thêm state để theo dõi trạng thái loading của files
  const [loadingFiles, setLoadingFiles] = useState(true)
  
  // Thêm state quản lý câu hỏi liên quan
  const [relatedQuestions, setRelatedQuestions] = useState<RelatedQuestion[]>([]);

  // Thêm useEffect để gọi API lấy câu hỏi gợi ý khi component mount
  useEffect(() => {
      updateRelatedQuestions();
  }, []); // Chỉ chạy một lần khi component mount

  const { toast } = useToast();

  // Thêm state để quản lý scroll
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Thêm event listener để kiểm tra vị trí scroll
  useEffect(() => {
    const handleScroll = () => {
      if (chatContainerRef.current) {
        const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
        setShouldAutoScroll(Math.abs(scrollHeight - clientHeight - scrollTop) < 100);
      }
    };

    const container = chatContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, []);

  // Sửa lại useEffect cho scroll
  useEffect(() => {
    if (shouldAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isTyping, shouldAutoScroll]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isSending) return;
    if (selectedFileIds.length === 0) {
      toast({
        title: "Chưa chọn tài liệu",
        description: "Vui lòng chọn ít nhất một tài liệu ở tab Tài liệu để tìm kiếm câu trả lời",
        variant: "warning",
        duration: 3000,
      });
      return;
    }
    setIsSending(true);
    setIsTyping(true);
    const userMessage = {
      id: Date.now().toString(),
      role: "user" as const,
      content: input,
      sources: [],
      citations: []
    };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    let abortController = new AbortController();
    const decoder = new TextDecoder();
    try {
      // Gọi fetchApiStream để lấy response stream
      const response = await fetchApiStream('/ask/stream', {
        method: 'POST',
        body: JSON.stringify({
          question: input,
          file_id: selectedFileIds
        }),
        signal: abortController.signal
      });

      // Phần xử lý stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Không thể đọc response');
      }
      let buffer = '';
      let sources: Source[] = [];
      let newSourcesData: Record<string, SourceDetail> = {};
      let hasCreatedAssistantMessage = false;
      let assistantMessageId = '';
      let currentContent = '';
      let currentQueryType = '';
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (!line.trim()) continue;
            
            // Handle start event to capture query_type
            if (line.startsWith('event: start')) {
              const dataLine = lines.find(l => l.startsWith('data:'));
              if (dataLine) {
                try {
                  const data = JSON.parse(dataLine.replace('data:', '').trim());
                  if (data.query_type) {
                    currentQueryType = data.query_type;
                    console.log(`Query type: ${currentQueryType}`);
                  }
                } catch (error) {
                  console.error('Lỗi khi parse dữ liệu start:', error);
                }
              }
            }
            else if (line.startsWith('event: content')) {
              const dataLine = lines.find(l => l.startsWith('data:'));
              if (dataLine) {
                try {
                  const data = JSON.parse(dataLine.replace('data:', '').trim());
                  if (data.content) {
                    currentContent += data.content;
                    if (!hasCreatedAssistantMessage) {
                      assistantMessageId = Date.now().toString();
                      setMessages(prev => [...prev, {
                        id: assistantMessageId,
                        role: "assistant",
                        content: currentContent,
                        sources: [],
                        citations: []
                      }]);
                      hasCreatedAssistantMessage = true;
                      console.log(`Created assistant message for query type: ${currentQueryType}`);
                    } else {
                      setMessages(prev => {
                        const updatedMessages = [...prev];
                        const lastMessage = updatedMessages[updatedMessages.length - 1];
                        if (lastMessage && lastMessage.role === 'assistant') {
                          lastMessage.content = currentContent;
                        }
                        return updatedMessages;
                      });
                    }
                  }
                } catch (error) {
                  console.error('Lỗi khi parse dữ liệu content:', error);
                }
              }
            }
            else if (line.startsWith('event: sources') && hasCreatedAssistantMessage) {
              const dataLine = lines.find(l => l.startsWith('data:'));
              if (dataLine) {
                try {
                  const data = JSON.parse(dataLine.replace('data:', '').trim());
                  if (data.sources && Array.isArray(data.sources)) {
                    sources = data.sources.map((source: any) => {
                      const sourceId = source.file_id || source.source || `source-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
                      if (source.content_snippet) {
                        newSourcesData[sourceId] = {
                          id: sourceId,
                          title: source.source || "Tài liệu không xác định",
                          page: source.page ? source.page.toString() : "1",
                          relevance: source.score || 0,
                          content: source.content_snippet,
                          highlight: source.highlight || source.content_snippet.substring(0, 150)
                        };
                      }
                      return {
                        id: sourceId,
                        title: source.source || "Tài liệu không xác định",
                        page: source.page ? source.page.toString() : "1",
                        relevance: source.score || 0
                      };
                    });
                    setMessages(prev => {
                      const updatedMessages = [...prev];
                      const lastMessage = updatedMessages[updatedMessages.length - 1];
                      if (lastMessage && lastMessage.role === 'assistant') {
                        lastMessage.sources = sources;
                      }
                      return updatedMessages;
                    });
                    setSourcesData(prevSources => ({
                      ...prevSources,
                      ...newSourcesData
                    }));
                  }
                } catch (error) {
                  console.error('Lỗi khi parse dữ liệu sources:', error);
                }
              }
            }
            else if (line.startsWith('event: end')) {
              try {
                const dataLine = lines.find(l => l.startsWith('data:'));
                if (dataLine) {
                  const data = JSON.parse(dataLine.replace('data:', '').trim());
                  console.log('Received end event with data:', data);
                  
                  // Ensure we've created an assistant message even if we didn't get content
                  if (!hasCreatedAssistantMessage && currentQueryType === 'other_question') {
                    console.log('Creating assistant message for other_question at end event');
                    assistantMessageId = Date.now().toString();
                    setMessages(prev => [...prev, {
                      id: assistantMessageId,
                      role: "assistant",
                      content: currentContent || "Mình là Chatbot chỉ hỗ trợ và phản hồi trong lĩnh vực cơ sở dữ liệu. Bạn vui lòng đặt câu hỏi liên quan đến cơ sở dữ liệu nhé.",
                      sources: [],
                      citations: []
                    }]);
                    hasCreatedAssistantMessage = true;
                  }
                  
                  await updateRelatedQuestions();
                }
              } catch (error) {
                console.error('Lỗi khi parse dữ liệu end:', error);
              }
              setIsTyping(false);
              setIsSending(false);
              break;
            }
          }
        }
      } finally {
        reader.cancel();
        abortController.abort();
        
        // Final fallback to ensure we always have an assistant message
        if (!hasCreatedAssistantMessage) {
          console.log('Creating fallback assistant message at stream end');
          setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role: "assistant",
            content: currentContent || "Mình là Chatbot chỉ hỗ trợ và phản hồi trong lĩnh vực cơ sở dữ liệu. Bạn vui lòng đặt câu hỏi liên quan đến cơ sở dữ liệu nhé.",
            sources: [],
            citations: []
          }]);
        }
        
        setIsTyping(false);
        setIsSending(false);
      }
    } catch (error) {
      console.error('Lỗi khi gửi câu hỏi:', error);
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: error instanceof Error ? error.message : "Có lỗi xảy ra khi gửi câu hỏi"
      });
      setIsTyping(false);
      setIsSending(false);
    }
  };
  
  const updateRelatedQuestions = async () => {
    try {
      const data = await fetchApi('/suggestions?num_suggestions=3', { method: 'GET' });
      if (data.suggestions && Array.isArray(data.suggestions)) {
        const newRelatedQuestions = data.suggestions.map((question: string, index: number) => ({
          id: `related-${index}`,
          text: question,
          query: question
        }));
        setRelatedQuestions(newRelatedQuestions);
      }
    } catch (error) {
      console.error('Lỗi khi cập nhật câu hỏi gợi ý:', error);
      setRelatedQuestions([]);
    }
  };
  
  // Hàm xử lý khi người dùng click vào câu hỏi gợi ý
  const handleRelatedQuestionClick = (questionQuery: string) => {
    setInput(questionQuery);
    // Tự động focus vào ô input (không cần thêm code nếu ô input đã tự focus)
  }
  
  // Hàm xử lý tạo lại câu trả lời
  const handleRegenerateResponse = (userMessageId: string) => {
    // Tìm câu hỏi của người dùng
    const messageIndex = messages.findIndex((msg) => msg.id === userMessageId);
    if (messageIndex === -1) return;
    
    const userMessage = messages[messageIndex];
    
    // Xóa câu trả lời hiện tại (tin nhắn tiếp theo sau tin nhắn người dùng)
    setMessages((prev) => prev.filter((_, index) => index !== messageIndex + 1));
    
    // Đặt trạng thái đang nhập
    setIsTyping(true);
    
    // Tạo lại câu trả lời (mô phỏng API call)
    setTimeout(() => {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content:
            "## SQL JOIN\n\n" +
            "SQL JOIN là một tính năng quan trọng[1] cho phép bạn truy vấn dữ liệu từ nhiều bảng trong một câu lệnh SELECT.\n\n" +
            "### Các loại JOIN\n\n" +
            "- INNER JOIN: Trả về các hàng khi có ít nhất một kết quả khớp trong cả hai bảng\n" +
            "- LEFT JOIN: Trả về tất cả các hàng từ bảng bên trái\n" +
            "- RIGHT JOIN: Trả về tất cả các hàng từ bảng bên phải\n\n" +
            "**Thiết kế cơ sở dữ liệu[2]** là quá trình tạo ra một mô hình dữ liệu chi tiết cho cơ sở dữ liệu.\n\n" +
            "```sql\n" +
            "SELECT columns\n" +
            "FROM table1\n" +
            "JOIN table2\n" +
            "ON table1.column = table2.column\n" +
            "```\n\n" +
            "1. Đầu tiên xác định các bảng cần join\n" +
            "2. Sau đó chỉ định điều kiện join\n" +
            "3. Cuối cùng chọn các cột cần hiển thị",
          sources: [
            { id: "source-1", title: "SQL_Basics.pdf", page: "12", relevance: 0.92 },
            { id: "source-2", title: "Database_Design.pdf", page: "45", relevance: 0.85 },
          ],
          citations: [
            {
              id: "1",
              text: "một tính năng quan trọng",
              sourceId: "source-1",
            },
            {
              id: "2",
              text: "Thiết kế cơ sở dữ liệu",
              sourceId: "source-2",
            },
          ],
        },
      ]);
      
      // Cập nhật câu hỏi liên quan sau khi tạo lại câu trả lời
      updateRelatedQuestions();
    }, 1500);
  };

  // Thêm state cho đồng hồ đếm
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Thêm useEffect để xử lý đồng hồ đếm
  useEffect(() => {
    if (isTyping) {
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        setElapsedTime(elapsed);
      }, 100);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setElapsedTime(0);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isTyping]);

  const formatMessageWithCitations = (message: Message) => {
    if (!message || !message.content) return "";
    return message.content; // Trả về nguyên văn nội dung
  };

  // Thay đổi cách hiển thị nội dung
  useEffect(() => {
    // Add click event handler using event delegation
    const handleCitationClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const citationLink = target.closest('.citation-link')
      
      if (citationLink) {
        event.preventDefault();
        const sourceId = citationLink.getAttribute('data-source-id')
        if (sourceId) {
          console.log('Đã nhấp vào citation-link với sourceId:', sourceId);
          console.log('Dữ liệu nguồn hiện có:', sourcesData);
          setSelectedSource(sourceId)
        }
      }
    }

    // Add single event listener to the document
    document.addEventListener('click', handleCitationClick)

    // Cleanup
    return () => {
      document.removeEventListener('click', handleCitationClick)
    }
  }, [sourcesData]) // Thêm sourcesData vào dependency array để đảm bảo luôn sử dụng dữ liệu mới nhất

  // Cleanup khi component unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  // Thêm hàm này vào trong component ChatInterface
  const sanitizeMarkdownContent = (content: string): string => {
    // Xử lý các trường hợp đặc biệt trong markdown
    
    // 1. Đảm bảo các cặp ** không bị cắt đứt
    let sanitized = content;
    
    // 2. Xử lý đặc biệt cho các từ khóa SQL và tên cột
    // Đảm bảo các từ khóa SQL và tên cột được bao quanh bởi backticks
    const sqlKeywords = [
      /\b(SELECT|FROM|WHERE|JOIN|ON|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|UNIQUE|PRIMARY KEY|FOREIGN KEY|REFERENCES)\b/g,
      /\b(malop|tenlop)\b/g,  // Tên cột cụ thể từ ví dụ
      /\b(PRIMARY|UNIQUE|KEY)\b/g  // Từ khóa SQL riêng lẻ
    ];
    
    // Tìm tất cả các đoạn code inline hiện có để tránh thêm backtick vào chúng
    const inlineCodeRegex = /`([^`]+)`/g;
    const inlineCodeMatches = [...sanitized.matchAll(inlineCodeRegex)];
    const existingCodeBlocks = new Set();
    
    inlineCodeMatches.forEach(match => {
      existingCodeBlocks.add(match[1]);
    });
    
    // Thêm backticks cho các từ khóa SQL nếu chúng chưa được bao quanh bởi backticks
    sqlKeywords.forEach(pattern => {
      sanitized = sanitized.replace(pattern, (match) => {
        // Kiểm tra xem từ khóa đã nằm trong code block chưa
        if (existingCodeBlocks.has(match)) {
          return match; // Đã nằm trong code block, giữ nguyên
        }
        return '`' + match + '`';
      });
    });
    
    // 3. Đảm bảo các đoạn code block (``` hoặc `) không bị cắt đứt
    // Đếm số lượng backticks (`) trong chuỗi
    const backtickCount = (sanitized.match(/`/g) || []).length;
    // Nếu số lượng backtick lẻ, có thể đã bị cắt giữa chừng
    if (backtickCount % 2 !== 0) {
      // Tìm vị trí backtick cuối cùng
      const lastBacktickIndex = sanitized.lastIndexOf('`');
      if (lastBacktickIndex !== -1) {
        // Loại bỏ backtick cuối cùng để tránh hiển thị lỗi
        sanitized = sanitized.substring(0, lastBacktickIndex) + 
                    sanitized.substring(lastBacktickIndex + 1);
      }
    }
    
    // 4. Đếm số lượng dấu ** để đảm bảo không bị cắt giữa chừng bold text
    const boldMarkerCount = (sanitized.match(/\*\*/g) || []).length;
    if (boldMarkerCount % 2 !== 0) {
      // Tìm vị trí ** cuối cùng
      const lastBoldIndex = sanitized.lastIndexOf('**');
      if (lastBoldIndex !== -1 && lastBoldIndex > sanitized.length - 5) {
        // Loại bỏ ** cuối cùng nếu nó nằm gần cuối chuỗi (có thể bị cắt)
        sanitized = sanitized.substring(0, lastBoldIndex) + 
                    sanitized.substring(lastBoldIndex + 2);
      }
    }
    
    // 5. Xử lý trường hợp nội dung bị lặp lại
    // Tìm kiếm các đoạn văn bản lặp lại liên tiếp (độ dài > 20 ký tự)
    const minRepeatLength = 20;
    for (let i = 0; i < sanitized.length - minRepeatLength * 2; i++) {
      const potentialRepeat = sanitized.substring(i, i + minRepeatLength);
      const nextChunk = sanitized.substring(i + minRepeatLength, i + minRepeatLength * 2);
      if (potentialRepeat === nextChunk) {
        // Phát hiện đoạn lặp, loại bỏ nó
        sanitized = sanitized.substring(0, i + minRepeatLength) + 
                    sanitized.substring(i + minRepeatLength * 2);
        // Sau khi loại bỏ, cần kiểm tra lại từ vị trí hiện tại
        i--;
      }
    }
    
    // 6. Xử lý trường hợp lặp lại dòng hoặc câu
    // Tách nội dung thành các dòng
    const lines = sanitized.split('\n');
    const uniqueLines: string[] = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.length > 10) { // Chỉ kiểm tra các dòng có ý nghĩa (đủ dài)
        // Kiểm tra xem dòng này có giống dòng tiếp theo không
        if (i < lines.length - 1 && line === lines[i + 1].trim()) {
          // Bỏ qua dòng trùng lặp
          continue;
        }
        
        // Kiểm tra xem dòng này có chứa nội dung của dòng tiếp theo không
        if (i < lines.length - 1) {
          const nextLine = lines[i + 1].trim();
          if (nextLine.length > 10 && line.includes(nextLine)) {
            // Dòng hiện tại đã bao gồm dòng tiếp theo, giữ lại dòng hiện tại và bỏ qua dòng tiếp theo
            uniqueLines.push(lines[i]);
            i++; // Bỏ qua dòng tiếp theo
            continue;
          }
        }
      }
      uniqueLines.push(lines[i]);
    }
    
    // 7. Xử lý trường hợp đặc biệt: lặp lại phần cuối của dòng trước ở đầu dòng sau
    for (let i = 0; i < uniqueLines.length - 1; i++) {
      const currentLine = uniqueLines[i].trim();
      const nextLine = uniqueLines[i + 1].trim();
      
      if (currentLine.length > 15 && nextLine.length > 15) {
        // Kiểm tra xem phần cuối của dòng hiện tại có trùng với phần đầu của dòng tiếp theo không
        for (let j = 10; j < Math.min(currentLine.length, nextLine.length); j++) {
          const currentEnd = currentLine.substring(currentLine.length - j);
          const nextStart = nextLine.substring(0, j);
          
          if (currentEnd === nextStart) {
            // Tìm thấy phần trùng lặp, loại bỏ nó khỏi dòng tiếp theo
            uniqueLines[i + 1] = uniqueLines[i + 1].substring(j);
            break;
          }
        }
      }
    }
    
    // 8. Xử lý trường hợp câu bị cắt giữa chừng
    // Tìm các câu kết thúc không hoàn chỉnh
    for (let i = 0; i < uniqueLines.length - 1; i++) {
      const currentLine = uniqueLines[i];
      
      // Nếu dòng hiện tại kết thúc bằng dấu chấm phẩy hoặc dấu phẩy
      // và không phải là phần của một danh sách hoặc mã code
      if (currentLine.trim().endsWith(',') || 
          (currentLine.trim().endsWith(';') && !currentLine.includes('```'))) {
        // Kiểm tra xem dòng tiếp theo có phải là phần tiếp của câu này không
        const nextLine = uniqueLines[i + 1];
        if (nextLine && nextLine.trim().length > 0 && 
            nextLine.trim()[0] === nextLine.trim()[0].toLowerCase() && 
            !nextLine.trim().startsWith('- ') && 
            !nextLine.trim().startsWith('* ')) {
          // Nối hai dòng lại với nhau
          uniqueLines[i] = currentLine + ' ' + uniqueLines[i + 1];
          // Xóa dòng tiếp theo
          uniqueLines.splice(i + 1, 1);
          // Kiểm tra lại dòng hiện tại
          i--;
        }
      }
    }
    
    // 9. Đảm bảo các cặp ngoặc đơn, ngoặc vuông, ngoặc nhọn được đóng đúng
    const brackets = {
      '(': ')',
      '[': ']',
      '{': '}'
    };
    
    Object.entries(brackets).forEach(([open, close]) => {
      const openCount = (sanitized.match(new RegExp(`\\${open}`, 'g')) || []).length;
      const closeCount = (sanitized.match(new RegExp(`\\${close}`, 'g')) || []).length;
      
      if (openCount > closeCount) {
        // Thiếu dấu đóng ngoặc, thêm vào cuối
        uniqueLines[uniqueLines.length - 1] += close.repeat(openCount - closeCount);
      }
    });
    
    return uniqueLines.join('\n');
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header - fixed at top */}
  

      {/* Content area - scrollable */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto" ref={chatContainerRef}>
            <div className="p-4">
              <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((message, index) => (
                  <ChatMessage 
                    key={`message-${message.id}-${index}`} 
                    message={message}
                    isLastMessage={index === messages.length - 1}
                    isTyping={isTyping}
                    relatedQuestions={index === messages.length - 1 ? relatedQuestions : []}
                    onRelatedQuestionClick={handleRelatedQuestionClick}
                  />
                ))}

                {isTyping && (
                  <LoadingMessage elapsedTime={elapsedTime} />
                )}

                <div ref={messagesEndRef} key="messages-end" />
              </div>
            </div>
          </div>

          <div className="border-t p-4 bg-muted/30 backdrop-blur-sm">
            <div className="max-w-3xl mx-auto">
              <div className="relative">
                <Textarea
                  placeholder="Nhập câu hỏi của bạn về cơ sở dữ liệu..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pr-12 min-h-[60px] resize-none shadow-subtle focus-visible:ring-primary"
                  rows={1}
                  spellCheck={false}
                  autoComplete="off"
                  disabled={isSending}
                />
                <Button
                  size="icon"
                  className="absolute right-2 bottom-2 h-8 w-8"
                  onClick={handleSend}
                  disabled={!input.trim() || isSending || isTyping}
                >
                  {isSending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <div className="flex items-center justify-between mt-2">
                <p className="text-xs text-muted-foreground">
                  Nhấn <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Shift</kbd> +{" "}
                  <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Enter</kbd> để xuống dòng
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <SourceModal
        isOpen={!!selectedSource}
        onClose={() => setSelectedSource(null)}
        source={selectedSource ? sourcesData[selectedSource] : null}
      />
    </div>
  )
}
