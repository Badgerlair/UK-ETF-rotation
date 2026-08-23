# UKACTIVE-A3R2U recent survivorship report

Classification: **RECENT_FIVE_YEAR_CENSUS_SUBSTANTIALLY_COMPLETE**.

The refresh captured 4,356 current LSE ETF/ETC/ETN lines and reconciled all 105 authoritative A2R2 research families. The five-year census combines current LSE presence, validated implementation-history starts/ends, canonical implementation transitions, and primary issuer evidence for selected closures, mergers and mandate changes.

It is not classified COMPLETE because no complete licensed historical LSE delisting feed was available. Current-survivor bias is controlled through `DYNAMIC_POINT_IN_TIME`, `FIVE_YEAR_START_STATIC`, `MATURE_ONLY`, and `MATURE_PLUS_DEVELOPING` views and through explicit issuer lifecycle events. Products absent from the current master are not silently treated as never having existed.

The mandate history of ISIN IE000KDY10O3 is explicitly bounded: Web 3.0 history is not US-defence history, and the US-defence family remains valid only after the July 2026 strategy change and A2R warm-up.
