#!/usr/bin/env python3
"""
Basic test script for CarBuddy application components.

Tests the core functionality without requiring actual hardware.
"""

import sys
import tempfile
import json
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import Config
from src.utils import setup_logging, get_device_info, validate_mac_address
from src.sentry_client import SentryClient


def test_config_loading():
    """Test configuration loading functionality."""
    print("🧪 Testing configuration loading...")
    
    # Create temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create default config
        default_config = {
            "sentry_dsn": "",
            "poll_interval": 300,
            "log_level": "INFO"
        }
        
        with open(config_dir / "default.json", 'w') as f:
            json.dump(default_config, f)
        
        # Create adapter MAC file
        with open(config_dir / "adapter_mac.txt", 'w') as f:
            f.write("AA:BB:CC:DD:EE:FF\n")
        
        # Test config loading
        config = Config(str(config_dir))
        
        assert config.poll_interval == 300
        assert config.log_level == "INFO"
        assert config.adapter_mac == "AA:BB:CC:DD:EE:FF"
        
        print("✅ Configuration loading test passed")


def test_utility_functions():
    """Test utility functions."""
    print("🧪 Testing utility functions...")
    
    # Test logging setup
    logger = setup_logging("DEBUG")
    assert logger is not None
    logger.info("Test log message")
    
    # Test device info
    device_info = get_device_info()
    assert isinstance(device_info, dict)
    assert "platform" in device_info
    
    # Test MAC address validation
    assert validate_mac_address("AA:BB:CC:DD:EE:FF") == True
    assert validate_mac_address("invalid") == False
    
    print("✅ Utility functions test passed")


def test_sentry_client():
    """Test Sentry client initialization."""
    print("🧪 Testing Sentry client...")
    
    # Test with empty DSN (should not crash)
    sentry_client = SentryClient("")
    assert sentry_client is not None
    assert not sentry_client.initialized
    
    # Test DTC severity calculation
    assert sentry_client._get_dtc_severity("P0171") == "high"
    assert sentry_client._get_dtc_severity("P1234") == "medium"
    assert sentry_client._get_dtc_severity("C1234") == "low"
    
    # Test DTC category
    assert sentry_client._get_dtc_category("P0171") == "powertrain"
    assert sentry_client._get_dtc_category("B1234") == "body"
    assert sentry_client._get_dtc_category("C1234") == "chassis"
    assert sentry_client._get_dtc_category("U1234") == "network"
    
    print("✅ Sentry client test passed")


def test_main_application_mock():
    """Test main application in mock mode."""
    print("🧪 Testing main application (mock mode)...")
    
    # Create temporary config
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir)
        
        # Create default config
        default_config = {
            "sentry_dsn": "https://test@test.ingest.sentry.io/123456",
            "poll_interval": 5,  # Short interval for testing
            "log_level": "DEBUG"
        }
        
        with open(config_dir / "default.json", 'w') as f:
            json.dump(default_config, f)
        
        # Create adapter MAC file  
        with open(config_dir / "adapter_mac.txt", 'w') as f:
            f.write("AA:BB:CC:DD:EE:FF\n")
        
        # Import and test main application
        from main import CarBuddyApplication
        
        app = CarBuddyApplication(config_dir=str(config_dir), mock_mode=True)
        
        # Test initialization
        assert app.initialize() == True
        assert app.config is not None
        assert app.logger is not None
        assert app.sentry_client is not None
        
        # Test one mock iteration
        app._mock_iteration()
        
        print("✅ Main application test passed")


def run_all_tests():
    """Run all tests."""
    print("🚗 Starting CarBuddy Basic Tests")
    print("=" * 40)
    
    try:
        test_config_loading()
        test_utility_functions() 
        test_sentry_client()
        test_main_application_mock()
        
        print("=" * 40)
        print("🎉 All tests passed!")
        print("CarBuddy application is ready for deployment!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
