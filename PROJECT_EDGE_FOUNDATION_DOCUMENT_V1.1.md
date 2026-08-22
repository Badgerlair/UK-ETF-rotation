# Project EDGE — Equity Research Platform

## Stage 0 Scientific Foundation

**Document type:** Scientific architecture and governance foundation  
**Status:** Approved in principle; Version 1.1 scientific amendments integrated subject to the stated gates  
**Version:** 1.1  
**Date:** 3 August 2026  
**Repository:** D:\codex\equity_quant_research_platform  
**Authoritative data source:** Market Data Manager (MDM) only  
**Version lineage:** Additive successor to Version 1.0, which remains retained and unchanged

---

## 1. Executive foundation

Project EDGE is an independent scientific research platform for discovering, measuring, explaining, and validating persistent statistical phenomena in equity markets. Its primary output is not a trading rule. Its primary output is a defensible statement about market behaviour, bounded by the populations, periods, conditions, and data on which that statement has survived testing.

The platform shall begin with questions such as:

- Does a measurable condition alter the subsequent distribution of returns, volatility, liquidity, correlation, volume, or participation?
- Is the effect persistent through time, across securities, and across relevant market environments?
- Can the effect be distinguished from a data artefact, common risk exposure, microstructure effect, or multiple-testing accident?
- What economic, institutional, behavioural, or structural mechanism could generate it?
- What evidence would falsify that explanation?

It shall not begin with questions such as:

- Which combination of indicators maximises a backtest?
- Which parameter set produces the best Sharpe ratio?
- When should a position be entered, sized, stopped, or exited?
- How can an execution or broker interface be built?

The scientific record is the central product. Supported, precise-null, contradicted, inconclusive, and invalid findings all belong in that record. A hypothesis that fails cleanly is useful knowledge because it closes a path, constrains explanations, and reduces repeated data mining.

This foundation defines the following staged architecture, including the inserted Stage 2.5:

| Stage | Purpose | Primary scientific artifact | Admission gate |
|---|---|---|---|
| 1. Phenomena Catalogue | Define research domains and falsifiable questions | Phenomenon charter and hypothesis family | Clear construct, scope, mechanism, outcome, and falsifier |
| 2. Feature Generation | Create point-in-time measurements | Versioned security-day feature panel | Data lineage and temporal integrity pass |
| 2.5. Feature Validation | Establish scientific trustworthiness of feature definitions | Feature-validation dossier and status | Only validated feature versions may enter discovery |
| 3. Discovery | Find candidate conditional behaviours | Exploratory evidence record | Complete search ledger and non-optimised effect evidence |
| 4. Validation | Challenge, reproduce, and directly replicate candidates | Preregistered validation and replication records | Mandatory scientific gates pass |
| 5. Knowledge Base | Preserve cumulative evidence | Versioned evidence synthesis | Curated claim with full provenance |
| 6. Future Strategy Assembly | Permit later use of mature findings | Traceable phenomenon-to-strategy rationale | Separate future governance; outside this project stage |

Stages 1–5, including Stage 2.5, form the research platform. Stage 6 is a deliberately separated downstream possibility, not an implementation instruction and not part of Stage 0.

---

## 2. Mandate, boundaries, and independence

### 2.1 Mandate

Project EDGE shall:

1. discover repeatable equity-market behaviours;
2. quantify effect size, uncertainty, decay, and domain of validity;
3. test plausible explanations and competing explanations;
4. validate claims using preregistered, point-in-time, out-of-sample methods;
5. preserve the full experimental history, including negative evidence; and
6. make every accepted claim independently repeatable from an authorised MDM data snapshot.

### 2.2 Hard boundaries

The following are outside scope:

- accessing, modifying, writing to, or producing any artifact outside D:\codex\equity_quant_research_platform during this project;
- accessing or modifying Project ICT (Forex), the Futures Research Engine, the Legacy Forex Research Engine, the Universal Regime Engine, completed experiment outputs, or previous findings databases;
- direct search for profitable strategies;
- parameter optimisation intended to maximise a performance metric;
- portfolio construction, risk allocation, position sizing, or capital allocation;
- order generation, execution logic, broker integration, or live trading;
- production trading infrastructure;
- importing findings, experimental results, code, databases, or artifacts from Project ICT (Forex), the Futures Research Engine, the Legacy Forex Research Engine, the Universal Regime Engine, completed experiment outputs, or previous findings databases; and
- use of any market-data source other than MDM.

The platform may embody general scientific lessons expressed as governance rules—reproducibility, immutability, honest out-of-sample testing, negative-result retention, and separation of discovery from optimisation—without sharing architecture, code, data, or findings with the prohibited programmes.

Every future intermediate file, registry, manifest, log, result, review, and final artifact created under this project must remain beneath D:\codex\equity_quant_research_platform. MDM may be queried only as the authorised market-data source; no MDM data is to be copied to an unapproved location.

### 2.3 Blank-slate rule

The initial catalogue and knowledge base shall start empty except for approved research questions, taxonomies, and methods established within this repository. No previous finding is presumed true. If a well-known equity effect is examined, it enters as a new hypothesis and must pass Project EDGE’s own point-in-time tests.

### 2.4 MDM exclusivity

MDM is the sole authorised source for prices, volume, security identity, corporate actions, classifications, index membership, fundamentals, earnings events, quotes, and any other market observation. A requested feature family is not automatically authorised merely because it appears in this document. If MDM cannot supply its inputs with adequate point-in-time provenance, that family must be marked unavailable or deferred. It must not be filled from another vendor, a previous database, or an internet dataset.

### 2.5 Architecture-only status

This document specifies scientific responsibilities, data contracts, artifacts, controls, and decision gates. It does not prescribe a software package layout and does not create an implementation.

### 2.6 Lessons-learned completeness

The clean-room boundary prevents this Stage 0 task from inspecting the named Forex or Futures programmes. Consequently, this document incorporates the non-empirical lessons stated in the brief but cannot independently certify that it captures every lesson contained in prohibited artifacts.

| Sanitised lesson supplied in the brief | Architecture invariant |
|---|---|
| Begin with phenomena, not strategies | Strategy-neutral phenomenon contract and Stage 3 prohibitions |
| Preregister and preserve experiments | Immutable registry, amendments, and complete run deposits |
| Retain negative evidence | Mandatory negative-results registry and searchable evidence graph |
| Do not optimise before discovery | Canonical measurement families and outcome-independent research budgets |
| Explain results | Mechanism, rival explanation, and falsification records |
| Treat the equity cross-section as first class | Point-in-time sector, industry, index, peer, and breadth architecture |

If “all lessons learned” requires additional coverage, an accountable project owner must supply or approve a sanitised, non-empirical list that does not reveal or import code, data, findings, schemas, or outputs from a prohibited programme. Any new lesson becomes a versioned architecture requirement inside this repository.

---

## 3. Scientific ontology

Shared definitions prevent research language from drifting into strategy language.

### 3.1 Observation

An observation is a point-in-time measurement attached to a stable security identifier, an event or trading date, an availability timestamp, an authorised MDM data vintage, and a declared eligible universe.

### 3.2 Feature

A feature is a reproducible measurement of information that was available at the declared research cutoff. It is neither a buy signal nor a sell signal. Each feature has a scientific definition, expected invariances, missing-data meaning, lineage, and a version.

### 3.3 Phenomenon

A phenomenon is a repeatable conditional difference in a measurable market outcome. A complete claim has the form:

> For population P, when observable condition X is present at admissible time t, the distribution of outcome Y over horizon H differs from comparator C by effect E, within declared uncertainty, and remains supported in domain D.

The outcome may be a return, residual return, volatility, volume, spread, liquidity, correlation, drawdown characteristic, participation measure, transition probability, or other market quantity. Profitability is not required for scientific validity.

### 3.4 Hypothesis

A hypothesis is a preregistrable, falsifiable proposition about a phenomenon. It specifies:

- population and unit of observation;
- exposure or conditioning variable;
- comparator or null model;
- outcome and measurement horizon;
- expected sign or explicitly two-sided alternative;
- minimum scientifically relevant effect;
- mechanism and competing mechanisms;
- admissible exclusions and missing-data policy;
- primary statistical estimand and inference method; and
- observations that would count against the claim.

The minimum scientifically relevant effect must be set from the meaning, measurement resolution, and scientific use of the outcome before candidate selection. It must not be reverse-engineered from the discovery estimate, a desired significance result, or assumed trading frictions.

### 3.5 Candidate, validated phenomenon, and scientific null

- A **candidate phenomenon** has survived exploration but has not passed confirmatory validation.
- A **validated phenomenon** is a governed knowledge status indicating that the registered association has passed all mandatory gates within a stated population, period, measurement, and uncertainty. It is not a declaration of universal truth.
- A **context-bound phenomenon** is supported only within a preregistered segment or regime and is labelled accordingly.
- A **scientific null** requires a valid equivalence or compatibility procedure whose multiplicity-adjusted interval lies wholly inside the predefined negligible-effect region.
- An **inconclusive result** has insufficient power, data quality, or precision to support either an effect or a scientific null.
- A **contradicted hypothesis** has valid, sufficiently precise evidence that opposes or excludes its preregistered claim.
- A failed or non-significant replication is **not replicated** or **inconclusive** unless it precisely contradicts the registered claim.
- An **invalidated experiment** cannot support an inference because its data or method failed; its record is retained.

Insufficient power is a design or execution reason attached to an inconclusive evidential result, not a distinct claim about the market. Absence of statistical significance is not automatically evidence of absence. Negative, null, contradicted, inconclusive, and invalidated are different states.

### 3.6 Exploration and confirmation

Exploration may generate hypotheses. Confirmation may test them. The two activities must use separate records and, wherever practicable, separate data partitions or future vintages. An exploratory result must never be relabelled as confirmatory after its outcome is known.

### 3.7 Explanation

An explanation is a mechanism with testable implications, not a narrative added after observing a result. Explanations may be behavioural, institutional, risk-based, microstructural, informational, regulatory, or mechanical. Each accepted explanation must name at least one competing account and at least one discriminating test. Causal language is prohibited unless the design supports causal identification.

### 3.8 Controlled evidence vocabulary

Evidence is classified at three different levels. Terms from one level must not substitute for another.

| Level | Canonical states |
|---|---|
| Run finding | Supported; precise null; contradicted; inconclusive, with reason such as underpowered; invalid |
| Hypothesis decision | Confirmed on locked evidence; confirmed conditional; not confirmed; contradicted; unresolved |
| Phenomenon maturity | Proposed; candidate; provisionally confirmed; directly replicated; validated; validated conditional; superseded; retracted |

“Negative finding” is an umbrella retention category, not a statistical decision. It includes precise nulls, contradictions, valid but non-confirming results, and informative failures. “Not replicated” records a replication outcome and must be accompanied by supported, precise-null, contradicted, inconclusive, or invalid at run level.

Only the Stage 5 evidence synthesis may assign **validated** to a phenomenon. An individual run may support a hypothesis but is never itself a validated phenomenon.

### 3.9 Continuous evidence profile

A phenomenon’s maturity status is a governed snapshot, not a binary statement of truth. Every phenomenon also possesses a continuously evolving evidence profile that records how scientific confidence changes as new evidence arrives.

The profile preserves:

- cumulative supporting and replicated evidence;
- competing and contradictory evidence;
- evidence that weakens or narrows an earlier claim;
- superseded evidence and the reason it ceased to be active;
- effect and uncertainty trajectories through time;
- changes in scope, regime, population, measurement, and data quality;
- the independence and quality of each contribution; and
- the rationale for every strengthening, weakening, or boundary change.

The profile need not be a single probability and this architecture does not prescribe Bayesian implementation. It is an append-only scientific account of confidence evolution. A discrete status may remain unchanged while its supporting confidence strengthens or weakens, and contradictory evidence may coexist without being forced into a premature true/false decision.

### 3.10 Research-planning concepts

- **Research Cost** is a pre-execution estimate of computational resources and statistical workload, followed by an immutable record of actual consumption.
- **Expected Scientific Information Gain (ESIG)** is an outcome-independent estimate of how much a proposed experiment could reduce material scientific uncertainty.
- **Discovery budget** is a predefined limit on exploratory degrees of freedom. It controls research drift and multiplicity, not computing expenditure.

Scientific value, expected information gain, computational cost, and discovery-budget consumption are separate dimensions. None is a proxy for another.

### 3.11 Scientific relationship structures

The platform maintains three distinct version-controlled relationship structures:

- the **append-only evidence provenance graph**, which records how questions, registrations, inputs, runs, findings, reviews, and decisions were produced and linked;
- the **Research Dependency Graph**, which records prerequisites that must exist before a hypothesis or experiment is scientifically executable; and
- the **Phenomena Interaction Graph**, which records evidence-backed relationships among phenomena, including reinforcement, redundancy, hierarchy, causal hypotheses, conditional dependence, interaction, and conflict.

A provenance edge establishes lineage, a dependency edge controls eligibility, and an interaction edge describes accumulated scientific knowledge. None substitutes for another, and none may infer causality merely from association.

### 3.12 Feature-validation status

Feature validation is a measurement-governance decision distinct from phenomenon validation. It establishes that a particular feature definition and version is scientifically trustworthy within a declared data, population, and time domain. It does not establish that the feature predicts any future outcome.

Only feature versions whose validation status is valid for the proposed experiment’s domain may enter Stage 3. A changed definition, input lineage, timing rule, or material MDM revision creates a new validation obligation.

---

## 4. Governing principles converted to architecture invariants

| Principle | Non-negotiable architecture invariant |
|---|---|
| Phenomena first | Research specifications describe conditions and outcome distributions, never entries and exits |
| Scientific governance | A confirmatory run cannot begin without an immutable preregistration and admissible data snapshot |
| Negative findings matter | Every initiated experiment receives a permanent outcome state; deletion and silent abandonment are prohibited |
| No optimisation before discovery | Candidate generation uses small, theory-led measurement grids; no performance-maximising tuning |
| Explainability | Every candidate carries mechanism, rival explanation, falsifier, and boundary-condition fields |
| Cross-sectional research | Every eligible security can be located relative to its point-in-time sector, industry, index, market, peers, and breadth context where MDM supports them |
| Point-in-time truth | Values, memberships, classifications, and revisions are joined only as they were knowable at the research cutoff |
| Validated measurement | Discovery consumes only feature definitions that have passed Stage 2.5 within the required domain |
| Continuous evidence | Discrete maturity states are accompanied by append-only confidence evolution and competing evidence |
| Bounded discovery | Exploratory families, combinations, grids, partitions, and horizons consume predefined discovery budgets |
| Cost/value separation | Computational cost, ESIG, scientific validity, and outcome attractiveness remain independent |
| Dependency integrity | Experiments cannot execute while versioned scientific prerequisites remain unsatisfied |
| Connected knowledge | Relationships among phenomena are retained as governed, evidence-backed graph artifacts |
| Independence | The project has no runtime, schema, code, result, or database dependency on prohibited programmes |
| Traceability | Every claim resolves to hypotheses, runs, feature versions, MDM vintage, statistical outputs, reviews, and replications |
| Non-universality | Claims always state their population, dates, conditions, and known failure regions |

---

## 5. Logical scientific architecture

The platform is conceptually divided into a scientific control plane and an evidence pipeline.

### 5.1 Scientific control plane

The control plane contains:

- the phenomena catalogue;
- the hypothesis and experiment registry;
- preregistration, amendment, and approval records;
- data-vintage and feature-definition registries;
- the feature-validation registry and validation dossiers;
- holdout access controls;
- statistical test-family and multiplicity ledgers;
- discovery-budget definitions and consumption ledgers;
- research-cost estimates, actual-cost records, and ESIG assessments;
- the versioned Research Dependency Graph;
- review, replication, and adjudication records;
- robustness and evidence-status rules;
- continuously evolving evidence profiles;
- the versioned Phenomena Interaction Graph; and
- the permanent knowledge base.

It governs what may be claimed. It must be logically independent of result values: rules are fixed before the corresponding evidence is revealed.

### 5.2 Evidence pipeline

The evidence pipeline has the following one-way scientific flow:

**Catalogue and hypothesis proposal → dependency mapping, Research Cost and ESIG planning, and discovery-budget reservation → MDM snapshot → admissibility checks → point-in-time observations → versioned features → Stage 2.5 feature validation and view conformance → final dependency and scheduler eligibility → exploratory discovery → candidate record → preregistered validation → independent reimplementation → direct replication → continuous evidence update and synthesis**

Research Cost and ESIG may be estimated while prerequisites are being planned, but execution eligibility is granted only after the exact dependencies, features, conformance record, budgets, data assignments, and protocol have passed their applicable gates.

Feedback is allowed only through new versioned artifacts. A failed test may motivate a new hypothesis, but it may not rewrite the old hypothesis. A corrected dataset creates a new data vintage and a new run; it does not silently replace history.

### 5.3 Separation of concerns

| Concern | Responsibility | Must not do |
|---|---|---|
| Data admissibility | Establish what was known, when, for which security | Infer missing history from future data |
| Measurement | Convert admissible inputs into declared features | Select feature parameters using outcome performance |
| Feature validation | Establish measurement trustworthiness, scope, determinism, and lineage | Test predictive attractiveness or admit an unvalidated feature to discovery |
| Research planning | Register dependencies, discovery-budget consumption, research cost, and ESIG before scheduling | Treat low cost or expected positive findings as scientific validity |
| Discovery | Estimate candidate conditional effects | Claim confirmation or optimise a tradable rule |
| Validation | Attempt to reject, bound, and replicate claims | Change tests after seeing confirmatory results |
| Knowledge curation | Update continuous evidence profiles and synthesize all evidence, contradictions, and phenomenon relationships | Store only successful findings or collapse confidence into binary truth |
| Future strategy assembly | Use mature evidence under separate governance | Feed strategy performance back into scientific validation |

### 5.4 Required scientific artifacts

The minimum artifact chain for any confirmatory claim is:

1. phenomenon charter;
2. hypothesis specification;
3. preregistration;
4. Research Dependency Graph snapshot and prerequisite decision;
5. mandatory research-cost estimate and ESIG assessment, plus a discovery-budget charge for exploratory work;
6. authorised MDM snapshot identity;
7. eligible-universe definition;
8. feature-definition versions and Stage 2.5 feature-validation dossiers;
9. immutable execution and actual-cost record;
10. complete statistical output, including diagnostics;
11. validation decision;
12. independent-reimplementation and direct-replication records;
13. continuous evidence-profile update and phenomenon-interaction assessment;
14. evidence synthesis; and
15. knowledge-base status history.

An artifact may be superseded, but never overwritten or erased.

---

## 6. Data foundation and point-in-time contract

Equity research fails easily when present-day identities or classifications are projected into the past. Data integrity is therefore a scientific gate, not a cleaning step.

### 6.1 MDM boundary contract

Before implementation, Project EDGE and MDM require a documented, versioned contract covering:

- stable instrument and issuer identifiers;
- ticker, exchange, share-class, and identifier history;
- listing, suspension, relisting, merger, acquisition, bankruptcy, and delisting events;
- raw and adjustment-aware prices;
- cash and stock distributions, splits, spin-offs, rights issues, and other corporate actions;
- volume and, if authorised and available, quote/spread observations;
- trading calendars, sessions, currencies, and timestamps;
- point-in-time sector and industry classifications;
- point-in-time index constituents and weights;
- fundamentals with fiscal period, release, availability, revision, and restatement times;
- earnings announcements and other events with reliable publication times;
- MDM correction policy and snapshot/vintage identifiers; and
- licensing and retention constraints relevant to reproducibility.

The contract must distinguish a field that is absent from a field that is present but unknown. It must also distinguish a value corrected later by MDM from the value available historically.

### 6.2 Four clocks

Every observation that can be revised or published later should support four times:

1. **Economic time:** when the underlying activity occurred or the period ended.
2. **Publication time:** when the information was released to the market.
3. **Availability time:** the earliest time Project EDGE could legitimately have known it under the chosen cutoff.
4. **Vintage time:** the MDM snapshot in which the stored representation was obtained or corrected.

Daily bars also require a precise session cutoff. A close-derived feature for day t cannot explain an outcome beginning before that close. Unknown or ambiguous timing must produce a conservative lag or make the observation inadmissible.

### 6.3 Security identity

The research key must be a stable MDM identifier, not a ticker. A point-in-time identity map must handle ticker reuse, multiple share classes, exchange transfers, corporate reorganisations, foreign listings, depositary receipts, and issuer/security distinctions.

The initial scope should explicitly decide whether it includes only primary common-equity listings or also REITs, ADRs, closed-end funds, ETFs, preferred shares, warrants, and special-purpose acquisition vehicles. These populations must not be mixed accidentally.

### 6.4 Universe history

An eligible universe is reconstructed for each trading day using only contemporaneously valid facts. Return, distress, lifecycle, size, and liquidity claims require inactive and delisted securities and terminal outcomes whenever their absence could materially change the estimand. If MDM cannot provide them, validation is prohibited unless the claim is narrowed to a clearly observed population and defensible missing-not-at-random sensitivity or bounding analysis shows what can and cannot be inferred. A generic coverage caveat is insufficient. Current constituents, current sector labels, and present-day market-cap rankings must never be applied retrospectively.

Universe rules are scientific design choices. Liquidity, price, listing-age, and market-cap eligibility rules must be declared before testing, applied consistently, and subjected to boundary sensitivity rather than tuned for better results.

### 6.5 Prices and corporate actions

