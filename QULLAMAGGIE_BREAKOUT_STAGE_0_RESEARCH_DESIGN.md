# Project EDGE - Qullamaggie Common Breakout Stage 0 Research Design

| Field | Value |
|---|---|
| Programme identifier | `EDGE-QB-CBRP-20260811-001` |
| Document identifier | `EDGE-QB-CBRP-S0-RD-001` |
| Version | `0.3 - proportional E0-E3 evidence-architecture review candidate` |
| Date | 2026-08-11 |
| Parent document | Version 0.2, 89,411 bytes, SHA-256 `99DF36C40DCBBD39BC60DDCAFC91D03A4951662002CCB9A57E04E3224FAC959A` |
| Programme-local amendment | `EDGE-QB-CBRP-GOV-AMD-001`, user-authorised 2026-08-11 |
| Scientific status | **DESIGN ONLY - NO EMPIRICAL RESULT AND NO VALIDATED EDGE** |
| E0 status | **PROPOSED GO AFTER EXACT-BYTE USER APPROVAL - engineering, manifests, synthetic/null/canary validation** |
| E1 readiness status | **PROPOSED GO AFTER EXACT-BYTE USER APPROVAL - construct and audit the minimum entry pack** |
| E1 market-outcome status | **CONDITIONAL GO - NO OUTCOME ACCESS UNTIL THE CONDITIONS IN SECTIONS 17-18 ARE CLOSED AND THE USER AUTHORISES THE FIRST RUN** |
| E2 status | **NO-GO pending estimand-specific qualification** |
| E3/confirmation/production status | **NO-GO** |
| Research subject | Qullamaggie / Kristjan Kullamagi **Common Breakout**, not Episodic Pivot |
| Sole authorised market-data source | Market Data Manager (MDM) |
| Required work location | `D:\codex\equity_quant_research_platform` |

## Stage 0 decision

The active repository was resolved before this revision and confirmed as exactly:

`D:\codex\equity_quant_research_platform`

All programme specifications, manifests, ledgers, evidence, outputs and findings must remain within that repository. MDM may be read as the authorised source; materialised programme artifacts must be written only inside the repository.

The repository contains no `.git` directory. For E1 this is `DEF-D`: exact hashes of the design, code, configuration, environment, MDM input inventory and outputs can provide reproducibility for exploratory work. Missing Git metadata does not itself invalidate an E1 estimand. Canonical version provenance remains a material E3 release requirement.

This revision used only architecture/governance inspection, MDM code and capability metadata, inventories, schemas, and small non-outcome samples. No research outcome panel, signal, forward return, feature-return relation, statistical test, parameter search, backtest or production experiment was run. Frozen Project EDGE foundation documents were not modified.

The resulting decision is tiered:

1. **E0 and E1 readiness are PROPOSED GO AFTER EXACT-BYTE USER APPROVAL.** Once the user approves this version and hash, the programme may build a programme-specific, outcome-blind, hash-bound exploratory data construction and validate it on synthetic/null/canary cases.
2. **E1 market-outcome access is CONDITIONAL GO.** It becomes GO only after the exact population, inputs, timestamps, action treatment, deficiencies and ledger are materialised in the minimum entry pack; all claim-relevant `DEF-A` defects are closed or the affected estimand is removed; and the user approves the proposed first experiment.
3. **E2 is NO-GO.** Every E2 claim requires a separate estimand-specific data-qualification decision.
4. **E3, confirmation and production are NO-GO.** They retain exact freeze, independent review, strong multiplicity control, authorised terminal read and untouched/prospective evidence requirements.

`GO` at E1 means permission to learn. It is not evidence that a hypothesis is true.

## Programme-local proportional evidence amendment

`EDGE-QB-CBRP-GOV-AMD-001` applies only to this directed programme. It does not amend any frozen Foundation document, resume the autonomous Project EDGE programme, consume or reset another programme's error budget, or convert exposed history into untouched evidence. It governs how existing controls are applied proportionately to E0-E3 here.

### Evidence levels

| Level | Permitted evidence and use | Claim ceiling |
|---|---|---|
| `E0 - ENGINEERING` | Synthetic, null and canary data; schema, clock, rank, path, ledger and deterministic-build tests | No empirical market inference |
| `E1 - EXPLORATORY DISCOVERY` | Adaptive analysis of the best available MDM/PIT history, with complete exposure/search logging and disclosed limitations | May identify observations, shapes, thresholds, interactions, concentration and candidates; cannot validate or confirm an edge |
| `E2 - DEVELOPMENTAL SCIENTIFIC EVIDENCE` | Outcome-exposed data sufficiently PIT-valid, survivorship-aware and action-consistent for the stated estimand; dependence-aware inference and robustness | May developmentally corroborate a candidate; remains exposed and cannot confirm |
| `E3 - CONFIRMATORY EVIDENCE` | Frozen specification, population, clock, outcomes and tests; formal multiplicity; strongest genuinely independent or prospective evidence; no outcome-driven alteration | Only E3 may formally confirm a Project EDGE phenomenon |

Historical exposure cannot be reset by changing identifiers, code or population labels. E1/E2 findings remain developmental forever.

### Estimand-specific deficiency classes

Use `DEF-A` through `DEF-D` to avoid confusion with research Stages A-D.

| Class | Meaning | E1 consequence |
|---|---|---|
| `DEF-A - INVALID MEASUREMENT` | A credible mechanism makes the affected measurement causally or numerically invalid | Automatic blocker for that affected E1 estimand until corrected, quarantined or removed |
| `DEF-B - MEASURABLE POTENTIAL BIAS` | Bias is plausible and material but can be characterised by registered sensitivity/scenario analysis | E1 may proceed with full disclosure; sensitivity dependence limits interpretation |
| `DEF-C - INTERPRETATION LIMIT` | Data cannot support a dimension or population claim, while another narrower estimand remains measurable | Narrow the claim; mark the unavailable dimension `NOT ESTIMABLE` |
| `DEF-D - INFRASTRUCTURE/GOVERNANCE LIMIT WITHOUT MATERIAL ESTIMAND EFFECT` | Reproducibility or platform debt does not materially alter the E1 measurement | Record and remediate proportionately; do not block E1 |

Classification is per field, clock, horizon and estimand, not a blanket label for a dataset. Each deficiency record must contain evidence, affected estimand, direction and likely magnitude where knowable, class, mitigation, residual limitation, owner, reviewer and disposition.

## Absolute controls retained at every evidence level

The amendment does not relax the following:

1. MDM is the sole authorised market-data source.
2. Programme artifacts remain inside the active repository.
3. No data, code, findings, filters, thresholds, preferred specifications or assumptions may be imported from Project ICT, Forex Research Engine, Futures Research Engine, external backtest engines, unrelated Project EDGE studies, survivor-only lists, or present-day constituents applied retrospectively.
4. No lookahead, future-derived feature, causal timestamp violation, current-survivor reconstruction, unsupported ticker/successor stitch, or knowingly split-contaminated return is permitted.
5. Failed, acquired, bankrupt, delisted and unresolved-terminal cases may not be silently removed or treated as benign survivors.
6. Genuine positive-tail observations remain in the primary distribution. Winsorisation/trimming is diagnostic only.
7. Every result-bearing E1 attempt, including failures, abandoned branches and recovery runs, enters an append-only search/exposure ledger.
8. E1/E2 results and exposed dates may never be relabelled as confirmation. An untouched E3 sample may not be optimised upon.
9. Common Breakout and Episodic Pivot remain separate. A prior EP is a later conditional lifecycle covariate only.
10. Daily scientific validation precedes intraday Stage N; entry validation precedes Stage O; validated entry/risk semantics precede Stage P.
11. No strategy construction, portfolio optimisation, live execution, production deployment or formal capacity claim is authorised by this design.

