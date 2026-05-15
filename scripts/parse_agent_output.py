#!/usr/bin/env python3
"""Parse Agent output to extract generated skill files.

Splits on `## FILE: <path>` headers and extracts content from fenced
code blocks.  Outputs a JSON array to stdout, progress to stderr.

Usage:
    python3 parse_agent_output.py <file>
    python3 parse_agent_output.py < agent_output.txt
"""

import json
import os
import re
import sys

FILE_HEADER_RE = re.compile(r"^## FILE:\s*(.+)$", re.MULTILINE)
FENCE_RE = re.compile(
    r"^\s*```[a-zA-Z]*\s*\n(.*?)^\s*```\s*$", re.MULTILINE | re.DOTALL
)


def parse_agent_output(text):
    """Extract file blocks from Agent output text.

    Returns list of {"path": str, "content": str, "size": int}.
    """
    splits = FILE_HEADER_RE.split(text)

    # splits[0] is preamble (before first header), then alternating:
    # path, content, path, content, ...
    if len(splits) < 3:
        return []

    files = []
    for i in range(1, len(splits), 2):
        path = splits[i].strip()
        raw_content = splits[i + 1] if i + 1 < len(splits) else ""

        fence_match = FENCE_RE.search(raw_content)
        content = fence_match.group(1) if fence_match else raw_content.strip()

        # Remove single trailing newline from fenced content
        if content.endswith("\n"):
            content = content[:-1]

        files.append({
            "path": path,
            "content": content,
            "size": len(content),
        })

    return files


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isfile(path):
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    files = parse_agent_output(text)

    if not files:
        print("Error: no ## FILE: headers found in input", file=sys.stderr)
        sys.exit(1)

    print(f"Extracted {len(files)} file(s)", file=sys.stderr)
    json.dump(files, sys.stdout, indent=2)
    print(file=sys.stdout)


if __name__ == "__main__":
    main()
