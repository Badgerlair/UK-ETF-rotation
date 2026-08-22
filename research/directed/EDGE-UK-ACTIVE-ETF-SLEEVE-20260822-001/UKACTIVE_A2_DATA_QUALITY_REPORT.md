# UKACTIVE A2 — Data Quality Report

Decision: `UKACTIVE_A2_PASS_WITH_OPEN_ITEMS`

- Automated tests: {'PASS': 46}; critical failures: 0.
- Usable A0A1 family histories: 90.
- Validated actual implementation histories: 90 families.
- Explicit distribution reconstruction: {'PASS': 3135, 'UNRESOLVED_NO_PRICE_ON_EVENT_DATE': 121, 'FAIL': 78, 'WARNING': 57, 'UNRESOLVED_NO_PRIOR_PRICE': 44}.
- Listing validation: {'PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE': 140, 'PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS': 97, 'PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION': 91, 'PASS_PRICE_RETURN_ETC_VENDOR_SEMANTICS_NO_DISTRIBUTION': 20, 'FAIL_DISTRIBUTION_RECONCILIATION': 13, 'PASS_WITH_OPEN_EVENT_TOLERANCE_ITEMS': 8, 'PASS_WITH_OPEN_EVENT_ALIGNMENT_ITEMS': 1, 'FAIL_SAME_ISIN_GBP_FX_COHERENCE': 1}.
- Representative Yahoo overlaps: {'PASS': 18, 'FAIL': 1, 'WARNING': 1}.
- FX same-ISIN cross-checks: {'WARNING': 120, 'PASS': 8, 'UNRESOLVED_NO_COMMON_VALID_DATES': 6, 'FAIL': 1}.
- Stale sessions flagged and invalidated: 1842.
- Missing in-life sessions retained as missing: 62667.
- Delisted exact-ISIN listing extensions retained: 4.
- Broker checks: zero; every row remains `NOT_CHECKED`.

No missing price was forward-filled and no stale price was converted to a legitimate zero return. Price-unit corrections are in `UKACTIVE_A2_LINEAGE_CORRECTIONS.csv`. The EODHD route is an indicative vendor source, not an official exchange total-return feed; this limitation remains open and visible.
