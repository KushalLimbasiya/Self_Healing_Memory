// forecast-chart.js - Predictor line and UI updates
let forecastChartInstance = null;

window.initForecastChart = async () => {
    await fetchForecast();
    // Poll forecast every 30s
    setInterval(fetchForecast, 30000);
};

const fetchForecast = async () => {
    try {
        const [predRes, curRes] = await Promise.all([
            fetch('/api/memory/predict/latest').then(r => r.json()),
            fetch('/api/memory/current').then(r => r.json())
        ]);
        
        if (predRes.success && predRes.forecast) {
            const totalRam = curRes.stats ? curRes.stats.total : null;
            if (curRes.stats) predRes.forecast.current_used_percent = curRes.stats.used_percent;
            
            updateForecastUI(predRes.forecast, totalRam);
            drawForecastChart(predRes.forecast);
        }
    } catch (e) {
        console.error('Forecast load error', e);
    }
};

const updateForecastUI = (forecast, totalRam) => {
    const cur = forecast.current_used_percent || 0;

    // Current RAM %
    const curEl = document.getElementById('f-current-pct');
    if (curEl) {
        curEl.textContent = cur.toFixed(1) + '%';
        curEl.style.color = cur >= 85 ? 'var(--red)' : cur >= 70 ? 'var(--yellow)' : 'var(--green)';
    }

    // Trend Badge
    const trendEl = document.getElementById('forecast-trend');
    if (trendEl) {
        if (forecast.trend === 'rising') {
            trendEl.textContent = 'RISING ▲'; trendEl.style.color = 'var(--red)';
        } else if (forecast.trend === 'falling') {
            trendEl.textContent = 'FALLING ▼'; trendEl.style.color = 'var(--green)';
        } else {
            trendEl.textContent = 'STABLE ●'; trendEl.style.color = 'var(--yellow)';
        }
    }

    // Method
    const methodEl = document.getElementById('forecast-method');
    if (methodEl) {
        const label = forecast.method === 'holt_winters' ? 'Holt-Winters' :
                      forecast.method === 'linear_regression' ? 'Linear Regression' : forecast.method;
        methodEl.textContent = label;
        const algoEl = document.getElementById('f-model-algo');
        if (algoEl) algoEl.textContent = label;
    }

    // Confidence
    const confValue = (forecast.confidence * 100).toFixed(0);
    const confEl = document.getElementById('forecast-confidence');
    if (confEl) confEl.textContent = `${confValue}%`;
    const confFill = document.getElementById('forecast-confidence-fill');
    if (confFill) {
        confFill.style.width = `${confValue}%`;
        confFill.style.backgroundColor = confValue > 80 ? 'var(--green)' : confValue > 50 ? 'var(--yellow)' : 'var(--red)';
    }

    // Snapshot values
    const p1h = forecast.predicted_1h;
    const p6h = forecast.predicted_6h;
    // Interpolate 3h midpoint
    const p3h = ((p1h + p6h) / 2).toFixed(1);

    const setEl = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    setEl('forecast-1h', p1h.toFixed(1) + '%');
    setEl('forecast-6h', p6h.toFixed(1) + '%');
    setEl('forecast-3h', p3h + '%');

    // Snapshot progress bars
    const setBar = (id, pct) => { const e = document.getElementById(id); if (e) e.style.width = Math.min(100, pct) + '%'; };
    setBar('f-bar-1h', p1h);
    setBar('f-bar-3h', parseFloat(p3h));
    setBar('f-bar-6h', p6h);

    if (totalRam) {
        const mb = (pct) => (totalRam * (pct / 100) / (1024**2)).toFixed(0) + ' MB';
        setEl('forecast-1h-mb', mb(p1h));
        setEl('forecast-3h-mb', mb(parseFloat(p3h)));
        setEl('forecast-6h-mb', mb(p6h));

        // ETA to 90%
        const etaEl = document.getElementById('forecast-eta');
        if (etaEl) {
            if (forecast.trend === 'rising' && p1h > cur) {
                const ratePerHour = p1h - cur;
                const remaining = 90 - cur;
                const hrs = remaining / ratePerHour;
                if (hrs > 0 && hrs < 24) {
                    const h = Math.floor(hrs), m = Math.round((hrs - h) * 60);
                    etaEl.textContent = `${h}h ${m}m`;
                    etaEl.style.color = hrs < 2 ? 'var(--red)' : 'var(--yellow)';
                } else { etaEl.textContent = '> 24 hrs'; etaEl.style.color = 'var(--text-main)'; }
            } else { etaEl.textContent = 'Stable'; etaEl.style.color = 'var(--green)'; }
        }
    }

    // Risk Level
    const riskEl = document.getElementById('f-risk-level');
    if (riskEl) {
        if (cur >= 90 || p1h >= 90) { riskEl.textContent = '🔴 Critical'; riskEl.style.color = 'var(--red)'; }
        else if (cur >= 80 || p1h >= 85) { riskEl.textContent = '🟠 High'; riskEl.style.color = 'var(--red)'; }
        else if (cur >= 70 || p1h >= 75) { riskEl.textContent = '🟡 Moderate'; riskEl.style.color = 'var(--yellow)'; }
        else { riskEl.textContent = '🟢 Low'; riskEl.style.color = 'var(--green)'; }
    }

    // Pressure assessment
    const pressEl = document.getElementById('f-pressure');
    if (pressEl) {
        if (cur >= 85) { pressEl.textContent = 'High'; pressEl.style.color = 'var(--red)'; }
        else if (cur >= 70) { pressEl.textContent = 'Moderate'; pressEl.style.color = 'var(--yellow)'; }
        else { pressEl.textContent = 'Low'; pressEl.style.color = 'var(--green)'; }
    }

    // Deltas
    const d1h = (p1h - cur).toFixed(1);
    const d6h = (p6h - cur).toFixed(1);
    const fmtDelta = (d, id) => {
        const e = document.getElementById(id);
        if (!e) return;
        e.textContent = (d >= 0 ? '+' : '') + d + '%';
        e.style.color = d > 3 ? 'var(--red)' : d < -1 ? 'var(--green)' : 'var(--text-muted)';
    };
    fmtDelta(parseFloat(d1h), 'f-delta-1h');
    fmtDelta(parseFloat(d6h), 'f-delta-6h');

    // Heal recommendation
    const healEl = document.getElementById('f-heal-rec');
    if (healEl) {
        const needsHeal = cur >= 75 || p1h >= 80;
        healEl.textContent = needsHeal ? '⚡ Yes' : '✅ Not yet';
        healEl.style.color = needsHeal ? 'var(--yellow)' : 'var(--green)';
    }
};


