#!/usr/bin/env python3
"""Resolve a Claude Code conversation JSONL file.

Usage:
  python3 find_session.py --mode resolve
  python3 find_session.py --mode resolve --arguments "<uuid>"

Output (JSON to stdout):
  {"path": "/absolute/path/to/session.jsonl"}   — session resolved
  {"error": "..."}                              — resolution failed, message includes guidance
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
CLAUDE_SESSIONS_DIR = Path.home() / ".claude" / "sessions"

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def get_ancestor_pids():
    """Yield PIDs walking up the process tree from this process."""
    pid = os.getpid()
    while pid and pid != 1:
        yield pid
        try:
            with open(f"/proc/{pid}/stat") as f:
                fields = f.read().split()
                pid = int(fields[3])
        except (OSError, IndexError, ValueError):
            break


def find_by_pid():
    """Find the current session JSONL by walking up the process tree.

    Looks for a matching {pid}.json in ~/.claude/sessions/, extracts the
    sessionId, then locates the corresponding JSONL via find_by_uuid().
    """
    if not CLAUDE_SESSIONS_DIR.is_dir():
        return None

    session_files = {f.stem: f for f in CLAUDE_SESSIONS_DIR.glob("*.json")}
    if not session_files:
        return None

    for pid in get_ancestor_pids():
        session_file = session_files.get(str(pid))
        if session_file:
            try:
                data = json.loads(session_file.read_text())
                return find_by_uuid(data["sessionId"])
            except (json.JSONDecodeError, KeyError, OSError):
                return None

    return None


def find_by_uuid(session_id):
    for dirpath, _, filenames in os.walk(CLAUDE_PROJECTS_DIR):
        for fname in filenames:
            if fname == f"{session_id}.jsonl":
                return os.path.join(dirpath, fname)
    return None


def resolve(arguments):
    args_stripped = (arguments or "").strip()
    args_lower = args_stripped.lower()

    if not args_stripped or args_lower in ("this", "current", "this conversation"):
        path = find_by_pid()
        if path:
            return {"path": path}
        return {
            "error": "Could not detect session. Use: /skillify <uuid>",
        }

    if UUID_RE.fullmatch(args_stripped):
        path = find_by_uuid(args_stripped)
        if path:
            return {"path": path}
        return {
            "error": (
                f"Session not found: {args_stripped}\n"
                f"List available sessions with: ls ~/.claude/projects/\n"
                f"Then re-run: /skillify <session-uuid>"
            ),
        }

    return {
        "error": (
            f"Unrecognized argument: {args_stripped}\n"
            f"Usage: /skillify          — skillify the current project session\n"
            f"       /skillify this     — same as above\n"
            f"       /skillify <uuid>   — skillify a specific session"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Resolve Claude Code conversation JSONL files")
    parser.add_argument("--mode", required=True, choices=["resolve"])
    parser.add_argument("--arguments", help="Raw arguments string", default="")
    args = parser.parse_args()

    result = resolve(args.arguments)
    json.dump(result, sys.stdout)
    print("", file=sys.stdout)
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
