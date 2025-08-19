"""
Sentry CarBuddy - OBD-II Vehicle Diagnostics to Sentry Integration

A headless Raspberry Pi application that reads Diagnostic Trouble Codes (DTCs)
from vehicles via a factory-paired Bluetooth OBD-II adapter and reports them
to Sentry.io for monitoring and alerting.
"""

import obd
import time
from datetime import datetime


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
                print("Error: Could not connect to OBD-II adapter")
                return None
            print(f"Connected to: {connection.port_name()}")
            return connection
        except Exception as e:
            print(f"Connection error: {e}")
            return None

    def ensure_connected(self):
        """Ensure we have an active connection, establishing/re-establishing as needed.
        Returns True if connected, False if connection failed (caller should wait)."""
        # Early return if already connected
        if self.connection is not None and self.connection.is_connected():
            return True

        # Handle connection loss
        if self.connection:
            print("Connection lost, attempting to reconnect...")
            self.connection.close()
            self.connection = None

        print(f"Attempting to connect (retry in {self.backoff_delay}s if failed)...")
        self.connection = self._connect_to_obd()

        # Connection failed, apply exponential backoff
        if self.connection is None:
            print(f"Connection failed. Retrying in {self.backoff_delay} seconds...")
            time.sleep(self.backoff_delay)
            self.backoff_delay = min(self.backoff_delay * 2, self.max_backoff)
            return False

        # Connection successful, reset backoff delay
        self.backoff_delay = 1
        return True

    def check_dtcs(self):
        """Check for Diagnostic Trouble Codes (DTCs) and print results. Assumes connection is established."""
        print(
            f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for DTCs..."
        )

        response = self.connection.query(obd.commands.GET_DTC)

        if response.is_null():
            print(
                "No response from vehicle (command not supported or connection issue)"
            )
        elif not response.value:
            print("✅ No DTCs found - Vehicle is healthy")
        else:
            print(f"⚠️  Found {len(response.value)} DTC(s):")
            for dtc_code, dtc_description in response.value:
                print(f"   • {dtc_code}: {dtc_description}")

    def close(self):
        """Close the connection if it exists."""
        if self.connection:
            self.connection.close()
            print("Connection closed.")


def main():
    print("Starting DTC monitoring...")

    car_buddy = CarBuddy()

    try:
        while True:
            # Try to establish/maintain connection
            if not car_buddy.ensure_connected():
                continue  # Connection failed, ensure_connected already handled the backoff delay

            try:
                car_buddy.check_dtcs()
                time.sleep(30)  # Wait before next check
            except Exception as e:
                print(f"Error during DTC check: {e}")

    except KeyboardInterrupt:
        print("\n\nStopping DTC monitoring...")
    finally:
        car_buddy.close()


if __name__ == "__main__":
    main()
