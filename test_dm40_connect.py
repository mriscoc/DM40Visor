#!/usr/bin/env python3
"""
Direct test connection to DM40
"""
import asyncio
from typing import cast
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# DM40_ADDRESS = "A7:CD:DA:CC:60:05"
DM40_ADDRESS = "30:02:86:1B:C2:DB"


def _display_name(device: BLEDevice | None, adv_data: AdvertisementData | None = None) -> str:
    device_name = getattr(device, "name", None) if device else None
    adv_name = getattr(adv_data, "local_name", None) if adv_data else None
    return device_name or adv_name or "Unknown"


def _display_address(device: BLEDevice | None) -> str:
    if device is None:
        return DM40_ADDRESS
    return getattr(device, "address", None) or str(device)


def _display_rssi(device: BLEDevice | None, adv_data: AdvertisementData | None = None) -> int:
    adv_rssi = getattr(adv_data, "rssi", None) if adv_data else None
    device_rssi = getattr(device, "rssi", None) if device else None
    return adv_rssi if isinstance(adv_rssi, int) else (device_rssi if isinstance(device_rssi, int) else -1)


def _find_scan_match(
    scanned: dict[str, tuple[BLEDevice, AdvertisementData]], target_address: str
) -> tuple[BLEDevice, AdvertisementData] | None:
    target_key = target_address.lower()
    pair = scanned.get(target_key)
    if pair is not None:
        return pair

    for addr, candidate in scanned.items():
        if addr.lower() == target_key:
            return candidate

    return None

async def test_connect():
    """Test connect to DM40"""
    print(f"Attempting connection to DM40: {DM40_ADDRESS}")
    print("=" * 60)

    print("\n🔍 Scanning advertisement data for target device...")
    scanned = cast(
        dict[str, tuple[BLEDevice, AdvertisementData]],
        await BleakScanner.discover(timeout=8.0, return_adv=True),
    )
    matched = _find_scan_match(scanned, DM40_ADDRESS)

    device: BLEDevice | None
    adv_data: AdvertisementData | None
    if matched is not None:
        device, adv_data = matched
    else:
        device = await BleakScanner.find_device_by_address(DM40_ADDRESS, timeout=8.0)
        adv_data = None

    print(f"   Name: {_display_name(device, adv_data)}")
    print(f"   Address: {_display_address(device)}")
    print(f"   RSSI: {_display_rssi(device, adv_data)} dBm")
    if adv_data is not None:
        service_uuids = [str(u).lower() for u in (getattr(adv_data, "service_uuids", None) or [])]
        print(f"   Local name: {getattr(adv_data, 'local_name', 'Unknown')}")
        print(f"   Advertised services: {len(service_uuids)}")

    try:
        connect_target = device if device is not None else DM40_ADDRESS
        async with BleakClient(connect_target) as client:
            print("✅ Connection successful!")

            # Get services
            print("\n📋 Discovered services:")
            for service in client.services:
                print(f"  Service: {service.uuid}")
                for char in service.characteristics:
                    print(f"    Characteristic: {char.uuid}")

            # Read device name
            name_char_uuid = "00002a00-0000-1000-8000-00805f9b34fb"
            has_name_char = any(
                str(char.uuid).lower() == name_char_uuid
                for service in client.services
                for char in service.characteristics
            )
            if has_name_char:
                try:
                    name = await client.read_gatt_char(name_char_uuid)
                    device_name = name.decode('utf-8', errors='ignore').strip('\x00')
                    print(f"\n📌 Device name (GATT): {device_name or _display_name(device, adv_data)}")
                except Exception as e:
                    print(f"\n⚠️ Unable to read GATT device name: {e}")
                    print(f"📌 Device name (fallback): {_display_name(device, adv_data)}")
            else:
                print("\nℹ️ Device Name characteristic (0x2A00) is not exposed by this device")
                print(f"📌 Device name (fallback): {_display_name(device, adv_data)}")

            return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connect())
