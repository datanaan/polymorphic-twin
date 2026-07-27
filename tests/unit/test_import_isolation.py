"""Test that the import isolation scanner correctly detects violations."""
import tempfile
from pathlib import Path

from scripts.check_import_isolation import check_isolation, get_imports


class TestGetImports:
    def test_extracts_import(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import polytwin.core.engine\nfrom polytwin.tom import types\n")
            f.flush()
            imports = get_imports(Path(f.name))
            assert "polytwin.core.engine" in imports
            assert "polytwin.tom" in imports

class TestCheckIsolation:
    def test_no_violations_with_clean_code(self, tmp_path):
        lab_dir = tmp_path / "polytwin" / "lab"
        lab_dir.mkdir(parents=True)
        (lab_dir / "__init__.py").write_text("from polytwin.tom.types import CallerIdentity\n")
        violations = check_isolation(tmp_path)
        assert violations == []

    def test_detects_lab_importing_core_engine(self, tmp_path):
        lab_dir = tmp_path / "polytwin" / "lab"
        lab_dir.mkdir(parents=True)
        (lab_dir / "__init__.py").write_text("from polytwin.core.engine import ConstraintEngine\n")
        violations = check_isolation(tmp_path)
        assert len(violations) == 1
        assert "polytwin.core.engine" in violations[0]

    def test_detects_bridge_importing_lab(self, tmp_path):
        bridge_dir = tmp_path / "polytwin" / "bridge"
        bridge_dir.mkdir(parents=True)
        (bridge_dir / "__init__.py").write_text("import polytwin.lab.explorer\n")
        violations = check_isolation(tmp_path)
        assert len(violations) == 1
        assert "polytwin.lab.explorer" in violations[0]
