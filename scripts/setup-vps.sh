#!/bin/bash

# VPS Setup Script for Docker and Application Deployment
# Run this script on your VPS to prepare it for deployment

set -e

echo "🚀 Setting up VPS for Docker deployment..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Create application directory
mkdir -p /home/$USER/app
cd /home/$USER/app

# Create data directory for persistent storage
mkdir -p ./data

# Set proper permissions
sudo chown -R $USER:$USER /home/$USER/app

# Create a simple nginx proxy configuration (optional)
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server rag-app:8000;
    }
    
    upstream frontend {
        server rag-frontend:3000;
    }

    server {
        listen 80;
        server_name _;

        # Frontend routes
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API routes
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

echo "🎉 VPS setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Add GitHub Secrets with the following keys:"
echo "   - VPS_HOST: 34.30.191.213"
echo "   - VPS_USER: nguyendaihoangphuc1911"
echo "   - VPS_SSH_KEY: (content of your private key)"
echo "   - DOCKERHUB_USERNAME: (your Docker Hub username)"
echo "   - DOCKERHUB_TOKEN: (your Docker Hub token)"
echo "   - BACKEND_ENV: (your backend .env content)"
echo "   - FRONTEND_ENV: (your frontend .env content)"
echo ""
echo "2. Push to GitHub and the deployment will start automatically!"
echo ""
echo "🌐 Your application will be available at:"
echo "   - Frontend: http://34.30.191.213:3000"
echo "   - Backend API: http://34.30.191.213:8000"
echo "   - Qdrant: http://34.30.191.213:6333"
