#!/usr/bin/env python3
"""Parse a Claude Code conversation JSONL into a compact workflow manifest.

Streams the JSONL line-by-line to handle large files (11MB+).
Outputs a JSON manifest to stdout, progress messages to stderr.

Usage: python3 parse_conversation.py <jsonl_path>
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Truncation limits
# ---------------------------------------------------------------------------
USER_TEXT_LIMIT = 500
WRITE_CONTENT_PREVIEW = 200
EDIT_PREVIEW = 200
TOOL_RESULT_PREVIEW = 300

# ---------------------------------------------------------------------------
# Correction-detection: context-aware multi-signal scoring
# ---------------------------------------------------------------------------
CORRECTION_EXCLUSIONS = re.compile(
    r"(?i)\b("
    r"no problem|no worries|no rush|no need|no issue|"
    r"I want to add|I want to create|I want to build|I want to make|"
    r"I'd like to|I would like to|"
    r"can you also|could you also|"
    r"that's great|that's good|that's perfect|that's fine|that's correct"
    r")\b"
)

STRONG_CORRECTION = re.compile(
    r"(?i)\b("
    r"don'?t|do not|that'?s not|not what i|wrong|revert|"
    r"I said|I meant|fix that|change that"
    r")\b"
)

WEAK_CORRECTION = re.compile(
    r"(?i)\b("
    r"instead|actually|rather than|switch to|go back to|"
    r"prefer|should be|use .+ not "
    r")\b"
)

IMPERATIVE_STARTERS_STRONG = {"no", "stop", "wait", "hold", "nope"}
IMPERATIVE_STARTERS_WEAK = {"use", "change", "switch", "try", "make"}

CORRECTION_THRESHOLD = 0.5

# Legacy pattern kept for backward compatibility
CORRECTION_PATTERNS = re.compile(
    r"(?i)\b("
    r"no[, ]|don'?t|do not|instead[, ]|actually[, ]|"
    r"change that|use .+ not |stop |wrong|"
    r"that'?s not|not what i|rather than|"
    r"switch to|go back to|revert|"
    r"prefer|should be|fix that|"
    r"I said|I meant|I want"
    r")\b"
)

# ---------------------------------------------------------------------------
# Environment variable detection patterns
# ---------------------------------------------------------------------------
ENV_VAR_PATTERNS = [
    re.compile(r'os\.environ\.get\(["\'](\w+)["\']'),
    re.compile(r'os\.environ\[["\'](\w+)["\']\]'),
    re.compile(r'export\s+(\w+)='),
    re.compile(r'\$\{?(\w+)\}?', re.MULTILINE),
    re.compile(r'getenv\(["\'](\w+)["\']'),
]

# Known non-env-var shell variables to exclude
SHELL_BUILTINS = {
    "HOME", "USER", "PATH", "PWD", "SHELL", "TERM", "LANG",
    "TMPDIR", "HOSTNAME", "LOGNAME", "EDITOR", "VISUAL",
    "CLAUDE_SKILL_DIR", "ARGUMENTS",
}


def truncate(text, limit):
    if not text or len(text) <= limit:
        return text
    return text[:limit] + f"... [{len(text)} chars total]"


def extract_text_from_content(content):
    """Extract plain text from a message content field (string or list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def classify_tool_call(name, input_dict):
    """Classify a tool call into a workflow phase and subtype."""
    if name in (
        "mcp__atlassian__searchJiraIssuesUsingJql",
        "mcp__atlassian__getJiraIssue",
        "mcp__atlassian__search",
    ):
        return "data_gathering", "jira_api"
    if name.startswith("mcp__atlassian__"):
        return "data_gathering", "atlassian_api"
    if name.startswith("mcp__google_workspace__"):
        return "data_gathering", "google_workspace"

    if name == "Bash":
        cmd = input_dict.get("command", "")
        if cmd.lstrip().startswith("gh "):
            return "data_gathering", "github_cli"
        if "python3" in cmd or "python " in cmd:
            return "data_processing", "python_execution"
        if "mkdir" in cmd:
            return "setup", "directory_creation"
        if "ln -s" in cmd:
            return "setup", "symlink"
        if "curl " in cmd or "wget " in cmd:
            return "data_gathering", "http_request"
        return "data_processing", "bash_command"

    if name == "Write":
        path = input_dict.get("file_path", "")
        if path.endswith(".py"):
            return "script_creation", "python_script"
        if "SKILL.md" in path:
            return "skill_creation", "skill_definition"
        if "README.md" in path:
            return "skill_creation", "readme"
        return "output_generation", "file_write"

    if name == "Edit":
        return "refinement", "file_edit"

    if name == "Agent":
        return "ai_delegation", "agent_call"

    if name == "Read":
        return "context_gathering", "file_read"

    if name == "WebFetch":
        return "data_gathering", "web_fetch"

    if name == "WebSearch":
        return "data_gathering", "web_search"

    if name == "AskUserQuestion":
        return "user_interaction", "question"

    if name == "Skill":
        return "skill_invocation", "skill_call"

    return "unknown", name


def extract_tool_input(name, input_dict):
    """Extract tool input with appropriate truncation."""
    result = {}
    if name == "Bash":
        result["command"] = input_dict.get("command", "")
    elif name == "Write":
        result["file_path"] = input_dict.get("file_path", "")
        content = input_dict.get("content", "")
        result["content_preview"] = truncate(content, WRITE_CONTENT_PREVIEW)
        result["content_length"] = len(content)
    elif name == "Edit":
        result["file_path"] = input_dict.get("file_path", "")
        result["old_string_preview"] = truncate(
            input_dict.get("old_string", ""), EDIT_PREVIEW
        )
        result["new_string_preview"] = truncate(
            input_dict.get("new_string", ""), EDIT_PREVIEW
        )
    elif name == "Read":
        result["file_path"] = input_dict.get("file_path", "")
    elif name == "Agent":
        result["prompt"] = input_dict.get("prompt", "")
        result["description"] = input_dict.get("description", "")
        if input_dict.get("subagent_type"):
            result["subagent_type"] = input_dict["subagent_type"]
    elif name == "Skill":
        result["skill"] = input_dict.get("skill", "")
        result["args"] = input_dict.get("args", "")
    else:
        result = dict(input_dict)
    return result


def extract_env_vars(text):
    """Extract environment variable names from text."""
    found = set()
    for pattern in ENV_VAR_PATTERNS:
        for match in pattern.finditer(text):
            var = match.group(1)
            if var not in SHELL_BUILTINS and var.isupper() and len(var) > 2:
                found.add(var)
    return found


def extract_jql_patterns(tool_calls):
    """Extract JQL query patterns from Jira tool calls."""
    patterns = []
    seen = set()
    for tc in tool_calls:
        if tc.get("subtype") == "jira_api":
            inp = tc.get("input", {})
            jql = inp.get("jql", "")
            if jql and jql not in seen:
                seen.add(jql)
                patterns.append({
                    "jql": jql,
                    "fields": inp.get("fields", []),
                    "max_results": inp.get("maxResults"),
                })
    return patterns


def score_correction(text, prev_message_type=None):
    """Score how likely a user message is a correction/redirection.

    Returns (score: float, is_correction: bool).
    """
    if not text or not text.strip():
        return 0.0, False

    if CORRECTION_EXCLUSIONS.search(text):
        return 0.0, False

    score = 0.0

    if STRONG_CORRECTION.search(text):
        score += 0.4
    elif WEAK_CORRECTION.search(text):
        score += 0.2

    if prev_message_type == "assistant":
        score += 0.2

    text_len = len(text.strip())
    if text_len < 50:
        score += 0.2
    elif text_len < 100:
        score += 0.1

    words = text.strip().split()
    if words:
        first_word = words[0].lower().rstrip(".,!?:")
        if first_word in IMPERATIVE_STARTERS_STRONG:
            score += 0.2
        elif first_word in IMPERATIVE_STARTERS_WEAK:
            score += 0.1

    return score, score >= CORRECTION_THRESHOLD


def is_correction(text):
    """Detect if a user message is correcting/redirecting the approach.

    Legacy wrapper around score_correction for backward compatibility.
    """
    _, result = score_correction(text)
    return result


def detect_written_file_type(path):
    """Classify a written file by its extension/name."""
    if path.endswith(".py"):
        return "python_script"
    if path.endswith("SKILL.md"):
        return "skill_definition"
    if path.endswith("README.md"):
        return "readme"
    if path.endswith(".md"):
        return "markdown"
    if path.endswith(".json"):
        return "json"
    if path.endswith(".yaml") or path.endswith(".yml"):
        return "yaml"
    if path.endswith(".sh"):
        return "shell_script"
    return "other"


def parse_conversation(jsonl_path):
    """Parse a conversation JSONL file into a workflow manifest."""
    user_intents = []
    tool_calls = []
    written_files = {}  # path -> latest info
    env_vars = set()
    corrections = []
    errors_and_recoveries = []
    iterations = []

    message_count = 0
    session_id = None
    project_path = None
    last_assistant_had_error = False
    last_error_info = None
    prev_message_type = None
    edit_counts = defaultdict(int)  # path -> edit count

    print("Parsing conversation...", file=sys.stderr)

    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"  Warning: skipping malformed line {line_num}",
                    file=sys.stderr,
                )
                continue

            entry_type = entry.get("type")

            if entry_type == "user":
                message_count += 1
                if not session_id and entry.get("sessionId"):
                    session_id = entry["sessionId"]
                if not project_path and entry.get("cwd"):
                    project_path = entry["cwd"]

                msg = entry.get("message", {})
                content = msg.get("content", "")
                text = extract_text_from_content(content)

                # Skip system-injected messages (local-command caveats, etc.)
                is_system_injected = "<local-command-" in text or "<system-reminder>" in text
                clean_text = text.strip()

                if clean_text and not is_system_injected:
                    intent = {
                        "index": message_count,
                        "text": truncate(clean_text, USER_TEXT_LIMIT),
                        "timestamp": entry.get("timestamp"),
                    }

                    if message_count == 1:
                        intent["is_initial_request"] = True
                    correction_score, is_correcting = score_correction(
                        clean_text, prev_message_type
                    )
                    if is_correcting:
                        intent["is_correction"] = True
                        intent["correction_score"] = correction_score
                        corrections.append({
                            "index": message_count,
                            "text": clean_text,
                            "timestamp": entry.get("timestamp"),
                            "score": correction_score,
                        })

                    user_intents.append(intent)

                # Extract tool results from user message content
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            tool_use_id = item.get("tool_use_id", "")
                            result_content = ""
                            is_error = item.get("is_error", False)

                            if isinstance(item.get("content"), str):
                                result_content = item["content"]
                            elif isinstance(item.get("content"), list):
                                for sub in item["content"]:
                                    if isinstance(sub, dict) and sub.get("type") == "text":
                                        result_content += sub.get("text", "")

                            # Attach result to matching tool call
                            for tc in reversed(tool_calls):
                                if tc.get("tool_use_id") == tool_use_id:
                                    tc["result_preview"] = truncate(
                                        result_content, TOOL_RESULT_PREVIEW
                                    )
                                    tc["result_length"] = len(result_content)
                                    tc["result_is_error"] = is_error
                                    break

                            if is_error:
                                last_assistant_had_error = True
                                last_error_info = {
                                    "error_preview": truncate(
                                        result_content, TOOL_RESULT_PREVIEW
                                    ),
                                    "tool_use_id": tool_use_id,
                                }

                            env_vars.update(extract_env_vars(result_content))

                prev_message_type = "user"

            elif entry_type == "assistant":
                message_count += 1
                msg = entry.get("message", {})
                content = msg.get("content", [])

                if not isinstance(content, list):
                    content = [content] if content else []

                for item in content:
                    if not isinstance(item, dict):
                        continue

                    if item.get("type") == "tool_use":
                        name = item.get("name", "")
                        input_dict = item.get("input", {})
                        tool_use_id = item.get("id", "")

                        phase, subtype = classify_tool_call(name, input_dict)
                        extracted_input = extract_tool_input(name, input_dict)

                        tc = {
                            "index": message_count,
                            "tool": name,
                            "phase": phase,
                            "subtype": subtype,
                            "input": extracted_input,
                            "tool_use_id": tool_use_id,
                        }
                        tool_calls.append(tc)

                        # Track written files (final version wins)
                        if name == "Write":
                            path = input_dict.get("file_path", "")
                            if path:
                                written_files[path] = {
                                    "path": path,
                                    "content_preview": truncate(
                                        input_dict.get("content", ""),
                                        WRITE_CONTENT_PREVIEW,
                                    ),
                                    "content_length": len(
                                        input_dict.get("content", "")
                                    ),
                                    "file_type": detect_written_file_type(path),
                                    "write_index": message_count,
                                }
                        elif name == "Edit":
                            path = input_dict.get("file_path", "")
                            if path:
                                edit_counts[path] += 1
                                if path in written_files:
                                    written_files[path]["edit_count"] = edit_counts[path]

                        # Track error recovery
                        if last_assistant_had_error and last_error_info:
                            errors_and_recoveries.append({
                                "error": last_error_info["error_preview"],
                                "recovery_tool": name,
                                "recovery_input_preview": truncate(
                                    json.dumps(extracted_input), TOOL_RESULT_PREVIEW
                                ),
                            })
                            last_assistant_had_error = False
                            last_error_info = None

                        # Extract env vars from tool inputs
                        input_text = json.dumps(input_dict)
                        env_vars.update(extract_env_vars(input_text))

                    elif item.get("type") == "text":
                        text = item.get("text", "")
                        env_vars.update(extract_env_vars(text))

                prev_message_type = "assistant"

    # Detect iterations (multiple edits to same file)
    for path, count in edit_counts.items():
        if count >= 2:
            iterations.append({
                "file": path,
                "edit_count": count,
                "type": "repeated_edits",
            })

    # Build detected patterns
    tool_names = {tc["tool"] for tc in tool_calls}
    subtypes = {tc["subtype"] for tc in tool_calls}
    phases = {tc["phase"] for tc in tool_calls}

    detected_patterns = {
        "uses_jira_api": "jira_api" in subtypes or "atlassian_api" in subtypes,
        "uses_github_cli": "github_cli" in subtypes,
        "uses_google_workspace": "google_workspace" in subtypes,
        "has_python_script": any(
            wf.get("file_type") == "python_script"
            for wf in written_files.values()
        ),
        "has_agent_delegation": "ai_delegation" in phases,
        "has_skill_creation": "skill_creation" in phases,
        "output_type": _detect_output_type(written_files),
        "is_read_only": "script_creation" not in phases
        and "output_generation" not in phases
        and "skill_creation" not in phases,
        "tools_used": sorted(tool_names),
    }

    # Extract JQL patterns
    jql_patterns = extract_jql_patterns(tool_calls)

    # Build github CLI commands
    gh_commands = []
    seen_gh = set()
    for tc in tool_calls:
        if tc["subtype"] == "github_cli":
            cmd = tc["input"].get("command", "")
            if cmd and cmd not in seen_gh:
                seen_gh.add(cmd)
                gh_commands.append(cmd)

    # Build manifest
    manifest = {
        "session_id": session_id,
        "project_path": project_path,
        "jsonl_path": jsonl_path,
        "total_messages": message_count,
        "parsed_at": datetime.now().isoformat(),
        "user_intents": user_intents,
        "tool_sequence": _compact_tool_sequence(tool_calls),
        "written_files": list(written_files.values()),
        "environment_variables": sorted(env_vars),
        "api_patterns": {
            "jql_queries": jql_patterns,
            "github_cli_commands": gh_commands,
        },
        "corrections": corrections,
        "errors_and_recoveries": errors_and_recoveries,
        "iterations": iterations,
        "detected_patterns": detected_patterns,
        "summary": {
            "user_messages": len(user_intents),
            "tool_calls": len(tool_calls),
            "files_written": len(written_files),
            "corrections_detected": len(corrections),
            "errors_encountered": len(errors_and_recoveries),
            "env_vars_needed": len(env_vars),
        },
    }

    print(
        f"  Parsed {message_count} messages, "
        f"{len(tool_calls)} tool calls, "
        f"{len(written_files)} written files",
        file=sys.stderr,
    )

    return manifest


