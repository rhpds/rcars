"""AgV access layer — creates and closes agnosticv PRs for the retirement pipeline.

Uses the GitHub App credential (RCARS_GITHUB_APP_*) to authenticate.
Supports rhpds/agnosticv, zt-rhelbu/agnosticv, and zt-ansiblebu/agnosticv.

RHDPCD-2103
"""
from __future__ import annotations

import base64
import json
import ssl
import time
import urllib.error
import urllib.request
from datetime import date

import jwt
import structlog

logger = structlog.get_logger(component="agv_access")

# v1 scope: these three repos only.  Partner RHDP is out of scope until there is
# a clearer path forward.
_NAMESPACE_REPO: dict[str, str] = {
    "zt-ansiblebu": "zt-ansiblebu/agnosticv",
    "zt-rhelbu": "zt-rhelbu/agnosticv",
}
_DEFAULT_REPO = "rhpds/agnosticv"
_GITHUB_API = "https://api.github.com"


# ── helpers ─────────────────────────────────────────────────────────────────


def _resolve_repo(base_name: str) -> tuple[str, str, str]:
    """Return (owner, repo_name, agv_path) for a CI base name.

    agv_path is the folder inside the repo, e.g. 'sandboxes-gpte/my-lab'.
    """
    agv_path = base_name.replace(".", "/", 1) if "." in base_name else base_name
    namespace = agv_path.split("/")[0] if "/" in agv_path else ""
    full_repo = _NAMESPACE_REPO.get(namespace, _DEFAULT_REPO)
    owner, repo_name = full_repo.split("/", 1)
    return owner, repo_name, agv_path


def _branch_name(base_name: str, jira_key: str) -> str:
    slug = base_name.replace(".", "-").replace("/", "-")
    today = date.today().strftime("%Y%m%d")
    return f"{slug}-{jira_key}-{today}"


def _get_installation_token(settings) -> str:
    """Exchange GitHub App credentials for a short-lived installation token."""
    if not settings.github_app_id or not settings.github_app_private_key:
        raise RuntimeError(
            "GitHub App not configured. Set RCARS_GITHUB_APP_ID, "
            "RCARS_GITHUB_APP_PRIVATE_KEY, and RCARS_GITHUB_APP_INSTALLATION_ID."
        )

    now = int(time.time())
    private_key = settings.github_app_private_key.replace("\\n", "\n")
    app_jwt = jwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": settings.github_app_id},
        private_key,
        algorithm="RS256",
    )

    token_url = (
        f"{_GITHUB_API}/app/installations"
        f"/{settings.github_app_installation_id}/access_tokens"
    )
    resp = _gh(app_jwt, "POST", token_url)
    return resp["token"]


def _gh(token: str, method: str, url: str, body: dict | None = None) -> dict:
    """Make a GitHub API request and return the parsed JSON response."""
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "rcars-agv-access/1.0",
        },
        method=method,
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {method} {url} → {exc.code}: {body_text}") from exc


def _get_default_branch_sha(token: str, owner: str, repo: str) -> str:
    data = _gh(token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/main")
    return data["object"]["sha"]


def _get_file(token: str, owner: str, repo: str, path: str) -> tuple[str, str]:
    """Return (content_str, file_sha) for an existing file."""
    data = _gh(token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}")
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


def _create_branch(token: str, owner: str, repo: str, branch: str, sha: str) -> None:
    _gh(token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/git/refs", {
        "ref": f"refs/heads/{branch}",
        "sha": sha,
    })


def _update_file(
    token: str, owner: str, repo: str, path: str,
    content: str, file_sha: str, branch: str, message: str,
) -> None:
    _gh(token, "PUT", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}", {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": file_sha,
        "branch": branch,
    })


def _delete_file(
    token: str, owner: str, repo: str, path: str,
    file_sha: str, branch: str, message: str,
) -> None:
    _gh(token, "DELETE", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}", {
        "message": message,
        "sha": file_sha,
        "branch": branch,
    })


def _create_pr(
    token: str, owner: str, repo: str,
    branch: str, title: str, body: str,
) -> dict:
    return _gh(token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/pulls", {
        "title": title,
        "body": body,
        "head": branch,
        "base": "main",
    })


# ── public API ───────────────────────────────────────────────────────────────


