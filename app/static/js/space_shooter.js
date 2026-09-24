/**
 * ICARUS 8-Bit Retro Space Shooter Engine (Round 2: The Launch)
 * Classic arcade pixel-art shooter with parallax starfields, debris, laser cannons,
 * score tracking, and cinematic flight crash termination.
 */

class SpaceShooterGame {
    constructor(canvasId, options = {}) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext("2d");
        this.onGameOver = options.onGameOver || null;
        this.onScoreUpdate = options.onScoreUpdate || null;

        this.width = this.canvas.width;
        this.height = this.canvas.height;

        this.isRunning = false;
        this.score = 0;
        this.timeLeft = 75; // 75 seconds timed flight launch
        this.lives = 3;
        this.shield = 100;
        this.altitude = 0;

        // Player Rocket
        this.player = {
            x: this.width / 2 - 16,
            y: this.height - 90,
            w: 32,
            h: 48,
            speed: 6,
            vx: 0,
            vy: 0
        };

        // Entities
        this.lasers = [];
        this.enemies = [];
        this.pickups = [];
        this.particles = [];
        this.stars = [];

        // Key states
        this.keys = {};
        this.lastShotTime = 0;

        this.initStars();
        this.bindEvents();
    }

    initStars() {
        this.stars = [];
        for (let i = 0; i < 70; i++) {
            this.stars.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                size: Math.random() < 0.2 ? 2.5 : 1.5,
                speed: 1 + Math.random() * 3,
                brightness: Math.random()
            });
        }
    }

    bindEvents() {
        this.handleKeyDown = (e) => {
            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", " "].includes(e.key) || e.code === "Space") {
                e.preventDefault();
            }
            this.keys[e.key.toLowerCase()] = true;
            if (e.code === "Space" || e.key === " ") {
                this.keys["space"] = true;
                this.shoot();
            }
        };

        this.handleKeyUp = (e) => {
            this.keys[e.key.toLowerCase()] = false;
            if (e.code === "Space" || e.key === " ") {
                this.keys["space"] = false;
            }
        };

        window.addEventListener("keydown", this.handleKeyDown);
        window.addEventListener("keyup", this.handleKeyUp);
    }

    destroy() {
        this.isRunning = false;
        if (this.timerInterval) clearInterval(this.timerInterval);
        window.removeEventListener("keydown", this.handleKeyDown);
        window.removeEventListener("keyup", this.handleKeyUp);
    }

    start() {
        this.isRunning = true;
        this.score = 0;
        this.timeLeft = 75;
        this.shield = 100;
        this.lasers = [];
        this.enemies = [];
        this.pickups = [];
        this.particles = [];

        this.player.x = this.width / 2 - 16;
        this.player.y = this.height - 90;

        if (this.timerInterval) clearInterval(this.timerInterval);
        this.timerInterval = setInterval(() => {
            if (this.isRunning) {
                this.timeLeft--;
                this.altitude += 16.2; // climbing in meters
                if (this.timeLeft <= 0) {
                    this.triggerCrashAnomaly("LAUNCH_WINDOW_EXPIRED");
                }
            }
        }, 1000);

        this.lastTime = performance.now();
        requestAnimationFrame((t) => this.loop(t));
    }

    shoot() {
        if (!this.isRunning) return;
        const now = performance.now();
        if (now - this.lastShotTime < 180) return; // rate limit fire
        this.lastShotTime = now;

        // Dual laser cannons
        this.lasers.push({
            x: this.player.x + 4,
            y: this.player.y,
            w: 4,
            h: 12,
            speed: 12
        });
        this.lasers.push({
            x: this.player.x + this.player.w - 8,
            y: this.player.y,
            w: 4,
            h: 12,
            speed: 12
        });
    }

    spawnDebris() {
        if (Math.random() < 0.05) {
            const types = ["DEBRIS", "METEOR", "SATELLITE_JUNK"];
            const type = types[Math.floor(Math.random() * types.length)];
            const size = type === "METEOR" ? 28 : (type === "SATELLITE_JUNK" ? 34 : 22);

            this.enemies.push({
                type: type,
                x: Math.random() * (this.width - size),
                y: -size - 10,
                w: size,
                h: size,
                speed: 2 + Math.random() * 3.5,
                hp: type === "METEOR" ? 2 : 1,
                points: type === "METEOR" ? 25 : (type === "SATELLITE_JUNK" ? 35 : 15),
                rot: 0,
                rotSpeed: (Math.random() - 0.5) * 0.1
            });
        }

        // Energy boost pickup
        if (Math.random() < 0.008) {
            this.pickups.push({
                x: Math.random() * (this.width - 24),
                y: -30,
                w: 20,
                h: 20,
                speed: 2
            });
        }
    }

    createExplosion(x, y, count = 14, color = "#000000") {
        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 1 + Math.random() * 4;
            this.particles.push({
                x: x,
                y: y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 1.0,
                decay: 0.02 + Math.random() * 0.04,
                size: 2 + Math.random() * 3,
                color: color
            });
        }
    }

    update(dt) {
        // Player Movement
        let moveX = 0;
        let moveY = 0;
        if (this.keys["arrowleft"] || this.keys["a"]) moveX -= 1;
        if (this.keys["arrowright"] || this.keys["d"]) moveX += 1;
        if (this.keys["arrowup"] || this.keys["w"]) moveY -= 0.7;
        if (this.keys["arrowdown"] || this.keys["s"]) moveY += 0.7;

        this.player.x += moveX * this.player.speed;
        this.player.y += moveY * this.player.speed;

        // Boundaries
        this.player.x = Math.max(10, Math.min(this.width - this.player.w - 10, this.player.x));
        this.player.y = Math.max(50, Math.min(this.height - this.player.h - 10, this.player.y));

        // Auto continuous fire if space held
        if (this.keys["space"]) {
            this.shoot();
        }

        // Stars
        this.stars.forEach(s => {
            s.y += s.speed;
            if (s.y > this.height) {
                s.y = 0;
                s.x = Math.random() * this.width;
            }
        });

        // Lasers
        for (let i = this.lasers.length - 1; i >= 0; i--) {
            const l = this.lasers[i];
            l.y -= l.speed;
            if (l.y < -20) {
                this.lasers.splice(i, 1);
            }
        }

        // Spawn Hazards
        this.spawnDebris();

        // Enemies update & collision with lasers
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const e = this.enemies[i];
            e.y += e.speed;
            e.rot += e.rotSpeed;

            // Collision with Lasers
            for (let j = this.lasers.length - 1; j >= 0; j--) {
                const l = this.lasers[j];
                if (l.x < e.x + e.w && l.x + l.w > e.x && l.y < e.y + e.h && l.y + l.h > e.y) {
                    this.lasers.splice(j, 1);
                    e.hp--;
                    this.createExplosion(l.x, l.y, 4, "#555555");
                    if (e.hp <= 0) {
                        this.score += e.points;
                        this.createExplosion(e.x + e.w / 2, e.y + e.h / 2, 16, "#000000");
                        this.enemies.splice(i, 1);
                        if (this.onScoreUpdate) this.onScoreUpdate(this.score);
                        break;
                    }
                }
            }

            // Collision with Player
            if (this.player.x < e.x + e.w && this.player.x + this.player.w > e.x &&
                this.player.y < e.y + e.h && this.player.y + this.player.h > e.y) {
                this.shield -= 25;
                this.createExplosion(e.x + e.w / 2, e.y + e.h / 2, 18, "#000000");
                this.enemies.splice(i, 1);

                if (this.shield <= 0) {
                    this.triggerCrashAnomaly("SHIELD_COLLAPSE");
                    return;
                }
                continue;
            }

            if (e.y > this.height + 40) {
                this.enemies.splice(i, 1);
            }
        }

        // Pickups
        for (let i = this.pickups.length - 1; i >= 0; i--) {
            const p = this.pickups[i];
            p.y += p.speed;
            if (this.player.x < p.x + p.w && this.player.x + this.player.w > p.x &&
                this.player.y < p.y + p.h && this.player.y + this.player.h > p.y) {
                this.score += 50;
                this.shield = Math.min(100, this.shield + 20);
                this.createExplosion(p.x + p.w / 2, p.y + p.h / 2, 10, "#000000");
                this.pickups.splice(i, 1);
                if (this.onScoreUpdate) this.onScoreUpdate(this.score);
                continue;
            }
            if (p.y > this.height + 30) {
                this.pickups.splice(i, 1);
            }
        }

        // Particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const pt = this.particles[i];
            pt.x += pt.vx;
            pt.y += pt.vy;
            pt.life -= pt.decay;
            if (pt.life <= 0) {
                this.particles.splice(i, 1);
            }
        }
    }

    render() {
        const ctx = this.ctx;
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, this.width, this.height);

        // Retro subtle grid lines
        ctx.strokeStyle = "#f4f4f5";
        ctx.lineWidth = 1;
        for (let x = 0; x < this.width; x += 40) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.height);
            ctx.stroke();
        }

        // Stars
        this.stars.forEach(s => {
            ctx.fillStyle = "#a1a1aa";
            ctx.fillRect(s.x, s.y, s.size, s.size);
        });

        // Thruster flame trail
        const flameHeight = 10 + Math.random() * 8;
        ctx.fillStyle = "#000000";
        ctx.beginPath();
        ctx.moveTo(this.player.x + 10, this.player.y + this.player.h);
        ctx.lineTo(this.player.x + this.player.w / 2, this.player.y + this.player.h + flameHeight);
        ctx.lineTo(this.player.x + this.player.w - 10, this.player.y + this.player.h);
        ctx.fill();

        // 8-Bit Pixel Rocket
        ctx.fillStyle = "#000000";
        // Main fuselage
        ctx.fillRect(this.player.x + 8, this.player.y + 12, this.player.w - 16, this.player.h - 14);
        // Nosecone
        ctx.beginPath();
        ctx.moveTo(this.player.x + this.player.w / 2, this.player.y);
        ctx.lineTo(this.player.x + 8, this.player.y + 12);
        ctx.lineTo(this.player.x + this.player.w - 8, this.player.y + 12);
        ctx.fill();
        // Left fin
        ctx.beginPath();
        ctx.moveTo(this.player.x + 8, this.player.y + 24);
        ctx.lineTo(this.player.x, this.player.y + this.player.h);
        ctx.lineTo(this.player.x + 8, this.player.y + this.player.h - 6);
        ctx.fill();
        // Right fin
        ctx.beginPath();
        ctx.moveTo(this.player.x + this.player.w - 8, this.player.y + 24);
        ctx.lineTo(this.player.x + this.player.w, this.player.y + this.player.h);
        ctx.lineTo(this.player.x + this.player.w - 8, this.player.y + this.player.h - 6);
        ctx.fill();

        // Rocket window
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(this.player.x + this.player.w / 2 - 3, this.player.y + 18, 6, 8);

        // Lasers
        ctx.fillStyle = "#000000";
        this.lasers.forEach(l => {
            ctx.fillRect(l.x, l.y, l.w, l.h);
        });

        // Hazards / Debris
        this.enemies.forEach(e => {
            ctx.save();
            ctx.translate(e.x + e.w / 2, e.y + e.h / 2);
            ctx.rotate(e.rot);
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 2;
            ctx.fillStyle = "#e4e4e7";

            if (e.type === "METEOR") {
                ctx.beginPath();
                ctx.arc(0, 0, e.w / 2, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
                // inner crater
                ctx.fillStyle = "#000000";
                ctx.fillRect(-4, -4, 6, 6);
            } else {
                ctx.fillRect(-e.w / 2, -e.h / 2, e.w, e.h);
                ctx.strokeRect(-e.w / 2, -e.h / 2, e.w, e.h);
                ctx.fillStyle = "#000000";
                ctx.fillRect(-e.w / 4, -e.h / 4, e.w / 2, e.h / 2);
            }
            ctx.restore();
        });

        // Pickups (Shield / Energy Cells)
        this.pickups.forEach(p => {
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 2;
            ctx.strokeRect(p.x, p.y, p.w, p.h);
            ctx.fillStyle = "#000000";
            ctx.font = "bold 12px monospace";
            ctx.fillText("+", p.x + 5, p.y + 15);
        });

        // Particles
        this.particles.forEach(pt => {
            ctx.fillStyle = pt.color;
            ctx.fillRect(pt.x, pt.y, pt.size, pt.size);
        });

        // HUD Overlay
        ctx.fillStyle = "#000000";
        ctx.font = "bold 13px 'JetBrains Mono', monospace";
        ctx.fillText(`SCORE: ${this.score}`, 16, 26);
        ctx.fillText(`ALT: ${Math.round(this.altitude)}m`, 160, 26);
        ctx.fillText(`TIME: ${this.timeLeft}s`, this.width - 110, 26);

        // Shield bar
        ctx.strokeStyle = "#000000";
        ctx.strokeRect(this.width / 2 - 60, 14, 120, 14);
        ctx.fillStyle = "#000000";
        ctx.fillRect(this.width / 2 - 58, 16, Math.max(0, (this.shield / 100) * 116), 10);
    }

    loop(time) {
        if (!this.isRunning) return;
        const dt = (time - this.lastTime) / 1000;
        this.lastTime = time;

        this.update(dt);
        this.render();

        requestAnimationFrame((t) => this.loop(t));
    }

    triggerCrashAnomaly(reason = "TERMINAL_ANOMALY") {
        this.isRunning = false;
        if (this.timerInterval) clearInterval(this.timerInterval);

        // Create massive explosion
        this.createExplosion(this.player.x + 16, this.player.y + 24, 45, "#000000");
        this.render();

        if (this.onGameOver) {
            this.onGameOver({
                score: this.score,
                altitude: Math.round(this.altitude),
                reason: reason
            });
        }
    }
}

window.SpaceShooterGame = SpaceShooterGame;
