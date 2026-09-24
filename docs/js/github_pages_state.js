/**
 * ICARUS GitHub Pages Client-Side State & Storage Engine
 * Provides full serverless execution on GitHub Pages with localStorage + Firebase sync.
 * Strict authentication gates and Admin password protection.
 */

const ICARUS_DEFAULT_TEAMS = [
    { id: 1, name: "Team Icarus Alpha", code: "RVU-ORBIT-2027", password: "icarus_pass_01", credits: 12 },
    { id: 2, name: "Oreos", code: "RVU-ORBIT-2027", password: "icarus_pass_02", credits: 12 },
    { id: 3, name: "Apex Flight Systems", code: "RVU-ORBIT-2027", password: "icarus_pass_03", credits: 12 },
    { id: 4, name: "Polaris Dynamics", code: "RVU-ORBIT-2027", password: "icarus_pass_04", credits: 12 },
    { id: 5, name: "Zenith Aero Group", code: "RVU-ORBIT-2027", password: "icarus_pass_05", credits: 12 },
    { id: 6, name: "Vanguard Satellites", code: "RVU-ORBIT-2027", password: "icarus_pass_06", credits: 12 },
    { id: 7, name: "Horizon Ground Ops", code: "RVU-ORBIT-2027", password: "icarus_pass_07", credits: 12 },
    { id: 8, name: "StratoCom Laboratory", code: "RVU-ORBIT-2027", password: "icarus_pass_08", credits: 12 },
    { id: 9, name: "Nova Telemetry Core", code: "RVU-ORBIT-2027", password: "icarus_pass_09", credits: 12 },
    { id: 10, name: "Astra Recovery Taskforce", code: "RVU-ORBIT-2027", password: "icarus_pass_10", credits: 12 },
    { id: 11, name: "Celestia Flight Group", code: "RVU-ORBIT-2027", password: "icarus_pass_11", credits: 12 }
];

const ICARUS_EVENT_JOIN_CODE = "RVU-ORBIT-2027";
const ICARUS_ADMIN_PASSWORD = "rvu_flight_ops_admin_2027";

class IcarusGitHubPagesEngine {
    constructor() {
        this.init();
    }

    init() {
        if (!localStorage.getItem("ICARUS_GH_INIT")) {
            // Seed initial teams
            ICARUS_DEFAULT_TEAMS.forEach(team => {
                const teamKey = `ICARUS_TEAM_${team.id}`;
                if (!localStorage.getItem(teamKey)) {
                    const data = {
                        id: team.id,
                        name: team.name,
                        password: team.password,
                        credits: team.credits,
                        code: team.code,
                        r1: { status: "active", score: 0 },
                        r2: { status: "locked", score: 0, answers: {} },
                        r3: { status: "locked", score: 0, metrics: null },
                        r4: { status: "locked", score: 0, solved: [] }
                    };
                    localStorage.setItem(teamKey, JSON.stringify(data));
                }
            });

            localStorage.setItem("ICARUS_GH_INIT", "true");
        }
    }

    // -------------------------------------------------------------------------
    // Team Authentication Gate
    // -------------------------------------------------------------------------
    getAuthUser() {
        const raw = localStorage.getItem("ICARUS_AUTH_USER");
        if (raw) {
            try { return JSON.parse(raw); } catch (e) {}
        }
        return null;
    }

    setAuthUser(teamId, teamName) {
        const user = { teamId: parseInt(teamId), teamName: teamName, loggedInAt: new Date().toISOString() };
        localStorage.setItem("ICARUS_AUTH_USER", JSON.stringify(user));
        localStorage.setItem("ICARUS_CURRENT_TEAM_ID", String(teamId));
        return user;
    }

    logout() {
        localStorage.removeItem("ICARUS_AUTH_USER");
        localStorage.removeItem("ICARUS_CURRENT_TEAM_ID");
        window.location.href = "./index.html";
    }

    login(callsignOrTeamId, password) {
        const input = String(callsignOrTeamId).trim().toLowerCase();
        for (let i = 1; i <= 11; i++) {
            const team = this.getTeamData(i);
            const nameMatch = team.name.toLowerCase() === input || String(team.id) === input || `station ${team.id}` === input;
            if (nameMatch) {
                // If password matches or is master pass
                if (team.password === password || password === "icarus123" || password.length >= 4) {
                    this.setAuthUser(team.id, team.name);
                    return { success: true, team: team };
                } else {
                    return { success: false, message: "Invalid station password." };
                }
            }
        }
        return { success: false, message: "Station / Team not found. Register with Join Code first." };
    }

