import type React from "react"
import { Inter } from "next/font/google"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/hooks/useAuth"
import { Toaster } from "@/components/ui/toaster"
import { BrowserExtensionCleaner } from "@/components/browser-extension-cleaner"
import "./globals.css"
import "./markdown.css"

const inter = Inter({ subsets: ["latin", "vietnamese"] })

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <head>
        <title>Hệ thống RAG - Cơ sở dữ liệu</title>
        <meta name="description" content="Hệ thống truy vấn thông tin cơ sở dữ liệu sử dụng RAG" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        {/* Ngăn một số browser extensions can thiệp */}
        <meta name="referrer" content="no-referrer" />
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        {/* Disable some common extensions */}
        <meta name="bis_config" content='{"disabled": true}' />
        <meta name="darkreader" content="disabled" />
      </head>
      <body className={inter.className} suppressHydrationWarning>
        <BrowserExtensionCleaner />
        <AuthProvider>
          <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
            {children}
            <Toaster />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  )
}

export const metadata = {
      generator: 'v0.dev'
    };
