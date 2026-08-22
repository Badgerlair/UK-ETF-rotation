# PROJECT EDGE

## IMPLEMENTATION MILESTONE 4 — PRODUCTION READINESS REVIEW

**Review date:** 4 August 2026  
**Repository:** `D:\codex\equity_quant_research_platform`  
**Review purpose:** Minimise time to the first scientifically valid empirical
phenomenon-discovery experiment without weakening point-in-time correctness,
reproducibility, admissibility, or bias prevention.  
**Implementation changes made:** None. This milestone is a readiness decision,
not an architecture or software milestone.

---

## 1. Executive decision

Project EDGE is not ready to execute a real empirical experiment today. The
dominant blocker is not missing enterprise infrastructure. It is the absence of
one authorised, scope-complete, immutable and exactly replayable MDM snapshot
containing the histories required by a scientifically defensible bounded pilot.

The fastest defensible pilot need not estimate returns. Milestone 2 Section 8.5
explicitly permits a narrowly scoped raw-observation study when unresolved
corporate-action economics cannot affect its estimand and the restriction is
explicit. A same-session, dimensionless volatility-persistence measurement can
therefore avoid waiting for complete cash-distribution and terminal-
consideration economics, while still requiring stable identity, a
survivor-accounted cohort, authoritative sessions, coherent OHLC rows,
immutable replay, typed missing outcomes, and detection/quarantine of any event
that makes a row incomparable.

The current Milestone 3 path does not yet express that frozen conditional
admission: it always constructs and validates a return-consistent view. A small
observed-price-only admission path is therefore part of the minimum fast route.
If that scoped exception cannot be proven, the fallback is to keep the current
path unchanged and require complete distributions and terminal-return data
before the pilot.

The shortest scientifically valid route is:

1. freeze one narrow daily pilot population and clock;
2. have MDM publish the bounded production data required by that exact
   raw-observation scope;
3. bind the ratified policy in the existing code and approve the exact source
   and request scope;
4. run the existing real-data admission, coverage, replay and release path;
5. close the mutation gap between access verification and experiment reading;
6. implement and validate only the one or very small number of measurements
   required by the pilot; and
7. execute one immutable, preregistered, tightly budgeted exploratory study and
   retain every result, including a null or rejection.

No generic discovery engine, enterprise registry platform, distributed system,
external ledger, broad feature factory, sector history, fundamentals, intraday
data, strategy layer, or trading infrastructure is needed for the first pilot.

Once a conforming MDM snapshot exists, an indicative Project EDGE planning
envelope is **15–30 person-days**, plus independent review: roughly 3–6 days for
policy, scope and real-data admission; 5–10 days for conditional observed-price
admission, protected release and mutation-safe access; and 7–14 days for the
feature, Stage 2.5, preregistration, analysis, and evidence deposit. Work may
overlap, and real data can trigger additional remediation. This is a planning
range, not a delivery promise. MDM remediation is the critical path and cannot
be estimated credibly until MDM confirms whether the missing histories already
exist in an admissible source.

The first study must be labelled **exploratory phenomenon discovery**. It may
produce a candidate, null, contradiction, or data limitation. It cannot by
itself establish persistence, exploitability, or a robust trading edge.

---

## 2. Review basis and classification rules

This review uses:

- the frozen Stage 0 Foundation Version 1.1;
- the frozen Milestone 2 MDM Data Foundation Specification;
- the Milestone 3 implementation, report, gate configurations, synthetic
  acceptance artifact, and content-addressed 79-test evidence record; and
- the current production-gate result: MDM `BLOCKED`, Population and Time
  Contract `UNRATIFIED`, production scope `NO_APPROVED_SCOPE`, and release
  authority `NOT_CONFIGURED`.

The frozen Foundation and Milestone 2 files were not modified. Their verified
SHA-256 values remain:

- Foundation V1.1:
  `f96d0b88bd6dce18faa92b3c7c111a743c365870814143ee0f23cf3077e14291`;
- Milestone 2:
  `ad811f11de8856ca217eaf857117d5ecb37fd2d974ecc578589aa5f50cfbb942`.

No material under `research/`, no completed experiment output, no previous
findings database, and no prohibited project was used in this review. The MDM
capability result is taken from the retained read-only Milestone 3 audit.

### 2.1 Classifications

| Classification | Decision rule |
|---|---|
| **Mandatory** | The first pilot cannot be scientifically valid without it because postponement would materially threaten point-in-time correctness, population validity, measurement validity, reproducibility, bias prevention, or prospective research control. |
| **Important** | Not required for one supervised, serialized and tightly bounded pilot, but required before wider, repeated, multi-user, or capability-dependent research. |
| **Future** | Useful for scale, convenience, resilience, or a later scientific domain, but should not delay the first pilot. |

An Important or Future capability remains unavailable. It may not be
approximated with current values, another data source, a prior-project proxy, or
an undocumented analyst transformation.

