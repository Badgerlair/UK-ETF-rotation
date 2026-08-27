# Supplement to “Development and Freeze of a Point-in-Time Multi-Horizon ETF Rotation Strategy for a UK SIPP”

Version 1.0 — 2026-08-27  
Historical cutoff: 2026-08-21  
Source repository commit: `df30c9be430c4a746a6e3ec0d97690612badd4fa`  
Frozen model: `INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL`

This supplement carries detail that would obstruct the main paper's argument: the complete lineage index, table catalogue, full sensitivity frontiers, implementation map, monthly runbook, prospective schema, metric reconciliation and source-conflict record. It is evidence, not a menu for renewed optimisation. The historical model remains closed.

## S1. Reproducibility map

The output root contains three layers:

- `tables/`: 23 deterministic CSV extracts or derived diagnostics built only from canonical frozen inputs;
- `figures/`: 16 publication figures generated from those inputs; and
- `scripts/`: read-only source audit, deterministic asset generation, document rendering and reproducibility checks.

`UKACTIVE_PAPER_SOURCE_EVIDENCE_MATRIX.csv` is the claim-level index. Its hierarchy is final machine-readable decision/configuration, final scorecard, final report, handoff, earlier development and conversation summary. `qa/UKACTIVE_PAPER_CANONICAL_SOURCE_AUDIT.json` records source hashes and schemas. `UKACTIVE_PAPER_FIGURE_MANIFEST.csv` identifies each figure's sample, cost, cadence, configuration, net/gross status and canonical source. The final manifest records generated-file hashes and software versions.

The deterministic assets do not extend the cutoff. Derived diagnostics are labelled and cannot change disposition. Figure 11 is an exact rerun of the canonical vectorised A4F randomisation algorithm solely to recover distribution arrays; the script asserts every published candidate metric and percentile against the frozen CSV before saving the chart.

## S2. Complete lineage register

| Stage | Objective | New capability | Principal test | Decision | Consequence |
|---|---|---|---|---|---|
| A0/A1 | Specify problem and construct listing/share-class/family hierarchy | Audited universe, taxonomy, current-investability separation | No strategy test | `DATA_FOUNDATION_ONLY` | Build causal total-return histories |
| A2 | Construct GBP total-return, FX, cash, implementation and PIT panels | Routing, distributions, stale/missing controls | Readiness and data quality | `CONDITIONAL_READY` | Remediate identity/history defects |
| A3R0 | Audit A3 pools against economic identity | Detected 14 material mismatches | Semantic and automated lineage audit | `FAIL_BLOCKED` | Repair before signal interpretation |
| A2R | Repair family and implementation histories | 13 of 14 remediated; no proxy for remaining family | 27 automated and 17 semantic tests | `PASS_WITH_ONE_EXCLUSION` | Re-run readiness |
| A3R1 | Re-run signal construction | Exposed calendar/session defect | Timing and endpoint checks | `FAIL_BLOCKED` | Reconstruct XLON calendar |
| A2R2 | Repair false sessions and endpoint logic | Deterministic XLON calendar; prior-only tolerance | Synthetic, benchmark and affected-family audits | `PASS` | Repeat discovery causally |
| A3R1R1 | Repeat preregistered signal tests | 180 formal HAC/bootstrap/FDR cells | Cross-sectional prediction | `NO_FDR_SURVIVOR` | Permit bounded portfolio exploration |
| A3R2/U/S/W/Q | Explore pools, counts, cadence and weights | Dynamic census, role taxonomy, equal-weight control | 315 specifications | `EXPLORATORY_LEAD_ONLY` | Forensic TOP1 test |
| A4 | Test initial concentrated rotation | Executable portfolio, costs, randomisation, contribution | TOP1 3/6/12 | `RIGHT_TAIL_DEPENDENT` | Test breadth |
| A4B/A4C | Test lifecycle, exits, regime, entry and core/satellite | Failure-mode and drawdown decomposition | Exit/lock/sizing/50-50 modules | `NO_EXIT_OR_REGIME_PROMOTION` | Build parsimonious multi-horizon stage |
| A4D | Compare signal, breadth, frequency, cash and weighting | M1–M3; TOP3–10; three cadences; CASH0–4 | Staged economic/statistical gates | `SELECT_M2_TOP7_MONTHLY_CASH0_EQUAL` | Falsify defence and SIPP claims |
| A4E-SIPP | Test SIPP translation, exposure and cash timing | Matched exposure/risk, live costs, crisis limits | CASH1 and global/cash controls | `STATIC_75_25_CONTROL_ONLY` | Test causal regime policies |
| A4F-SIPP | Test causal regimes and dynamic allocation | Four regimes, policy grid, influence tests | HAC/bootstrap/cost/year/family/spell gates | `NO_DYNAMIC_POLICY_PASSED` | Choose limited static wrapper |
| A5C-SIPP | Freeze model and prospective operations | Immutable spec, cost restatement, ledger, runbook | 26/26 correctness; zero prospective events | `FROZEN_AWAITING_HOLDINGS_INPUT` | Observe prospectively |

