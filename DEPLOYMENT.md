# CI/CD Deployment Guide

This guide explains how to set up the CI/CD pipeline for your DATN project using GitHub Actions.

## Prerequisites

### 1. VPS Setup
Ensure your VPS has the following installed:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. GitHub Secrets Configuration

Set up the following secrets in your GitHub repository (Settings > Secrets and variables > Actions):

#### Required Secrets:

1. **DOCKERHUB_USERNAME**: Your Docker Hub username
2. **DOCKERHUB_TOKEN**: Your Docker Hub access token
3. **VPS_HOST**: Your VPS IP address or domain
4. **VPS_USER**: Your VPS username (usually `root` or your username)
5. **VPS_SSH_KEY**: Your private SSH key for VPS access

6. **BACKEND_ENV**: Complete backend environment variables
```env
USE_GEMINI=true
API_KEY_LLM_SEARCH_TOOL=your_key_here
GEMINI_API_KEY=your_gemini_keys_here
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_key
QDRANT_COLLECTION_NAME=csdl_rag
TAVILY_API_KEY=your_tavily_key
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
LLM_MODEL_NAME=gemini-2.0-flash
LLM_TEMPERATURE=0
LLM_TOP_P=0.85
API_PREFIX=/api
API_TITLE="Hệ thống RAG cho Cơ sở dữ liệu"
API_DESCRIPTION="API cho hệ thống tìm kiếm và trả lời câu hỏi sử dụng RAG"
API_VERSION="1.0.0"
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_BATCH_SIZE=64
MAX_PARALLEL_WORKERS=8
DEFAULT_ALPHA=0.7
CHUNK_SIZE=800
CHUNK_OVERLAP=200
```

7. **FRONTEND_ENV**: Frontend environment variables
```env
NEXT_PUBLIC_API_URL=http://YOUR_VPS_IP:8000/api
```

### 3. SSH Key Setup

Generate SSH key pair for GitHub Actions:
```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -C "github-actions" -f ~/.ssh/github-actions

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/github-actions.pub user@your-vps-ip

# Add private key content to GITHUB SECRET: VPS_SSH_KEY
cat ~/.ssh/github-actions
```

## Workflow Overview

The CI/CD pipeline consists of two main workflows:

### 1. Development Build (`dev-build.yml`)
- Triggered on: Push to non-main branches, Pull requests
- Actions:
  - Test backend Python code
  - Test frontend TypeScript/React code
  - Build Docker images for testing (PR only)

### 2. Production Deployment (`ci-cd.yml`)
- Triggered on: Push to main/master branch
- Actions:
  - Build Docker images for backend and frontend
  - Push images to Docker Hub with proper tags
  - Deploy to VPS using SSH
  - Verify deployment health

## Deployment Process

### Step 1: Push to Main Branch
When you push to the main branch, the following happens:

1. **Build Phase**:
   - Creates production Docker images
   - Tags with latest, branch name, and commit SHA
   - Pushes to Docker Hub

2. **Deploy Phase**:
   - Connects to VPS via SSH
   - Creates docker-compose.prod.yml
   - Pulls latest images
   - Stops old containers
   - Starts new containers with proper networking
   - Verifies health checks

### Step 2: Network Configuration
The containers are connected via a Docker bridge network (`datn-network`):
- Backend: Available at `backend:8000` internally, `localhost:8000` externally
- Frontend: Available at `frontend:3000` internally, `localhost:3000` externally
- Frontend communicates with backend using internal Docker network

### Step 3: Health Checks
Both services have health checks:
- Backend: `curl -f http://localhost:8000/health`
- Frontend: `wget --spider http://localhost:3000`

## Manual Deployment Commands

If you need to deploy manually on the VPS:

```bash
# SSH to your VPS
ssh user@your-vps-ip

# Navigate to deployment directory
cd ~/datn-deployment

# Pull latest images
docker pull your-dockerhub-username/datn-backend:latest
docker pull your-dockerhub-username/datn-frontend:latest

# Stop existing containers
docker-compose -f docker-compose.prod.yml down

# Start new containers
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

## Troubleshooting

### Common Issues:

1. **Build Failures**:
   - Check GitHub Actions logs
   - Verify environment variables in secrets
   - Ensure Dockerfile syntax is correct

2. **Deployment Failures**:
   - Verify VPS SSH access
   - Check Docker/Docker Compose installation
   - Verify secrets configuration

3. **Container Health Check Failures**:
   - Check container logs: `docker-compose logs service-name`
   - Verify environment variables
   - Check network connectivity

4. **Frontend API Connection Issues**:
   - Ensure NEXT_PUBLIC_API_URL points to correct backend
   - Verify backend is healthy and accessible
   - Check Docker network configuration

### Monitoring Commands:

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend

# Test API health
curl http://localhost:8000/health
curl http://localhost:3000

# Check Docker networks
docker network ls
docker network inspect datn-deployment_datn-network
```

## Security Considerations

1. **SSH Keys**: Use dedicated SSH keys for GitHub Actions
2. **Environment Variables**: Store sensitive data in GitHub Secrets
3. **Docker Images**: Regularly update base images for security patches
4. **VPS Security**: Configure firewall and fail2ban on VPS
5. **HTTPS**: Consider setting up reverse proxy with SSL (Nginx/Traefik)

## Updating the Pipeline

To modify the deployment:

1. Update workflow files in `.github/workflows/`
2. Modify Docker configurations if needed
3. Update environment variables in GitHub Secrets
4. Test changes in feature branches before merging to main

## Production Considerations

For production deployment, consider:

1. **Database Persistence**: Ensure data volumes are properly mounted
2. **Backup Strategy**: Regular backups of application data
3. **Monitoring**: Set up application monitoring (Prometheus, Grafana)
4. **Logging**: Centralized logging solution
5. **Load Balancing**: If scaling multiple instances
6. **SSL/TLS**: HTTPS certificates for production domains
