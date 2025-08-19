#!/bin/bash -e

# Build CarBuddy Raspberry Pi image using pi-gen
echo "🚗 Building CarBuddy Raspberry Pi Image"
echo "======================================"

# Check if we're in the right directory
if [ ! -d "stage-carbuddy" ]; then
    echo "❌ Error: Must be run from image-build directory"
    echo "Usage: cd image-build && ./build-carbuddy-image.sh"
    exit 1
fi

# Check if pi-gen exists
if [ ! -d "pi-gen" ]; then
    echo "📥 Cloning pi-gen repository..."
    git clone https://github.com/RPi-Distro/pi-gen
fi

# Copy our custom stage to pi-gen
echo "📋 Copying CarBuddy stage to pi-gen..."
cp -r stage-carbuddy pi-gen/

# Copy configuration
echo "⚙️  Copying configuration..."
cp carbuddy-config pi-gen/config

# Build the image
echo "🔨 Building CarBuddy image (this will take a while)..."
cd pi-gen

# Clean previous builds
rm -rf deploy work

# Build using Docker (works on macOS)
./build-docker.sh

echo ""
echo "✅ Build complete!"
echo "📁 Image location: pi-gen/deploy/"
echo "🎉 Ready to flash: carbuddy-lite-$(date +%Y-%m-%d).img"
