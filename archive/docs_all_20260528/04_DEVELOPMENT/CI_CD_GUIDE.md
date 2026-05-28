---
doc_type: guide
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - developer
status: active
last_reviewed: 2026-05-19
tags:
  - ci-cd
  - deployment
  - automation
---

# CI/CD Guide

**Purpose:** Continuous Integration / Continuous Deployment for Dominion V2.

**Status:** Manual deployment (Phase 5). CI/CD planned Phase 10.

---

## Current State (Phase 5)

**Deployment Process (Manual):**
```bash
# 1. Pull latest
git pull origin main

# 2. Run tests
pytest tests/ -v

# 3. Restart services
sudo systemctl restart dominion

# 4. Verify
curl http://127.0.0.1:7474/health
```

**Issues:**
- Slow (30 min)
- Error-prone (forgot step 3 once)
- No rollback (if deploy fails)

---

## Target State (Phase 10)

**Automated CI/CD:**
1. Push to main
2. GitHub Actions runs tests
3. If pass: Deploy automatically
4. If fail: Alert + rollback

**Time:** 5 min (automated).

---

## CI Pipeline (GitHub Actions)

### Workflow: .github/workflows/ci.yml

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Lint
        run: |
          black --check src/
          flake8 src/
          mypy src/
      
      - name: Unit tests
        run: pytest tests/unit/ -v --cov=src --cov-report=xml
      
      - name: Integration tests
        run: pytest tests/integration/ -v
      
      - name: Coverage report
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
      
      - name: Security scan
        run: |
          pip install bandit
          bandit -r src/ -ll
```

**Triggers:**
- Every push (all branches)
- Every pull request

**Duration:** ~5 min

---

## CD Pipeline (Deployment)

### Workflow: .github/workflows/deploy.yml

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ -v
      
      - name: Build
        run: |
          python -m build
      
      - name: Deploy to production
        run: |
          ssh user@prod-server "cd /app/dominion && git pull && systemctl restart dominion"
      
      - name: Smoke test
        run: |
          sleep 10  # Wait for restart
          curl --fail http://prod-server:7474/health || exit 1
      
      - name: Notify
        if: success()
        run: |
          curl -X POST $SLACK_WEBHOOK -d '{"text":"Dominion deployed successfully"}'
      
      - name: Rollback
        if: failure()
        run: |
          ssh user@prod-server "cd /app/dominion && git checkout HEAD~1 && systemctl restart dominion"
          curl -X POST $SLACK_WEBHOOK -d '{"text":"⚠️ Dominion deploy failed, rolled back"}'
```

**Triggers:**
- Push to main (after tests pass)

**Steps:**
1. Tests
2. Build
3. Deploy (git pull + restart)
4. Smoke test (health check)
5. Notify (Slack)
6. Rollback if fails

---

## Deployment Strategies

### 1. Blue-Green Deployment (Phase 10)

**Setup:**
- Blue environment (current production)
- Green environment (new version)

**Process:**
1. Deploy to green
2. Smoke test green
3. Switch traffic (blue → green)
4. Keep blue as rollback

**Advantage:** Zero downtime, instant rollback.

**Implementation:**
```bash
# Deploy to green
ssh user@green-server "cd /app/dominion && git pull && systemctl restart dominion"

# Test green
curl --fail http://green-server:7474/health

# Switch load balancer (blue → green)
nginx-reload blue=off green=on

# Rollback if needed
nginx-reload blue=on green=off
```

---

### 2. Canary Deployment (Phase 14+)

**Setup:**
- 10% traffic → new version
- 90% traffic → old version

**Process:**
1. Deploy new version (canary)
2. Route 10% traffic
3. Monitor errors (5 min)
4. If stable: Route 100%
5. If errors: Rollback

**Advantage:** Gradual rollout, less risk.

---

## Pre-Commit Hooks

**File:** .git/hooks/pre-commit

```bash
#!/bin/bash

# Run linters
black --check src/ || exit 1
flake8 src/ || exit 1

# Run unit tests (fast)
pytest tests/unit/ -q || exit 1

# Audit MT5 safety
grep -r "order_send\|OrderSend\|TRADE_ACTION" src/ && exit 1

echo "✓ Pre-commit checks passed"
```

**Enable:**
```bash
chmod +x .git/hooks/pre-commit
```

---

## Post-Commit Hooks (Current)

**File:** .git/hooks/post-commit

```bash
#!/bin/bash
cd "$(git rev-parse --show-toplevel)" || exit 1

# Sync docs to vault
if git diff-tree --no-commit-id --name-only -r HEAD | grep -q '^docs/'; then
    python scripts/vault_sync.py --quiet 2>/dev/null || true
fi
```

