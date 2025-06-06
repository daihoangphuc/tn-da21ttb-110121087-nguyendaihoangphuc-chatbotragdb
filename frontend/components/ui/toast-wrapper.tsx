"use client"

import { toast as showToast } from "@/components/ui/use-toast"
import { ToastIcon } from "@/components/ui/toast"

type ToastType = "success" | "error" | "warning" | "info"

interface ToastOptions {
  title?: string
  description: string
  action?: React.ReactNode
  duration?: number
}

/**
 * Toast wrapper to ensure consistent styling and usage throughout the application
 * - success: green
 * - error: red
 * - warning: yellow
 * - info: default
 */
export const toast = {
  success: (options: ToastOptions) => {
    return showToast({
      variant: "success",
      title: options.title || "Thành công",
      description: (
        <div className="flex items-start gap-2">
          <ToastIcon variant="success" />
          <div>{options.description}</div>
        </div>
      ),
      action: options.action,
      duration: options.duration || 5000,
    })
  },
  
  error: (options: ToastOptions) => {
    return showToast({
      variant: "destructive",
      title: options.title || "Lỗi",
      description: (
        <div className="flex items-start gap-2">
          <ToastIcon variant="destructive" />
          <div>{options.description}</div>
        </div>
      ),
      action: options.action,
      duration: options.duration || 5000,
    })
  },
  
  warning: (options: ToastOptions) => {
    return showToast({
      variant: "warning",
      title: options.title || "Cảnh báo",
      description: (
        <div className="flex items-start gap-2">
          <ToastIcon variant="warning" />
          <div>{options.description}</div>
        </div>
      ),
      action: options.action,
      duration: options.duration || 5000,
    })
  },
  
  info: (options: ToastOptions) => {
    return showToast({
      variant: "default",
      title: options.title || "Thông báo",
      description: options.description,
      action: options.action,
      duration: options.duration || 5000,
    })
  },
} 