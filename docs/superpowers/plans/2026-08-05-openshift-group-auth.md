# OpenShift Group-Based Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenShift group membership as an additional role-resolution path alongside the existing email lists, so curators and admins can be managed via `oc adm groups` instead of editing a config file.

**Architecture:** `require_curator`/`require_admin` middleware already calls `settings.is_curator(user)` synchronously; we add an async group-lookup fallback in `auth.py` that hits the OpenShift groups API (`user.openshift.io/v1/groups/{name}`) using the pod's own ServiceAccount token. Results are cached 60s per group. The `rcars-oauth` ServiceAccount gets a new ClusterRole granting `get` on OpenShift groups. Email lists continue to work unchanged alongside group checks.

**Tech Stack:** Python 3.11, FastAPI, httpx (already a dependency), Ansible/Jinja2 templates, OpenShift `user.openshift.io/v1` Groups API.

## Global Constraints

- Never remove email-list support — email lists and group checks are additive (OR logic).
- No new Python dependencies — httpx is already used in `auth.py` for TokenReview.
- All env vars prefixed `RCARS_`, case-insensitive via Pydantic Settings.
- Ansible var naming must mirror the email list pattern: `curator_groups: []`, `admin_groups: []`.
- Group lookup must no-op gracefully when `KUBERNETES_SERVICE_HOST` is absent (local dev).
- Cache is process-local, 60s TTL, with stale-fallback on API error — same as labagator.
- Both API and scan-worker Deployments get the new env vars (same pattern as `RCARS_CURATOR_EMAILS_STR`).

---

## File Map

| File | Change |
|---|---|
| `src/api/rcars/config.py` | Add `curator_groups_str`, `admin_groups_str` fields + list properties |
| `src/api/rcars/api/middleware/auth.py` | Add group cache + `_fetch_group_members` + `_user_in_groups` + update `require_curator`/`require_admin`/`require_performance_view` |
| `src/api/tests/test_auth_middleware.py` | Update `_make_request` helper + add `TestGroupAuth` class |
| `ansible/templates/manifests-infra.yaml.j2` | Add ClusterRole + ClusterRoleBinding after SA block |
| `ansible/vars/common.yml` | Add `curator_groups: []` and `admin_groups: []` |
| `ansible/templates/manifests-app.yaml.j2` | Add `RCARS_CURATOR_GROUPS_STR` + `RCARS_ADMIN_GROUPS_STR` to both Deployment env blocks |

---

## Task 1: Settings Fields

**Files:**
- Modify: `src/api/rcars/config.py:82-88`
- Test: none (Pydantic field; covered implicitly by Task 3 tests)

**Interfaces:**
- Produces: `Settings.curator_groups_str: str`, `Settings.admin_groups_str: str`, `Settings.curator_groups -> list[str]`, `Settings.admin_groups -> list[str]`

- [ ] **Step 1: Add two new fields and two list properties to `Settings`**

  In `config.py`, in the `# Auth / roles` block (currently lines 82–88), add after `admin_emails_str`:

  ```python
  curator_groups_str: str = ""
  admin_groups_str: str = ""
  ```

  Then add two properties after the existing `admin_emails` property (around line 155):

  ```python
  @property
  def curator_groups(self) -> list[str]:
      return _parse_csv(self.curator_groups_str)

  @property
  def admin_groups(self) -> list[str]:
      return _parse_csv(self.admin_groups_str)
  ```

- [ ] **Step 2: Verify settings load cleanly**

  ```bash
  source ~/.virtualenvs/rcars-v2/bin/activate
  cd src/api
  python -c "
  from rcars.config import Settings
  s = Settings(database_url='postgresql://x/y', curator_groups_str='rhdp-curators,rhdp-team', admin_groups_str='rhdp-admins')
  print(s.curator_groups)   # ['rhdp-curators', 'rhdp-team']
  print(s.admin_groups)     # ['rhdp-admins']
  print(s.curator_emails)   # []  (still works)
  "
  ```

  Expected: both lists print correctly, no validation errors.

- [ ] **Step 3: Commit**

  ```bash
  git add src/api/rcars/config.py
  git commit -m "[RHDPCD-XXX] config: Add curator_groups_str and admin_groups_str settings"
  ```

---

