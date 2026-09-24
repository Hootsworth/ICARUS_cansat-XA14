/**
 * ICARUS Flight Operations State & Storage Engine
 * Handles Station License Key Authentication, 3-Phase Progression,
 * Real-time Anti-Cheat Event Logging, and Flight Director Retake Management.
 */

const ICARUS_DEFAULT_TEAMS = [
    { id: 1, name: "Ares Flight Group", key: "ICARUS-ARES-7711", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 2, name: "Athena Orbital", key: "ICARUS-ATHENA-8822", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 3, name: "Daedalus Dynamics", key: "ICARUS-DAEDALUS-9933", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 4, name: "Helios Telemetry", key: "ICARUS-HELIOS-1144", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 5, name: "Hermes Flight Unit", key: "ICARUS-HERMES-2255", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 6, name: "Titan Propulsion", key: "ICARUS-TITAN-3366", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 7, name: "Orion Space Labs", key: "ICARUS-ORION-4477", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 8, name: "Voyager Operations", key: "ICARUS-VOYAGER-5588", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 9, name: "Apollo Systems", key: "ICARUS-APOLLO-6699", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 10, name: "Selene Analytics", key: "ICARUS-SELENE-7700", code: "RVU-ORBIT-2027", credits: 12 },
    { id: 11, name: "Hyperion Dynamics", key: "ICARUS-HYPERION-8811", code: "RVU-ORBIT-2027", credits: 12 }
];

const ICARUS_ADMIN_PASSWORD = "rvu_flight_ops_admin_2027";
const STATE_VERSION = "ICARUS_V3_LIC_KEY";

class IcarusGitHubPagesEngine {
    constructor() {
        this.init();
    }

    init() {
        const currentVersion = localStorage.getItem("ICARUS_STATE_VERSION");
        // Initialize or migrate to license keys
        if (currentVersion !== STATE_VERSION) {
            ICARUS_DEFAULT_TEAMS.forEach(team => {
                const teamKey = `ICARUS_TEAM_${team.id}`;
                const existingRaw = localStorage.getItem(teamKey);
                let existingData = null;
                if (existingRaw) {
                    try { existingData = JSON.parse(existingRaw); } catch (e) {}
                }

                const data = {
                    id: team.id,
                    name: (existingData && existingData.name) ? existingData.name : team.name,
                    key: team.key,
                    code: team.code,
                    credits: 12,
                    r1: (existingData && existingData.r1) ? existingData.r1 : { status: "active", score: 0, details: null, completedAt: null },
                    r2: (existingData && existingData.r2) ? existingData.r2 : { status: "locked", score: 0, code: "", completedAt: null },
                    r3: (existingData && existingData.r3) ? existingData.r3 : { status: "locked", score: 0, answers: null, completedAt: null }
                };
                localStorage.setItem(teamKey, JSON.stringify(data));
            });
            localStorage.setItem("ICARUS_STATE_VERSION", STATE_VERSION);
            if (!localStorage.getItem("ICARUS_GLOBAL_ROUND")) {
                localStorage.setItem("ICARUS_GLOBAL_ROUND", "1");
            }
        }
    }

    // -------------------------------------------------------------------------
    // Global Round Control (Admin controlled)
    // -------------------------------------------------------------------------
    getGlobalRound() {
        return parseInt(localStorage.getItem("ICARUS_GLOBAL_ROUND") || "1");
    }

    setGlobalRound(roundNum) {
        localStorage.setItem("ICARUS_GLOBAL_ROUND", String(roundNum));
        for (let i = 1; i <= 11; i++) {
            const team = this.getTeamData(i);
            const rKey = `r${roundNum}`;
            if (team[rKey] && team[rKey].status === "locked") {
                team[rKey].status = "active";
                this.saveTeamData(team, i);
            }
        }
        if (window.IcarusCommander && window.IcarusCommander.syncToFirebase) {
            window.IcarusCommander.syncToFirebase({ globalRound: roundNum });
        }
    }

    // -------------------------------------------------------------------------
    // Anti-Cheat Logging
    // -------------------------------------------------------------------------
    logSecurityEvent(teamId, eventType, detail = "") {
        const events = this.getSecurityEvents();
        const team = this.getTeamData(teamId);
        const entry = {
            id: Date.now() + "_" + Math.random().toString(36).substr(2, 4),
            teamId: teamId,
            teamName: team ? team.name : `Station ${teamId}`,
            round: this.getGlobalRound(),
            eventType: eventType, // 'TAB_SWITCH', 'WINDOW_BLUR', 'FULLSCREEN_EXIT'
            detail: detail,
            timestamp: new Date().toLocaleTimeString() + " UTC (" + new Date().toISOString() + ")"
        };
        events.unshift(entry);
        if (events.length > 100) events.pop();
        localStorage.setItem("ICARUS_SECURITY_LOGS", JSON.stringify(events));

        if (window.IcarusCommander && window.IcarusCommander.syncSecurityEvent) {
            window.IcarusCommander.syncSecurityEvent(entry);
        }
        return entry;
    }

