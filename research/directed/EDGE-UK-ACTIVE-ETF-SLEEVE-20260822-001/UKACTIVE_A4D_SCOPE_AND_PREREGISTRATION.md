# UKACTIVE-A4D — scope and preregistration

Stage: `UKACTIVE-A4D`  
Run: `UKACTIVE-A4D-20260824-001`  
Title: **Multi-horizon relative momentum + leadership deterioration + portfolio breadth + rebalance frequency + cash defence**  
Mandate: **LOW FRICTION TO EXPLORE — HIGH FRICTION TO CLAIM**

## Frozen scientific contract

The economic-family identity, 27-family `INDUSTRY_PLUS_THEME` pool, dynamic signal-specific admission, corrected A2R2 endpoint chain, deterministic XLON calendar, GBP total-return accounting, `GLOBAL_DEVELOPED_WORLD`, contemporaneous equal-pool comparator, actual GBP cash, next-eligible-session execution and canonical costs are unchanged.

A4D never ranks ticker/listing/ISIN, never back-projects current eligibility, never fills prices or returns, never bridges a continuity reset, and never earns date-T return from a date-T signal. Existing A1–A5 artifacts and A5 ledgers are read-only.

## Stage A — signal

All inputs are within-pool percentile ranks of benchmark-relative returns at 21/42/63/126/252 XLON sessions.

- `M1_EQUAL_5H`: 20/20/20/20/20. This is mathematically equivalent to the already exposed A3R1/A3R2 `MH_LEVEL_EQ` and is retained as an anchor, not relabelled as new evidence.
- `M2_INTERMEDIATE_5H`: 10/15/25/30/20. These weights are frozen before A4D outcomes.
- `M3_STRUCTURAL_DETERIORATION`: structural = 40% R63 rank + 35% R126 rank + 25% R252 rank; fast = mean R21/R42 ranks; score = clip(structural + 20% max(fast−structural,0) − 35% max(structural−fast,0), 0, 1). Fast improvement can help modestly; deterioration is penalised more strongly.

Weekly date-level diagnostics use 21/42/63-session forward returns, Spearman IC, top-quintile versus pool, rank-1 versus pool and state/age conditioning. M1 is always carried as the prior-evidence anchor. At most one of M2/M3 is additionally carried: it must have positive top-quintile advantage and positive IC at two or more forward horizons; if both qualify, the larger minimum top-quintile advantage across horizons wins. This gate is developmental model selection and is reported as such.

Leadership states are diagnostic and fixed:

- `NEW_LEADERSHIP`: fast ≥ 0.80, structural ≥ 0.50, fast−structural ≥ 0.15 and 21-session score change ≥ 0.10.
- `ESTABLISHED_LEADERSHIP`: structural ≥ 0.75, fast ≥ 0.55 and RS63 > 0.
- `MATURE_DECELERATING`: structural ≥ 0.75 and either fast < 0.45, fast−structural ≤ −0.20, or 21-session score change ≤ −0.10.
- `FAILED_LEADERSHIP`: structural < 0.50 and fast < 0.50, or both RS63 and RS126 are non-positive.
- remaining valid observations are `TRANSITIONAL`.

Momentum age is the number of consecutive observations in the top quintile on the fixed weekly diagnostic clock. It cannot alter trading unless monotonic and economically meaningful evidence appears; no age rule is preregistered for A4D portfolios.

## Stage B — breadth

For each carried signal, test equal-weight TOP3 through TOP10 at MONTHLY review. Rebalance occurs only when target membership or target weights change; ordinary within-period drift is not mechanically reset. This isolates ranking turnover rather than daily equal-weight maintenance.

A viable breadth has positive net excess versus the equal-pool benchmark in both the final five years and 2020 onward. A breadth plateau requires at least two adjacent viable breadths whose final-five-year pool excess lies within three annualised percentage points of that signal's best viable breadth and whose maximum drawdown is no more than five percentage points worse. If no such adjacent region exists, A4D must say there is no stable breadth plateau.

The representative breadth is the integer middle of the widest viable adjacent region, not the single highest-CAGR cell.

## Stage C — frequency

Within the viable breadth region, compare DAILY, WEEKLY and MONTHLY using identical scores, selection, equal weighting, execution and costs. Each decision occurs after its close and any changed target executes at the first common valid endpoint one to three later XLON sessions.

The preferred frequency must retain positive final-five-year net excess versus both global and equal pool under baseline costs, remain positive versus the pool at doubled costs, and show favourable median drawdown efficiency across viable breadths. Frequency is selected on region-level behaviour, not one maximum-CAGR cell.

## Stage D — cash

Cash earns the validated GBP cash index. Apply only to the representative signal/frequency and the breadth plateau (or the fixed TOP5/TOP6 diagnostic fallback if no plateau exists).

- `CASH_0_ALWAYS_INVESTED`: no qualification.
- `CASH_1_INDIVIDUAL_ABOVE_CASH_252`: each selected rank retains its original 1/N slot only if its 252-session total return exceeds contemporaneous 252-session GBP cash return; unqualified slots are cash.
- `CASH_2_POOL_BREADTH`: use the proportion of otherwise eligible families above GBP cash at 252 sessions. At ≥60% use 100% risk; at 35–60% use 50%; below 35% use 0%.
- `CASH_3_GLOBAL_CONFIRMATION`: use 100% risk only when global-developed 252-session return exceeds GBP cash and its endpoint wealth is above its prior/current 200-session simple moving average; otherwise 100% cash.
- `CASH_4_PARSIMONIOUS_COMBINED`: apply individual qualification, then the breadth multiplier, and require global confirmation. No additional branches exist.

The preferred cash architecture must improve maximum drawdown by at least five percentage points or materially improve Calmar/Ulcer, retain positive net excess versus both benchmarks, and remain positive versus the equal pool at doubled costs. Return sacrifice, avoided drawdown, cash opportunity cost and whipsaw are reported.

## Stage E — weighting

Only after a viable breadth region exists, test on the representative architecture:

- `W0_EQUAL`;
- `W1_RANK_DECAY`, proportional to 1/rank;
- `W2_FIXED_TOP_HEAVY`: rank 1 = 30%, rank 2 = 22%, rank 3 = 16%, remaining 32% equally divided; if fewer than four holdings qualify, the available weights are normalised mechanically.

No fitted weights, leverage, shorts or volatility optimiser are allowed.

## Evidence windows and robustness

Report full history, pre-2020, 2020 onward, final five years (2021-09-01 onward), final three years (2023-08-21 onward), calendar years, and rolling 12/24/36-month excess. Serious candidates receive neighbouring-breadth, frequency, M1/M2/M3, doubled-cost, MATURE-only and leave-one-major-family-out checks.

No historical interval is untouched. Any representative forward specification is a new prospective registration only; A4D does not start it and does not amend A5.

