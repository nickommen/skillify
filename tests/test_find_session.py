"""Tests for find_session.py."""

import json
import os

from scripts.find_session import (
    find_by_name,
    find_by_uuid,
    find_parent,
    find_recent,
    get_first_user_message,
    list_sessions,
)


class TestFindRecent:
    def test_finds_most_recent_jsonl(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
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
        slug = "-home-user-emptyproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/home/user/emptyproject") is None

    def test_converts_path_to_slug(self, tmp_path, monkeypatch):
        slug = "-home-user-project"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        f = project_dir / "abc.jsonl"
        f.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_recent("/home/user/project")
        assert result is not None

    def test_exclude_session_skips_most_recent(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)

        old = project_dir / "source-session.jsonl"
        old.write_text("{}")
        fork = project_dir / "fork-session.jsonl"
        fork.write_text("{}")
        os.utime(old, (1000, 1000))
        os.utime(fork, (2000, 2000))

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_recent("/home/user/myproject", exclude_session="fork-session")
        assert result == str(old)

    def test_exclude_session_returns_none_if_only_match(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)

        only = project_dir / "only-session.jsonl"
        only.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/home/user/myproject", exclude_session="only-session") is None

    def test_ignores_non_jsonl_files(self, tmp_path, monkeypatch):
        slug = "-home-user-proj"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        (project_dir / "notes.txt").write_text("not a jsonl")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_recent("/home/user/proj") is None


class TestFindParent:
    def _write_history(self, history_file, entries):
        with open(history_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_finds_parent_session(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "parent-id", "timestamp": 1700000000000, "display": "Parent"},
            {"sessionId": "fork-id", "timestamp": 1700001000000, "display": "Fork"},
        ])
        project_dir = tmp_path / "projects" / "some-project"
        project_dir.mkdir(parents=True)
        (project_dir / "parent-id.jsonl").write_text("{}")
        (project_dir / "fork-id.jsonl").write_text("{}")

        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_parent("fork-id")
        assert result.endswith("parent-id.jsonl")

    def test_skips_fork_session(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "fork-id", "timestamp": 1700001000000, "display": "Fork"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_parent("fork-id") is None

    def test_returns_none_for_missing_history(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", tmp_path / "nonexistent.jsonl")
        assert find_parent("fork-id") is None

    def test_skips_sessions_without_jsonl(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "no-file", "timestamp": 1700001000000, "display": "No file"},
            {"sessionId": "has-file", "timestamp": 1700000000000, "display": "Has file"},
        ])
        project_dir = tmp_path / "projects" / "some-project"
        project_dir.mkdir(parents=True)
        (project_dir / "has-file.jsonl").write_text("{}")

        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_parent("fork-id")
        assert result.endswith("has-file.jsonl")


class TestGetFirstUserMessage:
    def _write_session(self, path, entries):
        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_extracts_first_user_message(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-1.jsonl", [
            {"type": "system", "content": "system msg"},
            {"type": "user", "message": {"role": "human", "content": "Hello world"}},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert get_first_user_message("sess-1") == "Hello world"

    def test_skips_xml_tagged_messages(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-2.jsonl", [
            {"type": "user", "message": {"role": "human",
                "content": "<ide_opened_file>foo</ide_opened_file>"}},
            {"type": "user", "message": {"role": "human", "content": "Real question here"}},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert get_first_user_message("sess-2") == "Real question here"

    def test_returns_none_for_missing_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert get_first_user_message("nonexistent") is None

    def test_truncates_long_messages(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-3.jsonl", [
            {"type": "user", "message": {"role": "human", "content": "x" * 200}},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert len(get_first_user_message("sess-3")) == 120

    def test_handles_list_content(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-4.jsonl", [
            {"type": "user", "message": {"role": "human", "content": [
                {"type": "text", "text": "Part one"},
                {"type": "text", "text": "part two"},
            ]}},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert get_first_user_message("sess-4") == "Part one part two"


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


class TestFindByName:
    def _write_session(self, path, entries):
        with open(path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_finds_by_custom_title(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-1.jsonl", [
            {"type": "user", "message": {"role": "human", "content": "hello"}},
            {"type": "custom-title", "customTitle": "sprint-status-skill"},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_by_name("sprint-status-skill")
        assert result.endswith("sess-1.jsonl")

    def test_finds_by_agent_name(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-2.jsonl", [
            {"type": "agent-name", "agentName": "weekly-rollup"},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = find_by_name("weekly-rollup")
        assert result.endswith("sess-2.jsonl")

    def test_case_insensitive(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-3.jsonl", [
            {"type": "custom-title", "customTitle": "Sprint-Status-Skill"},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_by_name("sprint-status-skill") is not None

    def test_returns_none_for_no_match(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        self._write_session(project_dir / "sess-4.jsonl", [
            {"type": "custom-title", "customTitle": "other-skill"},
        ])
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_by_name("sprint-status-skill") is None

    def test_returns_none_for_empty_projects_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "nonexistent")
        assert find_by_name("anything") is None

    def test_skips_non_jsonl_files(self, tmp_path, monkeypatch):
        project_dir = tmp_path / "projects" / "test"
        project_dir.mkdir(parents=True)
        (project_dir / "notes.txt").write_text('{"type":"custom-title","customTitle":"match"}')
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        assert find_by_name("match") is None


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

    def test_excludes_session(self, tmp_path, monkeypatch):
        history = tmp_path / "history.jsonl"
        self._write_history(history, [
            {"sessionId": "aaa", "timestamp": 1700000000000, "display": "First"},
            {"sessionId": "fork", "timestamp": 1700001000000, "display": "Fork"},
            {"sessionId": "bbb", "timestamp": 1700002000000, "display": "Second"},
        ])
        monkeypatch.setattr("scripts.find_session.HISTORY_FILE", history)

        sessions = list_sessions(exclude_session="fork")
        assert len(sessions) == 2
        ids = [s["session_id"] for s in sessions]
        assert "fork" not in ids

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
