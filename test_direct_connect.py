#!/usr/bin/env python3
"""
Direct test connection to DM40 device
"""
import asyncio
from typing import cast
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData


def _display_name(device: BLEDevice, adv_data: AdvertisementData | None = None) -> str:
    device_name = getattr(device, "name", None)
    adv_name = getattr(adv_data, "local_name", None) if adv_data else None
    return device_name or adv_name or "Unknown"


def _display_address(device: BLEDevice) -> str:
    return getattr(device, "address", None) or str(device)


def _display_rssi(device: BLEDevice, adv_data: AdvertisementData | None = None) -> int:
    adv_rssi = getattr(adv_data, "rssi", None) if adv_data else None
    device_rssi = getattr(device, "rssi", None)
    return adv_rssi if isinstance(adv_rssi, int) else (device_rssi if isinstance(device_rssi, int) else -1)

async def test_direct_connect():
    """Test direct connection"""
    # Original MAC address
    target_address = "A7:CD:DA:CC:60:05"

    print(f"🔍 Attempting to find device: {target_address}")
    print("-" * 50)

    # Scan with advertisement payloads so we can resolve attributes reliably.
    scanned = cast(
        dict[str, tuple[BLEDevice, AdvertisementData]],
        await BleakScanner.discover(timeout=10, return_adv=True),
    )

    lookup_key = target_address.lower()
    pair = scanned.get(lookup_key)
    if pair is None:
        for addr, candidate in scanned.items():
            if addr.lower() == lookup_key:
                pair = candidate
                break

    if pair:
        device, adv_data = pair
    else:
        # Fallback for environments that only resolve through address lookup.
        device = await BleakScanner.find_device_by_address(target_address, timeout=10)
        adv_data = None

    if device:
        print(f"✅ Device found: {device}")
        print(f"   Device name: {_display_name(device, adv_data)}")
        print(f"   Device address: {_display_address(device)}")
        print(f"   RSSI: {_display_rssi(device, adv_data)} dBm")

        # Try connecting
        print("\n🔗 Attempting connection...")
        try:
            async with BleakClient(device) as client:
                print("✅ Connection successful!")

                # List all services
                print("\n📋 Discovered services:")
                for service in client.services:
                    print(f"  Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"    Characteristic: {char.uuid} (properties: {char.properties})")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
    else:
        print(f"❌ Device not found: {target_address}")
        print("\n💡 Possible reasons:")
        print("1. DM40 multimeter is not powered on")
        print("2. DM40 Bluetooth function is not enabled")
        print("3. Device is out of range")
        print("4. Device address has changed (macOS device addresses are in UUID format)")
        print("\n🔍 Let me try scanning all devices...")

        # Scan all devices with advertisement data for better names and RSSI.
        scanned = cast(
            dict[str, tuple[BLEDevice, AdvertisementData]],
            await BleakScanner.discover(timeout=5, return_adv=True),
        )
        devices = list(scanned.values())
        print(f"\n📡 Discovered {len(devices)} devices:")
        for i, (d, adv_data) in enumerate(devices[:20], 1):
            name = _display_name(d, adv_data)
            addr = _display_address(d)
            rssi = _display_rssi(d, adv_data)
            print(f"  {i}. {name} - {addr} ({rssi} dBm)")

if __name__ == "__main__":
    asyncio.run(test_direct_connect())
