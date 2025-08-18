"""
Utility functions for Sentry CarBuddy.

Contains shared functionality for logging, device detection, and common operations.
"""

import os
import logging
import platform
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path


def setup_logging(
    log_level: str = "INFO", log_file: Optional[str] = None
) -> logging.Logger:
    """Set up logging configuration for CarBuddy.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs to console only.

    Returns:
        Configured logger instance.
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger("sentry_carbuddy")
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log file specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_device_info() -> Dict[str, Any]:
    """Get system information for device identification.

    Returns:
        Dictionary containing device information.
    """
    try:
        # Basic system info
        device_info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        # Raspberry Pi specific info
        if is_raspberry_pi():
            device_info.update(get_raspberry_pi_info())

        # Network info
        device_info["hostname"] = platform.node()

        return device_info

    except Exception as e:
        return {"error": f"Failed to get device info: {e}"}


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi.

    Returns:
        True if running on Raspberry Pi, False otherwise.
    """
    try:
        # Check for Raspberry Pi specific files
        pi_model_file = Path("/proc/device-tree/model")
        cpuinfo_file = Path("/proc/cpuinfo")

        if pi_model_file.exists():
            with open(pi_model_file, "r") as f:
                model = f.read().strip("\x00")
                return "Raspberry Pi" in model

        if cpuinfo_file.exists():
            with open(cpuinfo_file, "r") as f:
                content = f.read()
                return "BCM" in content and "ARMv" in content

        return False

    except Exception:
        return False


def get_raspberry_pi_info() -> Dict[str, str]:
    """Get Raspberry Pi specific information.

    Returns:
        Dictionary with Pi-specific info.
    """
    info = {}

    try:
        # Pi model
        model_file = Path("/proc/device-tree/model")
        if model_file.exists():
            with open(model_file, "r") as f:
                info["pi_model"] = f.read().strip("\x00")

        # Pi serial number
        cpuinfo_file = Path("/proc/cpuinfo")
        if cpuinfo_file.exists():
            with open(cpuinfo_file, "r") as f:
                for line in f:
                    if line.startswith("Serial"):
                        info["pi_serial"] = line.split(":")[1].strip()
                        break

        # Pi revision
        if cpuinfo_file.exists():
            with open(cpuinfo_file, "r") as f:
                for line in f:
                    if line.startswith("Revision"):
                        info["pi_revision"] = line.split(":")[1].strip()
                        break

    except Exception as e:
        info["error"] = f"Failed to get Pi info: {e}"

    return info


def check_bluetooth_service() -> bool:
    """Check if Bluetooth service is running.

    Returns:
        True if Bluetooth service is active, False otherwise.
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "bluetooth"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0 and result.stdout.strip() == "active"

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def check_network_connectivity(host: str = "8.8.8.8", timeout: int = 5) -> bool:
    """Check network connectivity by pinging a host.

    Args:
        host: Host to ping (default: Google DNS)
        timeout: Timeout in seconds

    Returns:
        True if host is reachable, False otherwise.
    """
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout * 1000), host],
            capture_output=True,
            timeout=timeout + 2,
        )
        return result.returncode == 0

    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists, creating it if necessary.

    Args:
        directory: Directory path to create
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def safe_file_read(file_path: str, default: str = "") -> str:
    """Safely read a file, returning default value on error.

    Args:
        file_path: Path to file to read
        default: Default value to return on error

    Returns:
        File contents or default value
    """
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except (OSError, IOError):
        return default


def format_mac_address(mac: str) -> str:
    """Format MAC address to standard format.

    Args:
        mac: MAC address in various formats

    Returns:
        MAC address in AA:BB:CC:DD:EE:FF format
    """
    # Remove common separators and normalize
    cleaned = mac.replace(":", "").replace("-", "").replace(".", "").upper()

    # Validate length
    if len(cleaned) != 12:
        raise ValueError(f"Invalid MAC address length: {mac}")

    # Format as AA:BB:CC:DD:EE:FF
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2))


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format.

    Args:
        mac: MAC address to validate

    Returns:
        True if MAC address is valid, False otherwise
    """
    try:
        formatted = format_mac_address(mac)
        return len(formatted) == 17 and formatted.count(":") == 5
    except ValueError:
        return False
