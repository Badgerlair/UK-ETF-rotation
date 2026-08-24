# UKACTIVE-A4D — final research report

Decision: **A4D_WEAK_OR_REGIME_DEPENDENT**  
Evidence: **E2 developmental; no independent historical confirmation**  
Data cutoff: **2026-08-21**  
Common causal portfolio-chain start: **2017-02-03**

## Executive finding

A4D preserved the accepted 27-family point-in-time `INDUSTRY_PLUS_THEME` universe, the A2R2 endpoint chain, the global-developed benchmark, actual GBP cash, next-session execution and the 20 bp plus £3.99 cost model. It did not modify A1–A5 or start prospective testing.

The staged experiment selected `M2_INTERMEDIATE_5H`, found a stable breadth plateau, and used `MONTHLY` as the region-level cadence. The defensive gate did not promote a cash overlay; always-invested remained the representative control. The final representative retained `W0_EQUAL`.

Final-five-year representative economics: net CAGR **13.62%**, excess versus global **2.10%**, excess versus the equal-weight opportunity pool **2.63%**, maximum drawdown **-22.34%**, Calmar **0.61**, Ulcer Index **10.13%**, and annual traded-notional turnover **6.93x**.

## Direct answers

1. **Multi-horizon rank versus prior A3:** M1 is the prior equal-five-horizon signal, not new evidence. M2 passed the frozen Stage-A gate and improved the same TOP7/monthly five-year pool excess from **0.08%** under M1 to **2.63%** under M2. M3's deterioration penalty did not add portfolio value. This is developmental comparison, not independent confirmation.
2. **Repeatable cross-sectional edge:** M2's full-history mean IC was positive at 21/42/63 sessions, but its mean top-quintile advantages were only **0.07% / −0.05% / 0.18%**. The representative's positive rolling-12m excess frequency was only **50.00%** versus the pool and **40.20%** versus global. That is not persistent enough for a strong claim.
3. **Breadth TOP3–TOP10:** TOP3–TOP5 generally diluted net selection economics; TOP6–TOP9 formed the M2 plateau; TOP10 lost pool excess. The table below is the five-year, after-cost frontier.

|   breadth | latest_5y_net_cagr   | latest_5y_net_excess_vs_equal_pool   | latest_5y_maximum_drawdown   |   latest_5y_calmar_mar | latest_5y_annual_turnover_traded_notional   |
|----------:|:---------------------|:-------------------------------------|:-----------------------------|-----------------------:|:--------------------------------------------|
|         3 | 7.42%                | -3.57%                               | -26.34%                      |                   0.28 | 11.33x                                      |
|         4 | 8.77%                | -2.22%                               | -27.88%                      |                   0.31 | 10.37x                                      |
|         5 | 11.83%               | 0.84%                                | -28.31%                      |                   0.42 | 8.66x                                       |
|         6 | 12.64%               | 1.65%                                | -24.11%                      |                   0.52 | 7.48x                                       |
|         7 | 13.62%               | 2.63%                                | -22.34%                      |                   0.61 | 6.93x                                       |
|         8 | 14.75%               | 3.76%                                | -20.10%                      |                   0.73 | 6.29x                                       |
|         9 | 12.46%               | 1.47%                                | -21.65%                      |                   0.58 | 6.21x                                       |
|        10 | 10.56%               | -0.43%                               | -19.86%                      |                   0.53 | 5.62x                                       |

4. **Plateau:** **Yes: TOP6–TOP9**
5. **Ranks creating excess:** ranks 4–5 contributed the most gross family market P&L, followed by ranks 6–10; the exact reconciled attribution is below.

| rank_bucket                                      |   gross_market_pnl_return_units | share_of_gross_family_market_pnl   |
|:-------------------------------------------------|--------------------------------:|:-----------------------------------|
| RANK_1                                           |                            0.48 | 19.98%                             |
| RANK_2_3                                         |                            0.41 | 17.24%                             |
| RANK_4_5                                         |                            0.9  | 37.28%                             |
| RANK_6_10                                        |                            0.64 | 26.50%                             |
| UNATTRIBUTED_HELD_OUTSIDE_CURRENT_SELECTED_RANKS |                           -0.02 | -1.00%                             |

6. **Diversification and drawdown:** the representative TOP7 reduced concentration versus TOP1, but five-year drawdown remained **-22.34%**. Marginal changes for every added holding are retained.
7. **Cadence:** weekly looked best before full cost stress, but doubled costs erased pool excess across all four breadths. Monthly retained positive doubled-cost pool excess in two of four breadths and therefore won the frozen region-level gate. Daily was dominated by noise and roughly **36.9x** median annual turnover.

