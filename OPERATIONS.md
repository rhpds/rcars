# RCARS — Operations Reference

Internal notes on how the deployment and CI are wired up. Not published.

---

## GitHub Actions Workflows

Two workflows in `.github/workflows/`:

### `docs.yml` — Documentation site
Triggers on push to `main` when any of these change: `docs/**`, `mkdocs.yml`, `requirements-docs.txt`.
Builds the MkDocs site and deploys to GitHub Pages via the Actions-native Pages deploy.
Can also be triggered manually from the Actions tab (workflow_dispatch).

### `build.yml` — OpenShift application build
Triggers on push to `main`, **except** when the only changes are docs files.
Calls the OpenShift BuildConfig webhook URL stored in `OPENSHIFT_BUILD_WEBHOOK_URL` (GitHub secret).
Does not deploy — it only triggers the OpenShift image build. Deploy still requires the Ansible playbook.

---

## OpenShift Build Webhook

The webhook URL that triggers an OpenShift image build is stored as a GitHub Actions secret:

**Settings → Secrets and variables → Actions → `OPENSHIFT_BUILD_WEBHOOK_URL`**

To find or rotate the URL:
```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig \
  oc describe bc/rcars -n rcars-dev | grep -A2 "Generic"
```

The old direct GitHub → OpenShift webhook (previously in repo Settings → Webhooks) was removed when `build.yml` was added. All builds now go through GitHub Actions.

---

## GitHub Pages

- **Source:** GitHub Actions (not "Deploy from branch")
- **Visibility:** Private (members of the rhpds org only)
- **URL:** https://rhpds.github.io/rcars/
- **Branch:** No branch to manage — the workflow uploads a Pages artifact directly

The Pages visibility setting is in **Settings → Pages → Visibility → Private**.
If Pages stops working, check that the `github-pages` environment exists under **Settings → Environments** — the deploy job creates it automatically on first run.

---

## Deployment (Application)

```bash
# Full deploy (build + manifests + rollout)
ansible-playbook ansible/deploy.yml -e env=dev --tags update

# Manifests only (no build)
ansible-playbook ansible/deploy.yml -e env=dev --tags apply

# Build only (no deploy)
ansible-playbook ansible/deploy.yml -e env=dev --tags builds

# Schema setup only
ansible-playbook ansible/deploy.yml -e env=dev --tags migrate
```

Kubeconfig: `~/devel/secrets/rcars-mgmt.kubeconfig`

---

## Pod CLI Access

```bash
KUBECONFIG=~/devel/secrets/rcars-mgmt.kubeconfig \
  oc exec -it deployment/rcars -n rcars-dev -- rcars <command>
```

Common commands: `rcars status`, `rcars refresh`, `rcars scan --max 5`

---

## Secrets and Credentials

| What | Where |
|---|---|
| OCP mgmt kubeconfig | `~/devel/secrets/rcars-mgmt.kubeconfig` |
| GCP Vertex credentials | `~/devel/secrets/gcp-vertex-key.json` |
| OpenShift build webhook URL | GitHub secret: `OPENSHIFT_BUILD_WEBHOOK_URL` |
| App config (DB URL, curator emails, etc.) | OpenShift Secret in `rcars-dev` namespace |
