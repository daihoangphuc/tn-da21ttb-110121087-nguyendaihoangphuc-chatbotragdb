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
    loadConversationsWithCache();
    fetchStats();
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
    setLoading(true);
    try {
      // Kiểm tra cache trước
      const cachedData = adminConversationsCache.getCachedData();
      if (cachedData) {
        setAllConversations(cachedData);
        setLoading(false);
        return;
      }

      // Nếu không có cache, fetch từ API
      const data = await adminConversationsCache.getConversations(fetchAllConversationsFromAPI);
      setAllConversations(data);
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể tải danh sách hội thoại",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
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
    // Xóa cache và load lại dữ liệu
    adminConversationsCache.invalidateCache();
    loadConversationsWithCache();
  };

  const formatDate = (dateString: string) => {
    return formatVietnameseDate(dateString);
  };

  // Real-time filter không cần debounce

  return (
    <div className="space-y-6 relative">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
          <Skeleton className="h-12 w-12 rounded-full" />
        </div>
      )}
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Tổng hội thoại</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_conversations}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <MessageCircle className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Tổng tin nhắn</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_messages}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Người dùng</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_users}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Tỷ lệ tin nhắn</span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-sm">
                <div>User: {stats.messages_by_role.user}</div>
                <div>Bot: {stats.messages_by_role.assistant}</div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs defaultValue="conversations" className="space-y-4">
        <TabsList>
          <TabsTrigger value="conversations">Danh sách hội thoại</TabsTrigger>
          <TabsTrigger value="stats">Thống kê chi tiết</TabsTrigger>
        </TabsList>

        <TabsContent value="conversations">
          <Card>
            <CardHeader>
              <CardTitle>Quản lý hội thoại</CardTitle>
              <CardDescription>
                Xem và quản lý tất cả hội thoại trong hệ thống
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Search and Filters */}
              <div className="space-y-4 mb-4">
                {/* Search bar và refresh button */}
                <div className="flex items-center space-x-2">
                  <div className="relative flex-1 max-w-sm">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Tìm kiếm theo email hoặc tin nhắn..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleRefreshData}
                    disabled={loading}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Làm mới
                  </Button>
                </div>

                {/* Cache status */}
                <div className="text-xs text-muted-foreground">
                  {(() => {
                    const cacheStatus = adminConversationsCache.getCacheStatus();
                    if (cacheStatus.hasCache && cacheStatus.isValid) {
                      const ageMinutes = Math.floor(cacheStatus.age / 60000);
                      return `Dữ liệu từ cache (${ageMinutes} phút trước)`;
                    } else if (cacheStatus.hasCache) {
                      return "Cache đã hết hạn, sẽ tải lại dữ liệu";
                    } else {
                      return "Đang tải dữ liệu từ server";
                    }
                  })()}
                </div>

                {/* Date filters - Improved layout */}
                <div className="border rounded-lg p-4 bg-muted/20">
                  <div className="flex items-center gap-2 mb-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Lọc theo thời gian</span>
                    {(searchTerm || dateFilter.from || dateFilter.to) && (
                      <Badge variant="secondary" className="ml-2">
                        Đang lọc
                      </Badge>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 items-end">
                    <div className="space-y-2">
                      <Label htmlFor="dateFrom" className="text-sm font-medium">Từ ngày</Label>
                      <Input
                        id="dateFrom"
                        type="date"
                        value={dateFilter.from}
                        onChange={(e) => setDateFilter({ ...dateFilter, from: e.target.value })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="space-y-2">
                      <Label htmlFor="dateTo" className="text-sm font-medium">Đến ngày</Label>
                      <Input
                        id="dateTo"
                        type="date"
                        value={dateFilter.to}
                        onChange={(e) => setDateFilter({ ...dateFilter, to: e.target.value })}
                        className="w-full"
                      />
                    </div>
                    
                    <div className="flex gap-2">
                      <Button 
                        onClick={handleFilter} 
                        disabled={loading}
                        className="flex-1"
                        size="sm"
                      >
                        <Search className="h-4 w-4 mr-1" />
                        Lọc
                      </Button>
                    </div>
                    
                    <div>
                      <Button 
                        variant="outline" 
                        onClick={handleClearFilter} 
                        disabled={loading}
                        className="w-full"
                        size="sm"
                      >
                        <X className="h-4 w-4 mr-1" />
                        Xóa bộ lọc
                      </Button>
                    </div>
                  </div>

                  {/* Filter summary */}
                  {(searchTerm || dateFilter.from || dateFilter.to) && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="flex flex-wrap gap-2">
                        {searchTerm && (
                          <Badge variant="outline" className="text-xs">
                            Tìm kiếm: "{searchTerm}"
                          </Badge>
                        )}
                        {dateFilter.from && (
                          <Badge variant="outline" className="text-xs">
                            Từ: {dateFilter.from}
                          </Badge>
                        )}
                        {dateFilter.to && (
                          <Badge variant="outline" className="text-xs">
                            Đến: {dateFilter.to}
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Conversations Table */}
              {loading ? (
                <div className="space-y-4">
                  <div className="space-y-2">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <div key={i} className="flex items-center space-x-4 p-4 border rounded">
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-4 w-40" />
                        <Skeleton className="h-4 w-64" />
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-4 w-32" />
                        <div className="flex gap-2">
                          <Skeleton className="h-8 w-8" />
                          <Skeleton className="h-8 w-8" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) :
                <div className="rounded-md border">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="p-2 text-left">ID</th>
                        <th className="p-2 text-left">Email</th>
                        <th className="p-2 text-left">Tin nhắn đầu</th>
                        <th className="p-2 text-center">Số tin nhắn</th>
                        <th className="p-2 text-left">Cập nhật</th>
                        <th className="p-2 text-center">Hành động</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayedConversations.map((conv, index) => (
                      <tr key={`${conv.conversation_id}_${index}`} className="border-b">
                        <td className="p-2 font-mono text-xs">
                          {conv.conversation_id.substring(0, 8)}...
                        </td>
                        <td className="p-2">{conv.user_email}</td>
                        <td className="p-2 max-w-xs truncate">{conv.first_message}</td>
                        <td className="p-2 text-center">{conv.message_count}</td>
                        <td className="p-2">{formatDate(conv.last_updated)}</td>
                        <td className="p-2">
                          <div className="flex gap-2 justify-center">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleViewMessages(conv)}
                              disabled={loading}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => {
                                setConversationToDelete(conv.conversation_id);
                                setShowDeleteDialog(true);
                              }}
                              disabled={loading}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              }

              {/* Pagination và Result count */}
              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Hiển thị {displayedConversations.length} / {filteredConversations.length} hội thoại
                  {filteredConversations.length !== allConversations.length && (
                    <span> (từ tổng {allConversations.length} hội thoại)</span>
                  )}
                  {totalPages > 1 && (
                    <span> - Trang {currentPage} / {totalPages}</span>
                  )}
                </div>
                
                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1 || loading}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Trước
                    </Button>
                    
                    <div className="flex items-center space-x-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        let pageNum;
                        if (totalPages <= 5) {
                          pageNum = i + 1;
                        } else if (currentPage <= 3) {
                          pageNum = i + 1;
                        } else if (currentPage >= totalPages - 2) {
                          pageNum = totalPages - 4 + i;
                        } else {
                          pageNum = currentPage - 2 + i;
                        }
                        
                        return (
                          <Button
                            key={pageNum}
                            variant={currentPage === pageNum ? "default" : "outline"}
                            size="sm"
                            onClick={() => setCurrentPage(pageNum)}
                            disabled={loading}
                            className="w-8 h-8 p-0"
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                    </div>
                    
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages || loading}
                    >
                      Sau
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
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
            <CardContent>
              {stats ? (
                <div className="space-y-8">
                  {/* Overview Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950 dark:to-blue-900 p-4 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-blue-700 dark:text-blue-300">Tổng hội thoại</p>
                          <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">{stats.total_conversations}</p>
                        </div>
                        <MessageSquare className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                      </div>
                    </div>

                    <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-950 dark:to-green-900 p-4 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-green-700 dark:text-green-300">Tổng tin nhắn</p>
                          <p className="text-2xl font-bold text-green-900 dark:text-green-100">{stats.total_messages}</p>
                        </div>
                        <MessageCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
                      </div>
                    </div>

                    <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-950 dark:to-purple-900 p-4 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-purple-700 dark:text-purple-300">Người dùng</p>
                          <p className="text-2xl font-bold text-purple-900 dark:text-purple-100">{stats.total_users}</p>
                        </div>
                        <Users className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                      </div>
                    </div>

                    <div className="bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950 dark:to-orange-900 p-4 rounded-lg border">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-orange-700 dark:text-orange-300">Trung bình/Hội thoại</p>
                          <p className="text-2xl font-bold text-orange-900 dark:text-orange-100">
                            {stats.total_conversations > 0 ? Math.round(stats.total_messages / stats.total_conversations) : 0}
                          </p>
                        </div>
                        <TrendingUp className="h-8 w-8 text-orange-600 dark:text-orange-400" />
                      </div>
                    </div>
                  </div>

                  {/* Charts Row */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Messages by Role Chart */}
                    <div className="bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-6 rounded-lg border">
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <MessageCircle className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                        Phân bố tin nhắn theo vai trò
                      </h3>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={[
                                { name: 'Người dùng', value: stats.messages_by_role.user, fill: '#3b82f6' },
                                { name: 'AI Assistant', value: stats.messages_by_role.assistant, fill: '#10b981' }
                              ]}
                              cx="50%"
                              cy="50%"
                              labelLine={false}
                              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(1)}%`}
                              outerRadius={80}
                              fill="#8884d8"
                              dataKey="value"
                            />
                            <RechartsTooltip formatter={(value) => [value, 'Tin nhắn']} />
                            <Legend />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Conversations by Date Chart */}
                    <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 dark:from-indigo-950 dark:to-indigo-900 p-6 rounded-lg border">
                      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                        Hội thoại theo ngày (7 ngày gần nhất)
                      </h3>
                      <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={stats.conversations_by_date.slice(-7)}>
                            <XAxis 
                              dataKey="date" 
                              tick={{ fontSize: 12 }}
                              tickFormatter={(value) => {
                                const date = new Date(value);
                                return `${date.getDate()}/${date.getMonth() + 1}`;
                              }}
                            />
                            <YAxis tick={{ fontSize: 12 }} />
                            <RechartsTooltip 
                              labelFormatter={(value) => `Ngày: ${formatDate(value)}`}
                              formatter={(value) => [value, 'Hội thoại']}
                            />
                            <Bar 
                              dataKey="count" 
                              fill="#6366f1"
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>

                  {/* Top Users Table */}
                  <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950 dark:to-emerald-900 p-6 rounded-lg border">
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
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64">
                  <div className="text-center">
                    <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <p className="text-muted-foreground">Đang tải thống kê...</p>
                  </div>
                </div>
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
                  <div className={`max-w-[70%] p-3 rounded-lg ${
                    msg.role === "user" 
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