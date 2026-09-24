"""
Live Contingency Finale State Machine Engine.
Simulates real-time spacecraft emergency recovery per team seed.
"""
import time
import json
import math
from datetime import datetime, timezone
from config import MASTER_SECRET
from crypto_utils import generate_flag
from models import get_db_connection

# Team active finale states stored in memory / DB cache
_FINALE_STATES = {}

class TeamFinaleState:
    def __init__(self, team_id: int, seed: int):
        self.team_id = team_id
        self.seed = seed
        self.start_real_time = time.time()
        
        # Seeded scenario
        # Faulted wheel: 1, 2, or 3
        self.faulted_wheel = (seed % 3) + 1
        # Stuck heater: A or B
        self.stuck_heater = "A" if (seed % 2 == 0) else "B"
        
        # Initial Spacecraft Emergency State
        self.mode = "SAFE"                 # "SAFE" (0) or "NOMINAL" (1)
        self.heater_a = "ON" if self.stuck_heater == "A" else "OFF"
        self.heater_b = "ON" if self.stuck_heater == "B" else "OFF"
        
        self.wheel_status = {
            1: "FAULT" if self.faulted_wheel == 1 else "OPERATIONAL",
            2: "FAULT" if self.faulted_wheel == 2 else "OPERATIONAL",
            3: "FAULT" if self.faulted_wheel == 3 else "OPERATIONAL"
        }
        self.wheel_rpm = {
            1: 0 if self.faulted_wheel == 1 else 3200,
            2: 0 if self.faulted_wheel == 2 else 3100,
            3: 0 if self.faulted_wheel == 3 else 3300
        }
        
        self.wheel_reset_timestamp = None
        self.initial_temp_c = 42.0 + (seed % 5) # 42..46 °C
        self.sim_penalty_sec = 0
        self.obc_resets = 0
        self.bus_v_mV = 4980
        self.recovered = False
        self.recovered_at = None

    def get_elapsed_sim_sec(self) -> float:
        real_elapsed = time.time() - self.start_real_time
        return real_elapsed + self.sim_penalty_sec

    def get_battery_temp(self) -> float:
        elapsed_m = self.get_elapsed_sim_sec() / 60.0
        # If stuck heater is still ON, temperature climbs +1.0 °C per sim minute
        heater_is_on = (self.stuck_heater == "A" and self.heater_a == "ON") or \
                       (self.stuck_heater == "B" and self.heater_b == "ON")
        if heater_is_on:
            return round(self.initial_temp_c + (elapsed_m * 1.0), 1)
        else:
            # Cooling down slowly towards 25°C
            return round(max(25.0, self.initial_temp_c - (elapsed_m * 0.4)), 1)

    def process_command(self, cmd_raw: str) -> dict:
        cmd = cmd_raw.strip().upper()
        elapsed_sec = int(self.get_elapsed_sim_sec())
        curr_temp = self.get_battery_temp()
        
        if cmd == "GET_HK" or cmd == "STATUS":
            # Update wheel RPM if recently reset and > 60s passed
            if self.wheel_reset_timestamp:
                time_since_reset = time.time() - self.wheel_reset_timestamp
                if time_since_reset >= 60.0 and self.wheel_status[self.faulted_wheel] == "SPINNING_UP":
                    self.wheel_status[self.faulted_wheel] = "OPERATIONAL"
                    self.wheel_rpm[self.faulted_wheel] = 3150
                    
            lines = [
                f"[SIM T+{elapsed_sec:04d}s] HK TELEMETRY REPORT:",
                f"  SPACECRAFT MODE:    {self.mode}",
                f"  BUS VOLTAGE:        {self.bus_v_mV} mV",
                f"  BATTERY TEMP:       {curr_temp} °C " + ("[WARNING: THERMAL LIMIT EXCEEDED >45°C]" if curr_temp > 45.0 else "[NOMINAL]"),
                f"  HEATER A:           {self.heater_a}",
                f"  HEATER B:           {self.heater_b}",
                f"  WHEEL 1 (X):        {self.wheel_status[1]} (RPM: {self.wheel_rpm[1]})",
                f"  WHEEL 2 (Y):        {self.wheel_status[2]} (RPM: {self.wheel_rpm[2]})",
                f"  WHEEL 3 (Z):        {self.wheel_status[3]} (RPM: {self.wheel_rpm[3]})",
                f"  OBC RESET COUNT:    {self.obc_resets}"
            ]
            return {"success": True, "output": "\n".join(lines)}
            
        elif cmd in ("HEATER A OFF", "HEATER B OFF"):
            target = "A" if "A" in cmd else "B"
            if target == "A":
                self.heater_a = "OFF"
            else:
                self.heater_b = "OFF"
            return {"success": True, "output": f"[SIM T+{elapsed_sec:04d}s] Command ACK: HEATER {target} set to OFF. Thermal load shed."}
            
        elif cmd.startswith("WHEEL") and "RESET" in cmd:
            # Parse wheel index
            try:
                parts = cmd.split()
                w_idx = int(parts[1])
            except Exception:
                return {"success": False, "output": "Syntax Error. Format: WHEEL <1|2|3> RESET"}
                
            if w_idx not in (1, 2, 3):
                return {"success": False, "output": "Invalid wheel index. Valid wheels: 1, 2, 3."}
                
            # Rule 1: If battery temp > 45 °C, high inrush causes brownout!
            if curr_temp > 45.0:
                self.obc_resets += 1
                self.sim_penalty_sec += 300 # 5 minutes penalty
                self.bus_v_mV = 3800
                self.mode = "SAFE"
                return {
                    "success": False,
                    "output": (
                        f"[CRITICAL ERROR T+{elapsed_sec:04d}s] Brownout detected! Inrush current with Bat Temp ({curr_temp}°C > 45°C) "
                        f"caused bus voltage dip to 3800 mV. OBC RESET triggered! +300s sim penalty added. Turn heater off first!"
                    )
                }
                
            # Rule 2: Resetting the wrong wheel causes attitude perturbation penalty!
            if w_idx != self.faulted_wheel:
                self.sim_penalty_sec += 300
                return {
                    "success": False,
                    "output": (
                        f"[ERROR T+{elapsed_sec:04d}s] Reset command sent to healthy Wheel {w_idx}! "
                        f"Wheel de-synced from ADCS bus. ADCS attitude perturbation detected. +300s sim penalty added."
                    )
                }
                
            # Correct wheel reset!
            self.wheel_status[w_idx] = "SPINNING_UP"
            self.wheel_reset_timestamp = time.time()
            return {
                "success": True,
                "output": (
                    f"[SIM T+{elapsed_sec:04d}s] Command ACK: Wheel {w_idx} reset signal sent. "
                    f"Power cycled. Wheel is now SPINNING_UP. (Runbook requires waiting 60s for nominal RPM lock)."
                )
            }
            
        elif cmd.startswith("WAIT"):
            try:
                parts = cmd.split()
                secs = int(parts[1])
                self.sim_penalty_sec += min(300, max(1, secs))
                return {"success": True, "output": f"[SIM T+{elapsed_sec:04d}s] Telemetry timeline advanced by {secs} seconds."}
            except Exception:
                return {"success": False, "output": "Syntax Error. Format: WAIT <seconds>"}
                
        elif cmd == "MODE NOMINAL":
            # Check conditions for Mode Nominal transition
            # 1. Stuck heater must be OFF
            stuck_is_on = (self.stuck_heater == "A" and self.heater_a == "ON") or \
                          (self.stuck_heater == "B" and self.heater_b == "ON")
            if stuck_is_on:
                return {"success": False, "output": "[REJECTED] Cannot enter NOMINAL mode: Stuck heater is still drawing abnormal current!"}
                
            # 2. Wheel must be OPERATIONAL (not FAULT and not still SPINNING_UP)
            if self.wheel_reset_timestamp:
                time_since_reset = time.time() - self.wheel_reset_timestamp
                if time_since_reset < 60.0:
                    return {
                        "success": False,
                        "output": (
                            f"[REJECTED] Cannot enter NOMINAL mode: Wheel {self.faulted_wheel} has only spun up for {int(time_since_reset)}s (<60s required). "
                            f"Runbook Revision 1.2 requires full spin-up verification before mode transition!"
                        )
                    }
                else:
                    self.wheel_status[self.faulted_wheel] = "OPERATIONAL"
                    self.wheel_rpm[self.faulted_wheel] = 3150
                    
            if self.wheel_status[self.faulted_wheel] != "OPERATIONAL":
                return {"success": False, "output": f"[REJECTED] Cannot enter NOMINAL mode: Wheel {self.faulted_wheel} is still in FAULT state!"}
                
            # All conditions met! Spacecraft successfully recovered!
            self.mode = "NOMINAL"
            self.recovered = True
            self.recovered_at = time.time()
            final_flag = generate_flag(MASTER_SECRET, str(self.seed), "FINALE")
            
            # Compute speed bonus: up to +200 points based on elapsed time (under 15 minutes = max bonus)
            speed_bonus = max(0, int(200 - (elapsed_sec / 900.0) * 200))
            
            return {
                "success": True,
                "recovered": True,
                "final_flag": final_flag,
                "speed_bonus": speed_bonus,
                "output": (
                    f"=======================================================================\n"
                    f"[MISSION SUCCESS] RVSAT-1 HAS BEEN RESTORED TO NOMINAL MODE!\n"
                    f"All subsystems green. Attitude locked. Thermal envelope stable.\n"
                    f"FINAL FLIGHT OPERATOR FLAG: {final_flag}\n"
                    f"Speed Bonus Awarded: +{speed_bonus} pts (Sim Elapsed: {elapsed_sec}s)\n"
                    f"======================================================================="
                )
            }
        else:
            return {
                "success": False,
                "output": f"Unknown command: '{cmd}'. Available commands: GET_HK, HEATER A OFF, HEATER B OFF, WHEEL <1|2|3> RESET, WAIT <s>, MODE NOMINAL."
            }

def get_or_create_finale_state(team_id: int, seed: int) -> TeamFinaleState:
    if team_id not in _FINALE_STATES:
        _FINALE_STATES[team_id] = TeamFinaleState(team_id, seed)
    return _FINALE_STATES[team_id]
