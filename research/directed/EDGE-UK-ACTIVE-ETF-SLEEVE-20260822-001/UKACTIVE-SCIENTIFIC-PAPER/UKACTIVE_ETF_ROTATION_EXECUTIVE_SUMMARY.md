# UKACTIVE ETF Rotation — Executive Research Summary

Version 1.0 — 2026-08-27  
Historical cutoff: 2026-08-21  
Evidence grade: `E2_DEVELOPMENTAL`  
Model status: `FROZEN`; historical development `CLOSED`  
Current readiness: `AWAITING_CURRENT_HOLDINGS_INPUT`; `pilot_operationally_ready=false`

## Purpose and conclusion

UKACTIVE investigates whether a UK SIPP can use a small, systematic ETF sleeve to participate in persistent leadership among industry and thematic exposures. The research unit is an economic-exposure family rather than a ticker, which prevents several listings of the same exposure from occupying several ranks. The final model is a long-only monthly relative-momentum process. It is not a whole-pension recommendation and it is not classified as independently confirmed alpha.

The frozen scientific strategy is:

`INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL`

For each eligible family, M2 calculates benchmark-relative total returns over 21, 42, 63, 126 and 252 London trading sessions, converts each horizon to a cross-sectional percentile, and combines them with weights 10%, 15%, 25%, 30% and 20%. It selects the seven highest families, equal-weights them, and trades on the first valid XLON session after month-end. The signal uses no leverage, shorting, same-close execution, discretionary substitution, cash-timing or regime allocation.

The central finding is deliberately qualified. M2 contains meaningful causal historical ranking information: matched random selection and rank shuffling placed its diagnostic CAGR above the 99th percentile of 10,000 paths. The standalone after-cost portfolio also exceeded both SWDA/global developed equities and the contemporaneous equal-weight industry/theme pool on the common 2017–2026 window. However, its advantage is episodic, statistically imprecise, cost-sensitive and materially dependent on a small set of years and holding spells. It is frozen for controlled prospective observation, not declared proven.

## Data and causal controls

The research began with 4,359 current LSE lines and 2,821 raw ISINs, curated to 296 share classes, 478 listings and 99 economic families. The final structural M2 pool has 27 families; 25 were signal-ready at the cutoff and two remained in warm-up. The common executable comparison window is 2017-03-01 to 2026-08-21.

The programme rebuilt a point-in-time research chain after two blocking audits. A3R0 found 14 material family/history mismatches; 13 were corrected without proxying the unresolved family. A later audit found 29 false vendor sessions. A2R2 replaced them with a deterministic XLON calendar and a prior-only endpoint rule: an observation may be accepted within three preceding true sessions, never from the future, and longer gaps reset the history. Missing observations are not forward-filled. Fund launches, closures and current broker availability are not back-projected.

Histories use validated adjusted close as the total-return basis. GBP and GBX units are normalised, foreign histories are converted once to GBP, and a GBP dealing line is not described as currency hedged unless the fund is hedged. Historical cash is a time-varying SONIA-based series, not a permanent 4% return.

## What was tested

The lineage tested isolated signals; multi-horizon M1, M2 and M3 composites; TOP3 through TOP10; daily, weekly and monthly cadence; five cash architectures; equal, rank-decay and top-heavy weighting; early entry, fast exits, giveback locks, deterioration and momentum-age ideas; matched-risk and matched-exposure controls; random selection and rank shuffling; static core/satellite wrappers; four causal regimes; and five dynamic policies with immediate and hysteresis switching.

Important negative results were retained:

- A3R1R1 tested 180 inference cells and A3R2 tested 315 portfolio specifications; neither produced a broad false-discovery-adjusted survivor.
- TOP3–TOP4 were too concentrated; TOP10 diluted the ranking effect.
- Daily trading lost most gross return to cost. Weekly was plausible at baseline costs but reversed versus the equal pool when costs doubled.
- CASH1 looked favourable recently but on full history compounded at 9.53%, lagged the pool by 2.00 percentage points and had a worse −27.16% drawdown. It also failed static matched-exposure controls.
- No deterioration, momentum-age, discretionary exit or weighting overlay improved the complete outcome.
- No dynamic regime policy passed. Regimes remain telemetry only.

M2, TOP7, monthly and equal weighting were selected as a coherent, simple representative—not as four uniquely optimal cells. TOP6 had the highest full-history CAGR; TOP8 had the highest latest-five-year CAGR. TOP7 sits within the TOP6–TOP9 region and avoids selecting either observed maximum.

