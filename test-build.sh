#!/bin/bash

# Local development script to test Docker builds
set -e

echo "🚀 Testing local Docker builds..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create test environment files
echo "📝 Creating test environment files..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Created .env from .env.example. Please update with your actual values.${NC}"
fi

if [ ! -f "frontend/.env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > frontend/.env.local
    echo -e "${GREEN}✅ Created frontend/.env.local${NC}"
fi

# Test backend build
echo -e "${YELLOW}🔨 Building backend Docker image...${NC}"
if docker build -f Dockerfile.backend -t datn-backend:test .; then
    echo -e "${GREEN}✅ Backend build successful${NC}"
else
    echo -e "${RED}❌ Backend build failed${NC}"
    exit 1
fi

# Test frontend build
echo -e "${YELLOW}🔨 Building frontend Docker image...${NC}"
if docker build -f Dockerfile.frontend -t datn-frontend:test \
    --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000/api .; then
    echo -e "${GREEN}✅ Frontend build successful${NC}"
else
    echo -e "${RED}❌ Frontend build failed${NC}"
    exit 1
fi

# Test docker-compose
echo -e "${YELLOW}🔨 Testing docker-compose...${NC}"
if docker-compose config > /dev/null; then
    echo -e "${GREEN}✅ Docker-compose configuration is valid${NC}"
else
    echo -e "${RED}❌ Docker-compose configuration has errors${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 All builds completed successfully!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "   1. Update your GitHub secrets"
echo "   2. Push to main branch to trigger CI/CD"
echo "   3. Monitor deployment at https://github.com/YOUR_USERNAME/YOUR_REPO/actions"