### 2.2 Effort scale

| Effort | Indicative work |
|---|---|
| **XS** | Less than one person-day |
| **S** | One to three person-days |
| **M** | Four to ten person-days |
| **L** | Two to six weeks |
| **External/unknown** | Depends on whether MDM possesses admissible source history; no honest estimate is possible yet |

Efforts overlap. The MDM identity, universe, action, and snapshot work should be
delivered as one bounded source release rather than as unrelated projects.

---

## 3. Minimum first-pilot envelope

The blocker classifications below assume the first pilot is deliberately
narrow. The recommended minimum study is a measurement of **daily intraday
volatility persistence**, not a return or strategy study:

- one market and preferably one exchange;
- one currency;
- one explicitly defined set of primary ordinary equity listings;
- security-level or listing-level analysis chosen prospectively and used
  consistently;
- daily post-close observations only;
- one bounded historical interval, including required lookback and outcome
  maturity, selected before outcome inspection;
- one point-in-time formation cohort, followed without deleting later inactive,
  halted, missing, or delisted members;
- primary feature: session `t` intraday log range, `log(high / low)`;
- primary outcome: the same measurement on the immediately following governed
  session;
- one feature, one outcome, one horizon, no regime partitions, and no parameter
  grid;
- no sector, industry, index, fundamental, earnings, event, quote, intraday, or
  cross-currency dependency;
- full return construction prohibited; coherent same-row OHLC basis required;
  any identity, unit, or event state that makes a session incomparable is
  prospectively quarantined;
- missing next-session measurements, halts, suspensions, and terminal cases
  retained in denominators with preregistered missing-not-at-random sensitivity
  or bounds;
- an explicitly reserved unexposed temporal sample for later confirmation; and
- no optimisation, strategy construction, portfolio simulation, broker link,
  execution, or claim of a proven exploitable edge.

Changing this envelope can activate additional Important capabilities as
Mandatory for the changed scope.

The recommended feature is dimensionless and does not compare price levels
across sessions. Multiplicative price adjustments therefore cancel within each
row. Cash distributions and terminal consideration are not inputs to its
estimand. They remain Mandatory before any return, gap, trend, momentum,
reversal, or continuity-dependent pilot.

Unless prospective missing-not-at-random bounds support a broader statement,
the primary estimand and every claim must be limited explicitly to cohort
members with a valid next-session observation. The retained missing and
terminal denominators describe the selection boundary; they are not silently
discarded or imputed.

---

## 4. Scientifically Mandatory blockers

Every item in this section must be complete before the first real pilot may
access its outcomes.

