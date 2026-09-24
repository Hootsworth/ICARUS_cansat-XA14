"""
Reference Frame Decoder Library for RVSAT-1 44-Byte Telemetry Frames.
"""
import struct
from datetime import datetime, timezone, timedelta
from config import MISSION_EPOCH
from crypto_utils import crc16_ccitt_false

# Calibration formulas per ICD
def decode_frame(frame_bytes: bytes):
    """
    Decodes a single 44-byte binary telemetry frame.
    Returns a dictionary of parsed telemetry parameters or None if ASM invalid.
    """
    if len(frame_bytes) != 44:
        return None
    
    # 0..3: ASM
    asm = frame_bytes[0:4]
    if asm != b'\x1a\xcf\xfc\xe1':
        return None
        
    # Check CRC (Bytes 4..41 vs Bytes 42..43)
    expected_crc = struct.unpack(">H", frame_bytes[42:44])[0]
    calculated_crc = crc16_ccitt_false(frame_bytes[4:42])
    crc_valid = (expected_crc == calculated_crc)
    
    # 4..5: Spacecraft ID
    sc_id = struct.unpack(">H", frame_bytes[4:6])[0]
    
    # 6..7: Sequence Counter
    seq_num = struct.unpack(">H", frame_bytes[6:8])[0]
    
    # 8..9: OBC Tick (0.1s) - LITTLE ENDIAN!
    obc_tick16 = struct.unpack("<H", frame_bytes[8:10])[0]
    
    # 10..11: Type & Mode
    frame_type = frame_bytes[10]
    mode = frame_bytes[11]
    
    if frame_type == 0x02: # TIME_SYNC
        unix_sec = struct.unpack(">I", frame_bytes[12:16])[0]
        sync_utc = datetime.fromtimestamp(unix_sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "crc_valid": crc_valid,
            "sc_id": sc_id,
            "seq_num": seq_num,
            "obc_tick16": obc_tick16,
            "frame_type": frame_type,
            "frame_type_name": "TIME_SYNC",
            "mode": mode,
            "sync_unix_sec": unix_sec,
            "sync_utc": sync_utc,
            "raw_bytes": frame_bytes
        }
        
    # Standard HK Telemetry (0x01)
    bat_v_raw = struct.unpack(">H", frame_bytes[12:14])[0]
    bat_v_mV = 6000.0 + 0.05 * bat_v_raw
    
    bat_i_mA = struct.unpack(">h", frame_bytes[14:16])[0]
    solar_i_mA = struct.unpack(">H", frame_bytes[16:18])[0]
    
    bus_v_raw = struct.unpack(">H", frame_bytes[18:20])[0]
    bus_v_mV = 4500.0 + 0.04 * bus_v_raw
    
    temp_bat_raw = struct.unpack(">h", frame_bytes[20:22])[0]
    temp_bat_c = (temp_bat_raw - 1000) / 100.0
    
    temp_panel_raw = struct.unpack(">h", frame_bytes[22:24])[0]
    temp_panel_c = (temp_panel_raw - 1000) / 100.0
    
    temp_obc_raw = struct.unpack(">h", frame_bytes[24:26])[0]
    temp_obc_c = (temp_obc_raw - 1050) / 100.0  # Rev B offset 1050
    
    w1, w2, w3 = struct.unpack(">3h", frame_bytes[26:32])
    gx, gy, gz = struct.unpack(">3h", frame_bytes[32:38])
    gyro_x_dps = gx * 0.01
    gyro_y_dps = gy * 0.01
    gyro_z_dps = gz * 0.01
    
    rssi = struct.unpack(">b", frame_bytes[38:39])[0]
    cpu_load = frame_bytes[39]
    reset_cnt = frame_bytes[40]
    flags = frame_bytes[41]
    
    cmd_ack = bool(flags & 0x01)
    heater_on = bool(flags & 0x02)
    payload_on = bool(flags & 0x04)
    
    return {
        "crc_valid": crc_valid,
        "sc_id": sc_id,
        "seq_num": seq_num,
        "obc_tick16": obc_tick16,
        "frame_type": frame_type,
        "frame_type_name": "HK",
        "mode": mode,
        "bat_v_raw": bat_v_raw,
        "bat_v_mV": bat_v_mV,
        "bat_i_mA": bat_i_mA,
        "solar_i_mA": solar_i_mA,
        "bus_v_raw": bus_v_raw,
        "bus_v_mV": bus_v_mV,
        "temp_bat_c": temp_bat_c,
        "temp_panel_c": temp_panel_c,
        "temp_obc_c": temp_obc_c,
        "wheel_rpm_1": w1,
        "wheel_rpm_2": w2,
        "wheel_rpm_3": w3,
        "gyro_x_dps": gyro_x_dps,
        "gyro_y_dps": gyro_y_dps,
        "gyro_z_dps": gyro_z_dps,
        "rssi_dBm": rssi,
        "cpu_load": cpu_load,
        "reset_count": reset_cnt,
        "flags": flags,
        "cmd_ack": cmd_ack,
        "heater_on": heater_on,
        "payload_on": payload_on,
        "raw_bytes": frame_bytes
    }

def parse_frames_stream(data_bytes: bytes):
    """Parses all 44-byte frames from a raw byte stream."""
    frames = []
    i = 0
    while i <= len(data_bytes) - 44:
        if data_bytes[i:i+4] == b'\x1a\xcf\xfc\xe1':
            fr = decode_frame(data_bytes[i:i+44])
            if fr:
                frames.append(fr)
            i += 44
        else:
            i += 1
    return frames
