#!/usr/bin/env python3
"""
Sentry CarBuddy - Main Application

Main entry point for the CarBuddy application that orchestrates OBD-II
communication, Bluetooth management, and Sentry error reporting.
"""

import sys
import time
import signal
import argparse
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config
from src.utils import setup_logging, ensure_directory_exists
from src.obd_manager import OBDManager
from src.bluetooth_mgr import BluetoothManager
from src.sentry_client import SentryClient


class CarBuddyApplication:
    """Main CarBuddy application class."""

    def __init__(self, config_dir: str = None, mock_mode: bool = False):
        """Initialize CarBuddy application.

        Args:
            config_dir: Optional configuration directory path
            mock_mode: Enable mock mode for testing without hardware
        """
        self.config_dir = config_dir
        self.mock_mode = mock_mode
        self.running = False
        self.config = None
        self.logger = None
        self.obd_manager = None
        self.bluetooth_manager = None
        self.sentry_client = None

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if self.logger:
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def initialize(self) -> bool:
        """Initialize all application components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load configuration
            self.config = Config(self.config_dir)

            if not self.config.validate():
                print("ERROR: Invalid configuration. Please check your settings.")
                return False

            # Set up logging
            log_file = None
            if not self.mock_mode:
                # Ensure logs directory exists
                if self.config_dir:
                    log_dir = Path(self.config_dir).parent / "logs"
                else:
                    log_dir = Path("/opt/sentry-carbuddy/logs")

                ensure_directory_exists(str(log_dir))
                log_file = str(log_dir / "carbuddy.log")

            self.logger = setup_logging(
                log_level=self.config.log_level, log_file=log_file
            )

            self.logger.info("=" * 50)
            self.logger.info("🚗 Starting Sentry CarBuddy Application")
            self.logger.info("=" * 50)

            if self.mock_mode:
                self.logger.warning(
                    "⚠️  Running in MOCK MODE - no real hardware interaction"
                )

            # Log configuration info
            self.logger.info(f"Configuration loaded from: {self.config.config_dir}")
            self.logger.info(
                f"Sentry DSN configured: {'Yes' if self.config.sentry_dsn else 'No'}"
            )
            self.logger.info(f"Adapter MAC: {self.config.adapter_mac}")
            self.logger.info(f"Poll interval: {self.config.poll_interval} seconds")

            # Initialize Sentry client
            self.sentry_client = SentryClient(
                dsn=self.config.sentry_dsn, device_info=self.config.device_info
            )

            if not self.mock_mode:
                # Test Sentry connection
                if self.sentry_client.test_connection():
                    self.logger.info("✅ Sentry connection test passed")
                else:
                    self.logger.error("❌ Sentry connection test failed")
                    return False

            if not self.mock_mode:
                # Initialize Bluetooth manager
                self.bluetooth_manager = BluetoothManager(self.config.adapter_mac)

                # Initialize OBD manager
                self.obd_manager = OBDManager(port=self.config.obd_port)

                # Test initial connections
                if not self._test_initial_connections():
                    return False
            else:
                self.logger.info("🧪 Mock mode: Skipping hardware initialization")

            self.logger.info("✅ CarBuddy application initialized successfully")
            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize CarBuddy application: {e}")
            else:
                print(f"ERROR: Failed to initialize CarBuddy application: {e}")

            if self.sentry_client:
                self.sentry_client.capture_exception(e)

            return False

    def _test_initial_connections(self) -> bool:
        """Test initial hardware connections.

        Returns:
            True if connections are healthy, False otherwise
        """
        # Check Bluetooth service
        if not self.bluetooth_manager.get_bluetooth_service_status():
            self.logger.error("❌ Bluetooth service is not running")
            return False

        # Check if adapter is paired
        if not self.bluetooth_manager.is_adapter_paired():
            self.logger.error(f"❌ Adapter {self.config.adapter_mac} is not paired")
            self.logger.error("This indicates a factory provisioning issue")
            return False

        # Check Bluetooth connection
        if not self.bluetooth_manager.is_connected():
            self.logger.warning(
                f"⚠️  Adapter {self.config.adapter_mac} is not currently connected"
            )
            self.logger.info("Attempting to reconnect...")

            if self.bluetooth_manager.attempt_reconnection():
                self.logger.info("✅ Bluetooth reconnection successful")
            else:
                self.logger.error("❌ Bluetooth reconnection failed")
                return False
        else:
            self.logger.info("✅ Bluetooth adapter is connected")

        # Test OBD connection
        if self.obd_manager.connect():
            self.logger.info("✅ OBD-II connection established")

            # Test basic communication
            if self.obd_manager.test_communication():
                self.logger.info("✅ OBD-II communication test passed")
            else:
                self.logger.warning("⚠️  OBD-II communication test failed")
                # Don't fail initialization, might work during operation
        else:
            self.logger.error("❌ Failed to connect to OBD-II adapter")
            return False

        return True

    def run(self) -> None:
        """Run the main application loop."""
        if not self.initialize():
            sys.exit(1)

        self.running = True

        try:
            self.logger.info("🚀 Starting main application loop")

            while self.running:
                if self.mock_mode:
                    self._mock_iteration()
                else:
                    self._real_iteration()

                # Sleep between iterations
                for _ in range(self.config.poll_interval):
                    if not self.running:
                        break
                    time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
            if self.sentry_client:
                self.sentry_client.capture_exception(e)

        finally:
            self.shutdown()

    def _real_iteration(self) -> None:
        """Perform one iteration of the main loop with real hardware."""
        try:
            # Check Bluetooth connection health
            if not self.bluetooth_manager.is_connected():
                self.logger.warning(
                    "Bluetooth adapter disconnected, attempting reconnection..."
                )
                if not self.bluetooth_manager.attempt_reconnection():
                    self.logger.error(
                        "Bluetooth reconnection failed, skipping this iteration"
                    )
                    return

            # Ensure OBD connection
            if not self.obd_manager.is_connected():
                self.logger.info(
                    "OBD-II adapter disconnected, attempting reconnection..."
                )
                if not self.obd_manager.reconnect():
                    self.logger.error(
                        "OBD-II reconnection failed, skipping this iteration"
                    )
                    return

            # Read DTCs
            self.logger.debug("Reading DTCs from vehicle...")
            dtcs = self.obd_manager.get_dtcs()

            if dtcs:
                self.logger.info(f"📋 Found {len(dtcs)} DTCs, reporting to Sentry")
                self.sentry_client.report_dtcs(dtcs)
            else:
                self.logger.debug("No DTCs found - vehicle is healthy! 🎉")

            # Log health status periodically
            self._log_health_status()

        except Exception as e:
            self.logger.error(f"Error in real iteration: {e}")
            if self.sentry_client:
                self.sentry_client.capture_exception(e)

    def _mock_iteration(self) -> None:
        """Perform one iteration in mock mode for testing."""
        self.logger.info("🧪 Mock iteration - simulating DTC reading...")

        # Simulate finding DTCs occasionally
        import random

        if random.random() < 0.3:  # 30% chance of mock DTCs
            mock_dtcs = [
                ("P0171", "System Too Lean (Bank 1)"),
                ("P0420", "Catalyst System Efficiency Below Threshold (Bank 1)"),
            ]

            self.logger.info(f"📋 Mock: Found {len(mock_dtcs)} DTCs")
            for code, desc in mock_dtcs:
                self.logger.info(f"Mock DTC: {code} - {desc}")

            # Don't actually send to Sentry in mock mode
            # self.sentry_client.report_dtcs(mock_dtcs)
        else:
            self.logger.debug("Mock: No DTCs found")

    def _log_health_status(self) -> None:
        """Log periodic health status information."""
        try:
            bluetooth_health = self.bluetooth_manager.get_connection_health()
            obd_health = self.obd_manager.get_health_status()

            self.logger.debug(f"Bluetooth Health: {bluetooth_health}")
            self.logger.debug(f"OBD Health: {obd_health}")

        except Exception as e:
            self.logger.warning(f"Failed to get health status: {e}")

    def shutdown(self) -> None:
        """Graceful application shutdown."""
        self.logger.info("🛑 Shutting down CarBuddy application...")

        try:
            # Disconnect OBD
            if self.obd_manager:
                self.obd_manager.disconnect()

            self.logger.info("✅ CarBuddy application shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sentry CarBuddy Application")
    parser.add_argument("--config-dir", help="Configuration directory path")
    parser.add_argument(
        "--mock", action="store_true", help="Run in mock mode for testing"
    )

    args = parser.parse_args()

    # Create and run application
    app = CarBuddyApplication(config_dir=args.config_dir, mock_mode=args.mock)

    app.run()


if __name__ == "__main__":
    main()
