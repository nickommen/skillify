# REST API Reference (Standalone Mode)

This reference is injected into the generation prompt only when the user selects standalone mode. It provides endpoint mappings for common MCP tools so the generation Agent can produce equivalent `urllib.request` calls.

---

## Jira Cloud REST API v2

Base URL: `{JIRA_URL}/rest/api/2`

Authentication: Basic auth — `base64(email:api_token)`

```python
import base64, os
creds = base64.b64encode(f"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_API_TOKEN']}".encode()).decode()
headers = {"Authorization": f"Basic {creds}", "Content-Type": "application/json", "Accept": "application/json"}
```

### Common Endpoints

| MCP Tool | REST Endpoint | Method | Notes |
|---|---|---|---|
| `searchJiraIssuesUsingJql` | `/rest/api/2/search` | POST | Body: `{"jql": "...", "startAt": 0, "maxResults": 50, "fields": [...]}`. Paginate with `startAt`. |
| `getJiraIssue` | `/rest/api/2/issue/{issueIdOrKey}` | GET | Query params: `?fields=summary,status,assignee` |
| `createJiraIssue` | `/rest/api/2/issue` | POST | Body: `{"fields": {"project": {"key": "PROJ"}, "issuetype": {"name": "Task"}, "summary": "..."}}` |
| `editJiraIssue` | `/rest/api/2/issue/{issueIdOrKey}` | PUT | Body: `{"fields": {...}}` |
| `transitionJiraIssue` | `/rest/api/2/issue/{issueIdOrKey}/transitions` | POST | Body: `{"transition": {"id": "31"}}`. GET first to list available transitions. |
| `addCommentToJiraIssue` | `/rest/api/2/issue/{issueIdOrKey}/comment` | POST | Body: `{"body": "..."}` |
| `getTransitionsForJiraIssue` | `/rest/api/2/issue/{issueIdOrKey}/transitions` | GET | Returns `{"transitions": [...]}` |

### Pagination Pattern

```python
start_at = 0
max_results = 50
all_issues = []
while True:
    body = json.dumps({"jql": jql, "startAt": start_at, "maxResults": max_results, "fields": fields}).encode()
    req = urllib.request.Request(f"{base_url}/rest/api/2/search", data=body, headers=headers, method="POST")
    resp = json.loads(urllib.request.urlopen(req).read())
    all_issues.extend(resp["issues"])
    if start_at + max_results >= resp["total"]:
        break
    start_at += max_results
```

---

## GitHub REST API v3

Base URL: `https://api.github.com`

Authentication: Token — `Authorization: Bearer {GITHUB_TOKEN}`

Alternatively, use the `gh` CLI which handles auth automatically.

### Common Endpoints

| MCP Tool / CLI | REST Endpoint | Method | Notes |
|---|---|---|---|
| `gh issue list` | `/repos/{owner}/{repo}/issues` | GET | Query: `?state=open&labels=bug&per_page=100` |
| `gh issue view` | `/repos/{owner}/{repo}/issues/{number}` | GET | |
| `gh issue create` | `/repos/{owner}/{repo}/issues` | POST | Body: `{"title": "...", "body": "...", "labels": [...]}` |
| `gh pr list` | `/repos/{owner}/{repo}/pulls` | GET | Query: `?state=open&per_page=100` |
| `gh pr view` | `/repos/{owner}/{repo}/pulls/{number}` | GET | |
| `gh pr create` | `/repos/{owner}/{repo}/pulls` | POST | Body: `{"title": "...", "body": "...", "head": "branch", "base": "main"}` |
| `gh api` | (direct) | varies | The `gh api` command already hits REST endpoints directly |

### Pagination Pattern

```python
page = 1
per_page = 100
all_items = []
while True:
    req = urllib.request.Request(f"{base_url}/repos/{owner}/{repo}/issues?state=open&page={page}&per_page={per_page}", headers=headers)
    resp = json.loads(urllib.request.urlopen(req).read())
    if not resp:
        break
    all_items.extend(resp)
    page += 1
```

---

## Confluence Cloud REST API v2

Base URL: `https://{site}.atlassian.net/wiki/api/v2`

Authentication: Same as Jira (basic auth with email + API token).

### Common Endpoints

| MCP Tool | REST Endpoint | Method | Notes |
|---|---|---|---|
| `getConfluencePage` | `/api/v2/pages/{pageId}` | GET | Query: `?body-format=storage` for HTML body |
| `createConfluencePage` | `/api/v2/pages` | POST | Body: `{"spaceId": "...", "title": "...", "body": {"representation": "storage", "value": "..."}}` |
| `updateConfluencePage` | `/api/v2/pages/{pageId}` | PUT | Requires current version number in body |
| `searchConfluenceUsingCql` | `/wiki/rest/api/content/search` | GET | Query: `?cql=...&limit=25` (v1 endpoint) |
| `getConfluenceSpaces` | `/api/v2/spaces` | GET | Query: `?limit=25` |

---

## Google Workspace

Google APIs require OAuth2 tokens and have complex auth flows. For standalone mode with Google Workspace tools, recommend that the generated script use a service account JSON key file or pre-authenticated token stored in an environment variable.

Base URLs:
- Docs: `https://docs.googleapis.com/v1/documents/{documentId}`
- Drive: `https://www.googleapis.com/drive/v3/files`
- Sheets: `https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}`

Authentication: `Authorization: Bearer {GOOGLE_ACCESS_TOKEN}`

Due to the complexity of Google OAuth2, generated standalone scripts should note that the user needs to provide a valid access token. Full OAuth2 implementation is beyond the scope of a stdlib-only script.

---

## General Patterns

### HTTP Request Helper

```python
def api_request(url, method="GET", data=None, headers=None):
    if data and isinstance(data, dict):
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        raise
```
