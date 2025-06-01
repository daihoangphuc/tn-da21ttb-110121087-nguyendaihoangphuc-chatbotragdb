# Quy trình quên mật khẩu (Password Reset Flow)

## Tổng quan

Quy trình quên mật khẩu cho hệ thống RAG gồm hai phần chính:
1. **Backend (Python FastAPI)**: Cung cấp API để gửi email quên mật khẩu và API để đặt lại mật khẩu
2. **Frontend (NestJS)**: Xây dựng giao diện người dùng và tích hợp với API backend

## Luồng hoạt động

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Người     │     │  Frontend   │     │   Backend   │     │  Supabase   │
│   dùng      │     │   (NestJS)  │     │  (FastAPI)  │     │   (Auth)    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 1. Yêu cầu        │                   │                   │
       │ quên mật khẩu     │                   │                   │
       │─────────────────> │                   │                   │
       │                   │ 2. Gửi request    │                   │
       │                   │ forgot-password   │                   │
       │                   │─────────────────> │                   │
       │                   │                   │ 3. Gọi API        │
       │                   │                   │ reset_password_   │
       │                   │                   │ for_email         │
       │                   │                   │─────────────────> │
       │                   │                   │                   │
       │                   │                   │ 4. Gửi email      │
       │                   │                   │ <──────────────── │
       │                   │                   │                   │
       │ 5. Nhận email     │                   │                   │
       │ <───────────────────────────────────────────────────────┐ │
       │                   │                   │                   │
       │ 6. Click vào      │                   │                   │
       │ liên kết          │                   │                   │
       │────────────────────────────────────> │                   │
       │                   │                   │ 7. Chuyển hướng   │
       │ <────────────────────────────────────│                   │
       │                   │                   │                   │
       │ 8. Nhập mật       │                   │                   │
       │ khẩu mới          │                   │                   │
       │─────────────────> │                   │                   │
       │                   │ 9. Gửi request    │                   │
       │                   │ reset-password    │                   │
       │                   │─────────────────> │                   │
       │                   │                   │ 10. Gọi API       │
       │                   │                   │ cập nhật mật khẩu │
       │                   │                   │─────────────────> │
       │                   │                   │                   │
       │                   │                   │ 11. Phản hồi      │
       │                   │                   │ <──────────────── │
       │                   │ 12. Phản hồi      │                   │
       │                   │ <──────────────── │                   │
       │ 13. Thông báo     │                   │                   │
       │ thành công        │                   │                   │
       │ <──────────────── │                   │                   │
       │                   │                   │                   │
```

## Chi tiết từng bước

### 1. Yêu cầu quên mật khẩu (Frontend)

Người dùng truy cập trang "Quên mật khẩu" và nhập email.

**Giao diện cần có:**
- Form nhập email
- Nút "Gửi yêu cầu"
- Thông báo gửi thành công/thất bại

### 2. Gửi request forgot-password (Frontend → Backend)

Frontend gửi request đến API backend:

```typescript
// Frontend (NestJS) service
async forgotPassword(email: string, redirectUrl: string): Promise<any> {
  return this.httpService.post('/api/auth/forgot-password', {
    email,
    redirect_to: redirectUrl
  }).toPromise();
}
```

### 3-4. Backend xử lý và gửi email (Backend → Supabase)

Backend gọi API Supabase để gửi email đặt lại mật khẩu:

```python
# Backend (FastAPI) - Đã triển khai
@app.post(f"{PREFIX}/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Gửi yêu cầu đặt lại mật khẩu đến email của người dùng
    """
    # Chuẩn bị options
    options = {}
    if request.redirect_to:
        options["redirect_to"] = request.redirect_to

    # Gọi API Supabase để gửi email đặt lại mật khẩu
    supabase_client.auth.reset_password_for_email(request.email, options)
    
    return {
        "status": "success",
        "message": "Yêu cầu đặt lại mật khẩu đã được gửi đến email của bạn."
    }
```

### 5. Người dùng nhận email

Email chứa liên kết đặt lại mật khẩu có dạng:
```
http://<redirect_url>/#access_token=<token>&type=recovery
```

### 6-7. Người dùng click vào liên kết và được chuyển hướng

Người dùng được chuyển hướng đến trang đặt lại mật khẩu với token trong URL hash fragment.

### 8-9. Nhập mật khẩu mới và gửi request reset-password (Frontend → Backend)

Frontend thu thập token từ URL và gửi cùng mật khẩu mới:

```typescript
// Frontend (NestJS) service
async resetPassword(password: string, accessToken: string): Promise<any> {
  return this.httpService.post('/api/auth/reset-password', {
    password,
    access_token: accessToken
  }).toPromise();
}
```

**Quan trọng**: Frontend cần lấy token từ URL hash fragment:

```typescript
// Hàm lấy token từ URL
function getAccessTokenFromHash(): string | null {
  const hash = window.location.hash.substring(1); // Bỏ dấu # ở đầu
  const params = new URLSearchParams(hash);
  return params.get('access_token');
}
```

### 10-11. Backend xử lý đặt lại mật khẩu (Backend → Supabase)

Backend gọi trực tiếp đến Supabase Auth API để cập nhật mật khẩu:

```python
# Backend (FastAPI) - Đã triển khai
@app.post(f"{PREFIX}/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Đặt lại mật khẩu với token xác thực
    """
    # Tạo URL endpoint cho API đặt lại mật khẩu
    auth_endpoint = urljoin(supabase_url, "auth/v1/user")
    
    # Tạo headers với token
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {request.access_token}",
        "Content-Type": "application/json"
    }
    
    # Tạo payload cho request
    payload = {
        "password": request.password
    }
    
    # Gửi request đến Supabase Auth API
    async with httpx.AsyncClient() as client:
        response = await client.put(
            auth_endpoint,
            headers=headers,
            json=payload
        )
        
        # Kiểm tra kết quả
        if response.status_code >= 200 and response.status_code < 300:
            return {
                "status": "success",
                "message": "Mật khẩu đã được đặt lại thành công"
            }
        else:
            raise ValueError(f"Lỗi khi cập nhật mật khẩu: {response.text}")
