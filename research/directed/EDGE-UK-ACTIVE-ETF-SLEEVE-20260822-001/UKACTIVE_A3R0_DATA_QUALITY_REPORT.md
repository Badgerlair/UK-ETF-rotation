# UKACTIVE-A3R0 — Data quality report

## Outcome

Decision: **UKACTIVE_A3R0_FAIL**.

- A0A1 families retained: 99.
- A2 families with raw usable implementation histories: 90.
- Material A2 family/implementation lineage failures found and blocked: 14.
- Families admitted after lineage control: 76.
- Proposed selectable non-benchmark families: 72.
- Shorter-than-504 histories recovered: 3.
- Families with no usable A2 history: 9.
- Automated controls passed: 38; failed: 0.

## Critical lineage findings

- `AUSTRALIA` — A2 canonical history is almost entirely a GBP-hedged share class although A0A1 family is unhedged
- `CHINA_BROAD` — A2 canonical history is overwhelmingly China A-shares and duplicates CHINA_A_SHARES rather than broad China
- `EUROPE_ENERGY` — A2 history uses an MSCI World Energy fund
- `EUROPE_FINANCIALS` — A2 history switches from Europe Financials to MSCI World Financials
- `EUROPE_HEALTHCARE` — A2 history switches from Europe Healthcare to MSCI World Health Care
- `EUROPE_INDUSTRIALS` — A2 history uses an MSCI World Industrials fund
- `EUROPE_MATERIALS` — A2 history uses an MSCI World Materials fund
- `EUROPE_TECHNOLOGY` — A2 history uses an MSCI World Technology fund
- `EUROPE_UTILITIES` — A2 history uses an MSCI World Utilities fund
- `GLOBAL_BANKS` — A2 history is principally Europe banks and contains a development-bank bond observation
- `GLOBAL_HEALTHCARE` — A2 history changes from a broad world-healthcare fund to healthcare-innovation implementations
- `GLOBAL_INFRASTRUCTURE` — A2 history uses US infrastructure and briefly Europe infrastructure rather than a stable global infrastructure implementation
- `GLOBAL_TECHNOLOGY` — A2 history uses a digitalisation thematic fund rather than a broad global technology sector fund
- `US_AEROSPACE_DEFENCE` — A2 history uses a global aerospace-and-defence fund rather than the available US-defence implementation

These rows are not dynamically admitted. The source A0A1/A2 artifacts remain immutable; the corrections ledger records the required repair.

## Dynamic eligibility

Eligible family counts by signal sessions: {"126": 76, "21": 76, "252": 75, "42": 76, "63": 76}. Dynamic dates count only valid observations and never use proxy data; later signal-date windows must independently remain valid.

## Public evidence and broker boundary

Queued public lines: 142. Retail-disclosure confirmed: 44. Public ISA-rules eligible: 44. Lines with at least one public uncertainty: 98. IBKR-confirmed lines: 0.

## Reproducibility

The programme directory is not a Git worktree. Exact executed source/config snapshots, hashes, input hashes, output hashes, package versions and command line are retained in the manifest and evidence directory. No strategy-performance output exists.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY
