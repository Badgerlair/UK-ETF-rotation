# UKACTIVE-A4F-SIPP idempotence repair — 2026-08-25

The independent 43-test suite passed. A subsequent full byte-level rebuild changed only the holding-spell ledger, holding-spell influence table, winner/false-leader aggregation and dependent manifest hash. The inherited spell utility iterates Python sets when assigning row order and spell IDs, so economically identical spells could receive different identifiers between processes.

A4F now canonicalises the inherited completed spell rows with a stable sort by contribution, entry date, family and exit date, then assigns deterministic spell IDs. This changes no holding boundary, family P&L, portfolio return, robustness exclusion, gate or selected strategy. The final build, all tests and the full-directory hash comparison must be rerun.

The canonical spell output also reports each family's 63/126-valid-observation pre-entry return, held-period family return and whether selection occurred before a majority of the combined positive pre-entry-plus-held move. These are ex-post mechanism diagnostics only and close the explicit right-tail timing question without changing a historical decision.
