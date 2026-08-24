# UKACTIVE-A4E-SIPP implementation audit

- Active map: 25/25 signal-ready industry/theme families are `CONFIRMED_BY_USER` in ii as of 2026-08-23; current-only evidence is not back-projected.
- Core: SWDA / IE00B4L5Y983 is user-confirmed in ii. Official iShares evidence reports Ireland domicile, UCITS, accumulating, physical optimised replication, 0.20% TER, ISA eligibility and SIPP availability.
- Active-family SIPP-specific availability remains `TO_CHECK_SIPP_SPECIFIC_ACCOUNT`; user-account tradability is not silently promoted to SIPP evidence.
- Missing current TER, AUM, tracking-difference, spread and traded-value fields remain explicit rather than estimated in the instrument map. Live-cost diagnostics use the median documented active TER only as a disclosed cost proxy and retain doubled historical cost stress.
- Preferred GBP/GBX lines are preserved. If a preferred line and its predeclared same-family alternate are unavailable, the affected slot is GBP cash. There is no discretionary substitute.
- Live cash is ii SIPP GBP broker cash for operating design. Historical research continues to use the accepted GBP cash series; current tiered ii rates are not back-projected.
