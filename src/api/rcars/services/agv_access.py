"""AgV access layer — GitHub operations for agnosticv repos.

Uses GitHub App credentials (RCARS_GITHUB_APP_*) to authenticate.
Supports rhpds/agnosticv, zt-rhelbu/agnosticv, and zt-ansiblebu/agnosticv.

All public functions are async. Curator/admin use only — agnosticv repos
contain credentials and must never be exposed through user-facing chat.

RHDPCD-2103
"""
from __future__ import annotations

import base64
import re
import time
from datetime import date

import httpx
import jwt
import structlog

logger = structlog.get_logger(component="agv_access")

_NAMESPACE_REPO: dict[str, str] = {
    "zt-ansiblebu": "zt-ansiblebu/agnosticv",
    "zt-rhelbu": "zt-rhelbu/agnosticv",
}
_DEFAULT_REPO = "rhpds/agnosticv"
_GITHUB_API = "https://api.github.com"
_GH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "rcars-agv-access/1.0",
}
_TIMEOUT = httpx.Timeout(30.0)

_NOTICE_PATTERN = re.compile(
    r"\[IMPORTANT\]\n\.RETIREMENT NOTICE\n\*{4}\n.+?\n\*{4}\n*",
    re.DOTALL,
)


class GitHubAPIError(Exception):
    """Raised when a GitHub API call returns a non-success status."""

    def __init__(self, method: str, url: str, status_code: int, body: str):
        self.method = method
        self.url = url
        self.status_code = status_code
        self.body = body
        super().__init__(f"GitHub API {method} {url} → {status_code}: {body}")


# ── helpers ─────────────────────────────────────────────────────────────────


def _normalize_for_match(name: str) -> str:
    """Lowercase and collapse hyphens/underscores for case- and separator-insensitive matching."""
    return name.lower().replace("-", "_")


async def _verify_agv_path(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, agv_path: str,
) -> str:
    """Resolve the actual agnosticv path by listing the namespace directory.

    Babylon normalizes directory names to lowercase hyphens, but the repo
    can have underscores, hyphens, or uppercase. List the namespace dir
    and match case-/separator-insensitively.
    """
    parts = agv_path.split("/", 1)
    if len(parts) != 2:
        raise GitHubAPIError(
            "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{agv_path}",
            404, f"CI path has no namespace: {agv_path}",
        )
    ns_guess, ci_guess = parts
    ns_norm = _normalize_for_match(ns_guess)
    ci_norm = _normalize_for_match(ci_guess)

    # Resolve the namespace directory
    try:
        top_entries = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/")
    except GitHubAPIError:
        raise GitHubAPIError(
            "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{agv_path}",
            404, f"Cannot list repo root for {owner}/{repo}",
        )
    ns_dir = None
    for entry in top_entries:
        if entry.get("type") == "dir" and _normalize_for_match(entry["name"]) == ns_norm:
            ns_dir = entry["name"]
            break
    if not ns_dir:
        raise GitHubAPIError(
            "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{agv_path}",
            404, f"Namespace directory not found for {ns_guess}",
        )

    # Resolve the CI directory within the namespace
    try:
        ns_entries = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{ns_dir}")
    except GitHubAPIError:
        raise GitHubAPIError(
            "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{agv_path}",
            404, f"Cannot list namespace directory {ns_dir}",
        )
    for entry in ns_entries:
        if entry.get("type") == "dir" and _normalize_for_match(entry["name"]) == ci_norm:
            resolved = f"{ns_dir}/{entry['name']}"
            logger.debug("agv_path_resolved", input=agv_path, resolved=resolved)
            return resolved

    raise GitHubAPIError(
        "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{agv_path}",
        404, f"CI directory not found in {ns_dir}/ matching {ci_guess}",
    )


_STAGE_SUFFIXES = (".prod", ".dev", ".event", ".test")


def _resolve_repo(base_name: str) -> tuple[str, str, str]:
    """Return (owner, repo_name, agv_path) for a CI base name."""
    agv_path = base_name.replace(".", "/", 1) if "." in base_name else base_name
    for suffix in _STAGE_SUFFIXES:
        if agv_path.endswith(suffix):
            agv_path = agv_path[:-len(suffix)]
            break
    namespace = agv_path.split("/")[0] if "/" in agv_path else ""
    full_repo = _NAMESPACE_REPO.get(namespace, _DEFAULT_REPO)
    owner, repo_name = full_repo.split("/", 1)
    return owner, repo_name, agv_path