The platform needs two coherent views:

- an observed-price view for gaps, limits, liquidity, spreads, and what the market printed; and
- a return-consistent view for economic returns across distributions and corporate actions.

Backward-adjusted series can leak later corporate actions into earlier feature values or distort historical price thresholds. Adjustment conventions, effective times, and total-return treatment must therefore be explicit. Delisting returns and terminal events must be represented rather than dropping the security.

### 6.6 Fundamentals and event data

Fundamentals must be joined by publication or conservative availability time, never merely by fiscal period end. Restated values must not replace the originally available value in historical tests. Earnings dates need timestamp quality sufficient to distinguish pre-market, intraday, after-hours, and date-only records.

If MDM lacks these histories, fundamental and earnings phenomena remain deferred. The same rule applies to institutional holdings or ownership data.

### 6.7 Classification and peer context

Sector, industry, index, and peer relationships are time-varying data. The platform should support:

- official point-in-time classifications when available from MDM;
- declared peer construction rules based only on contemporaneous features;
- membership effective dates and announcement dates where relevant; and
- an explicit unknown category rather than backfilled classifications.

Peer groups must have minimum breadth and concentration diagnostics. A stock is never compared with a group that did not exist or was not knowable at the relevant time.

### 6.8 Admissibility tests

No experiment may proceed until its required fields pass:

- identity continuity and duplicate checks;
- calendar/session alignment;
- monotonic availability timestamps;
- corporate-action reconciliation;
- impossible price, volume, return, and market-cap checks;
- missingness and coverage maps by time and segment;
- inactive/delisted-security inclusion checks;
- classification-history coverage;
- revision/vintage consistency; and
- deterministic snapshot fingerprinting.

Failures are reported by time, security type, exchange, market-cap segment, and field. Broad averages can conceal precisely the missing small, distressed, or delisted securities that create survivorship bias.

### 6.9 Data corrections

An MDM correction creates a new research data vintage. Existing experiment records retain the old vintage fingerprint. Material corrections trigger an impact assessment and, where needed, a new replication. Prior results are marked superseded or data-invalidated but remain visible.

---

## 7. Stage 1 — Phenomena Catalogue

### 7.1 Purpose

The Phenomena Catalogue is the platform’s scientific ontology and indexed map. It defines enduring constructs, questions, and mechanisms and presents links to accumulated evidence. The append-only registry and Knowledge Base are authoritative for evidence from the first preregistration onward; the Catalogue does not duplicate or overwrite those records. Stage 5 denotes governed synthesis and adjudication, not the moment at which storage begins.

The Experiment Registry holds one immutable specification for one test. One catalogue entry may index many hypotheses, experiments, replications, nulls, contradictions, and refinements. The catalogue must never collapse that history into the most attractive result.

Entries are classified on several independent axes:

- behaviour family;
- unit of analysis: security, issuer, event, industry, sector, index, peer set, or market;
- comparison mode: within-security, same-date cross-sectional, peer-relative, event-time, or regime-conditional;
- research clock: session, overnight, close-to-close, event time, or longer horizon;
- outcome: return distribution, volatility, liquidity, volume, correlation, breadth, duration, or state transition;
- conditioning context: market, sector, industry, size, liquidity, lifecycle, or regime;
- evidence maturity; and
- claim strength: descriptive, temporally predictive, mechanism-consistent, or causally identified.

Most initial claims should be descriptive or temporally predictive. A causally identified label requires a separate protocol defining the causal estimand, identifying assumptions, treatment timing, interference and anticipation risks, negative controls, pre-trend requirements where relevant, and sensitivity to unmeasured confounding.

### 7.2 Core phenomenon families

The following catalogue is deliberately broad enough to cover major equity behaviours while remaining strategy-neutral.

#### 7.2.1 Momentum, trend persistence, and price-path continuation

Investigate whether prior absolute or residual movement, directional consistency, trend efficiency, or path shape is associated with continuation, acceleration, decay, or reversal in later outcome distributions.

Equity-specific comparisons include:

- absolute movement versus market-, sector-, industry-, index-, and peer-relative movement;
- equal-weighted versus capitalisation-weighted effects;
- issuer-level effects versus duplicate share-class effects;
- broad participation versus movement concentrated in a small number of large securities; and
- persistence conditional on volatility, liquidity, and lifecycle.

The research object is continuation or decay as a distributional property, not a moving-average trading rule.

#### 7.2.2 Mean reversion and overreaction

Investigate normalisation following unusual displacement, drawdown, peer divergence, intraday extension, residual return, or liquidity shock. Distinguish:

- reversion toward a security’s own prior state;
- reversion toward market, sector, industry, or peer context;
- reversal caused by stale prices, bid–ask bounce, or thin trading;
- behavioural overreaction; and
- compensation for changing risk.

The depth, latency, prevalence, and duration of reversion are part of the phenomenon. A threshold selected because it backtests well is not.

#### 7.2.3 Volatility expansion, contraction, and state dynamics

Study clustering, expansion, contraction, asymmetry, volatility-of-volatility, jump intensity, tail shape, downside/upside variation, idiosyncratic volatility, and the duration and transition of volatility states.

Potential propagation paths include security to peer group, sector to constituents, market to sectors, and volume/liquidity/breadth changes to subsequent volatility. Regime definitions must be observable at the time.

#### 7.2.4 Gaps, jumps, and discontinuities

Study overnight and event gaps, jump persistence, closure probability and time, post-gap volatility, participation, and peer response. Every gap study must define:

- raw reference prices;
- corporate-action treatment;
- official session and event timestamp;
- after-hours and pre-market assignment;
- eligible comparison group; and
- outcome clock.

Splits, dividends, stale closes, and mis-timed announcements are mandatory rival explanations.

#### 7.2.5 Volume, participation, and activity persistence

Study abnormal turnover, persistent volume, price–volume coupling, volume surprise, participation breadth, volume concentration, and changes in trading intensity.

“Institutional accumulation” is not directly observable from ordinary price and volume. Unless MDM provides attributable participant data, the catalogue shall use terms such as **institutional-activity proxy** and record construct-validity limitations. Candidate proxies may include persistent abnormal dollar volume, price–volume asymmetry, low-impact high-volume episodes, or closing-auction concentration when supported by MDM.

#### 7.2.6 Liquidity and market quality

Study dollar volume, turnover, spreads when available, impact proxies, zero-return frequency, discontinuity, resiliency, closing effects, and liquidity shocks. Research must separate economic behaviour from minimum-tick effects, stale prices, halts, sparse trading, and other microstructure artifacts.

#### 7.2.7 Relative strength and cross-sectional dispersion

Study persistence and decay in a security’s contemporaneous rank or residual movement relative to its market, index, sector, industry, and justified peers. Relevant constructs include:

- relative-rank persistence;
- absolute versus residual movement;
- cross-sectional dispersion;
- leadership concentration;
- leader-to-peer information transmission; and
- changes in the breadth of outperformance.

The benchmark, weighting rule, group membership, minimum group size, and leave-one-out treatment must be explicit.

#### 7.2.8 Breadth, participation, and concentration

Breadth is a distribution, not one advance/decline statistic. Study:

- advancing, declining, unchanged, new-high, new-low, trend, volatility, and volume participation;
- equal-weighted and capitalisation-weighted breadth;
- sector and industry breadth;
- divergence between broad participation and headline indexes;
- contribution concentration;
- dispersion and average co-movement; and
- breadth persistence, deterioration, and transitions.

Every breadth observation retains its point-in-time denominator, missing count, coverage ratio, and weighting convention.

#### 7.2.9 Sector and industry rotation

Study measurable transitions in relative return, leadership, participation, dispersion, volatility, liquidity, and internal correlation among point-in-time sectors and industries. Rotation is a change in the cross-sectional state, not a direction to rotate a portfolio.

#### 7.2.10 Earnings, information, and corporate events

Subject to MDM capability, study pre-event conditions, immediate response, delayed response, peer diffusion, post-event drift or reversal, volatility transitions, and differences by uncertainty, liquidity, or regime for:

- earnings and fundamental releases;
- dividends, splits, buybacks, and issuance;
- index additions or removals;
- mergers, acquisitions, and spin-offs;
- IPOs, suspensions, relistings, and delistings; and
- other timestamped corporate events.

Actual public-availability time is essential. Fiscal period end is never a substitute for release time.

#### 7.2.11 Fundamental change and market response

Subject to point-in-time MDM support, study reported levels, changes, surprises, revisions, valuation, profitability, growth, quality, leverage, accruals, dilution, and the timing of market response.

Every observation must carry the period described, original release time, then-current version, restatement history, and staleness. Unsupported point-in-time history blocks the hypothesis family.

#### 7.2.12 Co-movement, diffusion, and lead–lag structure

Study changes in raw and residual correlation, dispersion, peer relationships, and propagation of stock-specific shocks. Shared market, sector, size, or liquidity exposure must be separated from apparent transmission. Stale and asynchronous prices are mandatory falsification checks.

#### 7.2.13 Risk and market regimes

Study states described by trailing market return, drawdown, volatility, breadth, dispersion, correlation, liquidity, concentration, or stable combinations of these. A regime is both a possible phenomenon and a conditioning context.

Regime labels must be derived from information available at the time. Full-sample clustering and retrospective peak/trough labels may support description only, not confirmatory conditioning.

#### 7.2.14 Equity lifecycle and calendar structure

Study IPO seasoning, listing maturity, distress, suspension, acquisition, delisting, earnings seasons, exchange-calendar structure, and recurring calendar effects where a plausible mechanism exists. Calendar searches require especially strict multiplicity budgets because unconstrained date partitions create large researcher freedom.

### 7.3 Catalogue entry contract

Every catalogue entry shall have a permanent ID and contain:

| Field group | Required content |
|---|---|
| Identity | Title, version, taxonomy, owner, reviewer, creation time, status history |
| Claim | Strategy-neutral scientific statement, unit, exposure/state, outcome, comparator, estimand |
| Time | Information cutoff, research clock, horizon, permissible lags, maturity date |
| Population | Geography, security types, point-in-time universe, peer/reference population, exclusions |
| Measurement | Canonical feature versions, outcome convention, missingness and outlier rules |
| Inference | Minimum relevant effect, precision/power target, dependence method, multiplicity family |
| Explanation | Proposed mechanism, competing explanations, confounders, falsifiers |
| Controls | Negative controls, placebo tests, artifact checks, sensitivity boundaries |
| Evidence | All experiments, datasets, results, replications, contradictions, reviews, and decisions |
| Limits | Known failure regions, data limitations, causal status, revalidation triggers |

### 7.3.1 Research Dependency Graph

The Research Dependency Graph is a first-class, version-controlled scientific artifact. It prevents experiments from running before their prerequisite measurements, classifications, data contracts, or scientific constructs are sufficiently established.

Graph nodes may represent:

- MDM capability and point-in-time data contracts;
- universe, identity, calendar, and timing decisions;
- feature definitions and Stage 2.5 validation dossiers;
- event or regime classifications;
- catalogue constructs and hypotheses;
- experiments, reproductions, and replications; and
- governed evidence or maturity decisions required by later work.

The primary directed edge is **requires**. Supporting edge types may include **produces**, **refines**, **blocks**, **invalidates**, and **supersedes**. Every edge records:

- permanent edge ID and version;
- exact source and target artifact versions;
- scientific rationale;
- minimum prerequisite status or evidence level;
- population, period, and domain in which the dependency applies;
- owner, reviewer, creation time, and supersession history;
- supporting decision or evidence; and
- current state: proposed, satisfied, conditionally satisfied, blocked, invalidated, or superseded.

The graph must reject unresolved cycles unless governance explicitly represents an iterative research programme with independently executable starting conditions. Each preregistration freezes the graph snapshot on which eligibility was decided.

Examples include:

- gap-continuation research **requires** an approved gap classification and validated gap features;
- sector-leadership research **requires** audited point-in-time sector history;
- institutional-activity proxy research **requires** validated volume, turnover, and liquidity features; and
- a regime-conditioned hypothesis **requires** a point-in-time regime definition with stable label semantics.

The research scheduler may release an experiment only when every mandatory incoming dependency is satisfied for the experiment’s declared domain. A later invalidation or supersession triggers a downstream impact review, potential feature or experiment revalidation, and evidence-profile update. It never silently deletes the affected history.

The dependency graph governs readiness. It is distinct from the Phenomena Interaction Graph in Stage 5, which describes scientific relationships among phenomena after evidence exists.

### 7.4 Catalogue governance

- A catalogue concept may evolve, but every hypothesis version is immutable after registration.
- A small, interpretable horizon dictionary shall be approved before empirical work. Additional horizons count as additional tests.
- Canonical measurement variants shall be motivated by distinct scientific clocks or definitions, not fine grids.
- Exploratory and confirmatory records must be visibly different.
- A post-result refinement is a child hypothesis, not a correction to the parent.
- Precise-null, contradicted, inconclusive—including underpowered—and invalid or abandoned work receives the same discoverability as supporting evidence.
- No catalogue status advances on a p-value, chart, model feature importance, or simulated profitability alone.

---

## 8. Stage 2 — Point-in-Time Feature Generation Engine

### 8.1 Scientific purpose

The feature engine creates hundreds of deterministic measurements for every eligible security and trading day, subject to MDM coverage. Its goal is rich, auditable measurement—not indiscriminate indicator generation. Features leaving Stage 2 are candidate measurements pending Stage 2.5 validation; generation alone does not make them eligible for discovery.

The feature panel and future outcomes must remain logically separated. A future label is attached only within an authorised experiment after the feature cutoff and outcome window have been enforced.

### 8.2 Conceptual processing responsibilities

| Responsibility | Scientific output |
|---|---|
| MDM receipt and manifest | Immutable source-vintage identity, coverage, and schema record |
| Point-in-time canonicalisation | Security identity, sessions, observations, events, classifications, and revisions |
| Daily observable panel | Values legitimately available at each approved cutoff plus quality flags |
| Atomic measurements | Minimally transformed returns, ranges, volumes, turnover, market cap, and event states |
| Historical measurements | Trailing features using prior or contemporaneously available observations only |
| Cross-sectional context | Leave-one-out peer, industry, sector, index, and market measurements |
| Regime descriptors | Trailing state measurements with stable, non-hindsight semantics |
| Feature-validation view | Frozen feature version, domain, inputs, expected invariants, and challenge dataset |
| Validated experiment feature view | Stage 2.5-approved selection of feature versions tied to a preregistration |
| Outcome view | Separately governed forward observations that cannot flow back into features |

These are logical responsibilities, not proposed software modules.

### 8.3 Feature-definition registry

Every feature version must specify:

- permanent feature ID and scientific construct;
- exact definition, unit, expected range, and invariants;
- source fields and full MDM lineage;
- observation cutoff and first permissible availability time;
- lag, lookback window, minimum valid history, and calendar treatment;
- eligible security types and universe requirements;
- corporate-action and return convention;
- peer membership, minimum size, fallback, weighting, and leave-one-out rules;
- transformation, scaling, ranking, clipping, and tie treatment;
- missing, stale, halted, insufficient-history, and not-applicable states;
- data-quality tests and quarantine rules;
- Research Dependency Graph prerequisites;
- Stage 2.5 validation status, scope, dossier, last review, and revalidation triggers;
- owner, reviewer, approval status, version, and supersession link; and
- known limitations and prohibited interpretations.

A changed formula or input convention creates a new version. Completed experiments continue to reference the old definition.

Definition approval and Stage 2.5 eligibility are separate decisions. The registry links, but never collapses, definition workflow, validation workflow, individual validation findings, feature-view conformance, and discovery-eligibility status.

### 8.4 Feature families

#### Price and path

- session, overnight, close-to-close, cumulative, and total-return measurements;
- intraday range and close location;
- distance from trailing extrema;
- drawdown depth, duration, and recovery;
- path efficiency, directional consistency, slope, and acceleration;
- return autocorrelation and reversal descriptors;
- raw and standardised gap measurements; and
- market-, sector-, industry-, index-, and peer-residual returns.

#### Volume and participation

- share and dollar volume;
- turnover relative to valid shares or float;
- relative volume against a security’s own trailing distribution;
- volume trend, persistence, surprise, concentration, and seasonality;
- price–volume coupling and carefully labelled signed-volume proxies;
- security contribution to group and market activity; and
- auction or block participation only where directly supplied by MDM.

#### Liquidity and market quality

Subject to audited MDM field fidelity:

- quoted, effective, or proxy spread with measurement type explicit;
- turnover, dollar-volume, and zero-return frequency;
- Amihud-style and other preregistered price-impact proxies;
- depth, resiliency, auction concentration, and discontinuity where observed;
- staleness, non-trading duration, halt, and minimum-tick states;
- changes, shocks, persistence, and recovery in liquidity;
- liquidity relative to security history and contemporaneous peers; and
- group and market liquidity breadth, dispersion, and concentration.

Proxy measures must not be labelled as observed spread, depth, or impact. Features that require intraday or quote data remain unavailable unless MDM passes the relevant point-in-time audit.

#### Volatility, distribution, and tails

- return- and range-based realised volatility;
- upside and downside semivariance;
- idiosyncratic volatility relative to point-in-time benchmarks;
- volatility ratios, changes, clustering, and volatility-of-volatility;
- jump and extreme-move frequency;
- skew, tail asymmetry, and drawdown statistics when sample size is adequate; and
- relative volatility within peers, industry, sector, and market.

#### Trend and persistence

- standardised direction and slope;
- directional consistency and path efficiency;
- absolute and residual trend;
- agreement or disagreement across the approved horizon dictionary; and
- persistence, acceleration, and decay of the measured state.

These describe conditions. They are not entry or exit rules.

#### Cross-sectional relative strength

- same-date percentile and robust standardised rank;
- excess or residual return relative to market, index, sector, industry, and peers;
- change and persistence in rank;
- peer-outperformance share; and
- dispersion-adjusted relative movement.

#### Breadth and concentration

- advance/decline and unchanged participation;
- new-high/new-low, trend, volatility, and volume participation;
- equal-weighted and authorised capitalisation-weighted breadth;
- sector and industry breadth;
- contribution concentration;
- cross-sectional dispersion and average co-movement;
- divergence between equal-weighted and capitalisation-weighted market states; and
- change, persistence, and asymmetry.

Every value includes eligible denominator, observed denominator, missing count, and coverage.

#### Sector, industry, index, and peer context

- group return, residual return, volatility, volume, liquidity, breadth, dispersion, and correlation;
- group leadership rank and persistence;
- internal participation and concentration;
- group-relative fundamental change where valid; and
- transmission descriptors between groups and members.

#### Fundamentals and earnings

Only where point-in-time MDM data pass audit:

- reported levels and changes;
- earnings, revenue, margin, cash-flow, balance-sheet, and capital-structure measures;
- contemporaneous surprise and revision measures;
- quality, growth, profitability, leverage, valuation, accrual, and dilution descriptors;
- filing age, reporting lag, version, and staleness; and
- event-time measurements around correctly timestamped releases.

Original values remain in force until a later version becomes publicly available.

#### Lifecycle, corporate-event, and calendar state

Subject to audited MDM identity and event histories:

- listing age, IPO seasoning, and time since resumption or relisting;
- suspension, halt, distress, acquisition, merger, spin-off, and delisting states;
- time since a publicly known corporate event and event-sequence position;
- index addition/removal announcement and effective states;
- distribution, split, issuance, and other corporate-action states;
- exchange session, weekday, month, quarter, reporting-season, and holiday-relative context; and
- point-in-time event density within peers, industry, sector, and market.

“Time until event” is admissible only for events whose future schedule was itself publicly known at the cutoff. Realised future events must never enter a feature retrospectively.

#### Market context

- broad-market and index return, volatility, volume, liquidity, trend, and drawdown;
- breadth, dispersion, correlation, and concentration;
- cross-sectional tail participation;
- sector-leadership distribution; and
- equal-weighted versus capitalisation-weighted divergence.

#### Observable institutional-activity proxies

- persistent abnormal dollar volume;
- price–volume asymmetry;
- signed-volume persistence proxies;
- low-impact high-volume episodes;
- closing-auction or block concentration when available; and
- concentrated activity around filings or events.

Names and documentation must make clear that these describe activity patterns, not participant identity.

#### Regime descriptors

- trailing market trend and drawdown;
- volatility and volatility-of-volatility;
- breadth level and deterioration;
- cross-sectional dispersion and correlation;
- liquidity and volume;
- sector and leadership concentration; and
- joint states fitted on prior data and frozen for the applicable future interval.

### 8.5 Cross-sectional feature architecture

Every security-day should resolve the point-in-time relationship:

**security → issuer → industry → sector → index membership or memberships → market**

Additional peer sets require an explicit economic rationale and time-valid membership. Cross-sectional calculations shall:

- exclude the subject from a comparison aggregate where self-inclusion creates mechanical association;
- prevent multiple share classes from unintentionally giving an issuer multiple weight;
- use declared equal, float, or capitalisation weighting;
- retain group identity, membership version, group size, observed size, coverage, and weighting;
- apply a fixed minimum peer count and fallback hierarchy;
- fit residualisation and normalisation only on information available by the cutoff;
- never use full-sample means, standard deviations, ranks, clipping points, or regime thresholds; and
- count related transformations and horizons in the appropriate multiple-testing family.

### 8.6 Horizon discipline

Hundreds of features are expected, but unrestricted parameter grids are prohibited. Each horizon shall correspond to an interpretable market clock—such as session, trading week, month, quarter, reporting cycle, or longer structural interval—and shall be approved before outcome inspection.

