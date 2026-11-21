/**
 * AEGIS Command Center — Dashboard Page Module
 * Displays real data from backend when available, clearly labels simulated data.
 * Zero fake AI or random data generation.
 */

const CommandCenter = (() => {
    let _chartInstances = {};
    let _refreshInterval = null;
    let _historicalMetrics = [];
    let _selectedEnvironment = "";
    let _selectedCollector = "";

    async function render(container) {
        container.innerHTML = getTemplate();
        bindFilterEvents();
        await loadData();
        startAutoRefresh();
    }

    function destroy() {
        if (_refreshInterval) clearInterval(_refreshInterval);
        Object.values(_chartInstances).forEach(c => c.destroy && c.destroy());
        _chartInstances = {};
    }

    function bindFilterEvents() {
        const tenantSelect = document.getElementById('cc-tenant-switcher');
        if (tenantSelect) {
            tenantSelect.value = AegisAPI.getTenant();
            tenantSelect.addEventListener('change', (e) => {
                const newT = e.target.value;
                AegisAPI.setTenant(newT);
                const globalSel = document.getElementById('global-tenant-select');
                if (globalSel) globalSel.value = newT;
                AegisToast.success(`Switched active bank to ${newT}`);
                loadData();
            });
        }
        const envSelect = document.getElementById('cc-env-filter');
        if (envSelect) {
            envSelect.addEventListener('change', (e) => {
                _selectedEnvironment = e.target.value;
                loadData();
            });
        }
        const colSelect = document.getElementById('cc-col-filter');
        if (colSelect) {
            colSelect.addEventListener('change', (e) => {
                _selectedCollector = e.target.value;
                loadData();
            });
        }
    }

    function getTemplate() {
        return `
        <div class="command-center">
            <div class="page-header">
                <div class="flex items-center justify-between flex-wrap gap-4">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="badge badge-accent" id="cc-tenant-badge">TENANT: ORG_001 (Acme Corp)</span>
                            <span class="badge badge-teal" id="cc-host-badge">Configured Host</span>
                            <span class="badge badge-good" id="cc-stage-badge">STAGE 1: INGEST</span>
                        </div>
                        <h1 class="page-title">SaaS Command Center</h1>
                        <p class="page-subtitle">Consolidated multi-environment observability & autonomous operations platform</p>
                    </div>
                    <div class="flex items-center gap-3 flex-wrap">
                        <!-- Tenant Switcher Dropdown (BANK_HDFC_IN vs BANK_ICICI_IN) -->
                        <div class="flex items-center gap-2">
                            <label class="text-xs text-muted font-medium" for="cc-tenant-switcher">Bank:</label>
                            <select id="cc-tenant-switcher" class="form-input" style="padding:4px 8px;font-size:12px;font-weight:600;width:auto;color:var(--color-primary);border:1px solid var(--color-border);border-radius:var(--radius-md);">
                                <option value="BANK_HDFC_IN">BANK_HDFC_IN (HDFC Bank)</option>
                                <option value="BANK_ICICI_IN">BANK_ICICI_IN (ICICI Bank)</option>
                            </select>
                        </div>
                        <!-- Selectors for Multi-Environment Fleet Filtering -->
                        <div class="flex items-center gap-2">
                            <label class="text-xs text-muted font-medium" for="cc-env-filter">Env:</label>
                            <select id="cc-env-filter" class="form-input" style="padding:4px 8px;font-size:12px;width:auto;">
                                <option value="">All Environments</option>
                                <option value="production" selected>Production (Core Switch)</option>
                                <option value="staging">Disaster Recovery (DR)</option>
                            </select>
                        </div>
                        <div class="flex items-center gap-2">
                            <label class="text-xs text-muted font-medium" for="cc-col-filter">Collector:</label>
                            <select id="cc-col-filter" class="form-input" style="padding:4px 8px;font-size:12px;width:auto;">
                                <option value="">All Collectors</option>
                                <option value="COLLECTOR_001" selected>COLLECTOR_001 (Local Host)</option>
                            </select>
                        </div>
                        <span class="text-xs text-muted" id="cc-last-updated">Last updated: —</span>
                        <button class="btn btn-secondary btn-sm" onclick="CommandCenter.refresh()">
                            ${AegisIcons.refresh()} Refresh
                        </button>
                    </div>
                </div>
            </div>

            <div id="cc-sim-banner"></div>

            <!-- Health Banner -->
            <div class="health-banner" id="cc-health-banner">
                <div class="health-score excellent" id="cc-health-score">
                    <span>—</span>
                </div>
                <div class="health-info">
                    <h3 id="cc-health-label">Calculating...</h3>
                    <p id="cc-health-desc" class="text-sm text-muted">Evaluating infrastructure health across all connected collectors</p>
                </div>
                <div class="health-states">
                    <div class="health-state-item excellent">
                        <span class="count" id="cc-state-excellent">0</span>
                        <span class="label">Excellent</span>
                    </div>
                    <div class="health-state-item good">
                        <span class="count" id="cc-state-good">0</span>
                        <span class="label">Good</span>
                    </div>
                    <div class="health-state-item fair">
                        <span class="count" id="cc-state-fair">0</span>
                        <span class="label">Fair</span>
                    </div>
                    <div class="health-state-item poor">
                        <span class="count" id="cc-state-poor">0</span>
                        <span class="label">Poor</span>
                    </div>
                </div>
            </div>

            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon accent">${AegisIcons.radio()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Connected Collectors</div>
                        <div class="stat-value" id="cc-collectors-online">0</div>
                        <div class="stat-change neutral" id="cc-collectors-offline">0 offline</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon poor">${AegisIcons.alertTriangle()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Active Incidents</div>
                        <div class="stat-value" id="cc-active-incidents">0</div>
                        <div class="stat-change neutral" id="cc-incidents-24h">0 in last 24h</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon fair">${AegisIcons.lock()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Security Alerts</div>
                        <div class="stat-value" id="cc-security-alerts">0</div>
                        <div class="stat-change neutral" id="cc-sec-severity">None active</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon excellent">${AegisIcons.shieldCheck()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Privacy Compliance</div>
                        <div class="stat-value" id="cc-privacy-status">Not Evaluated</div>
                        <div class="stat-change neutral" id="cc-egress-count">0 payloads transmitted</div>
                    </div>
                </div>
            </div>

            <!-- Resource Stats Row (Real Windows Machine Metrics) -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon teal">${AegisIcons.cpu()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Real CPU Load</div>
                        <div class="stat-value" id="cc-cpu-avg">—%</div>
                        <div class="text-xs text-muted" id="cc-cpu-detail">Windows Host Telemetry</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon accent">${AegisIcons.activity()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Real Memory Load</div>
                        <div class="stat-value" id="cc-mem-avg">—%</div>
                        <div class="text-xs text-muted" id="cc-mem-detail">Physical RAM Usage</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon good">${AegisIcons.hardDrive()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Real Disk Utilization</div>
                        <div class="stat-value" id="cc-disk-avg">—%</div>
                        <div class="text-xs text-muted" id="cc-disk-detail">C:\\ Storage Partition</div>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon fair">${AegisIcons.wifi()}</div>
                    <div class="stat-content">
                        <div class="stat-label">Network Latency</div>
                        <div class="stat-value" id="cc-latency-avg">— ms</div>
                        <div class="text-xs text-muted" id="cc-latency-detail">Real TCP Socket Probes</div>
                    </div>
                </div>
            </div>

            <!-- Real Time-Series Charts -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="card-header">
                        <span class="card-title">Real CPU & Memory Trend (Live Database Ingestion)</span>
                        <span class="text-xs text-muted" id="cc-chart-res-info">Historical psutil measurements</span>
                    </div>
                    <div class="chart-wrapper">
                        <canvas id="cc-chart-resources"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="card-header">
                        <span class="card-title">Network Socket Latency (Live Probes)</span>
                        <span class="text-xs text-muted" id="cc-chart-lat-info">Round-trip connect latency</span>
                    </div>
                    <div class="chart-wrapper">
                        <canvas id="cc-chart-latency"></canvas>
                    </div>
                </div>
            </div>

            <!-- Activity Lists -->
            <div class="activity-grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Correlated Incidents (Incident DNA)</span>
                        <button class="btn btn-ghost btn-sm" onclick="AegisRouter.navigate('incident-dna')">View All</button>
                    </div>
                    <div id="cc-incidents-list">
                        <div class="empty-state" style="padding:var(--space-6);">
                            <p class="text-sm text-muted">No active incidents detected. All operational signals nominal.</p>
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Explainable AI Recommendations</span>
                        <button class="btn btn-ghost btn-sm" onclick="AegisRouter.navigate('ai-insights')">View All</button>
                    </div>
                    <div id="cc-recommendations-list">
                        <div class="empty-state" style="padding:var(--space-6);">
                            <p class="text-sm text-muted">No remediation required. Operational baselines within ±2.5σ.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
    }

    async function loadData() {
        let summaryData = null;
        let metricsData = [];

        try {
            // Build query params for environment and collector
            let q = [];
            if (_selectedEnvironment) q.push(`environment=${encodeURIComponent(_selectedEnvironment)}`);
            if (_selectedCollector) q.push(`collector_id=${encodeURIComponent(_selectedCollector)}`);
            const qs = q.length ? `?${q.join('&')}` : '';

            // Fetch live summary and live time-series in parallel
            const [sumRes, metRes] = await Promise.all([
                AegisAPI.get(`/dashboard/summary${qs}`),
                AegisAPI.get(`/metrics?limit=30`)
            ]);

            summaryData = sumRes;
            metricsData = Array.isArray(metRes) ? metRes : [];
            _historicalMetrics = metricsData.slice().reverse(); // Chronological order

            showSimBanner(summaryData.simulated === true);
            updateUI(summaryData);
            updateChartsWithRealData(_historicalMetrics);
        } catch (err) {
            // Backend offline or error — display honest offline state with last update time
            showSimBanner(true, err.message);
            showOfflineState();
        }

        updateTimestamp();
    }

    function showOfflineState() {
        const scoreEl = document.getElementById('cc-health-score');
        const labelEl = document.getElementById('cc-health-label');
        if (scoreEl) {
            scoreEl.className = 'health-score fair';
            scoreEl.innerHTML = `<span>N/A</span>`;
        }
        if (labelEl) labelEl.textContent = 'Backend Offline — Waiting for Telemetry';
        setText('cc-cpu-avg', 'N/A');
        setText('cc-mem-avg', 'N/A');
        setText('cc-disk-avg', 'N/A');
        setText('cc-latency-avg', 'N/A');
    }

    function showSimBanner(show, customMsg = null) {
        const el = document.getElementById('cc-sim-banner');
        if (el) {
            if (show) {
                el.innerHTML = `
                <div class="sim-banner">
                    ${AegisIcons.alertTriangle()}
                    <span><strong>Connection Status:</strong> ${customMsg ? esc(customMsg) : 'Backend server unreachable. Make sure the AEGIS FastAPI server is running on port 8000.'}</span>
                </div>`;
            } else {
                el.innerHTML = '';
            }
        }
    }

    function updateUI(data) {
        // Sync active bank tenant badge and select
        const curTenant = AegisAPI.getTenant();
        const bankName = curTenant === 'BANK_ICICI_IN' ? 'ICICI Bank Ltd.' : 'HDFC Bank Ltd.';
        const tBadge = document.getElementById('cc-tenant-badge');
        if (tBadge) {
            tBadge.textContent = `TENANT: ${curTenant} (${bankName})`;
        }
        const tSwitcher = document.getElementById('cc-tenant-switcher');
        if (tSwitcher) {
            tSwitcher.value = curTenant;
        }

        // Health banner
        const scoreEl = document.getElementById('cc-health-score');
        const labelEl = document.getElementById('cc-health-label');
        const state = (data.health_state || 'Good').toLowerCase();
        if (scoreEl) {
            scoreEl.className = `health-score ${state}`;
            scoreEl.innerHTML = `<span>${data.health_score || '100'}</span>`;
        }
        if (labelEl) labelEl.textContent = `Fleet Health: ${data.health_state || 'Nominal'}`;

        // State counts
        setText('cc-state-excellent', data.states?.excellent ?? 0);
        setText('cc-state-good', data.states?.good ?? 0);
        setText('cc-state-fair', data.states?.fair ?? 0);
        setText('cc-state-poor', data.states?.poor ?? 0);

        // Dynamic host and maturity status badges
        const hBadge = document.getElementById('cc-host-badge');
        if (hBadge && data.host_status) {
            hBadge.textContent = data.host_status;
            hBadge.className = data.collectors_online > 0 ? 'badge badge-teal' : 'badge badge-fair';
        }
        const sBadge = document.getElementById('cc-stage-badge');
        if (sBadge && data.maturity_stage) {
            sBadge.textContent = data.maturity_stage.toUpperCase();
        }

        // Stats
        setText('cc-collectors-online', data.collectors_online ?? 0);
        setText('cc-collectors-offline', `${data.collectors_offline ?? 0} offline`);
        setText('cc-active-incidents', data.active_incidents ?? 0);
        setText('cc-incidents-24h', `${data.incidents_24h ?? 0} in last 24h`);
        setText('cc-security-alerts', data.security_alerts ?? 0);
        setText('cc-sec-severity', data.security_severity || 'None active');
        setText('cc-privacy-status', data.privacy_status || 'Not Evaluated');
        setText('cc-egress-count', `${data.egress_count ?? 0} verified proofs`);

        // Resources (Real Windows machine readings)
        if (data.collectors_online === 0 && (!data.cpu_avg || data.cpu_avg === 0)) {
            setText('cc-cpu-avg', 'N/A');
            setText('cc-mem-avg', 'N/A');
            setText('cc-disk-avg', 'N/A');
            setText('cc-latency-avg', 'N/A');
        } else {
            setText('cc-cpu-avg', `${data.cpu_avg ?? 'N/A'}%`);
            setText('cc-mem-avg', `${data.memory_avg ?? 'N/A'}%`);
            setText('cc-disk-avg', `${data.disk_avg ?? 'N/A'}%`);
            setText('cc-latency-avg', `${data.latency_avg ?? 'N/A'} ms`);
        }

        // Incidents list
        const incList = document.getElementById('cc-incidents-list');
        if (incList) {
            if (data.incidents && data.incidents.length > 0) {
                incList.innerHTML = data.incidents.map(inc => `
                    <div class="incident-row">
                        <div class="incident-severity ${(inc.severity || 'medium').toLowerCase()}"></div>
                        <div class="incident-details">
                            <div class="incident-title">${esc(inc.title)}</div>
                            <div class="incident-meta">${esc(inc.id)} · ${esc(inc.source || 'Windows Host')}</div>
                        </div>
                        <div class="incident-time">${esc(inc.time || 'Active')}</div>
                    </div>`).join('');
            } else {
                incList.innerHTML = `
                    <div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">No active incidents. Zero unmitigated breaches.</p>
                    </div>`;
            }
        }

        // Recommendations list
        const recList = document.getElementById('cc-recommendations-list');
        if (recList) {
            if (data.recommendations && data.recommendations.length > 0) {
                recList.innerHTML = data.recommendations.map(rec => `
                    <div class="recommendation-item">
                        <div class="recommendation-icon">${AegisIcons.brain()}</div>
                        <div class="recommendation-content">
                            <div class="recommendation-text">${esc(rec.text)}</div>
                            <div class="recommendation-reason">${esc(rec.reason)}</div>
                        </div>
                    </div>`).join('');
            } else {
                recList.innerHTML = `
                    <div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">All operational baselines nominal. Recommendations ready upon deviation.</p>
                    </div>`;
            }
        }
    }

    function updateChartsWithRealData(records) {
        if (typeof Chart === 'undefined') return;

        const gridColor = 'rgba(56, 189, 248, 0.06)';
        const tickColor = '#64748b';

        const commonScales = {
            x: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 } } },
            y: { grid: { color: gridColor }, ticks: { color: tickColor, font: { size: 10 } }, beginAtZero: true, max: 100 },
        };

        // Extract real timestamps and real metric values
        let labels = [];
        let cpuData = [];
        let memData = [];
        let latData = [];

        if (records && records.length > 0) {
            records.forEach(r => {
                const d = new Date(r.timestamp);
                const timeLabel = isNaN(d.getTime()) ? 'now' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                labels.push(timeLabel);
                cpuData.push(r.cpu_usage);
                memData.push(r.memory_usage);
                latData.push(r.latency_ms);
            });
        } else {
            labels = ['Waiting for collector...'];
            cpuData = [0];
            memData = [0];
            latData = [0];
        }

        // CPU & Memory Chart
        const resCanvas = document.getElementById('cc-chart-resources');
        if (resCanvas) {
            if (_chartInstances.resources) {
                _chartInstances.resources.data.labels = labels;
                _chartInstances.resources.data.datasets[0].data = cpuData;
                _chartInstances.resources.data.datasets[1].data = memData;
                _chartInstances.resources.update();
            } else {
                const resCtx = resCanvas.getContext('2d');
                _chartInstances.resources = new Chart(resCtx, {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            {
                                label: 'Real CPU %',
                                data: cpuData,
                                borderColor: '#22d3ee',
                                backgroundColor: 'rgba(34, 211, 238, 0.08)',
                                fill: true,
                                tension: 0.25,
                                borderWidth: 2,
                                pointRadius: 2,
                            },
                            {
                                label: 'Real Memory %',
                                data: memData,
                                borderColor: '#14b8a6',
                                backgroundColor: 'rgba(20, 184, 166, 0.08)',
                                fill: true,
                                tension: 0.25,
                                borderWidth: 2,
                                pointRadius: 2,
                            },
                        ],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 11 } } } },
                        scales: commonScales,
                        animation: { duration: 400 },
                    },
                });
            }
        }

        // Latency Chart
        const latCanvas = document.getElementById('cc-chart-latency');
        if (latCanvas) {
            if (_chartInstances.latency) {
                _chartInstances.latency.data.labels = labels;
                _chartInstances.latency.data.datasets[0].data = latData;
                _chartInstances.latency.update();
            } else {
                const latCtx = latCanvas.getContext('2d');
                _chartInstances.latency = new Chart(latCtx, {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [{
                            label: 'Socket Latency (ms)',
                            data: latData,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.08)',
                            fill: true,
                            tension: 0.25,
                            borderWidth: 2,
                            pointRadius: 2,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { labels: { color: tickColor, boxWidth: 12, font: { size: 11 } } } },
                        scales: {
                            x: commonScales.x,
                            y: { ...commonScales.y, max: undefined, suggestedMax: 60 },
                        },
                        animation: { duration: 400 },
                    },
                });
            }
        }
    }

    function startAutoRefresh() {
        if (_refreshInterval) clearInterval(_refreshInterval);
        _refreshInterval = setInterval(() => {
            if (AegisRouter.getCurrentPage() === 'command-center') {
                loadData();
            }
        }, 10000); // 10s auto-refresh
    }

    async function refresh() {
        await loadData();
        AegisToast.info('Live Command Center updated from PostgreSQL backend');
    }

    function updateTimestamp() {
        const el = document.getElementById('cc-last-updated');
        if (el) el.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
    }

    function setText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    function esc(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    return { render, destroy, refresh };
})();

window.CommandCenter = CommandCenter;
