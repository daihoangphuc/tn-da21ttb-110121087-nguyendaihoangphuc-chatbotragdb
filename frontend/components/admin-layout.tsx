"use client";

import { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { 
  Users, 
  Files, 
  Settings, 
  LogOut,
  Home,
  Shield,
  Menu,
  X,
  ChevronRight
} from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface AdminLayoutProps {
  children: React.ReactNode;
}

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  description?: string;
}

const sidebarItems: SidebarItem[] = [
  {
    id: "users",
    label: "Quản lý người dùng",
    icon: Users,
    href: "/admin",
    description: "Quản lý tài khoản và quyền người dùng"
  },
  {
    id: "files",
    label: "Quản lý tài liệu",
    icon: Files,
    href: "/admin/files",
    description: "Upload và quản lý tài liệu hệ thống"
  },
  {
    id: "settings",
    label: "Cài đặt hệ thống",
    icon: Settings,
    href: "/admin/settings",
    description: "Cấu hình và cài đặt hệ thống"
  }
];

export function AdminLayout({ children }: AdminLayoutProps) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [currentPath, setCurrentPath] = useState("/admin");

  // Update current path based on pathname
  useEffect(() => {
    setCurrentPath(pathname);
  }, [pathname]);

  const handleNavigation = (href: string) => {
    router.push(href);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className={cn(
        "fixed left-0 top-0 h-full bg-white border-r border-gray-200 shadow-lg transition-all duration-300 z-50",
        sidebarOpen ? "w-80" : "w-16"
      )}>
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          {sidebarOpen ? (
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <Shield className="h-6 w-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">Admin Panel</h1>
                <p className="text-xs text-gray-500">Quản trị hệ thống</p>
              </div>
            </div>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="p-1 bg-red-100 rounded-lg mx-auto">
                    <Shield className="h-5 w-5 text-red-600" />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Admin Panel</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="h-8 w-8 p-0"
          >
            {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>

        {/* User Info */}
        {sidebarOpen && (
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user?.email}
                </p>
                <p className="text-xs text-gray-500">Administrator</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {sidebarItems.map((item) => {
            const isActive = currentPath === item.href;
            const Icon = item.icon;
            
            return sidebarOpen ? (
              <button
                key={item.id}
                onClick={() => handleNavigation(item.href)}
                className={cn(
                  "w-full flex items-center px-3 py-2 rounded-lg transition-all duration-200",
                  isActive 
                    ? "bg-blue-50 text-blue-700 border border-blue-200" 
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                )}
              >
                <Icon className={cn(
                  "h-5 w-5 flex-shrink-0",
                  isActive ? "text-blue-600" : "text-gray-500"
                )} />
                <span className="ml-3 text-sm font-medium">{item.label}</span>
                {isActive && <ChevronRight className="h-4 w-4 ml-auto" />}
              </button>
            ) : (
              <TooltipProvider key={item.id}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => handleNavigation(item.href)}
                      className={cn(
                        "w-full flex items-center justify-center p-2 rounded-lg transition-all duration-200",
                        isActive 
                          ? "bg-blue-50 text-blue-700 border border-blue-200" 
                          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                      )}
                    >
                      <Icon className={cn(
                        "h-5 w-5",
                        isActive ? "text-blue-600" : "text-gray-500"
                      )} />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.label}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-gray-200 space-y-2">
          {sidebarOpen ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.location.href = "/?student=true"}
                className="w-full flex items-center gap-2"
              >
                <Home className="h-4 w-4" />
                Chế độ Student
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="w-full flex items-center gap-2"
              >
                <LogOut className="h-4 w-4" />
                Đăng xuất
              </Button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.location.href = "/?student=true"}
                      className="w-full p-2 flex justify-center"
                    >
                      <Home className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Chế độ Student</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={logout}
                      className="w-full p-2 flex justify-center"
                    >
                      <LogOut className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Đăng xuất</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className={cn(
        "flex-1 transition-all duration-300",
        sidebarOpen ? "ml-80" : "ml-16"
      )}>
        {/* Top Bar */}
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {sidebarItems.find(item => item.href === currentPath)?.label || "Dashboard"}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {sidebarItems.find(item => item.href === currentPath)?.description || "Quản lý hệ thống"}
              </p>
            </div>
            <div className="text-sm text-gray-500">
              {new Date().toLocaleDateString("vi-VN", {
                weekday: "long",
                year: "numeric",
                month: "long",
                day: "numeric"
              })}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
} 