Machine-readable source: `tables/TABLE_01_RESEARCH_LINEAGE.csv`; internal evidence IDs [LIN-A0-A1] through [LIN-A5C-SIPP].

## S3. Dataset, routes and point-in-time contracts

### S3.1 Funnel and coverage

The funnel is not a sequence of equally investable sets. The current discovery census contained 4,359 LSE lines and 2,821 distinct raw ISINs. Curation produced 296 share classes, 478 listings and 99 exposure families. A2 accepted at least one history for 90 families and classed 86 as then A3-ready. Coverage by trailing span was 89 one-year, 86 three-year, 77 five-year and 59 ten-year families. The final M2 universe is a role-restricted structural set of 27 families, of which 25 had all five M2 horizons at the cutoff.

A2 routed 367 histories plus four delisted routes, accepted 357 histories and constructed 667,700 panel observations. It invalidated 1,842 stale observations and left 62,667 in-life observations missing. These counts are provenance diagnostics and should not be added or divided as if each route were an independent economic family.

### S3.2 Calendar and endpoint rules

The causal calendar is a deterministic XLON session series. A vendor row on a non-session cannot create a lookback observation or execution day. A2R2 removed 29 such false sessions. Endpoint resolution accepts only the exact session or the latest value within three preceding true sessions, never a subsequent value. A gap over three true sessions resets the segment. Exchange holidays do not count as missing sessions.

At any review date, every M2 horizon must have both family and benchmark endpoints. Eligibility therefore changes as funds launch or histories fail. The percentile denominator is the number of complete eligible families at that date. No current fund is assumed to have existed earlier; no unavailable family receives a proxy. The preferred implementation ticker is downstream of the family rank.

### S3.3 Return, currency and cash rules

Adjusted close is the accepted total-return representation after validation. Dividends are not added again. GBP and GBX are distinct units: GBX is divided by 100 before return construction. Foreign-currency histories are translated once through the accepted ECB series. A GBP line can still be economically unhedged. The historical cash proxy is time-varying SONIA on the documented ACT/365 convention, not broker cash, CSH2, RLON or a constant yield.

Detailed machine-readable assumptions are in `tables/TABLE_03_ASSUMPTIONS.csv`; source facts are in evidence IDs [DATA-A2-PANEL], [DATA-A2-MISSING], [DATA-A2R-BLOCK], [DATA-A2R2-CALENDAR], [DATA-A2R2-ENDPOINT], [DATA-A2R2-ELIG] and [CASH-SONIA].

## S4. Signal and portfolio algorithm

For horizon (h), raw relative strength is

\[
RS^{raw}_{i,t,h}=\frac{1+R_{i,t,h}}{1+R_{B,t,h}}-1.
\]

The code applies `rank(method="average", pct=True)` cross-sectionally among eligible rows. M2 is

\[
0.10RS21+0.15RS42+0.25RS63+0.30RS126+0.20RS252.
\]

All components are percentiles on the same date. Missing one component means missing the composite. Exact composite ties sort by canonical family ID ascending after descending score. The first seven families receive equal sleeve weights. If only three to six families are eligible, all are selected and equally weighted. Fewer than three suspends the decision.

The monthly signal uses the final valid XLON month-end close and executes on the first following session within three valid sessions. It never assumes a same-close fill. The operating path maps each selected family to a frozen preferred GBP/GBX line. A line failure maps that slot to CSH2 rather than to the eighth-ranked family.

## S5. Full staged sensitivity results

### S5.1 Signal family

| Signal | IC-positive horizons | Top-quintile-positive horizons | Gate | Full net CAGR | Full pool difference | Full MDD | Latest-5y CAGR | Turnover |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| M1 equal five-horizon | 3 | 0 | Fail | 12.5231% | 0.9912 pp | −24.9518% | 11.0693% | 6.4298× |
| M2 intermediate | 3 | 2 | Pass | 13.1376% | 1.6057 pp | −23.5308% | 13.6202% | 5.5231× |
| M3 deterioration | 3 | 2 | Pass | 11.7695% | 0.2375 pp | −23.5311% | 11.3363% | 5.9593× |

Source: `tables/TABLE_04_SIGNAL_COMPARISON.csv`, baseline costs, full sample 2017-03-01–2026-08-21 and latest-five-year sample 2021-09-01–2026-08-21.

### S5.2 Breadth

