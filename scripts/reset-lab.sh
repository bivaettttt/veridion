#!/bin/sh
set -eu

# Use a separate Compose project and its own PostgreSQL volume.
project=veridion-sandbox
export VERIDION_WEB_PORT=3818 VERIDION_API_PORT=8818 VERIDION_DEMO=1
docker compose -f compose.yaml -p "$project" down -v
docker compose -f compose.yaml -p "$project" up -d --build --wait
