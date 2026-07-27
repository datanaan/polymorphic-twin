"""Verify that the M11b demo dashboard static assets exist and are valid."""

import subprocess
from pathlib import Path

DEMO_DIR = Path("demo")


class TestDashboardAssets:
    """All static assets for the CSTR demo dashboard must be present and well-formed."""

    # ── Existence checks ─────────────────────────────────────────

    def test_index_html_exists(self):
        assert (DEMO_DIR / "index.html").exists(), "demo/index.html is missing"

    def test_css_exists(self):
        assert (DEMO_DIR / "style.css").exists(), "demo/style.css is missing"

    def test_js_files_exist(self):
        for filename in ("app.js", "websocket.js", "components.js"):
            path = DEMO_DIR / filename
            assert path.exists(), f"demo/{filename} is missing"

    # ── HTML validity ────────────────────────────────────────────

    def test_index_html_valid_doctype(self):
        content = (DEMO_DIR / "index.html").read_text()
        assert "<!DOCTYPE html>" in content, "Missing DOCTYPE declaration"

    def test_index_html_has_title(self):
        content = (DEMO_DIR / "index.html").read_text()
        assert "<title>" in content, "Missing <title> element"
        assert "Polymorphic-Twin" in content, "Missing Polymorphic-Twin in title or body"

    def test_index_html_includes_chart_js(self):
        content = (DEMO_DIR / "index.html").read_text()
        assert "chart.js" in content.lower(), "Chart.js CDN reference missing"

    def test_index_html_has_canvas(self):
        content = (DEMO_DIR / "index.html").read_text()
        assert "<canvas" in content, "Missing <canvas> element for Chart.js"

    def test_index_html_loads_js_in_order(self):
        content = (DEMO_DIR / "index.html").read_text()
        ws_pos = content.index("websocket.js")
        comp_pos = content.index("components.js")
        app_pos = content.index("app.js")
        assert ws_pos < comp_pos < app_pos, (
            "JS files must load in order: websocket.js, components.js, app.js"
        )

    # ── CSS validity ─────────────────────────────────────────────

    def test_css_has_required_selectors(self):
        content = (DEMO_DIR / "style.css").read_text()
        required = [
            "#status-bar",
            ".panel",
            ".state-item",
            ".constraint",
            ".action",
            ".audit-entry",
            "#temp-chart",
        ]
        for selector in required:
            assert selector in content, f"Missing CSS selector: {selector}"

    def test_css_has_responsive_media_query(self):
        content = (DEMO_DIR / "style.css").read_text()
        assert "@media" in content, "Missing responsive media query"

    def test_css_has_css_variables(self):
        content = (DEMO_DIR / "style.css").read_text()
        assert ":root" in content, "Missing CSS custom properties (:root)"

    # ── JS syntax checks (requires Node.js) ──────────────────────

    def test_app_js_syntax_valid(self):
        result = subprocess.run(
            ["node", "--check", str(DEMO_DIR / "app.js")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in app.js: {result.stderr}"

    def test_websocket_js_syntax_valid(self):
        result = subprocess.run(
            ["node", "--check", str(DEMO_DIR / "websocket.js")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in websocket.js: {result.stderr}"

    def test_components_js_syntax_valid(self):
        result = subprocess.run(
            ["node", "--check", str(DEMO_DIR / "components.js")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in components.js: {result.stderr}"

    # ── Content checks ───────────────────────────────────────────

    def test_websocket_client_has_reconnection(self):
        content = (DEMO_DIR / "websocket.js").read_text()
        assert "WebSocket" in content, "Missing WebSocket reference"
        assert "reconnect" in content.lower(), "Missing reconnection logic"

    def test_app_js_has_chart_initialization(self):
        content = (DEMO_DIR / "app.js").read_text()
        assert "Chart" in content, "Missing Chart.js initialization"
        assert "chart" in content, "Missing chart variable"

    def test_app_js_handles_message_types(self):
        content = (DEMO_DIR / "app.js").read_text()
        for msg_type in ("tick", "validation", "action_space", "audit"):
            assert msg_type in content, f"Missing handler for message type: {msg_type}"

    def test_components_js_exports_render_functions(self):
        content = (DEMO_DIR / "components.js").read_text()
        for func in ("renderState", "renderConstraints", "renderActions", "renderAudit"):
            assert func in content, f"Missing component function: {func}"

    def test_app_js_uses_components(self):
        """Verify app.js delegates rendering to the Components module."""
        app_content = (DEMO_DIR / "app.js").read_text()
        assert "Components.renderState" in app_content, "app.js should call Components.renderState"
        assert "Components.renderConstraints" in app_content, "app.js should call Components.renderConstraints"
        assert "Components.renderActions" in app_content, "app.js should call Components.renderActions"
        assert "Components.renderAudit" in app_content, "app.js should call Components.renderAudit"
