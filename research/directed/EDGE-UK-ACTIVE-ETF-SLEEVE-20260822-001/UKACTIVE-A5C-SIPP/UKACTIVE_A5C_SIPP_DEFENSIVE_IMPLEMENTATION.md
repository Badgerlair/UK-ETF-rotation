# UKACTIVE-A5C-SIPP defensive implementation

Historical research continues to use the accepted causal GBP cash-return series. It is not rewritten with a current fund, Bank Rate, a constant return, or current ii broker interest.

## Live strategic defence — RLON

RLON is permitted prospectively as the primary strategic defensive vehicle only after the exact currently held Royal London fund name, share class, ISIN and dealing terms are supplied. No such record exists in the repository, so none has been guessed. Current state: `AWAITING_CURRENT_HOLDINGS_INPUT`.

## Live tactical defence — CSH2

- Ticker: `CSH2`
- ISIN: `LU1230136894`
- LSE/XLON trading line: GBP/GBX
- Intended use: near-term rebalance liquidity, temporarily unavailable M2 slots, execution/data/cost suspensions, and money awaiting a valid monthly decision.
- Current SIPP holding/availability: must be confirmed from the dated holdings export.

## Broker cash

Direct broker cash is limited to settlement, fees and residual balances. Prospective returns must use realised RLON, CSH2 and broker-cash returns separately. No 4% constant return is assumed.

Moving between RLON/CSH2 and risk assets creates real transaction/dealing effects. These must be recorded prospectively; historical cash is not retrofitted with those securities.
