#!/bin/bash
set -e

# Configuration
APPIMAGE_NAME="file-organizer-x86_64.AppImage"
DEPLOY_DIR="/mnt/share/Pron"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "Building and Deploying File Organizer AppImage"
echo "================================================"
echo ""

# ============================================================================
# PHASE 1: BUILD APPIMAGE
# ============================================================================

echo "================================================"
echo "Phase 1: Building AppImage"
echo "================================================"

# Clean previous builds
echo "Cleaning previous build artifacts..."
rm -rf build dist AppDir *.AppImage squashfs-root

# Install dependencies in build environment
echo "Upgrading pip, setuptools, wheel..."
python3 -m pip install --upgrade pip setuptools wheel --break-system-packages

# Create AppDir structure
echo "Creating AppDir structure..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/lib/python3.12/site-packages
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# Install application and dependencies
echo "Installing application and dependencies..."
pip3 install --target=AppDir/usr/lib/python3.12/site-packages --break-system-packages \
    unidecode pyyaml xxhash pymediainfo .

# Copy entry point
echo "Creating entry point script..."
cat > AppDir/usr/bin/file-organizer <<'EOF'
#!/bin/bash
APPDIR="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
export PYTHONPATH="$APPDIR/usr/lib/python3.12/site-packages:$PYTHONPATH"
export PYTHONHOME="$APPDIR/usr"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
exec "$APPDIR/usr/bin/python3" -m file_organizer.cli "$@"
EOF
chmod +x AppDir/usr/bin/file-organizer

# Bundle Python interpreter
echo "Copying Python interpreter..."
PYTHON_BINARY=$(readlink -f $(which python3))
echo "  Found Python at: $PYTHON_BINARY"
cp -L "$PYTHON_BINARY" AppDir/usr/bin/python3
chmod +x AppDir/usr/bin/python3

# Copy Python standard library
echo "Copying Python standard library..."
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python version: $PYTHON_VERSION"
if [ -d "/usr/lib/python${PYTHON_VERSION}" ]; then
    mkdir -p "AppDir/usr/lib/python${PYTHON_VERSION}"
    cp -a "/usr/lib/python${PYTHON_VERSION}"/* "AppDir/usr/lib/python${PYTHON_VERSION}/" 2>/dev/null || true
fi

# Also copy Python shared libraries
echo "Copying Python shared libraries..."
cp -a /usr/lib/x86_64-linux-gnu/libpython${PYTHON_VERSION}*.so* AppDir/usr/lib/ 2>/dev/null || true

# Copy required system libraries
echo "Copying system libraries..."
mkdir -p AppDir/usr/lib
for lib in libmediainfo.so* libzen.so* libz.so* libstdc++.so*; do
    find /usr/lib /lib -name "$lib" -exec cp -a {} AppDir/usr/lib/ \; 2>/dev/null || true
done

# Copy desktop entry and icon
echo "Copying desktop entry and icon..."
cp appimage/file-organizer.desktop AppDir/file-organizer.desktop
cp appimage/file-organizer.desktop AppDir/usr/share/applications/
cp appimage/file-organizer.png AppDir/file-organizer.png
cp appimage/file-organizer.png AppDir/usr/share/icons/hicolor/256x256/apps/

# Create .DirIcon symlink
cd AppDir
ln -sf file-organizer.png .DirIcon
cd ..

# Create AppRun
echo "Creating AppRun launcher..."
cat > AppDir/AppRun <<'EOF'
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="$APPDIR/usr/lib/python3.12/site-packages:$PYTHONPATH"
export PYTHONHOME="$APPDIR/usr"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
export PATH="$APPDIR/usr/bin:$PATH"

# Run the application
exec "$APPDIR/usr/bin/python3" -m file_organizer.cli "$@"
EOF
chmod +x AppDir/AppRun

# Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -c "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

# Build AppImage
echo "Building AppImage..."
ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir file-organizer-x86_64.AppImage

APPIMAGE_PATH="${SCRIPT_DIR}/${APPIMAGE_NAME}"
APPIMAGE_SIZE=$(ls -lh "$APPIMAGE_PATH" | awk '{print $5}')

echo ""
echo "✓ AppImage built successfully: $APPIMAGE_PATH ($APPIMAGE_SIZE)"
echo ""

# ============================================================================
# PHASE 2: DEPLOY APPIMAGE
# ============================================================================

echo "================================================"
echo "Phase 2: Deploying AppImage"
echo "================================================"

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

# Copy default config file only if it doesn't already exist
CONFIG_FILE=".file_organizer.yaml"
CONFIG_SOURCE="${SCRIPT_DIR}/${CONFIG_FILE}"
CONFIG_DEST="${DEPLOY_DIR}/${CONFIG_FILE}"

if [ -f "$CONFIG_SOURCE" ]; then
    if [ -f "$CONFIG_DEST" ]; then
        echo "Config file already exists in deployment directory, skipping..."
    else
        echo "Copying config file to deployment directory..."
        cp "$CONFIG_SOURCE" "$CONFIG_DEST"
        if [ $? -eq 0 ]; then
            echo "✓ Config file copied successfully"
        else
            echo "⚠ Warning: Failed to copy config file"
        fi
    fi
else
    echo "⚠ Warning: Default config file not found at $CONFIG_SOURCE"
fi

# Verify deployment
if [ -f "$DEPLOYED_PATH" ] && [ -x "$DEPLOYED_PATH" ]; then
    DEPLOYED_SIZE=$(ls -lh "$DEPLOYED_PATH" | awk '{print $5}')
    echo ""
    echo "================================================"
    echo "Build and Deployment Complete!"
    echo "================================================"
    echo "Deployed to: $DEPLOYED_PATH"
    echo "Size: $DEPLOYED_SIZE"
    echo ""
    echo "Test it with: $DEPLOYED_PATH --version"
else
    echo "✗ Deployment verification failed"
    exit 1
fi