```

### 12-13. Phản hồi và thông báo thành công

Frontend nhận phản hồi và hiển thị thông báo thành công, sau đó chuyển hướng người dùng đến trang đăng nhập.

## Mô hình dữ liệu

### ForgotPasswordRequest
```json
{
  "email": "user@example.com",
  "redirect_to": "http://example.com/reset-password.html"
}
```

### ResetPasswordRequest
```json
{
  "password": "NewPassword123",
  "access_token": "eyJhbG...token_from_url..."
}
```

### SuccessResponse
```json
{
  "status": "success",
  "message": "Mật khẩu đã được đặt lại thành công"
}
```

## Xác thực mật khẩu

Backend áp dụng xác thực mật khẩu mạnh:
- Ít nhất 8 ký tự
- Có ít nhất một chữ hoa
- Có ít nhất một chữ thường
- Có ít nhất một chữ số

Frontend cũng nên thực hiện xác thực tương tự trước khi gửi để tăng trải nghiệm người dùng.

## Xử lý lỗi

### Lỗi phổ biến:
1. Email không tồn tại
2. Token không hợp lệ hoặc đã hết hạn
3. Mật khẩu không đáp ứng yêu cầu bảo mật
4. Lỗi kết nối mạng

### Frontend cần xử lý:
- Hiển thị thông báo lỗi rõ ràng
- Cho phép người dùng yêu cầu token mới
- Kiểm tra mật khẩu mạnh trước khi gửi

## Bảo mật

- Sử dụng HTTPS cho tất cả các giao tiếp
- Không lưu token vào localStorage, chỉ lấy từ URL và sử dụng ngay
- Xóa token khỏi URL sau khi đã được sử dụng
- Thêm rate limiting để ngăn chặn tấn công brute force

## Triển khai trong NestJS

### Tạo Module Auth

```typescript
// auth.module.ts
@Module({
  imports: [HttpModule],
  controllers: [AuthController],
  providers: [AuthService],
  exports: [AuthService],
})
export class AuthModule {}
```

### Tạo Service

```typescript
// auth.service.ts
@Injectable()
export class AuthService {
  constructor(private httpService: HttpService) {}

  async forgotPassword(email: string): Promise<any> {
    const redirectUrl = `${process.env.FRONTEND_URL}/reset-password`;
    return this.httpService.post(`${process.env.API_URL}/api/auth/forgot-password`, {
      email,
      redirect_to: redirectUrl
    }).pipe(
      map(response => response.data),
      catchError(error => {
        console.error('Lỗi quên mật khẩu:', error.response?.data || error.message);
        throw new HttpException(
          error.response?.data?.detail || 'Lỗi khi yêu cầu đặt lại mật khẩu',
          error.response?.status || HttpStatus.INTERNAL_SERVER_ERROR
        );
      })
    ).toPromise();
  }

  async resetPassword(password: string, accessToken: string): Promise<any> {
    return this.httpService.post(`${process.env.API_URL}/api/auth/reset-password`, {
      password,
      access_token: accessToken
    }).pipe(
      map(response => response.data),
      catchError(error => {
        console.error('Lỗi đặt lại mật khẩu:', error.response?.data || error.message);
        throw new HttpException(
          error.response?.data?.detail || 'Lỗi khi đặt lại mật khẩu',
          error.response?.status || HttpStatus.INTERNAL_SERVER_ERROR
        );
      })
    ).toPromise();
  }
}
```

### Tạo Controller

```typescript
// auth.controller.ts
@Controller('auth')
export class AuthController {
  constructor(private authService: AuthService) {}

  @Post('forgot-password')
  async forgotPassword(@Body() body: { email: string }): Promise<any> {
    return this.authService.forgotPassword(body.email);
  }

  @Post('reset-password')
  async resetPassword(@Body() body: { password: string, accessToken: string }): Promise<any> {
    return this.authService.resetPassword(body.password, body.accessToken);
  }
}
```

## Kết luận

Quy trình quên mật khẩu được thiết kế để đảm bảo:
1. Tính bảo mật cao (sử dụng token an toàn, xác thực mật khẩu mạnh)
2. Trải nghiệm người dùng tốt (thông báo rõ ràng, xử lý lỗi)
3. Tích hợp dễ dàng với Supabase Auth

Frontend NestJS có trách nhiệm cung cấp giao diện người dùng và giao tiếp với backend FastAPI, trong khi backend chịu trách nhiệm xác thực và giao tiếp với Supabase Auth API. 