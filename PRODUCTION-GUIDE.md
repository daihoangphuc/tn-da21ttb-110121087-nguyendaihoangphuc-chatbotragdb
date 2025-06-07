# 🚀 DATN Production Deployment Guide

## ✅ Pipeline Status: READY FOR DEPLOYMENT

Your CI/CD pipeline is now fully configured and ready for production deployment!

## 📋 Pre-Deployment Checklist

### 1. Local Validation
Run the validation script to ensure everything is ready:

**Windows:**
```powershell
.\validate-pipeline.ps1
```

**Linux/Mac:**
```bash
bash validate-pipeline.sh
```

### 2. GitHub Repository Setup

#### Required Secrets (Repository Settings → Secrets and Variables → Actions)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | `your-username` |
| `DOCKERHUB_TOKEN` | Docker Hub access token | `dckr_pat_xxxxx` |
| `VPS_HOST` | Your VPS IP address | `123.456.789.012` |
| `VPS_USER` | SSH username for VPS | `root` or `ubuntu` |
| `VPS_SSH_KEY` | Private SSH key content | `-----BEGIN OPENSSH PRIVATE KEY-----` |
| `BACKEND_ENV` | Backend environment variables | Complete .env content |
| `FRONTEND_ENV` | Frontend environment variables | `NEXT_PUBLIC_API_URL=http://YOUR_VPS_IP:8000/api` |

#### Setting Up Secrets:
1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret from the table above

### 3. VPS Preparation

#### Option A: Automated Setup
```bash
# Copy the setup script to your VPS
scp setup-vps.sh user@your-vps-ip:~/

# SSH to your VPS and run the setup
ssh user@your-vps-ip
sudo bash ~/setup-vps.sh
```

#### Option B: Manual Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# Logout and login again for docker group changes
exit
```

## 🚀 Deployment Process

### Step 1: Final Validation
```bash
# Run validation script
bash validate-pipeline.sh
```

### Step 2: Push to Production
```bash
# Make sure you're on the main branch
git checkout main

# Push your code (this triggers the CI/CD pipeline)
git push origin main
```

### Step 3: Monitor Deployment
1. Go to your GitHub repository
2. Click on "Actions" tab
3. Watch the CI/CD pipeline execution
4. Monitor both "Build and Push" and "Deploy" jobs

## 📊 Pipeline Workflow

### Build Phase
1. **Checkout code** from repository
2. **Build Docker images** for backend and frontend
3. **Tag images** with latest, branch name, and commit SHA
4. **Push images** to Docker Hub
5. **Run in parallel** for both services

### Deploy Phase (only on main branch)
1. **SSH to VPS** and prepare deployment files
2. **Create production docker-compose.yml**
3. **Pull latest images** from Docker Hub
4. **Stop old containers** gracefully
5. **Start new containers** with health checks
6. **Verify deployment** with automated tests

## 🔍 Monitoring & Verification

### Check Deployment Status
```bash
# SSH to your VPS
ssh user@your-vps-ip

# Check running containers
docker ps

# Check service health
curl http://localhost:8000/health  # Backend
curl http://localhost:3000         # Frontend

# View logs
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml logs -f
```

### Access Your Application
- **Frontend:** `http://YOUR_VPS_IP:3000`
- **Backend API:** `http://YOUR_VPS_IP:8000`
- **API Health:** `http://YOUR_VPS_IP:8000/health`
- **API Docs:** `http://YOUR_VPS_IP:8000/docs`

## 🔧 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check GitHub Actions logs
# Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/actions

# Local testing
docker build -f Dockerfile.backend -t test-backend .
docker build -f Dockerfile.frontend -t test-frontend .
```

#### 2. Deployment Failures
```bash
# SSH to VPS and check
ssh user@your-vps-ip
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml logs

# Check container status
docker ps -a
```

#### 3. Network Issues
```bash
# Check if containers can communicate
docker network ls
docker network inspect datn-deployment_datn-network
```

#### 4. Environment Variables
```bash
# Verify environment files on VPS
cat ~/datn-deployment/.env
```

### Recovery Commands
```bash
# Restart services
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml restart

# Force rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Clean up resources
docker system prune -f
```

## 🔄 Future Deployments

After initial setup, deployments are automatic:

1. **Make changes** to your code
2. **Commit and push** to main branch
3. **CI/CD pipeline** automatically builds and deploys
4. **Monitor** through GitHub Actions

## 📈 Performance Optimization

### Production Recommendations
1. **Enable Docker BuildKit** for faster builds
2. **Use multi-stage builds** (already implemented)
3. **Implement image caching** (already configured)
4. **Monitor resource usage** with `docker stats`
5. **Set up log rotation** for long-running deployments

### Scaling Considerations
- Use **nginx reverse proxy** for better performance
- Implement **container orchestration** with Docker Swarm or Kubernetes
- Add **load balancing** for high availability
- Set up **monitoring** with Prometheus/Grafana

## 🎉 Success Indicators

Your deployment is successful when:
- ✅ GitHub Actions pipeline completes without errors
- ✅ Both containers show "healthy" status
- ✅ Frontend loads at `http://YOUR_VPS_IP:3000`
- ✅ Backend API responds at `http://YOUR_VPS_IP:8000/health`
- ✅ Frontend can communicate with backend API

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Examine container logs on VPS
4. Verify all secrets are correctly set
5. Ensure VPS has sufficient resources (2GB+ RAM recommended)

---

**🎯 Your CI/CD pipeline is now production-ready!**

Simply push to main branch and watch your application deploy automatically. Happy coding! 🚀
