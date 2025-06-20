# Thay đổi giới hạn file upload từ 50MB xuống 10MB

## Tóm tắt thay đổi

Đã cập nhật toàn bộ hệ thống để giới hạn file upload tối đa **10MB** thay vì 50MB trước đây.

## 🔧 Thay đổi Backend

### 1. API Endpoint (`src/api.py`)

**Thêm middleware kiểm tra request body size:**
```python
@app.middleware("http")
async def limit_upload_size(request: Request, call_next):
    if request.url.path.endswith("/upload"):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            max_size = 10 * 1024 * 1024  # 10MB
            if content_length > max_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body quá lớn. Kích thước tối đa: 10MB"}
                )
```

**Thêm validation trong upload endpoint:**
```python
# KIỂM TRA KÍCH THƯỚC FILE (10MB limit)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
if file.size and file.size > MAX_FILE_SIZE:
    raise HTTPException(
        status_code=413,
        detail=f"File quá lớn. Kích thước tối đa cho phép là 10MB. File của bạn: {file.size / (1024*1024):.2f}MB"
    )
```

## 🎨 Thay đổi Frontend

### 1. Admin Files Manager (`frontend/components/admin-files-manager.tsx`)
- Cập nhật validation từ 50MB → 10MB
- Cập nhật thông báo lỗi
- Cập nhật dialog description

### 2. Admin Settings (`frontend/components/admin-settings.tsx`)
- Cập nhật default value từ 50 → 10MB

### 3. File Uploader (`frontend/components/file-uploader.tsx`)
- Cập nhật description hiển thị giới hạn 10MB

### 4. API Library (`frontend/lib/api.ts`)
- Thêm validation 10MB trước khi gửi request
- Cập nhật thông báo lỗi chi tiết
- Cập nhật danh sách file types hỗ trợ

## 📝 Tệp được thay đổi

1. `src/api.py` - Backend validation và middleware
2. `frontend/components/admin-files-manager.tsx` - Admin file upload
3. `frontend/components/admin-settings.tsx` - Settings display
4. `frontend/components/file-uploader.tsx` - User file upload
5. `frontend/lib/api.ts` - API client validation

## ✅ Tính năng mới

### Backend
- **HTTP 413 status code** cho file quá lớn
- **Middleware validation** kiểm tra Content-Length header
- **File size validation** trong upload endpoint
- **Chi tiết thông báo lỗi** với kích thước file thực tế

### Frontend
- **Pre-upload validation** tại client
- **Thông báo lỗi rõ ràng** với kích thước file
- **UI updates** hiển thị giới hạn 10MB
- **Consistent validation** across all upload components

## 🔍 File types được hỗ trợ

- PDF (.pdf)
- Microsoft Word (.docx, .doc)
- Text files (.txt)
- Markdown (.md)
- SQL files (.sql)

**Tất cả đều giới hạn tối đa 10MB**

## 🚀 Lợi ích

1. **Tiết kiệm bandwidth** - Giảm tải mạng
2. **Faster processing** - Xử lý file nhỏ nhanh hơn
3. **Better UX** - Validation ngay tại client
4. **Consistent limits** - Đồng nhất giữa frontend và backend
5. **Clear error messages** - Thông báo lỗi dễ hiểu

## 🧪 Testing

Để test giới hạn mới:

1. **File nhỏ (< 10MB)**: Upload thành công
2. **File lớn (> 10MB)**: 
   - Frontend: Hiển thị lỗi trước khi upload
   - Backend: Trả về HTTP 413 nếu bypass client validation
3. **File type sai**: Hiển thị lỗi định dạng không hỗ trợ 