#!/bin/bash -e

# CarBuddy First Boot Setup
# Pairs with specific Veepeak adapter and configures device-specific settings

echo "🚗 CarBuddy First Boot Setup"
echo "============================"

# Configuration
CARBUDDY_DIR="/opt/sentry-carbuddy"
ADAPTER_MAC_FILE="${CARBUDDY_DIR}/config/adapter_mac.txt"
FIRSTBOOT_FLAG="/boot/carbuddy-firstboot"

# Check if first boot setup is needed
if [ ! -f "${FIRSTBOOT_FLAG}" ]; then
    echo "ℹ️  First boot setup not requested - skipping"
    exit 0
fi

# Read adapter MAC from first boot flag file
ADAPTER_MAC=$(cat "${FIRSTBOOT_FLAG}" 2>/dev/null || echo "")

if [ -z "${ADAPTER_MAC}" ]; then
    echo "❌ Error: No adapter MAC address provided in ${FIRSTBOOT_FLAG}"
    echo "   File should contain MAC address like: AA:BB:CC:DD:EE:FF"
    exit 1
fi

echo "🔵 Pairing with adapter: ${ADAPTER_MAC}"

# Ensure Bluetooth service is running
systemctl start bluetooth
sleep 3

# Attempt Bluetooth pairing
echo "🔍 Scanning for Bluetooth devices..."
timeout 30 bluetoothctl scan on &
SCAN_PID=$!

# Wait a bit for scan to find devices
sleep 10

# Stop scanning
kill $SCAN_PID 2>/dev/null || true
bluetoothctl scan off

# Attempt to pair with the specific adapter
echo "🤝 Pairing with ${ADAPTER_MAC}..."
if bluetoothctl pair "${ADAPTER_MAC}"; then
    echo "✅ Pairing successful"

    # Trust the device
    bluetoothctl trust "${ADAPTER_MAC}"
    echo "✅ Device trusted"

    # Try to connect
    if bluetoothctl connect "${ADAPTER_MAC}"; then
        echo "✅ Connection successful"
    else
        echo "⚠️  Connection failed but pairing completed"
    fi

    # Write MAC address to CarBuddy config
    echo "📝 Writing adapter MAC to CarBuddy config..."
    echo "# Factory-provisioned adapter MAC address" > "${ADAPTER_MAC_FILE}"
    echo "# Provisioned on first boot: $(date)" >> "${ADAPTER_MAC_FILE}"
    echo "${ADAPTER_MAC}" >> "${ADAPTER_MAC_FILE}"

    # Set ownership
    chown pi:pi "${ADAPTER_MAC_FILE}"

    echo "✅ Adapter MAC written to ${ADAPTER_MAC_FILE}"

else
    echo "❌ Pairing failed with ${ADAPTER_MAC}"
    echo "   Ensure adapter is in pairing mode and in range"
    exit 1
fi

# Enable CarBuddy service now that pairing is complete
echo "🚀 Enabling CarBuddy service..."
systemctl enable sentry-carbuddy.service

# Remove first boot flag to prevent re-running
rm -f "${FIRSTBOOT_FLAG}"

echo ""
echo "✅ First boot setup completed successfully!"
echo "🎉 CarBuddy is ready to use"
echo ""
echo "To start CarBuddy service immediately:"
echo "  sudo systemctl start sentry-carbuddy.service"
echo ""