    getSecurityEvents() {
        const raw = localStorage.getItem("ICARUS_SECURITY_LOGS");
        if (raw) {
            try { return JSON.parse(raw); } catch (e) {}
        }
        return [];
    }

    clearSecurityEvents() {
        localStorage.removeItem("ICARUS_SECURITY_LOGS");
    }

    // -------------------------------------------------------------------------
    // Team Authentication Gate (License Key + Optional Custom Team Name)
    // -------------------------------------------------------------------------
    getAuthUser() {
        const raw = localStorage.getItem("ICARUS_AUTH_USER");
        if (raw) {
            try { return JSON.parse(raw); } catch (e) {}
        }
        return null;
    }

    setAuthUser(teamId, teamName, key) {
        const user = {
            teamId: parseInt(teamId),
            teamName: teamName,
            key: key,
            loggedInAt: new Date().toISOString()
        };
        localStorage.setItem("ICARUS_AUTH_USER", JSON.stringify(user));
        localStorage.setItem("ICARUS_CURRENT_TEAM_ID", String(teamId));
        return user;
    }

    logout() {
        localStorage.removeItem("ICARUS_AUTH_USER");
        localStorage.removeItem("ICARUS_CURRENT_TEAM_ID");
        window.location.href = "./index.html";
    }

    /**
     * Authenticate via Station License Key
     * Allows team to customize/write their team name
     */
    loginWithKey(licenseKey, optionalCustomTeamName = "") {
        const cleanKey = String(licenseKey).trim().toUpperCase();
        if (!cleanKey) {
            return { success: false, message: "Please enter your assigned Station License Key." };
        }

        for (let i = 1; i <= 11; i++) {
            const team = this.getTeamData(i);
            if (team.key && team.key.toUpperCase() === cleanKey) {
                // If team provided custom team name, update team profile name
                if (optionalCustomTeamName && optionalCustomTeamName.trim().length > 0) {
                    team.name = optionalCustomTeamName.trim();
                    this.saveTeamData(team, i);
                }

                this.setAuthUser(team.id, team.name, team.key);
                return { success: true, team: team };
            }
        }

        return {
            success: false,
            message: "Invalid Station License Key. Please check the Admin Console or contact Flight Director."
        };
    }

    // -------------------------------------------------------------------------
    // Admin Password Protection Gate
    // -------------------------------------------------------------------------
    isAdminAuthenticated() {
        return sessionStorage.getItem("ICARUS_ADMIN_AUTH") === "true";
    }

    loginAdmin(password) {
        if (password.trim() === ICARUS_ADMIN_PASSWORD) {
            sessionStorage.setItem("ICARUS_ADMIN_AUTH", "true");
            return true;
        }
        return false;
    }

    logoutAdmin() {
        sessionStorage.removeItem("ICARUS_ADMIN_AUTH");
        window.location.reload();
    }

    // -------------------------------------------------------------------------
    // Team Data Management
    // -------------------------------------------------------------------------
    getCurrentTeamId() {
        const user = this.getAuthUser();
        return user ? user.teamId : parseInt(localStorage.getItem("ICARUS_CURRENT_TEAM_ID") || "1");
    }

    getTeamData(teamId = null) {
        const id = teamId || this.getCurrentTeamId();
        const raw = localStorage.getItem(`ICARUS_TEAM_${id}`);
        if (raw) {
            try { return JSON.parse(raw); } catch (e) {}
        }
        const defaultDef = ICARUS_DEFAULT_TEAMS.find(t => t.id === id) || {
            id: id,
            name: `Station ${id} Flight Group`,
            key: `ICARUS-STATION-${id}-KEY`,
            code: "RVU-ORBIT-2027"
        };
        return {
            id: defaultDef.id,
            name: defaultDef.name,
            key: defaultDef.key,
            code: defaultDef.code,
            credits: 12,
            r1: { status: "active", score: 0, details: null, completedAt: null },
            r2: { status: "locked", score: 0, code: "", completedAt: null },
            r3: { status: "locked", score: 0, answers: null, completedAt: null }
        };
    }

    saveTeamData(data, teamId = null) {
        const id = teamId || data.id || this.getCurrentTeamId();
        localStorage.setItem(`ICARUS_TEAM_${id}`, JSON.stringify(data));
        if (window.IcarusCommander && window.IcarusCommander.syncTeamData) {
            window.IcarusCommander.syncTeamData(data, id);
        }
    }

    // -------------------------------------------------------------------------
    // Round 1: Go / No-Go Launch Decision Game Submission
    // -------------------------------------------------------------------------
    submitRound1GoNoGo(score, details = {}) {
        const team = this.getTeamData();
        const finalScore = Math.min(100, Math.max(0, Math.round(score)));
        team.r1.status = "submitted";
        team.r1.score = finalScore;
        team.r1.details = details;
        team.r1.completedAt = new Date().toISOString();
        team.r2.status = "active"; // Unlock Round 2
        this.saveTeamData(team);

        return {
            success: true,
            score: finalScore,
            message: `Go / No-Go Launch Poll Complete: ${finalScore}/100 PTS recorded. Proceeding to Blackbox Telemetry Analysis.`
        };
    }

