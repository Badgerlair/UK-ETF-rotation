# PROJECT EDGE

## IMPLEMENTATION MILESTONE 5 — FIRST EMPIRICAL RESEARCH PROGRAMME

**Document:** Research Programme Specification  
**Programme ID:** `EDGE-VSP-001`  
**Programme family:** Volatility expansion, contraction, and state dynamics  
**Bounded research subject:** Security-level daily observed-range persistence  
**Document date:** 4 August 2026  
**Repository:** `D:\codex\equity_quant_research_platform`  
**Status:** Programme design complete; empirical execution not yet authorised  
**Implementation produced by this milestone:** None

---

## 1. Executive decision

Project EDGE shall begin with one research family only:

> **Daily security-level volatility expansion and persistence, measured through
> the observed regular-session high–low range.**

The programme is deliberately narrower than “volatility research” in general.
It asks whether a security’s observed daily range contains material information
about its own later range, after stable differences between securities,
common-date market conditions, data defects, trading-state artifacts,
survivorship, and dependence have been addressed.

This family is selected because it offers the highest immediate scientific
information gain under Project EDGE’s present data constraints:

- the atomic measurement `log(high / low)` uses only coherent values from the
  same observed MDM row;
- it is dimensionless and invariant to a common multiplicative adjustment
  within that row;
- it does not compare price levels between sessions;
- complete distribution and terminal-return economics do not enter this exact
  estimand;
- the exposure is known after the governed close of session `t` and the outcome
  occurs later;
- the core proposition can be rejected decisively before scarce confirmation
  evidence or additional data capabilities are consumed; and
- the same frozen measurement can support discovery, falsification,
  confirmation, independent reimplementation, and direct temporal replication.

The programme contains six ordered experiments:

1. a non-gating within-security one-session decomposition;
2. the primary security-linked residual association beyond common-date effects;
3. trading-state, missingness, concentration, and identity-linkage
   falsification;
4. one fixed trading-week duration boundary;
5. one sealed temporal confirmation; and
6. one independent reimplementation and direct temporal replication.

The sequence is a fixed gate, except that Experiment 1 cannot block Experiment
2: both one-session specifications are frozen before either result is viewed,
and Experiment 2 is the first decision-bearing phenomenon test. A valid precise
null or contradiction in Experiment 2, an artifact explanation, confirmation
failure, or valid temporal-replication failure can end the programme.
There is no authority to rescue a failed claim by trying another threshold,
window, outcome, regime, subgroup, estimator, or feature combination.

The programme can establish a temporally ordered, directly replicated candidate
association. It cannot by itself complete the Foundation's full Stage 4
validation programme, establish operational forecast value, demonstrate
profitability, or establish a genuine trading edge. A volatility
quantity is not directly commensurate with transaction costs, and Stages 0–5 do
not specify an instrument, direction, portfolio, turnover, or execution rule.
A fully successful programme would therefore produce a directly replicated
candidate input for later validation, not validated knowledge or a trading
strategy.

Project EDGE is not authorised to execute the programme today. Current
production gates remain:

- MDM capability audit: `BLOCKED`;
- Population and Time Contract: `UNRATIFIED`;
- production scope: `NO_APPROVED_SCOPE`; and
- release authority: `NOT_CONFIGURED`.

Milestone 4’s Mandatory release, feature-validation, preregistration, custody,
and real-MDM requirements remain prerequisites. Milestone 5 does not bypass or
redesign them.

---

## 2. Authority, preservation, and evidence boundary

### 2.1 Frozen authorities

This programme operationalises, but does not modify:

- Stage 0 Foundation Version 1.1;
- the Milestone 1 Scientific Governance Specification; and
- the Milestone 2 MDM Data Foundation Specification.

The locally verified frozen hashes remain:

- Foundation Version 1.1:
  `f96d0b88bd6dce18faa92b3c7c111a743c365870814143ee0f23cf3077e14291`;
- Milestone 2:
  `ad811f11de8856ca217eaf857117d5ecb37fd2d974ecc578589aa5f50cfbb942`.

No canonical Milestone 1 file and governing hash were present among the
permitted repository-root documents at this review. The programme treats the
Milestone 1 requirements already incorporated into Foundation Version 1.1 and
Milestone 4 as binding. Before execution, an authorised reviewer must consult
the canonical frozen Milestone 1 text and confirm that this programme satisfies
any stricter requirement. If the authoritative text cannot be consulted, that
is an execution blocker; it is not permission to reconstruct or amend it.

### 2.2 Clean research boundary

This specification was designed without using:

- any completed experiment output;
- any previous findings database;
- any material under `research/`;
- any prohibited Forex, Futures, legacy, or regime-engine project; or
- any market-data source other than the declared MDM boundary.

No empirical evidence about whether the proposed phenomenon exists has been
examined or produced. Every statement below is prospective.

### 2.3 Programme status versus experiment authority

Approving this specification does not authorise an experiment. Each experiment
must still possess its own immutable hypothesis, dependency decision, Stage 2.5
feature evidence, discovery-budget reservation, Research Cost record, ESIG
record, evidence allocation, preregistration, scheduler-eligibility decision,
execution record, review, and Knowledge Base deposit.

For one programme these records may be small content-addressed files. A generic
registry service, discovery engine, or workflow platform is not required.

Identifiers remain separate. `EDGE-VSP-H01` through `EDGE-VSP-H06` identify
immutable hypothesis records; `EDGE-VSP-E01` through `EDGE-VSP-E06` identify
their corresponding immutable experiment-specification records. The one-to-one
mapping is declared here for convenience but never merges the two records,
versions, hashes, amendments, or review histories.

---

## 3. Selection of the first research family

### 3.1 Selected family

The Foundation catalogue family is **volatility expansion, contraction, and
state dynamics**. The initial bounded construct is:

> regular-session observed-range persistence at the security level within one
> exchange, one currency, and one survivor-accounted primary ordinary-equity
> population.

The programme does not study volatility regimes, options, implied volatility,
intraday paths, jumps, return direction, gaps, sector propagation, or strategy
rules. Those are separate future questions.

### 3.2 Why other families are not selected first

| Family | Reason not selected for programme one |
|---|---|
| Opening gaps | Requires cross-session price continuity, complete action treatment, gap classification, and exact overnight/session assignment before valid inference. |
| Relative strength | Requires complete point-in-time return economics, a cross-sectional comparator, and usually market, sector, industry, or peer context. |
| Momentum and mean reversion | Require valid cross-session returns, terminal outcomes, and continuity across action intervals. |
| Sector leadership | Requires admitted point-in-time sector and industry histories that are not currently available for production research. |
| Breadth | Is feasible later but adds denominator, weighting, membership, and missingness questions before the simpler security-level state question has been answered. |
| Earnings behaviour | Requires admitted as-reported earnings, publication timestamps, revisions, and event-session assignment. |
| Institutional accumulation | Observable volume patterns cannot establish participant identity, and stronger proxies require additional float, shares, ownership, or market-quality capability. |

This is an ordering decision, not a conclusion that the deferred families lack
phenomena.

### 3.3 Why the Milestone 4 pilot needs a scientific estimand

A pooled correlation between `log(high / low)` on adjacent sessions is useful as
a platform commissioning result but is not sufficient evidence of a
security-level phenomenon. It can be positive because:

- some securities are persistently more volatile than others;
- a market-wide volatility state affects most securities together;
- the same dates and issuers are repeatedly observed;
- sparse trading, tick size, stale prices, or lifecycle attrition distort rows;
  or
- millions of stock-days are incorrectly treated as independent evidence.

Experiment 1 therefore removes stable security differences and records the
one-way decomposition. Experiment 2 removes both stable security differences
and common formation-date effects. The two specifications are frozen together,
and Experiment 2 must execute after any valid Experiment 1 result because
omitted common-date conditions can suppress as well as inflate the one-way
coefficient. Only the Experiment 2 conditional association is eligible to
become the programme's primary candidate claim.

---

## 4. Scientific objective and claim

### 4.1 Scientific objective

Determine whether daily observed equity volatility behaves as a persistent,
security-linked state rather than as noise, stable cross-sectional type,
market-wide clustering, or data artifact.

The programme must establish, in order:

1. how the one-way within-security recurrence compares with the primary model;
2. whether a security-linked residual association remains after common-date
   effects;
3. whether observable artifacts can explain it;
4. whether it persists beyond the immediately following session;
5. whether the unchanged claim confirms in untouched later time; and
6. whether an independent implementation reproduces it on genuinely new
   outcomes.

### 4.2 Complete phenomenon form

The strongest permitted claim has the Foundation’s required form:

> For the ratified population of primary ordinary equity listings on one
> exchange and in one currency, a larger observed regular-session log range at
> the post-close cutoff of session `t` is associated with a scientifically
> material increase in the same security's conditional expected later observed
> log range, relative to its declared population linear-projection model, after stable
> security and common-date effects, within declared uncertainty, and the effect
> remains compatible across sealed confirmation and direct temporal
> replication in the stated domain.

This is a conditional-mean association with temporal ordering. It is neither an
entire-distribution claim nor, without a separately validated prospective
forecast, an operational prediction claim. It is not a causal claim about
information arrival, institutional behaviour, or order flow.

### 4.3 Three conclusions that must remain separate

| Conclusion | Meaning in this programme | Maximum available evidence |
|---|---|---|
| Persistence | Today’s valid range state is materially associated with a later range state under the registered estimand. | Experiments 1–4 |
| Temporal generalisation | The frozen relationship repeats in later time without using later outcomes to select the claim. | Experiments 5–6 |
| Exploitability | A feasible economic decision captures value net of instruments, costs, constraints, capacity, and execution. | Not established by this programme |

