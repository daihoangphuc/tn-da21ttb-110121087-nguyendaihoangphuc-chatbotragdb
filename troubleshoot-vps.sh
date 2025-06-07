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
    environment:
      - USE_GEMINI=true
      - GEMINI_API_KEY=AIzaSyBuj64bK2ubgOv7cQTo0fVsDh0OOYoJRDg,AIzaSyDxT3CPjQzrgyoyXPUl9VK3Jj-wcaRdX_o,AIzaSyDSQkmsAIm_d62yXCu-iPyyU7vXEXVL0LA,AIzaSyDCeISy4laS1Skgnr_uYQiAsrlyLYdXptg,AIzaSyDXASZq2kt2s4AkwlnMiIqO3jkw7FOEoCc,AIzaSyAo37mPje3YHqjjk5qFIz7P1-nFGmWuEB4,AIzaSyCvVJFzZJq8t7XNEzwYTboFSTi9CZnpF1s,AIzaSyAUX-45CBoWfLvoOWzCzz_BddYE4514D8Y,AIzaSyBKH7G3Aai1JbfqApgwJH5jXQLF0Jj30sw,AIzaSyD5JqMWR2GPbVsdAC1nQ4CWvW8ZnnD3Oyk
      - QDRANT_URL=https://2f7481a0-b7e5-4785-afc0-14e7912f70d8.europe-west3-0.gcp.cloud.qdrant.io:6333/
      - QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.oD5nuszsntn8KKDUPDxB5UisjLYVEzonYaDByHdwFbg
      - QDRANT_COLLECTION_NAME=csdl_rag
      - TAVILY_API_KEY=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
      - EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
      - LLM_MODEL_NAME=gemini-2.0-flash
      - DEFAULT_ALPHA=0.7
      - CHUNK_SIZE=800
      - CHUNK_OVERLAP=200
      - SUPABASE_URL=https://yhlgzixdgvjllrblsxsr.supabase.co
      - SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlobGd6aXhkZ3ZqbGxyYmxzeHNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY3OTY1OTMsImV4cCI6MjA2MjM3MjU5M30.OHO8YwTzASgThYVPHFFEOu4COXKBhWnrVdy01c-PyrA
    restart: unless-stopped
    networks:
      - rag-network

  frontend:
    image: phuchoang1910/frontend:latest
    container_name: rag-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://rag-app:8000
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
sleep 10

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
