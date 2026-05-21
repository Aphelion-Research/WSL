---
synced: 2026-05-20 18:19
---
# domdata

`domdata` is the MT5 read-only data CLI. MT5 commands run under Wine-side Python. Conversion commands run under the Linux `.venv`.

Useful commands:

```bash
domdata notice
domdata doctor
domdata account-info
domdata select XAUUSD
domdata xautick
domdata xaurates --count 20
domdata xauticks --start 2026-05-11T00:00:00Z --count 20
domdata tick XAUUSD
domdata rates XAUUSD M1 --count 20
domdata ticks XAUUSD --start 2026-05-11T00:00:00Z --count 20
```

Blocked forever:

```bash
domdata order-send
domdata order-check
domdata buy
domdata sell
domdata close
domdata modify
```
