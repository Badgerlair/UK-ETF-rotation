# UKACTIVE-A2R manual validation cases

These 14 cases validate economic identity first and then reconstruct one stored GBP total return from the selected route's adjusted GBP wealth. They are data checks, not performance results.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

Completed cases: **14/14**. Passed: **14/14**.

## A2R-MAN-01 — AUSTRALIA

Intended economic definition → `AUSTRALIA × BROAD_MARKET × MSCI_AUSTRALIA × UNHEDGED × BROAD_COUNTRY`

Old A2 implementation → `AUSTRALIA × BROAD_MARKET × MSCI_AUSTRALIA × HEDGED_GBP × BROAD_COUNTRY`

Old result → FAIL|GBP-hedged share class attached to an unhedged Australia family

Replacement/state → `IE00BD4TY345|AUAD|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1_AND_A2_EXACT_IDENTITY_LINEAGE|ALL_OBSERVATIONS:MSCI_AUSTRALIA|EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY

Corrected first valid date → 2017-09-26 00:00:00

Sample check → date `2017-09-26 00:00:00`; stored `-0.007467544332254494`; independently reconstructed `-0.007467544332254494`; absolute error `0.0`.

Distribution check → PASS;UNRESOLVED_NO_PRICE_ON_EVENT_DATE

FX/GBP check → NOT_REQUIRED_GBP_OR_GBX_LISTING

A2 validation → PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION; manual status → **PASS**.

## A2R-MAN-02 — CHINA_BROAD

Intended economic definition → `CHINA × BROAD_MARKET × MSCI_CHINA × UNHEDGED × BROAD_COUNTRY`

Old A2 implementation → `CHINA × A_SHARES × MSCI_CHINA_A × UNHEDGED × NARROW_COUNTRY_SEGMENT`

Old result → FAIL|China A-share lines dominate a family intended to represent broad MSCI China

Replacement/state → `IE00B44T3H88|HMCH|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.assetmanagement.hsbc.co.uk/api/v1/download/document/ie00b44t3h88/gb/en/factsheet|ALL_OBSERVATIONS:MSCI_CHINA|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2011-02-24 00:00:00

Sample check → date `2011-02-24 00:00:00`; stored `-0.008379898938989383`; independently reconstructed `-0.008379898938989383`; absolute error `0.0`.

Distribution check → PASS;UNRESOLVED_NO_PRICE_ON_EVENT_DATE;UNRESOLVED_NO_PRIOR_PRICE

FX/GBP check → NOT_REQUIRED_GBP_OR_GBX_LISTING

A2 validation → PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION; manual status → **PASS**.

## A2R-MAN-03 — EUROPE_ENERGY

Intended economic definition → `EUROPE × ENERGY × MSCI_EUROPE_ENERGY_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × ENERGY × MSCI_WORLD_ENERGY × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|MSCI World Energy history attached to a Europe sector family

Replacement/state → `IE00BKWQ0F09|ENGY|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ssga.com/ie/en_gb/institutional/etfs/state-street-spdr-msci-europe-energy-ucits-etf-stn-fp|ALL_OBSERVATIONS:MSCI_EUROPE_ENERGY_35_20_CAPPED|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2016-02-11 00:00:00

Sample check → date `2016-02-11 00:00:00`; stored `-0.014255464225732206`; independently reconstructed `-0.014255464225732206`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-04 — EUROPE_FINANCIALS

Intended economic definition → `EUROPE × FINANCIALS × MSCI_EUROPE_FINANCIALS_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × FINANCIALS × MSCI_WORLD_FINANCIALS × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|Canonical route changes from Europe Financials to MSCI World Financials

Replacement/state → `IE00BKWQ0G16|FNCL|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1_AND_A2_EXACT_IDENTITY_LINEAGE|ALL_OBSERVATIONS:MSCI_EUROPE_FINANCIALS_35_20_CAPPED|EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY

Corrected first valid date → 2014-12-12 00:00:00

Sample check → date `2014-12-12 00:00:00`; stored `-0.028972965683985885`; independently reconstructed `-0.028972965683985885`; absolute error `0.0`.

Distribution check → NO_EVENT_AVAILABLE_VENDOR_SEMANTICS_VALIDATED

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE; manual status → **PASS**.

## A2R-MAN-05 — EUROPE_HEALTHCARE

Intended economic definition → `EUROPE × HEALTHCARE × MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × HEALTHCARE × MSCI_WORLD_HEALTH_CARE × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|Canonical route changes from Europe Health Care to MSCI World Health Care

Replacement/state → `IE00BKWQ0H23|HLTH|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1_AND_A2_EXACT_IDENTITY_LINEAGE|ALL_OBSERVATIONS:MSCI_EUROPE_HEALTH_CARE_35_20_CAPPED|EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY

Corrected first valid date → 2014-12-12 00:00:00

Sample check → date `2014-12-12 00:00:00`; stored `-0.024188523553278274`; independently reconstructed `-0.024188523553278274`; absolute error `0.0`.

