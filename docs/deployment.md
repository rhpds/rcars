# RCARS Deployment Guide

## Prerequisites

- `oc` CLI logged into the target cluster (`your-cluster`)
- `ansible` with `kubernetes.core` collection
- Read-only kubeconfig for the Babylon cluster
- Vertex AI service account JSON key
- GitHub personal access token (for webhook registration)

### Install Ansible Dependencies

    ansible-galaxy collection install -r ansible/requirements.yml

## Initial Deployment

### 1. Create your vars file

    cd ansible/vars
    cp dev.yml.example dev.yml

Edit `dev.yml` and fill in all `CHANGEME` values:

- `pg_password` — generate with `openssl rand -hex 16`
- `oauth_client_secret` — generate with `openssl rand -hex 16`
- `oauth_cookie_secret` — generate with `openssl rand -hex 16`
- `webhook_secret` — generate with `openssl rand -hex 16`
- `babylon_kubeconfig_path` — path to your Babylon read-only kubeconfig
- `vertex_credentials_json` — paste contents of your GCP JSON key
- `vertex_project_id` — your GCP project ID
- `github_token` — GitHub PAT with repo access
- `curator_emails` / `admin_emails` — comma-separated email lists

### 2. Run the playbook

    ansible-playbook ansible/deploy.yml -e env=dev

This will:
1. Create the `rcars-dev` namespace
2. Apply all secrets, deployments, services, routes, and BuildConfig
3. Trigger the first Docker build from GitHub
4. Wait for the build to complete (~3-5 minutes)
5. Run Alembic database migrations
6. Display the webhook URL for GitHub

### 3. Configure GitHub webhook

The playbook prints a webhook URL at the end. Add it to your GitHub repo:

1. Go to `https://github.com/<your-repo>/settings/hooks`
2. Click "Add webhook"
3. Paste the URL from the playbook output
4. Content type: `application/json`
5. Secret: the `webhook_secret` value from your vars file
6. Events: "Just the push event"

### 4. Verify

Open `https://rcars-dev.apps.your-cluster.example.com`

You should see the OpenShift SSO login page. After authenticating, RCARS loads with your email in the header.

## Day-to-Day Operations

### Code update (after push to main)

If webhooks are configured, the build triggers automatically. Then:

    ansible-playbook ansible/deploy.yml -e env=dev --tags update

This waits for the build, restarts the app, and runs any new migrations.

### Just run migrations

    ansible-playbook ansible/deploy.yml -e env=dev --tags migrate

### Just restart the app (no build)

    oc rollout restart deployment/rcars -n rcars-dev

### Check logs

    oc logs deployment/rcars -n rcars-dev -f

### Run CLI commands on the pod

    oc exec deployment/rcars -n rcars-dev -- rcars status
    oc exec deployment/rcars -n rcars-dev -- rcars refresh
    oc exec deployment/rcars -n rcars-dev -- rcars scan --max 5

## Production Deployment

Same process but with `prod` vars:

    cp ansible/vars/prod.yml.example ansible/vars/prod.yml
    # Edit prod.yml with production values
    ansible-playbook ansible/deploy.yml -e env=prod

Production builds from the `production` branch. Promote by merging `main → production`.

## Troubleshooting

### Build fails

    oc logs bc/rcars -n rcars-dev

### Pod won't start

    oc describe pod -l app=rcars,component=app -n rcars-dev
    oc logs deployment/rcars -n rcars-dev

### Database connection issues

    oc exec deployment/rcars -n rcars-dev -- python -c "
    from rcars.config import Settings
    s = Settings()
    print(f'DB URL: {s.database_url[:30]}...')
    from rcars.db import Database
    db = Database(s.database_url)
    print('Connected OK')
    db.close()
    "

### OAuth proxy issues

    oc logs deployment/rcars-oauth-proxy -n rcars-dev
