# Hướng dẫn cài đặt Docker cho dự án RAG

## Chuẩn bị môi trường

### 1. Cài đặt Docker và Docker Compose
- Cài đặt Docker: [Hướng dẫn cài đặt Docker](https://docs.docker.com/get-docker/)
- Cài đặt Docker Compose: [Hướng dẫn cài đặt Docker Compose](https://docs.docker.com/compose/install/)

### 2. Cấu hình biến môi trường
- Sao chép file `.env.example` thành `.env` và cập nhật các giá trị:
  ```bash
  cp .env.example .env
  ```
- Cập nhật các biến môi trường trong file `.env`, đặc biệt là:
  - `GOOGLE_API_KEY`: API key của Google Generative AI
  - `QDRANT_URL`: URL của Qdrant (mặc định là `http://qdrant:6333` khi sử dụng Docker Compose)
  - `SUPABASE_URL` và `SUPABASE_KEY` (nếu sử dụng Supabase)

## Chạy ứng dụng với Docker Compose

### 1. Build và khởi động các dịch vụ
```bash
docker-compose up -d --build
```

### 2. Kiểm tra trạng thái các dịch vụ
```bash
docker-compose ps
```

### 3. Xem logs của ứng dụng
```bash
docker-compose logs -f rag-app
```

### 4. Dừng các dịch vụ
```bash
docker-compose down
```

## Cấu trúc Docker

### 1. Dockerfile
- Base image: Python 3.10
- Cài đặt LibreOffice để xử lý các định dạng tài liệu
- Cài đặt các dependencies từ `requirements.txt`
- Khởi động ứng dụng FastAPI với Uvicorn

### 2. docker-compose.yml
- **rag-app**: Dịch vụ chính chạy ứng dụng RAG
  - Port: 8000
  - Volumes:
    - `./src:/app/src`: Mount thư mục mã nguồn
    - `./data:/app/data`: Mount thư mục dữ liệu
  
- **qdrant**: Vector database
  - Ports: 6333, 6334
  - Volume: `qdrant-data` để lưu trữ dữ liệu

## CI/CD với GitHub Actions

Dự án đã được cấu hình với GitHub Actions để tự động hóa quy trình CI/CD:

1. **Build và Test**:
   - Checkout code
   - Cài đặt dependencies
   - Chạy tests
   - Build Docker image
   - Push Docker image lên Docker Hub (chỉ khi push vào nhánh main)

2. **Deploy**:
   - Triển khai tự động khi có push vào nhánh main
   - Cần cấu hình thêm các bước triển khai cụ thể cho server của bạn

### Cấu hình GitHub Secrets
Để CI/CD hoạt động, bạn cần thêm các secrets sau vào GitHub repository:
- `DOCKERHUB_USERNAME`: Tên người dùng Docker Hub
- `DOCKERHUB_TOKEN`: Token xác thực Docker Hub

## Lưu ý quan trọng

1. **Bảo mật**:
   - Không commit file `.env` chứa thông tin nhạy cảm lên Git
   - Sử dụng GitHub Secrets để lưu trữ thông tin xác thực

2. **Dữ liệu**:
   - Dữ liệu Qdrant được lưu trong Docker volume `qdrant-data`
   - Để sao lưu dữ liệu, bạn có thể sử dụng Docker volume backup

3. **Tùy chỉnh**:
   - Điều chỉnh cấu hình trong `docker-compose.yml` theo nhu cầu
   - Có thể thêm các dịch vụ khác như Supabase local nếu cần 