A successful result may justify a later, separately governed Stage 6 feasibility
proposal. It must never be described as proof of a profitable or exploitable
edge.

### 4.4 Programme-level scientific objective function

The programme maximises learning by placing cheap falsifiers before expensive
or scarce evidence:

- core existence before mechanism elaboration;
- common-exposure and artifact challenges before holdout consumption;
- one interpretable longer horizon rather than a horizon sweep;
- one sealed confirmation rather than repeated holdout attempts; and
- one independent replication rather than correlated re-analysis.

Null, contradiction, data-defect, and boundary evidence are valuable outcomes.
The programme is successful as science if it reaches a trustworthy decision,
including termination.

---

## 5. Scientific rationale, mechanisms, and competing accounts

### 5.1 Rationale

Volatility clustering is a plausible market property, but its existence at an
aggregate level does not prove a useful single-security state. Equity data add
cross-sectional dependence, stable differences in tick size and liquidity,
changing universes, multiple share classes, and lifecycle attrition. A properly
designed equity programme must distinguish those sources.

If a security-linked residual range state persists after those challenges, it would
show that the observable post-close information set contains nontrivial
information about a later conditional expected range. If it does not, Project EDGE
can retire a large class of daily range-state features without constructing a
feature library or searching thresholds.

### 5.2 Prospective mechanisms

The following mechanisms are candidates only:

- persistent firm-specific information arrival;
- gradual resolution of uncertainty;
- multi-session adjustment to a firm-specific shock;
- persistent order-flow or participation imbalance;
- temporary liquidity deterioration; and
- propagation of a common market shock into heterogeneous security responses.

### 5.3 Serious competing accounts

- inherently volatile securities remain different from quiet securities;
- market-wide volatility clustering creates apparent stock-level recurrence;
- sector or peer propagation is mistaken for security-linked residual persistence;
- sparse trading, minimum ticks, stale prints, or zero-volume sessions distort
  high–low ranges;
- halts, suspensions, price limits, and reopening mechanics create persistence;
- corporate-action, identity, or row-basis errors create discontinuities;
- missing registered-horizon observations remove distressed or terminal securities;
- a small set of dates, issuers, or lifecycle states dominates the estimate;
- serially dependent outcomes and repeated observations create false precision; or
- selection, leakage, or mutable data create a non-reproducible result.

The Section 8.2 point-in-time sector and industry panels can reveal dominance
but are not a causal design. Without broader admitted peer histories and a
mechanism-led test, the programme cannot eliminate latent peer or sector
propagation. Explanatory maturity remains capped accordingly.

### 5.4 Falsification principle

The primary estimate is authoritative. Artifact challenges may invalidate,
narrow, or weaken it; they cannot replace it with a more attractive result. A
new measurement, subgroup, threshold, horizon, regime, or model observed after
outcome access is a new hypothesis outside this programme.

---

## 6. Programme population, clock, and evidence allocation

### 6.1 Population contract

Before any outcome-bearing access, governance must ratify:

- one geographic market and exactly one exchange;
- one currency;
- primary ordinary equity listings only;
- one stable analysis unit: the security’s ratified primary listing;
- one-primary-listing-per-issuer and multiple-share-class treatment;
- a point-in-time formation cohort constructed independently of bar
  availability and present-day survival;
- treatment of IPOs, relistings, acquisitions, bankruptcy, suspension, halt,
  inactivity, and delisting;
- exact start, end, lookback, outcome-maturity, and cutoff dates;
- minimum coverage and inferability requirements; and
- MDM retention, licensing, and replay authority.

Each evidence partition receives a cohort formed at its own start using only
then-admissible identity and lifecycle information. The cohort is followed
without deleting later inactive, acquired, bankrupt, suspended, or delisted
members. A new replication period receives a newly reconstructed cohort under
the identical rule.

The selected exchange shall be the one with the strongest pre-outcome audited
identity, lifecycle, calendar, OHLC, population, and replay coverage. It shall
not be selected because its range-persistence result is attractive.

### 6.2 Research clock

- Observation frequency: one governed exchange session.
- Feature cutoff: after the authoritative regular-session close of session `t`.
- Primary outcome: the immediately following governed session.
- Secondary duration outcome: one fixed trading-week clock defined in
  Experiment 4.
- Exposure/outcome pairs crossing a partition boundary are excluded
  prospectively.
- Outcomes must mature fully before entering any later estimation or review.

The exact MDM availability timestamp must precede the earliest future action
time before the phenomenon can be described as potentially
implementation-relevant. Scientific validity can remain intact if delivery is
later, but edge candidacy cannot.

### 6.3 Evidence partitions

Entire governed sessions, never individual stock rows, are allocated
chronologically into:

1. **measurement/development and discovery interval** — Stage 2.5 measurement
   challenges and Experiments 1–4;
2. **sealed confirmation interval** — Experiment 5 only; and
3. **direct-replication reserve** — Experiment 6 only.

Exact boundaries are chosen from coverage, effective-date counts,
dependence-aware power, and outcome maturity without inspecting the registered
relationships. The latest suitable interval should normally remain the
direct-replication reserve.

Because the raw range on a date can be a feature for one pair and an outcome for
the preceding pair, viewing range values or summaries in a sealed period can
consume that period. Confirmation and replication feature-view conformance must
therefore be performed blind by the custodian; only the registered release
decision becomes visible before the firewall opens.

If any purported holdout has already informed a feature, threshold, model,
horizon, or hypothesis choice, it is discovery data. It cannot regain sealed
status. If available history cannot provide discovery, confirmation, and
replication allocations with adequate effective dates, direct replication must
wait for prospective MDM observations.

### 6.4 Missing, halted, and terminal observations

Every cohort member remains in row and denominator accounting at each registered
horizon. Separate `t+1` and `t+5` outcome states are typed as valid, halted,
suspended, no-trade, source-absent, unexplained, quarantined, inactive,
delisted, or terminal as applicable. The complete intervening `t+1` through
`t+5` lifecycle and trading-state path is retained for the fifth-session
analysis even though the intermediate ranges are not alternative outcomes.

No missing outcome is:

- converted to zero volatility;
- carried forward;
- imputed by default;
- dropped from denominator reporting; or
- replaced with a later reappearance.

Each continuous estimand is conditional on a valid observed range at its exact
registered horizon: `t+1` for the one-session claim and `t+5` for the duration
claim. A `t+5` observation is never replaced by an intervening value, and no
minimum-count or partial-window convention exists because Experiment 4 has one
endpoint only. Unless a separately preregistered missing-not-at-random
sensitivity or bound supports a broader statement, each claim is explicitly
limited to its own observed-outcome scope. Horizon-specific coverage, attrition,
lifecycle state, transition paths, and survivor-only diagnostics remain part of
the evidence and may invalidate or narrow the claim.

---

## 7. Required measurements and Stage 2.5 validation

### 7.1 Primary atomic feature

**Feature ID:** `EDGE.VOL.LOG_RANGE.D1.V1`

For security `i` on governed session `t`:

`R(i,t) = log(high(i,t) / low(i,t))`

The feature is defined only when:

- high and low are finite and strictly positive;
- `high >= low`;
- all supplied OHLC values satisfy the registered row-order invariant;
- the values share one documented observed-price basis within the row;
- identity, session, currency, unit, availability, and quality resolve;
- no unresolved action or identity state can make the same-row values
  incomparable; and
- the row’s scientific-use scope is admitted.

Zero range is retained when it is a valid observation and is accompanied by its
volume, staleness, and trading-state information. It is not silently treated as
missing.

No clipping, winsorisation, smoothing, thresholding, ranking, imputation, or
alternative range estimator is part of Version 1.

### 7.2 Outcome construction

The outcome uses the same measurement on `next_session(t)`. It is constructed
only inside the experiment’s governed outcome layer after the feature cutoff
and horizon are enforced. It must not be stored in, joined to, or used to fit
the feature-ready view before outcome access is authorised.

The one-week outcome in Experiment 4 is the same valid log-range measurement on
governed session `t+5`. Sessions `t+2` through `t+4` are not tested as alternate
outcomes, so Experiment 4 asks one clean question about persistence at an
interpretable trading-week endpoint. No other horizon is examined in this
programme.

### 7.3 Governed state and mask fields

The following are data-quality or analysis-state fields, not predictive
features and not alternative hypotheses:

- cohort and eligibility state;
- valid coherent-range state;
- lifecycle state;
- halt, suspension, no-trade, and stale state;
- positive, zero, or missing volume state;
- action and row-basis compatibility state;
- separate `t+1` and `t+5` outcome states and the intervening lifecycle path;
- inclusion/exclusion reason; and
- source, snapshot, policy, lineage, and admissibility references.

Security effects and formation-date effects are estimator controls, not
separate market features.

### 7.4 Stage 2.5 obligations

Before Experiment 1, the exact feature definition and exact generated view must
pass:

- deterministic and computational reproduction;
- point-in-time and cutoff correctness;
- outcome-firewall and leakage challenges;
- high/low arithmetic and numerical stability;
- zero-range, tiny-range, missing, stale, halt, and terminal behaviour;
- raw/adjusted basis and same-row multiplicative-invariance tests;
- sensitivity to only the small predeclared defensible conventions;
- MDM revision and correction behaviour;
- version, dependency, and software consistency;
- full source-to-feature lineage; and
- independent review for the exact population, period, cutoff, and use.

Validation must be outcome-blind. Predictive attractiveness cannot make a
feature valid. Confirmation and replication views each require their own blind
conformance record, even when the definition version is unchanged.

### 7.5 Features intentionally excluded

The programme does not require:

