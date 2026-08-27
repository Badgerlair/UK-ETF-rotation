# UKACTIVE scientific-paper quality assurance

## QA disposition

| Field | Result |
|---|---|
| QA date | 2026-08-27 |
| Historical evidence cutoff | 2026-08-21 |
| Source manifest commit | `df30c9be430c4a746a6e3ec0d97690612badd4fa` |
| Frozen model | `INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL` |
| Overall result | **PASS_WITH_DISCLOSED_SOURCE_CONFLICT** |
| Scientific classification | `E2_DEVELOPMENTAL` |
| Model status | `FROZEN` |
| Historical model development | `CLOSED / M2_HISTORICAL_MODEL_DEVELOPMENT_CLOSED` |
| Live implementation status | `AWAITING_CURRENT_HOLDINGS_INPUT`; `pilot_operationally_ready=false` |

The disclosed conflict concerns only an A4F longer-core-only file and does not affect the common 2017-03-01–2026-08-21 executable-window results. The final machine-readable file contains 2010-03-01–2010-03-09, while the A4F narrative and reproduction audit describe 2010-01-08–2026-08-21. It is recorded as `LONG-CORE-CONFLICT` with status `UNRESOLVED_SOURCE_CONFLICT` in the evidence matrix. No longer-window performance statistic from that file is used in the paper.

## Required scientific checks

| # | Requirement | Result | Evidence / note |
|---:|---|---|---|
| 1 | Every material number has an authoritative source | PASS | The evidence matrix contains 182 unique claim records. Numerical main-paper claims cite a claim identifier and the exact canonical artefact, stage, field or row, and commit. |
| 2 | Full-history comparisons use compatible windows | PASS | Direct comparisons use the common executable window, 2017-03-01–2026-08-21. The unusable longer-core file is quarantined and not compared with rotation results. |
| 3 | Every result table identifies cost treatment | PASS | Main tables and captions state baseline or doubled costs, frequency, sample, benchmark and subscription treatment where applicable. Non-performance tables are explicitly definitional. |
| 4 | Negative strategy results are represented | PASS | A3 weakness, TOP3–TOP4 concentration, daily/weekly cost fragility, CASH1 full-history failure, CASH2–CASH4 failures, weighting/deterioration failures, regime-policy failures and influence reversals are all reported. |
| 5 | CASH1 is not described as successful | PASS | Section 16 reports the favourable recent result and the adverse full-history and matched-exposure results; disposition is rejected. |
| 6 | Dynamic regime policies are not described as promoted | PASS | Section 20 reports every policy as rejected or not promoted. Regime variables are telemetry only. |
| 7 | The 50/50 blend is not described as a live recommendation | PASS | It is consistently labelled a research comparator. |
| 8 | The 10% pilot is not described as proof of alpha | PASS | It is a risk-budgeted prospective wrapper conditional on operational readiness and approval. |
| 9 | Current ETF availability is not back-projected | PASS | Sections 4, 5 and 28 distinguish point-in-time research eligibility from current implementation availability. |
| 10 | Cash is not assumed to earn 4% permanently | PASS | Sections 7 and 29 describe the accepted time-varying GBP cash series and rate-dependent RLON/CSH2 returns. |
| 11 | GBP/GBX trading lines are not described as currency hedged | PASS | Sections 10 and 28 explicitly retain unhedged underlying foreign-currency exposure. |
| 12 | No broker FX fee is deducted from preferred GBP/GBX trades | PASS | The cost contract deducts no broker foreign-exchange transaction fee from preferred GBP/GBX execution lines. |
| 13 | Underlying currency exposure remains acknowledged | PASS | The paper distinguishes trading currency from economic currency exposure. |
| 14 | Active strategy, pilot wrapper and capital-continuity control are not conflated | PASS | Section 1 defines the three objects; Sections 18, 25, 27 and 30 preserve the distinction in results and intended use. |
| 15 | No post-cutoff evidence changes selection | PASS | All strategy conclusions use data through 2026-08-21. The prospective ledger remains empty at freeze and is discussed separately. |
| 16 | No new model optimisation was performed | PASS | New work is limited to exact reproduction, reconciliation, deterministic presentation and already-specified diagnostics. Asset-build QA records `new_model_search=false`. |

## Evidence, tabular and render checks

