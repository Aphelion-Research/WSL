#!/usr/bin/env bash
set -euo pipefail
exec "$HOME/Dominion/ragd/build/ragd" --db "$HOME/.ragd/ragd.sqlite" --host 127.0.0.1 --port 7474 --path "$HOME/Dominion/docs" --path "$HOME/Dominion/ragd/docs" "$@"