- adjusted or total returns;
- rolling volatility indicators;
- alternative lookbacks;
- ATR or technical indicators;
- sector, industry, index, peer, or regime **predictive features**;
- fundamentals or earnings;
- quote, spread, order-book, auction, or intraday features;
- options or implied volatility;
- feature combinations; or
- trading signals.

Any later use is a separate registered programme or formally approved
descendant with new evidence and complete ancestry.

Point-in-time capitalisation, sector, industry, liquidity, lifecycle, and
market-state fields required for the Stage 3 candidate-promotion dossier are
diagnostic segmentation and influence metadata, not predictive features or
additional phenomenon hypotheses.

---

## 8. Required MDM capabilities and execution blockers

### 8.1 Mandatory capabilities for all experiments

MDM must provide, for the exact bounded scope:

- stable issuer, security, listing, venue, symbol, share-class, and currency
  identity history;
- complete lifecycle history for active, inactive, halted, suspended, acquired,
  bankrupt, relisted, and delisted cohort members;
- a survivor-complete point-in-time formation population independent of bar
  availability;
- authoritative exchange sessions, timezone/DST, holidays, early closes,
  unscheduled closures, and exact previous/next-session links;
- raw observed daily OHLCV with units, basis, availability, quality, status, and
  vintage;
- authoritative price storage quantum or applicable tick-resolution metadata
  sufficient to assess high–low discreteness for the exact securities and dates;
- action, identity, and row-basis evidence sufficient to detect and quarantine
  internally incomparable OHLC rows;
- typed missing, halt, suspension, no-trade, and terminal states;
- one common cutoff and consistency token across the bounded source families;
- immutable IDs, schemas, source/logical hashes, correction lineage, retention,
  and exact replay;
- a scoped `Admissible conditional` decision restricted mechanically to the
  observed-range use;
- production policy and request-scope binding;
- independent real-data gate review;
- deterministic fresh-process reconstruction; and
- protected release custody and mutation-safe consumer access.

### 8.2 Stage-specific capabilities required before sealed confirmation

H01–H04 may produce bounded discovery evidence from the common capabilities in
Section 8.1. They do not by themselves authorise opening H05. Before candidate
promotion and sealed confirmation, MDM must additionally provide and Project
EDGE must admit, point in time:

- market capitalisation, or the exact admitted price and shares history needed
  to construct it without future shares or revisions;
- sector and adequately supported industry classification history with
  effective and availability time;
- liquidity and turnover inputs under one frozen definition;
- security age and lifecycle segmentation;
- market-state context sufficient for the registered descriptive stability
  panel; and
- complete coverage, missingness, lineage, version, and replay evidence for
  every diagnostic field.

Every diagnostic definition and version, input field, availability rule,
breakpoint, sparse-cell rule, weight, dominance tolerance, output role, and
promotion decision function is frozen from external definitions or prior
admissible information before any H01 or other Stage 3 outcome is inspected.
The underlying point-in-time data may be acquired and admitted later only
through a result-blind custodian process. Every derived capitalisation,
liquidity, turnover, lifecycle, or market-state diagnostic must have a
deterministic version, lineage record, measurement-validation evidence, and
exact-view conformance decision before it may describe or veto promotion. These
fields may describe and veto a candidate;
they cannot strengthen or rescue it. If any required dimension is unavailable
or not point-in-time correct, H01–H04 remain retained discovery evidence but the
programme stops before H05 at `L2 — Observed`, `exploratory-only`, or unresolved
as adjudicated.

### 8.3 Capabilities not required for initial discovery

Complete cash distributions and terminal-return amounts are not inputs to this
same-row range estimand. Fundamentals, earnings, quote, spread, order-book,
multi-currency data, and predictive uses of classification are not required.
Index-membership and broader peer histories may be deferred beyond the first
candidate-promotion gate, but remain outstanding Stage 4 debt wherever the
frozen validation panel requires them.

Their absence imposes hard interpretation limits:

- no return, gap, momentum, reversal, or price-continuity claim;
- no sector, industry, peer, or regime mechanism conclusion;
- no claim about participant identity;
- no transaction-cost comparison with the volatility effect;
- no formal capacity claim; and
- no profitability or strategy claim.

Terminal and lifecycle identities remain Mandatory even though terminal-return
amounts are not used, because missing terminal outcomes must remain visible.

### 8.4 Current execution blockers

At the date of this specification:

1. the MDM capability decision is blocked;
2. the Population and Time Contract is unratified;
3. no production scope is approved;
4. release authority is not configured;
5. the current Milestone 3 path cannot yet express the required scope-limited
   observed-price-only admission without also requiring a return view;
6. no real MDM feature-ready panel has been admitted and replayed;
7. `EDGE.VOL.LOG_RANGE.D1.V1` has not been implemented or passed Stage 2.5;
8. mutation-safe release-to-read custody remains incomplete;
9. no point-in-time capitalisation, classification, liquidity/turnover, or
   market-state diagnostic package has been admitted for Stage 3 promotion; and
10. the canonical Milestone 1 text must be available for final compliance review.

These are real blockers to their stated gates, not reasons to design more
infrastructure. Items 1–8 and 10 block initial empirical execution as
applicable. Item 9 blocks Stage 3 candidate promotion and H05, but need not delay
H01–H04 once their own prerequisites pass. Only the smallest work needed to
close each blocker for this exact programme is authorised.

---

## 9. Programme-wide scientific and statistical contract

### 9.1 Primary estimands

Let `R(i,t)` denote the validated log-range feature.

For each horizon, the target is an **equal-formation-date-weighted population
linear projection among valid observed-outcome pairs**, not an undefined pooled
stock-day regression. Every included formation date receives equal total
weight; within a date, each distinct eligible issuer receives equal weight.
The panel may be unbalanced because listing and outcome states are real. It is
not balanced by deleting short-lived securities. Issuers without sufficient
within-security variation remain in population and outcome-state accounting but
cannot identify the within-security slope. Exact minimum identification and
not-inferable rules are frozen before outcomes.

Experiment 1 estimates the non-gating one-way decomposition coefficient:

`R(i,t+1) = security_effect(i) + beta_WS * R(i,t) + error(i,t+1)`

Experiment 2 estimates the primary security-linked residual coefficient:

`R(i,t+1) = security_effect(i) + formation_date_effect(t) + beta_ID * R(i,t) + error(i,t+1)`

The security effect removes stable differences among naturally high- and
low-range securities. The formation-date effect removes common conditions
shared by the cross-section associated with the `t` to `t+1` pair. `beta_ID`
is therefore a conditional-mean linear-projection association net of common
dates, not a total market association, an entire-distribution effect, a uniquely
firm-specific effect, or a causal effect. Unobserved sector and peer propagation
can remain in the residual.

The registered point estimator is the equal-date-weighted fixed-effects within
estimator with a contiguous split-panel jackknife correction for finite-time
lagged-dependent-variable bias. Here `D` is the number of eligible ordered
formation dates in the estimation interval. If `b_F` is the full-period estimate and `b_A`
and `b_B` are estimates from the first and last `floor(D/2)` ordered formation
dates, the corrected estimate is `2*b_F - (b_A+b_B)/2`. When `D` is odd, the
central date appears in `b_F` but neither half estimate. Pairs crossing a split
boundary are purged. This rule has no outcome-selected fallback and is
immutable before outcome access; an infeasible correction makes the design
`not inferable` rather than authorising another estimator. Full-panel and
half-panel estimates are always reported. A design-calibrated, outcome-blind
finite-time bias assessment must show that remaining plausible bias cannot
cross the registered negligible or material-effect boundaries; otherwise the
experiment is `not inferable`.

The same weighting target and bias treatment apply to `beta_WEEK`. Date-block
resampling must rerun the complete estimator, not attach generic standard errors
to one fit. Equal-date and equal-issuer influence is reported so a large
surviving cross-section cannot substitute for independent time evidence.

### 9.2 Minimum relevant effects and decision regions

Before any exposure–outcome pair is inspected, the methods reviewer must ratify:

- `delta_WS`: the minimum scientifically relevant within-security recurrence;
- `delta_ID`: the minimum scientifically relevant security-linked residual
  recurrence net of common dates;
- `delta_WEEK`: the minimum relevant coefficient for the exact `R(i,t+5)`
  endpoint;
- the negligible-effect region around zero for each estimand;
- the confidence or compatibility level;
- dependence-aware minimum detectable effects and expected precision; and
- conditions under which the design is not inferable.

These numeric values cannot responsibly be fixed while actual MDM measurement
resolution, coverage, and effective-date counts remain unknown. Their meanings
are frozen by this programme: each is a carryover coefficient in the natural
log-range measurement, independent of trading profit, transaction costs, or an
observed candidate estimate. Numerical values must be set from measurement
resolution and scientific relevance using only non-outcome evidence, then
become immutable experiment metadata.

For every primary test:

- **supported** means the multiplicity-adjusted dependence-aware interval is
  wholly beyond the relevant-effect boundary in the registered direction;
- **precise null** means the adjusted interval lies wholly inside the registered
  negligible-effect region;
- **contradicted** means sufficiently precise evidence supports or contains
  only a scientifically material opposite effect;
- **inconclusive** means the interval cannot distinguish material support from
  negligible effect or contradiction; and
- **invalid** means data, feature, protocol, leakage, reproducibility, or
  inference integrity failed.

A p-value on its own never determines any state. Inconclusive is not a null.

### 9.3 Dependence-aware inference

The inferential unit is effective dates and date blocks, not raw stock-day rows.
The preregistration must address:

- serial dependence within securities;
- cross-sectional dependence within formation and outcome dates;
- persistent exposure states;
- repeated issuers and related share classes;
- event and lifecycle clustering;
- sparse or asynchronous trading;
- five-session temporal dependence in Experiment 4; and
- repeated use of the discovery interval.

