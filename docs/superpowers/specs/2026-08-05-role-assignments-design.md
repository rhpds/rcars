# Role Assignments — Design Spec

**Goal:** Replace hardcoded email-list config with a DB-backed role assignment table manageable via admin UI, while keeping env var entries as a permanent bootstrap safety net.

**Scope:** Curator and admin role elevation only. Basic authenticated access remains open to all OAuth-authenticated users.

---

## Data Layer

### `role_assignments` table

Added to `SCHEMA_SQL` in `src/api/rcars/db/database.py`:

```sql
CREATE TABLE IF NOT EXISTS role_assignments (
    id SERIAL PRIMARY KEY,
    type VARCHAR(10) NOT NULL CHECK (type IN ('user', 'group')),
    value VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL CHECK (role IN ('curator', 'admin')),
    added_by VARCHAR(255) NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(type, value)
);
```

- `type = 'user'` — a username (typically an email address in this cluster)
- `type = 'group'` — an OpenShift group name; membership resolved at auth time via the K8s API
- `UNIQUE(type, value)` — prevents duplicates; POST returns 409 on conflict

### DB methods (in `database.py`)

```python
def get_role_assignments(self) -> list[dict]: ...
def add_role_assignment(self, type: str, value: str, role: str, added_by: str) -> dict: ...
def delete_role_assignment(self, id: int) -> bool: ...  # returns False if not found
```

---

## Auth Middleware

File: `src/api/rcars/api/middleware/auth.py`

### Changes

Remove `curator_groups_str` / `admin_groups_str` from `config.py` — groups are stored in the DB, not env vars.

Add a module-level 30s cache (same pattern as `_GROUPS_CACHE`):

```python
_role_assignments_cache: tuple[list[dict], float] | None = None
_ROLE_ASSIGNMENTS_CACHE_TTL = 30.0
```

Add two functions:

```python
async def _get_cached_role_assignments(db) -> list[dict]:
    # Returns cached entries, or fetches from DB and caches them.

async def _user_has_db_role(db, email: str, required_roles: set[str]) -> bool:
    # Checks role_assignments table. For 'user' entries: case-insensitive match.
    # For 'group' entries: calls _fetch_group_members() (already implemented).
```

### Role check order in `require_curator` / `require_admin` / `require_performance_view`

1. **Env var bootstrap** — `settings.is_curator(user)` / `settings.is_admin(user)` — unchanged
2. **DB entries** — `await _user_has_db_role(db, user, required_roles)`

`require_curator` passes `{"curator", "admin"}` (admin satisfies curator).
`require_admin` passes `{"admin"}` only.

Cache is invalidated on every POST and DELETE to `/admin/role-assignments`.

---

## API

File: `src/api/rcars/api/routes/admin.py`

Three new endpoints, all gated by `require_admin`:

### `GET /admin/role-assignments`

Returns combined list:

```json
{
  "assignments": [
    {"id": null, "type": "user", "value": "you@redhat.com", "role": "admin", "source": "config", "added_by": null, "added_at": null},
    {"id": 1, "type": "group", "value": "rhdp-curators", "role": "curator", "source": "db", "added_by": "you@redhat.com", "added_at": "2026-08-05T..."}
  ]
}
```

Config entries are derived from `settings.curator_emails` and `settings.admin_emails` at request time. They have `id: null` and `source: "config"` — the UI uses these two fields to determine read-only vs. deletable.

### `POST /admin/role-assignments`

Request body: `{"type": "user"|"group", "value": "...", "role": "curator"|"admin"}`

- Validates `type` and `role` are valid values
- Returns 409 if `(type, value)` already exists
- Returns 201 with the created row
- Calls `invalidate_role_assignments_cache()` (exported from `auth.py`)

### `DELETE /admin/role-assignments/{id}`

- Returns 404 if not found
- Returns 204 on success
- Calls `invalidate_role_assignments_cache()` (exported from `auth.py`)

---

## Frontend

File: `src/frontend/src/pages/AdminPage.tsx`

New export: `AdminRolesPage`

### Layout

Two `admin-section` blocks inside `admin-layout admin-layout--wide`:

**From Configuration** (read-only)
- `status-table` with columns: Type / Value / Role
- Rows where `source === 'config'`, each row has a muted "config" badge in a fourth column
- No delete action

**Managed Access**
- Inline add form above the table:
  - Type: `<select>` with options `User` / `Group`
  - Value: `<input type="text" placeholder="username or group name">`
  - Role: `<select>` with options `Curator` / `Admin`
  - `Add` button — disabled while submitting; shows inline error on 409
- `status-table` with columns: Type / Value / Role / Added by / Added / Remove
- Remove is a small `×` button per row; calls DELETE, refreshes list on success

### API service calls (in `src/frontend/src/services/api.ts`)

```typescript
getRoleAssignments(): Promise<{assignments: RoleAssignment[]}>
addRoleAssignment(type: string, value: string, role: string): Promise<RoleAssignment>
deleteRoleAssignment(id: number): Promise<void>
```

### Routing

Added as a new admin sub-page, accessible from the admin sidebar. Follows the existing admin page registration pattern in `App.tsx` / `RcarsSidebar`.

---

## Deployment

### ClusterRole (still required)

The `rcars-oauth` ServiceAccount needs `get` on `user.openshift.io/groups` for group-type entries to resolve. Added to `manifests-infra.yaml.j2` (was already planned in the original task list).

### Ansible vars / env vars

No new env vars needed for groups — they live in the DB. The existing `curator_emails` / `admin_emails` Ansible vars remain for bootstrap. The planned `curator_groups` / `admin_groups` vars are dropped.

### Schema migration

`role_assignments` uses `CREATE TABLE IF NOT EXISTS` so it's applied automatically on next `rcars init-db` run (post-deploy hook).

---

## What's Not In Scope

- Basic access gating (open to all authenticated users by default — use OAuth proxy SAR if restriction is ever needed)
- `user` role entries in `role_assignments` (curator/admin elevation only)
- Cross-pod cache sharing (process-local 30s cache is sufficient)
- Audit log beyond `added_by` / `added_at` columns
