"use client";

import { SimpleLearningDashboard } from "@/components/simple-learning-dashboard";
import { useAuth } from "@/hooks/useAuth";
import { Header } from "@/components/header";
import { AuthGuard } from "@/components/auth-guard";
import { useState, useEffect } from "react";

export default function LearningPage() {
  const { user, loading } = useAuth();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  
  if (!mounted || loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50" suppressHydrationWarning={true}>
          <Header 
            onMenuClick={() => {}}
            onSqlClick={() => {}}
            sqlPanelOpen={false}
            onSidebarToggle={() => {}}
            isSidebarOpen={false}
            onSearch={() => {}}
            onSelectConversation={() => {}}
          />
          <div className="flex items-center justify-center min-h-[60vh]" suppressHydrationWarning={true}>
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" suppressHydrationWarning={true}></div>
          </div>
        </div>
      </AuthGuard>
    );
  }
  
  if (!user) {
    return (
      <AuthGuard>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50" suppressHydrationWarning={true}>
          <Header 
            onMenuClick={() => {}}
            onSqlClick={() => {}}
            sqlPanelOpen={false}
            onSidebarToggle={() => {}}
            isSidebarOpen={false}
            onSearch={() => {}}
            onSelectConversation={() => {}}
          />
          <div className="text-center py-12" suppressHydrationWarning={true}>
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Vui lòng đăng nhập để xem dashboard học tập
            </h1>
            <p className="text-gray-600">
              Bạn cần đăng nhập để truy cập tính năng phân tích học tập cá nhân.
            </p>
          </div>
        </div>
      </AuthGuard>
    );
  }
  
  return (
    <AuthGuard>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50" suppressHydrationWarning={true}>
        <Header 
          onMenuClick={() => {}}
          onSqlClick={() => {}}
          sqlPanelOpen={false}
          onSidebarToggle={() => {}}
          isSidebarOpen={false}
          onSearch={() => {}}
          onSelectConversation={() => {}}
        />
        <main className="container mx-auto py-8 px-4" suppressHydrationWarning={true}>
          {/* Header Section with Back Button */}
          <div className="mb-8" suppressHydrationWarning={true}>
            <div className="flex items-center justify-between" suppressHydrationWarning={true}>
              <div className="flex items-center space-x-4" suppressHydrationWarning={true}>
                <button
                  onClick={() => window.location.href = '/'}
                  className="flex items-center space-x-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 hover:text-gray-800 transition-colors duration-200 shadow-sm"
                  suppressHydrationWarning={true}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  <span>Quay về trang chủ</span>
                </button>
                <div className="h-6 w-px bg-gray-300" suppressHydrationWarning={true}></div>
                <div suppressHydrationWarning={true}>
                  <h1 className="text-3xl font-bold text-gray-900 tracking-tight">
                    Dashboard Phân Tích Học Tập
                  </h1>
                  <p className="text-gray-600 mt-1">
                    Theo dõi tiến bộ học tập và phát triển kỹ năng tư duy về Cơ sở dữ liệu
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <SimpleLearningDashboard />
        </main>
      </div>
    </AuthGuard>
  );
} 