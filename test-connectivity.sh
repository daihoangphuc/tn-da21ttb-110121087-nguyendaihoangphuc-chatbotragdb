#!/bin/bash

# Script để test kết nối giữa các services
echo "🧪 Testing connectivity between services..."

# Kiểm tra các containers đang chạy
echo "📋 Checking running containers..."
docker ps

echo ""
echo "🔍 Testing backend API..."

# Test backend từ host
echo "Testing backend from host..."
if curl -f -s http://localhost:8000/api/ > /dev/null; then
    echo "✅ Backend accessible from host"
    curl -s http://localhost:8000/api/ | head -3
else
    echo "❌ Backend not accessible from host"
fi

# Test backend từ frontend container
echo "Testing backend from frontend container..."
if docker exec rag-frontend curl -f -s http://rag-app:8000/api/ > /dev/null 2>&1; then
    echo "✅ Backend accessible from frontend container"
else
    echo "❌ Backend not accessible from frontend container"
fi

echo ""
echo "🔍 Testing frontend..."

# Test frontend từ host
echo "Testing frontend from host..."
if curl -f -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend accessible from host"
else
    echo "❌ Frontend not accessible from host"
fi

echo ""
echo "🌐 Testing external access (if on VPS)..."

# Test external IP (nếu đang trên VPS)
EXTERNAL_IP="34.30.191.213"

echo "Testing backend external access..."
if curl -f -s http://$EXTERNAL_IP:8000/api/ > /dev/null; then
    echo "✅ Backend accessible externally"
else
    echo "❌ Backend not accessible externally"
fi

echo "Testing frontend external access..."
if curl -f -s http://$EXTERNAL_IP:3000 > /dev/null; then
    echo "✅ Frontend accessible externally"
else
    echo "❌ Frontend not accessible externally"
fi

echo ""
echo "📊 Container logs summary..."
echo "Backend logs (last 10 lines):"
docker logs rag-app --tail=10 2>/dev/null || echo "Backend container not found"

echo ""
echo "Frontend logs (last 10 lines):"
docker logs rag-frontend --tail=10 2>/dev/null || echo "Frontend container not found"

echo ""
echo "✅ Connectivity test completed!"
