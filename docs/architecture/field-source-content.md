---
title: Field Source Content
description: How RCARS tracks which Git repositories field teams use when deploying OCP and RHEL content
---

# Field Source Content

Field Source Content is a visibility report that shows which Git repositories field teams provide when ordering OCP and RHEL catalog items. It helps curators understand what content is being deployed in the field and whether automation repositories are being used consistently.

## Data Source

The data comes from the RHDP reporting database via the same MCP server used for [Performance Analysis](performance-analysis.md). RCARS queries the `provisions` and `resource_claim_log` tables to extract Git repository URLs from each provision's `parameterValues`.

Two catalog items are tracked:

| Item | Catalog ID | Repo Parameter | Ref Parameter |
|---|---|---|---|
| OCP | 1969802 | `ocp4_workload_field_content_gitops_repo_url` | `ocp4_workload_field_content_gitops_repo_ref` |
| RHEL | 1970262 | `vm_workload_field_content_git_repo_url` | `vm_workload_field_content_git_repo_ref` |

No environment filter is applied — RHEL currently has only DEV provisions, so all environments are included to give a complete usage picture.

## Data Import

Field source data is imported as a sub-step of the reporting sync during the nightly Babylon pipeline (step 5b). It can also be triggered independently via `rcars reporting-db sync --field-source` or as a standalone job from the Sync page.

The sync performs a full replace: all existing rows are deleted and replaced with fresh data from the reporting MCP. The query pulls provisions from the trailing 12 calendar months. Each provision's UUID serves as the unique key.

Data is stored in the `field_source_provisions` table:

| Column | Type | Purpose |
|---|---|---|
| `catalog_item` | `TEXT` | `ocp` or `rhel` |
| `git_repo` | `TEXT` | Repository URL from provision parameters |
| `git_ref` | `TEXT` | Branch or tag reference |
| `provisioned_at` | `TIMESTAMPTZ` | When the provision was created |
| `retired_at` | `TIMESTAMPTZ` | When the provision was retired (nullable) |
| `provision_uuid` | `UUID UNIQUE` | Provision identifier from the reporting DB |

## API

`GET /api/v1/analysis/field-source` — returns all field source provisions, grouped by repository and ref. Accepts an optional `catalog_item` query parameter (`ocp` or `rhel`) to filter.

The response groups provisions by `(git_repo, git_ref, catalog_item)` and includes per-group counts, first/last seen dates, and the individual provision list for expanded row detail.

## Frontend

The Field Source Content page is under **Analysis > Field Source Content** in the sidebar. It shows:

- **Stat cards** — OCP repos, RHEL repos, total provisions
- **Sidebar filter pills** — filter by OCP or RHEL
- **Search bar** — filter by repository name
- **Sortable table** — repository, ref, type, provisions, first/last used
- **Expandable rows** — click a row to see individual provision dates

No PII is stored or displayed — the report shows repository URLs and provision dates only.
