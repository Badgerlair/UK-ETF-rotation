# UKACTIVE A2 Manual Validation Cases

These are data-accounting reconstructions only. They are not a strategy backtest and contain no portfolio-performance result.

| Case | Instrument | Date | Method | Absolute error | Status |
|---|---|---:|---|---:|---|
| MAN-01 — UK equity ETF | ISF / IE0005042456 | 2013-06-19 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-02 — US equity UCITS ETF listed in GBP | CSP1 / IE00B5BMR087 | 2019-09-26 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-03 — US equity ETF alternate USD listing | CSPX / IE00B5BMR087 | 2018-09-24 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-04 — Europe ETF | SMEA / IE00B4K48X80 | 2020-09-25 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-05 — Japan ETF | VJPN / IE00B95PGT31 | 2020-01-13 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-06 — Emerging-market ETF | VFEM / IE00B3VVMM84 | 2019-07-22 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-07 — Semiconductor ETF | SMGB / IE00BMC38736 | 2023-10-19 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-08 — Distributing equity ETF | ISF / IE0005042456 | 2000-08-29 | (raw close_t * split ratio + distribution converted to quote units) / raw close_t-1 - 1 | 3.539540417e-05 | PASS |
| MAN-09 — Accumulating economic equivalent | CSP1 / IE00B5BMR087 | 2019-09-26 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-10 — Government-bond ETF | VGOV / IE00B42WWV65 | 2019-10-09 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-11 — Corporate-bond ETF | SLXX / IE00B00FV011 | 2004-06-02 | (raw close_t * split ratio + distribution converted to quote units) / raw close_t-1 - 1 | 2.310264181e-05 | PASS |
| MAN-12 — Gold ETC | SGLN / IE00B4ND3602 | 2018-12-24 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-13 — Cash-like ETF | FEDG / LU1233598447 | 2022-10-07 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-14 — Actual GBP cash proxy | ACTUAL_GBP_CASH / NOT_APPLICABLE | 2022-06-22 | (1 + prior SONIA/100)^(calendar_days/365)-1; compared with IUDZOS2 index ratio | 1.916433081e-07 | PASS |
| MAN-15 — Hedged equity ETF | IGUS / IE00B3Y8X563 | 2018-09-25 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-16 — Unhedged equivalent | CSP1 / IE00B5BMR087 | 2019-09-26 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-17 — Later-inception ETF | DFNX / IE000BRM9046 | 2024-11-06 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-18 — Delisted/closed listing | HLTG / LU0533033311 | 2021-12-20 | adjusted GBP wealth_t / adjusted GBP wealth_t-1 - 1 | 0 | PASS |
| MAN-19 — Explicit ex-distribution event | ISF / IE0005042456 | 2000-08-29 | (raw close_t * split ratio + distribution converted to quote units) / raw close_t-1 - 1 | 3.539540417e-05 | PASS |
| MAN-20 — Explicit GBX-listed instrument | ISF / IE0005042456 | 2013-06-19 | displayed GBX close * 0.01 = GBP price | 0 | PASS |

For distributing lines, the distribution is used once for reconstruction and is not added to the adjusted-close return. For foreign-currency lines, GBP wealth uses the ECB rate published by the XLON close (same-date when available, otherwise latest prior across an observation gap). GBX cases explicitly apply 0.01.
