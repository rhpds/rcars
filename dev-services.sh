#!/usr/bin/env bash
# RCARS v2 local development services
# Starts PostgreSQL, Redis, API, Worker, and Frontend for local development.
#
# Usage:
#   ./dev-services.sh start    # Start all services
#   ./dev-services.sh stop     # Stop all services
#   ./dev-services.sh restart  # Restart all services
#   ./dev-services.sh status   # Show service status

set -euo pipefail

PG_CONTAINER="rcars-postgres"
REDIS_CONTAINER="rcars-redis"
PG_IMAGE="pgvector/pgvector:pg16"
REDIS_IMAGE="redis:7"
VENV="${HOME}/.virtualenvs/rcars-v2"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_DIR="${PROJECT_DIR}/src/api"
FRONTEND_DIR="${PROJECT_DIR}/src/frontend"

export RCARS_DATABASE_URL="postgresql://rcars:dev@localhost:5432/rcars"
export RCARS_REDIS_URL="redis://localhost:6379"
export RCARS_DEV_USER="${RCARS_DEV_USER:-dev@redhat.com}"
export RCARS_ADMIN_EMAILS="${RCARS_ADMIN_EMAILS:-dev@redhat.com}"
export RCARS_CURATOR_EMAILS="${RCARS_CURATOR_EMAILS:-dev@redhat.com}"

start_postgres() {
    if podman ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
        echo "  PostgreSQL already running"
        return
    fi
    podman start "${PG_CONTAINER}" 2>/dev/null || \
        podman run -d --name "${PG_CONTAINER}" \
            -e POSTGRES_USER=rcars -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=rcars \
            -p 5432:5432 "${PG_IMAGE}" >/dev/null
    sleep 2
    echo "  ✓  localhost:5432"
}

start_redis() {
    if podman ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
        echo "  Redis already running"
        return
    fi
    podman start "${REDIS_CONTAINER}" 2>/dev/null || \
        podman run -d --name "${REDIS_CONTAINER}" \
            -p 6379:6379 "${REDIS_IMAGE}" >/dev/null
    echo "  ✓  localhost:6379"
}

start_api() {
    if pgrep -f "uvicorn rcars.api" >/dev/null 2>&1; then
        echo "  API already running"
        return
    fi
    cd "${API_DIR}"
    "${VENV}/bin/uvicorn" rcars.api.app:create_app --factory --reload --port 8080 \
        > /tmp/rcars-api.log 2>&1 &
    echo "  ✓  localhost:8080"
    cd "${PROJECT_DIR}"
}

start_worker() {
    if pgrep -f "arq rcars.workers" >/dev/null 2>&1; then
        echo "  Worker already running"
        return
    fi
    cd "${API_DIR}"
    "${VENV}/bin/arq" rcars.workers.WorkerSettings \
        > /tmp/rcars-worker.log 2>&1 &
    echo "  ✓  localhost (background)"
    cd "${PROJECT_DIR}"
}

start_frontend() {
    if pgrep -f "vite.*3000" >/dev/null 2>&1; then
        echo "  Frontend already running"
        return
    fi
    cd "${FRONTEND_DIR}"
    npx vite --port 3000 > /tmp/rcars-frontend.log 2>&1 &
    echo "  ✓  localhost:3000"
    cd "${PROJECT_DIR}"
}

init_db() {
    cd "${API_DIR}"
    "${VENV}/bin/rcars" init-db 2>/dev/null || true
    cd "${PROJECT_DIR}"
}

start() {
    echo "Starting RCARS dev environment..."
    echo ""
    echo "Starting PostgreSQL (podman)..."
    start_postgres
    echo "Starting Redis (podman)..."
    start_redis
    echo "Initializing database..."
    init_db
    echo "Starting API (uvicorn --reload)..."
    start_api
    echo "Starting Worker (arq)..."
    start_worker
    echo "Starting Frontend (vite dev)..."
    start_frontend
    echo ""
    echo "RCARS dev environment ready."
    echo "Frontend:  http://localhost:3000"
    echo "API docs:  http://localhost:8080/api/v1/docs"
    echo "Logs:      /tmp/rcars-*.log"
}

stop() {
    echo "Stopping services..."
    pkill -f "uvicorn rcars" 2>/dev/null || true
    pkill -f "arq rcars" 2>/dev/null || true
    pkill -f "vite.*3000" 2>/dev/null || true
    podman stop "${REDIS_CONTAINER}" 2>/dev/null || true
    podman stop "${PG_CONTAINER}" 2>/dev/null || true
    echo "Stopped."
}

show_status() {
    echo "RCARS Service Status:"
    echo ""
    if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${PG_CONTAINER}$"; then
        echo "  PostgreSQL:  ✓ running (localhost:5432)"
    else
        echo "  PostgreSQL:  ✗ stopped"
    fi
    if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${REDIS_CONTAINER}$"; then
        echo "  Redis:       ✓ running (localhost:6379)"
    else
        echo "  Redis:       ✗ stopped"
    fi
    if pgrep -f "uvicorn rcars" >/dev/null 2>&1; then
        echo "  API:         ✓ running (localhost:8080)"
    else
        echo "  API:         ✗ stopped"
    fi
    if pgrep -f "arq rcars" >/dev/null 2>&1; then
        echo "  Worker:      ✓ running"
    else
        echo "  Worker:      ✗ stopped"
    fi
    if pgrep -f "vite.*3000" >/dev/null 2>&1; then
        echo "  Frontend:    ✓ running (localhost:3000)"
    else
        echo "  Frontend:    ✗ stopped"
    fi
}

case "${1:-start}" in
    start)   start ;;
    stop)    stop ;;
    restart) stop; sleep 1; start ;;
    status)  show_status ;;
    *)       echo "Usage: $0 {start|stop|restart|status}" ;;
esac
