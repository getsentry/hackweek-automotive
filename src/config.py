"""
Configuration management for Sentry CarBuddy.

Handles loading and merging of default configuration, user configuration,
and factory-provisioned settings like adapter MAC address.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """Configuration manager for CarBuddy application."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Optional path to configuration directory.
                       Defaults to /opt/sentry-carbuddy/config in production.
        """
        if config_dir is None:
            # Production path
            self.config_dir = Path("/opt/sentry-carbuddy/config")
        else:
            self.config_dir = Path(config_dir)

        # Define configuration file paths
        self.default_config_path = self.config_dir / "default.json"
        self.user_config_path = self.config_dir / "carbuddy-config.json"
        self.adapter_mac_path = self.config_dir / "adapter_mac.txt"

        # Load configuration
        self._config = self._load_config()
        self._adapter_mac = self._load_adapter_mac()

    def _load_config(self) -> Dict[str, Any]:
        """Load and merge configuration from default and user files.

        Returns:
            Merged configuration dictionary.
        """
        # Start with default configuration
        config = {}

        if self.default_config_path.exists():
            with open(self.default_config_path, "r") as f:
                config = json.load(f)

        # Override with user configuration if it exists
        if self.user_config_path.exists():
            with open(self.user_config_path, "r") as f:
                user_config = json.load(f)
                config.update(user_config)

        return config

    def _load_adapter_mac(self) -> str:
        """Load factory-provisioned adapter MAC address.

        Returns:
            Adapter MAC address or default value if file not found.
        """
        if self.adapter_mac_path.exists():
            with open(self.adapter_mac_path, "r") as f:
                mac = f.read().strip()
                # Remove comments and empty lines
                lines = [
                    line.strip()
                    for line in mac.splitlines()
                    if line.strip() and not line.startswith("#")
                ]
                if lines:
                    return lines[0]

        # Default MAC for development/testing
        return "00:00:00:00:00:00"

    @property
    def sentry_dsn(self) -> str:
        """Get Sentry DSN from configuration."""
        return self._config.get("sentry_dsn", "")

    @property
    def poll_interval(self) -> int:
        """Get polling interval in seconds."""
        return self._config.get("poll_interval", 300)  # 5 minutes default

    @property
    def obd_port(self) -> Optional[str]:
        """Get OBD port. None means auto-detect."""
        return self._config.get("obd_port")

    @property
    def adapter_mac(self) -> str:
        """Get factory-provisioned adapter MAC address."""
        return self._adapter_mac

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config.get("log_level", "INFO")

    @property
    def max_retries(self) -> int:
        """Get maximum number of connection retries."""
        return self._config.get("max_retries", 3)

    @property
    def retry_delay(self) -> int:
        """Get delay between retries in seconds."""
        return self._config.get("retry_delay", 30)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Get device information for Sentry context."""
        return self._config.get(
            "device_info",
            {
                "device_type": "raspberry_pi_zero_w",
                "application": "sentry_carbuddy",
                "version": "1.0.0",
            },
        )

    def validate(self) -> bool:
        """Validate configuration is complete and correct.

        Returns:
            True if configuration is valid, False otherwise.
        """
        # Check required fields
        if not self.sentry_dsn:
            return False

        # Validate Sentry DSN format (basic check)
        if not self.sentry_dsn.startswith(("http://", "https://")):
            return False

        # Validate adapter MAC format (basic check)
        mac_parts = self.adapter_mac.split(":")
        if len(mac_parts) != 6:
            return False

        # Validate numeric ranges
        if self.poll_interval <= 0:
            return False

        if self.max_retries < 0:
            return False

        if self.retry_delay < 0:
            return False

        return True

    def reload(self) -> None:
        """Reload configuration from files."""
        self._config = self._load_config()
        self._adapter_mac = self._load_adapter_mac()

    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary.

        Returns:
            Complete configuration dictionary.
        """
        return {**self._config, "adapter_mac": self._adapter_mac}
