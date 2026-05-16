You are generating a new Claude Code skill from a workflow manifest — a structured summary of a conversation where the user iterated on automating a task.

Your goal: produce **deterministic Python scripts** that capture all repeatable work, wrapped in a **minimal SKILL.md** that orchestrates them. AI should only be involved on future runs for semantic grouping, error diagnosis, or natural language summarization.

## Workflow Manifest

{WORKFLOW_MANIFEST}

## Skill Name

`{SKILL_NAME}`

## Save Location

`{SAVE_LOCATION}`

## User Corrections (encode as Rules)

These are places where the user redirected the approach during the original conversation. Encode each as a hard rule in the generated SKILL.md so the mistake is never repeated:

{CORRECTIONS}

## Existing Scripts (if any)

{EXISTING_SCRIPTS}

## Tool Mode

**Mode:** `{TOOL_MODE}`

- `preserve` (default): the generated skill uses the same MCP tools and CLIs from the source conversation. MCP tool calls become `allowed-tools` entries in the SKILL.md frontmatter with fixed parameters in the procedure.
- `standalone`: all tool calls are converted to REST API calls using `urllib.request`. No MCP dependency.

**Tool dependencies (for preserve mode):**

{TOOL_DEPENDENCIES}

**REST API mappings (for standalone mode only):**

{MCP_API_MAPPINGS}

## Preconditions

{PRECONDITIONS}

## Idempotency

{IDEMPOTENCY}

## Escalation Rules

{ESCALATION_RULES}

---

## Generation Instructions

### Python Script Requirements

