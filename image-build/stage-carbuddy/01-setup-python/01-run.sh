#!/bin/bash -e

# Set up Python environment for CarBuddy
echo "Setting up Python environment..."

# Create CarBuddy application directory
mkdir -p /opt/sentry-carbuddy

# Create Python virtual environment
python3 -m venv /opt/sentry-carbuddy/venv

# Upgrade pip in virtual environment
/opt/sentry-carbuddy/venv/bin/pip install --upgrade pip setuptools wheel

echo "Python environment created successfully"
