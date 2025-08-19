#!/bin/bash

cd /opt/carbuddy

# Create virtual environment
python3 -m venv .venv

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt
