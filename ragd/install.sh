#!/bin/bash
set -euo pipefail

echo "Installing RAGD - Blackmark Dominion RAG Daemon"

sudo apt-get update -qq
sudo apt-get install -y -qq build-essential cmake git curl jq libsqlite3-dev libssl-dev libgit2-dev pkg-config

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
sudo cmake --install build --prefix /usr/local

mkdir -p "$HOME/.ragd"
[ ! -f "$HOME/.ragd/config.json" ] && cp scripts/config.default.json "$HOME/.ragd/config.json"
echo "Config at: $HOME/.ragd/config.json"

sudo cp scripts/ragd-cli.sh /usr/local/bin/ragd-cli
sudo chmod +x /usr/local/bin/ragd-cli
for cmd in ragd-query ragd-remember ragd-todo ragd-handoff ragd-warn ragd-todos ragd-session-start ragd-session-end; do
  sudo ln -sf /usr/local/bin/ragd-cli "/usr/local/bin/$cmd"
done

sudo cp scripts/ragd.sh /etc/profile.d/ragd.sh
sudo chmod +x /etc/profile.d/ragd.sh

mkdir -p "$HOME/.config/systemd/user"
cp scripts/ragd.service "$HOME/.config/systemd/user/ragd.service"
systemctl --user daemon-reload || true
systemctl --user enable ragd || true
systemctl --user restart ragd || true

mkdir -p .claude .cursor
cat > .claude/mcp_config.json <<'JSON'
{
  "mcpServers": {
    "ragd": {
      "url": "http://localhost:7474/mcp",
      "transport": "http"
    }
  }
}
JSON
cp .claude/mcp_config.json .cursor/mcp.json

echo ""
echo "RAGD installed."
echo "Query: curl http://localhost:7474/health"
echo "Docs:  cat docs/api_reference.md"
echo "Init:  source scripts/agent-init.sh claude-code"
