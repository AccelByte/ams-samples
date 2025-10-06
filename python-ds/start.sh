#!/bin/bash

# BasicDS - Start script for AccelByte AMS Compatible Dedicated Server
# This script runs the server using UV and passes along all command line arguments

set -e  # Exit on any error

# Check if UV is available
if ! command -v uv &> /dev/null; then
    echo "Error: UV package manager is not installed or not in PATH"
    echo "Please install UV: https://github.com/astral-sh/uv"
    exit 1
fi

# Change to script directory to ensure correct working directory
cd "$(dirname "$0")"

echo "Starting BasicDS server..."
echo "Arguments: $*"

# Find built package - prefer wheel over source distribution
if ls *.whl &> /dev/null; then
    PACKAGE_FILE=$(ls *.whl | head -1)
    echo "Using wheel: $PACKAGE_FILE (faster startup)"
elif ls *.tar.gz &> /dev/null; then
    PACKAGE_FILE=$(ls *.tar.gz | head -1)
    echo "Using source distribution: $PACKAGE_FILE (will build at runtime)"
else
    echo "Error: No built package found (*.whl or *.tar.gz)"
    echo "Run 'uv build' first to create a distribution package"
    exit 1
fi

# Run the server using the built package directly (no installation needed)
exec uv run --with "./$PACKAGE_FILE" basicds "$@"