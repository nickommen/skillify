#!/usr/bin/env python3
"""Resolve a Claude Code conversation JSONL file.

Modes:
  parent    Find the parent session (most recent in history, excluding current fork).
  recent    Find the most recent JSONL for a project directory.
  uuid      Find a JSONL by session UUID.
  name      Find a session by custom title or agent name (from /rename).
  list      List the 10 most recent unique sessions.

Usage:
  python3 find_session.py --mode parent --exclude-session <fork-session-id>
  python3 find_session.py --mode recent --project-dir /path/to/project
  python3 find_session.py --mode uuid --session-id <uuid>
  python3 find_session.py --mode name --session-name <name>
  python3 find_session.py --mode list

Output (JSON to stdout):
  recent/uuid/name: {"path": "/absolute/path/to/session.jsonl"}
  list:             [{"session_id": "...", "timestamp": "...", "display": "...", "project": "..."}, ...]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
HISTORY_FILE = Path.home() / ".claude" / "history.jsonl"


def find_parent(exclude_session):
    if not HISTORY_FILE.exists():
        return None
    with open(HISTORY_FILE) as f:
        lines = f.readlines()
    seen = set()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = d.get("sessionId", "")
        if not sid or sid in seen or sid == exclude_session:
            continue
        path = find_by_uuid(sid)
        if path:
            return path
        seen.add(sid)
    return None


def find_recent(project_dir, exclude_session=None):
    slug = project_dir.replace("/", "-")
    project_path = CLAUDE_PROJECTS_DIR / slug
    if not project_path.is_dir():
        return None
    jsonl_files = sorted(project_path.glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    for f in jsonl_files:
        if exclude_session and f.stem == exclude_session:
            continue
        return str(f)
    return None


def find_by_uuid(session_id):
    for dirpath, _, filenames in os.walk(CLAUDE_PROJECTS_DIR):
        for fname in filenames:
            if fname == f"{session_id}.jsonl":
                return os.path.join(dirpath, fname)
    return None


def get_first_user_message(session_id):
    path = find_by_uuid(session_id)
    if not path:
        return None
    try:
        with open(path) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    entry = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "user":
                    continue
                msg = entry.get("message", {})
                content = msg.get("content", "")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        b.get("text", "")
                        for b in content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                else:
                    continue
                text = text.strip()
                if text and not text.startswith("<"):
                    return text[:120]
    except OSError:
        pass
    return None


def find_by_name(name):
    name_lower = name.lower().strip()
    if not CLAUDE_PROJECTS_DIR.is_dir():
        return None
    for dirpath, _, filenames in os.walk(CLAUDE_PROJECTS_DIR):
        for fname in filenames:
            if not fname.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, fname)
            try:
                with open(path) as f:
                    for raw_line in f:
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        try:
                            entry = json.loads(raw_line)
                        except json.JSONDecodeError:
                            continue
                        entry_type = entry.get("type", "")
                        if entry_type == "custom-title":
                            title = entry.get("customTitle", "")
                            if title.lower().strip() == name_lower:
                                return path
                        elif entry_type == "agent-name":
                            agent = entry.get("agentName", "")
                            if agent.lower().strip() == name_lower:
                                return path
            except OSError:
                continue
    return None


def list_sessions(count=10, exclude_session=None):
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
        if not sid or sid in seen or sid == exclude_session:
            continue
        seen.add(sid)
        ts = d.get("timestamp", 0)
        dt = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        first_msg = get_first_user_message(sid)
        display = first_msg if first_msg else d.get("display", "")[:80]
        project = d.get("project", "")
        sessions.append({
            "session_id": sid,
            "timestamp": dt,
            "display": display,
            "project": project,
        })
        if len(sessions) >= count:
            break
    return sessions


def main():
    parser = argparse.ArgumentParser(description="Resolve Claude Code conversation JSONL files")
    parser.add_argument("--mode", required=True, choices=["parent", "recent", "uuid", "name", "list"])
    parser.add_argument("--project-dir", help="Project directory (for recent mode)")
    parser.add_argument("--session-id", help="Session UUID (for uuid mode)")
    parser.add_argument("--session-name", help="Session name (for name mode)")
    parser.add_argument(
        "--exclude-session",
        help="Session ID to skip (for parent/recent mode)",
    )
    args = parser.parse_args()

    if args.mode == "parent":
        if not args.exclude_session:
            print("--exclude-session required for parent mode", file=sys.stderr)
            sys.exit(1)
        path = find_parent(args.exclude_session)
        if path:
            json.dump({"path": path}, sys.stdout)
        else:
            print("No parent session found", file=sys.stderr)
            sys.exit(1)

    elif args.mode == "recent":
        if not args.project_dir:
            print("--project-dir required for recent mode", file=sys.stderr)
            sys.exit(1)
        path = find_recent(args.project_dir, exclude_session=args.exclude_session)
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

    elif args.mode == "name":
        if not args.session_name:
            print("--session-name required for name mode", file=sys.stderr)
            sys.exit(1)
        path = find_by_name(args.session_name)
        if path:
            json.dump({"path": path}, sys.stdout)
        else:
            print("Session not found with name: " + args.session_name, file=sys.stderr)
            sys.exit(1)

    elif args.mode == "list":
        sessions = list_sessions(exclude_session=args.exclude_session)
        if sessions:
            json.dump(sessions, sys.stdout, indent=2)
        else:
            print("No sessions found", file=sys.stderr)
            sys.exit(1)

    print("", file=sys.stdout)


if __name__ == "__main__":
    main()
