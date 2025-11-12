#!/bin/bash
# Build script for File Organizer AppImage

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building File Organizer AppImage ==="

# Clean previous build
echo "Cleaning previous build..."
rm -f file-organizer-x86_64.AppImage

# Update AppDir with latest source code
echo "Updating AppDir with latest source code..."

# Copy source code
echo "  Copying source files..."
rm -rf AppDir/usr/lib/python3.12/site-packages/file_organizer
mkdir -p AppDir/usr/lib/python3.12/site-packages/file_organizer
cp -r src/file_organizer/* AppDir/usr/lib/python3.12/site-packages/file_organizer/

# Copy __init__.py if it exists
if [ -f src/file_organizer/__init__.py ]; then
    cp src/file_organizer/__init__.py AppDir/usr/lib/python3.12/site-packages/file_organizer/
fi

# Ensure dependencies are installed in AppDir
echo "  Installing dependencies..."
# Check if we need to install dependencies
if [ ! -d "AppDir/usr/lib/python3.12/site-packages/unidecode" ] || \
   [ ! -d "AppDir/usr/lib/python3.12/site-packages/yaml" ]; then
    echo "    Installing Python dependencies..."
    # Use the Python from AppDir to install packages
    AppDir/usr/bin/python3 -m pip install --target AppDir/usr/lib/python3.12/site-packages \
        --no-deps unidecode pyyaml 2>/dev/null || {
        echo "    Warning: Could not install via pip, checking if packages exist..."
    }
fi

# Verify AppRun is executable
chmod +x AppDir/AppRun
chmod +x AppDir/usr/bin/file-organizer
chmod +x AppDir/usr/bin/python3

# Build AppImage
echo "Building AppImage..."
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Error: appimagetool-x86_64.AppImage not found!"
    echo "Please download it from: https://github.com/AppImage/AppImageKit/releases"
    exit 1
fi

chmod +x appimagetool-x86_64.AppImage

# Run appimagetool
./appimagetool-x86_64.AppImage AppDir file-organizer-x86_64.AppImage

if [ -f "file-organizer-x86_64.AppImage" ]; then
    chmod +x file-organizer-x86_64.AppImage
    echo ""
    echo "=== Build successful! ==="
    echo "AppImage created: file-organizer-x86_64.AppImage"
    echo ""
    echo "To test:"
    echo "  ./file-organizer-x86_64.AppImage --help"
    echo ""
    ls -lh file-organizer-x86_64.AppImage
else
    echo "Error: AppImage build failed!"
    exit 1
fi

