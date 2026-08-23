# UKACTIVE-A5 comparator definitions

All comparators begin from the same first booked execution boundary and use the authoritative A2R2 GBP total-return/cash chain.

| Comparator | Definition | Cost convention |
|---|---|---|
| `GLOBAL_DEVELOPED_WORLD` | Global developed-world economic benchmark. | Frictionless research benchmark. |
| `EQUAL_WEIGHT_INDUSTRY_THEME_POOL` | Equal weight across contemporaneously 3/6/12-signal-eligible INDUSTRY+THEME families. | Frictionless research index; membership effective after the decision close. |
| `STATIC_CORE_PLUS_EQUAL_POOL_50` | 50% global core and 50% contemporaneous equal-weight pool, monthly rebalanced. | Same 20 bp plus £3.99/actual-leg convention as the shadow models. |
| `GBP_CASH` | Validated actual GBP cash series. | No ETF or zero-return assumption. |
| `UNSELECTED_INDUSTRY_THEME_POOL` | Equal weight across eligible pool members other than rank 1. | Frictionless research diagnostic. |

The static 50/50 comparator isolates active selection value from merely combining global core with the available industry/theme basket.
