# UKACTIVE-A4F-SIPP — final decision report

Historical cutoff: **2026-08-21**. Evidence: **E2 developmental**. Audit: **PASS**.

The risk and alpha modules were evaluated separately, then combined only through six frozen policies. All thresholds were prior-only, all targets executed next session, and no post-cutoff observation entered a state or result.

## DIRECT ANSWERS TO THE 25 FINAL QUESTIONS

1. **Why M2 varied by year:** M2 beat SWDA in 2020, 2025, 2026; it lagged in 2017, 2018, 2019, 2021, 2022, 2023, 2024. The holding-spell ledger shows a positively skewed process: persistent independent leaders help, false leaders and broad-market dominance hurt. Top-spell entry diagnostics were GLOBAL_SILVER_MINERS: pre-entry 126-session 12.5%, held 146.3%, before-majority=True; GLOBAL_BATTERY_EV: pre-entry 126-session -0.9%, held 109.4%, before-majority=True; GLOBAL_SEMICONDUCTORS: pre-entry 126-session -1.3%, held 78.4%, before-majority=True; these are ex-post mechanism diagnostics and never entered the rule.
2. **Observable positive-M2 states:** R2_LEADERSHIP_RISK_ON: M2-minus-global 1.80% annualised (86 return intervals/11 episodes). This is the only claim-qualified state result; sparse states are descriptive only.
3. **Recurrence:** adequately sampled states were R2_LEADERSHIP_RISK_ON (86 months/11 episodes). The R2 association recurred across the episode count shown above, but one claim-qualified state is insufficient to promote a switching map.
4. **Post-2020 versus date split:** the regime sample is not broad enough to attribute the post-2020 difference causally; `UNRESOLVED_REGIME_VERSUS_DATE_SPLIT` is the defensible conclusion.
5. **2025:** exceptional, but not the sole sign of M2 value. The selected replacement test is full 0.80%, excluding 2025 0.06%, doubled cost 0.03%; its ex-2025 margin is economically thin.
6. **Strong global/weak thematic leadership:** SWDA is preferred by the alpha rule; the selected static fallback nevertheless holds its fixed blend because dynamic timing failed its gates.
7. **10%/25% M2 sleeve:** static incremental CAGR was 0.07% at 10% and 0.36% at 25%; both failed the doubled-cost incremental gate. Conditional 25% alpha timing delivered 0.06% versus matched exposure and was not promoted.
8. **Weak global/strong selected leadership:** R3 had 16 return intervals across eight episodes, below the frozen 18-month requirement; M2 lagged global there by 1.63 percentage points annualised. No live retention rule is promoted.
9. **Both weak:** experimental policies allocated 50% cash at risk score 2 and 75% cash at score 3, but those policies failed. The selected static strategy holds 0% strategic cash.
10. **Gradual versus binary defence:** gradual Policy 1 returned 7.89% with MDD -17.53%, better than A4E's binary 252-session rule at 6.82% CAGR and -25.58% MDD. It still retained only 68.0% of global CAGR and lagged its matched static exposure control by -2.33%, so it was not promoted.
11. **Risk module versus matched exposure:** Policy 1 incremental CAGR was -2.33%; it failed the matched-risk gate.
12. **Alpha module versus static exposure:** Policy 2 incremental CAGR was 0.06%; the edge was insufficiently robust for promotion.
13. **Combined modules:** Policy 3 returned 8.03% versus matched-control 10.22%; combination did not add value beyond simpler controls.
14. **Strategy switches:** Policy 3 immediate averaged 4.33 aggregate allocation changes per year; ordinary M2 rebalances are reported separately.
15. **False-defensive opportunity cost:** at actual Policy 3 defensive-switch intervals, the summed negative next-month policy-minus-matched-control effect was 3.70% return units.
16. **Successful-defence value:** at actual defensive-switch intervals, the summed positive next-month effect was 8.41%; full-chain MDD improved by 5.17% versus its matched control. These are counterfactual diagnostics, not a claim that the entire MDD difference was caused by those individual switches.
17. **Asymmetric re-risking:** Policy 3 CAGR changed from 8.03% immediate to 7.39% hysteretic; it did not rescue the policy.
18. **2025 exclusion:** full 0.80%, excluding 2025 0.06%, doubled cost 0.03%. Excluding both 2020 and 2025 produces -1.39% annualised excess versus global; this is material two-regime fragility.
19. **Doubled costs:** the selected static M2 replacement comparison remained non-negative but thin; dynamic policy gates are shown explicitly in the cost-stress file.
20. **Major contributors:** the selected static blend passed every leave-one-family-out gate, but its incremental CAGR reversed to -2.18% after removing GLOBAL_BATTERY_EV;GLOBAL_GOLD_MINERS;GLOBAL_SEMICONDUCTORS and -2.53% after removing EUROPE_BANKS;GLOBAL_BATTERY_EV;GLOBAL_GOLD_MINERS;GLOBAL_SEMICONDUCTORS;GLOBAL_SILVER_MINERS. The pre-entry/held-move fields in the spell ledger show whether each winner was selected before a majority of its combined positive 126-session pre-entry plus held move. This is material right-tail fragility even though no single family alone explains the full result.
21. **Best strategy by regime:** R2_LEADERSHIP_RISK_ON: GLOBAL_50_M2_50. Insufficient states are explicitly excluded from strong inference.
22. **Switching versus static:** no selectable dynamic policy passed all gates; the static portfolio is superior under the frozen hierarchy.
23. **Exact SIPP research strategy:** `GLOBAL_50_M2_50` / `STATIC_MONTHLY`; deployment remains `REGIME_STRATEGY_SHADOW_ONLY` rather than live authorisation.
24. **Exact allocations:** SWDA 50%, M2 50%, cash 0% in every regime because the selected rule is static.
25. **Suspension:** unavailable instruments, unreproducible membership, invalid inputs, materially excessive costs, or inability to execute next-session timing suspend affected allocations; a data/eligibility defect or systematic prospective matched-control failure reopens research.

