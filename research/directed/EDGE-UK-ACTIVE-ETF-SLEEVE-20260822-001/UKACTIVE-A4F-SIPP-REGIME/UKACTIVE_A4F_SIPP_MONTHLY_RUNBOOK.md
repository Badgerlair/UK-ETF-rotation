# UKACTIVE-A4F-SIPP monthly runbook

## SHADOW RESEARCH RUN — GLOBAL_50_M2_50

After the final valid XLON close, validate the A2R2 inputs and calculate M2_BASE as the cross-sectional percentile-rank composite RS21 10% + RS42 15% + RS63 25% + RS126 30% + RS252 20% over the point-in-time, duplicate-suppressed INDUSTRY_PLUS_THEME universe. Select the current TOP7 economic families and weight them equally within the M2 sleeve, replacing prior families that are no longer TOP7. Target SWDA 50%, the seven equal-weight M2 families in aggregate 50%, and GBP cash 0%. Regime fields are recorded as telemetry only and never change these strategic weights. Record the decision before the next-session close; execute at the first valid following XLON session within three sessions; charge 20 bp and £3.99 per leg; if a verified M2 implementation is unavailable its affected allocation remains GBP cash; reconcile holdings, costs and hashes. No automatic broker execution.

This 50% SWDA / 50% M2 architecture is research/shadow only. Record regime telemetry, but do not let it change weights. It authorises no pension-capital or broker action.

## CURRENT OPERATING FALLBACK — GLOBAL_75_CASH25

After the final valid XLON close each month, validate SWDA and GBP-cash inputs. Target 75% SWDA and 25% GBP cash. Record before the next-session close; execute at the first valid following XLON session within three valid sessions; charge the applicable documented implementation costs. M2 allocation is 0%. This continuity rule remains separate from the shadow selection.

## INSTRUMENT AND SUSPENSION RULES

SWDA is the confirmed core. M2 uses only the preverified current implementation map; an unavailable preferred and alternate line leaves the affected slot in GBP cash. No discretionary substitute and no live-order generator exist.

- `DATA_VALIDATION_SUSPENSION` — trigger: Required price, total-return, cash, XLON-calendar, hash, or point-in-time-universe validation fails. Action: Create no decision and do not backfill; affected allocation remains GBP cash until a fully valid month-end.
- `M2_REPRODUCIBILITY_SUSPENSION` — trigger: The eligible INDUSTRY_PLUS_THEME universe or M2 ranks cannot be reproduced. Action: Allocate the M2 sleeve to GBP cash; require one subsequent fully valid monthly decision before restoration.
- `INSTRUMENT_AVAILABILITY_SUSPENSION` — trigger: Both the frozen preferred and predeclared alternate implementation for an exposure are unavailable. Action: Affected exposure remains GBP cash; no discretionary substitute.
- `CORE_AVAILABILITY_SUSPENSION` — trigger: SWDA and its predeclared verified alternate are unavailable. Action: Entire SWDA allocation remains GBP cash pending governance review.
- `EXECUTION_TIMING_SUSPENSION` — trigger: The first valid following XLON execution cannot be obtained within three valid sessions. Action: Do not chase price; affected allocation remains GBP cash and append an operational exception.
- `COST_SUSPENSION` — trigger: Estimated one-way implementation friction exceeds the frozen doubled-cost stress of 40 bp or fixed dealing cost exceeds GBP7.98 per leg at GBP250,000. Action: Suspend new allocation changes and perform a documented cost review.
- `RESEARCH_INVALIDATION` — trigger: A historical data, eligibility, lookahead, or accounting defect would have changed a material decision or conclusion. Action: Freeze interpretation and open a separately governed repair stage.
- `NO_PERFORMANCE_ONLY_STOP` — trigger: Short-term underperformance alone. Action: No automatic suspension; any prospective performance invalidation criterion must be separately preregistered.
