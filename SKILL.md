---
name: skillify
description: >
  Convert a Claude Code conversation into a deterministic Python-scripted skill.
  TRIGGER when: "skillify", "turn this into a skill", "make this a skill",
  "create a skill from this conversation", "convert this to a skill",
  "skillify this", "make a skill from this".
  Do NOT use for: creating skills from scratch without a source conversation,
  editing/refining existing skills, or generating prompt-only skills without scripts.
user-invocable: true
context: fork
argument-hint: [session-id | "this"]
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Agent
  - AskUserQuestion
model: claude-opus-4-6
---

# Skillify

Convert a Claude Code conversation — where the user iterated on automating a task — into a deterministic Python-scripted skill. The goal is to capture all repeatable work in Python scripts and use AI only for error recovery and semantic summarization on future runs.

## Rules

- Default to AskUserQuestion for all user input. Use it for confirmations, choices, and decisions. The built-in "Other" option handles free-text fallback.
- Generated SKILL.md files must stay under 500 lines. Put large references in separate files.
- Generated skill descriptions must state both what the skill does AND when to use it.
- Generated skills must list all tools they call in `allowed-tools`.
- Preserve the tools from the source conversation by default. Only convert MCP to REST if the user explicitly requests standalone mode.

## Procedure

### Step 1: Identify the Conversation

Resolve the source conversation JSONL file. Check these modes **in order** — use the FIRST one that matches and do NOT fall through to later modes.

**Mode A — Current session (MANDATORY when arguments are empty or say "this"):**
If `$ARGUMENTS` is empty, blank, unset, OR contains "this", "current", or "this conversation": use the current session. Do NOT show a picker. Do NOT ask the user to choose. Immediately resolve the JSONL path:
```
ls -t ~/.claude/projects/$(echo "$PWD" | sed 's|/|-|g; s|^-||')/*.jsonl 2>/dev/null | head -1
```
If found, proceed directly to Step 2.

**Mode B — Explicit session ID:**
Only if `$ARGUMENTS` contains a UUID (pattern: `[0-9a-f-]{36}`):
```
find ~/.claude/projects/ -name "$ARGUMENTS.jsonl" -type f 2>/dev/null
```
If not found, tell the user and ask for a different session ID.

**Mode C — Interactive picker:**
Only if `$ARGUMENTS` contains text that is NOT empty and NOT "this"/"current" and NOT a UUID:
1. Read `~/.claude/history.jsonl` and extract the 10 most recent unique sessions:
   ```
   tac ~/.claude/history.jsonl | python3 -c "
   import sys, json
   seen = set()
   for line in sys.stdin:
       d = json.loads(line.strip())
       sid = d.get('sessionId','')
       if sid and sid not in seen:
           seen.add(sid)
           ts = d.get('timestamp',0)
           from datetime import datetime
           dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M')
           print(f'{sid}  {dt}  {d.get(\"display\",\"\")[:80]}')
           if len(seen) >= 10: break
   "
   ```
2. Present the list and let the user pick via AskUserQuestion.
3. Locate the selected session's JSONL file.

**Success criteria:** A valid JSONL file path is identified.

---

### Step 2: Parse and Gather Context