## YEAR-BY-YEAR CONCLUSION

Selected-strategy annual results: 2017: 4.6%; 2018: -6.2%; 2019: 19.5%; 2020: 20.9%; 2021: 22.7%; 2022: -11.3%; 2023: 17.0%; 2024: 14.1%; 2025: 29.7%; 2026: 13.2%. M2 helped in some years and hurt in others; the detailed year table identifies best-return, lowest-drawdown, costs and sleeve contributions. Partial 2017/2026 are explicitly marked. Calendar years diagnose recurring states but do not choose the policy.

## REGIME CONCLUSION

Best adequately sampled static strategy by state: R2_LEADERSHIP_RISK_ON: GLOBAL_50_M2_50. Regime claims with fewer than 18 months or three episodes are marked insufficient. The causal policy selection result is `STATIC_GLOBAL_M2_CASH_BLEND`; oracle ceilings remain noncausal.

## ALPHA-ALLOCATION CONCLUSION

The M2 sleeve was tested directly against replacement by SWDA, under full history, 2025 exclusion, doubled costs and family/spell removals. Dynamic M2 addition was promoted only if matched-risk and multi-episode gates passed. Result: No dynamic policy passed all gates; the selected static blend retained positive preregistered M2 incremental value. For an M2 selection, the top-three removal result is -2.18% after removing GLOBAL_BATTERY_EV;GLOBAL_GOLD_MINERS;GLOBAL_SEMICONDUCTORS; excluding both 2020 and 2025 yields -1.39% annualised excess versus global. These sign reversals preclude robust alpha confirmation.

## RISK-ALLOCATION CONCLUSION

Gradual score-based risk scaling was compared with 100% global, static 75/25, matched average exposure, matched volatility and matched drawdown. A lower drawdown caused merely by lower average exposure was not treated as timing value. No dynamic risk policy passed. The selected static blend is return-oriented rather than a capital-protection success: MDD -23.62% versus SWDA -25.58%, Ulcer 5.89% versus 4.89%, and maximum underwater time 763 versus 586 days.

## BEST AVAILABLE WHOLE-SIPP STRATEGY

There is one A4F-selected strategy: the **research/shadow whole-SIPP architecture** `GLOBAL_50_M2_50` using `STATIC_MONTHLY`: SWDA 50.0%, M2 50.0%, cash 0.0%. Exact state allocations are in the state-machine JSON and table below. Its permitted action is shadow observation only; no pension capital is authorised by A4F. The static **75% SWDA / 25% GBP cash** core is documented solely as the current operational continuity fallback while the selected architecture remains shadow-only—not as a second A4F research selection.

## REGIME STATE MACHINE

| Risk score | Leadership | Regime | SWDA | M2 | Cash | Confirmation | Execution |
|---:|---|---|---:|---:|---:|---|---|
| 0 | LEADERSHIP_WEAK | R1_BROAD_RISK_ON | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 0 | LEADERSHIP_STRONG | R2_LEADERSHIP_RISK_ON | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 1 | LEADERSHIP_WEAK | R1_BROAD_RISK_ON | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 1 | LEADERSHIP_STRONG | R2_LEADERSHIP_RISK_ON | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 2 | LEADERSHIP_WEAK | R4_CAPITAL_PRESERVATION | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 2 | LEADERSHIP_STRONG | R3_ISOLATED_LEADERSHIP | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 3 | LEADERSHIP_WEAK | R4_CAPITAL_PRESERVATION | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |
| 3 | LEADERSHIP_STRONG | R3_ISOLATED_LEADERSHIP | 50% | 50% | 0% | Regime telemetry only; static allocation unchanged | Next valid XLON session |

