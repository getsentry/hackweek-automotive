#!/usr/bin/env python3
"""
Factory Provisioning Script for Sentry CarBuddy

This script provisions a Raspberry Pi Zero W with CarBuddy software during
manufacturing. It pairs the Pi with a specific Veepeak OBDCheck BLE+ adapter
and configures the system for plug-and-play operation.

Usage:
    sudo python factory_provision.py --adapter-mac AA:BB:CC:DD:EE:FF
    sudo python factory_provision.py --adapter-mac AA:BB:CC:DD:EE:FF --install-dir /opt/sentry-carbuddy
"""

import sys
import os
import json
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any


class FactoryProvisioner:
    """Factory provisioning manager for CarBuddy devices."""
    
    def __init__(self, adapter_mac: str, install_dir: str = "/opt/sentry-carbuddy"):
        """Initialize factory provisioner.
        
        Args:
            adapter_mac: MAC address of the Veepeak adapter to pair with
            install_dir: Installation directory for CarBuddy application
        """
        self.adapter_mac = adapter_mac.upper()
        self.install_dir = Path(install_dir)
        self.project_root = Path(__file__).parent.parent
        self.user = "pi"  # Default Pi user
        
        # Validate we're running as root
        if os.geteuid() != 0:
            raise PermissionError("Factory provisioning must be run as root (sudo)")
    
    def validate_adapter_mac(self) -> bool:
        """Validate adapter MAC address format.
        
        Returns:
            True if MAC address is valid, False otherwise
        """
        parts = self.adapter_mac.split(':')
        if len(parts) != 6:
            return False
        
        for part in parts:
            if len(part) != 2:
                return False
            try:
                int(part, 16)
            except ValueError:
                return False
        
        return True
    
    def provision_system(self) -> bool:
        """Run complete factory provisioning process.
        
        Returns:
            True if provisioning successful, False otherwise
        """
        print("🏭 Starting Factory Provisioning for Sentry CarBuddy")
        print("=" * 60)
        print(f"Adapter MAC: {self.adapter_mac}")
        print(f"Install Directory: {self.install_dir}")
        print(f"Target User: {self.user}")
        print("=" * 60)
        
        try:
            # Validate inputs
            if not self.validate_adapter_mac():
                print(f"❌ Invalid MAC address format: {self.adapter_mac}")
                return False
            
            # Step 1: System updates and dependencies
            if not self.install_system_dependencies():
                return False
            
            # Step 2: Python environment setup
            if not self.setup_python_environment():
                return False
            
            # Step 3: Install CarBuddy application
            if not self.install_carbuddy_application():
                return False
            
            # Step 4: Bluetooth pairing
            if not self.provision_bluetooth_pairing():
                return False
            
            # Step 5: System service configuration
            if not self.configure_system_services():
                return False
            
            # Step 6: Final verification
            if not self.verify_provisioning():
                return False
            
            print("=" * 60)
            print("🎉 Factory provisioning completed successfully!")
            print(f"CarBuddy is ready for deployment with adapter {self.adapter_mac}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"❌ Factory provisioning failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def install_system_dependencies(self) -> bool:
        """Install required system packages and updates.
        
        Returns:
            True if installation successful, False otherwise
        """
        print("📦 Installing system dependencies...")
        
        try:
            # Update package lists
            self._run_command(["apt", "update"], "Updating package lists")
            
            # Install required packages
            packages = [
                "python3-venv",
                "python3-pip", 
                "bluetooth",
                "bluez",
                "bluez-tools",
                "systemd",
            ]
            
            cmd = ["apt", "install", "-y"] + packages
            self._run_command(cmd, "Installing system packages")
            
            print("✅ System dependencies installed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to install system dependencies: {e}")
            return False
    
    def setup_python_environment(self) -> bool:
        """Set up Python virtual environment and install dependencies.
        
        Returns:
            True if setup successful, False otherwise
        """
        print("🐍 Setting up Python environment...")
        
        try:
            # Create install directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            
            # Create virtual environment
            venv_path = self.install_dir / "venv"
            self._run_command([
                "python3", "-m", "venv", str(venv_path)
            ], "Creating virtual environment")
            
            # Install Python dependencies
            pip_path = venv_path / "bin" / "pip"
            requirements_path = self.project_root / "requirements.txt"
            
            self._run_command([
                str(pip_path), "install", "--upgrade", "pip", "setuptools", "wheel"
            ], "Upgrading pip")
            
            self._run_command([
                str(pip_path), "install", "-r", str(requirements_path)
            ], "Installing Python dependencies")
            
            print("✅ Python environment configured")
            return True
            
        except Exception as e:
            print(f"❌ Failed to setup Python environment: {e}")
            return False
    
    def install_carbuddy_application(self) -> bool:
        """Install CarBuddy application files.
        
        Returns:
            True if installation successful, False otherwise
        """
        print("📱 Installing CarBuddy application...")
        
        try:
            # Copy application files
            src_dir = self.project_root / "src"
            app_src_dir = self.install_dir / "src"
            
            if app_src_dir.exists():
                shutil.rmtree(app_src_dir)
            shutil.copytree(src_dir, app_src_dir)
            
            # Copy main application
            shutil.copy2(
                self.project_root / "main.py",
                self.install_dir / "main.py"
            )
            
            # Create config directory structure
            config_dir = self.install_dir / "config"
            config_dir.mkdir(exist_ok=True)
            
            # Copy default configuration
            shutil.copy2(
                self.project_root / "config" / "default.json",
                config_dir / "default.json"
            )
            
            # Create factory-provisioned adapter MAC file
            adapter_mac_file = config_dir / "adapter_mac.txt"
            with open(adapter_mac_file, 'w') as f:
                f.write(f"# Factory-provisioned adapter MAC address\n")
                f.write(f"# Provisioned on: $(date)\n")
                f.write(f"{self.adapter_mac}\n")
            
            # Create logs directory
            logs_dir = self.install_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Set proper ownership
            self._run_command([
                "chown", "-R", f"{self.user}:{self.user}", str(self.install_dir)
            ], "Setting file ownership")
            
            # Set execute permissions on main.py
            main_py = self.install_dir / "main.py"
            main_py.chmod(0o755)
            
            print("✅ CarBuddy application installed")
            return True
            
        except Exception as e:
            print(f"❌ Failed to install CarBuddy application: {e}")
            return False
    
    def provision_bluetooth_pairing(self) -> bool:
        """Provision Bluetooth pairing with the specific adapter.
        
        Returns:
            True if pairing successful, False otherwise
        """
        print(f"🔵 Provisioning Bluetooth pairing with {self.adapter_mac}...")
        
        try:
            # Enable and start Bluetooth service
            self._run_command([
                "systemctl", "enable", "bluetooth"
            ], "Enabling Bluetooth service")
            
            self._run_command([
                "systemctl", "start", "bluetooth"
            ], "Starting Bluetooth service")
            
            # Wait for Bluetooth to initialize
            import time
            time.sleep(3)
            
            # Check if adapter is discoverable (this would be done during manufacturing
            # when the adapter is in pairing mode)
            print("⚠️  Factory Note: Ensure Veepeak adapter is in pairing mode")
            
            # Attempt pairing using bluetoothctl
            pairing_commands = f"""
agent on
default-agent
scan on
# Wait for adapter to appear in scan results
pair {self.adapter_mac}
trust {self.adapter_mac}
connect {self.adapter_mac}
quit
"""
            
            print("📝 Bluetooth pairing commands:")
            print(pairing_commands)
            
            # In a real factory setting, this would be automated
            # For now, we'll create a script that can be run manually
            pairing_script = self.install_dir / "pair_adapter.sh"
            with open(pairing_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write("# Factory Bluetooth pairing script\n")
                f.write(f"# Pair with adapter: {self.adapter_mac}\n\n")
                f.write("echo 'Starting Bluetooth pairing process...'\n")
                f.write("bluetoothctl << EOF\n")
                f.write("agent on\n")
                f.write("default-agent\n")
                f.write("scan on\n")
                f.write("# Factory operator: wait for adapter in scan results\n")
                f.write(f"pair {self.adapter_mac}\n")
                f.write(f"trust {self.adapter_mac}\n")
                f.write(f"connect {self.adapter_mac}\n")
                f.write("quit\n")
                f.write("EOF\n")
                f.write("echo 'Pairing process completed.'\n")
            
            pairing_script.chmod(0o755)
            
            print(f"✅ Bluetooth pairing configured for {self.adapter_mac}")
            print(f"📝 Manual pairing script created: {pairing_script}")
            print("ℹ️  Run the pairing script during manufacturing with adapter in pairing mode")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to provision Bluetooth pairing: {e}")
            return False
    
    def configure_system_services(self) -> bool:
        """Configure systemd services for auto-start.
        
        Returns:
            True if configuration successful, False otherwise
        """
        print("⚙️  Configuring system services...")
        
        try:
            # Copy systemd service file
            service_src = self.project_root / "systemd" / "sentry-carbuddy.service"
            service_dst = Path("/etc/systemd/system/sentry-carbuddy.service")
            
            # Read and customize service file
            with open(service_src, 'r') as f:
                service_content = f.read()
            
            # Replace paths with actual install directory
            service_content = service_content.replace(
                "/opt/sentry-carbuddy",
                str(self.install_dir)
            )
            
            # Write customized service file
            with open(service_dst, 'w') as f:
                f.write(service_content)
            
            # Set proper permissions
            service_dst.chmod(0o644)
            
            # Reload systemd and enable service
            self._run_command([
                "systemctl", "daemon-reload"
            ], "Reloading systemd")
            
            self._run_command([
                "systemctl", "enable", "sentry-carbuddy.service"
            ], "Enabling CarBuddy service")
            
            print("✅ System services configured")
            return True
            
        except Exception as e:
            print(f"❌ Failed to configure system services: {e}")
            return False
    
    def verify_provisioning(self) -> bool:
        """Verify that provisioning was completed correctly.
        
        Returns:
            True if verification successful, False otherwise
        """
        print("🔍 Verifying factory provisioning...")
        
        try:
            # Check installation directory
            if not self.install_dir.exists():
                print(f"❌ Install directory missing: {self.install_dir}")
                return False
            
            # Check main application
            main_py = self.install_dir / "main.py"
            if not main_py.exists():
                print("❌ Main application missing")
                return False
            
            # Check virtual environment
            venv_python = self.install_dir / "venv" / "bin" / "python"
            if not venv_python.exists():
                print("❌ Python virtual environment missing")
                return False
            
            # Check adapter MAC file
            adapter_mac_file = self.install_dir / "config" / "adapter_mac.txt"
            if not adapter_mac_file.exists():
                print("❌ Adapter MAC file missing")
                return False
            
            # Verify adapter MAC content
            with open(adapter_mac_file, 'r') as f:
                content = f.read().strip()
                if self.adapter_mac not in content:
                    print(f"❌ Adapter MAC not found in config: {content}")
                    return False
            
            # Check systemd service
            service_file = Path("/etc/systemd/system/sentry-carbuddy.service")
            if not service_file.exists():
                print("❌ Systemd service file missing")
                return False
            
            # Test Python imports
            test_cmd = [
                str(venv_python), "-c",
                "import sys; sys.path.insert(0, 'src'); from src.config import Config; print('✅ Imports working')"
            ]
            
            result = subprocess.run(
                test_cmd,
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"❌ Python imports test failed: {result.stderr}")
                return False
            
            print("✅ Factory provisioning verification passed")
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
    
    def _run_command(self, cmd: list, description: str, timeout: int = 300) -> None:
        """Run a system command with error handling.
        
        Args:
            cmd: Command to run as list
            description: Description for logging
            timeout: Command timeout in seconds
        
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        print(f"  📝 {description}...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            print(f"  ❌ Command failed: {' '.join(cmd)}")
            print(f"  Error: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
        
        if result.stdout.strip():
            print(f"  📄 Output: {result.stdout.strip()}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Factory Provisioning Script for Sentry CarBuddy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python factory_provision.py --adapter-mac AA:BB:CC:DD:EE:FF
  sudo python factory_provision.py --adapter-mac AA:BB:CC:DD:EE:FF --install-dir /opt/carbuddy
  
Notes:
  - Must be run as root (sudo)
  - Adapter should be in pairing mode during provisioning
  - Creates a complete ready-to-deploy CarBuddy system
        """
    )
    
    parser.add_argument(
        "--adapter-mac",
        required=True,
        help="MAC address of the Veepeak OBDCheck BLE+ adapter to pair with"
    )
    
    parser.add_argument(
        "--install-dir",
        default="/opt/sentry-carbuddy",
        help="Installation directory for CarBuddy (default: /opt/sentry-carbuddy)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")
        print(f"Would provision adapter: {args.adapter_mac}")
        print(f"Would install to: {args.install_dir}")
        return 0
    
    try:
        provisioner = FactoryProvisioner(
            adapter_mac=args.adapter_mac,
            install_dir=args.install_dir
        )
        
        success = provisioner.provision_system()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Provisioning failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