| ID | Remaining blocker and minimum acceptance condition | Classification | Scientific justification | Effort | Scientific risk if postponed | Recommendation |
|---|---|---|---|---|---|---|
| M-01 | **Ratify one narrow Research Population and Time Contract.** Freeze market/exchange, security types, primary/secondary rule, analysis unit, share-class treatment, lifecycle treatment, currency, session cutoff, raw-observation convention, dates, minimum coverage, and MDM retention/replay permission. Declare every return view and return-dependent use unavailable for the fast pilot. | Mandatory | These choices define the population, clock, estimand, and information set. They cannot become defaults or be selected after viewing outcomes. | S | Critical researcher degrees of freedom, scope drift, incomparable units, and an unstable estimand. | Complete before first pilot. Use one exchange and currency; omit optional screens unless their point-in-time inputs are admitted. |
| M-02 | **Scope-complete stable identity and lifecycle history from MDM.** For the exact population and period, MDM must supply stable issuer, security and listing IDs; ticker history and reuse; venue, share class and currency; listing/lifecycle intervals; inactive, acquired, bankrupt, relisted and delisted states; and required successor/predecessor facts. | Mandatory | Ticker drift, ticker reuse, collapsed share classes, and missing dead securities can manufacture cross-sectional and temporal effects. | L / External, overlapping M-03 | Critical identity error and survivorship bias. | Complete before first pilot. A universal legal-entity graph is not required. Unresolved rows must fail or be quarantined under prospective coverage limits. |
| M-03 | **Approved survivor-complete historical population.** Unlock and approve an MDM population export constructed independently of bar availability and current survival. Retain every candidate, inclusion/exclusion reason, lifecycle state, and denominator. Measure inactive, distressed, acquired, bankrupt, relisted and delisted coverage. | Mandatory | A dataset containing mainly securities that survived is the most direct route to a false positive equity effect. | L / External, overlapping M-02 | Critical upward bias and invalid generalisation. | Complete before first pilot for the exact bounded population; global or multi-market coverage is unnecessary. |
| M-04 | **Authoritative MDM calendar and cutoff.** For the selected exchange and period, supply session IDs, timezone/DST, opens, closes, holidays, early closes, unscheduled closures, previous/next sessions, availability, and the ratified research cutoff. | Mandatory | Calendar approximations misalign lags, gaps, lookbacks, outcome horizons, and what was knowable. | S–M / External | High look-ahead and horizon misclassification risk. | Complete before first pilot for the included venue-period only. |
| M-05 | **Explicit raw daily OHLCV contract.** MDM must provide raw unadjusted OHLCV with exact session keys, units, currency, status, availability, quality, vintage, and demonstrated raw/adjusted basis. | Mandatory | Undocumented adjustment or revision behaviour can turn corporate mechanics into apparent phenomena. | M / External | High false momentum, gap, reversal, and volatility effects. | Complete before first pilot. Do not infer basis from observed values. |
| M-06 | **Action and lifecycle sufficiency for the raw-range estimand.** MDM must supply enough identity, lifecycle, basis, action-status, and quality evidence to identify any session whose same-row OHLC values are not coherent or comparable. Such rows must be quarantined prospectively. Terminal, halt, suspension, and missing next-session states remain in denominators. Complete cash amounts and terminal consideration are not inputs to this estimand. | Mandatory | The selected feature is invariant to a common multiplicative row adjustment, but not to an internally inconsistent row, identity break, or silent deletion of missing/terminal observations. | M / External | High false volatility or attrition bias if incompatible rows or missing outcomes are hidden. | Complete before the raw-only pilot. If MDM cannot attest row coherence and detect incompatible states, use the full-return fallback and require complete distributions and terminal outcomes. |
| M-07 | **One atomic, immutable, exactly replayable MDM snapshot.** Publish the five source families under one immutable ID, common cutoff and consistency token, exact schemas, source and logical hashes, correction lineage, and authorised retained bytes or immutable retrievable reference. | Mandatory | Mixed vintages and mutable source files make the study non-reproducible and can mix future corrections into historical data. | M after data exists; source availability External | Critical provenance and replay failure. | Complete before first pilot. A bounded retained export is sufficient; no enterprise snapshot service is required. |
| M-08 | **Resolve only real revision and missingness semantics encountered.** Inspect whether MDM supplies single canonical calendar rows or a revision chain; how identity or membership corrections change interval boundaries; and how halts, suspensions, no-trade and unexplained absences are represented. Existing fail-closed behaviour is acceptable when unsupported patterns are absent. | Mandatory contract check; implementation conditional | Silent precedence guesses or classifying unexplained missing bars as halts would bias weak and distressed stocks. | XS to inspect; S–M only if a real pattern triggers work | High if guessed; negligible if absent and mechanically rejected. | Complete the contract check before first pilot. Implement a new selector only when the actual MDM contract requires it. |
| M-08A | **Implement the frozen observed-price-only conditional admission.** Milestone 2 Section 8.5 permits raw observations for an estimand unaffected by unresolved return economics. The current M3 implementation always creates and validates a return view, and production release currently requires unconditional `ADMISSIBLE` state with no limitations. Add a typed scope-limited path that releases only the observed panel, declares return fields and continuity-dependent uses unavailable, binds the allowed scientific use into scope and artifact identity, and mechanically denies any request exceeding it. | Mandatory for the minimum fast route | Without this change, the code either remains technically blocked by data irrelevant to the chosen estimand or would need an unsafe ad hoc bypass. | M | High if the gate is merely weakened or the restriction is free text; schedule delay if left unchanged. | Complete before the raw-only pilot with dedicated positive, scope-escape, release, and access tests. If this cannot be implemented cleanly, retain the existing path and make complete distributions/terminal economics Mandatory. |
| M-09 | **Code-bind the ratified production policy.** Add the exact approved policy identifiers and semantics to the executable allowlist and pass policy, timing, action, universe, and cutoff sentinels. The current code accepts only the synthetic test bundle. | Mandatory | Ratification alone does not make the policy executable, and an arbitrary caller label must not create scientific semantics. | S | High risk of unreviewed defaults or post-outcome policy changes. | Complete before first pilot; do not build a generic policy engine. |
| M-10 | **Refresh the capability decision to `READY` for the exact allowed use and approve the production scope.** Evidence must show every capability used by the raw-only pilot is admitted and every return-dependent use is blocked. The scope must bind approval ID and content hash to the MDM root, manifest hash, snapshot ID, source version, consistency token, request hash, dates, exchange, security types, currency, fields, and scientific-use restriction. | Mandatory | An exact scope prevents source substitution, silent widening, and the use of an unsupported data family. | S after M-01 to M-09 | High source and scope drift. | Complete before first pilot. Unsupported optional and return families remain explicitly unavailable. |
| M-11 | **Run every applicable Mandatory admission gate on real data and freeze thresholds before outcomes.** Execute the source, identity, calendar, OHLCV, population, point-in-time, missingness, outcome-firewall, lineage and replay checks; run the new conditional-use sentinels; and complete stratified coverage review, especially for inactive, halted, distressed and delisted members. A return check may be outside scope only through the explicit M-08A restriction, never through a false `PASS`. | Mandatory | Synthetic tests demonstrate control behaviour, not real MDM completeness or correctness. Aggregate coverage can hide concentrated attrition. | S after a conforming source; remediation variable | Critical selection, missingness, row-basis, and scope-escape bias. | Complete before first pilot and retain pass/fail evidence. No threshold or scope restriction may be relaxed after outcome inspection. |
| M-12 | **Prove real deterministic replay.** Rebuild the same admitted slice in a fresh production process with the retained runtime and require identical ordered rows, population counts, logical fingerprints, materialised profiles, and artifact identity. | Mandatory | The observed result must be attributable to fixed data and rules rather than environment, order, or mutable input. | S | High reproducibility failure. | Complete before first pilot and retain the exact environment record. |
| M-13 | **Create a truthful minimum pilot release-authority decision.** Do not flip the current Boolean alone. For one serialized pilot, bind the exact artifact and source hashes, scope, builder, genuinely distinct reviewer, content-addressed review evidence, and mutation-safe access condition. Write the chained register through a path protected from ordinary build and analysis writers, retain an independently held backup or copy, verify its integrity, and only then mark the narrow authority record ready. | Mandatory | The existing code correctly blocks production. Opening it without evidence or leaving the release record rewritable by ordinary research execution would turn governance into a self-assertion. | S–M after preceding gates | High chance of consuming an unreviewed/substituted artifact or losing the authoritative release decision. | Complete before first pilot. Full enterprise identity administration, automated external anchoring, recurring backup automation, and multi-writer coordination are classified separately below. |
| M-14 | **Independent content-bound scientific review.** A reviewer distinct from the builder must inspect the real validation, population, missingness, row-basis/action-state, replay, scope, prohibited-use, and limitation evidence and bind the decision to the immutable artifact. | Mandatory | Independent review is a practical sentinel against an unnoticed defect or self-serving admission decision. | XS–S plus reviewer availability | Medium–high undetected admission error. | Complete before first pilot. A named supervised reviewer and immutable review record are sufficient; an enterprise identity platform is not. |
| M-15 | **Mutation-safe consumption of the admitted artifact.** The experiment must read the exact bytes that were verified, through a held verified/read-only handle or locked content-addressed copy with hash verification at the actual read. The analysis identity must be unable to modify those bytes during the run, and pre-run and post-run hashes must agree. | Mandatory | The current access check can finish before a later reader opens a writable path. The analysed bytes could therefore differ from the reviewed bytes. | S–M | High break in chain of custody and irreproducibility. | Complete before first pilot using the smallest local solution. |
| M-16 | **Release and reopen one real outcome-free observed-price feature-ready dataset through the ordinary access path.** The experiment must consume the released panel, cohort/universe manifest, manifests, validation, lineage, and explicit prohibition on return use—not a build or quarantine directory. | Mandatory | This proves that normal research uses only admitted MDM-derived data and preserves both the outcome firewall and the conditional-use boundary. | XS after M-10 to M-15 | High risk of bypassing admission with a convenient build output or using unavailable return fields. | Complete before first pilot. |
| M-17 | **Implement only the exact Stage 2 measurement needed by the pilot.** Freeze formula, inputs, lags, history, timing, missingness, scaling, population, version, and source-to-feature lineage. Construct outcomes separately after the feature cutoff. | Mandatory | Milestone 3 produces a feature-ready panel, not feature values. An experiment cannot exist without a defined measurement, and features must not contain future outcomes. | S–M | High leakage, ambiguous exposure, or outcome contamination. | Complete before first pilot. Do not build a hundreds-feature engine yet. |
| M-18 | **Pass Stage 2.5 for every feature and exact generated view used.** Retain deterministic replay, point-in-time/leakage challenges, numerical and missingness tests, sensitivity, revision behaviour, version and lineage checks, scoped decision, reviewer, and conformance fingerprint. | Mandatory | A deterministic data panel does not prove that a derived feature is a valid measurement. | S–M | High measurement error propagated into every result. | Complete before first pilot for the selected feature only. |
| M-19 | **Freeze one minimal experiment-governance bundle before outcome access.** Record phenomenon family, scientific motivation, null/alternative, mechanism and competing mechanisms, falsification rule, population, feature, outcome, horizon, estimator, dependence handling, minimum relevant effect, effective-sample and dependence-aware power/precision assessment, equivalence/negligible region or an explicit rule that the planned design cannot support such inference, missingness, negative controls, search ancestry, multiplicity rule, discovery-budget caps, data exposure/holdout assignment, dependency decision, Research Cost estimate, ESIG assessment, software/data/feature versions, amendment rule, and all-result reporting obligation. Retain an audited scheduler-eligibility decision confirming that data, features, dependencies, budgets, cost, ESIG, evidence allocation, and protocol all pass immediately before execution. | Mandatory | This is the smallest control set that prevents outcome-driven choices, hidden search, underpowered overclaiming, holdout exhaustion, and selective reporting. The frozen Foundation requires these prospective records, but it does not require a database or scheduler service for one experiment. | S–M | Critical research drift, false discovery, false precision, and non-reproducible interpretation. | Complete before first pilot as content-addressed files with independent approval. Reserve untouched evidence for later validation. |
| M-20 | **Execute through one deterministic analysis routine and deposit complete evidence.** Retain commands, environment, exact inputs, outputs, failed checks, deviations, discovery-budget consumption, actual Research Cost, and a computational rerun. Preserve a null, contradiction, rejection, or data defect exactly as completely as a positive result. After adjudication, append the result to the Knowledge Base, create or update the continuous evidence-profile snapshot, and record the Phenomena Interaction Graph assessment, including an explicit `no edge proposed` or `not assessable` disposition when appropriate. | Mandatory | A first result is scientific only if it can be reconstructed, adverse findings cannot disappear, and the project’s permanent evidence record is updated rather than left as an orphan output. | S–M | High selective reporting, lost negative evidence, and irreproducibility. | Complete as part of the first pilot. Do not promote the result beyond exploratory-candidate status. |

