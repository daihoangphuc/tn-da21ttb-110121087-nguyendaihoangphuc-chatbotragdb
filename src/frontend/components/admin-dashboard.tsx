"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/use-toast";
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { 
  Users, 
  UserPlus, 
  Settings, 
  Shield, 
  ShieldOff, 
  Trash2, 
  Edit, 
  MoreHorizontal,
  LogOut,
  Home,
  RefreshCw,
  Search,
  Crown,
  GraduationCap
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { AdminUser, CreateUserData, UpdateUserData, BanUserData } from "./admin-types";
import { adminAPI } from "./admin-api";
import { formatVietnameseDate } from "@/lib/utils";

export function AdminDashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();
  
  // State
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState("");
  
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showBanModal, setShowBanModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  
  // Form states
  const [createForm, setCreateForm] = useState<CreateUserData>({
    email: "",
    password: "",
    role: "student",
    metadata: {}
  });
  const [editForm, setEditForm] = useState<UpdateUserData>({});
  const [banForm, setBanForm] = useState<BanUserData>({
    duration: "24h",
    reason: ""
  });

  // Fetch users function
  const fetchUsers = async (page = 1) => {
    try {
      setLoading(true);
      const data = await adminAPI.fetchUsers(page, perPage);
      setUsers(data.users);
      setTotalCount(data.total_count);
      setCurrentPage(data.page);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể tải danh sách người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Create user function
  const createUser = async () => {
    try {
      setLoading(true);
      await adminAPI.createUser(createForm);
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đã tạo người dùng mới"
      });
      setShowCreateModal(false);
      setCreateForm({ email: "", password: "", role: "student", metadata: {} });
      fetchUsers(currentPage);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể tạo người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Update user function
  const updateUser = async () => {
    if (!selectedUser) return;
    
    try {
      setLoading(true);
      await adminAPI.updateUser(selectedUser.id, editForm);
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đã cập nhật thông tin người dùng"
      });
      setShowEditModal(false);
      setEditForm({});
      setSelectedUser(null);
      fetchUsers(currentPage);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể cập nhật người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Ban user function
  const banUser = async () => {
    if (!selectedUser) return;
    
    try {
      setLoading(true);
      await adminAPI.banUser(selectedUser.id, banForm);
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đã cấm người dùng"
      });
      setShowBanModal(false);
      setBanForm({ duration: "24h", reason: "" });
      setSelectedUser(null);
      fetchUsers(currentPage);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể cấm người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Unban user function
  const unbanUser = async (userId: string) => {
    try {
      setLoading(true);
      await adminAPI.unbanUser(userId);
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đã bỏ cấm người dùng"
      });
      fetchUsers(currentPage);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể bỏ cấm người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Delete user function
  const deleteUser = async (userId: string) => {
    if (!confirm("Bạn có chắc chắn muốn xóa người dùng này?")) return;
    
    try {
      setLoading(true);
      await adminAPI.deleteUser(userId, true);
      toast({
        variant: "success",
        title: "Thành công",
        description: "Đã xóa người dùng"
      });
      fetchUsers(currentPage);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Lỗi",
        description: "Không thể xóa người dùng"
      });
    } finally {
      setLoading(false);
    }
  };

  // Effects
  useEffect(() => {
    fetchUsers(1);
  }, []);

  // Helper functions
  const formatDate = (dateString?: string) => {
    if (!dateString) return "Chưa có";
    return formatVietnameseDate(dateString);
  };

  const getRoleBadge = (role?: string) => {
    if (role === "admin") {
      return <Badge variant="default" className="flex items-center gap-1"><Crown className="w-3 h-3" /> Admin</Badge>;
    }
    return <Badge variant="secondary" className="flex items-center gap-1"><GraduationCap className="w-3 h-3" /> Student</Badge>;
  };

  const getBannedStatus = (bannedUntil?: string) => {
    if (bannedUntil) {
      return <Badge variant="destructive">Đã cấm</Badge>;
    }
    return <Badge variant="default" className="bg-green-500">Hoạt động</Badge>;
  };

  const totalPages = Math.ceil(totalCount / perPage);

  return (
    <div className="space-y-6 relative">
      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-background/80 backdrop-blur-sm z-10 flex items-center justify-center">
          <div className="flex flex-col items-center space-y-2">
            <RefreshCw className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Đang xử lý...</p>
          </div>
        </div>
      )}
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Tổng người dùng</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalCount}</div>
              <p className="text-xs text-muted-foreground">
                Đang hoạt động trong hệ thống
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Admin</CardTitle>
              <Crown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {users.filter(u => u.role === "admin").length}
              </div>
              <p className="text-xs text-muted-foreground">
                Quản trị viên
              </p>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Students</CardTitle>
              <GraduationCap className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {users.filter(u => u.role === "student").length}
              </div>
              <p className="text-xs text-muted-foreground">
                Sinh viên
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Users Management Card */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Quản lý người dùng</CardTitle>
                <CardDescription>
                  Quản lý tài khoản người dùng trong hệ thống
                </CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fetchUsers(currentPage)}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Làm mới
                </Button>
                <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
                  <DialogTrigger asChild>
                    <Button className="flex items-center gap-2">
                      <UserPlus className="w-4 h-4" />
                      Thêm người dùng
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[425px]">
                    <DialogHeader>
                      <DialogTitle>Tạo người dùng mới</DialogTitle>
                      <DialogDescription>
                        Nhập thông tin để tạo tài khoản người dùng mới
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="email" className="text-right">
                          Email
                        </Label>
                        <Input
                          id="email"
                          value={createForm.email}
                          onChange={(e) => setCreateForm({...createForm, email: e.target.value})}
                          className="col-span-3"
                        />
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="password" className="text-right">
                          Mật khẩu
                        </Label>
                        <Input
                          id="password"
                          type="password"
                          value={createForm.password}
                          onChange={(e) => setCreateForm({...createForm, password: e.target.value})}
                          className="col-span-3"
                        />
                      </div>
                      <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="role" className="text-right">
                          Vai trò
                        </Label>
                        <Select 
                          value={createForm.role} 
                          onValueChange={(value) => setCreateForm({...createForm, role: value})}
                        >
                          <SelectTrigger className="col-span-3">
                            <SelectValue placeholder="Chọn vai trò" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="student">Student</SelectItem>
                            <SelectItem value="admin">Admin</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button type="submit" onClick={createUser} disabled={loading}>
                        {loading ? "Đang tạo..." : "Tạo tài khoản"}
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Search */}
            <div className="flex items-center space-x-2 mb-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Tìm kiếm theo email..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8"
                />
              </div>
            </div>

            {/* Users Table */}
            {loading ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center space-x-4 p-4 border rounded">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-4 w-20" />
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-8 w-8 rounded" />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Vai trò</TableHead>
                    <TableHead>Trạng thái</TableHead>
                    <TableHead>Ngày tạo</TableHead>
                    <TableHead>Đăng nhập cuối</TableHead>
                    <TableHead className="text-right">Hành động</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users
                    .filter(user => 
                      user.email.toLowerCase().includes(searchTerm.toLowerCase())
                    )
                    .map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-medium">{user.email}</TableCell>
                      <TableCell>{getRoleBadge(user.role)}</TableCell>
                      <TableCell>{getBannedStatus(user.banned_until)}</TableCell>
                      <TableCell>{formatDate(user.created_at)}</TableCell>
                      <TableCell>{formatDate(user.last_sign_in_at)}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="h-8 w-8 p-0" disabled={loading}>
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => {
                                setSelectedUser(user);
                                setEditForm({
                                  email: user.email,
                                  role: user.role,
                                  metadata: user.metadata
                                });
                                setShowEditModal(true);
                              }}
                            >
                              <Edit className="mr-2 h-4 w-4" />
                              Chỉnh sửa
                            </DropdownMenuItem>
                            {user.banned_until ? (
                              <DropdownMenuItem onClick={() => unbanUser(user.id)}>
                                <ShieldOff className="mr-2 h-4 w-4" />
                                Bỏ cấm
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                onClick={() => {
                                  setSelectedUser(user);
                                  setShowBanModal(true);
                                }}
                              >
                                <Shield className="mr-2 h-4 w-4" />
                                Cấm
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuItem
                              onClick={() => deleteUser(user.id)}
                              className="text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              Xóa
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            {/* Simple Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-2 mt-6">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => currentPage > 1 && fetchUsers(currentPage - 1)}
                  disabled={currentPage <= 1}
                >
                  Trước
                </Button>
                
                <span className="text-sm text-gray-600">
                  Trang {currentPage} / {totalPages}
                </span>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => currentPage < totalPages && fetchUsers(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                >
                  Sau
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

      {/* Edit User Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Chỉnh sửa người dùng</DialogTitle>
            <DialogDescription>
              Cập nhật thông tin người dùng
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="edit-email" className="text-right">
                Email
              </Label>
              <Input
                id="edit-email"
                value={editForm.email || ""}
                onChange={(e) => setEditForm({...editForm, email: e.target.value})}
                className="col-span-3"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="edit-password" className="text-right">
                Mật khẩu mới
              </Label>
              <Input
                id="edit-password"
                type="password"
                value={editForm.password || ""}
                onChange={(e) => setEditForm({...editForm, password: e.target.value})}
                className="col-span-3"
                placeholder="Để trống nếu không đổi"
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="edit-role" className="text-right">
                Vai trò
              </Label>
              <Select 
                value={editForm.role || ""} 
                onValueChange={(value) => setEditForm({...editForm, role: value})}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="Chọn vai trò" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="student">Student</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" onClick={updateUser} disabled={loading}>
              {loading ? "Đang cập nhật..." : "Cập nhật"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Ban User Modal */}
      <Dialog open={showBanModal} onOpenChange={setShowBanModal}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Cấm người dùng</DialogTitle>
            <DialogDescription>
              Cấm người dùng {selectedUser?.email} truy cập hệ thống
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="ban-duration" className="text-right">
                Thời gian
              </Label>
              <Select 
                value={banForm.duration} 
                onValueChange={(value) => setBanForm({...banForm, duration: value})}
              >
                <SelectTrigger className="col-span-3">
                  <SelectValue placeholder="Chọn thời gian cấm" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1h">1 giờ</SelectItem>
                  <SelectItem value="24h">24 giờ</SelectItem>
                  <SelectItem value="7d">7 ngày</SelectItem>
                  <SelectItem value="30d">30 ngày</SelectItem>
                  <SelectItem value="365d">1 năm</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="ban-reason" className="text-right">
                Lý do
              </Label>
              <Textarea
                id="ban-reason"
                value={banForm.reason || ""}
                onChange={(e) => setBanForm({...banForm, reason: e.target.value})}
                className="col-span-3"
                placeholder="Lý do cấm (tùy chọn)"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="submit" onClick={banUser} variant="destructive">
              Cấm người dùng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
} 