# PROJECT EDGE

## EDGE QUALIFICATION FRAMEWORK

**Version:** 1.0  
**Purpose:** Practical research-family selection  
**Scope:** Project EDGE only  
**Status:** Programme decision framework; not an evidence state, validation standard, strategy specification, or replacement for the frozen Foundation

---

## 1. Executive decision

Project EDGE shall use a selective, non-compensatory qualification filter before committing substantial research effort to any phenomenon family.

The default decision is:

> **ELIMINATE**

A family qualifies for substantial further research only when every mandatory qualification criterion is satisfied. A strong result on one criterion cannot compensate for failure on another. In particular:

- statistical significance cannot compensate for economic immateriality;
- a large pooled coefficient cannot compensate for concentration or instability;
- an attractive narrative cannot compensate for unavailable point-in-time data;
- apparent robustness in the same exposed sample cannot compensate for absent independent reproduction; and
- plausible profitability cannot compensate for leakage, survivorship bias, identifier error, or failed reproducibility.

Qualification means only:

> The phenomenon has demonstrated enough scientific and economic potential to justify substantial further research.

It does not mean that the phenomenon is validated, profitable, implementable, or an exploitable edge.

### Current conclusion

No existing Project EDGE research family currently qualifies.

- The tested opening-gap ancestry is terminated.
- Daily observed-range recurrence is paused after an inconclusive Level-1 result that failed precision, identity-influence, date-influence, and missingness gates.
- All other catalogue families are empirically unstarted.

The highest-value new direction using the MDM dataset available today is:

> **One-session cross-sectional intraday-return dependence**

This family asks whether a security's same-session open-to-close return predicts its open-to-close return on the next observed MDM session after retained exact-case ticker-by-era proxy effects and formation-date effects. The date adjustment removes the common additive date mean and makes the identifying variation cross-sectional without requiring a separately tuned ranking rule; it does not remove sector or latent-factor co-movement.

---

## 2. The qualification question

For every research family, Project EDGE shall ask:

> Has this phenomenon demonstrated a persistent, distributed, reproducible, point-in-time observable and economically material relationship that is resistant to the most credible data and measurement artefacts?

If the answer is not clearly yes, the family does not qualify for substantial research.

The framework separates three matters that must not be conflated:

1. **Scientific existence:** Is a repeatable statistical relationship present?
2. **Edge relevance:** Is its magnitude and timing plausibly useful after realistic friction and capacity constraints?
3. **Strategy utility:** Can it eventually contribute to a robust trading process?

This framework addresses the first two only far enough to decide whether deeper research is justified. It does not design or optimise a strategy.

---

## 3. Operating principles

### 3.1 Non-compensatory gates

Every mandatory gate is classified as:

- `PASS`;
- `FAIL`; or
- `UNRESOLVED`.

Qualification requires every gate to be `PASS`.

`UNRESOLVED` is not partial qualification. It means the family has not earned substantial research effort.

### 3.2 Outcome-independent standards

Materiality boundaries, periods, populations, horizons, artefact challenges, inference methods and stopping rules must be fixed before the relevant outcomes are inspected.

They must not be selected because they make a result pass.

### 3.3 Fastest decisive test first

Tests should be ordered so that the cheapest credible falsification occurs first. Research stops at the first decisive failure.

### 3.4 One phenomenon before combinations

A phenomenon must qualify independently before combinations are studied. Indicator combinations, composite scores and parameter searches cannot rescue a weak standalone premise.

### 3.5 Negative decisions are final within the tested ancestry

An eliminated family may be reopened only by genuinely new scientific evidence or a distinct independently motivated mechanism. A new threshold, subgroup, horizon, transformation or estimator is not new evidence.

### 3.6 Pause carries no research priority

`PAUSE` is reserved for a named, material and scientifically consequential limitation that prevents a reliable conclusion. A paused family receives no substantial research allocation.

It may resume only when:

- an independently arising MDM capability or general-purpose scientific repair resolves the named limitation;
- the repair was not chosen to improve the observed result; and
- a new outcome-blind decision record establishes high expected information gain.

