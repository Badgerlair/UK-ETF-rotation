# UKACTIVE-A4 falsification report

Both diagnostics retain the frozen monthly dates, contemporaneous eligible pool, one holding, next-session endpoint contract and frozen transaction costs. A simulated path with an unavailable endpoint is invalid rather than filled.

| Diagnostic | CAGR percentile | excess-vs-pool percentile | drawdown percentile | selected-vs-unselected percentile | valid paths |
|---|---:|---:|---:|---:|---:|
| Random selection | 96.06% | 96.06% | 96.80% | 95.97% | 5,462 |
| Rank permutation | 96.10% | 96.10% | 97.25% | 96.03% | 5,487 |

These are E2 falsification diagnostics, not proof of alpha and not independent E3 confirmation. The monthly-endpoint drawdown statistic is comparable within the simulations but is not a replacement for the daily portfolio drawdown.

Only fully valid paths enter the percentile calculation. 4,538 random-selection paths and 4,513 rank-permutation paths encountered at least one unavailable frozen endpoint and were retained as invalid, not repaired. This attrition is a material interpretive limitation; the endpoint audit records every affected month/family.
