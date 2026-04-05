#!/usr/bin/env python3
"""
Quickly find DM40 series Bluetooth multimeter
"""

import asyncio
from typing import cast
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

async def find_dm40_device():
    """Find DM40 device"""
    print("🔍 Scanning for DM40 series devices...")
    print("=" * 60)

    devices = cast(
        dict[str, tuple[BLEDevice, AdvertisementData]],
        await BleakScanner.discover(timeout=8.0, return_adv=True),
    )

    dm40_devices = []
    all_devices = []

    for address, (device, adv_data) in devices.items():
      name = device.name or getattr(adv_data, "local_name", None) or "Unknown"
      rssi = getattr(adv_data, "rssi", -1)

      entry = {
          "name": name,
          "address": address,
          "rssi": rssi,
      }
      all_devices.append(entry)

      if "DM40" in name.upper() or "DM4" in name.upper():
          dm40_devices.append(entry.copy())

    print(f"📡 Total discovered {len(all_devices)} Bluetooth devices\n")

    if dm40_devices:
        print(f"✅ Discovered {len(dm40_devices)} DM40 devices:\n")
        for i, dev in enumerate(dm40_devices, 1):
            print(f"Device {i}:")
            print(f"  Name: {dev['name']}")
            print(f"  Address: {dev['address']}")
            print(f"  Signal strength: {dev['rssi']} dBm")
            print("-" * 40)

        # Display usage example for first device
        print("\n📌 Usage example:")
        print(f"device = Com_DM40(device_addr='{dm40_devices[0]['address']}')")
    else:
        print("❌ No DM40 devices found")
        print("\n📋 All discovered devices:")
        for i, dev in enumerate(all_devices[:10], 1):  # Only show first 10
            print(f"  {i}. {dev['name']} ({dev['address']}) - {dev['rssi']} dBm")

        print("\nTroubleshooting suggestions:")
        print("1. Ensure DM40 multimeter is powered on")
        print("2. Ensure Bluetooth is enabled")
        print("3. Ensure device is in discoverable mode")
        print("4. Try restarting the multimeter's Bluetooth")
        print("5. Reduce the distance to the computer")

if __name__ == "__main__":
    try:
        asyncio.run(find_dm40_device())
    except KeyboardInterrupt:
        print("\nScan interrupted")
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease ensure:")
        print("- bleak is installed: pip install bleak")
        print("- System Bluetooth is enabled")
        print("- System has Bluetooth adapter")