Distribution check → NO_EVENT_AVAILABLE_VENDOR_SEMANTICS_VALIDATED

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE; manual status → **PASS**.

## A2R-MAN-06 — EUROPE_INDUSTRIALS

Intended economic definition → `EUROPE × INDUSTRIALS × MSCI_EUROPE_INDUSTRIALS_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × INDUSTRIALS × MSCI_WORLD_INDUSTRIALS × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|MSCI World Industrials history attached to a Europe sector family

Replacement/state → `IE00BKWQ0J47|NDUS|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ssga.com/dk/en_gb/institutional/etfs/state-street-spdr-msci-europe-industrials-ucits-etf-stq-fp|ALL_OBSERVATIONS:MSCI_EUROPE_INDUSTRIALS_35_20_CAPPED|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2014-12-12 00:00:00

Sample check → date `2014-12-12 00:00:00`; stored `-0.024285311258823494`; independently reconstructed `-0.024285311258823494`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-07 — EUROPE_MATERIALS

Intended economic definition → `EUROPE × MATERIALS × MSCI_EUROPE_MATERIALS_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × MATERIALS × MSCI_WORLD_MATERIALS × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|MSCI World Materials history attached to a Europe sector family

Replacement/state → `IE00BKWQ0L68|MTRL|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ssga.com/nl/nl/institutional/etfs/funds/spdr-msci-europe-materials-ucits-etf-stp-fp|ALL_OBSERVATIONS:MSCI_EUROPE_MATERIALS_35_20_CAPPED|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2017-01-04 00:00:00

Sample check → date `2017-01-04 00:00:00`; stored `-0.0009828855246140078`; independently reconstructed `-0.0009828855246140078`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-08 — EUROPE_TECHNOLOGY

Intended economic definition → `EUROPE × TECHNOLOGY × MSCI_EUROPE_INFORMATION_TECHNOLOGY_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × TECHNOLOGY × MSCI_WORLD_INFORMATION_TECHNOLOGY × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|MSCI World Technology history attached to a Europe sector family

Replacement/state → `IE00BKWQ0K51|ITEC|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ssga.com/lu/en_gb/intermediary/library-content/products/factsheets/etfs/emea/factsheet-emea-en_gb-stk-fp.pdf|ALL_OBSERVATIONS:MSCI_EUROPE_INFORMATION_TECHNOLOGY_35_20_CAPPED|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2014-12-12 00:00:00

Sample check → date `2014-12-12 00:00:00`; stored `-0.021618850779303922`; independently reconstructed `-0.021618850779303922`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-09 — EUROPE_UTILITIES

Intended economic definition → `EUROPE × UTILITIES × MSCI_EUROPE_UTILITIES_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × UTILITIES × MSCI_WORLD_UTILITIES × UNHEDGED × BROAD_SECTOR`

Old result → FAIL|MSCI World Utilities history attached to a Europe sector family

Replacement/state → `IE00BKWQ0P07|UTIL|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ssga.com/uk/en_gb/institutional/etfs/state-street-spdr-msci-europe-utilities-ucits-etf-stu-fp|ALL_OBSERVATIONS:MSCI_EUROPE_UTILITIES_35_20_CAPPED|EXACT_INTENDED_INDEX_OR_OBJECTIVE

Corrected first valid date → 2014-12-12 00:00:00

Sample check → date `2014-12-12 00:00:00`; stored `-0.024909636500841437`; independently reconstructed `-0.024909636500841437`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-10 — GLOBAL_BANKS

Intended economic definition → `GLOBAL × BANKS × GLOBAL_DEVELOPED_BANKS × UNHEDGED × INDUSTRY`

Old A2 implementation → `EUROPE × BANKS × STOXX_EUROPE_600_OPTIMISED_BANKS × UNHEDGED × INDUSTRY`

Old result → FAIL|Europe banks and one development-bank bond observation attached to a global-banks family

Replacement/state → `NO_VALID_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1 registry and evidence ledger exhausted; no exact global-banks implementation established

Corrected first valid date → NOT_APPLICABLE

Sample check → date `NOT_APPLICABLE`; stored `nan`; independently reconstructed `nan`; absolute error `nan`.

Distribution check → NOT_APPLICABLE_EXCLUDED

FX/GBP check → NOT_APPLICABLE_EXCLUDED

A2 validation → PASS_EXCLUDED_BECAUSE_NO_VALID_HISTORY; manual status → **PASS**.

## A2R-MAN-11 — GLOBAL_HEALTHCARE

Intended economic definition → `GLOBAL × HEALTHCARE × MSCI_WORLD_HEALTH_CARE_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × HEALTHCARE_INNOVATION × THEMATIC_HEALTHCARE_INNOVATION × UNHEDGED × THEME`

Old result → FAIL|Broad world-health history changes into healthcare-innovation thematic implementations

