# Sentry Automotive - CarBuddy Implementation Plan

## Overview

Sentry CarBuddy is a hardware device based on Raspberry Pi Zero W that connects via Bluetooth LE to a factory-paired OBD-II adapter to read vehicle Diagnostic Trouble Codes (DTCs) and reports them as errors to Sentry.io. Each CarBuddy kit ships with a pre-paired Pi and Veepeak OBDCheck BLE+ adapter for plug-and-play operation.

## Architecture

```
┌─────────────────┐    Bluetooth LE    ┌──────────────────┐    OBD-II    ┌─────────────┐
│  Raspberry Pi   │ ◄──────────────── │  OBD-II Adapter  │ ◄─────────── │   Vehicle   │
│   Zero W        │                    │    (ELM327)      │               │   ECU       │
│                 │                    │                  │               │             │
│ CarBuddy App    │                    │                  │               │             │
│      │          │                    │                  │               │             │
│      ▼          │                    │                  │               │             │
│  Sentry SDK     │                    │                  │               │             │
└─────────────────┘                    └──────────────────┘               └─────────────┘
          │
          │ HTTPS
          ▼
┌─────────────────┐
│   Sentry.io     │
│   Platform      │
└─────────────────┘
```

## 1. Hardware Setup & Requirements

### 1.1 Hardware Components
- **Raspberry Pi Zero W** (with Wi-Fi and Bluetooth)
- **MicroSD card** (32GB recommended, Class 10)
- **Veepeak OBDCheck BLE+** (Bluetooth Low Energy OBD-II adapter, branded as "the adapter")
- **12V to 5V power adapter** (for car power)
- **Enclosure** (weather-resistant for automotive use)

### 1.2 Operating System & Python Setup
- **Raspberry Pi OS Lite** (headless configuration, Bookworm release)
- **Python 3.11.2** (default version shipped with current Pi OS Bookworm)
- No Python version upgrade required - 3.11.2 is sufficient for our needs

## 2. Deployment Strategy

### 2.1 Pre-configured SD Card Image
Create a custom Raspberry Pi OS image with:
- Pre-installed CarBuddy application using Python 3.11.2
- All dependencies and libraries in virtual environment
- Auto-start configuration
- Default configuration template
- Setup script for user configuration

**Benefits:**
- Plug-and-play user experience
- Consistent environment
- Reduced support burden
- Simplified user onboarding

**Implementation:**
1. Use `pi-gen` tool to create custom Raspberry Pi OS image
2. Create virtual environment with Python 3.11.2 (system default)
3. Pre-install all required Python packages in virtual environment
4. Include setup script for configuration management
5. Distribute via website download

### 2.2 Configuration File Management
Users will download a configuration file from the Sentry UI containing:
- Sentry DSN (Data Source Name)

*Note: Additional configuration options may be added in the future as requirements are identified.*

**Process:**
1. User creates Sentry project and downloads `carbuddy-config.json`
2. During or after SD card setup, user replaces the default config file
3. Setup script validates and applies the configuration
4. CarBuddy application reads configuration on startup

### 2.3 Factory Provisioning Process
CarBuddy devices are factory-provisioned during manufacturing with a comprehensive setup process:

**Python Environment Setup:**
- Use system Python 3.11.2 (no upgrade needed)
- Create virtual environment for CarBuddy application
- Install all Python dependencies from requirements.txt

**Bluetooth Pre-Pairing Process:**
CarBuddy devices are factory-provisioned with their specific Veepeak adapter MAC address:

```bash
# Factory provisioning (not user setup)
ADAPTER_MAC="AA:BB:CC:DD:EE:FF"  # Pre-configured for this specific CarBuddy unit

# 1. Enable Bluetooth services
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# 2. Automated pairing with known adapter MAC
sudo bluetoothctl << EOF
agent on
default-agent
pair $ADAPTER_MAC
trust $ADAPTER_MAC
connect $ADAPTER_MAC
EOF

# 3. Store adapter MAC for runtime use
echo "$ADAPTER_MAC" > /opt/sentry-carbuddy/config/adapter_mac.txt
```

**Important Notes:**
- **No user interaction required** - adapter MAC is factory-provisioned
- Each CarBuddy kit ships with a matched, pre-paired adapter
- Adapter auto-connects immediately on device boot
- python-OBD library connects to pre-paired adapter automatically
- Device is truly plug-and-play with no Bluetooth setup needed