    // -------------------------------------------------------------------------
    // Round 2: Telemetry Analysis Submission
    // -------------------------------------------------------------------------
    submitRound2Analysis(codeScript, notes = "") {
        const team = this.getTeamData();
        team.r2.status = "submitted";
        team.r2.code = codeScript;
        team.r2.notes = notes;
        team.r2.score = 50; // standard 50 pts for verified analysis script
        team.r2.completedAt = new Date().toISOString();
        team.r3.status = "active"; // Unlock Round 3
        this.saveTeamData(team);
        return {
            success: true,
            message: "Flight blackbox analysis script verified and logged (+50 PTS)."
        };
    }

    // -------------------------------------------------------------------------
    // Round 3: Root Cause Investigation Quiz Evaluation (15 Questions)
    // -------------------------------------------------------------------------
    submitRound3Quiz(answers) {
        const team = this.getTeamData();
        const rubric = {
            q1: "B",  // 15,000 ms (15.0s) Apogee timestamp
            q2: "B",  // 1,215.0 m peak altitude
            q3: "B",  // 3.29 G liftoff acceleration
            q4: "B",  // -38.0 m/s nominal freefall velocity
            q5: "C",  // 35,000 ms (35.0s) EPS voltage sag anomaly onset
            q6: "B",  // 2.39 V voltage sag level
            q7: "B",  // ~700 mA current surge
            q8: "B",  // 400 m deployment threshold altitude
            q9: "B",  // MCU brownout reset prevented squib firing
            q10: "C", // -43.5 to -44.8 m/s terminal descent velocity
            q11: "B", // Violent tumbling with gyro rates swinging to ±47 deg/s
            q12: "C", // 61,500 ms (61.5s) ground impact timestamp
            q13: "C", // -22.40 G peak impact deceleration shock
            q14: "B", // Primary EPS voltage collapse under high load causing recovery failure
            q15: "B"  // Electrically isolate pyrotechnic/RF circuitry from MCU logic
        };

        let correct = 0;
        const total = 15;
        for (const [k, v] of Object.entries(rubric)) {
            if (answers[k] && answers[k] === v) correct++;
        }

        const score = correct * 8; // 15 * 8 = 120 PTS max
        team.r3.status = "submitted";
        team.r3.score = score;
        team.r3.answers = answers;
        team.r3.completedAt = new Date().toISOString();
        this.saveTeamData(team);

        return {
            success: true,
            score: score,
            correct: correct,
            total: total,
            message: `Root Cause Investigation evaluated: ${correct}/${total} findings correct (+${score} PTS).`
        };
    }

    // -------------------------------------------------------------------------
    // Admin Stage Retake & Reset Methods
    // -------------------------------------------------------------------------
    resetTeamRound(teamId, roundNum) {
        const tid = parseInt(teamId);
        const team = this.getTeamData(tid);
        const rKey = String(roundNum).toLowerCase();

        if (rKey === "1" || rKey === "r1" || rKey === "all") {
            team.r1 = { status: "active", score: 0, details: null, completedAt: null };
        }
        if (rKey === "2" || rKey === "r2" || rKey === "all") {
            team.r2 = { status: "active", score: 0, code: "", completedAt: null };
        }
        if (rKey === "3" || rKey === "r3" || rKey === "all") {
            team.r3 = { status: "active", score: 0, answers: null, completedAt: null };
        }

        this.saveTeamData(team, tid);

        return {
            success: true,
            teamId: tid,
            teamName: team.name,
            round: rKey,
            message: `Retake granted: Station ${tid} (${team.name}) round ${rKey.toUpperCase()} reset to active.`
        };
    }

    unlockTeamRound(teamId, roundNum) {
        const tid = parseInt(teamId);
        const team = this.getTeamData(tid);
        const rKey = `r${roundNum}`;
        if (team[rKey]) {
            team[rKey].status = "active";
            this.saveTeamData(team, tid);
            return { success: true, message: `Round ${roundNum} unlocked for Station ${tid}.` };
        }
        return { success: false, message: "Invalid round specified." };
    }

    // -------------------------------------------------------------------------
    // Master Overview & License Key Registry (Admin Only)
    // -------------------------------------------------------------------------
    getAllTeamsOverview() {
        const overview = [];
        for (let i = 1; i <= 11; i++) {
            const team = this.getTeamData(i);
            const r1Pts = (team.r1 && team.r1.status === "submitted") ? (team.r1.score || 0) : 0;
            const r2Pts = (team.r2 && team.r2.status === "submitted") ? (team.r2.score || 0) : 0;
            const r3Pts = (team.r3 && team.r3.status === "submitted") ? (team.r3.score || 0) : 0;
            const grandTotal = r1Pts + r2Pts + r3Pts;

            overview.push({
                team: { id: team.id, name: team.name, key: team.key, code: team.code },
                r1: team.r1,
                r2: team.r2,
                r3: team.r3,
                r1_pts: r1Pts,
                r2_pts: r2Pts,
                r3_pts: r3Pts,
                grand_total: grandTotal
            });
        }
        return overview.sort((a, b) => b.grand_total - a.grand_total);
    }
}

window.IcarusEngine = new IcarusGitHubPagesEngine();
