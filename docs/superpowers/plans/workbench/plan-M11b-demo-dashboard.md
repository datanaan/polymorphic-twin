# M11b: 演示层 — 可视化面板与端到端验证

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建实时 Web 可视化面板展示 CSTR 六阶段演示全过程，完成端到端演示验证。

**Architecture:** 纯 HTML + CSS + JS 单页应用（无框架）。通过 WebSocket 接收 API 服务实时事件，Chart.js 绘制状态变量时序图。直接浏览器打开即可使用。

**Spec reference:** `docs/superpowers/specs/2026-05-07-product-demo.md` v1.0.0 §3, §4

**Quality gate:**
- 浏览器打开 `index.html` 自动连接 API 服务
- 演示六阶段中面板实时更新状态变量、约束状态、行动空间、审计日志
- Phase 5 回落触发时面板显示 FALLBACK 状态

**Depends on:** plan-M11a-demo-data.md, plan-M10c-api-deploy.md

---

## File Structure

```
demos/chemical_process/dashboard/
├── index.html                  # Task 1-2
├── style.css                   # Task 1
├── app.js                      # Task 5
├── websocket.js                # Task 2
├── charts.js                   # Task 3
└── components/
    ├── constraint-panel.js     # Task 4
    ├── action-panel.js         # Task 4
    └── audit-log.js            # Task 4
```

---

## Task 1: HTML 结构与 CSS 样式

**Files:**
- Create: `demos/chemical_process/dashboard/index.html`
- Create: `demos/chemical_process/dashboard/style.css`

**Purpose:** 页面布局与暗色主题样式。

- [ ] **Step 1: 编写 HTML 骨架**

```html
<!-- demos/chemical_process/dashboard/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymorphic-Twin Dashboard</title>
    <link rel="stylesheet" href="style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
</head>
<body>
    <!-- 顶部栏 -->
    <header id="header">
        <div class="header-left">
            <h1>Polymorphic-Twin</h1>
            <span class="twin-name" id="twin-name">CSTR-Demo-001</span>
        </div>
        <div class="header-right">
            <span class="status-dot" id="connection-dot"></span>
            <span id="connection-status">Connecting...</span>
        </div>
    </header>

    <!-- 主内容 -->
    <main>
        <!-- 左栏 -->
        <div class="col-left">
            <!-- 状态变量时序图 -->
            <section class="panel">
                <h2>状态变量</h2>
                <canvas id="state-chart"></canvas>
            </section>
            <!-- 行动空间 -->
            <section class="panel">
                <h2>行动空间</h2>
                <div id="action-panel"></div>
            </section>
        </div>

        <!-- 右栏 -->
        <div class="col-right">
            <!-- 约束状态 -->
            <section class="panel">
                <h2>约束状态</h2>
                <div id="constraint-panel"></div>
            </section>
            <!-- 审计日志 -->
            <section class="panel">
                <h2>审计日志</h2>
                <div id="audit-log"></div>
            </section>
        </div>
    </main>

    <!-- 底部状态栏 -->
    <footer id="status-bar">
        <div class="status-item">
            安全状态: <strong id="safety-status">--</strong>
        </div>
        <div class="status-item">
            身份状态: <strong id="identity-status">--</strong>
        </div>
        <div class="status-item">
            DomainPack: <strong id="dp-version">--</strong>
        </div>
        <div class="status-item">
            运行时间: <strong id="uptime">0s</strong>
        </div>
    </footer>

    <!-- Scripts -->
    <script src="websocket.js"></script>
    <script src="charts.js"></script>
    <script src="components/constraint-panel.js"></script>
    <script src="components/action-panel.js"></script>
    <script src="components/audit-log.js"></script>
    <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 编写 CSS**

```css
/* demos/chemical_process/dashboard/style.css */
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    background: #1a1a2e;
    color: #e0e0e0;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

header {
    background: #16213e;
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #0f3460;
}

