# RAG Assistant - Giao diện di động

Giao diện di động cho hệ thống RAG (Retrieval Augmented Generation) lấy cảm hứng từ Google NotebookLM.

## Hướng dẫn cài đặt

1. Đảm bảo đã cài đặt và khởi động backend API của hệ thống RAG tại thư mục gốc:

```bash
python -m src.api.main --reload
```

2. Mở file `index.html` trong trình duyệt hoặc sử dụng một web server đơn giản để phục vụ các file tĩnh:

```bash
cd src/UI
# Nếu sử dụng Python 3 có thể dùng web server đơn giản:
python -m http.server 8080
```

3. Truy cập giao diện tại `http://localhost:8080`

## Cấu hình API URL

Nếu API của bạn không chạy trên cùng origin với UI, bạn cần cấu hình URL cơ sở cho API trong file `app.js`:

```javascript
// Thay đổi dòng này để trỏ đến URL của API backend của bạn
const API_BASE_URL = 'http://localhost:8000'; 
```

- Để trống (`''`) nếu UI và API chạy trên cùng một origin
- Điền URL đầy đủ (ví dụ: `'http://localhost:8000'`) nếu API chạy trên origin khác

## Cấu trúc thư mục

```
src/UI/
├── index.html     # File HTML chính
├── app.js         # Logic JavaScript
├── style.css      # CSS bổ sung
└── README.md      # Hướng dẫn
```

## Tính năng

- **Giao diện đáp ứng (Responsive)**: Hoạt động trên cả desktop và thiết bị di động
- **Upload tài liệu**: Hỗ trợ upload nhiều file cùng lúc (PDF, DOCX, TXT, ...)
- **Trao đổi với AI**: Đặt câu hỏi và nhận câu trả lời dựa trên tài liệu đã tải lên
- **Xem nguồn tài liệu**: Hiển thị văn bản nguồn được trích dẫn trong câu trả lời
- **Quản lý tài liệu**: Xem và xóa các tài liệu đã tải lên

## Kết nối với API

Giao diện này kết nối với các API endpoint sau:

- `POST /api/query`: Gửi câu hỏi và nhận câu trả lời
- `POST /api/upload`: Tải file lên hệ thống
- `GET /api/files`: Lấy danh sách tài liệu đã tải lên
- `DELETE /api/files/{file_name}`: Xóa tài liệu
- `GET /api/index/progress/{task_id}`: Theo dõi tiến trình xử lý tài liệu

## Tùy chỉnh

Bạn có thể tùy chỉnh giao diện bằng cách chỉnh sửa:

1. `index.html` - Cấu trúc HTML cơ bản
2. `style.css` - CSS bổ sung ngoài Tailwind
3. `app.js` - Logic và tương tác với API

## Yêu cầu hệ thống

- Trình duyệt web hiện đại (Chrome, Firefox, Safari, Edge)
- Kết nối internet để tải CDN của Tailwind và Flowbite
- Backend API của hệ thống RAG đang chạy 