`PAUSE` must not become storage for disappointing ideas.

---

## 4. Mandatory qualification criteria

### Gate 1 — Defined, falsifiable and point-in-time observable

The phenomenon must have one precise definition covering:

- population;
- feature;
- observation time;
- outcome;
- forecast horizon; and
- direction or material-effect region.

The feature must be available from MDM before the outcome begins. Historical classification, membership, identity and fundamental fields must be used only as they were available at the decision time.

**PASS when:** the claim is reproducible from an immutable MDM snapshot without future information or discretionary interpretation.

**FAIL when:** the relationship requires future membership, revised data presented as historically known, an unfalsifiable definition, or an observation that becomes known only after the outcome starts.

### Gate 2 — Scientifically and economically material predictive content

The primary estimate must exceed a minimum relevant effect defined before outcome inspection.

The minimum must be derived from the phenomenon's intended economic scale, observation delay, plausible turnover and conservative friction—not from the historical coefficient distribution.

Statistical significance alone is insufficient. The uncertainty interval must distinguish a scientifically and economically relevant effect from a negligible one.

**PASS when:** the conservative bound on the primary effect clears the predeclared materiality boundary.

**FAIL when:** the effect is precisely negligible, contradicted, or too imprecise to distinguish material from submaterial despite the complete appropriate sample.

### Gate 3 — Persistence through time and stability on independent outcomes

The relationship must retain its direction and meaningful magnitude across predeclared chronological periods containing different market conditions.

At least one decision-bearing assessment must use outcomes that were not used to select the hypothesis, feature, model, population or horizon. Repeated slicing of the discovery sample is not independent replication.

**PASS when:** the conclusion is compatible across the frozen periods and survives a genuinely independent temporal assessment.

**FAIL when:** the effect reverses, economically collapses outside one episode, or is carried principally by one era.

### Gate 4 — Distributed population support

An equity phenomenon must be distributed across a scientifically meaningful population rather than created by one identifier, instrument class, liquidity pocket, listing episode or small cluster.

Reasonable population changes must be defined economically and before outcomes. Examples include identifiable instrument types, liquidity ranges, exchanges or security-lifecycle states where MDM can represent them point in time.

**PASS when:** no single security or small cluster can move the qualification decision, and the conclusion remains compatible across the prespecified target-preserving populations.

**FAIL when:** the result is dominated by a ticker, date block, post-hoc subgroup, mixed-instrument artefact or population that cannot be reconstructed point in time.

### Gate 5 — Resistance to credible measurement and data artefacts

Each experiment must identify the small number of mechanisms most capable of creating a false result for its exact measurement.

Relevant challenges may include:

- corporate actions;
- identifier reuse or drift;
- bad or stale bars;
- price-scale and tick effects;
- missing, halted or terminal observations;
- survivorship;
- future classifications or membership;
- shared-price algebra;
- calendar mistakes; and
- concentrated influence.

These are veto tests, not opportunities to search for a passing subset.

**PASS when:** the primary conclusion survives the preregistered credible challenges or a worst-case bound cannot change the decision.

**FAIL when:** a credible artefact explains the result, can move it across the qualification boundary, or cannot be bounded sufficiently for the claim being made.

### Gate 6 — Dependence-aware precision

Uncertainty must reflect the actual evidence structure, including repeated securities, common market dates, overlapping outcomes and serial dependence where applicable.

Millions of ticker-days do not constitute millions of independent observations.

**PASS when:** a prespecified dependence-aware interval is narrow enough to adjudicate the materiality boundary and no cluster has decision-changing influence.

**FAIL when:** apparent precision relies on nominal row count, the interval cannot adjudicate materiality, or a security/date cluster dominates the result.

### Gate 7 — Reproducibility

The complete result must be deterministically reproducible from the bound MDM input, feature definition, software version and experiment specification.

Before substantial research, the core conclusion must also survive either an independent calculation or a genuinely separate implementation. Later confirmation still requires untouched outcomes under the frozen Foundation.

**PASS when:** deterministic replay is exact and independent reconstruction reproduces the decision-bearing conclusion within a preregistered compatibility rule.

