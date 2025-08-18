"""
OBD-II communication manager for CarBuddy.

Handles connection to the factory-paired Veepeak OBDCheck BLE+ adapter
and provides DTC reading functionality using python-OBD library.
"""

import logging
import time
from typing import List, Tuple, Optional, Dict, Any

try:
    import obd

    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False


class OBDManager:
    """OBD-II communication manager for CarBuddy."""

    def __init__(self, port: Optional[str] = None):
        """Initialize OBD manager.

        Args:
            port: Optional serial port. If None, auto-detect is used.
        """
        self.port = port
        self.connection: Optional["obd.OBD"] = None
        self.logger = logging.getLogger(__name__)
        self.last_dtc_read = 0
        self.connection_retries = 0
        self.max_connection_retries = 3

        if not OBD_AVAILABLE:
            self.logger.error("python-OBD library not available")
            raise ImportError("python-OBD library is required but not installed")

    def connect(self) -> bool:
        """Connect to the factory-paired OBD-II adapter.

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected():
            return True

        self.logger.info(
            f"Connecting to OBD-II adapter{' on ' + self.port if self.port else ' (auto-detect)'}"
        )

        try:
            # Connect to OBD-II adapter
            if self.port:
                self.connection = obd.OBD(self.port)
            else:
                # Auto-detect - python-OBD will find the connected adapter
                self.connection = obd.OBD()

            if self.connection and self.connection.is_connected():
                self.logger.info(f"Successfully connected to OBD-II adapter")
                self.logger.info(f"Port: {self.connection.port_name()}")
                self.logger.info(f"Protocol: {self.connection.protocol_name()}")

                # Log supported commands for diagnostics
                supported_count = len(self.connection.supported_commands)
                self.logger.info(f"Adapter supports {supported_count} OBD commands")

                self.connection_retries = 0
                return True
            else:
                self.logger.error("Failed to connect to OBD-II adapter")
                return False

        except Exception as e:
            self.logger.error(f"OBD connection error: {e}")
            self.connection_retries += 1
            return False

    def disconnect(self) -> None:
        """Disconnect from OBD-II adapter."""
        if self.connection:
            try:
                self.connection.close()
                self.logger.info("Disconnected from OBD-II adapter")
            except Exception as e:
                self.logger.error(f"Error during disconnect: {e}")
            finally:
                self.connection = None

    def is_connected(self) -> bool:
        """Check if connected to OBD-II adapter.

        Returns:
            True if connected, False otherwise
        """
        return (
            self.connection is not None
            and hasattr(self.connection, "is_connected")
            and self.connection.is_connected()
        )

    def get_dtcs(self) -> List[Tuple[str, str]]:
        """Retrieve Diagnostic Trouble Codes from the vehicle.

        Returns:
            List of (code, description) tuples, empty list if no DTCs or error
        """
        if not self.is_connected():
            self.logger.warning("Not connected to OBD-II adapter")
            return []

        try:
            self.logger.debug("Querying DTCs from vehicle")
            response = self.connection.query(obd.commands.GET_DTC)

            if response.is_null():
                self.logger.debug("DTC query returned null response")
                return []

            dtcs = response.value or []
            self.last_dtc_read = time.time()

            if dtcs:
                self.logger.info(f"Retrieved {len(dtcs)} DTCs from vehicle")
                for code, description in dtcs:
                    self.logger.info(f"DTC: {code} - {description}")
            else:
                self.logger.debug("No DTCs found in vehicle")

            return dtcs

        except Exception as e:
            self.logger.error(f"Error reading DTCs: {e}")
            return []

    def clear_dtcs(self) -> bool:
        """Clear stored DTCs from the vehicle.

        Returns:
            True if DTCs were cleared successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.warning("Not connected to OBD-II adapter for DTC clearing")
            return False

        try:
            self.logger.info("Clearing DTCs from vehicle")
            response = self.connection.query(obd.commands.CLEAR_DTC)

            success = not response.is_null()
            if success:
                self.logger.info("DTCs cleared successfully")
            else:
                self.logger.warning("DTC clear command returned null response")

            return success

        except Exception as e:
            self.logger.error(f"Error clearing DTCs: {e}")
            return False

    def get_vehicle_info(self) -> Dict[str, Any]:
        """Get basic vehicle information if available.

        Returns:
            Dictionary with available vehicle information
        """
        if not self.is_connected():
            return {}

        info = {}

        # Try to get VIN
        try:
            vin_response = self.connection.query(obd.commands.VIN)
            if not vin_response.is_null():
                info["vin"] = str(vin_response.value)
        except Exception as e:
            self.logger.debug(f"Could not retrieve VIN: {e}")

        # Try to get fuel system status
        try:
            fuel_response = self.connection.query(obd.commands.FUEL_STATUS)
            if not fuel_response.is_null():
                info["fuel_status"] = str(fuel_response.value)
        except Exception as e:
            self.logger.debug(f"Could not retrieve fuel status: {e}")

        # Try to get engine load
        try:
            load_response = self.connection.query(obd.commands.ENGINE_LOAD)
            if not load_response.is_null():
                info["engine_load"] = str(load_response.value)
        except Exception as e:
            self.logger.debug(f"Could not retrieve engine load: {e}")

        return info

    def get_connection_info(self) -> Dict[str, Any]:
        """Get OBD connection information for diagnostics.

        Returns:
            Dictionary with connection details
        """
        info = {
            "connected": self.is_connected(),
            "port": self.port,
            "connection_retries": self.connection_retries,
            "last_dtc_read": self.last_dtc_read,
        }

        if self.connection:
            try:
                info.update(
                    {
                        "port_name": self.connection.port_name(),
                        "protocol_name": self.connection.protocol_name(),
                        "protocol_id": str(self.connection.protocol_id()),
                        "supported_commands_count": len(
                            self.connection.supported_commands
                        ),
                    }
                )
            except Exception as e:
                info["connection_error"] = str(e)

        return info

    def test_communication(self) -> bool:
        """Test basic communication with the OBD adapter.

        Returns:
            True if communication test passed, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            # Try a simple query that most vehicles support
            response = self.connection.query(obd.commands.RPM)

            # Response doesn't have to have a value, just not be null
            success = not response.is_null()

            if success:
                self.logger.debug("OBD communication test passed")
            else:
                self.logger.warning("OBD communication test failed - null response")

            return success

        except Exception as e:
            self.logger.error(f"OBD communication test failed: {e}")
            return False

    def reconnect(self) -> bool:
        """Reconnect to the OBD-II adapter.

        Returns:
            True if reconnection successful, False otherwise
        """
        self.logger.info("Attempting OBD-II reconnection")

        # Disconnect first
        self.disconnect()

        # Wait a moment
        time.sleep(2)

        # Attempt to reconnect
        return self.connect()

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of OBD connection.

        Returns:
            Dictionary with health information
        """
        health = {
            "connected": self.is_connected(),
            "communication_test_passed": False,
            "last_dtc_read_time": self.last_dtc_read,
            "connection_retries": self.connection_retries,
            "max_retries_reached": self.connection_retries
            >= self.max_connection_retries,
        }

        # Add connection info
        health.update(self.get_connection_info())

        # Test communication if connected
        if self.is_connected():
            health["communication_test_passed"] = self.test_communication()

        return health