Features that differ only by many adjacent lookbacks are not independent scientific concepts. The registry must group them as one construct family, and discovery must account for all evaluated variants.

### 8.7 Missingness and quality states

Missingness is typed rather than collapsed:

- not yet listed;
- delisted;
- halted or suspended;
- not applicable;
- insufficient history;
- not yet public;
- stale;
- source absent;
- failed validation; or
- peer group too small.

Imputation is prohibited by default. Any scientifically necessary imputation must be preregistered, fitted on admissible prior data, and accompanied by a missingness indicator and sensitivity analysis.

Suspect observations are flagged or quarantined with their evidence retained. Silent correction, deletion, winsorisation, or replacement is prohibited.

### 8.8 Quality controls

Feature production must test:

- referential and temporal integrity;
- duplicate security-day rows;
- impossible open/high/low/close relations;
- invalid prices, shares, volumes, and market capitalisations;
- corporate-action discontinuities;
- return extremes requiring investigation;
- calendar and session consistency;
- staleness and trading halts;
- peer and cross-sectional coverage;
- unexpected distribution and missingness shifts;
- feature-specific invariants;
- look-ahead sentinels; and
- deterministic reproduction from the same MDM snapshot.

Quality reports must be stratified. A feature that is reliable for large caps but incomplete for distressed or delisted securities cannot receive one universal quality label.

Passing Stage 2 generation checks is necessary but not sufficient. Stage 2.5 independently challenges the frozen feature version before any Stage 3 outcome search.

### 8.9 Reproducibility manifest

Every experiment feature view must resolve to:

- MDM snapshot and schema identity;
- point-in-time universe manifest;
- security-master and classification versions;
- exchange calendars and cutoff policy;
- corporate-action and return policies;
- feature IDs and versions;
- missingness and quality policies;
- future computation-environment identity;
- deterministic seeds where applicable;
- row counts, coverage diagnostics, and fingerprints;
- feature-validation dossier IDs and domain-valid status; and
- the preregistration that authorised the view.

---

## 8A. Stage 2.5 — Feature Validation

Section identifier 8A preserves the established numbering of Stages 3–6 while inserting Stage 2.5 at its correct scientific position.

### 8A.1 Purpose and boundary

Stage 2.5 establishes whether a frozen feature definition and version is scientifically trustworthy as a measurement within a declared population, period, MDM lineage, and information cutoff.

Feature validation asks whether the feature measures what its definition claims, using only admissible information, with reproducible and stable behaviour. It does not ask whether the feature predicts returns or produces an attractive experimental result. Predictive outcome inspection belongs to Stage 3 and cannot be used to choose which feature version “passes” Stage 2.5.

Discovery must never operate directly on a feature merely because Stage 2 generated it or because routine generation checks passed. Only a feature version with a current Stage 2.5 status valid for the proposed experiment’s domain is eligible for Stage 3.

### 8A.1.1 Two-layer validation model

Feature validation has two linked layers:

1. **Feature-definition validation** establishes whether the immutable definition, interpretation, dependencies, point-in-time rules, numerical behaviour, failure states, and lineage pass the registered scientific challenges.
2. **Feature-view conformance** establishes whether one generated panel conforms to that validated definition for its exact MDM snapshot, universe, calendar, classifications, corporate actions, coverage, and computational environment.

A valid definition does not excuse a malformed feature panel. A conforming panel does not rescue an invalid definition. Stage 3 requires both a scope-compatible definition decision and a conforming feature-view record.

### 8A.2 Validation dimensions

Feature validation applies the following dimensions where scientifically relevant:

| Dimension | Required scientific challenge |
|---|---|
| Deterministic reproducibility | Regenerate the same values from the frozen MDM snapshot, definition, environment, universe, and manifest |
| Point-in-time correctness | Demonstrate that every input, transformation, membership, threshold, and fitted quantity was available by the declared cutoff |
| Absence of information leakage | Test future-information sentinels, shifted timestamps, full-sample transformations, target separation, and retrospective adjustment risks |
| Numerical stability | Challenge precision, scale, overflow, underflow, tiny denominators, ties, sparse groups, and approved platform tolerances |
| Missing-data robustness | Examine typed missingness, missing-not-at-random patterns, coverage by segment, insufficient-history behaviour, and any preregistered imputation |
| Sensitivity analysis | Test a small, predeclared set of scientifically defensible conventions without selecting the variant with the best later outcome |
| Revision behaviour | Measure changes across authorised MDM vintages, corrections, restatements, classification revisions, and corporate-action updates |
| Computational determinism | Verify that parallel order, partitioning, resampling seeds, and repeated execution reproduce exact or approved tolerance-based results |
| Version consistency | Confirm that generated values match the registered formula, source versions, dependency versions, status, and supersession history |
| Data-lineage integrity | Trace every output through all transformations to authorised MDM fields, identities, calendars, classifications, and snapshots |

Additional construct-specific challenges may include:

- cross-sectional self-exclusion and peer-denominator integrity;
- issuer/share-class aggregation;
- raw versus adjusted price reconciliation;
- dimensional units and expected invariances;
- distribution, range, and monotonicity checks;
- boundary behaviour around minimum history and group size;
- coverage stability across time, market cap, liquidity, exchange, sector, and lifecycle; and
- conservative behaviour when publication time or data validity is ambiguous.

Sensitivity analysis is adversarial measurement review, not parameter optimisation. A sensitive feature may still be validated conditional if its domain and interpretation are narrowed in advance. A sensitivity variant inspired by results becomes a new feature version with its own lineage and validation obligation.

### 8A.2.1 Governed validation workflow

The governed workflow is:

1. **Intake:** Resolve the exact feature version, construct, domain, MDM inputs, and dependencies.
2. **Dependency gate:** Confirm that prerequisite data contracts, classifications, calendars, feature versions, and scientific components are eligible.
3. **Protocol freeze:** Register mandatory challenges, tolerances, reference cases, coverage, reviewer, statuses, and revalidation triggers.
4. **Reference reconstruction:** Reconstruct declared cases and confirm formula, unit, timing, identity, and quality-state behaviour.
5. **Temporal and leakage challenge:** Test availability, joins, lags, revisions, memberships, corporate actions, truncation, and future-data isolation.
6. **Numerical and computational challenge:** Test edge conditions, repeated execution, ordering, parallel aggregation, seeds, and tolerances.
7. **Missingness and sensitivity challenge:** Test typed missing states, admissible data loss, boundary conditions, defensible conventions, and conditional coverage.
8. **Vintage and version challenge:** Examine MDM corrections, schema changes, dependency versions, and consistency between definition, manifest, and output.
9. **Independent review and adjudication:** Deposit all evidence and assign a scoped feature decision.
10. **Feature-view conformance:** Verify the exact panel’s fingerprints, rows, coverage, dependencies, and validation envelope before Stage 3 admission.

Validation fails closed. Missing evidence is not a pass, and reviewer discretion cannot convert an unresolved point-in-time, leakage, authorised-lineage, or deterministic-reconstruction failure into an eligible feature.

### 8A.3 Feature-validation dossier

Every feature-validation attempt and state receives an immutable dossier containing:

- feature ID, version, scientific construct, unit, and exact definition;
- validation ID, owner, independent reviewer, and review time;
- MDM snapshot, schema, source partitions, and input fingerprints;
- security, universe, calendar, classification, peer, and corporate-action manifests;
- applicable Research Dependency Graph snapshot;
- validation population, dates, cutoffs, and declared domain;
- every required validation dimension and its registered acceptance rule;
- challenge datasets, sentinels, seeds, tolerances, and execution provenance;
- complete results, including failed checks and unavailable tests;
- coverage, missingness, revision, distribution, and sensitivity profiles;
- deterministic or tolerance-based reproduction result;
- known limitations, prohibited interpretations, and unresolved risks;
- status, status rationale, reviewer disagreement, and evidence links;
- revalidation triggers and next review date;
- expected and actual research-cost metadata; and
- supersession and downstream-impact links.

Feature-validation evidence is deposited whether the feature passes or fails. An abandoned validation records the stopping point, observed evidence, resource consumption, and reason.

### 8A.4 Feature-validation states

Feature workflow and validation conclusions remain separate. Recommended validation states are:

- **validation pending:** generated but not eligible for discovery;
- **validated:** all mandatory measurement gates pass within the declared domain;
- **validated conditional:** trustworthy only within explicitly bounded populations, periods, coverage, or conventions;
- **rejected:** valid evidence shows that the feature cannot meet its registered measurement claim;
- **inconclusive:** evidence or coverage is insufficient to decide;
- **invalid:** the validation procedure or required lineage failed;
- **quarantined:** prior eligibility is suspended while a material anomaly or dependency is reviewed;
- **revoked:** later valid evidence establishes a material defect in a previously eligible version;
- **revalidation due:** a trigger has consumed the current approval; and
- **superseded:** a new version exists, while the historical dossier remains retained.

“Validated feature” means measurement-trustworthy within scope. It does not mean predictive, economically useful, causally meaningful, or strategy-eligible.

### 8A.5 Admission to Stage 3

A Stage 3 preregistration must resolve every requested feature to:

1. an exact feature version;
2. a complete Stage 2.5 dossier;
3. a validated or validated-conditional state covering the experiment’s population, dates, cutoff, and MDM lineage;
4. satisfied mandatory dependencies;
5. unexpired review and revalidation conditions; and
6. a reproducibility manifest that matches the experiment feature view.

If any resolution fails, the scheduler blocks the experiment. Feature eligibility cannot be waived. A scope extension, revised definition, or renewed validation request creates new Stage 2.5 work and may not use the blocked feature in discovery before that work passes. Unvalidated features may be examined only within Stages 2 and 2.5 for measurement development and challenge; they may not be exposed to Stage 3 outcomes.

Derived and composite features require every upstream feature version to be valid for the same domain and must also pass their own Stage 2.5 validation. Upstream approval does not prove that a new combination is leakage-free, numerically stable, or scientifically coherent.

### 8A.6 Revalidation and downstream impact

Revalidation is triggered by material changes to:

- formula, parameter, horizon, lag, cutoff, scaling, clipping, ranking, tie, or fallback rules;
- missingness, imputation, outlier, halt, or stale-data treatment;
- security identity, universe, calendar, peer, classification, or weighting rules;
- raw/adjusted price or corporate-action policy;
- MDM schema, snapshot semantics, source history, correction, or revision behaviour;
- computational environment beyond approved numerical tolerances;
- construct interpretation or prohibited-use boundaries; or
- observed coverage or distribution behaviour outside registered validity limits.

A trigger marks the affected feature version revalidation due. The Research Dependency Graph identifies downstream features and experiments, while the Knowledge Base records the impact on phenomenon evidence profiles. Prior results remain visible and may be retained, downgraded, superseded, or invalidated only through explicit review.

### 8A.7 Governance and prohibited shortcuts

The feature author may not be the sole validation authority. Review should include the MDM/data steward and an independent measurement or methods reviewer. Feature validation itself receives research-cost metadata and scheduler admission, but it is not charged to a Stage 3 discovery budget unless it creates or screens exploratory feature variants.

Stage 2.5 prohibits:

- treating successful generation as scientific validation;
- validating a feature because it predicts an attractive outcome;
- comparing many definitions and approving the best-performing one;
- using full-sample ranks, thresholds, normalisations, or regime labels;
- ignoring conditional failure in small, illiquid, distressed, or delisted populations;
- carrying approval across a material feature or MDM version change;
- concealing rejected, inconclusive, abandoned, or superseded feature versions; and
- bypassing dependency, review, or revalidation gates for scheduling convenience.

---

## 9. Stage 3 — Phenomena Discovery Engine

### 9.1 Purpose

The Discovery Engine asks whether an observable state contains stable information about a later market behaviour relative to an appropriate point-in-time baseline. It estimates effect size, uncertainty, response shape, decay, scope, and stability.

The Discovery Engine may consume only exact feature versions that have passed Stage 2.5 for the experiment's declared domain and whose generated feature view has a current conformance record. Feature eligibility is resolved before outcome access and fails closed if a dossier, dependency, scope, lineage, or revalidation condition is unresolved.

It does not search for entries, exits, leverage, position sizes, portfolios, maximum Sharpe ratio, or profitable combinations.

Permissible outcomes include:

- future absolute, excess, or residual return distributions;
- volatility level, transition, duration, and tail risk;
- gap closure probability and duration;
- volume and liquidity change;
- breadth, participation, and concentration transitions;
- correlation and dispersion change; and
- persistence, decay, or reversal of a measured condition.

### 9.2 Candidate discovery unit

A discovery unit combines:

1. a catalogue construct;
2. an exposure or state;
3. a point-in-time population and comparator;
4. one primary outcome and horizon;
5. an estimand and dependence-aware inference method;
6. a declared test family;
7. a minimum relevant effect;
8. negative controls and artifact checks; and
9. a proposed mechanism, rival account, and falsifier.

The unit also resolves the exact feature IDs, Stage 2.5 dossiers, feature-view conformance record, Research Dependency Graph snapshot, discovery-budget allocation, Research Cost estimate, and frozen ESIG assessment that authorised it for scheduling. These planning records govern eligibility and priority; they do not become evidence for or against the hypothesis.

This structure makes a tested relationship auditable and prevents an attractive chart from becoming a candidate without a complete scientific statement.

### 9.3 Discovery workflow

1. **Intake:** Link the question to a catalogue entry and identify whether it is theory-led or exploration-led.
2. **Registration:** Freeze the intended discovery analysis, dataset assignment, test family, reporting set, and controls before the relevant outcomes are inspected.
3. **Panel construction:** Build the eligible security-day or event panel from immutable universe and feature manifests.
4. **Integrity check:** Enforce cutoffs, membership, feature/outcome separation, coverage accounting, and overlap rules.
5. **Primary estimation:** Execute every registered test, including expected nulls and controls.
6. **Distributional profiling:** Report magnitude, uncertainty, monotonicity or shape, decay, prevalence, and base rates.
7. **Artifact challenge:** Test dominance, leakage, microstructure, common exposures, and alternative admissible measurements.
8. **Multiplicity accounting:** Record all variants and apply the registered family policy.
9. **Independent review:** Review data validity, method, interpretation, and untouched validation availability.
10. **Disposition:** Promote to candidate; record a precise-null candidate, contradiction, non-confirmation, inconclusive reason, or invalid run; or register a distinct child hypothesis.

Before Registration, the scheduler-facing planning gate verifies prerequisite satisfaction, Stage 2.5 eligibility, discovery-budget availability, the Research Cost estimate, and the frozen ESIG record. Panel construction verifies conformance of the exact generated view rather than assuming that definition-level validation guarantees every panel. Any failure returns the work to the relevant earlier stage without exposing Stage 3 outcomes.

### 9.4 Supported scientific designs

#### Conditional distribution profiling

Compare future outcome distributions across preregistered exposure states using means, medians, quantiles, scale, skew, tail probabilities, duration, and probability of superiority where appropriate. A mean difference alone is not a full description.

#### Cross-sectional cohort and dose–response analysis

Use predeclared same-date ranks or cohorts to assess monotonicity, nonlinearity, saturation, and reversal. Bins and breakpoints cannot be selected after observing outcomes.

#### Repeated cross-section and panel analysis

Estimate relationships while accounting for common date shocks, security persistence, issuer duplication, sector structure, and fixed confounders. Depending on the question, suitable methods may include repeated cross-sectional estimates, date/security effects, and date- and issuer-aware inference.

#### Event studies

Align observations by valid public event time and compare with a declared baseline or matched control. Matching rules are fixed without post-event outcomes. Anticipation, after-hours assignment, overlapping events, common announcement dates, and confounding events must be reported.

#### State-transition, persistence, and duration analysis

Estimate the probability and time of remaining in, leaving, or moving between conditions. This is suitable for volatility states, drawdown recovery, gap closure, liquidity stress, and leadership persistence.

#### Dependence, diffusion, and network analysis

Measure peer, sector, and market propagation with controls for shared exposures and explicit accounting for large numbers of relationships. Lead–lag candidates must survive stale-price and asynchronous-trading tests.

#### Unsupervised exploration

Clustering, anomaly detection, and representation methods may organise discovery data and generate questions. They cannot validate a phenomenon. Any candidate must be translated into an interpretable frozen hypothesis and tested on untouched data.

#### Interpretable predictive screening

Predictive models may be used only for exploratory triage. Feature importance or model accuracy is not evidence of a phenomenon. A relationship must be restated as a falsifiable estimand and enter the normal pipeline.

### 9.5 Dependence-aware inference

Equity observations have strong common-date, sector, issuer, and temporal dependence. Millions of stock-day rows are not millions of independent experiments.

Inference must address:

- serial correlation within securities;
- cross-sectional correlation from market and sector shocks;
- overlapping forward outcomes;
- multiple share classes;
- event clustering;
- persistent conditioning states;
- sparse and asynchronous trading; and
- repeated inspection of the same history.

Before experimentation, methods governance shall approve a design-to-estimator matrix for repeated cross-sections, persistent security states, event studies, duration outcomes, and network or diffusion tests. The matrix shall specify:

- admissible estimators and estimands;
- minimum effective date, issuer, sector, and event-cluster counts;
- small-cluster corrections and finite-sample fallbacks;
- resampling unit and block-length selection;
- exchangeability conditions for permutation procedures;
- treatment of shared-market-date dependence;
- covariance treatment for overlapping outcomes; and
- conditions under which the available data are not inferable.

Each preregistration selects the applicable row of that matrix from its design, not from whichever method later gives the narrowest interval. Power and minimum detectable effects use the same dependence assumptions, preferably through cluster-aware calculation or simulation, never raw row counts. Independent-row standard errors are inadmissible.

Any matched, residualised, neutralised, or otherwise adjusted analysis must state whether its estimand is a raw association, total association, or conditional association; establish the temporal order and scientific justification of every adjustment; prohibit post-exposure, collider, outcome-derived, and future-derived controls; fit benchmarks point in time; and propagate benchmark-estimation uncertainty where material.

### 9.6 Multiple-testing and search ledger

Every feature, transformation, horizon, threshold, subgroup, interaction, outcome, model, and abandoned variant belongs in the global search and exposure ledger. The ledger records:

- planned, attempted, failed, and abandoned tests;
- raw and adjusted evidence;
- related experiments and descendant hypotheses;
- analysts or automated searches exposed to each data period;
- every use of discovery, confirmation, and replication partitions; and
- the remaining unexposed data reserve.

Global disclosure and statistical error-control families are related but not identical. An indefinitely growing programme cannot treat every ancestral test as one static family. The architecture shall distinguish:

- a declared discovery campaign, controlling false discovery across every screened candidate and variant in that campaign;
- a sealed-sample confirmatory family, controlling family-wise error across every confirmatory claim jointly tested on that sample;
- ordered secondary claims governed by a registered gatekeeping rule;
- a programme-level sequential allocation for repeated confirmations, using a finite alpha budget, approved online FWER/FDR method, alpha-investing, e-values, or another explicitly justified always-valid framework; and
- selective-inference treatment when exposed data helped define the reported claim.

A genuinely fresh sealed confirmation is not mechanically assigned the entire exploratory denominator, but the selection history remains visible and every candidate sharing that confirmation opportunity belongs to its confirmatory family. A nominally new descendant cannot reset error control when it reuses exposed outcomes or the same confirmatory decision.

Every registered family identifies the decision unit, included hypotheses, target error quantity and rate, dependence assumptions, stopping rule, hierarchy, sample, and treatment of descendants. False-discovery-rate control can support broad screening; strong family-wise control or dependence-aware resampling is preferred for finite confirmatory families.

Correlated features do not constitute independent confirmation. Selecting the best window, threshold, transform, cohort, segment, or regime is multiple testing even if only one is reported.

The global search and exposure ledger is not the discovery-budget ledger. The search ledger records everything attempted or exposed and supports statistical error control. The discovery-budget ledger limits how much exploratory freedom was authorised before exposure. A test may therefore be fully disclosed in the search ledger yet still represent an unauthorised budget overrun; conversely, an authorised budget does not remove the test from multiplicity accounting.

Exploratory work reserves the relevant budget units before execution and consumes them when outcome-bearing feedback can influence a research decision, including automated screening, failed runs that revealed outcomes, abandoned branches, and apparently null variants. Exhaustion invokes the controls in Section 13.6.1; it cannot be reset by renaming a feature, hypothesis, campaign, regime, or descendant.

### 9.7 Holdout firewall

Data are labelled as:

- **discovery data**, available for hypothesis generation;
- **sealed confirmation data**, opened only after a complete preregistration; or
- **replication reserve**, retained for later or analyst-independent testing.

A holdout is consumed when its outcomes influence a decision. Repeatedly inspected data become discovery data. A failed holdout cannot be presented as untouched for a modified descendant. If all historical data have been exposed, the honest status is retrospective evidence awaiting future MDM observations.

### 9.8 Required reporting

Every discovery report contains:

- effect size in natural and standardised units;
- uncertainty interval under the declared dependence model;
- base rate and absolute change in base rate;
- outcome distribution and response shape;
- horizon profile and decay;
- numbers of dates, issuers, securities, events, sectors, and effective independent units;
- coverage and typed missingness;
- raw and multiplicity-adjusted evidence;
- temporal, size, liquidity, sector, and market-state stability;
- influence diagnostics for dominant dates, issuers, and segments;
- placebo and negative-control results;
- sensitivity to preregistered defensible measurement conventions;
- common-exposure and competing-explanation analysis; and
- evidence classification and limitations.