Run the conversation parser to extract the workflow manifest:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_conversation.py "{JSONL_PATH}" > /tmp/skillify-manifest.json
```

If the parser fails, show the error and stop.

Also gather supplementary context:
1. If the source conversation's `project_path` is a git repo, run:
   ```
   git -C "{PROJECT_PATH}" log --oneline -10 2>/dev/null
   git -C "{PROJECT_PATH}" diff --stat 2>/dev/null | head -20
   ```
2. Detect project type:
   ```
   for f in package.json pyproject.toml Makefile Cargo.toml go.mod Gemfile requirements.txt; do
     [ -f "{PROJECT_PATH}/$f" ] && echo "Found: $f"
   done
   ```

Read `/tmp/skillify-manifest.json` to get the full manifest.

**Success criteria:** Manifest JSON is valid and contains at least 1 tool call.

---

### Step 3: Load Config, Present Summary, and Interview

Read the user's skillify config if it exists:
```
cat ~/.claude/skillify.json 2>/dev/null || echo '{}'
```

Use config values as defaults in the interview. If no config exists, use built-in defaults:
- `default_save_location`: `~/.claude/skills`
- `symlink_base`: `~/.claude/skills`

Present the manifest summary to the user:
- Total messages, tool calls, files written
- Tools used (grouped by category)
- API patterns detected (Jira JQL, GitHub CLI, etc.)
- Environment variables needed
- Corrections detected (user redirections, with scores)
- Whether the conversation already produced scripts or a skill

Then conduct a brief interview via AskUserQuestion:

**Round 1:** Ask all of these in a single AskUserQuestion with multiple questions:
- Suggest a skill name based on the workflow. Let the user confirm or rename.
- Suggest a one-line description (must include what it does AND when to use it). Let the user confirm or edit.
- Ask where to save the skill:
  - **Personal skills** (`{config.default_save_location}/{name}/`) — available across all projects (Recommended)
  - **This repo** (`.claude/skills/{name}/`) — for repo-specific workflows
- Ask about tool mode:
  - **Preserve tools** (Recommended) — generated skill uses the same MCP tools and CLIs from the source conversation
  - **Standalone** — convert all tool calls to REST API calls using `urllib.request` (no MCP dependency)

**Round 2 (skip for simple workflows with ≤3 tool call phases):**
- Present the identified workflow steps as a numbered list (derived from the tool call phases in the manifest).
- Ask via AskUserQuestion if anything is missing, should be changed, or needs special handling.
- Ask about preconditions: "Does this workflow require anything to be true before it runs?" (e.g., clean git repo, env vars set, specific files present)
- Ask about idempotency: "Is it safe to run this multiple times?"
- Ask about escalation: "When should the skill stop and ask for help vs. retry automatically?"

**Success criteria:** Skill name, description, save location, tool mode, and workflow steps are confirmed.

---

### Step 4: Check for Existing Scripts

Check the manifest's `written_files` for any Python scripts or SKILL.md files that were already created during the source conversation.

If existing scripts are found:
1. Read each script file (verify it still exists on disk).
2. Ask the user via AskUserQuestion:
   - **Use existing scripts as-is** (Recommended) — adapt and wrap them in the new skill
   - **Regenerate from workflow** — have the Agent generate new scripts from the manifest

If using existing scripts, read their full content for passing to the generation agent.

**Success criteria:** Decision made on whether to reuse or regenerate scripts.

---

### Step 5: Generate the Skill

Read the agent prompt template:
```
${CLAUDE_SKILL_DIR}/prompts/generate_skill.md
```

If the user chose standalone mode in Step 3, also read the REST API reference:
```
${CLAUDE_SKILL_DIR}/prompts/rest_api_reference.md
```

Substitute the placeholders:
- `{WORKFLOW_MANIFEST}` — the full manifest JSON from Step 2
- `{SKILL_NAME}` — the confirmed skill name from Step 3
- `{SAVE_LOCATION}` — the confirmed save path from Step 3
- `{CORRECTIONS}` — the corrections array from the manifest (or "None detected" if empty)
- `{EXISTING_SCRIPTS}` — content of existing scripts from Step 4 (or "None — generate from scratch" if regenerating)
- `{TOOL_MODE}` — "preserve" or "standalone" from Step 3
- `{TOOL_DEPENDENCIES}` — list of MCP servers and CLI tools the workflow requires
- `{PRECONDITIONS}` — from Round 2 interview (or "None specified")
- `{IDEMPOTENCY}` — from Round 2 interview (or "Not specified")
- `{ESCALATION_RULES}` — from Round 2 interview (or "Default: stop and ask on any error")
- `{MCP_API_MAPPINGS}` — contents of `rest_api_reference.md` if standalone mode, otherwise "N/A — preserving source tools"

Launch an Agent with the substituted prompt. The Agent will output file contents in clearly marked `## FILE:` sections.

Save the Agent's output to a temporary file, then parse it deterministically:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_agent_output.py /tmp/skillify-agent-output.txt > /tmp/skillify-files.json
```

Read `/tmp/skillify-files.json` to get the list of files.

**Success criteria:** Parser extracts at least SKILL.md and one Python script.

---

### Step 5b: Preview Generated Files

Present a summary of what will be written. For each file from the parsed output, show:
- Full target path: `{SAVE_LOCATION}/{relative_path}`
- File size in bytes
- First 20 lines of content

Then use AskUserQuestion:
- **Write all files** (Recommended) — proceed to Step 6
- **Write with changes** — let the user specify modifications before writing
- **Abort** — stop without writing anything

If the user chooses "Abort", stop and report that no files were written.
If the user chooses "Write with changes", ask what to change, apply modifications, then proceed to Step 6.

**Success criteria:** User has confirmed the files to write.

---

### Step 6: Write and Validate

Create the skill directory structure:
```
mkdir -p {SAVE_LOCATION}/scripts
mkdir -p {SAVE_LOCATION}/output
```

Write each file from the confirmed file list to its correct location.

Validate the generated Python script(s):
```
python3 -c "import ast; ast.parse(open('{SAVE_LOCATION}/scripts/{script_name}.py').read()); print('Python syntax OK')"
```

Validate the SKILL.md frontmatter:
```
python3 -c "
import re
text = open('{SAVE_LOCATION}/SKILL.md').read()
match = re.match(r'^---\n(.+?)\n---', text, re.DOTALL)
if not match:
    print('ERROR: No YAML frontmatter found')
    exit(1)
fm = match.group(1)
missing = [k for k in ['name', 'description', 'user-invocable'] if k + ':' not in fm]
if missing:
    print(f'WARNING: Missing frontmatter keys: {missing}')
else:
    print('Frontmatter structure OK')
"
```

If either validation fails, fix the syntax error and re-validate.

**Success criteria:** All files written, Python parses cleanly, frontmatter is valid.

---

### Step 7: Report

Tell the user:

1. **Files created** — list all files with their full paths
2. **Tool dependencies** — list MCP servers or CLI tools required (if tool mode is "preserve")
3. **Environment variables needed** — list each with a brief description
4. **Symlink command** (if not already in `~/.claude/skills/`):
   ```
   ln -sf {SAVE_LOCATION} ~/.claude/skills/{SKILL_NAME}
   ```
5. **How to invoke** — `/{SKILL_NAME}` or `/{SKILL_NAME} [arguments]`
6. **Suggest a test run** — recommend invoking the skill once to verify it works end-to-end

**Success criteria:** User has all information needed to use the new skill.
