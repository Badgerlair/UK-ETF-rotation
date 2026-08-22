# UKACTIVE A2 — Scope and Method

Decision: `UKACTIVE_A2_PASS_WITH_OPEN_ITEMS`

This stage constructs point-in-time identity, availability and GBP total-return data. It does **not** test momentum, rank signals, construct a portfolio or report strategy performance.

The authoritative input identity is A0A1's fund → share class/ISIN → listing model. A2 admitted 367 active price routes only where both ticker and ISIN matched the EODHD LSE catalogue, plus 4 exact-ISIN delisted listing extensions. Ticker-only matches were rejected.

The immutable long-form panel contains one row per economic family/date, so extra ETF providers cannot create extra economic opportunities. Canonical implementation selection uses only the prior XLON research session and the predeclared policy `UKACTIVE-A2-POLICY-v1.2.0`.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY.

Actual GBP cash is a separate SONIA-based research asset. It is not CSH2, another ETF or a claim about broker cash remuneration. Proxy and live implementation histories are structurally separate and are never spliced.
