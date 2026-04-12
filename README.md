# DM40 Bluetooth Multimeter Driver

A Python driver for Bluetooth communication with the DM40 series digital multimeter.

<img width="668" height="398" alt="ALIENTEK-DM40" src="https://github.com/user-attachments/assets/c11233ae-ed75-4b42-9069-f2a03ed68140" />


## 📋 Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Getting the Device Address](#getting-the-device-address)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## ✨ Features

- ✅ Bluetooth device scanning and discovery
- ✅ Real-time data reading (voltage / current)
- ✅ Mode switching (voltage / current)
- ✅ Background task management
- ✅ Data update callbacks
- ✅ Connection retry logic
- ✅ Async operation support

## 📦 Installation

```bash
pip install bleak
```

## Windows and Linux controller
The [Windows and Linux](https://www.patreon.com/posts/dm40visor-155598531) versions of the DM40Visor were built on the foundations of this project.  
  

![DM40_Winapp](https://github.com/user-attachments/assets/5eaf79a4-81b0-4095-8ccd-cee291b2e41d)

## 🔍 Getting the Device Address

### Method 1: Quick DM40 scan

```bash
python find_dm40.py
```

Example output:
```
🔍 Scanning for DM40 series devices...
============================================================
✅ Found 1 DM40 device:

Device 1:
  Name: DM40
  Address: D7:ED:DF:91:FC:4D
  Signal strength: -45 dBm
----------------------------------------
📌 Usage example:
device = Com_DM40(device_addr='D7:ED:DF:91:FC:4D')
```

### Method 2: Scan all Bluetooth devices

```bash
python scan_ble_devices.py
```

### Method 3: Search by keyword

```bash
python scan_ble_devices.py --search DM40
python scan_ble_devices.py --search DM40 20  # scan for 20 seconds
```

## 💻 Usage

### Basic usage

```python
from dm40ble import Com_DM40

# Create device instance (auto-discovers DM40 if no address given)
device = Com_DM40(device_addr="A7:CD:DA:CC:60:05")

# Set data update callback
def on_data_update(data: float, unit: str, mode: str) -> None:
    print(f"Reading: {data} {unit} ({mode})")

device.set_data_update_callback(on_data_update)

# Start background task (sample every 200 ms)
device.run(loop_ms=200)

# Wait for connection
import time
while device.get_state() != 1:
    time.sleep(0.1)
    if device.get_state() == -1:
        print("Connection failed")
        break

# Switch to voltage mode
device.set_mode(1)  # 1 = voltage mode

# Switch to current mode
device.set_mode(2)  # 2 = current mode

# Get latest data
value, unit, mode = device.get_current_data()
print(f"Current value: {value} {unit} ({mode})")

# Stop background task
device.stop()
```

### Async usage

```python
import asyncio
from dm40ble import Com_DM40

async def main():
    async with Com_DM40("A7:CD:DA:CC:60:05") as device:
        # Set voltage mode
        await device.set_voltage_mode()

        # Read data
        data, unit, mode = await device.get_data()
        print(f"Voltage: {data} {unit} ({mode})")

        # Set current mode
        await device.set_current_mode()

        data, unit, mode = await device.get_data()
        print(f"Current: {data} {unit} ({mode})")

asyncio.run(main())
```

### Full example

```python
from dm40ble import Com_DM40
import time

def data_callback(data: float, unit: str, mode: str) -> None:
    print(f"📊 Live reading: {data:.2f} {unit} ({mode})")

# Initialise device (omit device_addr to auto-discover)
device = Com_DM40(
    device_addr="A7:CD:DA:CC:60:05",
    max_retry=3
)

# Set callback
device.set_data_update_callback(data_callback)

# Start background task
print("Connecting to device...")
device.run(loop_ms=500)  # sample every 500 ms

# Wait for connection
while True:
    state = device.get_state()
    if state == 1:
        print("✓ Connected!")
        break
    elif state == -1:
        print("✗ Connection failed")
        device.stop()
        exit(1)
    time.sleep(0.1)

# Switch modes and read data
try:
    print("\nSwitching to voltage mode...")
    device.set_mode(1)
    time.sleep(2)

    print("\nSwitching to current mode...")
    device.set_mode(2)
    time.sleep(2)

    # Keep running
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")
    device.stop()
    print("Done")
```

## 📖 API Reference

### `Com_DM40` class

#### Constructor parameters
- `device_addr` (str, optional): Bluetooth device MAC address. If omitted, the driver auto-discovers any DM40 device nearby.
- `max_retry` (int): Number of connection retries. Default: 3.

#### Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|---------|
| `run(loop_ms)` | Start background task | Sampling interval (ms) | None |
| `stop()` | Stop background task | — | None |
| `set_data_update_callback(callback)` | Set data callback | Callback `(float, str, str)` | None |
| `get_current_data()` | Get latest cached data | — | `(float\|None, str, str)` |
| `get_state()` | Get task state | — | int (0=idle, 1=running, -1=error) |
| `set_mode(mode)` | Set mode (legacy) | 1=voltage, 2=current | None |
| `connect()` | Connect manually | — | bool |
| `disconnect()` | Disconnect | — | None |
| `get_data()` | Read one measurement | — | `(float\|None, str, str)` |
| `set_voltage_mode()` | Set DC voltage mode | — | bool |
| `set_current_mode()` | Set DC current mode | — | bool |
| `run_coroutine(coro)` | Run coroutine on internal loop | Coroutine | Any |

#### State codes
- `0`: Idle / not started
- `1`: Running / connected
- `-1`: Error / connection failed

## 🔧 Protocol Notes

### Commands
- **Read data**: `AF 05 03 09 00 40`
- **Voltage mode**: `AF 05 03 06 01 30 12`
- **Current mode**: `AF 05 03 06 01 39 09`

### Response format
```
Response bytes: [byte0 ... byteN]
- byte[5]: unit identifier
  - 0x30 = mV (millivolts)
  - 0x39 = mA (milliamps)

- byte[-8]: scale factor
  - 0x18 =  0.1
  - 0x19 = -0.1
  - 0x16 =  1
  - 0x17 = -1
  - 0x15 = -0.01
  - 0x14 =  0.01

- byte[-3] and byte[-2]: raw value (little-endian)
  data = byte[-3] | (byte[-2] << 8)

Final value = data × scale_factor
```

### BLE UUIDs (DM40C profile)
| Role | UUID |
|------|------|
| Service | `0000fff0-0000-1000-8000-00805f9b34fb` |
| Write (TX) | `0000fff1-0000-1000-8000-00805f9b34fb` |
| Notify (RX) | `0000fff2-0000-1000-8000-00805f9b34fb` |

## 🐛 Troubleshooting

### Issue 1: Bluetooth is off
**Error**: `Bluetooth device is turned off`

**Fix**:
- **Windows**: Settings → Bluetooth → On
- **macOS**: System Settings → Bluetooth → On
- **Linux**: `sudo systemctl start bluetooth`

### Issue 2: Insufficient permissions
**Error**: `Permission denied` or `Access denied`

**Fix**:
- **Linux**: Run with `sudo` or add user to the `bluetooth` group:
  ```bash
  sudo usermod -a -G bluetooth $USER
  ```
- **macOS**: System Settings → Privacy & Security → Bluetooth → allow Terminal

### Issue 3: Device not found
**Fix**:
1. Make sure the DM40 multimeter is powered on
2. Make sure Bluetooth is enabled on the meter
3. Try restarting the meter
4. Move closer to the computer (< 5 m)
5. Make sure the device is not already connected to another host

### Issue 4: Unstable connection
**Fix**:
- Increase retries: `Com_DM40(max_retry=5)`
- Increase sampling interval: `device.run(loop_ms=1000)`
- Check battery level

### Issue 5: Data parsing errors
**Fix**:
- Verify the device model is DM40/DM40C
- Print raw response: `print(response.hex())`
- Confirm the BLE UUIDs match the table above

## 📝 Notes

1. **Bluetooth adapter**: Make sure the computer has a Bluetooth adapter
2. **Range**: Keep the device within Bluetooth range (typically < 10 m)
3. **Interference**: Avoid environments with strong electromagnetic interference
4. **Battery**: Ensure the multimeter has sufficient battery
5. **Exclusive access**: Ensure the device is not already in use by another application

## 📄 License

MIT License

## Acknowledgements
- https://blog.csdn.net/weixin_41929418/article/details/149218095