def _branch_name(base_name: str, jira_key: str) -> str:
    slug = base_name.replace(".", "-").replace("/", "-")
    today = date.today().strftime("%Y%m%d")
    return f"{slug}-{jira_key}-{today}"


async def _gh(
    client: httpx.AsyncClient, token: str, method: str, url: str,
    body: dict | None = None,
) -> dict:
    """Make a GitHub API request and return the parsed JSON response."""
    headers = {**_GH_HEADERS, "Authorization": f"Bearer {token}"}
    resp = await client.request(method, url, json=body, headers=headers)
    if resp.status_code >= 400:
        raise GitHubAPIError(method, url, resp.status_code, resp.text)
    return resp.json() if resp.content else {}


async def _get_installation_token(
    client: httpx.AsyncClient, settings, owner: str,
) -> str:
    """Exchange GitHub App credentials for a short-lived installation token."""
    if not settings.github_app_id or not settings.github_app_private_key or not settings.github_app_installation_id:
        raise RuntimeError(
            "GitHub App not configured. Set RCARS_GITHUB_APP_ID, "
            "RCARS_GITHUB_APP_PRIVATE_KEY, and RCARS_GITHUB_APP_INSTALLATION_ID."
        )

    owner_id_map = {
        "zt-rhelbu": settings.github_app_installation_id_zt_rhelbu or settings.github_app_installation_id,
        "zt-ansiblebu": settings.github_app_installation_id_zt_ansiblebu or settings.github_app_installation_id,
    }
    installation_id = owner_id_map.get(owner, settings.github_app_installation_id)

    now = int(time.time())
    private_key = settings.github_app_private_key.replace("\\n", "\n")
    app_jwt = jwt.encode(
        {"iat": now - 60, "exp": now + 540, "iss": settings.github_app_id},
        private_key,
        algorithm="RS256",
    )

    url = f"{_GITHUB_API}/app/installations/{installation_id}/access_tokens"
    resp = await _gh(client, app_jwt, "POST", url)
    return resp["token"]


async def _get_default_branch(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
) -> tuple[str, str]:
    """Return (default_branch_name, sha) for the repo's default branch."""
    repo_data = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}")
    default_branch = repo_data.get("default_branch", "main")
    ref_data = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{default_branch}")
    return default_branch, ref_data["object"]["sha"]


async def _get_file(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
    path: str, ref: str | None = None,
) -> tuple[str, str]:
    """Return (content_str, file_sha) for an existing file."""
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    if ref:
        url += f"?ref={ref}"
    data = await _gh(client, token, "GET", url)
    content = base64.b64decode(data["content"]).decode("utf-8")
    return content, data["sha"]


async def _find_open_pr(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, branch: str,
) -> dict | None:
    """Return the first open PR for the branch, or None."""
    prs = await _gh(
        client, token, "GET",
        f"{_GITHUB_API}/repos/{owner}/{repo}/pulls?head={owner}:{branch}&state=open",
    )
    return prs[0] if prs else None


async def _get_pr_detail(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, pr_number: int,
) -> dict:
    """Return full PR details including merged state."""
    return await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}")


async def _create_branch(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
    branch: str, sha: str,
) -> None:
    await _gh(client, token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/git/refs", {
        "ref": f"refs/heads/{branch}",
        "sha": sha,
    })


async def _update_file(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
    path: str, content: str, file_sha: str, branch: str, message: str,
) -> None:
    await _gh(client, token, "PUT", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{path}", {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": file_sha,
        "branch": branch,
    })


