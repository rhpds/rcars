# Retirement Workflow Actions Design

**Jira:** RHDPCD-27
**Date:** 2026-07-02
**Status:** Draft

## Context

The retirement analysis dashboard is currently read-only. Curators can see retirement scores and filter/sort items, but cannot act on them. The retirement process is tracked externally in spreadsheets. RCARS should become the system of record for retirement decisions, replacing the spreadsheet with a checklist-style workflow that culminates in a Jira ticket and auto-closes when the item disappears from Babylon.

## Workflow Stages

Five stages, processed in order. Stages 1-4 are manual curator actions. Stage 5 is automatic.

1. **Reviewed** — Curator has examined the item and its retirement score
2. **Approved** — Decision made to retire, with a reason captured. A snapshot of the item's current metrics is frozen at this point (provisions, experiences, touched, closed, cost) since reporting data is rebuilt nightly.
3. **Owner Notified** — (optional, can be skipped) Content owner has been informed manually
4. **Retirement Started** — Jira ticket created via direct REST API, retirement clock starts. Default 30-day window per policy, configurable from immediate to longer.
5. **Retired** — Auto-closed when the item disappears from Babylon CRDs during the nightly sync

Each step records who performed it and when. Steps are tracked by their timestamp being non-NULL (no separate boolean columns). The `status` column is derived from the highest completed step for fast filtering.

## Data Model

New table: `retirement_workflow`

```sql
CREATE TABLE IF NOT EXISTS retirement_workflow (
    catalog_base_name    TEXT PRIMARY KEY,
    status               TEXT NOT NULL DEFAULT 'reviewed',
    step_reviewed_at     TIMESTAMPTZ,
    step_reviewed_by     TEXT,
    step_approved_at     TIMESTAMPTZ,
    step_approved_by     TEXT,
    approval_reason      TEXT,
    approval_snapshot    JSONB,
    step_notified_at     TIMESTAMPTZ,
    step_notified_by     TEXT,
    step_started_at      TIMESTAMPTZ,
    step_started_by      TEXT,
    retirement_target_date DATE,
    step_retired_at      TIMESTAMPTZ,
    replacement_ci       TEXT,
    replacement_name     TEXT,
    curator_notes        TEXT,
    jira_key             TEXT,
    jira_project         TEXT NOT NULL DEFAULT 'RHDPCD',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_retirement_workflow_status
    ON retirement_workflow (status);
```

**Status values:** `reviewed`, `approved`, `notified`, `started`, `retired`

**`approval_snapshot` JSONB** — frozen metrics captured at approval time:
```json
{
  "provisions": 6,
  "experiences": 12,
  "unique_users": 4,
  "touched_amount": 50000.0,
  "closed_amount": 0,
  "total_cost": 8500.0,
  "retirement_score": 72,
  "window": "12m",
  "snapshot_date": "2026-07-02"
}
```

**`replacement_ci`** — base name of the replacement item (e.g., `openshift_cnv.ocp4-getting-started`), if one exists. Optional.
**`replacement_name`** — display name of the replacement (e.g., "OCP4 Getting Started Workshop"). Optional.

**Relationship to existing tables:**
- Keyed by `catalog_base_name`, matching `reporting_metrics` (no FK since reporting_metrics is wiped and rebuilt nightly)
- The nightly CRD sync in `retire_removed_items()` will be extended to auto-set `step_retired_at` on any workflow record whose base name matches a newly-retired catalog item

## API Endpoints

All under `/api/v1/analysis/retirement`. All require `require_curator`.

