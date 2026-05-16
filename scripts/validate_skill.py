#!/usr/bin/env python3
"""Validate a generated skill directory.

Checks Python syntax of all scripts and validates SKILL.md frontmatter.

Usage:
  python3 validate_skill.py <skill_directory>

Output (JSON to stdout):
  {
    "valid": true,
    "checks": [
      {"file": "scripts/main.py", "check": "python_syntax", "ok": true},
      {"file": "SKILL.md", "check": "frontmatter", "ok": true}
    ],
    "errors": []
  }

Exits 0 if all checks pass, 1 if any fail.
"""

import ast
import json
import re
import sys
from pathlib import Path

REQUIRED_FRONTMATTER_KEYS = ["name", "description", "user-invocable"]


def check_python_syntax(filepath):
    try:
        source = Path(filepath).read_text()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def check_frontmatter(filepath):
    try:
        text = Path(filepath).read_text()
    except FileNotFoundError:
        return False, "SKILL.md not found"

    match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not match:
        return False, "No YAML frontmatter found"

    fm = match.group(1)
    missing = [k for k in REQUIRED_FRONTMATTER_KEYS if k + ":" not in fm]
    if missing:
        return False, "Missing frontmatter keys: " + ", ".join(missing)

    return True, None


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_skill.py <skill_directory>", file=sys.stderr)
        sys.exit(1)

    skill_dir = Path(sys.argv[1])
    if not skill_dir.is_dir():
        print("Not a directory: " + str(skill_dir), file=sys.stderr)
        sys.exit(1)

    result = {"valid": True, "checks": [], "errors": []}

    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for py_file in sorted(scripts_dir.glob("*.py")):
            ok, error = check_python_syntax(py_file)
            rel_path = str(py_file.relative_to(skill_dir))
            result["checks"].append({"file": rel_path, "check": "python_syntax", "ok": ok})
            if not ok:
                result["valid"] = False
                result["errors"].append(f"{rel_path}: {error}")
            print(f"Python syntax {'OK' if ok else 'FAIL'}: {rel_path}", file=sys.stderr)

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        ok, error = check_frontmatter(skill_md)
        result["checks"].append({"file": "SKILL.md", "check": "frontmatter", "ok": ok})
        if not ok:
            result["valid"] = False
            result["errors"].append(f"SKILL.md: {error}")
        print(f"Frontmatter {'OK' if ok else 'FAIL'}: SKILL.md", file=sys.stderr)
    else:
        result["valid"] = False
        result["errors"].append("SKILL.md not found")
        result["checks"].append({"file": "SKILL.md", "check": "exists", "ok": False})

    json.dump(result, sys.stdout, indent=2)
    print("", file=sys.stdout)

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
