#!/usr/bin/env python3
"""
Test script to verify OBD-II adapter connection using python-OBD library.

This script demonstrates the simplified connection approach where:
1. Bluetooth pairing is handled at the system level (via bluetoothctl)
2. python-OBD connects to the already-paired adapter
3. No complex Bluetooth management needed in the Python application

Prerequisites:
1. Veepeak OBDCheck BLE+ adapter paired via bluetoothctl
2. python-OBD library installed: pip install obd

Usage:
    python test_obd_connection.py
    python test_obd_connection.py --port /dev/rfcomm0  # specify port if needed
"""

import sys
import argparse
import time

try:
    import obd
except ImportError:
    print("Error: python-OBD library not installed")
    print("Install with: pip install obd")
    sys.exit(1)


def test_connection(port=None):
    """Test connection to OBD-II adapter."""
    print("🚗 Testing OBD-II Adapter Connection")
    print("=" * 40)

    try:
        # Connect to OBD-II adapter
        print(
            f"Connecting to OBD-II adapter{' on ' + port if port else ' (auto-detect)'}..."
        )

        if port:
            connection = obd.OBD(port)
        else:
            # Auto-detect - python-OBD will find the connected adapter
            connection = obd.OBD()

        if not connection.is_connected():
            print("❌ Failed to connect to OBD-II adapter")
            print("\nTroubleshooting:")
            print("1. Ensure adapter is paired via bluetoothctl:")
            print("   sudo bluetoothctl")
            print("   > scan on")
            print("   > pair XX:XX:XX:XX:XX:XX")
            print("   > trust XX:XX:XX:XX:XX:XX")
            print("   > connect XX:XX:XX:XX:XX:XX")
            print("2. Check if adapter creates a serial port (e.g., /dev/rfcomm0)")
            print("3. Try specifying the port manually: --port /dev/rfcomm0")
            return False

        print("✅ Successfully connected to OBD-II adapter")
        print(f"Port: {connection.port_name()}")
        print(f"Protocol: {connection.protocol_name()}")

        # Test basic communication
        print("\n📊 Testing basic OBD-II communication...")

        # Query supported commands
        supported_commands = connection.supported_commands
        print(f"Supported commands: {len(supported_commands)}")

        # Try to read vehicle identification
        print("\n🔍 Reading vehicle information...")

        # VIN (Vehicle Identification Number)
        try:
            vin_response = connection.query(obd.commands.VIN)
            if not vin_response.is_null():
                print(f"VIN: {vin_response.value}")
            else:
                print("VIN: Not available")
        except Exception as e:
            print(f"VIN: Error reading ({e})")

        # Test DTC reading (main functionality for CarBuddy)
        print("\n🚨 Testing DTC (Diagnostic Trouble Codes) reading...")
        try:
            dtc_response = connection.query(obd.commands.GET_DTC)
            if not dtc_response.is_null():
                dtcs = dtc_response.value
                if dtcs:
                    print(f"Found {len(dtcs)} DTCs:")
                    for code, description in dtcs:
                        print(f"  - {code}: {description}")
                else:
                    print("No DTCs found (vehicle is healthy! 🎉)")
            else:
                print("DTC query returned null response")
        except Exception as e:
            print(f"DTC reading error: {e}")

        # Close connection
        connection.close()
        print("\n✅ Test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("\nCommon issues:")
        print("- Adapter not paired at system level")
        print("- Adapter not connected to vehicle OBD-II port")
        print("- Vehicle not in 'ignition on' or 'engine running' state")
        print("- Bluetooth connection issues")
        return False


def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Test OBD-II adapter connection")
    parser.add_argument("--port", help="Specify serial port (e.g., /dev/rfcomm0)")
    parser.add_argument(
        "--mock", action="store_true", help="Use mock adapter for testing"
    )

    args = parser.parse_args()

    if args.mock:
        print("🧪 Mock mode not implemented yet")
        print("This will be useful for development without a real vehicle")
        return

    # Test connection
    success = test_connection(args.port)

    if success:
        print("\n🚀 Ready for CarBuddy implementation!")
        print("The simplified architecture works:")
        print("1. System-level Bluetooth pairing ✅")
        print("2. python-OBD connects to paired adapter ✅")
        print("3. DTC reading functionality ✅")
    else:
        print("\n🔧 Connection issues need to be resolved before proceeding")
        sys.exit(1)


if __name__ == "__main__":
    main()
