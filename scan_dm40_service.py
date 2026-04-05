#!/usr/bin/env python3
"""
Find devices through DM40 service UUID
"""
import asyncio
from typing import cast
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# DM40 service UUID
DM40_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"


def _display_name(device: BLEDevice, adv_data: AdvertisementData) -> str:
    device_name = getattr(device, "name", None)
    adv_name = getattr(adv_data, "local_name", None)
    return device_name or adv_name or "Unknown"


def _display_address(device: BLEDevice) -> str:
    return getattr(device, "address", None) or str(device)

async def scan_for_dm40_service():
    """Scan and find devices with DM40 service"""
    print("🔍 Scanning for Bluetooth devices with DM40 service...")
    print("=" * 60)

    # Scan all devices and advertisement payloads
    scanned = cast(
        dict[str, tuple[BLEDevice, AdvertisementData]],
        await BleakScanner.discover(timeout=10, return_adv=True),
    )
    devices = list(scanned.values())

    print(f"📡 Discovered {len(devices)} devices\n")

    found_candidates = []
    target_uuid = DM40_SERVICE_UUID.lower()

    for i, (device, adv_data) in enumerate(devices, 1):
        name = _display_name(device, adv_data)
        addr = _display_address(device)

        print(f"[{i}/{len(devices)}] Checking {name} ({addr[:38]}-)...", end=" ", flush=True)

        # Many BLE peripherals expose service UUIDs in advertisement data; check this first.
        adv_service_uuids = [
            str(u).lower() for u in (getattr(adv_data, "service_uuids", None) or [])
        ]
        if target_uuid in adv_service_uuids:
            print("✅ Found DM40 device via advertisement")
            found_candidates.append({
                'name': name,
                'address': addr,
                'services': adv_service_uuids,
            })
            continue

        # Try connecting and checking services
        try:
            async with BleakClient(device, timeout=5) as client:
                # Use discovered services from the connected client.
                service_uuids = [str(s.uuid).lower() for s in client.services]

                # Check if it has DM40 service
                if target_uuid in service_uuids:
                    print("✅ Found DM40 device!")
                    found_candidates.append({
                        'name': name,
                        'address': addr,
                        'services': service_uuids
                    })
                else:
                    # Show found services for debugging
                    if service_uuids:
                        print(f"No (services: {len(service_uuids)} items)")
                    else:
                        print("No services")

        except Exception as e:
            error_msg = str(e)[:40]
            print(f"❌ {error_msg}")

    # Output results
    print("\n" + "=" * 60)
    if found_candidates:
        print(f"✅ Found {len(found_candidates)} DM40 devices:\n")
        for i, dev in enumerate(found_candidates, 1):
            print(f"Device {i}:")
            print(f"  Name: {dev['name']}")
            print(f"  Address: {dev['address']}")
            print(f"  Service count: {len(dev['services'])}")
            print(f"\n📌 Update dm40ble.py:")
            print(f"  device = Com_DM40(device_addr=\"{dev['address']}\")")
            print("-" * 50)
    else:
        print("❌ No DM40 devices found")
        print("\nTips:")
        print("1. Ensure DM40 multimeter is powered on")
        print("2. Ensure DM40 Bluetooth is enabled")
        print("3. Try bringing the multimeter closer to the computer")
        print("4. Try restarting the multimeter's Bluetooth")

if __name__ == "__main__":
    try:
        asyncio.run(scan_for_dm40_service())
    except KeyboardInterrupt:
        print("\nScan interrupted")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
