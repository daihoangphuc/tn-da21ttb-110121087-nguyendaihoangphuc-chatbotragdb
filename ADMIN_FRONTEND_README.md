# Giao Diện Admin - Hướng Dẫn Sử Dụng

## Tổng Quan

Giao diện Admin được thiết kế để quản lý người dùng trong hệ thống RAG. Chỉ những người dùng có role `admin` mới có thể truy cập vào giao diện này.

## Tính Năng

### 1. Tự Động Chuyển Hướng
- Khi admin đăng nhập, hệ thống sẽ tự động chuyển hướng đến trang `/admin`
- Student sẽ được giữ ở trang chính `/` với giao diện chat

### 2. Dashboard Admin
Giao diện chính bao gồm:

#### **Header**
- Logo và tiêu đề "Admin Dashboard"
- Thông tin admin hiện tại
- Nút "Chế độ Student" - cho phép admin trải nghiệm giao diện như student
- Nút "Đăng xuất"

#### **Thống Kê**
- **Tổng người dùng**: Hiển thị tổng số người dùng trong hệ thống
- **Admin**: Số lượng quản trị viên
- **Students**: Số lượng sinh viên

#### **Quản Lý Người Dùng**
Bảng danh sách người dùng với các cột:
- **Email**: Địa chỉ email của người dùng
- **Vai trò**: Badge hiển thị Admin (đỏ) hoặc Student (xám)
- **Trạng thái**: Hoạt động (xanh) hoặc Đã cấm (đỏ)
- **Ngày tạo**: Thời gian tạo tài khoản
- **Đăng nhập cuối**: Lần đăng nhập gần nhất
- **Hành động**: Menu dropdown với các tùy chọn

### 3. Các Tính Năng Quản Lý

#### **Tạo Người Dùng Mới**
- Nhấn nút "Thêm người dùng"
- Nhập email, mật khẩu, và chọn vai trò
- Tự động gửi thông báo thành công

#### **Chỉnh Sửa Người Dùng**
- Nhấn menu "..." → "Chỉnh sửa"
- Có thể thay đổi email, mật khẩu, và vai trò
- Để trống mật khẩu nếu không muốn thay đổi

#### **Cấm Người Dùng**
- Nhấn menu "..." → "Cấm"
- Chọn thời gian cấm: 1h, 24h, 7d, 30d, 1 năm
- Có thể thêm lý do cấm (tùy chọn)

#### **Bỏ Cấm Người Dùng**
- Với người dùng đã bị cấm, menu sẽ hiển thị "Bỏ cấm"
- Nhấn để ngay lập tức bỏ cấm

#### **Xóa Người Dùng**
- Nhấn menu "..." → "Xóa"
- Có popup xác nhận trước khi xóa
- Xóa cứng (hard delete) người dùng khỏi hệ thống

### 4. Tìm Kiếm và Phân Trang
- **Tìm kiếm**: Tìm kiếm theo email trong ô search
- **Phân trang**: Điều hướng qua các trang với nút "Trước" và "Sau"
- **Làm mới**: Nút làm mới để tải lại danh sách

### 5. Chế Độ Student cho Admin
- Admin có thể chuyển sang "Chế độ Student" để trải nghiệm giao diện như sinh viên
- Khi ở chế độ Student, sẽ có banner màu xanh hiển thị thông tin admin
- Có thể quay lại trang Admin bất cứ lúc nào từ banner hoặc URL `/admin`

## Cấu Trúc File

### Frontend Structure
```
frontend/
├── app/
│   ├── admin/
│   │   ├── layout.tsx          # Layout bảo vệ cho admin
│   │   └── page.tsx            # Trang admin chính
│   └── page.tsx                # Trang chủ với logic routing
├── components/
│   ├── admin-dashboard.tsx     # Component chính của dashboard
│   ├── admin-api.ts           # API calls cho admin
│   ├── admin-types.ts         # Type definitions
│   └── main-layout.tsx        # Layout chính (có admin banner)
```

### Key Components

#### **AdminLayout (`app/admin/layout.tsx`)**
- Bảo vệ route, chỉ cho phép admin truy cập
- Tự động redirect nếu không phải admin

#### **AdminDashboard (`components/admin-dashboard.tsx`)**
- Component chính chứa toàn bộ giao diện admin
- Quản lý state và các modal
- Tích hợp với API backend

#### **AdminAPI (`components/admin-api.ts`)**
- Class chứa tất cả API calls
- Sử dụng `fetchApi` từ `lib/api.ts` để có authentication tự động

