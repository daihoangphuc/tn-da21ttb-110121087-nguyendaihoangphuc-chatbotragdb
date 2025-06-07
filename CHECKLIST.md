# CI/CD Deployment Checklist

Checklist này giúp bạn đảm bảo mọi thứ đã được thiết lập đúng cho CI/CD pipeline.

## ✅ Pre-deployment Checklist

### 1. GitHub Repository Setup
- [ ] Repository đã được tạo trên GitHub
- [ ] Code đã được push lên repository
- [ ] Workflow files đã có trong `.github/workflows/`

### 2. Docker Hub Setup
- [ ] Tài khoản Docker Hub đã được tạo
- [ ] Access token đã được tạo trên Docker Hub
- [ ] Repository `datn-backend` và `datn-frontend` đã được tạo (hoặc sẽ tự động tạo)

### 3. VPS Setup
- [ ] VPS đã được cấu hình và có thể SSH
- [ ] Docker đã được cài đặt trên VPS
- [ ] Docker Compose đã được cài đặt trên VPS
- [ ] User có quyền chạy Docker (trong group docker)
- [ ] Ports 3000 và 8000 đã được mở trên firewall
- [ ] Directory `~/datn-deployment` đã được tạo

### 4. SSH Key Setup
- [ ] SSH key pair đã được tạo cho GitHub Actions
- [ ] Public key đã được thêm vào VPS (~/.ssh/authorized_keys)
- [ ] Private key đã được thêm vào GitHub Secrets

### 5. GitHub Secrets Configuration
Tất cả secrets sau đã được thêm vào GitHub repository (Settings > Secrets and variables > Actions):

#### Required Secrets:
- [ ] `DOCKERHUB_USERNAME` - Username Docker Hub của bạn
- [ ] `DOCKERHUB_TOKEN` - Access token từ Docker Hub
- [ ] `VPS_HOST` - IP address hoặc domain của VPS
- [ ] `VPS_USER` - Username để SSH vào VPS
- [ ] `VPS_SSH_KEY` - Private SSH key (toàn bộ nội dung file)

#### Environment Secrets:
- [ ] `BACKEND_ENV` - Tất cả environment variables cho backend
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

- [ ] `FRONTEND_ENV` - Environment variables cho frontend
```env
NEXT_PUBLIC_API_URL=http://YOUR_VPS_IP:8000/api
```

### 6. Local Testing
- [ ] Đã test build backend locally: `docker build -f Dockerfile.backend -t test-backend .`
- [ ] Đã test build frontend locally: `docker build -f Dockerfile.frontend -t test-frontend .`
- [ ] Đã test docker-compose locally: `docker-compose config`
- [ ] Đã chạy script test: `./test-build.sh` (trên Linux/Mac)

## ✅ Deployment Process Checklist

### 1. First Deployment
- [ ] Push code lên branch `main` hoặc `master`
- [ ] Kiểm tra GitHub Actions workflow đang chạy
- [ ] Workflow "build-and-push" đã hoàn thành thành công
- [ ] Docker images đã được push lên Docker Hub
- [ ] Workflow "deploy" đã hoàn thành thành công

### 2. Verify Deployment
- [ ] SSH vào VPS và kiểm tra containers đang chạy:
```bash
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml ps
```

- [ ] Kiểm tra logs không có lỗi:
```bash
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs frontend
```

- [ ] Test health endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:3000
```

- [ ] Test từ browser:
  - [ ] Frontend accessible tại `http://VPS_IP:3000`
  - [ ] Backend API accessible tại `http://VPS_IP:8000/api`
  - [ ] Frontend có thể gọi được backend API

### 3. Network Verification
- [ ] Container backend có thể được access từ frontend qua internal network
- [ ] Frontend environment variable `NEXT_PUBLIC_API_URL` đã đúng
- [ ] Backend health check đang hoạt động
- [ ] Frontend health check đang hoạt động

## ✅ Post-deployment Checklist

### 1. Monitoring Setup
- [ ] Cài đặt monitoring script (optional)
- [ ] Setup log rotation
- [ ] Setup backup strategy

### 2. Security
- [ ] Đổi SSH port default (optional nhưng recommended)
- [ ] Setup fail2ban (optional)
- [ ] Configure firewall properly
- [ ] Setup SSL certificate nếu sử dụng domain (optional)

### 3. Production Readiness
- [ ] Setup proper domain và SSL
- [ ] Configure reverse proxy (Nginx/Traefik)
- [ ] Setup database backup strategy
- [ ] Configure monitoring và alerting
- [ ] Setup log aggregation

## 🔧 Troubleshooting Common Issues

### Build Failures
- [ ] Kiểm tra Dockerfile syntax
- [ ] Kiểm tra environment variables trong secrets
- [ ] Kiểm tra dependencies trong requirements.txt và package.json

### Deployment Failures
- [ ] Kiểm tra SSH connectivity
- [ ] Kiểm tra Docker và Docker Compose installation trên VPS
- [ ] Kiểm tra disk space trên VPS
- [ ] Kiểm tra network connectivity từ VPS

### Runtime Issues
- [ ] Kiểm tra container logs
- [ ] Kiểm tra environment variables
- [ ] Kiểm tra network connectivity giữa containers
- [ ] Kiểm tra health check status

## 📞 Emergency Commands

```bash
# Stop all services
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml down

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Force pull and restart
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Clean up disk space
docker system prune -a -f
```

## ✨ Success Criteria

Deployment được coi là thành công khi:
- [ ] GitHub Actions workflow hoàn thành không lỗi
- [ ] Docker images được push lên Docker Hub
- [ ] Containers đang chạy trên VPS
- [ ] Health checks đều passing
- [ ] Frontend accessible từ browser
- [ ] Backend API trả về response đúng
- [ ] Frontend có thể giao tiếp với backend thành công

---

**🎉 Congratulations! Your CI/CD pipeline is now ready!**