Visual reporting must show complete response surfaces and uncertainty, not only the most favourable bin.

### 9.9 Candidate promotion gate

A discovery can advance to Stage 4 only if:

- the registered analysis is complete and all deviations are visible;
- every feature version and exact generated view retained a valid Stage 2.5 decision throughout the run;
- every mandatory Research Dependency Graph prerequisite was satisfied on the frozen eligibility snapshot;
- the discovery-budget reservation and consumption record is complete, with no unapproved overrun;
- the Research Cost estimate and append-only actual-cost record are deposited, without using cost or ESIG to alter the evidential decision;
- MDM lineage, point-in-time construction, and data-quality gates pass;
- the effect meets the predefined scientific-materiality rule;
- uncertainty respects cross-sectional and temporal dependence;
- the full test family is recorded and multiplicity handled;
- the response is interpretable rather than one isolated favourable bin;
- it is not dominated by a few dates, issuers, sectors, or micro-cap observations;
- negative controls do not indicate leakage or artifact;
- a plausible mechanism and serious rival explanations are documented;
- an independent methods reviewer approves the evidence package; and
- genuinely untouched validation data remain.

Other valid Stage 3 dispositions are precise-null candidate, contradicted, not confirmed, inconclusive with reason, methodologically invalid, exploratory-only, or revised hypothesis required. Every disposition is retained.

### 9.10 Prohibited discovery behaviour

- using a pending, rejected, inconclusive, invalid, quarantined, revoked, superseded, revalidation-due, or out-of-scope feature version;
- executing before mandatory dependency, discovery-budget, Research Cost, or ESIG planning records are complete;
- exceeding an exploration budget and hiding the overrun through renamed families, descendants, partitions, horizons, or automated searches;
- changing ESIG after outcome exposure or treating low cost, high ESIG, or scheduler priority as evidence;
- searching directly for trading systems;
- optimising thresholds, windows, horizons, filters, or feature combinations;
- constructing portfolios, entries, exits, leverage, stops, or position sizes;
- ranking candidates primarily by simulated profit or Sharpe ratio;
- reporting only the strongest variant;
- reusing validation data until a result passes;
- treating predictive importance as scientific confirmation;
- using hindsight regimes;
- concealing negative, abandoned, or contradictory work;
- attributing participant identity without direct MDM evidence; or
- making causal claims from predictive association.

---

## 10. Stage 4 — Scientific Validation

### 10.1 Purpose and evidentiary standard

Validation determines whether a candidate is a repeatable, scientifically material equity-market behaviour rather than an artifact of leakage, sampling, microstructure, common exposure, one historical episode, or multiple testing.

Validation establishes reproducible association unless an explicit causal design supports more. It does not establish profitability. Three judgments are recorded separately:

1. **Scientific validity:** does the evidence support the registered association within its declared population, dates, measurements, and uncertainty?
2. **Explanatory credibility:** which mechanisms remain consistent with the evidence?
3. **Implementation relevance:** what can standardised friction stress, liquidity, breadth, and concentration descriptors establish, and what remains not assessable until Stage 6?

A strongly supported association can be scientifically validated but impractical. Apparent practicality cannot rescue invalid data or inference.

No parameter tuning, model selection, threshold adjustment, or optimisation is allowed during validation. A material post-result change creates a new linked hypothesis requiring untouched evidence.

### 10.2 Mandatory validation gates

1. **Eligibility gate:** The complete Stage 3 record, search lineage, candidate definition, discovery-budget record, and frozen dependency decision are available.
2. **Preregistration gate:** The confirmatory protocol is frozen before sealed outcomes are accessed.
3. **Data-integrity gate:** Identity, universe, timestamps, adjustments, classifications, and MDM lineage pass.
4. **Feature-continuity gate:** Every exact feature version and generated view has a current Stage 2.5 decision covering the validation domain, with no unresolved revalidation trigger.
5. **Primary-test gate:** The prespecified estimand and inference method are run once on the reserved sample.
6. **Temporal gate:** The unchanged phenomenon is assessed through registered rolling-origin or walk-forward evidence; descriptive monitoring is kept separate.
7. **Cross-sectional gate:** Mechanism-led confirmatory interactions and a standard descriptive transportability panel examine capitalisation, sector, industry, liquidity, and lifecycle heterogeneity.
8. **Regime gate:** Preregistered regime claims are tested inferentially; other bull/bear, volatility, participation, liquidity, and related states are descriptive diagnostics.
9. **Robustness and falsification gate:** Negative controls and adversarial sensitivity checks challenge the claim.
10. **Multiplicity gate:** Global ancestry is disclosed and the applicable discovery, sealed-sample, and sequential decision families pass their registered error control.
11. **Reproduction and replication gate:** The result is computationally reproduced, independently reimplemented, and directly tested on genuinely new eligible outcomes.
12. **Adjudication gate:** A governed decision, continuous evidence-profile update, interaction assessment, and complete dossier enter the Knowledge Base regardless of outcome.

Preregistration failure, point-in-time failure, concealed multiplicity, or failed reproduction is non-compensatory. No robustness score can override it.

### 10.2.1 Output roles and decision function

Every registered output receives exactly one role before exposure:

- **primary confirmatory evidence:** determines the main hypothesis decision;
- **ordered confirmatory secondary evidence:** can affect the decision only through its registered gatekeeping rule;
- **diagnostic:** describes stability, transportability, or artifacts but cannot strengthen the primary claim;
- **safety sentinel:** a failed leakage, timing, identity, or integrity check invalidates the run under a predeclared rule; or
- **exploratory output:** can create a descendant hypothesis but cannot affect the current confirmation.

The preregistration defines a complete decision function mapping the primary result, ordered secondary results, sentinel outcomes, missing ancillary tests, temporal heterogeneity, confirmatory interactions, and replication result to the canonical states in Section 3.8. Reviewers adjudicate compliance and interpretation; they do not invent the decision rule after observing the evidence.

### 10.3 Immutable preregistration

Each validation receives a permanent experiment ID and a timestamped immutable specification containing:

- parent catalogue, discovery, and hypothesis lineage;
- precise claim, direction, mechanism, and rival explanation;
- exposure or conditioning variable;
- primary outcome, horizon, unit, and observation cutoff;
- primary estimand, smallest effect of scientific interest, and its outcome-based rationale independent of selected discovery estimates and trading frictions;
- eligible securities, exchanges, dates, listing-age rules, and exclusions;
- universe, peer, and classification construction;
- exact feature versions and transformations, Stage 2.5 dossier IDs, validation scope, expiry or revalidation conditions, and feature-view conformance requirements;
- frozen Research Dependency Graph snapshot and prerequisite decision;
- Research Cost estimate, frozen ESIG assessment, scheduler decision, and applicable discovery-budget record, retained separately from evidential outputs;
- missing, stale, outlier, halt, corporate-action, and delisting policy;
- registered design-to-estimator policy row, statistical model, dependence correction, confidence level, and diagnostics;
- adjustment estimand, temporally ordered covariates, benchmark-fitting rule, and prohibited post-exposure controls;
- sealed sample and walk-forward schedule;
- separate rules for fitting-target leakage across boundaries and inference for overlapping validation outcomes;
- market-cap, sector, industry, liquidity, lifecycle, and regime panels, each labelled confirmatory or diagnostic;
- primary, ordered secondary, diagnostic, safety-sentinel, exploratory, robustness, and falsification outputs;
- complete decision function and treatment of unavailable ancillary outputs;
- discovery, sealed-sample, and programme-sequential testing families, their decision units, target error quantities, dependence assumptions, stopping rules, and correction methods;
- required issuers, dates, events, effective sample size, power, and minimum detectable effect;
- run-finding, hypothesis-decision, and phenomenon-maturity recommendations using the Section 3.8 vocabulary;
- mandatory survivorship artifact: inactive/delisted inclusion, terminal-outcome coverage, attrition by segment, and comparison with a survivor-only view where scientifically meaningful;
- fixed friction stress mappings and liquidity/concentration descriptors where scientifically applicable;
- direct-replication prediction or compatibility rule and independent reviewers;
- exact MDM snapshot identity; and
- deterministic seeds for registered resampling.

The preregistration and referenced inputs receive immutable fingerprints. Corrections are append-only amendments with author, time, and reason. An amendment after outcome access normally creates a new experiment version and cannot restore holdout status.

### 10.4 Validation isolation

The validation process must be able to demonstrate who or what had access to each time period and result. Organisational exposure matters: a period is not an honest holdout simply because it was absent from the final reported model.

A sealed sample is opened only for its registered purpose. Failed confirmation data cannot be reused as untouched evidence for a modified hypothesis. When all existing history has influenced the hypothesis, only provisional retrospective evidence is possible until future or otherwise reserved MDM observations mature.

### 10.5 Primary inference and effect reporting

The primary test defines the unit of analysis and uses the preregistered row of the governed design-to-estimator matrix in Section 9.5. That row, rather than post-result analyst choice, determines whether inference uses:

- issuer and date clustering;
- heteroskedasticity- and autocorrelation-consistent uncertainty;
- date-block or stationary bootstrap that preserves cross-sectional structure;
- within-date or within-sector permutation;
- event-level aggregation;
- matched or residualised comparisons fixed in advance; or
- dependence-aware combinations of these.

The design must meet the matrix’s effective-cluster, finite-sample, exchangeability, block-length, and overlap requirements. If it does not, the result is not inferable. Power is assessed under the same dependence model.

Every primary result reports:

- effect in natural units;
- standardised effect;
- confidence interval;
- minimum scientifically relevant effect or equivalence region;
- prevalence, base rate, and absolute base-rate change;
- probability of superiority or another distributional measure where appropriate;
- rank association, slope, or incremental explanatory measure where relevant;
- preregistered horizon-decay profile;
- issuers, securities, dates, events, sectors, and effective independent units;
- dominant-date, issuer, sector, liquidity, and micro-cap sensitivity; and
- raw and multiplicity-adjusted evidence.

It also includes the mandatory survivorship artifact: inactive and delisted coverage, terminal-outcome availability, attrition by period and segment, and the difference from a survivor-only view where that comparison is meaningful.

Statistical significance is insufficient when the interval supports only a negligible effect. Failure to reject is not automatically a null. Run findings use the Section 3.8 vocabulary:

- **supported:** direction, materiality, and uncertainty rules pass;
- **precise null:** an equivalence test or multiplicity-adjusted compatibility interval lies wholly within the preregistered negligible-effect region;
- **contradicted:** evidence opposes the predicted direction or excludes the registered claim;
- **inconclusive:** uncertainty remains too wide, with underpowered recorded as a reason where applicable; or
- **invalid:** integrity or protocol failure prevents inference.

### 10.5.1 Selection-induced inflation

Candidate selection tends to exaggerate discovery effects. The validation dossier shall therefore:

- display discovery, confirmation, and replication estimates separately;
- base confirmation and replication power on the independently chosen minimum relevant effect, not the selected discovery estimate;
- register a replication prediction or compatibility region before new outcomes are seen;
- report attenuation, sign reversal, and uncertainty expansion;
- use shrinkage or hierarchical synthesis only when registered and scientifically justified; and
- never pool discovery and confirmation before presenting the untouched confirmation estimate.

### 10.5.2 Survivorship-bias challenge

Every survivorship-sensitive validation produces a dedicated artifact that:

- reconciles the daily eligible population to active, suspended, acquired, bankrupt, delisted, and otherwise inactive securities;
- reports terminal-outcome and delisting coverage;
- traces attrition and missing outcomes by time, market cap, liquidity, sector, exchange, and lifecycle;
- quantifies how the primary estimate differs from a deliberately survivor-only view as a bias diagnostic;
- applies preregistered bounds or missing-not-at-random sensitivity where terminal data remain incomplete; and
- blocks or narrows the claim when plausible missing outcomes could materially change the estimand.

The survivor-only comparison is never the primary estimate. It makes the direction and potential scale of survivorship bias visible.

### 10.6 Walk-forward validation

At each registered cutoff:

1. every feature and cohort is reconstructed from information available by that cutoff;
2. nuisance estimates, normalisation, residualisation, and breakpoints use only prior estimation data;
3. the frozen hypothesis is evaluated in the next unseen interval;
4. fitting or training observations whose targets cross into the evaluation information set are purged when those outcomes could influence fitted quantities;
5. any embargo is derived from the label definition, fitting process, and information path rather than automatically set to the maximum horizon;
6. outcomes fully mature before influencing later estimation; and
7. each fold is retained even if it fails.

Overlap among forward outcomes inside a frozen evaluation window is primarily an inference-dependence problem, not something an embargo removes. The registered covariance or resampling method must represent that overlap.

Expanding-origin and fixed-length rolling designs answer different questions. Expanding designs assess cumulative persistence; rolling designs reveal decay and structural change. Their roles, lengths, and combination rule must be preregistered.

The report includes fold-level effects and intervals, sign consistency, effect dispersion, heterogeneity, proportion of folds above the relevant-effect boundary, possible structural breaks, and sensitivity to calendar boundaries. A large pooled result cannot conceal repeated fold reversals.

### 10.7 Rolling-window stability

In addition to formal walk-forward folds, the fixed phenomenon definition is examined through rolling windows to estimate:

- effect trajectory and confidence band;
- sign and rank stability;
- decay or strengthening;
- time-to-failure and recovery;
- dependence on a single market episode;
- relation to structural changes in coverage or market structure; and
- last date on which the evidence remained inside its validity bounds.

Rolling analysis is descriptive unless the protocol specifies simultaneous confidence bands, a registered change-point procedure, or always-valid sequential inference. Pointwise intervals must not drive “time-to-failure,” “recovery,” or revalidation decisions under repeated inspection. Ongoing revalidation that can change knowledge status requires its own sequential error budget. Any unregistered boundary found after inspection becomes a new hypothesis.

### 10.8 Cross-sectional segmentation

At minimum, validation reports a standard descriptive point-in-time transportability panel across:

- micro-, small-, mid-, and large-cap populations;
- sector and adequately powered industry groups;
- liquidity and turnover groups;
- exchange or listing venue;
- security age and lifecycle;
- index members and non-members; and
- broad peer-relative contexts.

Breakpoints and membership are reconstructed at each date. Minimum group size, intersection depth, and weighting are fixed in advance. Sparse cells are reported, not silently merged after results are seen.

The standard panel cannot strengthen the primary claim and does not require a phenomenon to “pass” every cell. Only mechanism-led interactions declared confirmatory before exposure may alter the hypothesis decision, and those interactions receive their own multiplicity control. Where many groups are estimated, hierarchical or partial-pooling methods should be used under the approved inference policy. Insufficient cells produce an **unresolved heterogeneity** limitation.

Confirmatory heterogeneity is assessed with interactions or direct difference tests. “Significant in one segment, not significant in another” does not establish that the segments differ.

A phenomenon need not be universal. If a proposed mechanism predicts a bounded segment and locked evidence supports it there, the Stage 4 hypothesis decision is **confirmed conditional**; only later Stage 5 synthesis may assign a context-bound validated maturity. Unexpected concentration in micro-caps, illiquid securities, or one sector triggers additional artifact investigation.

### 10.9 Market-state and regime validation

Regimes must be computable from lagged or contemporaneous information. The standard descriptive panel may include:

- advancing versus declining or bull versus bear context;
- high versus low volatility;
- broad versus narrow participation;
- liquid versus stressed markets;
- high versus low cross-sectional dispersion or correlation;
- concentrated versus diffuse sector leadership; and
- transitions between these states.

Thresholds are learned from prior data or fixed externally before validation, never from full-sample percentiles. Only regimes predicted by the registered mechanism are confirmatory; the rest are diagnostics and cannot strengthen the claim. A phenomenon is not required to pass an irrelevant regime. Confirmatory interaction estimates are preferred to isolated within-regime p-values and belong to a declared multiplicity family.

Retrospective peak/trough or full-history cluster labels may be shown descriptively but cannot support a confirmatory regime claim.

### 10.10 Multiple-testing control

The registry supplies complete ancestry and data-exposure disclosure. It does not force an indefinitely growing programme into one undefined static denominator. Validation applies the decision-aware framework in Section 9.6:

- the discovery campaign accounts for every screened feature, horizon, outcome, and segment under its registered FDR or selection policy;
- every candidate jointly tested on one sealed sample enters that sample’s finite confirmatory family under strong FWER or an approved dependence-aware alternative;
- ordered secondary claims use registered hierarchical gatekeeping;
- repeated confirmatory opportunities draw from a finite programme allocation or approved online/always-valid procedure; and
- a claim shaped by exposed outcomes requires selective-inference treatment or genuinely fresh confirmation.

For every decision family, the preregistration states the hypotheses, decision unit, target error quantity and rate, dependence assumptions, stopping rule, hierarchy, and descendant policy. Raw evidence is retained alongside corrected evidence. Analyst discretion and abandoned variants remain visible.

A fresh sealed test need not be mechanically penalised for the entire exploratory ancestry, but selection is never concealed, all candidates sharing that test are counted, and a nominally new submission cannot reset multiplicity when it reuses exposed outcomes or the same decision opportunity.

### 10.11 Robustness and falsification

Robustness challenges the phenomenon; it does not search for a better version. Preregistered challenges should include, where relevant:

- negative-control exposures and outcomes;
- impossible future leads and shifted timestamps;
- pseudo-events;
- dependence-preserving permutations;
- alternative valid feature definitions;
- reasonable alternative missingness and outlier policies;
- removal of the most influential dates, issuers, sectors, or event clusters;
- conditioning on market, sector, size, liquidity, and other common exposures;
- alternate valid corporate-action and return representations;
- stale-price, bid–ask, minimum-tick, and asynchronous-trading checks;
- alternate admissible universe boundaries; and
- placebo horizons at which the mechanism predicts no effect.

The registered primary estimate remains authoritative. A specification curve is descriptive unless the entire set was registered before outcomes were known. Choosing its strongest point creates a new discovery, not validation.

### 10.12 Transaction costs and capacity

Transaction-friction analysis is included to expose microstructure-scale artifacts and to provide a bounded future-relevance descriptor. It does not turn Stage 4 into strategy research.

For return-like phenomena only, governance may define one or more standardised, non-optimised measurement mappings and compare the gross conditional effect with conservative stress ranges for:

- quoted or estimated spread;
- fees and taxes;
- observation-to-action delay and slippage;
- impact as a function of liquidity and participation;
- borrow availability and cost when a symmetric measurement implies short exposure;
- stressed-market widening; and
- turnover implied by the phenomenon’s natural decay.

These mappings are scientific sensitivity devices, not proposed strategies. Results must state their assumed observation time, action timing, turnover interpretation, and data fidelity. For volatility, breadth, correlation, volume, and other outcomes not commensurate with trading costs, the correct status is normally **not applicable**.

Stage 4 may also report:

- point-in-time liquidity and trading-value distributions;
- opportunity breadth and issuer/sector concentration;
- effect concentration in low-liquidity observations;
- sensitivity to standardised ADV fractions as an exposure descriptor; and
- whether available MDM granularity is adequate, limited, or not assessable.

Formal capacity cannot be attributed to a phenomenon in isolation. It depends on capital, selection, portfolio construction, netting, rebalance timing, holding overlap, constraints, participation, and execution—elements intentionally absent from Stages 0–5. Formal capacity assessment is therefore deferred to a separately authorised Stage 6.

Transaction-cost and capacity descriptors concern possible downstream implementation relevance. They are unrelated to Research Cost, which records the computational and statistical workload required to conduct research.

The separate Implementation Relevance Profile uses **not applicable**, **not assessable**, **artifact-exposed**, **friction-sensitive under a standardised mapping**, or **descriptively liquid and broad**. It does not call a phenomenon “capacity-limited” and cannot change scientific validity. A phenomenon is not erased because frictions appear larger than a return-like effect, but such an effect must not be described as economically consequential without an authorised implementation design.

### 10.13 Scientific Robustness Profile

The platform shall publish an ordinal component profile. It shall not collapse unlike and partly overlapping scientific dimensions into a weighted 0–100 score.

| Dimension | Core question |
|---|---|
| Point-in-time data integrity | Can the declared historical information set and survivor population be trusted? |
| Preregistration, selection, and multiplicity | Was the decision fixed, the search disclosed, and each decision family controlled? |
| Effect magnitude and precision | Does the untouched estimate support a scientifically relevant effect or precise null? |
| Walk-forward and temporal evidence | Does the fixed claim repeat through genuinely unseen time with bounded heterogeneity? |
| Cross-sectional transportability | Is breadth or mechanism-predicted conditionality supported without same-date pseudo-replication? |
| Regime evidence | Are registered regime claims supported and descriptive state differences honestly bounded? |
| Specification and falsification resilience | Does the primary claim survive registered artifact challenges and safety sentinels? |
| Reproduction and direct replication | Can it be independently reimplemented and repeated on genuinely new outcomes? |

Each applicable dimension receives the Section 18.5 ordinal rating from 0 to 4, its supporting evidence, uncertainty, and reviewer disagreement. **Not applicable** and **not assessable** are explicit states with reasons; they are never converted silently to zero or omitted.

Critical gates remain pass/fail and non-compensatory. The profile cannot approve, rank, or optimise phenomena. Its role is to expose strengths and weaknesses consistently.

Mechanism evidence is reported in a separate **Explanatory Credibility Profile**. A repeatedly supported but unexplained association is not made less empirically valid, and a persuasive story cannot strengthen its statistical existence.

