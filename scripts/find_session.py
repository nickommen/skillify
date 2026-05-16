#!/usr/bin/env python3
"""Resolve a Claude Code conversation JSONL file.

Modes:
  recent    Find the most recent JSONL for a project directory.
  uuid      Find a JSONL by session UUID.
  list      List the 10 most recent unique sessions.

Usage:
  python3 find_session.py --mode recent --project-dir /path/to/project
  python3 find_session.py --mode uuid --session-id <uuid>
  python3 find_session.py --mode list

Output (JSON to stdout):
  recent/uuid: {"path": "/absolute/path/to/session.jsonl"}
  list:        [{"session_id": "...", "timestamp": "...", "display": "..."}, ...]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
HISTORY_FILE = Path.home() / ".claude" / "history.jsonl"


def find_recent(project_dir):
    slug = project_dir.lstrip("/").replace("/", "-")
    project_path = CLAUDE_PROJECTS_DIR / slug
    if not project_path.is_dir():
        return None
    jsonl_files = sorted(project_path.glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    return str(jsonl_files[0]) if jsonl_files else None


def find_by_uuid(session_id):
    for dirpath, _, filenames in os.walk(CLAUDE_PROJECTS_DIR):
        for fname in filenames:
            if fname == f"{session_id}.jsonl":
                return os.path.join(dirpath, fname)
    return None


def list_sessions(count=10):
    if not HISTORY_FILE.exists():
        print("History file not found: " + str(HISTORY_FILE), file=sys.stderr)
        return []
    sessions = []
    seen = set()
    with open(HISTORY_FILE) as f:
        lines = f.readlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = d.get("sessionId", "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        ts = d.get("timestamp", 0)
        dt = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        display = d.get("display", "")[:80]
        sessions.append({"session_id": sid, "timestamp": dt, "display": display})
        if len(sessions) >= count:
            break
    return sessions


def main():
    parser = argparse.ArgumentParser(description="Resolve Claude Code conversation JSONL files")
    parser.add_argument("--mode", required=True, choices=["recent", "uuid", "list"])
    parser.add_argument("--project-dir", help="Project directory (for recent mode)")
    parser.add_argument("--session-id", help="Session UUID (for uuid mode)")
    args = parser.parse_args()

    if args.mode == "recent":
        if not args.project_dir:
            print("--project-dir required for recent mode", file=sys.stderr)
            sys.exit(1)
        path = find_recent(args.project_dir)
        if path:
            json.dump({"path": path}, sys.stdout)
        else:
            print("No JSONL files found for project: " + args.project_dir, file=sys.stderr)
            sys.exit(1)

    elif args.mode == "uuid":
        if not args.session_id:
            print("--session-id required for uuid mode", file=sys.stderr)
            sys.exit(1)
        path = find_by_uuid(args.session_id)
        if path:
            json.dump({"path": path}, sys.stdout)
        else:
            print("Session not found: " + args.session_id, file=sys.stderr)
            sys.exit(1)

    elif args.mode == "list":
        sessions = list_sessions()
        if sessions:
            json.dump(sessions, sys.stdout, indent=2)
        else:
            print("No sessions found", file=sys.stderr)
            sys.exit(1)

    print("", file=sys.stdout)


if __name__ == "__main__":
    main()
