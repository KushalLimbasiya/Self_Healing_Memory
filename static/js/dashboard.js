// Global variables
let memoryChart;
let currentLogType = 'memory';

// Helper function to format bytes
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0 || bytes === undefined) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Helper function to format timestamps
function formatTimestamp(isoTimestamp) {
    const date = new Date(isoTimestamp);
    return date.toLocaleTimeString();
}

// Initialize the memory chart
function initMemoryChart() {
    const ctx = document.getElementById('memoryChart').getContext('2d');
    
    memoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Memory Usage (%)',
                data: [],
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Used Memory (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
}

// Update the memory chart with new data
function updateMemoryChart(historyData) {
    // Extract timestamps and used percentages
    const timestamps = historyData.map(entry => formatTimestamp(entry.timestamp));
    const usedPercentages = historyData.map(entry => entry.used_percent);
    
    // Update chart data
    memoryChart.data.labels = timestamps;
    memoryChart.data.datasets[0].data = usedPercentages;
    
    // Update chart
    memoryChart.update();
}

// Update the memory usage display
function updateMemoryUsage(stats) {
    const usedPercent = stats.used_percent;
    
    // Update progress bar
    const progressBar = document.getElementById('memoryUsageBar');
    progressBar.style.width = `${usedPercent}%`;
    progressBar.innerText = `${usedPercent.toFixed(1)}%`;
    
    // Set color based on usage level
    if (usedPercent > 90) {
        progressBar.className = 'progress-bar bg-danger';
    } else if (usedPercent > 70) {
        progressBar.className = 'progress-bar bg-warning';
    } else {
        progressBar.className = 'progress-bar bg-success';
    }
    
    // Update text display
    document.getElementById('memoryUsageText').innerText = `${usedPercent.toFixed(1)}%`;
    
    // Update details
    const detailsText = `Total: ${formatBytes(stats.total)} | Free: ${formatBytes(stats.free)}`;
    document.getElementById('memoryDetailsText').innerText = detailsText;
    
    // Update system information
    document.getElementById('totalMemory').innerText = formatBytes(stats.total);
    document.getElementById('freeMemory').innerText = formatBytes(stats.free);
    document.getElementById('availableMemory').innerText = formatBytes(stats.available);
    
    // Show buffers and cached if available
    if (stats.buffers !== undefined && stats.buffers !== null) {
        document.getElementById('buffers').innerText = formatBytes(stats.buffers);
    } else {
        document.getElementById('buffers').innerText = 'N/A';
    }
    
    if (stats.cached !== undefined && stats.cached !== null) {
        document.getElementById('cached').innerText = formatBytes(stats.cached);
    } else {
        document.getElementById('cached').innerText = 'N/A';
    }
    
    // Update status icon and text based on usage
    const statusIcon = document.getElementById('statusIcon');
    const statusText = document.getElementById('statusText');
    const statusDescription = document.getElementById('statusDescription');
    
    if (usedPercent > 90) {
        statusIcon.className = 'fas fa-exclamation-triangle fa-4x mb-2 text-danger';
        statusText.innerText = 'Critical';
        statusDescription.innerText = 'Memory usage is critically high';
    } else if (usedPercent > 80) {
        statusIcon.className = 'fas fa-exclamation-circle fa-4x mb-2 text-warning';
        statusText.innerText = 'Warning';
        statusDescription.innerText = 'Memory usage is high';
    } else if (usedPercent > 60) {
        statusIcon.className = 'fas fa-info-circle fa-4x mb-2 text-info';
        statusText.innerText = 'Moderate';
        statusDescription.innerText = 'Memory usage is moderate';
    } else {
        statusIcon.className = 'fas fa-check-circle fa-4x mb-2 text-success';
        statusText.innerText = 'Normal';
        statusDescription.innerText = 'Memory usage is normal';
    }
    
    // Update last updated timestamp
    document.getElementById('lastUpdated').innerText = 'Last updated: ' + new Date().toLocaleTimeString();
}

// Fetch the current memory statistics
function fetchMemoryStats() {
    fetch('/api/memory/current')
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                updateMemoryUsage(result.data);
            } else {
                console.error('Error fetching memory stats:', result.error);
            }
        })
        .catch(error => {
            console.error('Error fetching memory stats:', error);
        });
}

