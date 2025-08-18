"""
Bluetooth connection manager for CarBuddy.

Lightweight wrapper for monitoring system-level Bluetooth connections
to the factory-paired Veepeak OBDCheck BLE+ adapter.
"""

import logging
import subprocess
import time
from typing import Optional, List


class BluetoothManager:
    """Lightweight Bluetooth connection monitor for CarBuddy."""

    def __init__(self, adapter_mac: str):
        """Initialize Bluetooth manager.

        Args:
            adapter_mac: MAC address of the factory-paired OBD adapter
        """
        self.adapter_mac = adapter_mac.upper()
        self.logger = logging.getLogger(__name__)
        self.last_connection_check = 0
        self.connection_check_interval = 30  # seconds

    def is_connected(self) -> bool:
        """Check if the factory-paired adapter is connected.

        Returns:
            True if adapter is connected, False otherwise
        """
        current_time = time.time()

        # Rate limit connection checks
        if (current_time - self.last_connection_check) < self.connection_check_interval:
            return self._last_connection_status

        try:
            # Use bluetoothctl to check connection status
            result = subprocess.run(
                ["bluetoothctl", "info", self.adapter_mac],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                output = result.stdout.lower()
                connected = "connected: yes" in output
                self._last_connection_status = connected
                self.last_connection_check = current_time

                if not connected:
                    self.logger.warning(f"Adapter {self.adapter_mac} not connected")

                return connected
            else:
                self.logger.error(f"Failed to get adapter info: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Bluetooth connection check timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error checking Bluetooth connection: {e}")
            return False

    def get_adapter_info(self) -> Optional[dict]:
        """Get detailed information about the paired adapter.

        Returns:
            Dictionary with adapter information or None if unavailable
        """
        try:
            result = subprocess.run(
                ["bluetoothctl", "info", self.adapter_mac],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            # Parse bluetoothctl output
            info = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip()] = value.strip()

            return info

        except Exception as e:
            self.logger.error(f"Error getting adapter info: {e}")
            return None

    def attempt_reconnection(self) -> bool:
        """Attempt to reconnect to the factory-paired adapter.

        Returns:
            True if reconnection was successful, False otherwise
        """
        self.logger.info(f"Attempting to reconnect to adapter {self.adapter_mac}")

        try:
            # Try to connect via bluetoothctl
            result = subprocess.run(
                ["bluetoothctl", "connect", self.adapter_mac],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("Bluetooth reconnection successful")
                # Force connection check on next call
                self.last_connection_check = 0
                return True
            else:
                self.logger.error(f"Bluetooth reconnection failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("Bluetooth reconnection timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error during reconnection attempt: {e}")
            return False

    def get_bluetooth_service_status(self) -> bool:
        """Check if the Bluetooth service is running.

        Returns:
            True if Bluetooth service is active, False otherwise
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "bluetooth"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return result.returncode == 0 and result.stdout.strip() == "active"

        except Exception as e:
            self.logger.error(f"Error checking Bluetooth service: {e}")
            return False

    def restart_bluetooth_service(self) -> bool:
        """Restart the Bluetooth service (requires sudo permissions).

        Returns:
            True if restart was successful, False otherwise
        """
        self.logger.warning("Attempting to restart Bluetooth service")

        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "bluetooth"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info("Bluetooth service restarted successfully")
                # Wait a moment for service to initialize
                time.sleep(5)
                return True
            else:
                self.logger.error(
                    f"Failed to restart Bluetooth service: {result.stderr}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error restarting Bluetooth service: {e}")
            return False

    def list_paired_devices(self) -> List[str]:
        """List all paired Bluetooth devices.

        Returns:
            List of MAC addresses of paired devices
        """
        try:
            result = subprocess.run(
                ["bluetoothctl", "paired-devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return []

            devices = []
            for line in result.stdout.splitlines():
                # Format: "Device AA:BB:CC:DD:EE:FF Device Name"
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "Device":
                    devices.append(parts[1])

            return devices

        except Exception as e:
            self.logger.error(f"Error listing paired devices: {e}")
            return []

    def is_adapter_paired(self) -> bool:
        """Check if the factory adapter is in the paired devices list.

        Returns:
            True if adapter is paired, False otherwise
        """
        paired_devices = self.list_paired_devices()
        return self.adapter_mac in [mac.upper() for mac in paired_devices]

    def get_connection_health(self) -> dict:
        """Get comprehensive Bluetooth connection health information.

        Returns:
            Dictionary with health status information
        """
        health = {
            "bluetooth_service_active": self.get_bluetooth_service_status(),
            "adapter_paired": self.is_adapter_paired(),
            "adapter_connected": self.is_connected(),
            "adapter_mac": self.adapter_mac,
            "paired_devices_count": len(self.list_paired_devices()),
            "last_check_time": time.time(),
        }

        # Add adapter details if available
        adapter_info = self.get_adapter_info()
        if adapter_info:
            health["adapter_info"] = adapter_info

        return health
