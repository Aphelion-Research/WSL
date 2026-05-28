---
doc_type: roadmap
system: Dominion
ragd_priority: 6
audience:
  - owner
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - roadmap
  - planning
  - future
---

# Master Roadmap

**Status:** Phase 0 complete (LIVE_GREEN)  
**Current Phase:** Phase 1 (Stabilization)  
**Timeline:** 10 phases over 18-24 months

---

## Phase 0: Current State ✓ COMPLETE

**Status:** LIVE_GREEN  
**Completed:** 2026-05-19

**Deliverables:**
- ✓ RAGD memory system (7159 chunks, 24/24 C++ tests)
- ✓ domdata MT5 bridge (read-only, validated)
- ✓ Data pipeline (5 sources, 400+ features, 16/16 tests)
- ✓ Microstructure subsystems (LOB, Exec, TCA, Toxicity, Features, 30/30 tests)
- ✓ Agent OS (safety + lifecycle + complexity budgets)
- ✓ RAG retrieval (recall@10=1.0, MRR=1.0, nDCG@10=1.0)
- ✓ Native C++ core (11x faster scan: 18ms vs 201ms)
- ✓ Obsidian vault (878 notes, 0 broken links)
- ✓ Comprehensive documentation system (this doc brain)

**Validation:** 426/426 Python tests, 24/24 C++ tests, trading check PASS

---

## Phase 1: Stabilization (4-6 weeks)

**Objective:** Eliminate technical debt, improve reliability, harden platform.

**Required Work:**
1. Address complexity budget violations
2. Resolve TEMP_ADAPTER labels
3. Fix orphan RAGD chunks
4. Add missing tests
5. Improve error handling
6. Document known limitations
7. Create incident response playbook

**Deliverables:**
- All complexity budgets met
- Zero TEMP_ADAPTER labels
- Zero orphan chunks
- >85% test coverage across all modules
- Documented failure modes + recovery procedures
- Incident response playbook

**Definition of Done:**
- `dominion doctor --deep --json` reports `overall: ok` (not `warn`)
- All 10 complexity budgets met
- 450+ tests passing
- Zero known P0/P1 bugs

---

## Phase 2: RAGD Expansion (6-8 weeks)

**Objective:** Scale RAGD to 50,000+ chunks, improve retrieval quality, add semantic clustering.

**Required Work:**
1. Implement WebSocket support
2. Add multi-level indexing (file → symbol → chunk)
3. Semantic clustering for related chunks
4. Auto-reindexing on file change
5. Query rewriting for better retrieval
6. Cross-reference validation
7. RAGD performance optimization

**Deliverables:**
- WebSocket API operational
- Multi-level index structure
- Semantic clusters (topics, modules, features)
- File watcher + auto-reindex
- Query rewriter (synonym expansion, spelling correction)
- <50ms p95 query latency (currently ~100ms)

**Definition of Done:**
- 50,000+ chunks indexed
- WebSocket `/bus` operational
- Retrieval quality: recall@10 > 0.95, MRR > 0.9, nDCG@10 > 0.9
- <50ms p95 query latency

---

## Phase 3: Agent Automation (8-10 weeks)

**Objective:** Enable agents to work autonomously with minimal human oversight.

**Required Work:**
1. Automated code review pipeline
2. Self-healing platform (auto-fix common issues)
3. Proactive agent suggestions ("I noticed X, should I fix it?")
4. Agent collaboration framework (multiple agents in parallel)
5. Agent performance tracking + optimization
6. Automated documentation updates

**Deliverables:**
- Code review agent (auto-review PRs)
- Self-healing scripts (fix common errors automatically)
- Proactive agent mode (suggests improvements)
- Multi-agent orchestration (parallel workflows)
- Agent performance dashboard
- Auto-doc-update agent (keeps docs current)

**Definition of Done:**
- 80% of code reviews automated
- 90% of common issues self-heal
- 3+ agents can work in parallel without conflicts
- Agent performance metrics tracked

---

## Phase 4: Obsidian Sync (4-6 weeks)

**Objective:** Bidirectional sync between vault and RAGD, live knowledge graph updates.

