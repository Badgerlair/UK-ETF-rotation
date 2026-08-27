# UKACTIVE paper metric glossary

Version: 1.0  
Historical cutoff: 2026-08-21  
Frozen model: `INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL`

This glossary defines the terms used in the scientific paper and supplement. Percentages are returns or risk measures unless explicitly labelled percentage points (`pp`) or basis points (`bps`). One basis point is 0.01 percentage point. Unless a table says otherwise, M2 results are after the canonical 20 bps one-way market-friction assumption and the applicable fixed dealing charge; fund total expense ratios are reflected in observed ETF total-return histories and are not deducted again.

## Return and wealth measures

**Simple total return.** For an instrument or portfolio with value (V_t), the one-period simple total return is (r_t=V_t/V_{t-1}-1), including distributions when the source is an adjusted or total-return series. A return of 0.05 means 5.00%.

**Gross return.** Portfolio return before the explicit simulated transaction-cost debit. Gross does not mean that the underlying ETF's expense ratio has been added back; the observed adjusted-price history already reflects fund-level performance.

**Net return.** Portfolio return after the specified transaction-cost model. In A5C whole-SIPP tables, “subscription separate” deducts market friction and paid dealing charges but reports the Interactive Investor subscription as an account-level cost outside the incremental M2 comparison. “Subscription included” additionally deducts that subscription from the simulated account. The treatment must always be stated.

**Cumulative return.** The geometrically compounded return over (T) observations:

\[
R_{1:T}=\prod_{t=1}^{T}(1+r_t)-1.
\]

**Compound annual growth rate (CAGR).** If the beginning and ending wealth are (V_0) and (V_T), separated by (Y) years,

\[
\operatorname{CAGR}=\left(\frac{V_T}{V_0}\right)^{1/Y}-1.
\]

CAGR is a geometric rate. It is not the arithmetic mean of annual or daily returns.

**Terminal wealth.** Final portfolio value generated from a stated initial notional after compounding the specified return series. “Terminal wealth per £100,000” is (100{,}000\prod_t(1+r_t)). Values from different sample windows are not directly comparable.

**Arithmetic annualised excess.** The arithmetic mean of periodic candidate-minus-benchmark returns multiplied by the annualisation factor. For daily observations it is typically (252\bar{x}); for monthly observations, (12\bar{x}). It differs from a difference in CAGRs because it does not geometrically compound either series.

**CAGR difference.** Candidate CAGR minus comparator CAGR over the same window, expressed in percentage points. It is a difference between two geometric annual rates, not the CAGR of a return-difference series.

**Compounded relative return.** For candidate (C) and benchmark (B),

\[
R^{\mathrm{rel}}_{1:T}=\frac{\prod_t(1+r^C_t)}{\prod_t(1+r^B_t)}-1.
\]

This is used in rolling relative-regret displays. It differs from the arithmetic sum or mean of (r^C_t-r^B_t).

**Rolling excess.** A relative-performance statistic recalculated over a trailing window ending at each observation. In Figures 8 and 16 it is the compounded candidate return minus, or divided relative to, the corresponding compounded benchmark return as stated in the caption. The window length and exact convention must be identified.

**Active return / excess return.** A generic label that is prohibited without an estimand. The paper therefore specifies one of: CAGR difference, arithmetic annualised return difference, or compounded relative return. “M2 excess versus SWDA” in common-window economic scorecards means M2 net CAGR minus SWDA CAGR unless the table says otherwise.

## Risk and path measures

**Drawdown.** For wealth (V_t) and the running peak (P_t=\max_{s\leq t}V_s), drawdown is (D_t=V_t/P_t-1\leq0).

**Maximum drawdown (MDD).** The minimum value of (D_t) over the sample. It is reported as a negative percentage in tables. Figures that place “drawdown magnitude” on a positive horizontal axis plot (|\operatorname{MDD}|).

**Relative drawdown.** A decline in candidate wealth relative to a benchmark-relative wealth peak. It answers how far the candidate has fallen behind its best cumulative position versus the comparator; it is not the same as the candidate's absolute MDD.

**Ulcer Index.** The root mean square of percentage drawdowns:

\[
\operatorname{Ulcer}=\sqrt{\frac{1}{T}\sum_{t=1}^{T}D_t^2}.
\]

It reflects both depth and persistence of below-peak experience. Lower is better, but it is sample-dependent.

**Calmar ratio.** Annualised compound return divided by maximum-drawdown magnitude:

\[
\operatorname{Calmar}=\frac{\operatorname{CAGR}}{|\operatorname{MDD}|}.
\]

