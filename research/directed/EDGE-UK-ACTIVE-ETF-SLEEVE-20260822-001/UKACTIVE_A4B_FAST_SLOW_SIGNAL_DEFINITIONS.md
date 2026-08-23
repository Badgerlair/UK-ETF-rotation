# UKACTIVE-A4B fast/slow signal definitions

All values are formed after the applicable valid XLON close and may affect holdings only from the next eligible XLON session.

* `FAST_RS` is the equal mean of contemporaneous `RANK_RS_21`, `RANK_RS_42` and `RANK_RS_63` within `INDUSTRY_PLUS_THEME`.
* `SLOW_RS` is the unchanged `MH_LEVEL_3_6_12_REFERENCE`: the equal mean of `RANK_RS_63`, `RANK_RS_126` and `RANK_RS_252`.
* `FAST_RS_CHANGE_4W` and `SLOW_RS_CHANGE_4W` subtract the value four prior weekly observations earlier for the same economic family.
* `RELATIVE_SLOPE_42` and `RELATIVE_SLOPE_63` are the previously validated A3R1R1 log-relative-line regression slopes against `GLOBAL_DEVELOPED_WORLD`.
* `RS63_EXTENSION_Q90_PRIOR` is the family-specific expanding 90th percentile of weekly `RS_63`, shifted one observation and unavailable until 52 prior valid weekly observations exist.
* The three recent segments are the already validated, non-overlapping 0–21, 22–42 and 43–63-session benchmark-relative returns.
* Ordinal fast/slow ranks are descending and tie-broken by `economic_exposure_family_id` ascending.

Missing or invalid contemporaneous features are not filled, ranked or converted to zero. Same-horizon common-benchmark subtraction is descriptive and does not itself change cross-sectional order.
