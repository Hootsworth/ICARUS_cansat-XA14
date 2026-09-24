/**
 * Round 3: CanSat Parachute & Ejection Atmospheric Drop Simulator
 * Interactive HTML5 Canvas Simulation with Client-Side HMAC-SHA256 Signing.
 * Minimalist Flat B&W Editorial Design.
 */

// Pure Vanilla JS HMAC-SHA256 Implementation
const CryptoHMAC = (function () {
    function sha256(ascii) {
        function rightRotate(value, amount) {
            return (value >>> amount) | (value << (32 - amount));
        }
        var mathPow = Math.pow;
        var maxWord = mathPow(2, 32);
        var lengthProperty = 'length';
        var i, j;
        var result = '';
        var words = [];
        var asciiBitLength = ascii[lengthProperty] * 8;
        var hash = sha256.h = sha256.h || [];
        var k = sha256.k = sha256.k || [];
        var primeCounter = k[lengthProperty];
        var isComposite = {};
        for (var candidate = 2; primeCounter < 64; candidate++) {
            if (!isComposite[candidate]) {
                for (i = 0; i < 300; i += candidate) {
                    isComposite[i] = candidate;
                }
                hash[primeCounter] = (mathPow(candidate, .5) * maxWord) | 0;
                k[primeCounter++] = (mathPow(candidate, 1 / 3) * maxWord) | 0;
            }
        }
        ascii += '\x80';
        while (ascii[lengthProperty] % 64 - 56) ascii += '\x00';
        for (i = 0; i < ascii[lengthProperty]; i++) {
            j = ascii.charCodeAt(i);
            if (j >> 8) return;
            words[i >> 2] |= j << ((3 - i) % 4) * 8;
        }
        words[words[lengthProperty]] = ((asciiBitLength / maxWord) | 0);
        words[words[lengthProperty]] = (asciiBitLength | 0);
        for (j = 0; j < words[lengthProperty];) {
            var w = words.slice(j, j += 16);
            var oldHash = hash;
            hash = hash.slice(0, 8);
            for (i = 0; i < 64; i++) {
                var w15 = w[i - 15], w2 = w[i - 2];
                var s0 = rightRotate(w15, 7) ^ rightRotate(w15, 18) ^ (w15 >>> 3);
                var s1 = rightRotate(w2, 17) ^ rightRotate(w2, 19) ^ (w2 >>> 10);
                w[i] = i < 16 ? w[i] : (w[i - 16] + s0 + w[i - 7] + s1) | 0;
                var s1b = rightRotate(hash[4], 6) ^ rightRotate(hash[4], 11) ^ rightRotate(hash[4], 25);
                var ch = (hash[4] & hash[5]) ^ (~hash[4] & hash[6]);
                var temp1 = (hash[7] + s1b + ch + k[i] + w[i]) | 0;
                var s0b = rightRotate(hash[0], 2) ^ rightRotate(hash[0], 13) ^ rightRotate(hash[0], 22);
                var maj = (hash[0] & hash[1]) ^ (hash[0] & hash[2]) ^ (hash[1] & hash[2]);
                var temp2 = (s0b + maj) | 0;
                hash = [(temp1 + temp2) | 0].concat(hash);
                hash[4] = (hash[4] + temp1) | 0;
            }
            for (i = 0; i < 8; i++) {
                hash[i] = (hash[i] + oldHash[i]) | 0;
            }
        }
        for (i = 0; i < 8; i++) {
            for (j = 3; j + 1; j--) {
                var b = (hash[i] >> (j * 8)) & 255;
                result += ((b < 16 ? 0 : '') + b.toString(16));
            }
        }
        return result;
    }

    function hexToBytes(hex) {
        var bytes = [];
        for (var c = 0; c < hex.length; c += 2) {
            bytes.push(parseInt(hex.substr(c, 2), 16));
        }
        return bytes;
    }

    function bytesToString(bytes) {
        var str = '';
        for (var i = 0; i < bytes.length; i++) {
            str += String.fromCharCode(bytes[i]);
        }
        return str;
    }

    function hmacSha256(key, message) {
        var blockSize = 64;
        var keyBytes = [];
        for (var i = 0; i < key.length; i++) keyBytes.push(key.charCodeAt(i));
        if (keyBytes.length > blockSize) {
            keyBytes = hexToBytes(sha256(key));
        }
        while (keyBytes.length < blockSize) keyBytes.push(0);
        var o_key_pad = [], i_key_pad = [];
        for (var k = 0; k < blockSize; k++) {
            o_key_pad[k] = keyBytes[k] ^ 0x5c;
            i_key_pad[k] = keyBytes[k] ^ 0x36;
        }
        var inner = sha256(bytesToString(i_key_pad) + message);
        return sha256(bytesToString(o_key_pad) + bytesToString(hexToBytes(inner)));
    }

    return { hmac: hmacSha256 };
})();

