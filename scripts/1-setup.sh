#!/bin/bash

# System setup
cat >> ~/.bashrc << 'EOF'

# Fix locale settings
export LC_ALL=en_GB.UTF-8
export LANG=en_GB.UTF-8
export LANGUAGE=en_GB.UTF-8
EOF

export LC_ALL=en_GB.UTF-8
export LANG=en_GB.UTF-8


# Setup the python application
cd /opt/carbuddy
python3 -m venv .venv
source venv/bin/activate
pip install -r requirements.txt


# Setup bluetooth and connect the adapter
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