### 4.1 Mandatory does not mean “build a platform”

For the first pilot, the Catalogue record, dependency decision, discovery budget,
Research Cost estimate, ESIG assessment, feature dossier, preregistration,
review, and evidence deposit may be small immutable files with hashes and named
reviewers. Their scientific content is Mandatory. Generic registry services,
scheduler automation, dashboards, and workflow engines are not.

---

## 5. Operationally Important work that must not delay one controlled pilot

| ID | Remaining blocker | Classification | Why it can wait | Effort | Scientific risk if postponed | Recommendation |
|---|---|---|---|---|---|---|
| I-01 | **Recover and deposit the canonical Milestone 1 Scientific Governance Specification and verified governing hash.** No canonical local file currently exists. | Important, conditionally Mandatory | Exact handbook traceability does not change the admitted data bytes or the prospective content of one pilot if an authoritative frozen version remains consultable and M-19 binds the operative controls directly to Foundation V1.1. The document must not be reconstructed from memory. | XS if the authoritative copy exists | Low direct pilot risk; medium governance-drift risk as studies multiply. | Complete before wider research and earlier if readily available. If no authoritative Milestone 1 text can be consulted at all, or it reveals an unfulfilled stricter gate, recovery/compliance becomes Mandatory before the pilot. |
| I-02 | **Full authenticated operating identities and durable role administration.** | Important | The first pilot requires a genuinely independent reviewer and content-bound decision, but one supervised run can use named actors and controlled local accounts. | S–M | Low for one supervised run; medium/high with repeated or multi-user operation. | Complete before wider or multi-user research. |
| I-03 | **Comprehensive OS role and ACL hardening beyond the minimum protected pilot register.** | Important | M-13 already requires the pilot register to be unwritable by ordinary build/analysis identities. Full durable separation across all configurations, services, users, and lifecycle operations primarily supports repeated multi-user operation. | S–M | Low beyond the M-13 minimum for one supervised run; grows with users and release frequency. | Complete before wider research. Do not weaken M-13 or the Mandatory read-only artifact handoff in M-15. |
| I-04 | **Automated external anchoring, recurring independent backups, and scheduled integrity checks.** | Important | M-13 already requires one independently held and integrity-checked pilot register backup/copy. Automation and recurring external anchoring protect a long-lived evidence history. | S initially; ongoing | Low beyond the one-pilot minimum; medium long-term audit and recovery risk. | Complete before wider research. Public signing or hardware attestation remains Future unless local protection proves inadequate. |
| I-05 | **Exclusive append coordination or protected append service.** | Important | The first pilot can enforce one serialized release authority. Concurrency control is needed only before concurrent writers are allowed. | S–M | None while serialized; high if multiple writers operate. | Complete before concurrent or wider research. |
| I-06 | **Exercise real correction, successor, supersession, revocation, and impact workflows.** | Important; conditionally Mandatory | The code has synthetic evidence and a fixed first snapshot can remain immutable. A correction during the pilot immediately makes this Mandatory. | S–M | Low for one unchanged snapshot; medium once corrections arrive. | Complete before wider research, or immediately if MDM corrects the pilot snapshot. Never mutate the predecessor. |
| I-07 | **Long-term runtime archival and environment migration proof.** | Important | M-12 retains the exact initial environment and proves immediate replay. Long-horizon environment preservation is an operational continuity concern. | S initially; ongoing | Low immediate; rising inability to replay years later. | Complete before wider research and scheduled revalidation. |
| I-08 | **General calendar-revision and boundary-changing identity/membership correction support.** | Important; conditionally Mandatory | Current code fails closed. It need not support a source pattern absent from the chosen snapshot. | M if activated | None when absent and rejected; high if silently accepted. | Implement only when the MDM contract or pilot data contains the pattern. |
| I-09 | **Point-in-time sector/industry, index membership, peer, and classification history.** | Important; Mandatory when used | A price/volume pilot can operate without these fields. | External/unknown | None if formally absent from scope; critical if approximated. | Complete before sector-, industry-, peer-, breadth-by-sector-, rotation-, sector-neutral-, or index-dependent research. Market-wide breadth using the admitted universe does not require sector history. |
| I-10 | **As-reported fundamentals, earnings/events, shares/float, quote/spread summaries, and point-in-time market-cap or liquidity eligibility.** | Important; Mandatory when used | The minimum pilot can avoid these constructs and avoid policy screens needing them. | External/unknown | None for the narrow pilot; critical for a dependent hypothesis. | Complete before the named research family. Do not substitute present-day values. |
| I-11 | **Additional currencies, exchanges, markets, ADR/linkage rules, and asynchronous-close policy.** | Important; Mandatory when included | A single-exchange, single-currency population avoids cross-market information and unit-comparability problems. | M–L / External | None if excluded; high if incomparable units or clocks are pooled. | Complete before scope expansion. |
| I-12 | **Complete return economics.** This includes complete cash distributions, action revisions/cancellations, terminal consideration, return reconciliation, and full economic normalisation of mergers, acquisitions, spin-offs, rights, and reorganisations where continuity is required. | Important for the raw-only pilot; Mandatory before any return-, gap-, trend-, momentum-, reversal-, or continuity-dependent study | The selected log-range feature uses coherent values within one row and M-08A prohibits all return use. | L / External | Low for the restricted raw-range estimand if incompatible rows are detected and missing states retained; critical if any return or cross-session price-level comparison is introduced. | Complete before the dependent research family. Full complex-action normalisation may still be replaced by prospective quarantine where the later estimand permits. |
| I-13 | **Full Stage 4 confirmation: walk-forward/rolling validation, broad cap/sector/regime transportability, transaction-cost and capacity descriptors, independent reimplementation, and direct replication.** | Important before wider claims; scientifically Mandatory before promotion | These determine whether a candidate persists, generalises, and might later be exploitable. They are not prerequisites to execute the first explicitly exploratory discovery study. | L and evidence-time dependent | The immediate pilot remains valid as exploration, but any claim of persistence or edge would be invalid. | Reserve untouched evidence now. Complete before calling a phenomenon validated, persistent, or exploitable. |
| I-14 | **Scalable governance and Knowledge Base operations.** Examples: registry databases, automated dependency traversal, budget manager, scheduler, continuous evidence dashboards, and interaction-graph tooling. | Important when manual control becomes unreliable | One experiment can be governed transparently with immutable records and a manual eligibility checklist. | M–L | Low at one-study scale; growing omission and consistency risk later. | Complete incrementally before experiment volume exceeds reliable manual review. |
| I-15 | **Performance benchmark, partition reuse, and incremental successor construction.** | Important when measured | Slow execution affects schedule, not the scientific estimand. The existing embedded daily path is intentionally bounded. | XS to measure; M if work is justified | Delay and storage cost only. | Benchmark the real build; optimise only if measured cost is material. |