**Required Work:**
1. Bidirectional RAGD ↔ Vault sync
2. Real-time vault updates (file watcher)
3. Conflict resolution for concurrent edits
4. Graph visualization (Obsidian graph + RAGD graph alignment)
5. Auto-linking (suggest wiki links for terms)
6. Tag taxonomy enforcement

**Deliverables:**
- Bidirectional sync (edit in Obsidian → updates RAGD, edit in code → updates vault)
- Real-time file watching
- Conflict resolution UI
- Unified graph view (Obsidian + RAGD)
- Auto-linker (suggests `[[links]]` for relevant terms)
- Tag taxonomy validator

**Definition of Done:**
- Vault and RAGD stay in sync (<1 minute lag)
- Zero sync conflicts (or auto-resolved)
- Graph visualizer operational
- 2000+ vault notes

---

## Phase 5: Local LLM Layer (10-12 weeks)

**Objective:** Add local LLM for research synthesis, report generation, and offline work.

**Required Work:**
1. Evaluate local LLMs (Qwen, Llama, Mistral, DeepSeek)
2. Quantization + optimization for 3.5 GB GPU
3. RAGD-augmented local generation
4. Research synthesis pipeline (multi-doc summarization)
5. Report generation (daily intelligence reports, feature specs, ADRs)
6. Fallback to frontier models when local insufficient

**Deliverables:**
- Local LLM operational (Qwen 2.5 14B 4-bit quantized)
- <3.5 GB VRAM usage
- RAGD-augmented generation
- Research synthesis agent
- Report generation agent
- Graceful fallback to Claude/GPT-4

**Definition of Done:**
- Local LLM generates coherent summaries
- Research synthesis quality: human-rated >7/10
- <5 second latency for 500-token generation
- Offline mode functional (no internet required for basic work)

---

## Phase 6: Multi-Agent Workflows (8-10 weeks)

**Objective:** Orchestrate teams of agents for complex, multi-step tasks.

**Required Work:**
1. Agent orchestration framework
2. Task decomposition (break large tasks into subtasks)
3. Agent specialization (architect, coder, tester, reviewer)
4. Inter-agent communication (agent bus + MCP)
5. Conflict resolution (concurrent edits, diverging plans)
6. Workflow visualization

**Deliverables:**
- Orchestration engine (spawn, monitor, coordinate agents)
- Specialized agent types (architect, coder, tester, reviewer, documenter)
- Agent communication protocol
- Conflict resolver
- Workflow dashboard (visualize agent progress)

**Definition of Done:**
- 5+ agents can collaborate on single feature
- Task completion time: 50% faster than single agent
- Zero agent conflicts (or auto-resolved)
- Workflow dashboard operational

---

## Phase 7: System Dashboard (4-6 weeks)

**Objective:** Unified dashboard for platform health, agent activity, and system metrics.

**Required Work:**
1. Web dashboard (FastAPI + React or minimal HTML/JS)
2. Real-time metrics (RAGD health, agent status, test results, data pipeline)
3. Historical charts (test trends, coverage, complexity, agent productivity)
4. Alerting (Slack/email when critical issues occur)
5. Mobile-responsive design

**Deliverables:**
- Web dashboard on 127.0.0.1:8080
- Real-time health metrics
- Historical charts (7d/30d/90d views)
- Alerting system (Slack or email)
- Mobile-responsive UI

**Definition of Done:**
- Dashboard operational
- <100ms page load
- Alerts fire correctly for critical issues
- Mobile-friendly

---

## Phase 8: Long-Term Platform (12-16 weeks)

**Objective:** Prepare Dominion for 5-year timeline and potential team scaling.

**Required Work:**
1. Multi-user support (Matin, Dan, future contributors)
2. Role-based access control (owner, maintainer, reader)
3. Audit logging (all changes tracked)
4. Backup/restore system
5. Migration tooling (upgrade scripts for future schema changes)
6. API versioning
7. Plugin system (extend without core changes)

**Deliverables:**
- Multi-user support (permissions, roles)
- Audit log (who changed what, when)
- Automated backup/restore
- Migration framework (DB schema upgrades)
- API versioning (v1, v2, etc.)
- Plugin system (3rd-party extensions)

