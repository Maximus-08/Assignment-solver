# Deployment verification script - comprehensive system check

param(
    [string]$Environment = "production",
    [string]$BackendUrl = "",
    [string]$FrontendUrl = "",
    [switch]$Detailed = $false
)

Write-Host "🔍 Verifying Assignment Solver System Deployment..." -ForegroundColor Green

# Auto-detect URLs if not provided
if (-not $BackendUrl) {
    $BackendUrl = if ($Environment -eq "production") { "https://api.your-domain.com" } else { "http://localhost:8000" }
}

if (-not $FrontendUrl) {
    $FrontendUrl = if ($Environment -eq "production") { "https://your-domain.com" } else { "http://localhost:3000" }
}

Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Cyan
Write-Host "Frontend URL: $FrontendUrl" -ForegroundColor Cyan

$VerificationResults = @{
    SystemHealth = @{}
    Security = @{}
    Performance = @{}
    Functionality = @{}
    Monitoring = @{}
}

function Test-SystemComponent {
    param(
        [string]$ComponentName,
        [scriptblock]$TestScript,
        [string]$Category = "SystemHealth"
    )
    
    try {
        Write-Host "Testing $ComponentName..." -ForegroundColor Yellow
        $startTime = Get-Date
        $result = & $TestScript
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        $VerificationResults[$Category][$ComponentName] = @{
            Status = if ($result.Success) { "PASSED" } else { "FAILED" }
            Details = $result.Details
            Duration = $duration
            Timestamp = $endTime
        }
        
        $status = if ($result.Success) { "✅ PASSED" } else { "❌ FAILED" }
        $color = if ($result.Success) { "Green" } else { "Red" }
        Write-Host "$ComponentName: $status ($($duration.ToString('F2'))s)" -ForegroundColor $color
        
        if ($Detailed -and $result.Details) {
            Write-Host "  $($result.Details)" -ForegroundColor Gray
        }
        
        return $result.Success
    }
    catch {
        $VerificationResults[$Category][$ComponentName] = @{
            Status = "ERROR"
            Details = $_.Exception.Message
            Duration = 0
            Timestamp = Get-Date
        }
        
        Write-Host "$ComponentName: ❌ ERROR - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# System Health Verification
Write-Host "`n🏥 System Health Verification" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

Test-SystemComponent "Backend Health" {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/health" -TimeoutSec 10
        return @{ Success = ($response.status -eq "healthy"); Details = "Status: $($response.status)" }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "SystemHealth"

Test-SystemComponent "Frontend Health" {
    try {
        $response = Invoke-RestMethod -Uri "$FrontendUrl/api/health" -TimeoutSec 10
        return @{ Success = ($response.status -eq "healthy"); Details = "Status: $($response.status)" }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "SystemHealth"

Test-SystemComponent "Database Connectivity" {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/health/detailed" -TimeoutSec 10
        $dbHealthy = $response.checks.database.status -eq "healthy"
        return @{ Success = $dbHealthy; Details = "DB Status: $($response.checks.database.status), Response Time: $($response.checks.database.response_time_ms)ms" }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "SystemHealth"

Test-SystemComponent "System Resources" {
    try {
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/health/detailed" -TimeoutSec 10
        $system = $response.checks.system
        $cpuOk = $system.cpu_percent -lt 80
        $memoryOk = $system.memory_percent -lt 80
        $diskOk = $system.disk_percent -lt 80
        
        $allOk = $cpuOk -and $memoryOk -and $diskOk
        return @{ 
            Success = $allOk
            Details = "CPU: $($system.cpu_percent)%, Memory: $($system.memory_percent)%, Disk: $($system.disk_percent)%"
        }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "SystemHealth"

# Security Verification
Write-Host "`n🔒 Security Verification" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

Test-SystemComponent "HTTPS Configuration" {
    $httpsOk = $BackendUrl.StartsWith("https://") -and $FrontendUrl.StartsWith("https://")
    return @{ 
        Success = $httpsOk -or $Environment -ne "production"
        Details = "Backend HTTPS: $($BackendUrl.StartsWith('https://')), Frontend HTTPS: $($FrontendUrl.StartsWith('https://'))"
    }
} -Category "Security"

Test-SystemComponent "Security Headers" {
    try {
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 10 -UseBasicParsing
        $hasXFrame = $response.Headers.ContainsKey("X-Frame-Options")
        $hasXContent = $response.Headers.ContainsKey("X-Content-Type-Options")
        
        return @{
            Success = $hasXFrame -and $hasXContent
            Details = "X-Frame-Options: $hasXFrame, X-Content-Type-Options: $hasXContent"
        }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "Security"

Test-SystemComponent "Authentication Endpoints" {
    try {
        # Test that auth endpoint exists and returns appropriate error for missing credentials
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/auth/login" -Method POST -ErrorAction SilentlyContinue
        return @{ Success = $false; Details = "Unexpected success" }
    }
    catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { 0 }
        $authWorking = $statusCode -eq 422 -or $statusCode -eq 400  # Expected for missing body
        return @{ Success = $authWorking; Details = "Status Code: $statusCode" }
    }
} -Category "Security"

# Performance Verification
Write-Host "`n⚡ Performance Verification" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

Test-SystemComponent "API Response Time" {
    try {
        $startTime = Get-Date
        $response = Invoke-RestMethod -Uri "$BackendUrl/api/v1/health" -TimeoutSec 10
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        $performanceOk = $duration -lt 2.0  # Should respond within 2 seconds
        return @{
            Success = $performanceOk
            Details = "$($duration.ToString('F2'))s (target: <2.0s)"
        }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "Performance"

Test-SystemComponent "Frontend Load Time" {
    try {
        $startTime = Get-Date
        $response = Invoke-WebRequest -Uri $FrontendUrl -TimeoutSec 15 -UseBasicParsing
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        $performanceOk = $duration -lt 3.0  # Should load within 3 seconds
        return @{
            Success = $performanceOk
            Details = "$($duration.ToString('F2'))s (target: <3.0s)"
        }
    }
    catch {
        return @{ Success = $false; Details = $_.Exception.Message }
    }
} -Category "Performance"

# Functionality Verification
Write-Host "`n🔧 Functionality Verification" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

Test-SystemComponent "API Endpoints" {
    $endpoints = @(
        "$BackendUrl/api/v1/assignments",
        "$BackendUrl/api/v1/health/ready",
        "$BackendUrl/api/v1/health/live"
    )
    
    $workingEndpoints = 0
    $details = @()
    
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-RestMethod -Uri $endpoint -TimeoutSec 5 -ErrorAction SilentlyContinue
            $workingEndpoints++
            $details += "✅ $(Split-Path $endpoint -Leaf)"
        }
        catch {
            $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode } else { 0 }
            if ($statusCode -eq 401) {  # Auth required is expected
                $workingEndpoints++
                $details += "✅ $(Split-Path $endpoint -Leaf) (auth required)"
            } else {
                $details += "❌ $(Split-Path $endpoint -Leaf) ($statusCode)"
            }
        }
    }
    
    return @{
        Success = $workingEndpoints -eq $endpoints.Count
        Details = $details -join ", "
    }
} -Category "Functionality"

Test-SystemComponent "Frontend Pages" {
    $pages = @(
        "$FrontendUrl/",
        "$FrontendUrl/assignments",
        "$FrontendUrl/upload"
    )
    
    $workingPages = 0
    $details = @()
    
    foreach ($page in $pages) {
        try {
            $response = Invoke-WebRequest -Uri $page -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                $workingPages++
                $details += "✅ $(Split-Path $page -Leaf)"
            } else {
                $details += "❌ $(Split-Path $page -Leaf) ($($response.StatusCode))"
            }
        }
        catch {
            $details += "❌ $(Split-Path $page -Leaf) (error)"
        }
    }
    
    return @{
        Success = $workingPages -eq $pages.Count
        Details = $details -join ", "
    }
} -Category "Functionality"

# Monitoring Verification
Write-Host "`n📊 Monitoring Verification" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

Test-SystemComponent "Health Check Endpoints" {
    $healthEndpoints = @(
        "$BackendUrl/api/v1/health",
        "$BackendUrl/api/v1/health/ready",
        "$BackendUrl/api/v1/health/live",
        "$FrontendUrl/api/health"
    )
    
    $workingEndpoints = 0
    foreach ($endpoint in $healthEndpoints) {
        try {
            $response = Invoke-RestMethod -Uri $endpoint -TimeoutSec 5
            if ($response.status -eq "healthy" -or $response.status -eq "ready" -or $response.status -eq "alive") {
                $workingEndpoints++
            }
        }
        catch {
            # Endpoint not working
        }
    }
    
    return @{
        Success = $workingEndpoints -eq $healthEndpoints.Count
        Details = "$workingEndpoints/$($healthEndpoints.Count) health endpoints working"
    }
} -Category "Monitoring"

# Generate Verification Report
Write-Host "`n📋 Verification Report" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan

$totalTests = 0
$passedTests = 0

foreach ($category in $VerificationResults.Keys) {
    Write-Host "`n$category:" -ForegroundColor White
    foreach ($test in $VerificationResults[$category].Keys) {
        $result = $VerificationResults[$category][$test]
        $status = $result.Status
        $color = switch ($status) {
            "PASSED" { "Green" }
            "FAILED" { "Red" }
            "ERROR" { "Magenta" }
        }
        
        Write-Host "  $test: $status" -ForegroundColor $color
        if ($Detailed -and $result.Details) {
            Write-Host "    $($result.Details)" -ForegroundColor Gray
        }
        
        $totalTests++
        if ($status -eq "PASSED") { $passedTests++ }
    }
}

# Overall Results
$successRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
Write-Host "`n🎯 Overall Results:" -ForegroundColor Cyan
Write-Host "Total Tests: $totalTests" -ForegroundColor White
Write-Host "Passed: $passedTests" -ForegroundColor Green
Write-Host "Failed: $($totalTests - $passedTests)" -ForegroundColor Red
Write-Host "Success Rate: $successRate%" -ForegroundColor Cyan

# Deployment Status
if ($successRate -ge 95) {
    Write-Host "`n🎉 DEPLOYMENT VERIFIED - System is ready for production!" -ForegroundColor Green
    $exitCode = 0
} elseif ($successRate -ge 85) {
    Write-Host "`n⚠️  DEPLOYMENT PARTIALLY VERIFIED - Minor issues detected" -ForegroundColor Yellow
    $exitCode = 1
} else {
    Write-Host "`n❌ DEPLOYMENT VERIFICATION FAILED - Significant issues detected" -ForegroundColor Red
    $exitCode = 2
}

# Save detailed report
$reportFile = "verification-report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
$report = @{
    Environment = $Environment
    BackendUrl = $BackendUrl
    FrontendUrl = $FrontendUrl
    Timestamp = Get-Date
    Results = $VerificationResults
    Summary = @{
        TotalTests = $totalTests
        PassedTests = $passedTests
        FailedTests = ($totalTests - $passedTests)
        SuccessRate = $successRate
    }
}

$report | ConvertTo-Json -Depth 4 | Out-File -FilePath $reportFile -Encoding UTF8
Write-Host "`n📄 Detailed verification report saved to: $reportFile" -ForegroundColor Gray

exit $exitCode