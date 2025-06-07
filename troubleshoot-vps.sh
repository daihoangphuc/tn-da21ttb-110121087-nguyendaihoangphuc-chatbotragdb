#!/bin/bash

# Script để khắc phục sự cố và chạy container trên VPS
# Chạy lệnh: bash troubleshoot-vps.sh

set -e

echo "🔍 Bắt đầu khắc phục sự cố và chạy container..."

# Kiểm tra Docker
echo "📋 Kiểm tra trạng thái Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker chưa được cài đặt. Đang cài đặt..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Đã cài đặt Docker thành công"
else
    echo "✅ Docker đã được cài đặt"
    docker --version
fi

# Kiểm tra Docker Compose
echo "📋 Kiểm tra Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose chưa được cài đặt. Đang cài đặt..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Đã cài đặt Docker Compose thành công"
else
    echo "✅ Docker Compose đã được cài đặt"
    docker-compose --version
fi

# Kiểm tra và hiển thị images
echo "📋 Kiểm tra Docker images đã pull về chưa..."
docker images

# Kiểm tra và dừng container đang chạy
echo "🛑 Dừng tất cả containers đang chạy (nếu có)..."
docker stop $(docker ps -a -q) 2>/dev/null || echo "Không có container nào đang chạy"
docker rm $(docker ps -a -q) 2>/dev/null || echo "Không có container nào để xóa"

# Đảm bảo thư mục app tồn tại
mkdir -p ~/app
cd ~/app

# Tạo file .env (bạn cần cập nhật nội dung này với các key thực tế)
echo "📝 Tạo file .env..."
cat > .env << 'EOF'
# Thay đổi các giá trị này với thông tin thực tế của bạn
USE_GEMINI=true
GEMINI_API_KEY=your_gemini_api_keys_here
QDRANT_URL=https://your-qdrant-url.com:6333/
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=csdl_rag
TAVILY_API_KEY=your_tavily_api_key
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
LLM_MODEL_NAME=gemini-2.0-flash
DEFAULT_ALPHA=0.7
CHUNK_SIZE=800
CHUNK_OVERLAP=200
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your_supabase_key
EOF

# Tạo file docker-compose.yml
echo "📝 Tạo file docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  rag-app:
    image: phuchoang1910/backend:latest
    container_name: rag-app
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - rag-network

  frontend:
    image: phuchoang1910/frontend:latest
    container_name: rag-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://34.30.191.213:8000/api
    depends_on:
      - rag-app
    restart: unless-stopped
    networks:
      - rag-network

networks:
  rag-network:
    driver: bridge
EOF

# Khởi chạy containers với docker-compose
echo "🚀 Khởi chạy containers với docker-compose..."
docker-compose up -d

# Đợi một chút để containers khởi động
echo "⏳ Đang đợi containers khởi động..."
sleep 30

# Kiểm tra trạng thái containers
echo "📋 Kiểm tra trạng thái containers..."
docker-compose ps
docker ps -a

# Kiểm tra logs
echo "📋 Kiểm tra logs của containers..."
echo "📊 Logs của backend:"
docker-compose logs --tail=20 rag-app
echo "📊 Logs của frontend:"
docker-compose logs --tail=20 frontend

echo "✅ Quá trình khắc phục sự cố và chạy container đã hoàn tất!"
echo "🌐 Bạn có thể truy cập ứng dụng tại:"
echo "   - Frontend: http://34.30.191.213:3000"
echo "   - Backend API: http://34.30.191.213:8000"
