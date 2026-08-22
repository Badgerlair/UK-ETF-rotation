# UKACTIVE A2 — Canonical Implementation Selection Policy

For return date T, selection information is limited to the immediately prior canonical XLON session. Candidate requirements and ordered tie-breaks are fixed in `D:\Codex\equity_quant_research_platform\research\directed\EDGE-UK-ACTIVE-ETF-SLEEVE-20260822-001\config\UKACTIVE_A2_POLICY_v1.json`.

Order: GBP/GBX listing first; more valid observations accumulated only through the information date; fewer bad observations accumulated only through that date; earlier first observed date; then stable share-class and listing IDs. Current AUM, current liquidity, future eligibility, future returns, provider popularity and all legacy ETF strategy logic are forbidden.

The output records the selected share class, selected listing, information date, reason and evidence. `execution_eligible_date` is strictly later than `signal_information_date`; same-close return capture is impossible by construction.