const drawForecastChart = async (forecast) => {
    // We need recent history + the two forecast points
    const histRes = await fetch('/api/memory/history?limit=30');
    const histData = await histRes.json();
    if (!histData.success) return;
    
    const history = histData.history.slice().reverse(); // Fetch returns newest first, reverse for chronological chart
    if (history.length === 0) return;
    
    const lastHist = history[history.length - 1];
    const baseTime = new Date(lastHist.timestamp).getTime();
    
    // Build labels and past data
    const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}));
    const pastData = history.map(h => h.used_percent);
    
    // Future points
    labels.push('+1h');
    labels.push('+6h');
    
    const futureData = Array(pastData.length - 1).fill(null);
    futureData.push(lastHist.used_percent); // Connect past -> future
    futureData.push(forecast.predicted_1h);
    futureData.push(forecast.predicted_6h);
    
    // Past data padding
    const pastPadded = [...pastData, null, null];

    const ctx = document.getElementById('forecastChart').getContext('2d');
    
    if (forecastChartInstance) {
        forecastChartInstance.destroy();
    }
    
    forecastChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Historical',
                    data: pastPadded,
                    borderColor: 'rgba(139, 148, 158, 0.5)',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                },
                {
                    label: 'Forecast',
                    data: futureData,
                    borderColor: '#f85149',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    tension: 0.1,
                    pointRadius: 4,
                    pointBackgroundColor: '#f85149'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { 
                    min: 0, 
                    max: 100, 
                    grid: { color: 'rgba(128,128,128,0.1)', drawBorder: false }, 
                    ticks: { color: 'rgba(128,128,128,0.6)', callback: v => v + '%', font: { family: 'Inter' } } 
                },
                x: { 
                    grid: { display: false }, 
                    ticks: { color: 'rgba(128,128,128,0.6)', maxTicksLimit: 12, font: { family: 'Inter' } } 
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: { 
                    backgroundColor: '#16161e',
                    titleColor: 'rgba(255,255,255,0.6)',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: { label: ctx => ctx.parsed.y + '%' } 
                }
            }
        }
    });
};
