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

# Read OBD adapter MAC address from file
OBD_MAC=$(cat /opt/carbuddy/config/obd_mac_address.txt | tr -d '[:space:]')

# Connect OBD adapter via bluetoothctl
timeout 30 bluetoothctl << EOF
power on
agent on
default-agent
scan le
EOF

sleep 5

timeout 15 bluetoothctl << EOF
pair $OBD_MAC
trust $OBD_MAC
exit
EOF

# Create virtual serial port for python-obd
# TODO create a service to run this
sudo rfcomm connect hci0 $OBD_MAC &
