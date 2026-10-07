# RCARS × agv-retire: Automated Retirement Pipeline

**Status:** Draft spec — needs dev testing and Nate Stephany review before implementation  
**Author:** Billy Bethell  
**Related:** [agv-retire Confluence page](https://redhat.atlassian.net/wiki/spaces/RHPDS/pages/493683615)

---

## Problem

The current retirement process splits work across two systems that don't talk to each other:

- **RCARS** knows *when* to retire something: it tracks the recommendation, the approval, the countdown, and the target date.
- **agv-retire** knows *how* to retire something: it creates the agnosticv PRs that add the retirement notice adoc and ultimately remove the item from the prod catalog.

Today a human bridges the gap — RCARS ends at "Jira created," then someone manually runs agv-retire. The goal here is to close that gap so RCARS drives the full lifecycle automatically. The only step that stays manual is the agnosticv PR approve/merge (human gate, by design).

---

## Current RCARS Workflow Steps

```
reviewed → approved → started → notified → retired
```

- **reviewed**: RCARS recommends retirement (score-based)
- **approved**: curator signs off with reason, replacement CI, target days
- **started**: formal retirement begins — Jira ticket created today
- **notified**: notice adoc added to the catalog item (manual today)
- **retired**: item removed from prod catalog (manual today)

---

## Proposed Integration

### Phase 1 — `started` step triggers agv-retire notice PR

When an admin initiates retirement in the WorkflowDrawer, RCARS calls the AgV access layer to:

1. Create a PR on the target agnosticv repo adding the AsciiDoc retirement notice to the catalog item's config.
2. Store the PR URL back in the RCARS workflow record (`agv_notice_pr_url`).
3. Surface the PR link in the WorkflowDrawer so the admin can track review status.

The adoc template is already generated in `jira.py:build_retirement_description()` — this is the source of truth.

### Phase 2 — `retired` step triggers agv-retire removal PR

When the notice period expires and an admin marks the item ready for removal, RCARS:

1. Calls the AgV access layer to create the removal PR on the target agnosticv repo.
2. Stores the removal PR URL (`agv_retire_pr_url`) in the workflow record.
3. Surfaces the PR link in the WorkflowDrawer.

Once a human merges the removal PR, the item disappears from the Babylon catalog on the next sync. RCARS's existing soft-delete mechanism (`retired_at = NOW()`) picks this up automatically — no webhook or polling required.

---

## Proposed Implementation Approach

### AgV access layer (Python module)

The preferred approach is a native Python module in RCARS: `services/agv_access.py`. This provides generic git/GitHub operations — clone, branch, commit, push, open PR, close PR — that any part of RCARS can call. The retirement workflow is the first caller; other future needs that require touching AgV reuse the same layer.

**Option A: HTTP sidecar** (agv-retire container over localhost) — still viable but adds operational complexity. Not the preferred path.

**Option B: Direct Python module** — `services/agv_access.py` implements the operations natively. Simpler to operate, easier to test, and builds a reusable foundation. Nate is leaning this direction; spec reflects that.

The exact approach is still to be decided before implementation.

### Credential strategy

v1 scope: **rhpds/agnosticv**, **zt-rhelbu/agnosticv**, **zt-ansiblebu/agnosticv**. Partner RHDP agnosticV is out of scope — RCARS is currently unaware of partner RHDP and will remain so until there is a clearer path forward. This can be revisited in a later iteration.

Two credential options:

1. **GitHub App** — short-lived tokens, auditable, revocable. App scoped to the three target repos. RCARS exchanges the App private key (mounted as a Kubernetes sealed secret) for an installation token at runtime. Safest long-term option.

2. **Service-account PAT as a sealed secret** — lower setup cost. Long-lived credential but acceptable for a first pass.

Credential approach is also to be decided before implementation.

### New DB fields (retirement_workflow table)

```sql
agv_notice_pr_url   TEXT    -- PR URL for the retirement notice adoc
agv_retire_pr_url   TEXT    -- PR URL for the removal (informational only)
```

State tracking fields are not needed — the WorkflowDrawer surfaces the PR link only, and RCARS's soft-delete handles the retired state transition automatically when the item disappears from Babylon.

### New API endpoints

```
POST /analysis/retirement/{catalog_base_name}/agv-notice
```

- Auth: admin only
- Triggers notice PR creation via the AgV access layer
- Returns `{ pr_url, pr_number, repo }`
- Idempotent: if a PR already exists for this workflow, returns the existing one

```
POST /analysis/retirement/{catalog_base_name}/agv-retire
```

- Auth: admin only
- Triggers removal PR
- Only callable once `step_notified_at` is set and the notice period has elapsed

**Related:** Existing retirement endpoints are currently under `/analysis/performance/` — the wrong location. As part of this work, migrate them to `/analysis/retirement/` to consolidate all retirement routes in one place.

### WorkflowDrawer UI changes

- Surface the PR link next to the relevant step once created.
- No state badge or merge polling needed — when the removal PR merges, the item disappears from the active list via soft-delete and lives on in the retirement report.

---

## What Stays Manual

| Step | Manual? | Why |
|------|---------|-----|
| Retirement recommendation | Automated (RCARS score) | |
| Curator approval | Manual | Human judgment required |
| Jira creation | Automated (already done) | |
| agnosticv notice PR creation | Automated (this spec) | |
| agnosticv notice PR merge | **Manual — always** | Intentional human gate |
| agnosticv removal PR creation | Automated (this spec) | |
| agnosticv removal PR merge | **Manual — always** | Intentional human gate |
| RCARS retired state update | Automated (soft-delete via Babylon sync) | |

---

## Open Questions / Risks

1. **AgV namespace routing — decided:** v1 scope is **rhpds/agnosticv**, **zt-rhelbu**, **zt-ansiblebu**. The AgV access layer uses a routing table: `zt-ansiblebu.*` → `zt-ansiblebu/agnosticv`, `zt-rhelbu.*` → `zt-rhelbu/agnosticv`, everything else → `rhpds/agnosticv`.

2. **Notice period**: The window is already configurable per workflow (`target_days`, default 30). As part of this work, extend support to `0` days — implying immediate retirement. Useful for items that never went to prod and don't need a notice window.

3. **Replacement CI in the adoc**: Already handled in `jira.py:build_retirement_description()`. The same data feeds the agv-retire adoc template — no change needed.

4. **Branch naming**: Convention: `{ci-name}-{jira-issue}-{date}` (e.g. `demo-osp-RHDPCD-2103-20261007`). Unique per workflow run; avoids conflicts if a previous notice PR was abandoned.

5. **Rollback / cancel**: If an admin cancels the retirement after the notice PR is opened, RCARS should close the GitHub PR automatically via the AgV access layer.

---

## Dev Testing Requirements

Before this merges:

- [ ] Tested against the dev agnosticv repo (not prod) — confirm PR creation, branch naming, adoc content
- [ ] Credential path validated (GitHub App or PAT) — confirm token scopes are correct and least-privilege
- [ ] WorkflowDrawer PR link surfaces correctly in RCARS dev environment
- [ ] Cancel-retirement closes the open PR (not just orphans it)
- [ ] 0-day immediate retirement path tested end-to-end
- [ ] Nate Stephany review and approval

---

## References

- [agv-retire Confluence](https://redhat.atlassian.net/wiki/spaces/RHPDS/pages/493683615)
- `src/api/rcars/services/jira.py` — existing Jira ticket creation (adoc template source of truth)
- `src/api/rcars/services/retirement.py` — workflow step logic
- `src/frontend/src/pages/RetirementPage.tsx` — retirement dashboard
- `src/frontend/src/components/performance/WorkflowDrawer.tsx` — step management UI