| Breadth | Full net CAGR | Full pool diff | Full MDD | Full turnover | Latest-5y CAGR | Latest-5y pool diff | Latest-5y MDD | Latest-5y turnover |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3 | 10.4029% | −1.1291 pp | −28.0308% | 9.7979× | 7.4187% | −3.5713 pp | −26.3377% | 11.3318× |
| 4 | 11.5884% | 0.0564 pp | −27.8794% | 9.3474× | 8.7720% | −2.2180 pp | −27.8794% | 10.3745× |
| 5 | 13.2341% | 1.7021 pp | −28.3065% | 7.4567× | 11.8317% | 0.8418 pp | −28.3065% | 8.6624× |
| 6 | 13.4999% | 1.9679 pp | −24.3553% | 6.2456× | 12.6390% | 1.6490 pp | −24.1098% | 7.4847× |
| 7 | 13.1376% | 1.6057 pp | −23.5308% | 5.5231× | 13.6202% | 2.6302 pp | −22.3356% | 6.9259× |
| 8 | 13.1459% | 1.6139 pp | −23.5366% | 4.8476× | 14.7464% | 3.7564 pp | −20.1045% | 6.2913× |
| 9 | 11.5023% | −0.0297 pp | −25.1444% | 4.6093× | 12.4588% | 1.4688 pp | −21.6525% | 6.2093× |
| 10 | 10.2193% | −1.3127 pp | −24.7146% | 4.0979× | 10.5649% | −0.4251 pp | −19.8553% | 5.6215× |

Source: `tables/TABLE_05_BREADTH_FRONTIER.csv`. TOP7 is a representative region point; this table is not a permission to switch to TOP8.

### S5.3 Frequency and cost stress

| Cadence | Gross CAGR | Baseline net | Baseline pool diff | Double-cost net | Double-cost pool diff | MDD | Ulcer | Turnover | Drag | Holding days | Replacement | Legs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Daily | 18.0405% | 9.6388% | −2.7677 pp | 0.9092% | −11.4973 pp | −28.0959% | 9.0027% | 31.856× | 8.4017 pp | 23.85 | 15.15% | 7,699 |
| Weekly | 16.7581% | 13.3927% | 1.1045 pp | 10.0323% | −2.2559 pp | −25.9813% | 6.9798% | 13.175× | 3.3654 pp | 57.54 | 17.48% | 2,800 |
| Monthly | 14.4806% | 13.1376% | 1.6057 pp | 11.7987% | 0.2667 pp | −23.5308% | 8.1980% | 5.5231× | 1.3430 pp | 134.38 | 25.22% | 865 |

Source: `tables/TABLE_06_FREQUENCY_COMPARISON.csv`, common full window.

### S5.4 Cash architecture

| Rule | Full CAGR | Full pool diff | MDD | Ulcer | Calmar | Cash | Latest-5y CAGR | Latest-5y pool diff | Latest-5y MDD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CASH0 always invested | 13.1376% | 1.6057 pp | −23.5308% | 8.1980% | 0.5583 | 0.0000% | 13.6202% | 2.6302 pp | −22.3356% |
| CASH1 family above cash 252 | 9.5290% | −2.0029 pp | −27.1574% | 8.3155% | 0.3509 | 17.5445% | 13.2122% | 2.2223 pp | −18.9196% |
| CASH2 breadth defence | 6.9649% | −4.5670 pp | −32.1775% | 11.1062% | 0.2165 | 28.6300% | See CSV | See CSV | See CSV |
| CASH3 global confirmation | 8.3479% | −3.1841 pp | −25.5111% | 10.8918% | 0.3272 | 27.4300% | See CSV | See CSV | See CSV |
| CASH4 combined defence | 5.7927% | −5.7393 pp | −21.5600% | 10.1349% | 0.2687 | 46.3000% | See CSV | See CSV | See CSV |

Source: `tables/TABLE_07_CASH_ARCHITECTURES.csv`. The canonical CSV contains every baseline/doubled-cost and window row; no variant is promoted.

### S5.5 Weighting

| Weighting | Full net CAGR | Pool diff | MDD | Turnover | Disposition |
|---|---:|---:|---:|---:|---|
| Equal | 13.1376% | 1.6057 pp | −23.5308% | 5.5231× | Retained |
| Rank decay | 12.3987% | 0.8667 pp | −25.9472% | 8.1390× | Rejected |
| Fixed top-heavy | 12.0192% | 0.4872 pp | −25.2493% | 7.5650× | Rejected |

Source: `tables/TABLE_08_WEIGHTING_COMPARISON.csv`.

## S6. Economic and path results