The minimal preferred method is a governed resampling or covariance procedure
that preserves complete daily cross-sections and contiguous time dependence.
For example, a moving-date-block bootstrap may resample complete date panels,
retaining every security within each sampled date block. The exact block rule,
number of resamples, seeds, small-sample correction, and fallback must be fixed
before outcomes. They cannot be selected because they narrow the interval.

Power uses effective date blocks and issuer counts under the same dependence
assumptions as the primary estimator. Independent-row standard errors, random
stock-day train/test splits, and claims based on millions of nominal rows are
inadmissible.

### 9.4 Primary, secondary, diagnostic, and safety outputs

Each output receives one immutable role before execution:

- **primary:** determines the experiment decision;
- **ordered secondary:** tested only after its gate and under the registered
  hierarchy;
- **diagnostic:** describes shape, scope, or heterogeneity but cannot strengthen
  the claim;
- **safety sentinel:** may invalidate or narrow the experiment but cannot make
  it pass; or
- **exploratory exposure:** permanently consumes budget and cannot be promoted
  without new evidence.

Required diagnostics include effect magnitude in natural and standardised
units, full outcome distribution, effective dates and issuers, typed
missingness, lifecycle attrition, influence of dates and issuers, and the
deliberately survivor-only comparison.

### 9.5 Multiplicity and fixed-sequence gatekeeping

Experiments 1–4 form one finite discovery campaign. H01 and H02 are frozen
together and H02 executes after every H01 disposition unless a shared
prerequisite independently makes H02 invalid; H01 is a decomposition
diagnostic and cannot create, rescue, or terminate the candidate. H02 is the
first decision-bearing material-support test. H04 is the single ordered
duration test and becomes eligible only after H02 is supported and H03's
noncompensatory falsification gate is satisfied.

The exact policy is fixed-sequence control of the programme family-wise error
rate for material-support claims at the preregistered level: H02 is tested
first, and H04 is tested only after its gate. H01 is reported with an interval
as a labelled non-gating decomposition; H03's sentinels can only veto or narrow
the claim. The target error quantity, confidence level, interval sidedness, and
compatibility rules must be frozen before H01. No alternative multiplicity
policy may be selected after exposure.

The sealed confirmation family contains every claim that could reach the same
confirmation sample, including the one-session primary claim and the
predeclared trading-week ordered secondary claim. A discovery branch cannot
escape confirmation multiplicity merely because the other branch was not
selected.

There is exactly:

- one discovery allocation;
- one sealed confirmation opportunity; and
- one direct-replication opportunity under the initial programme budget.

Opening an interval for a failed, abandoned, diagnostic, or modified analysis
consumes it. Renaming or narrowing the claim does not restore independence.

### 9.6 Negative controls and falsification sentinels

The principal inferential negative control is a preregistered, date-preserving
reassignment of next-session outcomes across unrelated issuer identities. It
retains the same market dates and outcome distribution while destroying the
same-security link. Its matching restrictions, deterministic seeds or complete
permutation rule, number of repetitions, and decision boundary are fixed before
outcomes.

Other sentinels have narrower roles:

- future-derived or shifted-availability inputs are leakage sentinels and must
  be rejected by the pipeline;
- same-row multiplicative transformations are measurement-invariance tests;
- survivor-only results expose selection direction but never become primary;
- removal of predeclared influential dates or issuers is a fragility diagnostic;
- halt, suspension, zero-volume, stale, and lifecycle views test artifact
  concentration; and
- arbitrary lag shifts are not expected-null controls because genuine
  volatility persistence can make them non-null.

### 9.7 Amendment and refinement law

“Refine” does not mean try another scientific specification. It is permitted
only when:

- a documented data, implementation, or inferability defect is found;
- the original result remains retained as invalid or inconclusive;
- the amendment was allowed by the frozen branch or creates a new version;
- exposed dates remain discovery data;
- discovery and multiplicity ancestry remain complete; and
- fresh evidence exists for any changed scientific claim.

The initial programme authorises no outcome-triggered precision extension. An
inconclusive discovery, confirmation, or replication result closes the current
programme unresolved. Additional temporal observations require a prospective
new programme version, a new evidence allocation and sequential-error rule, and
must remain unexposed until approval.

### 9.8 Reporting and evidence retention

Every run deposits:

- exact commands, software/environment identity, seeds, and runtime;
- MDM, universe, feature, view, policy, protocol, and dependency fingerprints;
- complete row, cohort, exclusion, horizon-specific outcome-state, transition,
  and coverage accounting;
- every primary, secondary, diagnostic, sentinel, and failed output;
- adjusted and unadjusted evidence;
- Research Cost actuals and estimate variance;
- protocol deviations and invalidity reasons;
- independent review and adjudication; and
- Knowledge Base, continuous evidence-profile, scientific-debt, and Phenomena
  Interaction Graph updates.

Positive, null, contradictory, inconclusive, and invalid results receive the
same retention standard.

---

## 10. Ordered experiment sequence

### 10.1 Programme overview

| Order | Experiment | One precise uncertainty | Entry dependency | Exit on success |
|---:|---|---|---|---|
| 1 | `EDGE-VSP-H01` / `EDGE-VSP-E01` — one-way decomposition | What recurrence appears after stable security differences but before common-date adjustment? | Production data and Stage 2.5 gates | Execute the already-frozen primary H02 regardless of direction |
| 2 | `EDGE-VSP-H02` / `EDGE-VSP-E02` — primary common-date separation | Does a security-linked residual association remain after common-date effects? | H01 disposition deposited and H02 independently eligible; H01 support or validity is not required | Challenge artifacts |
| 3 | `EDGE-VSP-H03` / `EDGE-VSP-E03` — artifact falsification | Can observed trading-state, identity, missingness, survivorship, or concentration artifacts explain H02? | H02 supported | Test duration |
| 4 | `EDGE-VSP-H04` / `EDGE-VSP-E04` — fixed duration boundary | Does the full-domain state persist at the exact fifth governed session? | H03 supported and every noncompensatory sentinel satisfied | Freeze confirmation claim scope |
| 5 | `EDGE-VSP-H05` / `EDGE-VSP-E05` — sealed confirmation | Does the exact surviving claim confirm once in untouched later time? | H01–H04 frozen and Stage 3 candidate-promotion dossier passed | Independent replication |
| 6 | `EDGE-VSP-H06` / `EDGE-VSP-E06` — independent reconstruction then direct replication | Does an independently conforming implementation reproduce the claim on genuinely new outcomes? | H05 primary confirmed | Stage 5 synthesis and edge-relevance decision |

### 10.2 Experiment 1 — Within-security one-session recurrence

**Hypothesis ID:** `EDGE-VSP-H01`  
**Experiment-specification ID:** `EDGE-VSP-E01`  
**Question:** After stable security-level differences are removed, is a wider
range on session `t` materially associated with a wider range on the next
governed session?

**Population and unit:** Every eligible security-session exposure in the
discovery cohort with a valid feature, retaining complete denominator and
next-session outcome-state accounting.

**Exposure:** `R(i,t)`.  
**Outcome:** `R(i,t+1)`.  
**Comparator:** The registered security-effect null model without `R(i,t)`.  
**Decomposition estimand:** `beta_WS`.  
**Primary horizon:** One governed session.

**Null hypothesis:** `beta_WS` is non-positive or does not exceed the
prospectively ratified relevant-effect boundary.  
**Alternative hypothesis:** `beta_WS` is positive and exceeds `delta_WS`.

**Expected mechanism if supported:** A daily volatility state has temporal
memory within securities.  
**Competing mechanism still live:** Market-wide volatility clustering can
produce H01 even after stable security levels are removed.

**Falsification conditions:**

- feature availability or next-session mapping fails;
- outcome construction crosses the firewall;
- dependence-aware inference is not possible;
- the result depends on silent removal of missing or terminal rows;
- a few dates or issuers breach the registered influence tolerance; or
- deterministic reproduction fails.

**Decision after H01:**

- **Continue** to H02 after a supported, precise-null, contradicted,
  inconclusive, or H01-specific invalid result whenever H02 remains independently
  eligible. The H02 specification is already frozen and must not be changed in
  response.
- **Refine** only to repair an H01 data, leakage, inference, or reproducibility
  defect allowed by Section 9.7; the artifact family reserved for H03 is not run
  here.
- **Terminate execution, without a market inference,** only if an H01-invalidating
  prerequisite also makes H02 scientifically ineligible and cannot be repaired.

**Scientific learning:** H01 records how the estimate changes before common-date
adjustment. A positive, null, or opposite result can each reveal confounding or
suppression when compared with H02. H01 cannot establish or close the primary
candidate.

### 10.3 Experiment 2 — Security-linked residual recurrence beyond common dates

**Hypothesis ID:** `EDGE-VSP-H02`  
**Experiment-specification ID:** `EDGE-VSP-E02`  
**Dependency:** H01's disposition is deposited and H02's own prerequisites are
satisfied; neither H01 support nor H01 validity is itself required.  
**Question:** Does material same-security persistence remain after common
formation-date conditions are removed?

**Exposure and outcome:** Unchanged from H01.  
**Comparator:** The two-way security and formation-date effect model without
`R(i,t)`.  
**Primary estimand:** `beta_ID`.  
**Primary horizon:** One governed session.

**Material-support null:** After stable security and common-date effects,
`beta_ID <= delta_ID`. A small positive estimate is not automatically a precise
null; it is classified using Section 9.2's full interval regions.  
**Alternative hypothesis:** `beta_ID` is positive and exceeds `delta_ID`.