## EXPECTED OPERATING CHARACTERISTICS

Historical common-window references—not forecasts—were net CAGR 12.40%, maximum drawdown -23.62%, Ulcer 5.89%, annual turnover 2.89x, 11.9 executed trade events per year and **zero regime-strategy switches** for the selected static rule. Conservative governance/stress ranges are 4%–10% nominal net CAGR, -15% to -30% maximum drawdown, 3%–10% Ulcer Index and roughly 2x–4x annual traded-notional turnover. The shadow research architecture schedules 12 monthly reviews, holds M2 at 50%, cash at 0% strategically, and permits temporary cash from data/implementation blocks up to 100% of an affected sleeve. The current operating rule instead holds M2 0% and cash 25%. Likely underperformance includes broad-market rallies led outside selected themes, weak thematic breadth, right-tail droughts and reversals in major M2 leaders.

## CURRENT EVIDENCE GRADE

`E2_DEVELOPMENTAL` — no A4F historical result is independent E3 confirmation.

## DEPLOYMENT TIER

`REGIME_STRATEGY_SHADOW_ONLY`

This means shadow observation only for the selected 50/50 research architecture. It does not supersede the static 75/25 operational core fallback and authorises no broker order.

## MONTHLY OPERATING RULE

After the final valid XLON close, validate the A2R2 inputs and calculate M2_BASE as the cross-sectional percentile-rank composite RS21 10% + RS42 15% + RS63 25% + RS126 30% + RS252 20% over the point-in-time, duplicate-suppressed INDUSTRY_PLUS_THEME universe. Select the current TOP7 economic families and weight them equally within the M2 sleeve, replacing prior families that are no longer TOP7. Target SWDA 50%, the seven equal-weight M2 families in aggregate 50%, and GBP cash 0%. Regime fields are recorded as telemetry only and never change these strategic weights. Record the decision before the next-session close; execute at the first valid following XLON session within three sessions; charge 20 bp and £3.99 per leg; if a verified M2 implementation is unavailable its affected allocation remains GBP cash; reconcile holdings, costs and hashes. No automatic broker execution.

## FAILURE MODES

Whipsaw around threshold crossings, slow re-risking after abrupt rebounds, M2 false leadership, right-tail concentration, changing ETF availability, cash-rate decline, gaps before monthly execution, and future drawdowns beyond the short 2017–2026 sample.

## SUSPENSION RULES

- `DATA_VALIDATION_SUSPENSION` — trigger: Required price, total-return, cash, XLON-calendar, hash, or point-in-time-universe validation fails. Action: Create no decision and do not backfill; affected allocation remains GBP cash until a fully valid month-end.
- `M2_REPRODUCIBILITY_SUSPENSION` — trigger: The eligible INDUSTRY_PLUS_THEME universe or M2 ranks cannot be reproduced. Action: Allocate the M2 sleeve to GBP cash; require one subsequent fully valid monthly decision before restoration.
- `INSTRUMENT_AVAILABILITY_SUSPENSION` — trigger: Both the frozen preferred and predeclared alternate implementation for an exposure are unavailable. Action: Affected exposure remains GBP cash; no discretionary substitute.
- `CORE_AVAILABILITY_SUSPENSION` — trigger: SWDA and its predeclared verified alternate are unavailable. Action: Entire SWDA allocation remains GBP cash pending governance review.
- `EXECUTION_TIMING_SUSPENSION` — trigger: The first valid following XLON execution cannot be obtained within three valid sessions. Action: Do not chase price; affected allocation remains GBP cash and append an operational exception.
- `COST_SUSPENSION` — trigger: Estimated one-way implementation friction exceeds the frozen doubled-cost stress of 40 bp or fixed dealing cost exceeds GBP7.98 per leg at GBP250,000. Action: Suspend new allocation changes and perform a documented cost review.
- `RESEARCH_INVALIDATION` — trigger: A historical data, eligibility, lookahead, or accounting defect would have changed a material decision or conclusion. Action: Freeze interpretation and open a separately governed repair stage.
- `NO_PERFORMANCE_ONLY_STOP` — trigger: Short-term underperformance alone. Action: No automatic suspension; any prospective performance invalidation criterion must be separately preregistered.

## REMAINING EVIDENCE GAP

No untouched historical holdout, no A4F prospective decisions, limited crisis diversity, sparse regime states where flagged, no accepted release-vintage UK macro dataset, uncertain future live spreads/cash yield, and a selected M2 edge that reverses when 2020 and 2025 are jointly excluded. The selected strategy requires prospective observation before material active allocation.
