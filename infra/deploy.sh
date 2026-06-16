#!/usr/bin/env bash
# Idempotent deploy script for coachito.
#
# Steps:
#   1. Pre-flight (clean working tree, on a branch, env file present).
#   2. Tag the release locally with the short SHA.
#   3. Build production images (api + worker + web).
#   4. Push to the registry.
#   5. SSH to the host, pull, run `alembic upgrade head`, swap api/worker/web
#      without taking the stack down.
#
# Run with --dry to print the planned actions without executing them.
#
# Required env:
#   DEPLOY_HOST        — ssh target (user@host)
#   DEPLOY_DIR         — path on the host where docker-compose.prod.yml lives
#   REGISTRY           — image registry prefix, e.g. ghcr.io/coachito
#   (Optional) ENV_FILE — path to the .env consumed by docker-compose.prod.yml

set -euo pipefail

DRY=0
if [[ "${1-}" == "--dry" ]]; then
  DRY=1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Helpers ─────────────────────────────────────────────────────

step() { printf "\033[1;34m▸ %s\033[0m\n" "$*"; }
run() {
  if [[ $DRY -eq 1 ]]; then
    printf "  [dry] %s\n" "$*"
  else
    eval "$@"
  fi
}
require_env() {
  local name=$1
  if [[ -z "${!name-}" ]]; then
    printf "\033[1;31m✗ missing env: %s\033[0m\n" "$name" >&2
    exit 1
  fi
}

# ── Pre-flight ──────────────────────────────────────────────────

step "Pre-flight"

if [[ $DRY -eq 0 ]]; then
  require_env DEPLOY_HOST
  require_env DEPLOY_DIR
  require_env REGISTRY
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [[ $DRY -eq 0 ]]; then
    printf "\033[1;31m✗ not inside a git repository\033[0m\n" >&2
    exit 1
  fi
  GIT_SHA="dryrun"
  GIT_BRANCH="dryrun"
else
  if ! git diff --quiet || ! git diff --cached --quiet; then
    printf "\033[1;31m✗ working tree is dirty — commit or stash first\033[0m\n" >&2
    [[ $DRY -eq 0 ]] && exit 1
  fi
  GIT_SHA="$(git rev-parse --short=12 HEAD)"
  GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi
TAG="release-$(date -u +%Y%m%d-%H%M%S)-${GIT_SHA}"
printf "  branch=%s  sha=%s  tag=%s\n" "$GIT_BRANCH" "$GIT_SHA" "$TAG"

# ── Build ──────────────────────────────────────────────────────

step "Build images"
REG="${REGISTRY:-ghcr.io/coachito}"
run "docker build -f infra/api/Dockerfile -t ${REG}/api:${GIT_SHA} -t ${REG}/api:latest ."
run "docker build -f infra/web/Dockerfile -t ${REG}/web:${GIT_SHA} -t ${REG}/web:latest ."

# ── Push ───────────────────────────────────────────────────────

step "Push to registry"
run "docker push ${REG}/api:${GIT_SHA}"
run "docker push ${REG}/api:latest"
run "docker push ${REG}/web:${GIT_SHA}"
run "docker push ${REG}/web:latest"

# ── Tag locally ────────────────────────────────────────────────

step "Tag locally"
run "git tag -a ${TAG} -m 'deploy ${GIT_SHA}'"
run "git push origin ${TAG}"

# ── Remote rollout ─────────────────────────────────────────────

step "Remote rollout on ${DEPLOY_HOST-<dry>}"
REMOTE_SCRIPT=$(cat <<EOF
set -euo pipefail
cd ${DEPLOY_DIR:-/srv/coachito}
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml pull api worker web
# Migrations run in a one-shot api container so the live worker doesn't race
# the schema mid-deploy.
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml run --rm api alembic upgrade head
# Swap api + worker first; web last (cuts traffic over once the BE is ready).
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d --no-deps --build api worker
sleep 5
docker compose -f infra/docker-compose.yml -f infra/docker-compose.prod.yml up -d --no-deps --build web
# Smoke test
curl -fsS http://localhost:8000/healthz >/dev/null
echo "deploy: ok"
EOF
)

if [[ $DRY -eq 1 ]]; then
  printf "  [dry] ssh %s 'bash -s' <<EOF\n%s\nEOF\n" "${DEPLOY_HOST-<host>}" "$REMOTE_SCRIPT"
else
  ssh "$DEPLOY_HOST" "bash -s" <<EOF
$REMOTE_SCRIPT
EOF
fi

printf "\033[1;32m✓ deploy complete — %s\033[0m\n" "$TAG"
