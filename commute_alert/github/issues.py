import json
import os
from typing import Any, Dict, Optional

import requests

from commute_alert.errors import GitHubIssueError

STATE_MARKER_START = "<!-- commute-alert-state:start -->"
STATE_MARKER_END = "<!-- commute-alert-state:end -->"


def _get_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubIssueError("GITHUB_TOKEN is required")
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_api_url(path: str) -> str:
    repo = os.getenv("GITHUB_REPOSITORY")
    if not repo:
        raise GitHubIssueError("GITHUB_REPOSITORY is required")
    return f"https://api.github.com/repos/{repo}{path}"


def create_issue(title: str, body: str) -> int:
    response = requests.post(
        _repo_api_url("/issues"),
        headers=_get_headers(),
        json={"title": title, "body": body},
        timeout=20,
    )
    if response.status_code not in {200, 201}:
        raise GitHubIssueError(f"Create issue failed: {response.text}")
    return response.json()["number"]


def find_issue_number_by_title(title: str) -> Optional[int]:
    normalized = title.strip().lower()
    page = 1
    while True:
        response = requests.get(
            _repo_api_url("/issues"),
            headers=_get_headers(),
            params={"state": "all", "per_page": 100, "page": page},
            timeout=20,
        )
        if response.status_code != 200:
            raise GitHubIssueError(f"Fetch issues failed: {response.text}")
        issues = response.json()
        if not issues:
            return None
        for issue in issues:
            if "pull_request" in issue:
                continue
            issue_title = (issue.get("title") or "").strip().lower()
            if issue_title == normalized:
                return issue.get("number")
        page += 1


def get_issue_body(issue_number: int) -> str:
    response = requests.get(
        _repo_api_url(f"/issues/{issue_number}"),
        headers=_get_headers(),
        timeout=20,
    )
    if response.status_code != 200:
        raise GitHubIssueError(f"Fetch issue failed: {response.text}")
    return response.json().get("body") or ""


def update_issue_body(issue_number: int, body: str) -> None:
    response = requests.patch(
        _repo_api_url(f"/issues/{issue_number}"),
        headers=_get_headers(),
        json={"body": body},
        timeout=20,
    )
    if response.status_code != 200:
        raise GitHubIssueError(f"Update issue failed: {response.text}")


def post_comment(issue_number: int, body: str) -> None:
    response = requests.post(
        _repo_api_url(f"/issues/{issue_number}/comments"),
        headers=_get_headers(),
        json={"body": body},
        timeout=20,
    )
    if response.status_code not in {200, 201}:
        raise GitHubIssueError(f"Create comment failed: {response.text}")


def load_state_from_body(body: str) -> Dict[str, Any]:
    if STATE_MARKER_START not in body:
        return {}
    try:
        start = body.index(STATE_MARKER_START) + len(STATE_MARKER_START)
        end = body.index(STATE_MARKER_END)
    except ValueError:
        return {}
    state_json = body[start:end].strip()
    if not state_json:
        return {}
    try:
        return json.loads(state_json)
    except json.JSONDecodeError:
        return {}


def render_body_with_state(body: str, state: Dict[str, Any]) -> str:
    state_block = f"{STATE_MARKER_START}\n{json.dumps(state, indent=2)}\n{STATE_MARKER_END}"
    if STATE_MARKER_START in body and STATE_MARKER_END in body:
        start = body.index(STATE_MARKER_START)
        end = body.index(STATE_MARKER_END) + len(STATE_MARKER_END)
        return body[:start] + state_block + body[end:]
    if body and not body.endswith("\n"):
        body += "\n"
    return body + "\n" + state_block


def load_state(issue_number: int) -> Dict[str, Any]:
    body = get_issue_body(issue_number)
    return load_state_from_body(body)


def save_state(issue_number: int, state: Dict[str, Any]) -> None:
    body = get_issue_body(issue_number)
    updated = render_body_with_state(body, state)
    update_issue_body(issue_number, updated)


def bootstrap_issue(title: str, initial_state: Dict[str, Any]) -> int:
    body = render_body_with_state("", initial_state)
    return create_issue(title, body)


def load_local_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_local_state(path: str, state: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