## Read-only platform, MDM and exposure review

### Current Project EDGE architecture

The repository contains a strict production-oriented `src/edge_mdm/` boundary for identity/lifecycle, sessions, daily observations, corporate actions, terminal outcomes, PIT membership, immutable releases, replay, quarantine and review. Its five-table release is retained for E3 and for any E2 estimand that genuinely requires it. It is not a hidden prerequisite for every E1 measurement.

The platform does not yet provide a reusable Qullamaggie feature registry, multi-horizon path store, append-only E1 search service, dependence-aware inference engine or broad historical cost engine. These are E0/E1 engineering tasks, not reasons to prohibit discovery.

### MDM capability and practical construction review

The canonical MDM checkout is `D:\codex\market_data_manager`, code HEAD `e7c9b63b2a05b7b356bc3af044ed756b4acf57a7`. It is materially dirty and its data files are not commit-addressed, so every consumed file must be path/byte/SHA-256 bound.

A clean MDM readiness worktree exists at `D:\codex\market_data_manager_leadership_contraction_readiness`, HEAD `a5de2529cae2288f1ef531d8b4ddf7c9cc412e34`. It demonstrates a working historical PIT pagination client. That client flattens result rows and does not preserve replayable raw response pages or the complete cursor/request chain. A new EDGE-local lossless capture wrapper is therefore required before E1 construction. The generated readiness outputs are ignored by Git and are not programme evidence.

The current physical daily inventory observed on 2026-08-11 contains 4,850 partitions from 2007-05-01 through 2026-08-10. Minute data are physically available from 2016, but are not needed for the first E1 study. The direct VIX route is entitlement-blocked. SPY/QQQ are available through MDM as auxiliary benchmark series, subject to separate admission.

The existing readiness CSV named `pit_all_liquidity_ranked_tickers_monthly.csv` is not a broad census suitable for the primary E1 population. Its builder already requires valid bars, positive close and median dollar volume, and bounded price staleness; related outputs add price, liquidity and top-N rules. The adjusted panel also inherits prior episode and continuity thresholds. None of those filters, thresholds, episode rules, findings or preferred specifications will enter the primary construction.

The readiness worktree may supply only independently reviewed MDM access/schema-normalisation primitives. The first E1 population will be re-derived from newly retained raw historical MDM census pages. This satisfies the user clarification: the longer-history construction is usable only after its population, inputs and timestamp semantics are documented, and no prior research population/filter/finding is inherited merely because it was previously used.

Practical MDM limitations relevant to later stages are:

- daily OHLCV exists but exact regular-session aggregation/open/close semantics need validation for execution-clock claims;
- monthly historical PIT calls provide effective-date snapshots but not original historical `available_at` timestamps;
- stable issuer/listing/successor identity is incomplete;
- split data exist in three overlapping files; cash distributions and validated terminal economics are incomplete;
- sector/industry proxies are not admitted for this programme;
- market cap, shares and turnover are not reliable enough for primary strata;
- historical quotes are targeted/sparse and not representative of the broad population; and
- minute bars cannot resolve within-minute high/low order, auctions, halts or queue position.

These limitations are classified by estimand in Section 18. They do not create a blanket E1 prohibition.

### Prior exposure ancestry and quarantine

Prior Qullamaggie artifacts are search-history exposure only:

| Artifact | Overlap | Treatment |
|---|---|---|
| `EDGE-QULLAMAGGIE-UDRP-20260809-001` H1-H6 | Leadership, impulse, consolidation, contraction, volume, moving averages | Exposed ancestry only; no result, threshold, code choice or claim inheritance |
| UDRP H7 | Breakout transition | Quarantined: the located specification is draft/not frozen and forbids outcome access, yet a result exists; no matching ledger entry was located |
| UDRP H8 | Participation | Quarantined: result located without a matching pre-outcome specification/review or ledger entry |
| UDRP EP1-EP10 | Episodic Pivot | Separate phenomenon; excluded from core Common Breakout work |
| `EDGE-QULLAMAGGIE-DVP-001` | Composite Breakout + EP documentary replication | Firewalled; no decomposition or scientific inheritance |
| Other Project EDGE or external collisions | Possible conceptual overlap | Exposure metadata only; no input, control, prior or preferred specification |

The entire historical development interval is outcome-exposed and can be used only at E1/E2. Existing exposure must be imported into the new ledger before market-outcome access.

---

## 1. Precise scientific objective

Determine whether an equity-market continuation phenomenon exists in which an already strong listing exhibits a substantial prior advance, then retained-strength consolidation and volatility contraction, followed by renewed level/range expansion, and determine which measurable components contain independent predictive information.

The programme estimates conditional forward-return distributions and paths, not a trading-system CAGR:

`E[R(t,t+h) | causally available features at t]`

and incremental contrasts between scientifically comparable states. The core questions are whether:

- leadership predicts continuation;
- impulse adds information beyond conventional momentum;
- consolidation improves outcomes relative to equally strong leaders that do not rest;
- volatility contraction and final tightness add information;
- structural retention, moving averages and volume are independent predictors or descriptive proxies;
- a level break and/or range expansion adds information beyond the pre-breakout state;
- effects vary by regime, peer leadership and liquidity;
- repeated setups change through a listing-level trend episode;
- economic value is concentrated in rare extreme winners; and
- a candidate survives realistic implementation analysis and later E3 confirmation.

The valid conclusions include no phenomenon, conventional momentum only, a partial contraction/expansion phenomenon, regime-limited/tail-dependent evidence, data-sensitive uncertainty, or a simpler measurable effect than the published heuristic.

## 2. Research hypotheses

These are research questions, not claims. E1 may examine continuous shapes and scientifically plausible interactions adaptively, with complete logging.

| ID | Stage | Hypothesis |
|---|---|---|
| `QBC-H01` | A | Recent absolute momentum and PIT cross-sectional relative-strength rank predict the forward return path; the shape may be monotonic, threshold-like, U-shaped, extreme-tail-only or absent. |
| `QBC-H02` | B | Prior-impulse magnitude, duration and velocity add information beyond leadership; extreme extension may predict exhaustion. |
| `QBC-H03` | C | Among comparable leaders, a measurable consolidation improves the subsequent distribution relative to no consolidation. |
| `QBC-H04` | D | Directional volatility contraction adds information beyond leadership, impulse, duration, depth and proximity to highs. |
| `QBC-H05` | E | Final 3/5-session tightness adds information beyond whole-base contraction. |
| `QBC-H06` | F | Robust structural-retention measures, including lower-envelope slope and shallow downside excursions, add information beyond A-E. |
| `QBC-H07` | G | SMA10/SMA20/SMA50 position, ordering and slope add information beyond drift, pullback depth and contraction. |
| `QBC-H08` | H | An objective level breakout adds information beyond the pre-breakout leader/base state; range expansion adds more than crossing alone. |
| `QBC-H08X` | Core conjunction | Leadership x consolidation x contraction x breakout/range expansion may contain information even where one marginal feature is weak. |
| `QBC-H09` | I | Causally available base/breakout volume adds discrimination beyond price state and range expansion. |
| `QBC-H10` | J | Results vary by market state; matured success/failure of other comparable leaders adds regime information beyond SPY/QQQ trend. |
| `QBC-H11` | K | Strong stock plus strong PIT peer/industry state differs from strong stock plus weak peer/industry state. |
| `QBC-H12` | L | Gross effects and opportunity distributions vary by contemporaneous price/share volume/dollar volume, separately from capacity. |
| `QBC-H13` | M | Continuous base geometry may reveal reproducible descriptive families; any clusters remain exploratory until separately frozen. |
| `QBC-H14` | Repeated setups | Breakout ordinal within a listing-level trend episode has stable, increasing or declining expectancy. |
| `QBC-H15` | Tail | Extreme positive outcomes recur across independent listings/dates/regimes and may be predictable ex ante from setup quality. |
| `QBC-H16` | Integrated daily phenotype | A simple daily Common Breakout phenotype built from developmentally useful components adds information beyond conventional momentum. |
| `QBC-H17` | EP lifecycle extension | A prior EP/major-gap state predicts later Common Breakout outcomes, without defining the core population. Deferred. |
| `QBC-H18` | N | Completed-bar intraday confirmation improves failure avoidance, stop distance or capital efficiency beyond a validated daily event. Deferred. |
| `QBC-H19` | O | Failure timing, MAE/MFE and breakout-day/prior-day/ATR/structural risk references discriminate successful and failed entries. Deferred. |
| `QBC-H20` | P | The validated entry phenomenon is sufficiently positively skewed that partial harvesting plus trend retention monetises it better than simple fixed horizons. Deferred. |

