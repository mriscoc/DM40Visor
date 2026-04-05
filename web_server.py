"""
DM40 Bluetooth Multimeter Real-time Data Web Server
Supports multiple measurement modes: DC/AC voltage, DC/AC current, resistance, capacitance, frequency, temperature, etc.
"""
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import threading
import time
from dm40ble import Com_DM40

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dm40-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
dm40_device = None
last_device_addr = None
current_data = {"value": None, "unit": "", "mode": "", "status": "disconnected", "device_name": "DM40"}


def data_update_callback(data, unit, mode):
    """Data update callback function"""
    global current_data
    current_data["value"] = data
    current_data["unit"] = unit
    current_data["mode"] = mode
    current_data["status"] = "connected"
    # Push data to frontend via WebSocket
    socketio.emit('data_update', {
        'value': data,
        'unit': unit,
        'mode': mode,
        'status': 'connected',
        'timestamp': time.time()
    })


def monitor_connection_state(poll_s=0.2):
    """Track connection state and publish status transitions."""
    global dm40_device, current_data, last_device_addr
    last_status = None
    while True:
        if dm40_device is None:
            return

        state = dm40_device.get_state()
        connected = dm40_device.is_connected()

        if state == -1:
            status = "error"
        elif state == 1 or connected:
            status = "connected"
            # Cache resolved address for fast reconnect on next connect request.
            resolved_addr = dm40_device.get_device_addr()
            if resolved_addr:
                last_device_addr = resolved_addr
            current_data["device_name"] = dm40_device.get_device_name() or resolved_addr or "DM40"
        else:
            status = "connecting"

        if status != last_status:
            current_data["status"] = status
            socketio.emit('status_update', {
                'status': status,
                'device_name': current_data.get('device_name', 'DM40'),
                'timestamp': time.time()
            })
            last_status = status

            if status == "error":
                return

        time.sleep(poll_s)


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current status API"""
    return jsonify(current_data)


@app.route('/api/connect', methods=['POST'])
def connect_device():
    """Connect device"""
    global dm40_device, current_data, last_device_addr
    try:
        if dm40_device is None:
            dm40_device = Com_DM40(device_addr=last_device_addr)
            dm40_device.set_data_update_callback(data_update_callback)
            dm40_device.run(200)
            current_data["status"] = "connecting"
            socketio.emit('status_update', {
                'status': 'connecting',
                'device_name': current_data.get('device_name', 'DM40'),
                'timestamp': time.time()
            })
            threading.Thread(target=monitor_connection_state, daemon=True).start()
        return jsonify({'status': 'ok', 'message': 'Device connecting...'})
    except Exception as e:
        current_data["status"] = "error"
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/disconnect', methods=['POST'])
def disconnect_device():
    """Disconnect device"""
    global dm40_device, current_data
    try:
        if dm40_device:
            dm40_device.stop()
            dm40_device = None
        current_data = {"value": None, "unit": "", "mode": "", "status": "disconnected", "device_name": "DM40"}
        socketio.emit('status_update', {
            'status': 'disconnected',
            'device_name': 'DM40',
            'timestamp': time.time()
        })
        return jsonify({'status': 'ok', 'message': 'Disconnected'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _emit_mode_update(mode_name):
    current_data["mode"] = mode_name
    socketio.emit('mode_update', {'mode': mode_name})


# ==================== Voltage mode ====================

@app.route('/api/mode/dc_voltage', methods=['POST'])
def set_dc_voltage_mode():
    """Set DC voltage mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_DC_VOLTAGE)
            _emit_mode_update('DC Voltage')
            return jsonify({'status': 'ok', 'message': 'Switched to DC voltage mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/ac_voltage', methods=['POST'])
def set_ac_voltage_mode():
    """Set AC voltage mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_AC_VOLTAGE)
            _emit_mode_update('AC Voltage')
            return jsonify({'status': 'ok', 'message': 'Switched to AC voltage mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/ac_dc_voltage', methods=['POST'])
def set_ac_dc_voltage_mode():
    """Set AC+DC voltage mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_AC_DC_VOLTAGE)
            _emit_mode_update('AC+DC Voltage')
            return jsonify({'status': 'ok', 'message': 'Switched to AC+DC voltage mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Current mode ====================

@app.route('/api/mode/dc_current', methods=['POST'])
def set_dc_current_mode():
    """Set DC current mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_DC_CURRENT)
            _emit_mode_update('DC Current')
            return jsonify({'status': 'ok', 'message': 'Switched to DC current mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/ac_current', methods=['POST'])
def set_ac_current_mode():
    """Set AC current mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_AC_CURRENT)
            _emit_mode_update('AC Current')
            return jsonify({'status': 'ok', 'message': 'Switched to AC current mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/ac_dc_current', methods=['POST'])
def set_ac_dc_current_mode():
    """Set AC+DC current mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_AC_DC_CURRENT)
            _emit_mode_update('AC+DC Current')
            return jsonify({'status': 'ok', 'message': 'Switched to AC+DC current mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Other measurement modes ====================

@app.route('/api/mode/resistance', methods=['POST'])
def set_resistance_mode():
    """Set resistance mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_RESISTANCE)
            _emit_mode_update('Resistance')
            return jsonify({'status': 'ok', 'message': 'Switched to resistance mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/capacitance', methods=['POST'])
def set_capacitance_mode():
    """Set capacitance mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_CAPACITANCE)
            _emit_mode_update('Capacitance')
            return jsonify({'status': 'ok', 'message': 'Switched to capacitance mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/frequency', methods=['POST'])
def set_frequency_mode():
    """Set frequency mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_FREQUENCY)
            _emit_mode_update('Frequency')
            return jsonify({'status': 'ok', 'message': 'Switched to frequency mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/temperature', methods=['POST'])
def set_temperature_mode():
    """Set temperature mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_TEMPERATURE)
            _emit_mode_update('Temperature')
            return jsonify({'status': 'ok', 'message': 'Switched to temperature mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/diode', methods=['POST'])
def set_diode_mode():
    """Set diode mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_DIODE)
            _emit_mode_update('Diode')
            return jsonify({'status': 'ok', 'message': 'Switched to diode mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/mode/continuity', methods=['POST'])
def set_continuity_mode():
    """Set continuity mode"""
    global dm40_device
    try:
        if dm40_device:
            dm40_device.set_mode(Com_DM40.MODE_CONTINUITY)
            _emit_mode_update('Continuity')
            return jsonify({'status': 'ok', 'message': 'Switched to continuity mode'})
        return jsonify({'status': 'error', 'message': 'Device not connected'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== Backward compatible API ====================

@app.route('/api/mode/voltage', methods=['POST'])
def set_voltage_mode():
    """Set voltage mode (backward compatible with old code, default DC)"""
    return set_dc_voltage_mode()


@app.route('/api/mode/current', methods=['POST'])
def set_current_mode():
    """Set current mode (backward compatible with old code, default DC)"""
    return set_dc_current_mode()


# ==================== WebSocket events ====================

@socketio.on('connect')
def handle_connect():
    """WebSocket connection handler"""
    emit('connected', {'data': 'WebSocket connected'})
    emit('status_update', {
        'status': current_data.get('status', 'disconnected'),
        'device_name': current_data.get('device_name', 'DM40'),
        'timestamp': time.time()
    })
    # Send current data
    emit('data_update', current_data)


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket disconnect handler"""
    print('Client disconnected')


if __name__ == '__main__':
    port = 5001
    print("DM40 Web server starting...")
    print("Supported modes: DC/AC/AC+DC voltage, DC/AC/AC+DC current, resistance, capacitance, frequency, temperature, diode, continuity")
    print(f"Please open browser and visit: http://localhost:{port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
