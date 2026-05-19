---
doc_type: adr
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
  - owner
status: accepted
last_reviewed: 2026-05-19
tags:
  - decision
  - adr
  - native-core
  - performance
---

# ADR 0002: Native C++ File Scan Over Pure Python

**Status:** Accepted  
**Date:** 2025-03-10  
**Decision ID:** ADR_0002

**History:**
- 2025-03-10: Proposed
- 2025-03-11: Accepted after benchmarks
- 2026-05-19: Documented

---

## Context

Dominion loader must scan ~1,300 files to build manifest:
- Calculate SHA-256 hashes
- Extract Python symbol counts (functions, classes)
- Apply ignore policy (.gitignore + RAGD ignore rules)
- Normalize paths
- Detect file classification (source/test/generated/vendor)

### Problem Statement

Initial pure Python implementation (pathlib + hashlib) took 201ms for 1,281 files. As repo grows to 5K+ files, scan time becomes bottleneck for:
- `dominion scan` CLI command (frequent operation)
- RAGD index rebuilds
- Pre-commit hooks
- CI/CD pipelines

Need faster scan without sacrificing correctness.

### Constraints

- Must maintain Python API compatibility
- Must use same ignore policy rules
- Must produce identical hashes
- Must work on WSL/Debian
- Must be maintainable (no obscure C++)

### Assumptions

- File scanning I/O-bound, not CPU-bound
- Native code won't add significant maintenance burden
- C++ stdlib (filesystem, SHA-256) reliable
- Python bindings via ctypes or pybind11 acceptable

### Current Situation

Python implementation works but slow. Repo growing. Need headroom.

---

## Decision

**Implement native C++ file scanner with Python bindings.**

### Key Points

1. **C++ stdlib for I/O** — std::filesystem faster than pathlib
2. **OpenSSL for SHA-256** — Hardware-accelerated when available
3. **Python bindings via ctypes** — Simple, no build-time dependency
4. **Ignore policy in C++** — Same rules, no Python overhead
5. **Fall back to Python** — If native binary missing

---

## Consequences

### Positive

- **11x faster** — 18ms vs 201ms for 1,281 files (measured)
- **Scales better** — Linear time as repo grows
- **Hardware acceleration** — OpenSSL uses CPU crypto extensions
- **Python still works** — Pure Python fallback if native unavailable
- **Simple interface** — Single scan_files() function
- **CMake build** — Standard C++ workflow

### Negative

- **Build step required** — Must run cmake + make
- **Platform-specific binary** — Linux x86_64 only (WSL target acceptable)
- **C++ maintenance** — Requires C++ knowledge for changes
- **Build dependencies** — cmake, g++, openssl-dev
- **Two implementations** — Must maintain Python + C++ in sync

### Neutral

- **Ignore policy duplicated** — C++ reimplements Python ignore rules (acceptable, rules simple)
- **Bindings via ctypes** — Works well, but pybind11 might be cleaner (can migrate later)

---

## Alternatives Considered

### Alternative 1: Pure Python with multiprocessing

**Description:** Parallelize Python scan across CPU cores.

**Pros:**
- No native code
- Simple implementation
- Uses all cores

**Cons:**
- Process spawn overhead (50-100ms per process)
- Diminishing returns on small repos
- GIL contention for hash computation
- Complexity for marginal gain

**Why Rejected:** Benchmarks showed 2-3x speedup, not 10x. Native code simpler and faster.

### Alternative 2: Rust native implementation

**Description:** Use Rust for speed + safety, bind via PyO3.

**Pros:**
- Memory safety guarantees
- Fast (comparable to C++)
- Modern tooling (cargo)
- PyO3 mature

**Cons:**
- Another language to maintain
- Rust not already in project stack
- Longer build times
- Team unfamiliar with Rust

**Why Rejected:** C++ already used for RAGD core. Adding Rust fragments ecosystem.

### Alternative 3: mmap + parallel hashing in Python

**Description:** Memory-map files and use multiprocessing.Pool for hashing.

**Pros:**
- No native code
- Leverages OS page cache
- Parallelizable

**Cons:**
- mmap overhead for small files
- Still limited by Python I/O
- Complex error handling (SIGBUS on truncation)
- Minimal gain over simple Python

**Why Rejected:** Complexity without proportional speedup. Native code cleaner.

---

## Implementation

### Affected Components

- `ragd/native_scan.cpp` (C++ implementation)
- `ragd/native_scan.h` (C++ header)
- `dominion_loader/native.py` (Python bindings)
- `dominion_loader/scan.py` (fallback logic)
- `ragd/CMakeLists.txt` (build config)

### Migration Path

1. Build native scanner: `cmake -S ragd -B ragd/build && cmake --build ragd/build`
2. Python loader detects native binary: `ragd/build/native_scan`
3. If found: use native, else: fall back to Python
4. Both produce identical output (validated)

### Effort Estimate

- C++ implementation: 3 days
- Python bindings: 1 day
- Testing (unit + integration): 2 days
- Performance benchmarks: 1 day
- **Total:** 7 days (completed)

### Breaking Changes

None (transparent speedup, same API)

---

## Validation

### Success Criteria

- [x] Native scan 5x+ faster than Python
- [x] Produces identical hashes (byte-for-byte)
- [x] Applies same ignore policy
- [x] Falls back gracefully if native missing
- [x] All tests pass (24/24 C++ tests)

### Monitoring Metrics

```bash
# Performance comparison
time python -c "from dominion_loader import scan_files; scan_files('.')"  # Python
time ragd/build/native_scan .  # Native

# Validation: compare outputs
python -c "from dominion_loader import scan_files; print(scan_files('.'))" > python.json
ragd/build/native_scan . > native.json
diff python.json native.json  # Should be empty
```

### Current Status (2026-05-19)

- **Native scan:** 18ms for 1,282 files
- **Python scan:** 201ms for 1,281 files (1 file variance due to timing)
- **Speedup:** 11.2x
- **Hash validation:** 100% match
- **Tests:** 24/24 C++ tests passing

---

## Follow-Up Work

- [ ] Add incremental scan (only changed files)
- [ ] Cache results in SQLite (manifest DB)
- [ ] Benchmark 10K+ file repos
- [ ] Consider pybind11 migration (cleaner bindings)
- [ ] Add progress bar for large repos

---

## Related Decisions

- [[ADR_0001_sqlite_over_postgres]] — File-based SQLite complements native file-based scan
- Future: ADR for incremental scan strategy

---

## References

- C++ std::filesystem: https://en.cppreference.com/w/cpp/filesystem
- OpenSSL SHA-256: https://www.openssl.org/docs/man1.1.1/man3/SHA256.html
- Python ctypes: https://docs.python.org/3/library/ctypes.html
- Benchmarking methodology: scripts/benchmark_scan.py

---

## Retrieval Hints

- "why native scan"
- "c++ vs python performance"
- "file scanning speed"
- "native core rationale"
- "loader performance"
