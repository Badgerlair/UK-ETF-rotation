# UKACTIVE-A4F-SIPP metadata-schema repair — 2026-08-25

The completed full build passed its 23 internal checks. The independent suite then passed 42 of 43 checks and failed one fail-closed metadata assertion because `UKACTIVE_A4F_SIPP_SELECTED_STRATEGY.json` described the authoritative dynamic universe without the explicit literal `POINT_IN_TIME` token.

This repair makes that governance property explicit in the selected-strategy metadata. It changes no universe membership, signal, return, regime, threshold, allocation, cost, gate or selection. The full deterministic builder and test suite must be rerun so the final manifest hashes the corrected output.
