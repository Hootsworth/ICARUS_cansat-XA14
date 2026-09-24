/**
 * Interactive Live Contingency Terminal for Phase 4 Finale.
 */

document.addEventListener('DOMContentLoaded', () => {
    const terminalBody = document.getElementById('terminal-body');
    const terminalInput = document.getElementById('terminal-input');
    const commandHistory = [];
    let historyIndex = -1;

    function appendOutput(text, isUser = false) {
        if (!terminalBody) return;
        const line = document.createElement('div');
        line.style.marginBottom = '0.5rem';
        if (isUser) {
            line.style.color = '#ffffff';
            line.textContent = `> ${text}`;
        } else {
            line.style.color = '#38bdf8';
            line.textContent = text;
        }
        terminalBody.appendChild(line);
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }

    async function sendCommand(cmd) {
        if (!cmd.trim()) return;
        appendOutput(cmd, true);
        commandHistory.push(cmd);
        historyIndex = commandHistory.length;

        try {
            const res = await fetch('/api/console', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cmd: cmd.trim() })
            });
            const data = await res.json();
            appendOutput(data.output || 'No response from spacecraft.');
        } catch (e) {
            appendOutput(`[ERROR] Transmission failed: ${e.message}`);
        }
    }

    if (terminalInput) {
        terminalInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const cmd = terminalInput.value;
                terminalInput.value = '';
                sendCommand(cmd);
            } else if (e.key === 'ArrowUp') {
                if (historyIndex > 0) {
                    historyIndex--;
                    terminalInput.value = commandHistory[historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    terminalInput.value = commandHistory[historyIndex];
                } else {
                    historyIndex = commandHistory.length;
                    terminalInput.value = '';
                }
            }
        });
    }

    // Quick Command Chip buttons
    document.querySelectorAll('.cmd-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
            const cmd = btn.getAttribute('data-cmd');
            if (cmd) {
                if (terminalInput) terminalInput.value = cmd;
                sendCommand(cmd);
            }
        });
    });

    // Auto-fetch initial telemetry
    setTimeout(() => sendCommand('GET_HK'), 500);
});
