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
import { Badge } from "@/components/ui/badge";
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
  ComposedChart,
  RadialBarChart,
  RadialBar,
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
  Activity,
  Database,
  Clock,
  User,
  Shield,
  AlertTriangle,
  Zap,
  Star,
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
      upload_trend: Record<string, number>;
      avg_file_size: number;
    };
    systemStats?: any;
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
    uploadTrend: Record<string, number>;
    avgFileSize: number;
  };
  conversations: {
    total: number;
    totalMessages: number;
    avgMessagesPerConv: number;
    byDate: Array<{ date: string; count: number }>;
    messagesByRole: { user: number; assistant: number };
    topUsers: Array<{ email: string; count: number }>;
  };
  system?: {
    overview: any;
    user_metrics: any;
    activity_metrics: any;
    storage_metrics: any;
  };
}

const COLORS = {
  primary: "#3b82f6",
  secondary: "#10b981", 
  warning: "#f59e0b",
  danger: "#ef4444",
  purple: "#8b5cf6",
  pink: "#ec4899",
  indigo: "#6366f1",
  teal: "#14b8a6",
  orange: "#f97316",
  emerald: "#059669",
};

const CHART_COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", 
  "#ec4899", "#6366f1", "#14b8a6", "#f97316", "#059669"
];

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
        // Fetch dữ liệu song song
        const [users, files, filesStatsData, convStats] = await Promise.all([
          adminAPI.fetchUsers(1, 100),
          adminAPI.getFiles(),
          adminAPI.getFilesStats(),
          adminAPI.getConversationStats(parseInt(timeRange)),
        ]);

        usersData = users;
        filesData = files;
        conversationStats = convStats;

        if (filesStatsData) {
          filesData.total_files = filesStatsData.total_files;
          window.filesStats = filesStatsData;
        }

      } catch (error: any) {
        console.error("Error fetching dashboard data:", error);
        if (error.message?.includes('403') || error.message?.includes('Forbidden') || 
            error.message?.includes('Chỉ admin mới có quyền truy cập')) {
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
      let uploadTrend: Record<string, number> = {};
      let avgFileSize = 0;

      if (window.filesStats) {
        filesByType = window.filesStats.file_types;
        filesByCategory = window.filesStats.file_categories;
        totalSize = window.filesStats.total_size;
        uploadTrend = window.filesStats.upload_trend || {};
        avgFileSize = window.filesStats.avg_file_size || 0;
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
        if (uploadTrend[dateStr]) {
          count = uploadTrend[dateStr];
        } else if (filesData.files.length > 0) {
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
          uploadTrend,
          avgFileSize,
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
    .slice(0, 6)
    .map(([type, count], index) => ({
      name: type.toUpperCase(),
      value: count,
      fill: CHART_COLORS[index % CHART_COLORS.length],
    }));

  const fileCategoryData = Object.entries(stats.files.byCategory)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .map(([category, count], index) => ({
      name: category,
      value: count,
      fill: CHART_COLORS[index % CHART_COLORS.length],
    }));

  const userRoleData = [
    { name: "Student", value: stats.users.byRole.student, fill: COLORS.primary },
    { name: "Admin", value: stats.users.byRole.admin, fill: COLORS.warning },
  ];

  // Combined data for activity chart
  const activityData = stats.conversations.byDate.map((conv, index) => ({
    date: conv.date,
    conversations: conv.count,
    users: stats.users.recentSignups[index]?.count || 0,
    files: stats.files.recentUploads[index]?.count || 0,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Dashboard Quản Trị Hệ Thống
          </h1>
          <p className="text-muted-foreground">
            Thống kê tổng quan và phân tích dữ liệu trong {timeRange} ngày qua
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
        <Card className="border-blue-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-blue-700">
              Tổng người dùng
            </CardTitle>
            <Users className="h-5 w-5 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-800">{formatNumber(stats.users.total)}</div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="secondary" className="text-xs">
                <Activity className="w-3 h-3 mr-1" />
                {stats.users.active} hoạt động
              </Badge>
              {stats.users.banned > 0 && (
                <Badge variant="destructive" className="text-xs">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  {stats.users.banned} bị cấm
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-green-700">
              Tài liệu hệ thống
            </CardTitle>
            <FileText className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-800">{formatNumber(stats.files.total)}</div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs border-green-300 text-green-700">
                <Database className="w-3 h-3 mr-1" />
                {formatBytes(stats.files.totalSize)}
              </Badge>
              {/* <Badge variant="secondary" className="text-xs">
                <Clock className="w-3 h-3 mr-1" />
                {stats.files.last7Days} tuần này
              </Badge> */}
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-purple-700">
              Hội thoại
            </CardTitle>
            <MessageSquare className="h-5 w-5 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-800">{formatNumber(stats.conversations.total)}</div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-xs border-purple-300 text-purple-700">
                <Zap className="w-3 h-3 mr-1" />
                TB {stats.conversations.avgMessagesPerConv} tin nhắn
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-orange-200">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-orange-700">
              Tin nhắn tổng
            </CardTitle>
            <MessageCircle className="h-5 w-5 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-800">{formatNumber(stats.conversations.totalMessages)}</div>
            <div className="flex items-center gap-2 mt-1">
              {/* <Badge variant="outline" className="text-xs border-orange-300 text-orange-700">
                <User className="w-3 h-3 mr-1" />
                {formatNumber(stats.conversations.messagesByRole.user)}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                <Star className="w-3 h-3 mr-1" />
                {formatNumber(stats.conversations.messagesByRole.assistant)} AI
              </Badge> */}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 gap-4">
        {/* Activity Overview */}
        <Card className="lg:col-span-2 xl:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              Tổng quan hoạt động hệ thống
            </CardTitle>
            <CardDescription>
              Thống kê hoạt động theo thời gian (hội thoại, người dùng mới, files upload)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <ComposedChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  tick={{ fontSize: 12 }}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Bar dataKey="conversations" fill={COLORS.primary} name="Hội thoại" radius={[2, 2, 0, 0]} />
                <Line 
                  type="monotone" 
                  dataKey="users" 
                  stroke={COLORS.warning} 
                  strokeWidth={3}
                  name="Người dùng mới"
                  dot={{ fill: COLORS.warning, strokeWidth: 2, r: 4 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="files" 
                  stroke={COLORS.secondary} 
                  strokeWidth={3}
                  name="Files upload"
                  dot={{ fill: COLORS.secondary, strokeWidth: 2, r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* User Role Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-purple-600" />
              Phân bố vai trò
            </CardTitle>
            <CardDescription>
              Tỷ lệ admin và student trong hệ thống
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RadialBarChart data={userRoleData} innerRadius="30%" outerRadius="90%">
                <RadialBar 
                  dataKey="value" 
                  cornerRadius={10} 
                  label={{ position: 'insideStart', fill: '#fff', fontSize: 12 }}
                />
                <Tooltip 
                  formatter={(value: number) => [formatNumber(value), "Người dùng"]}
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--background))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Legend />
              </RadialBarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* File Type Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileIcon className="h-5 w-5 text-green-600" />
              Phân loại file
            </CardTitle>
            <CardDescription>
              Thống kê theo định dạng file
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={fileTypeData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {fileTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => [formatNumber(value), "Files"]} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* File Categories */}
        {/* <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderOpen className="h-5 w-5 text-indigo-600" />
              Danh mục tài liệu
            </CardTitle>
            <CardDescription>
              Phân loại theo chủ đề
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={fileCategoryData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 10 }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  formatter={(value: number) => [formatNumber(value), "Files"]}
                  contentStyle={{ 
                    backgroundColor: 'hsl(var(--background))', 
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px'
                  }}
                />
                <Bar 
                  dataKey="value" 
                  radius={[4, 4, 0, 0]}
                  fill={COLORS.indigo}
                >
                  {fileCategoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card> */}
      </div>

      {/* Top Active Users */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-5 w-5 text-yellow-600" />
            Top người dùng tích cực nhất
          </CardTitle>
          <CardDescription>Xếp hạng theo số lượng hội thoại</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {stats.conversations.topUsers.slice(0, 5).map((user, index) => (
              <div key={user.email} className="flex flex-col items-center p-4 bg-blue-50 rounded-lg border">
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-blue-500 text-white font-bold text-lg mb-2">
                  #{index + 1}
                </div>
                <span className="text-sm font-medium text-center truncate max-w-full" title={user.email}>
                  {user.email}
                </span>
                <Badge variant="outline" className="mt-2 text-xs">
                  {user.count} hội thoại
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 