#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REMOTE="${SEMICRAFT_REMOTE:-me}"
REMOTE_DIR="${SEMICRAFT_REMOTE_DIR:-Semicraft}"
BRANCH="${SEMICRAFT_BRANCH:-main}"
REPO_URL="${SEMICRAFT_REPO_URL:-https://github.com/kotazzz/Semicraft.git}"
SITE_URL="${SEMICRAFT_SITE_URL:-https://semi.kotaz.ru}"

usage() {
  echo "Usage: $0 \"commit message\""
  echo
  echo "Commits local changes, pushes to GitHub, and deploys on the server."
  exit 1
}

MSG="${1:-}"
[[ -n "$MSG" ]] || usage

if [[ -n "$(git status --porcelain)" ]]; then
  echo "==> Committing changes"
  git add -A
  git commit -m "$MSG"
else
  echo "==> No local changes to commit"
fi

echo "==> Pushing to origin/$BRANCH"
git push origin "$BRANCH"

echo "==> Deploying on $REMOTE"
ssh "$REMOTE" "bash -s" -- "$REMOTE_DIR" "$BRANCH" "$REPO_URL" <<'REMOTE'
set -euo pipefail
REMOTE_DIR="$1"
BRANCH="$2"
REPO_URL="$3"
HOME_DIR="$HOME/$REMOTE_DIR"

export PATH="$HOME/.local/share/fnm:$PATH"
eval "$(fnm env --shell bash)" 2>/dev/null || true

if [[ ! -d "$HOME_DIR/.git" ]]; then
  echo "==> Cloning repository to $HOME_DIR"
  if [[ -d "$HOME_DIR" ]]; then
    BACKUP="${HOME_DIR}.bak.$(date +%s)"
    echo "==> Backing up existing directory to $BACKUP"
    mv "$HOME_DIR" "$BACKUP"
  fi
  git clone --branch "$BRANCH" "$REPO_URL" "$HOME_DIR"
fi

cd "$HOME_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
./scripts/deploy.sh
REMOTE

echo "==> Published: $SITE_URL"
