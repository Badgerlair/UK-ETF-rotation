# PROJECT EDGE

## IMPLEMENTATION MILESTONE 3 — MDM DATA FOUNDATION

### Implementation and Scientific Acceptance Report

**Report date:** 3 August 2026  
**Repository:** `D:\codex\equity_quant_research_platform`  
**Implementation status:** Mandatory mechanics implemented and accepted against fixed synthetic safety evidence  
**Production research status:** **BLOCKED — MILESTONE NOT YET SCIENTIFICALLY COMPLETE ON REAL MDM DATA**

---

## 1. Executive decision

Project EDGE now has the smallest complete implementation path capable of
reading a production-shaped MDM snapshot, reconstructing a point-in-time daily
equity population, resolving historical identities, treating ordinary
corporate actions and terminal outcomes, producing an outcome-free
feature-ready panel, producing a separate return-consistent view, validating
the result, and proving deterministic replay.

The implementation path passes its complete synthetic acceptance suite. The
synthetic fixture contains no empirical market evidence, exercises the same
strict Parquet boundary used by production, and is permanently classified
`TEST_ONLY_NON_PRODUCTION`. It cannot be used by a production request, cannot
be released as a production artifact, and cannot enter phenomenon discovery.

The milestone is **not complete in the production scientific sense defined by
the user**. The authorised Market Data Manager does not currently expose every
Mandatory source capability needed to create a real admissible Project EDGE
snapshot. In addition, the initial Population and Time Contract is unratified.
The protected release authority is also not configured. No empirical
feature-ready dataset has therefore been released, and no phenomenon-discovery
experiment is authorised to begin.

This is a successful scientific outcome for the current implementation slice:
the platform fails closed instead of converting incomplete data into apparent
evidence of an equity-market edge.

---

## 2. Scope and constitutional compliance

The implementation remained confined to the confirmed repository:

`D:\codex\equity_quant_research_platform`

The frozen Stage 0 Foundation Version 1.1 and frozen Milestone 2 MDM Data
Foundation Specification were read as governing requirements and were not
modified. Milestone 1 was treated as frozen and was not redesigned. However, no
canonical Milestone 1 Scientific Governance Specification file or governing
hash is present in this repository, so its local immutability and exact
traceability could not be independently verified. A canonical copy and hash
must be bound before production research; this report does not reconstruct it
from memory.

Only the authorised Market Data Manager was inspected as a possible empirical
market-data source. No source code, data, outputs, findings, or architecture was
imported from or made dependent upon:

- Project ICT (Forex);
- Futures Research Engine;
- Legacy Forex Research Engine;
- Universal Regime Engine;
- completed experiment outputs; or
- previous findings databases.

The Milestone 3 implementation under `src/edge_mdm`, its tests, and its retained
acceptance evidence contain no discovery engine, hypothesis test, parameter
optimiser, strategy, portfolio, broker, execution, or live-trading component.
Pre-existing or concurrent material under `research/` is outside this milestone
and was excluded from the M3 implementation, dependency path, test-evidence
bindings, and scientific claims. It was neither imported nor used as an input.

---

## 3. Implemented data path

The bounded implementation flow is:

`strict MDM manifest → verified read-only Parquet tables → scoped canonical rows → point-in-time identity and population → outcome-free security-day panel → separate return-consistent view → Mandatory validation → immediate pre-write revalidation → immutable candidate artifact → strict disk re-verification → independent source rebuild → release register`

The path uses Python 3.12 and the single pinned runtime dependency
`duckdb==1.5.3`. It is intentionally local, deterministic, and non-distributed.
There is no generic vendor adapter, service framework, workflow platform,
streaming layer, or speculative storage abstraction.

The source contract accepts exactly five Mandatory tables:

1. `identity_lifecycle`;
2. `exchange_sessions`;
3. `daily_observations`;
4. `corporate_actions`; and
5. `universe_membership`.

Every table has an exact column order and exact DuckDB physical types. Extra
fields are rejected, including fields that might smuggle targets or future
outcomes across the source boundary.

---

## 4. Component implementation reports

### 4.1 Authorised MDM snapshot reader

**Implemented functionality**

- Accepts only `source_authority = MDM`.
- Distinguishes `MDM_PRODUCTION_SNAPSHOT` from
  `TEST_ONLY_NON_PRODUCTION` at the manifest level.
- Requires explicit production authorisation status and scope identity.
- Requires a complete, replayable, immutable snapshot with a fixed snapshot
  ID, source version, consistency token, creation time, and common cutoff.
- Rejects mutable identifiers containing meanings such as current, latest,
  rolling, or head.
- Resolves every path beneath an explicitly supplied authorised MDM root.
- Rejects path traversal and resolved paths outside the authorised root or
  snapshot bundle.
- Accepts Parquet only.
- Verifies file SHA-256, exact physical schema, schema SHA-256, row count,
  deterministic sort keys, duplicate sort-key groups, logical row count, and
  logical SHA-256.
- Requires every row's `mdm_vintage_id` to equal the manifest snapshot ID.
- Rejects required null values and source rows whose availability exceeds the
  snapshot cutoff.
