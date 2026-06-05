#!/usr/bin/env bash
# Rebuild and run the full stack locally, tailing logs.
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose up --build
