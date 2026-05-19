#!/bin/bash
set -e

BASHRC="$HOME/.bashrc"

set_env() {
  local key=$1 val=$2
  if grep -q "^export $key=" "$BASHRC" 2>/dev/null; then
    sed -i "s|^export $key=.*|export $key=\"$val\"|" "$BASHRC"
  else
    echo "export $key=\"$val\"" >> "$BASHRC"
  fi
}

prompt() {
  local key=$1 default=$2 secret=$3 val
  if [ -n "$secret" ]; then
    read -rsp "  $key${default:+ [$default]}: " val; echo
  else
    read -rp  "  $key${default:+ [$default]}: " val
  fi
  [ -z "$val" ] && val="$default"
  [ -n "$val" ] && set_env "$key" "$val"
}

echo ""
echo "=== Dominion Environment Setup ==="
echo ""

echo "[ AWS ]"
prompt AWS_ACCESS_KEY_ID     ""            secret
prompt AWS_SECRET_ACCESS_KEY ""            secret
prompt AWS_DEFAULT_REGION    "us-east-1"   ""

echo ""
echo "[ RAGD Embeddings ]"
prompt RAGD_EMBED_PROVIDER   "bedrock"                        ""
prompt RAGD_EMBED_MODEL      "amazon.titan-embed-text-v2:0"   ""

echo ""
echo "[ GitHub ]"
prompt GITHUB_PERSONAL_ACCESS_TOKEN "" secret

echo ""
echo "[ Greptile ]"
prompt GREPTILE_API_KEY "" secret

source "$BASHRC"

echo ""
echo "=== Status ==="
for key in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION \
            RAGD_EMBED_PROVIDER RAGD_EMBED_MODEL \
            GITHUB_PERSONAL_ACCESS_TOKEN GREPTILE_API_KEY; do
  val="${!key}"
  if [ -n "$val" ]; then
    echo "  ✅ $key=${val:0:6}..."
  else
    echo "  ❌ $key not set"
  fi
done

echo ""
echo "Run: source ~/.bashrc"