**FAIL when:** results depend on undocumented state, nondeterministic ordering, manual intervention, or an unexplained implementation disagreement.

### Gate 8 — Plausible friction survival and capacity

The phenomenon must have a credible path from observation to economic exposure without designing an optimised strategy.

Qualification requires a conservative envelope for:

- bid-ask friction or a defensible upper proxy;
- market impact;
- observation and execution delay;
- implied turnover;
- event frequency;
- liquidity and participation; and
- capacity at a commercially meaningful scale.

**PASS when:** the conservative lower effect bound plausibly exceeds the upper realistic friction envelope and the effect occurs across enough observable, sufficiently liquid securities.

**FAIL when:** even the plausible upper effect cannot survive friction, the signal is known too late to act upon, or apparent magnitude exists only in economically unusable instruments.

This gate is an economic plausibility check, not a backtest or strategy optimisation.

### Gate 9 — Plausible mechanism and falsifiable competing explanations

At least one economic, institutional or behavioural mechanism must explain why the phenomenon could persist, together with the strongest credible competing explanation.

The mechanism need not be proven before qualification, but it must produce testable implications and must not merely restate the observed correlation.

**PASS when:** the phenomenon and its principal rival explanations can be distinguished by future preregistered evidence.

**FAIL when:** the only explanation is a measurement artefact, an outcome-written narrative, or a story with no falsifiable consequence.

### Gate 10 — Standalone representation and future composability

The phenomenon must be representable as a standalone, point-in-time scientific object without requiring a fitted strategy, optimised indicator bundle or hidden interaction.

It should have a clear sign, scale, scope and conditional boundary so that later work can test whether it adds information to other qualified phenomena.

**PASS when:** the phenomenon can be measured and falsified independently and could later enter an interaction study without redefining it.

**FAIL when:** it exists only inside an optimised combination or cannot be separated from a trading rule.

Incremental complementarity is a priority discriminator after qualification, not a reason to reject Project EDGE's first genuine standalone phenomenon.

---

## 5. How thresholds are set without optimisation

This framework does not prescribe universal numerical thresholds. Universal values would be scientifically inappropriate across return, volatility, event and cross-sectional phenomena.

Every experiment must instead derive its boundaries from external or structural considerations before outcomes:

| Boundary | Outcome-independent basis |
|---|---|
| Minimum relevant effect | Conservative friction, delay, turnover, forecast scale or other economic viability constraint |
| Time periods | Calendar history, data availability and materially different preidentified market conditions |
| Population variants | Economic instrument definitions, exchange, lifecycle or liquidity categories—not result strength |
| Influence tolerance | Whether any one cluster could change the scientific or economic disposition |
| Missingness tolerance | Worst-case or scientifically justified bounds on missing outcomes relative to the decision boundary |
| Precision requirement | Ability of the interval to distinguish material from submaterial effects |
| Replication compatibility | Preregistered prediction, equivalence or compatibility region—not repeated statistical significance |

Thresholds must never be loosened after a near miss. A near miss is a failed gate, not an invitation to tune the boundary.

---

## 6. Minimum research funnel

The following sequence minimises cost while preserving decision quality.

### Step 1 — Question-value screen

Do not run the experiment unless either result will eliminate an important uncertainty.

Required answer:

> If the experiment succeeds or fails as expected, what important scientific uncertainty will disappear?

If no important uncertainty disappears, do not run it.

### Step 2 — MDM feasibility and timing check

Confirm that the exact narrow question is observable with current MDM data. Classify limitations using Section 8.

Stop only for a limitation that makes the exact conclusion unreliable. Narrow wording when a limitation merely restricts transportability.

### Step 3 — One bounded primary screen

Use:

- one phenomenon;
- one primary feature definition;
- one horizon;
- one population contract;
- one dependence-aware primary estimand; and
- fixed materiality and stopping rules.

A precise submaterial result eliminates the branch. No rescue variants follow.

### Step 4 — Distribution and artefact veto

Before interpreting a positive pooled result, determine whether it is carried by identity, date, missingness, security type, price scale or another credible artefact.