**Status:** Active (Phase 5).

---

## Monitoring & Alerts

**Prometheus Metrics (Phase 10):**
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests')
http_request_duration_seconds = Histogram('http_request_duration_seconds', 'HTTP request latency')

# Pipeline metrics
pipeline_runs_total = Counter('pipeline_runs_total', 'Total pipeline runs')
pipeline_duration_seconds = Histogram('pipeline_duration_seconds', 'Pipeline duration')
pipeline_errors_total = Counter('pipeline_errors_total', 'Pipeline errors')

# Feature metrics
features_computed_total = Counter('features_computed_total', 'Features computed')
feature_nan_total = Counter('feature_nan_total', 'Features with NaN')
```

**Grafana Dashboards:**
- System health (uptime, errors)
- Pipeline performance (latency, throughput)
- Resource usage (CPU, memory, disk)

**Alerts (AlertManager):**
- Pipeline failed (critical)
- Latency >20 min (warning)
- Disk >90% full (critical)
- Memory >80% (warning)

---

## Rollback Procedures

### Automatic Rollback (Deploy Failure)

**Trigger:** Smoke test fails (health check 500 error)

**Action:**
```bash
# Checkout previous commit
git checkout HEAD~1

# Restart
systemctl restart dominion

# Verify
curl http://127.0.0.1:7474/health
```

**Notification:** Slack alert (deploy failed, rolled back).

---

### Manual Rollback (Bug Discovered)

**Process:**
1. Identify bad commit (`git log`)
2. Checkout previous good commit
3. Deploy
4. Verify
5. Create hotfix branch (fix bug)
6. Merge + redeploy

```bash
# Rollback
git checkout abc123  # Last known good
./deploy.sh

# Fix
git checkout -b hotfix/bug-123
# Fix bug...
git commit -m "fix: bug 123"
git checkout main
git merge hotfix/bug-123
./deploy.sh
```

---

## Environment Management

**Environments:**
1. **Development** (local machine)
2. **Staging** (pre-production, optional)
3. **Production** (live system)

**Configuration:**
```python
# config.py
import os

ENV = os.getenv('DOMINION_ENV', 'development')

if ENV == 'development':
    DEBUG = True
    DATABASE_PATH = 'data/dev.db'
elif ENV == 'staging':
    DEBUG = False
    DATABASE_PATH = 'data/staging.db'
elif ENV == 'production':
    DEBUG = False
    DATABASE_PATH = 'data/prod.db'
```

**Deployment:**
```bash
# Production
DOMINION_ENV=production python -m data_pipeline.cli run
```

---

## Secrets Management (Phase 10)

**Current (Phase 5):**
- secrets/mt5.env (local file, .gitignore)

**Future (Phase 10):**
- AWS Secrets Manager or HashiCorp Vault

**GitHub Actions:**
```yaml
- name: Deploy
  env:
    MT5_PASSWORD: ${{ secrets.MT5_PASSWORD }}
  run: |
    echo "MT5_PASSWORD=$MT5_PASSWORD" > secrets/mt5.env
    ./deploy.sh
```

**Secrets in GitHub:**
- Settings → Secrets → New secret
- Name: MT5_PASSWORD
- Value: (encrypted)

---

## Release Process (Phase 10+)

**Versioning:** Semantic versioning (MAJOR.MINOR.PATCH)

**Process:**
1. Create release branch (`git checkout -b release/v2.1.0`)
2. Bump version (`scripts/bump_version.sh 2.1.0`)
3. Update CHANGELOG.md
4. Merge to main
5. Tag (`git tag v2.1.0`)
6. Push (`git push --tags`)
7. GitHub Actions deploys automatically

**Changelog Format:**
```markdown
## [2.1.0] - 2026-05-19

### Added
- Feature X
- Feature Y

### Fixed
- Bug Z

### Changed
- Improved performance (10% faster)
```

---

## Related Documentation

- [[TECH_DEBT_MAP]] — Debt #15 (manual deployment)
- [[ENHANCEMENT_BACKLOG]] — Enhancement #15 (CI/CD)
- [[DEBUGGING_GUIDE]] — Debug failed deploys
- [[CODING_STANDARDS]] — Pre-commit checks

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Status:** Manual deployment. CI/CD planned Phase 10.

**Next Steps:**
1. Phase 10: Implement GitHub Actions CI/CD
2. Phase 10: Blue-green deployment
3. Phase 10: Prometheus + Grafana
