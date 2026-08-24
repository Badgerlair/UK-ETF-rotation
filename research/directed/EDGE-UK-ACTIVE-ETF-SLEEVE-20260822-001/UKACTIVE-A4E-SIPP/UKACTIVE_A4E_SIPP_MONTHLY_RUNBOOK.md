# UKACTIVE-A4E-SIPP monthly runbook

## Whole-SIPP rule

Selected strategy: `GLOBAL_CASH_75_25`.

1. After the final valid XLON close of each calendar month, validate the A2R2 calendar/data cutoff and current instrument status.
2. For the selected fixed fallback, calculate current sleeve values and set SWDA to 75% and ii SIPP GBP cash to 25% of total portfolio value.
3. Record the decision before the next eligible XLON close is available.
4. Execute hypothetically/operationally at the first valid next XLON session, within three sessions; never use the signal close.
5. If SWDA is unavailable, cancel the affected purchase and hold GBP cash. Do not choose a discretionary substitute.
6. Charge/record actual commission, spread, platform, TER and any cash-rate change. Never infer historical availability from the current account.
7. Reconcile positions, cash, costs, signal timestamp and input hashes. No automatic broker order is authorised.

## Rotation shadow

Continue `M2_BASE | TOP7 | MONTHLY | CASH1 | EQUAL` in shadow only. Rank economic families, not listings. A slot qualifies only when its accepted 252-session total return exceeds contemporaneous GBP-cash 252-session return. An unavailable preferred and predeclared alternate means cash, not substitution.
