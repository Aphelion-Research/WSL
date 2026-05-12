#!/usr/bin/env bash
set -euo pipefail
prefix="${PREFIX:-$HOME/.local}"
rm -f "$prefix/bin/ragd" "$prefix/bin/ragd-query" "$prefix/bin/ragd-remember" "$prefix/bin/ragd-todo" "$prefix/bin/ragd-handoff" "$prefix/bin/ragd-warn" "$prefix/bin/ragd-todos" "$prefix/bin/ragd-session-start" "$prefix/bin/ragd-session-end"
rm -f "$HOME/.config/systemd/user/ragd.service"
echo "RAGD binaries removed. Database under ~/.ragd was not deleted."
