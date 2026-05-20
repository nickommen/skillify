"""Tests for find_session.py."""

import os

from scripts.find_session import (
    find_by_uuid,
    find_recent,
    resolve,
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

    def test_ignores_non_jsonl_files(self, tmp_path, monkeypatch):
        slug = "-home-user-proj"
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


class TestResolve:
    def test_empty_args_returns_path(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        session = project_dir / "session.jsonl"
        session.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("", project_dir="/home/user/myproject")
        assert result == {"path": str(session)}

    def test_this_returns_path(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        session = project_dir / "session.jsonl"
        session.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("this", project_dir="/home/user/myproject")
        assert result == {"path": str(session)}

    def test_current_returns_path(self, tmp_path, monkeypatch):
        slug = "-home-user-myproject"
        project_dir = tmp_path / "projects" / slug
        project_dir.mkdir(parents=True)
        session = project_dir / "session.jsonl"
        session.write_text("{}")

        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("current", project_dir="/home/user/myproject")
        assert result == {"path": str(session)}

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

    def test_this_no_session_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("this", project_dir="/nonexistent/project")
        assert "error" in result
        assert "/skillify" in result["error"]

    def test_this_no_project_dir_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("this")
        assert "error" in result

    def test_unrecognized_argument_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("some-random-text")
        assert "error" in result
        assert "Unrecognized argument" in result["error"]

    def test_empty_no_project_dir_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("scripts.find_session.CLAUDE_PROJECTS_DIR", tmp_path / "projects")
        result = resolve("")
        assert "error" in result