A veto failure stops promotion.

### Step 5 — Independent stability and reproduction

Only a material, distributed, inferable screen earns one bounded independent-period and independent-calculation assessment.

Failure eliminates the tested claim. It does not initiate a parameter search.

### Step 6 — Economic qualification

Only a scientifically surviving phenomenon receives a conservative friction, timing, turnover, liquidity and capacity assessment.

If the effect cannot plausibly survive, eliminate it as an edge-research family even if the statistical behaviour is real.

### Step 7 — Substantial research

Substantial confirmatory, explanatory, interaction and implementation-relevance work begins only after every mandatory qualification gate passes.

At most one unvalidated family should occupy this stage at a time unless two families have independently passed every gate and parallel work has clearly greater ESIG.

---

## 7. Programme decisions

### 7.1 ELIMINATE — default

Use `ELIMINATE` when:

- the effect is precisely submaterial or contradicted;
- an independent period materially fails;
- realistic friction overwhelms the effect;
- a security, period, population or artefact dominates it;
- the signal is unavailable before the outcome;
- the result requires post-outcome exclusions or parameter changes;
- independent reproduction fails without a demonstrated implementation defect; or
- the complete appropriate evidence remains unable to support a material conclusion and no general-purpose data improvement is expected to resolve it.

Retain the negative result permanently and close its tested ancestry.

### 7.2 PAUSE — no promotion and no active rescue

Use `PAUSE` only when a named data or inferential limitation prevents a reliable conclusion and the result cannot honestly be classified as a market null.

A pause must record:

- the exact blocking limitation;
- why it can change the conclusion;
- the independently defined condition that would resolve it; and
- why no current narrower claim is scientifically reliable.

Paused families do not receive substantial research resources and are excluded from the active priority queue.

### 7.3 INVALID — no market conclusion

Use `INVALID` for leakage, corrupted inputs, formula errors, failed lineage or failed deterministic reproduction.

Only correction of the exact technical defect is permitted. Outcome-driven scientific redesign is not.

### 7.4 QUALIFY FOR SUBSTANTIAL RESEARCH — rare

Qualification requires:

- every mandatory gate marked `PASS`;
- no unresolved decision-changing MDM limitation;
- a frozen statement of the surviving claim and boundary;
- a clear account of what independent evidence remains; and
- an ESIG case for why deeper research can still change the edge decision.

Qualification is a resource-allocation decision, not an evidence maturity label.

---

## 8. MDM limitation materiality test

MDM is the production data source. Its imperfections shall be analysed, not used as a routine reason to postpone research.

For each relevant limitation ask:

> Could this limitation plausibly create, erase, reverse, or move the estimated effect across the scientific or economic qualification boundary for the exact claim being made?

Classify the limitation as:

| Classification | Meaning | Action |
|---|---|---|
| `NON-MATERIAL` | It restricts wording but cannot reasonably change the exact conclusion | Proceed with bounded wording |
| `MATERIAL-BUT-BOUNDED` | It can affect the estimate, but a frozen worst-case bound cannot change the decision | Proceed and disclose the bound |
| `MATERIAL-UNBOUNDED` | It can change the decision and cannot be bounded with current MDM | Narrow the claim or pause |
| `INVALIDATING` | It creates leakage, future membership, corrupted outcomes or unreproducible identity | Stop with no market conclusion |

Examples:

- Mixed instrument types may be non-material for a claim about the exact raw MDM census but material for a claim about ordinary common stocks.
- Exact ticker identity may be adequate for an adjacent-session operational screen but material for a multi-year security-history claim.
- A coherent multiplicative price adjustment is immaterial to a same-row ratio such as `high/low` or `close/open`; it can be material to an unadjusted multi-session return.
- Missing outcomes are material when availability varies with the exposure and plausible missing outcomes can change the decision.
- An archive-derived session clock can support a claim about the next observed archive session while remaining insufficient for a claim about an authoritative exchange session.
- Absent bid-ask data need not block scientific discovery, but they prevent an edge-qualified economic claim unless a conservative friction envelope makes the conclusion insensitive to the missing detail.

