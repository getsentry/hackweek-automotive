#!/bin/bash

sudo apt-get update

# Install utilities
sudo apt-get install -y git

# Check out sources
sudo mkdir -p /opt/carbuddy
sudo chown -R $USER:$USER /opt/carbuddy
git clone https://github.com/getsentry/hackweek-automotive.git /opt/carbuddy
cd /opt/carbuddy
git switch manual

# Create virtual environment
python3 -m venv .venv

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt
