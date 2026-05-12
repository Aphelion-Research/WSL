#!/usr/bin/env bash
curl -s http://localhost:7474/query -d '{"query":"Dominion MT5 collector","mode":"hybrid","limit":5}'
