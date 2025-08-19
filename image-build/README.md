# CarBuddy Image Builder

This directory contains the pi-gen stages and build scripts to create a custom Raspberry Pi OS Lite image with CarBuddy pre-installed.

## Prerequisites

- Docker installed and running
- Git

## Building the Image

1. Navigate to the image-build directory:
   ```bash
   cd image-build
   ```

2. Run the build script:
   ```bash
   ./build-carbuddy-image.sh
   ```

The script will:
- Clone the official pi-gen repository if not present
- Copy the CarBuddy stage files
- Build the image using Docker
- Output the final image in `pi-gen/deploy/`

## Build Stages

The CarBuddy image is built using these stages:

### stage0-2 (Built-in)
Standard Raspberry Pi OS Lite base system

### stage-carbuddy (Custom)
Our custom stage that installs CarBuddy:

1. **00-install-packages**: Install system packages (bluetooth, python3-venv)
2. **01-setup-python**: Create Python virtual environment
3. **02-install-carbuddy**: Install CarBuddy application files and Python dependencies
4. **03-configure-services**: Set up systemd services

## Output

The build produces:
- `carbuddy-lite-YYYY-MM-DD.img` - Ready-to-flash Pi image
- Image includes complete CarBuddy installation
- Still requires first-boot setup for Bluetooth pairing

## Flashing

Use standard Pi imaging tools:
```bash
# With Raspberry Pi Imager (recommended)
rpi-imager

# Or with dd
sudo dd if=carbuddy-lite-YYYY-MM-DD.img of=/dev/sdX bs=4M
```

## Notes

- Build time: ~30-60 minutes depending on system
- Image size: ~2-3GB
- Works on macOS, Linux, and Windows (via Docker)
