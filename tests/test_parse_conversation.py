"""Tests for parse_conversation.py."""

import io
import json
import os
import sys
import tempfile

import pytest
from scripts.parse_conversation import (
    _compact_tool_sequence,
    _detect_output_type,
    classify_tool_call,
    detect_written_file_type,
    extract_env_vars,
    extract_jql_patterns,
    extract_text_from_content,
    extract_tool_input,
    is_correction,
    parse_conversation,
    score_correction,
    truncate,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------------------------------------------------------------------------
# truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_none_input(self):
        assert truncate(None, 100) is None

    def test_short_text(self):
        assert truncate("hello", 100) == "hello"

    def test_exact_boundary(self):
        assert truncate("12345", 5) == "12345"

    def test_long_text(self):
        text = "a" * 200
        result = truncate(text, 50)
        assert result.startswith("a" * 50)
        assert "200 chars total" in result

    def test_empty_string(self):
        assert truncate("", 100) == ""


# ---------------------------------------------------------------------------
# extract_text_from_content
# ---------------------------------------------------------------------------


class TestExtractTextFromContent:
    def test_plain_string(self):
        assert extract_text_from_content("hello") == "hello"

    def test_list_of_text_dicts(self):
        content = [
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
        ]
        assert extract_text_from_content(content) == "hello\nworld"

    def test_list_with_mixed_types(self):
        content = [
            {"type": "text", "text": "hello"},
            {"type": "tool_result", "tool_use_id": "123"},
            {"type": "text", "text": "world"},
        ]
        assert extract_text_from_content(content) == "hello\nworld"

    def test_list_of_strings(self):
        assert extract_text_from_content(["a", "b"]) == "a\nb"

    def test_empty_list(self):
        assert extract_text_from_content([]) == ""

    def test_none_input(self):
        assert extract_text_from_content(None) == ""

    def test_integer_input(self):
        assert extract_text_from_content(42) == ""


# ---------------------------------------------------------------------------
# classify_tool_call
# ---------------------------------------------------------------------------


class TestClassifyToolCall:
    def test_jira_search(self):
        assert classify_tool_call("mcp__atlassian__searchJiraIssuesUsingJql", {}) == (
            "data_gathering",
            "jira_api",
        )

    def test_jira_get_issue(self):
        assert classify_tool_call("mcp__atlassian__getJiraIssue", {}) == (
            "data_gathering",
            "jira_api",
        )

    def test_jira_search_rovo(self):
        assert classify_tool_call("mcp__atlassian__search", {}) == (
            "data_gathering",
            "jira_api",
        )

    def test_atlassian_generic(self):
        assert classify_tool_call("mcp__atlassian__createJiraIssue", {}) == (
            "data_gathering",
            "atlassian_api",
        )

    def test_google_workspace(self):
        assert classify_tool_call("mcp__google_workspace__get_doc_content", {}) == (
            "data_gathering",
            "google_workspace",
        )

    def test_bash_gh(self):
        assert classify_tool_call("Bash", {"command": "gh pr list --repo org/repo"}) == (
            "data_gathering",
            "github_cli",
        )

    def test_bash_python(self):
        assert classify_tool_call("Bash", {"command": "python3 scripts/analyze.py"}) == (
            "data_processing",
            "python_execution",
        )

    def test_bash_mkdir(self):
        assert classify_tool_call("Bash", {"command": "mkdir -p /tmp/output"}) == (
            "setup",
            "directory_creation",
        )

    def test_bash_symlink(self):
        assert classify_tool_call("Bash", {"command": "ln -sf /src /dest"}) == (
            "setup",
            "symlink",
        )

    def test_bash_curl(self):
        assert classify_tool_call("Bash", {"command": "curl -s https://api.example.com"}) == (
            "data_gathering",
            "http_request",
        )

    def test_bash_generic(self):
        assert classify_tool_call("Bash", {"command": "ls -la"}) == (
            "data_processing",
            "bash_command",
        )

    def test_write_python(self):
        assert classify_tool_call("Write", {"file_path": "/tmp/script.py"}) == (
            "script_creation",
            "python_script",
        )

    def test_write_skill_md(self):
        assert classify_tool_call("Write", {"file_path": "/path/to/SKILL.md"}) == (
            "skill_creation",
            "skill_definition",
        )

    def test_write_readme(self):
        assert classify_tool_call("Write", {"file_path": "/path/to/README.md"}) == (
            "skill_creation",
            "readme",
        )

    def test_write_other(self):
        assert classify_tool_call("Write", {"file_path": "/tmp/data.csv"}) == (
            "output_generation",
            "file_write",
        )

    def test_edit(self):
        assert classify_tool_call("Edit", {}) == ("refinement", "file_edit")

    def test_agent(self):
        assert classify_tool_call("Agent", {}) == ("ai_delegation", "agent_call")

    def test_read(self):
        assert classify_tool_call("Read", {}) == ("context_gathering", "file_read")

    def test_web_fetch(self):
        assert classify_tool_call("WebFetch", {}) == ("data_gathering", "web_fetch")

    def test_web_search(self):
        assert classify_tool_call("WebSearch", {}) == ("data_gathering", "web_search")

    def test_ask_user(self):
        assert classify_tool_call("AskUserQuestion", {}) == ("user_interaction", "question")

    def test_skill(self):
        assert classify_tool_call("Skill", {}) == ("skill_invocation", "skill_call")

    def test_unknown(self):
        assert classify_tool_call("SomeNewTool", {}) == ("unknown", "SomeNewTool")


# ---------------------------------------------------------------------------
# extract_tool_input
# ---------------------------------------------------------------------------


class TestExtractToolInput:
    def test_bash(self):
        result = extract_tool_input("Bash", {"command": "ls -la", "extra": "ignored"})
        assert result == {"command": "ls -la"}

    def test_write(self):
        result = extract_tool_input("Write", {"file_path": "/tmp/f.py", "content": "x" * 500})
        assert result["file_path"] == "/tmp/f.py"
        assert result["content_length"] == 500
        assert "content_preview" in result

    def test_edit(self):
        result = extract_tool_input(
            "Edit",
            {"file_path": "/tmp/f.py", "old_string": "old", "new_string": "new"},
        )
        assert result["file_path"] == "/tmp/f.py"
        assert "old_string_preview" in result
        assert "new_string_preview" in result

    def test_read(self):
        assert extract_tool_input("Read", {"file_path": "/tmp/f.py"}) == {"file_path": "/tmp/f.py"}

    def test_agent(self):
        result = extract_tool_input(
            "Agent",
            {"prompt": "Do X", "description": "Task", "subagent_type": "Explore"},
        )
        assert result["prompt"] == "Do X"
        assert result["description"] == "Task"
        assert result["subagent_type"] == "Explore"

    def test_agent_no_subagent(self):
        result = extract_tool_input("Agent", {"prompt": "Do X", "description": "Task"})
        assert "subagent_type" not in result

    def test_skill(self):
        assert extract_tool_input("Skill", {"skill": "deploy", "args": "--prod"}) == {
            "skill": "deploy",
            "args": "--prod",
        }

    def test_unknown_tool(self):
        assert extract_tool_input("CustomTool", {"a": 1, "b": 2}) == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# extract_env_vars
# ---------------------------------------------------------------------------


class TestExtractEnvVars:
    def test_os_environ_get(self):
        assert "JIRA_API_TOKEN" in extract_env_vars('os.environ.get("JIRA_API_TOKEN")')

    def test_os_environ_bracket(self):
        assert "GITHUB_TOKEN" in extract_env_vars("os.environ['GITHUB_TOKEN']")

    def test_export(self):
        assert "MY_SECRET" in extract_env_vars("export MY_SECRET=value123")

    def test_shell_variable(self):
        found = extract_env_vars("echo $API_KEY and ${API_SECRET}")
        assert "API_KEY" in found
        assert "API_SECRET" in found

    def test_getenv(self):
        assert "DATABASE_URL" in extract_env_vars('getenv("DATABASE_URL")')

    def test_excludes_builtins(self):
        assert len(extract_env_vars("$HOME $PATH $USER")) == 0

    def test_excludes_short_vars(self):
        assert len(extract_env_vars("$AB")) == 0

    def test_excludes_lowercase(self):
        assert len(extract_env_vars("$lowercase_var")) == 0

    def test_excludes_skill_dir(self):
        assert len(extract_env_vars("$CLAUDE_SKILL_DIR $ARGUMENTS")) == 0

    def test_empty_text(self):
        assert len(extract_env_vars("")) == 0


# ---------------------------------------------------------------------------
# score_correction
# ---------------------------------------------------------------------------


class TestScoreCorrection:
    def test_empty_string(self):
        score, result = score_correction("")
        assert score == 0.0
        assert result is False

    def test_none_text(self):
        score, result = score_correction(None)
        assert score == 0.0
        assert result is False

    # --- False positive exclusions ---

    def test_no_problem_excluded(self):
        score, result = score_correction("no problem, that looks great")
        assert score == 0.0
        assert result is False

    def test_no_worries_excluded(self):
        score, result = score_correction("no worries at all")
        assert score == 0.0
        assert result is False

    def test_want_to_add_excluded(self):
        score, result = score_correction("I want to add a dark mode toggle")
        assert score == 0.0
        assert result is False

    def test_thats_great_excluded(self):
        score, result = score_correction("that's great, keep going")
        assert score == 0.0
        assert result is False

    def test_can_you_also_excluded(self):
        score, result = score_correction("can you also add error handling?")
        assert score == 0.0
        assert result is False

    # --- Strong corrections ---

    def test_dont_after_assistant(self):
        score, result = score_correction("don't do that", "assistant")
        assert result is True
        assert score >= 0.5

    def test_wrong_short(self):
        _, result = score_correction("wrong", "assistant")
        assert result is True

    def test_revert(self):
        _, result = score_correction("revert that change", "assistant")
        assert result is True

    def test_i_said(self):
        _, result = score_correction("I said use tabs", "assistant")
        assert result is True

    def test_i_meant(self):
        _, result = score_correction("I meant the other one", "assistant")
        assert result is True

    def test_thats_not_what_i(self):
        _, result = score_correction("that's not what I asked for")
        assert result is True

    # --- Weak corrections needing context ---

    def test_actually_alone_low(self):
        score, _ = score_correction(
            "actually, I was thinking about something else entirely and "
            "we should probably consider a different approach to this problem"
        )
        assert score < 0.5

    def test_actually_short_after_assistant(self):
        _, result = score_correction("actually, use Python", "assistant")
        assert result is True

    def test_switch_to_after_assistant(self):
        _, result = score_correction("switch to the v2 API", "assistant")
        assert result is True

    # --- Imperative starters ---

    def test_no_starter(self):
        _, result = score_correction("no, use Jira", "assistant")
        assert result is True

    def test_stop_starter(self):
        _, result = score_correction("stop, that's wrong", "assistant")
        assert result is True

    def test_use_starter_with_keyword(self):
        _, result = score_correction("use tabs not spaces", "assistant")
        assert result is True

    # --- Normal requests should not trigger ---

    def test_normal_request(self):
        _, result = score_correction("Can you add error handling?")
        assert result is False

    def test_positive_feedback(self):
        _, result = score_correction("that looks good")
        assert result is False

    def test_simple_question(self):
        _, result = score_correction("How does the auth flow work?")
        assert result is False

    def test_long_feature_request(self):
        _, result = score_correction(
            "I would like to add a new endpoint that handles user registration "
            "with email verification and OAuth support"
        )
        assert result is False


# ---------------------------------------------------------------------------
# is_correction (legacy wrapper)
# ---------------------------------------------------------------------------


class TestIsCorrection:
    def test_strong_correction(self):
        assert is_correction("don't use GitHub for this") is True

    def test_normal_request(self):
        assert is_correction("Can you add a feature?") is False

    def test_empty(self):
        assert is_correction("") is False


# ---------------------------------------------------------------------------
# detect_written_file_type
# ---------------------------------------------------------------------------


class TestDetectWrittenFileType:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/tmp/script.py", "python_script"),
            ("/path/SKILL.md", "skill_definition"),
            ("/path/README.md", "readme"),
            ("/tmp/notes.md", "markdown"),
            ("/tmp/data.json", "json"),
            ("/tmp/config.yaml", "yaml"),
            ("/tmp/config.yml", "yaml"),
            ("/tmp/run.sh", "shell_script"),
            ("/tmp/file.txt", "other"),
        ],
    )
    def test_file_type(self, path, expected):
        assert detect_written_file_type(path) == expected