- Rechecks source bytes before every scan and after initial verification.
- Exposes a verified read-only handle rather than unrestricted source paths.
- Treats that handle as a convenience object rather than production authority:
  production build, approval, and access paths freshly verify the manifest and
  resolve all five tables again beneath the exact scope-bound authorised MDM
  root. Caller-supplied table paths are discarded.
- Rejects test data by default. Test data require an explicit opt-in and still
  retain `production_use_permitted = false`.

**Completed validation tests**

- valid strict Parquet snapshot verification;
- wrong physical hash;
- wrong row count;
- schema and unexpected outcome-column drift;
- physical type drift;
- mixed snapshot vintage;
- source and manifest mutation after verification;
- an adversarial forged verified-handle object whose observation path points to
  different Parquet, proving the production path rereads the genuine
  scope-bound MDM table instead;
- mutable snapshot identity;
- path escape;
- explicit test-only rejection; and
- read-only verified scans.

**Remaining Mandatory work**

- MDM must produce or expose a real snapshot satisfying this contract.
- The snapshot's authorisation scope must be bound to an independently approved
  Project EDGE production-scope record.
- MDM retention and exact replay permissions must be ratified.

**Known limitations**

- The reader deliberately has no compatibility adapter for the MDM's present
  heterogeneous files. Quiet inference would weaken the scientific contract.
- It reads one bounded snapshot, not incremental or streaming updates.

**Deferred items and justification**

- Generic vendor adapters, distributed ingestion, streaming, and automatic
  schema migration are deferred because they do not help determine whether a
  persistent equity phenomenon exists in the first research year.

### 4.2 Historical security identity

**Implemented functionality**

- Uses stable security, issuer, and listing identities rather than ticker as a
  key.
- Resolves ticker and lifecycle history through half-open effective intervals
  and availability cutoffs.
- Supports ticker change and later ticker reuse by a different security.
- Detects overlapping listing identities, ambiguous ticker ownership,
  malformed intervals, missing identity fields, invalid publication clocks,
  duplicate source records, and failed quality states.
- Supports exact-interval identity corrections when revisions have distinct
  information-availability times; equal-time ambiguity still fails closed.
- Enforces the first-slice lifecycle vocabulary (`ACTIVE`, `HALTED`,
  `SUSPENDED`, and `DELISTED`) and rejects unknown or misspelled states.
- Requires a stable listing ID to retain one security ID and one currency
  throughout the bounded slice; listing-to-security or listing-currency drift
  fails closed instead of joining incompatible histories.
- Retains and rejects a requested-universe member whose listing identity cannot
  be resolved, rather than filtering that member out before admission.
- Carries the exact selected identity source record into panel lineage.
- Applies primary-listing, security-type, and currency restrictions through the
  frozen request rather than present-day security-master values.

**Completed validation tests**

- `ARC` resolves to security S1 before its ticker change;
- S1 resolves as `NOVA` after the change;
- `ARC` resolves to newly listed security S2 after reuse;
- deliberately ambiguous overlapping ticker ownership fails;
- unknown lifecycle state and unresolved requested-universe identity fail;
- listing-to-security drift and listing-currency drift fail closed;
- pre-listing, active, delisted, and post-delisting states are reconstructed;
  and
- future or unavailable identity rows are not selected.

**Remaining Mandatory work**

- MDM must supply a complete adjudicated security/issuer/listing history,
  including inactive, acquired, bankrupt, relisted, venue-changed, and delisted
  listings.
- MDM must provide reliable successor/predecessor and ticker-reuse history.
- The real multiple-share-class and unit-of-analysis policy must be ratified.

**Known limitations**

- Exact-interval identity revisions are supported, but a complete MDM
  correction model has not yet been demonstrated. More complex corrections
  that change effective interval boundaries remain fail-closed until MDM
  supplies an authoritative precedence contract.
- Concurrent primary listings fail closed rather than being resolved by an
  inferred venue preference.

**Deferred items and justification**

- A universal legal-entity graph is deferred. Stable issuer/security/listing
  identity is sufficient for the bounded first daily programme.

### 4.3 Trading-session and cutoff spine

**Implemented functionality**

- Uses exchange-specific session identities, dates, timezones, opens, closes,
  post-close research cutoffs, early-close flags, and previous/next trading
  sessions.
- Distinguishes regular sessions, early closes, holidays, and closed dates.
- Validates timestamp ordering, non-overlap, timezone presence, internal
  previous/next links, quality state, and whether the calendar was knowable by
  the session.
- Executes only the code-bound first-slice policy bundle and enforces the
  `CAL-TEST-001` five-minute post-close cutoff exactly. A caller-supplied policy
  label cannot create new timing semantics.
- Provides deterministic session shifts and timestamp-to-session mapping.
- Requires an explicit exchange when more than one calendar is present.

**Completed validation tests**

- United States daylight-saving transition;
- holiday exclusion;
- early-close cutoff;
- prior/next trading-session offsets;
- post-close timestamps mapping to the next session;
- observations on a non-session failing admission; and
- a bar with no revision available by the approved cutoff failing admission;
  and
- a later retained correction remaining invisible at the earlier cutoff while
  its original available revision is selected;