## API Endpoints Sử Dụng

Dashboard sử dụng các API sau từ backend:

```
GET /api/admin/users?page=1&per_page=10  # Lấy danh sách user
POST /api/admin/users                    # Tạo user mới
PUT /api/admin/users/{id}                # Cập nhật user
DELETE /api/admin/users/{id}?hard=true   # Xóa user
POST /api/admin/users/{id}/ban           # Cấm user
POST /api/admin/users/{id}/unban         # Bỏ cấm user
```

## Bảo Mật

### Role-Based Access Control
- Chỉ user có `role = "admin"` mới truy cập được
- Frontend kiểm tra role và redirect tự động
- Backend cũng có middleware kiểm tra admin role

### Authentication
- Sử dụng JWT token từ localStorage
- Tự động include Authorization header trong mọi request
- Auto logout nếu token expired

### Admin Safety
- Admin không thể tự xóa hoặc tự cấm chính mình (backend protection)
- Có confirmation dialog cho các thao tác nguy hiểm

## Styling

### Design System
- Sử dụng **Tailwind CSS** và **shadcn/ui** components
- Theme nhất quán với hệ thống hiện tại
- Responsive design cho mobile và desktop

### Color Scheme
- **Admin badges**: Đỏ với icon Crown
- **Student badges**: Xám với icon GraduationCap  
- **Trạng thái hoạt động**: Xanh lá
- **Trạng thái bị cấm**: Đỏ
- **Admin banner**: Gradient xanh-tím

## Error Handling

### Toast Notifications
- Thành công: Toast màu xanh
- Lỗi: Toast màu đỏ với thông báo chi tiết
- Tự động ẩn sau vài giây

### Loading States
- Spinner khi đang tải dữ liệu
- Disable buttons khi đang xử lý
- Skeleton loading cho table

## Performance

### Optimizations
- Pagination để tránh load quá nhiều data
- Debounced search
- Lazy loading components
- Memoized calculations

### Caching
- LocalStorage cho sidebar state
- Không cache user data (để đảm bảo tính real-time)

## Mobile Support

### Responsive Design
- Table responsive với horizontal scroll
- Touch-friendly buttons và dropdowns
- Optimized spacing cho mobile

### Mobile-Specific Features
- Sidebar tự động đóng sau khi chọn conversation (trong student mode)
- Touch gestures cho navigation

## Future Enhancements

### Planned Features
1. **Bulk Operations**: Chọn nhiều user để thực hiện hành động hàng loạt
2. **Advanced Filters**: Lọc theo role, trạng thái, ngày tạo
3. **Export Data**: Xuất danh sách user ra CSV/Excel
4. **User Activity Logs**: Xem lịch sử hoạt động của user
5. **Role Management**: Quản lý permissions chi tiết hơn
6. **Dashboard Analytics**: Biểu đồ và thống kê chi tiết

### Technical Improvements
1. **Real-time Updates**: WebSocket để cập nhật real-time
2. **Advanced Search**: Full-text search, regex support
3. **Audit Trail**: Log mọi thao tác admin
4. **Backup/Restore**: Sao lưu và khôi phục dữ liệu user

## Troubleshooting

### Common Issues

1. **Không thể truy cập /admin**
   - Kiểm tra user có role "admin" không
   - Clear localStorage và đăng nhập lại

2. **API calls bị lỗi 401/403**
   - Token có thể đã expired
   - Kiểm tra backend có chạy không

3. **Giao diện không load đúng**
   - Clear browser cache
   - Kiểm tra console có lỗi JavaScript không

4. **Chế độ Student không hoạt động**
   - Kiểm tra URL có param `?student=true` không
   - Refresh lại trang

### Debug Tips

1. **Check Authentication**:
   ```javascript
   console.log('Token:', localStorage.getItem('auth_token'));
   console.log('User:', JSON.parse(localStorage.getItem('user_info')));
   ```

2. **Monitor API Calls**:
   - Mở Chrome DevTools → Network tab
   - Kiểm tra request/response

3. **Check User Role**:
   ```javascript
   // Trong component
   console.log('User role:', user?.role);
   ```

## Support

Nếu gặp vấn đề hoặc cần hỗ trợ:
1. Kiểm tra logs trong browser console
2. Kiểm tra network requests trong DevTools  
3. Verify backend API responses
4. Liên hệ team phát triển với thông tin chi tiết về lỗi 