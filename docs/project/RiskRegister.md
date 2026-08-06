# RiskRegister — UNION-BANK-: Known Risks & Mitigations

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Program Manager|
|Status|Approved|

|ID|Risk|Likelihood|Impact|Score|Mitigation|Owner|Status|
|---|---|---|---|---|---|---|---|
|R-01|Local env dependency gap (`pybreaker` missing)|High|Medium|8|Add to requirements-lock; reinstall; CI unaffected|Owner|Open (Tracker blocker)|
|R-02|SQLite write serialization under concurrency|High|Low|5|Documented PostgreSQL path (ADR-0005)|Owner|Mitigated|
|R-03|Token theft via XSS|Low|High|6|httpOnly + Strict cookies; CSP|Sec|Mitigated|
|R-04|Refresh token replay|Low|Medium|4|Rotation + family revocation|Sec|Mitigated|
|R-05|CSRF on state changes|Low|High|6|Double-submit pattern + tests|Sec|Mitigated|
|R-06|Rate-limit bypass via IP rotation|Medium|Medium|6|Account-based limits follow the account|Sec|Mitigated|
|R-07|Portfolio scope creep into regulated finance|Medium|High|9|Strict non-goals; educational scope statement|PM|Open|
|R-08|Coverage erosion below 73%|Medium|Medium|6|CI coverage gate + mutmut|QA|Open|
|R-09|v1/v2 API drift|Medium|Medium|6|Envelope v2 + deprecation headers + contract tests|Eng|Open|
|R-10|Dead code re-accumulation|Medium|Low|3|../reference/INVENTORY.md discipline + ADR-0001|Owner|Open|

## Risk Matrix

```mermaid
quadrantChart
    title Risk Prioritization
    x-axis Low Likelihood --> High Likelihood
    y-axis Low Impact --> High Impact
    quadrant-1 Watch: R-04, R-10
    quadrant-2 Manage: R-02, R-06, R-08, R-09
    quadrant-3 Avoid: R-03, R-05
    quadrant-4 Critical: R-01, R-07
```

## Top 3 Focus Risks

1. **R-01 pybreaker gap** — blocks local test runs; fix first (TASK-4.1).
2. **R-07 Scope creep** — keep educational boundaries explicit.
3. **R-08 Coverage erosion** — coverage gate + mutation testing in CI.

## Related Documents

|Document|Relationship|
|---|---|
|[PRD.md](../product/PRD.md)|Top risk summary|
|[SecurityAndCompliance.md](../technical/SecurityAndCompliance.md)|Security risks|
|[Tracker.md](Tracker.md)|R-01 blocker status|