**Definition of Done:**
- 3+ users can work concurrently
- Audit log captures all changes
- Backups run daily
- Zero-downtime upgrades possible

---

## Phase 9: Team Scale Plan (16-20 weeks)

**Objective:** Scale Dominion to support 10-100 person-equivalent capacity (agents + humans).

**Required Work:**
1. Distributed RAGD (sharding, replication)
2. Message queue for agent coordination (RabbitMQ or Redis)
3. Load balancing
4. Performance optimization (sub-10ms query latency)
5. Resource management (CPU/GPU/memory quotas per agent)
6. Cost tracking (agent runtime, API calls, storage)

**Deliverables:**
- Distributed RAGD (3+ node cluster)
- Message queue operational
- Load balancer
- <10ms p95 query latency
- Resource management system
- Cost dashboard

**Definition of Done:**
- 100+ agents can work concurrently
- Query latency <10ms p95
- System handles 1M+ chunks
- Cost per agent-hour tracked

---

## Phase 10: Enterprise State (20-24 weeks)

**Objective:** Enterprise-grade platform ready for external users (if applicable).

**Required Work:**
1. SaaS deployment (AWS/Azure/GCP)
2. Multi-tenancy (isolate customer data)
3. Enterprise SSO (SAML, OAuth)
4. Compliance (SOC 2, GDPR, etc.)
5. White-label customization
6. Enterprise support tier

**Deliverables:**
- SaaS deployment (Kubernetes, Terraform)
- Multi-tenancy operational
- SSO integration
- SOC 2 compliance
- White-label customization
- Support playbook

**Definition of Done:**
- 10+ customers using platform
- SOC 2 certification achieved
- 99.9% uptime SLA
- <1 hour MTTR for P0 incidents

---

## Timeline Summary

| Phase | Duration | Target Completion |
|---|---|---|
| Phase 0: Current State | — | 2026-05-19 ✓ |
| Phase 1: Stabilization | 4-6 weeks | 2026-07-01 |
| Phase 2: RAGD Expansion | 6-8 weeks | 2026-09-01 |
| Phase 3: Agent Automation | 8-10 weeks | 2026-11-15 |
| Phase 4: Obsidian Sync | 4-6 weeks | 2027-01-01 |
| Phase 5: Local LLM Layer | 10-12 weeks | 2027-03-31 |
| Phase 6: Multi-Agent Workflows | 8-10 weeks | 2027-06-15 |
| Phase 7: System Dashboard | 4-6 weeks | 2027-08-01 |
| Phase 8: Long-Term Platform | 12-16 weeks | 2027-12-01 |
| Phase 9: Team Scale Plan | 16-20 weeks | 2028-04-30 |
| Phase 10: Enterprise State | 20-24 weeks | 2028-10-31 |

**Total Timeline:** 24 months (2 years)

---

## Risk Factors

- Complexity grows faster than maintainability
- Agent quality degrades without oversight
- RAGD performance doesn't scale to 100K+ chunks
- Local LLM quality insufficient for research synthesis
- Multi-agent coordination becomes chaotic

See [09_RISK_AND_SECURITY/RISK_REGISTER.md](../09_RISK_AND_SECURITY/RISK_REGISTER.md) for full risk catalog.

---

## Dependencies

- Phase 2 depends on Phase 1 (stabilization before scaling)
- Phase 3 depends on Phase 2 (RAGD must scale before heavy automation)
- Phase 5 depends on Phase 2 (local LLM needs robust RAGD)
- Phase 6 depends on Phase 3 (multi-agent needs single-agent automation)
- Phase 9 depends on Phase 8 (scaling needs long-term platform)

---

## Related Docs

- [PHASE_0_CURRENT_STATE.md](PHASE_0_CURRENT_STATE.md)
- [PHASE_1_STABILIZATION.md](PHASE_1_STABILIZATION.md)
- [PHASE_2_RAGD_EXPANSION.md](PHASE_2_RAGD_EXPANSION.md)
- [15_FUTURE_STATE/FUTURE_STATE_VISION.md](../15_FUTURE_STATE/FUTURE_STATE_VISION.md)

---

## Retrieval Hints

- "roadmap"
- "future plans"
- "what's next"
- "phase timeline"
- "long-term vision"