// Fetch memory history data
function fetchMemoryHistory() {
    fetch('/api/memory/history')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.data.length > 0) {
                updateMemoryChart(result.data);
            } else {
                console.error('Error fetching memory history or no data available');
            }
        })
        .catch(error => {
            console.error('Error fetching memory history:', error);
        });
}

// Analyze memory conditions
function analyzeMemory() {
    const resultElement = document.getElementById('analyzeResult');
    
    // Show loading state
    resultElement.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-info" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Analyzing memory...</span>
        </div>
    `;
    
    fetch('/api/memory/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const analysis = result.analysis;
            
            let statusClass = 'success';
            if (analysis.anomaly_detected) {
                statusClass = analysis.severity === 'critical' ? 'danger' : 
                             (analysis.severity === 'high' ? 'warning' : 'info');
            }
            
            // Check if we should show the anomaly modal
            if (analysis.anomaly_detected && (analysis.severity === 'critical' || analysis.severity === 'high')) {
                // Update the modal content
                document.getElementById('anomalySeverity').innerText = analysis.severity.charAt(0).toUpperCase() + analysis.severity.slice(1);
                document.getElementById('anomalyDescription').innerText = analysis.anomaly_description || 'Unusual memory behavior detected';
                
                // Show the modal
                const anomalyModal = new bootstrap.Modal(document.getElementById('anomalyModal'));
                anomalyModal.show();
            }
            
            // Update the analysis result
            resultElement.innerHTML = `
                <div class="alert alert-${statusClass} mb-2">
                    <strong>Status:</strong> ${analysis.anomaly_detected ? 'Anomaly Detected' : 'Normal'}
                </div>
                ${analysis.anomaly_detected ? `
                    <div class="alert alert-${statusClass}">
                        <strong>Severity:</strong> ${analysis.severity || 'Unknown'}<br>
                        <strong>Description:</strong> ${analysis.anomaly_description || 'No description available'}<br>
                        ${analysis.recommendation ? `<strong>Recommendation:</strong> ${analysis.recommendation}` : ''}
                    </div>
                ` : '<p>No memory anomalies detected at this time.</p>'}
            `;
        } else {
            resultElement.innerHTML = `
                <div class="alert alert-danger">
                    Error analyzing memory: ${result.error}
                </div>
            `;
        }
    })
    .catch(error => {
        resultElement.innerHTML = `
            <div class="alert alert-danger">
                Error analyzing memory: ${error.message}
            </div>
        `;
    });
}

// Generate memory prediction
function predictMemory() {
    const resultElement = document.getElementById('predictResult');
    
    // Show loading state
    resultElement.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-warning" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Generating prediction...</span>
        </div>
    `;
    
    fetch('/api/memory/predict', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const prediction = result.prediction;
            
            // Update the prediction card
            const predictionIcon = document.getElementById('predictionIcon');
            const predictionText = document.getElementById('predictionText');
            const predictionDescription = document.getElementById('predictionDescription');
            
            // Determine status based on prediction
            const hasCriticalIssues = prediction.predicted_issues.some(issue => issue.severity === 'critical');
            const hasHighIssues = prediction.predicted_issues.some(issue => issue.severity === 'high');
            
            if (hasCriticalIssues) {
                predictionIcon.className = 'fas fa-exclamation-triangle fa-4x mb-2 text-danger';
                predictionText.innerText = 'Critical Issues Predicted';
                predictionDescription.innerText = 'Serious memory issues expected soon';
            } else if (hasHighIssues) {
                predictionIcon.className = 'fas fa-exclamation-circle fa-4x mb-2 text-warning';
                predictionText.innerText = 'Issues Predicted';
                predictionDescription.innerText = 'Memory issues may occur soon';
            } else if (prediction.predicted_memory_usage_1h > 80) {
                predictionIcon.className = 'fas fa-chart-line fa-4x mb-2 text-info';
                predictionText.innerText = 'High Usage Predicted';
                predictionDescription.innerText = `Predicted usage: ${prediction.predicted_memory_usage_1h.toFixed(1)}% in 1 hour`;
            } else {
                predictionIcon.className = 'fas fa-check-circle fa-4x mb-2 text-success';
                predictionText.innerText = 'Stable';
                predictionDescription.innerText = 'No memory issues predicted';
            }
            
            // Update the prediction result display
            let issuesHtml = '';
            if (prediction.predicted_issues && prediction.predicted_issues.length > 0) {
                issuesHtml = `
                    <h6 class="mt-3">Predicted Issues:</h6>
                    <ul class="list-group">
                `;
                
                prediction.predicted_issues.forEach(issue => {
                    const severityClass = issue.severity === 'critical' ? 'danger' : 
                                         (issue.severity === 'high' ? 'warning' : 'info');
                    
                    issuesHtml += `
                        <li class="list-group-item bg-transparent">
                            <span class="badge bg-${severityClass} me-2">${issue.severity}</span>
                            ${issue.description}
                            <div class="small mt-1">
                                <strong>Probability:</strong> ${(issue.probability * 100).toFixed(1)}% | 
                                <strong>Timeframe:</strong> ${issue.timeframe}
                            </div>
                        </li>
                    `;
                });
                
                issuesHtml += '</ul>';
            }
            
            // Display recommendations if available
            let recommendationsHtml = '';
            if (prediction.recommendations && prediction.recommendations.length > 0) {
                recommendationsHtml = `
                    <h6 class="mt-3">Recommendations:</h6>
                    <ul class="list-group">
                `;
                
                prediction.recommendations.forEach(recommendation => {
                    recommendationsHtml += `
                        <li class="list-group-item bg-transparent">
                            <i class="fas fa-lightbulb text-warning me-2"></i>${recommendation}
                        </li>
                    `;
                });
                
                recommendationsHtml += '</ul>';
            }
            
            resultElement.innerHTML = `
                <div class="card bg-dark border-warning">
                    <div class="card-body">
                        <h6>Prediction Results:</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <strong>Current Usage:</strong> ${result.stats.used_percent.toFixed(1)}%
                            </div>
                            <div class="col-md-6">
                                <strong>Predicted in 1h:</strong> ${prediction.predicted_memory_usage_1h ? prediction.predicted_memory_usage_1h.toFixed(1) + '%' : 'N/A'}
                            </div>
                        </div>
                        
                        ${prediction.predicted_memory_usage_24h ? `
                            <div class="row mt-2">
                                <div class="col-md-12">
                                    <strong>Predicted in 24h:</strong> ${prediction.predicted_memory_usage_24h.toFixed(1)}%
                                </div>
                            </div>
                        ` : ''}
                        
                        ${prediction.confidence_score ? `
                            <div class="mt-2">
                                <div class="progress" style="height: 20px;" title="Confidence Score">
                                    <div class="progress-bar bg-info" role="progressbar" style="width: ${prediction.confidence_score * 100}%;" aria-valuenow="${prediction.confidence_score * 100}" aria-valuemin="0" aria-valuemax="100">
                                        ${(prediction.confidence_score * 100).toFixed(0)}% Confidence
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        ${issuesHtml}
                        ${recommendationsHtml}
                    </div>
                </div>
            `;
        } else {
            resultElement.innerHTML = `
                <div class="alert alert-danger">
                    Error generating prediction: ${result.error}
                </div>
            `;
        }
    })
    .catch(error => {
        resultElement.innerHTML = `
            <div class="alert alert-danger">
                Error generating prediction: ${error.message}
            </div>
        `;
    });
}

// Generate healing plan
function generateHealingPlan() {
    const resultElement = document.getElementById('healResult');
    
    // Show loading state
    resultElement.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-success" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Generating healing plan...</span>
        </div>
    `;
    
    fetch('/api/memory/heal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            execute: false
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const healingPlan = result.healing_plan;
            
            // Update healing card if there's a plan
            if (healingPlan && healingPlan.actions && healingPlan.actions.length > 0) {
                const healingIcon = document.getElementById('healingIcon');
                const healingText = document.getElementById('healingText');
                const healingDescription = document.getElementById('healingDescription');
                
                healingIcon.className = 'fas fa-clipboard-list fa-4x mb-2 text-success';
                healingText.innerText = 'Plan Generated';
                healingDescription.innerText = `${healingPlan.actions.length} action(s) available`;
                
                // Display the healing plan
                let actionsHtml = '';
                
                healingPlan.actions.forEach(action => {
                    const priorityClass = action.priority === 'high' ? 'danger' : 
                                        (action.priority === 'medium' ? 'warning' : 'info');
                    
                    actionsHtml += `
                        <div class="card bg-dark border-${priorityClass} mb-2">
                            <div class="card-body">
                                <h6 class="card-title">
                                    <span class="badge bg-${priorityClass} me-2">${action.priority}</span>
                                    ${action.action_type}
                                </h6>
                                <p class="card-text">${action.description}</p>
                            </div>
                        </div>
                    `;
                });
                
                resultElement.innerHTML = `
                    <div class="alert alert-${healingPlan.severity === 'critical' ? 'danger' : 
                                             (healingPlan.severity === 'high' ? 'warning' : 
                                             (healingPlan.severity === 'moderate' ? 'info' : 'success'))}">
                        <strong>Severity:</strong> ${healingPlan.severity}
                    </div>
                    <h6>Proposed Actions:</h6>
                    ${actionsHtml}
                    <div class="alert alert-info mt-2">
                        <i class="fas fa-info-circle me-2"></i>Click "Execute Healing" to apply these actions
                    </div>
                `;
            } else {
                resultElement.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>No healing actions needed at this time
                    </div>
                `;
            }
        } else {
            resultElement.innerHTML = `
                <div class="alert alert-danger">
                    Error generating healing plan: ${result.error}
                </div>
            `;
        }
    })
    .catch(error => {
        resultElement.innerHTML = `
            <div class="alert alert-danger">
                Error generating healing plan: ${error.message}
            </div>
        `;
    });
}

// Execute healing actions
function executeHealing() {
    const resultElement = document.getElementById('healResult');
    
    // Show loading state
    resultElement.innerHTML = `
        <div class="text-center">
            <div class="spinner-border spinner-border-sm text-success" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <span class="ms-2">Executing healing actions...</span>
        </div>
    `;
    
    fetch('/api/memory/heal', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            execute: true
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            const healingPlan = result.healing_plan;
            const healingResults = result.results;
            const validation = result.validation;
            
            // Update healing card
            const healingIcon = document.getElementById('healingIcon');
            const healingText = document.getElementById('healingText');
            const healingDescription = document.getElementById('healingDescription');
            
            if (validation && validation.effective) {
                healingIcon.className = 'fas fa-check-circle fa-4x mb-2 text-success';
                healingText.innerText = 'Healing Successful';
                healingDescription.innerText = validation.details;
            } else {
                healingIcon.className = 'fas fa-times-circle fa-4x mb-2 text-warning';
                healingText.innerText = 'Healing Limited';
                healingDescription.innerText = validation ? validation.details : 'Limited effectiveness';
            }
            
            // Show healing results modal
            if (healingResults) {
                // Update before/after bars
                const beforePercent = healingResults.memory_before.used_percent;
                const afterPercent = healingResults.memory_after.used_percent;
                
                document.getElementById('beforeHealingBar').style.width = `${beforePercent}%`;
                document.getElementById('beforeHealingBar').innerText = `${beforePercent.toFixed(1)}%`;
                
                document.getElementById('afterHealingBar').style.width = `${afterPercent}%`;
                document.getElementById('afterHealingBar').innerText = `${afterPercent.toFixed(1)}%`;
                
                // Update details
                document.getElementById('beforeHealingDetails').innerText = 
                    `Total: ${formatBytes(healingResults.memory_before.total)} | Free: ${formatBytes(healingResults.memory_before.free)}`;
                
                document.getElementById('afterHealingDetails').innerText = 
                    `Total: ${formatBytes(healingResults.memory_after.total)} | Free: ${formatBytes(healingResults.memory_after.free)}`;
                
                // Update actions list
                const actionsContainer = document.getElementById('actionsPerformed');
                actionsContainer.innerHTML = '';
                
                if (healingResults.executed_actions && healingResults.executed_actions.length > 0) {
                    healingResults.executed_actions.forEach(action => {
                        const successClass = action.success ? 'success' : 'danger';
                        
                        const actionItem = document.createElement('li');
                        actionItem.className = 'list-group-item bg-transparent';
                        actionItem.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <i class="fas fa-${action.success ? 'check' : 'times'}-circle text-${successClass} me-2"></i>
                                    <strong>${action.action_type}</strong>: ${action.description}
                                </div>
                                <span class="badge bg-${successClass}">${action.success ? 'Success' : 'Failed'}</span>
                            </div>
                            <div class="small mt-1">${action.details}</div>
                        `;
                        
                        actionsContainer.appendChild(actionItem);
                    });
                } else {
                    actionsContainer.innerHTML = '<li class="list-group-item bg-transparent">No actions were executed</li>';
                }
                
                // Update effectiveness
                if (validation) {
                    const effectiveClass = validation.effective ? 'success' : 'warning';
                    document.getElementById('healingEffectiveness').innerHTML = `
                        <span class="badge bg-${effectiveClass}">
                            ${validation.effective ? 'Effective' : 'Limited Effect'}
                        </span>
                        ${validation.effectiveness_score ? 
                            `<span class="ms-2">(Score: ${(validation.effectiveness_score * 100).toFixed(0)}%)</span>` : 
                            ''}
                    `;
                    document.getElementById('healingEffectivenessDetails').innerText = validation.details;
                } else {
                    document.getElementById('healingEffectiveness').innerText = 'Unknown';
                    document.getElementById('healingEffectivenessDetails').innerText = 'No validation data available';
                }
                
                // Show the modal
                const healingModal = new bootstrap.Modal(document.getElementById('healingModal'));
                healingModal.show();
            }
            
            // Update the healing result display
            let resultHtml = '';
            
            if (result.executed && healingResults) {
                const successClass = healingResults.success ? 'success' : 'warning';
                
                resultHtml = `
                    <div class="alert alert-${successClass}">
                        <h6 class="alert-heading">
                            <i class="fas fa-${healingResults.success ? 'check' : 'exclamation'}-circle me-2"></i>
                            Healing ${healingResults.success ? 'Completed' : 'Partially Completed'}
                        </h6>
                        <hr>
                        <div class="row">
                            <div class="col-6">
                                <strong>Before:</strong> ${healingResults.memory_before.used_percent.toFixed(1)}%
                            </div>
                            <div class="col-6">
                                <strong>After:</strong> ${healingResults.memory_after.used_percent.toFixed(1)}%
                            </div>
                        </div>
                        ${validation ? `
                            <div class="mt-2">
                                <strong>Impact:</strong> ${validation.details}
                            </div>
                        ` : ''}
                    </div>
                `;
                
                // If there were executed actions, list them
                if (healingResults.executed_actions && healingResults.executed_actions.length > 0) {
                    resultHtml += `<h6>Actions Executed:</h6><ul class="list-group">`;
                    
                    healingResults.executed_actions.forEach(action => {
                        const actionClass = action.success ? 'success' : 'danger';
                        
                        resultHtml += `
                            <li class="list-group-item bg-transparent">
                                <i class="fas fa-${action.success ? 'check' : 'times'}-circle text-${actionClass} me-2"></i>
                                <strong>${action.action_type}</strong>: ${action.details}
                            </li>
                        `;
                    });
                    
                    resultHtml += `</ul>`;
                }
            } else if (result.healing_plan && result.healing_plan.actions && result.healing_plan.actions.length > 0) {
                resultHtml = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-circle me-2"></i>
                        No actions were executed. Click "Execute Healing" to apply the healing plan.
                    </div>
                `;
            } else {
                resultHtml = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        No healing actions were needed at this time.
                    </div>
                `;
            }
            
            resultElement.innerHTML = resultHtml;
            
            // Refresh memory stats after healing
            fetchMemoryStats();
            fetchMemoryHistory();
        } else {
            resultElement.innerHTML = `
                <div class="alert alert-danger">
                    Error executing healing: ${result.error}
                </div>
            `;
        }
    })
    .catch(error => {
        resultElement.innerHTML = `
            <div class="alert alert-danger">
                Error executing healing: ${error.message}
            </div>
        `;
    });
}

