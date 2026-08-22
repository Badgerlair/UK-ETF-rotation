# UKACTIVE A2 — Total-Return Data Policy

Raw close is retained but is not the authoritative return field. EODHD documents `adjusted_close` as adjusted for splits and dividends. A2 accepts that route only behind a validation gate consisting of explicit distribution reconstruction, corporate-action inspection, accumulating/distributing coherence checks and representative Yahoo overlaps.

For an ex-distribution date, the independent reconstruction is:

`(split-adjusted raw close_t + distribution_t in price units) / raw close_t-1 - 1`

The stored authoritative series remains adjusted-close percentage change. The distribution is not added again. Event status counts were `{'PASS': 3135, 'UNRESOLVED_NO_PRICE_ON_EVENT_DATE': 121, 'FAIL': 78, 'WARNING': 57, 'UNRESOLVED_NO_PRIOR_PRICE': 44}`; listing validation statuses were `{'PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE': 140, 'PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS': 97, 'PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION': 91, 'PASS_PRICE_RETURN_ETC_VENDOR_SEMANTICS_NO_DISTRIBUTION': 20, 'FAIL_DISTRIBUTION_RECONCILIATION': 13, 'PASS_WITH_OPEN_EVENT_TOLERANCE_ITEMS': 8, 'PASS_WITH_OPEN_EVENT_ALIGNMENT_ITEMS': 1, 'FAIL_SAME_ISIN_GBP_FX_COHERENCE': 1}`. Yahoo overlap statuses were `{'PASS': 18, 'FAIL': 1, 'WARNING': 1}`.

Where a GBP-labelled vendor event is numerically implausible relative to a GBP raw price, policy v1.1 applies a recorded 0.01 pence-to-GBP normalization only under the declared 20% plausibility bound. Missing ex-date prices remain unresolved and are never silently shifted.

Missing, stale, post-stale catch-up and unexplained >35% daily observations are invalid rather than forward-filled. Live implementation and proxy histories use different labels and files.
