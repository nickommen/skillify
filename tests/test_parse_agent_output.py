"""Tests for parse_agent_output.py."""

from scripts.parse_agent_output import parse_agent_output


class TestParseAgentOutput:
    def test_happy_path(self):
        text = """Some preamble text.

## FILE: scripts/run.py

```python
#!/usr/bin/env python3
print("hello")
```

## FILE: SKILL.md

```markdown
---
name: test-skill
---
# Test Skill
```
"""
        files = parse_agent_output(text)
        assert len(files) == 2

        assert files[0]["path"] == "scripts/run.py"
        assert 'print("hello")' in files[0]["content"]
        assert files[0]["size"] > 0

        assert files[1]["path"] == "SKILL.md"
        assert "name: test-skill" in files[1]["content"]

    def test_no_headers(self):
        files = parse_agent_output("Just some plain text without any file headers.")
        assert files == []

    def test_empty_input(self):
        assert parse_agent_output("") == []

    def test_no_fence(self):
        text = """## FILE: notes.txt

This content has no fenced code block.
Just plain text.
"""
        files = parse_agent_output(text)
        assert len(files) == 1
        assert files[0]["path"] == "notes.txt"
        assert "plain text" in files[0]["content"]

    def test_multiple_files(self):
        text = """## FILE: a.py

```python
a = 1
```

## FILE: b.py

```python
b = 2
```

## FILE: c.py

```python
c = 3
```
"""
        files = parse_agent_output(text)
        assert len(files) == 3
        assert files[0]["path"] == "a.py"
        assert files[1]["path"] == "b.py"
        assert files[2]["path"] == "c.py"

    def test_path_whitespace_stripped(self):
        text = """## FILE:   scripts/run.py

```python
x = 1
```
"""
        files = parse_agent_output(text)
        assert files[0]["path"] == "scripts/run.py"

    def test_size_matches_content(self):
        text = """## FILE: test.py

```python
hello = "world"
```
"""
        files = parse_agent_output(text)
        assert files[0]["size"] == len(files[0]["content"])

    def test_preserves_internal_newlines(self):
        text = """## FILE: multi.py

```python
line1 = 1

line3 = 3
```
"""
        files = parse_agent_output(text)
        assert "\n\n" in files[0]["content"]

    def test_fence_language_variants(self):
        text = """## FILE: config.json

```json
{"key": "value"}
```
"""
        files = parse_agent_output(text)
        assert len(files) == 1
        assert '"key"' in files[0]["content"]

    def test_content_between_headers_without_fence(self):
        text = """## FILE: README.md

# My Project

This is the readme content.

## FILE: CHANGELOG.md

```markdown
## v1.0
- Initial release
```
"""
        files = parse_agent_output(text)
        assert len(files) == 2
        assert files[0]["path"] == "README.md"
        assert "My Project" in files[0]["content"]
        assert files[1]["path"] == "CHANGELOG.md"
