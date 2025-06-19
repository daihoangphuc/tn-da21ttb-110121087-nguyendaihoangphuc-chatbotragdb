# Hướng dẫn sử dụng Admin User Management APIs

## Tổng quan

Bộ APIs này cho phép admin quản lý người dùng trong hệ thống thông qua Supabase Auth. Tất cả các API này yêu cầu quyền admin để truy cập.

## Cấu hình biến môi trường

Đảm bảo file `.env` của bạn có các biến sau:

```env
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Public key
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Service role key (bắt buộc cho admin APIs)
API_PREFIX=/api
```

**Lưu ý quan trọng**: `SUPABASE_SERVICE_KEY` là bắt buộc để các admin APIs hoạt động. Đây là service role key có đầy đủ quyền admin.

## Xác thực

Tất cả admin APIs yêu cầu:
1. Token Bearer hợp lệ trong header `Authorization: Bearer <token>`
2. Người dùng có role `admin` trong bảng `user_roles`

## Danh sách APIs

### 1. Liệt kê người dùng

```http
GET /api/admin/users?page=1&per_page=50
Authorization: Bearer <admin_token>
```

**Tham số:**
- `page` (int, optional): Trang hiện tại (mặc định: 1)
- `per_page` (int, optional): Số người dùng mỗi trang (mặc định: 50, tối đa: 100)

**Response:**
```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "created_at": "2024-01-01T00:00:00Z",
      "email_confirmed_at": "2024-01-01T00:05:00Z",
      "last_sign_in_at": "2024-01-02T10:30:00Z",
      "role": "student",
      "metadata": {},
      "banned_until": null
    }
  ],
  "total_count": 100,
  "page": 1,
  "per_page": 50
}
```

### 2. Tạo người dùng mới

```http
POST /api/admin/users
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "role": "student",
  "metadata": {
    "name": "Tên người dùng",
    "department": "Khoa CNTT"
  }
}
```

**Tham số:**
- `email` (string, required): Email của người dùng
- `password` (string, required): Mật khẩu
- `role` (string, optional): Vai trò ("admin" hoặc "student", mặc định: "student")
- `metadata` (object, optional): Thông tin bổ sung

**Response:**
```json
{
  "id": "uuid",
  "email": "newuser@example.com",
  "created_at": "2024-01-01T00:00:00Z",
  "email_confirmed_at": "2024-01-01T00:00:01Z",
  "last_sign_in_at": null,
  "role": "student",
  "metadata": {
    "name": "Tên người dùng",
    "department": "Khoa CNTT"
  },
  "banned_until": null
}
```

### 3. Lấy thông tin người dùng

```http
GET /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
```

**Tham số:**
- `user_id` (string, required): ID của người dùng

**Response:** Giống như response của API tạo người dùng

### 4. Cập nhật người dùng

```http
PUT /api/admin/users/{user_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "email": "updated@example.com",
  "password": "NewPassword123!",
  "role": "admin",
  "metadata": {
    "name": "Tên mới"
  }
}
```

**Tham số:**
- `user_id` (string, required): ID của người dùng
- `email` (string, optional): Email mới
- `password` (string, optional): Mật khẩu mới
- `role` (string, optional): Vai trò mới
- `metadata` (object, optional): Metadata mới

**Response:** Thông tin người dùng sau khi cập nhật

### 5. Xóa người dùng

```http
DELETE /api/admin/users/{user_id}?hard=true
Authorization: Bearer <admin_token>
```

**Tham số:**
- `user_id` (string, required): ID của người dùng
- `hard` (boolean, optional): `true` = xóa vĩnh viễn, `false` = xóa tạm thời (mặc định: `true`)

**Response:** 204 No Content

**Lưu ý:** Admin không thể xóa chính tài khoản của mình.

### 6. Cấm người dùng

```http
POST /api/admin/users/{user_id}/ban
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "duration": "24h",
  "reason": "Vi phạm quy định sử dụng"
}
```

**Tham số:**
- `user_id` (string, required): ID của người dùng
- `duration` (string, required): Thời gian cấm (format: "1h", "24h", "7d", etc.)
- `reason` (string, optional): Lý do cấm

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "banned_for": "24h",
  "reason": "Vi phạm quy định sử dụng",
  "banned_by": "admin@example.com",
  "banned_at": "2024-01-01T12:00:00Z"
}
```

### 7. Bỏ cấm người dùng

```http
POST /api/admin/users/{user_id}/unban
Authorization: Bearer <admin_token>
```

**Tham số:**
- `user_id` (string, required): ID của người dùng

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "unbanned_by": "admin@example.com",
  "unbanned_at": "2024-01-01T13:00:00Z"
}
```

**Lưu ý:** API này sử dụng `ban_duration: "none"` theo tài liệu Supabase Auth để bỏ cấm user một cách chính xác.

## Ví dụ sử dụng với Python

