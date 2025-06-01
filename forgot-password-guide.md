# Hướng dẫn xây dựng chức năng Quên mật khẩu (Forgot Password)

Tài liệu này hướng dẫn chi tiết cách xây dựng chức năng quên mật khẩu cho ứng dụng frontend, tương thích với API `/auth/forgot-password` của hệ thống RAG.

## API Endpoint

- **URL**: `/api/auth/forgot-password`
- **Method**: `POST`
- **Authentication**: Không yêu cầu
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "redirect_url": "http://your-frontend-url/reset-password"
  }
  ```
- **Response (Success - 200)**:
  ```json
  {
    "status": "success",
    "message": "Yêu cầu đặt lại mật khẩu đã được gửi đến email của bạn."
  }
  ```
- **Response (Error - 400)**:
  ```json
  {
    "detail": "Không tìm thấy người dùng với email này."
  }
  ```
  Hoặc các lỗi khác như: "Bạn đã gửi quá nhiều yêu cầu. Vui lòng thử lại sau.", "Tham số không hợp lệ..."

## Các bước triển khai

### 1. Tạo trang Quên mật khẩu

```jsx
// ForgotPassword.jsx (React)
import React, { useState } from 'react';
import axios from 'axios';

function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await axios.post('http://your-api-url/api/auth/forgot-password', {
        email,
        // Đường dẫn này sẽ là trang đặt lại mật khẩu mới trong ứng dụng của bạn
        redirect_url: 'http://your-frontend-url/reset-password'
      });

      if (response.data.status === 'success') {
        setMessage('Đã gửi liên kết đặt lại mật khẩu đến email của bạn.');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Đã xảy ra lỗi khi gửi yêu cầu đặt lại mật khẩu.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="forgot-password-container">
      <h2>Quên mật khẩu</h2>
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="Nhập email của bạn"
          />
        </div>
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Đang gửi...' : 'Gửi liên kết đặt lại mật khẩu'}
        </button>
      </form>
      
      <div className="links">
        <a href="/login">Trở về đăng nhập</a>
      </div>
    </div>
  );
}

export default ForgotPassword;
```

### 2. Tạo trang Đặt lại mật khẩu

```jsx
// ResetPassword.jsx (React)
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