## 3. Null hypotheses

For every feature or interaction, the operative null is no economically material, stable, recurrent change in the conditional forward-return distribution after the relevant parent state and dependence are accounted for.

Specific nulls include:

- leadership has a flat/adverse conditional trajectory;
- impulse magnitude/velocity adds nothing or excessive extension only exhausts;
- consolidation does not improve leader outcomes;
- volatility contraction/final tightness/retention/moving averages add no incremental information;
- crossing a high adds nothing beyond the pre-breakout state;
- range expansion and volume add no incremental discrimination;
- regime/peer/liquidity differences are absent or non-recurrent;
- repeated setup order has no stable relation;
- extreme winners do not recur across independent contributors or cannot be distinguished ex ante; and
- any apparent integrated effect is explained by conventional momentum, bias, dependence, one period or a few observations.

At E1 these are not confirmatory tests. A flat E1 atlas is reported as `NO PLAUSIBLE SIGNAL OBSERVED`, not a confirmed null.

## 4. Population definition

### Conceptual target

U.S.-locale, USD, exchange-listed common-stock listings that were present and active in the contemporaneous MDM historical census. The E1 estimand is listing/security-level price continuation. It is not an issuer, portfolio, total-return, institutional-capacity or all-operating-company claim.

### Exact proposed first E1 operational population

Construction identifier: `EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1`.

For each monthly effective snapshot `S`, retain the complete raw MDM `active=true` and `active=false` paginated responses. Primary eligibility at `S` requires exactly one nonconflicting row with:

- `market = stocks`;
- `locale = us`;
- `active = true`;
- `type = CS` from the dated vendor field;
- `currency_name = usd`;
- `primary_exchange` in `{XNAS, XNYS, XASE}`; and
- nonblank `ticker`.

The census retains every excluded and unknown row with a reason flag. There is no name-token inference and no inferred security type. No top-N, price, liquidity, ADV, market-cap, share-count, staleness or minimum-history population filter is permitted. The API `limit=1000` is pagination size, not a population cap.

ADR, ETF, ETN, fund, warrant, unit, right, preferred and unknown/blank types are excluded according to the contemporaneous dated field, not present-day labels. MDM cannot reliably separate every BDC, REIT or shell from `CS`; such rows remain in the listing-level population and that subtype dimension is `DEF-C/NOT ESTIMABLE`. Share classes remain separate. CIKs are not aggregated and symbols are not stitched.

### Units

- Stage A landmark unit: eligible listing/security episode at a completed daily landmark.
- Later event unit: qualifying listing/security episode and event timestamp.
- Cross-sectional rank denominator: all population-eligible rows with valid exact-session inputs for that feature horizon, irrespective of future outcome availability.
- Primary aggregation: date-equal; secondary: equal-event/listing-landmark.

## 5. Universe/time contract

### Monthly census schedule

The target schedule is independently defined as the first admitted U.S. equity session of every calendar month from July 2016 through April 2026 inclusive: 118 snapshots. It is not inherited from a prior research population. Pagination must be complete for every included formation date. An irretrievable whole date may be disabled only before outcomes, with the temporal-target change, reason and new configuration hash recorded; incomplete pagination within an included date is `DEF-A`.

For snapshot effective date `S`, define activation session `A` as the next admitted session after `S`. Historical `available_at` is unknown, so same-day use is prohibited. Store:

- `effective_date = S`;
- `retrieved_at_utc`;
- `historical_available_at = UNKNOWN`;
- `activation_session = A`;
- `decision_cutoff = official close(A)`; and
- `pit_quality = PIT_EFFECTIVE_DATE_APPROX_NOT_BITEMPORAL`.

No membership is backward-filled. A snapshot governs only its activation landmark in the first Stage A atlas; it is not silently carried to every day in the month. Later daily-event research requires a separately documented carry-forward rule and sensitivity.

The 118 proposed effective dates are:

```text
2016: 07-01 08-01 09-01 10-03 11-01 12-01
2017: 01-03 02-01 03-01 04-03 05-01 06-01 07-03 08-01 09-01 10-02 11-01 12-01
2018: 01-02 02-01 03-01 04-02 05-01 06-01 07-02 08-01 09-04 10-01 11-01 12-03
2019: 01-02 02-01 03-01 04-01 05-01 06-03 07-01 08-01 09-03 10-01 11-01 12-02
2020: 01-02 02-03 03-02 04-01 05-01 06-01 07-01 08-03 09-01 10-01 11-02 12-01
2021: 01-04 02-01 03-01 04-01 05-03 06-01 07-01 08-02 09-01 10-01 11-01 12-01
2022: 01-03 02-01 03-01 04-01 05-02 06-01 07-01 08-01 09-01 10-03 11-01 12-01
2023: 01-03 02-01 03-01 04-03 05-01 06-01 07-03 08-01 09-01 10-02 11-01 12-01
2024: 01-02 02-01 03-01 04-01 05-01 06-03 07-01 08-01 09-03 10-01 11-01 12-02
2025: 01-02 02-03 03-03 04-01 05-01 06-02 07-01 08-01 09-02 10-01 11-03 12-01
2026: 01-02 02-02 03-02 04-01
```

The date list is rechecked against the admitted session spine before data access. A mismatch is logged and resolved from the session contract, never from outcomes.

### Daily data interval and clocks

Use canonical MDM daily inputs only from 2016-01-04 through 2026-06-30. This supplies the 120-session feature lookback for the July 2016 start and 60-session maturation after the April 2026 snapshot activation.

At landmark `A`:

- membership is from snapshot `S < A`;
- features use completed exact-session bars through close `A`;
- the primary statistical outcome is split-consistent `close(A+h) / close(A) - 1` for `h` in `{1,2,3,5,10,20,40,60}`;
- this is a conditional-price landmark estimand, not an executable close fill;
- next-open translation is disabled in the first run unless regular-session open semantics pass the E0 clock gate; and
- MFE/MAE use future-session high/low only if daily high/low session semantics pass their E0 gate.

An H-session feature requires the exact admitted sessions `A` and `A-H`; last-observation-carried-forward and “last H available ticker bars” are prohibited. A young/missing listing may enter shorter horizons while remaining missing for longer horizons.

### E2/E3 contract

E2 requires an estimand-specific qualification showing that remaining limitations do not invalidate the proposed claim. E3 retains the canonical immutable five-table release or an independently approved equivalent meeting the frozen Foundation requirements. The E1 practical construction does not weaken that contract.

## 6. Point-in-time safeguards

