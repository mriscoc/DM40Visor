"""
DM40 Bluetooth Multimeter Communication Class
Supports multiple measurement modes: voltage, current, resistance, capacitance, frequency, temperature, etc.
"""
import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from typing import Optional, Callable, Any, Tuple
import time

class Com_DM40:
    DM40_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
    MEASUREMENT_HEADER = b"\xdf\x05\x03\x09"
    MEASUREMENT_FRAME_LEN = 16
    DEVICE_COUNTS = 60000.0
    CONTINUITY_ALT_AUX_SCALE_FLAGS = {0x84}
    CONTINUITY_WRAP_OFFSET = 65520
    FAST_ADDR_LOOKUP_TIMEOUT = 5.0
    DISCOVERY_TIMEOUT = 8.0



    ALT_SCALE_MAP = {
        # Reference-style scale bytes
        0x02: (6.0,    "V",  1.0,  4),   # 6 V variant
        0x04: (0.6,    "mV", 1e3,  2),   # 600 mV
        0x06: (0.6,    "mV", 1e3,  2),   # 600 mV alt
        0x08: (6.0,    "V",  1.0,  4),   # 6 V
        0x0A: (6.0,    "V",  1.0,  4),
        0x12: (6000.0, "V",  1.0,  1),   # 1000 V (ref)
        0x14: (600.0,  "V",  1.0,  2),   # 600 V
        0x16: (60.0,   "V",  1.0,  3),   # 60 V
        0x18: (6.0,    "V",  1.0,  4),   # 6 V (AUTO)
        0x1A: (6.0,    "V",  1.0,  4),
        0x26: (60.0,   "V",  1.0,  3),
        0x28: (6.0,    "V",  1.0,  4),   # 6 V (AUTO+)
        0x2A: (60.0,   "V",  1.0,  3),
        # FLAG_INFO-style VDC scale bytes (device firmware variant)
        0x00: (0.6,    "mV", 1e3,  2),   # VDC 600mV
        0x10: (60.0,   "V",  1.0,  3),   # VDC 60V
        0x20: (1000.0, "V",  1.0,  1),   # VDC 1000V
        0x30: (6.0,    "V",  1.0,  4),   # VDC AUTO+
        # FLAG_INFO-style VAC scale bytes
        0x40: (0.6,    "mV", 1e3,  2),   # VAC 600mV
        0x48: (6.0,    "V",  1.0,  4),   # VAC 6V
        0x50: (60.0,   "V",  1.0,  3),   # VAC 60V
        0x58: (600.0,  "V",  1.0,  2),   # VAC 600V
        0x60: (1000.0, "V",  1.0,  1),   # VAC 1000V
        0x68: (6.0,    "V",  1.0,  4),   # VAC AUTO
        0x70: (6.0,    "V",  1.0,  4),   # VAC AUTO+
    }

    # Some firmware variants reuse scale flags differently between ACV and DCV.
    # Keep VAC mapping intact while overriding DCV-only interpretations.
    VDC_SCALE_OVERRIDE_MAP = {
        0x02: (60.0, "V", 1.0, 3),
        0x04: (6.0, "V", 1.0, 4),
        0x06: (6.0, "V", 1.0, 4),
    }

    # DCV range flag (frame[5]) is more reliable than scale_flag on some variants.
    VDC_MODE_SCALE_MAP = {
        0x00: (0.6, "mV", 1e3, 2),   # 600mV
        0x08: (6.0, "V", 1.0, 4),     # 6V
        0x10: (60.0, "V", 1.0, 3),    # 60V
        0x18: (600.0, "V", 1.0, 2),   # 600V
        0x20: (1000.0, "V", 1.0, 1),  # 1000V
        0x28: (6.0, "V", 1.0, 4),     # AUTO
        0x30: (6.0, "V", 1.0, 4),     # AUTO+
    }

    AMP_SCALE_MAP = {
        0x02: (6000e-6, "uA", 1e6, 1),   # 6000 uA
        0x04: (600e-6,  "uA", 1e6, 2),   # 600 uA
        0x06: (600e-6,  "uA", 1e6, 2),
        0x14: (600e-3,  "mA", 1e3, 2),   # 600 mA
        0x16: (60e-3,   "mA", 1e3, 3),   # 60 mA
        0x18: (6e-3,    "mA", 1e3, 4),   # 6 mA
        0x1A: (6e-3,    "mA", 1e3, 4),
        0x26: (60.0,    "A",  1.0, 3),   # 60 A
        0x28: (6.0,     "A",  1.0, 4),   # 6 A
        0x2A: (6.0,     "A",  1.0, 4),
    }

    # Current mode flag map (frame[5]) to scale profile.
    # This avoids ambiguous scale_flag values on some firmware variants.
    AMP_MODE_SCALE_MAP = {
        0x01: (600e-6, "uA", 1e6, 2),
        0x09: (6e-3,   "uA", 1e6, 1),
        0x11: (60e-3,  "mA", 1e3, 3),
        0x19: (600e-3, "mA", 1e3, 2),
        0x21: (6.0,    "A",  1.0, 4),
        0x29: (10.0,   "A",  1.0, 3),
        0x41: (600e-6, "uA", 1e6, 2),
        0x49: (6e-3,   "uA", 1e6, 1),
        0x51: (60e-3,  "mA", 1e3, 3),
        0x59: (600e-3, "mA", 1e3, 2),
        0x61: (6.0,    "A",  1.0, 4),
        0x69: (10.0,   "A",  1.0, 3),
    }

    RES_SCALE_MAP = {
        0x00: (600000.0, "kΩ", 0.001, 2),
        0x02: (6000.0,   "Ω",  1.0,   1),
        0x04: (600.0,    "Ω",  1.0,   2),
        0x06: (600.0,    "Ω",  1.0,   2),
        0x14: (600000.0, "kΩ", 0.001, 2),
        0x16: (60000.0,  "kΩ", 0.001, 3),
        0x18: (6000.0,   "kΩ", 0.001, 4),
        0x1A: (6000.0,   "kΩ", 0.001, 4),
        0x26: (6e7,      "MΩ", 1e-6,  3),
        0x28: (6e6,      "MΩ", 1e-6,  4),
        0x2A: (6e6,      "MΩ", 1e-6,  4),
    }

    # Resistance mode flag map (frame[5]) to scale profile.
    # This is more reliable than scale_flag on some firmware variants.
    RES_MODE_SCALE_MAP = {
        0x02: (600.0,    "Ω",  1.0,   2),
        0x0A: (6000.0,   "kΩ", 0.001, 4),
        0x12: (60000.0,  "kΩ", 0.001, 3),
        0x1A: (600000.0, "kΩ", 0.001, 2),
        0x22: (6e6,      "MΩ", 1e-6,  4),
        0x2A: (6e7,      "MΩ", 1e-6,  3),
        0x42: (600.0,    "Ω",  1.0,   2),
        0x4A: (6000.0,   "kΩ", 0.001, 4),
        0x52: (60000.0,  "kΩ", 0.001, 3),
        0x5A: (600000.0, "kΩ", 0.001, 2),
        0x62: (6e6,      "MΩ", 1e-6,  4),
        0x6A: (6e7,      "MΩ", 1e-6,  3),
    }

    FREQ_SCALE_MAP = {
        0x02: (6000.0,    "Hz",  1.0,   1),
        0x04: (600.0,     "Hz",  1.0,   2),
        0x06: (60.0,      "Hz",  1.0,   3),
        0x14: (600000.0,  "kHz", 1e-3,  2),
        0x16: (60000.0,   "kHz", 1e-3,  3),
        0x18: (6000.0,    "kHz", 1e-3,  4),
        0x26: (6000000.0, "kHz", 1e-3,  1),
        0x28: (6000000.0, "MHz", 1e-6,  4),
    }

    CAP_SCALE_MAP = {
        0x02: (600e-9,  "nF", 1e9, 1),
        0x04: (60e-9,   "nF", 1e9, 2),
        0x06: (6e-9,    "nF", 1e9, 3),
        0x12: (600e-6,  "uF", 1e6, 1),
        0x14: (60e-6,   "uF", 1e6, 2),
        0x16: (6e-6,    "uF", 1e6, 3),
        0x24: (60e-3,   "mF", 1e3, 2),
        0x26: (6e-3,    "mF", 1e3, 3),
        0x28: (600e-6,  "uF", 1e6, 1),
    }

    # Fallback: raw multiplier per scale_flag when no scale map entry matches.
    # Gives a best-effort numeric value rather than silently dropping data.
    _FALLBACK_MULT = {
        0x00: 0.00001, 0x02: 0.001, 0x04: 0.001, 0x06: 0.001,
        0x08: 0.0001, 0x0A: 0.001, 0x0E: 0.001,
        0x12: 0.1,   0x14: 0.01,  0x16: 0.001, 0x18: 0.0001,
        0x24: 0.01,  0x26: 10.0,  0x28: 0.0001, 0x2A: 0.001,
    }
    _FALLBACK_UNIT = {
        "VDC": "V",  "VAC": "V",  "ADC": "A",   "AAC": "A",
        "RES": "Ω",  "CONT": "Ω", "CAP": "F",   "FREQ": "Hz",
        "DIODE": "V", "TEMP": "°C",
    }

    # Measurement mode constants
    MODE_DC_VOLTAGE = 1      # DC Voltage
    MODE_AC_VOLTAGE = 2      # AC Voltage
    MODE_DC_CURRENT = 3      # DC Current
    MODE_AC_CURRENT = 4      # AC Current
    MODE_AC_DC_VOLTAGE = 5   # AC+DC Voltage
    MODE_AC_DC_CURRENT = 6   # AC+DC Current
    MODE_RESISTANCE = 7      # Resistance
    MODE_CAPACITANCE = 8     # Capacitance
    MODE_FREQUENCY = 9       # Frequency
    MODE_TEMPERATURE = 10    # Temperature
    MODE_DIODE = 11          # Diode
    MODE_CONTINUITY = 12     # Continuity

    def __init__(self, device_addr: Optional[str] = None, max_retry: int = 3):
        self._device_addr = device_addr
        self._device_name: Optional[str] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Optional[BleakClient] = None
        self._rx_char: Optional[BleakGATTCharacteristic] = None
        self._tx_char: Optional[BleakGATTCharacteristic] = None
        self._response_event = asyncio.Event()
        self._response_data = bytearray()
        self.write_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"
        self.read_uuid = "0000fff2-0000-1000-8000-00805f9b34fb"
        self._task = None
        self._current_data = None
        self._current_unit = ""
        self._current_mode = ""
        self._stop_event = asyncio.Event()
        self._data_update_callback = None
        self._mode = 0
        self._task_state = 0
        self.max_retry = max_retry
        self._cmd_lock = asyncio.Lock()

    async def _resolve_target_device(self) -> Optional[Any]:
        """Resolve the target BLE device by address or by DM40 advertisement hints."""
        # If address is explicitly provided, prefer direct lookup first.
        if self._device_addr:
            by_addr = await BleakScanner.find_device_by_address(
                self._device_addr,
                timeout=self.FAST_ADDR_LOOKUP_TIMEOUT,
            )
            if by_addr:
                return by_addr

        scanned = await BleakScanner.discover(timeout=self.DISCOVERY_TIMEOUT, return_adv=True)
        target_service = self.DM40_SERVICE_UUID.lower()
        requested_addr = self._device_addr.lower() if self._device_addr else None

        # Pass 1: exact address match in scan results.
        if requested_addr:
            for addr, (device, _) in scanned.items():
                if addr.lower() == requested_addr:
                    return device

        # Pass 2: match by DM40 service UUID in advertisement payload.
        for _, (device, adv_data) in scanned.items():
            adv_service_uuids = [
                str(u).lower() for u in (getattr(adv_data, "service_uuids", None) or [])
            ]
            if target_service in adv_service_uuids:
                return device

        # Pass 3: match by known product name hints.
        for _, (device, adv_data) in scanned.items():
            name = getattr(device, "name", None) or getattr(adv_data, "local_name", None) or ""
            if "DM40" in name.upper():
                return device

        return None

    def run(self, loop_ms=1000):
        """Start background task to continuously fetch data"""
        import threading
        if self._loop is None or not self._loop.is_running():
            loop = asyncio.new_event_loop()
            self._loop = loop
            threading.Thread(target=loop.run_forever, daemon=True).start()
        else:
            loop = self._loop

        async def start_operations():
            if self._task_state not in (1,):
                try:
                    await self.connect()
                except Exception as e:
                    self._task_state = -1
                    print(f"Connection failed: {e}")
                    return

            if self._task_state == 0:
                self._stop_event.clear()
                self._task = asyncio.create_task(self._run_task(loop_ms))

        asyncio.run_coroutine_threadsafe(start_operations(), loop)


    def run_coroutine(self, coro: Any) -> Any:
        """Run a coroutine on the device's internal event loop and wait for result."""
        if self._loop is None:
            raise RuntimeError("Device loop is not running. Call run() first.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def set_data_update_callback(self, callback: Callable[[Any, str, str], None]):
        """Set data update callback (data, unit, mode)"""
        self._data_update_callback = callback

    async def _run_task(self, loop_ms=1000):
        """Background task main loop"""
        self._task_state = 1
        while not self._stop_event.is_set():
            try:
                data, unit, mode = await self.get_data()
                # if mode:
                #     self._current_mode = mode
                if data is not None:
                    self._current_data = data
                    self._current_unit = unit
                    self._current_mode = mode
                    if self._data_update_callback:
                        self._data_update_callback(data, unit, mode)
                await asyncio.sleep(loop_ms/1000)
            except Exception as e:
                print(f"Task run error: {e}")
                self._task_state = -1
                await asyncio.sleep(1)
                return
        await self.disconnect()
        self._task_state = 0

    def stop(self):
        """Stop background task"""
        if self._task:
            self._stop_event.set()
            while self._task_state == 1:
                time.sleep(0.1)
        self._task_state = 0

    def get_current_data(self) -> Tuple[Any, str, str]:
        """Get latest data (value, unit, mode)"""
        return self._current_data, self._current_unit, self._current_mode

    def get_state(self) -> int:
        """Get task/connection state: 0=idle/connecting, 1=running, -1=error."""
        return self._task_state

    def is_connected(self) -> bool:
        """Return True if BLE client exists and is connected."""
        return bool(self._client and self._client.is_connected)

    def get_mode(self) -> int:
        """Get currently selected UI mode constant."""
        return self._mode

    def get_device_addr(self) -> Optional[str]:
        """Get the currently resolved device address (if available)."""
        return self._device_addr

    def get_device_name(self) -> Optional[str]:
        """Get the currently resolved device name (if available)."""
        return self._device_name

    async def connect(self) -> bool:
        """Connect to Bluetooth device"""
        retry_count = 0
        while retry_count < self.max_retry:
            try:
                device = await self._resolve_target_device()
                if not device:
                    if self._device_addr:
                        raise Exception(f"Device not found: {self._device_addr}")
                    raise Exception("No DM40 device found by address, service UUID, or name")

                resolved_addr = getattr(device, "address", None) or str(device)
                resolved_name = (getattr(device, "name", None) or "").strip()
                self._device_addr = resolved_addr
                self._device_name = resolved_name or resolved_addr

                print(f"Device found: {resolved_addr}")
                self._client = BleakClient(device)
                print("Connecting:{}".format(resolved_addr))
                await self._client.connect()
                print("Connection successful:{}".format(resolved_addr))

                # Reset resolved characteristics for reconnect attempts.
                self._rx_char = None
                self._tx_char = None

                for service in self._client.services:
                    for char in service.characteristics:
                        uuid = str(char.uuid).lower()
                        if self.read_uuid == uuid:
                            self._rx_char = char
                        if self.write_uuid == uuid:
                            self._tx_char = char

                if not self._rx_char or not self._tx_char:
                    raise Exception("Characteristic not found")

                print("Setting notification:{}".format(self._rx_char.uuid))
                await self._client.start_notify(self._rx_char.uuid, self._notification_handler)
                return True
            except Exception as e:
                retry_count += 1
                print(f"Connection failed (attempt {retry_count}/{self.max_retry}): {e}")
                if retry_count < self.max_retry:
                    await asyncio.sleep(1)
        raise Exception("Maximum retry count reached, connection failed")

    async def disconnect(self):
        """Disconnect Bluetooth connection"""
        if self._client and self._client.is_connected:
            if self._rx_char:
                await self._client.stop_notify(self._rx_char.uuid)
            await self._client.disconnect()

    def _notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        """Receive data callback function"""
        self._response_data.extend(data)
        # Prevent unbounded growth from stray notifications
        if len(self._response_data) > 256:
            self._response_data = self._response_data[-256:]
        self._response_event.set()

    def _extract_measurement_frame(self, payload: bytes) -> Optional[bytes]:
        """Extract the latest full 16-byte measurement frame from notification payload."""
        idx = payload.rfind(self.MEASUREMENT_HEADER)
        if idx < 0:
            return None
        end = idx + self.MEASUREMENT_FRAME_LEN
        if end > len(payload):
            return None
        return payload[idx:end]

    def _decode_mode(self, mode_flag: int) -> Tuple[str, str]:
        """Decode DM40 mode flag to mode kind and UI mode name."""
        vdc_flags = {0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30}
        vac_flags = {0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70}
        vdc_ac_flags = {0x80, 0x88, 0x90, 0x98, 0xA0, 0xA8, 0xB0}
        adc_flags = {0x01, 0x09, 0x11, 0x19, 0x21, 0x29, 0x31, 0x39}
        aac_flags = {0x41, 0x49, 0x51, 0x59, 0x61, 0x69, 0x71, 0x79}
        adc_ac_flags = {0x81, 0x89, 0x91, 0x99, 0xA1, 0xA9, 0xB1, 0xB9}
        resistance_flags = {0x02, 0x0A, 0x12, 0x1A, 0x22, 0x2A, 0x32, 0x42, 0x4A, 0x52, 0x5A, 0x62, 0x6A, 0x72}

        if mode_flag in vdc_flags:
            return "VDC", "DC Voltage"
        if mode_flag in vac_flags:
            return "VAC", "AC Voltage"
        if mode_flag in vdc_ac_flags:
            return "VDC+AC", "AC+DC Voltage"
        if mode_flag in adc_flags:
            return "ADC", "DC Current"
        if mode_flag in aac_flags:
            return "AAC", "AC Current"
        if mode_flag in adc_ac_flags:
            return "ADC+AC", "AC+DC Current"
        if mode_flag in resistance_flags:
            return "RES", "Resistance"
        if mode_flag == 0x03:
            return "CAP", "Capacitance"
        if mode_flag == 0x05:
            return "FREQ", "Frequency"
        if mode_flag == 0x45:
            return "TEMP", "Temperature"
        if mode_flag == 0x04:
            return "DIODE", "Diode"
        if mode_flag == 0x44:
            return "CONT", "Continuity"
        return f"0x{mode_flag:02x}", "Unknown"

    async def write_command(self, cmd: bytes) -> bool:
        """Write a command without waiting for a response (fire-and-forget, for mode switches)"""
        if not self._client or not self._client.is_connected:
            raise Exception("Device not connected")
        if not self._tx_char:
            raise Exception("Write characteristic not initialized")
        await self._client.write_gatt_char(self._tx_char.uuid, cmd, response=False)
        return True

    async def send_command(self, cmd: bytes, timeout: float = 1.0) -> Optional[bytearray]:
        """Send command and wait for response"""
        if not self._client or not self._client.is_connected:
            raise Exception("Device not connected")
        if not self._tx_char:
            raise Exception("Write characteristic not initialized")

        async with self._cmd_lock:
            self._response_data.clear()
            self._response_event.clear()

            await self._client.write_gatt_char(self._tx_char.uuid, cmd)

            try:
                await asyncio.wait_for(self._response_event.wait(), timeout)
                return bytearray(self._response_data)
            except asyncio.TimeoutError:
                print("Waiting for response timed out")
                return None

    def _calculate_checksum(self, cmd_bytes: list) -> int:
        """Calculate checksum as two's-complement of byte sum."""
        return (-sum(cmd_bytes)) & 0xFF

    def _build_mode_command(self, mode_flag: int) -> bytes:
        """Build a mode switch command packet with checksum."""
        prefix = [0xaf, 0x05, 0x03, 0x06, 0x01, mode_flag]
        checksum = self._calculate_checksum(prefix)
        return bytes(prefix + [checksum])

    # ==================== Measurement mode settings ====================

    async def set_dc_voltage_mode(self) -> bool:
        """Set DC voltage mode (DCV)"""
        cmd = self._build_mode_command(0x30)
        await self.write_command(cmd)
        print("Set DC voltage mode")
        return True

    async def set_ac_voltage_mode(self) -> bool:
        """Set AC voltage mode (ACV)"""
        cmd = self._build_mode_command(0x70)
        await self.write_command(cmd)
        print("Set AC voltage mode")
        return True

    async def set_ac_dc_voltage_mode(self) -> bool:
        """Set AC+DC voltage mode"""
        cmd = self._build_mode_command(0xB0)
        await self.write_command(cmd)
        print("Set AC+DC voltage mode")
        return True

    async def set_dc_current_mode(self) -> bool:
        """Set DC current mode (DCA)"""
        cmd = self._build_mode_command(0x39)
        await self.write_command(cmd)
        print("Set DC current mode")
        return True

    async def set_ac_current_mode(self) -> bool:
        """Set AC current mode (ACA)"""
        cmd = self._build_mode_command(0x79)
        await self.write_command(cmd)
        print("Set AC current mode")
        return True

    async def set_ac_dc_current_mode(self) -> bool:
        """Set AC+DC current mode"""
        cmd = self._build_mode_command(0xB9)
        await self.write_command(cmd)
        print("Set AC+DC current mode")
        return True

    async def set_resistance_mode(self) -> bool:
        """Set resistance mode (Ω)"""
        cmd = self._build_mode_command(0x32)
        await self.write_command(cmd)
        print("Set resistance mode")
        return True

    async def set_capacitance_mode(self) -> bool:
        """Set capacitance mode (F)"""
        cmd = self._build_mode_command(0x03)
        await self.write_command(cmd)
        print("Set capacitance mode")
        return True

    async def set_frequency_mode(self) -> bool:
        """Set frequency mode (Hz)"""
        cmd = self._build_mode_command(0x05)
        await self.write_command(cmd)
        print("Set frequency mode")
        return True

    async def set_temperature_mode(self) -> bool:
        """Set temperature mode (°C)"""
        cmd = self._build_mode_command(0x45)
        await self.write_command(cmd)
        print("Set temperature mode")
        return True

    async def set_diode_mode(self) -> bool:
        """Set diode mode"""
        cmd = self._build_mode_command(0x04)
        await self.write_command(cmd)
        print("Set diode mode")
        return True

    async def set_continuity_mode(self) -> bool:
        """Set continuity mode"""
        cmd = self._build_mode_command(0x44)
        await self.write_command(cmd)
        print("Set continuity mode")
        return True

    # ==================== Backward compatibility ====================

    async def set_voltage_mode(self) -> bool:
        """Set voltage mode (default DC, backward compatible with old code)"""
        return await self.set_dc_voltage_mode()

    async def set_current_mode(self) -> bool:
        """Set current mode (default DC, backward compatible with old code)"""
        return await self.set_dc_current_mode()

    # ==================== Data retrieval ====================

    async def get_data(self) -> Tuple[Any, str, str]:
        """
        Get measurement data
        Return: (value, unit, mode)
        """
        cmd = bytes([0xaf, 0x05, 0x03, 0x09, 0x00, 0x40])
        response = await self.send_command(cmd)
        if response is None:
            return None, '', ''

        frame = self._extract_measurement_frame(bytes(response))
        if frame is None:
            return None, '', ''

        if len(frame) >= self.MEASUREMENT_FRAME_LEN:
            mode_flag = frame[5]
            mode_kind, mode = self._decode_mode(mode_flag)

            sign_flag = frame[-8]
            scale_flag = sign_flag & 0xFE
            aux_sign_flag = frame[-7]
            aux_scale_flag = frame[-7] & 0xFE
            sign = -1 if (sign_flag & 0x01) else 1
            aux_sign = -1 if (aux_sign_flag & 0x01) else 1

            # M1 counts are bytes 14 (lo), 15 (hi)
            counts = (frame[15] << 8) | frame[14]

            if counts == 0xFFFF:
                return "OL", "", mode

            scale_info = None
            effective_sign = sign
            if mode_kind == "VDC":
                # On this firmware family, DC voltage sign is carried in aux_sign across ranges.
                effective_sign = aux_sign if aux_sign_flag != 0xFF else sign
                scale_info = self.VDC_MODE_SCALE_MAP.get(mode_flag)
                if scale_info is None:
                    scale_info = self.VDC_SCALE_OVERRIDE_MAP.get(scale_flag, self.ALT_SCALE_MAP.get(scale_flag))
            elif mode_kind in ("VAC", "VDC+AC", "DIODE"):
                if mode_kind == "VDC+AC":
                    effective_sign = aux_sign if aux_sign_flag != 0xFF else sign
                if mode_kind in ("VAC", "VDC+AC") and mode_flag in (0x68, 0x70, 0xA8, 0xB0):
                    scale_info = self.ALT_SCALE_MAP.get(aux_scale_flag)
                    if scale_info is None:
                        scale_info = self.ALT_SCALE_MAP.get(scale_flag)
                else:
                    scale_info = self.ALT_SCALE_MAP.get(scale_flag)
            elif mode_kind in ("ADC", "AAC", "ADC+AC"):
                # Current sign is more reliable in the auxiliary byte on this device.
                effective_sign = aux_sign if aux_sign_flag != 0xFF else sign
                # Prefer explicit current mode flag mapping for fixed ranges.
                scale_info = self.AMP_MODE_SCALE_MAP.get(mode_flag)
                # 10A fixed range reports its effective scale in the auxiliary byte.
                if mode_flag in (0x29, 0x69, 0xA9):
                    aux_scale_info = self.AMP_SCALE_MAP.get(aux_scale_flag)
                    if aux_scale_info is not None:
                        scale_info = aux_scale_info
                # AUTO/AUTO+ variants: effective scale/sign may be in frame[-7].
                if scale_info is None and mode_flag in (0x31, 0x39, 0x71, 0x79, 0xB1, 0xB9):
                    scale_info = self.AMP_SCALE_MAP.get(aux_scale_flag)
                    if scale_info is None:
                        scale_info = self.AMP_SCALE_MAP.get(scale_flag)
                elif scale_info is None:
                    scale_info = self.AMP_SCALE_MAP.get(scale_flag)
            elif mode_kind == "CONT":
                # Continuity should be displayed in ohms, with a fixed 600Ω full-scale.
                # Firmware variants can encode continuity subtype in the auxiliary scale byte.
                scale_info = (600.0, "Ω", 1.0, 2)
            elif mode_kind == "RES":
                # For RES AUTO variants, the effective scale often appears in frame[-7]
                # rather than the sign/scale byte at frame[-8].
                if mode_flag in (0x32, 0x72):
                    scale_info = self.RES_SCALE_MAP.get(aux_scale_flag)
                    if scale_info is None:
                        scale_info = self.RES_SCALE_MAP.get(scale_flag)
                else:
                    scale_info = self.RES_MODE_SCALE_MAP.get(mode_flag)
                    if scale_info is None:
                        scale_info = self.RES_SCALE_MAP.get(scale_flag)
            elif mode_kind == "CAP":
                # For CAP AUTO variants, effective scale is often carried in frame[-7].
                if mode_flag == 0x03:
                    scale_info = self.CAP_SCALE_MAP.get(aux_scale_flag)
                    if scale_info is None:
                        scale_info = self.CAP_SCALE_MAP.get(scale_flag)
                else:
                    scale_info = self.CAP_SCALE_MAP.get(scale_flag)
            elif mode_kind == "FREQ":
                # For FREQ AUTO variants, effective scale is often carried in frame[-7].
                if mode_flag == 0x05:
                    scale_info = self.FREQ_SCALE_MAP.get(aux_scale_flag)
                    if scale_info is None:
                        scale_info = self.FREQ_SCALE_MAP.get(scale_flag)
                else:
                    scale_info = self.FREQ_SCALE_MAP.get(scale_flag)
            elif mode_kind == "TEMP":
                scale_info = (6000.0, "°C", 1.0, 1)

            if scale_info is None:
                # Fallback: use raw multiplier so data always shows.
                mult = self._FALLBACK_MULT.get(scale_flag, 1.0)
                unit = self._FALLBACK_UNIT.get(mode_kind, "")
                result = effective_sign * counts * mult
                print(f"[WARN] Unknown scale_flag 0x{scale_flag:02x} for {mode_kind}, using fallback mult={mult}")
                return round(result, 3), unit, mode

            full_scale, unit, unit_mul, decimals = scale_info
            if mode_kind == "CAP":
                effective_counts = self.DEVICE_COUNTS / 10.0
            elif mode_kind == "CONT":
                # Continuity subtype 0x84 uses a wrapped counter representation.
                # Unwrap by adding the observed firmware wrap offset and convert on 60k span.
                if aux_scale_flag in self.CONTINUITY_ALT_AUX_SCALE_FLAGS:
                    counts += self.CONTINUITY_WRAP_OFFSET
                effective_counts = self.DEVICE_COUNTS
            else:
                effective_counts = self.DEVICE_COUNTS
            result = effective_sign * counts * (full_scale / effective_counts) * unit_mul
            if unit in ("mV", "V", "uA", "mA", "A", "Ω", "kΩ", "MΩ", "Hz", "kHz", "MHz", "nF", "uF", "mF", "F", "°C", "°F"):
                return f"{result:.{decimals}f}", unit, mode
            return round(result, decimals), unit, mode

        return None, '', ''

    # ==================== Custom commands ====================

    async def send_custom_command(self, cmd_bytes: list) -> Tuple[Optional[bytearray], str]:
        """
        Send custom command for experimentation and debugging
        Args: cmd_bytes - command byte list, e.g., [0xaf, 0x05, 0x03, 0x06, 0x01, 0x30, 0x12]
        Return: (response, hex_string)
        """
        cmd = bytes(cmd_bytes)
        print(f"Sending custom command: {cmd.hex()}")
        response = await self.send_command(cmd)
        if response:
            return response, response.hex()
        return None, ""

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    def set_mode(self, mode: int):
        """Set mode and send BLE command to the device."""
        self._mode = mode
        mode_map = {
            self.MODE_DC_VOLTAGE:   self.set_dc_voltage_mode,
            self.MODE_AC_VOLTAGE:   self.set_ac_voltage_mode,
            self.MODE_AC_DC_VOLTAGE: self.set_ac_dc_voltage_mode,
            self.MODE_DC_CURRENT:   self.set_dc_current_mode,
            self.MODE_AC_CURRENT:   self.set_ac_current_mode,
            self.MODE_AC_DC_CURRENT: self.set_ac_dc_current_mode,
            self.MODE_RESISTANCE:   self.set_resistance_mode,
            self.MODE_CAPACITANCE:  self.set_capacitance_mode,
            self.MODE_FREQUENCY:    self.set_frequency_mode,
            self.MODE_TEMPERATURE:  self.set_temperature_mode,
            self.MODE_DIODE:        self.set_diode_mode,
            self.MODE_CONTINUITY:   self.set_continuity_mode,
        }
        setter = mode_map.get(mode)
        if setter:
            self.run_coroutine(setter())


if __name__ == "__main__":
    import time

    def update_display(data, unit, mode):
        print(f"[{mode}] Data: {data} {unit}")

    device = Com_DM40()
    device.set_data_update_callback(update_display)
    device.run(200)

    print("Waiting for connection...")
    try:
        while device.get_state() != 1:
            if device.get_state() == -1:
                print("Connection failed, exiting")
                exit(1)
            time.sleep(0.5)

        print("Connection successful! Starting measurement mode tests...")
        print("\n=== DM40 Measurement Mode Tests ===")

        # Test various modes
        modes = [
            ("DC Voltage", device.set_dc_voltage_mode),
            ("AC Voltage", device.set_ac_voltage_mode),
            ("DC Current", device.set_dc_current_mode),
            ("AC Current", device.set_ac_current_mode),
            ("Resistance", device.set_resistance_mode),
            ("Capacitance", device.set_capacitance_mode),
            ("Frequency", device.set_frequency_mode),
            ("Temperature", device.set_temperature_mode),
            ("Diode", device.set_diode_mode),
            ("Continuity", device.set_continuity_mode),
        ]

        for name, mode_func in modes:
            print(f"\n--- Switching to {name} mode ---")
            device.run_coroutine(mode_func())
            time.sleep(2)  # Wait for data to stabilize

        print("\nTest completed, continuing to read data...")

        # Continue reading data
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nManually stopped")
        device.stop()
        print("Finished")