- an arbitrary calendar-policy identifier being rejected before execution; and
- a cutoff inconsistent with the frozen five-minute rule failing admission.

**Remaining Mandatory work**

- MDM must supply an authoritative equity calendar with historical holidays,
  early closes, timezone rules, unscheduled closures, and approved research
  cutoffs.
- The real exchange and observation-clock policy must be ratified.
- After ratification, the exact production policy identifiers and semantics must
  be explicitly code-bound and pass the timing-policy sentinels. The current
  executable allowlist contains only the frozen synthetic test bundle and
  deliberately rejects every other bundle.

**Known limitations**

- The current implementation supports the daily post-close clock only.
- After-hours event assignment is not implemented because event research is not
  in the first slice.

**Deferred items and justification**

- Intraday sessions, auctions, detailed halts, and quote clocks are deferred
  until an approved intraday or microstructure hypothesis requires them.

### 4.4 Point-in-time historical equity universe

**Implemented functionality**

- Constructs an explicit assessment for every stable in-scope listing and
  trading session, including securities without observations.
- Derives the candidate population from identity and lifecycle records, never
  from the set of securities that have bars.
- Applies exactly one requested universe ID.
- Applies point-in-time membership only when both effective and available by the
  session cutoff.
- Applies explicit primary-listing, security-type, and currency rules.
- Preserves pre-listing, active, halted, suspended, inactive, first-terminal,
  and post-delisting states.
- Retains a terminal-settlement candidate row even when no bar exists.
- Records candidate and eligible flags, every exclusion reason, selected
  identity lineage, selected membership lineage, and deterministic population
  counts.

**Completed validation tests**

The fixed safety population produces:

- 18 security-session assessments;
- 14 candidate rows;
- 13 eligible rows;
- 1 candidate-ineligible terminal row;
- 4 non-candidate rows;
- 3 securities; and
- 6 trading sessions.

Tests also cover listing entry, ticker reuse, delisting, missing terminal data,
multiple universe contamination prevention, ambiguous identity, duplicate
universe keys, unresolved requested-universe listing identity, unknown
lifecycle state, and explicit exclusions.

**Remaining Mandatory work**

- MDM's historical population export must be completed, reviewed, unlocked,
  and authorised.
- Coverage of inactive, distressed, acquired, bankrupt, delisted, and relisted
  securities must be measured on real data.
- Population thresholds and all listing/share-class decisions must be ratified.

**Known limitations**

- The unratified production contract means no actual market, exchange, or
  security population has been selected.
- The initial implementation is intentionally conservative: unresolved
  identity or membership cannot be replaced with a current value.

**Deferred items and justification**

- Point-in-time sector, industry, index, and peer membership are unavailable
  and disabled. They become Mandatory before any dependent research family,
  but they are not required for an initial price-path-only pilot.

### 4.5 Corporate actions and return-consistent view

**Implemented functionality**

- Preserves raw unadjusted OHLCV unchanged.
- Maintains a separate action ledger and separate return-consistent view.
- Supports split/consolidation ratios, ordinary cash distributions, and
  terminal delisting consideration.
- Selects the latest action revision available by each row cutoff.
- Does not reveal the existence of a future action or later cancellation in an
  earlier observable row.
- Handles action revisions that change an ex-date by selecting the record before
  matching its effective session.
- Retains all revisions for each in-scope listing before point-in-time
  selection, so an out-of-range correction cannot resurrect an obsolete
  in-range action.
- Retains a same-effective-date revision learned after the historical cutoff
  without invalidating the earlier revision that was actually knowable then.
- Rejects a revision chain that changes listing identity, preventing one action
  from being applied independently to both the old and corrected listing.
- Ignores cancelled/reversed actions only after their cancellation state is
  knowable.
- Detects unsupported merger, acquisition, spin-off, rights, and reorganisation
  actions and marks continuity as broken instead of inventing economics.
- Requires valid information clocks, exact ex/effective dates, action status,
  timestamp precision, currency where applicable, positive split factors,
  non-negative cash amounts, and exactly one terminal outcome.
- Requires cash-distribution and terminal-consideration currency to match the
  governed listing currency; mismatches are quarantined because point-in-time
  FX conversion is not part of this slice.
- Requires a terminal action to coincide with the `DELISTED` lifecycle and the
  frozen terminal-no-bar convention. An ordinary bar, a non-delisted state, or
  a compound split/distribution on the terminal session is quarantined.
- Does not label a multi-session return as one-day: a prior close must belong to
  the immediately previous governed session.
- Breaks and quarantines return continuity if the current and previous listing
  currency differ; no unapproved point-in-time FX conversion is inferred.
- Separates raw close return, split-consistent price return, distribution
  return, total return, terminal return, comparable volume, action lineage,
  return quality, missing reason, and continuity state.

**Completed validation tests**

- A 2-for-1 split produces a raw close return of `-0.490000000000`, a
  split-consistent price return of `0.020000000000`, and comparable volume of
  `1100.000000000000`.
- A $1 cash distribution produces price return
  `-0.019230769231`, distribution return `0.019230769231`, and total return
  `0.000000000000`.
