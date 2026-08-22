# UKACTIVE A2 — FX and GBP Accounting Policy

Portfolio accounting currency is GBP. GBP and GBX listing lines receive no FX conversion; GBX applies the explicit price-unit multiplier `0.01`. Foreign-currency listing wealth is local adjusted wealth multiplied once by the ECB GBP-per-local reference rate published by the XLON close. The same-date rate is used when present; only ECB/TARGET observation gaps fall back to the latest prior rate.

The ECB normally publishes the reference rates around 16:00 CET, before the 16:30 Europe/London LSE close. They are used as deterministic informational valuation references, not asserted transaction prices.

Trading currency is not used to infer underlying economic currency exposure. A GBP-listed unhedged US equity ETF therefore receives no second FX conversion: its GBP quote already embeds translation. A USD listing of the same ISIN is converted once for GBP accounting.

Same-ISIN GBP/foreign listing validation statuses were `{'WARNING': 120, 'PASS': 8, 'UNRESOLVED_NO_COMMON_VALID_DATES': 6, 'FAIL': 1}` across 135 pairs. A2 recorded every A0A1/EODHD GBP-versus-GBX discrepancy as a versioned lineage correction rather than silently changing A0A1.