| Check | Result | Detail |
|---|---|---|
| Evidence-matrix uniqueness and coverage | PASS | 182 claim IDs; one disclosed conflict; no silent reconciliation. |
| Canonical input immutability | PASS | The asset generator reads the A1–A5C lineage and reports `canonical_artifact_modification=false`. |
| Exact randomisation reproduction | PASS | The 10,000-path matched-count and rank-shuffle distributions were regenerated from frozen inputs; the canonical diagnostic values were reproduced. |
| CSV integrity | PASS | All 23 derived table CSVs, the figure manifest and evidence matrix—25 files—were imported and inspected using `@oai/artifact-tool`. |
| Main-paper length | PASS | 15,615 words, excluding references and supplementary appendices; within the requested 15,000–25,000 range. |
| Abstract length | PASS | Approximately 360 words; within the requested 300–400 range. |
| Executive-summary length | PASS | 1,314 words; designed to remain within approximately four pages. |
| Required tables | PASS | 22 numbered main-paper tables, with detailed extensions in 23 reproducible supplementary CSVs. |
| Required figures | PASS | All 16 required figures are present, captioned and listed in the figure manifest. |
| DOCX render | PASS | Microsoft Word rendered the mixed portrait/landscape document without clipped text, split captions or malformed code-span table cells. |
| PDF render | PASS | 56 pages were rasterised and visually inspected; all 16 figures and all main tables are legible at publication scale. |
| Two-pass reproduction | PASS | 45 deterministic generated files had identical hashes. The two PDF passes had identical hashes for every independently rasterised page. |
| Raw PDF byte equality | DOCUMENTED EXCEPTION | Word varies internal PDF serialisation despite fixed metadata. Raw PDF hashes differ, while all 56 page-render hashes are identical. See `UKACTIVE_PAPER_REPRODUCTION_CHECKS.json`. |

## Acceptance-question cross-check

| # | A new reader can answer | Result | Paper location |
|---:|---|---|---|
| 1 | What exactly is the strategy? | PASS | Sections 8, 9 and 26 |
| 2 | What data were used? | PASS | Sections 4 and 5 |
| 3 | How was point-in-time causality preserved? | PASS | Sections 5 and 6 |
| 4 | Which assumptions were necessary? | PASS | Section 5, Table 3 and Section 34 |
| 5 | What was tested? | PASS | Sections 3 and 11–24 |
| 6 | What failed? | PASS | Sections 12, 16, 17, 20, 24 and 25 |
| 7 | What worked? | PASS | Sections 13–15, 18, 21 and 22 |
| 8 | Why was M2 selected? | PASS | Section 25 |
| 9 | Why was TOP7 selected rather than TOP8? | PASS | Sections 14 and 25 |
| 10 | Why is the strategy monthly? | PASS | Sections 15 and 25 |
| 11 | Why is the M2 sleeve always invested? | PASS | Sections 16, 25 and 26 |
| 12 | Why is the whole SIPP still partly defensive? | PASS | Sections 1, 25, 27, 29 and 30 |
| 13 | Why were cash and regime overlays rejected? | PASS | Sections 16 and 20 |
| 14 | How dependent is the strategy on major winners? | PASS | Sections 22 and 24 |
| 15 | How uncertain is the estimated edge? | PASS | Sections 23 and 34 |
| 16 | What are the exact historical statistics? | PASS | Sections 18, 19 and 27 |
| 17 | What are the live transaction-cost assumptions? | PASS | Sections 10, 27 and 28 |
| 18 | How should it be operated each month? | PASS | Section 30 and Supplement S11 |
| 19 | When should it be suspended? | PASS | Section 32 |
| 20 | What evidence is still required? | PASS | Sections 33–35 |

## Final interpretation check

PASS. The paper ends with the required restrained interpretation: the frozen M2 model contains meaningful causal historical ranking information and captured several major ETF-family trends, but its portfolio-level advantage is episodic, cost-sensitive and materially dependent on a small right tail. It is frozen for controlled, limited, prospective use rather than classified as independently confirmed alpha.

Permitted use remains a controlled 10% pilot after operational readiness and explicit user approval. The paper does not establish independently confirmed alpha, guaranteed drawdown protection, a permanent 4% cash return, superiority in every market regime, or suitability for an unrestricted whole-SIPP allocation.
