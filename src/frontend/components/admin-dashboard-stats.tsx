"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { adminAPI } from "./admin-api";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import {
  Users,
  FileText,
  MessageSquare,
  MessageCircle,
  Calendar,
  TrendingUp,
  FileIcon,
  FolderOpen,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { vi } from "date-fns/locale";

// Khai báo window.filesStats để TypeScript không báo lỗi
declare global {
  interface Window {
    filesStats?: {
      total_files: number;
      total_size: number;
      file_types: Record<string, number>;
      file_categories: Record<string, number>;
      last_7_days: number;
      last_30_days: number;
    };
  }
}

interface DashboardStats {
  users: {
    total: number;
    active: number;
    banned: number;
    byRole: { admin: number; student: number };
    growth: number;
    recentSignups: Array<{ date: string; count: number }>;
  };
  files: {
    total: number;
    totalSize: number;
    byType: Record<string, number>;
    byCategory: Record<string, number>;
    recentUploads: Array<{ date: string; count: number }>;
    last7Days: number;
    last30Days: number;
  };
  conversations: {
    total: number;
    totalMessages: number;
    avgMessagesPerConv: number;
    byDate: Array<{ date: string; count: number }>;
    messagesByRole: { user: number; assistant: number };
    topUsers: Array<{ email: string; count: number }>;
  };
}

const COLORS = {
  primary: "#3b82f6",
  secondary: "#10b981", 
  warning: "#f59e0b",
  danger: "#ef4444",
  purple: "#8b5cf6",
  pink: "#ec4899",
};