**System Configuration:**
- Configure Bluetooth services and permissions
- Complete Veepeak OBDCheck BLE+ pairing process above
- Set up systemd service for auto-start
- Configure logging directories and permissions
- Test OBD-II adapter connection via python-OBD

**Configuration Management:**
- Validate user-provided configuration file format
- Backup default configuration
- Apply user configuration with error handling
- Test Sentry connectivity with provided DSN

**Security & Permissions:**
- Set appropriate file permissions
- Configure firewall rules
- Enable necessary system services
- Create non-root user if needed

**Factory Verification:**
- Test OBD-II adapter pairing and connection
- Validate systemd service operation
- Generate factory provisioning report

### 2.4 User Configuration (Post-Purchase)
Simple user configuration script handles only Sentry setup:

**Sentry Configuration:**
- User downloads `carbuddy-config.json` from Sentry UI
- Replace default configuration with user's Sentry DSN
- Validate configuration format and DSN connectivity
- Restart CarBuddy service with new configuration

**System Verification:**
- Confirm pre-paired adapter connectivity (factory-provisioned)
- Test Sentry error reporting with user's DSN
- Generate user setup completion report

**No Bluetooth Setup Required:**
- Adapter MAC address is factory-provisioned in `/opt/sentry-carbuddy/config/adapter_mac.txt`
- python-OBD automatically connects to pre-paired adapter
- User never interacts with Bluetooth settings

## 3. Application Auto-Start Configuration

### 3.1 Systemd Service (Recommended)

Create `/etc/systemd/system/sentry-carbuddy.service`:

```ini
[Unit]
Description=Sentry CarBuddy OBD-II Monitor
After=network-online.target bluetooth.service
Wants=network-online.target
Requires=bluetooth.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/sentry-carbuddy
ExecStart=/opt/sentry-carbuddy/venv/bin/python /opt/sentry-carbuddy/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PYTHONUNBUFFERED=1
Environment=SENTRY_ENVIRONMENT=production

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
sudo systemctl enable sentry-carbuddy.service
sudo systemctl start sentry-carbuddy.service
```

### 3.2 Bluetooth Service Dependencies
Ensure Bluetooth stack is ready before starting:
```bash
sudo systemctl enable bluetooth
sudo systemctl enable hciuart
```

## 4. Application Implementation

### 4.1 Library Selection

**Primary Choice: python-OBD**
- Well-maintained and documented
- Supports multiple connection types (Serial, Bluetooth, WiFi)
- Comprehensive OBD-II command support
- Active community

**Alternative Libraries Evaluated:**
- `pyobd`: Legacy, limited functionality
- `obd2lib`: Basic, not actively maintained
- `cantools`: More complex, CAN-bus focused

**Installation:**
```bash
pip install obd sentry-sdk pybluez pyserial
```

### 4.2 Application Structure

```
/opt/sentry-carbuddy/
├── main.py              # Main application entry point
├── src/
│   ├── __init__.py
│   ├── obd_manager.py   # OBD-II communication handler
│   ├── sentry_client.py # Sentry integration
│   ├── bluetooth_mgr.py # Bluetooth connection management
│   ├── config.py        # Configuration management
│   └── utils.py         # Utility functions
├── config/
│   ├── default.json         # Default configuration template
│   ├── carbuddy-config.json # User configuration from Sentry UI
│   └── adapter_mac.txt      # Factory-provisioned adapter MAC address
├── logs/                # Application logs
├── requirements.txt     # Python dependencies
├── setup.sh            # Setup and configuration script
└── systemd/
    └── sentry-carbuddy.service
```

### 4.3 Core Implementation

**main.py:**
- Main application entry point and orchestration
- Initializes logging, configuration, and core components
- Manages main application loop for periodic DTC reading
- Handles graceful shutdown and cleanup
- Coordinates between OBD manager, Bluetooth manager, and Sentry client

**src/obd_manager.py:**
- Manages OBD-II communication using python-OBD library
- Connects to system-paired Veepeak OBDCheck BLE+ adapter
- Implements DTC retrieval and parsing functionality
- Provides DTC clearing capabilities
- Includes connection health monitoring and error handling

