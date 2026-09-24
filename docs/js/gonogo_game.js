/**
 * ICARUS Go / No-Go Rapid Verification Game Engine
 * 150 Technical, Computational, and Logic Verification Questions
 * Each team receives 20 randomised questions.
 * Rapid fire: Exactly 3.0 seconds per question!
 */

(function () {
    const MASTER_QUESTIONS = [
        { id: 1, text: "2 + 3 = 5", isGo: true },
        { id: 2, text: "2 + 3 = 6", isGo: false },
        { id: 3, text: "10 - 4 = 6", isGo: true },
        { id: 4, text: "10 - 4 = 5", isGo: false },
        { id: 5, text: "3 × 4 = 12", isGo: true },
        { id: 6, text: "3 × 4 = 15", isGo: false },
        { id: 7, text: "20 ÷ 4 = 5", isGo: true },
        { id: 8, text: "20 ÷ 4 = 4", isGo: false },
        { id: 9, text: "2 + 3 × 4 = 14", isGo: true },
        { id: 10, text: "2 + 3 × 4 = 20", isGo: false },
        { id: 11, text: "7 is odd.", isGo: true },
        { id: 12, text: "7 is even.", isGo: false },
        { id: 13, text: "0 is even.", isGo: true },
        { id: 14, text: "0 is odd.", isGo: false },
        { id: 15, text: "12 is divisible by 3.", isGo: true },
        { id: 16, text: "12 is divisible by 5.", isGo: false },
        { id: 17, text: "100 is a perfect square.", isGo: true },
        { id: 18, text: "50 is a perfect square.", isGo: false },
        { id: 19, text: "1 km = 1000 m.", isGo: true },
        { id: 20, text: "1 km = 100 m.", isGo: false },
        { id: 21, text: "1 hour = 60 minutes.", isGo: true },
        { id: 22, text: "1 hour = 100 minutes.", isGo: false },
        { id: 23, text: "Binary 10 = decimal 2.", isGo: true },
        { id: 24, text: "Binary 10 = decimal 10.", isGo: false },
        { id: 25, text: "Binary 111 = decimal 7.", isGo: true },
        { id: 26, text: "Binary 111 = decimal 3.", isGo: false },
        { id: 27, text: "Binary 1000 = decimal 8.", isGo: true },
        { id: 28, text: "Binary 1000 = decimal 1000.", isGo: false },
        { id: 29, text: "Binary uses only 0 and 1.", isGo: true },
        { id: 30, text: "Binary uses 0, 1, and 2.", isGo: false },
        { id: 31, text: "5 % 2 = 1.", isGo: true },
        { id: 32, text: "5 % 2 = 2.", isGo: false },
        { id: 33, text: "10 % 5 = 0.", isGo: true },
        { id: 34, text: "10 % 5 = 5.", isGo: false },
        { id: 35, text: "10 is a multiple of 5.", isGo: true },
        { id: 36, text: "10 is a multiple of 3.", isGo: false },
        { id: 37, text: "15 is a multiple of 3 and 5.", isGo: true },
        { id: 38, text: "15 is a multiple of 2.", isGo: false },
        { id: 39, text: "range(5) gives 0, 1, 2, 3, 4.", isGo: true },
        { id: 40, text: "range(5) gives 1, 2, 3, 4, 5.", isGo: false },
        { id: 41, text: "range(1, 5) gives 1, 2, 3, 4.", isGo: true },
        { id: 42, text: "range(1, 5) gives 1, 2, 3, 4, 5.", isGo: false },
        { id: 43, text: "A loop can run forever if the condition never becomes false.", isGo: true },
        { id: 44, text: "A loop always terminates.", isGo: false },
        { id: 45, text: "while True: runs forever unless it has a break.", isGo: true },
        { id: 46, text: "while True: always stops after 1 iteration.", isGo: false },
        { id: 47, text: "An if statement can exist without else.", isGo: true },
        { id: 48, text: "An else can exist without if.", isGo: false },
        { id: 49, text: "A function can return a value.", isGo: true },
        { id: 50, text: "A function must return a value.", isGo: false },
        { id: 51, text: "A variable can change its value.", isGo: true },
        { id: 52, text: "A constant can change its value.", isGo: false },
        { id: 53, text: "An array can hold multiple values.", isGo: true },
        { id: 54, text: "An array can only hold one value.", isGo: false },
        { id: 55, text: "An array index usually starts at 0.", isGo: true },
        { id: 56, text: "An array index usually starts at 1.", isGo: false },
        { id: 57, text: "arr[0] gets the first element.", isGo: true },
        { id: 58, text: "arr[0] gets the last element.", isGo: false },
        { id: 59, text: "A string is a sequence of characters.", isGo: true },
        { id: 60, text: "A string is a sequence of numbers.", isGo: false },
        { id: 61, text: "len(\"hello\") = 5.", isGo: true },
        { id: 62, text: "len(\"hello\") = 4.", isGo: false },
        { id: 63, text: "\"a\" + \"b\" = \"ab\".", isGo: true },
        { id: 64, text: "\"a\" + \"b\" = \"a b\".", isGo: false },
        { id: 65, text: "5 + 5 = 10.", isGo: true },
        { id: 66, text: "\"5\" + \"5\" = \"55\" in most languages.", isGo: true },
        { id: 67, text: "\"5\" + \"5\" = 10 in most languages.", isGo: false },
        { id: 68, text: "Integer division 7 // 2 = 3.", isGo: true },
        { id: 69, text: "Integer division 7 // 2 = 3.5.", isGo: false },
        { id: 70, text: "2 ** 3 = 8.", isGo: true },
        { id: 71, text: "2 ** 3 = 6.", isGo: false },
        { id: 72, text: "Square root of 9 is 3.", isGo: true },
        { id: 73, text: "Square root of 9 is 4.5.", isGo: false },
        { id: 74, text: "A prime number has exactly 2 divisors.", isGo: true },
        { id: 75, text: "A prime number has more than 2 divisors.", isGo: false },
        { id: 76, text: "1 is a prime number.", isGo: false },
        { id: 77, text: "2 is a prime number.", isGo: true },
        { id: 78, text: "4 is a prime number.", isGo: false },
        { id: 79, text: "If A > B and B > C, then A > C.", isGo: true },
        { id: 80, text: "If A > B and B > C, then A < C.", isGo: false },
        { id: 81, text: "If A = B and B = C, then A = C.", isGo: true },
        { id: 82, text: "If A = B and B = C, then A ≠ C.", isGo: false },
        { id: 83, text: "All dogs are animals. Rex is a dog. Rex is an animal.", isGo: true },
        { id: 84, text: "All dogs are animals. Rex is an animal. Rex is a dog.", isGo: false },
        { id: 85, text: "All squares are rectangles. This shape is a square. It's a rectangle.", isGo: true },
        { id: 86, text: "All squares are rectangles. This shape is a rectangle. It's a square.", isGo: false },
        { id: 87, text: "All students have IDs. You're a student. You have an ID.", isGo: true },
        { id: 88, text: "All students have IDs. You have an ID. You're a student.", isGo: false },
        { id: 89, text: "If it rains, the ground gets wet. It rained. The ground is wet.", isGo: true },
        { id: 90, text: "If it rains, the ground gets wet. The ground is wet. It rained.", isGo: false },
        { id: 91, text: "Some birds can't fly. Penguins are birds. Penguins can't fly.", isGo: true },
        { id: 92, text: "All birds can fly. Penguins are birds. Penguins can fly.", isGo: false },
        { id: 93, text: "If X is even, X+1 is odd.", isGo: true },
        { id: 94, text: "If X is even, X+1 is even.", isGo: false },
        { id: 95, text: "If X is odd, X+1 is even.", isGo: true },
        { id: 96, text: "If X is odd, X+1 is odd.", isGo: false },
        { id: 97, text: "Two even numbers add to an even number.", isGo: true },
        { id: 98, text: "Two even numbers add to an odd number.", isGo: false },
        { id: 99, text: "Two odd numbers add to an even number.", isGo: true },
        { id: 100, text: "Two odd numbers add to an odd number.", isGo: false },
        { id: 101, text: "An even + odd = odd.", isGo: true },
        { id: 102, text: "An even + odd = even.", isGo: false },
        { id: 103, text: "You can store text in a variable.", isGo: true },
        { id: 104, text: "You can store a number in a variable.", isGo: true },
        { id: 105, text: "You can store a variable in a variable (stores value).", isGo: true },
        { id: 106, text: "A program must have at least one line of code.", isGo: true },
        { id: 107, text: "An empty program is valid in most languages.", isGo: true },
        { id: 108, text: "Every program must print something.", isGo: false },
        { id: 109, text: "Comments are ignored by the compiler.", isGo: true },
        { id: 110, text: "Comments change program output.", isGo: false },
        { id: 111, text: "A syntax error prevents a program from running.", isGo: true },
        { id: 112, text: "A logic error prevents a program from running.", isGo: false },
        { id: 113, text: "A runtime error occurs while the program is running.", isGo: true },
        { id: 114, text: "A runtime error occurs before the program starts.", isGo: false },
        { id: 115, text: "A variable name can start with a number.", isGo: false },
        { id: 116, text: "A variable name can start with a letter.", isGo: true },
        { id: 117, text: "A variable name can contain underscores.", isGo: true },
        { id: 118, text: "A variable name can contain spaces.", isGo: false },
        { id: 119, text: "A function can take arguments.", isGo: true },
        { id: 120, text: "A function can return multiple values in Python.", isGo: true },
        { id: 121, text: "A function can return multiple values in C directly.", isGo: false },
        { id: 122, text: "Recursion is when a function calls itself.", isGo: true },
        { id: 123, text: "Recursion needs a base case to stop.", isGo: true },
        { id: 124, text: "Recursion works without any stopping condition.", isGo: false },
        { id: 125, text: "A stack follows LIFO.", isGo: true },
        { id: 126, text: "A stack follows FIFO.", isGo: false },
        { id: 127, text: "A queue follows FIFO.", isGo: true },
        { id: 128, text: "A queue follows LIFO.", isGo: false },
        { id: 129, text: "You can push to a stack.", isGo: true },
        { id: 130, text: "You can push to a queue (enqueue).", isGo: true },
        { id: 131, text: "A binary tree node has at most 2 children.", isGo: true },
        { id: 132, text: "A binary tree node has exactly 2 children.", isGo: false },
        { id: 133, text: "A linked list can grow dynamically.", isGo: true },
        { id: 134, text: "A linked list has fixed size.", isGo: false },
        { id: 135, text: "An array has fixed size in most languages.", isGo: true },
        { id: 136, text: "Searching an unsorted array takes O(n) in the worst case.", isGo: true },
        { id: 137, text: "Searching an unsorted array takes O(1) in the worst case.", isGo: false },
        { id: 138, text: "Binary search requires a sorted array.", isGo: true },
        { id: 139, text: "Binary search works on unsorted arrays.", isGo: false },
        { id: 140, text: "Sorting helps searching.", isGo: true },
        { id: 141, text: "Sorting makes searching slower.", isGo: false },
        { id: 142, text: "A hash map stores key-value pairs.", isGo: true },
        { id: 143, text: "A hash map stores only values.", isGo: false },
        { id: 144, text: "A hash map lookup is usually fast.", isGo: true },
        { id: 145, text: "A hash map lookup is always O(n).", isGo: false },
        { id: 146, text: "Two identical inputs to a function always give the same output.", isGo: true },
        { id: 147, text: "A function can give different outputs for the same input.", isGo: true },
        { id: 148, text: "A program can have more than one function.", isGo: true },
        { id: 149, text: "A program can have only one function.", isGo: true },
        { id: 150, text: "A program must have a main function in every language.", isGo: false }
    ];

    class GoNoGoGame {
        constructor(containerId) {
            this.container = document.getElementById(containerId);
            this.currentIndex = 0;
            this.score = 0;
            this.streak = 0;
            this.maxStreak = 0;
            this.questionTimer = null;
            this.timeRemainingMs = 3000;
            this.progressInterval = null;
            this.isRunning = false;
            this.answers = [];
            this.selectedQuestions = [];

            this.handleKeyDown = this.handleKeyDown.bind(this);
        }

        start() {
            // Pick 20 randomized questions from the pool of 150
            const shuffled = [...MASTER_QUESTIONS].sort(() => Math.random() - 0.5);
            this.selectedQuestions = shuffled.slice(0, 20);

            this.currentIndex = 0;
            this.score = 0;
            this.streak = 0;
            this.maxStreak = 0;
            this.isRunning = true;
            this.answers = [];

            window.addEventListener("keydown", this.handleKeyDown);
            this.renderUI();
            this.renderCard();
        }

        renderUI() {
            this.container.innerHTML = `
                <div style="background: #18181b; border: 1px solid #27272a; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem;">
                    <!-- Top stats header -->
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #27272a; padding-bottom: 1rem; margin-bottom: 1.25rem;">
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span class="badge mono" id="gng-step-badge" style="background: #27272a; color: #ffffff; border-radius: 8px;">QUESTION 1 / 20</span>
                            <span class="badge mono" id="gng-streak-badge" style="background: #000000; color: #a1a1aa; border-radius: 8px;">STREAK: 0</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 1rem;">
                            <div class="mono" style="font-size: 1.2rem; font-weight: 800; color: #ffffff;" id="gng-score-display">0 PTS</div>
                            <div class="mono" style="font-size: 1rem; font-weight: 700; color: #f59e0b; background: #27272a; padding: 4px 12px; border-radius: 8px; min-width: 75px; text-align: center;" id="gng-timer">3.0s</div>
                        </div>
                    </div>

                    <!-- 3-Second Visual Progress Bar -->
                    <div style="width: 100%; height: 6px; background: #27272a; border-radius: 3px; overflow: hidden; margin-bottom: 1.25rem;">
                        <div id="gng-progress-bar" style="width: 100%; height: 100%; background: #10b981; transition: width 0.05s linear;"></div>
                    </div>

                    <!-- Active Decision Card Container -->
                    <div id="gng-card-mount"></div>

                    <!-- Big Dual Decision Controls -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1.5rem;">
                        <button type="button" onclick="window.activeGoNoGo.makeDecision(true)" class="btn" style="background: #10b981; color: #ffffff; border-radius: 12px; padding: 1.15rem; font-size: 1.15rem; font-weight: 800; border: none; cursor: pointer; transition: transform 0.1s ease;">
                            ✅ GO (HOTKEY: G / &larr;)
                        </button>
                        <button type="button" onclick="window.activeGoNoGo.makeDecision(false)" class="btn" style="background: #ef4444; color: #ffffff; border-radius: 12px; padding: 1.15rem; font-size: 1.15rem; font-weight: 800; border: none; cursor: pointer; transition: transform 0.1s ease;">
                            ❌ NO-GO (HOTKEY: N / &rarr;)
                        </button>
                    </div>

                    <!-- Keyboard hotkey tip -->
                    <div style="text-align: center; margin-top: 0.85rem;">
                        <span class="mono" style="font-size: 0.74rem; color: #71717a;">Rapid Fire: Exactly 3 seconds per statement! [G] / Left Arrow for GO &bull; [N] / Right Arrow for NO-GO</span>
                    </div>
                </div>
            `;
        }

        renderCard() {
            if (this.currentIndex >= this.selectedQuestions.length) {
                this.finish();
                return;
            }

            const item = this.selectedQuestions[this.currentIndex];
            const mount = document.getElementById("gng-card-mount");
            const stepBadge = document.getElementById("gng-step-badge");
            const streakBadge = document.getElementById("gng-streak-badge");

            if (stepBadge) stepBadge.textContent = `QUESTION ${this.currentIndex + 1} / 20`;
            if (streakBadge) streakBadge.textContent = `STREAK: ${this.streak}`;

            if (mount) {
                mount.innerHTML = `
                    <div id="active-poll-card" style="background: #09090b; border: 2px solid #27272a; border-radius: 14px; padding: 2rem 1.75rem; text-align: center; transition: all 0.15s ease;">
                        <div class="eyebrow" style="color: #38bdf8; font-size: 0.72rem; margin-bottom: 0.75rem;">
                            [RAPID VERIFICATION #0${this.currentIndex + 1}]
                        </div>
                        <div style="font-size: 1.45rem; font-weight: 700; line-height: 1.4; color: #ffffff; min-height: 58px; display: flex; align-items: center; justify-content: center;">
                            ${item.text}
                        </div>
                        <div id="gng-feedback-msg" class="mono" style="font-size: 0.8rem; margin-top: 0.75rem; min-height: 20px; color: #71717a;">
                            Decide GO or NO-GO within 3 seconds...
                        </div>
                    </div>
                `;
            }

            this.start3sTimer();
        }

        start3sTimer() {
            if (this.questionTimer) clearTimeout(this.questionTimer);
            if (this.progressInterval) clearInterval(this.progressInterval);

            this.timeRemainingMs = 3000;
            const startTime = Date.now();
            const totalMs = 3000;

            const timerEl = document.getElementById("gng-timer");
            const barEl = document.getElementById("gng-progress-bar");

            this.progressInterval = setInterval(() => {
                const elapsed = Date.now() - startTime;
                const remaining = Math.max(0, totalMs - elapsed);
                const secs = (remaining / 1000).toFixed(1);

                if (timerEl) {
                    timerEl.textContent = `${secs}s`;
                    if (remaining <= 1000) {
                        timerEl.style.color = "#ef4444";
                    } else {
                        timerEl.style.color = "#f59e0b";
                    }
                }

                if (barEl) {
                    const pct = Math.max(0, (remaining / totalMs) * 100);
                    barEl.style.width = `${pct}%`;
                    barEl.style.background = remaining <= 1000 ? "#ef4444" : "#10b981";
                }

                if (remaining <= 0) {
                    clearInterval(this.progressInterval);
                }
            }, 40);

            // Timeout after 3.0s: counts as missed/timeout
            this.questionTimer = setTimeout(() => {
                clearInterval(this.progressInterval);
                this.handleTimeout();
            }, totalMs);
        }

        handleTimeout() {
            if (!this.isRunning || this.currentIndex >= this.selectedQuestions.length) return;

            const item = this.selectedQuestions[this.currentIndex];
            const cardEl = document.getElementById("active-poll-card");
            const feedbackEl = document.getElementById("gng-feedback-msg");

            this.streak = 0;
            if (cardEl) {
                cardEl.style.borderColor = "#ef4444";
                cardEl.style.boxShadow = "0 0 20px rgba(239, 68, 68, 0.25)";
            }
            if (feedbackEl) {
                feedbackEl.style.color = "#ef4444";
                feedbackEl.textContent = `⏰ TIME OUT: Answer was ${item.isGo ? 'GO' : 'NO-GO'}`;
            }

            this.answers.push({
                question: item.text,
                userChoice: null,
                correctChoice: item.isGo,
                isCorrect: false
            });

            this.currentIndex++;
            setTimeout(() => {
                this.renderCard();
            }, 300);
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
            if (!this.isRunning || this.currentIndex >= this.selectedQuestions.length) return;

            // Clear timers
            if (this.questionTimer) clearTimeout(this.questionTimer);
            if (this.progressInterval) clearInterval(this.progressInterval);

            const item = this.selectedQuestions[this.currentIndex];
            const isCorrect = (userChoice === item.isGo);
            const cardEl = document.getElementById("active-poll-card");
            const feedbackEl = document.getElementById("gng-feedback-msg");

            if (isCorrect) {
                this.streak++;
                if (this.streak > this.maxStreak) this.maxStreak = this.streak;
                // 20 questions total, 5 pts each = 100 PTS max
                this.score += 5;
                if (cardEl) {
                    cardEl.style.borderColor = "#10b981";
                    cardEl.style.boxShadow = "0 0 20px rgba(16, 185, 129, 0.25)";
                }
                if (feedbackEl) {
                    feedbackEl.style.color = "#10b981";
                    feedbackEl.textContent = `✓ CORRECT: ${item.isGo ? 'GO' : 'NO-GO'}`;
                }
            } else {
                this.streak = 0;
                if (cardEl) {
                    cardEl.style.borderColor = "#ef4444";
                    cardEl.style.boxShadow = "0 0 20px rgba(239, 68, 68, 0.25)";
                }
                if (feedbackEl) {
                    feedbackEl.style.color = "#ef4444";
                    feedbackEl.textContent = `✕ INCORRECT: Statement is ${item.isGo ? 'GO' : 'NO-GO'}`;
                }
            }

            this.answers.push({
                question: item.text,
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
            }, 300);
        }

        finish() {
            this.isRunning = false;
            if (this.questionTimer) clearTimeout(this.questionTimer);
            if (this.progressInterval) clearInterval(this.progressInterval);
            window.removeEventListener("keydown", this.handleKeyDown);

            const finalScore = Math.min(100, Math.round(this.score));
            const passed = finalScore >= 50;

            this.container.innerHTML = `
                <div style="background: #18181b; border: 1px solid #27272a; border-radius: 16px; padding: 2.5rem; text-align: center;">
                    <div class="mono" style="font-size: 2.5rem; margin-bottom: 0.5rem;">${passed ? "🚀" : "⚠️"}</div>
                    <div class="eyebrow" style="color: ${passed ? '#10b981' : '#f59e0b'}; font-size: 0.8rem; margin-bottom: 0.5rem;">
                        ${passed ? "[ROUND 1 / LAUNCH POLL CERTIFIED]" : "[ROUND 1 / LAUNCH SCRUBBED]"}
                    </div>
                    <h2 style="font-size: 1.6rem; color: #ffffff; margin-bottom: 0.5rem;">Go / No-Go Poll Completed</h2>
                    <p style="color: #a1a1aa; font-size: 0.88rem; max-width: 500px; margin: 0 auto 1.5rem;">
                        ${passed ? "20 rapid-fire verification statements evaluated. Station verified and cleared for Blackbox Telemetry Analysis." : "Review foundational logic before requesting re-attempt."}
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
                            Confirm Score & Advance to Telemetry Analysis &rarr;
                        </button>
                    </div>
                </div>
            `;
        }
    }

    window.GoNoGoGame = GoNoGoGame;
})();