function ResetPassword() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [token, setToken] = useState('');
  
  const location = useLocation();
  const navigate = useNavigate();

  // Lấy token từ URL khi component được mount
  useEffect(() => {
    // Supabase sẽ trả về token trong URL với tham số 'access_token'
    const params = new URLSearchParams(location.hash.substring(1));
    const accessToken = params.get('access_token');
    
    if (accessToken) {
      setToken(accessToken);
    } else {
      setError('Token không hợp lệ hoặc đã hết hạn.');
    }
  }, [location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Kiểm tra mật khẩu xác nhận
    if (password !== confirmPassword) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    
    if (!token) {
      setError('Không có token đặt lại mật khẩu.');
      return;
    }

    setIsLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await axios.post(
        'http://your-api-url/api/auth/reset-password',
        { password },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      if (response.data.status === 'success') {
        setMessage('Mật khẩu đã được đặt lại thành công.');
        // Chuyển hướng về trang đăng nhập sau 3 giây
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Đã xảy ra lỗi khi đặt lại mật khẩu.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="reset-password-container">
      <h2>Đặt lại mật khẩu</h2>
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
      
      {token ? (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="password">Mật khẩu mới</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength="6"
              placeholder="Nhập mật khẩu mới"
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">Xác nhận mật khẩu mới</label>
            <input
              type="password"
              id="confirmPassword"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength="6"
              placeholder="Nhập lại mật khẩu mới"
            />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Đang xử lý...' : 'Đặt lại mật khẩu'}
          </button>
        </form>
      ) : (
        <div className="token-error">
          <p>Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.</p>
          <a href="/forgot-password">Yêu cầu liên kết mới</a>
        </div>
      )}
      
      <div className="links">
        <a href="/login">Trở về đăng nhập</a>
      </div>
    </div>
  );
}

export default ResetPassword;
```

### 3. Cấu hình định tuyến (Routes)

```jsx
// App.jsx (React Router)
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
// Import các component khác...

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        {/* Các route khác... */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

### 4. Thêm liên kết "Quên mật khẩu" vào trang đăng nhập

```jsx
// Login.jsx (một phần của component)
<div className="login-links">
  <a href="/forgot-password">Quên mật khẩu?</a>
  <a href="/signup">Đăng ký tài khoản mới</a>
</div>
```

### 5. CSS cho trang Quên mật khẩu và Đặt lại mật khẩu

```css
/* styles.css */
.forgot-password-container,
.reset-password-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  background-color: #fff;
}

h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 15px;
}

label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

button {
  width: 100%;
  padding: 12px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #357ae8;
}

button:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.success-message {
  padding: 10px;
  background-color: #dff0d8;
  border: 1px solid #d6e9c6;
  color: #3c763d;
  border-radius: 4px;
  margin-bottom: 15px;
}

.error-message {
  padding: 10px;
  background-color: #f2dede;
  border: 1px solid #ebccd1;
  color: #a94442;
  border-radius: 4px;
  margin-bottom: 15px;
}

.links {
  margin-top: 15px;
  text-align: center;
}

.links a {
  color: #4a90e2;
  text-decoration: none;
}

.links a:hover {
  text-decoration: underline;
}

.token-error {
  text-align: center;
  padding: 20px 0;
}
```

## Luồng hoạt động đầy đủ

1. **Người dùng yêu cầu đặt lại mật khẩu**:
   - Người dùng nhập email vào form trang "Quên mật khẩu"
   - Frontend gửi request đến API `/auth/forgot-password` với email và redirect_url
   - Backend (Supabase) gửi email chứa liên kết đặt lại mật khẩu đến người dùng
   - Frontend hiển thị thông báo thành công (hoặc lỗi nếu có)

2. **Người dùng đặt lại mật khẩu**:
   - Người dùng nhấp vào liên kết trong email
   - Trình duyệt mở URL `redirect_url` với token xác thực trong fragment URL (#access_token=...)
   - Frontend lấy token từ URL và hiển thị form đặt lại mật khẩu
   - Người dùng nhập mật khẩu mới và xác nhận
   - Frontend gửi request đến API `/auth/reset-password` với token và mật khẩu mới
   - Backend (Supabase) xác thực token và cập nhật mật khẩu mới
   - Frontend hiển thị thông báo thành công và chuyển hướng về trang đăng nhập

## Lưu ý quan trọng

1. **URL chuyển hướng**:
   - Cần đảm bảo `redirect_url` được cấu hình đúng và phải là URL hợp lệ
   - URL này phải nằm trong danh sách URL được phép trong cấu hình Supabase

2. **Bảo mật**:
   - Token đặt lại mật khẩu thường có thời hạn ngắn (1 giờ)
   - Nên kiểm tra độ mạnh của mật khẩu trước khi gửi
   - Nên sử dụng HTTPS cho toàn bộ quá trình

3. **UX (Trải nghiệm người dùng)**:
   - Hiển thị thông báo rõ ràng cho mỗi bước
   - Hiển thị spinner hoặc loading indicator khi đang xử lý
   - Cung cấp liên kết để quay lại trang đăng nhập
   - Tự động chuyển hướng sau khi hoàn thành

4. **Xử lý lỗi**:
   - Hiển thị thông báo lỗi cụ thể và hướng dẫn người dùng cách khắc phục
   - Xử lý trường hợp token không hợp lệ hoặc hết hạn
   - Xử lý trường hợp mật khẩu không đáp ứng yêu cầu bảo mật

5. **Môi trường**:
   - Sử dụng biến môi trường để lưu URL API thay vì hard-coding
   - Ví dụ: `REACT_APP_API_URL` hoặc `VITE_API_URL`

## Triển khai cho các framework khác

### Vue.js

```vue
<!-- ForgotPassword.vue -->
<template>
  <div class="forgot-password-container">
    <h2>Quên mật khẩu</h2>
    <div v-if="message" class="success-message">{{ message }}</div>
    <div v-if="error" class="error-message">{{ error }}</div>
    
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="email">Email</label>
        <input
          type="email"
          id="email"
          v-model="email"
          required
          placeholder="Nhập email của bạn"
        />
      </div>
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? 'Đang gửi...' : 'Gửi liên kết đặt lại mật khẩu' }}
      </button>
    </form>
    
    <div class="links">
      <router-link to="/login">Trở về đăng nhập</router-link>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      email: '',
      message: '',
      error: '',
      isLoading: false
    };
  },
  methods: {
    async handleSubmit() {
      this.isLoading = true;
      this.error = '';
      this.message = '';

      try {
        const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/forgot-password`, {
          email: this.email,
          redirect_url: `${window.location.origin}/reset-password`
        });

        if (response.data.status === 'success') {
          this.message = 'Đã gửi liên kết đặt lại mật khẩu đến email của bạn.';
        }
      } catch (err) {
        this.error = err.response?.data?.detail || 'Đã xảy ra lỗi khi gửi yêu cầu đặt lại mật khẩu.';
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>
```

### Angular

```typescript
// forgot-password.component.ts
import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-forgot-password',
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.css']
})
export class ForgotPasswordComponent {
  email: string = '';
  message: string = '';
  error: string = '';
  isLoading: boolean = false;

  constructor(private http: HttpClient) {}

  async handleSubmit() {
    this.isLoading = true;
    this.error = '';
    this.message = '';

    try {
      const response: any = await this.http.post(`${environment.apiUrl}/api/auth/forgot-password`, {
        email: this.email,
        redirect_url: `${window.location.origin}/reset-password`
      }).toPromise();

      if (response.status === 'success') {
        this.message = 'Đã gửi liên kết đặt lại mật khẩu đến email của bạn.';
      }
    } catch (err: any) {
      this.error = err.error?.detail || 'Đã xảy ra lỗi khi gửi yêu cầu đặt lại mật khẩu.';
    } finally {
      this.isLoading = false;
    }
  }
}
```

```html
<!-- forgot-password.component.html -->
<div class="forgot-password-container">
  <h2>Quên mật khẩu</h2>
  <div *ngIf="message" class="success-message">{{ message }}</div>
  <div *ngIf="error" class="error-message">{{ error }}</div>
  
  <form (ngSubmit)="handleSubmit()">
    <div class="form-group">
      <label for="email">Email</label>
      <input
        type="email"
        id="email"
        [(ngModel)]="email"
        name="email"
        required
        placeholder="Nhập email của bạn"
      />
    </div>
    <button type="submit" [disabled]="isLoading">
      {{ isLoading ? 'Đang gửi...' : 'Gửi liên kết đặt lại mật khẩu' }}
    </button>
  </form>
  
  <div class="links">
    <a routerLink="/login">Trở về đăng nhập</a>
  </div>
</div>
```

## Tổng kết

Chức năng quên mật khẩu là thành phần quan trọng trong hệ thống xác thực người dùng. Việc triển khai đúng cách sẽ giúp người dùng dễ dàng khôi phục tài khoản khi quên mật khẩu, đồng thời bảo đảm tính bảo mật của hệ thống.

Hãy đảm bảo thực hiện đầy đủ các bước trên và chú ý đến các lưu ý quan trọng để xây dựng một chức năng quên mật khẩu hoàn chỉnh và an toàn. 