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
- **notified**: 30-day notice adoc added to the catalog item (manual today)
- **retired**: item removed from prod catalog (manual today)

---

## Proposed Integration

### Phase 1 — `started` step triggers agv-retire notice PR

When a curator clicks "Start Retirement" in the WorkflowDrawer, RCARS calls agv-retire (or its equivalent logic) to:

1. Create a PR on the relevant agnosticv namespace repo adding the AsciiDoc retirement notice to the catalog item's config.
2. Store the PR URL(s) back in the RCARS workflow record (`agv_notice_pr_url`).
3. Surface the PR link in the WorkflowDrawer UI so curators can track review status.

The adoc template is already generated in `jira.py:build_retirement_description()` — this is the source of truth.

### Phase 2 — `retired` step triggers agv-retire removal PR

When the target retirement date is reached and a curator marks the item as retired, RCARS:

1. Calls agv-retire to create the removal PR (deletes or unpublishes the item from prod catalog).
2. Stores the removal PR URL (`agv_retire_pr_url`) in the workflow.
3. Marks the RCARS item as fully retired once the PR is merged (webhook or polling).

---

## Proposed Implementation Approach

### agv-retire as a library / subprocess

agv-retire is currently a CLI tool. Two clean options:

**Option A (preferred): HTTP sidecar**  
Run agv-retire as a small FastAPI sidecar alongside the RCARS API pod. RCARS calls it over localhost. agv-retire handles GitHub auth via its own mounted secret. Clean separation, no credential bleed into RCARS config.

**Option B: Direct Python import**  
Pull agv-retire's core functions into RCARS as a `services/agv_retire.py` module. Simpler operationally but tighter coupling.

### Credential strategy

The key constraint: agv-retire needs a GitHub token with write access to the target agnosticv namespace repos (e.g. `rhpds/agnosticv`, partner forks, etc.).

Recommended approach:

1. Create a **GitHub App** scoped to the agnosticv repos that RCARS needs to touch. App installs generate short-lived tokens — no long-lived PAT stored anywhere.
2. Mount the GitHub App private key as a Kubernetes secret in the RCARS namespace.
3. RCARS (or the agv-retire sidecar) exchanges the App key for an installation token at runtime.

This is the safest path — no stored PAT, auditable via GitHub App install logs, revocable without rotating a shared secret.

**Alternative:** A dedicated service-account PAT stored as a sealed secret. Lower setup cost, works, but a long-lived credential. Acceptable if the GitHub App route is too much overhead for a first pass.

### New DB fields (retirement_workflow table)

```sql
agv_notice_pr_url   TEXT    -- PR URL for the retirement notice adoc
agv_retire_pr_url   TEXT    -- PR URL for the actual removal
agv_notice_pr_state TEXT    -- open | merged | closed
agv_retire_pr_state TEXT    -- open | merged | closed
```

### New API endpoint

```
POST /analysis/retirement/{catalog_base_name}/agv-notice
```

- Auth: curator or admin
- Triggers agv-retire notice PR creation
- Returns `{ pr_url, pr_number, repo }`
- Idempotent: if a PR already exists for this workflow, returns the existing one

```
POST /analysis/retirement/{catalog_base_name}/agv-retire
```

- Auth: admin only
- Triggers removal PR
- Only callable once `step_notified_at` is set and target date is reached

### WorkflowDrawer UI changes

- Show PR link and state badge next to the "Start Retirement" step.
- Add "Open PR" button that surfaces once the notice PR is created.
- Show merge status (polling or webhook-driven).

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
| RCARS status update | Automated (webhook/polling) | |

---

## Open Questions / Risks

1. **Multi-namespace agnosticv**: Some catalog items live in partner forks (e.g. `rhpds/agnosticv`, `zt-*` repos). agv-retire needs to know which repo to target. This mapping may need a lookup table or a convention from the CI name.

2. **30-day window**: The retirement notice period is fixed policy — this spec does not change it. RCARS already tracks `target_days` per workflow.

3. **Replacement CI in the adoc**: Already handled in `jira.py:build_retirement_description()`. The same data feeds the agv-retire adoc template.

4. **PR conflicts**: If the agnosticv repo already has a change in flight for the same CI, agv-retire's PR will need a unique branch name. Recommend `rcars/retire/{ci_base_name}/{workflow_id}` as the branch naming convention.

5. **Rollback / cancel**: If a curator cancels the retirement after the notice PR is opened, RCARS should close the GitHub PR automatically.

---

## Dev Testing Requirements

Before this merges:

- [ ] Tested against the dev agnosticv repo (not prod) — confirm PR creation, branch naming, adoc content
- [ ] Credential path validated (GitHub App or PAT) — confirm token scopes are correct and least-privilege
- [ ] WorkflowDrawer PR link surfaces correctly in RCARS dev environment
- [ ] Cancel-retirement closes the open PR (not just orphans it)
- [ ] Nate Stephany review and approval

---

## References

- [agv-retire Confluence](https://redhat.atlassian.net/wiki/spaces/RHPDS/pages/493683615)
- `src/api/rcars/services/jira.py` — existing Jira ticket creation (adoc template source of truth)
- `src/api/rcars/services/retirement.py` — workflow step logic
- `src/frontend/src/pages/RetirementPage.tsx` — retirement dashboard
- `src/frontend/src/components/performance/WorkflowDrawer.tsx` — step management UI