**Expected mechanism if supported:** Firm- or listing-linked uncertainty,
participation, or liquidity conditions persist beyond the common market state.
  
**Competing mechanisms still live:** Sector/peer propagation, trading-state
artifacts, and identity-linked data defects.

**Required interpretation:** H02 is a conditional association. It must state
the exact adjustment set and cannot be called a total or causal effect.

**Decision after H02:**

- **Continue** to H03 only if H02 is supported.
- **Refine** only to repair a prospectively allowed invalidity without changing
  the scientific claim or exposed evidence.
- **Terminate** the security-linked programme if H02 is a precise null or
  contradicted. Any evidence of a common-market state is retained but cannot
  trigger a silent pivot to a market-level programme.
- **Close unresolved** if H02 is valid but inconclusive or not inferable.
- **Close invalid** without a market conclusion if data, feature, protocol, or
  inference integrity fails and cannot be repaired under Section 9.7.

**Scientific learning:** H02 is the main residual-association gate. It
distinguishes a security-linked component net of common dates from a result that
merely timestamps market-wide volatility. It does not distinguish firm-specific
behaviour from unresolved sector or peer propagation.

### 10.4 Experiment 3 — Artifact and identity-linkage falsification

**Hypothesis ID:** `EDGE-VSP-H03`  
**Experiment-specification ID:** `EDGE-VSP-E03`  
**Dependency:** H02 supported.  
**Question:** Does the security-linked residual recurrence survive the concrete data,
trading-state, missingness, survivorship, concentration, and false-identity
accounts testable with the authorised MDM scope?

The authoritative claim remains the full-domain, valid-`t+1`-outcome `beta_ID`
from H02. H03 also registers a separate falsification estimand,
`beta_ID_LA`, in one prospectively defined low-artifact scope:

- coherent, positive, ordinary-session OHLC;
- no row-basis or identity ambiguity;
- no unresolved same-row action incompatibility;
- feature-time halt, suspension, no-trade, staleness, and volume masks that use
  information available no later than `t`; and
- the explicit valid-`t+1`-outcome condition already governing the continuous
  estimand.

Outcome-time missing, halt, suspension, inactivity, delisting, and terminal
states are never used to manufacture a favourable predictor-side filter. They
remain in the full denominator, MNAR evidence, and horizon-specific sentinel
reports. `beta_ID_LA` has its own population fingerprint and ancestry; it is not
the unchanged H02 coefficient and cannot replace or rescue an unsupported H02.

**Primary null:** The effect becomes negligible, reverses, or fails the
registered artifact decision after applying the frozen domain and sentinels.  
**Alternative:** A material positive `beta_ID` remains and no sentinel indicates
an artifact explanation.

**Noncompensatory safety evidence:**

- date-preserving cross-issuer outcome reassignment;
- typed missingness and lifecycle attrition;
- preregistered MNAR sensitivity where defensible;
- survivor-only comparison as a bias diagnostic;
- leave-one-influential-date and leave-one-influential-issuer diagnostics;
- outcome coverage by halt, suspension, volume, staleness, and terminal state;
- price/tick-resolution and low-price concentration using authoritative MDM
  price-unit or tick metadata; if unavailable, this sentinel is `not
  assessable` and H03 cannot declare the claim artifact-resistant;
- raw/adjusted basis and corporate-action row-coherence checks; and
- exact computational replay.

**Decision after H03:**

- **Continue** to H04 only if the primary estimate remains material and every
  safety sentinel passes its frozen rule, including compatibility of
  `beta_ID_LA` with the full-domain H02 claim. H04–H06 then carry forward the
  full-domain, horizon-specific observed-valid-outcome estimand only.
- **Refine:** no population refinement is authorised inside this programme. A
  restricted-domain claim requires a new hypothesis version and fresh evidence.
- **Terminate** if a registered artifact account explains the effect, the
  permutation control behaves like the true identity link, or influence is
  unacceptable.
- **Close invalid** rather than infer when data or sentinel integrity fails;
  `not assessable` on a material artifact risk cannot be treated as a pass.
- **Close unresolved** when valid sentinel evidence cannot distinguish an
  artifact explanation from an artifact-resistant effect.

Diagnostics cannot select a favourable subgroup. An effect restricted to an
unexpected price, liquidity, lifecycle, or market segment is recorded as an
exploratory exposure and does not rescue the programme.

### 10.5 Experiment 4 — Fixed trading-week duration boundary

**Hypothesis ID:** `EDGE-VSP-H04`  
**Experiment-specification ID:** `EDGE-VSP-E04`  
**Dependency:** H03 supported and every noncompensatory sentinel satisfied.  
**Question:** Does the unchanged full-domain security-linked residual range state remain material
beyond the immediate next session?

**Exposure:** `R(i,t)`.  
**Outcome:** `R(i,t+5)`, the same measurement on the fifth governed session.  
**Comparator:** The registered security and formation-date effect model without
the exposure.  
**Primary estimand:** `beta_WEEK`.  
**Horizon:** One fixed trading-week clock; no intermediate horizon search.

**Material-support null:** `beta_WEEK <= delta_WEEK` at the exact fifth governed
session. Small positive but scientifically immaterial evidence is classified by
the full Section 9.2 interval regions.  
**Alternative hypothesis:** `beta_WEEK` is positive and exceeds `delta_WEEK`.

The covariance or resampling method must represent five-session temporal
dependence. Partition boundaries must purge any pair whose outcome crosses the
boundary; an arbitrary embargo does not substitute for the registered
information path.

The H04 target uses the same full-domain formation rule as H02 and is conditional
only on a valid `t+5` range. Every cohort exposure retains a typed `t+5` outcome
state and the intervening lifecycle/trading-state path under Section 6.4. H04
cannot substitute `t+2`, `t+3`, or `t+4` when `t+5` is unavailable.

**Decision after H04:**

- **Continue** with both one-session and trading-week scope if supported.
- **Refine** to the preregistered one-session-only claim if H04 is a precise
  null, contradicted, or inconclusive but H02–H03 remain supported. The duration
  result remains visible; no different horizon may be tried.
- **Terminate** if the H04 result or its missingness reveals that the H02–H03
  claim itself was unstable or artifact-driven.
- **Close H04 invalid and continue only with the one-session claim** if the
  failure is demonstrably confined to the fifth-session outcome; invalidate the
  whole candidate if the failure also compromises H02 or H03.

H04 determines boundary, not whether the H02–H03 one-session candidate existed.
Its lower ESIG is
accepted because duration is a declared meaning of persistence and its exact
scope must be frozen before sealed confirmation. Running it later would turn
the confirmation result into a horizon-selection device.

### 10.5A Stage 3 candidate-promotion gate — not a new experiment

H05 remains locked until an independent methods reviewer approves one immutable
H01–H04 discovery dossier satisfying the Foundation's Stage 3 reporting and
candidate-promotion gate. The dossier must contain:

- all registered analyses, deviations, feature/view decisions, dependency
  states, discovery-budget consumption, Research Cost records, MDM lineage, and
  multiplicity ancestry;
- effect sizes in natural and standardised units, dependence-aware uncertainty,
  response shape, and the exact `t+1`/`t+5` horizon profile;
- counts of dates, issuers, securities, sectors, industries, and effective
  independent units, with complete typed coverage and missingness;
- temporal stability and influence diagnostics for dates and issuers;
- descriptive point-in-time capitalisation, liquidity/turnover, sector,
  adequately supported industry, lifecycle, and market-state panels under the
  frozen Section 8.2 definitions;
- explicit dominance tests showing that the candidate is not driven by a few
  dates, issuers, sectors, or micro-cap observations;
- every H03 negative control, artifact challenge, sensitivity, and unresolved
  rival explanation; and
- the exact supported, precise-null, contradicted, inconclusive, invalid, or
  exploratory-only disposition.

These panels are diagnostics and safety evidence, not additional hypothesis
families, feature combinations, subgroup claims, or opportunities to select a
favourable population. Sparse or heterogeneous cells remain visible. A panel
cannot make H02 or H04 pass, but a registered dominance failure can terminate
promotion. `Not assessable` on a required dimension, an unapproved deviation,
or failure of any other noncompensatory promotion condition blocks H05. The
sealed confirmation interval must remain unopened.

### 10.6 Experiment 5 — Sealed temporal confirmation

**Hypothesis ID:** `EDGE-VSP-H05`  
**Experiment-specification ID:** `EDGE-VSP-E05`  
**Dependency:** The H01–H04 discovery disposition, exact surviving claim, and
complete confirmation family are frozen, and Section 10.5A has passed.  
**Question:** Does the unchanged security-linked residual, artifact-resistant claim
confirm once on a chronologically later, untouched interval?

The feature version, population rule, estimator, effect boundary, dependence
method, missingness rules, sentinels, output roles, and decision function are
unchanged. A blind conformance build does not allow analysts to inspect sealed
values before release.

**Primary hypothesis:** The one-session `beta_ID` exceeds its registered
materiality boundary on sealed evidence.  
**Ordered secondary:** The trading-week claim is tested only if H04 supported it
and only under the frozen family-wise hierarchy.

**Confirmation success requires:**

- the sealed primary interval wholly exceeds the relevant-effect boundary;
- the estimate satisfies the preregistered discovery-to-confirmation prediction
  or compatibility rule;
- no sign reversal or material unexplained attenuation;
- all data, feature, missingness, artifact, and replay sentinels pass;
- fold-level evidence does not reveal registered incompatible instability; and
- discovery and confirmation estimates are reported separately before
  synthesis.

