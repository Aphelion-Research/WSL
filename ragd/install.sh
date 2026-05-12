#!/usr/bin/env bash
set -euo pipefail

prefix="${PREFIX:-$HOME/.local}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$HOME/.ragd" "$prefix/bin"
if [ ! -f "$HOME/.ragd/config.json" ]; then
  printf '{\n  "db_path": "%s/.ragd/ragd.sqlite",\n  "host": "127.0.0.1",\n  "port": 7474\n}\n' "$HOME" > "$HOME/.ragd/config.json"
fi

cmake -S "$root" -B "$root/build" -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$root/build" -j"$(nproc)"
cp "$root/build/ragd" "$prefix/bin/ragd"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-query"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-remember"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-todo"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-handoff"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-warn"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-todos"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-session-start"
cp "$root/scripts/ragd-cli.sh" "$prefix/bin/ragd-session-end"
chmod +x "$prefix/bin"/ragd*
mkdir -p "$HOME/.config/systemd/user"
cp "$root/scripts/ragd.service" "$HOME/.config/systemd/user/ragd.service"
echo "Installed ragd to $prefix/bin. Start manually with: ragd --db ~/.ragd/ragd.sqlite"
