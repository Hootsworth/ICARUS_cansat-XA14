"""
Orbit mechanics, spacecraft physics model, sensor baselines, and frame packing.
"""
import math
import struct
import numpy as np
from datetime import datetime, timezone, timedelta
from config import (
    FRAME_SIZE_BYTES, ASM_BYTES, SPACECRAFT_ID,
    ORBIT_PERIOD_S, SUNLIT_DURATION_S, ECLIPSE_DURATION_S,
    MISSION_EPOCH
)
from crypto_utils import crc16_ccitt_false

# -----------------------------------------------------------------------------
# Calibration Formulas (as defined in ICD)
# -----------------------------------------------------------------------------
# Battery Voltage: Eng (mV) = 6000 + 0.05 * raw   => raw = (Eng - 6000) / 0.05
# Bus Voltage:     Eng (mV) = 4500 + 0.04 * raw   => raw = (Eng - 4500) / 0.04
# Temp Battery:    Eng (cC) = raw - 1000          (where 1 cC = 0.01 °C, e.g. 2500 cC = 25.00 °C)
# Temp Panel:      Eng (cC) = raw - 1000
# Temp OBC:        Eng (cC) = raw - 1050 (Revision B offset) or raw - 1000 (Revision A)
# Gyro:            Eng (deg/s) = raw * 0.01

def bat_v_to_raw(mV: float) -> int:
    return max(0, min(65535, int(round((mV - 6000.0) / 0.05))))

def raw_to_bat_v(raw: int) -> float:
    return 6000.0 + 0.05 * raw

def bus_v_to_raw(mV: float) -> int:
    return max(0, min(65535, int(round((mV - 4500.0) / 0.04))))

def raw_to_bus_v(raw: int) -> float:
    return 4500.0 + 0.04 * raw

def temp_c_to_raw(temp_c: float, offset: int = 1000) -> int:
    # 1 °C = 100 cC
    cC = int(round(temp_c * 100.0))
    raw = cC + offset
    return max(-32768, min(32767, raw))

def raw_to_temp_c(raw: int, offset: int = 1000) -> float:
    cC = raw - offset
    return cC / 100.0

# -----------------------------------------------------------------------------
# Spacecraft Telemetry State at second t
# -----------------------------------------------------------------------------
class SpacecraftState:
    def __init__(self, t_sec: int, seed: int, drift_ppm: float):
        self.t_sec = t_sec
        self.seed = seed
        self.drift_ppm = drift_ppm
        
        # Orbit phase: 0..5699 s (0..3599 sunlit, 3600..5699 eclipse)
        self.orbit_phase = t_sec % ORBIT_PERIOD_S
        self.orbit_number = t_sec // ORBIT_PERIOD_S
        self.in_sunlight = (self.orbit_phase < SUNLIT_DURATION_S)
        
        # OBC Clock Simulation
        # 1 Hz sampling with oscillator drift
        # True ticks elapsed = t_sec * 10 * (1 + drift_ppm / 1e6)
        # Uint16 wraps every 6553.6 s (65536 ticks)
        ticks_total = int(round(t_sec * 10.0 * (1.0 + drift_ppm / 1.0e6)))
        self.obc_tick16 = ticks_total % 65536
        
        # Sequence counter wraps at 65536
        self.seq_num = t_sec % 65536
        
        # Subsystem defaults (Mode 1: Nominal)
        self.frame_type = 0x01   # 0x01 HK, 0x02 TIME_SYNC
        self.mode = 1            # 0 Safe, 1 Nominal, 2 Payload, 3 Detumble
        self.reset_count = 0
        self.flags = 0           # bit0: cmd_ack, bit1: heater_on, bit2: payload_on
        
        # Baselines
        rng = np.random.RandomState((seed * 1000003 + t_sec) & 0xFFFFFFFF)
        
        # Solar Current (mA)
        if self.in_sunlight:
            # Sinusoidal shape across sunlight window
            sun_angle = math.pi * (self.orbit_phase / SUNLIT_DURATION_S)
            self.solar_i_mA = int(max(0, 1800 * math.sin(sun_angle) + rng.normal(0, 15)))
        else:
            self.solar_i_mA = max(0, int(rng.normal(2, 1)))
            
        # Battery Current (mA): positive = charging, negative = discharging
        # Base load = ~350 mA nominal, +300 mA payload, +250 mA heater
        base_load = 350.0 + rng.normal(0, 5)
        self.bat_i_mA = int(self.solar_i_mA - base_load)
        
        # Battery Voltage (mV)
        # Nominal ~8100 mV in sunlight, drops to ~7700 mV in eclipse
        if self.in_sunlight:
            charge_frac = self.orbit_phase / SUNLIT_DURATION_S
            self.bat_v_mV = 7700.0 + 420.0 * (1.0 - math.exp(-charge_frac * 3.0)) + rng.normal(0, 4)
        else:
            eclipse_frac = (self.orbit_phase - SUNLIT_DURATION_S) / ECLIPSE_DURATION_S
            self.bat_v_mV = 8120.0 - 450.0 * (eclipse_frac ** 0.85) + rng.normal(0, 4)
            
        # Bus Voltage (mV): tightly regulated ~5000 mV
        self.bus_v_mV = 5020.0 + rng.normal(0, 3)
        
        # Thermal baseline (°C)
        # Battery: lag on sun exposure, nominal 15..28 °C
        if self.in_sunlight:
            self.temp_bat_c = 15.0 + 12.0 * math.sin(math.pi * (self.orbit_phase / SUNLIT_DURATION_S)) + rng.normal(0, 0.1)
            self.temp_panel_c = 5.0 + 45.0 * math.sin(math.pi * (self.orbit_phase / SUNLIT_DURATION_S)) + rng.normal(0, 0.3)
        else:
            self.temp_bat_c = 22.0 - 7.0 * ((self.orbit_phase - SUNLIT_DURATION_S) / ECLIPSE_DURATION_S) + rng.normal(0, 0.1)
            self.temp_panel_c = -25.0 + 20.0 * math.exp(-(self.orbit_phase - SUNLIT_DURATION_S) / 600.0) + rng.normal(0, 0.3)
            
        self.temp_obc_c = self.temp_bat_c + 4.5 + rng.normal(0, 0.15)
        
        # Wheels RPM (Nominal ~3200, 3100, 3300 RPM)
        self.wheel_rpm = [
            int(3200 + 40 * math.sin(t_sec / 400.0) + rng.normal(0, 3)),
            int(3100 + 35 * math.cos(t_sec / 350.0) + rng.normal(0, 3)),
            int(3300 + 50 * math.sin(t_sec / 500.0) + rng.normal(0, 3))
        ]
        
        # Gyro X, Y, Z (deg/s * 100): small noise around zero in nominal
        self.gyro_raw = [
            int(rng.normal(0, 5)),
            int(rng.normal(0, 5)),
            int(rng.normal(0, 5))
        ]
        
        # RSSI (dBm): Ground pass vs non-pass
        # Ground passes occur periodically
        pass_phase = t_sec % 3000
        if pass_phase < 600:
            # Over ground station: -85 dBm to -65 dBm
            p_frac = pass_phase / 600.0
            self.rssi_dBm = int(-85.0 + 25.0 * math.sin(math.pi * p_frac) + rng.normal(0, 1.5))
        else:
            self.rssi_dBm = int(-115.0 + rng.normal(0, 2))
            
        self.cpu_load = int(max(15, min(85, 28 + 4 * math.sin(t_sec / 120.0) + rng.normal(0, 2))))

