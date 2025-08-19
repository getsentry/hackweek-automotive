#!/bin/bash -e

# Install system packages required for CarBuddy
echo "Installing system packages for CarBuddy..."

# Update package lists
apt-get update

# Install required packages
apt-get install -y \
    python3-venv \
    bluetooth \
    bluez \
    bluez-tools

# Clean up package cache to reduce image size
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "System packages installed successfully"
