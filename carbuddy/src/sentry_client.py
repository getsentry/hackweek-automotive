"""
Sentry integration for CarBuddy.

Handles error reporting, DTC formatting, and Sentry SDK configuration.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

from .utils import get_device_info


class SentryClient:
    """Sentry integration client for CarBuddy."""

    def __init__(self, dsn: str, device_info: Optional[Dict[str, Any]] = None):
        """Initialize Sentry client.

        Args:
            dsn: Sentry Data Source Name
            device_info: Optional device information for context
        """
        self.dsn = dsn
        self.device_info = device_info or {}
        self.logger = logging.getLogger(__name__)
        self.initialized = False

        if not SENTRY_AVAILABLE:
            self.logger.warning("Sentry SDK not available. Error reporting disabled.")
            return

        if not dsn:
            self.logger.warning("No Sentry DSN provided. Error reporting disabled.")
            return

        self._initialize_sentry()

    def _initialize_sentry(self) -> None:
        """Initialize Sentry SDK with appropriate configuration."""
        try:
            # Configure logging integration
            logging_integration = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR,  # Send errors as events
            )

            # Initialize Sentry SDK
            sentry_sdk.init(
                dsn=self.dsn,
                integrations=[logging_integration],
                traces_sample_rate=0.1,  # Low sample rate for performance
                environment="production",
                release=f"carbuddy@{self._get_version()}",
                attach_stacktrace=True,
                send_default_pii=False,  # Don't send PII
            )

            # Set device context
            self._set_device_context()

            self.initialized = True
            self.logger.info("Sentry client initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize Sentry: {e}")
            self.initialized = False

    def _get_version(self) -> str:
        """Get CarBuddy version."""
        try:
            from . import __version__

            return __version__
        except ImportError:
            return "1.0.0"

    def _set_device_context(self) -> None:
        """Set device context for Sentry events."""
        if not self.initialized:
            return

        try:
            # Merge provided device info with detected info
            device_context = {**get_device_info(), **self.device_info}

            # Set user context (device identification)
            sentry_sdk.set_user(
                {
                    "id": device_context.get("pi_serial", "unknown"),
                    "device_type": device_context.get(
                        "device_type", "raspberry_pi_zero_w"
                    ),
                    "application": device_context.get("application", "sentry_carbuddy"),
                }
            )

            # Set device context
            sentry_sdk.set_context("device", device_context)

            self.logger.debug("Device context set for Sentry")

        except Exception as e:
            self.logger.warning(f"Failed to set device context: {e}")

    def report_dtcs(self, dtcs: List[Tuple[str, str]]) -> None:
        """Report DTCs as structured errors to Sentry.

        Args:
            dtcs: List of (code, description) tuples
        """
        if not self.initialized or not dtcs:
            return

        try:
            for code, description in dtcs:
                self._report_single_dtc(code, description)

            self.logger.info(f"Reported {len(dtcs)} DTCs to Sentry")

        except Exception as e:
            self.logger.error(f"Failed to report DTCs to Sentry: {e}")

    def _report_single_dtc(self, code: str, description: str) -> None:
        """Report a single DTC to Sentry.

        Args:
            code: DTC code (e.g., "P0171")
            description: DTC description
        """
        if not self.initialized:
            return

        try:
            with sentry_sdk.push_scope() as scope:
                # Set DTC-specific tags
                scope.set_tag("dtc_code", code)
                scope.set_tag("dtc_category", self._get_dtc_category(code))
                scope.set_tag("dtc_severity", self._get_dtc_severity(code))
                scope.set_tag("error_type", "diagnostic_trouble_code")

                # Set DTC context
                scope.set_context(
                    "vehicle_diagnostic",
                    {
                        "dtc_code": code,
                        "description": description,
                        "category": self._get_dtc_category(code),
                        "severity": self._get_dtc_severity(code),
                        "system": self._get_dtc_system(code),
                    },
                )

                # Set fingerprint for grouping
                scope.fingerprint = ["dtc", code]

                # Set level based on severity
                severity = self._get_dtc_severity(code)
                level = "error" if severity in ["high", "critical"] else "warning"
                scope.level = level

                # Capture the event
                sentry_sdk.capture_message(
                    f"Vehicle Diagnostic Trouble Code: {code} - {description}",
                    level=level,
                )

        except Exception as e:
            self.logger.error(f"Failed to report DTC {code}: {e}")

    def _get_dtc_category(self, code: str) -> str:
        """Get DTC category based on first character.

        Args:
            code: DTC code

        Returns:
            DTC category
        """
        if not code:
            return "unknown"

        category_map = {"P": "powertrain", "B": "body", "C": "chassis", "U": "network"}

        return category_map.get(code[0].upper(), "unknown")

    def _get_dtc_severity(self, code: str) -> str:
        """Determine DTC severity based on code.

        Args:
            code: DTC code

        Returns:
            Severity level
        """
        if not code or len(code) < 2:
            return "unknown"

        code_upper = code.upper()

        # High severity codes (emissions-related powertrain)
        if code_upper.startswith("P0"):
            return "high"

        # Medium severity codes
        if code_upper.startswith(("P1", "B", "U")):
            return "medium"

        # Lower severity codes (chassis)
        if code_upper.startswith("C"):
            return "low"

        # Critical codes (specific high-priority codes)
        critical_codes = [
            "P0301",
            "P0302",
            "P0303",
            "P0304",  # Cylinder misfires
            "P0171",
            "P0172",  # Fuel system lean/rich
            "P0420",
            "P0430",  # Catalyst efficiency
        ]

        if code_upper in critical_codes:
            return "critical"

        return "medium"

    def _get_dtc_system(self, code: str) -> str:
        """Get affected vehicle system based on DTC code.

        Args:
            code: DTC code

        Returns:
            Vehicle system name
        """
        if not code:
            return "unknown"

        code_upper = code.upper()

        # Powertrain systems
        if code_upper.startswith("P0"):
            if code_upper.startswith("P030"):
                return "ignition_system"
            elif code_upper.startswith("P017"):
                return "fuel_system"
            elif code_upper.startswith("P042"):
                return "emissions_catalyst"
            else:
                return "powertrain"

        # Body systems
        elif code_upper.startswith("B"):
            return "body_control"

        # Chassis systems
        elif code_upper.startswith("C"):
            return "chassis_control"

        # Network/communication
        elif code_upper.startswith("U"):
            return "network_communication"

        return "unknown"

    def capture_exception(self, exception: Exception, **kwargs) -> None:
        """Capture application exceptions.

        Args:
            exception: Exception to capture
            **kwargs: Additional context
        """
        if not self.initialized:
            return

        try:
            with sentry_sdk.push_scope() as scope:
                # Add any additional context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)

                sentry_sdk.capture_exception(exception)

        except Exception as e:
            self.logger.error(f"Failed to capture exception: {e}")

    def capture_message(self, message: str, level: str = "info", **kwargs) -> None:
        """Capture a custom message.

        Args:
            message: Message to capture
            level: Message level
            **kwargs: Additional context
        """
        if not self.initialized:
            return

        try:
            with sentry_sdk.push_scope() as scope:
                # Add any additional context
                for key, value in kwargs.items():
                    scope.set_extra(key, value)

                sentry_sdk.capture_message(message, level=level)

        except Exception as e:
            self.logger.error(f"Failed to capture message: {e}")

    def test_connection(self) -> bool:
        """Test Sentry connection by sending a test event.

        Returns:
            True if test was successful, False otherwise
        """
        if not self.initialized:
            return False

        try:
            self.capture_message("Sentry CarBuddy connection test", level="info")
            return True

        except Exception as e:
            self.logger.error(f"Sentry connection test failed: {e}")
            return False
