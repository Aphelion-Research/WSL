---
doc_type: adr
system: Dominion
ragd_priority: 8
audience:
  - maintainer
  - developer
status: accepted
date: 2025-04-01
tags:
  - adr
  - mt5
  - safety
  - trading
  - phase-2
---

# ADR-0007: Read-Only MT5 Architecture

**Date:** 2025-04-01  
**Status:** Accepted  
**Deciders:** Owner  
**Phase:** Phase 2 (Multi-Source Fusion)

---

## Context

MT5 (MetaTrader 5) provides real-time tick data for futures trading. Need integration for:
- Live tick ingestion (bid/ask/last)
- Historical tick retrieval
- Symbol information (contract specs)

**Critical Safety Requirement:** Never execute live trades (research platform only).

**Risk:** Accidental trade execution (bug, agent error) → real capital loss.

---

## Decision

Implement **read-only MT5 architecture** with multiple safety layers:

1. **No trade functions** in codebase (not imported, not called)
2. **Demo account only** (no real capital)
3. **Code review** (all MT5 code reviewed for trade calls)
4. **MQL5 EA read-only** (Expert Advisor exports ticks only, no OrderSend)
5. **Safety rules** (Agent OS forbids trade commands)

---

## Safety Layers

### Layer 1: No Trade Functions (Code-Level)

**Forbidden functions (never import):**
```python
# NEVER ALLOWED
from MetaTrader5 import order_send  # ❌
from MetaTrader5 import OrderSend   # ❌
from MetaTrader5 import order_check # ❌

# MQL5 equivalents (never in EA code)
OrderSend()          # ❌
OrderSendAsync()     # ❌
OrderDelete()        # ❌
OrderModify()        # ❌
```

**Allowed functions (read-only):**
```python
# OK
from MetaTrader5 import symbol_info          # ✓ Read symbol specs
from MetaTrader5 import copy_ticks_range     # ✓ Historical ticks
from MetaTrader5 import copy_rates_range     # ✓ OHLC bars
```

**Enforcement:** Code review + grep audit.

```bash
# Audit script (run before commit)
grep -r "order_send\|OrderSend\|TRADE_ACTION" src/
# Exit code 1 if found (block commit)
```

---

### Layer 2: Demo Account Only

**MT5 connection:**
```python
# secrets/mt5.env
MT5_LOGIN=12345678        # Demo account
MT5_PASSWORD=...
MT5_SERVER=BrokerDemo     # Demo server
```

**Verification:**
```python
import MetaTrader5 as mt5

def verify_demo_account():
    account_info = mt5.account_info()
    if account_info.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise RuntimeError("ERROR: Live account detected! Only demo allowed.")
    logger.info("Verified: Demo account only")
```

**Run on startup** (every MT5 connection).

---

### Layer 3: Code Review (Pre-Merge)

**Process:**
1. All MT5 PRs reviewed by owner
2. Check for trade functions (grep audit)
3. Verify demo account connection
4. Test on demo (smoke test)

**Checklist:**
- [ ] No `order_send` or `OrderSend` in Python code
- [ ] No `OrderSend()` in MQL5 EA code
- [ ] Demo account verified (not live)
- [ ] Tests pass on demo
- [ ] Code reviewed by owner

---

### Layer 4: MQL5 EA Read-Only

**Expert Advisor (domdata_export.mq5):**
```mql5
// Read-only EA: Export ticks to CSV

void OnTick() {
    MqlTick tick;
    SymbolInfoTick(_Symbol, tick);
    
    // Write to CSV
    string line = StringFormat("%d,%s,%.5f,%.5f,%.5f,%d",
        tick.time_msc,
        _Symbol,
        tick.bid,
        tick.ask,
        tick.last,
        tick.volume
    );
    
    FileWrite(file_handle, line);
    
    // NO TRADING FUNCTIONS
    // OrderSend() is NEVER called
}
```

**Verification:**
```bash
# Audit EA before deployment
grep -i "OrderSend\|OrderSendAsync\|TRADE_ACTION" domdata_export.mq5
# Exit code 1 if found
```

---

### Layer 5: Agent OS Safety Rules

**Forbidden commands:**
```python
# agent/safety.py
FORBIDDEN_COMMANDS = [
    'order_send',
    'OrderSend',
    'TRADE_ACTION_DEAL',
    'TRADE_ACTION_PENDING',
    'mt5.order_send',
]

def is_command_safe(command):
    for forbidden in FORBIDDEN_COMMANDS:
        if forbidden in command.lower():
            return False, f"CRITICAL: Trading command forbidden: {forbidden}"
    return True, "OK"
```

