---
doc_type: development
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - development
  - setup
  - installation
---

# Local Setup Guide

**Purpose:** First-time setup for Dominion development.

---

## Prerequisites

**Required:**
- WSL2/Debian (or Linux)
- Python 3.11+
- Git
- 4+ GB RAM
- 10+ GB disk space

**Optional:**
- CMake 3.20+ (for native C++ core)
- GCC 11+ (for native C++ core)
- Obsidian (for vault browsing)

---

## Quick Start (5 minutes)

```bash
# Clone repo
cd ~
git clone https://github.com/yourusername/Dominion.git
cd Dominion

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Bootstrap
./scripts/bootstrap_python.sh

# Validate
python -m pytest -q
python domdata/check_no_trading.py
```

If all pass → setup complete.

---

## Detailed Setup

### 1. System Packages

**Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install -y \
  python3.11 \
  python3.11-venv \
  python3-pip \
  git \
  build-essential \
  cmake \
  pkg-config \
  libsqlite3-dev
```

**Verify:**
```bash
python3.11 --version  # Should be ≥3.11
cmake --version       # Should be ≥3.20
gcc --version         # Should be ≥11
```

---

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/Dominion.git
cd Dominion
```

**Check branch:**
```bash
git branch  # Should be on 'main'
git status  # Should be clean
```

---

### 3. Python Environment

```bash
# Create virtualenv
python3.11 -m venv .venv

# Activate
source .venv/bin/activate

# Verify
which python  # Should be ~/Dominion/.venv/bin/python
python --version  # Should be 3.11.x
```

**Add to bashrc (optional):**
```bash
echo 'alias dominion-env="cd ~/Dominion && source .venv/bin/activate"' >> ~/.bashrc
source ~/.bashrc
```

Now: `dominion-env` activates environment.

---

### 4. Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Verify:**
```bash
pip list | grep -E "pytest|pandas|numpy|duckdb|sqlalchemy"
```

Should see all major dependencies.

---

### 5. Build Native Core (Optional but Recommended)

```bash
# Configure
cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo

# Build
cmake --build ragd/build -j$(nproc)

# Test
ctest --test-dir ragd/build --output-on-failure
```

**Expected:** 24/24 tests passing.

---

### 6. Bootstrap Platform

```bash
./scripts/bootstrap_python.sh
```

**This script:**
- Validates Python environment
- Checks dependencies
- Runs quick smoke tests
- Validates embedding stats
- Checks domdata

**Expected:** All checks pass (some warnings OK).

---

### 7. Validate Setup

```bash
# Core validation
python -m pytest -q                 # Should pass (426+ tests)
python domdata/check_no_trading.py  # Should output "PASS"

# C++ validation (if built)
ctest --test-dir ragd/build --output-on-failure  # 24/24 pass

# Platform health
python scripts/dominion_cli.py doctor --offline --json
```

**Expected:**
- All Python tests pass
- Trading check: PASS
- Doctor: `overall: warn` or `overall: ok`

---

### 8. Configure Environment (Optional)

**Set API keys (if needed):**
```bash
# Create .env file
cat > .env << 'EOF'
ALPHAVANTAGE_API_KEY=your_key_here
FRED_API_KEY=your_key_here
RAGD_EMBED_API_KEY=your_key_here
EOF

# Load in shell
source .env
export ALPHAVANTAGE_API_KEY
export FRED_API_KEY
export RAGD_EMBED_API_KEY
```

**Or add to bashrc:**
```bash
echo 'export ALPHAVANTAGE_API_KEY="your_key"' >> ~/.bashrc
echo 'export FRED_API_KEY="your_key"' >> ~/.bashrc
source ~/.bashrc
```

---

### 9. Start RAGD Daemon (Optional)

```bash
# Start in tmux
tmux new -s ragd

# Inside tmux
cd ~/Dominion
source .venv/bin/activate
ragd/build/ragd --db data/ragd.db --host 127.0.0.1 --port 7474 --daemon

# Detach: Ctrl+B, D
```

**Verify:**
```bash
curl http://127.0.0.1:7474/health
# Should output: {"status":"ok"}
```

---

### 10. Open Obsidian Vault (Optional)

**If you use Obsidian:**
1. Open Obsidian
2. "Open folder as vault"
3. Select: `~/Dominion/vault/`
4. Browse Home.md

---

## Verify Everything Works

```bash
# Quick smoke test
cd ~/Dominion
source .venv/bin/activate

# 1. Tests
python -m pytest -q
# Expected: 426+ passed

# 2. Trading check
python domdata/check_no_trading.py
# Expected: PASS

# 3. C++ tests (if built)
ctest --test-dir ragd/build
# Expected: 24/24 passed

# 4. Platform health
python scripts/dominion_cli.py doctor --offline --json
# Expected: overall: warn or ok

# 5. RAGD (if daemon running)
curl http://127.0.0.1:7474/health
# Expected: {"status":"ok"}

# 6. Quick query
python scripts/dominion_cli.py search "agent workflow" --top-k 3
# Expected: 3 results
```

If all pass → **Setup complete ✓**

---

## Troubleshooting

### Python version wrong

```bash
# Check available versions
ls /usr/bin/python*

# Use specific version
python3.11 -m venv .venv
```

### Missing dependencies

```bash
# Reinstall
pip install --upgrade --force-reinstall -r requirements.txt
```

### CMake not found

```bash
# Install
sudo apt install cmake

# Or download from https://cmake.org/download/
```

### Tests fail

```bash
# Run with verbose output
python -m pytest -v

# Run specific test
python -m pytest -v path/to/test.py::test_name

# Check for missing dependencies
pip list
```

### RAGD daemon won't start

```bash
# Check port availability
lsof -i :7474

# Kill existing process
pkill ragd

# Try again
ragd/build/ragd --db data/ragd.db --host 127.0.0.1 --port 7474
```

### domdata check fails

```bash
# Check Wine installation (if using MT5)
which wine

# Check MT5 secrets exist
ls -la secrets/mt5.env

# Check domdata CLI
python -m domdata.cli --help
```

---

## Next Steps

After setup:

1. **Read docs:**
   - [docs/INDEX.md](../INDEX.md)
   - [docs/AGENT_README.md](../AGENT_README.md) (if you're an agent)
   - [docs/HUMAN_README.md](../HUMAN_README.md) (if you're human)

2. **Explore codebase:**
   ```bash
   find . -name "*.py" -not -path "./.venv/*" | head -20
   ```

3. **Run data pipeline:**
   ```bash
   python -m data_pipeline.cli status
   ```

4. **Query RAGD:**
   ```bash
   python scripts/dominion_cli.py search "system architecture" --top-k 5
   ```

5. **Browse vault (if Obsidian installed):**
   Open `vault/Home.md`

---

## For New Contributors

**Read these first:**
1. [/README.md](/README.md)
2. [/AGENTS.md](/AGENTS.md)
3. [docs/AGENT_README.md](../AGENT_README.md)
4. [docs/04_DEVELOPMENT/CODING_STANDARDS.md](CODING_STANDARDS.md)

**Then:**
- Pick issue from backlog
- Ask questions in tmux or chat
- Follow agent workflow
- Write tests
- Submit PR (or commit to main if core team)

---

## Related Docs

- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [DEBUGGING_GUIDE.md](DEBUGGING_GUIDE.md)
- [docs/COLLABORATION.md](../COLLABORATION.md)

---

## Retrieval Hints

- "setup"
- "installation"
- "getting started"
- "first time setup"
- "how to install"
