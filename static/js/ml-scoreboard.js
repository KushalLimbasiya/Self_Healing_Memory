// ml-scoreboard.js - Render ML status page
window.initMLScoreboard = async () => {
    await fetchMLStatus();
    setInterval(fetchMLStatus, 10000); // 10s poll
};

const fetchMLStatus = async () => {
    try {
        const res = await fetch('/api/ml/status');
        const data = await res.json();
        
        if (data.success) {
            updateDetectorStatus(data.anomaly_detector);
            updatePredictorStatus(data.predictor);
            updateScoreboard(data.healer_scoreboard);
        }
    } catch (e) {
        console.error('ML Status load error', e);
    }
};

const updateDetectorStatus = (det) => {
    const typeEl = document.getElementById('ml-detector-type');
    if (typeEl) {
        typeEl.textContent = det.method === 'isolation_forest' ? 'Isolation Forest' : 'Z-Score (Fallback)';
    }
    
    const statusEl = document.getElementById('ml-detector-status');
    if (det.model_ready) {
        statusEl.textContent = 'Active / Trained';
        statusEl.style.color = 'var(--green)';
    } else {
        statusEl.textContent = 'Collecting Data...';
        statusEl.style.color = 'var(--yellow)';
    }
    
    document.getElementById('ml-detector-samples').textContent = `${det.samples_collected} / 500 max`;
};

const updatePredictorStatus = (pred) => {
    const statusEl = document.getElementById('ml-predictor-status');
    if (pred.ready) {
        statusEl.textContent = 'Active (Holt-Winters)';
        statusEl.style.color = 'var(--green)';
    } else {
        statusEl.textContent = 'Bootstrapping (Linear)';
        statusEl.style.color = 'var(--yellow)';
    }
    
    document.getElementById('ml-predictor-samples').textContent = `${pred.samples_in_buffer} / 200 max`;
    document.getElementById('ml-predictor-min').textContent = pred.min_for_holt_winters;
};

const updateScoreboard = (scores) => {
    const tbody = document.getElementById('scoreboard-tbody');
    tbody.innerHTML = '';
    
    if (!scores || scores.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No scores tracked yet</td></tr>';
        return;
    }
    
    scores.forEach((s) => {
        const tr = document.createElement('tr');
        
        // Render score as a mini progress bar
        const pct = (s.score * 100).toFixed(0);
        let barColor = 'var(--accent)';
        if (s.score > 0.6) barColor = 'var(--green)';
        else if (s.score < 0.4) barColor = 'var(--red)';
        
        tr.innerHTML = `
            <td style="font-family: var(--font-mono); font-weight: 500; color: var(--text-main);">${s.action}</td>
            <td>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-family: var(--font-mono); width: 40px;">${s.score.toFixed(3)}</span>
                    <div style="flex:1; height: 6px; background: var(--bg-border); border-radius: 3px; overflow: hidden; max-width: 150px;">
                        <div style="height: 100%; width: ${pct}%; background: ${barColor}"></div>
                    </div>
                </div>
            </td>
            <td style="font-family: var(--font-mono); color: var(--text-muted);">${s.times_used}x</td>
            <td style="font-family: var(--font-mono); color: var(--text-muted);">${s.avg_freed.toFixed(2)}%</td>
        `;
        
        tbody.appendChild(tr);
    });
};
