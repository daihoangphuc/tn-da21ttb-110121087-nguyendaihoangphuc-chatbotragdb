#!/bin/bash

# Final CI/CD Pipeline Validation Script
# This script validates all components before deployment

set -e

echo "🔍 DATN CI/CD Pipeline Validation"
echo "================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if Docker is installed and running
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        print_status 0 "Docker is installed and running"
    else
        print_status 1 "Docker is installed but not running"
        exit 1
    fi
else
    print_status 1 "Docker is not installed"
    exit 1
fi

# Check if Docker Compose is available
echo "2. Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_status 0 "Docker Compose is available"
else
    print_status 1 "Docker Compose is not available"
    exit 1
fi

# Validate Dockerfile.backend
echo "3. Validating Dockerfile.backend..."
if [ -f "Dockerfile.backend" ]; then
    if docker build -f Dockerfile.backend -t datn-backend-test . --no-cache &> /dev/null; then
        print_status 0 "Dockerfile.backend is valid"
        docker rmi datn-backend-test &> /dev/null || true
    else
        print_status 1 "Dockerfile.backend has issues"
    fi
else
    print_status 1 "Dockerfile.backend not found"
fi

# Validate Dockerfile.frontend
echo "4. Validating Dockerfile.frontend..."
if [ -f "Dockerfile.frontend" ]; then
    if docker build -f Dockerfile.frontend -t datn-frontend-test . --no-cache &> /dev/null; then
        print_status 0 "Dockerfile.frontend is valid"
        docker rmi datn-frontend-test &> /dev/null || true
    else
        print_status 1 "Dockerfile.frontend has issues"
    fi
else
    print_status 1 "Dockerfile.frontend not found"
fi

# Validate docker-compose.yml
echo "5. Validating docker-compose.yml..."
if [ -f "docker-compose.yml" ]; then
    if docker-compose config &> /dev/null; then
        print_status 0 "docker-compose.yml is valid"
    else
        print_status 1 "docker-compose.yml has syntax errors"
    fi
else
    print_status 1 "docker-compose.yml not found"
fi

# Check GitHub Actions workflow files
echo "6. Checking GitHub Actions workflows..."
if [ -f ".github/workflows/ci-cd.yml" ]; then
    print_status 0 "ci-cd.yml workflow exists"
else
    print_status 1 "ci-cd.yml workflow not found"
fi

if [ -f ".github/workflows/dev-build.yml" ]; then
    print_status 0 "dev-build.yml workflow exists"
else
    print_status 1 "dev-build.yml workflow not found"
fi

# Check for required files
echo "7. Checking required files..."
required_files=(
    "requirements.txt"
    "frontend/package.json"
    "src/api.py"
    "DEPLOYMENT.md"
    "setup-vps.sh"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "$file exists"
    else
        print_status 1 "$file missing"
    fi
done

# Test environment file creation
echo "8. Testing environment file structure..."
if [ -f ".env.example" ]; then
    print_status 0 ".env.example found"
else
    print_warning "No .env.example found - make sure you have environment templates"
fi

# Check network connectivity requirements
echo "9. Checking network requirements..."
if curl -s --max-time 10 https://hub.docker.com &> /dev/null; then
    print_status 0 "Docker Hub connectivity"
else
    print_status 1 "Cannot reach Docker Hub"
fi

if curl -s --max-time 10 https://github.com &> /dev/null; then
    print_status 0 "GitHub connectivity"
else
    print_status 1 "Cannot reach GitHub"
fi

echo
echo "🎯 DEPLOYMENT READINESS CHECKLIST"
echo "================================="

# GitHub Secrets Checklist
echo "📋 GitHub Secrets to verify in your repository:"
echo "   □ DOCKERHUB_USERNAME"
echo "   □ DOCKERHUB_TOKEN"
echo "   □ VPS_HOST"
echo "   □ VPS_USER"
echo "   □ VPS_SSH_KEY"
echo "   □ BACKEND_ENV"
echo "   □ FRONTEND_ENV"
echo

# VPS Checklist
echo "🖥️  VPS Setup Checklist:"
echo "   □ Run setup-vps.sh on your VPS"
echo "   □ Docker and Docker Compose installed"
echo "   □ SSH key configured for GitHub Actions"
echo "   □ Firewall configured (ports 22, 80, 443, 3000, 8000)"
echo "   □ Domain/IP accessible from internet"
echo

# Final Steps
echo "🚀 Final Deployment Steps:"
echo "   1. Verify all GitHub secrets are set"
echo "   2. Run setup-vps.sh on your VPS"
echo "   3. Test SSH connection: ssh user@your-vps-ip"
echo "   4. Push code to main branch"
echo "   5. Monitor GitHub Actions: https://github.com/YOUR_USERNAME/YOUR_REPO/actions"
echo "   6. Check deployment: http://YOUR_VPS_IP:3000"
echo

echo "✨ Pipeline validation completed!"
echo "If all checks passed, your CI/CD pipeline is ready for deployment."