# ---------------------------------------------------------------------------
# extract_jql_patterns
# ---------------------------------------------------------------------------


class TestExtractJqlPatterns:
    def test_empty_list(self):
        assert extract_jql_patterns([]) == []

    def test_non_jira_calls(self):
        calls = [{"subtype": "github_cli", "input": {"command": "gh pr list"}}]
        assert extract_jql_patterns(calls) == []

    def test_jira_calls(self):
        calls = [
            {
                "subtype": "jira_api",
                "input": {
                    "jql": "project = PROJ AND type = Bug",
                    "fields": ["summary"],
                    "maxResults": 50,
                },
            }
        ]
        patterns = extract_jql_patterns(calls)
        assert len(patterns) == 1
        assert patterns[0]["jql"] == "project = PROJ AND type = Bug"
        assert patterns[0]["fields"] == ["summary"]

    def test_deduplication(self):
        calls = [
            {"subtype": "jira_api", "input": {"jql": "project = PROJ"}},
            {"subtype": "jira_api", "input": {"jql": "project = PROJ"}},
        ]
        assert len(extract_jql_patterns(calls)) == 1


# ---------------------------------------------------------------------------
# _compact_tool_sequence
# ---------------------------------------------------------------------------


class TestCompactToolSequence:
    def test_empty(self):
        assert _compact_tool_sequence([]) == []

    def test_strips_tool_use_id(self):
        calls = [
            {
                "index": 1,
                "tool": "Bash",
                "phase": "data_processing",
                "subtype": "bash_command",
                "input": {"command": "ls"},
                "tool_use_id": "tu_123",
            }
        ]
        result = _compact_tool_sequence(calls)
        assert len(result) == 1
        assert "tool_use_id" not in result[0]
        assert result[0]["tool"] == "Bash"

    def test_preserves_error_fields(self):
        calls = [
            {
                "index": 1,
                "tool": "Bash",
                "phase": "data_processing",
                "subtype": "bash_command",
                "input": {"command": "ls"},
                "tool_use_id": "tu_123",
                "result_is_error": True,
                "result_preview": "command not found",
                "result_length": 17,
            }
        ]
        result = _compact_tool_sequence(calls)
        assert result[0]["result_is_error"] is True
        assert result[0]["result_preview"] == "command not found"

    def test_omits_non_error_fields(self):
        calls = [
            {
                "index": 1,
                "tool": "Read",
                "phase": "context_gathering",
                "subtype": "file_read",
                "input": {"file_path": "/tmp/f"},
                "tool_use_id": "tu_456",
            }
        ]
        result = _compact_tool_sequence(calls)
        assert "result_is_error" not in result[0]
        assert "result_preview" not in result[0]