## Task 2: Group Lookup Functions in auth.py

**Files:**
- Modify: `src/api/rcars/api/middleware/auth.py`
- Test: `src/api/tests/test_auth_middleware.py` (new `TestGroupLookup` class)

**Interfaces:**
- Consumes: `_K8S_TOKEN_PATH`, `_K8S_CA_PATH` (already defined in auth.py L15–16), `httpx.AsyncClient` (already imported)
- Produces: `async _fetch_group_members(group_name: str) -> set[str]`, `async _user_in_groups(email: str, groups: list[str]) -> bool`

- [ ] **Step 1: Write failing tests for `_fetch_group_members` and `_user_in_groups`**

  Add to `test_auth_middleware.py`, after the existing imports:

  ```python
  import os
  from rcars.api.middleware.auth import _fetch_group_members, _user_in_groups, _GROUPS_CACHE
  ```

  Add new test class:

  ```python
  class TestGroupLookup:
      def setup_method(self):
          _GROUPS_CACHE.clear()

      @patch("rcars.api.middleware.auth._K8S_TOKEN_PATH")
      @patch("rcars.api.middleware.auth.httpx.AsyncClient")
      @patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1", "KUBERNETES_SERVICE_PORT": "443"})
      async def test_fetch_group_members_returns_user_set(self, mock_client_cls, mock_token_path):
          mock_token_path.read_text.return_value = "pod-token"
          mock_client = _mock_async_client_get(
              get_return=_mock_group_response(["user@redhat.com", "other@redhat.com"])
          )
          mock_client_cls.return_value = mock_client
          members = await _fetch_group_members("rhdp-curators")
          assert "user@redhat.com" in members
          assert "other@redhat.com" in members

      @patch.dict(os.environ, {}, clear=True)
      async def test_fetch_group_members_returns_empty_when_not_in_cluster(self):
          # KUBERNETES_SERVICE_HOST absent → no API call, empty set
          members = await _fetch_group_members("any-group")
          assert members == set()

      @patch("rcars.api.middleware.auth._fetch_group_members", new_callable=AsyncMock)
      async def test_user_in_groups_returns_true_on_membership(self, mock_fetch):
          mock_fetch.return_value = {"user@redhat.com", "other@redhat.com"}
          result = await _user_in_groups("user@redhat.com", ["rhdp-curators"])
          assert result is True

      @patch("rcars.api.middleware.auth._fetch_group_members", new_callable=AsyncMock)
      async def test_user_in_groups_returns_false_when_not_member(self, mock_fetch):
          mock_fetch.return_value = {"other@redhat.com"}
          result = await _user_in_groups("user@redhat.com", ["rhdp-curators"])
          assert result is False

      async def test_user_in_groups_empty_list_returns_false(self):
          result = await _user_in_groups("user@redhat.com", [])
          assert result is False
  ```

  Also add these two helpers near the existing `_mock_async_client` helper:

  ```python
  def _mock_async_client_get(get_return=None) -> MagicMock:
      """Build a mock httpx.AsyncClient context manager with GET support."""
      client = AsyncMock()
      client.__aenter__ = AsyncMock(return_value=client)
      client.__aexit__ = AsyncMock(return_value=False)
      client.get = AsyncMock(return_value=get_return)
      return client

  def _mock_group_response(users: list[str]) -> MagicMock:
      """Build a mock httpx response for a groups API call."""
      resp = MagicMock()
      resp.json.return_value = {"users": users}
      resp.raise_for_status = MagicMock()
      return resp
  ```

- [ ] **Step 2: Run tests — confirm they fail**

  ```bash
  source ~/.virtualenvs/rcars-v2/bin/activate
  cd src/api
  python -m pytest tests/test_auth_middleware.py::TestGroupLookup -v
  ```

  Expected: `ImportError` — `_fetch_group_members`, `_user_in_groups`, `_GROUPS_CACHE` not yet defined.

