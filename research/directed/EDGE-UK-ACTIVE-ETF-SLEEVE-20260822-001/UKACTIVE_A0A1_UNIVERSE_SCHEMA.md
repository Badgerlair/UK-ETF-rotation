# UKACTIVE-A0A1 — Universe Schema

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

## Identity model

`fund_entity_id → share_class_id / ISIN → listing_id / MIC + ticker + price_unit`

Ticker is not a key. `listing_id` hashes ISIN, MIC, ticker, and explicit price unit. The economic taxonomy is orthogonal to identity: `economic_exposure_family_id` identifies the opportunity and `duplicate_group_id` groups interchangeable implementations with the same hedge state.

## Tables

- `UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv` — One row per current LSE catalogue listing line, including instruments not curated.
- `UKACTIVE_A0A1_FUND_MASTER.csv` — One row per observed legal fund/issuing entity.
- `UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv` — One row per selected ISIN/share class; accumulation/distribution and hedge state live here.
- `UKACTIVE_A0A1_LISTING_MASTER.csv` — One row per ISIN + MIC + ticker + price-unit implementation line.
- `UKACTIVE_A0A1_CURRENT_INVESTABILITY.csv` — Current, explicitly dated eligibility evidence per listing; never historical.
- `UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv` — One row per signalable future economic opportunity.
- `UKACTIVE_A0A1_DUPLICATE_GROUPS.csv` — One row per economically equivalent implementation group.
- `UKACTIVE_A0A1_IMPLEMENTATION_CANDIDATES.csv` — All retained listing candidates, evidence-ordered without a trade decision.

## Principal table columns

### Fund

`fund_entity_id`, `legal_fund_name`, `provider_issuer`, `domicile`, `fund_inception_date`, `fund_entity_identity_confidence`, `identity_evidence_ids`, `observation_date`, `historical_eligibility_supported`, `warning`

### Share class

`share_class_id`, `fund_entity_id`, `sub_fund_name`, `share_class_name`, `provider_issuer`, `isin`, `share_class_currency`, `fund_base_currency`, `underlying_economic_currency_exposure`, `hedged_unhedged`, `hedge_currency`, `share_class_inception_date`, `accumulating_distributing`, `ter_ocf_percent`, `benchmark_index`, `replication_method`, `product_structure`, `ucits_status`, `ucits_evidence_basis`, `instrument_type`, `physical_backing`, `collateralisation`, `issuer_risk_assessment`, `counterparty_risk_assessment`, `leverage`, `daily_reset`, `path_dependence`, `maturity`, `etc_structural_review_status`, `economic_exposure_family_id`, `duplicate_group_id`, `identity_evidence_ids`, `classification_evidence_ids`, `observation_date`, `historical_eligibility_supported`, `documented_exception_code`, `warning`

### Listing

`listing_id`, `share_class_id`, `fund_entity_id`, `isin`, `sedol`, `exchange`, `mic`, `ticker`, `listing_currency`, `price_unit`, `price_unit_multiplier_to_listing_currency`, `listing_inception_date`, `active_listing_status`, `active_status_verification_date`, `active_status_confidence`, `economic_exposure_family_id`, `duplicate_group_id`, `local_market_data_symbol_match`, `local_market_data_first_seen`, `local_market_data_last_seen`, `local_market_data_timeframes`, `identity_evidence_ids`, `observation_date`, `historical_eligibility_supported`, `warning`

### Investability

`listing_id`, `share_class_id`, `isin`, `mic`, `ticker`, `current_investability_state`, `current_uk_retail_eligibility`, `isa_eligibility`, `sipp_eligibility`, `ibkr_availability`, `broker_status`, `broker_check_method`, `broker_check_date`, `current_exchange_listing_status`, `kid_retail_document_evidence`, `kid_retail_document_url`, `structural_eligibility`, `eligibility_verification_date`, `eligibility_confidence`, `eligibility_evidence_ids`, `historical_eligibility`, `historical_eligibility_supported`, `warning`

### Economic exposure

`economic_exposure_family_id`, `economic_opportunity_id`, `duplicate_group_id`, `economic_exposure_name`, `opportunity_type`, `universe_tier`, `asset_class`, `sub_asset_class`, `primary_geography`, `geographic_scope`, `country`, `developed_emerging`, `sector`, `industry`, `economic_theme`, `deepvue_theme`, `factor_style`, `market_cap_segment`, `bond_issuer_type`, `bond_duration_bucket`, `bond_credit_bucket`, `inflation_linked`, `commodity_type`, `portfolio_role`, `underlying_economic_currency_exposure`, `hedged_unhedged`, `hedge_currency`, `share_class_count`, `listing_count`, `provider_count`, `providers`, `currently_verified_investable_isin_count`, `classification_rule_version`, `classification_basis`, `future_signal_unit`, `observation_date`, `historical_eligibility_supported`, `warning`

## Controlled values and null semantics

- Current investability: `CURRENTLY_INVESTABLE`, `CURRENT_CANDIDATE_UNVERIFIED`, `NOT_ELIGIBLE`.
- Canonical tier: `CORE`, `EXTENDED`, `EXPERIMENTAL`; exclusions are held separately.
- Broker: `NOT_CHECKED` unless an exact account-specific read-only result exists.
- Non-applicable classification: exactly `NOT_APPLICABLE`; unknown evidence is `NOT_VERIFIED`, `NOT_DETERMINED`, or `NOT_AVAILABLE` according to meaning.
- Price unit: `GBP` is pounds; `GBX` is pence and has multiplier `0.01` into GBP. Listing currency remains `GBP` for both.
- Historical fields: current outputs always carry `historical_eligibility_supported=NO`.

## Duplicate invariants

1. Same ISIN across listings → one share class and family; many listing IDs.
2. Accumulating versus distributing → distinct share classes/ISINs, usually the same family and duplicate group.
3. Hedged versus unhedged → distinct families and duplicate groups.
4. Equivalent indices across providers → one family, multiple implementation candidates.
5. Near-neighbour indices are only grouped after explicit economic-equivalence review; unresolved cases remain separate or experimental.
