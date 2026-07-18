#!/usr/bin/env bash
#
# Render Build Command.
#
# Builds the React frontend (Node/npm are available in Render's build phase) and
# installs the backend Python dependencies. The compiled UI lands in
# frontend/dist, which FastAPI serves at runtime (see start.sh).
#
# Render dashboard → Build Command:  ./build.sh
set -euo pipefail

# Resolve to the repo root regardless of where Render invokes the script.
cd "$(dirname "$0")"

echo "==> Building frontend"
cd frontend
npm ci
npm run build

echo "==> Installing backend dependencies"
cd ../backend
pip install -r requirements.txt

echo "==> Build complete"