MDM limitations must never be dismissed as harmless noise without an explicit argument or bound.

---

## 9. Prioritising families that pass the gates

There is no weighted qualification score. Passing one gate cannot offset failing another.

If more than one family qualifies, rank them using the following outcome-independent priorities:

1. **Decision value:** How much important uncertainty will the next experiment permanently remove?
2. **Direct edge relevance:** How closely is the measured outcome connected to observable gross economic return?
3. **ESIG relative to cost:** Can the branch be confirmed or closed with a small bounded programme?
4. **Breadth and capacity:** Is the effect likely to matter across a commercially usable population?
5. **Independence and complementarity:** Does it add distinct information rather than duplicate a stronger qualified phenomenon?
6. **MDM readiness:** Can current MDM support a trustworthy conclusion without large speculative infrastructure?

Substantial effort is allocated only to qualified families. Cheap screens remain cheap; paused and eliminated families receive no active research budget.

---

## 10. Practical qualification card

Every family can be assessed on one concise record:

| Field | Required content |
|---|---|
| Scientific question | One falsifiable sentence |
| Exact phenomenon | Feature, outcome, horizon and population |
| Availability time | When the feature is known relative to the outcome |
| Important uncertainty removed | Learning under support, null, contradiction and invalidity |
| MDM limitations | Classification and exact impact on the claim |
| Materiality basis | External economic or scientific basis; never fitted to outcomes |
| Temporal evidence | Frozen periods and genuinely independent outcomes |
| Population evidence | Influence and target-preserving population checks |
| Artefact challenges | Small preregistered set of credible rival explanations |
| Reproducibility | Input, code, environment, replay and independent calculation |
| Economic envelope | Friction, delay, turnover, frequency, liquidity and capacity |
| Mechanism | Primary explanation and strongest competitor |
| Gate decisions | `PASS`, `FAIL`, or `UNRESOLVED` for Gates 1–10 |
| Programme decision | `ELIMINATE`, `PAUSE`, `INVALID`, or `QUALIFY FOR SUBSTANTIAL RESEARCH` |

This card is a decision aid, not a new registry, evidence state or enterprise workflow.

---

## 11. Application to the current Project EDGE portfolio

| Research family | Current Project EDGE evidence | Qualification decision | Programme action |
|---|---|---|---|
| Opening gaps | Level-1 falsification sequence ended with `EDGE-L1-004` eliminating the surviving gap-up branch; gap-down was already closed | `FAIL` | **ELIMINATE.** Do not reopen through new thresholds, subgroups, horizons or gap-specific infrastructure |
| Daily observed-range recurrence | `EDGE-L1-005` produced a positive pooled estimate and positive era slopes but failed frozen precision, ticker-influence, date-block-influence and missingness gates; it is not a signed return outcome | `FAIL` for resource qualification under Gates 2, 4, 5 and 6 | Preserve the original frozen scientific decision `PAUSE`, but remove the family from active priority; do not run a rescue specification or activate formal `EDGE-VSP-001` |
| Relative strength, breadth, sector leadership, earnings, institutional accumulation, mean reversion and other catalogue families | No Project EDGE empirical evidence | Not assessed | None qualifies; compare only as candidates for one cheap first screen |

Therefore:

> **No existing Project EDGE family currently satisfies the Edge Qualification Framework.**

Project EDGE should not attempt to manufacture a qualifying candidate from the opening-gap or observed-range results.

---

## 12. Highest-value new research direction

### 12.1 Recommended family

> **One-session cross-sectional intraday-return dependence**

The first bounded question should be:

> Within the raw date-bounded MDM archive census, does a security's session `t` open-to-close log return predict its next-observed-session open-to-close log return after retained exact-case ticker-by-era proxy effects and formation-date effects?

Operational atomic measurement:

`r(i,t) = ln(close(i,t) / open(i,t))`

Formation-date effects make the estimate depend on within-date cross-sectional differences rather than the market's common daily return. A single continuous dependence estimate tests whether directional memory is:

