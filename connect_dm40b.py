#!/usr/bin/env python3
"""
Specifically test connection to DM40 device
"""
import asyncio
from typing import cast
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# DM40 service UUID
DM40_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
DM40_WRITE_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
DM40_READ_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"


def _display_name(device: BLEDevice, adv_data: AdvertisementData) -> str:
    device_name = getattr(device, "name", None)
    adv_name = getattr(adv_data, "local_name", None)
    return device_name or adv_name or "Unknown"


def _display_address(device: BLEDevice) -> str:
    return getattr(device, "address", None) or str(device)

async def connect_DM40():
    """Connect to DM40 and get service information"""
    print("🔍 Scanning advertisement data for DM40...")

    scanned = cast(
        dict[str, tuple[BLEDevice, AdvertisementData]],
        await BleakScanner.discover(timeout=10, return_adv=True),
    )

    target_uuid = DM40_SERVICE_UUID.lower()
    match: tuple[BLEDevice, AdvertisementData] | None = None
    matched_addr = ""

    for addr, (device, adv_data) in scanned.items():
        advertised_services = [
            str(u).lower() for u in (getattr(adv_data, "service_uuids", None) or [])
        ]
        if target_uuid in advertised_services:
            match = (device, adv_data)
            matched_addr = addr
            break

    if match is None:
        for addr, (device, adv_data) in scanned.items():
            name = _display_name(device, adv_data)
            if "DM40" in name.upper():
                match = (device, adv_data)
                matched_addr = addr
                break

    if match is None:
        print("❌ DM40 device not found")
        return None

    device, adv_data = match
    resolved_addr = _display_address(device)
    shown_addr = resolved_addr if resolved_addr and resolved_addr != "Unknown" else matched_addr

    print(f"✅ Device found: {_display_name(device, adv_data)}")
    print(f"📡 Address: {shown_addr}")
    print(f"📶 RSSI: {getattr(adv_data, 'rssi', 'Unknown')} dBm")

    # Attempt connection
    print("\n🔗 Attempting connection...")
    try:
        client = BleakClient(device, timeout=10)
        await client.connect()
        print("✅ Connection successful!")

        # List all services
        print("\n📋 Discovered services:")
        for service in client.services:
            print(f"\n  Service: {service.uuid}")
            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"    Characteristic: {char.uuid}")
                print(f"      Properties: {props}")

                # Check if this is the characteristic we need
                char_uuid = str(char.uuid).lower()
                if char_uuid == DM40_WRITE_UUID:
                    print(f"      ⭐ This is a write characteristic!")
                if char_uuid == DM40_READ_UUID:
                    print(f"      ⭐ This is a read characteristic!")

        # Enable notifications
        print(f"\n📢 Enabling notifications...")
        await client.start_notify(DM40_READ_UUID, lambda s, d: print(f"Received data: {d.hex()}"))
        print("✅ Notification enabled successfully")

        # Send read command
        print(f"\n📤 Sending read command...")
        cmd = bytes([0xaf, 0x05, 0x03, 0x09, 0x00, 0x40])
        await client.write_gatt_char(DM40_WRITE_UUID, cmd)
        print("✅ Command sent successfully")

        # Wait for response
        print("\n⏳ Waiting for response (5 seconds)...")
        await asyncio.sleep(5)

        # Disconnect
        await client.stop_notify(DM40_READ_UUID)
        await client.disconnect()
        print("\n✅ Test completed")

        return shown_addr

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(connect_DM40())

    if result:
        print(f"\n📌 Update dm40ble.py:")
        print(f'  device = Com_DM40(device_addr="{result}")')
