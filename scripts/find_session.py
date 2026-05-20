#!/usr/bin/env python3
"""Resolve a Claude Code conversation JSONL file.

Usage:
  python3 find_session.py --mode resolve --project-dir /path/to/project
  python3 find_session.py --mode resolve --arguments "<uuid>" --project-dir /path/to/project

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

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def find_recent(project_dir):
    slug = project_dir.replace("/", "-")
    project_path = CLAUDE_PROJECTS_DIR / slug
    if not project_path.is_dir():
        return None
    jsonl_files = sorted(project_path.glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    for f in jsonl_files:
        return str(f)
    return None


def find_by_uuid(session_id):
    for dirpath, _, filenames in os.walk(CLAUDE_PROJECTS_DIR):
        for fname in filenames:
            if fname == f"{session_id}.jsonl":
                return os.path.join(dirpath, fname)
    return None


def resolve(arguments, project_dir=None):
    args_stripped = (arguments or "").strip()
    args_lower = args_stripped.lower()

    if not args_stripped or args_lower in ("this", "current", "this conversation"):
        if project_dir:
            path = find_recent(project_dir)
            if path:
                return {"path": path}
        slug = project_dir.replace("/", "-") if project_dir else "<project-slug>"
        return {
            "error": (
                f"No session found for this project directory.\n"
                f"List available sessions with: ls ~/.claude/projects/{slug}/\n"
                f"Then re-run: /skillify <session-uuid>"
            ),
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
    parser.add_argument("--project-dir", help="Project directory")
    args = parser.parse_args()

    result = resolve(args.arguments, project_dir=args.project_dir)
    json.dump(result, sys.stdout)
    print("", file=sys.stdout)
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