---

## 6. Future enhancements and non-blockers

| ID | Item | Classification | Effort | Scientific risk if postponed | Recommendation |
|---|---|---|---|---|---|
| F-01 | Public-key signing, hardware-backed attestation, or enterprise ledger | Future | M–L | Negligible for one locally controlled pilot if mandatory hashes, review, serialization, and mutation-safe access exist | Defer. Activate only if local authority cannot be protected adequately. |
| F-02 | Distributed lakehouse, cluster execution, geographic replication, high availability, and cross-region failover | Future | L | None for bounded local science; operational delay only | Defer until measured scale or availability needs exist. |
| F-03 | Streaming, real-time ingestion, intraday bars, ticks, quotes, order books, auctions, and detailed halt reconstruction | Future | L / External | None for the daily pilot | Defer until an approved intraday or microstructure hypothesis requires them. |
| F-04 | Generic vendor adapters, multi-vendor reconciliation, query federation, arbitrary raw joins, and automatic schema migration | Future; alternate market-data sources remain prohibited | L | None; a generic layer would increase ambiguity | Defer. If needed, build only a bounded deterministic MDM-owned or MDM-lineaged exporter for the exact contract. |
| F-05 | Universal bitemporal query engine, lineage graph database, universal row/per-cell lineage, graphical catalogue, and monitoring UI | Future | L | None at pilot scale | Defer; current manifests and selected-record lineage are adequate. |
| F-06 | Machine-learning anomaly detection, automatic data repair, automatic descendant reruns, and automatic scientific reinterpretation | Future | L | None; automatic repair could reduce transparency | Defer. Continue to fail closed and retain explicit review decisions. |
| F-07 | Universal global legal-entity graph, exhaustive international investability, multi-jurisdiction calendars, and broad multi-asset schemas | Future | L / External | None for one bounded market | Defer until a registered scope requires them. |
| F-08 | Strategy optimisation, portfolio construction, broker/execution integration, positions, and live trading | Future and currently prohibited | L | None for phenomenon discovery; introducing them now would contaminate project scope | Do not implement during Stages 0–5. |

