# Sentry Automotive - CarBuddy Application

Sentry Automotive brings real-time error monitoring and diagnostics to the automotive industry through the **Sentry CarBuddy** - a compact hardware device designed to seamlessly integrate with your vehicle's diagnostic systems.

Built on the Raspberry Pi Zero W platform, the CarBuddy connects to your car's OBD-II port via Bluetooth LE, continuously monitoring vehicle health and automatically reporting Diagnostic Trouble Codes (DTCs) to Sentry.io. This enables fleet managers, automotive technicians, and car enthusiasts to proactively identify and resolve vehicle issues before they become critical problems.

## Key Features

- **Real-time DTC Monitoring**: Automatically detects and reports Diagnostic Trouble Codes as they occur
- **Wireless Connectivity**: Bluetooth LE connection to OBD-II adapters for easy installation
- **Sentry Integration**: Direct integration with Sentry.io for centralized error tracking and alerting
- **Compact Design**: Raspberry Pi Zero W-based hardware fits discreetly in any vehicle

## Development

### Raspberry Pi Setup

1. **Provision Raspberry Pi OS Lite (64-bit)** - Flash the OS to SD card and ensure SSH access via password is enabled
2. **Connect via SSH** - Insert the SD card, boot your Raspberry Pi, and remotely using SSH
3. **Initialize environment** - Manually run the steps from `scripts/0-init.sh` to initialize the environment
4. **Complete setup** - Run `scripts/1-setup.sh` to complete the setup process

