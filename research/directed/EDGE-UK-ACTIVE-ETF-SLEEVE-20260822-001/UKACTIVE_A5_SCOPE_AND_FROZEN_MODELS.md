# UKACTIVE-A5S scope and frozen shadow models

Status: **SETUP ONLY — PROSPECTIVE NOT STARTED**
Evidence target: **E3 only after 24 valid on-time monthly decisions**
Historical development cutoff: **2026-08-21**
Earliest official signal: **2026-08-28**

## A5-A — A5A_ACTIVE_BASELINE_V1

`INDUSTRY_PLUS_THEME | equal percentile ranks of RS63/RS126/RS252 | TOP_1 | MONTHLY | 100% active`.
The ranking identity is the economic family, ties use ascending family ID, the signal forms after the final valid XLON close of the month and execution is the first common valid close from the next XLON session within three sessions. One-way friction is 20 bp plus £3.99 per actual leg on a £250,000 shadow notional.

## A5-B — A5B_CORE_ACTIVE_50_V1

Exactly 50% of the same A5-A active leader and exactly 50% `GLOBAL_DEVELOPED_WORLD`, rebalanced monthly under the same timing and cost convention. A5-B may never generate a different active selection.

## Frozen implementation and safety contract

The 25 currently signal-ready active families use the versioned, user-confirmed ii map dated 2026-08-23. The preferred line is used first; only an already declared and verified alternate may replace it. Otherwise the affected allocation is GBP cash and the event is `IMPLEMENTATION_BLOCKED`; rank 2 is never substituted. The economic pool retains its frozen 27-family dynamic-admission lineage, so a later newly signal-ready family without a preverified line is blocked rather than silently added operationally.

The global core is the authoritative `GLOBAL_DEVELOPED_WORLD` line SWDA / IE00B4L5Y983. Public UK evidence is confirmed, and the user manually confirmed current ii tradability on 2026-08-23. This current-only observation is not historical platform evidence and is never back-projected.

No live order, broker connector, scheduler, backfill, same-close fill, discretionary substitution or model change exists in this infrastructure. Weekly FAST, geography and regime fields are telemetry only.