- [ ] **Step 3: Implement group lookup in `auth.py`**

  After the existing `_CACHE_TTL = 10.0` line (line 23), add:

  ```python
  import os

  _GROUPS_CACHE: dict[str, tuple[set[str], float]] = {}
  _GROUPS_CACHE_TTL = 60.0
  _K8S_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
  _K8S_PORT = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
  ```

  After the existing `_validate_api_key_cached` function, add:

  ```python
  async def _fetch_group_members(group_name: str) -> set[str]:
      now = time.monotonic()
      cached = _GROUPS_CACHE.get(group_name)
      if cached:
          members, fetched_at = cached
          if now - fetched_at < _GROUPS_CACHE_TTL:
              return members

      if not _K8S_HOST:
          return set()

      try:
          token = _K8S_TOKEN_PATH.read_text().strip()
          ca = str(_K8S_CA_PATH) if _K8S_CA_PATH.exists() else False
          url = f"https://{_K8S_HOST}:{_K8S_PORT}/apis/user.openshift.io/v1/groups/{group_name}"
          async with httpx.AsyncClient(verify=ca, timeout=5.0) as client:
              resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
              resp.raise_for_status()
          members = set(resp.json().get("users") or [])
          _GROUPS_CACHE[group_name] = (members, now)
          return members
      except Exception:
          logger.warning("group_fetch_failed", group=group_name, exc_info=True)
          return cached[0] if cached else set()


  async def _user_in_groups(email: str, groups: list[str]) -> bool:
      if not groups or not email:
          return False
      for group in groups:
          if email in await _fetch_group_members(group):
              return True
      return False
  ```

  **Note on `_K8S_HOST`:** This is a module-level constant read once at import time. This means the in-cluster check is evaluated at startup, which is fine — the env var is either set or not when the container starts.

- [ ] **Step 4: Run tests — confirm they pass**

  ```bash
  python -m pytest tests/test_auth_middleware.py::TestGroupLookup -v
  ```

  Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

  ```bash
  git add src/api/rcars/api/middleware/auth.py src/api/tests/test_auth_middleware.py
  git commit -m "[RHDPCD-XXX] auth: Add OpenShift group membership lookup with 60s cache"
  ```

---

## Task 3: Wire Groups into require_curator / require_admin / require_performance_view

**Files:**
- Modify: `src/api/rcars/api/middleware/auth.py:203–230`
- Test: `src/api/tests/test_auth_middleware.py` (new `TestGroupAuth` class)

**Interfaces:**
- Consumes: `_user_in_groups(email, groups)` (from Task 2), `Settings.curator_groups`, `Settings.admin_groups` (from Task 1)

- [ ] **Step 1: Update `_make_request` helper to expose group settings on mock**

  In `test_auth_middleware.py`, update `_make_request` to add group list support:

  ```python
  def _make_request(
      headers: dict | None = None,
      dev_user: str = "",
      sa_allowlist_str: str = "",
      proxy_verification_secret: str = "",
      db: MagicMock | None = None,
      curator_groups: list | None = None,
      admin_groups: list | None = None,
  ) -> MagicMock:
      request = MagicMock()
      request.headers = headers or {}
      settings = MagicMock()
      settings.dev_user = dev_user
      settings.sa_allowlist_str = sa_allowlist_str
      settings.proxy_verification_secret = proxy_verification_secret
      settings.is_curator = MagicMock(return_value=False)
      settings.is_admin = MagicMock(return_value=False)
      settings.curator_groups = curator_groups or []
      settings.admin_groups = admin_groups or []
      request.app.state.settings = settings
      request.app.state.db = db or MagicMock()
      request.state = MagicMock()
      return request
  ```

