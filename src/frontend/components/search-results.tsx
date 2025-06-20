"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileIcon, MessageSquare } from "lucide-react"

export function SearchResults() {
  // Mẫu dữ liệu kết quả tìm kiếm
  const results = [
    {
      id: "1",
      title: "SQL JOIN là gì?",
      content:
        "SQL JOIN là một mệnh đề được sử dụng để kết hợp các hàng từ hai hoặc nhiều bảng, dựa trên một cột liên quan giữa chúng. JOIN là một trong những tính năng quan trọng nhất của SQL, cho phép bạn truy vấn dữ liệu từ nhiều bảng trong một câu lệnh SELECT.",
      source: "SQL_Basics.pdf",
      page: "12",
      relevance: 0.95,
    },
    {
      id: "2",
      title: "Các loại JOIN trong SQL",
      content:
        "Có nhiều loại JOIN trong SQL: INNER JOIN, LEFT JOIN, RIGHT JOIN, và FULL JOIN. INNER JOIN trả về các hàng khi có ít nhất một kết quả khớp trong cả hai bảng. LEFT JOIN trả về tất cả các hàng từ bảng bên trái và các hàng khớp từ bảng bên phải.",
      source: "SQL_Basics.pdf",
      page: "13",
      relevance: 0.92,
    },
    {
      id: "3",
      title: "Cú pháp JOIN",
      content:
        "Cú pháp cơ bản của JOIN là: SELECT columns FROM table1 JOIN table2 ON table1.column = table2.column. Bạn có thể chỉ định loại JOIN bằng cách thêm từ khóa INNER, LEFT, RIGHT, hoặc FULL trước JOIN.",
      source: "SQL_Basics.pdf",
      page: "14",
      relevance: 0.88,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Kết quả tìm kiếm</h3>
        <span className="text-sm text-muted-foreground">Tìm thấy {results.length} kết quả</span>
      </div>

      {results.map((result) => (
        <Card key={result.id} className="overflow-hidden">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="mt-1 rounded-md bg-primary/10 p-2">
                <FileIcon className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">{result.title}</h4>
                  <Badge variant="outline" className="ml-2">
                    {Math.round(result.relevance * 100)}%
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground line-clamp-3">{result.content}</p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    {result.source} • Trang {result.page}
                  </span>
                  <Button size="sm" variant="ghost" className="h-8 gap-1">
                    <MessageSquare className="h-3 w-3" />
                    <span>Hỏi về kết quả này</span>
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
