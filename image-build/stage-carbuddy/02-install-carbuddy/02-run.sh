#!/bin/bash -e

# Install CarBuddy application files
echo "Installing CarBuddy application..."

# Copy application files from source
cp -r "${STAGE_DIR}/../../carbuddy/src" /opt/sentry-carbuddy/
cp "${STAGE_DIR}/../../carbuddy/main.py" /opt/sentry-carbuddy/
cp -r "${STAGE_DIR}/../../carbuddy/config" /opt/sentry-carbuddy/

# Create logs directory
mkdir -p /opt/sentry-carbuddy/logs

# Install Python dependencies
echo "Installing Python dependencies..."
/opt/sentry-carbuddy/venv/bin/pip install -r "${STAGE_DIR}/../../carbuddy/requirements.txt"

# Set ownership to pi user
chown -R pi:pi /opt/sentry-carbuddy

# Make main.py executable
chmod +x /opt/sentry-carbuddy/main.py

echo "CarBuddy application installed successfully"