Replacement/state → `LU0533033311|HLTW|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1_AND_A2_EXACT_IDENTITY_LINEAGE|ALL_OBSERVATIONS:MSCI_WORLD_HEALTH_CARE|EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY

Corrected first valid date → 2011-05-19 00:00:00

Sample check → date `2011-05-19 00:00:00`; stored `0.005756370343169781`; independently reconstructed `0.005756370343169781`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

## A2R-MAN-12 — GLOBAL_INFRASTRUCTURE

Intended economic definition → `GLOBAL × INFRASTRUCTURE × FTSE_GLOBAL_CORE_INFRASTRUCTURE × UNHEDGED × LISTED_INFRASTRUCTURE`

Old A2 implementation → `UNITED_STATES × INFRASTRUCTURE × US_INFRASTRUCTURE_DEVELOPMENT × UNHEDGED × THEME`

Old result → FAIL|US and Europe infrastructure products attached to a stable global-infrastructure family

Replacement/state → `IE00B1FZS467|INFR|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → https://www.ishares.com/uk/individual/en/products/251809/ishares-global-infrastructure-ucits-etf|2006-10-20_TO_2017_INDEX_CHANGE:MACQUARIE_GLOBAL_INFRASTRUCTURE_100|POST_CHANGE:FTSE_GLOBAL_CORE_INFRASTRUCTURE|SAME_LEGAL_FUND_AND_BROAD_GLOBAL_LISTED_INFRASTRUCTURE_OBJECTIVE;PREDECESSOR_INDEX_EXPLICITLY_ALLOWED_NOT_SPLICED

Corrected first valid date → 2006-10-26 00:00:00

Sample check → date `2006-10-26 00:00:00`; stored `-0.005227821285191059`; independently reconstructed `-0.005227821285191059`; absolute error `0.0`.

Distribution check → PASS;UNRESOLVED_NO_PRICE_ON_EVENT_DATE;UNRESOLVED_NO_PRIOR_PRICE

FX/GBP check → NOT_REQUIRED_GBP_OR_GBX_LISTING

A2 validation → PASS_EXPLICIT_DISTRIBUTION_RECONCILIATION; manual status → **PASS**.

## A2R-MAN-13 — GLOBAL_TECHNOLOGY

Intended economic definition → `GLOBAL × TECHNOLOGY × MSCI_WORLD_INFORMATION_TECHNOLOGY_35_20_CAPPED × UNHEDGED × BROAD_SECTOR`

Old A2 implementation → `GLOBAL × DIGITALISATION × DIGITALISATION_THEME × UNHEDGED × THEME`

Old result → FAIL|Digitalisation thematic implementation attached to a broad technology-sector family

Replacement/state → `IE00BYTRRD19|WTEC|CORRECTED_IMPLEMENTATION_HISTORY`

Identity evidence → A0A1_AND_A2_EXACT_IDENTITY_LINEAGE|ALL_OBSERVATIONS:MSCI_WORLD_INFORMATION_TECHNOLOGY_35_20_CAPPED|EXACT_INTENDED_OR_EXPLICITLY_ALLOWED_INDEX_FAMILY

Corrected first valid date → 2016-05-09 00:00:00

Sample check → date `2016-05-09 00:00:00`; stored `0.01213140106404853`; independently reconstructed `0.01213140106404853`; absolute error `0.0`.

Distribution check → NO_EVENT_AVAILABLE_VENDOR_SEMANTICS_VALIDATED

FX/GBP check → GBP_CONVERSION_APPLIED_ONCE_ECB_RATE_NO_LATER_THAN_DATE

A2 validation → PASS_VENDOR_SEMANTICS_NO_EVENT_AVAILABLE; manual status → **PASS**.

## A2R-MAN-14 — US_AEROSPACE_DEFENCE

Intended economic definition → `UNITED_STATES × AEROSPACE_AND_DEFENCE × VETTAFI_AMERICAN_FUTURE_OF_DEFENCE × UNHEDGED × INDUSTRY`

Old A2 implementation → `GLOBAL × AEROSPACE_AND_DEFENCE × GLOBAL_DEFENCE × UNHEDGED × INDUSTRY`

Old result → FAIL|Global defence history attached to a United States aerospace-and-defence family

Replacement/state → `IE000KDY10O3|SEAL|VALID_ONLY_FROM_LATER_DATE`

Identity evidence → https://hanetf.com/fund/gijo-future-of-us-defence-etf/|BEFORE_2026-07-16:GLOBAL_METAVERSE_NOT_VALID_FOR_FAMILY|FROM_2026-07-16:VETTAFI_AMERICAN_FUTURE_OF_DEFENCE|DATED_OBJECTIVE_CHANGE;PREDECESSOR_OBSERVATIONS_INVALIDATED

Corrected first valid date → 2026-07-20 00:00:00

Sample check → date `2026-07-20 00:00:00`; stored `0.0021417445482865283`; independently reconstructed `0.0021417445482865283`; absolute error `0.0`.

Distribution check → ZERO_REPORTED_DISTRIBUTIONS_ACCUMULATING

FX/GBP check → NOT_REQUIRED_GBP_OR_GBX_LISTING

A2 validation → PASS_VENDOR_SEMANTICS_AND_ZERO_REPORTED_DISTRIBUTIONS; manual status → **PASS**.

