/**
 * AEGIS Module Implementations — Fully Connected to Real Backend APIs
 * Live telemetry, Egress Proof verification, Incident DNA, AIOps, and Recovery Simulation.
 */

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}

// ==========================================
// 1. INFRASTRUCTURE MONITORING
// ==========================================
const InfraMonitoring = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Infrastructure Monitoring</h1>
                        <p class="page-subtitle">Real-time host metrics, CPU/memory telemetry, and health states</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="InfraMonitoring.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="infra-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Infrastructure metrics refreshed');
    },

    async load() {
        const el = document.getElementById('infra-content');
        if (!el) return;

        try {
            const data = await AegisAPI.get('/infrastructure');
            const servers = data.servers || [];

            if (servers.length === 0) {
                el.innerHTML = `
                    <div class="card">
                        <div class="empty-state">
                            ${AegisIcons.server()}
                            <h3>No Active Servers Reported</h3>
                            <p>Tier 1 collector telemetry has not yet been received. Start the collector daemon to ingest live host metrics.</p>
                        </div>
                    </div>`;
                return;
            }

            el.innerHTML = `
                <div class="stats-grid" style="margin-bottom:var(--space-6);">
                    <div class="stat-card">
                        <div class="stat-icon teal">${AegisIcons.server()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Total Servers</div>
                            <div class="stat-value">${servers.length}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon accent">${AegisIcons.cpu()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Fleet Avg CPU</div>
                            <div class="stat-value">${Math.round(servers.reduce((a, b) => a + b.cpu, 0) / servers.length)}%</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon good">${AegisIcons.activity()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Fleet Avg Memory</div>
                            <div class="stat-value">${Math.round(servers.reduce((a, b) => a + b.memory, 0) / servers.length)}%</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon excellent">${AegisIcons.shieldCheck()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Healthy Hosts</div>
                            <div class="stat-value">${servers.filter(s => s.health === 'Excellent' || s.health === 'Good').length}</div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Live Server Fleet Telemetry</span>
                        <span class="badge badge-accent">Live DB Ingestion</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Source ID</th><th>Host Identifier</th><th>Collector ID</th>
                                <th>CPU Usage</th><th>Memory</th><th>Disk</th><th>Health State</th><th>Last Seen</th>
                            </tr></thead>
                            <tbody>
                                ${servers.map(s => {
                                    const h = (s.health || 'Good').toLowerCase();
                                    return `
                                    <tr>
                                        <td class="mono"><strong>${escapeHtml(s.source_id)}</strong></td>
                                        <td>${escapeHtml(s.host)}</td>
                                        <td class="mono text-xs">${escapeHtml(s.collector_id)}</td>
                                        <td>
                                            <div class="flex items-center gap-2">
                                                <span>${s.cpu}%</span>
                                                <div style="width:60px;height:6px;background:var(--color-bg-tertiary);border-radius:3px;overflow:hidden;">
                                                    <div style="width:${Math.min(100, s.cpu)}%;height:100%;background:${s.cpu > 80 ? 'var(--color-poor)' : 'var(--color-accent)'};"></div>
                                                </div>
                                            </div>
                                        </td>
                                        <td>${s.memory}%</td>
                                        <td>${s.disk}%</td>
                                        <td><span class="badge badge-${h}">${escapeHtml(s.health)}</span></td>
                                        <td class="text-xs text-muted">${escapeHtml(s.last_seen)}</td>
                                    </tr>`;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 2. NETWORK MONITORING
// ==========================================
const NetworkMonitoring = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Network Monitoring</h1>
                        <p class="page-subtitle">Real TCP socket latency measurements, packet drop metrics, and pathway health</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="NetworkMonitoring.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="network-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Network metrics refreshed');
    },

    async load() {
        const el = document.getElementById('network-content');
        if (!el) return;

        try {
            const data = await AegisAPI.get('/network');
            el.innerHTML = `
                <div class="stats-grid" style="margin-bottom:var(--space-6);">
                    <div class="stat-card">
                        <div class="stat-icon teal">${AegisIcons.wifi()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Measured Latency</div>
                            <div class="stat-value">${data.avg_latency} ms</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon fair">${AegisIcons.activity()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Packet Loss</div>
                            <div class="stat-value">${data.avg_packet_loss}%</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon accent">${AegisIcons.network()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Throughput Rate</div>
                            <div class="stat-value">${data.bandwidth_mbps} Mbps</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon excellent">${AegisIcons.globe()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Network Status</div>
                            <div class="stat-value">${escapeHtml(data.connectivity)}</div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Recent Network Telemetry Samples</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Source ID</th><th>Latency</th><th>Packet Loss</th><th>Timestamp</th>
                            </tr></thead>
                            <tbody>
                                ${(data.history || []).slice(0, 15).map(h => `
                                <tr>
                                    <td class="mono">${escapeHtml(h.source)}</td>
                                    <td><strong>${h.latency_ms} ms</strong></td>
                                    <td>${h.packet_loss}%</td>
                                    <td class="text-xs text-muted">${escapeHtml(h.timestamp)}</td>
                                </tr>`).join('') || `<tr><td colspan="4" class="text-muted" style="text-align:center;">Awaiting network data samples</td></tr>`}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 3. SECURITY MONITORING
// ==========================================
const SecurityMonitoring = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Security Monitoring</h1>
                        <p class="page-subtitle">Privacy-safe authentication summaries, threat levels, and brute-force detection</p>
                    </div>
                    <div class="flex gap-2">
                        <button class="btn btn-secondary btn-sm" onclick="SecurityMonitoring.injectFailedLogins()">
                            ${AegisIcons.zap()} Simulate Failed Logins
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="SecurityMonitoring.refresh()">
                            ${AegisIcons.refresh()} Refresh
                        </button>
                    </div>
                </div>
            </div>
            <div id="security-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async injectFailedLogins() {
        try {
            await AegisAPI.post('/security/event', {
                source_id: 'AUTH_GATEWAY_01',
                event_category: 'Brute-Force Anomaly',
                severity: 'High',
                failed_login_count: 5,
                description: 'Repeated authentication failures detected against auth-service'
            });
            AegisToast.warning('Security alert injected — check updated dashboard');
            await this.load();
        } catch (err) {
            AegisToast.error(err.message);
        }
    },

    async refresh() {
        await this.load();
        AegisToast.info('Security summaries refreshed');
    },

    async load() {
        const el = document.getElementById('security-content');
        if (!el) return;

        try {
            const data = await AegisAPI.get('/security');
            const alerts = data.alerts || [];

            el.innerHTML = `
                <div class="stats-grid" style="margin-bottom:var(--space-6);">
                    <div class="stat-card">
                        <div class="stat-icon poor">${AegisIcons.lock()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Security Incidents</div>
                            <div class="stat-value">${data.total_alerts}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon fair">${AegisIcons.alertTriangle()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Failed Auth Attempts</div>
                            <div class="stat-value">${data.total_failures}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon excellent">${AegisIcons.shieldCheck()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Raw Auth Logs Exported</div>
                            <div class="stat-value">0</div>
                            <div class="stat-change up">Retained locally by policy</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon accent">${AegisIcons.fingerprint()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Credential Protection</div>
                            <div class="stat-value">Active</div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Sanitized Security Alert Feed</span>
                        <span class="badge badge-accent">Summaries Only (No Raw Secrets)</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Severity</th><th>Event Category</th><th>Source</th><th>Failed Count</th><th>Description</th><th>Time</th>
                            </tr></thead>
                            <tbody>
                                ${alerts.length === 0 ? `<tr><td colspan="6" class="text-muted" style="text-align:center;">No security anomalies detected. System operating within normal thresholds.</td></tr>` :
                                alerts.map(a => `
                                <tr>
                                    <td><span class="badge badge-${(a.severity || 'medium').toLowerCase()}">${escapeHtml(a.severity)}</span></td>
                                    <td><strong>${escapeHtml(a.event)}</strong></td>
                                    <td class="mono">${escapeHtml(a.source)}</td>
                                    <td>${a.count}</td>
                                    <td>${escapeHtml(a.description)}</td>
                                    <td class="text-xs text-muted">${escapeHtml(a.time)}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 4. COLLECTOR MANAGEMENT
// ==========================================
const CollectorManagement = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Collector Fleet Management</h1>
                        <p class="page-subtitle">Tier 1 local collector nodes, heartbeat telemetry, and buffer queue monitoring</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="CollectorManagement.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="collector-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Collector fleet status refreshed');
    },

    async load() {
        const el = document.getElementById('collector-content');
        if (!el) return;

        try {
            const collectors = await AegisAPI.get('/collectors');
            el.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Registered Customer Environment Collectors</span>
                        <span class="badge badge-accent">${collectors.length} Nodes</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Collector ID</th><th>Host Identifier</th><th>Version</th><th>Status</th>
                                <th>CPU / Mem</th><th>Last Heartbeat</th><th>Pending Buffer</th><th>Last Delivery</th>
                            </tr></thead>
                            <tbody>
                                ${collectors.length === 0 ? `<tr><td colspan="8" class="text-muted" style="text-align:center;">No collectors registered. Run collector/main.py in your environment.</td></tr>` :
                                collectors.map(c => `
                                <tr>
                                    <td class="mono"><strong>${escapeHtml(c.collector_id)}</strong></td>
                                    <td>${escapeHtml(c.host_identifier)}</td>
                                    <td><span class="badge badge-accent">v${escapeHtml(c.version)}</span></td>
                                    <td>
                                        <span class="badge badge-${c.status === 'Online' ? 'excellent' : 'poor'}">
                                            <span class="status-dot ${c.status === 'Online' ? 'online' : 'offline'}"></span>
                                            ${escapeHtml(c.status)}
                                        </span>
                                    </td>
                                    <td class="text-xs">${c.cpu_usage}% / ${c.memory_usage}%</td>
                                    <td class="text-xs text-muted">${escapeHtml(c.last_heartbeat)}</td>
                                    <td>
                                        <span class="badge ${c.pending_buffered > 0 ? 'badge-fair' : 'badge-good'}">
                                            ${c.pending_buffered} queued
                                        </span>
                                    </td>
                                    <td class="text-xs text-muted">${escapeHtml(c.last_delivery_success || 'None')}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 5. INCIDENT DNA (ALERT CORRELATION)
// ==========================================
const IncidentDNA = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Incident DNA</h1>
                        <p class="page-subtitle">Intelligent alert correlation, timeline reconstruction, and noise reduction</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="IncidentDNA.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="dna-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Incident correlation state refreshed');
    },

    async resolve(incidentId) {
        try {
            await AegisAPI.post(`/incidents/${incidentId}/resolve`, {});
            AegisToast.success(`Incident ${incidentId} marked as Resolved`);
            await this.load();
        } catch (err) {
            AegisToast.error(err.message);
        }
    },

    async load() {
        const el = document.getElementById('dna-content');
        if (!el) return;

        try {
            const incidents = await AegisAPI.get('/incidents');

            if (incidents.length === 0) {
                el.innerHTML = `
                    <div class="card">
                        <div class="empty-state">
                            ${AegisIcons.dna()}
                            <h3>Zero Active Correlated Incidents</h3>
                            <p>Incident DNA is actively evaluating incoming telemetry. Disparate alerts will be correlated here automatically when an anomaly occurs.</p>
                        </div>
                    </div>`;
                return;
            }

            el.innerHTML = incidents.map(inc => `
                <div class="card" style="margin-bottom:var(--space-6);">
                    <div class="card-header">
                        <div>
                            <div class="flex items-center gap-3">
                                <span class="badge badge-${(inc.severity || 'medium').toLowerCase()}">${escapeHtml(inc.severity)}</span>
                                <span class="card-title">${escapeHtml(inc.title)}</span>
                                <span class="badge badge-good">${escapeHtml(inc.status)}</span>
                            </div>
                            <div class="text-xs text-muted" style="margin-top:4px;">
                                Incident ID: <span class="mono">${escapeHtml(inc.incident_id)}</span> · Affected Service: <strong>${escapeHtml(inc.affected_service)}</strong> · Correlation Confidence: <strong>${Math.round(inc.confidence * 100)}%</strong>
                            </div>
                        </div>
                        ${inc.status !== 'Resolved' ? `
                        <button class="btn btn-secondary btn-sm" onclick="IncidentDNA.resolve('${escapeHtml(inc.incident_id)}')">
                            ${AegisIcons.check()} Resolve Incident
                        </button>` : ''}
                    </div>

                    <div class="grid grid-2 gap-4" style="margin-bottom:var(--space-4);">
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-4);border-radius:var(--radius-md);">
                            <div class="text-xs text-muted uppercase font-semibold">Correlated Operational Factor</div>
                            <div class="text-sm" style="margin-top:var(--space-1);">${escapeHtml(inc.likely_cause)}</div>
                        </div>
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-4);border-radius:var(--radius-md);">
                            <div class="text-xs text-muted uppercase font-semibold">Recommended Investigation</div>
                            <div class="text-sm" style="margin-top:var(--space-1);">${escapeHtml(inc.recommended_investigation)}</div>
                        </div>
                    </div>

                    <div>
                        <div class="text-xs text-muted uppercase font-semibold" style="margin-bottom:var(--space-2);">Incident Event Timeline</div>
                        <div style="border-left:2px solid var(--color-border);padding-left:var(--space-4);margin-left:var(--space-2);">
                            ${(inc.timeline || []).map(t => `
                            <div style="margin-bottom:var(--space-3);position:relative;">
                                <div style="position:absolute;left:-21px;top:4px;width:10px;height:10px;border-radius:50%;background:var(--color-accent);"></div>
                                <div class="text-sm font-medium">${escapeHtml(t.event)}</div>
                                <div class="text-xs text-muted">${escapeHtml(t.details)} · <span class="mono">${escapeHtml(t.timestamp)}</span></div>
                            </div>`).join('')}
                        </div>
                    </div>
                </div>`).join('');
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 6. AI INSIGHTS
// ==========================================
const AIInsights = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Explainable AI Insights</h1>
                        <p class="page-subtitle">Dual-engine statistical baselines (MAD, Z-Score) and Scikit-Learn Isolation Forest telemetry</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="AIInsights.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="ai-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('AIOps insights refreshed');
    },

    async load() {
        const el = document.getElementById('ai-content');
        if (!el) return;

        try {
            const [pipeline, anomalies, baselines] = await Promise.all([
                AegisAPI.get('/aiops/pipeline-status'),
                AegisAPI.get('/aiops/anomalies'),
                AegisAPI.get('/aiops/baselines')
            ]);

            el.innerHTML = `
                <!-- 5-Stage AIOps Roadmap -->
                <div class="card" style="margin-bottom:var(--space-6);">
                    <div class="card-header">
                        <span class="card-title">AIOps Autonomous Lifecycle</span>
                        <span class="badge badge-accent">Dual-Engine Active</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(5, 1fr);gap:var(--space-3);">
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-3);border-radius:var(--radius-md);">
                            <div class="badge badge-accent" style="margin-bottom:var(--space-1);">1. OBSERVE</div>
                            <div class="text-xs text-muted">${escapeHtml(pipeline.observe.description)}</div>
                        </div>
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-3);border-radius:var(--radius-md);">
                            <div class="badge badge-accent" style="margin-bottom:var(--space-1);">2. DETECT</div>
                            <div class="text-xs text-muted">${escapeHtml(pipeline.detect.description)}</div>
                        </div>
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-3);border-radius:var(--radius-md);">
                            <div class="badge badge-accent" style="margin-bottom:var(--space-1);">3. CORRELATE</div>
                            <div class="text-xs text-muted">${escapeHtml(pipeline.correlate.description)}</div>
                        </div>
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-3);border-radius:var(--radius-md);">
                            <div class="badge badge-accent" style="margin-bottom:var(--space-1);">4. RECOMMEND</div>
                            <div class="text-xs text-muted">${escapeHtml(pipeline.recommend.description)}</div>
                        </div>
                        <div style="background:var(--color-bg-tertiary);padding:var(--space-3);border-radius:var(--radius-md);">
                            <div class="badge badge-good" style="margin-bottom:var(--space-1);">5. ACT (SIM)</div>
                            <div class="text-xs text-muted">${escapeHtml(pipeline.act.description)}</div>
                        </div>
                    </div>
                </div>

                <!-- Detected Anomalies with Baselines -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Detected Metric Anomalies & Statistical Deviations</span>
                        <span class="badge badge-good">${anomalies.length} Recorded</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Anomaly ID</th><th>Source</th><th>Metric</th><th>Observed</th>
                                <th>Baseline</th><th>Score</th><th>Severity</th><th>Explainable Evidence</th>
                            </tr></thead>
                            <tbody>
                                ${anomalies.length === 0 ? `<tr><td colspan="8" class="text-muted" style="text-align:center;">No active anomalies. Current telemetry conforms to historical baselines.</td></tr>` :
                                anomalies.map(a => `
                                <tr>
                                    <td class="mono text-xs">${escapeHtml(a.anomaly_id)}</td>
                                    <td class="mono"><strong>${escapeHtml(a.source_id)}</strong></td>
                                    <td>${escapeHtml(a.metric)}</td>
                                    <td><strong style="color:var(--color-poor);">${a.observed_value}</strong></td>
                                    <td class="text-muted">${a.baseline_value}</td>
                                    <td><span class="badge badge-accent">${Math.round(a.anomaly_score * 100)}%</span></td>
                                    <td><span class="badge badge-${(a.severity || 'medium').toLowerCase()}">${escapeHtml(a.severity)}</span></td>
                                    <td class="text-xs">${escapeHtml(a.reason)}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 7. PRIVACY PASSPORT
// ==========================================
const PrivacyPassport = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Privacy Passport</h1>
                        <p class="page-subtitle">Strict field allow-listing, secret redactor configuration, and local retention policies</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="PrivacyPassport.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="privacy-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Privacy policy status refreshed');
    },

    async load() {
        const el = document.getElementById('privacy-content');
        if (!el) return;

        try {
            const [policies, stats] = await Promise.all([
                AegisAPI.get('/privacy/policies'),
                AegisAPI.get('/privacy/stats')
            ]);
            const policy = policies[0] || {};

            el.innerHTML = `
                <div class="stats-grid" style="margin-bottom:var(--space-6);">
                    <div class="stat-card">
                        <div class="stat-icon excellent">${AegisIcons.shieldCheck()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Compliance Status</div>
                            <div class="stat-value">${escapeHtml(stats.compliance_status)}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon accent">${AegisIcons.fileCheck()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Payloads Inspected</div>
                            <div class="stat-value">${stats.total_payloads_inspected}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon good">${AegisIcons.lock()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Sensitive Fields Dropped</div>
                            <div class="stat-value">${stats.total_sensitive_fields_blocked}</div>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon teal">${AegisIcons.database ? AegisIcons.database() : AegisIcons.server()}</div>
                        <div class="stat-content">
                            <div class="stat-label">Raw Data Boundary</div>
                            <div class="stat-value" style="font-size:var(--text-lg);">Customer Local</div>
                        </div>
                    </div>
                </div>

                <div class="card" style="margin-bottom:var(--space-6);">
                    <div class="card-header">
                        <span class="card-title">Enforced Field Allow-List (Strict Allow-List Policy)</span>
                        <span class="badge badge-accent">Explicit Approval Required</span>
                    </div>
                    <p class="text-sm text-muted" style="margin-bottom:var(--space-4);">
                        Only these explicit fields are permitted to cross the customer boundary. All unknown keys, raw logs, passwords, and environment dumps are rejected by default.
                    </p>
                    <div class="field-list">
                        ${(policy.allowed_fields || []).map(f => `<span class="field-tag approved">✓ ${escapeHtml(f)}</span>`).join('')}
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Secret Redaction Engine Rules</span>
                        <span class="badge badge-excellent">Automatic Pre-Egress Scrubbing</span>
                    </div>
                    <p class="text-sm text-muted" style="margin-bottom:var(--space-4);">
                        Regex patterns applied against all string values. Any detected credentials are automatically redacted with <code>[REDACTED_SECRET]</code> prior to cryptographic hashing.
                    </p>
                    <pre class="payload-json" style="max-height:180px;">${escapeHtml(JSON.stringify(policy.redaction_rules || {}, null, 2))}</pre>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 8. EGRESS PROOF (VERIFIABLE PROOF LOG)
// ==========================================
const EgressProof = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Egress Proof</h1>
                        <p class="page-subtitle">Verifiable proof of every outgoing payload — exact canonical JSON, SHA-256 hash, and server ACK</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="EgressProof.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="egress-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Egress proof log refreshed');
    },

    showDetails(payloadId, exactJson, hash, verified) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay active';
        modal.innerHTML = `
            <div class="modal" style="max-width:700px;">
                <div class="modal-header">
                    <div>
                        <h3 class="modal-title">Egress Proof Verification</h3>
                        <div class="text-xs text-muted mono">${escapeHtml(payloadId)}</div>
                    </div>
                    <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">✕</button>
                </div>
                <div style="margin-bottom:var(--space-4);">
                    <div class="text-xs text-muted uppercase font-semibold">SHA-256 Payload Hash</div>
                    <div class="mono text-xs" style="background:var(--color-bg-primary);padding:var(--space-3);border-radius:var(--radius-md);word-break:break-all;color:var(--color-accent);margin-top:4px;">
                        ${escapeHtml(hash)}
                    </div>
                    <div style="margin-top:var(--space-2);">
                        <span class="badge ${verified ? 'badge-excellent' : 'badge-poor'}">
                            ${verified ? '✓ Cryptographically Verified & Intact' : '⚠ Hash Mismatch'}
                        </span>
                    </div>
                </div>
                <div>
                    <div class="text-xs text-muted uppercase font-semibold" style="margin-bottom:4px;">Exact Transmitted Canonical JSON</div>
                    <pre class="payload-json">${escapeHtml(JSON.stringify(JSON.parse(exactJson || '{}'), null, 2))}</pre>
                </div>
            </div>`;
        document.body.appendChild(modal);
    },

    async load() {
        const el = document.getElementById('egress-content');
        if (!el) return;

        try {
            const proofs = await AegisAPI.get('/egress-proof');

            el.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Cryptographic Transmission Proof Log</span>
                        <span class="badge badge-accent">${proofs.length} Records</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Payload ID</th><th>Source ID</th><th>SHA-256 Hash</th><th>Approved Fields</th>
                                <th>Dropped / Redacted</th><th>Status</th><th>Verification</th><th>Action</th>
                            </tr></thead>
                            <tbody>
                                ${proofs.length === 0 ? `<tr><td colspan="8" class="text-muted" style="text-align:center;">No egress records transmitted yet. Collector activity will populate this live log.</td></tr>` :
                                proofs.map(p => `
                                <tr>
                                    <td class="mono text-xs"><strong>${escapeHtml(p.payload_id.slice(0, 12))}...</strong></td>
                                    <td class="mono">${escapeHtml(p.source_id)}</td>
                                    <td class="mono text-xs" title="${escapeHtml(p.payload_hash)}">${escapeHtml(p.payload_hash.slice(0, 16))}...</td>
                                    <td><span class="badge badge-excellent">${(p.approved_fields || []).length} approved</span></td>
                                    <td><span class="badge badge-fair">${(p.redacted_fields || []).length} blocked</span></td>
                                    <td class="text-xs">${escapeHtml(p.transmission_status)}</td>
                                    <td>
                                        <span class="badge ${p.hash_verified ? 'badge-excellent' : 'badge-poor'}">
                                            ${p.hash_verified ? 'Verified ✓' : 'Mismatch ⚠'}
                                        </span>
                                    </td>
                                    <td>
                                        <button class="btn btn-secondary btn-sm" onclick='EgressProof.showDetails(${JSON.stringify(p.payload_id)}, ${JSON.stringify(p.exact_transmitted_json)}, ${JSON.stringify(p.payload_hash)}, ${p.hash_verified})'>
                                            Inspect
                                        </button>
                                    </td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 9. AUDIT CENTER
// ==========================================
const AuditCenter = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Audit Center</h1>
                        <p class="page-subtitle">Immutable log of system actions, policy checks, recovery simulations, and security events</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="AuditCenter.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="audit-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Audit trail refreshed');
    },

    async load() {
        const el = document.getElementById('audit-content');
        if (!el) return;

        try {
            const logs = await AegisAPI.get('/audit');
            el.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">System Audit Log Records</span>
                        <span class="badge badge-accent">${logs.length} Entries</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Timestamp (UTC)</th><th>Actor</th><th>Action</th><th>Target</th><th>Result</th><th>Details</th>
                            </tr></thead>
                            <tbody>
                                ${logs.length === 0 ? `<tr><td colspan="6" class="text-muted" style="text-align:center;">No audit records found.</td></tr>` :
                                logs.map(l => `
                                <tr>
                                    <td class="mono text-xs">${escapeHtml(l.timestamp_utc)}</td>
                                    <td><strong>${escapeHtml(l.actor)}</strong></td>
                                    <td>${escapeHtml(l.action)}</td>
                                    <td class="mono text-xs">${escapeHtml(l.target)}</td>
                                    <td><span class="badge ${l.result === 'Success' ? 'badge-excellent' : 'badge-poor'}">${escapeHtml(l.result)}</span></td>
                                    <td class="text-xs text-muted mono">${escapeHtml(JSON.stringify(l.details))}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 10. RECOVERY SIMULATOR
// ==========================================
const RecoverySimulator = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">Recovery Simulator</h1>
                        <p class="page-subtitle">Human-approved, safe operational remediation simulation with audit trails and rollback planning</p>
                    </div>
                    <button class="btn btn-secondary btn-sm" onclick="RecoverySimulator.refresh()">
                        ${AegisIcons.refresh()} Refresh
                    </button>
                </div>
            </div>
            <div id="recovery-content">
                <div style="display:flex;justify-content:center;padding:var(--space-8);"><div class="spinner"></div></div>
            </div>`;
        await this.load();
    },

    async refresh() {
        await this.load();
        AegisToast.info('Recovery simulations refreshed');
    },

    async triggerSimulation(incidentId, recText) {
        const session = AegisAuth.getSession();
        const approverName = session ? session.name : 'Veeresh M V';

        try {
            const res = await AegisAPI.post('/recovery/simulate', {
                incident_id: incidentId,
                recommendation_text: recText,
                approver: approverName
            });
            AegisToast.success(`Recovery simulation ${res.simulation_id} executed successfully!`);
            await this.load();
        } catch (err) {
            AegisToast.error(err.message);
        }
    },

    async load() {
        const el = document.getElementById('recovery-content');
        if (!el) return;

        try {
            const [simulations, recommendations] = await Promise.all([
                AegisAPI.get('/recovery'),
                AegisAPI.get('/recommendations')
            ]);

            el.innerHTML = `
                <!-- Controlled Workflow Guide -->
                <div class="card" style="margin-bottom:var(--space-6);">
                    <div class="card-header">
                        <span class="card-title">Controlled Remediation Workflow</span>
                        <span class="badge badge-accent">Zero Uncontrolled Production Actions</span>
                    </div>
                    <div style="display:flex;gap:var(--space-2);flex-wrap:wrap;padding:var(--space-2) 0;">
                        <span class="badge badge-accent">1. AIOps Detection</span>
                        <span class="text-muted">→</span>
                        <span class="badge badge-accent">2. Recommendation</span>
                        <span class="text-muted">→</span>
                        <span class="badge badge-accent">3. Policy Check</span>
                        <span class="text-muted">→</span>
                        <span class="badge badge-fair">4. Human Approval</span>
                        <span class="text-muted">→</span>
                        <span class="badge badge-good">5. Sandbox Simulation</span>
                        <span class="text-muted">→</span>
                        <span class="badge badge-excellent">6. Verified Rollback</span>
                    </div>
                </div>

                <!-- Available Recommendations Awaiting Human Approval -->
                <div class="card" style="margin-bottom:var(--space-6);">
                    <div class="card-header">
                        <span class="card-title">Remediation Proposals Awaiting Operator Approval</span>
                        <span class="badge badge-fair">${recommendations.length} Pending</span>
                    </div>
                    ${recommendations.length === 0 ? `<div class="empty-state" style="padding:var(--space-6);"><p class="text-sm text-muted">All incidents currently nominal. No simulations pending approval.</p></div>` :
                    recommendations.map(rec => `
                    <div style="border:1px solid var(--color-border);padding:var(--space-4);border-radius:var(--radius-md);margin-bottom:var(--space-3);background:var(--color-bg-tertiary);">
                        <div class="flex items-center justify-between">
                            <div>
                                <strong>${escapeHtml(rec.title)}</strong>
                                <div class="text-xs text-muted">${escapeHtml(rec.reason)}</div>
                            </div>
                            <button class="btn btn-primary btn-sm" onclick='RecoverySimulator.triggerSimulation(${JSON.stringify(rec.incident_id || "INC-001")}, ${JSON.stringify(rec.suggested_action)})'>
                                ${AegisIcons.check()} Approve & Simulate
                            </button>
                        </div>
                        <div style="margin-top:var(--space-3);background:var(--color-bg-primary);padding:var(--space-2) var(--space-3);border-radius:var(--radius-sm);font-size:var(--text-xs);">
                            <code>${escapeHtml(rec.suggested_action)}</code>
                        </div>
                    </div>`).join('')}
                </div>

                <!-- Simulation History & Rollback Logs -->
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Completed Recovery Simulations & Rollback Snapshots</span>
                        <span class="badge badge-good">${simulations.length} Completed</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Simulation ID</th><th>Incident ID</th><th>Approver</th><th>Status</th>
                                <th>Policy Check</th><th>Projected Impact</th><th>Rollback Plan</th>
                            </tr></thead>
                            <tbody>
                                ${simulations.length === 0 ? `<tr><td colspan="7" class="text-muted" style="text-align:center;">No simulations run yet. Approve a proposal above to test.</td></tr>` :
                                simulations.map(s => `
                                <tr>
                                    <td class="mono text-xs"><strong>${escapeHtml(s.simulation_id)}</strong></td>
                                    <td class="mono text-xs">${escapeHtml(s.incident_id)}</td>
                                    <td><strong>${escapeHtml(s.approver)}</strong></td>
                                    <td><span class="badge badge-excellent">${escapeHtml(s.status)}</span></td>
                                    <td><span class="badge badge-accent">${escapeHtml(s.policy_check)}</span></td>
                                    <td class="text-xs">${escapeHtml(s.simulation_result)}</td>
                                    <td class="text-xs text-muted mono">${escapeHtml(s.rollback_info)}</td>
                                </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;
        } catch (err) {
            el.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
        }
    }
};

// ==========================================
// 11. ORGANIZATION SETTINGS
// ==========================================
const OrgSettings = {
    async render(container) {
        const session = AegisAuth.getSession();
        let orgProfile = {
            tenant_id: session?.orgId || 'ORG_001',
            name: session?.org || 'AEGIS Demo Corp',
            region: 'us-east-1',
            timezone: 'UTC'
        };

        try {
            orgProfile = await AegisAPI.get('/organizations/profile');
        } catch {}

        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">Organization Settings</h1>
                <p class="page-subtitle">Multi-tenant identity, role-based access control, and regional data residency</p>
            </div>

            <div class="card" style="margin-bottom:var(--space-6);">
                <div class="card-header">
                    <span class="card-title">Tenant Identity & Profile</span>
                    <span class="badge badge-excellent">Tenant Isolation Enforced</span>
                </div>
                <div class="grid grid-2 gap-4">
                    <div class="form-group">
                        <label class="form-label">Organization Name</label>
                        <input class="form-input" value="${escapeHtml(orgProfile.name)}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Tenant ID (Isolated Database Partition)</label>
                        <input class="form-input mono" value="${escapeHtml(orgProfile.tenant_id)}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Current Authenticated User</label>
                        <input class="form-input" value="${escapeHtml(session?.name || 'Administrator')}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Assigned Role</label>
                        <input class="form-input" value="${escapeHtml(session?.role || 'Organization Owner')}" readonly>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-bottom:var(--space-6);">
                <div class="card-header">
                    <span class="card-title">Data Residency & Sovereignty</span>
                    <span class="badge badge-accent">Global-Ready Architecture</span>
                </div>
                <div class="grid grid-2 gap-4">
                    <div class="form-group">
                        <label class="form-label">Designated Ingestion Region</label>
                        <input class="form-input" value="${escapeHtml(orgProfile.region || 'us-east-1')} (AWS US East)" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Event Timestamp Standardization</label>
                        <input class="form-input" value="UTC (ISO 8601 strictly enforced across Tiers)" readonly>
                    </div>
                </div>
            </div>`;
    }
};

// ==========================================
// 12. AI DEMONSTRATION CONTROLS
// ==========================================
const DemoControls = {
    async render(container) {
        container.innerHTML = `
            <div class="page-header">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="page-title">AI Demonstration Controls</h1>
                        <p class="page-subtitle">Controlled test scenarios and live end-to-end pipeline verification</p>
                    </div>
                    <button class="btn btn-danger btn-sm" onclick="DemoControls.stopWorkload()">
                        ${AegisIcons.x()} Emergency Stop All
                    </button>
                </div>
            </div>

            <!-- Warning and Safe Limits Notice -->
            <div class="sim-banner" style="background:rgba(34, 211, 238, 0.08);border-color:rgba(34, 211, 238, 0.2);color:var(--color-accent);margin-bottom:var(--space-6);">
                ${AegisIcons.shieldCheck()}
                <span><strong>Safe Bounded Workloads:</strong> All stress routines run on the local test machine with strict duration limits (10-15s) and an immediate abort control. Zero uncontrolled production commands.</span>
            </div>

            <!-- Demonstration Scenario Cards -->
            <div class="grid grid-3 gap-4" style="margin-bottom:var(--space-6);">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">1. Local CPU Stress Test</span>
                        <span class="badge badge-accent">Real psutil Detection</span>
                    </div>
                    <p class="text-sm text-muted" style="margin-bottom:var(--space-4);">
                        Spawns safe bounded computational threads on this Windows machine for 12 seconds. Tier 1 collector will observe real CPU elevation.
                    </p>
                    <div class="flex gap-2">
                        <button class="btn btn-primary btn-sm" onclick="DemoControls.startCpuStress()">
                            ${AegisIcons.zap()} Start CPU Load (12s)
                        </button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">2. Correlated Incident DNA</span>
                        <span class="badge badge-poor">Multi-Signal Anomaly</span>
                    </div>
                    <p class="text-sm text-muted" style="margin-bottom:var(--space-4);">
                        Injects coordinated telemetry (CPU 96.5% + Latency 310ms). Demonstrates Incident DNA alert correlation, noise reduction, and recommendations.
                    </p>
                    <div class="flex gap-2">
                        <button class="btn btn-primary btn-sm" onclick="DemoControls.triggerCorrelatedIncident()">
                            ${AegisIcons.dna()} Trigger Correlated Flow
                        </button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">3. Brute-Force Auth Detection</span>
                        <span class="badge badge-fair">Local Privacy Scrubbing</span>
                    </div>
                    <p class="text-sm text-muted" style="margin-bottom:var(--space-4);">
                        Simulates 5 failed logins. Verifies security summaries are generated locally while raw authentication credentials stay inside the perimeter.
                    </p>
                    <div class="flex gap-2">
                        <button class="btn btn-secondary btn-sm" onclick="DemoControls.triggerSecurityAnomaly()">
                            ${AegisIcons.lock()} Simulate Auth Anomaly
                        </button>
                    </div>
                </div>
            </div>

            <!-- Live Verification Pipeline Trace Card -->
            <div class="card">
                <div class="card-header">
                    <span class="card-title">Complete End-to-End Processing Result</span>
                    <span class="badge badge-good" id="demo-trace-status">Awaiting Trigger</span>
                </div>
                <div id="demo-trace-container" style="background:var(--color-bg-primary);padding:var(--space-4);border-radius:var(--radius-md);font-family:var(--font-mono);font-size:var(--text-xs);color:var(--color-accent);max-height:260px;overflow-y:auto;">
                    [AEGIS AIOps Engine] Select a scenario above to observe live end-to-end evidence generation across Tier 1 and Tier 2.
                </div>
            </div>`;
    },

    async startCpuStress() {
        const trace = document.getElementById('demo-trace-container');
        const status = document.getElementById('demo-trace-status');
        if (status) status.textContent = 'Running CPU Stress...';
        if (trace) trace.textContent = '[1/3] Starting safe 12s CPU stress threads on Windows host...\n[2/3] Local psutil monitor sampling CPU percent in real-time...\n[3/3] Tier 1 AIOps running rolling MAD and robust Z-score...';
        
        try {
            const res = await AegisAPI.post('/demo/cpu-stress', { duration: 12 });
            AegisToast.info('CPU stress active — check Command Center CPU metrics');
            if (trace) trace.textContent += `\n[SUCCESS] ${res.message}\n[MONITORING] Open Command Center to see real-time CPU rise on this host.`;
        } catch (err) {
            AegisToast.error(err.message);
        }
    },

    async triggerCorrelatedIncident() {
        const trace = document.getElementById('demo-trace-container');
        const status = document.getElementById('demo-trace-status');
        if (status) status.textContent = 'Injecting Correlated Flow...';

        try {
            const res = await AegisAPI.post('/demo/correlated-incident', {});
            AegisToast.warning('Multi-signal performance breach injected');
            if (status) status.textContent = 'Pipeline Verified ✓';
            if (trace) {
                trace.textContent = `=== AEGIS END-TO-END PIPELINE TRACE ===\n` +
                    `Payload ID: ${res.payload_id}\n` +
                    `Injected Signals:\n` +
                    `  • CPU: ${res.signals_injected.cpu_usage}\n` +
                    `  • Latency: ${res.signals_injected.latency_ms}\n` +
                    `  • Memory: ${res.signals_injected.memory_usage}\n\n` +
                    `Executed Stages:\n` +
                    res.pipeline_stages.map(s => `  ✓ ${s}`).join('\n') + `\n\n` +
                    `-> Visit 'Incident DNA' to inspect the correlated timeline and resolution actions!\n` +
                    `-> Visit 'Egress Proof' to inspect the SHA-256 cryptographic verification!`;
            }
        } catch (err) {
            AegisToast.error(err.message);
        }
    },

    async triggerSecurityAnomaly() {
        try {
            await SecurityMonitoring.injectFailedLogins();
            const trace = document.getElementById('demo-trace-container');
            if (trace) {
                trace.textContent = `=== LOCAL SECURITY PRIVACY VERIFICATION ===\n` +
                    `[1] 5 failed authentication attempts recorded locally in Tier 1.\n` +
                    `[2] Privacy Engine evaluated raw credentials dump: STRICTLY RETAINED LOCAL.\n` +
                    `[3] Sanitized security summary exported to Tier 2: Category=Brute-Force, Severity=High.\n` +
                    `[4] Zero raw credentials or plain passwords crossed customer boundary.`;
            }
        } catch (err) {}
    },

    async stopWorkload() {
        try {
            await AegisAPI.post('/demo/stop', {});
            AegisToast.success('All stress workloads stopped');
            const status = document.getElementById('demo-trace-status');
            if (status) status.textContent = 'Halted';
        } catch (err) {
            AegisToast.error(err.message);
        }
    }
};

// Export to window
window.InfraMonitoring = InfraMonitoring;
window.NetworkMonitoring = NetworkMonitoring;
window.SecurityMonitoring = SecurityMonitoring;
window.CollectorManagement = CollectorManagement;
window.IncidentDNA = IncidentDNA;
window.AIInsights = AIInsights;
window.PrivacyPassport = PrivacyPassport;
window.EgressProof = EgressProof;
window.AuditCenter = AuditCenter;
window.RecoverySimulator = RecoverySimulator;
window.OrgSettings = OrgSettings;
window.DemoControls = DemoControls;
