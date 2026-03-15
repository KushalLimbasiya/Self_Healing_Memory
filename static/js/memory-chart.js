// memory-chart.js - Dashboard Real-time Chart
let memoryChartInstance = null;
let memoryChartData = {
    labels: [],
    datasets: [{
        label: 'Memory Used %',
        data: [],
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88, 166, 255, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointBackgroundColor: [],
        pointBorderColor: [],
        pointRadius: [],
    }]
};

window.initMemoryChart = async () => {
    const ctx = document.getElementById('memoryChart').getContext('2d');
    
    // Gradient for the area
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(37, 99, 235, 0.25)'); // deep blue
    gradient.addColorStop(1, 'rgba(37, 99, 235, 0.0)');
    memoryChartData.datasets[0].backgroundColor = gradient;
    memoryChartData.datasets[0].borderColor = '#3b82f6';
    memoryChartData.datasets[0].tension = 0.45;

    memoryChartInstance = new Chart(ctx, {
        type: 'line',
        data: memoryChartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: {
                y: { 
                    min: 0, 
                    max: 100, 
                    grid: { color: 'rgba(255,255,255,0.04)', drawBorder: false }, 
                    ticks: { color: 'rgba(255,255,255,0.4)', callback: v => v + '%', font: { family: 'Inter' } } 
                },
                x: { 
                    grid: { display: false }, 
                    ticks: { color: 'rgba(255,255,255,0.4)', maxTicksLimit: 8, font: { family: 'Inter' } } 
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
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) { label += ': '; }
                            if (context.parsed.y !== null) { label += context.parsed.y + '%'; }
                            return label;
                        }
                    }
                }
            }
        }
    });

    // Load initial history
    try {
        const res = await fetch('/api/memory/history?limit=100');
        const data = await res.json();
        if (data.success && data.history) {
            data.history.forEach(item => {
                const time = new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
                memoryChartData.labels.push(time);
                memoryChartData.datasets[0].data.push(item.used_percent);
                
                // Keep points hidden unless they are anomalies (we don't have historical anomaly markers here, so just base color)
                memoryChartData.datasets[0].pointBackgroundColor.push('#58a6ff');
                memoryChartData.datasets[0].pointBorderColor.push('#161b22');
                memoryChartData.datasets[0].pointRadius.push(0); // hide normal points
            });
            memoryChartInstance.update();
        }
    } catch (e) { console.error('History load error:', e); }

    // Load recent anomalies for the table
    try {
        const resA = await fetch('/api/memory/anomalies?limit=10');
        const dataA = await resA.json();
        if (dataA.success && dataA.anomalies) {
            // anomalies come back descending from the DB, so we iterate in reverse
            // because addAnomalyToTable inserts at the top of the table.
            dataA.anomalies.reverse().forEach(anom => {
                addAnomalyToTable(anom.timestamp, anom.used_percent, anom.severity, anom.method);
            });
        }
    } catch (e) {
        console.error('Anomalies load error:', e);
    }
};

window.updateMemoryChart = (currentData) => {
    if (!memoryChartInstance) return;
    
    const { stats, analysis } = currentData;
    const time = new Date(stats.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    
    memoryChartData.labels.push(time);
    memoryChartData.datasets[0].data.push(stats.used_percent);
    
    const isAnomaly = analysis.anomaly && analysis.anomaly.is_anomaly;
    if (isAnomaly) {
        memoryChartData.datasets[0].pointBackgroundColor.push('#f85149');
        memoryChartData.datasets[0].pointBorderColor.push('#fff');
        memoryChartData.datasets[0].pointRadius.push(6); // Show anomaly big
    } else {
        memoryChartData.datasets[0].pointBackgroundColor.push('#58a6ff');
        memoryChartData.datasets[0].pointBorderColor.push('#161b22');
        memoryChartData.datasets[0].pointRadius.push(0); // Hide normal
    }

    // Keep max points based on selected range
    const maxPoints = window.chartPointLimit || 100;
    if (memoryChartData.labels.length > maxPoints) {
        memoryChartData.labels.shift();
        memoryChartData.datasets[0].data.shift();
        memoryChartData.datasets[0].pointBackgroundColor.shift();
        memoryChartData.datasets[0].pointBorderColor.shift();
        memoryChartData.datasets[0].pointRadius.shift();
    }
    
    memoryChartInstance.update();

    // Update the CPU card (defined in processes.js)
    if (typeof window.updateCpuCard === 'function') {
        window.updateCpuCard(stats);
    }

    // Also update anomalies table if there's an anomaly this tick
    if (isAnomaly) {
        addAnomalyToTable(stats.timestamp, stats.used_percent, analysis.severity, analysis.anomaly.method);
    }
};

const addAnomalyToTable = (timestamp, used, severity, method) => {
    const tbody = document.getElementById('anomalies-tbody');
    // Clear "No recent" if present
    if (tbody.querySelector('.text-center')) {
        tbody.innerHTML = '';
    }
    
    const tr = document.createElement('tr');
    const timeStr = new Date(timestamp).toLocaleTimeString();
    let sevBadge = `<span class="badge ${severity === 'critical' ? 'red' : (severity === 'high' ? 'yellow' : 'green')}">${severity}</span>`;
    
    tr.innerHTML = `
        <td>${timeStr}</td>
        <td style="font-family: var(--font-mono);">${used.toFixed(1)}%</td>
        <td>${sevBadge}</td>
        <td><span class="badge" style="background: rgba(255,255,255,0.1)">${method}</span></td>
    `;
    
    tbody.insertBefore(tr, tbody.firstChild);
    
    // limit 10
    if (tbody.children.length > 10) {
        tbody.removeChild(tbody.lastChild);
    }
    
    // Update badge count
    const badge = document.getElementById('anomaly-badge');
    badge.textContent = parseInt(badge.textContent) + 1;
};
