# skillify

Convert a Claude Code conversation — where you iterated on automating a task — into a deterministic Python-scripted skill. Skillify parses the conversation JSONL, extracts the workflow (API calls, data transforms, output format), and generates Python scripts + a SKILL.md wrapper. Future runs of the generated skill are deterministic, using AI only for error recovery and semantic summarization.

## Installation

```bash
git clone https://github.com/nickommen/skillify.git
cd skillify
./install.sh
```

Or manually:

```bash
git clone https://github.com/nickommen/skillify.git
ln -sf "$(pwd)/skillify" ~/.claude/skills/skillify
```

After installation, `/skillify` will be available in Claude Code.

## Prerequisites

- Python 3.12+
- No pip dependencies — stdlib only
- Claude Code with skill support

## Usage

```bash
# Skillify the current conversation
/skillify this

# Skillify a specific past conversation by session ID
/skillify 15555f6f-ed1d-47fb-b542-efdaff259864

# Browse recent conversations and pick one
/skillify
```

Also triggers on natural language: "turn this into a skill", "make this a skill", "create a skill from this conversation", "convert this to a skill"

## How It Works

1. **Identify** the source conversation — current session, explicit session ID, or interactive picker from recent history
2. **Parse** the conversation JSONL into a compact workflow manifest using `parse_conversation.py`
3. **Supplement** with git state and project type detection for additional context
4. **Interview** the user to confirm skill name, description, save location, tool mode, and workflow steps. For non-trivial workflows, also captures preconditions, idempotency, and escalation rules.
5. **Check** if the conversation already produced Python scripts — reuse if possible
6. **Generate** Python scripts, validators, and SKILL.md via an Agent reading the manifest
7. **Preview** generated files for user confirmation before writing
8. **Validate** generated Python syntax and YAML frontmatter
9. **Report** created files, tool dependencies, env vars needed, and how to invoke

## Configuration

Optionally create `~/.claude/skillify.json` to set defaults:

```json
{
  "default_save_location": "~/.claude/skills",
  "symlink_base": "~/.claude/skills",
  "author": ""
}
```

All fields are optional. Without a config file, skillify uses sensible defaults.

## Generated Skill Structure

When skillify generates a new skill, it creates:

```text
skill-name/
  SKILL.md              # Orchestration procedure (under 500 lines)
  README.md             # Documentation and setup instructions
  scripts/
    run.py              # Main deterministic script (stdlib-only)
    validators.py       # Precondition checks and output validation
  skill.schema.json     # Input/output schema (when applicable)
  output/               # Timestamped run results (gitignored)
```

Generated skills are designed to be:

- **Deterministic** — Python scripts handle all API calls, data transforms, and formatting
- **Composable** — other LLM sessions can invoke the skill via `/skill-name` or the `Skill` tool
- **Self-validating** — `validators.py` checks preconditions before execution

## Tool Modes

By default, generated skills **preserve the tools** used in the source conversation (MCP tools, CLIs like `gh`, etc.). This is the recommended approach — MCP tools with fixed inputs are already deterministic.

Optionally, you can choose **standalone mode** during the interview, which converts all tool calls to REST API calls using `urllib.request`. This removes MCP dependencies but adds complexity (auth handling, pagination, URL construction).

## Project Structure

```text
skillify/
  SKILL.md                          # Skillify's own skill definition
  scripts/
    parse_conversation.py           # JSONL conversation parser
    parse_agent_output.py           # Agent output file extractor
    find_session.py                 # Session JSONL resolution (recent/uuid/list)
    gather_context.py               # Project context gathering (git, project type)
    validate_skill.py               # Generated skill validation (syntax, frontmatter)
  prompts/
    generate_skill.md               # Generation agent prompt template
    rest_api_reference.md           # REST endpoint reference (standalone mode)
  tests/
    test_parse_conversation.py      # Parser tests
    test_parse_agent_output.py      # Agent output parser tests
    test_find_session.py            # Session resolution tests
    test_gather_context.py          # Context gathering tests
    test_validate_skill.py          # Skill validation tests
    fixtures/                       # Synthetic test data
  install.sh                        # One-line installer
```

## Development

```bash
uv venv .venv && source .venv/bin/activate
uv sync
pytest --cov             # tests + coverage
ruff check scripts/ tests/  # lint
```

## License

MIT