The complete common-window profile is in `tables/TABLE_09_COMMON_WINDOW_ECONOMICS.csv`. It includes SWDA, 75/25, M2, 50/50, 50/25/25, 75/25 M2/cash, 50/50 M2/cash and the equal pool with CAGR, terminal wealth, MDD, Calmar, Ulcer, volatility, underwater duration, turnover and drag. Direct comparisons must use 2017-03-01–2026-08-21.

`tables/TABLE_10_CALENDAR_RETURNS.csv` carries every full and partial calendar year. The annual rows do not support a performance stop. `tables/TABLE_23_RELATIVE_REGRET_SUMMARY.csv` records maximum relative drawdown and longest relative-underperformance duration for the standalone strategy and three wrappers.

### S6.1 Estimand reconciliation

| Label | Window / frequency | Canonical value vs equal pool | Definition |
|---|---|---:|---|
| Full-history CAGR difference | 2017-03-01–2026-08-21, daily wealth | 1.6057 pp | M2 net CAGR minus pool CAGR |
| Full-history arithmetic annualised excess | Same window, daily return differences | 4.3864% | 252 × mean daily M2-minus-pool return |
| Bootstrap observed excess | 2021-09-01–2026-08-21, monthly | 2.9385% | 12 × mean monthly M2-minus-pool return |

The values differ because the estimand, compounding and sample differ. The canonical row-level reproduction ledger is `UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_METRIC_RECONCILIATION.csv`; it is not copied into the paper output because it contains hundreds of exact A4D-to-A4E cell checks, all retained unchanged in the source lineage.

### S6.2 Longer-core quarantine

The A4F narrative states a longer core-only context from 2010-01-08 to 2026-08-21. The final `UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv` covers only 2010-03-01 to 2010-03-09 and produces meaningless annualisation. Status: `UNRESOLVED_SOURCE_CONFLICT`. Resolution applied here: no return, drawdown or wealth from that file appears in the main comparison. The conflict is recorded in evidence row [LONG-CORE-CONFLICT] and the QA report.

## S7. Regimes and policies

### S7.1 Four regimes

| Regime | Months | Episodes | Average months | M2 return | Volatility | Worst month | Episode MDD | M2−SWDA | M2−pool | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R1 broad risk-on | 7 | 6 | 1.17 | 13.08% | 12.33% | −1.97% | −1.44% | 3.82% | 0.52% | Insufficient |
| R2 leadership risk-on | 86 | 11 | 7.82 | 9.77% | 13.71% | −8.72% | −9.77% | 1.80% | 0.18% | Sufficient descriptively |
| R3 isolated leadership | 16 | 8 | 2.00 | 10.24% | 21.13% | −11.98% | −10.02% | −1.63% | −0.34% | Insufficient |
| R4 capital preservation | 5 | 5 | 1.00 | 105.18% annualised | 17.27% | 0.80% | 0.00% | 5.01% | 0.27% | Insufficient |

The R4 annualised number demonstrates why very short regime samples must not be interpreted literally. Source: `tables/TABLE_11_REGIME_SUMMARY.csv`.

### S7.2 Dynamic policy grid

| Policy | Switch | CAGR | MDD | Ulcer | Turnover | Global | M2 | Cash | Retention | Eligible | Gates |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| P0 static | Immediate | 9.2632% | −19.5516% | 3.5993% | 0.1413× | 75.00% | 0.00% | 25.00% | 79.85% | Yes | Fail as dynamic candidate |
| P0 static | Hysteresis | 9.2632% | −19.5516% | 3.5993% | 0.1413× | 75.00% | 0.00% | 25.00% | 79.85% | Yes | Fail as dynamic candidate |
| P1 risk | Immediate | 7.8925% | −17.5290% | 5.8946% | 1.0429× | 85.22% | 0.00% | 14.78% | 68.03% | Yes | Fail |
| P1 risk | Hysteresis | 7.3277% | −17.5290% | 5.8245% | 1.0083× | 81.96% | 0.00% | 18.04% | 63.16% | Yes | Fail |
| P2 alpha | Immediate | 11.6594% | −24.5033% | 5.2790% | 2.2818× | 77.61% | 22.39% | 0.00% | 100.50% | Yes | Fail |
| P2 alpha | Hysteresis | 11.7113% | −24.5033% | 5.1881% | 1.8846× | 79.78% | 20.22% | 0.00% | 100.95% | Yes | Fail |
| P3 balanced | Immediate | 8.0310% | −16.8767% | 6.1673% | 2.5164× | 65.54% | 19.67% | 14.78% | 69.23% | Yes | Fail |
| P3 balanced | Hysteresis | 7.3925% | −16.8770% | 6.0529% | 2.2601× | 64.35% | 17.61% | 18.04% | 63.72% | Yes | Fail |
| P4 defensive | Immediate | 6.7511% | −14.7584% | 6.8339% | 2.7384× | 61.53% | 18.77% | 19.70% | 58.19% | Yes | Fail |
| P4 defensive | Hysteresis | 5.9120% | −17.2912% | 7.5047% | 2.4757× | 59.21% | 16.74% | 24.05% | 50.96% | Yes | Fail |
| P5 diagnostic | Immediate | 8.2620% | −16.3167% | 6.7752% | 4.0121× | 45.87% | 39.35% | 14.78% | 71.22% | No | Fail |
| P5 diagnostic | Hysteresis | 7.5417% | −17.2291% | 6.8275% | 3.5038× | 46.74% | 35.22% | 18.04% | 65.01% | No | Fail |

