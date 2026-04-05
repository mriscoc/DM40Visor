#!/usr/bin/env python3
"""
Get Bluetooth device UUIDs paired on macOS
"""
import asyncio
from bleak import BleakClient, BleakScanner

async def find_paired_dm40():
    """Find paired DM40 device"""
    print("🔍 Scanning paired DM40 devices...")
    print("=" * 60)

    # Scan devices
    devices = await BleakScanner.discover(timeout=10, return_adv=True)

    dm40_candidates = []

    for address, (device, adv_data) in devices.items():
        try:
            address = device.address
        except AttributeError:
            address = str(device)

        # Try connecting to each device and read name
        try:
            async with BleakClient(address, timeout=2) as client:
                try:
                    name_bytes = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                    name = name_bytes.decode('utf-8', errors='ignore').strip('\x00')

                    if "DM40" in name.upper() or "C-1-ATK" in name.upper():
                        dm40_candidates.append({
                            'name': name,
                            'address': address
                        })
                        print(f"✅ Found: {name}")
                        print(f"   Address: {address}")
                except:
                    pass
        except:
            pass

    if dm40_candidates:
        print(f"\n📌 Usage with first device address:")
        print(f"  device = Com_DM40(device_addr='{dm40_candidates[0]['address']}')")
    else:
        print("\n❌ No DM40 devices found")

if __name__ == "__main__":
    asyncio.run(find_paired_dm40())
