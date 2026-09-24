/**
 * Client-side utilities: UTC clock, T-Minus countdown, challenge submission handler.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Live UTC Clock
    const utcDisplay = document.getElementById('live-utc-clock');
    if (utcDisplay) {
        setInterval(() => {
            const now = new Date();
            utcDisplay.textContent = now.toISOString().replace('.000', '').replace('Z', ' UTC');
        }, 1000);
    }

    // 2. T-Minus Competition Countdown (Target: 14:00 UTC / event end)
    const countdownEl = document.getElementById('mission-countdown');
    if (countdownEl) {
        const targetTime = new Date(Date.now() + 3.5 * 3600 * 1000).getTime();
        setInterval(() => {
            const now = Date.now();
            const diff = targetTime - now;
            if (diff <= 0) {
                countdownEl.textContent = "00:00:00 [CLOSED]";
                return;
            }
            const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
            const mins = Math.floor((diff / (1000 * 60)) % 60);
            const secs = Math.floor((diff / 1000) % 60);
            countdownEl.textContent = `T-${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }, 1000);
    }

    // 3. Challenge Submission Handler
    const submitForm = document.getElementById('challenge-submit-form');
    if (submitForm) {
        submitForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const challengeId = document.getElementById('challenge_id').value;
            const answerInput = document.getElementById('answer_input');
            const submitBtn = document.getElementById('submit-btn');
            const statusBox = document.getElementById('submission-status-box');

            if (!answerInput.value.trim()) return;

            submitBtn.disabled = true;
            submitBtn.textContent = "Evaluating Telemetry...";

            try {
                const res = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        challenge_id: challengeId,
                        answer: answerInput.value.trim()
                    })
                });

                const data = await res.json();
                statusBox.style.display = 'block';

                if (res.ok && data.status === 'correct') {
                    statusBox.className = 'alert alert-info';
                    let html = `<strong>CORRECT!</strong> +${data.points_awarded} pts awarded!`;
                    if (data.flag_unlocked) {
                        html += `<br><br><strong>PHASE FLAG UNLOCKED:</strong> <code style="color:#10b981;font-size:1.1rem;">${data.flag_unlocked}</code>`;
                    }
                    statusBox.innerHTML = html;
                    setTimeout(() => window.location.reload(), 3000);
                } else {
                    statusBox.className = 'alert alert-warning';
                    statusBox.innerHTML = `<strong>INCORRECT:</strong> ${data.message || 'Answer rejected by ground station.'}`;
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Transmit Solution";
                }
            } catch (err) {
                statusBox.style.display = 'block';
                statusBox.className = 'alert alert-warning';
                statusBox.textContent = `Submission Error: ${err.message}`;
                submitBtn.disabled = false;
                submitBtn.textContent = "Transmit Solution";
            }
        });
    }
});