Before release, the custodian partitions the sealed interval into three
contiguous, non-overlapping blocks with as equal a number of eligible formation
dates as possible; any remainder is assigned from earliest to latest blocks.
Exact date hashes, boundary purges, minimum effective-date rules, and the
incompatibility veto are preregistered. The complete sealed interval is primary;
block estimates are temporal-stability safety diagnostics and cannot rescue it.
Calendar-time, capitalisation, sector, adequately supported industry,
liquidity/turnover, lifecycle, and market-state panels admitted for Section
10.5A are repeated descriptively on the sealed sample. They cannot strengthen
or rescue the primary decision, and a registered safety failure may veto it.
Additional index, peer, and broader Stage 4 panels are reported only when their
MDM histories are admitted; otherwise the exact dimension is `not assessable`,
scientific debt is recorded, and later L5 maturity remains blocked.

**Decision after H05:**

- **Continue** to H06 only if the primary claim confirms.
- **Refine** to a one-session-only replication claim if the primary confirms but
  the ordered `t+5` secondary is a precise null, contradicted, inconclusive, or
  horizon-confined invalid. The secondary failure remains visible.
- **Terminate/not confirm** after a valid primary precise null, contradiction,
  or confirmation incompatibility.
- **Close unresolved** after a valid but inconclusive primary result; no
  outcome-triggered extension is authorised.
- **Close invalid** without a market inference if sealed-sample or protocol
  integrity fails. The opened interval remains permanently consumed.

No narrowed descendant may reuse this confirmation interval as untouched
evidence.

### 10.7 Experiment 6 — Independent reimplementation and direct replication

**Hypothesis ID:** `EDGE-VSP-H06`  
**Experiment-specification ID:** `EDGE-VSP-E06`  
**Dependency:** H05 confirmed.  
**Question:** Can a separate implementation reproduce the exact confirmed claim
on genuinely new eligible outcomes?

H06 has two locked phases so implementation disagreement is not confused with a
change in market time.

**Phase A — same-input independent reconstruction gate.** A separate analyst or
team receives the frozen specification and already opened inputs, but neither
the original source code nor the original analytical outputs or decisions. It
independently reconstructs the panel, feature, masks, weights, estimators,
intervals, and decisions. Before comparison, the independent team deposits and
hash-freezes its complete result, code, environment, dependency manifest, and
output schema. Only then may an adjudicator reveal the original outputs and
compare cohort keys, state counts, feature values, population fingerprints,
weights, coefficients, uncertainty outputs, and decisions under prospectively
frozen exact or numeric tolerances.

A material discrepancy closes the current Phase A as invalid; iterative
debugging against revealed outputs cannot turn that exposed attempt into H06
eligibility. If adjudication identifies a material defect in the original
implementation, the affected H01–H05 evidence and confirmation are invalidated,
the evidence profile and scientific-debt register are updated, and the temporal
replication reserve remains sealed. Phase-A failure is not evidence for or
against the market hypothesis. Any later reconstruction attempt requires a new
governed version and a fresh independence review.

**Phase B — direct temporal replication.** Only after Phase A passes does the
sealed independent implementation run once on:

- an untouched later interval and a new point-in-time formation cohort under
  the identical rule; or
- prospectively accumulated MDM observations if no historical interval remains
  genuinely untouched.

The independence record states personnel, codebase, environment, dependency
build, data snapshot/vintage, cohort construction, and temporal-outcome
independence. MDM remains the same authorised source by constitution; the
hypothesis, feature definition, estimand, and decision rule remain the same by
design.

**Null:** The new-outcome estimate fails the registered direction,
materiality, or compatibility region.  
**Alternative:** The estimate remains material and compatible with the frozen
replication prediction under the registered heterogeneity rule.

Replication success is not “another p-value below 0.05” and is not
confidence-interval overlap. It requires the preregistered prediction,
compatibility, or meta-analytic heterogeneity criterion.

The one-session H05 claim is the H06 primary. The `t+5` claim is an ordered
secondary only if it passed both H04 discovery and H05 confirmation. Phase B
tests the primary first under the frozen hierarchy. Failure of only the ordered
secondary removes the duration claim but cannot erase a validly replicated
one-session claim unless the same evidence exposes a shared artifact or
integrity failure.

Accordingly, H06 primary success with secondary failure yields an L4
**one-session-only** candidate and partial programme success. The maximal
all-six-experiments success case requires both the one-session primary and the
eligible `t+5` ordered secondary to satisfy their replication rules.

**Decision after H06:**

- **Continue — maximal success:** after Phase A conformance and valid Phase B
  replication of both the primary and eligible `t+5` secondary, deposit an L4
  directly replicated `t+1` and `t+5` candidate for Stage 5 synthesis.
- **Continue — narrowed success:** if the primary replicates but the ordered
  secondary does not, deposit an L4 one-session-only candidate, permanently
  retain the weakening duration evidence, and do not call the full programme
  successful.
- **Refine:** no outcome-driven refinement is permitted inside this programme.
  A materially different claim requires a new programme, budget, and fresh
  evidence.
- **Terminate/not replicate:** after a valid Phase B primary incompatibility,
  precise null, or contradiction. This is the only evidence-based H06 failure.
- **Remain unresolved:** after a valid but imprecise Phase B primary result;
  await a separately governed allocation of genuinely new observations without
  claiming persistence.
- **Close Phase A or Phase B invalid:** when its own data, protocol, or execution
  fails. Such a run is reproducibility or scientific debt, cannot count against
  the phenomenon, cannot validate it, and may be repaired only under the frozen
  amendment and evidence-exposure rules. Phase A failure leaves the temporal
  reserve unopened.

---

## 11. Discovery budget and evidence budget

### 11.1 Initial exploration allocation

The following is the maximum authorised exploratory freedom for
`EDGE-VSP-001`. It is a research-drift budget, not a compute allowance or
multiplicity correction.

| Budget dimension | Maximum authorised amount |
|---|---:|
| Phenomenon families | 1 |
| Atomic exposure feature definitions | 1 |
| Feature transformations | 1: the declared logarithmic ratio |
| Feature combinations | 0 |
| Discovery hypotheses | 4, fixed as H01–H04 |
| Primary outcome clocks | 2: next session and fixed trading week |
| Forecast-horizon grid cells | 0 |
| Alternative lookbacks | 0 |
| Threshold searches or outcome-selected bins | 0 |
| Regime partitions | 0 |
| Confirmatory subgroup claims | 0 |
| Primary estimator specifications | 2, ordered: security effects, then security plus formation-date effects |
| Registered artifact-domain challenge | 1 |
| Inferential negative-control family | 1: date-preserving cross-issuer reassignment |
| Sealed confirmation opportunities | 1 |
| Independent direct-replication opportunities | 1 |

The full and low-artifact views are one preregistered primary-plus-falsification
pair. They cannot seed searches for a better price, liquidity, volume, age,
sector, or lifecycle threshold.

### 11.2 Consumption rules

A budget unit is consumed when outcome-bearing information could influence a
decision, including:

- a completed analysis;
- a failed run that exposed an outcome summary;
- an abandoned estimator or diagnostic;
- an informal plot, notebook, query, or automated screen;
- a holdout conformance process that reveals values or distributions; or
- a result described as “only a check” but capable of changing the next action.

Mechanical failure before any outcome-bearing output may release a reservation
only after an independent recorded decision.

### 11.3 Exhaustion

When any limit is consumed, additional exploration is blocked. Governance may
only:

1. validate the already frozen claim;
2. conduct an evidence review and close or narrow the programme under an
   existing branch; or
3. approve a new prospective programme budget with complete ancestry, a
   scientific rationale independent of result direction, and genuinely
   unexposed evidence.

A favourable, disappointing, nearly significant, cheap, or commercially
interesting result is not a valid expansion reason.

### 11.4 Statistical and evidence allocation

The discovery campaign, confirmation family, and programme-sequential decision
rule remain separate from the discovery budget:

- H01 is a non-gating decomposition and H02 then H04 use the exact registered
  fixed-sequence discovery-family policy, with H03 as a noncompensatory veto;
- H05 uses strong family-wise control for all claims eligible to enter its one
  sealed interval;
- H06 uses the preregistered replication prediction or compatibility rule; and
- later repeated confirmation opportunities require a new finite sequential
  allocation or approved always-valid framework.

Every raw and adjusted result remains visible.

---

## 12. Expected Scientific Information Gain and Research Cost

### 12.1 ESIG principles

ESIG is frozen before outcomes and is independent of whether a result is
positive. A precise null that ends the family can have greater information gain
than a weak positive result. ESIG affects scheduling only after scientific
eligibility; it never alters evidential interpretation.

### 12.2 ESIG ranking

Ranks express programme-start expected marginal learning after accounting for
the probability that a dependency is reached. The qualitative bands are broad;
two experiments in the same band need not have identical ESIG. “Once eligible”
states the conditional value of confirmation or replication and does not move it
ahead of an unmet scientific dependency.

| ESIG rank | Experiment | Expected ESIG | Outcome-independent contribution |
|---:|---|---|---|
| 1 | H02 — common-date separation | Very high | It is the first decisive phenomenon test and resolves the central ambiguity between a security-linked residual association and a common market timestamp. |
| 2 | H01 — one-way decomposition | High | It cheaply shows how stable-security adjustment behaves and reveals inflation or suppression when compared with the already-frozen H02, but cannot close the family. |
| 3 | H03 — artifact falsification | High | Can invalidate a candidate before sealed evidence is consumed and directly tests the most credible data and microstructure rivals. |
| 4 | H05 — sealed confirmation | Very high once eligible | Untouched later evidence determines whether the discovery survives selection and historical specificity. Its conditional value is high, but it cannot run before H04 fixes scope. |
| 5 | H06 — independent replication | Very high once eligible | Separates implementation reproducibility from new-time compatibility and determines whether the claim reaches directly replicated candidate status. Its value exists only after confirmation. |
| 6 | H04 — duration boundary | Medium–high | Clarifies whether the phenomenon lasts beyond one session; useful but not necessary to decide whether one-session recurrence exists. |

