# Final CI/CD Pipeline Validation Script for Windows
# This script validates all components before deployment

Write-Host "🔍 DATN CI/CD Pipeline Validation" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Function to print status
function Print-Status {
    param(
        [bool]$Success,
        [string]$Message
    )
    if ($Success) {
        Write-Host "✅ $Message" -ForegroundColor Green
    } else {
        Write-Host "❌ $Message" -ForegroundColor Red
    }
}

function Print-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

# Check if Docker is installed and running
Write-Host "1. Checking Docker installation..."
try {
    $dockerVersion = docker --version 2>$null
    if ($dockerVersion) {
        try {
            docker info 2>$null | Out-Null
            Print-Status $true "Docker is installed and running"
        } catch {
            Print-Status $false "Docker is installed but not running"
            exit 1
        }
    } else {
        Print-Status $false "Docker is not installed"
        exit 1
    }
} catch {
    Print-Status $false "Docker is not installed"
    exit 1
}

# Check if Docker Compose is available
Write-Host "2. Checking Docker Compose..."
try {
    $composeVersion = docker-compose --version 2>$null
    if ($composeVersion) {
        Print-Status $true "Docker Compose is available"
    } else {
        Print-Status $false "Docker Compose is not available"
        exit 1
    }
} catch {
    Print-Status $false "Docker Compose is not available"
    exit 1
}

# Validate Dockerfile.backend
Write-Host "3. Validating Dockerfile.backend..."
if (Test-Path "Dockerfile.backend") {
    try {
        docker build -f Dockerfile.backend -t datn-backend-test . --no-cache 2>$null | Out-Null
        Print-Status $true "Dockerfile.backend is valid"
        docker rmi datn-backend-test 2>$null | Out-Null
    } catch {
        Print-Status $false "Dockerfile.backend has issues"
    }
} else {
    Print-Status $false "Dockerfile.backend not found"
}

# Validate Dockerfile.frontend
Write-Host "4. Validating Dockerfile.frontend..."
if (Test-Path "Dockerfile.frontend") {
    try {
        docker build -f Dockerfile.frontend -t datn-frontend-test . --no-cache 2>$null | Out-Null
        Print-Status $true "Dockerfile.frontend is valid"
        docker rmi datn-frontend-test 2>$null | Out-Null
    } catch {
        Print-Status $false "Dockerfile.frontend has issues"
    }
} else {
    Print-Status $false "Dockerfile.frontend not found"
}

# Validate docker-compose.yml
Write-Host "5. Validating docker-compose.yml..."
if (Test-Path "docker-compose.yml") {
    try {
        docker-compose config 2>$null | Out-Null
        Print-Status $true "docker-compose.yml is valid"
    } catch {
        Print-Status $false "docker-compose.yml has syntax errors"
    }
} else {
    Print-Status $false "docker-compose.yml not found"
}

# Check GitHub Actions workflow files
Write-Host "6. Checking GitHub Actions workflows..."
if (Test-Path ".github\workflows\ci-cd.yml") {
    Print-Status $true "ci-cd.yml workflow exists"
} else {
    Print-Status $false "ci-cd.yml workflow not found"
}

if (Test-Path ".github\workflows\dev-build.yml") {
    Print-Status $true "dev-build.yml workflow exists"
} else {
    Print-Status $false "dev-build.yml workflow not found"
}

# Check for required files
Write-Host "7. Checking required files..."
$requiredFiles = @(
    "requirements.txt",
    "frontend\package.json",
    "src\api.py",
    "DEPLOYMENT.md",
    "setup-vps.sh"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Print-Status $true "$file exists"
    } else {
        Print-Status $false "$file missing"
    }
}

# Test environment file creation
Write-Host "8. Testing environment file structure..."
if (Test-Path ".env.example") {
    Print-Status $true ".env.example found"
} else {
    Print-Warning "No .env.example found - make sure you have environment templates"
}

# Check network connectivity requirements
Write-Host "9. Checking network requirements..."
try {
    $response = Invoke-WebRequest -Uri "https://hub.docker.com" -TimeoutSec 10 -UseBasicParsing 2>$null
    Print-Status $true "Docker Hub connectivity"
} catch {
    Print-Status $false "Cannot reach Docker Hub"
}

try {
    $response = Invoke-WebRequest -Uri "https://github.com" -TimeoutSec 10 -UseBasicParsing 2>$null
    Print-Status $true "GitHub connectivity"
} catch {
    Print-Status $false "Cannot reach GitHub"
}

Write-Host ""
Write-Host "🎯 DEPLOYMENT READINESS CHECKLIST" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# GitHub Secrets Checklist
Write-Host "📋 GitHub Secrets to verify in your repository:" -ForegroundColor Yellow
Write-Host "   □ DOCKERHUB_USERNAME"
Write-Host "   □ DOCKERHUB_TOKEN"
Write-Host "   □ VPS_HOST"
Write-Host "   □ VPS_USER"
Write-Host "   □ VPS_SSH_KEY"
Write-Host "   □ BACKEND_ENV"
Write-Host "   □ FRONTEND_ENV"
Write-Host ""

# VPS Checklist
Write-Host "🖥️  VPS Setup Checklist:" -ForegroundColor Yellow
Write-Host "   □ Run setup-vps.sh on your VPS"
Write-Host "   □ Docker and Docker Compose installed"
Write-Host "   □ SSH key configured for GitHub Actions"
Write-Host "   □ Firewall configured (ports 22, 80, 443, 3000, 8000)"
Write-Host "   □ Domain/IP accessible from internet"
Write-Host ""

# Final Steps
Write-Host "🚀 Final Deployment Steps:" -ForegroundColor Yellow
Write-Host "   1. Verify all GitHub secrets are set"
Write-Host "   2. Run setup-vps.sh on your VPS"
Write-Host "   3. Test SSH connection: ssh user@your-vps-ip"
Write-Host "   4. Push code to main branch"
Write-Host "   5. Monitor GitHub Actions: https://github.com/YOUR_USERNAME/YOUR_REPO/actions"
Write-Host "   6. Check deployment: http://YOUR_VPS_IP:3000"
Write-Host ""

Write-Host "✨ Pipeline validation completed!" -ForegroundColor Green
Write-Host "If all checks passed, your CI/CD pipeline is ready for deployment." -ForegroundColor Green
