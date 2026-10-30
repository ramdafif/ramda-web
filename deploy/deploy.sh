#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
expected_branch='web-pribadi/NEW'
if [[ "$(git branch --show-current)" != "$expected_branch" ]]; then
    printf 'Deploy requires branch %s\n' "$expected_branch" >&2
    exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
    printf 'Working tree must be clean before deploy.\n' >&2
    exit 1
fi
git pull --ff-only origin "$expected_branch"
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install --disable-pip-version-check -r backend/requirements.lock
npm --prefix frontend ci
npm --prefix frontend run check
npm --prefix frontend run build
mkdir -p backend/instance frontend/.astro var/uploads var/backups
backend/.venv/bin/python deploy/migrate.py
sudo systemctl restart ramda-backend ramda-frontend
backend/.venv/bin/python deploy/healthcheck.py
