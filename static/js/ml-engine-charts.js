// ml-engine-charts.js — Live charts for Anomaly Detector & Predictor Engine cards
let anomalyChartInst = null;
let predictorChartInst = null;

const ML_CHART_OPTS = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    scales: {
        x: { display: false },
        y: {
            min: 0,
            max: 100,
            grid: { color: 'rgba(128,128,128,0.08)', drawBorder: false },
            ticks: { color: 'rgba(128,128,128,0.55)', font: { size: 10, family: 'Inter' }, callback: v => v + '%', maxTicksLimit: 5 }
        }
    },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: '#16161e',
            titleColor: 'rgba(255,255,255,0.5)',
            bodyColor: '#fff',
            borderColor: 'rgba(255,255,255,0.08)',
            borderWidth: 1,
            padding: 8,
            callbacks: { label: ctx => (ctx.parsed.y !== null ? ctx.parsed.y.toFixed(1) + '%' : '') }
        }
    }
};

/* ── Anomaly Detector Chart ────────────────────────────────────────────────── */
async function drawAnomalyChart() {
    const canvas = document.getElementById('anomaly-chart');
    if (!canvas) return;

    const [histRes, anomRes] = await Promise.all([
        fetch('/api/memory/history?limit=40').then(r => r.json()).catch(() => null),
        fetch('/api/memory/anomalies?limit=100').then(r => r.json()).catch(() => null)
    ]);

    if (!histRes || !histRes.success || histRes.history.length === 0) return;

    const history = histRes.history;
    const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const ramLine = history.map(h => h.used_percent);

    // Build a set of anomaly timestamps for quick lookup
    const anomalyTs = new Set();
    if (anomRes && anomRes.success) {
        anomRes.anomalies.forEach(a => {
            // Match to nearest history point by timestamp prefix (minute-level)
            const t = new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            anomalyTs.add(t);
        });
    }

    // Anomaly highlight points — null where not anomaly, value where anomaly
    const anomalyPoints = history.map((h, i) => {
        const t = new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return anomalyTs.has(t) ? h.used_percent : null;
    });

    const anomalyCount = anomalyPoints.filter(v => v !== null).length;
    const countLabel = document.getElementById('anomaly-count-label');
    if (countLabel) countLabel.textContent = `${anomalyCount} detected`;

    const ctx = canvas.getContext('2d');
    if (anomalyChartInst) anomalyChartInst.destroy();

    anomalyChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'RAM %',
                    data: ramLine,
                    borderColor: 'rgba(88,166,255,0.6)',
                    borderWidth: 1.5,
                    tension: 0.4,
                    pointRadius: 0,
                    fill: {
                        target: 'origin',
                        above: 'rgba(88,166,255,0.07)'
                    }
                },
                {
                    label: 'Anomaly',
                    data: anomalyPoints,
                    borderColor: 'transparent',
                    backgroundColor: '#f85149',
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    pointStyle: 'circle',
                    showLine: false
                }
            ]
        },
        options: ML_CHART_OPTS
    });
}

/* ── Predictor Engine Chart ─────────────────────────────────────────────────── */
async function drawPredictorChart() {
    const canvas = document.getElementById('predictor-chart');
    if (!canvas) return;

    const [histRes, predRes] = await Promise.all([
        fetch('/api/memory/history?limit=30').then(r => r.json()).catch(() => null),
        fetch('/api/memory/predict/latest').then(r => r.json()).catch(() => null)
    ]);

    if (!histRes || !histRes.success || histRes.history.length === 0) return;

    const history = histRes.history.slice().reverse();
    const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    const observed = history.map(h => h.used_percent);

    // Add forecast points
    labels.push('+1h', '+6h');
    const p1h = (predRes && predRes.success && predRes.forecast) ? predRes.forecast.predicted_1h : null;
    const p6h = (predRes && predRes.success && predRes.forecast) ? predRes.forecast.predicted_6h : null;

    // Observed padded + nulls for forecast labels
    const observedPadded = [...observed, null, null];

    // Forecast line connects from last observed point
    const lastVal = observed[observed.length - 1];
    const forecastData = Array(observed.length - 1).fill(null);
    forecastData.push(lastVal); // bridge
    forecastData.push(p1h);
    forecastData.push(p6h);

    // Predictor buffer label
    const bufLabel = document.getElementById('predictor-buffer-label');
    if (bufLabel) {
        const sampleCount = history.length;
        bufLabel.textContent = `${Math.min(sampleCount, 200)} / 200 samples`;
    }

    const ctx = canvas.getContext('2d');
    if (predictorChartInst) predictorChartInst.destroy();

    predictorChartInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Observed',
                    data: observedPadded,
                    borderColor: 'rgba(139,148,158,0.55)',
                    borderWidth: 1.5,
                    tension: 0.3,
                    pointRadius: 0,
                    fill: false
                },
                {
                    label: 'Forecast',
                    data: forecastData,
                    borderColor: '#58a6ff',
                    borderDash: [4, 4],
                    borderWidth: 2,
                    tension: 0.2,
                    pointRadius: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 6],
                    pointBackgroundColor: ['transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', 'transparent', '#58a6ff', '#f0a500'],
                    fill: false
                }
            ]
        },
        options: ML_CHART_OPTS
    });
}

/* ── Public init called by navigation handler ──────────────────────────────── */
window.initMLEngineCharts = async () => {
    await Promise.all([drawAnomalyChart(), drawPredictorChart()]);
    // Refresh every 30 seconds while on this view
    window._mlChartsInterval = setInterval(async () => {
        if (document.getElementById('ml-view')?.classList.contains('active')) {
            await Promise.all([drawAnomalyChart(), drawPredictorChart()]);
        }
    }, 30000);
};
