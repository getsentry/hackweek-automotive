# Sentry Automotive - CarBuddy Implementation Plan

## Overview

Sentry CarBuddy is a hardware device based on Raspberry Pi Zero W that connects via Bluetooth LE to an OBD-II adapter to read vehicle Diagnostic Trouble Codes (DTCs) and reports them as errors to Sentry.io.

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
- Project-specific settings
- Device identification parameters

**Process:**
1. User creates Sentry project and downloads `carbuddy-config.json`
2. During or after SD card setup, user replaces the default config file
3. Setup script validates and applies the configuration
4. CarBuddy application reads configuration on startup

### 2.3 Setup Script Development
Create a comprehensive setup script (`setup.sh`) that handles:

**Python Environment Setup:**
- Use system Python 3.11.2 (no upgrade needed)
- Create virtual environment for CarBuddy application
- Install all Python dependencies from requirements.txt

**System Configuration:**
- Configure Bluetooth services and permissions
- Set up systemd service for auto-start
- Configure logging directories and permissions
- Validate Veepeak OBDCheck BLE+ adapter connectivity

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

**Verification:**
- Test OBD-II adapter connection
- Verify Sentry communication
- Validate systemd service operation
- Generate setup completion report

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
│   ├── default.json        # Default configuration template
│   └── carbuddy-config.json # User configuration from Sentry UI
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
- Handles connection/disconnection to Veepeak OBDCheck BLE+ adapter
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
- Manages Bluetooth Low Energy connectivity
- Handles pairing and connection management with adapter
- Provides connection status monitoring
- Implements automatic reconnection logic
- Manages Bluetooth service dependencies

**src/config.py:**
- Configuration management system
- Loads and merges default and user configurations
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
1. **Download** pre-configured SD card image
2. **Flash** to SD card using Raspberry Pi Imager
3. **Insert** SD card into Pi Zero W
4. **Power on** and wait for setup completion
5. **Replace** default configuration with downloaded `carbuddy-config.json` from Sentry UI
6. **Run setup script** to apply configuration and validate connectivity
7. **Verify** adapter connection and Sentry reporting

### 5.2 Status Indicators
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
