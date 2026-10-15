"""Tests for the AgV access layer (GitHub operations for agnosticv repos)."""
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rcars.services.agv_access import (
    GitHubAPIError,
    _branch_name,
    _remove_notice_block,
    _resolve_repo,
    close_pr,
    create_notice_pr,
    create_retire_pr,
    get_last_updated,
    get_pr_state,
    revert_notice_pr,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _settings(**overrides):
    s = MagicMock()
    s.github_app_id = "12345"
    s.github_app_private_key = "fake-pem"
    s.github_app_installation_id = "99999"
    s.github_app_installation_id_zt_rhelbu = ""
    s.github_app_installation_id_zt_ansiblebu = ""
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def _resp(status_code=200, json_data=None):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.content = b"{}" if json_data is not None else b""
    r.text = str(json_data) if json_data else ""
    r.json.return_value = json_data if json_data is not None else {}
    return r


def _file_content(text: str) -> dict:
    return {"content": base64.b64encode(text.encode()).decode(), "sha": "abc123"}


_PR = {"html_url": "https://github.com/rhpds/agnosticv/pull/42", "number": 42}


# ── pure function tests ─────────────────────────────────────────────────────


def test_resolve_repo_default():
    owner, repo, path = _resolve_repo("sandboxes-gpte.my-lab")
    assert owner == "rhpds"
    assert repo == "agnosticv"
    assert path == "sandboxes-gpte/my-lab"


def test_resolve_repo_strips_stage_suffix():
    _, _, path = _resolve_repo("agd-v2.mcp-with-openshift-sandbox.dev")
    assert path == "agd-v2/mcp-with-openshift-sandbox"
    _, _, path = _resolve_repo("openshift-cnv.ocp-virt-advanced-ops.prod")
    assert path == "openshift-cnv/ocp-virt-advanced-ops"
    _, _, path = _resolve_repo("summit-2026.lb1393-trilio.event")
    assert path == "summit-2026/lb1393-trilio"


def test_resolve_repo_no_stage_suffix_unchanged():
    _, _, path = _resolve_repo("sandboxes-gpte.my-lab")
    assert path == "sandboxes-gpte/my-lab"


@pytest.mark.parametrize("namespace,repo_name", [
    ("zt-ansiblebu", "zt-ansiblebu-agnosticv"),
    ("zt-rhelbu", "zt-rhelbu-agnosticv"),
])
@pytest.mark.parametrize("stage", ["", ".prod", ".dev", ".event", ".test"])
def test_resolve_repo_zt_items_use_rhpds(namespace, repo_name, stage):
    assert _resolve_repo(f"{namespace}.some-demo{stage}") == (
        "rhpds", repo_name, f"{namespace}/some-demo",
    )


def test_resolve_repo_no_dot():
    owner, repo, path = _resolve_repo("standalone")
    assert owner == "rhpds"
    assert path == "standalone"


def test_branch_name_format():
    with patch("rcars.services.agv_access.date") as mock_date:
        mock_date.today.return_value.strftime.return_value = "20261014"
        result = _branch_name("sandboxes-gpte.my-lab", "RHDPCD-99")
    assert result == "sandboxes-gpte-my-lab-RHDPCD-99-20261014"


def test_remove_notice_block_found():
    content = (
        "[IMPORTANT]\n.RETIREMENT NOTICE\n****\n"
        "This item will be retired on *2026-11-15*.\n\n"
        "For any questions regarding this retirement, please contact "
        "Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].\n"
        "****\n\n"
        "= Original Content\nSome text here."
    )
    result = _remove_notice_block(content)
    assert result is not None
    assert "[IMPORTANT]" not in result
    assert "RETIREMENT NOTICE" not in result
    assert "Original Content" in result


def test_remove_notice_block_not_found():
    assert _remove_notice_block("= Just a normal doc\nNo notice here.") is None


def test_remove_notice_block_collapses_blank_lines():
    content = (
        "[IMPORTANT]\n.RETIREMENT NOTICE\n****\n"
        "This item will be retired on *2026-11-15*.\n\n"
        "For any questions regarding this retirement, please contact "
        "Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].\n"
        "****\n\n\n\n"
        "= Content"
    )
    result = _remove_notice_block(content)
    assert "\n\n\n" not in result


def test_github_api_error_stores_status():
    exc = GitHubAPIError("GET", "https://api.github.com/foo", 404, "not found")
    assert exc.status_code == 404
    assert exc.method == "GET"
    assert "404" in str(exc)


# ── async tests (httpx mocked) ──────────────────────────────────────────────


def _mock_client():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _setup_client_for_pr(client, existing_content="= Old content", *, namespace="sandboxes-gpte", ci_name="my-lab", pr=None):
    """Wire up a mock client for the happy path of creating a PR."""
    call_count = {"n": 0}
    responses = [
        _resp(200, {"token": "inst-token"}),                     # installation token
        _resp(200, {"default_branch": "master"}),                # repo metadata
        _resp(200, {"object": {"sha": "main-sha-123"}}),         # ref/heads/master
        _resp(200, [{"name": namespace, "type": "dir"}]),       # list repo root
        _resp(200, [{"name": ci_name, "type": "dir"}]),         # list namespace dir
        _resp(200, {}),                                           # create branch
        _resp(200, _file_content(existing_content)),             # get file
        _resp(200, {}),                                           # update/delete file
        _resp(200, []),                                           # find open PR (none)
        _resp(200, pr or _PR),                                    # create PR
    ]

    async def side_effect(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        r = responses[idx]
        if r.status_code >= 400:
            raise GitHubAPIError(args[0] if args else "GET", "", r.status_code, r.text)
        return r

    client.request = AsyncMock(side_effect=side_effect)
    return client


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_create_notice_pr_happy_path(mock_jwt, mock_client_cls):
    client = _mock_client()
    _setup_client_for_pr(client)
    mock_client_cls.return_value = client

    workflow = {"replacement_ci": None, "retirement_target_date": "2026-11-15"}
    result = await create_notice_pr(_settings(), "sandboxes-gpte.my-lab", "RHDPCD-99", workflow)

    assert result["pr_url"] == _PR["html_url"]
    assert result["pr_number"] == 42
    assert result["repo"] == "rhpds/agnosticv"


@pytest.mark.parametrize("namespace,repo_name", [
    ("zt-ansiblebu", "zt-ansiblebu-agnosticv"),
    ("zt-rhelbu", "zt-rhelbu-agnosticv"),
])
@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_zt_notice_uses_rhpds_repo_and_installation(mock_jwt, mock_client_cls, namespace, repo_name):
    client = _mock_client()
    pr_url = f"https://github.com/rhpds/{repo_name}/pull/42"
    _setup_client_for_pr(
        client, namespace=namespace, ci_name="some-demo",
        pr={"html_url": pr_url, "number": 42},
    )
    mock_client_cls.return_value = client
    settings = _settings(
        github_app_installation_id_zt_rhelbu="unused-rhel-installation",
        github_app_installation_id_zt_ansiblebu="unused-ansible-installation",
    )

    result = await create_notice_pr(settings, f"{namespace}.some-demo.prod", "RHDPCD-99", {})

    assert result == {"pr_url": pr_url, "pr_number": 42, "repo": f"rhpds/{repo_name}"}
    urls = [call.args[1] for call in client.request.call_args_list]
    assert urls[0] == "https://api.github.com/app/installations/99999/access_tokens"
    assert all(url.startswith(f"https://api.github.com/repos/rhpds/{repo_name}") for url in urls[1:])
    assert any(f"/contents/{namespace}/some-demo/description.adoc" in url for url in urls)


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_create_notice_pr_idempotent_on_422(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        if call_count["n"] == 2:
            return _resp(200, {"default_branch": "master"})
        if call_count["n"] == 3:
            return _resp(200, {"object": {"sha": "sha1"}})
        if call_count["n"] == 4:  # list repo root
            return _resp(200, [{"name": "sandboxes-gpte", "type": "dir"}])
        if call_count["n"] == 5:  # list namespace dir
            return _resp(200, [{"name": "lab", "type": "dir"}])
        if call_count["n"] == 6:  # create branch → 422
            raise GitHubAPIError("POST", "", 422, "exists")
        if call_count["n"] == 7:  # find open PR → existing
            return _resp(200, [_PR])
        return _resp(200, {})

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    workflow = {"replacement_ci": None, "retirement_target_date": None}
    result = await create_notice_pr(_settings(), "sandboxes-gpte.lab", "RHDPCD-1", workflow)
    assert result["pr_url"] == _PR["html_url"]


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_create_retire_pr_happy_path(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        if call_count["n"] == 2:
            return _resp(200, {"default_branch": "master"})
        if call_count["n"] == 3:
            return _resp(200, {"object": {"sha": "main-sha"}})
        if call_count["n"] == 4:  # list repo root
            return _resp(200, [{"name": "sandboxes-gpte", "type": "dir"}])
        if call_count["n"] == 5:  # list namespace dir
            return _resp(200, [{"name": "lab", "type": "dir"}])
        if call_count["n"] == 6:
            return _resp(200, {})  # create branch
        # directory tree deletion calls (ref, commit, contents, tree, commit, patch)
        if call_count["n"] == 7:
            return _resp(200, {"object": {"sha": "head-sha"}})
        if call_count["n"] == 8:
            return _resp(200, {"tree": {"sha": "tree-sha"}})
        if call_count["n"] == 9:
            return _resp(200, [{"type": "file", "path": "sandboxes-gpte/lab/prod.yaml"},
                               {"type": "file", "path": "sandboxes-gpte/lab/common.yaml"}])
        if call_count["n"] == 10:
            return _resp(200, {"sha": "new-tree"})
        if call_count["n"] == 11:
            return _resp(200, {"sha": "new-commit"})
        if call_count["n"] == 12:
            return _resp(200, {})  # update ref
        if call_count["n"] == 13:
            return _resp(200, [])  # find open PR
        if call_count["n"] == 14:
            return _resp(200, _PR)  # create PR
        return _resp(200, {})

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    result = await create_retire_pr(_settings(), "sandboxes-gpte.lab", "RHDPCD-55")
    assert result["pr_url"] == _PR["html_url"]
    assert result["repo"] == "rhpds/agnosticv"


def _setup_client_for_revert(client, existing_content):
    """Wire up a mock client for the revert_notice_pr flow."""
    call_count = {"n": 0}
    responses = [
        _resp(200, {"token": "inst-token"}),                     # installation token
        _resp(200, {"default_branch": "master"}),                # repo metadata
        _resp(200, {"object": {"sha": "main-sha-123"}}),         # ref/heads/master
        _resp(200, [{"name": "sandboxes-gpte", "type": "dir"}]), # list repo root
        _resp(200, [{"name": "lab", "type": "dir"}]),            # list namespace dir
        _resp(200, {}),                                           # create branch
        _resp(200, _file_content(existing_content)),             # get file
        _resp(200, {}),                                           # update file
        _resp(200, _PR),                                          # create PR
    ]

    async def side_effect(*args, **kwargs):
        idx = min(call_count["n"], len(responses) - 1)
        call_count["n"] += 1
        return responses[idx]

    client.request = AsyncMock(side_effect=side_effect)


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_revert_notice_pr_removes_block(mock_jwt, mock_client_cls):
    notice = (
        "[IMPORTANT]\n.RETIREMENT NOTICE\n****\n"
        "This item will be retired on *2026-11-15*.\n\n"
        "For any questions regarding this retirement, please contact "
        "Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].\n"
        "****\n\n"
        "= Original Content"
    )
    client = _mock_client()
    _setup_client_for_revert(client, existing_content=notice)
    mock_client_cls.return_value = client

    result = await revert_notice_pr(_settings(), "sandboxes-gpte.lab", "RHDPCD-1")
    assert result is not None
    assert result["pr_url"] == _PR["html_url"]


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_revert_notice_pr_none_when_no_block(mock_jwt, mock_client_cls):
    client = _mock_client()
    _setup_client_for_revert(client, existing_content="= No notice here")
    mock_client_cls.return_value = client

    result = await revert_notice_pr(_settings(), "sandboxes-gpte.lab", "RHDPCD-1")
    assert result is None


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_revert_notice_pr_none_on_404(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        if call_count["n"] == 2:
            return _resp(200, {"default_branch": "master"})
        if call_count["n"] == 3:
            return _resp(200, {"object": {"sha": "sha1"}})
        if call_count["n"] == 4:  # list repo root
            return _resp(200, [{"name": "sandboxes-gpte", "type": "dir"}])
        if call_count["n"] == 5:  # list namespace dir
            return _resp(200, [{"name": "lab", "type": "dir"}])
        if call_count["n"] == 6:
            return _resp(200, {})  # create branch
        # get_file → 404
        raise GitHubAPIError("GET", "", 404, "not found")

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    result = await revert_notice_pr(_settings(), "sandboxes-gpte.lab", "RHDPCD-1")
    assert result is None


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_close_pr_sends_patch(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "inst-token"})
        return _resp(200, {})

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    await close_pr(_settings(), "rhpds/agnosticv", 42)
    calls = client.request.call_args_list
    close_call = [c for c in calls if "PATCH" in str(c)]
    assert len(close_call) >= 1


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_get_pr_state(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        return _resp(200, {"state": "closed", "merged": True})

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    result = await get_pr_state(_settings(), "rhpds/agnosticv", 42)
    assert result == {"state": "closed", "merged": True}


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_get_last_updated(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        return _resp(200, [{
            "commit": {
                "committer": {"date": "2026-10-01T12:00:00Z"},
                "author": {"name": "Jane"},
                "message": "fix: update config\ndetails here",
            },
            "sha": "abc123",
            "html_url": "https://github.com/rhpds/agnosticv/commit/abc123",
        }])

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    result = await get_last_updated(_settings(), "rhpds", "agnosticv", "some/path")
    assert len(result) == 1
    assert result[0]["date"] == "2026-10-01T12:00:00Z"
    assert result[0]["author"] == "Jane"
    assert result[0]["message"] == "fix: update config"


@patch("rcars.services.agv_access.httpx.AsyncClient")
@patch("rcars.services.agv_access.jwt.encode", return_value="fake-jwt")
async def test_get_last_updated_empty(mock_jwt, mock_client_cls):
    client = _mock_client()
    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _resp(200, {"token": "t"})
        return _resp(200, [])

    client.request = AsyncMock(side_effect=side_effect)
    mock_client_cls.return_value = client

    result = await get_last_updated(_settings(), "rhpds", "agnosticv", "nonexistent")
    assert result == []
