#!/usr/bin/env python3
"""
Simple test of dm40ble module
"""
import asyncio
from dm40ble import Com_DM40

async def test_dm40() -> None:
    """Test DM40 connection"""
    print("🔍 Starting DM40 test...")
    device = Com_DM40()

    try:
        # Connect to device
        print("📡 Connecting...")
        await device.connect()
        print("✅ Connection successful!")

        # Set callback
        data_received = False

        def on_data(data: float, unit: str, state: str) -> None:
            nonlocal data_received
            data_received = True
            print(f"📊 Data received: {data} {unit} ({state})")

        device.set_data_update_callback(on_data)

        # Test reading data
        print("\n📤 Reading data...")
        for i in range(5):
            data, unit, state = await device.get_data()
            if data is not None:
                print(f"  [{i+1}] Data: {data} {unit} ({state})")
            else:
                print(f"  [{i+1}] No data ({state})")
            await asyncio.sleep(0.5)

        # Disconnect
        print("\n🔌 Disconnecting...")
        await device.disconnect()
        print("✅ Test completed!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_dm40())
