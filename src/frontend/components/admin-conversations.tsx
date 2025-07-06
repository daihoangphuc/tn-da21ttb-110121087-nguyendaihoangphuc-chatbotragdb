"use client";

import React from "react";
import { useState, useEffect } from "react";
import { adminAPI, AdminConversation, AdminMessage, AdminConversationStats } from "./admin-api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { useToast } from "@/hooks/use-toast";
import {
  MessageSquare,
  Search,
  Trash2,
  Eye,
  Calendar,
  User,
  Clock,
  TrendingUp,
  MessageCircle,
  Users,
  BarChart3,
  Bot,
  UserIcon,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  X
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { formatVietnameseDate } from "@/lib/utils";
import { adminConversationsCache } from "@/lib/admin-conversations-cache";
import { Badge } from "@/components/ui/badge";
import { ResponsiveContainer, PieChart, Pie, Tooltip as RechartsTooltip, Legend, BarChart, XAxis, YAxis, Bar } from "recharts";

export function AdminConversations() {
  const [allConversations, setAllConversations] = useState<AdminConversation[]>([]);
  const [filteredConversations, setFilteredConversations] = useState<AdminConversation[]>([]);
  const [displayedConversations, setDisplayedConversations] = useState<AdminConversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<AdminConversation | null>(null);
  const [messages, setMessages] = useState<AdminMessage[]>([]);
  const [stats, setStats] = useState<AdminConversationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true); // Thêm state cho lần tải đầu tiên

  const [showMessageDialog, setShowMessageDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [dateFilter, setDateFilter] = useState({ from: "", to: "" });
  const { toast } = useToast();

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [perPage] = useState(20);

  // Load toàn bộ dữ liệu khi component mount
  useEffect(() => {
    const loadInitialData = async () => {
      // 1. Tải dữ liệu thống kê trước và đợi hoàn thành.
      // API này thường nhanh và sẽ hiển thị ngay lập tức.
      await fetchStats();

      // 2. Sau khi có thống kê, bắt đầu tải danh sách hội thoại ngầm.
      // Thao tác này sẽ chạy nền và điền vào cache.
      loadConversationsWithCache();
    };

    loadInitialData();
  }, []);

  // Filter local khi searchTerm hoặc dateFilter thay đổi
  useEffect(() => {
    filterConversations();
  }, [allConversations, searchTerm, dateFilter]);

  // Pagination local
  useEffect(() => {
    paginateConversations();
  }, [filteredConversations, currentPage]);

  const loadConversationsWithCache = async () => {
    // Không đặt trạng thái loading chung ở đây để tránh làm mờ toàn bộ giao diện.
    // Trạng thái `initialLoading` là đủ để hiển thị skeleton trong tab danh sách.
    try {
      const cachedData = adminConversationsCache.getCachedData();
      if (cachedData) {
        setAllConversations(cachedData);
        setInitialLoading(false); // Dữ liệu đã có từ cache, kết thúc tải.
        return;
      }

      // Nếu không có cache, fetch từ API. `initialLoading` vẫn là true.
      const data = await adminConversationsCache.getConversations(fetchAllConversationsFromAPI);
      setAllConversations(data);
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách hội thoại",
        variant: "destructive"
      });
    } finally {
      // Dù thành công hay thất bại, quá trình tải ban đầu đã kết thúc.
      setInitialLoading(false);
    }
  };

  const fetchAllConversationsFromAPI = async (): Promise<AdminConversation[]> => {
    let allConversationsData: AdminConversation[] = [];
    let currentPageLoad = 1;
    let hasMoreData = true;

    while (hasMoreData) {
      const params: any = {
        page: currentPageLoad,
        per_page: 100 // Giới hạn tối đa của backend
      };

      const response = await adminAPI.fetchConversations(params);
      allConversationsData = [...allConversationsData, ...response.conversations];

      // Kiểm tra xem còn trang nào không
      if (response.conversations.length < 100 || currentPageLoad >= response.total_pages) {
        hasMoreData = false;
      } else {
        currentPageLoad++;
      }
    }

    // Deduplicate dữ liệu dựa trên conversation_id
    const uniqueConversations = allConversationsData.filter((conv, index, arr) =>
      arr.findIndex(c => c.conversation_id === conv.conversation_id) === index
    );

    console.log('Data loaded:', {
      total: allConversationsData.length,
      unique: uniqueConversations.length,
      duplicates: allConversationsData.length - uniqueConversations.length
    });

    return uniqueConversations;
  };

  const fetchAllConversations = async () => {
    // Deprecated - sử dụng loadConversationsWithCache thay thế
    await loadConversationsWithCache();
  };

  const filterConversations = () => {
    let filtered = [...allConversations];

    // Kiểm tra duplicates trong allConversations
    const duplicateIds = allConversations
      .map(conv => conv.conversation_id)
      .filter((id, index, arr) => arr.indexOf(id) !== index);

    if (duplicateIds.length > 0) {
      console.warn('Found duplicate conversation IDs:', duplicateIds);
    }

    // Filter theo search term
    if (searchTerm.trim()) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(conv =>
        conv.user_email.toLowerCase().includes(searchLower) ||
        conv.first_message.toLowerCase().includes(searchLower)
      );
    }

    // Filter theo date range - IMPROVED LOGIC
    if (dateFilter.from || dateFilter.to) {
      filtered = filtered.filter(conv => {
        // Parse conversation date (có thể có timezone)
        const convDate = new Date(conv.last_updated);

        // Nếu date không hợp lệ, bỏ qua
        if (isNaN(convDate.getTime())) {
          console.warn('Invalid date:', conv.last_updated);
          return true; // Giữ lại nếu không parse được
        }

        // Chuyển về local date (YYYY-MM-DD) để so sánh
        const convDateStr = convDate.toLocaleDateString('en-CA'); // Format: YYYY-MM-DD

        // Kiểm tra range
        if (dateFilter.from && convDateStr < dateFilter.from) {
          return false;
        }

        if (dateFilter.to && convDateStr > dateFilter.to) {
          return false;
        }

        return true;
      });
    }

    // Kiểm tra duplicates trong filtered data
    const filteredDuplicates = filtered
      .map(conv => conv.conversation_id)
      .filter((id, index, arr) => arr.indexOf(id) !== index);

    if (filteredDuplicates.length > 0) {
      console.warn('Found duplicate conversation IDs in filtered data:', filteredDuplicates);
      // Deduplicate filtered data as safety measure
      filtered = filtered.filter((conv, index, arr) =>
        arr.findIndex(c => c.conversation_id === conv.conversation_id) === index
      );
    }

    console.log('Filter result:', {
      original: allConversations.length,
      filtered: filtered.length,
      searchTerm,
      dateFilter,
      duplicatesFound: duplicateIds.length > 0 || filteredDuplicates.length > 0
    });

    setFilteredConversations(filtered);
    setCurrentPage(1); // Reset về trang đầu khi filter
  };

  const paginateConversations = () => {
    const startIndex = (currentPage - 1) * perPage;
    const endIndex = startIndex + perPage;
    const paginated = filteredConversations.slice(startIndex, endIndex);

    setDisplayedConversations(paginated);
    setTotalPages(Math.ceil(filteredConversations.length / perPage));
  };

  const fetchStats = async () => {
    try {
      const response = await adminAPI.getConversationStats(7);
      setStats(response);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const handleFilter = () => {
    // Validation date range
    if (dateFilter.from && dateFilter.to) {
      const fromDate = new Date(dateFilter.from);
      const toDate = new Date(dateFilter.to);

      if (fromDate > toDate) {
        toast({
          title: "Lỗi",
          description: "Ngày bắt đầu không thể lớn hơn ngày kết thúc",
          variant: "destructive"
        });
        return;
      }
    }

    // Debug info
    console.log('Filter applied:', {
      searchTerm,
      dateFilter,
      totalConversations: allConversations.length
    });

    // Filter sẽ tự động chạy qua useEffect
    filterConversations();
  };

  const handleClearFilter = () => {
    setSearchTerm("");
    setDateFilter({ from: "", to: "" });
    setCurrentPage(1);

    console.log('Filter cleared');
  };

  const handleViewMessages = async (conversation: AdminConversation) => {
    setSelectedConversation(conversation);
    setShowMessageDialog(true);

    try {
      const response = await adminAPI.getConversationMessages(conversation.conversation_id);
      setMessages(response.messages);
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể tải tin nhắn",
        variant: "destructive"
      });
    }
  };

  const handleDeleteConversation = async () => {
    if (!conversationToDelete) return;

    try {
      setLoading(true);
      await adminAPI.deleteConversation(conversationToDelete);

      // Cập nhật cache
      adminConversationsCache.removeConversation(conversationToDelete);

      // Cập nhật state local
      const updatedConversations = allConversations.filter(conv => conv.conversation_id !== conversationToDelete);
      setAllConversations(updatedConversations);

      toast({
        title: "Thành công",
        description: "Đã xóa hội thoại"
      });
      setShowDeleteDialog(false);
      setConversationToDelete(null);

      fetchStats();
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể xóa hội thoại",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshData = () => {
    adminConversationsCache.invalidateCache(); // Sử dụng invalidateCache thay vì clearCache
    loadConversationsWithCache();
    fetchStats();
    toast({
      title: "Thành công",
      description: "Đã làm mới dữ liệu từ máy chủ.",
    });
  };

  const formatDate = (dateString: string) => {
    return formatVietnameseDate(dateString);
  };

  // Real-time filter không cần debounce

  return (
    <div className="space-y-1 relative">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
          <Skeleton className="h-12 w-12 rounded-full" />
        </div>
      )}
      {/* Stats Cards */}
      {stats && (
        <div className="">
          {/*  */}
        </div>
      )}

      <Tabs defaultValue="stats" className="w-full">
        <TabsList>
          <TabsTrigger value="stats">Thống kê chi tiết</TabsTrigger>
          <TabsTrigger value="conversations">Danh sách hội thoại</TabsTrigger>
        </TabsList>
        <TabsContent value="stats">
          <AdminStats stats={stats} />
        </TabsContent>
        <TabsContent value="conversations">
          <Card>
            <CardHeader>
              <CardTitle>Bộ lọc hội thoại</CardTitle>
              <CardDescription>Tìm kiếm và lọc danh sách các cuộc hội thoại.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="space-y-2">
                  <Label htmlFor="search">Tìm theo Email hoặc Tin nhắn đầu</Label>
                  <Input
                    id="search"
                    placeholder="Nhập email hoặc nội dung..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="date-from">Từ ngày</Label>
                  <Input
                    id="date-from"
                    type="date"
                    value={dateFilter.from}
                    onChange={(e) => setDateFilter(prev => ({ ...prev, from: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="date-to">Đến ngày</Label>
                  <Input
                    id="date-to"
                    type="date"
                    value={dateFilter.to}
                    onChange={(e) => setDateFilter(prev => ({ ...prev, to: e.target.value }))}
                  />
                </div>
              </div>
              <div className="flex gap-2">
                <Button onClick={handleFilter}>
                  <Search className="mr-2 h-4 w-4" />
                  Lọc
                </Button>
                <Button variant="outline" onClick={handleClearFilter}>
                  Xóa bộ lọc
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Danh sách hội thoại</CardTitle>
              <CardDescription>
                Hiển thị {displayedConversations.length} trên tổng số {filteredConversations.length} hội thoại.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {initialLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
                </div>
              ) : (
                <>
                  <ScrollArea className="h-[600px] w-full">
                    <div className="space-y-4">
                      {displayedConversations.map((conv) => (
                        <ConversationItem
                          key={conv.conversation_id}
                          conv={conv}
                          handleViewMessages={handleViewMessages}
                          setConversationToDelete={setConversationToDelete}
                          setShowDeleteDialog={setShowDeleteDialog}
                        />
                      ))}
                    </div>
                  </ScrollArea>
                  <AppPagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={setCurrentPage}
                  />
                </>
              )}
            </CardContent>
          </Card>

        </TabsContent>
      </Tabs>

      {/* View Messages Dialog */}
      <Dialog open={showMessageDialog} onOpenChange={setShowMessageDialog}>
        <DialogContent className="max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Chi tiết hội thoại</DialogTitle>
            <DialogDescription>
              Xem toàn bộ tin nhắn trong hội thoại này
            </DialogDescription>
          </DialogHeader>

          {selectedConversation && (
            <div className="space-y-1 text-sm text-muted-foreground border-b pb-4">
              <p>ID: {selectedConversation.conversation_id}</p>
              <p>Email: {selectedConversation.user_email}</p>
              <p>Số tin nhắn: {messages.length}</p>
            </div>
          )}

          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.message_id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div className={`max-w-[70%] p-3 rounded-lg ${msg.role === "user"
                    ? "bg-blue-100 text-blue-900"
                    : "bg-gray-100 text-gray-900"
                    }`}>
                    <div className="flex items-center gap-2 mb-1">
                      {msg.role === "user" ? (
                        <UserIcon className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                      <span className="text-xs font-medium">
                        {msg.role === "user" ? "Người dùng" : "Assistant"}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(msg.created_at)}
                      </span>
                    </div>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>


        </DialogContent>
      </Dialog>



      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc chắn muốn xóa hội thoại này? Hành động này không thể hoàn tác.
              Tất cả tin nhắn trong hội thoại cũng sẽ bị xóa.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConversation}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={loading}
            >
              {loading ? "Đang xóa..." : "Xóa"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// =============================================
// Sub-components for better organization
// =============================================

function AdminStats({ stats }: { stats: AdminConversationStats | null }) {
  const formatDate = (dateString: string) => {
    // Sửa lại: chỉ truyền một tham số theo đúng định nghĩa của hàm
    return formatVietnameseDate(dateString);
  };

  if (!stats) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">Đang tải thống kê...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Thống kê chi tiết hệ thống
        </CardTitle>
        <CardDescription>
          Phân tích dữ liệu hội thoại và hoạt động người dùng
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard title="Tổng hội thoại" value={stats.total_conversations} icon={MessageSquare} color="blue" />
          <StatCard title="Tổng tin nhắn" value={stats.total_messages} icon={MessageCircle} color="green" />
          <StatCard title="Người dùng" value={stats.total_users} icon={Users} color="purple" />
          <StatCard
            title="Trung bình/Hội thoại"
            value={stats.total_conversations > 0 ? Math.round(stats.total_messages / stats.total_conversations) : 0}
            icon={TrendingUp}
            color="orange"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6">
            {/* Top Users Table */}
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Users className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                Người dùng hoạt động nhất
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-emerald-200 dark:border-emerald-800">
                      <th className="text-left p-3 text-sm font-medium text-emerald-800 dark:text-emerald-200">Email</th>
                      <th className="text-center p-3 text-sm font-medium text-emerald-800 dark:text-emerald-200">Số hội thoại</th>
                      <th className="text-center p-3 text-sm font-medium text-emerald-800 dark:text-emerald-200">Hoạt động</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.top_users.slice(0, 5).map((user, index) => (
                      <tr key={user.user_id} className="border-b border-emerald-100 dark:border-emerald-900 hover:bg-emerald-50 dark:hover:bg-emerald-900/50">
                        <td className="p-3 text-sm">{user.email}</td>
                        <td className="p-3 text-center text-sm font-medium">{user.conversation_count}</td>
                        <td className="p-3 text-center">
                          <div className="flex items-center justify-center">
                            <div className="w-16 bg-emerald-200 dark:bg-emerald-800 rounded-full h-2">
                              <div
                                className="bg-emerald-500 h-2 rounded-full"
                                style={{
                                  width: `${Math.min(100, (user.conversation_count / Math.max(...stats.top_users.map(u => u.conversation_count))) * 100)}%`
                                }}
                              ></div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
          </Card>
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Hội thoại theo ngày
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.conversations_by_date.slice(-7)}>
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => formatDate(value)}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <RechartsTooltip
                    labelFormatter={(value) => `Ngày: ${formatVietnameseDate(value)}`}
                    formatter={(value) => [value, 'Hội thoại']}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      </CardContent>
    </Card>
  );
}

type StatCardColor = 'blue' | 'green' | 'purple' | 'orange';

function StatCard({ title, value, icon: Icon, color }: { title: string, value: number, icon: React.ElementType, color: StatCardColor }) {
  const colors = {
    blue: "from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 text-blue-700 dark:text-blue-300",
    green: "from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 text-green-700 dark:text-green-300",
    purple: "from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 text-purple-700 dark:text-purple-300",
    orange: "from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900 text-orange-700 dark:text-orange-300",
  };
  const textColors = {
    blue: "text-blue-900 dark:text-blue-100",
    green: "text-green-900 dark:text-green-100",
    purple: "text-purple-900 dark:text-purple-100",
    orange: "text-orange-900 dark:text-orange-100",
  };
  const iconColors = {
    blue: "text-blue-600 dark:text-blue-400",
    green: "text-green-600 dark:text-green-400",
    purple: "text-purple-600 dark:text-purple-400",
    orange: "text-orange-600 dark:text-orange-400",
  };

  return (
    <div className={`bg-gradient-to-br p-4 rounded-lg border ${colors[color]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className={`text-2xl font-bold ${textColors[color]}`}>{value}</p>
        </div>
        <Icon className={`h-8 w-8 ${iconColors[color]}`} />
      </div>
    </div>
  );
}

interface ConversationItemProps {
  conv: AdminConversation;
  handleViewMessages: (conv: AdminConversation) => void;
  setConversationToDelete: (id: string | null) => void;
  setShowDeleteDialog: (show: boolean) => void;
}

function ConversationItem({ conv, handleViewMessages, setConversationToDelete, setShowDeleteDialog }: ConversationItemProps) {
  return (
    <div key={conv.conversation_id} className="border rounded-lg p-4 flex justify-between items-center hover:bg-muted/50 transition-colors">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-primary truncate">{conv.user_email}</p>
        <p className="text-sm text-muted-foreground truncate">{conv.first_message}</p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground mt-1">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formatVietnameseDate(conv.last_updated)}</span>
          </div>
          <div className="flex items-center gap-1">
            <MessageSquare className="h-3 w-3" />
            <span>{conv.message_count} tin nhắn</span>
          </div>
        </div>
      </div>
      <div className="flex gap-2 ml-4">
        <Button size="sm" variant="outline" onClick={() => handleViewMessages(conv)}>
          <Eye className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => {
            setConversationToDelete(conv.conversation_id);
            setShowDeleteDialog(true);
          }}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

interface AppPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

function AppPagination({ currentPage, totalPages, onPageChange }: AppPaginationProps) {
  if (totalPages <= 1) return null;

  const handlePrevious = (e: React.MouseEvent) => {
    e.preventDefault();
    onPageChange(Math.max(1, currentPage - 1));
  };

  const handleNext = (e: React.MouseEvent) => {
    e.preventDefault();
    onPageChange(Math.min(totalPages, currentPage + 1));
  };

  const handlePageClick = (e: React.MouseEvent, page: number) => {
    e.preventDefault();
    onPageChange(page);
  };
  
  const getPageItems = () => {
    const items: (number | 'ellipsis')[] = [];
    const delta = 1;
    const left = currentPage - delta;
    const right = currentPage + delta;

    const range: number[] = [];
    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= left && i <= right)) {
        range.push(i);
      }
    }
    
    let l: number | undefined;
    for (const i of range) {
      if (l) {
        if (i - l === 2) {
          items.push(l + 1);
        } else if (i - l > 2) {
          items.push('ellipsis');
        }
      }
      items.push(i);
      l = i;
    }
    return items;
  };

  return (
    <Pagination className="mt-6">
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious href="#" onClick={handlePrevious} />
        </PaginationItem>
        {getPageItems().map((item, index) => (
          <PaginationItem key={index}>
            {item === 'ellipsis' ? (
              <PaginationEllipsis />
            ) : (
              <PaginationLink 
                href="#" 
                isActive={currentPage === item}
                onClick={(e) => handlePageClick(e, item as number)}
              >
                {item}
              </PaginationLink>
            )}
          </PaginationItem>
        ))}
        <PaginationItem>
          <PaginationNext href="#" onClick={handleNext} />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}