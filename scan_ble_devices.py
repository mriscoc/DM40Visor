#!/usr/bin/env python3
"""
Bluetooth device scanning script
Used to scan nearby BLE devices and display their addresses and names
"""

import asyncio
from bleak import BleakScanner
import sys

async def scan_ble_devices(timeout=10):
    """
    Scan Bluetooth devices

    Args:
        timeout: scan time (seconds)

    Returns:
        list: list of discovered devices, each device contains address and name
    """
    print(f"Starting Bluetooth device scan... (scan time: {timeout}s)")
    print("-" * 60)

    # Start scanning
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)

    device_list = []

    for address, (device, adv_data) in devices.items():
        if device.name:  # Only display devices with names
            device_info = {
                'address': device.address,
                'name': device.name,
                'rssi': adv_data.rssi if adv_data else -1
            }
            device_list.append(device_info)

            print(f"Device name: {device_info['name']}")
            print(f"MAC address: {device_info['address']}")
            print(f"Signal strength: {device_info['rssi']} dBm")
            print("-" * 60)

    if not device_list:
        print("No Bluetooth devices found")
        print("Possible reasons:")
        print("1. Bluetooth not enabled")
        print("2. No BLE devices broadcasting")
        print("3. Insufficient permissions (Linux requires sudo, macOS requires system permissions)")

    return device_list

async def scan_for_specific_device(device_name_keyword, timeout=15):
    """
    Scan for devices with specific name

    Args:
        device_name_keyword: device name keyword
        timeout: scan time
    """
    print(f"Searching for devices containing '{device_name_keyword}'...")
    print("-" * 60)

    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)

    for address, (device, adv_data) in devices.items():
        if device.name and device_name_keyword.lower() in device.name.lower():
            print(f"✓ Target device found!")
            print(f"  Name: {device.name}")
            print(f"  Address: {device.address}")
            print(f"  Signal strength: {adv_data.rssi if adv_data else 'N/A'} dBm")
            return device.address

    print(f"✗ Device containing '{device_name_keyword}' not found")
    return None

def main():
    """Main function"""
    if len(sys.argv) > 1:
        # Mode 1: search for specific device
        if sys.argv[1] == "--search":
            if len(sys.argv) < 3:
                print("Usage: python scan_ble_devices.py --search <device name keyword>")
                sys.exit(1)
            keyword = sys.argv[2]
            timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 15
            asyncio.run(scan_for_specific_device(keyword, timeout))
        else:
            print("Unknown parameter")
            print("Usage:")
            print("  python scan_ble_devices.py                    # Scan all devices")
            print("  python scan_ble_devices.py --search DM40      # Search for DM40 devices")
            print("  python scan_ble_devices.py --search DM40 20   # Search for 20 seconds")
    else:
        # Mode 2: scan all devices
        try:
            asyncio.run(scan_ble_devices(timeout=10))
        except KeyboardInterrupt:
            print("\nScan interrupted by user")
        except Exception as e:
            print(f"Scan error: {e}")
            print("\nPossible solutions:")
            print("- Ensure Bluetooth is enabled")
            print("- Linux: Try running with sudo")
            print("- macOS: Ensure terminal has Bluetooth permissions")
            print("- Windows: Ensure Bluetooth service is running")

if __name__ == "__main__":
    main()
