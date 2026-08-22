# Project EDGE - Qullamaggie Common Breakout First E1 Experiment Proposal

| Field | Value |
|---|---|
| Programme | `EDGE-QB-CBRP-20260811-001` |
| Experiment | `EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001` |
| Version | `0.1 - pre-outcome review proposal` |
| Date | 2026-08-11 |
| Evidence tier | `E1 - EXPLORATORY DISCOVERY` |
| Parent design | `EDGE-QB-CBRP-S0-RD-001`, version 0.3 |
| Data construction | `EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1` |
| Status | **NO RUN AUTHORITY - USER REVIEW REQUIRED** |
| Market-data source | MDM only |
| Empirical work performed | None |

## 1. Purpose

Build the Stage A leadership atlas before defining a Common Breakout setup.

Question: at a causal completed-close landmark, do higher recent absolute returns and higher point-in-time cross-sectional ranks predict a more positive forward price-return trajectory, and is any effect a broad location shift or a rare-winner/right-tail phenomenon?

This experiment does not test consolidation, contraction, a breakout event, an entry rule, stops, exits, costs, a portfolio or a strategy. It establishes the conventional-momentum comparator against which later Common Breakout components must be judged.

The experiment is exposed and adaptive. It can generate candidates but cannot validate or confirm an edge.

## 2. Hypothesis and null

Exploratory hypothesis `QBC-H01`:

For lookbacks `L in {5,10,20,40,60,120}`, the conditional forward return path varies with:

`M_L(A) = log(P_A / P_(A-L))`

and same-landmark PIT percentile rank:

`RS_L(A) = (average_rank(M_L) - 0.5) / N_L(A)`.

Ranks are ascending: rank 1 is the lowest momentum and rank `N` is the highest. Exact ties receive their arithmetic average rank. The formula intentionally maps into `(0,1)` rather than attaining either endpoint. If `N=1`, set `RS_L=0.5`, mark `SINGLETON_DENOMINATOR`, and exclude that date/horizon from cross-sectional-shape interpretation while retaining its population audit.

The shape may be monotonic, threshold-like, nonlinear, U-shaped, exhaustion-dominated or concentrated only in the extreme tail. No top-1%, top-2%, 30% advance or other published threshold is presumed.

E1 null description: after date effects, dependence, action/terminal sensitivities and contributor concentration are considered, the forward trajectory is flat/adverse or too unstable to nominate for E2.

This is not a formal confirmatory null test.

## 3. Exact population

Use only `EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1` as defined in the Stage 0 design.

At each monthly effective date `S`, retrieve full historical MDM census pages for both `active=true` and `active=false`. The primary eligible cross-section at `S` consists of the unique nonconflicting `active=true` records satisfying exactly:

- `market=stocks`;
- `locale=us`;
- `type=CS` from the dated field;
- `currency_name=usd`;
- `primary_exchange in {XNAS,XNYS,XASE}`; and
- nonblank `ticker`.

There is no top-N, price, dollar-volume, ADV, market-cap, shares, staleness or minimum-history population rule. No inferred type, name-token classification, current-constituent list, survivor filter, ticker stitching or issuer aggregation is allowed.

Excluded/unknown rows remain in the census audit with one or more reason flags. Later inactive/acquired/bankrupt/delisted listings remain eligible at earlier landmarks if they met the dated rule.

### Census capture and normalised keys

The clean MDM client is an access/pagination primitive only: it currently flattens result rows and does not retain replayable raw pages. A new EDGE-local capture wrapper must therefore persist, before normalisation:

- exact request path and redacted query parameters (never credentials);
- snapshot date, active mode and page ordinal;
- response status and request ID where present;
- complete raw response bytes or a proved lossless canonical representation;
- the redacted `next_url` chain;
- retrieval timestamp, byte length and SHA-256; and
- client/source-code hash.

The normalised census schema retains at least `snapshot_date,ticker,name,market,locale,primary_exchange,type,active,currency_name,cik,composite_figi,share_class_figi,last_updated_utc,delisted_utc,source_universe_mode`, plus request/page lineage.

Canonicalise strings only by Unicode normalisation, outer-whitespace removal and documented case normalisation. Collapse rows only when all normalised source fields are identical, while retaining every page lineage. For each `(snapshot_date,ticker)`:

