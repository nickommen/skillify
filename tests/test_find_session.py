"""Tests for find_session.py."""

import json
import os

from scripts.find_session import find_by_uuid, find_recent, list_sessions


class TestFindRecent:
    def test_finds_most_recent_jsonl(self, tmp_path, monkeypatch):
        slug = "home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)

        old = project_dir / "old-session.jsonl"
        old.write_text("{}")
        new = project_dir / "new-session.jsonl"
        new.write_text("{}")
        # Ensure new has a later mtime
        os.utime(old, (1000, 1000))
        os.utime(new, (2000, 2000))

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_recent("/home/user/myproject")
        assert result == str(new)

    def test_returns_none_for_missing_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/nonexistent/project") is None

    def test_returns_none_for_empty_project_dir(self, tmp_path, monkeypatch):
        slug = "home-user-emptyproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/home/user/emptyproject") is None

    def test_strips_leading_slash_from_path(self, tmp_path, monkeypatch):
        slug = "home-user-project"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        f = project_dir / "abc.jsonl"
        f.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_recent("/home/user/project")
        assert result is not None

    def test_ignores_non_jsonl_files(self, tmp_path, monkeypatch):
        slug = "home-user-proj"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        (project_dir / "notes.txt").write_text("not a jsonl")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/home/user/proj") is None


class TestFindByUuid:
    def test_finds_session_by_uuid(self, tmp_path, monkeypatch):
        session_dir = tmp_path / "projects" / "some-project"
        session_dir.mkdir(parents=True)
        target = session_dir / "abc-123-def.jsonl"
        target.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_by_uuid("abc-123-def")
        assert result == str(target)

    def test_returns_none_for_missing_uuid(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        (tmp_path / "projects").mkdir(parents=True)
        assert find_by_uuid("nonexistent-uuid") is None

    def test_finds_in_nested_directories(self, tmp_path, monkeypatch):
        nested = tmp_path / "projects" / "deep" / "nested"
        nested.mkdir(parents=True)
        target = nested / "my-session.jsonl"
        target.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_by_uuid("my-session")
        assert result == str(target)


class TestListSessions:
    def _write_history(self, history_file, entries):
        with open(history_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_lists_recent_sessions(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "aaa", "timestamp": 1700000000000, "display": "First session"},
            {"sessionId": "bbb", "timestamp": 1700001000000, "display": "Second session"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "bbb"
        assert sessions[1]["session_id"] == "aaa"

    def test_deduplicates_sessions(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "aaa", "timestamp": 1700000000000, "display": "First"},
            {"sessionId": "aaa", "timestamp": 1700001000000, "display": "First again"},
            {"sessionId": "bbb", "timestamp": 1700002000000, "display": "Second"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert len(sessions) == 2
        ids = [s["session_id"] for s in sessions]
        assert ids.count("aaa") == 1

    def test_limits_to_count(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        entries = [
            {"sessionId": f"session-{i}", "timestamp": 1700000000000 + i * 1000, "display": f"S{i}"}
            for i in range(20)
        ]
        self._write_history(history, entries)
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions(count=5)
        assert len(sessions) == 5

    def test_returns_empty_for_missing_history(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", tmp_path / "nonexistent.jsonl")
        assert list_sessions() == []

    def test_skips_entries_without_session_id(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"timestamp": 1700000000000, "display": "No session ID"},
            {"sessionId": "", "timestamp": 1700001000000, "display": "Empty session ID"},
            {"sessionId": "valid", "timestamp": 1700002000000, "display": "Valid"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "valid"

    def test_truncates_display_to_80_chars(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        long_display = "x" * 200
        self._write_history(history, [
            {"sessionId": "aaa", "timestamp": 1700000000000, "display": long_display},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert len(sessions[0]["display"]) == 80

    def test_handles_malformed_json_lines(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        with open(history, "w") as f:
            f.write("not valid json\n")
            entry = {"sessionId": "ok", "timestamp": 1700000000000, "display": "Good"}
            f.write(json.dumps(entry) + "\n")
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "ok"

    def test_formats_timestamp(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "aaa", "timestamp": 1700000000000, "display": "Test"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions()
        assert sessions[0]["timestamp"]
        # Should be in YYYY-MM-DD HH:MM format
        parts = sessions[0]["timestamp"].split(" ")
        assert len(parts) == 2
        assert "-" in parts[0]
        assert ":" in parts[1]
