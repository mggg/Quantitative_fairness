#!/usr/bin/env bash
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)" || exit

exec uv run --project "$REPO_ROOT" --locked python "$REPO_ROOT/scripts/replicate.py" portland "$@"