class CanSatDropGame {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.sessionId = null;
        this.sessionToken = null;
        this.isRunning = false;
        this.isGameOver = false;

        // Flight Physics State (SI Units)
        this.altitude = 1000.0;    // meters AGL
        this.vy = 0.0;             // m/s downward (positive is downward)
        this.vx = 0.0;             // m/s lateral
        this.xOffset = 0.0;        // meters displacement from bullseye (0 = center)
        this.gForce = 1.0;         // Gs
        this.maxG = 1.0;

        // Subsystems
        this.chuteDeployed = false;
        this.chuteDeployAlt = 0;
        this.chuteInflation = 0.0; // 0 to 1.0
        this.finTrim = 0;          // -1 (port) to +1 (starboard)
        this.buzzerArmed = false;
        this.buzzerArmedAlt = 0;

        // Atmosphere / Environment
        this.windSpeed = 3.5;      // m/s (+ to right, - to left)
        this.particles = [];       // wind stream visualization
        for (let i = 0; i < 40; i++) {
            this.particles.push({
                x: Math.random() * 860,
                y: Math.random() * 380,
                len: 10 + Math.random() * 20,
                speed: 1.0 + Math.random() * 1.5
            });
        }

        // Timing & Speed
        this.simSpeed = 2.8;       // 2.8x speed gives ~23s duration
        this.lastTimestamp = 0;
        this.totalFlightTime = 0.0;
        this.actionsCount = 0;
        this.animationFrameId = null;