async def _delete_directory_tree(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
    dir_path: str, branch: str, message: str,
) -> None:
    """Delete an entire directory in a single commit via the Git Trees API."""
    ref_data = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{branch}")
    head_sha = ref_data["object"]["sha"]

    commit_data = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/git/commits/{head_sha}")
    base_tree_sha = commit_data["tree"]["sha"]

    entries = await _gh(client, token, "GET", f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{dir_path}?ref={branch}")

    delete_entries = []
    for entry in entries:
        if entry["type"] == "file":
            delete_entries.append({"path": entry["path"], "mode": "100644", "type": "blob", "sha": None})
        elif entry["type"] == "dir":
            sub_entries = await _gh(
                client, token, "GET",
                f"{_GITHUB_API}/repos/{owner}/{repo}/contents/{entry['path']}?ref={branch}",
            )
            for sub in sub_entries:
                if sub["type"] == "file":
                    delete_entries.append({"path": sub["path"], "mode": "100644", "type": "blob", "sha": None})

    if not delete_entries:
        logger.warning("agv_delete_dir_empty", dir_path=dir_path, action="delete_directory")
        return

    new_tree = await _gh(client, token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/git/trees", {
        "base_tree": base_tree_sha,
        "tree": delete_entries,
    })

    new_commit = await _gh(client, token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/git/commits", {
        "message": message,
        "tree": new_tree["sha"],
        "parents": [head_sha],
    })

    await _gh(client, token, "PATCH", f"{_GITHUB_API}/repos/{owner}/{repo}/git/refs/heads/{branch}", {
        "sha": new_commit["sha"],
    })


async def _create_pr(
    client: httpx.AsyncClient, token: str, owner: str, repo: str,
    branch: str, base_branch: str, title: str, body: str,
) -> dict:
    return await _gh(client, token, "POST", f"{_GITHUB_API}/repos/{owner}/{repo}/pulls", {
        "title": title,
        "body": body,
        "head": branch,
        "base": base_branch,
    })


def _remove_notice_block(content: str) -> str | None:
    """Remove the retirement notice block from description.adoc content.

    Returns cleaned content, or None if no notice block was found.
    """
    match = _NOTICE_PATTERN.search(content)
    if not match:
        return None
    cleaned = content[:match.start()] + content[match.end():]
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.lstrip("\n")


# ── public API ───────────────────────────────────────────────────────────────


async def create_notice_pr(settings, base_name: str, jira_key: str, workflow: dict) -> dict:
    """Create the retirement notice PR on agnosticv.

    Prepends the AsciiDoc retirement notice block to description.adoc.
    Returns {pr_url, pr_number, repo}. Idempotent.
    """
    from rcars.services.jira import build_retirement_adoc_notice

    owner, repo_name, agv_path = _resolve_repo(base_name)
    branch = _branch_name(base_name, jira_key)
    adoc_notice = build_retirement_adoc_notice(workflow)

    logger.info("agv_notice_pr_start", base_name=base_name, repo=f"{owner}/{repo_name}", branch=branch, action="create_notice_pr")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        default_branch, main_sha = await _get_default_branch(client, token, owner, repo_name)
        agv_path = await _verify_agv_path(client, token, owner, repo_name, agv_path)
        desc_path = f"{agv_path}/description.adoc"

        branch_existed = False
        try:
            await _create_branch(client, token, owner, repo_name, branch, main_sha)
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            branch_existed = True
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if pr:
                logger.info("agv_notice_pr_reused", pr_url=pr["html_url"], action="create_notice_pr")
                return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

        try:
            existing_content, file_sha = await _get_file(
                client, token, owner, repo_name, desc_path,
                ref=branch if branch_existed else None,
            )
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                raise RuntimeError(
                    f"No description.adoc found at {desc_path} in {owner}/{repo_name}. "
                    "Retirement notice cannot be added automatically for CIs without a description.adoc."
                ) from exc
            raise
        if adoc_notice not in existing_content:
            new_content = adoc_notice + "\n\n" + existing_content
            await _update_file(
                client, token, owner, repo_name, desc_path, new_content, file_sha, branch,
                f"retire: add retirement notice for {agv_path} ({jira_key})",
            )

        pr = await _find_open_pr(client, token, owner, repo_name, branch)
        if pr:
            logger.info("agv_notice_pr_reused", pr_url=pr["html_url"], action="create_notice_pr")
            return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

        try:
            pr = await _create_pr(
                client, token, owner, repo_name, branch, default_branch,
                title=f"retire: {agv_path} — retirement notice ({jira_key})",
                body=(
                    f"Retirement notice PR for **{agv_path}**.\n\n"
                    f"Jira: [{jira_key}](https://redhat.atlassian.net/browse/{jira_key})\n\n"
                    "Adds the AsciiDoc retirement notice block to `description.adoc`.\n\n"
                    "---\n"
                    "_Generated by RCARS agv-retire integration — RHDPCD-2103_"
                ),
            )
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if not pr:
                raise
            logger.info("agv_notice_pr_reused_on_conflict", pr_url=pr["html_url"], action="create_notice_pr")
            return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

    logger.info("agv_notice_pr_created", pr_url=pr["html_url"], pr_number=pr["number"], action="create_notice_pr")
    return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}