- A terminal value of $2 after a $10 previous close produces terminal and total
  return `-0.800000000000`.
- Missing terminal consideration fails admission.
- An action not available by its effective-session cutoff fails admission.
- An in-range active split superseded before cutoff by an out-of-range
  cancellation is not applied.
- A cash-action currency mismatch fails admission.
- A later same-date action revision is retained but does not rewrite the
  historical action selected at the earlier cutoff.
- Action listing drift, a null required cash amount, terminal/bar conflict,
  compound terminal actions, and unsupported complex actions all fail at typed
  boundaries.
- Listing-currency drift produces an explicit cross-currency continuity break
  rather than a return computed across unlike units.
- A later daily-bar revision available by cutoff is selected, an unavailable
  future revision is retained but not joined, and equal-time ambiguity fails
  closed.
- Unsupported continuity is quarantined rather than normalised speculatively.

**Remaining Mandatory work**

- MDM must supply complete cash distributions, delistings, terminal outcomes,
  action cancellations/revisions, and detection of complex reorganisations.
- Real action-window reconciliation and coverage tests must pass across the
  selected market history.

**Known limitations**

- Full merger, acquisition, spin-off, rights, and reorganisation economics are
  not implemented. The first slice detects and quarantines them, as permitted
  by the frozen Milestone 2 specification.
- Longer-horizon lookback composition is not part of this milestone. The
  return view supplies a continuity-break field that later feature generation
  must respect.

**Deferred items and justification**

- Full complex-action economic normalisation is deferred until a research scope
  needs continuity across those events. It must be activated before such a
  scope is admitted.

### 4.6 Outcome-free feature-ready security-day panel

**Implemented functionality**

- Emits one deterministic row for every candidate security-session, not only
  surviving observations.
- Includes stable identity, session and cutoff, lifecycle, population status,
  point-in-time action state, raw OHLCV, price basis, typed missingness, quality,
  and exact row lineage.
- Retains a terminal row with typed null OHLCV instead of silently truncating the
  security.
- Retains halted and suspended candidates without bars using typed
  `HALTED_NO_BAR` and `SUSPENDED_NO_BAR` states, and breaks return continuity so
  resumed trading is not labelled a one-session return across the absence.
- Uses a frozen exact output schema and column order.
- Rejects arbitrary requested fields in the first implementation.
- Enforces immutable field roles and rejects outcome, target, label, signal,
  strategy, future, and unknown fields even if an alias attempts to disguise
  them.
- Keeps returns in a separate artifact. No forward return or label appears in
  the observable panel.

**Completed validation tests**

- 14 candidate panel rows with 13 matched raw bars and one typed terminal row;
- zero multiple-match rows;
- exact schema and ordering;
- full OHLCV consistency;
- typed nulls and missing reasons;
- governed halt missingness and post-halt continuity breaks;
- row-level identity, membership, action, and observation lineage;
- outcome-field and alias-resistance sentinels; and
- unexpected source outcome-column rejection.

**Remaining Mandatory work**

- A real feature-ready panel cannot be created until a conforming MDM snapshot
  passes every upstream gate.
- Real field coverage and concentrated missingness must be measured across the
  candidate and eligible populations.

**Known limitations**

- Halted and suspended no-bar rows are admitted only when the point-in-time
  lifecycle record supplies that state. Other non-terminal source absences
  remain hard failures; they cannot be reclassified as halts by inference.
- The real MDM lifecycle and coverage semantics must demonstrate that a missing
  bar and an authoritative halt/suspension are consistently distinguishable.
- No feature values are calculated. This is a feature-ready data panel, not the
  Stage 2 Feature Generation Engine.

**Deferred items and justification**

- Fundamentals, earnings, events, index membership, sector/industry context,
  and peer groups are disabled until MDM provides admitted point-in-time
  histories and a selected hypothesis requires them.

### 4.7 Mandatory admissibility

**Implemented functionality**

Admission is derived from typed evidence. A caller cannot create a release
certificate by merely passing booleans that claim the source, lineage, outcome
firewall, or replay checks succeeded.

Admission recomputes the scoped source, universe, observable-panel, and return
fingerprints from the exact rows being assessed. It binds them to the verified
source-table hashes, source manifest, lineage, software source hash, and replay
fingerprints. Materialisation repeats the full validation immediately before
writing, preventing mutation of a previously validated in-memory build from
being published under stale evidence.

The implemented report contains fourteen fail-closed Mandatory gates:

1. `AUTHORISED_MDM_SOURCE`;
2. `SNAPSHOT_INTEGRITY`;
3. `REQUIRED_SCHEMA`;
4. `STABLE_IDENTITY`;
5. `TRADING_CALENDAR`;
6. `DAILY_OBSERVATIONS`;
7. `POINT_IN_TIME_AVAILABILITY`;
8. `CORPORATE_ACTIONS`;
9. `HISTORICAL_UNIVERSE`;
10. `FEATURE_READY_KEYS`;
11. `TYPED_MISSINGNESS`;
12. `OUTCOME_FIREWALL`;
13. `LINEAGE`; and
14. `DETERMINISTIC_REPLAY`.