Friction and liquidity descriptors form a separate **Implementation Relevance Profile** and do not change the scientific ratings.

### 10.13.1 Explanatory Credibility Profile

Explanation is assessed separately through:

- whether the mechanism preceded confirmatory outcome access;
- temporal ordering of the proposed cause, proxy, and response;
- construct validity of each proxy;
- explicit rival mechanisms and confounders;
- discriminating cross-sectional, temporal, event-time, decay, or regime predictions;
- negative controls and placebo predictions;
- consistency across conceptual measurements;
- sensitivity to common-exposure adjustment; and
- causal-identification status and untestable assumptions.

The profile may conclude mechanism-consistent, rival mechanisms unresolved, artifact explanation favoured, or causally identified under stated assumptions. None of these labels changes whether the registered association itself was statistically supported.

### 10.14 Reproduction and replication

The architecture distinguishes:

- **computational reproduction:** the same result is recovered from the same MDM snapshot and frozen specification;
- **independent reimplementation:** a separate researcher reconstructs the analysis from the preregistration without the original analytical output;
- **direct replication:** the same registered estimand is tested on genuinely new outcome evidence, preferably an untouched later period;
- **transportability test:** another population, segment, exchange, or same-date cross-section is examined, with shared market-date dependence explicit; and
- **conceptual replication:** a different preregistered measurement tests construct or mechanism validity.

Same-date cross-sectional evidence is normally transportability, not independent replication of persistence, because market, sector, macroeconomic, and pipeline shocks are shared. It can count as direct replication only if the preregistration demonstrates that the independent sampling unit and failure modes are genuinely distinct.

MDM remains the sole authorised data source. Independent reimplementation can expose analytical defects but cannot eliminate a systematic MDM measurement error. That residual single-source risk must be stated, challenged with MDM lineage audits and sentinels, and reflected in the data-integrity rating.

Reproduction and replication each resolve their exact Stage 2.5 feature eligibility and dependency snapshot independently. A previous feature-validation pass does not excuse a nonconforming new panel, a changed MDM vintage, or a consumed revalidation trigger.

Direct replication success uses a preregistered prediction interval, equivalence/compatibility region, or hierarchical/meta-analytic heterogeneity rule. Confidence-interval overlap and a second p-value below a threshold are not valid generic criteria. A non-significant replication is inconclusive unless it precisely excludes the registered effect.

Full validation normally requires computational reproduction, independent reimplementation, and direct replication on untouched temporal evidence. A scientifically justified alternative independent unit may be accepted only through preregistration and adjudication. Transportability and conceptual replication strengthen domain or mechanism understanding but do not replace direct replication.

### 10.15 Adjudication states

Every Stage 4 dossier records:

- one run finding: supported, precise null, contradicted, inconclusive with reason, or invalid;
- one hypothesis decision: confirmed on locked evidence, confirmed conditional, not confirmed, contradicted, or unresolved; and
- a maturity recommendation: candidate, provisionally confirmed awaiting direct replication, or eligible for Stage 5 synthesis.

Superseded and retracted are workflow/history states, not substitutes for an evidential result. Only Stage 5 synthesis can assign validated maturity to a phenomenon.

The dossier includes the frozen protocol, data-lineage certificate, integrity audit, complete primary and secondary output, adjusted and unadjusted tests, fold matrix, segment and regime matrix, falsification results, effect-size and power report, implementation-relevance profile, replication report, deviations, limitations, review decisions, and signatures.

Negative and invalid outcomes enter the same permanent knowledge process as positive findings.

---

## 11. Stage 5 — Scientific Knowledge Base

### 11.1 Purpose

The Knowledge Base is the platform’s permanent scientific memory, not a showcase of successful effects. It preserves the path from question to evidence to governed conclusion, including null, contradictory, invalid, incomplete, abandoned, retracted, and superseded work.

It must distinguish:

- **phenomenon:** the recurring conditional behaviour being claimed;
- **hypothesis:** one falsifiable proposition about that behaviour;
- **experiment:** one registered procedure;
- **run:** one immutable execution against identified inputs;
- **finding:** the result of a run;
- **reproduction:** reconstruction of a result from the same specification;
- **independent reimplementation:** separate reconstruction of the registered analysis;
- **direct replication:** the same estimand tested on genuinely new eligible outcomes;
- **transportability test:** the claim examined in another population or segment;
- **explanation:** a mechanism hypothesis with discriminating predictions;
- **review:** a methods, data, domain, or replication assessment; and
- **knowledge decision:** the governed synthesis of all relevant evidence.

The Knowledge Base also treats a **feature-validation dossier**, **continuous evidence-profile snapshot**, **dependency decision**, and **phenomenon-interaction relationship** as distinct versioned scientific objects. These objects may be linked to a phenomenon without being collapsed into the phenomenon's maturity status.

This separation prevents one significant experiment from being promoted directly into “knowledge.”

### 11.2 Append-only evidence graph

The minimum relationship is:

**Catalogue question → phenomenon claim → hypotheses → preregistrations → data and feature manifests → runs → findings → reproductions and replications → reviews → knowledge decisions**

Mechanism hypotheses, amendments, deviations, retractions, contradictions, and supersessions attach to the relevant object without erasing it.

This provenance graph records how evidence was produced. It links to, but remains distinct from, the Research Dependency Graph that controls readiness and the Phenomena Interaction Graph that records scientific relationships among phenomena. A provenance path does not itself prove that a prerequisite is satisfied or that two phenomena interact.

Every object has:

- a permanent ID;
- immutable content version;
- creation time and author;
- parent and descendant links;
- status history;
- access and amendment history;
- supporting fingerprints; and
- reasoned reviewer decisions.

MDM corrections, changed features, revised universes, or corrected methods create new linked objects. Completed results never change in place.

Permanence additionally requires:

- role-based write and status-transition authority;
- tamper-evident linking and trusted timestamps;
- periodic verification of object and relationship integrity;
- tested backup, restore, and disaster-recovery procedures;
- approved retention consistent with MDM licensing;
- migration procedures that preserve permanent IDs, versions, fingerprints, and audit history; and
- reviewer-visible records of failed writes, verification failures, and restorations.

Fingerprints without retrievable source bytes or an immutable MDM version are insufficient for exact replay.

### 11.3 Minimum run record

Every run record shall retain:

- registration and protocol fingerprint;
- MDM snapshot, schema, and authorised extract identity;
- security, universe, calendar, classification, and corporate-action manifests;
- feature and outcome versions;
- applicable Stage 2.5 validation dossiers and exact feature-view conformance record;
- frozen Research Dependency Graph decision, discovery-budget charge, Research Cost estimate, and ESIG assessment;
- future analysis-environment identity and deterministic seeds;
- start, finish, executor, execution provenance, and append-only actual Research Cost;
- all registered outcomes, horizons, segments, models, and diagnostics;
- row counts, coverage, exclusions, and effective sample estimates;
- all failed checks and deviations;
- estimates, intervals, distributions, and aggregate result tables;
- multiplicity family and corrections;
- reviewer identities, decisions, reasons, and times; and
- links to reproduction, replication, supersession, or invalidation.

### 11.4 Workflow and evidence are separate axes

Workflow states may be:

- proposed;
- registered;
- in progress;
- completed;
- computationally reproduced;
- independently reimplemented;
- directly replicated;
- transportability-tested;
- reviewed;
- superseded;
- retracted; or
- not completed, with reason.

The Knowledge Base stores all three canonical evidence levels in Section 3.8: run finding, hypothesis decision, and phenomenon maturity. Underpowered is a reason attached to an inconclusive run. Not replicated is an outcome label accompanied by the replication run’s canonical finding. Validated and validated conditional are phenomenon-maturity decisions made only through Stage 5 synthesis.

A completed experiment can be inconclusive. An incomplete experiment can still contain outcome exposure that consumes a holdout. Workflow and evidence must therefore never be represented by one status field.

Phenomenon maturity and continuous evidence evolution are also separate axes. A phenomenon may retain the same maturity state while confidence strengthens, weakens, becomes more conditional, or faces unresolved contradiction. Conversely, a maturity transition is a governed decision supported by an evidence-profile snapshot, not an automatic result of accumulating a specified number of studies.

### 11.5 Mandatory negative-results registry

Every registered experiment terminates in either:

1. a complete result deposit; or
2. a permanent not-completed record containing the reason, stopping point, data viewed, and outputs known before stopping.

Negative records receive the same identifiers, metadata, indexing, retention, and review as positive findings. Invalid runs are retained for audit but excluded from evidential synthesis.

Before registering a new hypothesis, researchers must search linked null and negative records. Re-testing requires an explicit justification, such as:

- genuinely new out-of-sample MDM observations;
- correction of a documented design or data defect;
- a new population or regime with an a priori rationale;
- a mechanistically distinct refinement; or
- a materially improved measurement.

The new hypothesis links to the previous negative evidence. Repeated invisible testing until a favourable result appears is thereby prevented.

### 11.6 Phenomenon evidence card

Every candidate or validated phenomenon receives a strategy-neutral evidence card containing:

- precise conditional-behaviour statement;
- current evidence level and decision history;
- current continuous evidence-profile snapshot, trajectory, and previous-snapshot link;
- population, geography, exchanges, security types, exclusions, and dates;
- unit of observation and point-in-time information boundary;
- conditioning variable, comparator, peer group, and reference population;
- outcome definition and horizons;
- estimated direction, magnitude, response shape, uncertainty, prevalence, and decay;
- null and minimum relevant effect;
- all supported, precise-null, contradicted, inconclusive, invalid, and incomplete experiments;
- computational-reproduction, independent-reimplementation, direct-replication, transportability, and conceptual-replication status;
- temporal, market-cap, sector, industry, regime, liquidity, and lifecycle stability;
- sensitivity to universes, features, policies, and MDM vintages;
- dependence on market, sector, size, liquidity, and other common exposures;
- Implementation Relevance Profile where relevant and not-applicable/not-assessable where necessary;
- separate Explanatory Credibility Profile;
- proposed mechanisms, rivals, and falsification status;
- incoming and outgoing Phenomena Interaction Graph relationships, their maturity, and their evidence profiles;
- known failure boundaries;
- invalidation and revalidation triggers; and
- next review date.

The card does not contain buy/sell instructions, thresholds selected for performance, portfolio weights, or execution parameters.

### 11.6.1 Continuous evidence profile

Every phenomenon, including a precise-null or contradicted phenomenon claim, possesses an append-only continuous evidence profile. The profile is a sequence of immutable snapshots that describes the current balance, quality, independence, scope, and trajectory of evidence. It is not required to be a single numerical probability, and no implementation method is prescribed at Stage 0.

Each snapshot contains at least:

| Profile component | Required content |
|---|---|
| Identity and time | Phenomenon ID and version, snapshot ID, effective time, previous snapshot, custodian, and reviewers |
| Claim scope | Population, period, measurement, exposure, comparator, outcome, horizon, estimand, and declared domain |
| Evidence inventory | Every eligible supporting, precise-null, contradictory, inconclusive, invalid, incomplete, superseded, reproduction, replication, and transportability record |
| Comparability | Which studies address the same claim and which differ in estimand, population, horizon, data vintage, measurement, or design |
| Magnitude and precision | Effect distributions, uncertainty, materiality, response shape, prevalence, decay, and their evolution |
| Independence | Shared samples, analysts, implementations, MDM lineages, feature definitions, market periods, and other dependence among contributions |
| Competing evidence | Evidence for rival explanations, null accounts, measurement artifacts, boundary conditions, and conflicting claims |
| Stability and scope | Temporal, market-cap, sector, industry, liquidity, lifecycle, regime, and measurement heterogeneity |
| Explanation | Mechanism predictions, discriminating tests, causal-status limits, and Explanatory Credibility Profile |
| Confidence evolution | Reasoned direction and degree of strengthening, weakening, replication, contradiction, narrowing, broadening, or unresolved change since the prior snapshot |
| Decision | Current maturity, limitations, disagreement, revalidation needs, and reasoned adjudication |

An incoming contribution is classified by what it changes, not by whether its headline result is statistically significant. Contribution types include:

- **strengthening:** improves precision, consistency, scope, or challenge survival;
- **weakening:** reduces estimated magnitude, precision, stability, or explanatory credibility without necessarily contradicting the claim;
- **replicating:** tests the registered claim with its dimensions of independence made explicit;
- **contradictory:** valid evidence opposes or excludes a material part of the claim;
- **competing:** supports a rival explanation or alternative phenomenon;
- **scope-refining:** narrows, broadens, or relocates a boundary of validity;
- **superseding:** establishes why a prior measurement, interpretation, or synthesis is no longer the active basis for decision; and
- **non-informative:** adds little because it is invalid, too imprecise, duplicative, or unable to discriminate among live accounts.

Profile updates are required after a new eligible run, confirmation, reproduction, replication, transportability test, contradiction, evidence review, material MDM correction, feature supersession or revalidation, dependency invalidation, interaction finding, or scheduled knowledge review. Each update preserves the earlier snapshot, shows the evidence added or reclassified, and records reviewer disagreement.

Evidence is not accumulated by counting studies or summing significance. Quality, relevance, independence, selection history, effect magnitude, uncertainty, and comparability govern its contribution. Replicated evidence receives no automatic weight unless its independence is established. Superseded and adverse evidence remains visible and may continue to inform measurement risk or historical interpretation. The profile may remain genuinely mixed; the architecture prohibits forcing continuous confidence evolution into binary true/false thinking.

### 11.7 Evidence ladder

| Level | Meaning |
|---|---|
| L0 — Idea | Measurable catalogue question; no empirical evidence |
| L1 — Registered | Falsifiable protocol locked |
| L2 — Observed | Valid executed finding on discovery evidence |
| L3 — Confirmed | Passed a locked confirmatory test |
| L4 — Directly replicated | Independently reimplemented and repeated on genuinely new eligible outcomes; independence dimensions recorded |
| L5 — Validated phenomenon | Evidence synthesis and all critical gates pass within stated bounds |
| L6 — Strategy-eligible evidence | Inactive in the present programme; assignable only after a separately authorised Stage 6 charter |

An evidence level is not a probability of truth, a claim of causality, or evidence of profitability.

The current platform may assign no status above L5. Different analyst, different implementation, new time period, new population, and independent measurement system are stored as separate replication metadata rather than collapsed into one ambiguous “independence” flag.

The ladder is a maturity vocabulary, not a substitute for the continuous evidence profile. Two phenomena at the same level may have materially different precision, independence, contradictory evidence, scope, and confidence trajectory.

### 11.8 Evidence synthesis and contradictions

Knowledge decisions consider the full evidence set, not a vote count of significant studies. Synthesis should examine:

- compatibility of estimands and populations;
- study independence and shared data exposure;
- effect magnitude and uncertainty;
- heterogeneity by time, segment, and regime;
- multiplicity and selection history;
- data and method quality;
- prospective versus retrospective evidence;
- mechanism-specific predictions; and
- publication and abandonment patterns within the platform.

Contradictory evidence is attached, displayed, and adjudicated. Possible conclusions include narrower domain, structural change, measurement dependence, non-replication, or unresolved inconsistency. A contradiction never disappears because a later synthesis chooses one interpretation.

### 11.8.1 Phenomena Interaction Graph

The Phenomena Interaction Graph is a first-class, version-controlled scientific artifact that maps evidence-backed relationships among equity-market phenomena. It prevents the Knowledge Base from becoming a set of isolated cards and supports an evolving scientific account of how behaviours coexist, overlap, condition, explain, or oppose one another.

Nodes resolve to exact phenomenon versions and may also link to scoped hypotheses, mechanism hypotheses, precise-null claims, and governed evidence profiles. Required relationship types are:

| Relationship | Scientific meaning |
|---|---|
| Reinforcement | The presence or strength of one phenomenon is associated with greater magnitude, prevalence, persistence, or confidence in another under declared conditions |
| Redundancy | Two phenomena substantially encode the same measured behaviour or explanatory content within a declared domain |
| Hierarchy | One phenomenon is a broader, narrower, constituent, or emergent form of another |
| Causal hypothesis | A proposed directed mechanism links phenomena; the edge remains explicitly hypothetical unless a causal design justifies stronger language |
| Conditional dependence | The relationship or distribution of one phenomenon differs conditional on the state of another |
| Interaction | Their joint occurrence differs materially from the preregistered additive, independent, or other baseline relationship |
| Conflict | Their claims, mechanisms, scopes, or empirical predictions cannot all be reconciled within the stated domain |

Every edge records:

- permanent edge ID, version, direction or symmetry, relationship type, and exact node versions;
- a strategy-neutral relationship statement and proposed mechanism;
- population, dates, market state, sector or industry scope, horizon, cutoff, comparator, estimand, and minimum relevant relationship;
- MDM, feature, Stage 2.5, exposure, and outcome lineage;
- linked preregistrations, runs, reviews, reproductions, replications, contradictions, and falsifiers;
- shared-sample, shared-feature, analyst, implementation, and other independence information;
- effect magnitude, uncertainty, heterogeneity, known boundaries, competing relationships, and unresolved conflict;
- causal-status label and rival accounts;
- workflow state, relationship maturity, continuous evidence profile, revalidation triggers, reviewers, and full status history; and
- links to superseded or invalidated edge versions.

Empirical interaction edges enter through the same discovery, multiplicity, confirmation, independent-reimplementation, replication, and synthesis disciplines as phenomenon claims. An edge may be proposed, candidate, provisionally confirmed, validated within scope, contradicted, superseded, or retracted. Its continuously evolving evidence profile is separate from the profiles of its endpoint phenomena; validation of both nodes does not validate their relationship.

The graph is not inferred from adjacency in reports, feature correlation, shared market dates, or post-hoc narrative. Redundancy does not delete either phenomenon. Conflict is preserved rather than averaged away. Cycles may describe reciprocal or unresolved scientific relations but cannot be used as evidence of causality. Proposed edges and causal hypotheses must remain visibly distinct from supported relationships.

This graph differs from the Research Dependency Graph: dependencies determine whether work may begin, while interaction edges state what the evidence suggests about relationships after eligible work has been conducted. It also differs from the append-only provenance graph, which records how artifacts and evidence were produced. The Phenomena Interaction Graph is scientific knowledge, not a strategy-combination map, and may not contain portfolio, entry, exit, sizing, or execution logic.

### 11.9 Knowledge decay and revalidation

Validation is time-bounded. Each evidence card records:

- last eligible observation;
- scheduled review or revalidation date;
- required future sample;
- structural-break, coverage, or data-quality triggers;
- expected evidence maturity;
- current, decaying, dormant, superseded, contradicted, or retracted state; and
- reason for every change.

New evidence updates the graph. It does not rewrite the conclusion that was scientifically justified at an earlier date.

Revalidation also reviews affected continuous evidence profiles and Phenomena Interaction Graph edges. A changed endpoint claim, revoked feature, invalidated dependency, new contradiction, or structural break may weaken, narrow, suspend, supersede, or require re-testing of related edges without deleting their prior states.

### 11.10 Findability and reuse

The Knowledge Base must support search by construct, exposure, outcome, horizon, population, data field, feature family, Stage 2.5 validation state, dependency, sector, market-cap group, regime, mechanism, evidence state, confidence trajectory, interaction type, relationship maturity, and failure reason.

Before new work, the system should surface:

- related positive and negative hypotheses;
- consumed holdouts;
- known data defects;
- near-duplicate features and tests;
- competing explanations already examined;
- unresolved replications;
- blocking or invalidated research dependencies; and
- reinforcing, redundant, hierarchical, conditional, interacting, causal-hypothesis, and conflicting phenomenon relationships.

Findability turns negative evidence into an active research asset rather than an archival obligation.

---

## 12. Stage 6 — Future Strategy Assembly Boundary

### 12.1 Status

Stage 6 is an interface specification for a possible future programme. It is not authorised by this document. No strategy construction, parameter optimisation, portfolio logic, broker interface, or live-trading component belongs in the present project.

### 12.2 Scientific firewall

The following distinctions are permanent:

- a validated phenomenon is an empirical regularity, not a trading signal;
- a profitable strategy would not prove its proposed phenomenon;
- a failed strategy would not invalidate a scientifically sound phenomenon;
- statistical significance does not establish implementation feasibility;
- explanatory plausibility does not establish causality; and
- strategy-stage optimisation may not revise historical scientific evidence.

Stage 6 would require an explicitly governed separation, a new charter, fresh testing budgets, and untouched evidence. A different repository or filesystem location is not authorised by this document and would require an explicit new user authorisation. Until then, every artifact remains confined to D:\codex\equity_quant_research_platform.

### 12.3 Strategy-eligibility gate

A future authorised Stage 6 programme could assign evidence level L6 only if the phenomenon has:

- passed locked confirmation;
- been computationally reproduced, independently reimplemented, and directly replicated on genuinely new outcomes;
- passed point-in-time identity, universe, survivorship, corporate-action, and data-vintage audits;
- demonstrated a scientifically relevant effect, not merely a low p-value;
- passed its registered multiple-testing policy;
- shown reasonable stability or clearly bounded conditionality;
- documented common market, sector, size, liquidity, lifecycle, and microstructure explanations;
- documented decay, standardised friction and liquidity descriptors where applicable, and all not-assessable implementation questions;
- a complete positive, negative, contradictory, and invalid evidence record; and
- no unresolved critical data or protocol defect.

