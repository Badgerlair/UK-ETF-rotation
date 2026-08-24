# UKACTIVE-A4D — provenance and research delta

Status: preregistration audit completed before A4D outcome computation  
Repository starting commit: `68f91022e11a4085a3cf7fb545306c9f792b3d85`  
Historical data cutoff: `2026-08-21`  
Evidence ceiling: `E2_DEVELOPMENTAL`; adaptive mechanism interpretation is `E1_EXPLORATORY`; no A4D result is E3.

## Canonical lineage reconstructed

There is no separate canonical `UKACTIVE-A1` artifact set. The identity/universe stage is the combined `UKACTIVE-A0A1` lineage. It retained 99 economic exposure families from 4,359 LSE discovery rows, with signal identity fixed at `economic_exposure_family_id`, not ticker, listing or ISIN.

The authoritative return and timing chain is A2 → A2R → A2R2. A2R closed the 14 material semantic-lineage cases; A2R2 repaired observed-union calendar contamination and an invalid consecutive-daily-return rolling rule. A4D therefore uses only:

- `UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet`;
- `UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet`;
- `UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet`;
- the deterministic A2R2 XLON calendar;
- the validated A2 actual-GBP-cash series.

Formation endpoints require an exact valid decision-date endpoint and the nominal historical XLON endpoint, or only the nearest previous valid endpoint within three genuine XLON sessions. Gaps beyond three sessions reset continuity. No price or return is forward-filled, proxy history is excluded, stale observations remain invalid, and a decision after close T can execute only after T.

The frozen A4D primary pool is the accepted dynamic `INDUSTRY_PLUS_THEME` economic-family pool: 27 structural families (9 industry, 18 theme), of which 25 have valid 252-session signal history at the 2026-08-21 cutoff. Dynamic admission is signal-specific and point-in-time. The earliest valid 252-session observation in this pool is 2007-10-25; families are not required to share a start date.

Benchmark A is `GLOBAL_DEVELOPED_WORLD`. Benchmark B is the contemporaneously eligible equal-weight `INDUSTRY_PLUS_THEME` research index. Cash is the validated GBP cash index based on SONIA/ACT-365 and is not treated as zero return or as an ETF.

The canonical implementation-cost convention is 20 bp one-way friction plus £3.99 per actual risky trade leg on £250,000. The doubled stress is 40 bp plus £7.98 per leg. Product OCFs are already embedded in implementation total returns and are not charged twice. No stamp duty is assumed without product-specific evidence.

## Prior findings that remain immutable

- A3: `UKACTIVE_A3_WEAK_OR_REGIME_DEPENDENT_SIGNAL`. `ABOVE_GBP_CASH_252` was the best-supported but secondary qualification; no FDR-surviving broad signal was established.
- A3R1R1: `UKACTIVE_A3R1_RESEARCH_CANDIDATE_FOUND`. Multi-horizon level and pairwise industry evidence were economically interesting but statistically unresolved; acceleration was rejected and geography/broad sector were not trade candidates.
- A3R2: `UKACTIVE_A3R2_REGIME_CONDITIONAL_CANDIDATE_FOUND`. The developmental contemporary candidate was `INDUSTRY_PLUS_THEME | 3/6/12 | TOP_1 | MONTHLY | EQUAL`; equal weighting remained preferred. A3R2 tested TOP1/2/3/5/variable and weekly/fortnightly/monthly, but not TOP4/6/7/8/9/10 or daily review.
- A4: `UKACTIVE_A4_REGIME_CONDITIONAL_ONLY`. The five-year TOP1 result was positively skewed and depended on a few plausible winners; TOP2/TOP3 did not resolve that dependence.
- A4B: `UKACTIVE_A4B_BASELINE_REMAINS_PREFERRED`. The preregistered fast taper, MFE locks, strength harvesting and regime multipliers failed their economic gates.
- A4C: `UKACTIVE_A4C_CORE_SATELLITE_CANDIDATE_FOUND`. Fast scouts and weekly trend-failure exits were rejected; direct volatility sizing reduced risk but surrendered too much right tail; the 50/50 global-core/active blend was the only promoted E2 architecture.
- A5S setup: `UKACTIVE_A5_SETUP_PASS`, but prospective A5 is incomplete and has not started. Decision, execution, NAV and run ledgers contain zero prospective events. A4D must not write to them or alter either frozen A5 model.

## What A4D genuinely adds

1. A new fixed 10/15/25/30/20 multi-horizon rank composite.
2. One asymmetric fast-versus-structural deterioration-aware score; it is not the rejected A3R1 acceleration composite.
3. Momentum-age and leadership-state diagnostics on a fixed weekly clock.
4. A complete equal-weight TOP3–TOP10 breadth frontier and marginal-holding attribution.
5. A causal DAILY cadence compared with WEEKLY and MONTHLY while holding other rules fixed.
6. Diversified-portfolio cash architectures based on the prior A3 cash qualification, contemporaneous pool breadth and the frozen global benchmark.
7. Limited rank-decay and one predetermined bounded top-heavy weighting only after a breadth region survives.

## What A4D cannot establish causally

All historical data through 2026-08-21 have been exposed to the research programme. No genuinely untouched historical holdout exists. Parameter exploration is therefore developmental E2/E1 evidence, not independent confirmation. Current 25/25 ii visibility is dated current-only metadata and cannot establish historical broker, ISA or retail availability. Historical spread observations are unavailable; costs are controlled assumptions. A4D may freeze a prospective candidate, but only future untouched observations can supply E3 evidence.

## Unresolved deployment blockers

- historical UK-retail, ISA, account and platform eligibility remains partly unresolved;
- realised historical bid/ask spreads and market impact are not observed;
- dynamic recent-theme survivorship reconstruction is substantially complete, not perfect;
- all new A4D selection is outcome-exposed developmental research;
- no A4D result authorises orders, deployment or modification of A5.