# -----------------------------------------------------------------------------
# Binary Frame Packer (44 Bytes)
# -----------------------------------------------------------------------------
def pack_frame(state: SpacecraftState) -> bytes:
    """
    Packs telemetry state into exact 44-byte binary frame per ICD:
    Offset  Size  Field
    0       4     ASM: 1A CF FC E1
    4       2     Spacecraft ID (uint16 big-endian)
    6       2     Sequence (uint16 big-endian)
    8       2     OBC tick (uint16 LITTLE-ENDIAN deliberate trap)
    10      1     Type (0x01 HK, 0x02 TIME_SYNC)
    11      1     Mode (0..3)
    12      2     Battery voltage raw (uint16 big-endian)
    14      2     Battery current mA (int16 big-endian)
    16      2     Solar current mA (uint16 big-endian)
    18      2     Bus voltage raw (uint16 big-endian)
    20      2     Temp battery raw (int16 big-endian)
    22      2     Temp panel raw (int16 big-endian)
    24      2     Temp OBC raw (int16 big-endian)
    26      6     Wheel RPM 1..3 (int16 each big-endian)
    32      6     Gyro X, Y, Z (int16 each big-endian)
    38      1     RSSI (int8)
    39      1     CPU load (uint8)
    40      1     Reset count (uint8)
    41      1     Flags (uint8)
    42      2     CRC-16/CCITT-FALSE (uint16 big-endian over bytes 4..41)
    """
    bat_v_raw = bat_v_to_raw(state.bat_v_mV)
    bus_v_raw = bus_v_to_raw(state.bus_v_mV)
    temp_bat_raw = temp_c_to_raw(state.temp_bat_c, offset=1000)
    temp_panel_raw = temp_c_to_raw(state.temp_panel_c, offset=1000)
    temp_obc_raw = temp_c_to_raw(state.temp_obc_c, offset=1050) # Rev B in ICD
    
    # Bytes 4..41 (38 bytes)
    # Note: OBC tick at offset 8 (relative to frame) = offset 4 in payload -> pack with '<H'
    header_part1 = struct.pack(">HH", SPACECRAFT_ID, state.seq_num) # 4 bytes (offset 4..7)
    tick_part = struct.pack("<H", state.obc_tick16)                  # 2 bytes (offset 8..9) - LITTLE ENDIAN!
    header_part2 = struct.pack(">BB", state.frame_type, state.mode)  # 2 bytes (offset 10..11)
    
    if state.frame_type == 0x02: # TIME_SYNC frame
        # Bytes 12..15 hold UTC unix seconds (uint32 big-endian), rest zero
        sync_epoch_unix = int((MISSION_EPOCH + timedelta(seconds=state.t_sec)).timestamp())
        payload_data = struct.pack(">I", sync_epoch_unix) + (b'\x00' * 26)
    else:
        payload_data = struct.pack(
            ">HhHHhhh3h3hbBBB",
            bat_v_raw,
            state.bat_i_mA,
            max(0, state.solar_i_mA),
            bus_v_raw,
            temp_bat_raw,
            temp_panel_raw,
            temp_obc_raw,
            state.wheel_rpm[0],
            state.wheel_rpm[1],
            state.wheel_rpm[2],
            state.gyro_raw[0],
            state.gyro_raw[1],
            state.gyro_raw[2],
            state.rssi_dBm,
            state.cpu_load,
            state.reset_count,
            state.flags
        )
    
    body = header_part1 + tick_part + header_part2 + payload_data
    calc_crc = crc16_ccitt_false(body)
    crc_bytes = struct.pack(">H", calc_crc)
    
    return ASM_BYTES + body + crc_bytes
