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

# Patch bluetooth service configuration
if [ -f /etc/systemd/system/dbus-org.bluez.service ]; then
    BT_FILE="/etc/systemd/system/dbus-org.bluez.service"
else
    BT_FILE="/lib/systemd/system/bluetooth.service"
fi

sudo cp "$BT_FILE" "${BT_FILE}.backup.$(date +%Y%m%d_%H%M%S)"

# Ensure ExecStart has the correct value
sudo sed -i 's|^ExecStart=.*|ExecStart=/usr/lib/bluetooth/bluetoothd -C|g' "$BT_FILE"
if ! grep -q "^ExecStartPost=" "$BT_FILE"; then
    sudo sed -i '/^ExecStart=/a ExecStartPost=/usr/bin/sdptool add SP' "$BT_FILE"
else
    sudo sed -i 's|^ExecStartPost=.*|ExecStartPost=/usr/bin/sdptool add SP|g' "$BT_FILE"
fi

# Reload systemd and restart bluetooth service
sudo systemctl daemon-reload


# Create RFCOMM service
sudo tee /etc/systemd/system/rfcomm.service > /dev/null << 'EOF'
[Unit]
Description=RFCOMM service
After=bluetooth.service
Requires=bluetooth.service

[Service]
ExecStart=/usr/bin/rfcomm watch hci0

[Install]
WantedBy=multi-user.target
EOF

# Reload all services
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
sudo systemctl enable rfcomm.service

# Connect OBD adapter via bluetoothctl
timeout 30 bluetoothctl << EOF
power on
agent on
default-agent
scan le
EOF

sleep 5

OBD_MAC=$(cat /opt/carbuddy/config/obd_mac_address.txt | tr -d '[:space:]')
timeout 15 bluetoothctl << EOF
pair $OBD_MAC
trust $OBD_MAC
disconnect $OBD_MAC
exit
EOF

# Create virtual serial port for python-obd
# TODO create a service to run this
sudo rfcomm connect hci0 $OBD_MAC &
