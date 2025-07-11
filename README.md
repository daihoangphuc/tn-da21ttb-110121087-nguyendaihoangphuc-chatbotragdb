# Hệ thống RAG cho Cơ sở dữ liệu

Hệ thống chatbot hỗ trợ môn học cơ sở dữ liệu sử dụng Retrieval-Augmented Generation (RAG).

## Cấu trúc dự án

```
V2/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD pipeline
├── docs/                       # Tài liệu
├── src/                        # Source code chính
│   ├── .dockerignore.backend   # Docker ignore cho backend
│   ├── .dockerignore.frontend  # Docker ignore cho frontend
│   ├── .env                    # Environment variables
│   ├── .env.example           # Environment template
│   ├── docker-compose.yml     # Docker compose configuration
│   ├── Dockerfile.backend     # Backend Dockerfile
│   ├── Dockerfile.frontend    # Frontend Dockerfile
│   ├── requirements.txt       # Python dependencies
│   ├── backend/              # Backend code
│   │   ├── api.py           # FastAPI application
│   │   ├── rag.py           # RAG system
│   │   ├── llm.py           # LLM integration
│   │   ├── vector_store.py  # Vector database
│   │   ├── supabase/        # Supabase integration
│   │   ├── test/            # Backend tests
│   │   └── ...
│   └── frontend/            # Frontend code
│       ├── app/             # Next.js app directory
│       ├── components/      # React components
│       ├── package.json     # Node.js dependencies
│       └── ...
└── README.md
```

## Yêu cầu hệ thống

- Docker & Docker Compose
- Node.js 20+ (để phát triển frontend)
- Python 3.10+ (để phát triển backend)

## Cài đặt và chạy

### 1. Sao chép dự án

```bash
git clone <repository-url>
cd V2
```

### 2. Cấu hình môi trường

Tạo file `.env` trong thư mục `src/` bằng cách copy nội dung dưới đây:

```bash
# src/.env
# Supabase Configuration
SUPABASE_URL="your-supabase-url"
SUPABASE_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_KEY="your-supabase-service-key"

# LLM Configuration
GEMINI_API_KEY="your-gemini-api-key"

# Vector Store Configuration (nếu dùng Qdrant)
QDRANT_URL="your-qdrant-url"
QDRANT_API_KEY="your-qdrant-api-key"

# Environment variables for Docker Compose
# Các biến này được sử dụng khi chạy với docker-compose
DOCKERHUB_USERNAME="your-dockerhub-username"
TAG="latest"
FRONTEND_URL="http://localhost:3000"
CORS_ORIGINS="http://localhost:3000"
NEXT_PUBLIC_API_URL="http://localhost:8000/api"
```

**Lưu ý:**
- Các biến `SUPABASE_*` và `GEMINI_API_KEY` là bắt buộc cho cả khi chạy bằng Docker và chạy local.
- Các biến còn lại (`DOCKERHUB_USERNAME`, `TAG`, `FRONTEND_URL`, `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`) chủ yếu dành cho `docker-compose`. Khi chạy local, các giá trị này sẽ được override bởi code.

### 3. Chạy hệ thống với Docker (Khuyến khích)

Đây là cách đơn giản nhất để chạy toàn bộ hệ thống.

```bash
cd src
docker-compose up --build
```

Hệ thống sẽ khởi động với:
- **Backend:** `http://localhost:8000` (API docs tại `http://localhost:8000/docs`)
- **Frontend:** `http://localhost:3000`

Frontend đã được cấu hình để tự động kết nối với backend qua địa chỉ trên.

### 4. Chạy riêng từng service (Dành cho Development)

Nếu bạn muốn phát triển và xem thay đổi ngay lập tức (hot-reloading).

**Chạy Backend:**
```bash
# Từ thư mục gốc V2/
cd src/backend
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
pip install -r ../requirements.txt

# Chạy FastAPI server
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
- **Quan trọng:** Backend cần các biến môi trường `SUPABASE_*` và `GEMINI_API_KEY`. Hãy đảm bảo file `src/.env` đã được tạo và cấu hình đúng. Backend sẽ tự động đọc file này.

**Chạy Frontend:**
```bash
# Từ thư mục gốc V2/
cd src/frontend
pnpm install
pnpm dev
```
- Frontend sẽ chạy tại `http://localhost:3000` và tự động kết nối đến backend tại `http://localhost:8000/api` nhờ cấu hình trong `src/frontend/lib/config.ts`. Bạn không cần set `NEXT_PUBLIC_API_URL` khi chạy local.

## Phát triển (Development)

### Backend Development

```bash
cd src/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd src/frontend
pnpm install
pnpm dev
```

### Chạy tests

```bash
cd src
python -m pytest backend/test/ -v
```

## Build và Deploy

### Build local images

```bash
# Build backend
docker build -f src/Dockerfile.backend -t db-rag-backend:local .

# Build frontend
docker build -f src/Dockerfile.frontend -t db-rag-frontend:local .
```

### CI/CD với GitHub Actions

Dự án sử dụng GitHub Actions để tự động build và deploy:

1. **Build Stage**: Build Docker images cho cả backend và frontend
2. **Deploy Stage**: Deploy lên VPS với Nginx và SSL

#### Cấu hình GitHub Secrets

Cần cấu hình các secrets sau trong GitHub repository:

```
DOCKERHUB_USERNAME=your-dockerhub-username
DOCKERHUB_TOKEN=your-dockerhub-token
VPS_HOST=your-vps-ip
VPS_USER=your-vps-username
VPS_SSH_KEY=your-private-ssh-key
BACKEND_ENV=your-backend-environment-variables
FRONTEND_ENV=your-frontend-environment-variables
```

## API Documentation

Sau khi chạy backend, truy cập:
- API Docs: http://localhost:8000/docs

## Các lệnh Docker hữu ích

```bash
# Xem logs
cd src && docker-compose logs -f

# Dừng services
cd src && docker-compose down

# Dừng và xóa volumes
cd src && docker-compose down -v

# Rebuild từ đầu
cd src && docker-compose up --build --force-recreate

# Xóa tất cả containers và images không sử dụng
docker system prune -a
```

## Troubleshooting

### 1. Port đã được sử dụng
```bash
# Kiểm tra port đang sử dụng
netstat -tulpn | grep :3000
netstat -tulpn | grep :8000

# Hoặc trên Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Dừng tất cả containers
cd src && docker-compose down
```

### 2. Permission denied với Docker
```bash
# Linux/Mac: Thêm user vào group docker
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Build lỗi do cache
```bash
# Build lại không sử dụng cache
cd src && docker-compose build --no-cache
```

### 4. Lỗi kết nối database
- Kiểm tra file `.env` có đúng thông tin Supabase không
- Đảm bảo Supabase project đang hoạt động
- Kiểm tra network connectivity

### 5. Frontend không connect được với Backend
- Kiểm tra biến `NEXT_PUBLIC_API_URL` trong environment
- Đảm bảo backend đang chạy và healthy
- Kiểm tra CORS settings trong backend

## Các tính năng chính

- **Hỏi đáp thông minh**: Trả lời câu hỏi dựa trên tài liệu đã upload
- **Quản lý hội thoại**: Lưu trữ và tìm kiếm lịch sử chat
- **Quản lý tài liệu**: Upload và quản lý file PDF, DOCX, TXT
- **Quản lý người dùng**: Phân quyền Admin/Student
- **Authentication**: Đăng ký/đăng nhập với Supabase Auth
- **Responsive UI**: Giao diện thân thiện trên mọi thiết bị