Execution order remains H01 → H02 → H03 → H04 → H05 → H06. H01 precedes H02
only as a locked, non-gating decomposition on the same admitted data. H04
precedes the higher-conditional-ESIG holdout work because its single duration
claim must be fixed before confirmation. ESIG rank does not override
dependencies, artifact checks, or evidence preservation.

### 12.3 Learning from every possible result

| Result class | Programme learning |
|---|---|
| H01 decomposition — any valid result | Inflation, suppression, or agreement relative to the already-frozen H02 is learned; H02 still executes. |
| Supported at a decision-bearing gate | The named uncertainty is reduced and the next dependency may unlock. |
| Precise null at a decision-bearing gate | A materially meaningful version of that claim is absent in the tested domain; only the descendants governed by that gate close. |
| Contradicted at a decision-bearing gate | The expected direction is wrong and anti-persistence or decay evidence is retained without reversal mining; the registered gate determines closure. |
| Inconclusive at a decision-bearing gate | Available effective evidence cannot decide; that branch closes or waits rather than searching specifications. |
| Invalid | MDM, measurement, inference, or governance debt is exposed; H02 proceeds after an H01-specific invalidity only when its own prerequisites remain valid. |

### 12.4 Research Cost planning

Exact CPU, memory, storage, runtime, data volume, and statistical-complexity
estimates cannot be made until the bounded real MDM snapshot, row counts,
effective dates, and resampling policy exist. Before scheduling, every
experiment receives its permanent numeric or bounded-range Research Cost record.

Initial relative planning is:

| Experiment | Relative computational work | Dominant driver |
|---|---|---|
| H01 | Moderate | Repeated-panel estimation and date-block inference |
| H02 | Moderate | Two-way adjustment and date-block inference |
| H03 | Moderate | Frozen permutation control, influence, missingness, and replay sentinels |
| H04 | Moderate–high | Fifth-session outcomes and longer temporal-dependence blocks |
| Stage 3 promotion dossier | Moderate and source-dependent | Point-in-time diagnostic joins, segment coverage, dominance tests, and independent review |
| H05 | Moderate | One blind conformance build and locked confirmation execution |
| H06 | Moderate plus independent labour | Same-input independent reconstruction gate, sealed code/manifest, new snapshot/view conformance, and one temporal replication inference |

The scheduler should complete the low-cost decomposition and terminal tests H01–H03 before consuming
confirmation data or independent-replication effort. Lower cost does not excuse
an inadmissible or underpowered design.

---

## 13. Programme success criteria

### 13.1 Minimum evidence required to continue deeper

The programme continues beyond discovery only when:

- the H01 disposition is deposited, and any H01 invalidity is either repaired
  or independently adjudicated as H01-specific and non-material to H02;
- H02 demonstrates a material security-linked residual component after common-date
  adjustment;
- H03 retains that effect without a failed integrity, identity, trading-state,
  missingness, survivor, concentration, permutation, or replay sentinel;
- effect size and precision meet the pre-outcome materiality rule;
- the response is not dominated by a few dates, issuers, sectors, or micro-cap
  observations under the frozen influence rules;
- every mandatory point-in-time capitalisation, liquidity/turnover, sector,
  industry, lifecycle, and market-state diagnostic in Section 10.5A is complete;
- the feature and every exact view remain Stage 2.5 eligible;
- discovery and multiplicity budgets are intact;
- an independent methods reviewer approves the complete Stage 3 candidate
  dossier; and
- sufficient untouched confirmation and replication evidence remains.

H04 determines whether the continuation claim includes trading-week duration or
is restricted to the immediately following session.

### 13.2 Complete programme success and maturity ceiling

Full success requires all six experiments to complete validly and successfully:

1. H01 completes validly and its non-gating decomposition is retained, whatever
   its direction.
2. H02 materially supports the security-linked residual conditional
   association net of common dates.
3. H03 survives every noncompensatory artifact and integrity challenge.
4. H04 materially supports persistence beyond the immediate session.
5. H05 confirms the unchanged one-session primary and the eligible `t+5`
   ordered secondary on sealed later evidence.
6. H06 passes result-blind same-input independent reconstruction and directly
   replicates both the one-session primary and the eligible `t+5` ordered
   secondary on genuinely new temporal outcomes.

The literal all-six-experiments success case includes a valid H01. An
independently adjudicated H01-specific invalidity does not block an otherwise
valid H02–H06 path to an L4 candidate, because H01 is diagnostic and non-gating;
the unresolved decomposition remains visible scientific debt.

In addition:

- discovery, confirmation, and replication estimates remain separately visible;
- temporal heterogeneity is compatible with the registered claim;
- all population and missing-outcome boundaries are retained;
- deterministic reconstruction succeeds throughout;
- no unapproved exploration or protocol amendment occurred;
- every result and cost record is deposited;
- the Knowledge Base and continuous evidence profile are updated; and
- Stage 5 synthesis updates the candidate evidence profile without bypassing any
  outstanding Stage 4 gate.

The maximum scientific conclusion from full programme success is an **L4
directly replicated `t+1` and `t+5` observed-range-persistence candidate** within
the exact declared domain. If only the H06 primary replicates, the maximum is an
L4 one-session-only candidate and the programme is partially, not fully,
successful. Neither state is `validated` or `validated-conditional` knowledge.

### 13.3 Outstanding Foundation Stage 4 validation

This bounded first programme deliberately does not delay discovery until every
wider validation data family exists. It also cannot waive those gates. Before
the Knowledge Base may assign `validated` or `validated-conditional` maturity,
a later preregistered validation programme must complete every applicable
frozen Stage 4 obligation, including:

- rolling-origin/walk-forward and rolling-window stability beyond this single
  confirmation and replication sequence;
- point-in-time market-capitalisation, sector, industry, liquidity, lifecycle,
  and other required transportability panels;
- bull/bear market and high/low-volatility state diagnostics under frozen
  definitions;
- complete survivorship, missingness, multiple-testing, and robustness-profile
  synthesis;
- transaction-cost and capacity relevance where an economic implementation
  claim is proposed; and
- the Foundation's independent review and evidence-ladder gates.

An unavailable dimension is `not assessable` and becomes visible scientific
debt; it is never a pass. These later obligations remain within the same
phenomenon family but are outside the first bounded programme and do not delay
the first discovery result.

### 13.4 Edge-relevance decision after scientific success

After H06, a separate non-optimising implementation-relevance review records:

- exact feature availability time and earliest possible response time;
- whether any part of the measured outcome occurs before the feature is usable;
- opportunity breadth and issuer concentration;
- observed price, volume, and liquidity descriptors available from admitted
  MDM fields;
- concentration in abnormal, stale, illiquid, low-price, or lifecycle states;
  and
- whether implementation relevance is `not applicable`, `not assessable`,
  `artifact-exposed`, or sufficiently broad and timely to warrant a later Stage
  6 feasibility proposal.

The review must not subtract spreads or costs from a log-range coefficient;
those quantities have different units. It must not invent an instrument,
direction, position, or portfolio.

If the observation is not available before material portions of the future
outcome occur, or the effect exists only where executable exposure is not
credible, the phenomenon may remain scientifically valid while this family is
terminated as a route toward a trading edge.

---

## 14. Failure criteria and exact abandonment rule

### 14.1 Programme-level failure

The bounded family receives an evidence-based termination if any of the
following occurs after a valid, adequately powered execution:

1. H02 is a precise null or material contradiction.
2. H03 shows that data, common exposure, identity, trading state, missingness,
   survivorship, concentration, or a false identity link explains the result.
3. H04 exposes missingness, instability, or an artifact that also invalidates
   the one-session H02–H03 claim rather than only the fifth-session outcome.
4. The complete Stage 3 dossier shows that a few sectors or micro-cap
   observations dominate the candidate under the frozen influence rule.
5. H05's primary claim is a precise null, contradicted, or incompatible with the
   registered discovery prediction.
6. H06 Phase B validly fails primary direct-replication compatibility.

H04 alone does not erase a supported one-session phenomenon. A precise null or
inconclusive H04 result activates only the preregistered one-session boundary;
no other duration may be searched.

### 14.2 Data-limited closure is not a market null

If MDM cannot provide the required identity, survivor population, calendar,
coherent OHLC, replay, missingness, or unexposed effective dates, the programme
closes as **data-limited** or **invalid**, not as evidence that range persistence
is absent.

If the Section 10.5A capitalisation, liquidity, classification, lifecycle, or
market-state diagnostics are unavailable or not point-in-time correct, the
programme stops before H05 with L2 discovery evidence. That is a promotion-data
limitation, not a market null and not authority to open the holdout.

If a valid run remains underpowered, its state is **inconclusive**, not a
scientific null. Further work waits for genuinely new information; it does not
search for a stronger specification.

An H01, H02, H03, H04, H05, H06 Phase A, or H06 Phase B integrity failure closes
the affected execution as **invalid** unless a prospectively authorised repair
is possible. A material governance breach, concealed search, leakage, mutable
input, or failed independent reconstruction is scientific debt, not evidence
that the market phenomenon is absent. An inconclusive, data-limited, or invalid
closure is not described as abandonment.

### 14.3 Meaning of “abandon the family entirely”

The family being abandoned is deliberately bounded:

> security-level regular-session daily observed-range persistence in the
> ratified one-exchange, one-currency, primary ordinary-equity population under
> the frozen feature, clocks, estimands, and materiality rules.

