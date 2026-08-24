# UKACTIVE-A4E-SIPP reproduction audit

Decision: `PASS`

- Deterministic cells reconciled: 720/720 within 1e-10.
- Common causal boundary: 2017-02-03; first executable monthly portfolio row: 2017-03-01.
- Headline CAGR-difference full-history excess vs pool: 1.605658%.
- Arithmetic annualised daily-return excess vs pool: 4.386409%.
- A4D monthly block-bootstrap observed excess vs pool: 2.938498%.

These are different estimands and are not expected to be numerically identical. Turnover is window-specific because the numerator includes only trades executed inside each window and the denominator is that window’s calendar duration. Accepted GBP cash accrues from `UKACTIVE_A2_CASH_SERIES.parquet`; distributions and FX are already embedded once in the A2R2 GBP total-return endpoints. No later data, proxy, closure bridge or forward-filled return was introduced. Partial 2017 and partial 2026 remain explicitly partial.