export function AdminDashboardStats() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("7");
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const fetchDashboardStats = async () => {
    setLoading(true);
    setError(null);
    try {
      let usersData: any = { users: [], total_count: 0 };
      let filesData: any = { total_files: 0, files: [] };
      let conversationStats: any = {
        total_conversations: 0,
        total_messages: 0,
        conversations_by_date: [],
        messages_by_role: { user: 0, assistant: 0 },
        top_users: [],
      };

      try {
        usersData = await adminAPI.fetchUsers(1, 100);
      } catch (error: any) {
        console.error("Error fetching users:", error);
        if (error.message?.includes('403') || error.message?.includes('Forbidden') || 
            error.message?.includes('Chỉ admin mới có quyền truy cập')) {
          setError('Bạn không có quyền truy cập trang quản trị. Vui lòng liên hệ quản trị viên để được cấp quyền admin.');
          return;
        }
      }

      try {
        const [files, filesStats] = await Promise.all([
          adminAPI.getFiles(),
          adminAPI.getFilesStats(),
        ]);
        filesData = files;
        if (filesStats) {
          filesData.total_files = filesStats.total_files;
          window.filesStats = filesStats;
        }
      } catch (error: any) {
        console.error("Error fetching files:", error);
        if (error.message?.includes('403') || error.message?.includes('Forbidden')) {
          setError('Bạn không có quyền truy cập trang quản trị. Vui lòng liên hệ quản trị viên để được cấp quyền admin.');
          return;
        }
      }

      try {
        conversationStats = await adminAPI.getConversationStats(
          parseInt(timeRange)
        );
      } catch (error: any) {
        console.error("Error fetching conversation stats:", error);
        if (error.message?.includes('403') || error.message?.includes('Forbidden')) {
          setError('Bạn không có quyền truy cập trang quản trị. Vui lòng liên hệ quản trị viên để được cấp quyền admin.');
          return;
        }
      }

      // Process data
      const now = new Date();
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

      const activeUsers = usersData.users.filter(
        (u: any) => u.last_sign_in_at && new Date(u.last_sign_in_at) > weekAgo
      ).length;

      const bannedUsers = usersData.users.filter(
        (u: any) => u.banned_until
      ).length;

      const usersByRole = usersData.users.reduce(
        (acc: any, user: any) => {
          const role = user.role || "student";
          if (role === "admin") acc.admin++;
          else acc.student++;
          return acc;
        },
        { admin: 0, student: 0 }
      );

      const lastWeekUsers = Math.floor(usersData.total_count * 0.9);
      const growth =
        ((usersData.total_count - lastWeekUsers) / lastWeekUsers) * 100;

      const recentSignups = Array.from({ length: parseInt(timeRange) }, (_, i) => {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        const dateStr = format(date, "yyyy-MM-dd");

        const count = usersData.users.filter((u: any) => {
          const signupDate = format(parseISO(u.created_at), "yyyy-MM-dd");
          return signupDate === dateStr;
        }).length;

        return { date: dateStr, count };
      }).reverse();

      let filesByType: Record<string, number> = {};
      let filesByCategory: Record<string, number> = {};
      let totalSize = 0;

      if (window.filesStats) {
        filesByType = window.filesStats.file_types;
        filesByCategory = window.filesStats.file_categories;
        totalSize = window.filesStats.total_size;
      } else {
        filesByType = filesData.files.reduce((acc: any, file: any) => {
          const ext = file.extension.toLowerCase().replace(".", "");
          acc[ext] = (acc[ext] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);

        filesByCategory = filesData.files.reduce((acc: any, file: any) => {
          const category = file.category || "Chưa phân loại";
          acc[category] = (acc[category] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);

        totalSize = filesData.files.reduce(
          (sum: any, file: any) => sum + file.size,
          0
        );
      }

      const recentUploads = Array.from({ length: parseInt(timeRange) }, (_, i) => {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        const dateStr = format(date, "yyyy-MM-dd");

        let count = 0;
        if (filesData.files.length > 0) {
          count = filesData.files.filter((f: any) => {
            if (!f.upload_date) return false;
            const uploadDate = format(parseISO(f.upload_date), "yyyy-MM-dd");
            return uploadDate === dateStr;
          }).length;
        }

        return { date: dateStr, count };
      }).reverse();

      const recentFilesInfo = window.filesStats
        ? {
            last7Days: window.filesStats.last_7_days,
            last30Days: window.filesStats.last_30_days,
          }
        : { last7Days: 0, last30Days: 0 };

      setStats({
        users: {
          total: usersData.total_count,
          active: activeUsers,
          banned: bannedUsers,
          byRole: usersByRole,
          growth,
          recentSignups,
        },
        files: {
          total: filesData.total_files,
          totalSize,
          byType: filesByType,
          byCategory: filesByCategory,
          recentUploads,
          last7Days: recentFilesInfo.last7Days,
          last30Days: recentFilesInfo.last30Days,
        },
        conversations: {
          total: conversationStats.total_conversations,
          totalMessages: conversationStats.total_messages,
          avgMessagesPerConv:
            conversationStats.total_conversations > 0
              ? Math.round(
                  conversationStats.total_messages /
                    conversationStats.total_conversations
                )
              : 0,
          byDate: conversationStats.conversations_by_date,
          messagesByRole: conversationStats.messages_by_role,
          topUsers: conversationStats.top_users.map((u: any) => ({
            email: u.email,
            count: u.conversation_count,
          })),
        },
      });
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
      toast({
        title: "Lỗi",
        description: "Không thể tải dữ liệu thống kê",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardStats();
  }, [timeRange]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    try {
      return format(parseISO(dateStr), "dd/MM", { locale: vi });
    } catch {
      return dateStr;
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('vi-VN').format(num);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-6 w-20" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="text-center max-w-md">
          <div className="mb-4">
            <Users className="h-16 w-16 text-red-500 mx-auto" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Không có quyền truy cập
          </h2>
          <p className="text-gray-600 mb-4">
            {error}
          </p>
          <div className="bg-blue-50 border-l-4 border-blue-400 p-4 text-left">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <strong>Lưu ý:</strong> Để truy cập trang quản trị, bạn cần:
                </p>
                <ul className="mt-2 text-sm text-blue-600 list-disc list-inside">
                  <li>Có tài khoản với vai trò admin</li>
                  <li>Được quản trị viên hệ thống cấp quyền</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  // Custom Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border rounded-lg p-3 shadow-md">
          <p className="font-medium">{formatDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatNumber(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Prepare data for charts
  const fileTypeData = Object.entries(stats.files.byType)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([type, count]) => ({
      name: type.toUpperCase(),
      value: count,
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Thống kê tổng quan hệ thống</h1>
          <p className="text-muted-foreground text-sm">
            Dữ liệu thống kê trong {timeRange} ngày qua
          </p>
        </div>
        <Select value={timeRange} onValueChange={setTimeRange}>
          <SelectTrigger className="w-[180px]">
            <Calendar className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">7 ngày qua</SelectItem>
            <SelectItem value="30">30 ngày qua</SelectItem>
            <SelectItem value="90">90 ngày qua</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Main Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Tổng người dùng
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.users.total)}</div>
            <p className="text-xs text-muted-foreground">
              {stats.users.active} người dùng hoạt động
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Tổng tài liệu
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.files.total)}</div>
            <p className="text-xs text-muted-foreground">
              Dung lượng: {formatBytes(stats.files.totalSize)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Tổng hội thoại
            </CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.conversations.total)}</div>
            <p className="text-xs text-muted-foreground">
              Trung bình {stats.conversations.avgMessagesPerConv} tin nhắn/hội thoại
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Tổng tin nhắn
            </CardTitle>
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(stats.conversations.totalMessages)}</div>
            <p className="text-xs text-muted-foreground">
              Người dùng: {formatNumber(stats.conversations.messagesByRole.user)} | 
              AI: {formatNumber(stats.conversations.messagesByRole.assistant)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* File Statistics */}
        <Card>
          <CardHeader>
            <CardTitle>Thống kê tài liệu</CardTitle>
            <CardDescription>
              Phân loại tài liệu theo định dạng
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={fileTypeData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(value: any) => [formatNumber(value), "Số lượng"]}
                  labelStyle={{ color: '#000' }}
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--background))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Bar 
                  dataKey="value" 
                  fill={COLORS.primary}
                  radius={[4, 4, 0, 0]}
                  animationBegin={0}
                  animationDuration={1500}
                  animationEasing="ease-out"
                >
                  {fileTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % Object.values(COLORS).length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Conversation Statistics */}
        <Card>
          <CardHeader>
            <CardTitle>Thống kê hội thoại</CardTitle>
            <CardDescription>
              Số lượng hội thoại theo ngày
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={stats.conversations.byDate}>
                <defs>
                  <linearGradient id="colorConv" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.8}/>
                    <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tickFormatter={formatDate} />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={COLORS.primary}
                  fillOpacity={1}
                  fill="url(#colorConv)"
                  name="Số hội thoại"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Top Active Users */}
      <Card>
        <CardHeader>
          <CardTitle>Top người dùng tích cực</CardTitle>
          <CardDescription>5 người dùng có nhiều hội thoại nhất</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {stats.conversations.topUsers.slice(0, 5).map((user, index) => (
              <div key={user.email} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>
                  <span className="text-sm truncate max-w-[200px]">{user.email}</span>
                </div>
                <span className="text-sm font-medium">{user.count} hội thoại</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 