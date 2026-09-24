/**
 * Live Scoreboard with auto-polling every 10 seconds.
 * Minimalist Flat Black & White Editorial Design.
 */

async function fetchScoreboard() {
    try {
        const res = await fetch('/api/scoreboard');
        if (!res.ok) return;
        const data = await res.json();
        
        const tbody = document.getElementById('scoreboard-tbody');
        const freezeAlert = document.getElementById('freeze-alert');
        
        if (data.frozen && freezeAlert) {
            freezeAlert.style.display = 'flex';
        } else if (freezeAlert) {
            freezeAlert.style.display = 'none';
        }
        
        if (!tbody) return;
        
        let html = '';
        data.standings.forEach((team) => {
            const rankClass = team.rank === 1 ? 'rank-1' : '';
            const solveDate = team.last_solve_ts > 0 ? new Date(team.last_solve_ts).toISOString().substr(11, 8) + ' UTC' : '--:--:--';
            
            html += `
            <tr>
                <td style="width: 60px; text-align: center;">
                    <div class="rank-pill ${rankClass}" style="margin: 0 auto;">${team.rank}</div>
                </td>
                <td style="font-weight: 700; color: #ffffff;">${team.team_name}</td>
                <td class="mono" style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">${team.total_points} PTS</td>
                <td class="mono" style="color: ${team.r1_points > 0 ? '#ffffff' : 'var(--text-dim)'};">${team.r1_points > 0 ? '+' + team.r1_points : '--'}</td>
                <td class="mono" style="color: ${team.r2_points > 0 ? '#ffffff' : 'var(--text-dim)'};">${team.r2_points > 0 ? '+' + team.r2_points : '--'}</td>
                <td class="mono" style="color: ${team.r4_points > 0 ? '#ffffff' : 'var(--text-dim)'};">${team.r4_points > 0 ? '+' + team.r4_points : '--'}</td>
                <td class="mono" style="font-size: 0.78rem; color: var(--text-muted);">
                    P1:${team.phase_progress.PHASE_1} / P2:${team.phase_progress.PHASE_2} / P3:${team.phase_progress.PHASE_3} / B:${team.phase_progress.BONUS} / F:${team.phase_progress.FINALE}
                </td>
                <td class="mono" style="color: var(--text-dim); font-size: 0.8rem;">${solveDate}</td>
            </tr>
            `;
        });
        
        tbody.innerHTML = html;
    } catch (e) {
        console.error("Scoreboard update failed:", e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchScoreboard();
    setInterval(fetchScoreboard, 10000); // Poll every 10 seconds
});