        this.bindEvents();
    }

    bindEvents() {
        window.addEventListener('keydown', (e) => {
            if (!this.isRunning || this.isGameOver) return;

            if (e.code === 'Space') {
                e.preventDefault();
                this.deployParachute();
            } else if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') {
                e.preventDefault();
                this.trimLeft();
            } else if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') {
                e.preventDefault();
                this.trimRight();
            } else if (e.key === 'b' || e.key === 'B') {
                e.preventDefault();
                this.toggleBuzzer();
            }
        });

        window.addEventListener('keyup', (e) => {
            if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft' ||
                e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') {
                this.finTrim = 0;
                this.updateButtons();
            }
        });
    }

    deployParachute() {
        if (!this.chuteDeployed) {
            this.chuteDeployed = true;
            this.chuteDeployAlt = this.altitude;
            this.actionsCount++;
            this.logEvent(`[ALT ${Math.round(this.altitude)}m] PARACHUTE DEPLOYMENT COMMANDED. Pyrotechnic pin fired.`, "#ffffff");
            this.updateButtons();
        }
    }

    trimLeft() {
        this.finTrim = -1;
        this.actionsCount++;
        this.updateButtons();
    }

    trimRight() {
        this.finTrim = 1;
        this.actionsCount++;
        this.updateButtons();
    }

    toggleBuzzer() {
        if (!this.buzzerArmed) {
            this.buzzerArmed = true;
            this.buzzerArmedAlt = this.altitude;
            this.actionsCount++;
            this.logEvent(`[ALT ${Math.round(this.altitude)}m] RECOVERY BEACON ARMED: 433MHz acoustic buzzer transmitting.`, "#ffffff");
            this.updateButtons();
        }
    }

    updateButtons() {
        const btnChute = document.getElementById("btn-chute");
        const btnBuzzer = document.getElementById("btn-buzzer");
        const btnLeft = document.getElementById("btn-trim-left");
        const btnRight = document.getElementById("btn-trim-right");

        if (btnChute) {
            btnChute.className = this.chuteDeployed ? "game-btn btn-active" : "game-btn";
            btnChute.innerHTML = this.chuteDeployed ? "<span>✓ CHUTE DEPLOYED</span>" : "<span>[SPACE] Deploy Parachute</span>";
        }
        if (btnBuzzer) {
            btnBuzzer.className = this.buzzerArmed ? "game-btn btn-active" : "game-btn";
            btnBuzzer.innerHTML = this.buzzerArmed ? "<span>✓ BEACON ACTIVE (433MHz)</span>" : "<span>[B] Arm Recovery Buzzer</span>";
        }
        if (btnLeft) {
            btnLeft.className = this.finTrim === -1 ? "game-btn btn-active" : "game-btn";
        }
        if (btnRight) {
            btnRight.className = this.finTrim === 1 ? "game-btn btn-active" : "game-btn";
        }
    }

    logEvent(msg, color = "#a3a3a3") {
        const logBox = document.getElementById("game-log");
        if (logBox) {
            const entry = document.createElement("div");
            entry.style.color = color;
            entry.style.fontSize = "0.78rem";
            entry.style.marginBottom = "0.25rem";
            entry.innerText = `[T+${this.totalFlightTime.toFixed(1)}s] ${msg}`;
            logBox.prepend(entry);
        }
    }

    start(sessionId, sessionToken) {
        this.sessionId = sessionId;
        this.sessionToken = sessionToken;
        this.isRunning = true;
        this.isGameOver = false;
        this.altitude = 1000.0;
        this.vy = 2.0; // initial ejection speed
        this.vx = 0.0;
        this.xOffset = (Math.random() - 0.5) * 40.0; // initial small random drift
        this.lastTimestamp = performance.now();
        this.logEvent("EJECTION SUCCESSFUL: CanSat dropped from 1,000m AGL. Atmospheric entry in progress.", "#ffffff");
        this.loop(this.lastTimestamp);
    }

    loop(currentTimestamp) {
        if (!this.isRunning) return;
        const dt = Math.min((currentTimestamp - this.lastTimestamp) / 1000.0, 0.05);
        this.lastTimestamp = currentTimestamp;

        this.update(dt * this.simSpeed);
        this.render();

        if (this.isGameOver) {
            this.finalizeMission();
            return;
        }

        this.animationFrameId = requestAnimationFrame((ts) => this.loop(ts));
    }

    update(dt) {
        this.totalFlightTime += dt / this.simSpeed;

        // Dynamic Wind Profile depending on altitude layers
        if (this.altitude > 650) {
            this.windSpeed = 4.2; // upper jet
        } else if (this.altitude > 250) {
            this.windSpeed = -2.5; // mid layer shear
        } else {
            this.windSpeed = 1.8; // surface drift
        }

        // Parachute Inflation Physics
        if (this.chuteDeployed && this.chuteInflation < 1.0) {
            this.chuteInflation = Math.min(1.0, this.chuteInflation + 1.2 * dt);
        }

        // Drag & Terminal Velocity calculation
        // Freefall terminal ~44 m/s; With parachute ~6.8 m/s
        const freefallCd = 0.008;
        const chuteCd = 0.18;
        const currentCd = freefallCd + (chuteCd * this.chuteInflation);

        const dragForceY = currentCd * (this.vy * this.vy);
        const gravity = 9.81;
        const netAy = gravity - dragForceY;

        // G-Force computation
        this.gForce = Math.max(0.1, Math.abs(netAy) / gravity);
        if (this.gForce > this.maxG) this.maxG = this.gForce;

        this.vy += netAy * dt;
        this.altitude -= this.vy * dt;

        // Lateral steering and wind drift
        // Fins provide lateral control force (-3 m/s to +3 m/s)
        const finLift = this.finTrim * 4.5;
        const lateralDrag = 1.5;
        this.vx += (this.windSpeed * (this.chuteDeployed ? 0.9 : 0.3) + finLift - this.vx * lateralDrag) * dt;
        this.xOffset += this.vx * dt;

        // Altitude Milestones
        if (this.altitude <= 500 && !this._logged500) {
            this._logged500 = true;
            this.logEvent("ALTITUDE 500m AGL REACHED. Primary parachute deployment recommended.", "#ffffff");
        }
        if (this.altitude <= 250 && !this.buzzerArmed && !this._warnedBuzzer) {
            this._warnedBuzzer = true;
            this.logEvent("⚠️ CAUTION: Below 250m. Acoustic recovery beacon must be armed [B]!", "#ffffff");
        }

        // Touchdown Check
        if (this.altitude <= 0) {
            this.altitude = 0;
            this.isRunning = false;
            this.isGameOver = true;
            this.logEvent(`TOUCHDOWN CONFIRMED at ${Math.abs(this.xOffset).toFixed(1)}m from center. Impact velocity: ${this.vy.toFixed(1)} m/s.`, "#ffffff");
        }
    }

    render() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, w, h);

        // 1. Grid & Atmospheric Layer lines (Clean subtle technical grid)
        ctx.strokeStyle = "#f0f0f2";
        ctx.lineWidth = 1;
        for (let y = 0; y < h; y += 40) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // 2. Wind Streamer particles
        ctx.strokeStyle = "#d4d4d8";
        ctx.lineWidth = 1;
        for (let p of this.particles) {
            p.x += (this.windSpeed * 12 + (p.speed * 10)) * 0.05;
            if (p.x > w + 50) p.x = -50;
            if (p.x < -50) p.x = w + 50;

            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p.x + (this.windSpeed > 0 ? p.len : -p.len), p.y);
            ctx.stroke();
        }

        // 3. Left Altitude Tape (Aviation Style Monochrome Barometer)
        const tapeW = 70;
        ctx.fillStyle = "#f8f8fa";
        ctx.fillRect(0, 0, tapeW, h);
        ctx.strokeStyle = "#e4e4e7";
        ctx.beginPath();
        ctx.moveTo(tapeW, 0); ctx.lineTo(tapeW, h);
        ctx.stroke();

        ctx.font = "9px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#71717a";
        // Altitude ticks: 1000m mapped to canvas height
        for (let a = 1000; a >= 0; a -= 100) {
            const tickY = 25 + ((1000 - a) / 1000) * (h - 50);
            ctx.beginPath();
            ctx.moveTo(tapeW - 12, tickY); ctx.lineTo(tapeW, tickY);
            ctx.stroke();
            ctx.fillText(`${a}m`, 10, tickY + 3);
        }

        // Altitude Indicator Bug on Tape
        const currentTapeY = 25 + ((1000 - Math.max(0, this.altitude)) / 1000) * (h - 50);
        ctx.fillStyle = "#000000";
        ctx.beginPath();
        ctx.moveTo(tapeW - 16, currentTapeY - 5);
        ctx.lineTo(tapeW - 2, currentTapeY);
        ctx.lineTo(tapeW - 16, currentTapeY + 5);
        ctx.closePath();
        ctx.fill();

        // 4. Center Ground & Landing Target Bullseye (when altitude < 250m)
        const groundY = h - 35;
        if (this.altitude < 300) {
            const groundAlpha = Math.min(1.0, (300 - this.altitude) / 200.0);
            ctx.save();
            ctx.globalAlpha = groundAlpha;

            // Ground Baseline
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(tapeW, groundY); ctx.lineTo(w, groundY);
            ctx.stroke();

            // Ground Target Pad Center (mapped to screen center w/ scale)
            const targetScreenX = tapeW + (w - tapeW) / 2;
            // Target rings: 25m, 75m, 150m
            const mToPx = 1.6; // 1 meter = 1.6 px

            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.moveTo(targetScreenX, groundY - 10); ctx.lineTo(targetScreenX, groundY + 10);
            ctx.stroke();
            ctx.font = "10px 'JetBrains Mono', monospace";
            ctx.fillStyle = "#000000";
            ctx.fillText("◉ 0m", targetScreenX - 12, groundY + 22);

            // Ring boundaries
            ctx.strokeStyle = "#71717a";
            ctx.strokeRect(targetScreenX - 25 * mToPx, groundY - 4, 50 * mToPx, 8);
            ctx.strokeRect(targetScreenX - 75 * mToPx, groundY - 2, 150 * mToPx, 4);

            ctx.restore();
        }

        // 5. Draw CanSat Vehicle
        const centerX = tapeW + (w - tapeW) / 2;
        const cansatScreenX = Math.max(tapeW + 20, Math.min(w - 20, centerX + (this.xOffset * 1.6)));
        let cansatScreenY;
        if (this.altitude > 150) {
            cansatScreenY = 130 + Math.sin(this.totalFlightTime * 2) * 4;
        } else {
            const progress = (150 - this.altitude) / 150.0;
            cansatScreenY = 130 + progress * (groundY - 145);
        }

        // Parachute (if deployed)
        if (this.chuteDeployed && this.chuteInflation > 0.05) {
            const chuteRadius = 28 * this.chuteInflation;
            const canopyY = cansatScreenY - 48;

            // Suspension Lines
            ctx.strokeStyle = "#71717a";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(cansatScreenX, cansatScreenY - 10); ctx.lineTo(cansatScreenX - chuteRadius, canopyY + 6);
            ctx.moveTo(cansatScreenX, cansatScreenY - 10); ctx.lineTo(cansatScreenX + chuteRadius, canopyY + 6);
            ctx.moveTo(cansatScreenX, cansatScreenY - 10); ctx.lineTo(cansatScreenX, canopyY);
            ctx.stroke();

            // Parachute Canopy (Monochrome Black Dome with White Vent)
            ctx.fillStyle = "#000000";
            ctx.beginPath();
            ctx.arc(cansatScreenX, canopyY, chuteRadius, Math.PI, 0, false);
            ctx.closePath();
            ctx.fill();

            // Canopy Gores (White technical stripes)
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(cansatScreenX, canopyY, chuteRadius * 0.5, Math.PI, 0, false);
            ctx.stroke();
        }

        // CanSat Cylinder Body (Crisp Black Technical Cylinder)
        ctx.fillStyle = "#000000";
        ctx.fillRect(cansatScreenX - 6, cansatScreenY - 10, 12, 20);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1;
        ctx.strokeRect(cansatScreenX - 5, cansatScreenY - 8, 10, 16);

        // Steering Fins
        ctx.fillStyle = this.finTrim !== 0 ? "#000000" : "#52525b";
        if (this.finTrim === -1) {
            ctx.fillRect(cansatScreenX - 11, cansatScreenY + 2, 5, 6);
            ctx.fillRect(cansatScreenX + 6, cansatScreenY + 4, 4, 4);
        } else if (this.finTrim === 1) {
            ctx.fillRect(cansatScreenX - 10, cansatScreenY + 4, 4, 4);
            ctx.fillRect(cansatScreenX + 6, cansatScreenY + 2, 5, 6);
        } else {
            ctx.fillRect(cansatScreenX - 10, cansatScreenY + 4, 4, 4);
            ctx.fillRect(cansatScreenX + 6, cansatScreenY + 4, 4, 4);
        }

        // Recovery Strobe / Buzzer indicator on vehicle
        if (this.buzzerArmed) {
            const strobe = Math.floor(this.totalFlightTime * 6) % 2 === 0;
            if (strobe) {
                ctx.fillStyle = "#000000";
                ctx.beginPath();
                ctx.arc(cansatScreenX, cansatScreenY - 13, 3, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // 6. In-Canvas Telemetry HUD Labels
        ctx.font = "11px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#09090b";
        ctx.fillText(`ALTITUDE: ${Math.round(this.altitude)} m`, tapeW + 15, 25);
        ctx.fillText(`DESCENT V: -${this.vy.toFixed(1)} m/s`, tapeW + 15, 42);
        ctx.fillText(`DRIFT OFFSET: ${this.xOffset >= 0 ? '+' : ''}${this.xOffset.toFixed(1)} m`, tapeW + 15, 59);

        // Right side HUD
        ctx.textAlign = "right";
        ctx.fillText(`CROSSWIND: ${this.windSpeed.toFixed(1)} m/s`, w - 15, 25);
        ctx.fillText(`G-LOAD: ${this.gForce.toFixed(1)} G`, w - 15, 42);
        ctx.fillText(`BEACON: ${this.buzzerArmed ? "ACTIVE" : "STANDBY"}`, w - 15, 59);
        ctx.textAlign = "left";

        this.updateDOMHUD();
    }

    updateDOMHUD() {
        const elAlt = document.getElementById("hud-altitude");
        const elSpeed = document.getElementById("hud-speed");
        const elDrift = document.getElementById("hud-drift");
        const elBeacon = document.getElementById("hud-beacon");

        if (elAlt) elAlt.innerText = Math.round(this.altitude) + " m";
        if (elSpeed) elSpeed.innerText = this.vy.toFixed(1) + " m/s";
        if (elDrift) elDrift.innerText = (this.xOffset >= 0 ? "+" : "") + this.xOffset.toFixed(1) + " m";
        if (elBeacon) elBeacon.innerText = this.buzzerArmed ? "ACTIVE" : "STANDBY";
    }

    calculateScore() {
        // Max 500 PTS
        // 1. Descent Velocity (Target 5.0 to 9.5 m/s) -> 200 PTS
        let vScore = 0;
        const v = this.vy;
        if (v >= 5.5 && v <= 8.5) {
            vScore = 200;
        } else if ((v >= 4.5 && v < 5.5) || (v > 8.5 && v <= 10.0)) {
            vScore = 150;
        } else if (v > 10.0 && v <= 12.0) {
            vScore = 75; // Hard impact
        } else if (v > 12.0) {
            vScore = 0;  // Severe crash impact
        } else {
            vScore = 60; // Too slow / excessive drift
        }

        // 2. Bullseye Precision Landing (Target <= 15m) -> 200 PTS
        let dScore = 0;
        const d = Math.abs(this.xOffset);
        if (d <= 15.0) {
            dScore = 200;
        } else if (d <= 35.0) {
            dScore = 170;
        } else if (d <= 65.0) {
            dScore = 130;
        } else if (d <= 120.0) {
            dScore = 80;
        } else if (d <= 200.0) {
            dScore = 40;
        } else {
            dScore = 0;
        }

        // 3. Audio Buzzer / Beacon Subsystem -> 100 PTS
        let bScore = 0;
        if (this.buzzerArmed && this.buzzerArmedAlt <= 400) {
            bScore = 100;
        } else if (this.buzzerArmed) {
            bScore = 60; // armed too early
        }

        const totalScore = Math.max(0, Math.min(500, Math.round(vScore + dScore + bScore)));
        return {
            totalScore,
            vScore,
            dScore,
            bScore
        };
    }

    async finalizeMission() {
        this.isRunning = false;
        const scoring = this.calculateScore();
        const rawScore = scoring.totalScore;
        const vScaled = Math.round(this.vy * 10);
        const dRounded = Math.round(Math.abs(this.xOffset));

        // Signature message: r3:{session_id}:{raw_score}:{p1}:{p2}
        const messageToSign = `r3:${this.sessionId}:${rawScore}:${vScaled}:${dRounded}`;
        const signature = CryptoHMAC.hmac(this.sessionToken, messageToSign);

        const overlay = document.getElementById("game-overlay");
        const statusMsg = document.getElementById("game-status-msg");
        if (overlay) overlay.style.display = "flex";
        if (statusMsg) statusMsg.innerText = "Dispatching cryptographically signed CanSat flight telemetry to ground station...";

        try {
            const res = await fetch("/api/round3/submit", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    raw_score: rawScore,
                    p1: vScaled,
                    p2: dRounded,
                    signature: signature,
                    metrics: {
                        touchdown_velocity_mps: parseFloat(this.vy.toFixed(2)),
                        landing_offset_m: parseFloat(this.xOffset.toFixed(2)),
                        chute_deployment_alt_m: Math.round(this.chuteDeployAlt),
                        beacon_deployed: this.buzzerArmed,
                        max_g_force: parseFloat(this.maxG.toFixed(2)),
                        flight_duration_s: parseFloat(this.totalFlightTime.toFixed(1))
                    }
                })
            });

            const data = await res.json();
            if (data.verified) {
                if (statusMsg) {
                    // ZERO-LEAKAGE: We show flight telemetry stats, but NEVER the raw score!
                    statusMsg.innerHTML = `
                        <div class="mono" style="font-size:1.8rem; margin-bottom:0.75rem;">[TOUCHDOWN CONFIRMED]</div>
                        <h3 style="color:#ffffff; margin-bottom:0.5rem; font-size:1.2rem;">CanSat Atmospheric Flight Log Sealed</h3>
                        <p style="color:var(--text-muted); font-size:0.85rem; margin-bottom:1.5rem; line-height:1.5;">
                            Ground station has authenticated your CanSat descent telemetry package via cryptographic HMAC.
                            Flight metrics and structural integrity logs have been archived directly into the master flight ledger.
                        </p>
                        <div style="display:flex; justify-content:center; gap:1rem; margin-bottom:1.5rem; text-align:center;">
                            <div style="border:1px solid var(--border-muted); padding:0.6rem 1rem;">
                                <div class="eyebrow">TOUCHDOWN VELOCITY</div>
                                <div class="mono" style="color:#ffffff; font-weight:700;">${this.vy.toFixed(1)} m/s</div>
                            </div>
                            <div style="border:1px solid var(--border-muted); padding:0.6rem 1rem;">
                                <div class="eyebrow">BULLSEYE DISPLACEMENT</div>
                                <div class="mono" style="color:#ffffff; font-weight:700;">${Math.abs(this.xOffset).toFixed(1)} m</div>
                            </div>
                            <div style="border:1px solid var(--border-muted); padding:0.6rem 1rem;">
                                <div class="eyebrow">RECOVERY BEACON</div>
                                <div class="mono" style="color:#ffffff; font-weight:700;">${this.buzzerArmed ? "AUTHENTICATED" : "NOT ARMED"}</div>
                            </div>
                        </div>
                        <a href="/dashboard" class="btn btn-primary" style="padding:0.75rem 2rem;">Return to Dashboard &rarr;</a>
                    `;
                }
            } else {
                if (statusMsg) statusMsg.innerText = "Verification failed: " + (data.detail || "Server rejected telemetry.");
            }
        } catch (e) {
            if (statusMsg) statusMsg.innerText = "Network transmission error during telemetry verification.";
        }
    }
}

window.CanSatDropGame = CanSatDropGame;
