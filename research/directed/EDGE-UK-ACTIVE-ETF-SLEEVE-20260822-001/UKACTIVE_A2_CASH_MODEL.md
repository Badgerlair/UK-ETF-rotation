# UKACTIVE A2 — GBP Cash Model

`ACTUAL_GBP_CASH` is a separate research asset, not an exchange-traded instrument. It uses Bank of England daily SONIA (`IUDSOIA`) mirrored by FRED, compounded ACT/365 across calendar days between XLON sessions. The independent validation series is the Bank of England SONIA Compounded Index (`IUDZOS2`), also mirrored by FRED.

Validation result: `{'overlap_observations': 2076, 'median_absolute_error': 2.0478083284647397e-07, 'p95_absolute_error': 7.0528131542735295e-06, 'max_absolute_error': 1.760198931921586e-05, 'status': 'PASS', 'method': 'SONIA rate ACT/365 between XLON sessions; independently compared with official SONIA Compounded Index'}`.

No fee, haircut, tax or account-specific spread is applied in A2. The series is not represented as CSH2 or another cash-like ETF, and it is not a claim about IBKR or any broker's client cash rate.
