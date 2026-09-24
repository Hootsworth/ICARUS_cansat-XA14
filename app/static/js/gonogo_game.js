/**
 * ICARUS Go / No-Go Pre-Launch Flight Poll Game Engine
 * Subsystem telemetry validation for launch readiness.
 */

(function () {
    const CHECKS = [
        {
            id: 1,
            subsystem: "AVIONICS POWER",
            telemetry: "Main 3.3V power bus reads 3.31 V, ripple 8 mV. Operational spec: 3.20 V – 3.40 V.",
            isGo: true,
            rationale: "Power rail is well within nominal voltage limits and ripple is clean."
        },
        {
            id: 2,
            subsystem: "RANGE SAFETY WEATHER",
            telemetry: "Surface wind shear gusting at 29 knots. Launch corridor safety limit: 18 knots.",
            isGo: false,
            rationale: "Excessive wind shear creates dangerous flight trajectory dispersion."
        },
        {
            id: 3,
            subsystem: "PYROTECHNIC RECOVERY",
            telemetry: "Parachute ejection squib continuity loop resistance reads 1.9 Ω. Specification: 1.5 Ω – 2.2 Ω.",
            isGo: true,
            rationale: "Squib bridge wire is intact and within firing tolerance."
        },
        {
            id: 4,
            subsystem: "DOWNLINK TELEMETRY",
            telemetry: "Radio signal at -112 dBm with 46% packet loss. Ground receiver threshold: -95 dBm, loss < 1%.",
            isGo: false,
            rationale: "Severe packet loss prevents critical flight telemetry reception."
        },
        {
            id: 5,
            subsystem: "SEALED PAYLOAD BAY",
            telemetry: "Bay internal pressure: 1012.8 hPa. Rate of pressure decay < 0.05 hPa/min.",
            isGo: true,
            rationale: "Payload pressure hull seal is hermetic and stable."
        },
        {
            id: 6,
            subsystem: "IMU CALIBRATION",
            telemetry: "3-Axis rate gyroscope zero-rate bias < 0.08°/s across roll, pitch, and yaw.",
            isGo: true,
            rationale: "Gyroscope sensor drift is negligible and ready for flight attitude tracking."
        },
        {
            id: 7,
            subsystem: "PRIMARY FLIGHT BATTERY",
            telemetry: "LiPo internal resistance measured at 185 mΩ. Maximum safety limit: 45 mΩ.",
            isGo: false,
            rationale: "Degraded cell internal resistance causes catastrophic voltage sag under load."
        },
        {
            id: 8,
            subsystem: "FLIGHT SOFTWARE",
            telemetry: "Hardware Watchdog Timer (WDT) enabled; main loop heartbeat confirmed at 50 Hz.",
            isGo: true,
            rationale: "Flight firmware fault-recovery watchdog is fully armed."
        },
        {
            id: 9,
            subsystem: "PROPULSION SYSTEM",
            telemetry: "Solid motor casing temperature at 84°C under direct solar bake. Maximum thermal limit: 42°C.",
            isGo: false,
            rationale: "Elevated motor propellant grain temperature risks case overpressure and burn rate anomaly."
        },
        {
            id: 10,
            subsystem: "GNSS NAVIGATION",
            telemetry: "GPS 3D fix verified with 11 satellites locked, HDOP = 0.82.",
            isGo: true,
            rationale: "Satellite positioning geometry provides pinpoint trajectory tracking."
        },
        {
            id: 11,
            subsystem: "RECOVERY SENSORS",
            telemetry: "Dual barometric altimeters show ΔP = 0.3 hPa differential (< 1.5 hPa limit).",
            isGo: true,
            rationale: "Redundant altitude sensor agreement confirms altitude sensor health."
        },
        {
            id: 12,
            subsystem: "AERODYNAMIC STABILITY",
            telemetry: "Center of Gravity (CG) is located 14 mm AFT of Center of Pressure (CP).",
            isGo: false,
            rationale: "Negative static stability margin! CG behind CP will cause aerodynamic cartwheel / tumbling."
        },
        {
            id: 13,
            subsystem: "RF SPECTRUM CLEARANCE",
            telemetry: "UHF 433.250 MHz frequency scan confirms zero local co-channel interference.",
            isGo: true,
            rationale: "Clean transmission channel ensures uninterrupted ground station reception."
        },
        {
            id: 14,
            subsystem: "TERMINATION SYSTEM",
            telemetry: "Flight safety cutoff squib battery reads 1.90 V on a 3.7 V nominal cell.",
            isGo: false,
            rationale: "Dead termination system battery violates range safety protocols."
        },
        {
            id: 15,
            subsystem: "FLIGHT CODE INTEGRITY",
            telemetry: "Avionics binary SHA-256 hash matches official Flight Director build manifest.",
            isGo: true,
            rationale: "Firmware authenticity confirmed against flight release."
        }
    ];

    class GoNoGoGame {
        constructor(containerId, options = {}) {
            this.container = document.getElementById(containerId);
            this.options = options;
            this.currentIndex = 0;
            this.score = 0;
            this.streak = 0;
            this.maxStreak = 0;
            this.timeLeft = 60;
            this.timerInterval = null;
            this.isRunning = false;
            this.answers = [];

            this.handleKeyDown = this.handleKeyDown.bind(this);
        }

        start() {
            this.currentIndex = 0;
            this.score = 0;
            this.streak = 0;
            this.maxStreak = 0;
            this.timeLeft = 60;
            this.isRunning = true;
            this.answers = [];

            window.addEventListener("keydown", this.handleKeyDown);
            this.renderUI();
            this.renderCard();

            if (this.timerInterval) clearInterval(this.timerInterval);
            this.timerInterval = setInterval(() => {
                this.timeLeft--;
                const timerEl = document.getElementById("gng-timer");
                if (timerEl) {
                    timerEl.textContent = `T-${this.timeLeft}s`;
                    if (this.timeLeft <= 10) {
                        timerEl.style.color = "#ef4444";
                    }
                }
                if (this.timeLeft <= 0) {
                    this.finish();
                }
            }, 1000);
        }

        renderUI() {
            this.container.innerHTML = `
                <div style="background: #18181b; border: 1px solid #27272a; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem;">
                    <!-- Top stats header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #27272a; padding-bottom: 1rem; margin-bottom: 1.25rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span class="badge mono" id="gng-step-badge" style="background: #27272a; color: #ffffff; border-radius: 8px;">CHECK 1 / 15</span>
                            <span class="badge mono" id="gng-streak-badge" style="background: #000000; color: #a1a1aa; border-radius: 8px;">STREAK: 0</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div class="mono" style="font-size: 1.2rem; font-weight: 800; color: #ffffff;" id="gng-score-display">0 PTS</div>
                            <div class="mono" style="font-size: 1rem; font-weight: 700; color: #f59e0b; background: #27272a; padding: 4px 10px; border-radius: 8px;" id="gng-timer">T-60s</div>
                        </div>
                    </div>

                    <!-- Active Decision Card Container -->
                    <div id="gng-card-mount"></div>

                    <!-- Big Dual Decision Controls -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.5rem;">
                        <button type="button" onclick="window.activeGoNoGo.makeDecision(true)" class="btn" style="background: #10b981; color: #ffffff; border-radius: 12px; padding: 1.1rem; font-size: 1.1rem; font-weight: 800; border: none; cursor: pointer; transition: transform 0.1s ease;">
                            ✓ GO (HOTKEY: G / &larr;)
                        </button>
                        <button type="button" onclick="window.activeGoNoGo.makeDecision(false)" class="btn" style="background: #ef4444; color: #ffffff; border-radius: 12px; padding: 1.1rem; font-size: 1.1rem; font-weight: 800; border: none; cursor: pointer; transition: transform 0.1s ease;">
                            ✕ NO-GO (HOTKEY: N / &rarr;)
                        </button>
                    </div>

                    <!-- Keyboard hotkey tip -->
                    <div style="text-align: center; margin-top: 0.75rem;">
                        <span class="mono" style="font-size: 0.72rem; color: #71717a;">Tip: Use [G] / Left Arrow for GO &bull; [N] / Right Arrow for NO-GO</span>
                    </div>
                </div>
            `;
        }

        renderCard() {
            if (this.currentIndex >= CHECKS.length) {
                this.finish();
                return;
            }

            const item = CHECKS[this.currentIndex];
            const mount = document.getElementById("gng-card-mount");
            const stepBadge = document.getElementById("gng-step-badge");
            const streakBadge = document.getElementById("gng-streak-badge");

            if (stepBadge) stepBadge.textContent = `CHECK ${this.currentIndex + 1} / ${CHECKS.length}`;
            if (streakBadge) streakBadge.textContent = `STREAK: ${this.streak}`;

            if (mount) {
                mount.innerHTML = `
                    <div id="active-poll-card" style="background: #09090b; border: 2px solid #27272a; border-radius: 14px; padding: 1.75rem; text-align: left; transition: all 0.2s ease;">
                        <div class="eyebrow" style="color: #38bdf8; font-size: 0.75rem; margin-bottom: 0.35rem;">
                            [SUBSYSTEM: ${item.subsystem}]
                        </div>
                        <div style="font-size: 1.15rem; font-weight: 600; line-height: 1.5; color: #f4f4f5; margin-bottom: 1rem;">
                            ${item.telemetry}
                        </div>
                        <div id="gng-feedback-msg" class="mono" style="font-size: 0.8rem; min-height: 20px; color: #71717a;">
                            Awaiting Flight Director poll response...
                        </div>
                    </div>
                `;
            }
        }

        handleKeyDown(e) {
            if (!this.isRunning) return;
            const key = e.key.toLowerCase();
            if (key === "g" || e.key === "ArrowLeft") {
                this.makeDecision(true);
            } else if (key === "n" || e.key === "ArrowRight") {
                this.makeDecision(false);
            }
        }

        makeDecision(userChoice) {
            if (!this.isRunning || this.currentIndex >= CHECKS.length) return;

            const item = CHECKS[this.currentIndex];
            const isCorrect = (userChoice === item.isGo);
            const cardEl = document.getElementById("active-poll-card");
            const feedbackEl = document.getElementById("gng-feedback-msg");

            if (isCorrect) {
                this.streak++;
                if (this.streak > this.maxStreak) this.maxStreak = this.streak;
                // Score: base 6 pts + streak bonus, max 100
                const ptsEarned = Math.round(100 / CHECKS.length);
                this.score += ptsEarned;
                if (cardEl) {
                    cardEl.style.borderColor = "#10b981";
                    cardEl.style.boxShadow = "0 0 20px rgba(16, 185, 129, 0.2)";
                }
                if (feedbackEl) {
                    feedbackEl.style.color = "#10b981";
                    feedbackEl.textContent = `✓ CORRECT: ${item.rationale}`;
                }
            } else {
                this.streak = 0;
                if (cardEl) {
                    cardEl.style.borderColor = "#ef4444";
                    cardEl.style.boxShadow = "0 0 20px rgba(239, 68, 68, 0.2)";
                }
                if (feedbackEl) {
                    feedbackEl.style.color = "#ef4444";
                    feedbackEl.textContent = `✕ FLAW DETECTED: ${item.rationale}`;
                }
            }

            this.answers.push({
                subsystem: item.subsystem,
                userChoice: userChoice,
                correctChoice: item.isGo,
                isCorrect: isCorrect
            });

            this.score = Math.min(100, this.score);
            const scoreEl = document.getElementById("gng-score-display");
            if (scoreEl) scoreEl.textContent = `${this.score} PTS`;

            this.currentIndex++;
            setTimeout(() => {
                this.renderCard();
            }, 550);
        }

        finish() {
            this.isRunning = false;
            if (this.timerInterval) clearInterval(this.timerInterval);
            window.removeEventListener("keydown", this.handleKeyDown);

            const finalScore = Math.min(100, Math.round(this.score));
            const passed = finalScore >= 50;

            this.container.innerHTML = `
                <div style="background: #18181b; border: 1px solid #27272a; border-radius: 16px; padding: 2.5rem; text-align: center;">
                    <div class="mono" style="font-size: 2.5rem; margin-bottom: 0.5rem;">${passed ? "🚀" : "⚠️"}</div>
                    <div class="eyebrow" style="color: ${passed ? '#10b981' : '#f59e0b'}; font-size: 0.8rem; margin-bottom: 0.5rem;">
                        ${passed ? "[LAUNCH AUTHORIZATION GRANTED]" : "[LAUNCH SCRUBBED - SYSTEM REVIEW]"}
                    </div>
                    <h2 style="font-size: 1.6rem; color: #ffffff; margin-bottom: 0.5rem;">Go / No-Go Poll Completed</h2>
                    <p style="color: #a1a1aa; font-size: 0.88rem; max-width: 500px; margin: 0 auto 1.5rem;">
                        ${passed ? "All critical subsystem metrics evaluated. Vehicle cleared for flight telemetry streaming." : "Review subsystem limits before proceeding."}
                    </p>

                    <div style="display: inline-flex; gap: 2rem; background: #09090b; padding: 1.25rem 2.5rem; border-radius: 12px; border: 1px solid #27272a; margin-bottom: 2rem;">
                        <div>
                            <div class="eyebrow">FINAL SCORE</div>
                            <div class="mono" style="font-size: 1.8rem; font-weight: 800; color: #ffffff;">${finalScore} / 100</div>
                        </div>
                        <div style="border-left: 1px solid #27272a; padding-left: 2rem;">
                            <div class="eyebrow">MAX STREAK</div>
                            <div class="mono" style="font-size: 1.8rem; font-weight: 800; color: #38bdf8;">${this.maxStreak}</div>
                        </div>
                    </div>

                    <div>
                        <button type="button" onclick="window.commitGoNoGoScore(${finalScore})" class="btn btn-primary" style="padding: 0.9rem 2.5rem; font-size: 0.95rem;">
                            Confirm Launch Poll & Advance to Telemetry &rarr;
                        </button>
                    </div>
                </div>
            `;
        }
    }

    window.GoNoGoGame = GoNoGoGame;
})();
