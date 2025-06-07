# 🚀 HƯỚNG DẪN TRIỂN KHAI TỰ ĐỘNG LÊN VPS

## 📋 **CÀI ĐẶT GITHUB SECRETS**

Vào repository GitHub của bạn và thêm các Secrets sau:

### 🔑 **Secrets cần thiết:**

1. **VPS_HOST**: `34.30.191.213`
2. **VPS_USER**: `nguyendaihoangphuc1911`
3. **VPS_SSH_KEY**: Nội dung của file `ssh-key-2024-07-03.key`
4. **DOCKERHUB_USERNAME**: Username Docker Hub của bạn
5. **DOCKERHUB_TOKEN**: Access Token của Docker Hub
6. **BACKEND_ENV**: Nội dung file .env của backend
7. **FRONTEND_ENV**: Nội dung file .env của frontend

### 📝 **Cách thêm Secrets:**

1. Vào GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Thêm từng secret với tên và giá trị tương ứng

### 🔐 **Nội dung VPS_SSH_KEY:**

```
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAs98+2iOut0DQ4lo+EBzhRCBCjPxmHZYcN62EoWrapPWHhd+c
zSfMmB9Xd9ouGjh8junOJriL+kytDmpDPAYcosinhWUx9kcNlLaiUXIbIXyp/DAI
1r+6gbKgAUE5GX93g28U1q7cNnx/axNVqCcMtUkNhSG+G1pc/yOsCbb3nRnPFpPN
3K0phqnHA/eji1jI6VulL60axxYF5d2CrVhqWZR0eCyt50yfCynRLIjSNwm9z4B4
oM17EJOjthxRPU4T/ui7Ch6VKgayAvqilX67WdWSzsqZfll61w5a7ScWoXop2xhP
bmahQE72KYaUczcP1xHvuCeKWDjidMET2ZKqYwIDAQABAoIBADNJwcMzj3sDSUxx
jObNRVJGnJNU2M0w40Tg/kOEk2mb9ROwKia5ZXYu4aL0HFcvqhyaAEU8M/Wf7WyB
... (toàn bộ nội dung private key)
-----END RSA PRIVATE KEY-----
```

## 🛠️ **SETUP VPS LẦN ĐẦU**

### 1. **Kết nối VPS và chạy setup:**

```bash
# Kết nối VPS
ssh -i "C:\Users\ADMIN\Downloads\ssh-key-2024-07-03.key" nguyendaihoangphuc1911@34.30.191.213

# Upload và chạy setup script
wget https://raw.githubusercontent.com/[YOUR_USERNAME]/[YOUR_REPO]/main/scripts/setup-vps.sh
chmod +x setup-vps.sh
./setup-vps.sh

# Hoặc chạy manual:
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Tạo thư mục app
mkdir -p /home/nguyendaihoangphuc1911/app
cd /home/nguyendaihoangphuc1911/app
mkdir -p ./data
```

### 2. **Logout và login lại để áp dụng Docker group:**

```bash
exit
ssh -i "C:\Users\ADMIN\Downloads\ssh-key-2024-07-03.key" nguyendaihoangphuc1911@34.30.191.213
```

## 🚀 **TRIỂN KHAI TỰ ĐỘNG**

### 📤 **Push code để trigger deployment:**

```bash
# Trên máy local
git add .
git commit -m "feat: setup CI/CD deployment"
git push origin main
# hoặc
git push origin test/cicd
```

### 📊 **Theo dõi deployment:**

1. Vào GitHub repository → **Actions**
2. Xem log của workflow **"Build, Push and Deploy"**
3. Kiểm tra từng step của deployment

## 🌐 **KIỂM TRA DEPLOYMENT**

### 🔗 **URLs sau khi deploy:**

- **Frontend**: http://34.30.191.213:3000
- **Backend API**: http://34.30.191.213:8000
- **API Docs**: http://34.30.191.213:8000/docs
- **Health Check**: http://34.30.191.213:8000/health
- **Qdrant**: http://34.30.191.213:6333

### 🩺 **Health Check Commands:**

```bash
# Kiểm tra containers
ssh -i "C:\Users\ADMIN\Downloads\ssh-key-2024-07-03.key" nguyendaihoangphuc1911@34.30.191.213
docker ps
docker logs rag-app
docker logs rag-frontend
docker logs qdrant

# Kiểm tra health endpoints
curl http://34.30.191.213:8000/health
curl http://34.30.191.213:3000
curl http://34.30.191.213:6333/health
```

## 🔄 **DEPLOYMENT WORKFLOW**

### 🎯 **Tự động trigger khi:**

- Push vào branch `main`, `master`, hoặc `test/cicd`
- GitHub Actions sẽ:
  1. ✅ Build Docker images
  2. ✅ Push lên Docker Hub
  3. ✅ Connect VPS qua SSH
  4. ✅ Pull latest images
  5. ✅ Stop old containers
  6. ✅ Start new containers
  7. ✅ Clean up old images

### 🔧 **Manual deployment (nếu cần):**

```bash
# Trên VPS
cd /home/nguyendaihoangphuc1911/app
docker-compose down
docker pull [DOCKERHUB_USERNAME]/backend:latest
docker pull [DOCKERHUB_USERNAME]/frontend:latest
docker-compose up -d
```

## 🛡️ **BẢO MẬT VÀ TỐI ƯU**

### 🔒 **Firewall (khuyến nghị):**

```bash
# Trên VPS
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 6333/tcp
sudo ufw enable
```

### ⚡ **Monitoring (optional):**

```bash
# Xem logs realtime
docker logs -f rag-app
docker logs -f rag-frontend

# Kiểm tra resource usage
docker stats
```

## 🆘 **TROUBLESHOOTING**

### ❌ **Lỗi thường gặp:**

1. **SSH connection failed**: Kiểm tra SSH key và permissions
2. **Docker pull failed**: Kiểm tra Docker Hub credentials
3. **Port conflict**: Kiểm tra ports đã được sử dụng chưa
4. **Health check failed**: Kiểm tra logs containers

### 🔍 **Debug commands:**

```bash
# Kiểm tra port usage
sudo netstat -tlnp | grep :3000
sudo netstat -tlnp | grep :8000

# Restart docker service
sudo systemctl restart docker

# Check disk space
df -h
docker system prune -f
```

---

## ✅ **CHECKLIST TRƯỚC KHI DEPLOY**

- [ ] Đã thêm tất cả GitHub Secrets
- [ ] VPS đã cài Docker và Docker Compose
- [ ] SSH key có quyền truy cập VPS
- [ ] Docker Hub credentials hợp lệ
- [ ] Environment variables đã được set
- [ ] Ports trên VPS không bị conflict

**🎉 Sau khi hoàn thành, chỉ cần push code và hệ thống sẽ tự động deploy!**
