#!/bin/bash

# VPS Setup Script for DATN Project
# Run this script on your VPS to prepare it for deployment

set -e

echo "=== DATN VPS Setup Script ==="
echo "This script will install Docker, Docker Compose, and prepare your VPS for deployment."
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root or with sudo"
    exit 1
fi

# Update system packages
echo "Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    wget \
    unzip

# Install Docker
echo "Installing Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install Docker Compose (standalone)
echo "Installing Docker Compose..."
DOCKER_COMPOSE_VERSION="2.24.1"
curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create docker-compose symlink for compatibility
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Add current user to docker group (if not root)
if [ "$SUDO_USER" ]; then
    usermod -aG docker $SUDO_USER
    echo "Added $SUDO_USER to docker group"
fi

# Create deployment directory
echo "Creating deployment directory..."
DEPLOY_DIR="/home/${SUDO_USER:-$USER}/datn-deployment"
mkdir -p $DEPLOY_DIR
chown -R ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} $DEPLOY_DIR

# Configure firewall (if UFW is available)
if command -v ufw &> /dev/null; then
    echo "Configuring firewall..."
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 3000/tcp  # Frontend
    ufw allow 8000/tcp  # Backend API
    ufw --force enable
fi

# Install fail2ban for security
echo "Installing fail2ban for security..."
apt-get install -y fail2ban
systemctl start fail2ban
systemctl enable fail2ban

# Create swap file if not exists (helps with memory)
if [ ! -f /swapfile ]; then
    echo "Creating swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
fi

# Optimize Docker for production
echo "Optimizing Docker configuration..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

systemctl restart docker

# Create monitoring script
echo "Creating monitoring script..."
cat > $DEPLOY_DIR/monitor.sh << 'EOF'
#!/bin/bash
# Simple monitoring script for DATN services

echo "=== DATN Service Status ==="
echo "Date: $(date)"
echo

echo "=== Docker Containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo

echo "=== Container Health ==="
docker-compose -f ~/datn-deployment/docker-compose.prod.yml ps
echo

echo "=== System Resources ==="
echo "Memory Usage:"
free -h
echo
echo "Disk Usage:"
df -h /
echo

echo "=== Service URLs ==="
echo "Frontend: http://$(curl -s ifconfig.me):3000"
echo "Backend API: http://$(curl -s ifconfig.me):8000"
echo "Backend Health: http://$(curl -s ifconfig.me):8000/health"
echo

echo "=== Recent Logs (last 10 lines) ==="
echo "Backend logs:"
docker-compose -f ~/datn-deployment/docker-compose.prod.yml logs --tail=10 backend 2>/dev/null || echo "Backend not running"
echo
echo "Frontend logs:"
docker-compose -f ~/datn-deployment/docker-compose.prod.yml logs --tail=10 frontend 2>/dev/null || echo "Frontend not running"
EOF

chmod +x $DEPLOY_DIR/monitor.sh
chown ${SUDO_USER:-$USER}:${SUDO_USER:-$USER} $DEPLOY_DIR/monitor.sh

# Test Docker installation
echo "Testing Docker installation..."
docker --version
docker-compose --version

echo
echo "=== VPS Setup Complete! ==="
echo
echo "Next steps:"
echo "1. Log out and log back in to apply docker group changes"
echo "2. Test Docker: docker run hello-world"
echo "3. Your deployment directory is at: $DEPLOY_DIR"
echo "4. Use the monitor script: $DEPLOY_DIR/monitor.sh"
echo "5. Make sure your GitHub Actions secrets are configured:"
echo "   - VPS_HOST: $(curl -s ifconfig.me)"
echo "   - VPS_USER: ${SUDO_USER:-$USER}"
echo "   - VPS_SSH_KEY: Your private SSH key"
echo "   - DOCKERHUB_USERNAME: Your Docker Hub username"
echo "   - DOCKERHUB_TOKEN: Your Docker Hub access token"
echo "   - BACKEND_ENV: Your backend environment variables"
echo "   - FRONTEND_ENV: Your frontend environment variables"
echo
echo "=== Setup completed successfully! ==="