Each gate records status, severity, error count, typed error codes, and bounded
sample evidence. Every listed gate is a hard blocker. In particular, corrupt
daily observations cannot coexist with an `ADMISSIBLE` decision.

**Completed validation tests**

- all fourteen gates pass on the strict synthetic acceptance snapshot;
- future bars, non-session bars, duplicate bars, ambiguous identity, missing
  terminal outcome, late action availability, schema drift, mixed vintage, and
  outcome fields all fail at a typed boundary;
- mutable snapshot aliases, path escape, physical type drift, source/manifest
  mutation after verification, unknown lifecycle, orphan universe membership,
  terminal conflicts, and arbitrary cutoff policy also fail closed;
- an invalid build cannot be materialised; and
- a valid build mutated after admission cannot be materialised;
- caller-created production-scope assertions cannot override the canonical
  blocked capability, population, scope-status, and release-authority records;
- caller-created verified source handles cannot redirect a production build,
  approval, or access check away from the scope-bound authorised MDM root;
- a production scope binds its ID to an exact content hash and binds the exact
  source root, manifest hash, source version, consistency token, snapshot, and
  complete request/policy hash; and
- CLI build failures can be retained as immutable typed attempt evidence
  without retaining unsafe data.

**Remaining Mandatory work**

- Run the gates on the first real MDM snapshot.
- Ratify real population, coverage, missingness, and action-reconciliation
  thresholds before inspecting research outcomes.
- Perform independent review of the production validation evidence.

**Known limitations**

- Synthetic acceptance proves control behavior, not the empirical completeness
  or correctness of MDM's real history.

**Deferred items and justification**

- Statistical anomaly detection and automatic repair are deferred. Automatic
  repair would obscure scientific provenance and is not required for the first
  deterministic release.

### 4.8 Versioning, lineage, snapshot lifecycle, and release control

**Implemented functionality**

- Binds source snapshot ID, source manifest hash, source table logical hashes,
  request ID, all policy versions, pipeline version, exact Python-source hash,
  output logical hashes, and environment versions.
- Records field-level lineage for every observable-panel field.
- Carries exact selected source record IDs at row level.
- Produces immutable Parquet artifacts for historical universe, observable
  panel, and return-consistent view.
- Produces immutable JSON request, lineage, validation, join-audit, and artifact
  manifests.
- Rereads every materialised Parquet file, enforces its exact schema and type
  order, and records a separately recomputable materialised logical profile.
- Refuses to overwrite an existing content-derived artifact ID.
- Requires a production-authorised MDM snapshot, a separately approved
  production scope, a ratified population/time contract, a ready capability
  gate, a protected release authority, and an admissible validation report
  before an artifact can even become ready for production review.
- Requires the canonical approved-scope register to bind approval ID to the
  exact scope-content SHA-256; reusing an approved ID with broader content does
  not open the gate.
- Requires the reviewer to differ from the builder.
- Rejects caller-constructed artifacts unless the manifest has the exact
  contract, the exact seven-file payload is present, every JSON evidence record
  is internally consistent, every Parquet schema/row count/logical hash is
  recomputed, and the content-derived artifact ID is reproduced.
- Requires the verified production MDM handle and exact scope again at release,
  freshly verifies the source manifest and tables beneath the scope-bound MDM
  root, then independently rebuilds the requested slice and compares
  fingerprints, lineage, validation, join audit, population, artifact identity,
  and independently rematerialised Parquet logical profiles before appending a
  release record.
- Appends a SHA-256-chained release record.
- Detects reuse of one source snapshot ID with different source-manifest
  content.
- Rechecks artifact-manifest and artifact-file bytes at access time, then repeats
  the independent source rebuild and actual Parquet/profile comparison before
  granting access.
- Supports append-only `REVOKED` and `SUPERSEDED` transitions. A revoked or
  superseded artifact immediately fails the ordinary access check.
- Keeps test-only artifacts permanently outside the production release path.

**Completed validation tests**

- immutable candidate materialisation;
- test-only release rejection;
- arbitrary text named as Parquet with self-asserted production flags is
  rejected before any register entry;
- post-validation row mutation is rejected;
- chained governance-record integrity and append-only revocation;
- byte-tamper detection;
- exact materialised schema, file-set, support-evidence, and logical-profile
  verification;
- schema-conforming Parquet row tampering rejected by the independent rebuild;
- canonical approval-ID-to-scope-hash enforcement and individual source/request
  binding drift rejection;
- adversarial caller-supplied source-handle path substitution rejected through
  fresh production source verification; and
- canonical production-gate enforcement despite a caller-created scope object.

**Remaining Mandatory work**

- Configure operating-system permissions so the production release register
  and release authority are protected from ordinary build and research writers.
- Replace string-only builder/reviewer identities with authenticated operating
  identities and bind review evidence to an immutable reviewed artifact before
  the first production release.
- Add exclusive append coordination or a protected append service before
  concurrent release authorities are permitted.
- Complete an independent review using a real production snapshot.
- Exercise correction, successor-snapshot, impact, supersession, and revocation
  operations on real retained artifacts.