1. **Stdlib-only** — no pip dependencies. Use `json`, `os`, `re`, `sys`, `urllib.request`, `urllib.parse`, `collections`, `datetime`, etc.
2. **Credential validation** — check all required environment variables at startup, print clear error messages to stderr if missing, and exit 1.
3. **Output discipline** — structured output (JSON or markdown) goes to stdout. Progress messages and diagnostics go to stderr.
4. **Paginated API calls** — if the workflow queries APIs that return paginated results, implement pagination (e.g., Jira's `startAt` + `maxResults`).
5. **Constants at the top** — extract project keys, component names, API base URLs, JQL templates, and other configuration to named constants at the top of the script.
6. **No runtime discovery** — hard-code field names, project keys, and query parameters. The skill should not need to discover these at runtime.
7. **Tool handling** — depends on tool mode:
   - **Preserve mode:** Python scripts handle data transformation, formatting, and report generation. The SKILL.md procedure calls MCP tools and CLIs directly (the same ones used in the source conversation). Scripts receive tool output via stdin or file arguments.
   - **Standalone mode:** Replace all MCP tool calls with equivalent REST API calls using `urllib.request`. Use the REST API mappings provided above for endpoint details.
8. **Error handling** — catch HTTP errors, parse error responses, print actionable messages to stderr.

### validators.py Requirements

Always generate a `scripts/validators.py` with:

1. **`check_preconditions()`** — validates all preconditions before the main script runs:
   - Required environment variables exist and are non-empty
   - Required CLI tools are available (`shutil.which`)
   - Required files or directories exist
   - Any workflow-specific preconditions from the interview
2. **`validate_output(output_path)`** — basic output validation:
   - File exists and is non-empty
   - Expected format (JSON is valid, markdown has content, etc.)
3. **Exit with clear error messages** if any check fails. Each check should print exactly what's wrong and how to fix it.

The main script should call `check_preconditions()` at startup before doing any real work.

### skill.schema.json Requirements

Generate `skill.schema.json` when the skill takes arguments or produces structured output. This file defines the skill's interface for composability — other skills and LLM sessions use it to understand what this skill accepts and returns.

Schema structure:
```json
{
  "name": "skill-name",
  "version": "1.0.0",
  "inputs": {
    "arguments": [
      {"name": "arg-name", "type": "string", "required": true, "description": "..."}
    ],
    "environment": [
      {"name": "ENV_VAR", "required": true, "description": "..."}
    ]
  },
  "outputs": {
    "format": "markdown|json|text",
    "location": "stdout|file",
    "file_pattern": "output/skill-name-{timestamp}.md"
  }
}
```

Skip this file only for skills with no arguments and trivial output.

### SKILL.md Requirements

1. **Stay under 500 lines.** Put large references in separate files. Challenge every line: "Does Claude really need this?"
2. **YAML frontmatter** with:
   - `name`: lowercase letters, numbers, hyphens only (max 64 chars)
   - `description`: must include both **what it does** AND **when to use it**. Be specific — Claude uses fuzzy matching on description to choose between 100+ skills.
   - `user-invocable: true`
   - `context: fork`
   - `allowed-tools`: list every tool the skill calls. Use prefix patterns like `Bash(gh *)` for CLI tools. Include `Skill(other-skill)` if composing with other skills.
   - `argument-hint`: show expected args in autocomplete (e.g., `"[issue-number]"`)
3. **Minimal orchestration** — the procedure should be:
   - Step 1: Run validators, create output directory, run the Python script, capturing output to a timestamped file
   - Step 2: Read and present the output
   - Step 3: Provide a brief summary with key metrics
4. **Per-step success criteria** — each step must state what proves it succeeded
5. **Rules section** — encode user corrections as hard rules that must be followed
6. **Agent delegation** — only include an Agent step if the original workflow genuinely needed semantic grouping or natural language summarization. If the workflow is purely data gathering + transformation + reporting, no Agent is needed.
7. **Human checkpoints** — add confirmation steps before any write/modify operations (creating issues, sending messages, etc.). Use AskUserQuestion to present choices rather than asking for free-text input.
8. **Environment variables** — list all required env vars in a Prerequisites section within the procedure
9. **Preconditions** — document any preconditions (clean git repo, specific files present, etc.) in a Prerequisites section
10. **Idempotency** — if the skill is safe to run multiple times, state this. If not, document what changes on re-run.
11. **Escalation** — document when the skill should stop and ask for help vs. retry automatically. Default: stop and ask on any error.
12. **Predictable output** — output format must be consistent (always JSON to stdout, or always markdown to a file) so downstream consumers can parse it.
13. **Error recovery with AskUserQuestion** — when a script fails during execution, present recovery options via AskUserQuestion rather than asking the user to type instructions. Standard options: "Retry with same params" / "Retry with modified params" / "Skip this step" / "Abort"

### README.md Requirements

1. One-paragraph description of what the skill does
2. **Trigger** section — how to invoke (`/skill-name`) and any natural language triggers
3. **How It Works** — numbered list of technical steps
4. **Usage** — example invocation(s)
5. **Prerequisites** — environment variables needed, with instructions on how to obtain them
6. **Setup** — symlink command
7. **Composability** — if the skill produces structured output, document the output format and how other skills can consume it

---

## Output Format

Output each file in a clearly marked section. The file paths are relative to the skill directory.

## FILE: scripts/{script_name}.py

```python
[complete script content]
```

## FILE: scripts/validators.py

```python
[precondition checks and output validation]
```

## FILE: SKILL.md

```markdown
[complete SKILL.md content — must be under 500 lines]
```

## FILE: README.md

```markdown
[complete README.md content]
```

## FILE: skill.schema.json

```json
[input/output schema — only if the skill takes arguments or produces structured output]
```

---

## Rules

- The generated skill must require MINIMAL AI on future runs — all API calls, data transforms, and report formatting go in Python
- Extract ALL constants and configuration to the top of scripts
- Make JQL queries, API endpoints, and field names explicit — never discover at runtime
- If the manifest shows the conversation already produced a working Python script (in `existing_scripts`), adapt and improve it rather than rewriting from scratch
- Self-contained stdlib-only Python, credentials validated upfront, paginated API calls, progress on stderr, structured output on stdout
- Use `$CLAUDE_SKILL_DIR` to reference files relative to the skill directory in SKILL.md
- **Preserve source tools by default.** MCP tools with fixed inputs are already deterministic — only convert to REST when tool mode is "standalone"
- **Generated skills are reusable capabilities.** Other LLM sessions can invoke the skill, chain its output, or use it as a building block. Design the interface (description, schema, output format) accordingly.
- **Use AskUserQuestion for user interaction** — during recovery, confirmations, and choices. The built-in "Other" option handles free-text fallback.
- **validators.py runs first** — precondition failures should be caught before any real work starts, with clear messages about what's missing and how to fix it
- **No inline bash complexity in SKILL.md** — never use `python3 -c "..."` with embedded code, multi-line heredocs, or complex shell pipelines in SKILL.md code blocks. These trigger Claude Code security prompts ("expansion obfuscation", "cannot be statically analyzed") that interrupt execution. Instead, put all logic in standalone Python scripts under `scripts/` and call them with simple one-line commands. Keep bash code blocks to single-line invocations like `python3 ${CLAUDE_SKILL_DIR}/scripts/foo.py "arg"`.
