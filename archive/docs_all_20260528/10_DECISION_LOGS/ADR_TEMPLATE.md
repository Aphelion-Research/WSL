---
doc_type: adr
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - adr
  - template
---

# ADR Template

**Copy this template to create new ADR.**

---

```markdown
---
doc_type: adr
system: <Dominion | RAGD | domdata | ...>
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
  - owner
status: proposed | accepted | deprecated | superseded
last_reviewed: YYYY-MM-DD
tags:
  - adr
  - <relevant tags>
---

# ADR-<NNNN>: <Title>

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded  
**Impact:** High | Medium | Low  
**Deciders:** <Who made the decision>

---

## Status

**Current:** <Proposed | Accepted | Deprecated | Superseded>

**History:**
- YYYY-MM-DD: Proposed by <author>
- YYYY-MM-DD: Accepted
- (if deprecated) YYYY-MM-DD: Deprecated, superseded by ADR-<NNNN>

---

## Context

<What is the issue that motivated this decision?>

<Include:**
- **Problem statement** (what needs to be solved)
- **Constraints** (technical, business, time, resources)
- **Assumptions** (what we're taking for granted)
- **Current situation** (what exists now)

<Be specific. Include data, metrics, examples.>

---

## Decision

<What is the change we're proposing or have agreed to?>

<Clearly state the decision in 1-2 sentences, then elaborate.>

**Key points:**
- Point 1
- Point 2
- Point 3

---

## Consequences

### Positive

- Benefit 1: description
- Benefit 2: description

### Negative

- Drawback 1: description, mitigation
- Drawback 2: description, mitigation

### Neutral

- Tradeoff 1: description

---

## Alternatives Considered

### Alternative 1: <Name>

**Description:** <What was this alternative?>

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Why rejected:** <Reason>

### Alternative 2: <Name>

**Description:** <What was this alternative?>

**Pros:**
- Pro 1

**Cons:**
- Con 1

**Why rejected:** <Reason>

---

## Implementation

**Affected components:**
- Component 1: <what changes>
- Component 2: <what changes>

**Migration path:**
1. Step 1
2. Step 2
3. Step 3

**Estimated effort:** <hours/days/weeks>

**Breaking changes:** <Yes/No, details>

---

## Validation

**How will we know the decision is correct?**

**Success criteria:**
- Criterion 1: <measurable>
- Criterion 2: <measurable>

**Monitoring:**
- Metric 1: <what to track>
- Metric 2: <what to track>

---

## Follow-up Work

- [ ] Task 1: description, assignee
- [ ] Task 2: description, assignee
- [ ] Task 3: description, assignee

---

## Related Decisions

- **Depends on:** ADR-<NNNN> (link)
- **Conflicts with:** ADR-<NNNN> (link)
- **Supersedes:** ADR-<NNNN> (link, if applicable)
- **Superseded by:** ADR-<NNNN> (link, if deprecated)

---

## References

- Link to issue: #123
- Link to PR: #456
- External doc: [Title](URL)
- Research: [Paper/article](URL)

---

## Retrieval Hints

- "<decision topic>"
- "<problem domain>"
- "<technology name>"
```

---

## Notes on Using Template

### Title

- Short (≤10 words)
- Describes decision, not problem
- Use present tense: "Use X for Y" not "Should we use X?"

**Good:**
- "Use Kalman Filtering for Multi-Source Fusion"
- "Implement Agent OS with SQLite Backend"

**Bad:**
- "Data Pipeline Decision"
- "Should we use Kalman filtering?"

---

### Context

**Include:**
- Why this decision is needed
- What constraints exist
- What alternatives were obvious
- What assumptions are we making

**Don't:**
- Write generic background (focus on this specific problem)
- Assume reader knows context (explain fully)
- Skip constraints (they're important)

---

### Decision

**Be clear and direct:**

✓ Good:
> We will use a 6-filter Kalman bank with per-source trust scoring for
> multi-source data fusion.

✗ Bad:
> We think maybe Kalman filtering could be good for data fusion.

---

### Consequences

**Be honest:**
- List both positive and negative
- Don't hide drawbacks
- Explain mitigations for negatives

**Example:**

**Positive:**
- Fusion handles outliers gracefully
- Trust scoring adapts to source quality

**Negative:**
- Kalman filter adds complexity (20% more code)
  - Mitigation: comprehensive tests + documentation
- Requires tuning process/observation noise
  - Mitigation: sensible defaults + tuning guide

---

### Alternatives Considered

**Include at least 2 alternatives.**

**Format:**
1. Describe alternative
2. List pros
3. List cons
4. Explain why rejected

**Don't:**
- Straw-man alternatives (make them realistic)
- Skip explaining why rejected
- Compare only to worst alternatives

---

### Implementation

**Make it actionable:**
- List affected files/modules
- Outline migration steps
- Estimate effort
- Note breaking changes

---

## Related Docs

- [DECISION_LOG_INDEX.md](DECISION_LOG_INDEX.md)
- [01_ARCHITECTURE/](../01_ARCHITECTURE/)

---

## Retrieval Hints

- "ADR template"
- "decision template"
- "how to write ADR"
