"""Tests for find_session.py."""

import json
import os

from scripts.find_session import (
    find_by_pid,
    find_by_uuid,
    get_ancestor_pids,
    resolve,
)


class TestGetAncestorPids:
    def test_yields_current_pid(self):
        pids = list(get_ancestor_pids())
        assert pids[0] == os.getpid()

    def test_yields_at_least_two_pids(self):
        pids = list(get_ancestor_pids())
        assert len(pids) >= 2

    def test_does_not_include_pid_1(self):
        pids = list(get_ancestor_pids())
        assert 1 not in pids


class TestFindByPid:
    def _setup_session(self, tmp_path, pid, session_id, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        (sessions_dir / f"{pid}.json").write_text(
            json.dumps({"pid": pid, "sessionId": session_id})
        )
        monkeypatch.setattr("scripts.find_session.CLAUDE_SESSIONS_DIR", sessions_dir)
        return sessions_dir

    def test_finds_session_via_pid(self, tmp_path, monkeypatch):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self._setup_session(tmp_path, 1234, uuid, monkeypatch)

        project_dir = tmp_path / "projects" / "some-project"
        project_dir.mkdir(parents=True)
        jsonl = project_dir / f"{uuid}.jsonl"
        jsonl.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([9999, 1234]))

        assert find_by_pid() == str(jsonl)

    def test_skips_non_matching_pids(self, tmp_path, monkeypatch):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self._setup_session(tmp_path, 3000, uuid, monkeypatch)

        project_dir = tmp_path / "projects" / "proj"
        project_dir.mkdir(parents=True)
        jsonl = project_dir / f"{uuid}.jsonl"
        jsonl.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([1000, 2000, 3000]))

        assert find_by_pid() == str(jsonl)

    def test_returns_none_when_no_sessions_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_SESSIONS_DIR", tmp_path / "nonexistent")
        assert find_by_pid() is None

    def test_returns_none_when_sessions_dir_empty(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setattr("scripts.find_session.CLAUDE_SESSIONS_DIR", sessions_dir)
        assert find_by_pid() is None

    def test_returns_none_when_no_pid_matches(self, tmp_path, monkeypatch):
        self._setup_session(tmp_path, 5555, "some-uuid", monkeypatch)
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([1111, 2222]))
        assert find_by_pid() is None

    def test_returns_none_on_corrupt_session_file(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "1234.json").write_text("not json")
        monkeypatch.setattr("scripts.find_session.CLAUDE_SESSIONS_DIR", sessions_dir)
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([1234]))
        assert find_by_pid() is None

    def test_returns_none_on_missing_session_id_key(self, tmp_path, monkeypatch):
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        (sessions_dir / "1234.json").write_text(json.dumps({"pid": 1234}))
        monkeypatch.setattr("scripts.find_session.CLAUDE_SESSIONS_DIR", sessions_dir)
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([1234]))
        assert find_by_pid() is None

    def test_returns_none_when_jsonl_not_found(self, tmp_path, monkeypatch):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        self._setup_session(tmp_path, 1234, uuid, monkeypatch)

        (tmp_path / "projects").mkdir()
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        monkeypatch.setattr("scripts.find_session.get_ancestor_pids", lambda: iter([1234]))

        assert find_by_pid() is None


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


class TestResolve:
    def test_empty_args_uses_pid_detection(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.find_session.find_by_pid",
            lambda: "/path/to/session.jsonl",
        )
        assert resolve("") == {"path": "/path/to/session.jsonl"}

    def test_this_uses_pid_detection(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.find_session.find_by_pid",
            lambda: "/path/to/session.jsonl",
        )
        assert resolve("this") == {"path": "/path/to/session.jsonl"}

    def test_current_uses_pid_detection(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.find_session.find_by_pid",
            lambda: "/path/to/session.jsonl",
        )
        assert resolve("current") == {"path": "/path/to/session.jsonl"}

    def test_this_conversation_uses_pid_detection(self, monkeypatch):
        monkeypatch.setattr(
            "scripts.find_session.find_by_pid",
            lambda: "/path/to/session.jsonl",
        )
        assert resolve("this conversation") == {"path": "/path/to/session.jsonl"}

    def test_pid_detection_failure_returns_error(self, monkeypatch):
        monkeypatch.setattr("scripts.find_session.find_by_pid", lambda: None)
        result = resolve("")
        assert "error" in result
        assert "/skillify <uuid>" in result["error"]

    def test_uuid_returns_path(self, tmp_path, monkeypatch):
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        project_dir = tmp_path / "projects" / "some-project"
        project_dir.mkdir(parents=True)
        session = project_dir / f"{uuid}.jsonl"
        session.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve(uuid)
        assert result == {"path": str(session)}

    def test_uuid_not_found_returns_error(self, tmp_path, monkeypatch):
        (tmp_path / "projects").mkdir(parents=True)
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")

        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        result = resolve(uuid)
        assert "error" in result
        assert uuid in result["error"]

    def test_unrecognized_argument_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("some-random-text")
        assert "error" in result
        assert "Unrecognized argument" in result["error"]
