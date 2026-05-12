#!/bin/bash
set -euo pipefail

systemctl --user disable --now ragd 2>/dev/null || true
rm -f "$HOME/.config/systemd/user/ragd.service"
systemctl --user daemon-reload 2>/dev/null || true

sudo rm -f /usr/local/bin/ragd /usr/local/bin/ragd-cli \
  /usr/local/bin/ragd-query /usr/local/bin/ragd-remember /usr/local/bin/ragd-todo \
  /usr/local/bin/ragd-handoff /usr/local/bin/ragd-warn /usr/local/bin/ragd-todos \
  /usr/local/bin/ragd-session-start /usr/local/bin/ragd-session-end \
  /etc/profile.d/ragd.sh

echo "RAGD binaries, shell hook, and user service were removed. Database under ~/.ragd was left intact."
