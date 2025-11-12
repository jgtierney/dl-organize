#!/bin/bash
set -e

echo "================================================"
echo "Building File Organizer AppImage..."
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
# Find the actual Python binary
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
# Copy libmediainfo and dependencies if available
for lib in libmediainfo.so* libzen.so* libz.so* libstdc++.so*; do
    find /usr/lib /lib -name "$lib" -exec cp -a {} AppDir/usr/lib/ \; 2>/dev/null || true
done

# Copy desktop entry and icon
echo "Copying desktop entry and icon..."
cp appimage/file-organizer.desktop AppDir/file-organizer.desktop  # AppImage root
cp appimage/file-organizer.desktop AppDir/usr/share/applications/
cp appimage/file-organizer.png AppDir/file-organizer.png  # AppImage root
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

echo "================================================"
echo "AppImage created successfully!"
echo "================================================"
ls -lh file-organizer-x86_64.AppImage
echo ""
echo "Test it with: ./file-organizer-x86_64.AppImage --version"