Eligibility means only that a future programme may consider the evidence. It is not a recommendation to trade.

### 12.4 Strategy-neutral evidence contract

Stage 5 may expose an immutable evidence contract containing:

- phenomenon ID and version;
- eligible population and point-in-time conditions;
- conditional outcome distribution and uncertainty;
- supported horizons and failure boundaries;
- dependencies and redundancies with other phenomena;
- empirical decay;
- standardised friction, liquidity, breadth, and concentration descriptors without a trading recommendation, with formal capacity deferred;
- data limitations and invalidation triggers; and
- complete provenance back to MDM and preregistered experiments.

A future consumer references this contract and may not edit it.

### 12.5 Conditions for any future assembly programme

If separately authorised, future strategy research should require:

- a new thesis and preregistration;
- an explicit set of eligible phenomenon versions;
- a combination rationale based on complementary mechanisms, not merely low in-sample correlation;
- dependency analysis to prevent double-counting the same underlying exposure;
- a new global search and multiple-testing budget;
- nested design, validation, and final locked partitions;
- realistic turnover, spread, impact, borrow, and capacity assumptions;
- an independent final review; and
- a rule that newly observed market behaviours return to the phenomena pipeline as new hypotheses.

Deployment, broker connectivity, and live trading would require a further and separately authorised programme. They are not implied by Stage 6.

---

## 13. Cross-cutting scientific governance

### 13.1 Scientific constitution

Before empirical work, the project shall ratify a short constitution containing at least:

1. phenomena precede strategies;
2. MDM is the sole market-data authority;
3. point-in-time validity is a hard gate;
4. exploration and confirmation are different evidence classes;
5. all tests and data exposures enter a permanent ledger;
6. preregistrations and completed records are append-only;
7. negative, null, contradictory, incomplete, and invalid work is retained;
8. multiplicity is controlled across experiment ancestry, not only within one report;
9. causal language requires causal identification;
10. no optimisation occurs before validated discovery;
11. no strategy or trading implementation is authorised by Stages 0–5;
12. unvalidated features and unsatisfied scientific dependencies cannot enter discovery;
13. exploratory freedom is bounded before outcome exposure;
14. Research Cost and ESIG affect planning, never evidential conclusions; and
15. confidence evolves through retained supporting, weakening, replicated, competing, and contradictory evidence rather than binary truth labels.

### 13.2 Roles and decision rights

| Role | Responsibility | Independence expectation |
|---|---|---|
| Phenomenon owner | Defines construct, rationale, hypothesis, and falsifier | Cannot alone approve promotion |
| MDM/data steward | Certifies source vintage, identity, timing, universe, and quality | Independent of desired result |
| Feature-validation reviewer | Challenges measurement correctness, leakage, numerical behaviour, missingness, revisions, determinism, versions, and lineage | Cannot approve a feature from predictive attractiveness |
| Experiment executor | Executes frozen specification and deposits complete output | Cannot change protocol after exposure |
| Methods reviewer | Reviews estimand, dependence, power, multiplicity, and interpretation | Preferably not the hypothesis author |
| Domain/mechanism reviewer | Challenges explanation and proposes discriminating tests | Must consider rival accounts |
| Replication lead | Independently reimplements and conducts direct replication without original analytical output where possible | Distinct preparation, controlled access, and genuinely new outcomes |
| Research-planning steward | Reviews dependencies, discovery-budget use, Research Cost, ESIG, feasibility, and scheduling record | Cannot use expected outcomes or planning priority as evidence |
| Knowledge and graph custodian | Maintains statuses, continuous evidence profiles, graph links, negative records, contradictions, and revalidation | Cannot delete adverse evidence or assert unsupported relationships |
| Adjudication panel | Grants validated or context-bound status | No single-person admission |

Where staffing prevents full separation, the overlap is recorded as a limitation and the evidence level is capped until independent review occurs.

### 13.3 Experiment lifecycle

The governed lifecycle is:

**propose → dependency review → feature-eligibility review → discovery-budget reservation → Research Cost and ESIG review → feasibility decision → preregister → freeze → execute → deposit all results and actual cost → computationally reproduce → provisionally adjudicate → independently reimplement → directly replicate → update continuous evidence and interaction profiles → synthesize → assign governed phenomenon maturity → revalidate**

An experiment cannot disappear between stages. A stopped experiment records why it stopped and what outcomes were seen.

### 13.4 Amendment policy

- Pre-exposure clerical amendments preserve the original and may remain within the same experiment if reviewers agree the estimand is unchanged.
- Pre-exposure scientific changes create a new version.
- Post-exposure changes create exploratory descendants and consume the exposed data.
- Protocol deviations are reported even when believed immaterial.
- A data correction creates a new run against a new MDM vintage.
- Retraction and supersession add status; neither deletes the original record.

### 13.5 Holdout stewardship

The holdout ledger records dataset, period, population, access time, accessor, purpose, outputs revealed, and whether independence remains. Automated processes count as accessors.

The replication reserve should be managed by a custodian not involved in discovery where practical. Outcome summaries, even without row-level data, can consume independence if they influence feature or hypothesis choices.

### 13.6 Research budgets

Before a catalogue family begins, governance should set:

- canonical feature and horizon variants;
- primary and secondary outcomes;
- maximum exploratory test family;
- discovery-campaign, sealed-sample, and programme-sequential error-control policies;
- number and purpose of confirmation opportunities;
- minimum precision and relevant-effect rules; and
- conditions under which future data may be reserved.

The budget cannot be enlarged merely because the initial evidence is disappointing. Expansion requires a scientific rationale, a new registered family, and honest multiplicity ancestry.

This existing statistical and evidence budget governs error rates, confirmation opportunities, precision, and unexposed data. It is related to, but not interchangeable with, the discovery budget, Research Cost, or ESIG defined below.

### 13.6.1 Discovery budgets

A discovery budget is a prospective limit on the exploratory degrees of freedom available to a catalogue family or discovery campaign. Its purpose is to control research drift, undisclosed researcher freedom, and the growth of false discoveries. It is not a CPU allowance, financial budget, significance threshold, or permission to omit tests from multiplicity accounting.

Before exploratory work begins, a versioned budget defines limits, as applicable, for:

- number of hypothesis families and child hypotheses;
- individual features, transformations, and joint feature combinations;
- parameter values, grid cells, thresholds, bins, windows, and functional forms;
- regime definitions, regime partitions, segments, and interaction families;
- forecast outcomes and horizons;
- comparators, null models, mechanism alternatives, and descendants; and
- automated searches, unsupervised branches, model-assisted triage, and analyst follow-up generated from them.

Budgets may be hierarchical. A programme allocation may contain catalogue-family, campaign, analyst, automated-search, and experiment allocations, provided every unit has one traceable ancestry and cannot be charged selectively after results are known. The budget record contains its scientific rationale, unit definitions, authorised limits, owner, reviewers, approval time, eligible period, parent allocation, reservation history, consumption history, remaining balance, and supersession links.

Exploratory capacity is reserved before outcome access. It is consumed when an analysis, diagnostic, failed run, abandoned branch, automated screen, parameter cell, or summary reveals outcome-bearing information that could influence later choices. A computational failure before any outcome-bearing feedback may release a reservation only through a recorded review. Renaming, regrouping, splitting, or creating a descendant does not restore consumed capacity.

Once a limit is consumed, further exploratory work in that scope is blocked until one of three governed actions occurs:

1. **Validation:** move an already specified claim into its registered confirmation or replication path without adding exploratory freedom;
2. **Evidence review:** synthesize the work performed, close redundant branches, assess whether uncertainty has been reduced, and decide whether a narrower scientifically justified question remains; or
3. **Formal approval for additional exploration:** create a prospective budget version with a scientific rationale, explicit added units, complete prior exposure and multiplicity ancestry, remaining unexposed evidence, reviewers, and approval before further outcome access.

Additional exploration cannot be authorised merely because prior results were disappointing, favourable, close to a threshold, or computationally cheap. Its rationale must be independent of desired outcome direction and must state why the additional degrees of freedom are expected to resolve a material uncertainty not adequately addressed by validation or evidence synthesis.

Discovery-budget consumption remains visible alongside the complete search ledger and applicable statistical error-control family. Budget compliance does not imply evidential validity, and a multiplicity adjustment does not retrospectively authorise an over-budget search.

### 13.6.2 Research Cost accounting

Every proposed experiment, feature-validation study, reproduction, replication, interaction study, and material revalidation receives a formal Research Cost record before scheduling. The estimate is permanent planning metadata tied to the exact protocol version. It may be refined prospectively through a new version, but it is never overwritten after execution or after the original assumptions cease to be valid.

The pre-execution estimate contains:

| Cost dimension | Minimum estimate |
|---|---|
| Expected CPU cost | Core-hours or equivalent compute range, execution shape, parallelism assumption, and material accelerator use if any |
| Expected memory | Peak and sustained memory range, aggregation pressure, and material per-worker or total distinction |
| Expected storage | Temporary, intermediate, retained-input, retained-output, log, and Knowledge Base storage, with retention assumptions |
| Expected runtime | Wall-clock range under a named resource profile, expected queue or coordination constraints, and timeout risk |
| Expected data volume | MDM rows and bytes read, feature-panel rows and bytes, intermediate volume, output volume, periods, securities, and partitions |
| Expected statistical complexity | Numbers of estimators, tests, fitted models, folds, rolling windows, resamples, simulations, permutations, segments, regimes, horizons, interactions, and network relationships, with the dominant complexity driver |

Each value uses declared units or a bounded range and records the estimation method, hardware or resource-profile assumption, software/environment identity where relevant, confidence or uncertainty in the estimate, protocol and data-snapshot assumptions, estimator, reviewer, and estimate version. Unknown is an explicit state requiring feasibility review; it is not silently represented as zero.

The scheduler evaluates Research Cost before execution to determine feasibility, resource fit, sequencing, concurrency, storage and retention availability, and whether a scientifically equivalent lower-cost design should be prospectively considered. A redesign caused by infeasibility creates a new protocol and cost version and must preserve the original proposal and reason for change.

At termination, an append-only actual-cost record captures CPU consumption, peak memory, temporary and retained storage, wall time, queue and retry time where material, MDM and intermediate data volumes, executed statistical workload, failures, and stopped work. Material differences from the estimate receive an explanation. Failed, invalid, and abandoned work retains both estimated and actual cost so that future estimates learn from the full record rather than successful runs alone.

Research Cost is scientifically neutral. High cost does not make an experiment valuable, valid, or important; low cost does not make it admissible. It is distinct from discovery-budget consumption, statistical error budgets, transaction-cost stress in Stage 4, and any future economic implementation assessment.

### 13.6.3 Expected Scientific Information Gain

Expected Scientific Information Gain (ESIG) is a frozen, pre-outcome assessment of how much a proposed experiment could reduce a material scientific uncertainty. It supports the objective of maximising scientific learning per unit of computational effort without predicting whether the experiment will produce a positive, significant, large, profitable, or preferred result.

An ESIG assessment asks how the possible result classes could change knowledge. Relevant dimensions include:

- resolution of a clearly named uncertainty or disagreement;
- ability to discriminate among mechanisms, rival explanations, measurement artifacts, and null accounts;
- falsification strength and the value of precise null, contradictory, or boundary-refining evidence;
- expected precision relative to the minimum relevant effect and ability to distinguish support, equivalence, contradiction, and inconclusion;
- independence from existing samples, analysts, implementations, features, and market periods;
- improvement in scope, transportability, temporal stability, or regime boundaries;
- unlocking or invalidating downstream nodes in the Research Dependency Graph;
- learning that applies to several phenomena, measurements, or interaction edges; and
- redundancy with evidence already held.

The permanent pre-execution ESIG record contains:

- the target uncertainty and why resolving it matters scientifically;
- the live competing accounts or decisions;
- plausible registered result classes and the knowledge each would add, including null, contradiction, inconclusion, or data-defect discovery;
- expected precision and evidence-independence assumptions;
- affected phenomenon profiles, interaction edges, and dependency nodes;
- potential scope, mechanism, falsification, and revalidation consequences;
- expected redundancy and complementarity with existing evidence;
- an ordinal band or bounded range, confidence in the assessment, material disagreements, owner, reviewers, and frozen time; and
- the exact Research Dependency Graph, evidence-profile, and protocol versions used to judge it.

ESIG is frozen before relevant outcomes are inspected. A scientifically material pre-exposure change creates a new assessment version. After exposure, actual learning is documented separately in the evidence profile; the original expectation remains visible and is not rewritten to appear prescient.

ESIG, Research Cost, scientific validity, and result direction remain separate axes. Scheduling may consider the expected information return relative to declared resource constraints through transparent priority classes, Pareto comparisons, or another approved rule. It must not hide the decision inside an unexplained scalar, and ESIG must never alter a p-value, interval, robustness rating, maturity state, or evidential interpretation.

### 13.6.4 Scheduler-facing research-planning contract

The scheduler is a scientific gatekeeper as well as a resource coordinator. It may release only an eligible, version-resolved unit of work whose planning record contains:

1. catalogue, hypothesis, and protocol IDs;
2. a frozen Research Dependency Graph snapshot with every mandatory prerequisite satisfied for scope;
3. exact feature versions, current Stage 2.5 dossiers, and feature-view conformance requirements;
4. authorised MDM, population, timing, holdout, and evidence-reservation decisions;
5. applicable discovery-budget reservation and remaining balance;
6. complete statistical family and exposure-ledger assignment;
7. reviewed Research Cost estimate and resource-feasibility decision;
8. frozen ESIG assessment;
9. scientific priority, scheduling decision, decision rule, owner, reviewer, and time; and
10. every override, deferral, cancellation, and supersession with reason.

Eligible work should be prioritised by its expected ability to reduce important uncertainty under available computational and evidence constraints rather than simple first-in, first-out order. The governed rule should preserve capacity for feature validation, direct replication, revalidation, data-integrity investigations, null-focused work, contradiction resolution, and foundational dependency work, even when these are less novel than new discovery proposals.

Neither low Research Cost nor high ESIG can bypass data admissibility, feature validation, dependency, discovery-budget, statistical, holdout, preregistration, or independence gates. Cost or queue pressure cannot justify a scientifically weaker unregistered design. An urgent override remains possible only under named authority, with prospective rationale and permanent audit history; it changes schedule, not evidence.

The four planning controls remain distinct:

| Control | What it limits or estimates | What it must not become |
|---|---|---|
| Discovery budget | Prospective exploratory degrees of freedom | A compute allowance or multiplicity correction |
| Statistical and evidence budget | Error allocation, confirmation opportunities, precision, and unexposed data | Permission for unlimited search |
| Research Cost | Expected and actual computational, storage, runtime, data, and statistical workload | Scientific importance or validity |
| ESIG | Expected reduction of material scientific uncertainty | Expected positive result, evidence score, or post-outcome justification |

### 13.7 Reproducibility standard

“Reproducible” means an authorised reviewer can start from the referenced MDM snapshot and immutable scientific artifacts and obtain the same eligible universe, feature panel, statistical results, diagnostics, and decision.

Required properties include:

- deterministic definitions and seeds;
- frozen calendars, classifications, and cutoffs;
- byte-stable retained MDM snapshots or guaranteed immutable and retrievable MDM versions, subject to licensing;
- content manifests for every input partition;
- machine-verifiable fingerprints and trusted timestamps in a future implementation;
- exact analysis revision, dependency/runtime lock, and random-number generator and stream;
- deterministic or explicitly tolerance-based numerical expectations;
- complete exclusions and row accounting;
- raw outputs, logs, and reviewer-visible failure records;
- no dependence on unrecorded analyst state; and
- exact linkage from claim to inputs and outputs.

If MDM cannot retain or reproduce historical vintages, exact replay and any affected point-in-time claim must be downgraded explicitly. This document does not implement those controls; it defines the standard an implementation must meet.

### 13.8 Scientific incentives

Internal review and progress measures should reward:

- precise nulls and useful negative results;
- detection of data defects;
- successful falsification;
- independent replication;
- well-bounded conditional claims;
- evidence synthesis;
- reproducibility; and
- reduction in unnecessary feature or test families.

Counting only validated positive findings would recreate publication bias inside the platform.

---

## 14. Recommended Stage 1 programme

Stage 1 should establish a bounded, testable catalogue and its governance—not launch a broad feature-mining exercise.

### 14.1 Recommendation 1 — Ratify scope and vocabulary

Approve the scientific constitution and the three-level vocabulary in Section 3. Resolve run finding, hypothesis decision, phenomenon maturity, workflow status, and the use of underpowered as an inconclusive reason. Approve the clean-room rule and MDM exclusivity in writing.

### 14.2 Recommendation 2 — Complete an MDM capability audit

Before accepting catalogue families, establish whether MDM supplies, with adequate historical availability:

- inactive and delisted securities and terminal outcomes;
- permanent security and issuer identity and ticker history;
- raw prices, distributions, splits, mergers, spin-offs, and other corporate actions;
- point-in-time shares, float, and market capitalisation;
- exchange, currency, calendar, and session history;
- historical sector, industry, index, and peer membership;
- original fundamentals, release times, revisions, and restatements;
- earnings event date and time;
- quotes, spreads, halts, and auction fields;
- holdings or participant data needed for any direct institutional claim; and
- MDM snapshot, revision, and correction history.

Produce a capability matrix with quality grade, start date, coverage, timestamp precision, known gaps, and authorised use. Unsupported catalogue families are deferred; no substitute source is used.

### 14.3 Recommendation 3 — Define the research population

Ratify:

- geography and exchanges;
- ordinary shares and treatment of REITs, ADRs, ETFs, funds, OTC instruments, preferreds, warrants, and special-purpose vehicles;
- security versus issuer unit;
- primary and secondary listings and multiple share classes;
- IPO seasoning, suspensions, relistings, bankruptcies, acquisitions, and delistings;
- currency and return convention;
- point-in-time price, history, and liquidity eligibility; and
- peer, index, sector, and industry hierarchy.

These decisions precede feature design because they determine denominators and survivorship.

### 14.4 Recommendation 4 — Approve temporal semantics

Define the official daily research cutoff, exchange timezone treatment, early closes, after-hours and pre-market event assignment, corporate-action timing, feature availability, outcome start, overlap, maturity, and conservative handling of date-only timestamps.

### 14.5 Recommendation 5 — Approve measurement and inference contracts

Before any outcome search, approve:

- the phenomenon-charter template;
- the feature-definition template;
- the Stage 2.5 feature-validation protocol, dossier, status vocabulary, conformance rules, and revalidation policy;
- a small canonical horizon dictionary;
- primary outcome conventions;
- point-in-time cross-sectional normalisation;
- dependence-aware uncertainty standards;
- minimum relevant effect and power policy;
- missingness, outlier, stale-price, and halt policy;
- multiplicity family and hierarchy rules;
- holdout and replication policy;
- robustness-profile rubric;
- Research Dependency Graph governance;
- discovery-budget definitions and exhaustion policy;
- Research Cost and ESIG planning records; and
- continuous evidence-profile and Phenomena Interaction Graph governance.

### 14.6 Recommendation 6 — Build the catalogue before the library

Seed only a bounded set of high-value catalogue questions. Do not generate hundreds of feature variants first and then ask which correlate with outcomes.

The first entries should cover orthogonal constructs and exercise the equity cross-section:

1. cross-sectional relative-strength persistence and decay;
2. short-horizon continuation versus reversal;
3. volatility-state persistence and transition;
4. gap response with exact session and corporate-action semantics;
5. abnormal volume and price-response persistence; and
6. breadth, concentration, and sector/industry dispersion.

This is a governance and measurement pilot, not a search for positive effects. Fundamentals, earnings, historical rotation, and institutional behaviour should enter only after their MDM point-in-time contract passes.

### 14.7 Recommendation 7 — Include data falsification studies

Before phenomena tests, design negative controls intended to reveal:

- future corporate-action leakage;
- current constituent or classification backfill;
- restatement leakage;
- ticker reuse and issuer duplication;
- outcome leakage into cross-sectional transforms;
- impossible future-leading features;
- stale-price and bid–ask artifacts; and
- dependence-breaking randomisation.

A platform that cannot reliably detect deliberate sentinels is not ready to discover subtle phenomena.

### 14.8 Recommendation 8 — Reserve evidence and track exposure

Allocate discovery, sealed confirmation, and replication-reserve roles before exploration. Start the access ledger before the first descriptive output is viewed. Where data history is too short for three partitions, prefer prospective accumulation to pretending a reused interval is untouched.

### 14.9 Recommendation 9 — Establish independent review

Name the data steward, feature-validation reviewer, methods reviewer, research-planning steward, knowledge and graph custodian, and replication lead. Approve conflict and role-overlap disclosures. No phenomenon should be promoted by its sole author.

### 14.10 Recommendation 10 — Define Stage 1 completion

Stage 1 is complete when:

- the scientific constitution is approved;
- every MDM field required by the pilot catalogue is certified fit for its declared point-in-time use, and unsupported families are removed or deferred;
- population and time semantics are fixed;
- catalogue, hypothesis, and evidence states are defined;
- a bounded pilot catalogue is approved;
- test families, statistical budgets, discovery budgets, and evidence reserves are assigned;
- Research Cost and ESIG planning policies are approved;
- the initial Research Dependency Graph is reviewed and versioned;
- Stage 2.5 acceptance, conformance, quarantine, and revalidation rules are approved;
- continuous evidence-profile and Phenomena Interaction Graph contracts are approved;
- negative controls and holdout policy are registered;
- review roles and decision rights are assigned; and
- all blocking risks have owners and dispositions.

