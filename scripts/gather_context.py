#!/usr/bin/env python3
"""Gather supplementary project context for skill generation.

Checks git history, diff stats, and detects project type from marker files.

Usage:
  python3 gather_context.py <project_path>

Output (JSON to stdout):
  {
    "is_git_repo": true,
    "git_log": ["abc1234 commit message", ...],
    "git_diff_stat": "3 files changed, ...",
    "project_files": ["pyproject.toml", "Makefile"]
  }
"""

import json
import os
import subprocess
import sys

PROJECT_MARKERS = [
    "package.json",
    "pyproject.toml",
    "Makefile",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "requirements.txt",
]


def run_git(project_path, *args):
    try:
        result = subprocess.run(
            ["git", "-C", project_path, *list(args)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: gather_context.py <project_path>", file=sys.stderr)
        sys.exit(1)

    project_path = sys.argv[1]
    if not os.path.isdir(project_path):
        print("Not a directory: " + project_path, file=sys.stderr)
        sys.exit(1)

    context = {
        "is_git_repo": False,
        "git_log": [],
        "git_diff_stat": "",
        "project_files": [],
    }

    git_log = run_git(project_path, "log", "--oneline", "-10")
    if git_log is not None:
        context["is_git_repo"] = True
        context["git_log"] = git_log.splitlines()

        diff_stat = run_git(project_path, "diff", "--stat")
        if diff_stat:
            lines = diff_stat.splitlines()
            context["git_diff_stat"] = "\n".join(lines[:20])

    for marker in PROJECT_MARKERS:
        if os.path.isfile(os.path.join(project_path, marker)):
            context["project_files"].append(marker)

    json.dump(context, sys.stdout, indent=2)
    print("", file=sys.stdout)


if __name__ == "__main__":
    main()