---

## 7. Current monolithic release-authority blocker

`config/production_release_authority.v1.json` currently combines several
controls into one `NOT_CONFIGURED` hard gate. Milestone 4 does not recommend
bypassing that gate or changing the Boolean without evidence. It recommends
distinguishing the minimum scientific control from later operational hardening.

### 7.1 Minimum control required for pilot one

- one exact approved production scope;
- one admitted content-addressed artifact;
- one builder and one genuinely independent reviewer;
- review evidence bound to the artifact, source, validation, and scope hashes;
- serialized release through the existing chained record, stored outside the
  ordinary build/analysis write path;
- one independently held backup or copy of the pilot release record with a
  verified integrity hash;
- access through the ordinary verifier; and
- mutation-safe consumption of the verified bytes by an analysis identity that
  cannot modify them during the run, with matching pre-run and post-run hashes.

These are covered by M-10 and M-13 to M-16.

### 7.2 Hardening that should follow

- full authenticated role administration;
- comprehensive OS ACL separation beyond the mandatory pilot register and
  artifact protection;
- automated external anchoring, recurring independent backups, and scheduled
  integrity checks beyond the mandatory one-pilot copy;
- exclusive concurrent append coordination;
- automated correction and impact workflows; and
- enterprise signing or ledger infrastructure if simpler local controls prove
  inadequate.

