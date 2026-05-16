"""Tests for gather_context.py."""

import json
import os
import subprocess

import pytest
from scripts.gather_context import main, run_git


class TestRunGit:
    def test_returns_output_for_valid_repo(self, tmp_path):
        subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t"},
        )
        result = run_git(str(tmp_path), "log", "--oneline", "-1")
        assert result is not None
        assert "init" in result

    def test_returns_none_for_non_repo(self, tmp_path):
        result = run_git(str(tmp_path), "log", "--oneline", "-1")
        assert result is None

    def test_returns_none_for_nonexistent_path(self):
        result = run_git("/nonexistent/path/abc123", "status")
        assert result is None


class TestMainIntegration:
    def test_outputs_json_for_git_repo(self, tmp_path, monkeypatch, capsys):
        subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "test commit"],
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t"},
        )

        monkeypatch.setattr("sys.argv", ["gather_context.py", str(tmp_path)])
        main()
        output = json.loads(capsys.readouterr().out)

        assert output["is_git_repo"] is True
        assert len(output["git_log"]) >= 1
        assert "test commit" in output["git_log"][0]
        assert isinstance(output["project_files"], list)

    def test_outputs_json_for_non_git_dir(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["gather_context.py", str(tmp_path)])
        main()
        output = json.loads(capsys.readouterr().out)

        assert output["is_git_repo"] is False
        assert output["git_log"] == []

    def test_detects_project_files(self, tmp_path, monkeypatch, capsys):
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "Makefile").write_text("all:")

        monkeypatch.setattr("sys.argv", ["gather_context.py", str(tmp_path)])
        main()
        output = json.loads(capsys.readouterr().out)

        assert "pyproject.toml" in output["project_files"]
        assert "Makefile" in output["project_files"]

    def test_no_project_files_detected(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["gather_context.py", str(tmp_path)])
        main()
        output = json.loads(capsys.readouterr().out)

        assert output["project_files"] == []

    def test_exits_on_missing_args(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["gather_context.py"])
        with pytest.raises(SystemExit, match="1"):
            main()

    def test_exits_on_nonexistent_dir(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["gather_context.py", "/nonexistent/dir/xyz"])
        with pytest.raises(SystemExit, match="1"):
            main()

    def test_git_diff_stat_included(self, tmp_path, monkeypatch, capsys):
        subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
        env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
            capture_output=True, env=env,
        )
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "-C", str(tmp_path), "add", "file.txt"], capture_output=True)

        monkeypatch.setattr("sys.argv", ["gather_context.py", str(tmp_path)])
        main()
        output = json.loads(capsys.readouterr().out)

        assert output["is_git_repo"] is True
        assert "git_diff_stat" in output