Abandonment means:

- no threshold, lookback, horizon, regime, subgroup, estimator, or related
  range-feature rescue within the existing budget;
- no descendant presented as independent merely because it is renamed;
- all evidence and scientific debt remain permanent; and
- reopening requires genuinely new MDM capability, independent mechanism
  evidence, or new temporal outcomes, followed by formal evidence review, a new
  programme version, new discovery budget, complete ancestry, and unexposed
  evidence.

It would be scientifically invalid to claim that one bounded daily programme
proves that every possible volatility phenomenon in all equity markets is
absent.

---

## 15. Decision tree

```text
Real MDM admission, release custody, or Stage 2.5 fails
    └── BLOCK / INVALID — repair the named prerequisite; do not infer

H01: material within-security recurrence?
    ├── valid supported / null / contradicted / inconclusive ── H02 UNCHANGED
    └── invalid
        ├── H01-specific and H02 independently eligible ── H02 UNCHANGED + DEBT
        └── shared prerequisite compromises H02 ── REPAIR or CLOSE INVALID

H02: material security-linked residual component after common-date effects?
    ├── precise null or contradicted ── TERMINATE SECURITY-LEVEL FAMILY
    ├── inconclusive ── CLOSE UNRESOLVED under the precision rule
    ├── invalid ── CLOSE INVALID; NO MARKET INFERENCE
    └── supported ── H03

H03: survives artifacts, missingness, concentration, and false-identity control?
    ├── artifact explanation ── TERMINATE
    ├── not assessable / invalid ── CLOSE INVALID OR UNRESOLVED; DO NOT PASS
    └── yes ── H04

H04: material persistence beyond next session on the fixed trading-week clock?
    ├── precise null / contradicted / inconclusive ── one-session-only claim
    ├── horizon-confined invalid ── one-session-only claim; record debt
    ├── shared invalidity ── CLOSE CANDIDATE INVALID
    └── yes ── retain one-session primary plus ordered duration claim

Every surviving one-session or one-session-plus-duration branch
    │
    ▼
Stage 3 promotion dossier complete and not segment-dominated?
    ├── no / required dimension not assessable ── STOP AT L2; DO NOT OPEN H05
    └── yes ── H05

H05: exact claim confirms once on sealed later evidence?
    ├── primary null / contradicted / incompatible ── TERMINATE; DO NOT CONFIRM
    ├── primary inconclusive ── CLOSE UNRESOLVED; evidence stays consumed
    ├── invalid ── CLOSE INVALID; evidence stays consumed
    └── primary confirmed ── freeze one-session claim; retain t+5 only if it confirms
                              │
                              ▼
H06 Phase A: independent same-input reconstruction conforms?
    ├── no / invalid ── SCIENTIFIC DEBT; NO MARKET INFERENCE; RESERVE STAYS SEALED
    └── yes ── seal independent implementation; open Phase B once

H06 Phase B: primary replicates on genuinely new outcomes?
    ├── precise null / contradicted / incompatible ── DO NOT REPLICATE; TERMINATE
    ├── inconclusive ── REMAIN UNRESOLVED; await new outcomes
    ├── invalid attempt ── NO INFERENCE; repair only under frozen exposure rules
    └── yes
        ├── eligible t+5 secondary replicates ── FULL L4 t+1 + t+5 CANDIDATE
        └── t+5 absent / fails ── PARTIAL L4 ONE-SESSION-ONLY CANDIDATE
```

Every branch is frozen before H01. “Refine” never authorises outcome-driven
parameter changes.

---

## 16. Minimum enabling work and execution order

The programme requires no generic discovery engine or feature factory. The
minimum path is:

1. make the canonical Milestone 1 text available for compliance review;
2. ratify the exact one-market Population and Time Contract;
3. obtain the bounded immutable initial-discovery MDM snapshot required by
   Section 8.1;
4. implement the already frozen conditional observed-price admission and bind
   the exact production policy and scope;
5. pass every applicable real-data admission, coverage, replay, review, release,
   backup, and mutation-safe access gate from Milestone 4;
6. implement only `EDGE.VOL.LOG_RANGE.D1.V1` and its outcome builder;
7. complete Stage 2.5 definition validation and exact-view conformance;
8. ratify the numeric minimum effects, inferability rules, dependence method,
   partitions, discovery budget, and evidence allocation without outcome
   inspection;
9. create the programme charter and immutable, jointly frozen H01 and H02
   hypothesis and experiment-specification records, plus every dependency,
   Research Cost, ESIG, and scheduler-eligibility record;
10. execute H01–H04 under the fixed stopping rules;
11. before H05, admit the additional point-in-time diagnostic data in Section
    8.2 and pass the immutable Stage 3 dossier in Section 10.5A; and
12. only after promotion passes, open H05 once and then execute H06 under its
    two-phase gate if eligible.

Steps 1–5 are infrastructure only because they genuinely block valid evidence.
Steps 6–10 produce the first discovery result. Step 11 is scientifically
Mandatory for candidate promotion but should not delay H01 or H02. No wider
Stage 4 or enterprise enhancement should delay the first discovery result.

---

## 17. Knowledge Base and programme closure

After every experiment, the Knowledge Base receives:

- hypothesis and experiment identities;
- complete provenance and data-exposure ancestry;
- supported, precise-null, contradicted, inconclusive, or invalid finding;
- effect, uncertainty, heterogeneity, missingness, and boundary evidence;
- mechanism and rival-account assessment;
- exact continue, refine, or terminate decision and rationale;
- actual discovery-budget and Research Cost consumption;
- computational reproduction and review record;
- continuous evidence-profile update;
- scientific-debt changes; and
- Phenomena Interaction Graph assessment, including `not assessable` or
  `no relationship proposed` where appropriate.

Closing or terminating the programme never deletes it. A negative programme is
a permanent map of a branch that Project EDGE need not unknowingly repeat.
Even after full programme success, the lifecycle ceiling is `candidate` at L4
until the outstanding Foundation Stage 4 gates in Section 13.3 are completed.

---

## 18. Principal scientific risks and residual limitations

| Risk | Programme control | Residual limitation |
|---|---|---|
| Stable security differences mistaken for state persistence | Security effects in H01 | Time-varying unobserved security traits may remain |
| Common market dates mistaken for security information | Formation-date effects in H02 and date-preserving inference | Sector/peer propagation remains unresolved without admitted histories |
| Finite-time bias in lagged-outcome fixed-effects models | Frozen split-panel jackknife, full/half estimates, and outcome-blind bias bound | Correction can reduce precision and may render short panels not inferable |
| Stock-day pseudo-replication | Complete-date block inference and effective-date power | Finite market histories limit independent time evidence |
| Survivorship and terminal attrition | Formation cohorts, lifecycle retention, missing-denominator and survivor-only artifacts | Broad claims remain conditional when MNAR uncertainty cannot be bounded |
| Tick, stale-price, zero-volume, halt, or action artifacts | Stage 2.5 plus H03 safety sentinels | Daily OHLC cannot resolve every microstructure mechanism |
| Multiple testing and research drift | Finite budget, fixed sequence, one confirmation and one replication | A later new programme still carries full ancestry |
| Holdout contamination | Chronological firewall and blind conformance | Previously viewed history cannot become independent again |
| Single MDM source | Immutable lineage, revision challenge, and replay | Independent implementation cannot eliminate a systematic MDM error |
| Mechanism storytelling | Prospective rivals and no causal label | Association may remain empirically valid but unexplained |
| Exploitability overclaim | Separate implementation-relevance profile and Stage 6 firewall | No profitability, cost, capacity, or portfolio conclusion is available here |
| Maturity overclaim | L4 ceiling and explicit outstanding Stage 4 gates | Wider transportability and regime evidence may later weaken the candidate |

The largest immediate scientific risk is not a weak statistical model. It is
executing on an incomplete survivor population or mutable/non-replayable MDM
history. The largest interpretive risk after a positive result is calling
range recurrence a trading edge or validated knowledge.

---

## 19. Final answer

### If every experiment in this programme is completed successfully, what scientific uncertainty will have been eliminated, and how much closer will Project EDGE be to determining whether a genuine, persistent trading edge exists?

Successful completion would eliminate, within the exact registered domain, the
material uncertainty about whether daily observed equity range has a persistent
security-linked residual component net of common dates. Project EDGE would know
that the conditional-mean relationship:

- exists within securities rather than arising only from stable differences
  between volatile and quiet stocks;
- remains after common-date market conditions are removed;
- is not explained by the registered identity, OHLC-basis, trading-state,
  missingness, survivorship, concentration, or false-link artifacts;
- persists beyond the immediate next session on one fixed trading-week clock;
- confirms without modification in untouched later history; and
- reproduces at both `t+1` and `t+5` under an independent implementation on
  genuinely new temporal outcomes.

That would move Project EDGE materially closer to its primary objective. The
project would advance from having a scientifically governed data platform but
no empirical phenomenon to possessing its first independently replicated,
point-in-time-correct **L4 candidate market behaviour**. It would justify Stage
5 evidence synthesis and a bounded next validation decision. It would not yet
justify `validated`, `validated-conditional`, or Stage 6 strategy-eligibility
status because the outstanding frozen Stage 4 transportability, regime,
rolling-window, robustness, and implementation-relevance gates remain.

It would not eliminate uncertainty about causal mechanism, applicability to
other markets or instruments, directional return value, transaction costs,
capacity, portfolio interaction, execution, or net profitability. Therefore it
would not prove that a genuine trading edge exists. It would replace “no trusted
candidate phenomenon” with “one directly replicated candidate source of
temporally ordered information”—a necessary and substantial scientific step,
but not the final validation or commercial conclusion.
