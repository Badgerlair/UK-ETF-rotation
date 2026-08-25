# UKACTIVE-A4F-SIPP completeness repair — 2026-08-25

This separately committed correctness repair completes the A4F audit trail before the final atomic results build. It does not change any preregistered signal, threshold, allocation map, economic gate, cost rule or strategy-selection hierarchy.

The repair adds:

- accepted GBP total-return endpoint values to every executable policy-decision record;
- the complete M2 TOP7 holding-spell ledger and winner/false-leader comparison;
- longer-window global/cash controls, explicitly separated from direct common-window ranking against the 2017-start rotation history;
- direct, data-driven answers to the 25 mandatory final-report questions;
- fail-closed generated-output assertions for cutoff compliance, state-machine reconciliation, policy-decision coverage, selected-static-family robustness and holding-spell completeness;
- matching automated regression tests.

The same repair also corrects three transition-ledger presentation fields: prior-state duration is measured from the completed preceding episode, risky-minus-cash uses the accepted global and GBP-cash interval returns, and regime changes that produce no allocation change are labelled `NO_ALLOCATION_SWITCH` rather than a beneficial switch. These fields are diagnostic and do not alter a portfolio return or frozen selection gate.

Final read-only review additionally identified and repaired report-boundary issues before regeneration: calendar-year return/drawdown/Ulcer calculations now include the first in-year daily return; annual sleeve weights are calculated from that year's actual holdings rather than a full-history average; January monthly extremes are retained from the full chain; selected-static year exclusions are complete; switch counterfactuals use actual allocation-change dates; mutually exclusive policies are not summed in charts; and the selected JSON/runbook embeds the exact M2 weights, TOP7 rule, point-in-time universe, replacement convention and operational fallback. The final narrative explicitly discloses the selected shadow portfolio's weak capital-protection economics and top-three/top-five contributor fragility.

All historical evidence remains capped at 2026-08-21. No prospective record or live order is created. Prior A1–A5, A4D and A4E-SIPP artefacts remain immutable.
