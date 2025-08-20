#!/usr/bin/env python3

"""
Sentry CarBuddy - OBD-II Vehicle Diagnostics to Sentry Integration

A headless Raspberry Pi application that reads Diagnostic Trouble Codes (DTCs)
from vehicles via a factory-paired Bluetooth OBD-II adapter and reports them
to Sentry.io for monitoring and alerting.
"""

import obd
import time
import logging
import yaml
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("carbuddy")


LIVE_DATA_COMMANDS = [
    "STATUS",
    "ENGINE_LOAD",
    "COOLANT_TEMP",
    "FUEL_PRESSURE",
    "INTAKE_PRESSURE",
    "RPM",
    "SPEED",
    "INTAKE_TEMP",
    "MAF",
    "THROTTLE_POS",
    "OBD_COMPLIANCE",
    "RUN_TIME",
    "FUEL_LEVEL",
    "RELATIVE_THROTTLE_POS",
    "AMBIANT_AIR_TEMP",
    "ACCELERATOR_POS_D",
    "ACCELERATOR_POS_E",
    "ACCELERATOR_POS_F",
    "TIME_SINCE_DTC_CLEARED",
    "FUEL_TYPE",
    "ETHANOL_PERCENT",
    "RELATIVE_ACCEL_POS",
    "HYBRID_BATTERY_REMAINING",
    "OIL_TEMP",
    "FUEL_RATE",
]


def load_config():
    """Load configuration from config/config.yaml file."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config: {e}")
        raise


class CarBuddy:
    """OBD-II connection manager and DTC checker."""

    def __init__(self, config):
        self.connection = None
        self.live_data_commands = None
        self.config = config
        self.backoff_delay = config["bluetooth"]["initial_backoff"]
        self.max_backoff = config["bluetooth"]["max_backoff"]
        self.vin = None

    def _connect_to_obd(self):
        """Connect to OBD-II adapter with error handling."""
        try:
            connection = obd.OBD(
                portstr=self.config["bluetooth"].get("device", None),
                baudrate=self.config["bluetooth"].get("baudrate", None),
            )
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
        self.backoff_delay = self.config["bluetooth"]["initial_backoff"]
        self._ensure_commands()
        self._ensure_vin()
        return True

    def _ensure_commands(self):
        """Ensure we have a list of commands to query."""
        if self.live_data_commands is not None:
            return

        assert self.connection is not None

        supported_commands = []
        for name in LIVE_DATA_COMMANDS:
            try:
                command = obd.commands[name]
                if self.connection.supports(command):
                    supported_commands.append(command)
            except Exception as e:
                logger.error(f"Error getting command {name}: {e}")

        self.live_data_commands = supported_commands

    def _ensure_vin(self):
        """Read and store the Vehicle Identification Number (VIN) if not already read."""
        if self.vin is not None:
            return

        assert self.connection is not None

        try:
            response = self.connection.query(obd.commands["VIN"])
        except Exception as e:
            logger.error(f"Error reading VIN: {e}", exc_info=True)
            return

        if response.is_null():
            logger.warning(
                "VIN not available (command not supported or connection issue)"
            )
            return

        # response.value can be anything, but we expect a bytearray for VIN
        if isinstance(response.value, (bytes, bytearray)):
            self.vin = bytes(response.value).decode("ascii", errors="ignore")
            logger.info(f"Vehicle VIN: {self.vin}")
        else:
            logger.warning(
                f"Unexpected VIN response: {type(response.value)}; got: {response.value!r}"
            )

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

    def dump_live_data(self):
        """Dump all mode 02 live data from the OBD-II adapter."""
        if self.live_data_commands is None:
            return

        assert self.connection is not None

        for command in self.live_data_commands:
            response = self.connection.query(command)
            self._dump_value(response)

    def _dump_value(self, response):
        command = response.command
        value = response.value
        if command == obd.commands["STATUS"]:
            logger.info("%s:", command.name)
            logger.info("  MIL: %s", value.MIL)
            logger.info("  DTC count: %s", value.DTC_count)
            logger.info("  Ignition type: %s", value.ignition_type)
        elif isinstance(value, str):
            logger.info("%s: %s", command.name, value)
        else:
            logger.info("%s: %s %s", command.name, value.magnitude, response.unit)

    def close(self):
        """Close the connection if it exists."""
        if self.connection:
            self.connection.close()
            logger.info("Connection closed.")


def main():
    logger.info("Starting Sentry CarBuddy")

    # Load configuration
    config = load_config()
    car_buddy = CarBuddy(config)

    try:
        while True:
            if not car_buddy.ensure_connected():
                continue  # Connection failed, try again

            car_buddy.dump_live_data()
            # car_buddy.check_dtcs()

            time.sleep(config["obd"]["check_interval"])
    except KeyboardInterrupt:
        logger.info("Shutting down Sentry CarBuddy")
    finally:
        car_buddy.close()


if __name__ == "__main__":
    main()
