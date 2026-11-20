/**
 * AEGIS Module Stubs — Placeholder pages for all navigation modules.
 * Each module gets a proper implementation in later milestones.
 */

function createModulePage(title, subtitle, icon, sections = []) {
    const sectionsHTML = sections.map(s => `
        <div class="card" style="margin-bottom:var(--space-4);">
            <div class="card-header">
                <span class="card-title">${s.title}</span>
                ${s.badge ? `<span class="badge badge-accent">${s.badge}</span>` : ''}
            </div>
            <div>${s.content}</div>
        </div>`).join('');

    return `
        <div class="page-header">
            <h1 class="page-title">${title}</h1>
            <p class="page-subtitle">${subtitle}</p>
        </div>
        <div class="sim-banner">
            ${AegisIcons.alertTriangle()}
            <span>Module under development — Backend integration pending. Layout and structure are functional.</span>
        </div>
        ${sectionsHTML || `
        <div class="empty-state">
            ${icon}
            <h3>${title}</h3>
            <p>This module will be connected to live backend APIs in upcoming milestones.</p>
        </div>`}`;
}

// Infrastructure Monitoring
const InfraMonitoring = {
    render(container) {
        container.innerHTML = createModulePage(
            'Infrastructure Monitoring',
            'Server health, resource utilization, and anomaly detection',
            AegisIcons.server(),
            [
                {
                    title: 'Registered Servers',
                    badge: 'Milestone 7',
                    content: `
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Source ID</th><th>Host</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Health</th><th>Last Seen</th>
                            </tr></thead>
                            <tbody id="infra-table-body">
                                <tr><td colspan="7" class="text-muted" style="text-align:center;padding:var(--space-6);">
                                    Awaiting collector data — connect a Tier 1 collector to see live metrics
                                </td></tr>
                            </tbody>
                        </table>
                    </div>`
                }
            ]
        );
    }
};

// Network Monitoring
const NetworkMonitoring = {
    render(container) {
        container.innerHTML = createModulePage(
            'Network Monitoring',
            'Bandwidth, latency, packet loss, and connectivity health',
            AegisIcons.network(),
            [
                {
                    title: 'Network Health Overview',
                    badge: 'Milestone 7',
                    content: `
                    <div class="stats-grid" style="margin-bottom:0;">
                        <div class="stat-card">
                            <div class="stat-icon teal">${AegisIcons.wifi()}</div>
                            <div class="stat-content">
                                <div class="stat-label">Avg Latency</div>
                                <div class="stat-value">— ms</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon fair">${AegisIcons.activity()}</div>
                            <div class="stat-content">
                                <div class="stat-label">Packet Loss</div>
                                <div class="stat-value">— %</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon accent">${AegisIcons.network()}</div>
                            <div class="stat-content">
                                <div class="stat-label">Bandwidth</div>
                                <div class="stat-value">— Mbps</div>
                            </div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-icon excellent">${AegisIcons.globe()}</div>
                            <div class="stat-content">
                                <div class="stat-label">Connectivity</div>
                                <div class="stat-value">—</div>
                            </div>
                        </div>
                    </div>`
                }
            ]
        );
    }
};

// Security Monitoring
const SecurityMonitoring = {
    render(container) {
        container.innerHTML = createModulePage(
            'Security Monitoring',
            'Authentication failures, suspicious activity, and threat detection',
            AegisIcons.lock(),
            [
                {
                    title: 'Security Alerts',
                    badge: 'Milestone 7',
                    content: `
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Severity</th><th>Event</th><th>Source</th><th>Count</th><th>Time</th><th>Status</th>
                            </tr></thead>
                            <tbody>
                                <tr><td colspan="6" class="text-muted" style="text-align:center;padding:var(--space-6);">
                                    No security events — connect collector for real-time detection
                                </td></tr>
                            </tbody>
                        </table>
                    </div>`
                }
            ]
        );
    }
};

// Collector Management
const CollectorManagement = {
    render(container) {
        container.innerHTML = createModulePage(
            'Collector Management',
            'Monitor and manage Tier 1 collectors across your infrastructure',
            AegisIcons.radio(),
            [
                {
                    title: 'Registered Collectors',
                    badge: 'Milestone 5',
                    content: `
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Collector ID</th><th>Host</th><th>Version</th><th>Status</th>
                                <th>Last Heartbeat</th><th>Buffered</th><th>Config</th>
                            </tr></thead>
                            <tbody>
                                <tr><td colspan="7" class="text-muted" style="text-align:center;padding:var(--space-6);">
                                    No collectors registered — start a Tier 1 collector to see it here
                                </td></tr>
                            </tbody>
                        </table>
                    </div>`
                }
            ]
        );
    }
};

// Incident DNA
const IncidentDNA = {
    render(container) {
        container.innerHTML = createModulePage(
            'Incident DNA',
            'Correlated incidents, alert grouping, and root cause analysis',
            AegisIcons.dna(),
            [
                {
                    title: 'Active Incidents',
                    badge: 'Milestone 8',
                    content: `<div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">Incident correlation engine will group related alerts and display incident timelines.</p>
                    </div>`
                }
            ]
        );
    }
};

// AI Insights
const AIInsights = {
    render(container) {
        container.innerHTML = createModulePage(
            'AI Insights',
            'Anomaly detection, explainable recommendations, and AIOps analysis',
            AegisIcons.brain(),
            [
                {
                    title: 'AIOps Pipeline Status',
                    content: `
                    <div class="flex gap-4" style="flex-wrap:wrap;">
                        <div class="badge badge-accent">OBSERVE — Active</div>
                        <div class="badge badge-accent">DETECT — Active</div>
                        <div class="badge badge-info">CORRELATE — Pending data</div>
                        <div class="badge badge-info">RECOMMEND — Pending data</div>
                        <div class="badge badge-info">ACT — Requires approval</div>
                    </div>`
                },
                {
                    title: 'Recent Anomalies',
                    badge: 'Milestone 8',
                    content: `<div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">AIOps engine will display detected anomalies with baselines, deviations, and evidence.</p>
                    </div>`
                }
            ]
        );
    }
};