1. if the same normalised identity appears in both active modes, set `ACTIVE_MODE_CONFLICT` and quarantine eligibility at that snapshot;
2. if multiple `active=true` rows disagree on `market`, `locale`, `type`, `primary_exchange`, `currency_name`, `active`, share-class FIGI or composite FIGI, set `ACTIVE_IDENTITY_CONFLICT` and quarantine;
3. otherwise define `listing_key` as `SF:<share_class_figi>` when present, else `CF:<composite_figi>`, else provisional `TK:<ticker>@<primary_exchange>` with `IDENTITY_LOW_CONFIDENCE`;
4. over the complete `[A-120,A+60]` session window, quarantine the listing-landmark if a ticker maps to multiple nonblank share-class FIGIs, one share-class FIGI maps to multiple nonblank composite FIGIs, or a provisional ticker key overlaps a conflicting identity; and
5. never bridge an absence, inactive transition or key change as a successor stitch.

Missing FIGI alone does not remove a conflict-free listing-level E1 landmark, but it triggers the low-confidence sensitivity and prohibits issuer/successor claims.

## 4. Landmark and timestamp contract

The target contains 118 effective snapshot dates: the first admitted U.S. equity session of each calendar month from 2016-07 through 2026-04 inclusive. Complete pagination is required for every included formation date. If a whole date is irretrievable, it may be disabled only before outcomes, with the reason, temporal-target change and new configuration hash recorded; incomplete pagination within an included date is `DEF-A`.

For each effective date `S`:

1. `A` is the next admitted U.S. equity session after `S`.
2. The snapshot is never used on `S` and is never backward-filled.
3. Features use exact completed sessions through close `A`.
4. The decision/measurement timestamp is post-close `A`.
5. Primary forward outcomes begin immediately after close `A` and end at close `A+h`.
6. The close-to-close quantity is a statistical conditional-price outcome, not an executable close fill.
7. Next-open entry translation is disabled in version 0.1.
8. MFE/MAE are enabled only if an E0 audit validates the regular-session high/low semantics; otherwise they are marked `NOT ESTIMABLE` for this run without blocking close-to-close outcomes.

Historical snapshot `available_at` is unknown. The one-session lag is a proposed E1 effective-date approximation pending explicit approval, labelled `PIT_EFFECTIVE_DATE_APPROX_NOT_BITEMPORAL`; it cannot support an E3 PIT claim.

## 5. Input and action basis

### Daily inputs

Read canonical MDM daily files only from 2016-01-04 through 2026-06-30. Bind every file by absolute source path, byte length and SHA-256 in the E1 entry manifest.

Consumed fields:

- `date`;
- `ticker`;
- `open` only for validation, not a v0.1 outcome;
- `high`/`low` only if path semantics pass;
- `close`;
- `volume`;
- `transactions`;
- `source_file`; and
- `ingested_at_utc` as lineage only.

VWAP is disabled. No stale fill is permitted. Create separate field-validity flags:

- `close_valid`: finite positive close;
- `open_valid`: finite positive open;
- `range_valid`: finite positive high/low with `high >= max(open,close)`, `low <= min(open,close)` and `high >= low` when the referenced open/close fields are valid; and
- `volume_valid`: finite nonnegative volume.

A close-only H01 feature or outcome requires only the exact close fields it uses. An invalid unused open/range/volume field must not remove that observation or become a hidden liquidity filter. Open, path and volume estimands require their own flags. Exact duplicates collapse with complete lineage. Conflicting ticker-date variants are quarantined for the affected fields/intervals.

### Split-consistent price basis

Primary label: `SPLIT_CONSISTENT_PRICE_RETURN_NO_DISTRIBUTIONS`.

Use the three path/hash-bound MDM split sources recorded in Stage 0. The physical action field is `execution_date`, and `split_factor = split_to / split_from`. Collapse exact duplicate actions. A ticker/execution-date may have one unique finite positive factor. Conflicting factors quarantine every feature/outcome interval crossing that date.

For an execution date `d` that is an admitted session, the transition from the previous admitted session `p` through `d` is `close(d) * split_factor(d) / close(p)`. Compose those one-session economic ratios over each feature/outcome horizon. If an execution date is not an admitted session, assign it to the first admitted session on or after `execution_date`; multiple intervening events multiply, and the mapping is logged. An action dated after the horizon never alters that horizon. Do not inherit prior readiness residual, continuity, episode-gap or price-gap thresholds. Do not auto-stitch successor symbols.