| frequency   | median_latest5_pool_excess   | median_latest5_mdd   | median_turnover   | positive_double_cost_pool_gate_fraction   | passes_frequency_gate   |
|:------------|:-----------------------------|:---------------------|:------------------|:------------------------------------------|:------------------------|
| DAILY       | -1.02%                       | -21.75%              | 36.87x            | 0.00%                                     | False                   |
| WEEKLY      | 2.85%                        | -20.51%              | 14.97x            | 0.00%                                     | False                   |
| MONTHLY     | 2.14%                        | -21.99%              | 6.61x             | 50.00%                                    | True                    |

8. **Costs:** baseline and doubled-cost results are both retained. At TOP7/monthly the pool excess fell from **2.63%** to **0.96%** under doubled costs. No gross-only result is promoted.
9. **Cash:** **No tested cash architecture passed the complete preregistered promotion gate.** Individual asset qualification (`CASH_1_INDIVIDUAL_ABOVE_CASH_252`) was the best defensive research lead: at representative TOP7 it produced net CAGR **13.21%**, pool excess **2.22%** and MDD **-18.92%**, but its region-level drawdown improvement missed the fixed five-point gate.
10. **Defensive mechanism:** C1 preserved return best; C2 reduced drawdown more but its median doubled-cost pool excess turned negative; global confirmation and the combined rule sacrificed too much return. Always-invested therefore remains the representative, while C1 is a future preregistration lead—not a promoted A4D rule.

| cash_architecture                | median_latest5_net_cagr   | median_latest5_return_sacrifice_vs_always_invested   | median_latest5_drawdown_avoided   | median_latest5_pool_excess   | double_cost_pool_excess   |   median_latest5_calmar | median_latest5_ulcer   | median_average_cash_weight   | passes_cash_promotion_gate   |
|:---------------------------------|:--------------------------|:-----------------------------------------------------|:----------------------------------|:-----------------------------|:--------------------------|------------------------:|:-----------------------|:-----------------------------|:-----------------------------|
| CASH_0_ALWAYS_INVESTED           | 13.13%                    | 0.00%                                                | 0.00%                             | 2.14%                        | 0.45%                     |                    0.59 | 10.12%                 | 0.00%                        | False                        |
| CASH_1_INDIVIDUAL_ABOVE_CASH_252 | 13.12%                    | 0.01%                                                | 4.15%                             | 2.13%                        | 0.65%                     |                    0.74 | 8.30%                  | 16.04%                       | False                        |
| CASH_2_POOL_BREADTH              | 12.16%                    | 0.97%                                                | 5.77%                             | 1.17%                        | -0.20%                    |                    0.75 | 8.05%                  | 33.47%                       | False                        |
| CASH_3_GLOBAL_CONFIRMATION       | 10.10%                    | 3.03%                                                | -3.66%                            | -0.89%                       | -2.65%                    |                    0.39 | 12.29%                 | 25.00%                       | False                        |
| CASH_4_PARSIMONIOUS_COMBINED     | 9.12%                     | 4.01%                                                | 5.58%                             | -1.87%                       | -3.15%                    |                    0.58 | 9.44%                  | 46.20%                       | False                        |

11. **CAGR sacrificed per drawdown reduction:** C1's region median sacrificed about **0.01 percentage point** of CAGR for **4.15 points** of MDD improvement. C2 sacrificed about **0.97 point** for **5.77 points**. The full arithmetic is retained in `UKACTIVE_A4D_CASH_ECONOMIC_VALUE.csv`.
12. **Versus global:** final-five-year excess was **2.10%**.
13. **Versus equal pool:** final-five-year excess was **2.63%**.
14. **Winner dependence:** the top three family share of gross family market P&L was **44.57%**. Removing all three changed five-year pool excess to **-3.10%**, so the edge remains materially right-tail dependent even though removing any single contributor left positive excess.
15. **Subperiod/neighbour stability:** pre-2020 pool excess was **-3.57%**, post-2020 **4.06%**. Calendar-year pool excess was positive in only five of ten displayed years, and 2025 supplied a disproportionate gain. MATURE and MATURE+DEVELOPING sensitivities were positive, so launch cohorts do not explain the whole result. Pre-2017 breadth compounding is intentionally unavailable.
16. **Simplest architecture:** `M2_INTERMEDIATE_5H | TOP_7 | MONTHLY | CASH_0_ALWAYS_INVESTED | W0_EQUAL`.
17. **Prospective freeze:** **not authorised from A4D**. A reproducible developmental reference specification is written, but no untouched historical holdout exists and the weak/regime-dependent disposition does not justify opening a new validation lineage.

## Statistical uncertainty

No Stage-A IC, top-quintile or rank-1 effect survived the within-window/metric HAC–BH screen at q < 0.10. The paired six-month block-bootstrap 95% interval for five-year annualised excess was **−9.04% to 16.20%** versus global and **−5.61% to 12.73%** versus the equal pool; both include zero. Positive-excess bootstrap probabilities were **59.86%** and **73.80%**, respectively. This supports the weak/regime-dependent disposition rather than a strong claim.

