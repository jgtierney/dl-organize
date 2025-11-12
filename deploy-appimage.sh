#!/bin/bash
set -e

# Configuration
APPIMAGE_NAME="file-organizer-x86_64.AppImage"
DEPLOY_DIR="/mnt/share/Pron"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "Deploying File Organizer AppImage"
echo "================================================"

# Check if AppImage exists
APPIMAGE_PATH="${SCRIPT_DIR}/${APPIMAGE_NAME}"
if [ ! -f "$APPIMAGE_PATH" ]; then
    echo "Error: AppImage not found at $APPIMAGE_PATH"
    echo "Please build the AppImage first using: ./build-appimage.sh"
    exit 1
fi

# Check if deploy directory exists, create if it doesn't
if [ ! -d "$DEPLOY_DIR" ]; then
    echo "Deploy directory does not exist: $DEPLOY_DIR"
    echo "Attempting to create it..."
    mkdir -p "$DEPLOY_DIR" 2>/dev/null
    if [ $? -eq 0 ] && [ -d "$DEPLOY_DIR" ]; then
        echo "✓ Directory created successfully"
    else
        echo "Error: Failed to create directory: $DEPLOY_DIR"
        echo ""
        echo "Possible reasons:"
        echo "  - Directory is a mount point that needs to be mounted first"
        echo "  - Insufficient permissions to create the directory"
        echo "  - Parent directory does not exist"
        echo ""
        echo "Please ensure the directory exists and is accessible, then run this script again."
        exit 1
    fi
fi

# Check if deploy directory is writable
if [ ! -w "$DEPLOY_DIR" ]; then
    echo "Error: Deploy directory is not writable: $DEPLOY_DIR"
    exit 1
fi

# Get AppImage info
APPIMAGE_SIZE=$(ls -lh "$APPIMAGE_PATH" | awk '{print $5}')
echo "Source: $APPIMAGE_PATH ($APPIMAGE_SIZE)"
echo "Target: $DEPLOY_DIR"
echo ""

# Copy AppImage
echo "Copying AppImage to deployment directory..."
cp "$APPIMAGE_PATH" "$DEPLOY_DIR/"
if [ $? -eq 0 ]; then
    echo "✓ AppImage copied successfully"
else
    echo "✗ Failed to copy AppImage"
    exit 1
fi

# Make it executable
DEPLOYED_PATH="${DEPLOY_DIR}/${APPIMAGE_NAME}"
chmod +x "$DEPLOYED_PATH"
if [ $? -eq 0 ]; then
    echo "✓ AppImage set as executable"
else
    echo "⚠ Warning: Failed to set executable permissions"
fi

# Verify deployment
if [ -f "$DEPLOYED_PATH" ] && [ -x "$DEPLOYED_PATH" ]; then
    DEPLOYED_SIZE=$(ls -lh "$DEPLOYED_PATH" | awk '{print $5}')
    echo ""
    echo "================================================"
    echo "Deployment successful!"
    echo "================================================"
    echo "Deployed to: $DEPLOYED_PATH"
    echo "Size: $DEPLOYED_SIZE"
    echo ""
    echo "Test it with: $DEPLOYED_PATH --version"
else
    echo "✗ Deployment verification failed"
    exit 1
fi