No empirical phenomenon needs to be “found” for Stage 1 to succeed.

### 14.11 Recommendation 11 — Pilot the Version 1.1 governance extensions before discovery

Use a small set of measurement-only pilot cases to rehearse the complete path from a catalogue prerequisite through Research Cost and ESIG assessment, discovery-budget reservation, feature validation, scheduler admission, and Knowledge Base deposit. The pilot should deliberately include a rejected feature, an exhausted discovery budget, an unsatisfied dependency, a materially inaccurate cost estimate, competing evidence, and a proposed interaction edge. Success means that every case is blocked, retained, reviewed, or updated correctly before any genuine Stage 3 outcome search begins.

---

## 15. Scientific risk register

The risks below are open at Stage 0 unless explicitly resolved by a later approved decision. “Required response” describes a scientific control, not an implementation instruction.

| ID | Risk | Consequence | Required response |
|---|---|---|---|
| R01 | Contamination from prohibited projects or previous findings | Independence and multiplicity history become unknowable | Clean-room provenance; new identifiers, hypotheses, data manifests, and evidence only |
| R02 | MDM does not contain required point-in-time fields | Entire feature families may be invalid or impossible | Capability audit; defer unsupported families; no substitute source |
| R03 | Survivorship and missing delisting outcomes | Effects biased toward securities that survived | Reconstruct daily universe; retain inactive and delisted securities and terminal outcomes |
| R04 | Look-ahead through fundamentals, revisions, memberships, or classifications | Artificial predictive relations | Use original availability and vintage times; conservative lag; prohibit present-day backfill |
| R05 | Ticker reuse, issuer/security confusion, and multiple share classes | False histories, duplicates, and overweighted issuers | Stable MDM IDs; lifecycle mapping; issuer-aware analysis |
| R06 | Corporate-action and return-convention errors | False gaps, momentum, reversals, and volatility | Preserve raw observations; reconcile actions; use declared return views |
| R07 | Large-N illusion | Grossly understated uncertainty | Treat common dates and overlapping horizons as dependent; report effective units |
| R08 | Multiple testing across features, horizons, outcomes, and segments | High false-discovery rate | Global lineage ledger, hierarchical families, registered FWER/FDR policy, sealed confirmation |
| R09 | Holdout exhaustion | Confirmation becomes disguised exploration | Access ledger; consume exposed samples; reserve future evidence |
| R10 | Micro-cap or illiquid-stock dominance | Artifact mistaken for broad equity behaviour | Point-in-time size/liquidity analysis, influence diagnostics, microstructure challenges |
| R11 | Bid–ask bounce, stale and asynchronous prices, closing artifacts | False reversal, volatility, and lead–lag effects | Quote-aware checks where MDM permits; staleness, alternate price, and liquidity sensitivity |
| R12 | Present-day sector/index memberships projected backward | False peer, breadth, and rotation patterns | Point-in-time membership only; unknown rather than backfilled |
| R13 | Peer self-inclusion and issuer duplication | Mechanical relative or breadth relationships | Leave-one-out aggregates and issuer-aware weights |
| R14 | Missing-not-at-random data | Coverage effects mistaken for phenomena | Typed missingness, segment coverage maps, no silent imputation |
| R15 | Regimes defined with hindsight | Future information embedded in context | Lagged rules or rolling training; retrospective labels marked descriptive |
| R16 | Cross-sectional and temporal non-stationarity | Historical evidence does not persist | Walk-forward, rolling estimates, structural-break diagnostics, revalidation |
| R17 | Common exposures mistaken for stock phenomena | Market, sector, size, or liquidity beta masquerades as discovery | Report raw and conditional estimands with mechanisms fixed in advance |
| R18 | Feature redundancy | Correlated variants appear as independent confirmation | Feature-family ontology, canonical variants, dependence-aware multiplicity |
| R19 | Post-hoc economic stories | Explanation appears stronger than evidence | Register mechanisms, rivals, and discriminating tests before confirmation |
| R20 | False institutional attribution | OHLCV proxy over-interpreted as participant identity | Use proxy terminology and construct-validity tests; direct claim only with direct MDM data |
| R21 | Underpowered tests classified as null | Potential effects prematurely dismissed | Precision/power targets and equivalence bounds; inconclusive finding with underpowered reason |
| R22 | Statistical significance without materiality | Trivial effects promoted | Minimum relevant effect, intervals, prevalence, and distributional reporting |
| R23 | Daily data used for precise cost/capacity claims | False implementation certainty | Standardised friction stress only; formal capacity deferred to Stage 6; use not-assessable states |
| R24 | MDM corrections silently alter history | Completed experiments cease to be immutable | Versioned snapshots; correction impact assessments and new linked runs |
| R25 | Data cleaning discretion | Researcher choices bias results | Preregistered policies; retain flags, exclusions, and sensitivity results |
| R26 | Event-time ambiguity | Earnings or corporate effects assigned to wrong session | Timestamp-quality grades and conservative rules for date-only observations |
| R27 | Calendar, timezone, and currency inconsistency | Misaligned returns and exposures | Approved exchange calendars, session cutoffs, currency and conversion policy |
| R28 | Replication lacks real independence | Same pipeline defect or market-date shock reproduced twice | Independent reimplementation plus genuinely new outcome evidence, normally prospective time |
| R29 | Internal publication bias | Positive families receive more attention and status | Mandatory termination records; reward nulls, falsification, and replication |
| R30 | Black-box predictive performance substitutes for science | Uninterpretable, unstable claims | Use models for triage only; require interpretable estimand and standard validation |
| R31 | Observational association described as causal | Unsupported explanations | Explicit causal-status label and identification requirement |
| R32 | Data licensing or retention prevents exact replay | Reproducibility promise cannot be met | Confirm MDM retention, snapshot, and audit permissions before research |
| R33 | Security-population scope drifts across experiments | Results become incomparable | Ratified universe definitions and versioned deviations |
| R34 | Strategy incentives leak into discovery | Thresholds and horizons become performance-selected | Strategy-neutral reports and hard Stage 6 firewall |
| R35 | Robustness score creates false precision | Weaknesses hidden by an average or arbitrary ranking | Publish ordinal components, uncertainty, disagreement, and critical gates; prohibit composite ranking |
| R36 | One authorised MDM measurement system has a systematic defect | Independent analysis repeats the same source error | MDM lineage audit, sentinels, correction tracking, residual-risk disclosure, and evidence downgrade |
| R37 | “All lessons learned” cannot be audited under the clean-room prohibition | Unknown governance lesson may be omitted | Owner-approved sanitised lesson list and lesson-to-invariant traceability inside this repository |
| R38 | Stage 3 receives an unvalidated, out-of-scope, stale, or nonconforming feature | Leakage or measurement error contaminates discovery and all descendants | Fail-closed Stage 2.5 dossier and view-conformance gate; quarantine, revalidation, and downstream impact review |
| R39 | Feature validation is influenced by predictive outcomes | Attractive but defective measurements are approved | Isolate measurement challenges from Stage 3 outcomes; register acceptance rules; independent validation review |
| R40 | A discrete maturity label substitutes for continuous evidence | Weakening, competing, superseded, or contradictory evidence becomes invisible | Append-only evidence-profile snapshots; contribution classification; full evidence inventory and reasoned updates |
| R41 | Dependency graph is stale, cyclic, incomplete, or falsely satisfied | Research executes before its scientific prerequisites exist | Versioned edge ontology, frozen eligibility snapshot, execution-time recheck, cycle governance, and invalidation propagation |
| R42 | Discovery budgets are evaded through renamed descendants, automation, or hidden grids | Research drift and false discoveries expand without control | Hierarchical reservation and consumption ledger; complete ancestry; exhaustion gate and prospective expansion approval |
| R43 | Research Cost is missing, optimistic, or recorded only for successful work | Scheduler failure, selective feasibility, storage loss, and distorted planning | Mandatory ranged estimates; feasibility review; actuals and variance for complete, failed, invalid, and abandoned work |
| R44 | ESIG becomes a disguised forecast of positive results or an opaque ranking score | Favoured hypotheses receive resources and apparent evidential weight | Freeze ESIG pre-outcome; value every result class; preserve separate cost/value axes, reviewer disagreement, and audit history |
| R45 | Interaction edges are inferred from correlation, shared samples, adjacency, or narrative | Redundancy is mistaken for replication and association for causality | Registered relationship estimands, edge-specific evidence profiles, independence metadata, causal labels, and normal validation |
| R46 | Phenomena and relationship graphs grow without review or revalidation | The scientific map becomes contradictory, stale, and unusable | Named graph custodian, controlled vocabularies, maturity states, scheduled synthesis, supersession, and conflict retention |

### 15.1 Highest-priority scientific threats

Eight risks dominate:

1. **Point-in-time data insufficiency.** The requested catalogue assumes identity, delisting, corporate-action, classification, event, and revision histories that MDM may not provide.
2. **Large-N illusion.** Common market dates and overlapping outcomes can make weak relationships look overwhelmingly certain.
3. **Multiplicity and holdout consumption.** Hundreds of features multiplied by horizons, segments, and regimes can exhaust false-discovery control and historical independence rapidly.
4. **Equity-universe reconstruction.** Survivorship, ticker reuse, share classes, and changing membership can corrupt every cross-sectional result.
5. **Feature trustworthiness.** A generated but unvalidated or nonconforming feature can carry leakage, revision error, or numerical instability into every later stage.
6. **Research-planning integrity.** Hidden exploration, optimistic cost estimates, or outcome-influenced ESIG can distort which uncertainties are investigated and exhaust scientific or computational capacity.
7. **Evidence and graph governance drift.** Stale dependencies, binary evidence summaries, or unsupported interaction edges can make apparently orderly research scientifically selective or causally misleading.
8. **Scientific/strategy boundary erosion.** Performance-led thresholds can quietly turn a phenomena programme into an optimiser.

These are architecture-level risks. They cannot be repaired solely by later robustness checks.

---

## 16. Open decisions and omissions before implementation

The following items are not safely inferable from the Stage 0 brief. They must be resolved or explicitly accepted as limitations before software implementation or empirical testing.

### 16.1 Blocking scope decisions

- geographic market and exchange coverage;
- security types and treatment of ordinary shares, REITs, ADRs, ETFs, funds, OTC securities, preferreds, warrants, and special-purpose vehicles;
- primary-listing, secondary-listing, issuer, and multiple-share-class rules;
- IPO seasoning, suspensions, relistings, bankruptcies, acquisitions, and delistings;
- base currency, foreign-exchange conversion policy if relevant, and total-return convention;
- eligible historical era and required minimum coverage; and
- whether intraday, quote, auction, borrow, ownership, and event data exist in MDM.

### 16.2 Blocking time and identity decisions

- official research cutoff for each exchange;
- timezone, daylight-saving, holiday, early-close, and unscheduled-closure handling;
- after-hours, pre-market, and date-only event assignment;
- economic, publication, availability, and MDM-vintage semantics;
- security-versus-issuer identifier hierarchy and ticker reuse;
- corporate-action effective and knowledge times; and
- point-in-time sector, industry, index, and peer definitions.

### 16.3 Blocking statistical decisions

- canonical outcome and horizon dictionary;
- minimum scientifically relevant effect by phenomenon family;
- power, precision, and equivalence policy;
- approved design-to-estimator matrix, effective-cluster minima, small-sample corrections, and not-inferable conditions;
- overlapping-outcome purge and embargo rules;
- discovery-campaign FDR, sealed-sample FWER, selective-inference, and programme-sequential decision frameworks;
- interim-inspection rules;
- holdout ownership, access, refresh, and prospective-data policy; and
- direct-replication prediction/compatibility criteria and independent reimplementation required for each evidence level.

### 16.4 Blocking data-quality decisions

- typed missingness and default non-imputation policy;
- outlier, stale-price, halt, zero-volume, and suspension handling;
- raw versus adjusted price and return views;
- delisting outcome treatment;
- MDM correction and historical-vintage retention policy;
- acceptable fundamental/event timestamp quality;
- classification and membership coverage thresholds;
- Stage 2.5 deterministic and numerical tolerances, reference cases, coverage minima, and feature-view conformance criteria;
- feature-validation conditional-scope, expiry, quarantine, revocation, supersession, and revalidation-trigger policy;
- standardised friction and liquidity-descriptor fidelity, with formal capacity deferred to Stage 6; and
- MDM licensing and reproducibility permissions.

### 16.5 Governance decisions

- named owners for data, methods, catalogue, knowledge, replication, and adjudication;
- permissible role overlap;
- preregistration amendment and deviation rules;
- registered output roles and the hypothesis decision function;
- abandonment, retraction, contradiction, and supersession rules;
- robustness-profile ordinal anchor, assessor-disagreement, and not-applicable procedure;
- evidence-card review and revalidation cadence;
- internal incentives for negative results; and
- explicit authority required to activate Stage 6.

### 16.6 Blocking Version 1.1 governance decisions

- continuous evidence-profile contribution vocabulary, snapshot triggers, synthesis cadence, update authority, reviewer-disagreement treatment, and maturity-decision interface;
- Research Dependency Graph node and edge ontology, minimum prerequisite states, cycle treatment, graph steward, execution-time recheck, review cadence, and downstream invalidation propagation;
- discovery-budget units by research family, hierarchy, reservation and consumption events, automation accounting, exhaustion review, release rules, and authority for prospective expansion;
- Research Cost units, standard resource profiles, range and confidence conventions, estimation review, actual-cost capture, material-variance threshold, calibration process, and scheduler feasibility limits;
- ESIG assessment rubric, permissible ordinal bands or ranges, reviewer roles, uncertainty and disagreement reporting, priority and tie-break policy, protected scientific capacity, and outcome-information firewall;
- scheduler release authority, queue-decision audit requirements, override authority, cancellation and rescheduling policy, and separation of priority from evidence;
- Phenomena Interaction Graph node and edge ontology, direction and symmetry rules, relationship maturity, independence requirements, causal-status labels, graph steward, contradiction handling, and revalidation cadence; and
- feature-validation and graph retention rules when MDM licensing, correction history, or reproducibility constraints limit exact replay.

Until resolved, these are declared omissions rather than assumptions. In particular, the document does not assume that MDM already supports point-in-time fundamentals, earnings timestamps, index membership, spreads, ownership, borrow, or delisting returns.

---

## 17. Acceptance gates

### 17.1 Stage 0 foundation gate

Implementation should not begin until:

- repository confinement and project-independence rules are ratified;
- MDM is confirmed as the sole market-data authority;
- scientific vocabulary and the evidence lifecycle are approved;
- all blocking population, identity, timing, and return semantics are resolved;
- preregistration and amendment policy is complete;
- dependence, power, multiplicity, holdout, and replication policies are approved;
- the Stage 2.5 validation, dossier, feature-view conformance, quarantine, and revalidation model is accepted;
- the append-only Knowledge Base, negative-results model, and continuous evidence-profile contract are accepted;
- the Research Dependency Graph, evidence provenance graph, and Phenomena Interaction Graph have distinct approved ontologies, ownership, and review rules;
- discovery-budget, Research Cost, ESIG, and scheduler-planning policies are approved as separate controls;
- review roles and decision rights are assigned;
- each critical risk is closed or accepted by a named accountable owner;
- every blocking decision in Section 16.6 is resolved or explicitly accepted with a named owner; and
- Stage 6 remains a non-authorised boundary.

### 17.2 Stage 1 catalogue gate

A catalogue entry is ready for experimentation only when it is:

- measurable and strategy-neutral;
- falsifiable;
- mapped exclusively to audited MDM fields;
- attached to a point-in-time population and comparator;
- explicit about cutoff, outcome, horizon, and estimand;
- linked to exact versioned Research Dependency Graph prerequisites and minimum acceptable states;
- assigned to a complete test family;
- accompanied by minimum relevant effect and precision rules;
- accompanied by mechanisms, rivals, confounders, falsifiers, and negative controls;
- reviewed for data feasibility and method;
- allocated an explicit discovery-budget envelope and reserved evidence; and
- eligible for later experiment-level Research Cost, ESIG, feature-validation, and scheduler review without presuming their approval.

### 17.3 Stage 2 feature-readiness gate

A generated feature is ready to enter Stage 2.5 review only when:

- its point-in-time definition and first availability are unambiguous;
- MDM lineage and snapshot semantics pass;
- security, classification, peer, and corporate-action dependencies are versioned;
- missingness and quality states are defined;
- no full-sample transformation or outcome leakage exists;
- deterministic reconstruction and invariants pass; and
- the feature family and multiplicity treatment are recorded.

These are necessary generation controls, not scientific feature validation and not permission to enter Stage 3.

### 17.3A Stage 2.5 feature-validation gate

A feature version and generated view are eligible for Stage 3 only when:

- an immutable validation dossier exists for the exact feature definition and version;
- every applicable dimension in Section 8A.2 was challenged under frozen acceptance rules and complete results were retained;
- the decision is validated or validated conditional for the proposed population, period, cutoff, MDM lineage, and scientific use;
- the exact generated feature view has a conforming fingerprint, row, coverage, dependency, and environment record;
- every upstream data, classification, feature, and scientific dependency is satisfied for the same domain;
- no quarantine, revocation, supersession, expiry, unresolved anomaly, or revalidation-due trigger applies;
- an independent reviewer and MDM/data steward approved the decision within their authority; and
- known limitations and prohibited interpretations are visible to the experiment preregistration and scheduler.

This gate cannot be waived. A failed or incomplete gate returns the feature to measurement work in Stages 2 or 2.5 and prohibits exposure to Stage 3 outcomes.

### 17.4 Per-experiment gates

1. **Planning admission:** The exact proposal has a satisfied dependency snapshot, applicable discovery-budget reservation, statistical-family assignment, Research Cost estimate, frozen ESIG assessment, evidence allocation, and audited scheduler decision.
2. **Feature eligibility:** Exact feature versions and the generated view pass the current Stage 2.5 gate for the declared domain, and eligibility is rechecked immediately before execution.
3. **Registration:** Protocol is complete and frozen before relevant outcome access.
4. **Data integrity:** MDM lineage, universe, identity, timing, and corporate actions pass.
5. **Execution integrity:** All registered analyses complete; deviations, failed checks, actual Research Cost, and estimate variances are deposited.
6. **Interpretation:** The governed estimator row, registered decision function, selection-aware multiplicity, magnitude, uncertainty, and dependence-aware power are handled correctly; cost, ESIG, and scheduler priority remain excluded from evidence.
7. **Confirmation:** The claim passes one genuinely locked sample.
8. **Replication:** Independent reimplementation and direct replication on genuinely new outcomes meet a prediction, compatibility, or meta-analytic criterion registered in advance.
9. **Knowledge admission:** Supported, precise-null, contradicted, inconclusive, and invalid conclusions are curated with limitations, a continuous evidence-profile update, and a Phenomena Interaction Graph assessment.
10. **Revalidation:** Current status and relationship edges are maintained only while new evidence, dependencies, features, and data remain within declared bounds.

No universal p-value or single score determines passage. Leakage, invalid point-in-time construction, feature-validation failure, unsatisfied mandatory dependency, concealed or over-budget search, and non-reproducibility are absolute failures.

### 17.5 Stage 6 authorisation gate

Future strategy assembly requires a separate approved charter, strategy-neutral evidence contracts at the required maturity, fresh locked data, a new testing budget, independent review, and an explicit scope decision. Until that occurs, strategy design, optimisation, portfolio logic, broker integration, and live-trading work remain prohibited.

---

## 18. Normative scientific templates

These templates define the minimum content of future scientific artifacts. They are conceptual records, not software schemas.

### 18.1 Phenomenon charter

**Identity**

- Permanent phenomenon ID and version
- Title and taxonomy
- Owner and independent reviewers
- Creation and last-review times

**Scientific claim**

- Strategy-neutral statement
- Unit of analysis
- Observable condition
- Comparator
- Outcome distribution
- Horizon and information cutoff
- Population and domain

**Scientific relevance**

- Minimum relevant effect or equivalence region
- Expected shape, sign, or explicitly two-sided alternative
- Prevalence and duration of interest

**Measurement**

- Required MDM fields and capability status
- Point-in-time feature definitions
- Universe, membership, and peer construction
- Missingness and quality policy
- Return and corporate-action convention

**Explanation**

- Proposed mechanism
- Competing mechanisms
- Confounders
- Discriminating predictions
- Falsifying evidence
- Permissible causal label

**Inference and governance**

- Primary estimand
- Dependence-aware uncertainty method
- Test family and multiplicity rule
- Power and precision expectation
- Negative controls and placebos
- Confirmation and replication requirements
- Evidence reservation
- Required Research Dependency Graph nodes, versions, minimum states, and unresolved prerequisites
- Discovery-budget family and envelope

**Evidence**

- Linked registrations, runs, findings, reproductions, and replications
- Supporting, precise-null, contradicted, inconclusive—including underpowered—and invalid results
- Current evidence level
- Current continuous evidence-profile snapshot and trajectory
- Competing, weakening, replicating, contradictory, scope-refining, and superseded contributions
- Existing or proposed Phenomena Interaction Graph relationships and their maturity
- Known boundaries and revalidation triggers

### 18.2 Experiment preregistration

**Lineage**

- Experiment ID
- Parent phenomenon and hypothesis versions
- Complete prior search and data-exposure history
- Discovery campaign, sealed-sample family, and programme-sequential allocation
- Frozen Research Dependency Graph snapshot and eligibility decision
- Discovery-budget reservation and ancestry

