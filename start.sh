#!/usr/bin/env bash
#
# Render Start Command.
#
# Runs the FastAPI app (which also serves the built React UI from
# frontend/dist). The frontend build + dependency install happen earlier, in
# build.sh — Node is only available during Render's build phase, not at runtime,
# so nothing is compiled here.
#
# Render dashboard → Start Command:  ./start.sh
set -euo pipefail

# Resolve to the repo root regardless of where Render invokes the script.
cd "$(dirname "$0")/backend"

# Render provides $PORT; default to 8000 for local use.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
