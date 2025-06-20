"use client";

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
  UserIcon
} from "lucide-react";
import { format } from "date-fns";
import { vi } from "date-fns/locale";

export function AdminConversations() {
  const [conversations, setConversations] = useState<AdminConversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<AdminConversation | null>(null);
  const [messages, setMessages] = useState<AdminMessage[]>([]);
  const [stats, setStats] = useState<AdminConversationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showMessageDialog, setShowMessageDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);

  const [dateFilter, setDateFilter] = useState({ from: "", to: "" });
  const [userFilter, setUserFilter] = useState("");
  const { toast } = useToast();

  useEffect(() => {
    fetchConversations();
    fetchStats();
  }, [page, dateFilter, userFilter]);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const params: any = { page, per_page: 20 };
      if (userFilter) params.user_id = userFilter;
      if (dateFilter.from) params.date_from = dateFilter.from;
      if (dateFilter.to) params.date_to = dateFilter.to;

      const response = await adminAPI.fetchConversations(params);
      setConversations(response.conversations);
      setTotalPages(response.total_pages);
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

  const fetchStats = async () => {
    try {
      const response = await adminAPI.getConversationStats(7);
      setStats(response);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
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

  const handleSearchMessages = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    try {
      const response = await adminAPI.searchMessages({
        query: searchQuery,
        page: 1,
        per_page: 50
      });
      setSearchResults(response.messages);
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể tìm kiếm tin nhắn",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async () => {
    if (!conversationToDelete) return;

    try {
      await adminAPI.deleteConversation(conversationToDelete);
      toast({
        title: "Thành công",
        description: "Đã xóa hội thoại"
      });
      setShowDeleteDialog(false);
      setConversationToDelete(null);
      fetchConversations();
      fetchStats();
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể xóa hội thoại",
        variant: "destructive"
      });
    }
  };



  const formatDate = (dateString: string) => {
    if (!dateString) return "N/A";
    try {
      return format(new Date(dateString), "dd/MM/yyyy HH:mm", { locale: vi });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
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
          <TabsTrigger value="search">Tìm kiếm tin nhắn</TabsTrigger>
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
              {/* Filters */}
              <div className="flex gap-4 mb-4">
                <div className="flex-1">
                  <Label htmlFor="dateFrom">Từ ngày</Label>
                  <Input
                    id="dateFrom"
                    type="date"
                    value={dateFilter.from}
                    onChange={(e) => setDateFilter({ ...dateFilter, from: e.target.value })}
                  />
                </div>
                <div className="flex-1">
                  <Label htmlFor="dateTo">Đến ngày</Label>
                  <Input
                    id="dateTo"
                    type="date"
                    value={dateFilter.to}
                    onChange={(e) => setDateFilter({ ...dateFilter, to: e.target.value })}
                  />
                </div>
                <div className="flex-1">
                  <Label htmlFor="userFilter">User ID</Label>
                  <Input
                    id="userFilter"
                    placeholder="Lọc theo user ID"
                    value={userFilter}
                    onChange={(e) => setUserFilter(e.target.value)}
                  />
                </div>
                <div className="flex items-end">
                  <Button onClick={fetchConversations}>Lọc</Button>
                </div>
              </div>

              {/* Conversations Table */}
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
                    {conversations.map((conv) => (
                      <tr key={conv.conversation_id} className="border-b">
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

              {/* Pagination */}
              <div className="flex justify-between items-center mt-4">
                <Button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  variant="outline"
                >
                  Trang trước
                </Button>
                <span>Trang {page} / {totalPages}</span>
                <Button
                  onClick={() => setPage(page + 1)}
                  disabled={page === totalPages}
                  variant="outline"
                >
                  Trang sau
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="search">
          <Card>
            <CardHeader>
              <CardTitle>Tìm kiếm tin nhắn</CardTitle>
              <CardDescription>
                Tìm kiếm tin nhắn trong toàn bộ hệ thống
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder="Nhập từ khóa tìm kiếm..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && handleSearchMessages()}
                />
                <Button onClick={handleSearchMessages} disabled={loading}>
                  <Search className="h-4 w-4 mr-2" />
                  Tìm kiếm
                </Button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Tìm thấy {searchResults.length} kết quả
                  </p>
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-4">
                      {searchResults.map((msg) => (
                        <Card key={msg.message_id}>
                          <CardHeader className="pb-3">
                            <div className="flex justify-between items-start">
                              <div className="space-y-1">
                                <p className="text-sm font-medium">{msg.user_email}</p>
                                <p className="text-xs text-muted-foreground">
                                  {formatDate(msg.created_at)}
                                </p>
                              </div>
                              <div className={`px-2 py-1 rounded text-xs ${
                                msg.role === "user" ? "bg-blue-100 text-blue-700" : "bg-green-100 text-green-700"
                              }`}>
                                {msg.role}
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stats">
          <Card>
            <CardHeader>
              <CardTitle>Thống kê chi tiết</CardTitle>
              <CardDescription>
                Phân tích xu hướng và hoạt động
              </CardDescription>
            </CardHeader>
            <CardContent>
              {stats && (
                <div className="space-y-6">
                  {/* Top Users */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Top người dùng hoạt động</h3>
                    <div className="space-y-2">
                      {stats.top_users.map((user, index) => (
                        <div key={user.user_id} className="flex items-center justify-between p-3 border rounded">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold">
                              {index + 1}
                            </div>
                            <div>
                              <p className="font-medium">{user.email}</p>
                              <p className="text-sm text-muted-foreground">ID: {user.user_id}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold">{user.conversation_count}</p>
                            <p className="text-sm text-muted-foreground">hội thoại</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Conversations by Date */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Hội thoại theo ngày</h3>
                    <div className="space-y-2">
                      {stats.conversations_by_date.map((item) => (
                        <div key={item.date} className="flex items-center justify-between p-3 border rounded">
                          <span>{formatDate(item.date)}</span>
                          <span className="font-semibold">{item.count} hội thoại</span>
                        </div>
                      ))}
                    </div>
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
            >
              Xóa
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