async def create_retire_pr(settings, base_name: str, jira_key: str) -> dict:
    """Create the removal PR on agnosticv.

    Deletes the entire CI folder from the repo. A human reviewer must
    approve and merge.  Returns {pr_url, pr_number, repo}. Idempotent.
    """
    owner, repo_name, agv_path = _resolve_repo(base_name)
    branch = _branch_name(base_name, jira_key) + "-retire"

    logger.info("agv_retire_pr_start", base_name=base_name, repo=f"{owner}/{repo_name}", branch=branch, action="create_retire_pr")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        default_branch, main_sha = await _get_default_branch(client, token, owner, repo_name)
        agv_path = await _verify_agv_path(client, token, owner, repo_name, agv_path)

        branch_existed = False
        try:
            await _create_branch(client, token, owner, repo_name, branch, main_sha)
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            branch_existed = True
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if pr:
                logger.info("agv_retire_pr_reused", pr_url=pr["html_url"], action="create_retire_pr")
                return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

        try:
            await _delete_directory_tree(
                client, token, owner, repo_name, agv_path, branch,
                f"retire: remove {agv_path} from catalog ({jira_key})",
            )
        except GitHubAPIError as exc:
            if exc.status_code != 404:
                raise

        pr = await _find_open_pr(client, token, owner, repo_name, branch)
        if pr:
            logger.info("agv_retire_pr_reused", pr_url=pr["html_url"], action="create_retire_pr")
            return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

        try:
            pr = await _create_pr(
                client, token, owner, repo_name, branch, default_branch,
                title=f"retire: remove {agv_path} ({jira_key})",
                body=(
                    f"Removal PR for **{agv_path}**.\n\n"
                    f"Jira: [{jira_key}](https://redhat.atlassian.net/browse/{jira_key})\n\n"
                    "Deletes the CI folder, removing the item from the catalog. "
                    "Once merged, the item will disappear from Babylon on the next catalog sync "
                    "and RCARS will mark it retired automatically via soft-delete.\n\n"
                    "---\n"
                    "_Generated by RCARS agv-retire integration — RHDPCD-2103_"
                ),
            )
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if not pr:
                raise
            logger.info("agv_retire_pr_reused_on_conflict", pr_url=pr["html_url"], action="create_retire_pr")
            return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

    logger.info("agv_retire_pr_created", pr_url=pr["html_url"], pr_number=pr["number"], action="create_retire_pr")
    return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}


