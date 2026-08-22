# UKACTIVE A3 — Research Candidates

Stage decision: **UKACTIVE_A3_WEAK_OR_REGIME_DEPENDENT_SIGNAL**.

Best-supported definition: `ABOVE_GBP_CASH_252` (SECONDARY).

| signal_id | signal_family | classification | criteria_passed | criteria_applicable | criteria_fraction | headline_average_mean_ic | headline_fdr_survivor_count | headline_positive_spread_cells | headline_average_monotonicity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ABOVE_GBP_CASH_252 | CASH_RELATIVE_QUALIFICATION | SECONDARY | 10 | 13 | 0.769231 | 0.088123 | 0 | 6 | 0.564959 |
| ABS_POS_252 | ABSOLUTE_MOMENTUM_QUALIFICATION | SECONDARY | 9 | 13 | 0.692308 | 0.084005 | 0 | 6 | 0.514960 |
| TREND_MA_252 | TOTAL_RETURN_TREND_QUALIFICATION | SECONDARY | 9 | 13 | 0.692308 | 0.035523 | 0 | 4 | 0.500317 |
| RISK_ADJ_MOM_252_VOL63 | RISK_ADJUSTED_MOMENTUM | WEAK | 6 | 12 | 0.500000 | 0.019504 | 0 | 4 | 0.527557 |
| MULTI_Z_63_126_252 | MULTI_HORIZON_RELATIVE_STRENGTH | WEAK | 6 | 12 | 0.500000 | 0.006671 | 0 | 6 | 0.513605 |
| MOM_12_1 | TWELVE_MINUS_ONE_MOMENTUM | WEAK | 5 | 11 | 0.454545 | 0.003203 | 0 | 4 | 0.501189 |
| ABS_POS_126 | ABSOLUTE_MOMENTUM_QUALIFICATION | REJECTED | 4 | 11 | 0.363636 | -0.012662 | 0 | 5 | 0.509002 |
| ABOVE_GBP_CASH_126 | CASH_RELATIVE_QUALIFICATION | REJECTED | 4 | 11 | 0.363636 | -0.016629 | 0 | 5 | 0.510482 |
| RISK_ADJ_MOM_126_VOL63 | RISK_ADJUSTED_MOMENTUM | REJECTED | 4 | 12 | 0.333333 | -0.042344 | 0 | 5 | 0.507090 |
| MOM_126 | SIMPLE_TOTAL_RETURN_MOMENTUM | REJECTED | 4 | 12 | 0.333333 | -0.046505 | 0 | 5 | 0.509044 |
| MOM_63 | SIMPLE_TOTAL_RETURN_MOMENTUM | REJECTED | 2 | 11 | 0.181818 | -0.042266 | 0 | 1 | 0.485000 |
| MOM_252 | SIMPLE_TOTAL_RETURN_MOMENTUM | REJECTED | 2 | 12 | 0.166667 | -0.001845 | 0 | 0 | 0.493748 |
| MULTI_Z_21_63_126 | MULTI_HORIZON_RELATIVE_STRENGTH | REJECTED | 2 | 12 | 0.166667 | -0.041157 | 0 | 3 | 0.485521 |
| MOM_21 | SIMPLE_TOTAL_RETURN_MOMENTUM | REJECTED | 0 | 11 | 0.000000 | -0.029272 | 0 | 0 | 0.482926 |

## Promotion rule

`RESEARCH_CANDIDATE` requires at least 75% of applicable predeclared criteria, at least one BH-FDR-surviving headline IC result, correct economic direction, and no critical timing/data failure. `SECONDARY`, `WEAK` and `REJECTED` retain all unsuccessful as well as successful specifications in the multiple-testing ledger.

## Boundary

Classification is signal-level only. It does not select holdings, weights, turnover controls, a regime overlay or an implementation vehicle, and it is not a deployment-candidate designation.
