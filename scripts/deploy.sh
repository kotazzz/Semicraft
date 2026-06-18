#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing dependencies"
npm ci

echo "==> Installing Quartz plugins"
npx quartz plugin install --from-config

echo "==> Building site"
npx quartz build

echo "==> Reloading web container"
docker compose restart semicraft-web

echo "==> Done."
