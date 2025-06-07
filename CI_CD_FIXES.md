# CI/CD Deployment Fixes

## Issues Fixed

### 1. Docker Image Cleanup
**Problem**: Old Docker images with `<none>` tags weren't being cleaned up despite having `docker image prune -f`.

**Solution**: 
- Added comprehensive cleanup process that removes containers first, then `<none>` images, old versions of specific images, and finally runs system cleanup
- Enhanced cleanup in both CI/CD workflow and troubleshooting script

### 2. Frontend-Backend Connectivity
**Problem**: Frontend couldn't connect to backend API despite backend working fine when tested directly.

**Solution**:
- Fixed API URL configuration: Changed from `http://34.30.191.213:8000` to `http://34.30.191.213:8000/api` to match backend's API prefix
- Added internal API URL for container-to-container communication: `NEXT_PUBLIC_INTERNAL_API_URL=http://rag-app:8000/api`
- Enhanced Docker networking with `rag-network` bridge network

### 3. Deployment Monitoring & Error Handling
**Problem**: Limited visibility into deployment issues and container status.

**Solution**:
- Added comprehensive container status checking with `docker-compose ps` and `docker ps -a`
- Added API connectivity testing for both backend and frontend
- Enhanced container log display with more lines (30 instead of 20)
- Added automatic container restart if initial startup fails
- Created dedicated connectivity testing script

## Files Modified

1. **`.github/workflows/docker-ci.yml`**
   - Enhanced Docker image cleanup process
   - Fixed API URL configuration with `/api` path
   - Added internal API URL for container communication
   - Improved deployment monitoring and error handling
   - Added API connectivity testing

2. **`troubleshoot-vps.sh`**
   - Synchronized with CI/CD improvements
   - Enhanced Docker cleanup process
   - Fixed API URL configuration
   - Added connectivity testing

3. **`test-connectivity.sh`** (New)
   - Comprehensive connectivity testing between services
   - Tests both internal and external access
   - Provides detailed debugging information

## Key Configuration Changes

### API URLs
- **External (browser to backend)**: `http://34.30.191.213:8000/api`
- **Internal (container to container)**: `http://rag-app:8000/api`

### Docker Cleanup Process
```bash
# Stop and remove all containers
docker stop $(docker ps -a -q) 2>/dev/null || echo "No containers to stop"
docker rm $(docker ps -a -q) 2>/dev/null || echo "No containers to remove"

# Remove <none> images
docker images | grep '<none>' | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null

# Remove old versions of specific images
docker images username/backend | grep -v latest | awk 'NR>1{print $3}' | xargs -r docker rmi -f 2>/dev/null

# System cleanup
docker system prune -f
docker image prune -f
```

### Network Configuration
```yaml
networks:
  rag-network:
    driver: bridge
```

## Testing

After deployment, run:
```bash
bash test-connectivity.sh
```

This will test:
- Backend API accessibility from host and containers
- Frontend accessibility
- External IP access (for VPS)
- Container logs summary

## Expected Results

1. **Docker Images**: No more `<none>` tagged images accumulating
2. **Frontend-Backend Communication**: Successful API calls from frontend to backend
3. **Authentication**: Working login/signup functionality
4. **Monitoring**: Clear visibility into container status and connectivity issues