## Calendar-year stability

|   calendar_year | partial_year   | net_return_or_cagr   | excess_vs_global   | excess_vs_pool   | maximum_drawdown   |
|----------------:|:---------------|:---------------------|:-------------------|:-----------------|:-------------------|
|            2017 | False          | 5.17%                | -1.21%             | -4.41%           | -4.23%             |
|            2018 | False          | -7.95%               | -4.80%             | 0.78%            | -13.91%            |
|            2019 | False          | 14.95%               | -7.21%             | -8.27%           | -6.83%             |
|            2020 | False          | 29.38%               | 18.30%             | 15.62%           | -23.53%            |
|            2021 | False          | 21.65%               | -2.30%             | -1.09%           | -7.94%             |
|            2022 | False          | -14.31%              | -5.74%             | -8.88%           | -18.69%            |
|            2023 | False          | 14.82%               | -2.58%             | 7.41%            | -11.99%            |
|            2024 | False          | 9.05%                | -12.22%            | -1.27%           | -11.74%            |
|            2025 | False          | 46.98%               | 35.31%             | 21.45%           | -16.72%            |
|            2026 | True           | 24.33%               | 5.00%              | 5.40%            | -13.61%            |

## Largest gross family contributors

| economic_exposure_family_id   |   gross_market_pnl_return_units | share_of_gross_family_market_pnl   |
|:------------------------------|--------------------------------:|:-----------------------------------|
| GLOBAL_BATTERY_EV             |                            0.38 | 15.82%                             |
| GLOBAL_SEMICONDUCTORS         |                            0.36 | 14.91%                             |
| GLOBAL_SILVER_MINERS          |                            0.33 | 13.84%                             |
| GLOBAL_GOLD_MINERS            |                            0.26 | 10.98%                             |
| EUROPE_BANKS                  |                            0.23 | 9.37%                              |
| GLOBAL_SOFTWARE               |                            0.15 | 6.04%                              |
| GLOBAL_OIL_GAS                |                            0.14 | 5.96%                              |
| GLOBAL_ROBOTICS_AUTOMATION    |                            0.13 | 5.41%                              |
| GLOBAL_TRANSPORTATION         |                            0.13 | 5.30%                              |
| GLOBAL_SOLAR                  |                            0.12 | 5.03%                              |

## Leadership deterioration and momentum age

The fixed state definitions and high-rank age buckets are diagnostics only. `MATURE_DECELERATING` did not underperform established leadership; in the latest five years its mean 42-session forward return was higher. Momentum age was not monotonic. Therefore no deterioration exit, age rule, fast exit or discretionary override was added.

## Data-lineage limitation

The last unreconstructed `GLOBAL_GOLD_MINERS` implementation gap makes broad-portfolio compounding before 2017-02-03 non-causal. A4D starts portfolio tests at the first endpoint of the final admitted segment. No price, return, liquidation proceeds or proxy was manufactured. Signal diagnostics can use earlier valid observations, but they are not represented as a continuous executable portfolio.

## RECOMMENDED ROBUST PORTFOLIO REGION

- Preferred signal family: `M2_INTERMEDIATE_5H`.
- Acceptable breadth range: `TOP6–TOP9`.
- Preferred rebalance frequency: `MONTHLY`.
- Acceptable neighbouring frequency: see the complete gate in `UKACTIVE_A4D_FREQUENCY_SUMMARY.csv`; no neighbour is implied if it failed.
- Cash/risk-state mechanism: `CASH_0_ALWAYS_INVESTED` for the representative; `CASH_1_INDIVIDUAL_ABOVE_CASH_252` is the best unpromoted defensive research lead.
- Weighting: `W0_EQUAL`.
- Expected historical CAGR range across the breadth region: **12.46% to 14.75%**.
- Excess CAGR versus equal pool: **1.47% to 3.76%**.
- Maximum drawdown range: **-24.11% to -20.10%**.
- Calmar range: **0.52 to 0.73**.
- Turnover range: **6.21x to 7.48x**.
- Principal failure modes: top-three removal turns excess negative; only 50% of rolling 12-month pool-excess windows are positive; pre-2020 weakness; cost-fragile weekly results; 2025 concentration; and incomplete historical implementation eligibility evidence.
- Remaining evidence gap: genuinely prospective data after a separately approved freeze.

## REPRESENTATIVE SPECIFICATION FOR FORWARD TESTING

`M2_INTERMEDIATE_5H | TOP_7 | MONTHLY | CASH_0_ALWAYS_INVESTED | W0_EQUAL`

This is the middle of the selected breadth region, uses the region-level cadence decision, and retains the simplest weight/cash choice that passed its gate. It is not the maximum-CAGR cell. It is stored only as a **developmental reference** in `config/UKACTIVE_A4D_REPRESENTATIVE_FORWARD_SPEC.json`; A4D does not authorise or start it and does not modify the existing A5 lineages.
