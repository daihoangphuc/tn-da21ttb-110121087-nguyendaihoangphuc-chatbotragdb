"use client"

import { Button } from "@/components/ui/button"
import { Menu, Database, Moon, Sun, Code, PanelLeftClose, PanelLeft } from "lucide-react"
import { useTheme } from "next-themes"
import { useMobile } from "@/hooks/use-mobile"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { UserDropdown } from "@/components/user-dropdown"

interface HeaderProps {
  onMenuClick?: () => void
  onSqlClick?: () => void
  sqlPanelOpen?: boolean
  onSidebarToggle?: () => void
  isSidebarOpen?: boolean
}

export function Header({ onMenuClick, onSqlClick, sqlPanelOpen, onSidebarToggle, isSidebarOpen }: HeaderProps) {
  const { theme, setTheme } = useTheme()
  const isMobile = useMobile()

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-subtle relative z-50">
      <div className="flex h-16 items-center px-4">
        {isMobile ? (
          <Button variant="ghost" size="icon" onClick={onMenuClick} className="mr-2">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Mở menu</span>
          </Button>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onSidebarToggle}
                  className="mr-2"
                >
                  {isSidebarOpen ? (
                    <PanelLeftClose className="h-5 w-5" />
                  ) : (
                    <PanelLeft className="h-5 w-5" />
                  )}
                  <span className="sr-only">
                    {isSidebarOpen ? "Thu gọn sidebar" : "Mở rộng sidebar"}
                  </span>
                </Button>
              </TooltipTrigger>
              <TooltipContent className="z-[100]">
                <p>{isSidebarOpen ? "Thu gọn sidebar" : "Mở rộng sidebar"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        <div className="flex items-center gap-2 font-semibold">
          <div className="bg-primary/10 p-1.5 rounded-md">
            <Database className="h-5 w-5 text-primary" />
          </div>
          <span>Hệ thống RAG - Cơ sở dữ liệu</span>
          {/* <Badge variant="outline" className="ml-1 font-normal">
            Beta
          </Badge> */}
        </div>
        <div className="ml-auto flex items-center gap-2">
          {!isMobile && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant={sqlPanelOpen ? "secondary" : "outline"}
                    size="sm"
                    onClick={onSqlClick}
                    className="gap-1.5"
                  >
                    <Code className="h-4 w-4" />
                    <span>SQL Playground</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{sqlPanelOpen ? "Đóng" : "Mở"} SQL Playground</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  aria-label="Chuyển đổi chế độ sáng/tối"
                >
                  <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                  <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                  <span className="sr-only">Chuyển đổi chế độ sáng/tối</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Chuyển đổi chế độ sáng/tối</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <UserDropdown />
        </div>
      </div>
    </header>
  )
}