// Simulate memory usage
function simulateMemoryUsage() {
    const usageValue = document.getElementById('memoryUsage').value;
    
    fetch('/api/memory/simulate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            usage_mb: parseInt(usageValue)
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            // Show toast or notification
            alert(result.message);
            
            // Refresh memory stats after a delay to see the effect
            setTimeout(() => {
                fetchMemoryStats();
                fetchMemoryHistory();
            }, 1000);
        } else {
            alert(`Error: ${result.error}`);
        }
    })
    .catch(error => {
        alert(`Error: ${error.message}`);
    });
}

// Load logs
function loadLogs(logType) {
    currentLogType = logType;
    const logsContent = document.getElementById('logsContent');
    
    // Show loading state
    logsContent.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-secondary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading ${logType} logs...</p>
        </div>
    `;
    
    // Set active button
    document.getElementById('memoryLogsBtn').classList.remove('active');
    document.getElementById('predictionLogsBtn').classList.remove('active');
    document.getElementById('healingLogsBtn').classList.remove('active');
    document.getElementById(`${logType}LogsBtn`).classList.add('active');
    
    let endpoint = '';
    switch (logType) {
        case 'memory':
            endpoint = '/api/logs/memory';
            break;
        case 'prediction':
            endpoint = '/api/logs/predictions';
            break;
        case 'healing':
            endpoint = '/api/logs/healing';
            break;
    }
    
    fetch(endpoint)
        .then(response => response.json())
        .then(result => {
            if (result.success && result.logs && result.logs.length > 0) {
                // Reverse to show newest first
                const logs = result.logs.reverse();
                let logsHtml = '';
                
                logs.forEach(log => {
                    let entryClass = 'log-entry';
                    let iconClass = 'fa-info-circle text-info';
                    let title = '';
                    let content = '';
                    
                    if (logType === 'memory') {
                        // Format memory log entry
                        title = `Memory Event at ${formatTimestamp(log.timestamp)}`;
                        
                        if (log.analysis && log.analysis.anomaly_detected) {
                            entryClass += ' anomaly';
                            iconClass = 'fa-exclamation-triangle text-danger';
                            title += ` - ${log.analysis.severity} Anomaly`;
                        }
                        
                        content = `
                            <div>
                                <strong>Memory Usage:</strong> ${log.stats.used_percent.toFixed(1)}%
                                (Total: ${formatBytes(log.stats.total)} | Free: ${formatBytes(log.stats.free)})
                            </div>
                        `;
                        
                        if (log.analysis && log.analysis.anomaly_detected) {
                            content += `
                                <div class="mt-2">
                                    <strong>Anomaly:</strong> ${log.analysis.anomaly_description || 'No description'}
                                </div>
                            `;
                        }
                    } else if (logType === 'prediction') {
                        // Format prediction log entry
                        title = `Prediction at ${formatTimestamp(log.timestamp)}`;
                        
                        const hasCriticalIssues = log.predicted_issues && log.predicted_issues.some(issue => issue.severity === 'critical');
                        const hasHighIssues = log.predicted_issues && log.predicted_issues.some(issue => issue.severity === 'high');
                        
                        if (hasCriticalIssues) {
                            entryClass += ' prediction anomaly';
                            iconClass = 'fa-exclamation-circle text-danger';
                            title += ' - Critical Issues';
                        } else if (hasHighIssues) {
                            entryClass += ' prediction';
                            iconClass = 'fa-exclamation-circle text-warning';
                            title += ' - Issues';
                        } else {
                            entryClass += ' prediction';
                            iconClass = 'fa-chart-line text-info';
                        }
                        
                        content = `
                            <div>
                                <strong>Current:</strong> ${log.current_memory_used.toFixed(1)}% |
                                <strong>Predicted (1h):</strong> ${log.predicted_memory_usage_1h ? log.predicted_memory_usage_1h.toFixed(1) + '%' : 'N/A'}
                                ${log.predicted_memory_usage_24h ? `| <strong>Predicted (24h):</strong> ${log.predicted_memory_usage_24h.toFixed(1)}%` : ''}
                            </div>
                        `;
                        
                        if (log.predicted_issues && log.predicted_issues.length > 0) {
                            content += `<div class="mt-2"><strong>Issues:</strong></div><ul class="mb-0">`;
                            
                            log.predicted_issues.forEach(issue => {
                                content += `
                                    <li>
                                        <span class="badge bg-${issue.severity === 'critical' ? 'danger' : (issue.severity === 'high' ? 'warning' : 'info')}">
                                            ${issue.severity}
                                        </span>
                                        ${issue.description} (${(issue.probability * 100).toFixed(0)}% probability)
                                    </li>
                                `;
                            });
                            
                            content += `</ul>`;
                        }
                    } else if (logType === 'healing') {
                        // Format healing log entry
                        title = `Healing Event at ${formatTimestamp(log.timestamp)}`;
                        entryClass += ' healing';
                        iconClass = 'fa-heart-pulse text-success';
                        
                        const validation = log.validation || {};
                        if (validation.effective) {
                            title += ' - Effective';
                        } else {
                            title += ' - Limited Effect';
                        }
                        
                        content = `
                            <div>
                                <strong>Memory Before:</strong> ${log.memory_stats.used_percent.toFixed(1)}%
                            </div>
                        `;
                        
                        if (log.results && log.results.memory_after) {
                            content += `
                                <div>
                                    <strong>Memory After:</strong> ${log.results.memory_after.used_percent.toFixed(1)}%
                                    <strong>Change:</strong> ${log.results.memory_change.difference.toFixed(1)}%
                                </div>
                            `;
                        }
                        
                        if (log.healing_plan && log.healing_plan.actions) {
                            content += `<div class="mt-2"><strong>Actions:</strong></div><ul class="mb-0">`;
                            
                            log.healing_plan.actions.forEach(action => {
                                content += `
                                    <li>
                                        <span class="badge bg-${action.priority === 'high' ? 'danger' : (action.priority === 'medium' ? 'warning' : 'info')}">
                                            ${action.priority}
                                        </span>
                                        ${action.action_type}: ${action.description}
                                    </li>
                                `;
                            });
                            
                            content += `</ul>`;
                        }
                        
                        if (validation) {
                            content += `
                                <div class="mt-2">
                                    <strong>Effectiveness:</strong> ${validation.details || 'No details'}
                                </div>
                            `;
                        }
                    }
                    
                    logsHtml += `
                        <div class="${entryClass} p-3 bg-dark mb-3">
                            <div class="d-flex align-items-start">
                                <i class="fas ${iconClass} mt-1 me-2"></i>
                                <div class="flex-grow-1">
                                    <h6>${title}</h6>
                                    ${content}
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                logsContent.innerHTML = logsHtml;
            } else {
                logsContent.innerHTML = `
                    <div class="text-center py-5">
                        <i class="fas fa-folder-open fa-3x text-secondary mb-3"></i>
                        <p>No ${logType} logs available</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            logsContent.innerHTML = `
                <div class="alert alert-danger">
                    Error loading logs: ${error.message}
                </div>
            `;
        });
}

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the memory chart
    initMemoryChart();
    
    // Fetch initial data
    fetchMemoryStats();
    fetchMemoryHistory();
    
    // Load initial logs
    loadLogs('memory');
    
    // Set up refresh button
    document.getElementById('refreshBtn').addEventListener('click', function() {
        fetchMemoryStats();
        fetchMemoryHistory();
    });
    
    // Set up auto-refresh interval (every 30 seconds)
    setInterval(function() {
        fetchMemoryStats();
        fetchMemoryHistory();
    }, 30000);
    
    // Set up analyze button
    document.getElementById('analyzeBtn').addEventListener('click', analyzeMemory);
    
    // Set up predict button
    document.getElementById('predictBtn').addEventListener('click', predictMemory);
    
    // Set up healing buttons
    document.getElementById('planHealBtn').addEventListener('click', generateHealingPlan);
    document.getElementById('executeHealBtn').addEventListener('click', executeHealing);
    
    // Set up auto-heal button in the anomaly modal
    document.getElementById('autoHealBtn').addEventListener('click', function() {
        // Close the modal
        const anomalyModal = bootstrap.Modal.getInstance(document.getElementById('anomalyModal'));
        if (anomalyModal) {
            anomalyModal.hide();
        }
        
        // Execute healing
        executeHealing();
    });
    
    // Set up memory simulation
    document.getElementById('memoryUsage').addEventListener('input', function() {
        document.getElementById('memoryUsageValue').textContent = this.value + ' MB';
    });
    
    document.getElementById('simulateBtn').addEventListener('click', simulateMemoryUsage);
    
    // Set up log type buttons
    document.getElementById('memoryLogsBtn').addEventListener('click', function() {
        loadLogs('memory');
    });
    
    document.getElementById('predictionLogsBtn').addEventListener('click', function() {
        loadLogs('prediction');
    });
    
    document.getElementById('healingLogsBtn').addEventListener('click', function() {
        loadLogs('healing');
    });
});
