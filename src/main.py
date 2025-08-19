"""
Sentry CarBuddy - OBD-II Vehicle Diagnostics to Sentry Integration

A headless Raspberry Pi application that reads Diagnostic Trouble Codes (DTCs)
from vehicles via a factory-paired Bluetooth OBD-II adapter and reports them
to Sentry.io for monitoring and alerting.
"""

import obd
import time
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("carbuddy")


class CarBuddy:
    """OBD-II connection manager and DTC checker."""

    def __init__(self):
        self.connection = None
        self.backoff_delay = 1  # Start with 1 second
        self.max_backoff = 30  # Maximum backoff delay

    def _connect_to_obd(self):
        """Connect to OBD-II adapter with error handling."""
        try:
            connection = obd.OBD()
            if not connection.is_connected():
                logger.error("Could not connect to OBD-II adapter")
                return None
            logger.info(f"Connected to: {connection.port_name()}")
            return connection
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            return None

    def ensure_connected(self):
        """Ensure we have an active connection, establishing/re-establishing as needed.
        Returns True if connected, False if connection failed (caller should wait)."""
        # Early return if already connected
        if self.connection is not None and self.connection.is_connected():
            return True

        # Handle connection loss
        if self.connection:
            logger.warning("Connection lost, attempting to reconnect...")
            self.connection.close()
            self.connection = None

        logger.info(
            f"Attempting to connect (retry in {self.backoff_delay}s if failed)..."
        )
        self.connection = self._connect_to_obd()

        # Connection failed, apply exponential backoff
        if self.connection is None:
            logger.warning(
                f"Connection failed. Retrying in {self.backoff_delay} seconds..."
            )
            time.sleep(self.backoff_delay)
            self.backoff_delay = min(self.backoff_delay * 2, self.max_backoff)
            return False

        # Connection successful, reset backoff delay
        self.backoff_delay = 1
        return True

    def check_dtcs(self):
        """Check for Diagnostic Trouble Codes (DTCs) and log results. Assumes connection is established."""
        try:
            logger.info("Checking for DTCs...")

            assert self.connection is not None
            response = self.connection.query(obd.commands["GET_DTC"])

            if response.is_null():
                logger.warning(
                    "No response from vehicle (command not supported or connection issue)"
                )
            elif not response.value:
                logger.info("✅ No DTCs found - Vehicle is healthy")
            else:
                logger.warning(f"⚠️  Found {len(response.value)} DTC(s):")
                for dtc_code, dtc_description in response.value:
                    logger.warning(f"   • {dtc_code}: {dtc_description}")
        except Exception as e:
            logger.error(f"Error during DTC check: {e}", exc_info=True)

    def close(self):
        """Close the connection if it exists."""
        if self.connection:
            self.connection.close()
            logger.info("Connection closed.")


def main():
    logger.info("Starting Sentry CarBuddy")

    car_buddy = CarBuddy()

    try:
        while True:
            # Try to establish/maintain connection
            if not car_buddy.ensure_connected():
                continue  # Connection failed, ensure_connected already handled the backoff delay

            car_buddy.check_dtcs()
            time.sleep(30)  # Wait before next check

    except KeyboardInterrupt:
        logger.info("Shutting down Sentry CarBuddy")
    finally:
        car_buddy.close()


if __name__ == "__main__":
    main()