# ---------------------------------------------------------------------------
# _detect_output_type
# ---------------------------------------------------------------------------


class TestDetectOutputType:
    def test_python_script(self):
        assert _detect_output_type({"a.py": {"file_type": "python_script"}}) == "python_script"

    def test_markdown(self):
        assert _detect_output_type({"a.md": {"file_type": "markdown"}}) == "markdown_report"

    def test_json(self):
        assert _detect_output_type({"a.json": {"file_type": "json"}}) == "json_data"

    def test_empty(self):
        assert _detect_output_type({}) == "unknown"

    def test_python_takes_priority(self):
        files = {
            "a.md": {"file_type": "markdown"},
            "b.py": {"file_type": "python_script"},
        }
        assert _detect_output_type(files) == "python_script"


# ---------------------------------------------------------------------------
# parse_conversation (integration)
# ---------------------------------------------------------------------------


def _parse_quietly(path):
    """Run parse_conversation with stderr suppressed, return (manifest, stderr_text)."""
    stderr = io.StringIO()
    old_stderr = sys.stderr
    sys.stderr = stderr
    try:
        manifest = parse_conversation(path)
    finally:
        sys.stderr = old_stderr
    return manifest, stderr.getvalue()


class TestParseConversationIntegration:
    def test_minimal_conversation(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "minimal_conversation.jsonl"))

        assert manifest["session_id"] == "abc-123"
        assert manifest["project_path"] == "/home/user/project"
        assert manifest["total_messages"] > 0
        assert len(manifest["tool_sequence"]) > 0
        assert len(manifest["written_files"]) > 0

        written = manifest["written_files"][0]
        assert written["path"] == "/tmp/bug-report.md"
        assert written["file_type"] == "markdown"

        assert manifest["detected_patterns"]["uses_jira_api"] is True
        assert manifest["summary"]["tool_calls"] > 0

    def test_empty_file(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "empty.jsonl"))

        assert manifest["total_messages"] == 0
        assert manifest["tool_sequence"] == []
        assert manifest["written_files"] == []
        assert manifest["corrections"] == []

    def test_malformed_lines_skipped(self):
        manifest, warnings = _parse_quietly(
            os.path.join(FIXTURES_DIR, "malformed_lines.jsonl")
        )

        assert "Warning" in warnings
        assert manifest["session_id"] == "def-456"
        assert manifest["total_messages"] > 0

    def test_correction_detection(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                '{"type":"user","sessionId":"test","cwd":"/tmp",'
                '"timestamp":1700000000000,"message":{"content":"List bugs"}}\n'
            )
            f.write(
                '{"type":"assistant","message":{"content":'
                '[{"type":"text","text":"Here are the bugs from GitHub."}]}}\n'
            )
            f.write(
                '{"type":"user","timestamp":1700000001000,"message":'
                '{"content":"No, don\'t use GitHub. Use Jira instead."}}\n'
            )
            tmp_path = f.name

        try:
            manifest, _ = _parse_quietly(tmp_path)

            assert len(manifest["corrections"]) > 0
            correction_texts = [c["text"] for c in manifest["corrections"]]
            assert any("Jira" in t for t in correction_texts), (
                f"Expected a Jira correction, got: {correction_texts}"
            )
        finally:
            os.unlink(tmp_path)

    def test_tool_result_attachment(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "minimal_conversation.jsonl"))

        jira_call = next(
            (tc for tc in manifest["tool_sequence"] if tc["subtype"] == "jira_api"), None
        )
        assert jira_call is not None
        assert "result_preview" in jira_call
        assert "PROJ-1" in jira_call["result_preview"]

    def test_jql_patterns_extracted(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "minimal_conversation.jsonl"))

        jql = manifest["api_patterns"]["jql_queries"]
        assert len(jql) > 0
        assert "project = PROJ" in jql[0]["jql"]

    def test_manifest_has_required_keys(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "minimal_conversation.jsonl"))

        required_keys = [
            "session_id",
            "project_path",
            "jsonl_path",
            "total_messages",
            "parsed_at",
            "user_intents",
            "tool_sequence",
            "written_files",
            "environment_variables",
            "api_patterns",
            "corrections",
            "errors_and_recoveries",
            "iterations",
            "detected_patterns",
            "summary",
        ]
        for key in required_keys:
            assert key in manifest, f"Missing key: {key}"

    def test_manifest_is_json_serializable(self):
        manifest, _ = _parse_quietly(os.path.join(FIXTURES_DIR, "minimal_conversation.jsonl"))

        serialized = json.dumps(manifest)
        assert isinstance(serialized, str)
        roundtrip = json.loads(serialized)
        assert roundtrip["session_id"] == manifest["session_id"]
