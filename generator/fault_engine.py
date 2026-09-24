"""
Deterministic fault injection, decoy generation, and scenario timeline per team seed.
"""
import math
import random
import numpy as np
from datetime import timedelta
from config import MISSION_EPOCH, ORBIT_PERIOD_S, SUNLIT_DURATION_S, ECLIPSE_DURATION_S
from generator.telemetry_model import (
    SpacecraftState, pack_frame, bat_v_to_raw, raw_to_bat_v
)
from crypto_utils import crc16_ccitt_false

class MissionScenario:
    def __init__(self, team_id: int, seed: int):
        self.team_id = team_id
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        
        # Clock oscillator drift: 40 to 90 ppm fast
        self.drift_ppm = 40.0 + (seed % 51) + (self.rng.uniform(0.0, 0.99))
        
        # ---------------------------------------------------------------------
        # Plan Scheduled Events (The "Planned Operations Schedule")
        # ---------------------------------------------------------------------
        # 1. Planned Safe Mode 1
        psm1_start = 11400 + int(self.rng.randint(-300, 300))
        psm1_end = psm1_start + 600
        
        # 2. Planned Safe Mode 2
        psm2_start = 33000 + int(self.rng.randint(-300, 300))
        psm2_end = psm2_start + 600
        
        # 3. Planned Payload Window
        payload_start = 18000 + int(self.rng.randint(-300, 300))
        payload_end = payload_start + 1200
        
        # 4. Planned Heater Window (Decoy for F2)
        p_heater_start = 24000 + int(self.rng.randint(-300, 300))
        p_heater_end = p_heater_start + 900
        
        # 5. Planned Ground Station Handovers
        handover_1 = 8100 + int(self.rng.randint(-100, 100))
        handover_2 = 31200 + int(self.rng.randint(-100, 100))
        handover_3 = 65400 + int(self.rng.randint(-100, 100))
        
        self.planned_schedule = [
            {"event": "GROUND_PASS_1", "start_sec": 0, "end_sec": 600, "description": "Pass Station Alpha (GS-1)"},
            {"event": "GS_HANDOVER_1", "start_sec": handover_1, "end_sec": handover_1 + 20, "description": "Station handover GS-1 to GS-2 (gap expected)"},
            {"event": "PLANNED_SAFE_MODE_1", "start_sec": psm1_start, "end_sec": psm1_end, "description": "Planned attitude calibration in Safe Mode"},
            {"event": "PAYLOAD_ACTIVATION", "start_sec": payload_start, "end_sec": payload_end, "description": "Planned Imager / Spectrometer experiment"},
            {"event": "PLANNED_HEATER_OP", "start_sec": p_heater_start, "end_sec": p_heater_end, "description": "Planned thermal conditioning window"},
            {"event": "GS_HANDOVER_2", "start_sec": handover_2, "end_sec": handover_2 + 20, "description": "Station handover GS-2 to GS-3 (gap expected)"},
            {"event": "PLANNED_SAFE_MODE_2", "start_sec": psm2_start, "end_sec": psm2_end, "description": "Planned star tracker gyro alignment in Safe Mode"},
            {"event": "GS_HANDOVER_3", "start_sec": handover_3, "end_sec": handover_3 + 20, "description": "Station handover GS-3 to GS-1 (gap expected)"},
        ]
        
        # ---------------------------------------------------------------------
        # Unplanned Faults (Seeded per team)
        # ---------------------------------------------------------------------
        # Fault 1 (EPS-07): Battery cell degradation during eclipse
        # Orbit selection: orbit 4 (around t = 4 * 5700 + 3600 + offset)
        f1_orbit = 4
        f1_eclipse_start = f1_orbit * ORBIT_PERIOD_S + SUNLIT_DURATION_S
        f1_offset = 300 + int(self.rng.randint(50, 400)) # Inside eclipse
        self.f1_onset_sec = f1_eclipse_start + f1_offset
        self.f1_orbit = f1_orbit
        self.f1_eclipse_end_sec = (f1_orbit + 1) * ORBIT_PERIOD_S
        
        # Fault 2 (THM-03): Unplanned Heater Stuck ON
        # Around orbit 7 (t ≈ 41000..44000s), definitely not in planned schedule
        self.f2_onset_sec = 41500 + int(self.rng.randint(0, 1200))
        self.f2_duration_sec = 2400 # 40 minutes stuck on
        
        # Fault 3 (ADCS-02 Cascade): Wheel 2 freeze -> Gyro Z step -> Bus dip & OBC reset
        # Around orbit 10 (t ≈ 57000..60000s)
        self.f3_onset_sec = 57600 + int(self.rng.randint(0, 1000))
        self.f3_gyro_step_sec = self.f3_onset_sec + 150
        self.f3_obc_reset_sec = self.f3_onset_sec + 350
        
        # Fault 4 (COM-04): Single Bit Flip in exactly one frame
        # Around orbit 12 (t ≈ 70000..75000s)
        self.f4_target_sec = 71200 + int(self.rng.randint(50, 2000))
        # Choose to flip a bit in battery voltage raw high byte (byte 12) or low byte (byte 13)
        # We will flip bit 3 of byte 13
        self.f4_byte_index = 13
        self.f4_bit_in_byte = int(self.rng.choice([1, 2, 3, 4]))
        self.f4_global_bit_index = self.f4_byte_index * 8 + self.f4_bit_in_byte
        
        # Multi-bit unrecoverable corruptions (decoys)
        self.decoy_corrupt_sec_1 = 15320 + int(self.rng.randint(0, 500))
        self.decoy_corrupt_sec_2 = 48750 + int(self.rng.randint(0, 500))

    def get_frame(self, t_sec: int) -> bytes:
        """Generates the true or faulted 44-byte frame for second t_sec."""
        state = SpacecraftState(t_sec, self.seed, self.drift_ppm)
        
        # Apply Scheduled Events
        for event in self.planned_schedule:
            if event["start_sec"] <= t_sec < event["end_sec"]:
                if "SAFE_MODE" in event["event"]:
                    state.mode = 0
                    state.flags |= 0x01 # cmd_ack set
                elif "PAYLOAD" in event["event"]:
                    state.mode = 2
                    state.flags |= 0x04 # payload_on
                    state.temp_obc_c += 3.2
                    state.bat_i_mA -= 300
                elif "HEATER" in event["event"]:
                    state.flags |= 0x02 # heater_on
                    state.bat_i_mA -= 250
                    state.temp_bat_c += 4.0
        
        # Apply Fault 1 (EPS-07): -150 mV battery step down from onset onwards
        if t_sec >= self.f1_onset_sec:
            state.bat_v_mV -= 150.0
            
        # Apply Fault 2 (THM-03): Unplanned Heater ON (bit 1 set, temp rises)
        if self.f2_onset_sec <= t_sec < (self.f2_onset_sec + self.f2_duration_sec):
            state.flags |= 0x02 # heater_on
            state.bat_i_mA -= 250
            # Heating ramp +0.5°C/min
            mins_elapsed = (t_sec - self.f2_onset_sec) / 60.0
            temp_rise = min(12.0, mins_elapsed * 0.5)
            state.temp_bat_c += temp_rise
            state.temp_obc_c += temp_rise * 0.4
            
        # Apply Fault 3 (ADCS-02 Cascade)
        if t_sec >= self.f3_onset_sec:
            if t_sec < self.f3_gyro_step_sec:
                # Stage 1: Wheel 2 RPM freezes completely (zero variance)
                state.wheel_rpm[1] = 3125
            elif t_sec < self.f3_obc_reset_sec:
                # Stage 2: Wheel 2 frozen AND Gyro Z steps up (+45.00 deg/s = 4500 raw)
                state.wheel_rpm[1] = 3125
                state.gyro_raw[2] = 4500
                # Bus voltage begins to dip slightly before reset
                if t_sec >= self.f3_obc_reset_sec - 10:
                    state.bus_v_mV = 4410.0
            else:
                # Stage 3: OBC Reset has triggered!
                state.reset_count = 1
                state.mode = 0 # Safe Mode
                # Reset counters restart from 0 at the reset moment
                post_reset_s = t_sec - self.f3_obc_reset_sec
                ticks_post = int(round(post_reset_s * 10.0 * (1.0 + self.drift_ppm / 1.0e6)))
                state.obc_tick16 = ticks_post % 65536
                state.seq_num = post_reset_s % 65536
                state.wheel_rpm[1] = 0 # Powered down in safe mode
                state.gyro_raw[2] = 12 # Settling
        
        # Pack to 44 bytes
        frame_bytes = pack_frame(state)
        
        # Fault 4 (COM-04): Single Bit Flip
        if t_sec == self.f4_target_sec:
            # Store original uncorrupted battery voltage for challenge C3.3 answer
            self.f4_original_bat_v_mV = state.bat_v_mV
            self.f4_frame_reset_cnt = state.reset_count
            self.f4_frame_seq = state.seq_num
            
            # Flip bit
            ba = bytearray(frame_bytes)
            ba[self.f4_byte_index] ^= (1 << self.f4_bit_in_byte)
            # DO NOT recompute CRC!
            frame_bytes = bytes(ba)
            
        # Decoy Multi-bit Corruptions
        if t_sec in (self.decoy_corrupt_sec_1, self.decoy_corrupt_sec_2):
            ba = bytearray(frame_bytes)
            ba[14] ^= 0xFF
            ba[15] ^= 0xAA
            ba[25] ^= 0x55
            frame_bytes = bytes(ba)
            
        return frame_bytes

    def get_f1_post_eclipse_bat_v(self) -> float:
        """Returns the battery voltage at the end of the F1 eclipse (second f1_eclipse_end_sec)."""
        st = SpacecraftState(self.f1_eclipse_end_sec, self.seed, self.drift_ppm)
        st.bat_v_mV -= 150.0
        return st.bat_v_mV