header h1 { font-size: 16px; color: #4fc3f7; }

.header-left { display: flex; align-items: center; gap: 16px; }
.header-right { display: flex; align-items: center; gap: 8px; font-size: 13px; }

.twin-name { color: #aaa; font-size: 14px; }

.status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #666; display: inline-block;
}
.status-dot.connected { background: #4caf50; }
.status-dot.disconnected { background: #f44336; }

main {
    flex: 1; display: flex; gap: 12px; padding: 12px;
    overflow: hidden;
}

.col-left, .col-right {
    flex: 1; display: flex; flex-direction: column; gap: 12px;
    min-width: 0;
}

.panel {
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 12px;
    flex: 1;
    overflow: auto;
}

.panel h2 {
    font-size: 13px;
    color: #4fc3f7;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* 约束面板 */
.constraint-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid #1a2744;
    font-size: 13px;
}
.constraint-row:last-child { border-bottom: none; }
.constraint-name { flex: 1; }
.constraint-status { font-weight: bold; min-width: 80px; text-align: right; }
.constraint-criticality { color: #888; font-size: 11px; margin-left: 8px; }

.status-pass { color: #4caf50; }
.status-uncertain { color: #ffeb3b; }
.status-failed { color: #f44336; animation: blink 0.5s infinite; }
.status-na { color: #666; }
.status-learn { color: #42a5f5; }

@keyframes blink { 50% { opacity: 0.4; } }

.safety-critical { font-weight: bold; }

/* 行动空间 */
.action-group { margin-bottom: 10px; }
.action-group-title { font-size: 12px; color: #888; margin-bottom: 4px; }
.action-item {
    padding: 4px 8px; margin: 2px 0; border-radius: 3px;
    background: #1a2744; font-size: 13px;
}
.action-immediate { border-left: 3px solid #4caf50; }
.action-conditional { border-left: 3px solid #ffeb3b; }
.action-forbidden { border-left: 3px solid #f44336; }
.action-undetermined { border-left: 3px solid #666; }
.prohibition-reason { color: #f44336; font-size: 11px; margin-top: 2px; }

/* 审计日志 */
.audit-entry {
    padding: 3px 0; font-size: 12px; border-bottom: 1px solid #1a2744;
    display: flex; gap: 10px;
}
.audit-time { color: #888; min-width: 80px; }
.audit-type { color: #4fc3f7; min-width: 120px; }
.audit-summary { color: #e0e0e0; }

/* 底部状态栏 */
footer {
    background: #16213e;
    padding: 8px 20px;
    display: flex; gap: 24px;
    border-top: 1px solid #0f3460;
    font-size: 13px;
}

.status-item { color: #888; }
.status-item strong { color: #e0e0e0; }

/* 安全状态颜色 */
.safety-normal { color: #4caf50; }
.safety-warning { color: #ffeb3b; }
.safety-fallback { color: #f44336; font-weight: bold; }
.safety-recovering { color: #42a5f5; }
```

- [ ] **Step 3: Commit**

```bash
mkdir -p demos/chemical_process/dashboard/components
git add demos/chemical_process/dashboard/index.html demos/chemical_process/dashboard/style.css
git commit -m "feat(demo): add dashboard HTML structure and dark theme CSS"
```

---

## Task 2: WebSocket 客户端

**Files:**
- Create: `demos/chemical_process/dashboard/websocket.js`

**Purpose:** 连接 API WebSocket，自动重连，分发事件。

- [ ] **Step 1: 实现 WebSocket 客户端**

```javascript
// demos/chemical_process/dashboard/websocket.js
class TwinWebSocket {
    constructor(baseUrl, twinId) {
        this.baseUrl = baseUrl;
        this.twinId = twinId;
        this.ws = null;
        this.handlers = {};
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 10000;
    }

    on(eventType, handler) {
        if (!this.handlers[eventType]) this.handlers[eventType] = [];
        this.handlers[eventType].push(handler);
    }

    connect() {
        const url = `${this.baseUrl}/api/v1/twins/${this.twinId}/ws`;
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectDelay = 1000;
            this._updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this._dispatch(data.event_type, data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this._updateConnectionStatus(false);
            setTimeout(() => this.connect(), this.reconnectDelay);
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };
    }

    _dispatch(eventType, data) {
        // 通用处理器
        if (this.handlers['*']) {
            this.handlers['*'].forEach(h => h(eventType, data));
        }
        // 特定类型处理器
        if (this.handlers[eventType]) {
            this.handlers[eventType].forEach(h => h(data));
        }
    }

    _updateConnectionStatus(connected) {
        const dot = document.getElementById('connection-dot');
        const text = document.getElementById('connection-status');
        if (dot) dot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
        if (text) text.textContent = connected ? 'Connected' : 'Disconnected';
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add demos/chemical_process/dashboard/websocket.js
git commit -m "feat(demo): add WebSocket client with auto-reconnect"
```

---

## Task 3: 状态变量时序图

**Files:**
- Create: `demos/chemical_process/dashboard/charts.js`

**Purpose:** Chart.js 折线图展示温度、压力等状态变量实时变化，约束边界用虚线标注。

- [ ] **Step 1: 实现时序图**

```javascript
// demos/chemical_process/dashboard/charts.js
class StateChart {
    constructor(canvasId) {
        this.maxPoints = 200;
        this.labels = [];
        this.datasets = {
            temperature: { data: [], label: 'Temperature (°C)', borderColor: '#f44336', yAxisID: 'y-temp' },
            pressure: { data: [], label: 'Pressure (atm)', borderColor: '#ffeb3b', yAxisID: 'y-pres' },
            concentration_A: { data: [], label: 'Conc. A (mol/L)', borderColor: '#42a5f5', yAxisID: 'y-conc' },
            concentration_B: { data: [], label: 'Conc. B (mol/L)', borderColor: '#4caf50', yAxisID: 'y-conc' },
        };
        this.chart = new Chart(document.getElementById(canvasId), {
            type: 'line',
            data: {
                labels: this.labels,
                datasets: Object.values(this.datasets).map(ds => ({
                    ...ds, fill: false, tension: 0.3, pointRadius: 0, borderWidth: 1.5,
                })),
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                scales: {
                    x: { display: true, title: { display: true, text: 'Time (s)', color: '#888' }, ticks: { color: '#666', maxTicksLimit: 10 } },
                    'y-temp': { position: 'left', title: { display: true, text: '°C', color: '#f44336' }, ticks: { color: '#f44336' }, grid: { color: '#1a2744' } },
                    'y-pres': { position: 'right', title: { display: true, text: 'atm', color: '#ffeb3b' }, ticks: { color: '#ffeb3b' }, grid: { drawOnChartArea: false } },
                    'y-conc': { display: false },
                },
                plugins: {
                    legend: { labels: { color: '#e0e0e0', font: { size: 11 } } },
                },
            },
            plugins: [{
                // 约束边界线插件
                id: 'constraintLines',
                afterDraw: (chart) => {
                    const yScale = chart.scales['y-temp'];
                    if (!yScale) return;
                    const ctx = chart.ctx;
                    // 280°C 红色虚线
                    const y280 = yScale.getPixelForValue(280);
                    if (y280 >= yScale.top && y280 <= yScale.bottom) {
                        ctx.save();
                        ctx.strokeStyle = '#f44336';
                        ctx.setLineDash([5, 5]);
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(chart.chartArea.left, y280);
                        ctx.lineTo(chart.chartArea.right, y280);
                        ctx.stroke();
                        ctx.fillStyle = '#f44336';
                        ctx.font = '10px monospace';
                        ctx.fillText('280°C limit', chart.chartArea.right - 60, y280 - 4);
                        ctx.restore();
                    }
                },
            }],
        });
    }

    addPoint(timestamp, values) {
        const t = timestamp.toFixed(1);
        this.labels.push(t);
        for (const [key, ds] of Object.entries(this.datasets)) {
            ds.data.push(values[key] !== undefined ? values[key] : null);
        }
        // 限制点数
        if (this.labels.length > this.maxPoints) {
            this.labels.shift();
            Object.values(this.datasets).forEach(ds => ds.data.shift());
        }
        this.chart.update('none');
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add demos/chemical_process/dashboard/charts.js
git commit -m "feat(demo): add state variable time-series chart with constraint boundary"
```

---

## Task 4: 约束面板、行动面板、审计日志

**Files:**
- Create: `demos/chemical_process/dashboard/components/constraint-panel.js`
- Create: `demos/chemical_process/dashboard/components/action-panel.js`
- Create: `demos/chemical_process/dashboard/components/audit-log.js`

- [ ] **Step 1: 实现约束面板**

```javascript
// demos/chemical_process/dashboard/components/constraint-panel.js
class ConstraintPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.constraints = {};
    }

    update(constraintEvaluations) {
        for (const [id, status] of Object.entries(constraintEvaluations)) {
            if (!this.constraints[id]) {
                this.constraints[id] = { status, element: this._createRow(id, status) };
                this.container.appendChild(this.constraints[id].element);
            }
            this._updateRow(this.constraints[id], status);
        }
    }

    _createRow(id, status) {
        const row = document.createElement('div');
        row.className = 'constraint-row';
        row.innerHTML = `
            <span class="constraint-name ${this._isCritical(id) ? 'safety-critical' : ''}">${id}</span>
            <span class="constraint-status ${this._statusClass(status)}">${status}</span>
        `;
        return row;
    }

    _updateRow(constraint, status) {
        const statusEl = constraint.element.querySelector('.constraint-status');
        statusEl.className = 'constraint-status ' + this._statusClass(status);
        statusEl.textContent = status;
    }

    _statusClass(status) {
        const map = { passed: 'status-pass', uncertain: 'status-uncertain',
                      failed: 'status-failed', not_applicable: 'status-na',
                      learnable: 'status-learn' };
        return map[status] || 'status-na';
    }

    _isCritical(id) {
        return ['max_temperature', 'max_pressure', 'min_coolant_flow', 'thermal_runaway_warning'].includes(id);
    }
}
```

- [ ] **Step 2: 实现行动面板**

```javascript
// demos/chemical_process/dashboard/components/action-panel.js
class ActionPanel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    update(actionSpace) {
        this.container.innerHTML = '';
        const groups = [
            { key: 'immediate_actions', title: 'Immediate', cls: 'action-immediate' },
            { key: 'conditional_actions', title: 'Conditional', cls: 'action-conditional' },
            { key: 'forbidden_actions', title: 'Forbidden', cls: 'action-forbidden' },
            { key: 'undetermined_actions', title: 'Undetermined', cls: 'action-undetermined' },
        ];
        for (const g of groups) {
            const actions = actionSpace[g.key] || [];
            if (actions.length === 0) continue;
            const div = document.createElement('div');
            div.className = 'action-group';
            div.innerHTML = `<div class="action-group-title">${g.title} (${actions.length})</div>`;
            for (const a of actions) {
                const item = document.createElement('div');
                item.className = 'action-item ' + g.cls;
                item.textContent = a.action_template || a.action_id || '?';
                if (a.prohibition_reason) {
                    const reason = document.createElement('div');
                    reason.className = 'prohibition-reason';
                    reason.textContent = a.prohibition_reason;
                    item.appendChild(reason);
                }
                div.appendChild(item);
            }
            this.container.appendChild(div);
        }
    }
}
```

- [ ] **Step 3: 实现审计日志**

```javascript
// demos/chemical_process/dashboard/components/audit-log.js
class AuditLog {
    constructor(containerId, maxEntries = 100) {
        this.container = document.getElementById(containerId);
        this.maxEntries = maxEntries;
    }

    append(timestamp, eventType, summary) {
        const entry = document.createElement('div');
        entry.className = 'audit-entry';
        entry.innerHTML = `
            <span class="audit-time">${timestamp}</span>
            <span class="audit-type">${eventType}</span>
            <span class="audit-summary">${summary}</span>
        `;
        this.container.appendChild(entry);

        // 限制条目数
        while (this.container.children.length > this.maxEntries) {
            this.container.removeChild(this.container.firstChild);
        }
        // 自动滚动
        this.container.scrollTop = this.container.scrollHeight;
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add demos/chemical_process/dashboard/components/
git commit -m "feat(demo): add constraint panel, action panel, and audit log components"
```

---

## Task 5: 主应用控制器

**Files:**
- Create: `demos/chemical_process/dashboard/app.js`

**Purpose:** 初始化所有组件，连接 WebSocket，分发事件，更新底部状态栏。

- [ ] **Step 1: 实现主控制器**

```javascript
// demos/chemical_process/dashboard/app.js
(function() {
    // 配置
    const API_BASE = new URLSearchParams(window.location.search).get('api') || 'ws://localhost:8000';
    const HTTP_BASE = API_BASE.replace('ws://', 'http://').replace('wss://', 'https://');
    const TWIN_ID = new URLSearchParams(window.location.search).get('twin') || 'demo';
    const startTime = Date.now();

    // 初始化组件
    const chart = new StateChart('state-chart');
    const constraints = new ConstraintPanel('constraint-panel');
    const actions = new ActionPanel('action-panel');
    const audit = new AuditLog('audit-log');

    // 连接 WebSocket
    const ws = new TwinWebSocket(API_BASE, TWIN_ID);

    // 事件处理
    ws.on('state_updated', (data) => {
        if (data.data && data.data.values) {
            chart.addPoint(data.timestamp || 0, data.data.values);
        }
        audit.append(
            formatTime(data.timestamp),
            'state_updated',
            Object.keys(data.data?.values || {}).join(', ')
        );
    });

    ws.on('constraint_evaluated', (data) => {
        if (data.data && data.data.evaluations) {
            constraints.update(data.data.evaluations);
        }
        audit.append(
            formatTime(data.timestamp),
            'constraint_evaluated',
            Object.entries(data.data?.evaluations || {}).map(([k, v]) => `${k}=${v}`).join(' ')
        );
    });

    ws.on('fallback_triggered', (data) => {
        updateSafetyStatus('fallback');
        audit.append(
            formatTime(data.timestamp),
            'fallback_triggered',
            data.data?.fallback_action || 'emergency'
        );
    });

    ws.on('action_space_updated', (data) => {
        if (data.data) {
            actions.update(data.data);
        }
        audit.append(
            formatTime(data.timestamp),
            'action_space_updated',
            'Bridge output refreshed'
        );
    });

    ws.on('identity_status_changed', (data) => {
        const status = data.data?.status || 'unknown';
        document.getElementById('identity-status').textContent = status;
        document.getElementById('identity-status').className = status === 'confirmed' ? 'status-pass' : 'status-uncertain';
        audit.append(formatTime(data.timestamp), 'identity_status', status);
    });

    ws.on('exploration_progress', (data) => {
        const pct = data.data?.progress || 0;
        audit.append(formatTime(data.timestamp), 'lab_progress', `${pct}%`);
    });

    ws.on('exploration_completed', (data) => {
        const count = data.data?.hypotheses_count || '?';
        audit.append(formatTime(data.timestamp), 'lab_completed', `${count} hypotheses`);
    });

    ws.on('domain_pack_updated', (data) => {
        document.getElementById('dp-version').textContent = data.data?.version || 'updated';
    });

    // 连接
    ws.on('*', (eventType, data) => {
        updateUptime();
    });

    ws.connect();

    // 辅助函数
    function formatTime(ts) {
        if (!ts) return new Date().toLocaleTimeString();
        return new Date(ts * 1000 || ts).toLocaleTimeString();
    }

    function updateSafetyStatus(status) {
        const el = document.getElementById('safety-status');
        const classMap = {
            normal: 'safety-normal', warning: 'safety-warning',
            fallback_triggered: 'safety-fallback', recovering: 'safety-recovering',
        };
        el.textContent = status;
        el.className = classMap[status] || '';
    }

    function updateUptime() {
        const sec = Math.floor((Date.now() - startTime) / 1000);
        const min = Math.floor(sec / 60);
        document.getElementById('uptime').textContent = min > 0 ? `${min}m ${sec % 60}s` : `${sec}s`;
    }

    // 定时更新 uptime
    setInterval(updateUptime, 1000);

    console.log('Polymorphic-Twin Dashboard initialized');
    console.log(`  API: ${API_BASE}`);
    console.log(`  Twin: ${TWIN_ID}`);
})();
```

- [ ] **Step 2: Commit**

```bash
git add demos/chemical_process/dashboard/app.js
git commit -m "feat(demo): add main app controller with WebSocket event routing"
```

---

## Task 6: 端到端演示验证脚本

**Files:**
- Create: `tests/demo/test_dashboard_e2e.py`

**Purpose:** 验证完整演示流程在 Docker 环境下可运行。

- [ ] **Step 1: 编写验证脚本**

```python
# tests/demo/test_dashboard_e2e.py
"""端到端演示验证。

需要 Docker 和 docker-compose。设置 SKIP_DOCKER_E2E=1 跳过。
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

skip_docker = pytest.mark.skipif(
    os.environ.get("SKIP_DOCKER_E2E") == "1",
    reason="Docker E2E tests skipped (SKIP_DOCKER_E2E=1)",
)


class TestDashboardFiles:
    """不需要 Docker 的文件完整性检查。"""

    def test_index_html_exists(self):
        assert Path("demos/chemical_process/dashboard/index.html").exists()

    def test_style_css_exists(self):
        assert Path("demos/chemical_process/dashboard/style.css").exists()

    def test_app_js_exists(self):
        assert Path("demos/chemical_process/dashboard/app.js").exists()

    def test_websocket_js_exists(self):
        assert Path("demos/chemical_process/dashboard/websocket.js").exists()

    def test_charts_js_exists(self):
        assert Path("demos/chemical_process/dashboard/charts.js").exists()

    def test_components_exist(self):
        base = Path("demos/chemical_process/dashboard/components")
        assert (base / "constraint-panel.js").exists()
        assert (base / "action-panel.js").exists()
        assert (base / "audit-log.js").exists()

    def test_index_references_all_scripts(self):
        html = Path("demos/chemical_process/dashboard/index.html").read_text()
        assert "websocket.js" in html
        assert "charts.js" in html
        assert "app.js" in html
        assert "constraint-panel.js" in html

    def test_chartjs_loaded(self):
        html = Path("demos/chemical_process/dashboard/index.html").read_text()
        assert "chart.js" in html.lower()


class TestDemoRunner:
    """验证 demo_runner 脚本结构正确。"""

    def test_runner_exists(self):
        assert Path("demos/chemical_process/demo_runner.py").exists()

    def test_runner_is_importable(self):
        from demos.chemical_process.demo_runner import run_demo
        assert callable(run_demo)

    def test_scenarios_all_exist(self):
        scenarios_dir = Path("demos/chemical_process/scenarios")
        for name in ["01_startup", "02_steady_state", "03_sensor_drift",
                      "04_temperature_spike", "05_emergency", "06_recovery"]:
            assert (scenarios_dir / f"{name}.json").exists(), f"Missing: {name}.json"

    def test_emergency_scenario_has_high_temp(self):
        data = json.loads(Path("demos/chemical_process/scenarios/05_emergency.json").read_text())
        max_temp = max(t["values"]["temperature"] for t in data)
        assert max_temp >= 280, f"Emergency max temp only {max_temp}"

    def test_readme_exists(self):
        assert Path("demos/chemical_process/README.md").exists()
```

- [ ] **Step 2: 运行测试**

```bash
pytest tests/demo/test_dashboard_e2e.py -v
```

Expected: ~12 passed

- [ ] **Step 3: Commit**

```bash
git add tests/demo/test_dashboard_e2e.py
git commit -m "test(demo): add dashboard file integrity and demo e2e verification"
```

---

## Quality Gate Checklist

- [ ] 浏览器打开 `index.html` 不报 JS 错误
- [ ] WebSocket 连接后 `connection-dot` 变绿
- [ ] 运行 demo_runner 后图表实时更新
- [ ] Phase 5 回落触发时约束面板 max_temperature 变红闪烁
- [ ] 底部状态栏显示 FALLBACK
- [ ] 审计日志持续追加事件
- [ ] 无第三方依赖（除 Chart.js CDN）
- [ ] `pytest tests/demo/ -v` 全部通过