- Back up and independently integrity-check the production register.
- Put released artifacts in immutable or read-only protected storage and bind
  each experiment read to a freshly verified access handle. The current access
  check cannot by itself prevent mutation after it returns and before an
  ungoverned downstream reader opens a path.

**Known limitations**

- Code can enforce logical role separation but cannot create independent human
  authority or filesystem access control by itself. Production remains blocked
  until those operational controls exist.
- The SHA-256 chain detects accidental or partial tampering but is not an
  external trust anchor: a principal able to rewrite the entire register can
  recompute the chain. Protected storage, independent backups, and periodic
  external anchoring remain Mandatory for production.
- No production release has been attempted or claimed.
- No consumer read handle is claimed complete; protected artifact storage and
  read-boundary verification are production-activation requirements.

**Deferred items and justification**

- Public-key signing, hardware-backed attestation, an enterprise ledger, and a
  lineage graph database are deferred. They are unnecessary if protected local
  authority and the chained register prove adequate.

### 4.9 Deterministic reproducibility

**Implemented functionality**

- Sets DuckDB execution to one thread and UTC for governed reads and writes.
- Uses exact sort keys for every source table and output.
- Uses canonical JSON encodings for strings, integers, booleans, decimals,
  dates, timestamps, bytes, paths, enums, and dataclasses.
- Separately fingerprints physical files, physical schemas, logical source
  rows, logical output rows, materialised Parquet logical rows, and exact Python
  source code.
- Rebuilds the complete transform from reversed input order and compares every
  output fingerprint before admission.
- Runs a separate acceptance test in two fresh Python interpreter processes.

**Completed validation tests**

Two fresh processes produced identical:

- universe logical fingerprint;
- observable-panel logical fingerprint;
- return-view logical fingerprint;
- replay fingerprints;
- content-derived artifact ID; and
- physical artifact file hashes.

The fixed logical fingerprints are:

- universe: `7df2850c865399b42d2ab932ab873b60cda513866f920d09b797f0194eeaa5bc`;
- observable panel: `ed8b93a00ac9ebf1bcf2528b5bc9cc517c5c33ad38919d8829cfc4182c84c4da`;
- return-consistent view: `f8d9f67e4b3e979e7a6ecab1e13aad1dc89221465ec7032db7405cea905b38e7`.

**Remaining Mandatory work**

- Repeat the proof on the actual retained MDM snapshot and production runtime.
- Retain the exact production dependency environment and verify long-term MDM
  replay.

**Known limitations**

- Exact replay of real empirical data cannot be demonstrated until MDM provides
  an immutable retrievable snapshot.

**Deferred items and justification**

- Distributed deterministic execution is deferred because the local embedded
  path is adequate for the first bounded daily slice and is easier to audit.

---

## 5. Acceptance evidence

The final retained automated result is:

`79 passed, 0 failed, 0 errors, 0 skipped`

The suite covers structural intake, scientific transformations, anti-bias
sentinels, action arithmetic, deterministic replay, immutable artifact
materialisation, release governance, source-handle substitution resistance,
identity and currency continuity, and fresh-process reproducibility.

The content-addressed machine-readable test-evidence record is:

`evidence/milestone3/EDGE-M3-PYTEST-D8958518BCA763637BB5874DC082A89100F8A3FB9F878C4D09950BB6166CD69B/manifest.json`

Its manifest SHA-256 is
`e70ffb4035a553cebb5f57a541c364fe6b3b7299506997a83d13e3ef1566672b`.
It retains the exact collected node IDs, commands, environment, stdout, stderr,
JUnit results, source/test/config/tool hashes, and output-file hashes. The run
was completed by exclusive atomic directory creation and the evidence builder
refuses to overwrite an existing evidence ID.

The retained synthetic acceptance bundle contains:

- a strict test-only MDM-shaped source snapshot;
- exact source manifest and table fingerprints;
- historical universe Parquet;
- outcome-free observable panel Parquet;
- separate return-consistent view Parquet;
- request manifest;
- join audit;
- field and dataset lineage;
- Mandatory validation report; and
- artifact manifest.

Its governing classification is:

- `TEST_ONLY_NON_PRODUCTION`;
- `contains_empirical_market_data = false`; and
- `production_use_permitted = false`.

The exact retained evidence paths and current artifact hash are recorded in:

`artifacts/milestone3/synthetic_acceptance/acceptance_summary.json`

The retained acceptance artifact is
`EDGE-32B7CDC6C0F050309F5BC907`; its manifest SHA-256 is
`a0a0c176af39345b678be0c2a29616c8246b8a789512fe3120e88a59dbdba453`.
Its exact Python-source fingerprint is
`e0ad6a3b219de0734a9a083c0bd82b0a3e6a09df1f741c8444fc9ab9e7990d07`.

The previous non-production acceptance artifacts
`EDGE-18BD7AA13250B76707379551` and
`EDGE-56BBC9C4D9E1A12EE4BB111C` are retained under
`artifacts/milestone3/superseded_synthetic_acceptance/` with an explicit
supersession chain. They are not current evidence.

---

## 6. Actual MDM capability result

The MDM audit was read-only. The observed MDM repository was clean at commit:

`e7c9b63b2a05b7b356bc3af044ed756b4acf57a7`

Observed useful data include a large local daily equity aggregate history and
monthly point-in-time reference snapshots. Those resources are not sufficient
for a scientifically complete Project EDGE release.

The production gate is blocked for the following reasons:

1. **No complete stable identity history.** There is no adjudicated stable
   security/listing identity, complete ticker-reuse history, or complete
   successor/predecessor chain suitable for the required contract.
2. **No authoritative equity calendar.** The audited MDM state does not supply
   a complete equity session spine with historical timezones, holidays, early
   closes, and Project EDGE cutoffs.
3. **Corporate actions are incomplete.** Split data exist, but complete cash
   distributions, terminal outcomes, delisting economics, and complete
   revision/cancellation support are absent.
4. **The historical universe is not approved.** The available monthly export is
   explicitly partial/review-required and locked pending approval.
5. **No atomic immutable MDM snapshot.** There is no single cross-dataset
   snapshot ID, common consistency token, source checksum manifest, correction
   lineage, and guaranteed exact replay mechanism.
6. **Raw-basis and temporal declarations are incomplete.** The daily files do
   not carry the complete row-level contract required to prove raw versus
   adjusted basis and common snapshot provenance.
7. **Sector proxy use is prohibited.** The available proxy is connected to prior
   research and is not imported into this independent project. Sector-dependent
   research remains blocked.

The machine-readable evidence is retained in:

`config/mdm_capability_audit.v1.json`

The result is intentionally `production_gate = BLOCKED`.

---

## 7. Remaining Mandatory work

The following work must be completed before the milestone's production exit
criterion can be satisfied.

### 7.1 MDM must publish a conforming authorised snapshot

MDM must supply the five exact Mandatory data families with:

- complete stable security, issuer, listing, ticker, share-class, venue, and
  lifecycle history;
- complete inactive, distressed, acquired, bankrupt, relisted, and delisted
  coverage;
- an authoritative equity calendar and research cutoffs;
- raw unadjusted daily OHLCV with explicit basis, units, status, availability,
  and quality;
- splits, cash distributions, action revisions/cancellations, detected complex
  actions, and terminal consideration;
- an approved survivor-complete historical universe;
- one immutable snapshot identity and common consistency token;
- source and logical fingerprints;
- exact retained replay or an immutable retrievable reference; and
- authorised retention/licensing terms.

### 7.2 Project EDGE must ratify the Population and Time Contract

The currently unratified decisions include:

- first market and exchanges;
- eligible security types;
- primary/secondary listing rules;
- security versus issuer analysis unit;
- multiple-share-class treatment;
- IPO, suspension, relisting, acquisition, bankruptcy, and delisting rules;
- currency policy;
- exchange research cutoff;
- raw, price-return, and total-return conventions;
- research start and minimum coverage; and
- MDM retention and replay permissions.

Until ratification, code defaults must not silently become scientific policy.
Ratification alone will not make the policy executable. The exact approved
production identifiers and semantics must then be added to the code-bound
allowlist and pass the Mandatory policy and timing tests; the present
implementation accepts only the synthetic test bundle.

### 7.3 Production admission must be executed independently

- Create an approved production-scope record referencing a ready capability
  audit and ratified Population and Time Contract.
- Build the real bounded snapshot.
- Run all Mandatory validation and anti-bias sentinels.
- Perform population and missingness review, especially among small, inactive,
  distressed, acquired, bankrupt, and delisted securities.
- Perform an independent reviewer sign-off distinct from the builder.
- Configure authenticated builder, reviewer, and release-authority identities.
- Deposit or bind the canonical frozen Milestone 1 Scientific Governance
  Specification and its independently verified hash. No such local artefact is
  currently available, so exact governance-document traceability is incomplete.
- Protect, externally anchor, and back up the canonical append-only release
  register; `config/production_release_authority.v1.json` intentionally remains
  `NOT_CONFIGURED` until that control exists.
- Put production artifacts in immutable or locked read-only storage and bind
  downstream consumption to a verified handle that prevents mutation between
  access verification and the actual read.
- Release and re-open the artifact through the ordinary access verifier.
- Repeat the build in a fresh production process and compare logical and
  physical fingerprints.

### 7.4 Resolve contracts exposed only by a real revision-bearing snapshot

- Confirm whether MDM publishes a single canonical point-in-time calendar row
  per exchange-session or a retained calendar revision chain. The current slice
  admits the former and fails closed on duplicate session rows; a governed
  revision selector must be added if MDM supplies the latter.
- Exercise identity and membership corrections whose effective boundaries
  change, rather than only exact-interval revisions, and implement additional
  precedence only from an authoritative MDM contract.
- Measure halted, suspended, no-trade, and unexplained-absence states on real
  data and ratify their state-dependent admissibility rules.
- Bind production-scope approval and independent review evidence to protected,
  content-addressed records with authenticated actors. Repository JSON and
  arbitrary identity strings are not sufficient production authority.

Only after these steps pass may the first empirical feature-ready dataset be
declared ready for Stage 2 Feature Generation.

---

