# RAG Pipeline API

API cho hệ thống RAG sử dụng chunking và clustering.

## Cài đặt

Để chạy API, cần cài đặt các thư viện sau:

```bash
pip install fastapi uvicorn python-multipart
```

## Chạy API

Từ thư mục gốc của dự án, chạy lệnh sau:

```bash
python -m src.api.main --host 0.0.0.0 --port 8000 --reload
```

Các tham số:
- `--host`: Host để chạy API (mặc định: 0.0.0.0)
- `--port`: Port để chạy API (mặc định: 8000)
- `--reload`: Tự động reload khi code thay đổi (tùy chọn)

## API Endpoints

### Kiểm tra trạng thái API

```
GET /
```

Response:
```json
{
  "message": "API hệ thống RAG đang hoạt động"
}
```

### Truy vấn dữ liệu

```
POST /query
```

Request body:
```json
{
  "query": "Câu truy vấn của bạn"
}
```

Response:
```json
{
  "response": "Câu trả lời từ hệ thống RAG"
}
```

### Upload và index tài liệu

```
POST /upload
```

Form data:
- `files`: Các file cần upload và index (lưu vào thư mục D:\DATN\V2\src\data)

Response:
```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "message": "Đã upload và bắt đầu quá trình indexing X file"
}
```

### Index dữ liệu từ các file

```
POST /index/files
```

Form data:
- `files`: Các file cần index (lưu vào thư mục tạm)

Response:
```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "message": "Đã bắt đầu quá trình indexing X file"
}
```

### Index dữ liệu từ thư mục

```
POST /index/path
```

Form data:
- `directory`: Đường dẫn đến thư mục cần index

Response:
```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "message": "Đã bắt đầu quá trình indexing từ thư mục X"
}
```

### Kiểm tra trạng thái indexing

```
GET /index/status/{task_id}
```

Response:
```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "running|completed|failed",
  "message": "Thông tin về trạng thái"
}
```

### Kiểm tra tiến trình chi tiết

```
GET /index/progress/{task_id}
```

Response:
```json
{
  "task_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "running|completed|failed",
  "message": "Thông tin về trạng thái",
  "progress": {
    "step": "loading|chunking|clustering|vectorizing|completed",
    "step_name": "Tên bước hiện tại",
    "completed_steps": 1,
    "total_steps": 4,
    "progress_percent": 0.25,
    "start_time": 1625482800.123,
    "current_time": 1625482830.456,
    "elapsed_time": 30.333,
    "estimated_time_remaining": 90.999
  }
}
```

### Liệt kê tất cả files

```
GET /files
```

Response:
```json
[
  {
    "name": "document.pdf",
    "path": "D:\\DATN\\V2\\src\\data\\upload_20240501_123456\\document.pdf",
    "size": 1048576,
    "last_modified": 1625482800.123
  },
  {
    "name": "data.docx",
    "path": "D:\\DATN\\V2\\src\\data\\upload_20240502_123456\\data.docx",
    "size": 524288,
    "last_modified": 1625482700.456
  }
]
```

### Xóa file và embedding tương ứng

```
DELETE /files/{file_name}?upload_dir={upload_dir}
```

Parameters:
- `file_name`: Tên file cần xóa (đường dẫn)
- `upload_dir` (tùy chọn): Tên thư mục upload chứa file

Response:
```json
{
  "deleted_file": "D:\\DATN\\V2\\src\\data\\upload_20240501_123456\\document.pdf",
  "deleted_embeddings": 15,
  "success": true,
  "message": "Đã xóa file: document.pdf và 15 embedding liên quan"
}
```

### Liệt kê các thư mục upload

```
GET /uploads
```

Response:
```json
{
  "uploads": [
    {
      "name": "upload_20240501_123456",
      "path": "D:\\DATN\\V2\\src\\data\\upload_20240501_123456",
      "files": ["file1.pdf", "file2.docx"],
      "file_count": 2
    }
  ]
}
```

### Xóa index

```
DELETE /index
```

Response:
```json
{
  "message": "Đã xóa index thành công"
}
```

## Ví dụ sử dụng với curl

### Upload và index tài liệu

```bash
curl -X 'POST' \
  'http://localhost:8000/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@/path/to/file1.pdf' \
  -F 'files=@/path/to/file2.docx'
```

### Truy vấn

```bash
curl -X 'POST' \
  'http://localhost:8000/query' \
  -H 'Content-Type: application/json' \
  -d '{"query": "Câu truy vấn của tôi?"}'
```

### Liệt kê tất cả files

```bash
curl -X 'GET' \
  'http://localhost:8000/files'
```

### Xóa file và embedding tương ứng

```bash
curl -X 'DELETE' \
  'http://localhost:8000/files/document.pdf'
```

### Xóa file trong thư mục cụ thể

```bash
curl -X 'DELETE' \
  'http://localhost:8000/files/document.pdf?upload_dir=upload_20240501_123456'
```

### Index dữ liệu từ thư mục

```bash
curl -X 'POST' \
  'http://localhost:8000/index/path' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'directory=/đường/dẫn/đến/thư/mục/dữ/liệu'
```

### Kiểm tra trạng thái indexing

```bash
curl -X 'GET' \
  'http://localhost:8000/index/status/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

### Kiểm tra tiến trình chi tiết

```bash
curl -X 'GET' \
  'http://localhost:8000/index/progress/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
```

### Liệt kê các thư mục upload

```bash
curl -X 'GET' \
  'http://localhost:8000/uploads'
```

### Xóa index

```bash
curl -X 'DELETE' \
  'http://localhost:8000/index'
```

## Theo dõi tiến trình xử lý

Hệ thống hỗ trợ theo dõi chi tiết tiến trình xử lý qua API `/index/progress/{task_id}`. Quy trình xử lý gồm 4 bước chính:

1. **Loading** (0-25%): Load tài liệu từ thư mục
2. **Chunking** (25-50%): Chia nhỏ tài liệu thành các chunk
3. **Clustering** (50-75%): Phân cụm và gộp các chunk liên quan
4. **Vectorizing** (75-100%): Upload vào vector database

Thông tin progress trả về bao gồm thời gian đã trôi qua và ước tính thời gian còn lại, giúp người dùng đánh giá được thời gian cần thiết để hoàn thành quá trình xử lý. 