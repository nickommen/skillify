---
name: skillify
description: >
  Convert a Claude Code conversation into a deterministic Python-scripted skill.
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

- You MUST use the AskUserQuestion tool for all user input — confirmations, choices, and decisions. Do NOT ask questions as plain text in your response. The built-in "Other" option handles free-text fallback. If AskUserQuestion is unavailable, fall back to asking as plain text as a last resort.
- Generated SKILL.md files must stay under 500 lines. Put large references in separate files.
- Generated skill descriptions must state both what the skill does AND when to use it.
- Generated skills must list all tools they call in `allowed-tools`.
- Preserve the tools from the source conversation by default. Only convert MCP to REST if the user explicitly requests standalone mode.
- Keep Bash commands simple to avoid Claude Code security prompts. Specifically: no multi-line commands, no heredocs, no inline `python3 -c`, no `$(cmd)` in file paths or arguments (capture to a variable first), and no `#` characters in quoted strings. If complex logic is needed, write it to a temporary Python script and execute that.
- Generated skills must never write files under `~/.claude/` or `${CLAUDE_SKILL_DIR}/`. Use `/tmp/{skill-name}/` for transient intermediate files. Write final output to the current working directory (`$PWD`).
- Follow the Procedure steps exactly in order. Do NOT read other skills for "patterns", explore the filesystem for examples, infer paths from the environment, or skip steps. All guidance for generating skills is in the procedure and the generation prompt template. The save location MUST come from the Step 3 interview — never invent or guess a path.

## Procedure

### Step 1: Identify the Conversation

Resolve the source conversation JSONL file. Check these modes **in order** — use the FIRST one that matches and do NOT fall through to later modes.

**Mode A — "this" (auto-select most recent session):**
If `$ARGUMENTS` contains "this", "current", or "this conversation": auto-select the most recent session for the current project directory. Do NOT show a picker.

```
python3 ${CLAUDE_SKILL_DIR}/scripts/find_session.py --mode recent --project-dir "$PWD"
```
Parse the JSON output for the `path` field. If not found (exit code 1), fall through to Mode D (interactive picker).

**Mode B — Explicit session ID:**
Only if `$ARGUMENTS` contains a UUID (pattern: `[0-9a-f-]{36}`):
```
python3 ${CLAUDE_SKILL_DIR}/scripts/find_session.py --mode uuid --session-id "$ARGUMENTS"
```
Parse the JSON output for the `path` field. If not found (exit code 1), tell the user and ask for a different session ID.

**Mode C — Named session (from /rename):**
Only if `$ARGUMENTS` contains text that is NOT empty, NOT "this"/"current", and NOT a UUID:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/find_session.py --mode name --session-name "$ARGUMENTS"
```
Parse the JSON output for the `path` field. If not found (exit code 1), fall through to Mode D (interactive picker).

**Mode D — Interactive picker:**
If `$ARGUMENTS` is empty, blank, or unset — OR if Mode A/C fell through because no session was found:
1. List recent sessions:
   ```
   python3 ${CLAUDE_SKILL_DIR}/scripts/find_session.py --mode list
   ```
   Parse the JSON array output — each entry has `session_id`, `timestamp`, `display`, and `project` fields.
2. Present the list via AskUserQuestion. Format each option as `{timestamp} [{project}] {display}` so the user can identify sessions by time, project directory, and description.
3. Locate the selected session's JSONL file:
   ```
   python3 ${CLAUDE_SKILL_DIR}/scripts/find_session.py --mode uuid --session-id "{SELECTED_SESSION_ID}"
   ```

**Success criteria:** A valid JSONL file path is identified.

---

### Step 2: Parse Conversation

Run the conversation parser to extract the workflow manifest:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/parse_conversation.py "{JSONL_PATH}" > /tmp/skillify-manifest.json
```

If the parser fails, show the error and stop.

Read `/tmp/skillify-manifest.json` to get the full manifest.

**Success criteria:** Manifest JSON is valid and contains at least 1 tool call.

---

### Step 3: Load Config, Present Summary, and Interview

Read the user's skillify config if it exists at `~/.claude/skillify.json`. If the file does not exist, use empty defaults.

Use config values as defaults in the interview. If no config exists, use built-in defaults:
- `default_save_location`: `~/skills`

Present the manifest summary to the user:
- Total messages, tool calls, files written
- Tools used (grouped by category)
- API patterns detected (Jira JQL, GitHub CLI, etc.)
- Environment variables needed
- Corrections detected (user redirections, with scores)
- Whether the conversation already produced scripts or a skill

Then conduct a MANDATORY interview via AskUserQuestion. Do NOT skip this step. Do NOT proceed to Step 4 without completing Round 1. Every question below MUST be asked and answered before continuing.

**Round 1 (REQUIRED):** Ask all of these in a single AskUserQuestion with multiple questions:
- Suggest a skill name based on the workflow. Let the user confirm or rename.
- Suggest a one-line description (must include what it does AND when to use it). Let the user confirm or edit.
- Ask where to save the skill. Do NOT save directly into `~/.claude/` — writes there trigger sensitive-file permission prompts.
  - **Personal skills directory** (Recommended) — save to `{config.default_save_location}/{name}/`. A symlink to `~/.claude/skills/{name}` will be created in the final step for discovery.
  - **This repo** (`.claude/skills/{name}/`) — for repo-specific workflows, discovered automatically (no symlink needed)
  - **Custom path** — let the user specify any directory via "Other" (e.g., a shared skills repo). A symlink will be created for discovery.
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

Create the skill directory structure and write each file from the confirmed file list to its correct location. Ensure `{SAVE_LOCATION}/scripts/` exists.

Validate the generated skill:
```
python3 ${CLAUDE_SKILL_DIR}/scripts/validate_skill.py "{SAVE_LOCATION}"
```
Parse the JSON output. If `valid` is false, fix the errors listed in the `errors` array and re-validate.

If either validation fails, fix the syntax error and re-validate.

**Success criteria:** All files written, Python parses cleanly, frontmatter is valid.

---

### Step 7: Report

Tell the user:

1. **Files created** — list all files with their full paths
2. **Tool dependencies** — list MCP servers or CLI tools required (if tool mode is "preserve")
3. **Environment variables needed** — list each with a brief description
4. **Install the skill** — if the save location is NOT `.claude/skills/{name}/` in the current repo, create a symlink for discovery:
   ```
   ln -sf {SAVE_LOCATION} ~/.claude/skills/{SKILL_NAME}
   ```
   If the skill was saved to `.claude/skills/{name}/` in the current repo, skip the symlink — it is discovered automatically.
5. **How to invoke** — `/{SKILL_NAME}` or `/{SKILL_NAME} [arguments]`
6. **Suggest a test run** — recommend invoking the skill once to verify it works end-to-end

**Success criteria:** User has all information needed to use the new skill.