## Historical economics and uncertainty

On 2017-03-01–2026-08-21, at the scientific £250,000 cost convention:

| Portfolio | Net CAGR | Terminal wealth / £100,000 | MDD | Ulcer | Volatility | Longest underwater |
|---|---:|---:|---:|---:|---:|---:|
| SWDA/global | 11.60% | £282,859 | −25.58% | 4.89% | 14.57% | 586 days |
| Equal opportunity pool | 11.53% | £281,204 | −28.30% | 6.52% | 16.77% | 444 days |
| **M2 TOP7** | **13.14%** | **£321,979** | **−23.53%** | **8.20%** | **18.49%** | **857 days** |
| 50% SWDA / 50% M2 comparator | 12.40% | £302,751 | −23.62% | 5.89% | 15.87% | 763 days |
| 75% SWDA / 25% cash control | 9.26% | £231,457 | −19.55% | 3.60% | 10.88% | 550 days |

M2's full CAGR differences were +1.54 percentage points versus SWDA and +1.61 percentage points versus the pool. Latest-five-year net CAGR was 13.62%, +2.10 points versus SWDA. Baseline turnover was 5.52× and cost drag 1.34 points; doubled costs reduced CAGR to 11.80%, leaving only a small margin.

Performance was concentrated. M2 materially improved 2020 and 2025 but lagged SWDA in most other full or partial calendar years. Excluding 2025 reversed the SWDA difference to −1.03 points; excluding 2020 and 2025 produced −3.78 points. Battery/EV, semiconductors, silver miners, gold miners and European banks contributed 64.92% of gross family P&L. No single-family deletion reversed the full result, but deleting the largest holding spell essentially removed the active advantage; deleting the top three spells reduced CAGR to 9.47% and reversed it by −2.13 points versus SWDA.

Six-month circular block bootstraps on 59 latest-five-year monthly observations produced wide 95% intervals. Arithmetic annualised excess versus SWDA was 1.88% with an interval from −9.04% to 16.20% and 59.86% positive paths. Versus the pool it was 2.94%, interval −5.61% to 12.73%, with 73.80% positive. Both intervals include zero.

## Intended SIPP use

The three portfolio objects must remain distinct:

- **Scientific active strategy:** 100% M2 diagnostic used to estimate ranking economics.
- **Conditional initial pilot:** 65% SWDA, 10% M2, 25% defensive assets.
- **Capital-continuity control:** 75% SWDA, 25% defensive assets, 0% M2.

At a 10% sleeve, each M2 family is approximately 1.43% of the whole SIPP. Total active/thematic exposure must remain at or below 25%; M2 must absorb or replace existing thematic holdings rather than automatically add risk.

At a £563,000 II Plus illustration, the 10% wrapper's full-history gross CAGR was 9.61%, subscription-separated net CAGR 9.42%, subscription-included CAGR 9.40%, MDD −19.11% and incremental CAGR +0.14 points versus the 75/25 control. Latest-five-year subscription-separated CAGR was 9.80%, +0.23 points versus control, with −13.51% MDD. The 15% and 25% rows are research comparators, not authorised allocations.

Historical costs assume market-price execution, 20 bps one-way friction and fixed dealing fees. Preferred GBP/GBX lines incur no broker FX conversion fee, but underlying currency exposure remains. RLON is intended for strategic defence but its exact share class remained unresolved. CSH2 (`LU1230136894`) is tactical liquidity and receives unavailable M2 slots. Neither is assumed to earn 4% indefinitely.

## Governance and next evidence

The process suspends for data/calendar/hash failure, rank non-reproducibility, unavailable instruments, missed three-session execution, one-way friction above 40 bps or a material historical defect. Short-term underperformance alone is not a model defect, and there is no performance-only stop.

The prospective ledger was empty at freeze. Each future month must record data hashes, eligible families, scores, ranks, mappings, targets, actual fills, fees, shortfall, substitutions and control outcomes. There is no automatic requirement to wait exactly 24–36 months and no automatic escalation after profits. A higher allocation would require varied prospective leadership episodes, operational stability, costs within bounds, continued advantage versus controls and explicit approval.

**Permitted use:** controlled 10% pilot after operational readiness and explicit user approval.  
**Not established:** independently confirmed alpha, guaranteed drawdown protection, a permanent 4% cash return, superiority in every regime, or suitability for unrestricted whole-SIPP allocation.