It is descriptive and inherits the sampling error of both numerator and denominator.

**Annualised volatility.** Sample standard deviation of periodic returns multiplied by the square root of the assumed number of periods per year, normally (sqrt{252}) for daily returns. It measures dispersion rather than permanent loss.

**Longest underwater period.** Maximum calendar-day span during which portfolio wealth remains below its previous high-water mark, measured using the canonical wealth path. It is not the same as the time from drawdown trough to recovery.

**Worst rolling six months.** The minimum compounded return over all eligible trailing six-month windows under the canonical convention. This is a path diagnostic, not a confidence bound.

**Relative regret.** The paper's descriptive name for candidate underperformance versus its designated comparator over rolling horizons. It is not a utility-theory regret estimator and does not define a performance stop.

## Trading and cost measures

**Portfolio turnover.** The sum of absolute changes in portfolio weights at a rebalance, aggregated through time according to the source implementation. Cash is included or excluded only as defined by the originating canonical calculation.

**Traded-notional turnover.** The monetary amount bought plus the monetary amount sold, divided by portfolio net asset value. A value of 1.00 means traded notional equal to 100% of account value over the stated annualised period; it does not necessarily mean the entire portfolio was replaced once.

**Trade leg.** One purchase or one sale of one instrument generated by the rebalance. A switch from ETF A to ETF B normally creates two legs. The leg count is used to apply fixed dealing fees and free-trade credits.

**Replacement rate.** At a review, the fraction of selected risky slots whose economic-exposure family differs from the previous selection. It is distinct from traded-notional turnover because existing weights may drift and trades may occur without a family replacement.

**Average holding period.** Mean elapsed calendar days for completed holding spells under the canonical spell definition. Open spells and same-family rebalances are treated as specified in the underlying ledger.

**One-way friction.** Proportional cost applied separately to purchases and sales. The baseline is 20 bps one-way. A complete round trip therefore incurs proportional friction on both legs, before fixed dealing charges.

**Cost drag.** Gross CAGR minus net CAGR under the stated cost model and sample, expressed in percentage points per year. Because gross and net wealth compound separately, cost drag is not simply annual turnover multiplied by the one-way rate.

**Historical total market friction.** Cumulative simulated proportional friction plus applicable dealing charges over the backtest at the stated notional. It excludes the account subscription when that subscription is reported separately.

**Implementation shortfall.** Difference between the model's reference execution value and the actual achieved execution value, including spread, delay and market impact under the chosen sign convention. Prospective implementation shortfall is recorded from actual fills; no unarchived manual spread statistic is treated as historical evidence.

**Market-price execution assumption.** The conservative modelling convention that transactions are costed at observable market prices with the explicit one-way friction, rather than assuming midpoint fills. It is an assumption, not a claim that every live order will execute at the worst displayed price.

**Subscription-separated result.** A5C net performance after market friction and dealing charges, with the broker plan subscription disclosed separately because it supports the whole account rather than only M2.

**Subscription-included result.** A5C net performance after market friction, dealing charges and the full simulated broker plan subscription. It is a conservative all-in account view, not the preferred measure of M2's incremental cost.

## Signal and cross-sectional measures

**Economic-exposure family.** The canonical ranked unit representing one economic theme or industry. Multiple listings or share classes may implement the same family; they do not receive independent ranks.

**Eligible family.** A structural family with all data required by the frozen point-in-time rule at the review date, including complete 21-, 42-, 63-, 126- and 252-session components. Current broker availability is not part of historical signal eligibility.

**Relative strength (RS).** The frozen horizon-(h) benchmark-relative cumulative total return:

\[
RS^{\mathrm{raw}}_{i,t,h}=\frac{1+R_{i,t,h}}{1+R_{B,t,h}}-1,
\]

subsequently converted to an average-tie cross-sectional percentile among eligible families. The paper uses `RS21`, `RS42`, `RS63`, `RS126` and `RS252` for those percentile values.

**Percentile rank.** Pandas-style average rank divided by the number of non-missing eligible observations at the same review date. Larger values denote stronger benchmark-relative history. Exact ties receive their average rank.

**M2 score.** The frozen composite (0.10RS21+0.15RS42+0.25RS63+0.30RS126+0.20RS252). It is defined only when every component exists and at least three families are eligible for cross-sectional ranking.

**Rank information coefficient (rank IC).** Spearman-type cross-sectional association between a signal rank at time (t) and a specified future return. Positive IC indicates that higher-ranked families subsequently performed better on average. Overlapping horizons induce dependence; the originating tables therefore use heteroskedasticity-and-autocorrelation-consistent inference where specified.