1. Retrieve complete historical `active=true` and `active=false` pages for every included `S`. An EDGE-local wrapper must preserve exact redacted request/query, active mode, page ordinal, response status/request ID where present, complete raw response bytes or a proved lossless canonical form, redacted `next_url` chain, retrieval timestamp, byte length, hash and client-code hash before normalisation.
2. Never construct membership from present-day status or later success/failure.
3. Activate a snapshot only on `A>S`; do not backward-fill or use later snapshots to repair earlier fields.
4. Eligibility uses only the dated fields in Section 4. Missing/conflicting type, exchange, currency or active state is flagged, not inferred from names/current records.
5. Retain inactive pages for lifecycle audit. Later delisting cannot remove a listing from its earlier eligible census.
6. Maintain separate cross-sectional rank denominators for every feature horizon/date before outcomes are joined.
7. Daily `ingested_at_utc` is lineage metadata, not causal observation availability.
8. Normalise and retain at least `snapshot_date,ticker,name,market,locale,primary_exchange,type,active,currency_name,cik,composite_figi,share_class_figi,last_updated_utc,delisted_utc,source_universe_mode` plus page lineage. Collapse only fully identical normalised rows.
9. For each snapshot/ticker, quarantine active-mode conflicts and multiple `active=true` rows that disagree on eligibility/identity fields. Define `listing_key` as share-class FIGI, else composite FIGI, else provisional ticker@exchange. Across `[A-120,A+60]`, quarantine multiple nonblank share-class mappings, inconsistent share-class/composite mappings and overlapping provisional/conflicting identities. Missing FIGI alone is a flagged listing-level sensitivity, never authority to stitch.
10. Quarantine a feature/outcome interval that crosses an unresolved identity or split conflict. Count and disclose all quarantined intervals.
11. SPY/QQQ, if used later, are separately admitted MDM auxiliary benchmark series. Breadth, dispersion, leader abundance and comparable-breakout success are derived only from the same contemporaneous equity census.

## 7. Event definitions

Stage A contains no breakout event. It is a landmark leadership study and foundational comparator.

Later daily definitions must be objective and clocked:

- **Pre-break state:** all leadership, impulse, base, contraction, retention, moving-average and lagged-volume variables are complete by `t-1` for a next-session event study, or by close `t` for a post-close landmark study.
- **Level breakout:** completed close above the maximum completed high/close of a registered lookback/base interval.
- **Intraday high break:** deferred to Stage N; a one-minute high can trigger only after that minute completes unless admitted sequenced trades exist.
- **Range expansion:** current true range or high-low range divided by a lagged median/ATR, evaluated separately from level crossing.
- **Volatility-adjusted break:** distance above resistance divided by lagged ATR, never using same-event final ATR information not known at decision time.
- **Pre-break counterfactual:** compare the qualifying leader/base state before the event with the later event, using risk-set/landmark methods rather than assuming the event is causal.
- **Day-one confirmation:** close location, expansion and volume are post-close event descriptors; any action based on them begins no earlier than the next admitted session.

Hand-drawn chart boundaries are prohibited. E1 may explore objective base-window and geometry variants adaptively, but every definition and result is ledgered and cannot become E3 without a fresh finite freeze.

## 8. Candidate explanatory variables

### A - leadership

- split-consistent price return over 5, 10, 20, 40, 60 and 120 exact sessions;
- log return and robust slope of log price;
- same-date PIT percentile rank for each horizon;
- absolute and rank measures separately and jointly;
- continuous curves, descriptive bins and low-degree splines.

No top 1-2% threshold is assumed.

### B - prior impulse

- preceding N-session return and maximum advance;
- distance from medium-term low/high;
- impulse duration, log-price slope and return/session;
- count/magnitude of large positive sessions;
- positive/negative volume asymmetry and gap contribution where daily semantics allow;
- nonlinear extension/exhaustion shape.

### C - consolidation

- duration, depth and peak-to-trough drawdown;
- retracement of prior impulse and distance from high;
- high-low and closing-price range;
- regression slope/equilibrium dispersion;
- pullback count/size and close-location frequencies;
- leader plus no-consolidation counterfactual.

### D-E - contraction and final tightness

- ATR/price, ADR, close volatility, Parkinson volatility, median true range, Bollinger width;
- ATR5/ATR20, ATR10/ATR40, Range5/Range20 and Range3/Range10;
- direction of volatility change and ordering: recent < intermediate < impulse;
- 3/5-day range/base range, narrow-range percentile, inside-day count, declining-range sequences and closing compression.

### F-G - structural retention and moving averages

- lower-envelope slope, higher-low proxy, shallow retracement, proximity to high, downside excursions/recoveries and upper-range closes;
- price/SMA10, price/SMA20, price/SMA50, SMA10/SMA20, SMA20/SMA50 and 10/20/50 slopes;
- EMA analogues only as a logged exploratory redundancy check.

### H-I - breakout and volume

- level crossing, ATR-scaled breakout distance, gap, close location and day-one follow-through;
- current range/prior median, true range/ATR and expansion separate from crossing;
- volume/ADV20, dollar volume, PIT volume percentile, base volume contraction, relative breakout volume and up/down-volume balance.

### J-M - context, liquidity and geometry

- admitted SPY/QQQ trend/distance from SMA20/50/200 and realised volatility;
- same-census breadth, dispersion, leader abundance and matured comparable-event success;
- PIT peer/industry strength only after fresh taxonomy qualification;
- contemporaneous price, share volume and dollar volume; market cap/turnover disabled until valid;
- upper/lower-bound slopes, base depth/width/duration/retracement/compression/proximity to high;
- exploratory clustering only after continuous geometry is understood.

### Interactions

Scientifically plausible E1 interactions may be examined without requiring significant marginal effects:

- leadership x impulse;
- leadership x consolidation;
- leadership x contraction;
- impulse x shallow retracement;
- contraction x range expansion;
- final tightness x relative volume;
- leadership x regime;
- stock leadership x peer leadership;
- impulse x base duration; and
- leadership x consolidation x contraction x retained strength x breakout/range expansion.

This authorises hypothesis-led adaptive exploration, not unrestricted combinatorial optimisation. Each wave receives a unique child ID, explicit rationale and complete ledger entry.

## 9. Outcome variables

For horizons `{1,2,3,5,10,20,40,60}` report the complete trajectory.

Primary Stage A statistical outcome:

`R_h = split_consistent_close(A+h) / split_consistent_close(A) - 1`.

Later event studies use a separately frozen causal boundary. Next-open returns are implementation-relevance outcomes only after open semantics are validated.

Required outputs where observable:

- arithmetic mean and median;
- win rate, average gain/loss and payoff ratio;
- profit factor only for a fully specified event-return translation where meaningful;
- standard deviation, skewness and kurtosis;
- P25/P50/P75/P90/P95/P99, minimum and maximum;
- same-date cross-sectionally neutral and admitted benchmark-relative returns as secondary contrasts;
- MFE and MAE over each horizon, time-to-MFE/MAE and first failure/success timing;
- complete event counts, denominators, missingness and censoring by horizon;
- date-equal primary and equal-event secondary estimates; and
- full path storage, not only terminal returns.

For missing/terminal paths, report observed portions and scenario-specific terminal outcomes separately. Never invent future bars for MFE/MAE.

## 10. Right-tail treatment

The complete untrimmed distribution is primary. Genuine extreme positive observations may be the edge.

For every economically interpretable return distribution report:

- top 1%, 5%, 10% and 20% contribution to total positive return and total signed weighted return;
- counterfactual mean/expectancy excluding each tail fraction, diagnostic only;
- tail concentration/HHI and effective number of contributors;
- number of distinct listings, dates, industries where available, and nonadjacent periods contributing to the tail;
- leave-largest-outcome, leave-largest-listing, leave-largest-date-block and leave-largest-period diagnostics;
- tail outcomes by setup strength and regime; and
- whether the largest outcomes recur or appear isolated.

For each weighting scheme separately, normalise analysis weights to one, sort observations by raw return descending, and define the top 1/5/10/20% by cumulative analysis weight rather than row count. Fractionally allocate the single boundary observation when a cut crosses its weight. Positive-tail contribution uses `sum(w * max(R,0))` as denominator; signed contribution uses `sum(w * R)`. If the absolute denominator is at most `1e-12 * max(1, sum(w * abs(R)))`, report the contribution as `UNDEFINED_NEAR_ZERO_DENOMINATOR`. Diagnostic deletion removes the same cumulative weight, including the fractional boundary allocation, then renormalises remaining weights to one before recomputing expectancy. Ties retain deterministic `(return, listing_episode_id, landmark_date)` ordering while equal-return boundary allocations are also reported as a tie-range sensitivity.

Do not winsorise, trim or remove the best 10-20% as the primary series. Obvious data errors are corrected/quarantined through documented validity rules, not statistical extremeness. Returns above 100% are retained and audited, not presumed erroneous.

## 11. Repeated observations and clustering

Observations overlap by listing, time, horizon, trend episode and possibly peer group.

For E1:

- primary weighting is equal formation date, then equal event within date;
- equal-event weighting is mandatory secondary;
- use listing/security-episode and formation-date dependence diagnostics;
- use a chronological block bootstrap with blocks at least as long as the maximum 60-session outcome horizon;
- display fixed calendar-quarter and calendar-year stability without post-hoc market labels;
- do not call ticker events independent merely because identifiers differ;
- do not infer issuer clusters or successor chains without valid identity; mark them `NOT ESTIMABLE`; and
- repeated-breakout analysis waits for a robust, outcome-blind listing-episode/trend-episode definition.

E2/E3 uncertainty must use estimand-appropriate multiway clustering or resampling with effective-cluster diagnostics. Row-i.i.d. standard errors are never sufficient.

## 12. Exploratory versus confirmatory boundary

### E0

Validate synthetic/null/canary cases for census pagination, clocks, lags, exact-session alignment, ranks/denominators, split arithmetic, event causality, horizon indexing, MFE/MAE, tail contributions, terminal scenarios, clustering inputs, deterministic shards and append-only ledger behaviour. E0 may inspect schemas/metadata but not feature-outcome relationships.

### E1

E1 may adapt after observed results. It may examine new horizons, bins, splines, transforms, subgroups and plausible interactions. Every attempt is recorded with timestamp, parent rationale, code/config/input hashes, population, result and disposition.

Permitted vocabulary:

- `EXPLORATORY OBSERVATION`;
- `CANDIDATE`;
- `NO PLAUSIBLE SIGNAL OBSERVED`;
- `SENSITIVITY-DEPENDENT`;
- `INVALID`; and
- `NOT ESTIMABLE`.

E1 may not use `validated`, `confirmed`, `supported scientific claim` or `precise null`.

### E2

E2 begins only after a candidate and its estimand receive separate data qualification. Permitted vocabulary is `DEVELOPMENTALLY CORROBORATED`, `NOT CORROBORATED`, `UNRESOLVED` or `INVALID`. E2 remains outcome-exposed.

### E3

Before E3, freeze the simplest developmentally corroborated candidate, population, timestamps, outcomes, tests, SESOI, dependence method, finite family and decision rule. Use genuinely untouched/prospective sampling units and one authorised terminal analysis. An independent implementation on already exposed market dates remains E2 robustness, not E3 evidence. Only E3 can use formal confirmation language.

## 13. Multiple-testing controls

### E1 - diagnostic only

There is no programme-lifetime strong FWER budget over adaptive discovery and no requirement to freeze every exploratory transform before it can be viewed.

The append-only ledger is the primary protection. It records every horizon, threshold, spline knot, bin, transformation, subgroup, interaction, recovery run, null and abandoned branch.

Report raw effects, dependence-aware uncertainty, specification counts and cumulative Benjamini-Yekutieli FDR diagnostics after every result-bearing wave. Every valid scalar inferential contrast with a p-value is a decision unit keyed by programme, experiment, wave, hypothesis, feature/lookback, outcome horizon, model/contrast, terminal scenario, weighting and subgroup. Descriptive outputs without a scalar inferential test are ledgered `NONINFERENTIAL_DESCRIPTIVE`; invalid/low-support tests are ledgered with the exclusion reason and no p-value. Neither class enters BY. Result-bearing recoveries and scenario/subgroup tests are distinct units. E1 FDR is diagnostic only:

- `q > 0.10` cannot suppress an otherwise scientifically plausible exploratory specification;
- `q <= 0.10` cannot validate a specification or nominate it automatically;
- FDR is not a confirmatory gate and transfers no alpha to E3; and
- the diagnostic denominator grows with the campaign and is never reset.

E1 prioritises effect magnitude, shape coherence, stability, recurrence, concentration, contributor diversity and robustness to `DEF-B` sensitivities. Candidate selection is transparently adaptive and exposed.

### E3 - formal control

Formal strong multiplicity control applies to a finite frozen confirmatory family. Before any E3 outcome is accessible, a future freeze must allocate the complete programme-lifetime error budget across H01-H20, H16 confirmation, independent replication and every deferred extension that may make a confirmatory claim. The allocations and sequential rules may not be created, enlarged or revised after any earlier E3 result is observed; there is no alpha recycling. This Stage 0 design does not spend or allocate E3 alpha, so no current reservation is claimed.

## 14. Temporal validation plan

All current historical dates are developmentally exposed. Use them honestly.

E1 will report:

- fixed chronological quarters and years;
- rolling/expanding-window shape stability;
- predeclared broad calendar partitions based on information available at the time, not outcome-selected bull/bear labels;
- separately measured high/low realised volatility, SPY/QQQ trend, breadth/dispersion and leader-success states where causally available;
- recurrence across nonadjacent periods and independent contributors; and
- leave-period-out sensitivity.

Walk-forward analysis on exposed history assesses developmental stability; it is not untouched confirmation. Any promising candidate is simplified and frozen before E2/E3. If adequate genuinely untouched history is unavailable, E3 accrues prospectively. Alternate securities on the same exposed dates are transportability evidence, not automatically independent confirmation.

## 15. Cost treatment

Separate phenomenon from implementation.

E1 Stage A tests gross split-consistent price continuation and makes no trade/fill claim. It does not reject a phenomenon because one arbitrary execution model performs poorly.

After a daily candidate is developmentally credible:

- use the existing Project EDGE cost policy;
- stress spread, slippage, commissions, gap-through-stop and liquidity impact;
- distinguish modelled envelopes from measured representative quotes;
- use targeted quote data only if its sampling population/timestamps are independently documented, causal and admitted for this programme;
- keep price/share-volume/dollar-volume opportunity descriptors separate from formal capacity; and
- do not claim market-cap/turnover capacity until the fields are valid.

Strategy optimisation, portfolio construction and live implementation remain outside this programme.

## 16. Dependency map between research stages

### Evidence-tier path

`E0 engineering -> E1 minimum entry pack -> E1 adaptive discovery -> estimand-specific E2 qualification/corroboration -> finite E3 freeze -> untouched/prospective confirmation -> independent replication -> separate strategy charter`

### Scientific dependencies

After the common E1 population/path panel and each stage's E0 checks pass, the following descriptive/marginal work may proceed in parallel where technically efficient:

- A leadership;
- B impulse;
- C consolidation;
- D contraction;
- E tightness;
- F retention;
- G moving averages;
- I lagged/base volume;
- J admissible regime variables;
- L price/volume liquidity descriptors; and
- M continuous geometry.

Parallel execution does not erase conditioning logic. Incremental models retain named parent blocks, and an integrated phenotype is not promoted until component and interaction evidence is understood.

Mandatory information dependencies are:

- H breakout comparisons require an objective base/event clock;
- breakout-day volume requires H event timing;
- K requires a newly qualified PIT taxonomy;
- endogenous comparable-breakout-success regime requires matured prior events only;
- repeated setups require a defensible listing/trend episode;
- H16 follows component and plausible-interaction discovery;
- H17 remains separate and follows core Common Breakout understanding;
- N follows daily E3 validation and intraday admission;
- O follows validated entry semantics; and
- P follows validated entry/risk semantics.

## 17. Stop/go criteria

### Minimum E1 entry pack

Before any market-outcome access, create and review:

1. exact broad exploratory population and exclusion-reason table, with no inherited prior filter;
2. raw census page inventory and canonical daily/split input path/byte/SHA-256 manifest;
3. exact fields, snapshot dates, retrieval timestamps and pagination completeness audit;
4. feature, decision and outcome timestamps and admitted session spine;
5. rank-denominator/missingness contract for each horizon;
6. price/action basis and split-conflict policy;
7. estimand-specific `DEF-A`-`DEF-D` register and `DEF-B` sensitivity plan;
8. imported exposure ancestry and Common Breakout/EP firewall;
9. append-only run/search ledger opened before outcomes;
10. design, code, config, environment and synthetic-validation hashes; and
11. unique run ID and written user authority for the first empirical run.

Five-table production completeness, complete terminal economics, restored `.git`, production scope, a finite discovery budget, an FDR pass and independent approval of every exploratory transform are not hidden E1 prerequisites.

### E1 stage decisions

- `GO - NOMINATE FOR E2 (MONTHLY ACTIVATION-LANDMARK ESTIMAND ONLY)`: no claim-relevant `DEF-A`; an interpretable location or upper-tail shift is directionally coherent across trajectory, recurs across multiple chronological blocks/contributors, and is not wholly reversed by reasonable action/terminal sensitivities. FDR significance is not required. Daily-landmark generalisation requires a separate carry-forward qualification.
- `CONTINUE E1`: plausible but shape-, period-, contributor- or sensitivity-dependent; conduct a targeted, logged adaptive wave.
- `NO-GO FOR E2 NOMINATION`: valid E1 analysis is consistently flat/adverse across plausible forms and periods. This is not a confirmed null.
- `INVALID / DEF-A`: population, clock, action, identity or outcome validity fails for the affected estimand.
- `NOT ESTIMABLE`: the requested dimension is unsupported, while narrower E1 work may continue.

No marginal component must pass before a scientifically plausible E1 interaction can be explored. Conversely, an interaction found adaptively cannot become E3 evidence without a new finite freeze.

### Current programme decision

- E0: `PROPOSED GO AFTER EXACT-BYTE USER APPROVAL`.
- E1 readiness: `PROPOSED GO AFTER EXACT-BYTE USER APPROVAL`.
- E1 outcome access: `CONDITIONAL GO`, currently not executable because the minimum entry pack is proposed but not materialised/reviewed and the user explicitly requested review before execution.
- E2: `NO-GO`.
- E3/confirmation/production: `NO-GO`.

## 18. Data deficiencies and blockers

### Current classification for first Stage A E1 estimands

| Deficiency | Class for first E1 | Consequence and treatment |
|---|---|---|
| No `.git` in EDGE target | `DEF-D` | Hash-bind all artifacts; repair canonical provenance before E3 |
| Canonical MDM data directory mutable/dirty | `DEF-A` until a run-specific atomic manifest is made | Bind every consumed file/page by path, bytes and SHA-256; do not use a moving input set |
| Existing readiness populations embed filters/thresholds | `DEF-A` for a broad-population claim | Do not consume them as primary membership; build the new broad census |
| Historical PIT `available_at` unknown | `DEF-B`, conditional on approval of one-session lag and no observed future-derived field | Label effective-date approximation; use `A>S`; run eligibility/missingness sensitivities. Any actual inseparable future field is `DEF-A` |
| Present-day/survivor-only membership | `DEF-A` | Prohibited; complete active/inactive historical pagination required |
| Population type/exchange/currency conflicts | `DEF-A` for affected row/snapshot | Quarantine affected eligibility; disclose rates/concentration; material unresolvable coverage can invalidate that snapshot/estimand |
| Daily duplicate/conflicting ticker-date rows | `DEF-A` for affected interval | Collapse exact duplicates with lineage; quarantine conflicts; quantify concentration before proceeding |
| Daily session/open/high/low semantics incompletely proven | `DEF-B/C` for close-to-close landmark if closing-date alignment is sound; `DEF-A` for next-open/fill or MFE/MAE claims until validated | Primary first run is close-to-close; disable invalid secondary outcomes |
| Split files overlap; action history incomplete | `DEF-A` for intervals crossing unresolved split conflicts or obvious split contamination | Deduplicate exact actions, require one positive factor/date, quarantine affected intervals, audit population-scale coverage |
| Cash distributions unavailable | `DEF-C/B` | Primary claim is split-consistent price return, not total return; label and later test admitted total-return subset |
| Terminal economics incomplete | Normally `DEF-B` for E1 exploratory shape/path estimands; `DEF-A` for an unconditional population-expectancy claim that cannot be identified | Retain every affected landmark; report frequency/concentration/horizon and multiple labelled scenarios. Never silently delete. Final unconditional edge claim remains blocked |
| Stable issuer/successor identity incomplete | `DEF-C` for listing-level E1; `DEF-A` if unsupported stitch is attempted | No stitch/issuer aggregation; identity conflicts start/quarantine episodes; issuer/repeated-chain claims `NOT ESTIMABLE` |
| Sector/industry taxonomy not admitted | `DEF-C` for Stage K; irrelevant to Stage A | Stage K disabled until fresh qualification |
| Market cap/shares/turnover unreliable | `DEF-C` for those strata; irrelevant to gross Stage A | Use only price/share volume/dollar volume later; no cap/turnover claim |
| Broad representative quotes absent | `DEF-D/C` for gross Stage A; later implementation limit | Use transparent modelled cost envelopes only after phenomenon work |
| Minute order/session ambiguity | `DEF-C` for daily Stage A; `DEF-A` for unsupported intraday fill/order claim | Stage N disabled |
| Direct VIX unavailable | `DEF-C`; Stage A unaffected | Do not substitute external VIX; use separately admitted MDM benchmark/cross-section state later |
| Entire historical interval outcome-exposed | `DEF-C` claim ceiling | E1/E2 only; E3 accrues independently/prospectively |
| H7/H8/EP/DVP anomalies and overlap | Governance/exposure control | Quarantine results; import exposure only; no finding/specification inheritance |

### Terminal scenario policy for E1

Before outcomes, freeze a listing-key/session classifier with these exhaustive states: `ENDPOINT_OBSERVED`, `INTERMITTENT_BAR_GAP_WITH_REAPPEARANCE`, `VALID_MDM_TERMINAL`, `DATED_INACTIVE_OR_DELISTED_NO_ECONOMICS`, `UNEXPLAINED_CESSATION`, `IDENTITY_OR_SUCCESSOR_AMBIGUITY`, `ACTION_CONFLICT`, and `RIGHT_BOUNDARY_CENSORING`. Identity/action conflicts are `DEF-A` quarantine; right-boundary censoring disables the affected formation date/horizon before outcomes. Intermittent gaps do not trigger a terminal scenario.