async def revert_notice_pr(settings, base_name: str, jira_key: str) -> dict | None:
    """Create a PR that removes the retirement notice from description.adoc.

    Used when cancelling a retirement after the notice PR was already merged.
    Returns {pr_url, pr_number, repo} or None if the notice block wasn't found.
    """
    owner, repo_name, agv_path = _resolve_repo(base_name)
    branch = _branch_name(base_name, jira_key) + "-revert-notice"

    logger.info("agv_revert_notice_start", base_name=base_name, repo=f"{owner}/{repo_name}", action="revert_notice_pr")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        default_branch, main_sha = await _get_default_branch(client, token, owner, repo_name)
        agv_path = await _verify_agv_path(client, token, owner, repo_name, agv_path)
        desc_path = f"{agv_path}/description.adoc"

        branch_existed = False
        try:
            await _create_branch(client, token, owner, repo_name, branch, main_sha)
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            branch_existed = True
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if pr:
                return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

        try:
            content, file_sha = await _get_file(
                client, token, owner, repo_name, desc_path,
                ref=branch if branch_existed else None,
            )
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                logger.warning("agv_revert_notice_no_file", base_name=base_name, action="revert_notice_pr")
                return None
            raise

        cleaned = _remove_notice_block(content)
        if cleaned is None:
            logger.info("agv_revert_notice_not_found", base_name=base_name, action="revert_notice_pr")
            return None

        await _update_file(
            client, token, owner, repo_name, desc_path, cleaned, file_sha, branch,
            f"retire: remove retirement notice for {agv_path} ({jira_key})",
        )

        try:
            pr = await _create_pr(
                client, token, owner, repo_name, branch, default_branch,
                title=f"retire: remove retirement notice for {agv_path} ({jira_key})",
                body=(
                    f"Removes the retirement notice from **{agv_path}** `description.adoc`.\n\n"
                    f"Jira: [{jira_key}](https://redhat.atlassian.net/browse/{jira_key})\n\n"
                    "The retirement for this item was cancelled. This PR removes the notice "
                    "that was previously merged.\n\n"
                    "---\n"
                    "_Generated by RCARS agv-retire integration — RHDPCD-2103_"
                ),
            )
        except GitHubAPIError as exc:
            if exc.status_code != 422:
                raise
            pr = await _find_open_pr(client, token, owner, repo_name, branch)
            if not pr:
                raise
            logger.info("agv_revert_pr_reused_on_conflict", pr_url=pr["html_url"], action="revert_notice_pr")
            return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}

    logger.info("agv_revert_notice_created", pr_url=pr["html_url"], pr_number=pr["number"], action="revert_notice_pr")
    return {"pr_url": pr["html_url"], "pr_number": pr["number"], "repo": f"{owner}/{repo_name}"}


async def close_pr(settings, repo_full: str, pr_number: int) -> None:
    """Close an open agnosticv PR and delete its branch."""
    owner, repo_name = repo_full.split("/", 1)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        pr = await _get_pr_detail(client, token, owner, repo_name, pr_number)
        await _gh(client, token, "PATCH", f"{_GITHUB_API}/repos/{owner}/{repo_name}/pulls/{pr_number}", {
            "state": "closed",
        })
        branch = pr.get("head", {}).get("ref")
        if branch and branch not in ("main", "master"):
            try:
                await _gh(client, token, "DELETE", f"{_GITHUB_API}/repos/{owner}/{repo_name}/git/refs/heads/{branch}")
                logger.info("agv_branch_deleted", repo=repo_full, branch=branch, action="close_pr")
            except GitHubAPIError as exc:
                if exc.status_code != 422:
                    logger.warning("agv_branch_delete_failed", repo=repo_full, branch=branch, error=str(exc), action="close_pr")
    logger.info("agv_pr_closed", repo=repo_full, pr_number=pr_number, action="close_pr")


async def get_pr_state(settings, repo_full: str, pr_number: int) -> dict:
    """Return {state, merged} for a PR. Used to decide close vs revert on cancel."""
    owner, repo_name = repo_full.split("/", 1)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        pr = await _get_pr_detail(client, token, owner, repo_name, pr_number)
    return {"state": pr.get("state"), "merged": pr.get("merged", False)}


async def get_last_updated(settings, owner: str, repo: str, path: str, limit: int = 1) -> list[dict]:
    """Return recent commits that touched a file.

    Works on any repo the GitHub App can access (installed orgs + public repos).
    Returns a list of {date, sha, url, author, message} dicts, newest first.
    Empty list if the file has no history.

    Default limit=1 for a quick freshness check ("last updated on ...").
    Pass limit=5 for a curator commit drawer.

    Curator/admin tool only — do not expose through user-facing chat.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        token = await _get_installation_token(client, settings, owner)
        commits = await _gh(
            client, token, "GET",
            f"{_GITHUB_API}/repos/{owner}/{repo}/commits?path={path}&per_page={limit}",
        )
    return [
        {
            "date": c["commit"]["committer"]["date"],
            "sha": c["sha"],
            "url": c["html_url"],
            "author": c["commit"]["author"]["name"],
            "message": c["commit"]["message"].split("\n", 1)[0],
        }
        for c in commits
    ]
