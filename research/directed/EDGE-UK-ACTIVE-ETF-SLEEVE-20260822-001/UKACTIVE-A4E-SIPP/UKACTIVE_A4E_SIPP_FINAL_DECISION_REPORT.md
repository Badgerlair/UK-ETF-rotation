# UKACTIVE-A4E-SIPP — final decision report

Historical cutoff: **2026-08-21**  
Evidence: **E2 developmental; no independent confirmation**  
Decision: **UKACTIVE_A4E_SIPP_STRATEGY_SELECTED**

## What we now know

A4D reproduced exactly. CASH1 retains the attractive five-year economics but fails the preregistered full-history retention and stability standard: full-history TOP7 CAGR falls from 13.14% CASH0 to 9.53% CASH1, and full-history drawdown changes from -23.53% to -27.16%. Its recent drawdown benefit is real economic information, but not a stable whole-period timing edge. CORE1 global absolute momentum also fails: it retains 58.8% of CORE0 CAGR and does not improve full-history maximum drawdown.

The final active-edge hierarchy is `False`. Full-history equal-pool excess is -2.00%; excluding 2025 it is -3.85%; doubled-cost full-history excess is -3.26%. Random/rank-shuffle percentiles are reported in the falsification table, but do not overcome the failed full-history cash/risk gate or missing E3 evidence.

Matched exposure rejects a timing claim for CASH1. A static version of the same rotation portfolio at CASH1's average exposure produced 11.27% CAGR and -19.64% drawdown versus CASH1's 9.53% and -27.16%; the same-exposure global/cash control produced 9.96% and -21.38%. CASH1 ranked at the 94.4% percentile of matched-count random selection and the 99.6% percentile of monthly rank shuffles, which is interesting E2 evidence but not enough to pass the mandatory active-edge hierarchy. M2_BASE and its bounded neighbours broadly retain an always-invested TOP6–TOP8 ranking effect; TOP9 and family-removal sensitivity show that it is not a sufficiently stable whole-SIPP alpha claim.

## What we can rule out

- M2 neighbourhood testing does not convert the exposed result into independent confirmation.
- Exact CASH1 is not a reliable full-history drawdown solution.
- The frozen 252-session global/cash rule is not a superior retirement core over the causal period.
- Weekly CASH1 exit-only monitoring and rank hysteresis cannot be promoted unless all frozen gates pass; failed rows remain disclosed.
- No accepted implementation data support 2000–03 or 2007–09 crisis claims.

## What looks economically interesting

CASH1’s post-2020 and final-five-year behaviour remains worth prospective shadow observation. It is selected before outcomes through the same family-level process and ranks unusually relative to the bounded random controls. This is a developmental mechanism lead, not a live alpha claim.

## BEST AVAILABLE WHOLE-SIPP STRATEGY

`GLOBAL_CASH_75_25`

- 75% `GLOBAL_DEVELOPED_WORLD` through SWDA, ISIN IE00B4L5Y983.
- 25% Interactive Investor SIPP GBP broker cash.
- Rebalance after the final valid XLON close each month.
- Execute at the first valid next XLON session within three sessions; never same-close.
- No volatility scaling, leverage, shorting, discretionary replacement or active theme allocation.
- If SWDA is unavailable, leave the affected amount in GBP cash until a same-exposure alternate is separately evidenced and frozen.
- Historical cost convention: 20 bp one-way plus £3.99 per leg; live platform, TER and cash-rate economics are reported separately.

## WHY THIS STRATEGY WAS SELECTED

No active or dynamic global/cash candidate cleared the complete return/risk hierarchy. The mandatory fallback rule therefore selected the highest-return static global/cash allocation that remains inside the approximately -20% historical drawdown budget. It is simpler, cheaper and less dependent on 2025 or a small set of thematic winners than the rotation alternatives. It does not claim alpha and may sacrifice material equity upside; that is the explicit cost of the selected drawdown budget.

Full-history selected metrics: net CAGR **9.26%**, maximum drawdown **-19.55%**, Ulcer Index **3.60%**, Calmar **0.47**, average cash **24.9%**.

At £250,000, the current live-cost audit estimates **£674 (0.27%)** including platform fee, an explicit spread assumption and SWDA TER. TER is already economically embedded in realised ETF returns and is shown here for ownership-cost transparency, not added a second time to the historical total-return chain.

## EXPECTED PERFORMANCE RANGE

- Conservative governance planning range for net CAGR: **4% to 9% nominal after costs**.
- Conservative maximum-drawdown planning range: **approximately -15% to -30%**.
- Observed historical net-CAGR reference across full/five-/three-year windows: **9.3% to 15.0%**; this short-sample range is not the expectation.
- Observed historical maximum-drawdown range: **-19.6% to -13.9%**; future drawdown can be worse.
- Strategic cash allocation: **25%**, with drift corrected monthly.
- Expected turnover: approximately **0.14x** annual traded notional under the historical engine.
- Likely underperformance: strong uninterrupted global-equity bull markets, rapid rebounds after cash has reduced beta, and periods when the global core substantially outpaces cash.
- Principal uncertainty: no accepted 2000–03/2007–09 implementation test, no inflation series, short 2017–2026 whole-portfolio history and no E3 evidence.

These are historical reference ranges, not forecasts or drawdown guarantees.

## ACTIVE ROTATION SLEEVE

Architecture: `M2_BASE | TOP7 | MONTHLY | CASH1 | EQUAL`. Evidence: **E2 developmental**. Allocation: **0%**. Status: **shadow observation only** under `CORE_ONLY`. The current 25-family implementation map is ii-confirmed, but SIPP-specific evidence remains incomplete for active lines.

## CORE STRATEGY

Static 75% SWDA / 25% ii SIPP GBP cash, rebalanced monthly after the final valid XLON close and executed next session. The tested 252-session dynamic global/cash rule was rejected because it lost too much return without improving full-history maximum drawdown.

## CURRENT DEPLOYMENT TIER

`CORE_ONLY`

## MONTHLY OPERATING RULE

Validate data and instrument state after month-end close; freeze a 75/25 target; record it before next-session close; execute at the first valid next XLON session; book all legs/costs; leave unavailable exposure in GBP cash; reconcile holdings and audit hashes. Rotation rankings are telemetry/shadow only and cannot change the whole-SIPP allocation.

## FAILURE MODES

The strategy can lag badly in strong equity markets, cash rates can fall, monthly rebalancing can be late around gaps, SWDA remains exposed to global equity and currency risk, and a future drawdown can exceed the historical range. Inflation can erode the fixed cash sleeve. The active shadow can fail because its apparent edge is regime- and right-tail-dependent.

## SUSPENSION AND REVIEW RULES

Suspend affected purchases for unavailable instruments, unreproducible point-in-time membership, invalid prices/signals, or material cost overruns. Reopen research for systematic prospective divergence, meaningful matched-risk failure, risk-envelope breach or a discovered lineage defect. Review the rotation shadow at 6/12/24/36 valid monthly decisions; do not increase allocation based only on profitability.

## REMAINING EVIDENCE GAP

No untouched historical holdout, no prospective A4E lineage, no accepted 2000–09 implementation stress, incomplete active-line SIPP/product-cost evidence, no accepted UK inflation series and uncertain future broker cash rates. Rotation remains a shadow hypothesis rather than a material SIPP sleeve.
