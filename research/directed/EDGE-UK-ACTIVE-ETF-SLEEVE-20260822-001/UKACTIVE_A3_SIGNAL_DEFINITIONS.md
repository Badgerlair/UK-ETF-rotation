# UKACTIVE A3 — Signal Definitions

Policy: `UKACTIVE-A3-POLICY-v1.1.0`. The registry was written before the empirical run and its row-level definition hashes are preserved.

| registry_order | signal_id | signal_family | role | registry_class | lookback_sessions | skip_sessions | volatility_window_sessions | formula |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MOM_21 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 21.0 |  |  | TR(t-21,t) |
| 2 | MOM_63 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 63.0 |  |  | TR(t-63,t) |
| 3 | MOM_126 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 126.0 |  |  | TR(t-126,t) |
| 4 | MOM_252 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 252.0 |  |  | TR(t-252,t) |
| 5 | MOM_12_1 | TWELVE_MINUS_ONE_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 252.0 | 21.0 |  | TR(t-252,t-21); all 252 sessions must be valid |
| 6 | MULTI_Z_21_63_126 | MULTI_HORIZON_RELATIVE_STRENGTH | CONTINUOUS_RANK | PRIMARY |  |  |  | equal mean of date-level within-peer winsorised z-scores |
| 7 | MULTI_Z_63_126_252 | MULTI_HORIZON_RELATIVE_STRENGTH | CONTINUOUS_RANK | PRIMARY |  |  |  | equal mean of date-level within-peer winsorised z-scores |
| 8 | ABS_POS_126 | ABSOLUTE_MOMENTUM_QUALIFICATION | BINARY_QUALIFICATION | PRIMARY | 126.0 |  |  | 1 if MOM_126 > 0 else 0 |
| 9 | ABS_POS_252 | ABSOLUTE_MOMENTUM_QUALIFICATION | BINARY_QUALIFICATION | PRIMARY | 252.0 |  |  | 1 if MOM_252 > 0 else 0 |
| 10 | ABOVE_GBP_CASH_126 | CASH_RELATIVE_QUALIFICATION | BINARY_QUALIFICATION | PRIMARY | 126.0 |  |  | 1 if MOM_126 exceeds contemporaneous 126-session A2 actual-GBP-cash return else 0 |
| 11 | ABOVE_GBP_CASH_252 | CASH_RELATIVE_QUALIFICATION | BINARY_QUALIFICATION | PRIMARY | 252.0 |  |  | 1 if MOM_252 exceeds contemporaneous 252-session A2 actual-GBP-cash return else 0 |
| 12 | TREND_MA_252 | TOTAL_RETURN_TREND_QUALIFICATION | BINARY_QUALIFICATION | PRIMARY | 252.0 |  |  | 1 if total-return wealth index exceeds its trailing 252-session simple moving average else 0 |
| 13 | RISK_ADJ_MOM_126_VOL63 | RISK_ADJUSTED_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 126.0 |  | 63.0 | MOM_126 divided by annualised 63-session realised volatility |
| 14 | RISK_ADJ_MOM_252_VOL63 | RISK_ADJUSTED_MOMENTUM | CONTINUOUS_RANK | PRIMARY | 252.0 |  | 63.0 | MOM_252 divided by annualised 63-session realised volatility |
| 15 | MOM_105 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | SECONDARY_NEIGHBOURHOOD | 105.0 |  |  | TR(t-105,t) |
| 16 | MOM_147 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | SECONDARY_NEIGHBOURHOOD | 147.0 |  |  | TR(t-147,t) |
| 17 | MOM_210 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | SECONDARY_NEIGHBOURHOOD | 210.0 |  |  | TR(t-210,t) |
| 18 | MOM_294 | SIMPLE_TOTAL_RETURN_MOMENTUM | CONTINUOUS_RANK | SECONDARY_NEIGHBOURHOOD | 294.0 |  |  | TR(t-294,t) |
| 19 | ABS_POS_210 | ABSOLUTE_MOMENTUM_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 210.0 |  |  | 1 if MOM_210 > 0 else 0 |
| 20 | ABS_POS_294 | ABSOLUTE_MOMENTUM_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 294.0 |  |  | 1 if MOM_294 > 0 else 0 |
| 21 | ABOVE_GBP_CASH_210 | CASH_RELATIVE_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 210.0 |  |  | 1 if MOM_210 exceeds contemporaneous 210-session A2 actual-GBP-cash return else 0 |
| 22 | ABOVE_GBP_CASH_294 | CASH_RELATIVE_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 294.0 |  |  | 1 if MOM_294 exceeds contemporaneous 294-session A2 actual-GBP-cash return else 0 |
| 23 | TREND_MA_210 | TOTAL_RETURN_TREND_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 210.0 |  |  | 1 if total-return wealth index exceeds its trailing 210-session simple moving average else 0 |
| 24 | TREND_MA_294 | TOTAL_RETURN_TREND_QUALIFICATION | BINARY_QUALIFICATION | SECONDARY_TRIGGERED_NEIGHBOURHOOD | 294.0 |  |  | 1 if total-return wealth index exceeds its trailing 294-session simple moving average else 0 |

## Common construction rules

- Total-return momentum compounds validated A2 GBP returns and requires a complete canonical-session window.
- `MOM_12_1` includes sessions t-251 through t-21 and excludes t-20 through t.
- Multi-horizon composites use equal weights after date-level, within-peer 5th/95th percentile winsorisation and z-scoring.
- Absolute, cash-relative and moving-average states are qualifications, not portfolio overlays.
- Risk-adjusted signals use a fixed 63-session realised-volatility denominator; the window was not optimised.
- DeepVue labels have no computational role.
