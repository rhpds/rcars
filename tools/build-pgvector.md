# Building the rcars-pgvector Image

Multi-arch build for `quay.io/rhpds/rcars-pgvector`.

## Prerequisites

- `podman` with the `agnosticd` machine running
- Logged in to quay.io: `podman login quay.io`

## Build & Push

The OpenShift cluster runs `linux/amd64`, so force that architecture even from an ARM Mac:

```bash
# Build for amd64 (matches the OCP cluster architecture)
podman build --platform linux/amd64 \
  -t quay.io/rhpds/rcars-pgvector:0.8.0-pg16 \
  -f - . <<'EOF'
FROM pgvector/pgvector:0.8.0-pg16
LABEL maintainer="nstephan@redhat.com"
LABEL description="pgvector 0.8.0 on PostgreSQL 16 for RCARS"
EOF

# Push to quay.io
podman push quay.io/rhpds/rcars-pgvector:0.8.0-pg16
```

## Updating the version

When upgrading pgvector, change the tag in both places:
1. The `FROM` line and `-t` flag in the build command above
2. `ansible/vars/common.yml` → `pg_image`

## Why this exists

The original image (`pgvector/pgvector` from Docker Hub) is a third-party image
without Red Hat scanning. Mirroring to quay.io gives us a controlled, scannable
copy in a trusted registry. See security audit v3 finding M-9.