These are I-02 to I-06 and F-01. They should not remain bundled as an
all-or-nothing reason to delay one supervised, serialized pilot.

---

## 8. Traceability from the Milestone 3 blocker list

| Milestone 3 blocker group | Milestone 4 disposition |
|---|---|
| Conforming MDM snapshot, identity, lifecycle, universe, calendar, OHLCV, actions, terminal outcomes, and replay | M-02 to M-08 — identity, population, calendar, OHLCV coherence and replay are Mandatory; full return economics move to I-12 only for the M-08A raw-only pilot |
| Population and Time Contract | M-01 — Mandatory |
| Current implementation cannot admit raw observations without a valid return view | M-08A — Mandatory for the minimum fast route under frozen Milestone 2 Section 8.5 |
| Production policy code binding | M-09 — Mandatory |
| Ready capability audit and approved exact scope | M-10 — Mandatory |
| Real validation, population/missingness review, and independent replay | M-11 and M-12 — Mandatory |
| Independent review and release/reopen | M-13, M-14, and M-16 — Mandatory |
| Immutable/read-only storage and consumer read-boundary gap | M-15 — Mandatory in the smallest mutation-safe form |
| Missing canonical Milestone 1 file/hash | I-01 — Important traceability; functional per-experiment governance remains Mandatory under M-19 |
| Authenticated identities, protected register, external anchor, backup, and concurrent append control | M-13 — minimum protected pilot register and one independently held integrity-checked copy are Mandatory; I-02 to I-05 — comprehensive identity, anchoring, recurring backup, ACL, and concurrent-append hardening are Important before wider or concurrent research |
| Real correction/supersession/revocation exercises | I-06 — Important unless a correction occurs, then Mandatory |
| Calendar revision chains and boundary-changing corrections | M-08 contract check; I-08 implementation only if the real source requires it |
| Halt, suspension, no-trade, and unexplained absence semantics | M-08 and M-11 — Mandatory measurement and prospective disposition |
| Long-term runtime retention and scale | M-12 for immediate replay; I-07 and I-15 for continued operation |
| Stage 2 measurement, Stage 2.5 validation, and first experiment governance not implemented by Milestone 3 | M-17 to M-20 — Mandatory before actual phenomenon discovery |

No recorded Milestone 3 blocker is silently discarded. Items have been narrowed,
made conditional on the chosen scope, or reclassified according to whether they
can change the scientific result of one controlled pilot.

---

## 9. Minimum critical path

### Track A — decisions and MDM delivery

1. Select the narrow pilot envelope and ratify M-01.
2. MDM proves availability and publishes M-02 to M-07 as one bounded immutable
   raw-observation production snapshot.
3. Project EDGE completes the real contract check in M-08.

Tracks A1 and A2 should run in parallel where possible. If MDM does not possess
the required identity, survivor-population, calendar, row-coherence, or replay
evidence, there is no scientifically valid workaround within the authorised
boundary. The pilot must wait. Missing return economics are different only
because the chosen estimand does not use returns and M-08A mechanically
prohibits that use; another data source remains prohibited.

