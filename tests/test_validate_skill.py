"""Tests for validate_skill.py."""

import contextlib
import json

import pytest
from scripts.validate_skill import check_frontmatter, check_python_syntax


class TestCheckPythonSyntax:
    def test_valid_python(self, tmp_path):
        script = tmp_path / "good.py"
        script.write_text("x = 1\nprint(x)\n")
        ok, error = check_python_syntax(str(script))
        assert ok is True
        assert error is None

    def test_syntax_error(self, tmp_path):
        script = tmp_path / "bad.py"
        script.write_text("def foo(\n")
        ok, error = check_python_syntax(str(script))
        assert ok is False
        assert "Line" in error

    def test_empty_file(self, tmp_path):
        script = tmp_path / "empty.py"
        script.write_text("")
        ok, _ = check_python_syntax(str(script))
        assert ok is True

    def test_nonexistent_file(self):
        ok, error = check_python_syntax("/nonexistent/file.py")
        assert ok is False
        assert error is not None

    def test_complex_valid_python(self, tmp_path):
        script = tmp_path / "complex.py"
        script.write_text(
            "import json\nimport os\n\n"
            "def process(data):\n"
            "    return {k: v for k, v in data.items() if v}\n\n"
            "if __name__ == '__main__':\n"
            "    print(process({'a': 1, 'b': 0}))\n"
        )
        ok, _ = check_python_syntax(str(script))
        assert ok is True


class TestCheckFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test-skill\n"
            "description: A test skill\n"
            "user-invocable: true\n"
            "---\n"
            "# Test\n"
        )
        ok, _ = check_frontmatter(str(skill_md))
        assert ok is True

    def test_missing_name(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "description: A test skill\n"
            "user-invocable: true\n"
            "---\n"
        )
        ok, error = check_frontmatter(str(skill_md))
        assert ok is False
        assert "name" in error

    def test_missing_description(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test-skill\n"
            "user-invocable: true\n"
            "---\n"
        )
        ok, error = check_frontmatter(str(skill_md))
        assert ok is False
        assert "description" in error

    def test_missing_user_invocable(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test-skill\n"
            "description: A test skill\n"
            "---\n"
        )
        ok, error = check_frontmatter(str(skill_md))
        assert ok is False
        assert "user-invocable" in error

    def test_no_frontmatter(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Just a heading\nNo frontmatter here.\n")
        ok, error = check_frontmatter(str(skill_md))
        assert ok is False
        assert "No YAML frontmatter" in error

    def test_file_not_found(self):
        ok, error = check_frontmatter("/nonexistent/SKILL.md")
        assert ok is False
        assert "not found" in error

    def test_multiple_missing_keys(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test\n---\n")
        ok, error = check_frontmatter(str(skill_md))
        assert ok is False
        assert "description" in error
        assert "user-invocable" in error

    def test_multiline_description(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test-skill\n"
            "description: >\n"
            "  A multi-line\n"
            "  description\n"
            "user-invocable: true\n"
            "---\n"
        )
        ok, _ = check_frontmatter(str(skill_md))
        assert ok is True


class TestMainIntegration:
    def _run_main(self, skill_dir, monkeypatch, capsys):
        """Run validate_skill main() and return parsed JSON output."""
        from scripts.validate_skill import main
        monkeypatch.setattr("sys.argv", ["validate_skill.py", str(skill_dir)])
        with contextlib.suppress(SystemExit):
            main()
        return json.loads(capsys.readouterr().out)

    def test_valid_skill(self, tmp_path, monkeypatch, capsys):
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('hello')\n")
        (tmp_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test skill\nuser-invocable: true\n---\n# Test\n"
        )

        output = self._run_main(tmp_path, monkeypatch, capsys)
        assert output["valid"] is True
        assert output["errors"] == []
        assert len(output["checks"]) == 2

    def test_invalid_python(self, tmp_path, monkeypatch, capsys):
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "bad.py").write_text("def broken(\n")
        (tmp_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test\nuser-invocable: true\n---\n"
        )

        output = self._run_main(tmp_path, monkeypatch, capsys)
        assert output["valid"] is False
        assert any("bad.py" in e for e in output["errors"])

    def test_missing_skill_md(self, tmp_path, monkeypatch, capsys):
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("x = 1\n")

        output = self._run_main(tmp_path, monkeypatch, capsys)
        assert output["valid"] is False
        assert any("SKILL.md" in e for e in output["errors"])

    def test_no_scripts_dir(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test\nuser-invocable: true\n---\n"
        )

        output = self._run_main(tmp_path, monkeypatch, capsys)
        assert output["valid"] is True
        assert len(output["checks"]) == 1

    def test_multiple_scripts(self, tmp_path, monkeypatch, capsys):
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print(1)\n")
        (scripts_dir / "validators.py").write_text("print(2)\n")
        (scripts_dir / "helpers.py").write_text("print(3)\n")
        (tmp_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test\nuser-invocable: true\n---\n"
        )

        output = self._run_main(tmp_path, monkeypatch, capsys)
        assert output["valid"] is True
        python_checks = [c for c in output["checks"] if c["check"] == "python_syntax"]
        assert len(python_checks) == 3

    def test_exits_on_missing_args(self, monkeypatch):
        from scripts.validate_skill import main
        monkeypatch.setattr("sys.argv", ["validate_skill.py"])
        with pytest.raises(SystemExit, match="1"):
            main()

    def test_exits_on_nonexistent_dir(self, monkeypatch):
        from scripts.validate_skill import main
        monkeypatch.setattr("sys.argv", ["validate_skill.py", "/nonexistent/dir/xyz"])
        with pytest.raises(SystemExit, match="1"):
            main()