Source: `tables/TABLE_12_DYNAMIC_POLICIES.csv`, common window, baseline costs. No row passed all mandatory gates.

## S8. Falsification, contribution and uncertainty

### S8.1 Randomisation

Both controls used 10,000 paths and the exact contemporaneous eligible count. The matched random-selection candidate had diagnostic net CAGR 12.59968%, MDD −19.27967% and turnover 5.52993×. Its CAGR percentile was 99.36 and drawdown percentile 98.47. Rank shuffling produced 99.48 and 98.30. The diagnostic ends with its last executable rebalance on 2026-08-03 and differs from the primary wealth-engine CAGR by construction. Source: `tables/TABLE_13_RANDOMISATION.csv` and Figure 11.

### S8.2 Family contribution

| Rank | Family | Share of gross family P&L |
|---:|---|---:|
| 1 | Global battery/EV | 15.8207% |
| 2 | Global semiconductors | 14.9096% |
| 3 | Global silver miners | 13.8389% |
| 4 | Global gold miners | 10.9787% |
| 5 | Europe banks | 9.3730% |
| 6 | Global software | 6.0450% |
| 7 | Global oil & gas | 5.9650% |
| 8 | Global robotics & automation | 5.4100% |
| 9 | Global transportation | 5.2900% |
| 10 | Global solar | 5.0300% |

The exact full family ledger is `tables/TABLE_14_FAMILY_CONTRIBUTION.csv`. Top-three share is 44.5692%; top-five share is 64.9208%. The rank-bucket ledger is `tables/TABLE_15_RANK_CONTRIBUTION.csv`: rank 1, 19.9799%; ranks 2–3, 17.2359%; ranks 4–5, 37.2843%; ranks 6–10, 26.4981%; other/unattributed, −0.9981%.

### S8.3 Largest holding spells

| Spell | Family | Entry | Exit | Held return | Normalised arithmetic contribution |
|---|---|---|---|---:|---:|
| 0001 | Global silver miners | 2025-03-03 | 2026-05-01 | 146.30% | 14.9717% |
| 0002 | Global battery/EV | 2019-11-01 | 2021-09-01 | 109.44% | 11.6003% |
| 0003 | Global semiconductors | 2023-02-01 | 2024-09-02 | 78.42% | 9.2755% |
| 0004 | Global battery/EV | 2025-08-01 | 2026-07-01 | See ledger | 9.0703% |
| 0005 | Global oil & gas | 2021-10-01 | 2023-02-01 | See ledger | 7.6854% |
| 0006 | Europe banks | 2025-02-03 | 2025-10-01 | See ledger | 7.0841% |

`tables/TABLE_16_HOLDING_SPELL_LEDGER.csv` contains the full ranked positive-spell extract used in Figure 12. It is ex-post attribution, not a holding forecast or exit instruction.

### S8.4 Influence

| Evidence type | Exclusion | Net CAGR | Incremental versus control | Assessment |
|---|---|---:|---:|---|
| Family leave-one-out | Minimum across individual families | See CSV | 0.0913 pp | Weakens, no reversal |
| Family set | Top one | See CSV | 0.2533 pp | Weakens |
| Family set | Top three | See CSV | −4.3665 pp | Reverses |
| Family set | Top five | See CSV | −5.0682 pp | Reverses |
| Holding spell | Delete top one | 11.5973% | −0.0038 pp | Removes advantage |
| Holding spells | Delete top three | 9.4690% | −2.1321 pp | Reverses |
| Holding spells | Delete top five | 7.7655% | −3.8356 pp | Reverses |

Sources: `tables/TABLE_17_HOLDING_SPELL_INFLUENCE.csv` and `tables/TABLE_18_INFLUENCE_SUMMARY.csv`. The counterfactuals delete known winners ex post and therefore measure influence, not implementability.

### S8.5 Bootstrap and multiplicity

| Comparator | Monthly observations | Block | Paths | Observed arithmetic annualised excess | 95% interval | P(excess > 0) |
|---|---:|---:|---:|---:|---:|---:|
| SWDA/global | 59 | Circular 6 months | 5,000 | 1.8766% | −9.0367% to 16.2033% | 59.86% |
| Equal pool | 59 | Circular 6 months | 5,000 | 2.9385% | −5.6088% to 12.7338% | 73.80% |

