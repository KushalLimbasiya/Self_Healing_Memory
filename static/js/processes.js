/**
 * processes.js
 * Drives the right-sidebar:
 *  - Compact proc-list (#proc-list)
 *  - CPU card update (called from memory-chart.js)
 *  - Optimizer buttons (#btn-deep-optimize, #btn-quick-heal)
 */

const PROCESS_REFRESH_MS = 8000;

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtMB(mb) {
    if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB';
    return mb.toFixed(0) + ' MB';
}

function barColor(pct) {
    if (pct >= 15) return 'var(--red)';
    if (pct >= 8)  return 'var(--yellow)';
    return 'var(--accent)';
}

function truncate(str, n) {
    return str.length > n ? str.slice(0, n - 1) + '…' : str;
}

function getProcIcon(name) {
    const lName = name.toLowerCase();
    if (lName.includes('chrome') || lName.includes('msedge') || lName.includes('brave') || lName.includes('firefox')) {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4d8aff" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="4"></circle><line x1="21.17" y1="8" x2="12" y2="8"></line><line x1="3.95" y1="6.06" x2="8.54" y2="14"></line><line x1="10.88" y1="21.94" x2="15.46" y2="14"></line></svg>`;
    } else if (lName.includes('code') || lName.includes('idea') || lName.includes('studio')) {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`;
    } else if (lName.includes('python') || lName.includes('node') || lName.includes('java')) {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>`;
    } else if (lName.includes('antigravity')) {
        return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line></svg>`;
    }
    return `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`;
}

// ── Compact sidebar process list ─────────────────────────────────────────────

async function refreshProcList() {
    try {
        const r    = await fetch('/api/memory/processes?limit=8');
        const data = await r.json();
        if (!data.success) return;

        const list = document.getElementById('proc-list');
        if (!list) return;

        list.innerHTML = data.processes.map(p => {
            const pct   = p.mem_pct || 0;
            const color = barColor(pct);
            // cap bar at 100% (pct is % of total RAM, so x5 to amplify small values)
            const barW  = Math.min(100, pct * 5);
            return `
            <div class="proc-item" title="${p.name} (PID ${p.pid})">
                <span class="proc-item-icon" style="display:flex;align-items:center;margin-right:8px">${getProcIcon(p.name)}</span>
                <span class="proc-item-name" style="flex:1">${truncate(p.name, 18)}</span>
                <div class="proc-item-bar-wrap">
                    <div class="proc-item-track">
                        <div class="proc-item-fill" style="width:${barW}%;background:${color};border-radius:3px"></div>
                    </div>
                </div>
                <span class="proc-item-val">${fmtMB(p.mem_mb)}</span>
            </div>`;
        }).join('');
    } catch (e) {
        console.warn('Proc list refresh failed:', e);
    }
}

// ── CPU Card ─────────────────────────────────────────────────────────────────

function updateCpuCard(stats) {
    const el = document.getElementById('dash-cpu-pct');
    if (!el || stats.cpu_percent == null) return;
    const pct = stats.cpu_percent;
    el.textContent = pct.toFixed(1) + '%';
    const card = document.getElementById('cpu-card');
    if (card) {
        card.classList.remove('metric-warn', 'metric-danger');
        if (pct >= 80) card.classList.add('metric-danger');
        else if (pct >= 50) card.classList.add('metric-warn');
    }
}

// ── Optimizer Buttons ────────────────────────────────────────────────────────

function showOptimizerResult(data) {
    document.getElementById('opt-freed').textContent      = (data.freed_mb >= 0 ? '+' : '') + data.freed_mb + ' MB';
    document.getElementById('opt-trimmed').textContent    = data.trimmed;
    document.getElementById('opt-standby').textContent    = data.standby_flushed ? '✅ Yes' : '❌ No (needs admin)';
    document.getElementById('opt-before-after').textContent =
        Math.round(data.before_mb) + ' MB → ' + Math.round(data.after_mb) + ' MB';

    const el = document.getElementById('opt-result');
    if (el) el.style.display = '';
}

async function runOptimize(endpoint, buttonEl) {
    const spinner  = document.getElementById('opt-spinner');
    buttonEl.disabled = true;
    if (spinner) spinner.style.display = '';

    try {
        const r    = await fetch(endpoint, { method: 'POST' });
        const data = await r.json();
        if (data.success) {
            showOptimizerResult(data);
            // refresh proc list immediately after optimize
            await refreshProcList();
        }
    } catch (e) {
        console.error('Optimize failed:', e);
    } finally {
        buttonEl.disabled = false;
        if (spinner) spinner.style.display = 'none';
    }
}

// ── Auto-start ───────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // initial load
    refreshProcList();
    setInterval(refreshProcList, PROCESS_REFRESH_MS);

    // expose for memory-chart.js
    window.updateCpuCard = updateCpuCard;

});
