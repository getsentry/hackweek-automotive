#!/usr/bin/env python3

"""
Sentry CarBuddy - OBD-II Vehicle Diagnostics to Sentry Integration

A headless Raspberry Pi application that reads Diagnostic Trouble Codes (DTCs)
from vehicles via a factory-paired Bluetooth OBD-II adapter and reports them
to Sentry.io for monitoring and alerting.
"""

import logging
import time
from pathlib import Path

import obd
import sentry_sdk
import yaml
from sentry_sdk import logger as sentry_logger
from sentry_sdk.integrations.logging import LoggingIntegration

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
        with open(config_path) as f:
            config = yaml.safe_load(f)
        logger.info("Loaded configuration from %s", config_path)
        return config
    except FileNotFoundError:
        logger.error("Config file not found at %s", config_path)
        raise
    except yaml.YAMLError as e:
        logger.error("Error parsing config file: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error loading config: %s", e)
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
            logger.info("Connected to: %s", connection.port_name())
            return connection
        except Exception as e:
            logger.error("Connection error: %s", e, exc_info=True)
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
            "Attempting to connect (retry in %ss if failed)...", self.backoff_delay
        )
        self.connection = self._connect_to_obd()

        # Connection failed, apply exponential backoff
        if self.connection is None:
            logger.warning(
                "Connection failed. Retrying in %s seconds...", self.backoff_delay
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
                logger.error("Error getting command %s: %s", name, e)

        self.live_data_commands = supported_commands

        sentry_attributes = {}
        for command in self.connection.supported_commands:
            sentry_attributes[f"obd.commands.{command.name.lower()}"] = True
        for desired_command in LIVE_DATA_COMMANDS:
            key = f"obd.commands.{desired_command.lower()}"
            if key not in sentry_attributes:
                sentry_attributes[key] = False

        sentry_logger.info("OBD command support detected", attributes=sentry_attributes)

    def _ensure_vin(self):
        """Read and store the Vehicle Identification Number (VIN).

        Only reads if not already read.
        """
        if self.vin is not None:
            return

        assert self.connection is not None

        try:
            response = self.connection.query(obd.commands["VIN"])
        except Exception as e:
            logger.error("Error reading VIN: %s", e, exc_info=True)
            return

        if response.is_null():
            logger.warning(
                "VIN not available (command not supported or connection issue)"
            )
            return

        if isinstance(response.value, bytes | bytearray):
            self.vin = bytes(response.value).decode("ascii", errors="ignore")
            logger.info("Vehicle VIN: %s", self.vin)
        else:
            logger.warning(
                "Unexpected VIN response: %s; got: %r",
                type(response.value),
                response.value,
            )

    def check_dtcs(self):
        """Check for Diagnostic Trouble Codes (DTCs) and log results.

        Assumes connection is established.
        """
        try:
            logger.info("Checking for DTCs...")

            assert self.connection is not None
            response = self.connection.query(obd.commands["GET_DTC"])

            if response.is_null():
                logger.warning(
                    "No response from vehicle "
                    "(command not supported or connection issue)"
                )
            elif not response.value:
                logger.info("✅ No DTCs found - Vehicle is healthy")
            else:
                logger.warning("⚠️  Found %s DTC(s):", len(response.value))
                for dtc_code, dtc_description in response.value:
                    logger.warning("   • %s: %s", dtc_code, dtc_description)
        except Exception as e:
            logger.error("Error during DTC check: %s", e, exc_info=True)

    def log_obd_status(self):
        assert self.connection is not None
        status = self.connection.status()
        elm_version = self.connection.query(obd.commands["ELM_VERSION"])
        elm_voltage = self.connection.query(obd.commands["ELM_VOLTAGE"])

        attributes = {
            "obd.connection.status": status,
            "obd.connection.elm": status != obd.OBDStatus.NOT_CONNECTED,
            "obd.connection.car": status == obd.OBDStatus.CAR_CONNECTED,
            "obd.elm.version": elm_version.value,
            "obd.elm.voltage": (
                elm_voltage.value.magnitude if elm_voltage.value else None
            ),
        }

        sentry_logger.info("OBD connection status", attributes=attributes)
        for key, value in attributes.items():
            logger.info("%s: %s", key, value)

    def log_live_data(self):
        """Dump all mode 02 live data from the OBD-II adapter."""
        if self.live_data_commands is None:
            return

        assert self.connection is not None

        sentry_attributes = {}
        if self.vin:
            sentry_attributes["vehicle.vin"] = self.vin

        for command in self.live_data_commands:
            response = self.connection.query(command)
            self._extract_sentry_attributes(response, sentry_attributes)
            self._dump_value(response)

        sentry_logger.info("Vehicle telemetry collected", attributes=sentry_attributes)

    def _extract_sentry_attributes(self, response, attributes):
        """Add OBD response to sentry attributes dictionary."""
        command = response.command
        value = response.value

        if command == obd.commands["STATUS"]:
            attributes["vehicle.status.mil"] = value.MIL
            attributes["vehicle.status.dtc_count"] = value.DTC_count
            attributes["vehicle.status.ignition_type"] = str(value.ignition_type)
        elif isinstance(value, str):
            attributes[f"vehicle.{command.name.lower()}"] = value
        else:
            attr_name = f"vehicle.{command.name.lower()}"
            attributes[attr_name] = (
                float(value.magnitude) if hasattr(value, "magnitude") else value
            )
            if response.unit:
                attributes[f"{attr_name}.unit"] = str(response.unit)

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

    config = load_config()

    sentry_sdk.init(
        dsn=config["sentry"]["dsn"],
        enable_logs=True,
        integrations=[LoggingIntegration(sentry_logs_level=logging.ERROR)],
    )

    car_buddy = CarBuddy(config)

    try:
        while True:
            if not car_buddy.ensure_connected():
                continue  # Connection failed, try again

            car_buddy.log_obd_status()
            car_buddy.log_live_data()
            # car_buddy.check_dtcs()

            time.sleep(config["obd"]["check_interval"])
    except KeyboardInterrupt:
        logger.info("Shutting down Sentry CarBuddy")
    finally:
        car_buddy.close()


if __name__ == "__main__":
    main()