Cash distributions are not included, so this is not total return. Any later admitted total-return subset is a separately labelled sensitivity.

## 6. Formation eligibility and rank denominator

Eligibility is horizon-specific.

For lookback `L`, a population-eligible row enters the `L` feature denominator at landmark `A` only if:

- exact-session close values at `A` and `A-L` are valid;
- all split transitions needed for the ratio are resolved; and
- the identity interval does not cross a quarantined ticker/FIGI conflict.

A listing can enter `L=5` while remaining missing for `L=120`. Lack of a longer history never excludes it from a shorter-horizon denominator.

For each `(A,L)` store:

- full census count;
- primary eligible count;
- feature-valid denominator `N_L(A)`;
- each exclusion/missing reason count;
- rank ties;
- future-outcome-missing count, joined only after ranks are frozen; and
- concentration by type/exchange/identity-quality flags.

Ranks are formed before any forward-outcome availability filter. Ties receive their average rank. Never recompute ranks on complete-outcome survivors.

Because valid populations differ by lookback, version 0.1 also reports a common-support sensitivity restricted, within each landmark, to listings with valid 5/10/20/40/60/120-session features. Cross-lookback differences are not interpreted as horizon effects unless they persist on this common support; otherwise they are labelled composition-sensitive. The horizon-specific populations remain primary for estimating each horizon without imposing a 120-session listing-age filter.

## 7. Baseline feature atlas

For each `L in {5,10,20,40,60,120}`:

1. raw split-consistent simple return;
2. log return `M_L`;
3. same-date percentile rank `RS_L`;
4. horizon-specific missingness/quality flags; and
5. no outcome-derived feature.

### Baseline descriptive views

For `RS_L`, report the user-proposed shape bins:

- 0-50%;
- 50-70%;
- 70-80%;
- 80-90%;
- 90-95%;
- 95-98%;
- 98-99%; and
- 99-100%.

Also show equal-frequency deciles so conclusions do not depend on tail-focused bin widths.

For absolute momentum, show pooled feature-quantile deciles and a direct return-axis curve. Quantile cut points are generated from formation features before outcomes are joined and are stored in the manifest.

### Baseline continuous views

- separate low-degree restricted cubic splines for `M_L` and `RS_L`;
- a joint `M_L + RS_L` model;
- date-fixed-effect/cross-sectionally neutral versions; and
- one parsimonious multihorizon additive diagnostic using 20/60/120-session features without automated selection.

Spline knot positions are fixed from predictor-only pooled quantiles before outcome access and logged. Version 0.1 uses five predictor quantiles `{0.05, 0.275, 0.50, 0.725, 0.95}`. Tail-focused empirical-bin plots remain descriptive and must show cell counts/effective dates.

No single “best” model is selected in the baseline wave.

## 8. Outcomes

For `h in {1,2,3,5,10,20,40,60}`:

`R_h(A) = P_(A+h) / P_A - 1`

on the split-consistent price basis.

The complete eight-horizon trajectory is primary. The 20-session outcome is the interpretive anchor selected before outcome access, but no favorable horizon may replace the complete path.

Report both:

- absolute price return; and
- same-date cross-sectionally neutral return, subtracting the scenario-consistent equal-weight return of the eligible feature denominator with observable/scenario outcomes.

SPY/QQQ-relative returns are secondary and disabled unless those MDM benchmark series pass separate input/clock admission.

If high/low semantics pass E0, calculate MFE/MAE from sessions `A+1` through `A+h` relative to `P_A`, carrying split factors onto the `A` share basis. Do not infer within-day order. If semantics fail, close-path results proceed and MFE/MAE are `NOT ESTIMABLE`.

## 9. Terminal and missing-path treatment

Every affected landmark remains in population accounting and rank formation. Report frequency and concentration by date, lookback, rank bin, exchange, identity quality and horizon.

Before outcomes, freeze this missing-path classifier and apply it mechanically by listing key and admitted session:

- `COMPLETE_OR_ENDPOINT_OBSERVED`: required endpoint close exists on the same listing key; internal missing bars are separately flagged and make only affected path/MFE/MAE metrics incomplete;
- `INTERMITTENT_BAR_GAP`: a required session is missing but the same listing key later reappears within the maximum 60-session window; no terminal scenario begins, and missing path portions remain missing;
- `VALID_MDM_TERMINAL`: an admitted MDM lifecycle/action record supplies a terminal timestamp and economic consideration;
- `DATED_INACTIVE_OR_DELISTED_NO_ECONOMICS`: dated MDM inactive/delisted evidence occurs inside the horizon but no validated consideration exists;
- `UNEXPLAINED_CESSATION`: after the last valid same-key bar, no later same-key bar exists through `A+60`, and no valid terminal economics or identity boundary explains the cessation;
- `IDENTITY_OR_SUCCESSOR_AMBIGUITY`: the key changes/conflicts or a possible successor is unsupported; this is `DEF-A` quarantine, not a terminal scenario;
- `ACTION_CONFLICT`: the interval crosses an unresolved split/action conflict; this is `DEF-A` quarantine; and
- `RIGHT_BOUNDARY_CENSORING`: the admitted MDM/session input ends before a required horizon; the formation date/horizon is disabled before outcome access, not assigned a loss/flat scenario.

Scenario start is deterministic: the admitted terminal timestamp for `VALID_MDM_TERMINAL`; the first admitted session on or after dated inactive/delisted evidence for `DATED_INACTIVE_OR_DELISTED_NO_ECONOMICS`; and the first required session after the last valid same-key bar for `UNEXPLAINED_CESSATION`. Store the class, evidence fields, last valid session, scenario start and classification code. Halt/suspension/provider-gap ambiguity remains visible as `UNEXPLAINED_CESSATION`; it is never silently called a true delisting.

Run these explicitly labelled E1 scenarios:

1. **Observed valid MDM terminal economics**, where available.
2. **Severe-loss/full-loss stress:** set post-terminal value to zero at the first unresolved terminal transition. This is an assumption, not vendor truth or a mathematical lower bound.
3. **Last-valid/flat stress:** carry the last valid observed split-consistent value through the remaining horizon. This is an assumption, not vendor truth or a bound.
4. **Complete-path-only diagnostic:** omit unresolved paths only from this diagnostic table, never from census/affected-case reporting or the headline sensitivity comparison.
5. **Censoring/identified-set analysis:** only if its assumptions and mathematical validity are documented.

For truncated high/low paths, report only observed MFE/MAE and observation length. Do not invent later bars.

If reasonable terminal scenarios reverse direction or economic materiality, the result is `SENSITIVITY-DEPENDENT / E1 UNRESOLVED`. Version 0.1 cannot make an unconditional population-expectancy claim while terminal economics remain incomplete.

## 10. Required distribution and right-tail outputs

For every `(feature view, h, scenario, weighting)` cell, apply the pre-outcome support rules in Section 11 and report:

- count, number of dates and effective listing contributors;
- mean, median, standard deviation, win rate;
- average positive/negative return and payoff ratio;
- skewness and kurtosis;
- P25/P50/P75/P90/P95/P99, minimum and maximum;
- MFE/MAE/time-to-extreme where enabled;
- top 1%, 5%, 10% and 20% contribution to positive weighted return;
- top 1%, 5%, 10% and 20% contribution to signed weighted return;
- diagnostic-only expectancy after deleting each top fraction;
- tail HHI/effective contributor count;
- distinct listing/date/nonadjacent-period contributors; and
- leave-largest-outcome, listing, date-block and calendar-period results.

For each weighting scheme separately, normalise weights to one and sort by raw return descending. Top 1/5/10/20% means cumulative analysis weight, not row count; fractionally allocate a boundary observation when needed. Positive contribution has denominator `sum(w*max(R,0))`; signed contribution has denominator `sum(w*R)`. A denominator with absolute value at most `1e-12 * max(1,sum(w*abs(R)))` is reported `UNDEFINED_NEAR_ZERO_DENOMINATOR`. The deletion counterfactual removes the same cumulative weight, including fractional boundary weight, and renormalises the remainder to one. Use deterministic `(return,listing_key,landmark_date)` ordering and report a boundary tie-range sensitivity for equal returns.

The untrimmed distribution is always primary. An extreme value is removed only if an outcome-blind data-validity audit proves it erroneous; that correction and original observation remain in lineage.

## 11. Weighting and dependence

Primary estimate: equal weight to each landmark date, with equal weight to valid listings inside that date.

Mandatory secondary estimate: equal weight to every listing-landmark.

Exploratory uncertainty/stability diagnostics:

- listing/security-episode clustering where identity supports it;
- landmark-date clustering;
- two-way listing/date clustering where numerically supported;
- chronological block bootstrap with block length at least 60 admitted sessions;
- fixed calendar-quarter and calendar-year estimates; and
- leave-year-out/leave-quarter-block-out sensitivity.

Issuer clustering is `NOT ESTIMABLE` unless reliable issuer identity is separately qualified. Row-i.i.d. standard errors must not be presented as sufficient.

Pre-outcome support rules:

- always list cell counts, dates, weights and missingness, even when support is low;
- a curve/model cell is interpretable only with at least 24 distinct monthly landmarks, 500 listing-landmarks and Kish effective sample size `1/sum(w^2) >= 200` after cell-normalised weights;
- the 99-100% bin additionally requires at least 100 listing-landmarks across at least 24 dates and no one date above 20% of its weight;
- cells below a threshold are labelled `LOW_SUPPORT / NOT ELIGIBLE FOR E2 NOMINATION`, not silently removed; and
- these thresholds affect interpretability, not whether the attempt enters the search ledger/FDR classification.

The chronological sensitivity is a circular moving-block bootstrap on the admitted daily-session index with 60-session blocks, 2,000 replicates and deterministic seed `20260811`. Resample whole date cross-sections by sampled blocks until the original number of monthly landmarks is reached, then truncate. Report numbers of landmark-date and listing-key clusters, cluster-size concentration and bootstrap effective replicate count. Two-way cluster diagnostics require at least 30 dates and 50 listing keys; otherwise report the block bootstrap only.

Any E1 nomination from this experiment is explicitly limited to the monthly activation-landmark estimand. Generalisation to arbitrary daily landmarks requires a separate, outcome-blind snapshot carry-forward qualification and experiment ID.

## 12. Adaptive waves and search ledger

The baseline atlas in Sections 7-11 is frozen before first market-outcome access. After it is inspected, E1 may adapt.

Every adaptive wave receives a child identifier:

`EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001-WNNN`

and records:

- timestamp and analyst/agent;
- scientific rationale and parent result;
- exact specification/transform/bin/knot/subgroup/interaction;
- population, sample and horizons;
- code/config/input/output hashes;
- complete result, including null/failure;
- deficiency/sensitivity status;
- disposition and reason for continuation/abandonment; and
- whether it is eligible for later simplification/freezing.

Allowed adaptive work includes alternative smoothers, tail resolution, shape-falsification views, robust transformations and theory-led interactions. Unrestricted brute-force trees, thousands of grids, best-equity-curve selection and silent replacement of failed specifications are prohibited.

## 13. Multiplicity

E1 FDR is diagnostic only.

After each result-bearing wave, report cumulative Benjamini-Yekutieli diagnostics over all recorded, valid scalar inferential contrasts that produce a p-value. The decision-unit key is `(programme,experiment,wave,hypothesis,feature/lookback,outcome_horizon,model/contrast,terminal_scenario,weighting,subgroup)`. Primary and secondary inferential contrasts, recovery specifications viewed after outcomes, and scenario/subgroup tests each enter as distinct units. A unit cannot be removed because its result is inconvenient.

Purely descriptive distribution cells, plots and metrics without a predeclared scalar inferential test are ledgered as `NONINFERENTIAL_DESCRIPTIVE` and do not enter BY. Invalid or low-support tests receive no p-value, remain ledgered with `INVALID` or `NONINFERENTIAL_LOW_SUPPORT`, and do not enter BY. Engineering reruns that never produced a valid viewed result are recorded but are not result-bearing units. Preserve and grow the inferential denominator; never reset it.

- `q > 0.10` cannot veto a scientifically plausible exploratory specification.
- `q <= 0.10` cannot validate or confirm it.
- FDR does not define a discovery budget and transfers no alpha to E3.
- Candidate decisions prioritise magnitude, shape, stability, recurrence, concentration, contributor diversity and robustness.

Any E2/E3 candidate is later reduced to a simple separately frozen specification. Strong finite-family multiplicity control begins at E3, not here.

## 14. E0 tests required before outcome access

Synthetic/null/canary tests must demonstrate:

1. full pagination and duplicate-page detection;
2. exact `S -> A` activation and no same-day/backfill membership;
3. exact-session `A-L` feature alignment;
4. feature ranks formed before outcome missingness;
5. tie handling and denominator accounting;
6. split factor composition for forward/reverse splits;
7. conflict quarantine and no successor stitch;
8. horizon indexing for 1/2/3/5/10/20/40/60;
9. no future outcome in any feature;
10. same-date neutral-return arithmetic;
11. terminal scenario arithmetic and affected-case retention;
12. MFE/MAE/path arithmetic where enabled;
13. top-tail contribution and deletion diagnostics;
14. primary/secondary weighting;
15. clustering/bootstrap input construction;
16. deterministic sharding/merge and stable hashes; and
17. append-only ledger refusal to overwrite an existing run ID.

## 15. Category A entry gates

The first market-outcome run is prohibited until all are closed or the affected output is disabled:

1. **Immutable MDM input release:** every raw census page and daily/action file is path/byte/hash bound; replay produces identical inputs.
2. **Population validity:** active/inactive pagination is complete for every included formation date; dated type/exchange/currency conflicts are audited; no current/survivor or prior readiness filter enters eligibility. An irretrievable whole date can be disabled only outcome-blind with a narrowed target/config hash; a partial included census is invalid.
3. **PIT clock:** the user/reviewer accepts the one-session-lagged effective-date approximation for E1 and no actual inseparable future-derived membership field is found.
4. **Primary clock/data:** daily date/close alignment is valid for close-to-close outcomes. Next-open and high/low path outputs remain disabled unless their stronger semantics pass.
5. **Identity:** no unsupported stitch; intervals with material ticker/FIGI conflicts are quarantined and counted.
6. **Corporate actions:** exact split duplicates reconciled; conflicts quarantined; included feature/outcome ratios are not obviously split contaminated.
7. **Daily data conflicts:** exact duplicates collapse; conflicting variants are quarantined; central predictor/outcome fields are sufficiently present.
8. **Missing-path classification:** the frozen taxonomy, evidence fields, transition timestamps and scenario-start rules in Section 9 pass E0 tests; temporary gaps, right censoring, identity/action conflicts and unresolved cessation cannot be conflated.
9. **Governance:** exposure/search ledger is open; E0 tests pass; exact design/spec/code/config/environment/input hashes and run ID are recorded; written user run authority is obtained.

Terminal incompleteness is a `DEF-B` sensitivity for this E1 atlas unless it renders a particular horizon/estimand uninterpretable. It is not silently deleted and does not become a blanket block. An unconditional population-edge claim remains prohibited.

## 16. E1 decision rules

`GO - NOMINATE H01 FOR E2 (MONTHLY ACTIVATION-LANDMARK ESTIMAND ONLY)` when:

- no central Category A defect remains;
- an interpretable location or upper-tail shift is directionally coherent across the trajectory;
- it recurs across multiple nonadjacent dates/periods and independent listings;
- it is not wholly reversed by reasonable action/terminal sensitivities; and
- its magnitude is potentially economically meaningful.

FDR significance is not required.

`CONTINUE E1` when a plausible observation is shape-, period-, contributor- or sensitivity-dependent and a targeted logged refinement can clarify it.

`NO-GO FOR H01 E2 NOMINATION` when a valid atlas is consistently flat/adverse or economically negligible across plausible forms and periods. This is not a confirmed null.

`INVALID / DEF-A` when central population, clock, identity, action or outcome integrity fails.

H01 non-nomination does not prohibit separate E1 consolidation/contraction/expansion studies or the theory-led core conjunction. It does determine whether any later candidate is distinct from conventional momentum.

## 17. Output layout after future authorisation

All future artifacts remain inside:

`research/directed/EDGE-QB-CBRP-20260811-001/`

Proposed subdirectories:

- `governance/`
- `e1_data/raw_census_pages/`
- `e1_data/manifests/`
- `e1_data/quality/`
- `e0_validation/`
- `search_ledger/`
- `experiments/EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001/specification/`
- `experiments/EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001/outputs/`
- `experiments/EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001/review/`

No directory is an authority by itself. Every result must bind exact inputs, code/config/environment and outputs.

## 18. Current decision

- Proposal documentation: complete for user review.
- E0/readiness preparation: `GO` after approval of Stage 0 v0.3.
- First E1 outcome access: `CONDITIONAL GO / NOT YET AUTHORISED`.
- Empirical run performed: **No**.
- Next action if approved: materialise the outcome-blind minimum entry pack and return its Category A closure report before requesting run authority.