### Workflow State

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workflow/{base_name}` | Get workflow state for one item |
| PUT | `/workflow/{base_name}/review` | Mark as reviewed |
| PUT | `/workflow/{base_name}/approve` | Approve with reason + snapshot (body: `{reason, replacement_ci?, replacement_name?}`) |
| PUT | `/workflow/{base_name}/notify` | Mark owner notified |
| PUT | `/workflow/{base_name}/start` | Create Jira ticket, start retirement clock (body: `{target_days?, jira_project?}`) |
| PUT | `/workflow/{base_name}/notes` | Update curator notes (body: `{notes}`) |
| DELETE | `/workflow/{base_name}` | Cancel/reset workflow |

### Behavior Details

**PUT /review:** Creates the workflow record if it doesn't exist. Sets `step_reviewed_at = NOW()`, `step_reviewed_by = user`, `status = 'reviewed'`.

**PUT /approve:** Sets approval fields. Body must include `reason`. Optionally accepts `replacement_ci` and `replacement_name`. The endpoint looks up the item's current reporting metrics and freezes them into `approval_snapshot`. Updates `status = 'approved'`. If not yet reviewed, also sets reviewed fields (auto-completing earlier step).

**PUT /notify:** Sets notification fields. Updates `status = 'notified'`. This step is optional — curators can skip straight from approved to start.

**PUT /start:** Creates a Jira ticket via direct REST API call and starts the retirement clock:
- Sets `jira_key`, `step_started_at`, `retirement_target_date = NOW() + target_days` (default 30)
- Updates `status = 'started'`
- If not yet reviewed or approved, auto-completes those steps
- See "Jira Ticket Creation" section for ticket content

**PUT /notes:** Updates `curator_notes` and `updated_at`. Can be called at any stage.

**DELETE:** Removes the workflow record entirely. Use case: curator changed their mind, item should stay.

### Dashboard Enrichment

The existing `GET /retirement` endpoint will LEFT JOIN with `retirement_workflow` to include workflow state per item:
- `workflow_status`: the status string (or NULL if no workflow exists)
- `jira_key`: linked Jira ticket
- `retirement_target_date`: when retirement is expected

A new query parameter `workflow_status` enables filtering:
- `workflow_status=none` — items with no workflow record
- `workflow_status=reviewed` — items in reviewed state
- `workflow_status=approved`, `workflow_status=started`, `workflow_status=retired`

## Auto-Closing Retired Items

The nightly CRD sync (`retire_removed_items()` in `database.py`) already sets `retired_at` on catalog items that disappear from Babylon. This function will be extended to:

1. After marking items retired, query `retirement_workflow` for any records whose `catalog_base_name` matches a newly-retired item AND `step_retired_at IS NULL`
2. Set `step_retired_at = NOW()`, `status = 'retired'`
3. Log the auto-close via `analysis_log`

This closes the loop: curator starts the process, Jira ticket drives the actual removal, and when the item disappears from Babylon, RCARS auto-marks the workflow complete.

## Jira Ticket Creation

When a curator clicks "Start Retirement", RCARS creates a Jira ticket by calling the Jira Cloud REST API directly from the Python backend (`POST /rest/api/3/issue`). No MCP tools or LLM token usage involved — it's a straightforward HTTP call using the same `urllib` pattern as the reporting MCP queries.

### Configuration

New settings in `config.py`:
- `jira_base_url: str = "https://redhat.atlassian.net"` — Jira Cloud instance
- `jira_api_email: str = ""` — Service account email for Basic auth
- `jira_api_token: str = ""` — API token for Basic auth
- `jira_retirement_template: str = "GPTEINFRA-14367"` — Template issue to clone-link

### Ticket Content

Modeled on the existing retirement Jira skill (GPTEINFRA pattern):

- **Project:** Configurable per item, default RHDPCD
- **Issue type:** Task
- **Summary:** `Retire "<display_name>"`
- **Label:** `RHDP_RETIREMENT`
- **Description** (markdown):

```
**CI Name:** <display_name>

**RHDP URL:** https://demo.redhat.com/catalog?search=<catalog_base_name>

**AgV:** https://github.com/rhpds/agnosticv/tree/master/<agv_path>

**Retirement Notice:** <target_days> days (target date: <retirement_target_date>)

**Replacement CI:** <replacement_name> (<replacement_ci>) or "N/A"

**Reason & Notes:**

* <approval_reason>
* <curator_notes if any>

**Metrics at approval (snapshot <snapshot_date>):**

| Metric | Value |
|--------|-------|
| Retirement Score | <score> |
| Provisions | <provisions> |
| Experiences | <experiences> |
| Unique Users | <unique_users> |
| Touched Amount | $<touched> |
| Closed Amount | $<closed> |
| Total Cost | $<cost> |

**RCARS Dashboard:** <link to retirement page>

---

**Suggested adoc template:**

