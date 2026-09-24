/**
 * ICARUS Real-Time Multi-Computer State Synchronization & Firebase Auth
 * Syncs Flight Director timer commands & announcements across all team screens.
 * Uses Firebase Firestore real-time onSnapshot with smart local REST polling fallback.
 */

(function () {
    // Current state cache
    const compState = {
        timerRunning: false,
        timerEndsAt: 0,
        timerTitle: "STANDBY",
        activeRound: 1,
        announcement: "",
        announcementId: "",
        localTimerInterval: null
    };

    // UI elements
    let countdownEl = null;
    let announcementBanner = null;

    function initUI() {
        countdownEl = document.getElementById("mission-countdown");

        // Create announcement banner element if not present
        if (!document.getElementById("icarus-announcement-banner")) {
            announcementBanner = document.createElement("div");
            announcementBanner.id = "icarus-announcement-banner";
            announcementBanner.style.cssText = `
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #09090b;
                color: #ffffff;
                padding: 0.75rem 1.5rem;
                font-family: var(--font-mono, monospace);
                font-size: 0.85rem;
                font-weight: 700;
                z-index: 9999;
                border-bottom: 2px solid #38bdf8;
                box-shadow: 0 8px 24px rgba(0,0,0,0.5);
                justify-content: space-between;
                align-items: center;
            `;
            document.body.appendChild(announcementBanner);
        } else {
            announcementBanner = document.getElementById("icarus-announcement-banner");
        }
    }

    function applyState(state) {
        if (!state) return;

        compState.timerRunning = !!state.timer_running;
        compState.timerEndsAt = parseInt(state.timer_ends_at || 0);
        compState.timerTitle = state.timer_title || "FLIGHT OPS";
        compState.activeRound = state.active_round || 1;

        // Auto sync active round to local engine if changed
        if (window.IcarusEngine && state.active_round && window.IcarusEngine.getGlobalRound() !== state.active_round) {
            localStorage.setItem("ICARUS_GLOBAL_ROUND", String(state.active_round));
            if (typeof renderCurrentStage === "function") {
                renderCurrentStage();
            }
        }

        // 1. Handle Announcement Banner
        if (state.announcement && state.announcement.trim()) {
            if (announcementBanner) {
                announcementBanner.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="background: #38bdf8; color: #000000; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 800;">BROADCAST</span>
                        <span>${state.announcement}</span>
                    </div>
                    <button onclick="document.getElementById('icarus-announcement-banner').style.display='none'" style="background:transparent; border:none; color:#a1a1aa; font-family:monospace; font-weight:700; cursor:pointer; font-size:0.9rem;">[DISMISS ✕]</button>
                `;
                announcementBanner.style.display = "flex";
            }
        } else {
            if (announcementBanner) announcementBanner.style.display = "none";
        }

        // 2. Start / Update local countdown loop
        if (compState.localTimerInterval) {
            clearInterval(compState.localTimerInterval);
        }

        compState.localTimerInterval = setInterval(updateCountdownDisplay, 1000);
        updateCountdownDisplay();
    }

    function updateCountdownDisplay() {
        if (!countdownEl) {
            countdownEl = document.getElementById("mission-countdown");
            if (!countdownEl) return;
        }

        if (!compState.timerRunning || !compState.timerEndsAt) {
            countdownEl.textContent = `[ROUND ${compState.activeRound}: STANDBY]`;
            countdownEl.style.borderColor = "#3f3f46";
            countdownEl.style.color = "#a1a1aa";
            return;
        }

        const now = Date.now();
        const diff = compState.timerEndsAt - now;

        if (diff <= 0) {
            countdownEl.textContent = `00:00:00 [ROUND ${compState.activeRound} TIME EXPIRED]`;
            countdownEl.style.borderColor = "#ef4444";
            countdownEl.style.color = "#ef4444";
            return;
        }

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const mins = Math.floor((diff / (1000 * 60)) % 60);
        const secs = Math.floor((diff / 1000) % 60);

        const timeStr = (hours > 0 ? `${hours}:` : "") +
            `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;

        countdownEl.textContent = `T-${timeStr} [${compState.timerTitle}]`;
        countdownEl.style.borderColor = "#ffffff";
        countdownEl.style.color = "#ffffff";
    }

    // -------------------------------------------------------------------------
    // Fallback Local Polling
    // -------------------------------------------------------------------------
    async function pollLocalState() {
        try {
            const res = await fetch("/api/competition/state");
            if (res.ok) {
                const data = await res.json();
                applyState(data);
            }
        } catch (e) {
            // Local server offline or on static hosting
        }
    }

    // -------------------------------------------------------------------------
    // Firebase Firestore Realtime Connection & Multi-Device Sync
    // -------------------------------------------------------------------------
    async function initFirebaseSync() {
        const isConfigured = window.IcarusFirebase && window.IcarusFirebase.isConfigured();
        if (!isConfigured) {
            console.log("[ICARUS SYNC] Firebase not yet configured or using local fallback.");
            setInterval(pollLocalState, 2500);
            pollLocalState();
            return;
        }

        try {
            const { initializeApp } = await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js");
            const { getFirestore, doc, onSnapshot, setDoc, getDoc, collection, onSnapshot: onCollectionSnapshot } = await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js");
            const { getAuth, signInAnonymously, onAuthStateChanged } = await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-auth.js");

            const cfg = window.IcarusFirebase.getConfig();
            const app = initializeApp(cfg);
            const db = getFirestore(app);
            const auth = getAuth(app);

            // Optional Analytics initialization
            try {
                const { getAnalytics, isSupported } = await import("https://www.gstatic.com/firebasejs/10.8.0/firebase-analytics.js");
                if (await isSupported()) {
                    window.IcarusFirebase.analytics = getAnalytics(app);
                }
            } catch (anErr) {
                // Analytics is optional for web app state sync
            }

            window.IcarusFirebase.app = app;
            window.IcarusFirebase.db = db;
            window.IcarusFirebase.auth = auth;
            window.IcarusFirebase.isInitialized = true;

            console.log("[ICARUS SYNC] Connected to Firebase Firestore real-time channel:", cfg.projectId);

            // Anonymous auth to ensure Firestore security rules allow read/write
            try {
                await signInAnonymously(auth);
                console.log("[ICARUS SYNC] Authenticated anonymously to Firebase.");
            } catch (authErr) {
                console.warn("[ICARUS SYNC] Anonymous auth notice:", authErr);
            }

            // Expose Commander API for Admin Console
            window.IcarusCommander = {
                async startTimer(roundNum, minutes, title) {
                    const now = Date.now();
                    const duration_s = minutes * 60;
                    const endsAt = now + (duration_s * 1000);
                    const statePayload = {
                        timer_running: true,
                        timer_ends_at: endsAt,
                        timer_duration_s: duration_s,
                        timer_title: title || `ROUND ${roundNum}`,
                        active_round: roundNum,
                        updated_at: new Date().toISOString()
                    };

                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), statePayload, { merge: true });
                    } catch (err) {
                        console.warn("[Firebase write error]", err);
                    }
                },

                async pauseTimer() {
                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), { timer_running: false }, { merge: true });
                    } catch (e) {}
                },

                async resetTimer() {
                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), { timer_running: false, timer_ends_at: 0 }, { merge: true });
                    } catch (e) {}
                },

                async broadcast(message) {
                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), {
                            announcement: message,
                            announcement_id: String(Date.now())
                        }, { merge: true });
                    } catch (e) {}
                },

                async clearBroadcast() {
                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), {
                            announcement: "",
                            announcement_id: ""
                        }, { merge: true });
                    } catch (e) {}
                },

                async syncToFirebase(payload) {
                    try {
                        await setDoc(doc(db, "icarus_competition", "state"), payload, { merge: true });
                    } catch (e) {}
                },

                async syncSecurityEvent(entry) {
                    try {
                        await setDoc(doc(db, "icarus_security_logs", String(entry.id)), entry);
                    } catch (e) {}
                },

                async syncTeamData(teamData, teamId) {
                    try {
                        await setDoc(doc(db, "icarus_teams", `team_${teamId}`), teamData, { merge: true });
                    } catch (e) {}
                }
            };

            // Firestore real-time listener for mission state & timer
            onSnapshot(doc(db, "icarus_competition", "state"), (snapshot) => {
                if (snapshot.exists()) {
                    const data = snapshot.data();
                    applyState(data);
                }
            }, (error) => {
                console.warn("[ICARUS SYNC] Snapshot error:", error);
            });

            // Sync teams from Firestore into local cache if on Admin Console
            onCollectionSnapshot(collection(db, "icarus_teams"), (snapshot) => {
                snapshot.forEach(docSnap => {
                    const data = docSnap.data();
                    if (data && data.id) {
                        const local = localStorage.getItem(`ICARUS_TEAM_${data.id}`);
                        // Merge or update local team data
                        localStorage.setItem(`ICARUS_TEAM_${data.id}`, JSON.stringify(data));
                    }
                });
                if (typeof renderAdminStandings === "function") {
                    renderAdminStandings();
                }
            });

            // Sync security feed
            onCollectionSnapshot(collection(db, "icarus_security_logs"), (snapshot) => {
                const logs = [];
                snapshot.forEach(docSnap => logs.push(docSnap.data()));
                logs.sort((a, b) => (b.id || "").localeCompare(a.id || ""));
                localStorage.setItem("ICARUS_SECURITY_LOGS", JSON.stringify(logs.slice(0, 100)));
                if (typeof renderSecurityFeed === "function") {
                    renderSecurityFeed();
                }
            });

        } catch (err) {
            console.warn("[ICARUS SYNC] Firebase initialization error, falling back:", err);
            setInterval(pollLocalState, 3000);
            pollLocalState();
        }
    }

    // Initialize on DOM load
    document.addEventListener("DOMContentLoaded", () => {
        initUI();
        initFirebaseSync();
    });
})();
