# VPS Setup Instructions

This guide helps you prepare your VPS for the CI/CD deployment.

## 1. Install Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or use:
newgrp docker

# Verify Docker installation
docker --version
docker run hello-world
```

## 2. Install Docker Compose

```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

## 3. Create Deployment Directory

```bash
# Create deployment directory
mkdir -p ~/datn-deployment
cd ~/datn-deployment

# Create data directory for backend
mkdir -p backend_data
```

## 4. Configure Firewall (if using UFW)

```bash
# Install UFW if not installed
sudo apt install ufw

# Allow SSH (important!)
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow your app ports
sudo ufw allow 3000
sudo ufw allow 8000

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## 5. Optional: Setup Nginx Reverse Proxy

Create `/etc/nginx/sites-available/datn`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/datn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 6. Setup SSL with Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Verify auto-renewal
sudo certbot renew --dry-run
```

## 7. System Monitoring (Optional)

Create a simple monitoring script `/home/user/monitor.sh`:

```bash
#!/bin/bash

# Check if containers are running
echo "=== Container Status ==="
cd ~/datn-deployment
docker-compose -f docker-compose.prod.yml ps

echo -e "\n=== System Resources ==="
df -h | grep -E "/$|Filesystem"
free -h
uptime

echo -e "\n=== Recent Logs ==="
docker-compose -f docker-compose.prod.yml logs --tail=5 backend
docker-compose -f docker-compose.prod.yml logs --tail=5 frontend
```

Make it executable and add to cron:
```bash
chmod +x ~/monitor.sh

# Add to crontab (run every 5 minutes)
crontab -e
# Add this line:
# */5 * * * * /home/user/monitor.sh >> /home/user/monitor.log 2>&1
```

## 8. Backup Strategy

Create backup script `/home/user/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application data
cd ~/datn-deployment
tar -czf $BACKUP_DIR/datn-data-$DATE.tar.gz backend_data/

# Backup docker-compose and env files
tar -czf $BACKUP_DIR/datn-config-$DATE.tar.gz docker-compose.prod.yml .env

# Keep only last 7 backups
cd $BACKUP_DIR
ls -t datn-*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: $DATE"
```

Add to daily cron:
```bash
crontab -e
# Add this line:
# 0 2 * * * /home/user/backup.sh >> /home/user/backup.log 2>&1
```

## 9. Verify Setup

Test your setup:

```bash
# Test Docker
docker run hello-world

# Test Docker Compose
cd ~/datn-deployment
echo "version: '3.8'
services:
  test:
    image: hello-world" > test-compose.yml
docker-compose -f test-compose.yml up
rm test-compose.yml

# Test network connectivity
curl -I http://localhost
ping -c 4 google.com
```

Your VPS is now ready for the CI/CD deployment!