### Track B — existing data path activation

4. Implement the scoped raw-only admission and code-bind the policy and tests
   (M-08A and M-09).
5. Mark the capability evidence ready and approve the exact scope (M-10).
6. Build, validate, inspect coverage, and replay in a fresh process (M-11 and
   M-12).
7. Obtain independent review, issue the narrow release decision, and release
   and reopen through mutation-safe access (M-13 to M-16).

### Track C — one research measurement and experiment

8. Implement one frozen measurement and separate outcome (M-17).
9. Complete its Stage 2.5 dossier and exact-view conformance review (M-18).
10. Freeze the minimal governance and statistical protocol (M-19).
11. Execute deterministically and deposit all evidence (M-20).

Do not begin Track C outcome access until Tracks A and B have passed and the
Stage 2.5 and preregistration records are frozen.

---

## 10. Pilot release decision rule

The first real experiment may start only when all of the following are true:

1. the exact pilot population, clock, period, outcome horizon, and return basis
   were fixed before outcome inspection;
2. every market fact comes only from the authorised MDM snapshot;
3. identity, inactive/delisted population, calendar, coherent OHLCV, required
   action/lifecycle states, and replay are complete for the declared raw-only
   scope or prospectively quarantined without invalidating coverage;
4. every real-data Mandatory gate and applicable anti-bias sentinel passes;
5. the same inputs and environment reproduce the same artifact;
6. an independent reviewer approves evidence bound to the exact hashes;
7. the experiment reads the exact admitted bytes through mutation-safe access;
8. the exact feature and generated view pass Stage 2.5;
9. the hypothesis, statistical design, search limits, dependencies, exposure
   allocation, dependence-aware power/precision or not-inferable rule, Research
   Cost, ESIG, audited scheduler-eligibility decision, and reporting rule are
   frozen;
10. an untouched temporal allocation remains reserved for later validation;
11. every result and deviation will be retained regardless of direction, then
    deposited into the Knowledge Base with a continuous evidence-profile update
    and an explicit interaction-graph assessment; and
12. the study is described only as exploratory discovery, not as proof of a
   persistent or exploitable edge.

If any statement is false, the pilot remains blocked. A missing Important or
Future capability does not block the pilot unless the selected study uses it.

---

## 11. Final answer

### What is the minimum additional work required before Project EDGE can execute its first scientifically valid empirical phenomenon-discovery experiment using real MDM data?

Project EDGE must complete only these seven deliverables:

1. **One narrow ratified pilot contract:** one market/exchange, one currency,
   one explicit security population, daily cutoff, return basis, dates,
   coverage, and replay rights.
2. **One conforming real MDM snapshot:** scope-complete identity/lifecycle, a
   point-in-time survivor-accounted cohort, authoritative calendar, coherent
   raw OHLCV, action/lifecycle evidence sufficient to detect incompatible rows,
   one immutable version, and exact replay.
3. **One executable and approved data scope:** implement the frozen
   observed-price-only conditional admission, prohibit return use, code-bind the
   ratified policy, refresh the capability audit to ready for that exact use,
   and approve the exact source/request hash binding.
4. **One admitted reproducible dataset:** pass all real-data gates, stratified
   coverage and missingness review, action reconciliation, independent review,
   and a fresh-process identical rebuild.
5. **One safe release-to-read path:** protect the chained release record from
   ordinary build/analysis writes, retain and integrity-check one independently
   held copy, issue the narrow content-bound release, reopen it through the
   normal verifier, and ensure a non-writing analysis identity consumes the
   exact immutable/read-only bytes that were reviewed with matching pre-run and
   post-run hashes.
6. **One validated measurement:** implement only the pilot's exact feature and
   separate outcome, bind full lineage, and pass Stage 2.5 plus exact-view
   conformance.
7. **One frozen experiment and complete evidence record:** preregister the
   hypothesis, estimand, horizon, dependence-aware method, minimum effect,
   power/precision or explicit not-inferable rule, discovery budget,
   multiplicity, dependencies, holdout, Research Cost, ESIG, audited scheduler
   eligibility, and all-result reporting; then run deterministically, retain
   positive, null, contradictory, failed, and rejected outputs equally, and
   append the adjudicated result, continuous evidence-profile update, and
   interaction-graph assessment to the Knowledge Base.

The critical path is MDM delivery of identity, survivor-accounted population,
calendar, coherent raw OHLC, incompatible-row detection, and immutable-snapshot
evidence, followed by the small conditional-admission change. Complete cash-
distribution and terminal-return economics are not required for this one
raw-range estimand, but become Mandatory before any return, cross-session
price-level, or continuity comparison. Everything else should be implemented in
the smallest fixed form needed for that single pilot. Enterprise governance hardening, additional data
families, scale engineering, full validation/replication, and any trading
infrastructure must not delay the first exploratory scientific result.
