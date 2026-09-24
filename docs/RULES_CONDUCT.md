# Rules & Code of Conduct
**Event:** RVSAT-1 Satellite Telemetry & Flight Operations Challenge  

---

## 1. General Principles
1. **Fair Competition:** Every team operates an independently seeded satellite simulation. Solutions and flags are non-transferable.
2. **AI Assistants Allowed:** You may use AI code assistants (LLMs) to write decoding scripts, numerical analysis routines, or plot telemetry. However, teams are responsible for verifying all answers before submission.
3. **No Network Attacks:** Attacking the competition server, automated denial of service, attempting to bypass rate limits, or exploiting unauthorized web paths will result in immediate team disqualification.
4. **Credit Governance:** Downlink credits represent real ground-station tracking time. Manage your budget carefully.

---

## 2. Submission & Grading Rules
- Answers are auto-graded against deterministic, exact keys with stated numerical/time tolerances ($\pm 1\text{s}$ for timestamps).
- Format: ISO-8601 UTC for timestamps (`YYYY-MM-DDTHH:MM:SSZ`), uppercase fault codes.
- 5 attempts per challenge before a 10-minute cooldown lock is imposed.
- Each incorrect attempt incurs a -5% penalty on awarded points.
