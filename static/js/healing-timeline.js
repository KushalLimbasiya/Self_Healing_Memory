// healing-timeline.js - Render healing history table and summary
window.refreshHealingTimeline = async () => {
    try {
        const [healRes, curRes] = await Promise.all([
            fetch('/api/logs/healing?limit=50').then(r => r.json()),
            fetch('/api/memory/current').then(r => r.json())
        ]);
        
        // Support both old `healing-timeline` div and new `main-heal-log` table
        const tbody = document.getElementById('main-heal-log');
        const legacyContainer = document.getElementById('healing-timeline');
        const container = tbody || legacyContainer;
        
        if (!container) return; // neither element exists, bail out silently
        
        if (!healRes.success || healRes.events.length === 0) {
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:2rem; text-align:center; color:var(--text-muted);">No healing history yet.</td></tr>';
            } else {
                legacyContainer.innerHTML = '<div class="timeline-empty">No healing history yet.</div>';
            }
            return;
        }

        // Clear existing content
        container.innerHTML = '';

        let totalMB = 0;
        let successCount = 0;
        const totalRam = curRes.success && curRes.stats ? curRes.stats.total : (16 * 1024**3); // default 16GB if fail
        
        healRes.events.forEach(event => {
            const timeStr = new Date(event.timestamp).toLocaleString([], {month:'short', day:'numeric', hour: '2-digit', minute:'2-digit', second:'2-digit'});
            const val = event.validation || {};
            const plan = event.plan || {};
            
            // Stats calculation
            const freedMB = (val.freed_percent > 0) ? (totalRam * (val.freed_percent / 100) / (1024**2)) : 0;
            totalMB += freedMB;
            if (val.success !== false) successCount++;
            
            // Actions string
            const actions = (plan.recommended_actions || [])
                .map(a => `<span class="method-tag" style="margin:0 0.2rem 0.2rem 0; font-size:0.75rem; padding:0.2rem 0.5rem;">${a.action}</span>`)
                .join('');
                
            // Trigger: comes from plan.severity (auto / manual / high / moderate etc.)
            const triggerStr = plan.severity || plan.trigger || 'auto';
            
            // Actions executed (from results.actions)
            const executedActions = (event.results && event.results.actions) ? event.results.actions : [];
            const actionsCount = executedActions.length || (plan.recommended_actions || []).length;
            const actionsCountStr = actionsCount > 0 ? actionsCount + ' action' + (actionsCount > 1 ? 's' : '') : '--';
            
            // Status: use validation.effective field, or fall back to freed > threshold
            let statusMarkup = '<span style="color:var(--green)">Effective</span>';
            if (val.effective === false || val.freed_percent < 0.5) {
                statusMarkup = '<span style="color:var(--yellow)">Partial</span>';
            }
                
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="padding:0.75rem 1rem; font-family:var(--font-mono); font-size:0.82rem;">${timeStr}</td>
                <td style="padding:0.75rem 1rem; color:var(--accent); text-transform:capitalize; font-weight:500;">${triggerStr}</td>
                <td style="padding:0.75rem 1rem;">${actions || '--'}</td>
                <td style="padding:0.75rem 1rem; color:var(--green); font-weight:600;">+${freedMB.toFixed(1)} MB</td>
                <td style="padding:0.75rem 1rem; color:var(--text-muted);">${actionsCountStr}</td>
                <td style="padding:0.75rem 1rem; font-weight:500;">${statusMarkup}</td>
            `;
            if (tbody) {
                tbody.appendChild(tr);
            } else {
                // Legacy timeline fallback — render simplified cards
                const item = document.createElement('div');
                item.className = 'timeline-item';
                item.style.padding = '0.8rem 0';
                item.style.borderBottom = '1px solid var(--bg-border)';
                item.style.display = 'flex';
                item.style.justifyContent = 'space-between';
                item.innerHTML = `<span>${timeStr} — ${actions || triggerStr}</span><span style="color:var(--green)">+${freedMB.toFixed(1)} MB</span>`;
                container.appendChild(item);
            }
        });
        
        // Update summary metrics (only available in new HTML)
        const totalCountEl = document.getElementById('healing-total-count');
        const totalMbEl = document.getElementById('healing-total-mb');
        const successRateEl = document.getElementById('healing-success-rate');
        if (totalCountEl) totalCountEl.textContent = healRes.events.length;
        if (totalMbEl) totalMbEl.textContent = totalMB.toFixed(1) + ' MB';
        if (successRateEl) {
            const successRate = ((successCount / healRes.events.length) * 100).toFixed(0);
            successRateEl.textContent = `${successRate}%`;
        }
        
    } catch (e) {
        console.error('Healing log error', e);
    }
};
