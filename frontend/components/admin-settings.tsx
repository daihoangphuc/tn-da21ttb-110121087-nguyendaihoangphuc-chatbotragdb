"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { 
  Settings,
  Database,
  Server,
  Shield,
  Bell,
  Trash2,
  RefreshCw
} from "lucide-react";

export function AdminSettings() {
  return (
    <div className="space-y-6">
      {/* System Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <CardTitle>Cấu hình hệ thống</CardTitle>
          </div>
          <CardDescription>
            Cấu hình các thông số cơ bản của hệ thống
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="system-name">Tên hệ thống</Label>
              <Input
                id="system-name"
                placeholder="Hệ thống RAG cho Cơ sở dữ liệu"
                defaultValue="Hệ thống RAG cho Cơ sở dữ liệu"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max-file-size">Kích thước file tối đa (MB)</Label>
              <Input
                id="max-file-size"
                type="number"
                placeholder="50"
                defaultValue="50"
              />
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Cho phép đăng ký mới</Label>
                <p className="text-sm text-muted-foreground">
                  Người dùng mới có thể tự đăng ký tài khoản
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Yêu cầu xác nhận email</Label>
                <p className="text-sm text-muted-foreground">
                  Bắt buộc xác nhận email khi đăng ký
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Chế độ bảo trì</Label>
                <p className="text-sm text-muted-foreground">
                  Tạm thời ngưng hoạt động hệ thống để bảo trì
                </p>
              </div>
              <Switch />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Database Management */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Database className="h-5 w-5" />
            <CardTitle>Quản lý cơ sở dữ liệu</CardTitle>
          </div>
          <CardDescription>
            Thông tin và thao tác với cơ sở dữ liệu vector
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Tổng tài liệu</div>
              <div className="text-2xl font-bold">-</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Vector đã lưu</div>
              <div className="text-2xl font-bold">-</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Dung lượng sử dụng</div>
              <div className="text-2xl font-bold">-</div>
            </div>
          </div>
          
          <Separator />
          
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              Rebuild Index
            </Button>
            <Button variant="outline" size="sm" className="flex items-center gap-2">
              <Database className="w-4 h-4" />
              Backup Database
            </Button>
            <Button variant="destructive" size="sm" className="flex items-center gap-2">
              <Trash2 className="w-4 h-4" />
              Clear All Data
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Shield className="h-5 w-5" />
            <CardTitle>Cài đặt bảo mật</CardTitle>
          </div>
          <CardDescription>
            Cấu hình các thiết lập bảo mật và quyền truy cập
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="session-timeout">Thời gian hết hạn session (phút)</Label>
              <Input
                id="session-timeout"
                type="number"
                placeholder="60"
                defaultValue="60"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max-login-attempts">Số lần đăng nhập tối đa</Label>
              <Input
                id="max-login-attempts"
                type="number"
                placeholder="5"
                defaultValue="5"
              />
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Bắt buộc mật khẩu mạnh</Label>
                <p className="text-sm text-muted-foreground">
                  Yêu cầu mật khẩu có ít nhất 8 ký tự, chữ hoa, chữ thường và số
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Bật 2FA</Label>
                <p className="text-sm text-muted-foreground">
                  Bật xác thực 2 yếu tố cho tài khoản admin
                </p>
              </div>
              <Switch />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Ghi log hoạt động</Label>
                <p className="text-sm text-muted-foreground">
                  Ghi lại tất cả hoạt động của admin
                </p>
              </div>
              <Switch defaultChecked />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Bell className="h-5 w-5" />
            <CardTitle>Cài đặt thông báo</CardTitle>
          </div>
          <CardDescription>
            Cấu hình các thông báo hệ thống
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Email thông báo user mới</Label>
                <p className="text-sm text-muted-foreground">
                  Gửi email khi có user đăng ký mới
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Thông báo lỗi hệ thống</Label>
                <p className="text-sm text-muted-foreground">
                  Gửi email khi có lỗi nghiêm trọng
                </p>
              </div>
              <Switch defaultChecked />
            </div>
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Báo cáo hàng tuần</Label>
                <p className="text-sm text-muted-foreground">
                  Gửi báo cáo thống kê hoạt động hàng tuần
                </p>
              </div>
              <Switch />
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-2">
            <Label htmlFor="admin-email">Email admin nhận thông báo</Label>
            <Input
              id="admin-email"
              type="email"
              placeholder="admin@example.com"
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Settings */}
      <div className="flex justify-end space-x-2">
        <Button variant="outline">Hủy bỏ</Button>
        <Button>Lưu cài đặt</Button>
      </div>
    </div>
  );
} 