Source: `tables/TABLE_19_STATISTICAL_UNCERTAINTY.csv`. A3R1R1 and A3R2 multiple-testing ledgers recorded zero BH-q survivors at 0.10. No SPA test was completed.

## S9. Time and cost robustness

| Diagnostic | Net CAGR | Incremental vs SWDA | MDD | Cost | Disposition |
|---|---:|---:|---:|---|---|
| Full | 13.1376% | 1.5365 pp | −23.5308% | Base | Preserves |
| Pre-2020 | 3.7575% | −4.3179 pp | −13.9078% | Base | Reverses |
| Post-2020 | 17.2533% | 4.2857 pp | −23.5308% | Base | Preserves |
| Latest five years | 13.6202% | 2.1037 pp | −22.3356% | Base | Preserves |
| Latest three years | 29.5119% | 10.8296 pp | −16.7189% | Base | Preserves, concentrated |
| Excluding 2025 | 10.4240% | −1.0281 pp | −23.5308% | Base | Reverses |
| Excluding 2020 | 12.1094% | 0.6056 pp | −22.3356% | Base | Preserves narrowly |
| Excluding 2020 and 2025 | 7.5841% | −3.7752 pp | −22.3356% | Base | Reverses |
| Full doubled costs | 11.7987% | 0.1976 pp | −23.7318% | Double | Materially weakens |

The complete machine-readable table is `tables/TABLE_20_ROBUSTNESS.csv`. Leave-one-year-out rows remain in the canonical A4F source and are summarised in the paper evidence matrix. Exclusion CAGRs are non-contiguous diagnostics: they remove calendar blocks and compound the remaining returns; they are not returns on a feasible continuous live path.

## S10. Whole-SIPP cost restatement

### S10.1 £563,000 Plus plan

| Window | Allocation | Gross CAGR | Net, subscription separate | Net, subscription included | Increment vs control | MDD | Ulcer | Turnover | Legs | Historical dealing | Historical market friction | Current annual market friction | Current annual all-in |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Full | 75/0/25 control | 9.2920% | 9.2784% | 9.2530% | 0 | −19.5505% | 3.5964% | 0.1413× | 114 | £0.00 | £1,779.66 | £159.05 | £338.93 |
| Full | 65/10/25 pilot | 9.6114% | 9.4225% | 9.3969% | 0.1441 pp | −19.1060% | 3.5785% | 0.6838× | 1,076 | £3,842.37 | £10,855.35 | £769.97 | £1,355.46 |
| Full | 60/15/25 comparator | 9.7701% | 9.5210% | 9.4954% | 0.2426 pp | −18.8814% | 3.6492% | 0.9569× | 1,076 | £3,842.37 | £15,423.64 | £1,077.44 | £1,662.92 |
| Full | 50/25/25 comparator | 10.0810% | 9.7112% | 9.6855% | 0.4328 pp | −18.4318% | 3.8609% | 1.5025× | 1,076 | £3,842.37 | £24,537.57 | £1,691.80 | £2,277.29 |
| Latest 5y | 75/0/25 control | 9.5824% | 9.5700% | 9.5497% | 0 | −13.8986% | 3.3522% | 0.0576× | 60 | £0.00 | £553.34 | £64.84 | £244.72 |
| Latest 5y | 65/10/25 pilot | 10.0133% | 9.8007% | 9.7801% | 0.2307 pp | −13.5135% | 3.5113% | 0.7520× | 597 | £2,142.63 | £7,401.07 | £846.76 | £1,457.81 |
| Latest 5y | 60/15/25 comparator | 10.2247% | 9.9355% | 9.9149% | 0.3655 pp | −13.3829% | 3.6798% | 1.1010× | 597 | £2,142.63 | £10,847.68 | £1,239.69 | £1,850.75 |
| Latest 5y | 50/25/25 comparator | 10.6385% | 10.1957% | 10.1750% | 0.6257 pp | −13.1464% | 4.1089% | 1.7982× | 597 | £2,142.63 | £17,729.02 | £2,024.76 | £2,635.82 |

`tables/TABLE_21_WHOLE_SIPP_COMPARISON.csv` also contains £250,000 restatements and standalone/global diagnostics. The subscription total was £1,708.86 on full history and £899.40 on the latest five years. It is reported separately because the plan serves the whole SIPP.

### S10.2 Plan rules

- II Plus: £3.99 per paid ETF leg, one free monthly credit, £14.99 monthly subscription.
- II Premium: £2.99 per paid ETF leg, two free monthly credits, £39.99 monthly subscription.
- Preferred GBP/GBX lines: no broker FX conversion fee.
- Historical market-price friction: 20 bps one-way; 40 bps stress.
- ETF TER: not deducted again.
- Manual unarchived spread review: not formal evidence.

