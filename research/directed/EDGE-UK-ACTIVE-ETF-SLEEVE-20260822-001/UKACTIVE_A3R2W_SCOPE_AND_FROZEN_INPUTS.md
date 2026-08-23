# UKACTIVE-A3R2W scope and frozen inputs

Frozen at: 2026-08-23T07:50:03+00:00  
Frozen from completed A3R2S decision: `911b178ae18215ee02cae504eb279f634580f1f061591a55ed7283247b4f6859`

## Authorisation

A3R2S authorised A3R2W because at least one combination passed the registered 8-of-12 developmental gate. This is a gated research comparison, not a strategy confirmation.

## Frozen architecture

- Pool: `INDUSTRY_PLUS_THEME`
- Signal: `MH_LEVEL_3_6_12_REFERENCE`
- Cadence: `MONTHLY`
- Selection counts: `TOP_1`, `TOP_2`, `TOP_3`
- Windows: final five years primary; final three years and full history context
- Costs: 20 bp one way + £3.99 per executed trade leg on £250,000, with applicable 0.75% non-GBP preferred-line FX; 10/20/40 bp and £100k/£250k/£500k sensitivities
- Methods: `EQUAL`, `RANK_DECAY`, `SCORE_PROPORTIONAL_CAPPED`, `INVERSE_VOLATILITY_CAPPED`, `SIGNAL_X_INVERSE_VOLATILITY`
- Multiple-position cap: 50%; a single selected exposure may be 100%
- All methods rebalance to their target weights on the registered monthly review schedule so the weighting comparison is like-for-like. Signal forms after close; execution is next eligible XLON session within the existing three-session rule.

TOP_1 is retained as a parity control: every weighting method must produce the same target before costs. TOP_2 and TOP_3 provide the informative weighting comparison.

No weighting method, cap, signal, pool, count, cadence, or cost was selected after observing A3R2W results. The choice of this family reflects the completed A3R2S gate and neighbourhood coherence, not maximum CAGR alone.
