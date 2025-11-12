#!/bin/bash
# Deployment script for File Organizer AppImage
# Copies the AppImage to /mnt/share/Pron/ and overwrites any existing version

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

APPIMAGE_NAME="file-organizer-x86_64.AppImage"
DEPLOY_PATH="/mnt/share/Pron"
TARGET_FILE="${DEPLOY_PATH}/${APPIMAGE_NAME}"

echo "=== Deploying File Organizer AppImage ==="

# Check if AppImage exists
if [ ! -f "$APPIMAGE_NAME" ]; then
    echo "Error: $APPIMAGE_NAME not found in current directory!"
    echo "Please build the AppImage first using: ./build_appimage.sh"
    exit 1
fi

# Check if deployment directory exists
if [ ! -d "$DEPLOY_PATH" ]; then
    echo "Error: Deployment directory $DEPLOY_PATH does not exist!"
    echo "Please ensure the mount point is available."
    exit 1
fi

# Check if we can write to the deployment directory
if [ ! -w "$DEPLOY_PATH" ]; then
    echo "Error: No write permission to $DEPLOY_PATH"
    echo "You may need to run this script with sudo or check permissions."
    exit 1
fi

# Remove existing AppImage if it exists
if [ -f "$TARGET_FILE" ]; then
    echo "Removing existing AppImage: $TARGET_FILE"
    rm -f "$TARGET_FILE"
fi

# Copy the AppImage
echo "Copying $APPIMAGE_NAME to $DEPLOY_PATH..."
cp "$APPIMAGE_NAME" "$TARGET_FILE"

# Make it executable
chmod +x "$TARGET_FILE"

# Verify the copy
if [ -f "$TARGET_FILE" ]; then
    echo ""
    echo "=== Deployment successful! ==="
    echo "AppImage deployed to: $TARGET_FILE"
    echo ""
    ls -lh "$TARGET_FILE"
    echo ""
    echo "To test the deployed AppImage:"
    echo "  $TARGET_FILE --help"
else
    echo "Error: Deployment failed - file not found at destination!"
    exit 1
fi