## 8. Known scientific risks and omissions

### 8.1 False edge caused by population incompleteness

Missing delisted, bankrupt, acquired, inactive, or distressed securities can
create an apparently persistent positive effect. This is the most serious
current risk and is why the historical-universe gate remains closed.

### 8.2 False return effects caused by incomplete actions

Missing distributions, split corrections, or terminal outcomes can convert
corporate mechanics into apparent momentum, reversal, volatility, or gap
phenomena. Real return-based research is blocked until action coverage is
complete.

### 8.3 Calendar approximation

Weekday approximations can misalign lags, gaps, and event windows. The
implementation refuses such approximations; the resulting risk is schedule
delay rather than biased science.

### 8.4 Unratified population choices

Listing, share-class, currency, and cutoff decisions materially change the
estimand. Selecting them during or after outcome inspection would introduce
researcher degrees of freedom. They must be ratified first.

### 8.5 Synthetic evidence is not empirical validation

The fixture proves that controls behave correctly for known sentinels. It does
not prove MDM coverage, vendor correctness, real corporate-action completeness,
or economic validity.

### 8.6 Conservative missingness policy

Authoritatively halted or suspended candidates may carry typed no-bar rows and
must break return continuity. Every other non-terminal source absence still
fails the slice. Any broader relaxation must be preregistered, retain
denominators, preserve lifecycle states, and be validated for concentration in
weak or distressed stocks.

### 8.7 Operational authority

Source and artifact hashes do not protect against an operator who can rewrite
both data and the release register. String inequality does not authenticate a
reviewer. Protected filesystem roles, authenticated independent review,
exclusive append coordination, backups, and an external integrity anchor remain
Mandatory production controls.

### 8.8 Scale

The embedded implementation is appropriate for a bounded daily slice, but it
has not been performance-tested against the full MDM history because the
required canonical snapshot does not yet exist. Partitioning or incremental
construction should be introduced only after measurement demonstrates need.

---

## 9. Explicit deferrals

The following are safely deferred and must remain unavailable rather than
approximated:

- sector, industry, peer, and rotation context until point-in-time histories are
  admitted;
- index membership and weights until an index-dependent hypothesis is approved;
- fundamentals and as-reported revisions until fundamental research is
  approved;
- earnings and other event histories until event research is approved;
- full complex-reorganisation economics until continuity across such events is
  required;
- intraday bars, quotes, ticks, order books, auction phases, and detailed halt
  reconstruction;
- multi-currency conversion;
- distributed storage and compute;
- streaming and live data;
- generic temporal query languages;
- automatic data repair;
- broker, execution, portfolio, and live-trading infrastructure; and
- all strategy construction and optimisation.

Each deferred capability has a fail-closed activation boundary. No current
value, weekday approximation, prior-project proxy, alternate vendor, or analyst
guess may substitute for it.

---

## 10. Advancement of the ultimate objective

The commercial objective is to determine whether a genuine persistent
exploitable equity-market edge exists. This milestone advances that objective
by attacking the largest class of false positives before any phenomenon is
tested.

The implemented platform prevents a supposed edge from being manufactured by:

- current-survivor selection;
- ticker drift or ticker reuse;
- future universe membership;
- future action knowledge;
- adjusted/raw basis confusion;
- unaccounted splits or distributions;
- missing terminal returns;
- holiday or early-close misalignment;
- duplicate or arbitrary joins;
- future targets crossing the feature boundary;
- mutable source extracts; or
- irreproducible row order and software state.

This makes a later positive result more credible. It also makes a negative
result more informative because absence of an effect cannot be dismissed as an
unreproducible dataset accident.

Within the Milestone 3 implementation and its retained acceptance evidence, no
result has been optimised or interpreted to force a profitable conclusion. The
M3 pipeline has not tested an empirical market hypothesis.

---

## 11. Final milestone assessment

### Implementation assessment

**Sufficiently complete to attempt a bounded canonical MDM intake and expose
remaining real-data defects:** Yes.

The bounded source contract, deterministic transformation, feature-ready
artifacts, validation, lineage, failure evidence, and release controls are
implemented and pass synthetic acceptance. This is not a declaration that an
unknown future MDM revision model is already supported; the first real intake
must resolve the remaining items in Section 7.4 without weakening any gate.

### Scientific production assessment

**Sufficiently complete to begin the first empirical phenomenon-discovery
experiment:** No.

The user-defined completion condition requires a real point-in-time-correct,
fully reproducible, scientifically trustworthy feature-ready dataset. The
authorised MDM does not currently satisfy the Mandatory input contract, the
Population and Time Contract is unratified, and production release authority is
not operationally protected and reviewed. Protected immutable artifact storage
and a mutation-safe consumer read boundary are also not yet configured. The
canonical frozen Milestone 1 document and governing hash are not locally
available for exact traceability.

### Decision

Maintain the production gate at **BLOCKED**. Complete the remaining MDM and
ratification work, then run this implementation without weakening any gate. If
the first real snapshot passes all checks and independent replay, Project EDGE
may proceed to Stage 2 Feature Generation. If it does not, retain the failed
evidence and correct the data foundation before conducting market research.