- [ ] **Step 2: Write failing tests for group-based role checks**

  Add new class to `test_auth_middleware.py`:

  ```python
  class TestGroupAuth:
      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_require_curator_passes_for_group_member(self, mock_groups):
          mock_groups.return_value = True
          request = _make_request(
              headers={"X-Forwarded-Email": "new@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              curator_groups=["rhdp-curators"],
          )
          # email lists return False; groups return True
          result = await require_curator(request)
          assert result == "new@redhat.com"
          mock_groups.assert_called_once_with("new@redhat.com", ["rhdp-curators"])

      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_require_curator_passes_for_admin_group_member(self, mock_groups):
          """Admin group membership also satisfies curator requirement."""
          mock_groups.return_value = True
          request = _make_request(
              headers={"X-Forwarded-Email": "admin@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              admin_groups=["rhdp-admins"],
          )
          result = await require_curator(request)
          assert result == "admin@redhat.com"

      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_require_curator_blocks_non_member(self, mock_groups):
          mock_groups.return_value = False
          request = _make_request(
              headers={"X-Forwarded-Email": "stranger@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              curator_groups=["rhdp-curators"],
          )
          with pytest.raises(HTTPException) as exc_info:
              await require_curator(request)
          assert exc_info.value.status_code == 403

      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_require_admin_passes_for_admin_group_member(self, mock_groups):
          mock_groups.return_value = True
          request = _make_request(
              headers={"X-Forwarded-Email": "admin@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              admin_groups=["rhdp-admins"],
          )
          result = await require_admin(request)
          assert result == "admin@redhat.com"

      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_require_admin_blocks_curator_group_member(self, mock_groups):
          """Curator group alone is NOT enough for admin."""
          mock_groups.return_value = False
          request = _make_request(
              headers={"X-Forwarded-Email": "curator@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              curator_groups=["rhdp-curators"],
              admin_groups=["rhdp-admins"],
          )
          with pytest.raises(HTTPException) as exc_info:
              await require_admin(request)
          assert exc_info.value.status_code == 403
          # _user_in_groups must be called with admin_groups only
          mock_groups.assert_called_once_with("curator@redhat.com", ["rhdp-admins"])

      @patch("rcars.api.middleware.auth._user_in_groups", new_callable=AsyncMock)
      async def test_email_list_takes_precedence_no_group_call(self, mock_groups):
          """If email list grants access, group lookup is skipped entirely."""
          request = _make_request(
              headers={"X-Forwarded-Email": "listed@redhat.com", "X-Proxy-Secret": "s"},
              proxy_verification_secret="s",
              curator_groups=["rhdp-curators"],
          )
          request.app.state.settings.is_curator.return_value = True
          result = await require_curator(request)
          assert result == "listed@redhat.com"
          mock_groups.assert_not_called()
  ```

- [ ] **Step 3: Run tests — confirm they fail**

  ```bash
  python -m pytest tests/test_auth_middleware.py::TestGroupAuth -v
  ```

  Expected: FAIL — `require_curator` still raises 403 for group members.

- [ ] **Step 4: Update `require_curator`, `require_admin`, `require_performance_view` in `auth.py`**

  Replace `require_curator` (currently lines 203–209):

  ```python
  async def require_curator(request: Request) -> str:
      user = await require_auth(request)
      _check_api_key_role_ceiling(request, "curator")
      settings: Settings = request.app.state.settings
      if settings.is_curator(user) or settings.is_admin(user):
          return user
      if await _user_in_groups(user, settings.curator_groups + settings.admin_groups):
          return user
      raise HTTPException(status_code=403, detail="Curator role required")
  ```

  Replace `require_performance_view` (currently lines 212–221):

  ```python
  async def require_performance_view(request: Request) -> str:
      """Any authenticated user when performance_public; curator/admin otherwise."""
      user = await require_auth(request)
      settings: Settings = request.app.state.settings
      if settings.performance_public:
          return user
      _check_api_key_role_ceiling(request, "curator")
      if settings.is_curator(user) or settings.is_admin(user):
          return user
      if await _user_in_groups(user, settings.curator_groups + settings.admin_groups):
          return user
      raise HTTPException(status_code=403, detail="Curator role required")
  ```

  Replace `require_admin` (currently lines 224–230):

  ```python
  async def require_admin(request: Request) -> str:
      user = await require_auth(request)
      _check_api_key_role_ceiling(request, "admin")
      settings: Settings = request.app.state.settings
      if settings.is_admin(user):
          return user
      if await _user_in_groups(user, settings.admin_groups):
          return user
      raise HTTPException(status_code=403, detail="Admin role required")
  ```

- [ ] **Step 5: Run full test suite**

  ```bash
  python -m pytest tests/test_auth_middleware.py -v
  ```

  Expected: all tests PASS (including existing ones — logic is additive, not replacing).

- [ ] **Step 6: Commit**

  ```bash
  git add src/api/rcars/api/middleware/auth.py src/api/tests/test_auth_middleware.py
  git commit -m "[RHDPCD-XXX] auth: Check OpenShift group membership in require_curator/require_admin"
  ```

---

## Task 4: ClusterRole for Group Read Access in Infra Template

