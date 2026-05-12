#!/bin/bash
export RAGD_ENDPOINT="${RAGD_ENDPOINT:-http://localhost:7474}"
export RAGD_SOCKET="${RAGD_SOCKET:-/tmp/ragd.sock}"

if ! curl -sf "$RAGD_ENDPOINT/health" > /dev/null 2>&1; then
  if command -v ragd > /dev/null 2>&1; then
    ragd --daemon > "${HOME:-/tmp}/.ragd/ragd.autostart.log" 2>&1 &
    sleep 0.5
  fi
fi
