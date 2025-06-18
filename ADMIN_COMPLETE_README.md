# Admin Panel Hoàn Chỉnh - Hệ Thống RAG

## Tổng Quan

Hệ thống admin panel hoàn chỉnh với sidebar navigation và quản lý toàn diện các tính năng của hệ thống RAG.

## Cấu Trúc Admin System

### 1. Layout & Navigation

#### AdminLayout Component
- **Sidebar Navigation**: Có thể thu gọn/mở rộng
- **Top Bar**: Hiển thị tên trang hiện tại và ngày tháng
- **User Info**: Thông tin admin đang đăng nhập
- **Quick Actions**: Chuyển sang chế độ student, đăng xuất

**Các trang trong admin:**
- `/admin` - Quản lý người dùng (Dashboard chính)
- `/admin/files` - Quản lý tài liệu 
- `/admin/settings` - Cài đặt hệ thống

### 2. Quản Lý Người Dùng

#### Features:
- **User CRUD**: Tạo, đọc, cập nhật, xóa người dùng
- **Role Management**: Admin/Student roles
- **Ban/Unban**: Cấm người dùng với thời gian và lý do
- **Search & Pagination**: Tìm kiếm và phân trang
- **Statistics**: Thống kê tổng quan người dùng

### 3. Quản Lý Tài Liệu

#### Features:
- **File Upload**: Upload các loại file PDF, DOCX, TXT, MD, SQL
- **File Management**: Xem, xóa tài liệu
- **Category System**: Phân loại tài liệu
- **Search & Filter**: Tìm kiếm và lọc theo danh mục
- **Statistics**: Thống kê file theo loại

### 4. Cài Đặt Hệ Thống

#### Features:
- **System Configuration**: Tên hệ thống, kích thước file tối đa
- **Security Settings**: Session timeout, password policy, 2FA
- **Database Management**: Thông tin DB, backup, rebuild index
- **Notification Settings**: Email notifications, alerts

## API Endpoints

### User Management:
```
GET /api/admin/users        # Lấy danh sách users
POST /api/admin/users       # Tạo user mới
PUT /api/admin/users/{id}   # Cập nhật user
DELETE /api/admin/users/{id} # Xóa user
POST /api/admin/users/{id}/ban   # Cấm user
POST /api/admin/users/{id}/unban # Bỏ cấm user
```

### File Management:
```
GET /api/files              # Lấy danh sách files
POST /api/upload            # Upload file mới (chỉ admin)
DELETE /api/files/{filename} # Xóa file (chỉ admin)
```

## Installation & Setup

### Prerequisites:
- Node.js 18+
- Next.js 14+
- Backend API running với admin endpoints

### Setup Steps:
1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Run Development**:
   ```bash
   npm run dev
   ```

### Admin Account Setup:
1. Tạo user bình thường qua signup
2. Update role trong database:
   ```sql
   INSERT INTO user_roles (user_id, role) VALUES ('user_id', 'admin');
   ```

## Usage Examples

### Tạo User Mới:
1. Vào Admin Dashboard
2. Click "Tạo người dùng"
3. Điền thông tin: email, password, role
4. Submit form

### Upload Tài Liệu:
1. Vào Files Management
2. Click "Upload tài liệu"
3. Chọn file (PDF, DOCX, TXT, MD, SQL)
4. Thêm category (optional)
5. Submit upload

## Key Components

- **AdminLayout**: Layout chính với sidebar
- **AdminDashboard**: Quản lý người dùng
- **AdminFilesManager**: Quản lý tài liệu
- **AdminSettings**: Cài đặt hệ thống
- **AdminAPI**: API client cho admin operations

## Routing & Access Control

### Admin Routes:
```
/admin/                 # Admin dashboard (user management)
/admin/files/          # File management
/admin/settings/       # System settings
```

### Access Control:
- **Authentication Required**: Tất cả admin routes yêu cầu đăng nhập
- **Role Check**: Chỉ user có role="admin" mới truy cập được
- **Auto Redirect**: User thường tự động chuyển về trang chủ

## UI/UX Features

### Design System:
- **Consistent Styling**: Sử dụng shadcn/ui components
- **Responsive Design**: Hoạt động tốt trên mobile và desktop
- **Loading States**: Spinner và skeleton loading
- **Toast Notifications**: Thông báo thành công/lỗi

### Navigation:
- **Collapsible Sidebar**: Thu gọn để tiết kiệm không gian
- **Active State**: Highlight trang hiện tại
- **Breadcrumb**: Hiển thị vị trí trong navigation
- **Quick Actions**: Nút chuyển về student mode

### Interactions:
- **Modal Dialogs**: Cho các form create/edit
- **Confirmation Dialogs**: Xác nhận các hành động nguy hiểm
- **Search & Filter**: Real-time search, dropdown filters
- **Pagination**: Navigation trang với số trang

## API Integration

### Authentication:
- **Token-based**: Sử dụng JWT tokens
- **Role Verification**: Kiểm tra role trong mỗi request
- **Error Handling**: Xử lý 401, 403, 500 errors

### File Management:
- **FormData Upload**: Multipart form data cho file upload
- **Progress Tracking**: Theo dõi tiến trình upload
- **File Validation**: Client-side và server-side validation

### User Management:
- **CRUD Operations**: Full CRUD cho user management
- **Batch Operations**: Có thể mở rộng cho multiple selection
- **Real-time Updates**: Refresh data sau mỗi operation

## Components Architecture

```
AdminLayout
├── Sidebar
│   ├── Logo & Title
│   ├── User Info
│   ├── Navigation Menu
│   └── Quick Actions
└── Main Content
    ├── Top Bar
    │   ├── Page Title
    │   ├── Breadcrumb
    │   └── Date Display
    └── Page Content
        ├── AdminDashboard (User Management)
        ├── AdminFilesManager (File Management)
        └── AdminSettings (System Settings)
```

## State Management

### Local State:
- **Component State**: useState cho UI state
- **Form State**: Controlled components cho forms
- **Loading State**: Loading indicators cho async operations

### Data Fetching:
- **useEffect**: Fetch data on component mount
- **Error Boundaries**: Handle API errors gracefully
- **Cache Strategy**: Refresh data after mutations

## Security Considerations

### Client-side:
- **Route Protection**: Role-based access control
- **Form Validation**: Client-side validation trước khi submit
- **XSS Prevention**: Sanitize user inputs

### API Integration:
- **JWT Tokens**: Secure authentication
- **Role Verification**: Server-side role checks
- **HTTPS Only**: Secure data transmission

## Future Enhancements

### Planned Features:
- **Bulk Operations**: Multiple user selection và actions
- **Advanced Analytics**: Charts và detailed statistics
- **Audit Logs**: Track tất cả admin activities
- **Role Permissions**: Fine-grained permission system
- **System Monitoring**: Server health và performance metrics
- **Backup Management**: Automated backup scheduling
- **Email Templates**: Custom email notification templates

### Performance Optimizations:
- **Virtual Scrolling**: Cho large datasets
- **Infinite Scroll**: Thay thế pagination
- **Caching Strategy**: Client-side data caching
- **Lazy Loading**: Component lazy loading

## Support

Để được hỗ trợ:
1. Check README này trước
2. Xem API documentation
3. Check browser console errors
4. Review network requests trong DevTools 