\`\`\`
[IMPORTANT]
.RETIREMENT NOTICE
****
This item will be retired on **<retirement_target_date>**. <if replacement: Please use this as an alternative: link:<replacement_url>[<replacement_name>, window="_blank"]>

For any questions regarding this retirement, please contact Nate Stephany at mailto:nstephan@redhat.com[nstephan@redhat.com].
****
\`\`\`
```

### Post-Creation

After creating the ticket:
1. Create a clone link to the retirement template issue (GPTEINFRA-14367) via `POST /rest/api/3/issueLink`
2. Store the `jira_key` on the workflow record

### AgV Path Resolution

The AgV URL needs the path within the agnosticv repo. RCARS can derive this from the `catalog_base_name` using the existing `catalog_items` table which stores the `ci_name` (format: `component/item.stage`). The component path maps to the AgnosticV directory structure.

## Frontend Changes

### Inline Status Indicator (Table Row)

Each item row gets a single badge next to the retirement score:
- **No workflow:** no badge
- **Any active workflow** (reviewed, approved, notified, started): single "Retirement In Process" badge — a small indicator that this item is being worked through the retirement workflow
- The status filter handles the granularity; the inline indicator just flags "something is happening"

### Slide-Out Drawer

Clicking an item opens a drawer (reusing the BrowsePage drawer pattern) with:

**Top section — Item context:**
- Display name, base name, retirement score
- Current metrics (provisions, touched, closed, cost)
- Stage badges (prod/event/dev)

**Middle section — Workflow checklist:**
- Each step as a checkbox line with timestamp and user when complete
- "Reviewed" checkbox (click to toggle)
- "Approved" with reason text input (required) and optional replacement CI fields
- "Owner Notified" checkbox (optional, can skip)
- "Start Retirement" button with target days input (default 30) and project selector
- "Retired" — shown as auto-complete status, not clickable
- If `approval_snapshot` exists, show the frozen metrics alongside current metrics for comparison

**Bottom section — Notes:**
- Textarea for curator notes (auto-saves on blur, like BrowsePage)
- Jira ticket link (when created)

### Status Filter

New filter row alongside the existing score filter buttons:
- All | No Action | In Process | Started | Retired

"In Process" collapses reviewed + approved + notified into one filter option since the inline badge doesn't distinguish them.

## Database Methods

New methods on the `Database` class:

- `get_retirement_workflow(base_name) -> dict | None`
- `upsert_retirement_workflow(base_name, fields) -> dict`
- `delete_retirement_workflow(base_name) -> bool`
- `list_retirement_workflows(status=None) -> list[dict]`
- `auto_close_retired_workflows(retired_base_names: set[str]) -> int`

## Jira Service

New module: `src/api/rcars/services/jira.py`

Follows the same pattern as Publishing House Central's `jira_client.py` — direct Jira REST API v3 calls with Basic auth (email:token base64-encoded). Uses `urllib` (consistent with RCARS's existing HTTP patterns) rather than `httpx` (PH Central's choice).

Functions:
- `create_retirement_ticket(settings, workflow, metrics) -> str` — returns Jira key
- `link_to_template(settings, jira_key) -> None` — clone link to template issue

No MCP tools, no LLM token usage. Pure HTTP calls.

## Audit Trail

All workflow actions are logged via the existing `analysis_log` table using `log_action(ci_name, action, user_id, details)`. Actions logged:
- `retirement_reviewed`, `retirement_approved`, `retirement_notified`
- `retirement_started` (includes jira_key in details)
- `retirement_auto_closed`
- `retirement_cancelled`

## Migration

Alembic migration 012 creates the `retirement_workflow` table. No changes to existing tables.

## Out of Scope / Future Backlog

**Automated owner notification:** The AgnosticV catalog records include maintainer information (email, team). A future enhancement could automatically send an email or Slack notification to the content owner when the "Owner Notified" step is reached, instead of requiring the curator to do it manually. This would use the maintainer data already available in the CRD metadata. To be tracked as a separate backlog item after this feature is implemented.

## Testing

- Unit tests for DB methods (get/upsert/delete/list/auto-close)
- Unit tests for status derivation logic
- Unit test for Jira ticket description formatting
- Unit test for `jira.py` service (mock HTTP responses)
- API endpoint tests (mock DB, verify correct fields set per action)
