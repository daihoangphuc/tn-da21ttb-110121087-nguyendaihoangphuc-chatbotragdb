"use client"

import { Button } from "@/components/ui/button"
import { toast } from "@/components/ui/toast-wrapper"

export function ToastExample() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <h2 className="text-2xl font-bold">Toast Examples</h2>
      
      <div className="flex flex-wrap gap-4">
        <Button
          onClick={() => {
            toast.success({
              description: "Thao tác thành công!",
            })
          }}
        >
          Success Toast
        </Button>

        <Button
          variant="destructive"
          onClick={() => {
            toast.error({
              description: "Đã xảy ra lỗi. Vui lòng thử lại sau.",
            })
          }}
        >
          Error Toast
        </Button>

        <Button
          variant="warning"
          onClick={() => {
            toast.warning({
              description: "Cảnh báo! Bạn cần chú ý điều này.",
            })
          }}
        >
          Warning Toast
        </Button>

        <Button
          variant="outline"
          onClick={() => {
            toast.info({
              description: "Đây là một thông báo thông tin.",
            })
          }}
        >
          Info Toast
        </Button>

        <Button
          variant="secondary"
          onClick={() => {
            toast.success({
              title: "Tiêu đề tùy chỉnh",
              description: "Bạn có thể tùy chỉnh tiêu đề và thời gian hiển thị.",
              duration: 10000, // 10 seconds
            })
          }}
        >
          Custom Duration Toast
        </Button>
      </div>
    </div>
  )
} 