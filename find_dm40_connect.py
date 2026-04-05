#!/usr/bin/env python3
"""
Find DM40 device through connection attempt
"""
import asyncio
from bleak import BleakClient, BleakScanner

# DM40 service UUID
SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"

async def try_connect_to_device(address, timeout=3):
    """Try to connect to device and check if it's DM40"""
    try:
        async with BleakClient(address, timeout=timeout) as client:
            # Try to get device name
            try:
                name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
                device_name = name.decode('utf-8', errors='ignore')
            except:
                device_name = None

            # Check if device name contains DM40
            if device_name and "DM40" in device_name.upper():
                # Check if device has DM40 service
                services = client.services
                service_uuids = [str(s.uuid) for s in services]

                return {
                    'address': address,
                    'name': device_name,
                    'is_dm40': True,
                    'services': service_uuids
                }
            # Return name for debugging
            return {'found': False, 'name': device_name}
    except Exception as e:
        return {'found': False, 'error': str(e)[:50]}

async def find_dm40_by_connecting():
    """Find DM40 device by connecting and checking"""
    print("🔍 Scanning and trying to connect to find DM40 device...")
    print("=" * 60)

    # First scan all devices
    devices = await BleakScanner.discover(timeout=5, return_adv=True)

    print(f"📡 Discovered {len(devices)} devices, starting to connect and check...\n")

    # Sort by signal strength (first check strongest signals)
    device_list = []
    for address, (device, adv_data) in devices.items():
        try:
            rssi = adv_data.rssi
        except AttributeError:
            rssi = -100

        try:
            address = device.address
        except AttributeError:
            address = str(device)

        device_list.append((address, rssi))

    # Sort by signal strength (from strongest to weakest)
    device_list.sort(key=lambda x: x[1], reverse=True)

    # Only check top 20 devices with strongest signal
    found_names = []
    for i, (address, rssi) in enumerate(device_list[:20], 1):
        print(f"[{i}/20] Attempt connection to {address}...", end=" ", flush=True)

        result = await try_connect_to_device(address)

        if result and result.get('is_dm40'):
            print(f"✅ Found DM40!")
            print(f"\nDevice info:")
            print(f"  Name: {result['name']}")
            print(f"  Address: {result['address']}")
            print(f"\n📌 Usage:")
            print(f'  device = Com_DM40(device_addr="{result["address"]}")')
            return result['address']
        else:
            # Display found device name
            name = result.get('name')
            if name:
                print(f"Name: {name}")
                found_names.append(name)
            else:
                error = result.get('error', '')
                print(f"❌ {error if error else 'Unable to read name'}")

    print(f"\n❌ DM40 device not found")
    if found_names:
        print(f"\n📋 Successfully read device names:")
        for n in found_names:
            print(f"  - {n}")
    print("\nTips:")
    print("1. Ensure DM40 multimeter is powered on")
    print("2. Ensure DM40 Bluetooth is enabled")
    print("3. Try bringing the multimeter closer to the computer")

if __name__ == "__main__":
    try:
        asyncio.run(find_dm40_by_connecting())
    except KeyboardInterrupt:
        print("\n\nScan interrupted")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
