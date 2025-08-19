#!/bin/bash -e

# Configure systemd services for CarBuddy
echo "Configuring systemd services..."

# Copy systemd service file
cp "${STAGE_DIR}/../../systemd/sentry-carbuddy.service" /etc/systemd/system/

# Set proper permissions
chmod 644 /etc/systemd/system/sentry-carbuddy.service

# Enable Bluetooth service
systemctl enable bluetooth

# Install first-boot setup script
cp "${STAGE_DIR}/../../first-boot-setup.sh" /usr/local/bin/
chmod +x /usr/local/bin/first-boot-setup.sh

# Create systemd service for first-boot setup
cat > /etc/systemd/system/carbuddy-firstboot.service << 'EOF'
[Unit]
Description=CarBuddy First Boot Setup
After=network.target bluetooth.service
Wants=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/first-boot-setup.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable first-boot service
systemctl enable carbuddy-firstboot.service

# Enable CarBuddy service (will be started after first-boot setup)
systemctl enable sentry-carbuddy.service

echo "Systemd services configured successfully"