def create_notice_pr(settings, base_name: str, jira_key: str, workflow: dict) -> dict:
    """Create the retirement notice PR on agnosticv.

    Prepends the AsciiDoc retirement notice block to description.adoc and
    opens a PR against main.

    Returns {pr_url, pr_number, repo}.
    """
    from rcars.services.jira import build_retirement_adoc_notice

    owner, repo_name, agv_path = _resolve_repo(base_name)
    branch = _branch_name(base_name, jira_key)
    adoc_notice = build_retirement_adoc_notice(workflow)
    desc_path = f"{agv_path}/description.adoc"

    logger.info("agv_notice_pr_start", base_name=base_name, repo=f"{owner}/{repo_name}", branch=branch)

    token = _get_installation_token(settings)
    main_sha = _get_default_branch_sha(token, owner, repo_name)
    _create_branch(token, owner, repo_name, branch, main_sha)

    existing_content, file_sha = _get_file(token, owner, repo_name, desc_path)
    new_content = adoc_notice + "\n\n" + existing_content

    _update_file(
        token, owner, repo_name, desc_path, new_content, file_sha, branch,
        f"retire: add retirement notice for {base_name} ({jira_key})",
    )

    pr = _create_pr(
        token, owner, repo_name, branch,
        title=f"retire: {base_name} — retirement notice ({jira_key})",
        body=(
            f"Retirement notice PR for **{base_name}**.\n\n"
            f"Jira: [{jira_key}](https://redhat.atlassian.net/browse/{jira_key})\n\n"
            "Adds the AsciiDoc retirement notice block to `description.adoc`. "
            "Review the date placeholder and replace `[DATE TBD]` with the actual retirement date before merging.\n\n"
            "---\n"
            "_Generated by RCARS agv-retire integration — RHDPCD-2103_"
        ),
    )

    logger.info("agv_notice_pr_created", pr_url=pr["html_url"], pr_number=pr["number"])
    return {
        "pr_url": pr["html_url"],
        "pr_number": pr["number"],
        "repo": f"{owner}/{repo_name}",
    }


def create_retire_pr(settings, base_name: str, jira_key: str) -> dict:
    """Create the removal PR on agnosticv.

    Deletes prod.yaml from the CI folder, removing the item from the prod
    catalog stage.  A human reviewer must approve and merge.

    Returns {pr_url, pr_number, repo}.
    """
    owner, repo_name, agv_path = _resolve_repo(base_name)
    branch = _branch_name(base_name, jira_key) + "-retire"
    prod_path = f"{agv_path}/prod.yaml"

    logger.info("agv_retire_pr_start", base_name=base_name, repo=f"{owner}/{repo_name}", branch=branch)

    token = _get_installation_token(settings)
    main_sha = _get_default_branch_sha(token, owner, repo_name)
    _create_branch(token, owner, repo_name, branch, main_sha)

    _, file_sha = _get_file(token, owner, repo_name, prod_path)
    _delete_file(
        token, owner, repo_name, prod_path, file_sha, branch,
        f"retire: remove {base_name} from prod catalog ({jira_key})",
    )

    pr = _create_pr(
        token, owner, repo_name, branch,
        title=f"retire: remove {base_name} from prod ({jira_key})",
        body=(
            f"Removal PR for **{base_name}**.\n\n"
            f"Jira: [{jira_key}](https://redhat.atlassian.net/browse/{jira_key})\n\n"
            "Deletes `prod.yaml`, removing the item from the prod catalog stage. "
            "Once merged, the item will disappear from Babylon on the next catalog sync "
            "and RCARS will mark it retired automatically via soft-delete.\n\n"
            "---\n"
            "_Generated by RCARS agv-retire integration — RHDPCD-2103_"
        ),
    )

    logger.info("agv_retire_pr_created", pr_url=pr["html_url"], pr_number=pr["number"])
    return {
        "pr_url": pr["html_url"],
        "pr_number": pr["number"],
        "repo": f"{owner}/{repo_name}",
    }


def close_pr(settings, repo_full: str, pr_number: int) -> None:
    """Close an open agnosticv PR (e.g. on retirement cancellation)."""
    owner, repo_name = repo_full.split("/", 1)
    token = _get_installation_token(settings)
    _gh(token, "PATCH", f"{_GITHUB_API}/repos/{owner}/{repo_name}/pulls/{pr_number}", {
        "state": "closed",
    })
    logger.info("agv_pr_closed", repo=repo_full, pr_number=pr_number)
