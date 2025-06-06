"use client"

import { ToastExample } from "@/components/toast-example"

export default function ToastDemoPage() {
  return (
    <div className="container mx-auto py-10">
      <h1 className="text-3xl font-bold mb-6">Demo Hệ Thống Toast</h1>
      <p className="mb-8 text-gray-600">
        Trang này giới thiệu hệ thống toast đã được cải tiến với màu sắc nhất quán và thiết kế UI/UX tốt hơn.
      </p>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <ToastExample />
      </div>
      
      <div className="mt-8 prose dark:prose-invert max-w-none">
        <h2>Hướng dẫn sử dụng</h2>
        <p>
          Hệ thống toast đã được cải tiến để đảm bảo tính nhất quán và cải thiện trải nghiệm người dùng. 
          Toast hiện có 4 loại với màu sắc nhất quán:
        </p>
        
        <ul>
          <li><strong className="text-green-500">Success (Thành công)</strong>: Màu xanh lá</li>
          <li><strong className="text-red-500">Error (Lỗi)</strong>: Màu đỏ</li>
          <li><strong className="text-yellow-500">Warning (Cảnh báo)</strong>: Màu vàng</li>
          <li><strong>Info (Thông tin)</strong>: Màu mặc định</li>
        </ul>
        
        <h3>Cách sử dụng</h3>
        <p>Thay vì sử dụng trực tiếp <code>import {"{ toast }"} from "@/components/ui/use-toast"</code>, hãy sử dụng wrapper mới:</p>
        
        <pre className="bg-gray-100 dark:bg-gray-900 p-4 rounded-md overflow-auto">
          <code>{`import { toast } from "@/components/ui/toast-wrapper"

// Hiển thị toast thành công
toast.success({
  description: "Thao tác thành công!"
})

// Hiển thị toast lỗi
toast.error({
  description: "Đã xảy ra lỗi. Vui lòng thử lại sau."
})`}</code>
        </pre>
        
        <p>Xem thêm hướng dẫn chi tiết tại <code>frontend/toast-guide.md</code></p>
      </div>
    </div>
  )
} 