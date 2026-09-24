"""
Master Data and Scenario Generator for the Satellite Telemetry Challenge.
Generates all 11 teams' data packages, encrypted zip archives, beacon files,
sample dumps, uplink logs, answers, and printable Round 1 sheets.
"""
import os
import json
import csv
import struct
import numpy as np
from datetime import datetime, timezone, timedelta
from config import (
    TOTAL_TEAMS, MASTER_SECRET, MISSION_EPOCH, TOTAL_DURATION_S,
    GENERATED_DATA_DIR, TEAMS_DATA_DIR, SERVER_ARCHIVES_DIR, ANSWERS_DIR,
    FRAME_SIZE_BYTES, SPACECRAFT_ID, ASM_BYTES
)
from crypto_utils import (
    generate_flag, generate_team_hmac_keys, compute_command_hmac,
    create_encrypted_zip, crc16_ccitt_false
)
from generator.telemetry_model import (
    SpacecraftState, pack_frame, raw_to_bat_v, raw_to_bus_v,
    raw_to_temp_c, bat_v_to_raw
)
from generator.fault_engine import MissionScenario

def generate_all_teams(num_teams: int = TOTAL_TEAMS, master_secret: str = MASTER_SECRET):
    print(f"[*] Starting generation for {num_teams} teams with Master Secret: {master_secret[:6]}***")
    
    os.makedirs(TEAMS_DATA_DIR, exist_ok=True)
    os.makedirs(SERVER_ARCHIVES_DIR, exist_ok=True)
    os.makedirs(ANSWERS_DIR, exist_ok=True)
    
    master_answers = {}
    teams_metadata = []
    
    for team_id in range(1, num_teams + 1):
        seed = 1000 + team_id * 137
        print(f"  -> Generating Team {team_id:02d} (Seed: {seed})...")
        
        scenario = MissionScenario(team_id, seed)
        team_dir = os.path.join(TEAMS_DATA_DIR, f"team_{team_id:02d}")
        os.makedirs(team_dir, exist_ok=True)
        
        # 1. Generate Full 24h Archive (86,400 seconds)
        archive_path = os.path.join(SERVER_ARCHIVES_DIR, f"team_{team_id:02d}_archive.bin")
        archive_frames = []
        
        beacon_rows = []
        cur_min_frames = []
        
        for t in range(TOTAL_DURATION_S):
            frame = scenario.get_frame(t)
            archive_frames.append(frame)
            cur_min_frames.append((t, frame))
            
            # Beacon aggregation every 60 seconds
            if len(cur_min_frames) == 60:
                minute_idx = t // 60
                min_utc = (MISSION_EPOCH + timedelta(minutes=minute_idx)).strftime("%Y-%m-%dT%H:%M:%SZ")
                
                # Unpack and aggregate valid frames
                valid_bat_v = []
                valid_temp_bat = []
                valid_temp_obc = []
                valid_gyro = []
                valid_rssi = []
                crc_err_count = 0
                
                start_tick = 0
                last_mode = 1
                last_reset_cnt = 0
                
                for idx_in_min, (ft_sec, f_bytes) in enumerate(cur_min_frames):
                    # Check CRC
                    expected_crc = struct.unpack(">H", f_bytes[42:44])[0]
                    calc_crc = crc16_ccitt_false(f_bytes[4:42])
                    
                    # Tick at offset 8 (little endian)
                    tick = struct.unpack("<H", f_bytes[8:10])[0]
                    if idx_in_min == 0:
                        start_tick = tick
                        
                    mode = f_bytes[11]
                    last_mode = mode
                    reset_cnt = f_bytes[40]
                    last_reset_cnt = reset_cnt
                    
                    if expected_crc != calc_crc:
                        crc_err_count += 1
                    else:
                        # Extract valid parameters
                        bat_v_raw = struct.unpack(">H", f_bytes[12:14])[0]
                        bat_v_mV = raw_to_bat_v(bat_v_raw)
                        valid_bat_v.append(bat_v_mV)
                        
                        temp_bat_raw = struct.unpack(">h", f_bytes[20:22])[0]
                        valid_temp_bat.append(raw_to_temp_c(temp_bat_raw, offset=1000) * 100.0) # cC
                        
                        temp_obc_raw = struct.unpack(">h", f_bytes[24:26])[0]
                        valid_temp_obc.append(raw_to_temp_c(temp_obc_raw, offset=1050) * 100.0) # cC
                        
                        gx, gy, gz = struct.unpack(">3h", f_bytes[32:38])
                        valid_gyro.append(max(abs(gx), abs(gy), abs(gz)))
                        
                        rssi = struct.unpack(">b", f_bytes[38:39])[0]
                        valid_rssi.append(rssi)
                
                bat_min = round(min(valid_bat_v)) if valid_bat_v else 0
                bat_mean = round(sum(valid_bat_v) / len(valid_bat_v)) if valid_bat_v else 0
                t_bat_max = round(max(valid_temp_bat)) if valid_temp_bat else 0
                t_obc_max = round(max(valid_temp_obc)) if valid_temp_obc else 0
                gyro_max = max(valid_gyro) if valid_gyro else 0
                rssi_min_val = min(valid_rssi) if valid_rssi else -120
                
                health_bits = 0x01 if crc_err_count == 0 and last_mode != 0 else 0x00
                
                beacon_rows.append({
                    "utc_iso": min_utc,
                    "obc_tick16": start_tick,
                    "mode": last_mode,
                    "bat_v_min_mV": bat_min,
                    "bat_v_mean_mV": bat_mean,
                    "temp_bat_max_cC": t_bat_max,
                    "temp_obc_max_cC": t_obc_max,
                    "gyro_abs_max": gyro_max,
                    "rssi_min": rssi_min_val,
                    "crc_err_cnt": crc_err_count,
                    "reset_cnt": last_reset_cnt,
                    "health_bits": f"0x{health_bits:02X}"
                })
                cur_min_frames = []
        
        # Write full archive
        with open(archive_path, "wb") as f_arch:
            for fr in archive_frames:
                f_arch.write(fr)
                
        # 2. Write Beacon CSV
        beacon_csv_path = os.path.join(team_dir, "beacon.csv")
        with open(beacon_csv_path, "w", newline="", encoding="utf-8") as f_csv:
            writer = csv.DictWriter(f_csv, fieldnames=list(beacon_rows[0].keys()))
            writer.writeheader()
            writer.writerows(beacon_rows)
            
        # 3. Generate Sample Dump (Phase 1)
        # 30-minute window (1800s total window) starting at t = 6200s (just before tick wrap at ~6553.6s)
        # Contains 1 data gap of duration 45s (e.g. t = 6800..6845)
        # Contains 2 bad CRC frames (t = 6400, t = 7500)
        # Contains 3 TIME_SYNC frames (t = 6300, 7000, 7700)
        dump_start_sec = 6200
        dump_end_sec = dump_start_sec + 1800
        gap_start_sec = 6820
        gap_duration = 45
        gap_end_sec = gap_start_sec + gap_duration
        
        sample_dump_bytes = bytearray()
        
        # Calculate rollover timestamp in sample dump:
        # uint16 wraps at 65536 ticks. Ticks = t * 10 * (1 + drift_ppm/1e6).
        # t_wrap = 65536 / (10 * (1 + drift_ppm/1e6))
        exact_wrap_sec = int(round(65536.0 / (10.0 * (1.0 + scenario.drift_ppm / 1.0e6))))
        wrap_utc_iso = (MISSION_EPOCH + timedelta(seconds=exact_wrap_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        gap_start_utc_iso = (MISSION_EPOCH + timedelta(seconds=gap_start_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        dump_start_utc_iso = (MISSION_EPOCH + timedelta(seconds=dump_start_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        for t_s in range(dump_start_sec, dump_end_sec):
            # Skip frames in data gap
            if gap_start_sec <= t_s < gap_end_sec:
                continue
            
            # Base state
            st = SpacecraftState(t_s, seed, scenario.drift_ppm)
            
            # TIME_SYNC frames
            if t_s in (6300, 7000, 7700):
                st.frame_type = 0x02
                
            fr_bytes = pack_frame(st)
            
            # Inject corrupted CRC frames in sample dump
            if t_s in (6400, 7500):
                ba = bytearray(fr_bytes)
                ba[43] ^= 0xFF
                fr_bytes = bytes(ba)
                
            sample_dump_bytes.extend(fr_bytes)
            
        sample_dump_path = os.path.join(team_dir, "sample_dump.bin")
        with open(sample_dump_path, "wb") as f_sd:
            f_sd.write(sample_dump_bytes)
            
        # 4. Generate Planned Operations Schedule CSV
        planned_sched_path = os.path.join(team_dir, "planned_schedule.csv")
        sched_rows = []
        for ev in scenario.planned_schedule:
            st_iso = (MISSION_EPOCH + timedelta(seconds=ev["start_sec"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            end_iso = (MISSION_EPOCH + timedelta(seconds=ev["end_sec"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            sched_rows.append({
                "event_id": ev["event"],
                "start_utc": st_iso,
                "end_utc": end_iso,
                "duration_s": ev["end_sec"] - ev["start_sec"],
                "description": ev["description"]
            })
        with open(planned_sched_path, "w", newline="", encoding="utf-8") as f_sc:
            writer = csv.DictWriter(f_sc, fieldnames=list(sched_rows[0].keys()))
            writer.writeheader()
            writer.writerows(sched_rows)
            
        # 5. Generate Uplink Log (Bonus Track)
        hmac_full, hmac_part_a, hmac_part_b = generate_team_hmac_keys(master_secret, str(seed))
        uplink_rows = []
        for i in range(1, 26):
            cmd_id = f"CMD-{1000 + i}"
            counter = i
            payload = f"SUBSYS_CONFIG_REG_{i:02X}"
            
            # Forged signature at command 14
            if i == 14:
                hmac_val = "E4A901F8BC293810"
                forged_cmd_id = cmd_id
            # Replayed counter at command 19 (replays counter 18)
            elif i == 19:
                counter = 18
                hmac_val = compute_command_hmac(hmac_full, cmd_id, counter, payload)
                replayed_cmd_id = cmd_id
            else:
                hmac_val = compute_command_hmac(hmac_full, cmd_id, counter, payload)
                
            uplink_rows.append({
                "command_id": cmd_id,
                "counter": counter,
                "payload": payload,
                "hmac_sha256_16": hmac_val
            })
            
        uplink_csv_path = os.path.join(team_dir, "uplink_log.csv")
        with open(uplink_csv_path, "w", newline="", encoding="utf-8") as f_up:
            writer = csv.DictWriter(f_up, fieldnames=list(uplink_rows[0].keys()))
            writer.writeheader()
            writer.writerows(uplink_rows)
            
        # 6. Generate Flags & Keys
        flag_p1 = generate_flag(master_secret, str(seed), "PHASE_1")
        flag_p2 = generate_flag(master_secret, str(seed), "PHASE_2")
        flag_p3 = generate_flag(master_secret, str(seed), "PHASE_3")
        flag_finale = generate_flag(master_secret, str(seed), "FINALE")
        
        launch_auth_code = f"AUTH-RV{seed % 899 + 100}"
        api_token = f"rvsat_tok_{team_id:02d}_{seed}"
        
        # Save API token to text file for package
        api_token_path = os.path.join(team_dir, "api_token.txt")
        with open(api_token_path, "w") as f_tok:
            f_tok.write(f"TEAM_ID={team_id}\nAPI_TOKEN={api_token}\nBASE_URL=http://localhost:8000\n")
            
        # 7. Create Encrypted Phase Packages (Chained)
        packages_dir = os.path.join(team_dir, "packages")
        os.makedirs(packages_dir, exist_ok=True)
        
        # Phase 1 package (unencrypted or password = launch_auth_code)
        p1_files = {
            "sample_dump.bin": bytes(sample_dump_bytes),
            "README_PHASE1.txt": (
                f"=== RVSAT-1 MISSION CONTROL: PHASE 1 SIGNAL ACQUISITION ===\n"
                f"Team ID: {team_id:02d} | Spacecraft ID: 0x4256\n\n"
                f"Tasks:\n"
                f"1. Decode the 44-byte binary telemetry frames in sample_dump.bin.\n"
                f"2. Validate CRC-16/CCITT-FALSE on each frame (bytes 4..41).\n"
                f"3. Determine the oscillator drift rate in PPM (C1.1).\n"
                f"4. Detect the telemetry drop gap (C1.2).\n"
                f"5. Locate the exact timestamp of uint16 tick rollover (C1.3).\n\n"
                f"Submit answers on the Dashboard to earn Phase 1 Flag and decrypt Phase 2 Package!\n"
            )
        }
        create_encrypted_zip(
            os.path.join(packages_dir, f"team_{team_id:02d}_phase1.zip"),
            p1_files,
            password=launch_auth_code
        )
        
        # Phase 2 package (Password = flag_p1)
        with open(beacon_csv_path, "rb") as f_b, open(planned_sched_path, "rb") as f_ps, open(uplink_csv_path, "rb") as f_ul, open(api_token_path, "rb") as f_tk:
            beacon_data = f_b.read()
            sched_data = f_ps.read()
            uplink_data = f_ul.read()
            token_data = f_tk.read()
            
        p2_files = {
            "beacon.csv": beacon_data,
            "planned_schedule.csv": sched_data,
            "api_token.txt": token_data,
            "uplink_log.csv": uplink_data,
            "README_PHASE2.txt": (
                f"=== RVSAT-1 MISSION CONTROL: PHASE 2 DOWNLINK INVESTIGATION ===\n"
                f"Team ID: {team_id:02d} | 12 Downlink Credits Available\n\n"
                f"Investigate the 24-hour beacon telemetry alongside your Planned Operations Schedule.\n"
                f"Fetch high-rate 10-minute passes via POST /api/pass {{\"start_utc\": \"...\"}} with your API token.\n"
                f"Identify faults F1, F2, F3, F4, their exact onset times, and ICD fault codes.\n"
            )
        }
        create_encrypted_zip(
            os.path.join(packages_dir, f"team_{team_id:02d}_phase2.zip"),
            p2_files,
            password=flag_p1
        )
        
        # Phase 3 package (Password = flag_p2)
        p3_files = {
            "README_PHASE3.txt": (
                f"=== RVSAT-1 MISSION CONTROL: PHASE 3 FAULT ISOLATION ===\n"
                f"Team ID: {team_id:02d}\n\n"
                f"Deep telemetry questions on your fetched windows:\n"
                f"C3.1: Cascade sequence order of parameter anomalies (e.g. wheel_rpm_2,gyro_z,bus_v)\n"
                f"C3.2: UTC timestamp of the first frame after OBC reset\n"
                f"C3.3: Single bit flip index (0-based) and recovered original battery voltage (mV)\n"
                f"C3.4: Orbit index of F1 onset and post-eclipse battery voltage (mV)\n"
            )
        }
        create_encrypted_zip(
            os.path.join(packages_dir, f"team_{team_id:02d}_phase3.zip"),
            p3_files,
            password=flag_p2
        )
        
        # 8. Compute Exact Answers & Tolerances
        f1_onset_iso = (MISSION_EPOCH + timedelta(seconds=scenario.f1_onset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f2_onset_iso = (MISSION_EPOCH + timedelta(seconds=scenario.f2_onset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f3_onset_iso = (MISSION_EPOCH + timedelta(seconds=scenario.f3_onset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        f3_obc_reset_iso = (MISSION_EPOCH + timedelta(seconds=scenario.f3_obc_reset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        f1_post_bat_v = scenario.get_f1_post_eclipse_bat_v()
        
        team_answers = {
            "seed": seed,
            "drift_ppm": round(scenario.drift_ppm, 2),
            "launch_auth_code": launch_auth_code,
            "api_token": api_token,
            "hmac_part_a": hmac_part_a,
            "hmac_part_b": hmac_part_b,
            "flags": {
                "PHASE_1": flag_p1,
                "PHASE_2": flag_p2,
                "PHASE_3": flag_p3,
                "FINALE": flag_finale
            },
            "challenges": {
                "C1.1": {
                    "question": "OBC clock oscillator drift rate in PPM (or true dump start UTC)",
                    "answer": f"{round(scenario.drift_ppm, 1)}",
                    "alt_answer": dump_start_utc_iso,
                    "tolerance": 1.0,
                    "type": "numeric"
                },
                "C1.2": {
                    "question": "Telemetry gap start UTC and duration in seconds",
                    "answer": f"{gap_start_utc_iso} {gap_duration}",
                    "alt_answer": f"{gap_start_utc_iso} {gap_duration}s",
                    "tolerance": 1,
                    "type": "iso_time_and_val"
                },
                "C1.3": {
                    "question": "UTC timestamp of uint16 OBC tick counter rollover",
                    "answer": wrap_utc_iso,
                    "tolerance": 1,
                    "type": "iso_time"
                },
                "C2.1": {
                    "question": "Fault 1 (EPS) onset UTC and ICD fault code",
                    "answer": f"{f1_onset_iso} EPS-07",
                    "tolerance": 1,
                    "type": "iso_time_and_code"
                },
                "C2.2": {
                    "question": "Fault 2 (THM) onset UTC and ICD fault code",
                    "answer": f"{f2_onset_iso} THM-03",
                    "tolerance": 1,
                    "type": "iso_time_and_code"
                },
                "C2.3": {
                    "question": "Fault 3 (ADCS) cascade onset UTC and ICD fault code",
                    "answer": f"{f3_onset_iso} ADCS-02",
                    "tolerance": 1,
                    "type": "iso_time_and_code"
                },
                "C2.4": {
                    "question": "Fault 4 (Comms) corrupted frame ID (reset_count:sequence) and ICD code",
                    "answer": f"{scenario.f4_frame_reset_cnt}:{scenario.f4_frame_seq} COM-04",
                    "tolerance": 0,
                    "type": "frame_id_and_code"
                },
                "C3.1": {
                    "question": "Ordered list of parameter IDs whose deviation begins in F3 cascade",
                    "answer": "wheel_rpm_2,gyro_z,bus_v",
                    "alt_answer": "wheel2,gyro_z,bus_v",
                    "tolerance": 0,
                    "type": "string"
                },
                "C3.2": {
                    "question": "UTC timestamp of first frame after OBC reset",
                    "answer": f3_obc_reset_iso,
                    "tolerance": 1,
                    "type": "iso_time"
                },
                "C3.3": {
                    "question": "0-based flipped bit index in frame and recovered original battery voltage (mV)",
                    "answer": f"{scenario.f4_global_bit_index} {int(round(scenario.f4_original_bat_v_mV))}",
                    "tolerance": 10,
                    "type": "index_and_mV"
                },
                "C3.4": {
                    "question": "Orbit number of F1 onset and battery voltage at end of that eclipse (mV)",
                    "answer": f"{scenario.f1_orbit} {int(round(f1_post_bat_v))}",
                    "tolerance": 20,
                    "type": "orbit_and_mV"
                },
                "B1.1": {
                    "question": "Bonus: Command ID of the forged telecommand in uplink_log.csv",
                    "answer": forged_cmd_id,
                    "tolerance": 0,
                    "type": "string"
                },
                "B1.2": {
                    "question": "Bonus: Command ID of the replayed telecommand in uplink_log.csv",
                    "answer": replayed_cmd_id,
                    "tolerance": 0,
                    "type": "string"
                }
            }
        }
        
        master_answers[str(team_id)] = team_answers
        teams_metadata.append({
            "team_id": team_id,
            "seed": seed,
            "team_name": f"Team {team_id:02d}",
            "launch_auth_code": launch_auth_code,
            "api_token": api_token,
            "hmac_part_a": hmac_part_a,
            "hmac_part_b": hmac_part_b
        })
        
    # Save Master Answers
    master_answers_path = os.path.join(ANSWERS_DIR, "master_answers.json")
    with open(master_answers_path, "w", encoding="utf-8") as f_ma:
        json.dump(master_answers, f_ma, indent=2)
        
    print(f"[✓] Generation complete for all {num_teams} teams! Saved to {GENERATED_DATA_DIR}")
    return master_answers, teams_metadata

if __name__ == "__main__":
    generate_all_teams()