- positive, consistent with continuation;
- negative, consistent with reversal; or
- economically negligible.

This is one family and one slope, not simultaneous strategy research.

The slope alone is not an economic qualification measure. Before outcome access, the screen must also freeze one interpretable exposure-scale contrast that converts the continuous relationship into expected next-session gross-return units. That contrast—not a fitted portfolio or outcome-selected cutoff—is compared with the conservative friction envelope.

### 12.2 Why it has the highest current expected value

1. It opens a genuinely new family and does not rescue gaps or range recurrence.
2. It uses equity cross-sectional information as first-class evidence.
3. Its signed return outcome is directly comparable with a later conservative friction envelope.
4. The feature is known after session `t` closes and before the next session's open-to-close outcome begins.
5. Both feature and outcome are same-row ratios, reducing coherent corporate-action scaling risk.
6. It requires only the existing MDM daily ticker/OHLC census and the deterministic daily-panel capability already demonstrated.
7. One feature, one horizon and one continuous slope can close the exact unconditional linear short-horizon branch without a parameter grid.
8. A precise negligible result is highly valuable because it eliminates material linear continuation and reversal within the raw MDM census at that exact horizon.

### 12.3 MDM limitations and whether they block the first screen

Current relevant limitations are:

- exact ticker rather than certified permanent security identity;
- mixed ordinary shares, ETFs, ADRs, preferreds, warrants and other instruments;
- incomplete lifecycle, halt and delisting state;
- archive-derived rather than authoritative exchange sessions;
- raw open and close without independently certified auction semantics; and
- no complete historical bid-ask spread record.

These limitations do not invalidate the narrow initial question about the exact raw MDM ticker census because:

- identity continuity is required only across adjacent archive sessions;
- `ln(close/open)` is invariant to coherent within-row multiplicative adjustment;
- all formation observations can remain in missing-outcome accounting;
- formation-date effects remove the common additive date mean, while sector and latent-factor co-movement remain explicit competing explanations; and
- absent spread data affects later economic qualification more than existence of the raw statistical relationship.

They do prevent claims about ordinary common stocks, authoritative auction returns, validation, profitability or a genuine exploitable edge.

All MDM dates through `2026-07-30` are already Level-1 exposed. The proposed screen can therefore provide exploratory falsification and triage, but it cannot itself pass Gate 3's independent-outcomes requirement. A surviving result would require untouched later MDM outcomes, collected after the specification is frozen, before the family could qualify for substantial research.

The screen must stop or pause if missingness, bad bars, ticker/date concentration or microstructure proxies can change its conclusion. Those checks must be frozen before outcome inspection and may veto promotion but never rescue a weak result.

### 12.4 Decision value

The first screen should have only three scientific consequences:

- **Precise economically submaterial relationship:** eliminate the exact raw-MDM-census, one-session, unconditional linear dependence branch.
- **Material, stable, distributed and inferable relationship:** permit one bounded independent qualification assessment; do not claim an edge.
- **Failed inferability or material MDM limitation:** pause with the exact blocker; do not search for a passing population, threshold or horizon.

No portfolio, trading rule, optimiser, broker interface or execution system is required.

A null in this first screen cannot eliminate nonlinear dependence or an ordinary-equity-specific effect. Those possibilities remain untested, but they receive no follow-up merely because the broader idea survived the wording boundary; either would require a separately motivated hypothesis based on genuinely new scientific evidence.

---

## 13. Final programme rule

Project EDGE shall spend most of its research effort only after a phenomenon has passed every mandatory qualification gate.

Before qualification:

- experiments remain small;
- hypotheses remain singular;
- rejection remains the expected outcome;
- adverse results close branches; and
- infrastructure is added only when it directly enables a decision-bearing experiment.

The current portfolio contains no edge-qualified phenomenon.

The next highest-value direction is the bounded one-session cross-sectional intraday-return-dependence family because it is new, directly directional, executable with current MDM data, economically interpretable, and capable of closing a major branch with one disciplined test.

Its selection is a research-priority decision, not evidence that the phenomenon or an exploitable edge exists.
