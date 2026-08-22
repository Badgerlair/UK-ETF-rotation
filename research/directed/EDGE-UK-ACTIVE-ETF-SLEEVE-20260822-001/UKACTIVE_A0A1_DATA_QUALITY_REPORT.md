# UKACTIVE-A0A1 — Data Quality Report

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

Decision: `UKACTIVE_A0A1_PASS_WITH_OPEN_ITEMS`

The automated suite executed 27 controls: 27 passed and 0 failed. The current discovery registry has 4,359 listing lines and 2,821 ISINs; the curated master has 296 ISINs, 478 listing lines, and 99 economic families.

| Test | Status | Requirement | Detail |
|---|---:|---|---|
| QC-001 | PASS | Ticker is not treated as globally unique | listing_id is a deterministic hash of ISIN+MIC+ticker+price unit; ticker is descriptive only |
| QC-002 | PASS | Canonical share classes have ISIN or documented exception | share_classes=296 |
| QC-003 | PASS | Same-ISIN listings do not become multiple economic opportunities | unique_isins=296 |
| QC-004 | PASS | Unhedged GBP/USD listings remain one exposure | multi-price-unit ISINs tested=179 |
| QC-005 | PASS | Accumulating/distributing versions are distinct share classes | families_with_pair=UK_GILTS_SHORT;GLOBAL_ALL_WORLD;GLOBAL_INFRASTRUCTURE;UK_LARGE_CAP;EUROZONE;US_BROAD_LARGE_CAP;GLOBAL_CLEAN_ENERGY;ASIA_PACIFIC_EX_JAPAN;GLOBAL_CORPORATE_IG_GBP_HEDGED;EMERGING_MARKETS;SOUTH_KOREA;GLOBAL_DEVELOPED_WORLD;US_AI;JAPAN |
| QC-006 | PASS | Hedged and unhedged exposures are not collapsed | hedge_pairs=[('GLOBAL_DEVELOPED_WORLD', 'GLOBAL_DEVELOPED_WORLD_GBP_HEDGED'), ('US_BROAD_LARGE_CAP', 'US_BROAD_LARGE_CAP_GBP_HEDGED'), ('US_TOTAL_MARKET', 'US_TOTAL_MARKET_GBP_HEDGED'), ('JAPAN', 'JAPAN_GBP_HEDGED')] |
| QC-007 | PASS | GBP and GBX are explicit and correctly scaled | GBX maps to GBP at 0.01; GBP maps at 1 |
| QC-008 | PASS | UCITS is never inferred from name | allowed evidence bases enforced |
| QC-009 | PASS | Broker status is not inferred from price data | all broker states deliberately NOT_CHECKED |
| QC-010 | PASS | Current eligibility is not converted into historical eligibility | CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY |
| QC-011 | PASS | Leveraged/inverse/path-dependent instruments cannot enter canonical tiers | canonical_isins=296; structural_exclusions=403 |
| QC-012 | PASS | ETCs are assessed rather than blanket-excluded | unleveraged gold ETC candidate retained and structurally assessed |
| QC-013 | PASS | DeepVue themes are never invented | confirmed_label_count=31 |
| QC-014 | PASS | Non-thematic broad and bond products are not forced into DeepVue | explicit negative mappings checked, including growth-biased Nasdaq-100 |
| QC-015 | PASS | Sector and theme remain separate dimensions | separate columns and differing values observed |
| QC-016 | PASS | Geography is not inferred from listing currency | Japan GBP/GBX listings=6 |
| QC-017 | PASS | Provider duplication creates no additional opportunity rows | one row per family despite multi-provider implementations |
| QC-018 | PASS | Identity references are valid | fund→share class→listing foreign keys resolve |
| QC-019 | PASS | Tiers are exhaustive and permitted | all canonical families have exactly one permitted tier |
| QC-020 | PASS | Manual audit suite covers all required cases | audited=20/20 |
| QC-021 | PASS | Discovery universe is substantial | listings=4359; unique_isins=2821; families=99 |
| QC-022 | PASS | No strategy/backtest output exists | builder contains no price-return, signal, rank, portfolio, order, or backtest calculation |
| QC-023 | PASS | Direct gold cannot contain gold-mining equity products | direct_gold_share_classes=6 |
| QC-024 | PASS | Abbreviated daily-short products are excluded | daily_short_negative_controls=31 |
| QC-025 | PASS | GBP overnight family has explicit sterling-rate evidence | gbp_cash_share_classes=3 |
| QC-026 | PASS | Verified current investability requires product-specific retail evidence | verified_listing_rows=51 |
| QC-027 | PASS | Every canonical listing has a dated current status source | listing_rows=478 |

## Interpretation

`PASS_WITH_OPEN_ITEMS` is used when all correctness controls pass and the master is substantial, but broker confirmation, cross-provider product-level eligibility, historical reconstruction, or total-return validation remains visibly incomplete. Those gaps must never be relabelled as favourable evidence.

No strategy, signal, rank, portfolio, order, or return statistic was computed.
