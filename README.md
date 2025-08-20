# Sentry Automotive - CarBuddy Application

Sentry Automotive brings real-time error monitoring and diagnostics to the automotive industry through the **Sentry CarBuddy** - a compact hardware device designed to seamlessly integrate with your vehicle's diagnostic systems.

Built on the Raspberry Pi Zero W platform, the CarBuddy connects to your car's OBD-II port via Bluetooth LE, continuously monitoring vehicle health and automatically reporting Diagnostic Trouble Codes (DTCs) to Sentry.io. This enables fleet managers, automotive technicians, and car enthusiasts to proactively identify and resolve vehicle issues before they become critical problems.

## Key Features

- **Real-time DTC Monitoring**: Automatically detects and reports Diagnostic Trouble Codes as they occur
- **Wireless Connectivity**: Bluetooth LE connection to OBD-II adapters for easy installation
- **Sentry Integration**: Direct integration with Sentry.io for centralized error tracking and alerting
- **Compact Design**: Raspberry Pi Zero W-based hardware fits discreetly in any vehicle

## Development

### Environment Setup

Before starting development, ensure you have the proper virtual environment activated:

```bash
# Option 1: Use direnv (recommended)
direnv allow

# Option 2: Manually source the environment
source .envrc
```

This will create and activate the `.venv` virtual environment with the correct Python version.

### Editor Setup

We recommend using **Visual Studio Code** with the recommended extensions. The project includes VSCode configuration that will:

- Automatically format code on save (Black)
- Automatically organize imports on save (Ruff)
- Show linting errors inline (Ruff)
- Display type checking issues (mypy)

When you open this project in VSCode, it will prompt you to install the recommended extensions if they're not already installed.

### Code Quality

Run linting and formatting tools:

```bash
# Format code
black src/

# Lint and auto-fix issues
ruff check src/ --fix

# Type checking
mypy src/
```

### Raspberry Pi Setup

1. **Provision Raspberry Pi OS Lite (64-bit)** - Flash the OS to SD card and ensure SSH access via password is enabled
2. **Connect via SSH** - Insert the SD card, boot your Raspberry Pi, and remotely using SSH
3. **Initialize environment** - Manually run the steps from `scripts/0-init.sh` to initialize the environment
4. **Complete setup** - Run `scripts/1-setup.sh` to complete the setup process

### Testing with Emulator

For development and testing purposes, you can use an OBD-II emulator instead of connecting to an actual vehicle.

1. **Install development requirements** - This will install the emulator in your virtual environment:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Start the emulator** - Run the emulator with the car scenario:
   ```bash
   elm -s car
   ```

3. **Note the device path** - When the emulator starts, it will output the device information:
   ```
   Emulator scenario switched to 'car'
   Welcome to the ELM327 OBD-II adapter emulator.
   ELM327-emulator is running on /dev/ttys044
   ...
   ```

For testing with the emulator, it's recommended to set the device and baud rate manually in your `config/config.yaml`. On macOS, this typically looks like:

```yaml
bluetooth:
  initial_backoff: 1
  max_backoff: 30
  device: "/dev/ttys044"
  baudrate: 38400
```

Make sure to use the actual device path shown in the emulator output.

