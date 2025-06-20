"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-background group-[.toaster]:text-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg group-[.toaster]:rounded-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton:
            "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground group-[.toast]:rounded-md",
          cancelButton:
            "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground group-[.toast]:rounded-md",
          success: 
            "group-[.toast]:bg-green-500 group-[.toast]:text-white group-[.toast]:border-green-500",
          error: 
            "group-[.toast]:bg-red-500 group-[.toast]:text-white group-[.toast]:border-red-500",
          warning: 
            "group-[.toast]:bg-yellow-500 group-[.toast]:text-white group-[.toast]:border-yellow-500",
          info: 
            "group-[.toast]:bg-blue-500 group-[.toast]:text-white group-[.toast]:border-blue-500",
        },
        duration: 5000,
      }}
      {...props}
    />
  )
}

export { Toaster }