For a dated inactive/delisted case, the scenario begins on the first admitted session on/after the dated evidence. For unexplained cessation, it begins on the first required session after the last valid same-key bar when no same-key bar reappears through `A+60`. Store the class, evidence, last valid session and scenario-start timestamp. This distinguishes terminal sensitivity from feed gaps, halts, ticker reuse, successor ambiguity and calendar-end censoring without pretending the classifier supplies vendor economics.

Affected landmarks remain in the audit population. For each horizon report their count, share, dates, rank distribution and concentration. Run, as explicitly labelled assumptions rather than vendor truth or mathematical bounds:

1. observed valid MDM terminal economics where available;
2. severe-loss/full-loss-at-terminal scenario;
3. last-valid-price/flat-continuation scenario;
4. complete-observed-path diagnostic only; and
5. censoring/identified-set methods only where mathematically defensible.

If reasonable scenarios reverse direction/materiality, classify `SENSITIVITY-DEPENDENT / E1 UNRESOLVED`. Missing terminal outcomes do not automatically block unrelated preceding relationships, but they block any affected unconditional final population-edge claim until resolved.

### Remaining `DEF-A` gates before the first E1 outcome access

1. Materialise and hash one immutable, programme-specific MDM census/daily/split input release; do not consume the filtered readiness outputs.
2. Complete active/inactive census pagination for every included formation date and audit dated population fields; quarantine/resolve conflicting eligibility rows. An irretrievable whole date may be disabled outcome-blind with a narrowed target, but a partially paginated included date is invalid.
3. Obtain explicit approval of the `S -> next session A` effective-date approximation and verify no actual future-derived membership field enters eligibility.
4. Admit the session spine and validate the daily date/close semantics needed for the primary close-to-close landmark; disable next-open/MFE/MAE until their fields pass.
5. Audit ticker/FIGI conflicts over each feature-plus-outcome window; prohibit stitching and quarantine ambiguous intervals.
6. Reconcile exact duplicate split records and quarantine conflicting/missing split intervals; demonstrate that included returns are not obviously action-contaminated.
7. Collapse exact daily duplicates, quarantine conflicting ticker-date rows and show that central predictor/outcome fields are sufficiently present for the affected estimands.
8. Freeze and validate the missing-path/terminal taxonomy, evidence fields and scenario-start timestamps; do not conflate temporary gaps, right censoring or identity/action conflicts with terminal scenarios.
9. Open the append-only exposure/search ledger, pass E0 synthetic/null/canary tests, freeze the baseline first-run proposal and obtain written user run authority.

Terminal incompleteness is not a blanket `DEF-A` under the approved E1 amendment. It becomes `DEF-A` only for an affected estimand that cannot be meaningfully measured or sensitivity-characterised.

## 19. Proposed experiment identifiers

Identifiers reserve lineage only; none grants outcome access.

| Purpose | Identifier / tier |
|---|---|
| Stage 0 design | `EDGE-QB-CBRP-S0-RD-001` |
| Proportionality amendment | `EDGE-QB-CBRP-GOV-AMD-001` |
| Exposure reconciliation | `EDGE-QB-CBRP-GOV-EXPOSURE-001` |
| Broad E1 data construction | `EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1` |
| E0 data/feature validation | `EDGE-QB-E0-VAL-DATA-001`, `EDGE-QB-E0-VAL-FEATURE-001` |
| E0 inference/ledger validation | `EDGE-QB-E0-VAL-INFERENCE-001`, `EDGE-QB-E0-VAL-LEDGER-001` |
| E1 search campaign | `EDGE-QB-E1-DISC-CAMPAIGN-001` |
| First empirical experiment | `EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001` |
| Stage B-P E1 studies | `EDGE-QB-E1-{STAGE}-{SUBJECT}-DISC-{NNN}` |
| E2 developmental studies | `EDGE-QB-E2-{STAGE}-{SUBJECT}-DEV-{NNN}` |
| Future finite E3 campaign | `EDGE-QB-E3-CONF-CAMPAIGN-001` |
| Future independent replication | `EDGE-QB-E3-Q-DAILY-PHENOTYPE-REPL-001` |

Every recovery/adaptive wave receives a new child ID. Existing artifacts are never overwritten or relabelled.

### Exact proposed first data construction

`EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1` will:

1. use the clean MDM historical PIT client at commit `a5de2529cae2288f1ef531d8b4ddf7c9cc412e34` only for access/pagination/schema-normalisation primitives, wrapped by new EDGE-local lossless page capture;
2. query complete `active=true` and `active=false` pages for every included target date; before normalisation retain redacted request/query, active mode, page ordinal, response metadata, complete raw bytes/lossless canonical payload, redacted cursor chain, retrieval time and hash;
3. store raw census pages and normalised fields `snapshot_date,ticker,name,market,locale,primary_exchange,type,active,currency_name,cik,composite_figi,share_class_figi,last_updated_utc,delisted_utc,source_universe_mode` plus page lineage within `research/directed/EDGE-QB-CBRP-20260811-001/e1_data/`;
4. apply only the explicit Section 4 eligibility fields, with no inherited readiness filter or threshold;
5. read canonical MDM daily OHLCV from 2016-01-04 through 2026-06-30 and bind every file by path/bytes/hash;
6. consume only `date,ticker,open,high,low,close,volume,transactions,source_file,ingested_at_utc`; VWAP is disabled;
7. create separate `close_valid`, `open_valid`, `range_valid` and `volume_valid` flags; a close-only H01 feature/outcome requires only the exact fields it uses, while open/range/volume defects disable only their corresponding estimands; never let an unused field become a hidden population filter;
8. preserve missingness rather than stale-fill;
9. collapse exact daily/action duplicates with lineage and quarantine conflicts; for the physical `execution_date`, define `split_factor=split_to/split_from`, assigning a non-session action to the first admitted session on/after that date;
10. compute each crossing-session ratio as `close(d)*split_factor(d)/close(previous_session)`, multiplying multiple intervening factors, then compose split-consistent price returns without distributions; do not inherit readiness continuity residuals, episode gaps or action thresholds;
11. keep share classes separate, create no successor stitch and make no issuer claim;
12. build horizon-specific exact-session feature/rank denominators before outcomes; and
13. produce deterministic manifests/hashes, deficiency counts and a replay command before outcome access.

The three currently observed split inputs are:

| MDM file interval | SHA-256 |
|---|---|
| 2007-01-01 to 2015-12-31 | `09A74DC95B2E4E0974B26A05E5E860C23E570CA445A86E59D17B57FCED60B033` |
| 2015-01-01 to 2026-06-30 | `DAE66FAE4468C0F43C7A5F0982B22B8BD21FF373FDD768D8B408E4DED4B95350` |
| 2021-11-01 to 2025-12-31 | `1BD3D13D4B3E7DEC038B660C198DDA95FC1EC8F46673EAC7E9F8F5C7A1990081` |

Those hashes are current observations, not the future release manifest; they must be rechecked when the entry pack is materialised.

### Proposed first empirical experiment

The separate review specification `QULLAMAGGIE_BREAKOUT_E1_FIRST_EXPERIMENT_PROPOSAL.md` defines `EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001`.

It is an E1 Stage A leadership atlas:

- features: absolute/log momentum and same-date PIT percentile ranks for 5/10/20/40/60/120 sessions;
- primary outcomes: untrimmed split-consistent close-to-close paths for 1/2/3/5/10/20/40/60 sessions;
- primary question: shape, magnitude, recurrence, stability and right-tail concentration, with no top-1% assumption;
- dependence: date-equal primary, equal-event secondary, listing/date clustering diagnostics and 60-session block bootstrap;
- terminal/action limitations: fully retained and scenario-tested;
- E1 FDR: diagnostic only;
- no breakout, strategy, stop, exit, cost, portfolio or live-trading test; and
- no execution until the user reviews and explicitly authorises it.