## S11. Complete implementation roles

The exact 31-row current map is `tables/TABLE_22_LIVE_IMPLEMENTATION_MAP.csv`. In addition to the 27 M2 family rows and SWDA core row shown in the main paper, it contains:

| Role | Instrument / identity | Status | Automatic alternate | Historical back-projection |
|---|---|---|---|---|
| Broker cash | Interactive Investor SIPP GBP cash | Minimal operational balance only | No USD/EUR line | Prohibited |
| Strategic defence | RLON user label; exact share class unresolved | `AWAITING_CURRENT_HOLDINGS_INPUT` | None | Prohibited |
| Tactical liquidity | CSH2, Amundi Smart Overnight Return GBP Hedged, `LU1230136894` | Permitted prospectively pending SIPP confirmation | None | Prohibited |
| Global core | SWDA, `IE00B4L5Y983`, unhedged | Confirmed current | IWDA recorded; no USD line | Prohibited |

Every M2 map row distinguishes preferred ticker, ISIN, trading currency, hedge status, alternate ticker/ISIN/currency, signal readiness, current account status and automatic-alternate permission. A blank hedging field is not interpreted as hedged. An alternate in the table is a controlled candidate, not automatic authority.

## S12. Monthly operating runbook

### S12.1 Before month-end

1. Confirm frozen code/configuration hashes and append-only ledger integrity.
2. Confirm the authoritative 27-family structural universe.
3. Do not force the two warm-up families into the signal.
4. Confirm preferred and permitted alternate GBP/GBX lines in the current SIPP.
5. Reconcile existing active/thematic holdings and test the 25% cap.
6. Confirm the current Interactive Investor plan, credits and dealing schedule.
7. Confirm exact RLON share class and CSH2 permission.

### S12.2 Official signal run

1. Wait until the final valid XLON month-end close is fully ingested.
2. Validate prices, total returns, GBP cash, XLON calendar, universe and hashes.
3. Calculate raw benchmark-relative returns over 21/42/63/126/252 sessions.
4. Form eligible cross-sectional percentiles with average ties.
5. Compute M2 weights 10/15/25/30/20.
6. Sort by M2 descending and family ID ascending.
7. Select TOP7 and assign (1/7) of the sleeve to each.
8. Resolve current preferred or permitted alternate line.
9. Put an unavailable slot in CSH2; do not promote rank eight.
10. Append the immutable decision before the execution close is known.
11. Record regime fields as telemetry only.

### S12.3 Manual execution pack

1. Identify the first following valid XLON session, no later than the third.
2. Reconcile actual holdings and calculate 65/10/25 targets.
3. At £563,000, reference targets are £365,950 SWDA, £56,300 M2 and £140,750 defensive; each M2 slot is £8,042.86 before drift and rounding.
4. Build a review-only trade list. No A5C code may transmit an order.
5. Use 20 bps expected one-way friction and current plan fee/credits.
6. If quoted one-way friction exceeds 40 bps, suspend the change and use CSH2.
7. Obtain explicit approval.
8. Execute manually; record actual fill, time, fee and shortfall.
9. Reconcile post-trade holdings and residual cash.

### S12.4 Suspension table

| Condition | Required action | Forbidden response |
|---|---|---|
| Data/hash/calendar/universe failure | No decision; retain affected capital in CSH2 | Backfill or improvise source data |
| Rank reproducibility failure | Suspend the M2 sleeve to CSH2 | Choose the “most plausible” rank |
| Preferred and permitted alternate unavailable | Put that slot in CSH2 | Promote another family |
| Execution unavailable within three sessions | Do not chase; use CSH2 | Shift silently to a later favourable price |
| Quoted/actual one-way friction >40 bps | Suspend the change and review | Change historical 20 bps model |
| Material historical defect | Stop and open new governed research lineage | Patch live model without review |
| Short-term underperformance | Continue frozen process and record evidence | Performance-only stop or intra-month exit |

## S13. Prospective ledger and evidence review

The frozen prospective ledger has zero data rows. A valid new row must be generated after freeze and cannot describe a historical month. Recommended fields are:

- run ID, review date, execution date and timestamp;
- code, configuration, data and calendar hashes;
- eligible families and denominator;
- five raw relative returns, five percentiles and M2 score for every structural family;
- rank, TOP7 selection and tie-break result;
- preferred/alternate/CSH2 mapping and availability proof;
- prior and target weights, trade legs and approval;
- planned price, actual fill, dealing charge, quoted spread, realised implementation shortfall and estimated one-way friction;
- actual whole-SIPP active/thematic exposure;
- regime telemetry, random/matched controls and equal-pool outcome;
- suspension or exception reason;
- immutable append timestamp.

