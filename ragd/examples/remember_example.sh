#!/usr/bin/env bash
curl -s http://localhost:7474/memory/decision -d '{"session_id":"example","text":"RAGD should never index secrets."}'
