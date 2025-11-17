# Complete deployment script for the Assignment Solver system

param(
    [string]$Environment = "production",
    [switch]$SkipTests = $false,
    [switch]$SkipBuild = $false
)

Write-Host "🚀 Deploying Assignment Solver System to $Environment..." -ForegroundColor Green

# Configuration
$ErrorActionPreference = "Stop"
$DeploymentLog = "deployment_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $DeploymentLog -Value $logMessage
}

function Test-Prerequisites {
    Write-Log "Checking deployment prerequisites..." "INFO"
    
    $prerequisites = @(
        @{ Command = "node"; Name = "Node.js" },
        @{ Command = "npm"; Name = "npm" },
        @{ Command = "python3"; Name = "Python 3" },
        @{ Command = "docker"; Name = "Docker" }
    )
    
    foreach ($prereq in $prerequisites) {
        try {
            $null = Get-Command $prereq.Command -ErrorAction Stop
            Write-Log "✅ $($prereq.Name) is installed" "INFO"
        }
        catch {
            Write-Log "❌ $($prereq.Name) is not installed or not in PATH" "ERROR"
            throw "Missing prerequisite: $($prereq.Name)"
        }
    }
}

function Build-Frontend {
    Write-Log "Building frontend application..." "INFO"
    
    Set-Location frontend
    
    try {
        Write-Log "Installing frontend dependencies..." "INFO"
        npm ci --only=production
        
        Write-Log "Building frontend for production..." "INFO"
        npm run build
        
        Write-Log "✅ Frontend build completed successfully" "INFO"
    }
    catch {
        Write-Log "❌ Frontend build failed: $($_.Exception.Message)" "ERROR"
        throw
    }
    finally {
        Set-Location ..
    }
}

function Build-Backend {
    Write-Log "Preparing backend application..." "INFO"
    
    Set-Location backend
    
    try {
        Write-Log "Installing backend dependencies..." "INFO"
        pip install -r requirements.txt
        
        Write-Log "✅ Backend preparation completed successfully" "INFO"
    }
    catch {
        Write-Log "❌ Backend preparation failed: $($_.Exception.Message)" "ERROR"
        throw
    }
    finally {
        Set-Location ..
    }
}

function Build-Agent {
    Write-Log "Preparing automation agent..." "INFO"
    
    Set-Location agent
    
    try {
        Write-Log "Installing agent dependencies..." "INFO"
        pip install -r requirements.txt
        
        Write-Log "✅ Agent preparation completed successfully" "INFO"
    }
    catch {
        Write-Log "❌ Agent preparation failed: $($_.Exception.Message)" "ERROR"
        throw
    }
    finally {
        Set-Location ..
    }
}

function Deploy-WithDocker {
    Write-Log "Deploying with Docker Compose..." "INFO"
    
    try {
        Write-Log "Building Docker images..." "INFO"
        docker-compose -f docker-compose.prod.yml build
        
        Write-Log "Starting services..." "INFO"
        docker-compose -f docker-compose.prod.yml up -d
        
        Write-Log "Waiting for services to start..." "INFO"
        Start-Sleep -Seconds 30
        
        Write-Log "✅ Docker deployment completed successfully" "INFO"
    }
    catch {
        Write-Log "❌ Docker deployment failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Deploy-ToCloud {
    Write-Log "Deploying to cloud platforms..." "INFO"
    
    try {
        # Deploy frontend to Vercel
        Write-Log "Deploying frontend to Vercel..." "INFO"
        if (Test-Path "scripts/deploy-vercel.ps1") {
            & "scripts/deploy-vercel.ps1"
        } else {
            Write-Log "⚠️  Vercel deployment script not found, skipping..." "WARN"
        }
        
        # Deploy backend and agent to Railway
        Write-Log "Deploying backend and agent to Railway..." "INFO"
        if (Test-Path "scripts/deploy-railway.ps1") {
            & "scripts/deploy-railway.ps1"
        } else {
            Write-Log "⚠️  Railway deployment script not found, skipping..." "WARN"
        }
        
        Write-Log "✅ Cloud deployment completed successfully" "INFO"
    }
    catch {
        Write-Log "❌ Cloud deployment failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Test-Deployment {
    Write-Log "Testing deployed system..." "INFO"
    
    try {
        if (Test-Path "scripts/test-system.ps1") {
            & "scripts/test-system.ps1"
            Write-Log "✅ System tests completed successfully" "INFO"
        } else {
            Write-Log "⚠️  System test script not found, skipping tests..." "WARN"
        }
    }
    catch {
        Write-Log "❌ System tests failed: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Verify-Environment {
    Write-Log "Verifying environment configuration..." "INFO"
    
    $envFiles = @(
        "backend/.env.production",
        "frontend/.env.production", 
        "agent/.env.production"
    )
    
    foreach ($envFile in $envFiles) {
        if (Test-Path $envFile) {
            Write-Log "✅ Found $envFile" "INFO"
        } else {
            Write-Log "⚠️  Missing $envFile - using defaults" "WARN"
        }
    }
}

# Main deployment process
try {
    Write-Log "Starting deployment process..." "INFO"
    Write-Log "Environment: $Environment" "INFO"
    Write-Log "Skip Tests: $SkipTests" "INFO"
    Write-Log "Skip Build: $SkipBuild" "INFO"
    
    # Step 1: Check prerequisites
    Test-Prerequisites
    
    # Step 2: Verify environment
    Verify-Environment
    
    # Step 3: Build applications (if not skipped)
    if (-not $SkipBuild) {
        Build-Frontend
        Build-Backend
        Build-Agent
    } else {
        Write-Log "Skipping build step as requested" "INFO"
    }
    
    # Step 4: Deploy based on environment
    if ($Environment -eq "docker") {
        Deploy-WithDocker
    } elseif ($Environment -eq "production") {
        Deploy-ToCloud
    } else {
        Write-Log "Unknown environment: $Environment" "ERROR"
        throw "Unsupported environment"
    }
    
    # Step 5: Test deployment (if not skipped)
    if (-not $SkipTests) {
        Start-Sleep -Seconds 10  # Give services time to fully start
        Test-Deployment
    } else {
        Write-Log "Skipping tests as requested" "INFO"
    }
    
    Write-Log "🎉 Deployment completed successfully!" "INFO"
    Write-Log "Deployment log saved to: $DeploymentLog" "INFO"
    
    # Display next steps
    Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
    Write-Host "1. Verify all services are running correctly" -ForegroundColor White
    Write-Host "2. Configure monitoring and alerting" -ForegroundColor White
    Write-Host "3. Set up backup procedures" -ForegroundColor White
    Write-Host "4. Configure SSL certificates (if using custom domains)" -ForegroundColor White
    Write-Host "5. Test the complete user workflow" -ForegroundColor White
    
}
catch {
    Write-Log "❌ Deployment failed: $($_.Exception.Message)" "ERROR"
    Write-Log "Check the deployment log for details: $DeploymentLog" "ERROR"
    exit 1
}