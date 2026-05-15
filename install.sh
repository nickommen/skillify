#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${HOME}/.claude/skills/skillify"

mkdir -p "${HOME}/.claude/skills"
ln -sf "${SKILL_DIR}" "${TARGET}"

echo "Skillify installed at ${TARGET}"
echo "Invoke with /skillify in Claude Code"
