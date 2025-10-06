# BasicDS - Build script for AccelByte AMS Compatible Dedicated Server
# This script builds only the wheel distribution and prepares deployment files

# Set error action preference to stop on errors
$ErrorActionPreference = "Stop"

# Check if UV is available
try {
    $uvVersion = uv --version
    Write-Host "Found UV: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: UV package manager is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install UV: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Building BasicDS wheel package..." -ForegroundColor Cyan

# Clean previous build artifacts
if (Test-Path "dist") {
    Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "dist\*"
} else {
    Write-Host "Creating dist directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "dist" -Force | Out-Null
}

# Build only the wheel (faster than building both wheel and sdist)
Write-Host "Building wheel distribution..." -ForegroundColor Cyan
uv build --wheel

# Copy start script to dist for deployment
Write-Host "Copying start script to dist..." -ForegroundColor Cyan
Copy-Item "start.sh" "dist\" -Force

# List build outputs
Write-Host ""
Write-Host "Build complete! Generated files in dist/:" -ForegroundColor Green
Get-ChildItem "dist" | Format-Table Name, Length, LastWriteTime
