# UKACTIVE-A2R2 root-cause report

## Exact cutoff

The old A3R1 constructor reproduces `RS_252_LAST_VALID_DATE = 2017-11-03` and `FIVE_HORIZON_COMPOSITE_LAST_VALID_DATE = 2017-08-25`.

## Root cause

The A2 calendar was an observed vendor-session union, not a complete official XLON calendar. It admitted 29 bank holidays/non-sessions. Examples are 2017-08-28, 2018-05-07, 2018-05-28, 2018-08-27, 2019-05-06, 2019-05-27, 2019-08-26, 2020-05-08. On 2017-08-28, a small number of vendor rows caused the bank holiday to be treated as a session. Some instruments received a spurious valid zero return; most received a missing row, and the next genuine session could also lose the prior-session canonical selection.

A3R1 then required every one of 252 consecutive master-calendar daily-return rows to be valid. The benchmark suffered a genuine selected-line gap on 2017-11-08. A single gap could age out after 252 master rows, but recurring contaminated bank-holiday/missing-selection pairs ensured that no later 252-row window became clean. Thus short horizons intermittently recovered while strict 252-session and five-horizon signals disappeared from the modern period.

The root-cause codes are: `MASTER_CALENDAR_CONTAMINATION`, `CONSECUTIVE_ROW_REQUIREMENT`, `BENCHMARK_VALIDITY_CHAIN`, `RETURN_CHAIN_BREAK`, `MASTER_ROW_SESSION_COUNT_ERROR`, and `DAILY_VALIDITY_USED_AS_FORMATION_ENDPOINT_VALIDITY`. Stale-price propagation and canonical implementation transitions were investigated and are not the cause of the synchronous 2017 cutoff.

## Repair

A2R2 replaces only the research-session and signal-history adapter: official-session rules determine the XLON calendar, while formation returns use validated GBP total-return-index endpoints within explicit continuity segments. Raw A2R daily values on retained dates are unchanged. Missing and stale observations remain invalid.