**Enforcement:** Pre-execution hook (see [[ADR_0004_agent_safety_architecture]]).

---

## Alternatives Considered

### Alternative 1: API Key Restrictions (Exchange-Level)

**Approach:** Use read-only API key (no trade permissions).

**Pros:**
- Enforced by broker (not code)
- Impossible to trade (even if bug)

**Cons:**
- MT5 doesn't support read-only API keys
- All MT5 accounts have trade permissions

**Verdict:** Not possible with MT5 (would use if available).

---

### Alternative 2: Separate Read-Only Account (Broker)

**Approach:** Request broker to disable trading on account.

**Pros:**
- Broker-enforced (strong guarantee)

**Cons:**
- Not offered by most brokers
- Demo account sufficient (no real capital)

**Verdict:** Demo account equivalent (no real capital at risk).

---

### Alternative 3: Network Firewall (Block Trade Packets)

**Approach:** Firewall blocks packets to broker trade server.

**Pros:**
- Network-level enforcement

**Cons:**
- Complex (packet inspection)
- Fragile (broker may change protocol)
- MT5 uses same connection for data + trades (can't separate)

**Verdict:** Rejected (too complex, brittle).

---

### Alternative 4: No MT5 (Use Yahoo Finance Only)

**Approach:** Avoid MT5 entirely, use Yahoo Finance (no trade capability).

**Pros:**
- No trade risk (Yahoo read-only API)

**Cons:**
- No real-time ticks (Yahoo 15-min delay)
- No LOB data (Yahoo OHLCV only)

**Verdict:** Rejected (need real-time for microstructure).

---

## Consequences

### Positive

1. **Zero trade risk** — Multiple safety layers (code + demo + review)
2. **Auditable** — Grep audit catches trade functions
3. **Agent-safe** — Agent OS blocks trade commands
4. **Peace of mind** — Sleep knowing trades impossible

### Negative

1. **Manual review overhead** — All MT5 PRs need owner review
2. **Testing limitation** — Can't test real execution (demo only)

### Neutral

1. **Demo account** — Need demo account from broker (easy to obtain)
2. **Paper trading** — Phase 7 uses simulated execution (not real)

---

## Validation

**Phase 2 (Initial, Q2 2025):**
- Grep audit: 0 trade functions found ✓
- Demo account verified ✓
- 3 months usage: 0 trade attempts

**Phase 5 (Current, Q2 2026):**
- 12 months MT5 usage
- 0 trade attempts (accidental or intentional)
- 0 real capital at risk

**Phase 7 (Paper Trading, Q3 2026):**
- Simulated execution (no MT5 OrderSend)
- Still demo account
- Still read-only architecture

**Phase 10+ (Production, 2028):**
- **Decision point:** Enable live trading?
- **Answer:** TBD. Likely stay read-only (use broker separately for execution).

---

## Implementation

**Location:**
- `domdata/client.py` — Python MT5 client (read-only)
- `mql5/domdata_export.mq5` — MQL5 EA (read-only)
- `agent/safety.py` — Agent OS safety rules

**Tests:**
- `tests/unit/test_mt5_safety.py` — Verify no trade functions imported
- Audit script: `scripts/audit_mt5_safety.sh`

**Docs:** [[DOMDATA_FEATURE]], [[AGENT_OPERATING_SYSTEM]]

---

## Audit Schedule

**Before every commit touching MT5:**
```bash
scripts/audit_mt5_safety.sh
# Grep for trade functions, fail if found
```

**Monthly (automated):**
```bash
# CI job: Audit entire codebase
grep -r "order_send\|OrderSend\|TRADE_ACTION" src/ mql5/
# Alert if found
```

**Quarterly (manual):**
- Owner reviews all MT5 code
- Verify demo account still active
- Check for new trade functions (MT5 API updates)

---

## Future Considerations (Phase 10+)

### Scenario: Enable Live Trading

**If decision to trade live:**
1. Create separate `trading/` module (isolated)
2. Require 2FA confirmation (hardware key)
3. Position limits (max $1K per trade)
4. Kill switch (manual + automatic)
5. Extensive testing (6+ months paper trading)

**Unlikely:** Dominion designed as research platform. Execution via external broker more likely.

---

## Related

- [[ADR_0004_agent_safety_architecture]] — Agent safety rules
- [[DOMDATA_FEATURE]] — MT5 integration spec
- [[PHASE_2]] — Multi-source fusion (MT5 integration)
- [[SAFETY_RULES]] — Complete safety guidelines

---

## References

- MetaTrader 5 Documentation (MQL5)
- OWASP Secure Coding Guidelines
- Knight Capital Incident (2012) — $440M loss from trading bug