**Files:**
- Modify: `ansible/templates/manifests-infra.yaml.j2`

**Context:** The `rcars-oauth` ServiceAccount is defined at line 199. A ClusterRole + ClusterRoleBinding must be added immediately after it. Currently the SA has no RBAC at all — `oc auth can-i get groups.user.openshift.io --as system:serviceaccount:rcars-dev:rcars-oauth` returns `no`.

- [ ] **Step 1: Add ClusterRole + ClusterRoleBinding after the ServiceAccount block**

  After line 206 (the `---` separator after the SA), insert:

  ```yaml
  ---
  # Allow the OAuth SA to read OpenShift group membership for role resolution
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRole
  metadata:
    name: {{ app_name }}-group-reader
    labels:
      app: {{ app_name }}
  rules:
    - apiGroups: ["user.openshift.io"]
      resources: ["groups"]
      verbs: ["get"]
  ---
  apiVersion: rbac.authorization.k8s.io/v1
  kind: ClusterRoleBinding
  metadata:
    name: {{ app_name }}-group-reader
    labels:
      app: {{ app_name }}
  roleRef:
    apiGroup: rbac.authorization.k8s.io
    kind: ClusterRole
    name: {{ app_name }}-group-reader
  subjects:
    - kind: ServiceAccount
      name: {{ app_name }}-oauth
      namespace: {{ namespace }}
  ```

- [ ] **Step 2: Apply config-only to dev to create the ClusterRole**

  ```bash
  ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config
  ```

- [ ] **Step 3: Verify the SA now has access**

  ```bash
  KUBECONFIG=/Users/nstephan/devel/secrets/rcars-mgmt-dev.kubeconfig \
    oc auth can-i get groups.user.openshift.io \
    --as system:serviceaccount:rcars-dev:rcars-api
  ```

  Expected: `yes`

- [ ] **Step 4: Commit**

  ```bash
  git add ansible/templates/manifests-infra.yaml.j2
  git commit -m "[RHDPCD-XXX] infra: Add ClusterRole for OpenShift group-read access"
  ```

---

## Task 5: Ansible Vars and App Template Env Vars

**Files:**
- Modify: `ansible/vars/common.yml`
- Modify: `ansible/templates/manifests-app.yaml.j2` (two Deployment env blocks)

- [ ] **Step 1: Add group vars to `common.yml`**

  After `admin_emails: []` (currently line 38), add:

  ```yaml
  curator_groups: []
  admin_groups: []
  ```

- [ ] **Step 2: Add env vars to both Deployment blocks in `manifests-app.yaml.j2`**

  After line 119 (`RCARS_ADMIN_EMAILS_STR` block), in **both** Deployment env blocks (around lines 116–119 and 472–475), add:

  ```yaml
            - name: RCARS_CURATOR_GROUPS_STR
              value: "{{ curator_groups | join(',') }}"
            - name: RCARS_ADMIN_GROUPS_STR
              value: "{{ admin_groups | join(',') }}"
  ```

- [ ] **Step 3: Verify template renders correctly**

  ```bash
  ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config --check
  ```

  Expected: no errors, diff shows new env vars added to both Deployments.

- [ ] **Step 4: Commit**

  ```bash
  git add ansible/vars/common.yml ansible/templates/manifests-app.yaml.j2
  git commit -m "[RHDPCD-XXX] ansible: Add curator_groups and admin_groups vars and env vars"
  ```

---

## Verification

After all tasks are committed and deployed to dev:

1. Set `curator_groups: ["rhpds-admins"]` (or whichever group you want to test with) in `ansible/vars/dev.yml`.
2. Run `ansible-playbook ansible/deploy.yml -e env=dev --tags apply-config` to apply.
3. Log in to the dev frontend as a user who is in that group but NOT in the `curator_emails` list.
4. Confirm you can access curator features (Curator drawer in Browse, retirement workflow actions).
5. Log in as a user in neither list nor group — confirm 403 on curator endpoints.

---

## What Was Skipped

- **Cache invalidation endpoint** — not needed; 60s TTL is acceptable for role changes.
- **Cross-pod cache sharing** — each replica caches independently (same as labagator). Fine at this scale.
- **`list` verb on groups** — only `get` (by name) is needed since we look up specific groups; `list` would be over-permissive.