Review for a possible increase to 15% or 25% requires diverse prospective episodes, stable ranks and operations, cost within bounds, ranking advantage relative to controls and an acceptable whole-SIPP budget. There is no automatic 24–36 month wait and no automatic escalation from profitability. Any change requires explicit approval and a new governed decision record. Advancement beyond E2 requires prospective evidence; correctness checks alone are insufficient.

## S14. Table and figure catalogue

| Output | Contents |
|---|---|
| `TABLE_01_RESEARCH_LINEAGE.csv` | 14-stage chronology and consequences |
| `TABLE_02_UNIVERSE_FUNNEL.csv` | Listing-to-family-to-ready funnel |
| `TABLE_03_ASSUMPTIONS.csv` | Assumption, bias, mitigation and limitation |
| `TABLE_04_SIGNAL_COMPARISON.csv` | M1/M2/M3 gate and economics |
| `TABLE_05_BREADTH_FRONTIER.csv` | TOP3–TOP10 full/latest-five-year frontier |
| `TABLE_06_FREQUENCY_COMPARISON.csv` | Daily/weekly/monthly base and cost stress |
| `TABLE_07_CASH_ARCHITECTURES.csv` | CASH0–CASH4 across windows/costs |
| `TABLE_08_WEIGHTING_COMPARISON.csv` | Equal/rank-decay/top-heavy results |
| `TABLE_09_COMMON_WINDOW_ECONOMICS.csv` | Static and active path profiles |
| `TABLE_10_CALENDAR_RETURNS.csv` | Full calendar table including partial years |
| `TABLE_11_REGIME_SUMMARY.csv` | R1–R4 months, episodes and returns |
| `TABLE_12_DYNAMIC_POLICIES.csv` | P0–P5 immediate/hysteresis results |
| `TABLE_13_RANDOMISATION.csv` | 10,000-path control summaries |
| `TABLE_14_FAMILY_CONTRIBUTION.csv` | Family P&L shares |
| `TABLE_15_RANK_CONTRIBUTION.csv` | Rank-bucket P&L shares |
| `TABLE_16_HOLDING_SPELL_LEDGER.csv` | Ranked holding spells |
| `TABLE_17_HOLDING_SPELL_INFLUENCE.csv` | Spell-deletion counterfactuals |
| `TABLE_18_INFLUENCE_SUMMARY.csv` | Family/spell concentration summary |
| `TABLE_19_STATISTICAL_UNCERTAINTY.csv` | Bootstrap intervals/probabilities |
| `TABLE_20_ROBUSTNESS.csv` | Time, year and cost robustness |
| `TABLE_21_WHOLE_SIPP_COMPARISON.csv` | 0/10/15/25/100% and notional restatements |
| `TABLE_22_LIVE_IMPLEMENTATION_MAP.csv` | All live roles and controls |
| `TABLE_23_RELATIVE_REGRET_SUMMARY.csv` | Relative drawdown/duration summaries |

The 16 figures and their complete metadata are enumerated in `UKACTIVE_PAPER_FIGURE_MANIFEST.csv`. All are PNG publication assets at deterministic dimensions and resolution.

## S15. Acceptance-question crosswalk

| Reader question | Main paper section |
|---|---|
| What exactly is the strategy? | 8, 9, 26 |
| What data were used? | 4, 5 |
| How was causality preserved? | 5, 6 |
| Which assumptions were necessary? | 5, Table 3 |
| What was tested and failed? | 11–17, 20, 24 |
| What worked and why M2? | 13–15, 21, 25 |
| Why TOP7 rather than TOP8? | 14 |
| Why monthly and always invested? | 15, 16 |
| Why is the SIPP defensive? | 1, 16, 27, 29 |
| How winner-dependent is it? | 22, 24 |
| How uncertain is the edge? | 23, 24, 34 |
| Exact statistics and costs? | 18, 27, 10 |
| How is it operated and suspended? | 30, 32; Supplement S12 |
| What remains required? | 33–35 |

## S16. Final evidence status

Scientific classification: `E2_DEVELOPMENTAL`  
Model: `FROZEN`  
Historical development: `CLOSED`  
Operational readiness: `AWAITING_CURRENT_HOLDINGS_INPUT`; `pilot_operationally_ready=false`  
Prospective records at freeze: zero  
Permitted use: controlled 10% pilot after readiness and explicit approval  
Unresolved source conflict: A4F longer-core-only CSV window and metrics; quarantined  
Prohibited: model optimisation, post-cutoff historical selection, broker-order creation, performance-only stop, unrestricted whole-SIPP interpretation.