**Primary design**

- Exact claim and direction
- Exposure, comparator, outcome, estimand, and horizon
- Information cutoff and outcome maturity
- Minimum relevant effect, independent scientific rationale, output roles, and complete decision function
- Eligible population and date interval

**Data**

- MDM snapshot identity
- Security, universe, membership, calendar, and corporate-action versions
- Inclusion, exclusion, missingness, stale, outlier, halt, and delisting policies
- Coverage and minimum effective-sample requirements

**Features**

- Feature IDs and versions
- Stage 2.5 dossier IDs, scoped validation state, review time, expiry or revalidation state, and prohibited interpretations
- Exact feature-view conformance record and dependency versions
- Transformations fitted only on prior data
- Cross-sectional denominator, leave-one-out, and peer rules

**Inference**

- Governed design-to-estimator policy row and uncertainty method
- Date, issuer, sector, event, and overlap dependence treatment
- Raw/total/conditional estimand and temporally admissible adjustment set
- Primary, ordered secondary, diagnostic, safety-sentinel, and exploratory outputs
- Decision-family hypotheses, error quantity, dependence, stopping rule, and correction
- Dependence-aware power, precision, and equivalence rules

**Validation**

- Discovery, confirmation, independent reimplementation, and direct-replication assignments
- Walk-forward and rolling-window plan
- Segment and regime interactions
- Negative controls, falsification, and robustness checks
- Direct-replication prediction or compatibility rule
- Standardised friction stress mapping and liquidity descriptors where applicable; formal capacity deferred

**Governance**

- Author, executor, data steward, reviewers, and replication lead
- Research-planning steward and feature-validation reviewer
- Registration time and fingerprint
- Permitted amendments
- Deposit and adjudication requirements

### 18.2.1 Research-planning record

**Identity and eligibility**

- Planning-record ID and version
- Proposed experiment, validation, reproduction, replication, or revalidation ID
- Protocol and MDM-scope versions
- Research Dependency Graph snapshot, required nodes and minimum states, eligibility result, and execution-time recheck requirement
- Stage 2.5 feature versions, dossier decisions, and conformance requirements

**Discovery and evidence controls**

- Discovery-budget parent, units, reservation, consumption rule, remaining balance, and expansion status
- Statistical family, error-control allocation, holdout assignment, and exposure-ledger links
- Confirmation and replication evidence reservations

**Research Cost estimate**

- Expected CPU core-hours or equivalent range and parallelism assumptions
- Expected peak and sustained memory
- Expected temporary, intermediate, retained-input, retained-output, log, and Knowledge Base storage
- Expected wall-clock runtime, resource profile, queue constraints, and timeout risk
- Expected MDM, feature, intermediate, and output data volume in rows, bytes, securities, periods, and partitions
- Expected statistical complexity: estimators, tests, fits, folds, windows, simulations, resamples, segments, regimes, horizons, interactions, and network relationships
- Units, ranges, estimation method, resource and environment assumptions, estimate uncertainty, owner, reviewer, version, and feasibility decision

**ESIG assessment**

- Target scientific uncertainty and current evidence-profile versions
- Competing accounts and discriminating value
- Plausible result classes and expected learning from support, precise null, contradiction, inconclusion, boundary refinement, or data-defect discovery
- Expected precision, independence, scope, falsification, dependency-unlocking, interaction, and multi-phenomenon value
- Redundancy, assumptions, ordinal band or range, assessment confidence, reviewer disagreement, owner, reviewers, and frozen time

**Scheduling and actuals**

- Priority rule, protected-capacity class, queue decision, time, decision-maker, deferrals, overrides, and reason
- Actual CPU, memory, storage, runtime, queue/retry time, data volume, and executed statistical workload
- Estimate-versus-actual variance and explanation, including for failed, invalid, stopped, and abandoned work
- Links to superseded estimates without overwriting any prior record

### 18.3 Feature-definition record

- Feature ID, version, name, and construct
- Mathematical definition and unit
- MDM input lineage and availability
- Security and universe scope
- Cutoff, lag, history, and minimum observations
- Corporate-action and return convention
- Peer, grouping, weighting, self-exclusion, and fallback
- Scaling, ranking, clipping, and ties
- Typed missingness and imputation status
- Expected range and invariants
- Known artifacts and prohibited interpretation
- Quality grade by period and segment
- Research Dependency Graph prerequisites and upstream feature versions
- Stage 2.5 validation state, dossier IDs, scoped domain, conformance requirements, expiry, and revalidation triggers
- Owner, reviewer, approval, and supersession

### 18.3A Feature-validation dossier

**Identity and scope**

- Validation ID, feature ID and version, construct, definition fingerprint, unit, owner, independent reviewer, MDM/data steward, and decision time
- Validation population, dates, cutoff, MDM lineage, universe, calendars, classifications, corporate actions, peer rules, and intended scientific use
- Research Dependency Graph snapshot and all upstream feature-validation states

**Frozen validation protocol**

- Applicable validation dimensions and construct-specific challenges
- Acceptance rules, numerical tolerances, deterministic expectations, reference cases, sentinels, seeds, minimum coverage, and permitted conditional outcomes
- Missingness, revision, sensitivity, environment, and feature-view conformance procedures

**Complete evidence**

- Deterministic reproducibility and computational determinism results
- Point-in-time, availability, target-separation, and leakage results
- Numerical stability, missing-data robustness, sensitivity, and boundary results
- MDM revision, correction, schema, and version-consistency results
- End-to-end data-lineage and exact generated-view conformance results
- All failed, unavailable, inconclusive, rejected, abandoned, and reviewer-disputed checks
- Research Cost estimate, actuals, and variance

**Decision and lifecycle**

- Validated, validated conditional, rejected, inconclusive, invalid, quarantined, revoked, revalidation due, superseded, or pending state
- Exact scope, limitations, prohibited interpretations, rationale, approval authority, and dissent
- Expiry, revalidation triggers, next review, downstream dependencies, impact-review links, and supersession history

### 18.4 Result and validation dossier

- Frozen preregistration and all amendments
- Frozen dependency, discovery-budget, Research Cost, ESIG, feature-validation, and scheduler-planning records
- MDM and feature manifests
- Data-integrity and point-in-time certificate
- Complete row, universe, exclusion, and coverage accounting
- Primary result and diagnostics
- Every registered secondary, segment, regime, and robustness result
- Raw and adjusted multiplicity output
- Fold-level and rolling stability
- Effect magnitude, uncertainty, materiality, and power
- Negative controls and falsification
- Influence and artifact checks
- Reproduction and replication
- Scientific Robustness Profile
- Implementation Relevance Profile
- Mechanism and rival-explanation assessment
- Deviations and limitations
- Actual Research Cost and estimate-variance explanation
- Reviewer decisions and adjudication
- Evidence-card, continuous evidence-profile, Phenomena Interaction Graph, and revalidation updates

### 18.5 Robustness scoring rubric

Each applicable scientific dimension in Section 10.13 is rated from 0 to 4 under a rubric approved before candidate results:

| Score | General anchor |
|---:|---|
| 0 | Critical failure, absent required evidence, or invalid construction |
| 1 | Major weakness; evidence is fragile or mostly retrospective |
| 2 | Mixed evidence; minimum execution standard met but important instability remains |
| 3 | Strong evidence; registered criterion met with no unresolved major weakness |
| 4 | Exceptional evidence; independent or prospective challenge provides additional support |

Dimension-specific anchors shall define observable criteria. Examples include:

- **Point-in-time integrity:** from material leakage at 0 to independently reconstructed identity, timing, universe, and MDM lineage at 4.
- **Preregistration and multiplicity:** from undisclosed search at 0 to fully prospective protocol, complete ancestry disclosure, and correct decision-family and sequential control at 4.
- **Magnitude and precision:** from negligible or unbounded at 0 to precise, materially meaningful, distributionally coherent evidence at 4.
- **Temporal stability:** from one-episode dominance at 0 to repeated prospective periods with bounded heterogeneity at 4.
- **Cross-sectional transportability:** from unexplained single-cell concentration at 0 to broad or mechanism-predicted replication at 4.
- **Regime behaviour:** from hindsight conditioning at 0 to point-in-time replication of registered regime predictions at 4.
- **Falsification resilience:** from failed sentinels at 0 to survival of strong negative controls and discriminating tests at 4.
- **Reproduction and replication:** from non-reproducible at 0 to independent reimplementation plus direct replication on genuinely new outcomes at 4.

The rating vector is not aggregated, averaged, or used to rank phenomena. Critical gates remain authoritative. Reviewers record supporting evidence, confidence in the rating, disagreement, and not-applicable or not-assessable reasons.

Mechanism evidence receives a separate Explanatory Credibility Profile using its own registered anchors. Implementation descriptors receive a separate Implementation Relevance Profile. Neither changes the scientific ratings.

The ordinal anchors and assessor process must be challenged before candidate outcomes using:

- simulated null panels with realistic dependence;
- deliberately leaked features;
- point-in-time membership and corporate-action sentinels;
- dependence-preserving permutations;
- known data-quality failures; and
- repeatability challenges.

This exercise should measure inter-rater reliability and ability to recognise known failure cases as well as nulls. It cannot transform qualitative ratings into a probability of truth. Thresholds or weights derived by looking at actual candidate results are prohibited.

### 18.6 Continuous evidence-profile update

- Phenomenon and profile-snapshot IDs and versions
- Previous snapshot, update trigger, evidence cutoff, custodian, reviewers, and decision time
- Exact claim scope, estimands, measurements, populations, horizons, and MDM vintages represented
- Complete eligible evidence inventory and excluded-invalid evidence with reasons
- Comparability and independence assessment across studies
- Effect, precision, materiality, heterogeneity, prevalence, response-shape, and decay trajectory
- Each incoming contribution classified as strengthening, weakening, replicating, contradictory, competing, scope-refining, superseding, or non-informative, with reason
- Mechanism, rival, falsification, boundary, and causal-status update
- Confidence evolution since the prior snapshot without compulsory scalar or binary truth label
- Current maturity, limitations, unresolved contradiction, reviewer disagreement, revalidation need, and links to affected interaction edges

### 18.7 Phenomena Interaction Graph edge record

- Permanent relationship ID and version; exact endpoint phenomenon versions
- Relationship type: reinforcement, redundancy, hierarchy, causal hypothesis, conditional dependence, interaction, or conflict
- Direction or symmetry, scientific statement, mechanism, rival accounts, and causal-status label
- Population, period, regime, sector or industry, cutoff, exposure, comparator, outcome, horizon, estimand, and minimum relevant relationship
- MDM lineage, exact features and Stage 2.5 dossiers, dependency snapshot, and exposure history
- Linked registrations, runs, findings, reproductions, replications, falsifiers, reviews, and contradictions
- Effect, uncertainty, heterogeneity, independence, shared-sample and shared-feature limits, and known boundaries
- Edge-specific continuous evidence-profile snapshot, maturity, review decision, disagreement, revalidation triggers, status history, and supersession links

---

## 19. Conclusion and approval recommendation

Project EDGE should proceed as a clean-room scientific platform whose durable product is cumulative evidence about equity-market behaviour. Its defining architecture is not the number of features it can calculate. It is the chain of custody from an authorised MDM observation, through point-in-time measurement and fully disclosed discovery, to preregistered validation, independent reimplementation, direct replication, and an append-only knowledge decision.

Version 1.1 strengthens that chain at three points. Stage 2.5 prevents unvalidated measurements from entering discovery. Research dependencies, discovery budgets, Research Cost, ESIG, and a governed scheduler make scientific readiness, exploratory freedom, computational effort, and expected learning explicit before execution. Continuous evidence profiles and the Phenomena Interaction Graph then preserve how confidence and relationships evolve instead of reducing the Knowledge Base to isolated binary labels.

Stage 1 should begin only after approval of this foundation and should prioritise, in order:

1. the scientific constitution and strategy boundary;
2. the MDM point-in-time capability audit;
3. the security population, identity, classification, calendar, and return conventions;
4. the catalogue, preregistration, test-family, holdout, and negative-results contracts;
5. a small, balanced pilot catalogue covering relative strength, continuation/reversal, volatility states, gaps, volume response, breadth, and cross-sectional dispersion;
6. deliberate data-leakage and survivorship falsification studies; and
7. independent review roles and Stage 1 acceptance.

Before any Stage 3 discovery, Stage 1 must additionally ratify the Stage 2.5 protocol, seed and review the Research Dependency Graph, approve discovery-budget units and exhaustion rules, calibrate the Research Cost and ESIG planning records, establish scheduler decision rights, and approve the continuous evidence-profile and Phenomena Interaction Graph contracts. The measurement-only governance pilot in Section 14.11 should demonstrate those controls using both passing and deliberately failing cases.

Fundamental, earnings, institutional, sector-rotation, quote-level, and friction-descriptor research must remain conditional on MDM proving the necessary historical availability and timestamp fidelity. Formal capacity research remains deferred to an authorised Stage 6.

Implementation should pause if any of the following remain unresolved:

- survivorship-complete security history and delisting treatment;
- stable security/issuer identity;
- corporate-action and return semantics;
- point-in-time availability and revision rules;
- historical sector/index/peer membership;
- approved Stage 2.5 acceptance, conformance, and revalidation rules;
- dependency-graph ownership and prerequisite semantics;
- discovery-budget units, consumption, and expansion authority;
- Research Cost, ESIG, and scheduler-decision standards;
- continuous evidence-profile and interaction-graph governance;
- dependence-aware inference;
- global multiplicity and holdout stewardship; or
- immutable retention of negative and contradictory evidence.

The central scientific risks are point-in-time leakage, false precision from dependent equity panels, unvalidated or stale features, multiplicity and discovery drift across a large feature space, holdout exhaustion, stale or falsely satisfied dependencies, misestimated research cost, outcome-influenced ESIG, binary evidence summaries, unsupported interaction or causal claims, microstructure and small-cap artifacts, post-hoc explanation, and gradual erosion of the phenomenon/strategy boundary. The principal omissions are the unresolved market scope, the unverified extent of MDM’s point-in-time coverage, and the unratified Version 1.1 governance decisions in Section 16.6.

Subject to those explicit Stage 0 gates, this Version 1.1 architecture is recommended as the scientific foundation for Stage 1. It supports broad but bounded discovery without rewarding indiscriminate search, preserves failure and changing confidence as knowledge, gives cross-sectional equity context first-class status, builds an evolving scientific map of phenomenon relationships, and keeps any future strategy activity downstream of independently validated science.

---

## 20. Version 1.1 change log

### 20.1 Change method and preservation

Version 1.1 is an additive successor to the approved-in-principle Version 1.0. The original `PROJECT_EDGE_FOUNDATION_DOCUMENT.md` remains the Version 1.0 authority and has not been rewritten by this amendment process. Existing major section numbers 1–19 were preserved. Stage 2.5 was inserted as Section 8A so that Stages 3–6 and their established section numbers did not need to be renumbered.

No source code, package structure, placeholder module, strategy, optimisation, broker integration, execution component, or live-trading component was introduced. MDM remains the sole authorised market-data source, and the clean-room restrictions remain unchanged.

### 20.2 Amendment integration summary

| Amendment | Primary integration | Exact architectural effect | Principal secondary integrations |
|---|---|---|---|
| 1. Continuous Evidence Accumulation | Sections 3.9 and 11.6.1 | Adds an immutable sequence of continuous evidence-profile snapshots; classifies strengthening, weakening, replicating, contradictory, competing, scope-refining, superseding, and non-informative contributions; separates confidence evolution from discrete maturity and binary truth | Sections 4, 5.1–5.4, 11.1–11.10, 13.1–13.3, 14.5, 14.10–14.11, R40, 16.6, 17.1 and 17.4, 18.1, 18.4 and 18.6, and Section 19 |
| 2. Research Cost Accounting | Sections 13.6.2 and 18.2.1 | Requires permanent pre-execution estimates of CPU, memory, storage, runtime, data volume, and statistical complexity; makes them scheduler inputs; appends actual consumption and variance for successful, failed, invalid, stopped, and abandoned work; keeps cost independent of scientific value | Sections 3.10, 4, 5.1–5.4, 8A.3 and 8A.7, 9.2–9.10, 10.3, 10.12, 11.3, 13.2–13.3 and 13.6.4, 14.5 and 14.10–14.11, R43, 16.6, 17.1–17.4, 18.3A–18.4, and Section 19 |
| 3. Expected Scientific Information Gain | Sections 13.6.3 and 13.6.4 | Defines ESIG as a frozen outcome-independent assessment of uncertainty reduction across all plausible result classes; supports learning-per-effort and non-FIFO scheduling without becoming expected support, significance, profitability, evidence weight, or a hidden composite score | Sections 3.10, 4, 5.1–5.4, 9.2–9.10, 10.3, 11.3, 13.1–13.3, 14.5 and 14.10–14.11, R44, 16.6, 17.1–17.4, 18.2.1 and 18.4, and Section 19 |
| 4. Research Dependency Graph | Sections 7.3.1 and 13.6.4 | Creates a first-class versioned prerequisite graph with typed nodes and edges, minimum states, frozen eligibility snapshots, cycle controls, scheduler blocking, and downstream invalidation review | Sections 3.11, 4, 5.1–5.4, 8.3, 8A.3–8A.7, 9.2–9.10, 10.2–10.3 and 10.14, 11.2–11.3 and 11.9–11.10, 13.1–13.3, 14.5 and 14.10–14.11, R41, 16.6, 17.1–17.4, 18.1–18.3A and 18.7, and Section 19 |
| 5. Discovery Budgets | Sections 9.6 and 13.6.1 | Adds prospective limits for hypothesis families, features and combinations, parameter grids, regime partitions, horizons, outcomes, descendants, and automated search; defines reservation, consumption, ancestry, exhaustion, evidence review, validation, and formal expansion approval; separates exploration control from compute and statistical budgets | Sections 3.10, 4, 5.1–5.4, 7.4, 9.2–9.3 and 9.9–9.10, 10.2–10.3, 11.3, 13.1–13.3 and 13.6.4, 14.5, 14.8 and 14.10–14.11, R42, 16.6, 17.1–17.4, 18.1–18.2.1 and 18.4, and Section 19 |
| 6. Phenomena Interaction Graph | Sections 11.8.1 and 18.7 | Creates a first-class evolving scientific map with reinforcement, redundancy, hierarchy, causal-hypothesis, conditional-dependence, interaction, and conflict edges; gives each edge its own scope, evidence, maturity, confidence evolution, contradictions, and revalidation | Sections 3.11, 4, 5.1–5.4, 7.3.1, 11.1–11.2 and 11.6–11.10, 13.1–13.3, 14.5 and 14.10–14.11, R45–R46, 16.6, 17.1 and 17.4, 18.1, 18.4 and 18.6, and Section 19 |
| 7. Stage 2.5 Feature Validation | Sections 8A and 17.3A | Inserts a fail-closed scientific measurement stage with definition validation and exact-view conformance; covers deterministic reproducibility, point-in-time correctness, leakage, numerical stability, missingness, sensitivity, revisions, computational determinism, version consistency, lineage, scoped decisions, quarantine, and revalidation; bars all unvalidated features from Stage 3 | Sections 1, 3.12, 4, 5.1–5.4, 8.1–8.3 and 8.8–8.9, 9.1–9.3 and 9.9–9.10, 10.2–10.3 and 10.14, 11.1 and 11.3, 13.1–13.3, 14.5 and 14.9–14.11, R38–R39, 16.4 and 16.6, 17.1–17.4, 18.2–18.4 and 18.3A, and Section 19 |

### 20.3 Detailed placement by new section

- **Section 3.9** establishes the architectural commitment to continuous, non-binary confidence evolution.
- **Sections 3.10–3.12** add the planning ontology, distinguish the three scientific relationship structures, and define feature-validation status.
- **Section 7.3.1** places prerequisite governance in Stage 1 so hypothesis readiness exists before feature generation or experimentation.
- **Section 8A** inserts Stage 2.5 between generation and discovery without renumbering the approved downstream stages.
- **Sections 9.1–9.3, 9.6, 9.9, and 9.10** make feature validation, dependencies, discovery budgets, Research Cost, and ESIG enforceable at discovery admission and promotion.
- **Sections 10.2–10.3, 10.12, and 10.14** preserve feature eligibility through confirmation, keep Research Cost separate from transaction-cost and capacity descriptors, and require current eligibility for reproduction and replication.
- **Section 11.6.1** makes continuous evidence profiles permanent Knowledge Base objects.
- **Section 11.8.1** makes phenomenon relationships permanent, versioned, evidence-backed Knowledge Base objects distinct from prerequisite and provenance graphs.
- **Sections 13.6.1–13.6.4** contain the formal discovery-budget, Research Cost, ESIG, and scheduler-facing planning architecture.
- **Sections 14–19** extend recommendations, risks, unresolved decisions, gates, normative records, and the final approval recommendation so that the amendments are governable before implementation.

### 20.4 Compatibility statement

The Version 1.1 additions do not relax any Version 1.0 scientific boundary. Where an amendment creates a new control, the stricter rule governs: discovery cannot use an unvalidated feature; an unsatisfied dependency blocks execution; consumed exploratory capacity cannot be hidden or reset; cost and ESIG cannot influence evidence; earlier or adverse evidence cannot be erased; and phenomenon relationships cannot be promoted from association or narrative alone.