```python
import requests

# Cấu hình
API_BASE = "http://localhost:8000/api"
ADMIN_TOKEN = "your_admin_token_here"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# 1. Lấy danh sách người dùng
response = requests.get(f"{API_BASE}/admin/users", headers=headers)
users = response.json()
print(f"Tổng số người dùng: {users['total_count']}")

# 2. Tạo người dùng mới
new_user_data = {
    "email": "student@example.com",
    "password": "SecurePass123!",
    "role": "student",
    "metadata": {"name": "Sinh viên mới"}
}
response = requests.post(f"{API_BASE}/admin/users", json=new_user_data, headers=headers)
new_user = response.json()
print(f"Đã tạo người dùng: {new_user['email']}")

# 3. Cấm người dùng
ban_data = {
    "duration": "24h",
    "reason": "Spam"
}
user_id = new_user['id']
response = requests.post(f"{API_BASE}/admin/users/{user_id}/ban", json=ban_data, headers=headers)
print("Đã cấm người dùng")

# 4. Bỏ cấm người dùng
response = requests.post(f"{API_BASE}/admin/users/{user_id}/unban", headers=headers)
print("Đã bỏ cấm người dùng")
```

## Ví dụ sử dụng với cURL

```bash
# Lấy danh sách người dùng
curl -X GET "http://localhost:8000/api/admin/users?page=1&per_page=10" \
  -H "Authorization: Bearer your_admin_token"

# Tạo người dùng mới
curl -X POST "http://localhost:8000/api/admin/users" \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "role": "student"
  }'

# Cấm người dùng
curl -X POST "http://localhost:8000/api/admin/users/USER_ID/ban" \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "duration": "24h",
    "reason": "Vi phạm quy định"
  }'
```

## Bảo mật

1. **Service Key Security**: `SUPABASE_SERVICE_KEY` có quyền admin đầy đủ. Giữ bí mật và chỉ sử dụng trên server.

2. **Role-based Access**: Chỉ user có role `admin` mới có thể truy cập các API này.

3. **Self-protection**: Admin không thể xóa hoặc cấm chính tài khoản của mình.

4. **Audit Trail**: Tất cả hành động admin đều được ghi log với thông tin người thực hiện.

## Lỗi thường gặp

### 403 Forbidden
```json
{
  "detail": "Chỉ admin mới có quyền truy cập API này"
}
```
**Giải pháp:** Đảm bảo user có role `admin` trong bảng `user_roles`.

### 409 Conflict
```json
{
  "detail": "Email này đã được đăng ký"
}
```
**Giải pháp:** Sử dụng email khác hoặc cập nhật user hiện tại.

### 500 Internal Server Error
```json
{
  "detail": "Không thể khởi tạo service client"
}
```
**Giải pháp:** Kiểm tra `SUPABASE_SERVICE_KEY` trong file `.env`.

## Testing

Để test các API này, bạn cần:

1. Một tài khoản admin (có role `admin` trong bảng `user_roles`)
2. Token hợp lệ từ việc đăng nhập admin
3. Sử dụng token này trong header `Authorization`

```python
# Ví dụ test với pytest
import pytest
import requests

class TestAdminAPIs:
    def setup_method(self):
        # Đăng nhập admin để lấy token
        login_data = {
            "email": "admin@example.com",
            "password": "admin_password"
        }
        response = requests.post("http://localhost:8000/api/auth/login", json=login_data)
        self.admin_token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.admin_token}"}
    
    def test_list_users(self):
        response = requests.get("http://localhost:8000/api/admin/users", headers=self.headers)
        assert response.status_code == 200
        assert "users" in response.json()
```

## Tích hợp với hệ thống hiện tại

Các admin APIs này đã được tích hợp hoàn toàn với hệ thống hiện tại của bạn:

1. **Sử dụng cùng prefix API**: `/api` như các API khác
2. **Tương thích với authentication**: Sử dụng cùng hệ thống token và role
3. **Kết nối Supabase**: Sử dụng cùng client và database
4. **Logging**: Tích hợp với hệ thống logging hiện tại

## Chạy server

```bash
# Đảm bảo đã cài đặt dependencies
pip install -r requirements.txt

# Chạy server
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy trên `http://localhost:8000` và admin APIs sẽ có sẵn tại các endpoint `/api/admin/*`.

## Script Test

Tôi đã tạo sẵn một script test đơn giản `test_admin_simple.py` để demo tất cả các admin APIs:

```bash
# Cài đặt requests nếu chưa có
pip install requests

# Chỉnh sửa thông tin admin trong file test_admin_simple.py
# Đổi email và password admin thực tế của bạn

# Chạy test script
python test_admin_simple.py
```

Script sẽ test tất cả các chức năng:
1. Đăng nhập admin
2. Liệt kê người dùng
3. Tạo người dùng mới
4. Lấy thông tin người dùng
5. Cập nhật thông tin người dùng
6. Cấm người dùng
7. Bỏ cấm người dùng
8. Xóa người dùng 