## 20. Exact order in which hypotheses should be tested

1. Approve/reject the exact-byte Stage 0 v0.3 design and first-experiment proposal.
2. Reconcile/import prior exposure ancestry and open the append-only search ledger.
3. Materialise `EDGE-QB-E1-DATA-BROAD-CS-PIT-201607-202604-V1` without outcome calculations.
4. Classify every relevant deficiency per estimand; close/quarantine all first-run `DEF-A` defects.
5. Run E0 synthetic/null/canary validation for clocks, ranks, split arithmetic, outcomes, paths, tail metrics, scenarios, dependence inputs and deterministic replay.
6. Freeze the baseline atlas for `EDGE-QB-E1-A-LEADERSHIP-SHAPE-DISC-001`; obtain written user authority.
7. Run E1 `QBC-H01`: leadership shape and continuation trajectory.
8. Evaluate H01 by magnitude, shape, recurrence, stability, concentration and robustness; use FDR diagnostically only. Log adaptive waves separately.
9. Once the shared panel and stage-specific E0 checks pass, allow scientifically independent E1 work on H02-H07, lagged/base H09, admissible H10, H12 and H13 in parallel.
10. Define/test H03 leader plus consolidation versus leader plus no consolidation; do not infer value from descriptive charts.
11. Test H04 contraction conditional on leadership/impulse/base descriptors and H05 final tightness beyond whole-base contraction.
12. Test H06 retention and H07 moving-average redundancy/increment.
13. Freeze objective base/event clocks for H08; compare pre-break state, level crossing and range expansion.
14. Test breakout-day H09 volume only after H08 timing is valid.
15. Test H10 index/cross-sectional/endogenous leader-success states using only matured prior events.
16. Run H11 only after fresh PIT taxonomy qualification; otherwise mark `NOT ESTIMABLE`.
17. Run H12 gross price/share-volume/dollar-volume heterogeneity, without practitioner-scale filters or formal capacity claims.
18. Explore H13 continuous geometry; any clusters remain E1 candidates.
19. Define listing/trend episodes outcome-blindly before H14 repeated-setup ordinal analysis.
20. Analyse H15 right-tail predictability and recurrence while preserving the full tail.
21. Explore the hypothesis-led interactions in Section 8, including the core conjunction, without marginal-significance prerequisites; log all adaptive branches.
22. Construct the simplest H16 daily phenotype from E1/E2 evidence and compare it with conventional momentum. Do not call it validated.
23. Qualify selected estimands for E2, re-run under frozen developmental specifications and record corroboration/instability.
24. Reduce the surviving candidate to the simplest finite E3 specification; freeze population, clock, outcomes, tests, SESOI, multiplicity and decision rules before untouched/prospective evidence begins.
25. Conduct one authorised strong-FWER E3 analysis and later independent replication. No E1/E2 result donates confirmation.
26. Only after daily confirmation/replication, test H17 EP lifecycle as a separate covariate; it never defines the Common Breakout population.
27. Only after daily confirmation and minute-data admission, test H18 Stage N with completed-bar timestamps and no invented within-minute order.
28. Only after valid entry semantics, test H19 failures/MAE/MFE/risk references.
29. Only after entry/risk evidence, test H20 payoff harvesting.
30. If scientific, implementation, right-tail, stability and replication gates pass, propose a separate strategy/capacity charter. Do not build it under this authority.

The sequence preserves scientific dependencies without imposing administrative seriality on independent E1 discovery. A null/weak H01 does not forbid separate contraction/expansion or theory-led conjunction exploration; it does determine whether any later result is distinguishable from conventional momentum.

## Tier-specific approval records

### Before E1 market outcomes

Approval must bind:

- Stage 0 v0.3 SHA-256/byte length;
- first-experiment proposal SHA-256/byte length;
- E1 minimum entry pack and exact MDM manifests;
- exposure/search ledger location and initial hash;
- E0 validation results;
- all unresolved deficiency classifications and disabled estimands; and
- user run authority for the named experiment.

### Before E2

Add an estimand-specific PIT/survivorship/action/dependence qualification and frozen developmental specification.

### Before E3

Add canonical immutable release authority, exact finite hypothesis family, SESOI, strong FWER/sequential allocation, independent review, genuinely independent/prospective sample clock, terminal-read authority and replication reservation.

## Review evidence index

Primary repository sources reviewed include:

- `PROJECT_EDGE_FOUNDATION_DOCUMENT_V1.1.md`
- `PROJECT_EDGE_EDGE_QUALIFICATION_FRAMEWORK.md`
- `PROJECT_EDGE_SCIENTIFIC_PROGRAMME_REVIEW.md`
- `PROJECT_EDGE_MILESTONE_2_MDM_DATA_FOUNDATION_SPECIFICATION.md`
- `PROJECT_EDGE_MILESTONE_3_IMPLEMENTATION_REPORT.md`
- `PROJECT_EDGE_MILESTONE_4_PRODUCTION_READINESS_REVIEW.md`
- `PROJECT_EDGE_MILESTONE_5_FIRST_EMPIRICAL_RESEARCH_PROGRAMME_SPECIFICATION.md`
- `README.md`
- `src/edge_mdm/contracts.py`
- `src/edge_mdm/actions.py`
- `src/edge_mdm/release.py`
- `config/mdm_capability_audit.v1.json`
- `config/population_time_contract.v1.json`
- `config/production_scope_status.v1.json`
- `research/directed/EDGE-QULLAMAGGIE-UDRP-20260809-001/`
- `research/directed/EDGE-QULLAMAGGIE-DVP-001/`

Canonical MDM and the clean readiness worktree were inspected because MDM is the mandated source. No external research-engine artifact was admitted. Physical inventory counts are mutable capability metadata until the E1 entry pack binds exact paths and hashes.

## Integrity note

This file cannot safely contain its own final byte hash. A sidecar hash record must bind the exact reviewed bytes. The following frozen/control-file hashes were rechecked after revision; this document did not modify those files:

| File | SHA-256 |
|---|---|
| `PROJECT_EDGE_FOUNDATION_DOCUMENT_V1.1.md` | `F96D0B88BD6DCE18FAA92B3C7C111A743C365870814143EE0F23CF3077E14291` |
| `PROJECT_EDGE_EDGE_QUALIFICATION_FRAMEWORK.md` | `C145688345F2207564E04F72BE27F622E792E14DE6D0549E44D9E61BB60B27CA` |
| `PROJECT_EDGE_SCIENTIFIC_PROGRAMME_REVIEW.md` | `0B4C925E53F709A20846B75700FC6ADB4C02403100B9C2CFA1CE8926304DAEBB` |
| `PROJECT_EDGE_MILESTONE_2_MDM_DATA_FOUNDATION_SPECIFICATION.md` | `AD811F11DE8856CA217EAF857117D5ECB37FD2D974ECC578589AA5F50CFBB942` |
| `PROJECT_EDGE_MILESTONE_3_IMPLEMENTATION_REPORT.md` | `46353238896384D735B7F5D7855300B9BA59ED38C9CE40C13F4DB022998B0321` |
| `PROJECT_EDGE_MILESTONE_4_PRODUCTION_READINESS_REVIEW.md` | `798693A9E503DD53F1958A174865EDCAA9FE1C52E68997259EF72C70FC857A71` |
| `PROJECT_EDGE_MILESTONE_5_FIRST_EMPIRICAL_RESEARCH_PROGRAMME_SPECIFICATION.md` | `535AA3BB339A66369EA960787773F5BEE16193FC33453F47ED82D70EB3937EA9` |

Any edit to this design creates a new version, byte length and SHA-256 and requires renewed review. Pathname approval alone is insufficient.
