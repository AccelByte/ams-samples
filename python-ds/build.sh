#!/bin/bash

# BasicDS - Build script for AccelByte AMS Compatible Dedicated Server
# This script builds only the wheel distribution and prepares deployment files

set -e  # Exit on any error

# Check if UV is available
if ! command -v uv &> /dev/null; then
    echo "Error: UV package manager is not installed or not in PATH"
    echo "Please install UV: https://github.com/astral-sh/uv"
    exit 1
fi

echo "Building BasicDS wheel package..."

# Clean previous build artifacts
if [ -d "dist" ]; then
    echo "Cleaning previous build artifacts..."
    rm -rf dist/*
fi

# Build only the wheel (faster than building both wheel and sdist)
echo "Building wheel distribution..."
uv build --wheel

# Copy start script to dist for deployment
echo "Copying start script to dist..."
cp start.sh dist/

# Make start script executable in dist
chmod +x dist/start.sh

# List build outputs
echo ""
echo "Build complete! Generated files in dist/:"
ls -la dist/