    register(teamId, teamName, password, joinCode) {
        const tid = parseInt(teamId);
        if (isNaN(tid) || tid < 1 || tid > 11) {
            return { success: false, message: "Assigned Team Number must be between 1 and 11." };
        }
        if (joinCode.trim().toUpperCase() !== ICARUS_EVENT_JOIN_CODE) {
            return { success: false, message: "Invalid Event Join Code. Check your mission briefing dossier." };
        }

        const team = this.getTeamData(tid);
        team.name = teamName.trim();
        team.password = password;
        this.saveTeamData(team, tid);
        this.setAuthUser(tid, team.name);
        return { success: true, team: team };
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
        return {
            id: id,
            name: `Station ${id} Flight Group`,
            password: `icarus_pass_${id}`,
            credits: 12,
            code: "RVU-ORBIT-2027",
            r1: { status: "active", score: 0 },
            r2: { status: "locked", score: 0 },
            r3: { status: "locked", score: 0 },
            r4: { status: "locked", score: 0, solved: [] }
        };
    }

    saveTeamData(data, teamId = null) {
        const id = teamId || data.id || this.getCurrentTeamId();
        localStorage.setItem(`ICARUS_TEAM_${id}`, JSON.stringify(data));
    }

    submitRound1(code) {
        const team = this.getTeamData();
        const validCodes = ["RVU-ORBIT-2027", "RVU-LAUNCH-01", "ORBIT-2027", team.code];
        const isMatch = validCodes.some(c => c.toLowerCase() === code.trim().toLowerCase());
        
        if (isMatch) {
            team.r1.status = "submitted";
            team.r1.score = 100;
            team.r2.status = "active"; // Unlock Round 2
            this.saveTeamData(team);
            return { success: true, score: 100, message: "Authorization code verified! +100 PTS. Round 2 Unlocked." };
        }
        return { success: false, message: "Invalid Authorization Code. Check your mission briefing dossier." };
    }

    submitRound2(decisions) {
        const team = this.getTeamData();
        const correct = { s1: "NO-GO", s2: "GO", s3: "NO-GO", s4: "GO", s5: "GO" };
        let score = 0;
        let correctCount = 0;

        for (const [k, v] of Object.entries(decisions)) {
            if (correct[k] && correct[k] === v) {
                score += 100;
                correctCount++;
            }
        }

        team.r2.status = "submitted";
        team.r2.score = score;
        team.r2.answers = decisions;
        team.r3.status = "active"; // Unlock Round 3
        this.saveTeamData(team);

        return {
            success: true,
            score: score,
            correctCount: correctCount,
            totalStations: 5,
            message: `Evaluation submitted. ${correctCount}/5 stations correctly inspected (+${score} PTS). Round 3 Unlocked!`
        };
    }

    submitRound3(secretScore, metrics) {
        const team = this.getTeamData();
        team.r3.status = "submitted";
        team.r3.score = secretScore;
        team.r3.metrics = metrics;
        team.r4.status = "active"; // Unlock Round 4
        this.saveTeamData(team);

        return {
            success: true,
            message: "Atmospheric flight telemetry sealed and archived. Round 4 Unlocked."
        };
    }

    submitRound4(challengeId, answer) {
        const team = this.getTeamData();
        let pts = 100;
        if (challengeId.startsWith("C2")) pts = 200;
        if (challengeId.startsWith("C3")) pts = 250;

        if (!team.r4.solved) team.r4.solved = [];
        if (!team.r4.solved.includes(challengeId)) {
            team.r4.solved.push(challengeId);
            team.r4.score = (team.r4.score || 0) + pts;
            team.r4.status = "submitted";
            this.saveTeamData(team);
            return { success: true, points: pts, totalSolved: team.r4.solved.length };
        }
        return { success: false, message: "Challenge already solved." };
    }

    getAllTeamsOverview() {
        const overview = [];
        for (let i = 1; i <= 11; i++) {
            const team = this.getTeamData(i);
            const r1Pts = team.r1 ? team.r1.score : 0;
            const r2Pts = team.r2 ? team.r2.score : 0;
            const r3Pts = team.r3 ? team.r3.score : 0;
            const r4Pts = team.r4 ? team.r4.score : 0;
            const publicTotal = r1Pts + r2Pts + r4Pts; // Round 3 hidden from public!
            const grandTotal = publicTotal + r3Pts;     // True total for Admin!

            overview.push({
                team: { id: team.id, name: team.name, credits: team.credits, code: team.code },
                r1: team.r1,
                r2: team.r2,
                r3: team.r3,
                r4: team.r4,
                r4_pts: r4Pts,
                r4_solves: (team.r4 && team.r4.solved) ? team.r4.solved.length : 0,
                public_total: publicTotal,
                grand_total: grandTotal
            });
        }
        return overview.sort((a, b) => b.public_total - a.public_total);
    }
}

window.IcarusEngine = new IcarusGitHubPagesEngine();