// Privacy Passport
const PrivacyPassport = {
    render(container) {
        container.innerHTML = createModulePage(
            'Privacy Passport',
            'Data classification, privacy policies, and field-level controls',
            AegisIcons.fingerprint(),
            [
                {
                    title: 'Active Privacy Policies',
                    badge: 'Milestone 4',
                    content: `<div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">Privacy engine configuration, field allow-lists, and redaction rules will appear here.</p>
                    </div>`
                }
            ]
        );
    }
};

// Egress Proof
const EgressProof = {
    render(container) {
        container.innerHTML = createModulePage(
            'Egress Proof',
            'Verifiable proof of every outgoing payload — what was sent, what was redacted',
            AegisIcons.fileCheck(),
            [
                {
                    title: 'Transmission Log',
                    badge: 'Milestone 4',
                    content: `
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Payload ID</th><th>Tenant</th><th>Source</th><th>Timestamp</th>
                                <th>Approved Fields</th><th>Redacted</th><th>Hash</th><th>Status</th>
                            </tr></thead>
                            <tbody>
                                <tr><td colspan="8" class="text-muted" style="text-align:center;padding:var(--space-6);">
                                    No egress records — connect collector with privacy pipeline enabled
                                </td></tr>
                            </tbody>
                        </table>
                    </div>`
                }
            ]
        );
    }
};

// Audit Center
const AuditCenter = {
    render(container) {
        container.innerHTML = createModulePage(
            'Audit Center',
            'Complete audit trail of all system operations and data access',
            AegisIcons.clipboardList(),
            [
                {
                    title: 'Audit Log',
                    badge: 'Milestone 9',
                    content: `
                    <div class="table-container">
                        <table class="data-table">
                            <thead><tr>
                                <th>Timestamp</th><th>Actor</th><th>Action</th><th>Target</th><th>Result</th>
                            </tr></thead>
                            <tbody>
                                <tr><td colspan="5" class="text-muted" style="text-align:center;padding:var(--space-6);">
                                    Audit log entries will appear as system operations are performed
                                </td></tr>
                            </tbody>
                        </table>
                    </div>`
                }
            ]
        );
    }
};

// Recovery Simulator
const RecoverySimulator = {
    render(container) {
        container.innerHTML = createModulePage(
            'Recovery Simulator',
            'Safe remediation workflows with human approval and rollback tracking',
            AegisIcons.rotateCcw(),
            [
                {
                    title: 'Recovery Workflow',
                    badge: 'Milestone 9',
                    content: `
                    <div style="display:flex;gap:var(--space-3);flex-wrap:wrap;padding:var(--space-2) 0;">
                        <div class="badge badge-accent">1. AI Recommendation</div>
                        <span class="text-muted">→</span>
                        <div class="badge badge-info">2. Engineer Review</div>
                        <span class="text-muted">→</span>
                        <div class="badge badge-info">3. Policy Validation</div>
                        <span class="text-muted">→</span>
                        <div class="badge badge-info">4. Human Approval</div>
                        <span class="text-muted">→</span>
                        <div class="badge badge-info">5. Safe Simulation</div>
                        <span class="text-muted">→</span>
                        <div class="badge badge-info">6. Audit & Rollback</div>
                    </div>
                    <div class="empty-state" style="padding:var(--space-6);">
                        <p class="text-sm text-muted">Recovery simulator will execute safe remediation workflows after AIOps integration.</p>
                    </div>`
                }
            ]
        );
    }
};

// Organization Settings
const OrgSettings = {
    render(container) {
        const session = AegisAuth.getSession();
        container.innerHTML = `
            <div class="page-header">
                <h1 class="page-title">Organization Settings</h1>
                <p class="page-subtitle">Manage your organization, users, roles, and privacy policies</p>
            </div>
            <div class="card" style="margin-bottom:var(--space-4);">
                <div class="card-header">
                    <span class="card-title">Organization Profile</span>
                </div>
                <div class="grid grid-2 gap-4">
                    <div class="form-group">
                        <label class="form-label">Organization Name</label>
                        <input class="form-input" value="${session?.org || 'AEGIS Demo Corp'}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Organization ID</label>
                        <input class="form-input mono" value="${session?.orgId || 'ORG_001'}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Owner</label>
                        <input class="form-input" value="${session?.name || '—'}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Role</label>
                        <input class="form-input" value="${session?.role || '—'}" readonly>
                    </div>
                </div>
            </div>
            <div class="card" style="margin-bottom:var(--space-4);">
                <div class="card-header">
                    <span class="card-title">Data Residency</span>
                    <span class="badge badge-accent">Global-Ready</span>
                </div>
                <div class="grid grid-2 gap-4">
                    <div class="form-group">
                        <label class="form-label">Region</label>
                        <select class="form-select">
                            <option>US East (us-east-1)</option>
                            <option>EU West (eu-west-1)</option>
                            <option>Asia Pacific (ap-south-1)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Timezone</label>
                        <input class="form-input" value="UTC" readonly>
                        <div class="text-xs text-muted" style="margin-top:var(--space-1);">All events use UTC timestamps internally</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="card-header">
                    <span class="card-title">User Management</span>
                    <span class="badge badge-info">Milestone 6</span>
                </div>
                <div class="empty-state" style="padding:var(--space-6);">
                    <p class="text-sm text-muted">User management will be available after backend integration.</p>
                </div>
            </div>`;
    }
};

// Export all modules
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