**src/sentry_client.py:**
- Integrates with Sentry SDK for error reporting
- Formats DTCs into structured Sentry events
- Determines DTC severity levels based on error codes
- Manages Sentry configuration and context setting
- Handles exception capture for application errors

**src/bluetooth_mgr.py:**
- Monitors system-level Bluetooth connection status
- Provides connection health checks for paired adapter
- Handles adapter disconnection detection and alerts
- Manages adapter reconnection via system commands if needed
- Lightweight wrapper around system Bluetooth services

**src/config.py:**
- Configuration management system
- Loads and merges default and user configurations
- Reads factory-provisioned adapter MAC address
- Validates configuration format and required fields
- Provides typed access to configuration properties
- Handles configuration file updates and backups

**src/utils.py:**
- Shared utility functions
- Device identification and hardware detection
- Logging helpers and formatting functions
- System health checks and diagnostics
- Common error handling utilities

### 4.4 Local Development Setup

**Development Environment Requirements:**
- Python 3.11.2 (matching Raspberry Pi OS Bookworm)
- `.python-version` file specifies exact version for consistency
- Virtual environment (`.venv`) for dependency isolation

**Setup Steps:**
```bash
# Clone repository
git clone https://github.com/sentry-automotive/carbuddy.git
cd carbuddy

# Verify Python version matches .python-version file
python3 --version  # Should show Python 3.11.2

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run application (with mock OBD data)
python main.py --mock
```

**Project Files:**
- `.python-version` - Specifies Python 3.11.2 for pyenv users
- `.gitignore` - Excludes `.venv/` from version control
- `.envrc` - Direnv configuration for automatic environment setup
- `requirements.txt` - Python dependencies

**Optional: Using direnv (Recommended)**
If you have [direnv](https://direnv.net/) installed, it will automatically:
- Install Python 3.11.2 using pyenv (if pyenv is available and version not installed)
- Create the virtual environment if it doesn't exist
- Activate the virtual environment when entering the directory

```bash
# Install direnv (macOS)
brew install direnv

# Allow the .envrc file
direnv allow

# Environment will now activate automatically when entering the directory
```

## 5. User Experience

### 5.1 Initial Setup Process
1. **Receive** CarBuddy kit with pre-paired Pi Zero W and Veepeak adapter
2. **Download** Sentry configuration file (`carbuddy-config.json`) from Sentry UI
3. **Connect** CarBuddy to computer via USB to access SD card
4. **Replace** default configuration with downloaded `carbuddy-config.json`
5. **Install** CarBuddy in vehicle:
   - Connect to vehicle's 12V power supply
   - Plug Veepeak adapter into vehicle's OBD-II port
   - Mount CarBuddy device securely
6. **Power on** - device automatically connects to pre-paired adapter
7. **Verify** operation via Sentry dashboard (DTCs will appear if present)

### 5.2 Factory Pre-Pairing Benefits
**No User Bluetooth Setup Required:**
- ✅ **Pre-paired at factory** - Pi and adapter are matched as a kit
- ✅ **Plug-and-play operation** - no scanning, selection, or pairing needed
- ✅ **Immediate connectivity** - adapter connects automatically on boot
- ✅ **No user input needed** - perfect for headless device operation

**Behind the Scenes:**
```
CarBuddy Boot Sequence:
[✓] System startup
[✓] Bluetooth service enabled
[✓] Connecting to pre-paired adapter AA:BB:CC:DD:EE:FF
[✓] OBD-II adapter connected
[✓] Sentry CarBuddy ready
```

Users never see this process - the device simply works when powered on.

### 5.3 Status Indicators
- **LED indicators** for connection status
- **Web dashboard** for diagnostics
- **Mobile app** for notifications (future)

## 6. Future Enhancements

- **Real-time data streaming** (RPM, speed, fuel efficiency)
- **Predictive maintenance** alerts
- **Fleet management** capabilities
- **Machine learning** for pattern recognition
- **Mobile application** for user interaction
- **Voice alerts** for critical issues
- **Integration** with other automotive platforms

---

This implementation plan provides a comprehensive roadmap for developing the Sentry CarBuddy application. The modular architecture ensures maintainability while the deployment strategy prioritizes user experience and reliability.