def _compact_tool_sequence(tool_calls):
    """Remove internal fields (tool_use_id) and produce compact sequence."""
    compact = []
    for tc in tool_calls:
        entry = {
            "index": tc["index"],
            "tool": tc["tool"],
            "phase": tc["phase"],
            "subtype": tc["subtype"],
            "input": tc["input"],
        }
        if tc.get("result_is_error"):
            entry["result_is_error"] = True
        if tc.get("result_preview"):
            entry["result_preview"] = tc["result_preview"]
        if tc.get("result_length"):
            entry["result_length"] = tc["result_length"]
        compact.append(entry)
    return compact


def _detect_output_type(written_files):
    """Detect the primary output type from written files."""
    types = [wf.get("file_type") for wf in written_files.values()]
    if "python_script" in types:
        return "python_script"
    if "markdown" in types:
        return "markdown_report"
    if "json" in types:
        return "json_data"
    return "unknown"


def main():
    if len(sys.argv) != 2:
        print(
            f"Usage: {sys.argv[0]} <jsonl_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    jsonl_path = sys.argv[1]
    if not os.path.isfile(jsonl_path):
        print(f"Error: file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)

    manifest = parse_conversation(jsonl_path)
    json.dump(manifest, sys.stdout, indent=2)
    print(file=sys.stdout)  # trailing newline


if __name__ == "__main__":
    main()