**Top-tail / top-quintile return.** Forward outcome for a signal-defined high-rank group under the precise originating rule. It is a diagnostic of ranking monotonicity, not the return of the final TOP7 portfolio unless explicitly labelled as such.

**Eligibility denominator.** Number of families with valid values included in a review-date cross-section. It changes through time as histories become available or cease to be valid; current structural members are not back-filled into earlier denominators.

**Rank persistence.** Cross-sectional stability of ranks between consecutive causal review dates, as defined in the A4F regime ledger. It is telemetry and does not control the frozen allocation.

**Leadership spread.** A4F difference between the aggregate strength of leading families and the broader opportunity set under the frozen prior-only calculation. It is one of three leadership telemetry components.

## Cash, allocation and exposure measures

**Cash weight.** Fraction of portfolio value assigned to the accepted historical time-varying GBP cash series, or to the corresponding live liquidity vehicle under prospective rules. A zero strategic cash weight in M2 does not mean that the whole SIPP has no defensive allocation.

**CASH0.** Frozen always-invested active-sleeve architecture: every available TOP7 risky slot is invested; only an unavailable or suspended live implementation slot is temporarily mapped to CSH2 under the operational rule.

**CASH1–CASH4.** Developmental defensive architectures defined in the A4D scorecards. They are rejected research variants and must not be mistaken for live controls.

**Matched exposure.** A static comparator with the same average risky exposure as a dynamic rule. It distinguishes a timing benefit from the mechanically lower risk of holding less equity.

**Active-sleeve return.** Return of the standalone 100% M2 diagnostic portfolio. It is not the return of the whole SIPP when M2 occupies 10%, 15% or 25% of capital.

**Whole-SIPP wrapper return.** Return of the complete core/M2/defensive allocation after wrapper-level costs. The authorised pilot target is 65% SWDA, 10% M2 and 25% defensive assets; the signal itself remains unchanged.

## Statistical and falsification measures

**HAC test.** A test using a heteroskedasticity-and-autocorrelation-consistent covariance estimator to account for non-constant variance and serial dependence. The lag rule must come from the source artefact; HAC does not create an independent holdout.

**Raw p-value.** Probability, under the specified null and test assumptions, of a statistic at least as extreme as observed. It is not the probability that the strategy has no edge.

**False-discovery-adjusted q-value.** Benjamini–Hochberg-style multiple-testing adjustment recorded in the originating inference ledger. A q-value is the smallest false-discovery-rate threshold at which a cell would be selected. No A3/A4D broad signal result used here is described as surviving where the canonical ledger says otherwise.

**Block bootstrap.** Resampling method that draws contiguous return blocks rather than independent individual months. The A4D uncertainty calculation used a six-month circular block, 59 monthly observations and 5,000 paths on the latest-five-year window.

**Bootstrap probability of positive excess.** Fraction of resampled paths for which the specified arithmetic annualised candidate-minus-comparator return is positive. It is conditional on the historical series and bootstrap design, not a literal probability of future success.

**Bootstrap confidence interval.** Percentile range of a statistic across block-resampled paths. Inclusion of zero means the completed procedure did not exclude non-positive excess at the reported level.

**Random-selection percentile.** Fraction of matched random paths whose diagnostic outcome is no better than the M2 candidate under the canonical orientation. It answers whether the historical ranking beat random choice from the same opportunity set; it does not establish stable alpha or eliminate contributor concentration.

**Rank-shuffle control.** A monthly falsification that destroys the mapping between M2 ranks and chosen families while preserving the contemporaneous opportunity set and selected count.

**Leave-one-family-out test.** Recomputed strategy result after excluding one economic family. The minimum single-family exclusion remained positive versus SWDA, but joint top-three and top-five exclusions reversed the incremental result.

**Holding-spell deletion.** Ex-post influence diagnostic that removes specified completed holding spells and recomputes the outcome. It measures concentration of the historical estimate; it is not an implementable exit rule.

**Contributor share.** Normalised arithmetic contribution of a family, rank bucket or holding spell to gross family market P&L. Shares can exceed 100% collectively when other contributors are negative. They are not CAGRs and are not additive to after-cost portfolio CAGR.

**Evidence grade E2_DEVELOPMENTAL.** Internal classification indicating causal developmental historical evidence without independent confirmation. It is compatible with a frozen limited pilot after operational readiness; it is not a claim of validation or proven alpha.

