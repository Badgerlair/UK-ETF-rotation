# Project EDGE — Implementation Milestone 2

## MDM Data Foundation Specification

**Document type:** Scientific data architecture and implementation specification  
**Document version:** 1.0  
**Date:** 2026-08-03  
**Status:** Proposed Milestone 2 implementation authority  
**Constitutional authority:** Project EDGE Stage 0 Foundation Version 1.1  
**Governance authority:** Project EDGE Milestone 1 Scientific Governance Specification  
**Repository:** `D:\codex\equity_quant_research_platform`  
**Authoritative market-data source:** Market Data Manager (MDM) only  
**Initial research horizon:** Requirements reasonably foreseeable during the first 12 months  
**Explicit exclusions:** Trading strategies, optimisation, portfolios, execution, brokers, and live trading

---

## 1. Authority, purpose, and implementation posture

### 1.1 Frozen authorities

The Stage 0 Foundation Version 1.1 and Milestone 1 Governance Specification are frozen. This specification implements their data requirements without redesigning them.

If implementation exposes a genuine constitutional or governance deficiency, work shall stop at the affected boundary and create a formal issue. Milestone 2 must not enlarge governance merely for architectural convenience.

### 1.2 Purpose

The MDM Data Foundation is the single authoritative gateway between MDM and Project EDGE. No downstream feature, experiment, validation, or knowledge component may read market data except through a sealed and admissible Data Foundation snapshot.

The Data Foundation shall:

1. obtain authorised data from MDM;
2. preserve exact source and extraction identity;
3. canonicalise security identity, sessions, actions, memberships, observations, and revisions;
4. enforce what was knowable at every research cutoff;
5. reconstruct the eligible historical population without survivor filtering;
6. expose deterministic point-in-time joins;
7. produce immutable, reproducible research snapshots;
8. certify data admissibility for an exact scientific use; and
9. provide feature-ready observations without generating research features or outcomes.

The governing rule is:

> No direct MDM access downstream; no sealed snapshot, no data use; no admissibility certificate, no experiment.

### 1.3 Practical implementation philosophy

Every proposed element must answer: **Will this be required by the first 12 months of scientific research?**

- If yes, implement the simplest deterministic form that preserves scientific integrity.
- If probably yes but not required for the first research release, define the contract and schedule it as **Important**.
- If no, mark it **Future** and do not implement it now.

The initial implementation shall not introduce a message bus, service mesh, distributed data lake, streaming platform, generic enterprise catalogue, cloud warehouse, or multi-vendor abstraction.

### 1.4 Priority vocabulary

| Priority | Meaning |
|---|---|
| Mandatory | Required before the first phenomenon-discovery experiment may execute |
| Important | Expected within the first 12 months or required before a named research family can begin; not part of the minimum first release unless that family is selected |
| Future | Safely postponed beyond the first 12 months or until a concrete approved requirement exists |

Priority never relaxes a scientific gate. An Important dataset that has not been implemented is **unavailable**, not approximated. Any experiment requiring it remains blocked.

---

## 2. Initial scientific scope and mandatory decisions

### 2.1 First-release research envelope

The minimum release shall support daily or session-level equity research using:

- stable security and issuer identity;
- raw daily OHLCV observations;
- distributions, splits, reorganisations, delistings, and terminal outcomes;
- exchange sessions and trading-day offsets;
- historical listing and eligibility states;
- versioned universe rules;
- point-in-time sector and industry context when the first pilot requires it and MDM passes audit;
- deterministic as-of joins; and
- reproducible security-day datasets.

This is sufficient to begin bounded work on price path, continuation and reversal, volatility states, gaps, volume response, relative strength, market breadth, and cross-sectional dispersion.

### 2.2 Decisions that must precede data implementation

Milestone 2 shall not silently choose unresolved scientific scope. Before the first production snapshot, owners must ratify:

- geographic markets and exchanges;
- eligible security types;
- primary versus secondary listing rules;
- security versus issuer unit of analysis;
- multiple-share-class treatment;
- IPO seasoning, suspension, relisting, acquisition, bankruptcy, and delisting rules;
- base currency and currency-conversion policy;
- official research cutoff for each exchange;
- raw, price-return, and total-return conventions;
- research start date and minimum coverage;
- point-in-time sector, industry, index, and peer policies; and
- MDM licensing, snapshot retention, and replay permissions.

These decisions form a versioned **Research Population and Time Contract**. The implementation supports the ratified contract; it does not build a generic policy engine for hypothetical markets.

The minimum contract should use one currency or one explicitly comparable currency group. A multi-currency release is blocked until a versioned conversion policy, point-in-time conversion observations supplied by MDM, and their cutoffs have been implemented and admitted. Likewise, pooling venues with asynchronous closes requires a frozen common absolute-time or staggered-information policy; per-exchange dates alone are not sufficient.

### 2.3 Capability audit

No separate in-repository MDM capability specification exists. Therefore the first Milestone 2 artifact must be an MDM capability matrix, not an assumed interface.

For every requested dataset or field, the matrix shall record:

| Field | Required assessment |
|---|---|
| Capability | Available, partially available, unavailable, or unknown |
| MDM identity | Logical dataset, documented operation, schema, and version mechanism |
| History | Earliest date, latest date, gaps, exchanges, and security coverage |
| Temporal fidelity | Economic, publication, availability, effective, and vintage timestamps supplied |
| Identity fidelity | Stable security, issuer, listing, exchange, and share-class identifiers |
| Revisions | Original values, corrections, revisions, restatements, and retrievability |
| Population | Inactive, suspended, delisted, acquired, bankrupt, and relisted coverage |
| Corporate actions | Types, event dates, effective dates, factors, cash flows, and terminal outcomes |
| Memberships | Sector, industry, index, announcement, effective, and removal history |
| Snapshot support | Immutable snapshot ID, version token, or reproducible extraction capability |
| Quality | Timestamp precision, known defects, missingness, and MDM quality flags |
| Retention | Licensing, allowed storage, replay, and audit restrictions |
| Authorised use | Research families that may use the field and explicit prohibitions |

Unknown capability is a blocker for dependent work. No substitute market-data source is permitted.

---

## 3. Minimal logical architecture

### 3.1 Four logical layers

The first implementation contains four logical layers. These are responsibilities, not separate services.

| Layer | Responsibility | Output |
|---|---|---|
| MDM boundary | Resolve capabilities, submit exact requests, capture MDM identity and responses | Source-capture manifest and retained extract or immutable MDM reference |
| Canonical point-in-time layer | Normalise types, times, identity, calendars, actions, membership, revisions, and quality states | Versioned canonical tables |
| Snapshot and admissibility layer | Freeze inputs, validate content, record lineage, issue scoped admission decisions | Sealed snapshot and admissibility certificate |
| Feature-ready access layer | Serve deterministic security-day, universe, event, and as-of views | Experiment-bindable dataset manifest |

No feature calculation, forward outcome construction, hypothesis logic, or statistical test belongs in this layer.

### 3.2 Initial storage choice

The practical default is:

- immutable columnar files, preferably Parquet, for retained tabular data;
- one human-readable manifest per snapshot, preferably JSON;
- content fingerprints for every retained file;
- an embedded analytical reader for validation and research access; and
- generated indexes for convenience, never as the sole authority.

Daily observations should initially be partitioned by logical dataset and trading year, subject to measurement. Per-security files are prohibited because they create unnecessary small-file complexity. Different partitioning requires a measured need.

If MDM supplies a guaranteed immutable and retrievable snapshot, Project EDGE may retain the MDM snapshot identity and exact extraction manifest instead of duplicating source bytes where licensing or storage requires it. If replay cannot be guaranteed, affected evidence cannot claim exact reproducibility.

Server databases, distributed processing, object-store abstraction, and streaming ingestion are Future unless measured first-year scale proves the simple approach insufficient.

### 3.3 Data zones

Only three retained data zones are required:

1. **Source capture:** exact MDM extract or retrievable immutable source reference, unchanged except for transport packaging.
2. **Canonical data:** typed, normalised, point-in-time tables with source values preserved and no research-specific feature logic.
3. **Feature-ready snapshot:** scoped, admissible, joined observations and population manifests bound to an exact snapshot.

Terms such as bronze, silver, gold, lakehouse, and data product add no scientific value here and are not required.

### 3.4 Downstream access law

Downstream components receive an immutable snapshot handle containing:

- snapshot ID and version;
- manifest fingerprint;
- schema versions;
- table and partition inventory;
- MDM source identity;
- Research Population and Time Contract version;
- cutoff policy;
- admissibility certificate;
- known limitations;
- supersession and correction state; and
- approved access scope.

Downstream code may read only sealed canonical or feature-ready artifacts. Direct MDM credentials and unsealed build paths shall not be available to ordinary feature or experiment execution.

### 3.5 Mandatory release-access decision

Ordinary downstream access shall pass through one small fail-closed decision that verifies:

- immutable snapshot or view ID, never a mutable alias;
- manifest fingerprint against the protected release record;
- current admissibility state, expiry, quarantine, revocation, and supersession rules;
- requested fields, population, dates, cutoff, and scientific use against the certificate scope;
- requesting stage and authorised access class; and
- complete lineage and storage integrity.

On success, the decision returns a read-only handle to the admitted partitions and evidence bundle. On failure, it returns a typed denial and records the attempt. The normal feature/experiment execution identity shall have no read access to source-capture, build, quarantine, or unrestricted MDM locations. Controlled diagnostic access is separate, read-only, logged, and cannot produce an admissible research input.

---

## 4. Component priority summary

| Requirement | Priority | First-release interpretation |
|---|---|---|
| 1. MDM interface | Mandatory | One read-only gateway using documented capabilities; no generic vendor abstraction |
| 2. Point-in-time correctness | Mandatory | Four-clock semantics, cutoff enforcement, and future-information sentinels |
| 3. Security identity | Mandatory | Stable MDM security and issuer IDs with listing and ticker history |
| 4. Corporate actions | Mandatory | Raw observations, actions, return-consistent treatment, and terminal outcomes |
| 5. Historical universe | Mandatory | Daily survivor-complete population and typed exclusion reasons |
| 6. Trading calendars | Mandatory | MDM-sourced sessions, cutoffs, timezones, holidays, and trading-day offsets |
| 7. Data versioning | Mandatory | Exact source, schema, transform, policy, and artifact versions |
| 8. Snapshot management | Mandatory | Immutable build, validation, sealing, correction, and replay lifecycle |
| 9. Data lineage | Mandatory | Dataset- and field-level source-to-output lineage; per-cell lineage deferred |
| 10. Data admissibility | Mandatory | Fail-closed scoped certificates and stratified quality reports |
| 11. Point-in-time joins | Mandatory | One governed as-of join contract with deterministic tie and expiry rules |
| 12. Feature-ready datasets | Mandatory | Daily core panel, universe manifest, actions, quality states, and reproducibility manifest |

Point-in-time sector and industry histories are **Important** by default and become **Mandatory** if the first pilot uses sector or industry context. Index membership, fundamentals, earnings, quotes, and other events follow the component-specific priorities below.

---

## 5. Component 1 — MDM interface

**Priority: Mandatory**

### 5.1 Responsibility

The MDM interface is the only authorised route for market data. It shall be read-only from Project EDGE's perspective unless MDM explicitly requires non-market control operations that cannot alter data.

The interface must not invent endpoint names or behaviours before the capability audit. It defines logical operations and guarantees.

### 5.2 Logical operations

| Operation | Input | Required result |
|---|---|---|
| Describe capabilities | Dataset or field family | Supported fields, schemas, history, timestamps, versions, quality, and restrictions |
| Resolve source version | Requested cutoff and datasets | Immutable MDM snapshot/version tokens or declared lack of support |
| Plan extraction | Population, dates, fields, source version | Exact request plan and expected partitions |
| Extract | Approved extraction plan | Data plus request ID, source identity, counts, and MDM metadata |
| Retrieve correction history | Dataset/version interval | Corrections, affected records or partitions, effective times, and successor versions |
| Verify retrievability | Source version and request | Proof that the identical source can be replayed or explicit failure |
| Health and schema check | Dataset/version | Availability, schema fingerprint, and incompatible change report |

### 5.3 Interface contract

Every extraction shall record:

- request ID;
- requesting Project EDGE artifact;
- MDM operation or dataset identity;
- exact parameters;
- source snapshot or version;
- schema version;
- extraction start and finish;
- MDM cutoff or consistency token;
- returned partitions and row counts;
- transport and source quality flags;
- content fingerprints where retained;
- retry history; and
- errors and partial delivery.

Partial responses are not silently treated as complete.

### 5.4 Failure rules

- MDM unavailable: fail the build; do not use cached mutable data or another source.
- Unknown source version: snapshot cannot be sealed.
- Undocumented schema change: quarantine the affected extraction and create a new schema contract.
- Partial extraction: retain for diagnosis but mark incomplete and inadmissible.
- Retry: retain all attempt metadata; accept only a complete version-consistent result.
- MDM correction: create a new Project EDGE snapshot and downstream impact assessment.

### 5.5 Deferred interface work

| Item | Priority | Reason |
|---|---|---|
| Multiple market-data vendors | Future | Prohibited by MDM exclusivity |
| Streaming or real-time ingestion | Future | No first-year scientific need |
| Generic query federation | Future | Adds complexity without scientific value |
| Interactive data-catalogue UI | Future | Manifests and capability reports are sufficient initially |
| Automated cross-region failover | Future | One governed research environment is sufficient |

---

## 6. Component 2 — Point-in-time correctness

**Priority: Mandatory**

### 6.1 Temporal model

Every revisable or later-published observation shall distinguish:

1. **Economic time:** when the underlying activity occurred or period ended.
2. **Publication time:** when information was released publicly.
3. **Availability time:** earliest time it could legitimately be used under the approved research cutoff.
4. **Vintage time:** MDM snapshot or correction version from which the stored representation came.

Where membership or state changes are involved, records also require effective start and end times. Where Project EDGE ingests data after MDM availability, ingestion time is recorded for operations but does not replace availability time.

### 6.2 Common temporal fields

Canonical records use the applicable subset of:

- `economic_at` or fiscal-period end;
- `published_at`;
- `available_at`;
- `effective_from`;
- `effective_to`, exclusive;
- `session_date`;
- `mdm_vintage_id`;
- `edge_snapshot_id`; and
- timestamp-precision or ambiguity grade.

Names are conceptual; exact physical names are fixed in the schema contract.

### 6.3 Availability rule

A value may be joined to a research observation at cutoff `t` only when:

- its applicable security and membership scope is valid at `t`;
- `available_at <= t`;
- it has not expired or been replaced before `t` under the chosen historical vintage semantics;
- the selected revision was the latest revision available by `t`, not the latest known today; and
- all joining keys and tie-break rules resolve deterministically.

Unknown or date-only publication time receives a conservative, versioned availability rule. If no scientifically defensible lag exists, the record is inadmissible for predictive use.

### 6.4 Future-information prohibitions

The layer shall block:

- present-day classifications projected backward;
- latest-restated fundamentals substituted historically;
- current index constituents used as historical universes;
- future corporate actions embedded in historical price thresholds;
- outcomes beginning before the feature cutoff;
- full-history normalisation or thresholds in canonical data;
- forward-filling beyond a record's validity or staleness limit; and
- resolving ambiguous event dates in the researcher's favour.

### 6.5 Validation

Mandatory temporal checks include:

- `available_at` never later joined to an earlier cutoff;
- revision sequences are monotonic and non-overlapping;
- effective intervals are valid and deterministic;
- after-hours events map to the correct later session;
- date-only events obey the conservative policy;
- current classification and membership sentinels fail when deliberately projected backward;
- future-shifted fields cannot predict their own past availability; and
- repeated point-in-time builds return identical matches.

### 6.6 Deferral

| Item | Priority | Treatment |
|---|---|---|
| Daily price and volume cutoffs | Mandatory | First release |
| Sector and industry availability histories | Important | Mandatory before sector-dependent research |
| Index announcement and effective histories | Important | Mandatory before index-effect research |
| Fundamentals and restatement vintages | Important | Mandatory before fundamental research |
| Earnings timestamps | Important | Mandatory before earnings research |
| Intraday publication ordering | Future | Defer until approved intraday research |

---

## 7. Component 3 — Security identity management

**Priority: Mandatory**

### 7.1 Identity law

The research key is a stable MDM security or listing identifier. Ticker is an attribute with a validity interval, never a primary key.

The model distinguishes:

- issuer;
- security or share class;
- exchange listing;
- ticker and other symbols;
- currency;
- primary or secondary listing status; and
- corporate lifecycle state.

### 7.2 Canonical identity history

The security identity dataset shall record:

- stable MDM security ID;
- stable MDM issuer ID where supplied;
- stable listing ID where supplied;
- security type and share class;
- exchange and currency;
- ticker and identifier history with validity intervals;
- listing, suspension, resumption, transfer, relisting, and delisting intervals;
- primary-listing status under the approved policy;
- predecessor, successor, merger, acquisition, spin-off, and conversion references where MDM supplies them;
- status and reason codes;
- source version and temporal fields; and
- ambiguity or quality state.

### 7.3 Resolution outcomes

Identity resolution produces one of:

- exact;
- exact within declared historical interval;
- unresolved;
- ambiguous;
- conflicting; or
- unavailable.

Ambiguous or conflicting identity is not guessed. Affected observations are quarantined or excluded with a typed reason and coverage impact.

### 7.4 Identity validation

Checks include:

- ticker reuse across different stable IDs;
- overlapping ticker/exchange assignments;
- duplicate security-session rows;
- issuer/security confusion;
- multiple share classes counted unintentionally as multiple issuers;
- observations outside listing intervals;
- discontinuities around transfers and relistings;
- missing delisting or terminal state;
- predecessor/successor cycles; and
- present-day identifier backfill.

### 7.5 Deferral

| Item | Priority | Treatment |
|---|---|---|
| Stable security/listing/issuer history | Mandatory | First release |
| Multiple-share-class and issuer grouping | Mandatory | First release |
| ADR and foreign-listing linkage | Important | Implement only if included in the ratified population |
| Complex global legal-entity hierarchy | Future | No first-year need without multi-jurisdiction scope |
| External identifier-master enrichment | Future | Prohibited unless supplied through MDM |

---

## 8. Component 4 — Corporate actions

**Priority: Mandatory**

### 8.1 Responsibility

The Data Foundation shall preserve two coherent and explicitly named views:

1. **Observed-price view:** what the market printed, for gaps, price levels, limits, liquidity, and discontinuities.
2. **Return-consistent view:** economic return across valid distributions and corporate actions.

Neither view silently replaces the other. Every downstream request declares which view it uses.

### 8.2 Corporate-action record

Where supplied by MDM, each action records:

- stable action ID;
- affected security, issuer, and listing IDs;
- action type;
- announcement, publication, ex, record, effective, payable, and completion times where applicable;
- availability and MDM vintage times;
- cash amount, currency, ratio, factor, new security, or consideration as applicable;
- predecessor and successor relationships;
- source quality and timestamp precision;
- cancellation or amendment history; and
- exact source and snapshot lineage.

The first release must capture, identify, preserve, and classify all of the following when MDM reports them: splits and consolidations, cash and stock distributions, mergers and acquisitions, spin-offs, rights or similar distributions, symbol/listing changes, and delisting or terminal events. Mandatory economic normalisation covers splits, ordinary distributions, and terminal-return treatment. A complex action that is detected but not yet normalised is quarantined across every continuity-dependent interval; its mere presence does not require a speculative general reorganisation engine.

### 8.3 Adjustment rules

- Raw observations are immutable and never overwritten by adjusted values.
- Adjustment factors are derived artifacts with their own policy and version.
- A factor may affect a feature at cutoff `t` only under the declared point-in-time and effective-time policy.
- Backward-adjusted present-day price series cannot be used as the source for historical price thresholds or gaps.
- Split-consistent volume and share quantities use the same action lineage as prices.
- Cash distributions and delisting proceeds follow the ratified total-return convention.
- A corporate reorganisation does not automatically imply continuous security identity.
- Unknown or conflicting actions quarantine the affected return-consistent interval; they do not invite discretionary repair.

Before the first return-consistent view is admitted, its action-timing convention shall freeze:

- when an announced action may enter a feature;
- the ex-session and effective-session rule;
- treatment of actions announced after a research cutoff;
- treatment of records corrected after their effective date;
- return horizons that cross an action;
- distribution and delisting consideration timing;
- cancellation and successor handling; and
- the distinction between contemporaneously knowable return inputs and later revised economic measurement.

Features and lookback returns may use only action records available by the row cutoff. A realised forward outcome may incorporate actions that occur within its outcome horizon, but those records remain in the outcome layer and cannot flow back into features. A later corrected measurement may support an explicitly governed measurement-sensitivity view; it cannot silently rewrite the historically available feature view.

### 8.4 Validation

Checks include:

- raw-price discontinuities reconciled to actions;
- factor arithmetic and direction;
- split price/volume consistency;
- duplicate, cancelled, or overlapping actions;
- action application before announcement or effective time;
- cash amount and currency consistency;
- successor identity resolution;
- terminal outcome coverage;
- observed-view versus return-view reconciliation; and
- extreme returns concentrated around unresolved actions.

Quality reports must identify affected securities and dates. Passing broad aggregate return checks is insufficient.

### 8.5 Failure and priority

An unresolved split, reorganisation, or terminal outcome makes the affected return-consistent data inadmissible. Raw observations may remain admissible for a narrowly scoped study only if the unresolved action cannot affect its estimand and the limitation is explicit.

| Item | Priority |
|---|---|
| Raw observations and explicit action table | Mandatory |
| Split and distribution reconciliation | Mandatory |
| Delisting and terminal outcomes | Mandatory |
| Capture, identify, and quarantine unsupported complex actions | Mandatory |
| Full complex reorganisation economics | Important; Mandatory before continuity-dependent use across such events |
| Tax-lot, withholding, or investor-specific treatment | Future |

---

## 9. Component 5 — Historical universe reconstruction

**Priority: Mandatory**

### 9.1 Responsibility

The universe is reconstructed for every session from historical identity and lifecycle facts. It is never derived from today's symbols, constituents, or surviving securities.

Universe policy is a scientific design artifact, not a data-cleaning convenience.

### 9.2 Universe policy

A versioned policy declares:

- markets and exchanges;
- eligible security types;
- primary/secondary listing treatment;
- issuer and multiple-share-class treatment;
- listing-age and IPO-seasoning rules;
- active, suspended, halted, distressed, relisted, bankrupt, acquired, and delisted treatment;
- price, liquidity, market-cap, and history requirements where used;
- currency policy;
- required terminal outcomes;
- inclusion and exclusion precedence; and
- unknown-data treatment.

These criteria are fixed before outcome inspection and never tuned for attractive results.

### 9.3 Daily universe manifest

For every security-session candidate, retain:

- security, issuer, and listing IDs;
- session date and exchange;
- candidate-population status;
- eligible or ineligible decision;
- every applicable exclusion reason;
- listing and lifecycle state;
- required-history state;
- price/liquidity/size inputs and their availability times when used by policy;
- membership/classification availability state;
- policy version;
- source snapshot; and
- quality and missingness state.

The manifest preserves the candidate denominator, eligible denominator, excluded count, and unknown count. It must be possible to explain why any security is absent on any date.

### 9.4 Survivorship controls

- Inactive and delisted securities remain in historical identity and observation tables.
- Acquired or bankrupt securities are not truncated before terminal outcomes.
- Current exchange, index, or sector membership cannot define past inclusion.
- Eligibility at date `t` uses only facts available by the approved cutoff.
- Market-cap or liquidity screens use point-in-time inputs and retain boundary values.
- A survivor-only universe may exist only as a labelled diagnostic sentinel, never the default scientific population.
- If MDM lacks materially affected inactive or terminal histories, the relevant broad-population claim is inadmissible or explicitly narrowed with approved bounding analysis.

### 9.5 Validation

Checks include:

- daily population reconciliation to MDM lifecycle records;
- inactive and delisted coverage;
- terminal-outcome coverage;
- listing intervals and observations outside them;
- duplicate issuer or share-class weights;
- sudden unexplained population loss;
- eligibility before IPO or after final delisting;
- point-in-time screen inputs;
- exclusion counts by exchange, year, size, liquidity, and lifecycle; and
- comparison with a survivor-only sentinel to expose material bias.

### 9.6 Deferred work

| Item | Priority | Treatment |
|---|---|---|
| Daily historical primary research population | Mandatory | First release |
| Multiple share-class issuer controls | Mandatory | First release |
| Point-in-time market-cap and liquidity eligibility | Important | Implement when the selected pilot requires it and MDM passes audit |
| Complex cross-country investability rules | Future | No generic global universe engine initially |
| Portfolio-style rebalance universes | Future | Outside Stages 0–5 |

---

## 10. Component 6 — Trading calendar management

**Priority: Mandatory**

### 10.1 Responsibility

Trading calendars define the scientific clock. Calendar days cannot substitute for exchange sessions.

All calendar and session facts must come from MDM. If MDM cannot support an exchange calendar with required fidelity, that exchange is not admissible until the deficiency is resolved within the authorised data boundary.

### 10.2 Session record

Each exchange session records:

- exchange/calendar ID and version;
- local trading date;
- timezone and UTC offset under historical daylight-saving rules;
- scheduled open and close;
- actual or authoritative open and close where supplied;
- early-close indicator;
- holiday or closure type;
- unscheduled closure or interruption;
- auction boundaries where required and available;
- previous and next valid sessions;
- MDM vintage and availability; and
- quality state.

### 10.3 Calendar operations

The governed interface shall support:

- resolve timestamp to exchange session;
- resolve pre-market, regular, after-hours, and date-only event assignment;
- shift by a declared number of trading sessions;
- determine feature cutoff and earliest outcome start;
- determine horizon maturity;
- identify missing expected observations;
- calculate listing and event age in sessions; and
- combine calendars only through an approved cross-market policy.

### 10.4 Validation

Checks include:

- observations on non-trading dates;
- missing scheduled sessions;
- duplicate sessions;
- invalid or overlapping open/close times;
- early-close handling;
- historical timezone and daylight-saving consistency;
- event-to-session boundary cases;
- outcome windows beginning before feature cutoff; and
- deterministic trading-day offsets.

### 10.5 Deferral

| Item | Priority |
|---|---|
| Daily exchange sessions and cutoffs | Mandatory |
| Historical timezone, holiday, and early-close handling | Mandatory |
| After-hours event assignment | Important; mandatory for event research |
| Auction-phase calendar | Important only for auction research |
| Continuous intraday bar schedule | Future |
| Generic cross-asset calendar algebra | Future |

---

## 11. Component 7 — Data versioning

**Priority: Mandatory**

### 11.1 Version dimensions

The Data Foundation keeps distinct versions for:

| Version | Meaning |
|---|---|
| MDM source version | Snapshot, vintage, correction, or immutable source token |
| Interface-contract version | Agreed MDM capability, request, and response semantics |
| Canonical-schema version | Field names, types, keys, nulls, units, and constraints |
| Transformation version | Deterministic canonicalisation or derived-view logic |
| Builder-software version | Exact Project EDGE revision plus relevant runtime and dependency lock used to extract, transform, validate, and encode |
| Scientific-policy version | Population, cutoff, calendar, corporate-action, or availability rule |
| Snapshot version | Exact sealed collection of inputs, transformations, validations, and outputs |
| Admissibility-rule version | Checks and acceptance rules applied to the snapshot |

These versions are linked but never collapsed into one ambiguous number.

### 11.2 Change classification

- **Compatible extension:** optional field or metadata added without changing existing meaning; creates a new schema version.
- **Semantic change:** field meaning, unit, timing, key, or policy changes; creates a new schema/transformation version and requires downstream review.
- **MDM correction:** source values change; creates a new MDM vintage and Project EDGE snapshot.
- **Transformation correction:** prior canonicalisation was wrong; creates a successor transform and snapshot, with impact assessment.
- **Policy change:** universe, cutoff, adjustment, or join rule changes; creates a successor policy and snapshot.

No completed snapshot is rebuilt in place.

### 11.3 Version binding

Every experiment and feature view binds exact versions of:

- MDM source;
- source extraction;
- schema;
- transformations;
- builder software and reproducibility environment;
- population and time policy;
- calendars;
- identity;
- corporate actions;
- classifications or memberships where used;
- snapshot; and
- admissibility certificate.

### 11.4 Practical boundary

A versioned manifest is Mandatory. A separate enterprise schema-registry service, semantic-version automation platform, or generic migration framework is Future. Simple explicit contracts and deterministic compatibility checks are sufficient initially.

---

## 12. Component 8 — Snapshot management

**Priority: Mandatory**

### 12.1 Snapshot definition

A Project EDGE research snapshot is an immutable, internally coherent set of source identities, retained data, canonical tables, policies, validation results, lineage, and admissibility decisions.

It is distinct from an MDM snapshot. One EDGE snapshot may reference one atomic MDM snapshot or an explicitly reconciled set of MDM dataset versions captured under a common extraction cutoff.

### 12.2 Snapshot request

Every build begins with a frozen request containing:

- request ID;
- scientific purpose or target data release;
- population-policy version;
- markets, security types, date range, and cutoffs;
- required datasets and fields;
- requested MDM source version or common cutoff;
- canonical schema and transformation versions;
- builder software and reproducibility-environment versions;
- required quality and admissibility rules;
- expected partitions and storage;
- builder and reviewer; and
- parent snapshot if incremental or corrective.

### 12.3 Snapshot manifest

The sealed manifest contains:

- snapshot ID and version;
- parent and supersession links;
- creation and seal times;
- request and owner;
- MDM request IDs, source versions, schemas, and extraction times;
- consistency boundary across datasets;
- all retained files or immutable source references;
- canonical schemas and transformations;
- builder software, runtime, dependency lock, and encoding versions;
- population, cutoff, calendar, identity, corporate-action, and join policies;
- row counts, date bounds, security counts, and partition inventory;
- content fingerprints;
- validation and coverage reports;
- lineage records;
- admissibility status and scope;
- known limitations and Scientific Debt;
- licensing and retention conditions; and
- reviewer and seal decision.

### 12.4 Lifecycle

| State | Meaning | Downstream use |
|---|---|---|
| Requested | Frozen build request exists | No |
| Building | Extraction or canonicalisation in progress | No |
| Captured | Declared source payload is complete but not yet validated | No |
| Validating | Mandatory checks are running | No |
| Incomplete | Build stopped or partial | No |
| Validation failed | Mandatory check failed | No |
| Validated pending admission | Checks complete; scientific scope review pending | No |
| Sealed admissible | Immutable and admitted for stated uses | Yes |
| Sealed conditional | Admitted only within explicit limitations | Yes, within scope only |
| Quarantined | Material anomaly under investigation | No new use |
| Rejected | Admission was denied | No |
| Superseded | Successor is active; historical users remain linked | No new use by default |
| Data-invalidated | Fatal source or build defect confirmed | No; downstream impact review required |

Only sealed admissible or sealed conditional snapshots may be bound to new experiments.

### 12.4A Seal attestation and protected release register

A content hash is not an adequate seal if the payload and its reference hash can be changed together. The minimum implementation shall therefore maintain an append-only release register protected from the ordinary build and research write paths.

Every register event records:

- release-event ID;
- snapshot or view ID;
- complete manifest fingerprint;
- prior release event or chain fingerprint;
- state transition and reason;
- seal or transition time;
- builder identity;
- reviewer identity and authorised role;
- admissibility-decision reference; and
- successor, quarantine, revocation, or invalidation reference where applicable.

Publication requires a register entry written by the authorised release path after independent review. Consumers verify both the manifest fingerprint and current register state before access. The register is backed up and integrity-checked independently of generated datasets. Role separation plus a chained append-only record is Mandatory; external public-key signing or hardware-backed attestation is Important only if the local environment cannot provide a sufficiently protected authority. An enterprise ledger service is Future.

### 12.5 Atomicity and consistency

Preferred order:

1. use one MDM immutable snapshot across all datasets;
2. otherwise use dataset-level immutable versions with a common extraction cutoff and a manifest proving consistency;
3. if neither is possible, block sealing rather than mix changing datasets silently.

### 12.6 Corrections

An MDM or Project EDGE correction creates a new snapshot with:

- exact parent;
- changed source or transformation;
- affected partitions and records;
- comparison report;
- scientific impact classification;
- downstream experiments and features; and
- decision to retain, reproduce, revalidate, supersede, or data-invalidate affected evidence.

The earlier snapshot remains retrievable.

### 12.7 Practical boundary

Full and incrementally built snapshots may both exist, but they must seal to the same deterministic artifact contract. Sophisticated branch/merge snapshot management, deduplicating object stores, and distributed snapshot coordination are Future.

---

## 13. Component 9 — Data lineage

**Priority: Mandatory**

### 13.1 Required lineage depth

The first release requires:

- source dataset and field lineage;
- extraction request and MDM version;
- canonical output dataset and field;
- transformation and policy version;
- input/output partition fingerprints;
- join inputs and rules;
- snapshot and admissibility decision; and
- downstream feature-view or experiment references.

This provides dataset-, field-, and partition-level lineage. Universal per-cell lineage is Future because it adds substantial storage and complexity without first-year scientific benefit.

### 13.2 Lineage record

Every canonical or feature-ready field records:

- output dataset and field;
- scientific meaning and unit;
- MDM input datasets and fields;
- transformation steps in order;
- temporal and join rules;
- missingness and quality propagation;
- relevant identity, calendar, corporate-action, or membership policy;
- code or transformation version when implemented;
- input and output fingerprints;
- owner and reviewer; and
- known limitations.

### 13.3 Lineage graph

The minimum graph is:

**MDM source version → extraction → source capture → canonical table → point-in-time join or derived view → feature-ready dataset → Stage 2 feature version → experiment**

Lineage is provenance, not dependency satisfaction. The Milestone 1 Research Dependency Graph references lineage decisions but remains a separate scientific artifact.

### 13.4 Validation and failure

- Every retained output column must resolve to authorised MDM fields or explicitly declared non-market metadata.
- Every transformation must be versioned and deterministic.
- Orphan fields, missing fingerprints, ambiguous source versions, or undocumented joins block admission.
- A corrected upstream node triggers downstream impact traversal.
- Lineage indexes may be regenerated; authoritative manifests and records may not be discarded.

### 13.5 Deferral

| Item | Priority |
|---|---|
| Dataset/field/partition lineage | Mandatory |
| Downstream snapshot-to-feature-to-experiment links | Mandatory |
| Interactive lineage visualisation | Important but not required for first release |
| Universal row-level lineage | Important only for datasets with material revision ambiguity |
| Universal per-cell lineage | Future |

---

## 14. Component 10 — Data admissibility

**Priority: Mandatory**

### 14.1 Scoped decision

Admissibility is always relative to an exact snapshot, dataset, population, period, cutoff, and scientific use. A snapshot may be admissible for daily price-path research while inadmissible for fundamentals or sector analysis.

### 14.2 States

| State | Meaning |
|---|---|
| Pending | Admission review incomplete |
| Unavailable | MDM cannot supply the required history, identity, timing, revision, or replay semantics for the declared use |
| Admissible | All mandatory checks pass for the declared scope |
| Admissible conditional | Trustworthy only inside explicit limits irrelevant to the permitted estimand |
| Inadmissible | A mandatory requirement fails |
| Quarantined | Prior decision suspended pending anomaly review |
| Revoked | A previously admitted scope is confirmed no longer defensible; new use is prohibited and descendants require impact review |
| Superseded | A successor decision or snapshot is active |

Conditional admission cannot excuse look-ahead, unauthorised data, identity ambiguity material to the population, survivor loss material to the estimand, corrupt lineage, or non-reproducibility.

### 14.3 Admission certificate

The certificate records:

- certificate ID and version;
- snapshot and manifest fingerprint;
- declared scientific uses and prohibitions;
- population, period, exchanges, security types, and cutoff;
- required datasets and fields;
- applied rule versions;
- complete check inventory and results;
- coverage and missingness by time and segment;
- unresolved limitations and debt;
- state and rationale;
- reviewer and data-steward decisions;
- expiry and recheck triggers; and
- downstream references.

### 14.4 Mandatory cross-dataset checks

- MDM is the sole source.
- Source versions and schemas resolve exactly.
- Snapshot contents and fingerprints match the manifest.
- Stable identity and uniqueness pass.
- Calendar and session alignment pass.
- Point-in-time and availability rules pass.
- Corporate actions and return views reconcile.
- Historical population includes required inactive and delisted securities.
- Required classifications or memberships are historical, not current backfills.
- Revisions and vintages are reproducible.
- Missingness is typed and stratified.
- No silent imputation, deletion, winsorisation, or repair occurred.
- Lineage is complete.
- Repeated build or replay is deterministic.

### 14.5 Dataset-specific checks

| Dataset | Minimum checks |
|---|---|
| Daily market observations | Unique security-session key; OHLC consistency; positive/valid price; non-negative volume; exchange/currency; staleness; halt state; action discontinuity |
| Identity | Valid intervals; ticker reuse; share-class and issuer consistency; observations within listing life; no ambiguous primary key |
| Corporate actions | Type, date, factor, cash, currency, cancellation, successor, terminal outcome, price/volume reconciliation |
| Calendar | Complete sessions; no invalid overlaps; timezone/DST; holiday/early close; observation alignment |
| Universe | Candidate and eligible denominators; exclusion reasons; delisted coverage; policy inputs known at cutoff |
| Classification/membership | Effective and availability intervals; unknown category; no present-day backfill; coverage by date/segment |
| Fundamentals | Fiscal period, publication, availability, revision/restatement chain; original values retained |
| Events | Timestamp precision; session assignment; revisions/cancellations; date-only conservative treatment |

### 14.6 Quality and missingness states

Lifecycle, value availability, and quality are separate dimensions.

**Lifecycle state:**

- pre-listing;
- active;
- halted;
- suspended;
- inactive;
- delisted; or
- terminal state unknown.

**Value state:**

- present;
- structurally not applicable;
- outside listing life;
- no trading session;
- not yet public;
- source value absent;
- MDM coverage absent;
- unavailable in this vintage;
- ambiguous identity;
- quarantined;
- invalid; or
- missing reason unresolved.

**Quality state:**

- passed;
- passed with warning;
- suspect;
- quarantined; or
- invalid.

Feature-readiness reasons may additionally include stale, insufficient history, or peer group too small. Null never means zero; missing reason unresolved blocks scientific use; no row is silently dropped; and any approved imputation belongs to a later governed feature or experiment definition, not canonicalisation.

### 14.7 Stratification

Quality reports must be stratified by:

- time;
- exchange;
- security type;
- active/inactive/delisted state;
- market-cap and liquidity segment when available;
- sector/industry when available;
- field; and
- source vintage.

Broad averages cannot conceal missing distressed, small, inactive, or delisted securities.

### 14.8 Failure

Admission failure blocks the dependent dataset or scientific use. The system retains the failed report, affected scope, and attempted snapshot. It does not repair data silently or broaden exclusions until checks pass.

## 15. Component 11 — Point-in-time joins

**Priority: Mandatory**

### 15.1 Responsibility

Point-in-time joins assemble only facts that were both applicable and knowable at the declared research cutoff. They are governed scientific operations, not unrestricted database joins.

Every join specification shall identify:

- the immutable left-side dataset and key;
- the exact right-side snapshot and dataset;
- the stable security, issuer, listing, index, or classification identity used;
- the observation session and research cutoff;
- the business relationship being joined;
- the effective-time rule;
- the availability-time rule;
- the revision-selection rule;
- the maximum permitted staleness, if any;
- the missing-match policy;
- the multiple-match policy;
- the output fields; and
- the join-rule version.

The specification and result become immutable lineage artefacts.

### 15.2 General eligibility rule

A right-side record is eligible only when all of the following hold:

1. its stable identity matches the governed relationship;
2. it belongs to the bound snapshot;
3. its effective interval contains the applicable observation time, where an effective interval exists;
4. its `available_at` is no later than the research cutoff;
5. its revision or vintage was the applicable version available at that cutoff;
6. it satisfies the declared staleness limit; and
7. the dataset is admissible for the declared use.

Among eligible revisions, the join selects the latest revision available at the cutoff under the frozen revision policy. It never selects the present-day latest record merely because that record describes an earlier period.

### 15.3 Required safeguards

The join layer shall:

- prohibit joining on ticker or company name alone;
- prohibit implicit access to a current security master;
- prohibit equality-on-calendar-date as a substitute for availability logic;
- prohibit unrestricted forward filling;
- prohibit a nearest-date join unless a bounded backward-looking rule is explicitly registered;
- keep announcement time separate from effective time;
- retain unmatched left rows with typed reasons unless the frozen population policy explicitly excludes them;
- reject multiple eligible matches unless a preregistered deterministic precedence rule resolves a scientifically legitimate source duplication;
- report records rejected because they were not yet available;
- report coverage and staleness by time and segment; and
- fail closed when required temporal semantics are unknown.

A date-only release time may be assigned only to a documented conservative cutoff. It shall never be given a favourable intraday time.

### 15.4 Domain-specific rules

#### 15.4.1 Classification and index membership

A classification or membership must be effective on the observation session and available by the research cutoff. An advance announcement may be represented as a separate known announcement, but it does not make the future classification or membership currently effective.

#### 15.4.2 Fundamentals

Fiscal-period end is not an availability date. A fundamental value requires a reliable publication or filing availability time and its revision chain. Restatements remain separate vintages. If MDM cannot establish those semantics, fundamental joins are unavailable and the affected experiment is blocked.

#### 15.4.3 Events

Events require the original public timestamp, timestamp precision, timezone, revision or cancellation chain, and calendar mapping. A date-only event is assigned according to the frozen conservative policy and is not presumed available before the session close.

#### 15.4.4 Daily market observations

A completed daily bar is unavailable before the approved post-close cutoff. Suspended, halted, absent, and non-session observations retain distinct states. The same session's complete bar cannot enter a feature evaluated at an earlier clock.

### 15.5 Join audit output

Every join shall produce:

- input and output fingerprints;
- left-row count;
- eligible-match count;
- unmatched count by reason;
- multiple-match count;
- future or not-yet-public records rejected;
- stale matches by age band;
- exclusions by reason;
- coverage by date, lifecycle, exchange, and relevant segment;
- exact rule and source versions; and
- deterministic result fingerprint.

These counts are acceptance evidence, not disposable diagnostics.

### 15.6 Failure and priority

Future leakage, unresolved multiple matches, identity ambiguity, unknown required availability time, or non-deterministic replay makes the join output inadmissible. The failed output and audit remain retained.

- **Mandatory:** governed daily as-of joins for identity, lifecycle, calendar, prices, corporate actions, universe, classifications, and memberships required by the initial research scope.
- **Important:** as-reported fundamental and event joins before those research families begin; reusable correction-impact comparisons.
- **Future:** a general temporal-query language, arbitrary analyst-authored raw joins, and a universal bitemporal database engine.

## 16. Component 12 — Feature-ready datasets

**Priority: Mandatory**

### 16.1 Responsibility and boundary

Feature-ready datasets are immutable, point-in-time-correct scientific inputs to Stage 2 Feature Generation. They organise admissible observations; they do not create predictive features, labels, signals, rankings, strategies, or forward outcomes.

Stage 2.5 Feature Validation remains a separate frozen governance gate. Admission here proves data fitness and provenance, not scientific validity of a derived feature.

### 16.2 Mandatory first-release datasets

| Dataset | Priority | Minimum responsibility |
|---|---|---|
| Snapshot manifest | Mandatory | Exact MDM sources, scope, schemas, versions, partitions, fingerprints, validation, admissibility, and lineage |
| Security and issuer history | Mandatory | Stable identities; share-class, listing, venue, symbol, lifecycle, and successor history |
| Trading-session spine | Mandatory | One governed session sequence per supported exchange with cutoffs and session states |
| Raw daily observations | Mandatory | Unadjusted OHLCV and supplied status fields, with currency, units, availability, missingness, and quality |
| Corporate-action history | Mandatory | Action types, announcement/effective dates, amounts/factors, cancellations, successor and terminal-event facts |
| Return-consistent daily view | Mandatory | Explicit price-return, distribution, total-return, and terminal-return components with action lineage |
| Historical population state | Mandatory | Pre-listing, active, halted, suspended, inactive, delisted, and terminal states by session |
| Universe manifest | Mandatory | Exact candidate and eligible security-days, all inclusion/exclusion reasons, policy version, and fingerprint |
| Security-day observable panel | Mandatory | Point-in-time assembly of identity, session, lifecycle, market observations, action state, context fields required by scope, and typed quality |
| Classification history | Important; Mandatory when used | Point-in-time sector and industry values with unknown states; research using them is blocked until admitted |
| Index membership history | Important; Mandatory when used | Point-in-time membership and supplied weights; research using them is blocked until admitted |
| Fundamentals history | Important | As-reported values, publication time, revision/restatement chain, units, currency, and staleness |
| Earnings and event history | Important | Event identity, public time, timestamp precision, revision/cancellation state, and session mapping |
| Intraday and quote observations | Future | Separate capability and timing audit when an approved research need exists |

“Mandatory when used” means the blocking capability and honest unavailable state must exist before release. The platform shall not fabricate a missing history merely to satisfy the initial scope.

### 16.3 Security-day observable panel

The minimum panel contains one deterministic row for each candidate security-session, not merely each surviving observation. It shall contain or reference:

- stable security, issuer, listing, exchange, and calendar identities;
- session date, open and close timestamps, research cutoff, and session state;
- lifecycle state and historical-universe eligibility;
- raw open, high, low, close, and volume where supplied;
- explicit raw/adjusted/return basis;
- applicable corporate-action and terminal-event state;
- point-in-time sector, industry, index, and peer identifiers required by the approved scope;
- value state, missing-reason code, and quality state;
- source dataset and record references; and
- snapshot, policy, lineage, and admissibility references.

The panel shall not contain future returns, forward event outcomes, future memberships, target variables, post-outcome ranks, or any other label. Outcomes are produced only by a separately governed experiment-specific process so that they cannot enter features accidentally.

### 16.4 Request interface

A feature-ready view request shall specify:

- immutable admitted research snapshot;
- exact universe-policy version;
- supported market, exchanges, security types, and date range;
- observation clock and cutoff policy;
- required canonical fields;
- price and corporate-action basis;
- classification, industry, and membership systems;
- revision and staleness policies;
- point-in-time join version;
- missing, halted, newly listed, inactive, and delisted treatment; and
- requested output schema version.

No default may silently select current symbols, current classifications, current constituents, current fundamentals, an adjusted price series, or the newest MDM extract.

### 16.5 Response interface

The response shall provide:

- immutable view ID;
- deterministic data ordered by declared keys;
- complete manifest and fingerprints;
- bound source snapshot and partition IDs;
- schema, universe, calendar, action, join, and cutoff versions;
- row, security, and session counts;
- population flow and exclusions;
- typed missingness and quality profiles;
- admissibility certificate and conditions;
- validation and join-audit reports;
- lineage record; and
- warnings, scope restrictions, and expiry/recheck triggers.

Only `Admissible` or correctly scoped `Admissible conditional` views may enter Stage 2. Quarantined data are exposed only through a controlled diagnostic path and cannot be used for discovery.

### 16.6 Determinism and storage

For the same source snapshot, request, rules, and software version, construction shall produce the same ordered rows, encoded values, population counts, and fingerprints. Concurrency or partition order must not change the scientific output.

The initial physical representation should remain simple: columnar immutable partitions plus manifests and validation reports. A local embedded analytical reader is sufficient for the expected daily first-year scale. Generated caches and indexes may be rebuilt; they are not authoritative scientific artefacts.

### 16.7 Failure and priority

The view build fails if any mandatory source is inadmissible, any requested scope exceeds an admission certificate, a point-in-time join fails, an outcome field crosses the boundary, lineage is incomplete, or replay changes the fingerprint.

- **Mandatory:** daily security-session panel, population manifest, observed-price and return-consistent views, outcome firewall, typed quality, deterministic replay.
- **Important:** as-reported fundamentals, events, quote summaries, shares/float, currency normalisation, and richer aggregate views when an approved hypothesis needs them.
- **Future:** live mutable feature stores, analyst-defined joins against raw MDM, streaming panels, and broad multi-asset schemas.

## 17. End-to-end data flow

**Priority: Mandatory**

The minimum governed flow is:

`MDM capability contract → frozen extraction request → source capture/reference → canonicalisation → snapshot sealing → validation → scoped admissibility → historical population construction → governed point-in-time joins → feature-ready view → Stage 2 Feature Generation → Stage 2.5 Feature Validation → Stage 3 eligibility`

### 17.1 Planning and capability check

1. A planned research family declares required observations, population, dates, clocks, and context.
2. The gateway checks the MDM capability contracts.
3. Unsupported facts remain `Unavailable`; the research scope is narrowed formally or the work is blocked.
4. Required Important capabilities are activated only when the registered programme needs them.

### 17.2 Acquisition and canonicalisation

1. The request binds exact fields, scope, MDM version, revision policy, and expected schema.
2. MDM returns a versioned payload or immutable reference.
3. The source capture is fingerprinted before transformation.
4. Canonicalisation applies only deterministic, versioned mappings.
5. Raw values remain recoverable; no silent repair or imputation occurs.
6. Partial or semantically unexpected captures are quarantined.

### 17.3 Sealing, validation, and admission

1. Complete partitions and inventories are staged privately.
2. The immutable manifest is generated.
3. Content and manifest fingerprints are computed.
4. Snapshot, temporal, identity, calendar, corporate-action, universe, and coverage checks run.
5. A scoped admissibility certificate is issued or the snapshot remains blocked.
6. Publication occurs atomically only after sealing and decision.

### 17.4 Assembly and release

1. The historical candidate population and session spine are constructed.
2. Universe eligibility and every exclusion reason are evaluated point in time.
3. Governed joins attach only applicable and available facts.
4. The observable panel and separate return-consistent view are built.
5. Output-field inspection enforces the outcome firewall.
6. Deterministic replay and anti-bias sentinels pass.
7. The admitted immutable view is released to Stage 2 with its evidence bundle.

### 17.5 Corrections

1. An MDM correction, schema change, or local mapping defect is detected.
2. The prior snapshot remains immutable.
3. A successor source or mapping version is created and independently admitted.
4. A deterministic difference report identifies affected fields, identities, securities, and dates.
5. Lineage identifies dependent views and governed experiments.
6. The frozen governance process decides quarantine, revalidation, rerun, evidence weakening, supersession, or retraction.

The data foundation reports impact; it does not rewrite scientific conclusions automatically.

## 18. Snapshot lifecycle and release control

**Priority: Mandatory**

### 18.1 Lifecycle

The canonical path is:

`Requested → Building → Captured → Validating → Validated pending admission → Sealed admissible / Sealed conditional / Quarantined / Rejected`

Exception transitions are `Building → Incomplete`, `Validating → Validation failed`, and an already sealed snapshot may later become `Quarantined`, `Superseded`, or `Data-invalidated`. “Active for new work” is a mutable recommendation recorded outside the scientific binding; it is not a snapshot state and experiments never bind to it.

Rules:

- each attempt has a permanent identity;
- a partial payload never becomes a usable snapshot;
- sealing is atomic and irreversible;
- admitted payloads and manifests are never edited;
- correction creates a successor, not a replacement;
- supersession changes the recommendation for new work, not historical experiment bindings;
- conditional admission is enforced mechanically at request time;
- quarantined, rejected, superseded, and invalidated artefacts remain retained for audit; and
- deletion is prohibited while any governed artefact references the snapshot.

### 18.2 Atomicity across MDM families

The priority order is:

1. use one immutable MDM snapshot spanning all required families;
2. otherwise bind each family to exact versions under a common documented cutoff and validate cross-family coherence;
3. if coherent reconstruction cannot be established, block the combined snapshot.

Project EDGE shall not claim transaction-level atomicity that MDM does not supply.

### 18.3 Publication rule

The build location is not a downstream interface. A snapshot or view becomes visible to ordinary consumers only after:

- all declared partitions exist;
- inventories agree;
- fingerprints verify;
- required validation completes;
- lineage resolves;
- the admissibility decision is signed; and
- the manifest is sealed.

Convenience labels such as `recommended` may support planning, but no preregistration, feature view, experiment, or result may bind to such a mutable label.

### 18.4 Retention and reproducibility

If MDM guarantees exact retrieval by immutable source version, Project EDGE may retain the source reference and manifest rather than duplicate the payload. If exact retrieval is not guaranteed, the exact bounded MDM extract shall be retained in the repository when authorised. A retained extract remains MDM-sourced; it is not a second market-data source.

If neither exact retrieval nor authorised immutable retention is possible, the capability is not reproducible enough for registered scientific use and remains unavailable.

### 18.5 Practical deferrals

- **Important:** partition reuse and incremental successor construction when measured storage or runtime justifies them; automated field-level impact summaries as experiment volume grows.
- **Future:** snapshot branch/merge semantics, distributed transaction coordination, geographically replicated serving, complex content-addressed catalogues, and automatic rerunning of all descendants.

## 19. Failure handling and scientific incident response

**Priority: Mandatory**

### 19.1 Fail-closed principle

Failure shall be contained at the narrowest scientifically defensible scope, but it shall never be hidden by silently reducing the research population, substituting a source, guessing an identity, changing an availability time, or imputing a value.

A local quarantine is permissible only when the affected securities, fields, dates, and downstream uses can be identified exactly and the remaining scope still satisfies its preregistered population and coverage rules. Narrowing scope merely to pass validation is prohibited.

### 19.2 Failure matrix

| Failure | Required response | Downstream consequence |
|---|---|---|
| MDM unavailable | Record failed attempt and source/version request; retry only as a new attempt | No snapshot publication; no implicit cached `latest` fallback |
| Unsupported MDM capability | Mark the capability `Unavailable` with reason and scope | Dependent research is narrowed formally or blocked |
| Partial extraction | Retain incomplete payload and attempt metadata under quarantine | No usable snapshot ID |
| Unexpected schema or semantic change | Stop canonicalisation; quarantine; compare capability and schema contracts | New review and mapping version required |
| Source version not provable | Reject sealing | Dataset cannot support governed research |
| Fingerprint mismatch | Quarantine the artifact and investigate integrity | All dependent publication and execution blocked |
| Duplicate canonical key | Quarantine affected dataset; retain duplicates and evidence | No arbitrary de-duplication |
| Missing or conflicting identity | Quarantine affected identities and dates | No ticker-based guess; population impact assessed |
| Missing or ambiguous availability time | Mark field unavailable for timing-sensitive historical use | Point-in-time join and dependent research blocked |
| Calendar gap or ambiguity | Quarantine affected venue/session scope | Security-day construction and horizons blocked |
| Impossible or suspect market value | Preserve and flag the source value; investigate MDM status and actions | Scoped admission only if predefined rules permit |
| Corporate-action inconsistency | Quarantine return-consistent outputs across affected windows | Raw observations may remain usable only for admitted raw-price uses |
| Historical-universe attrition | Reject or quarantine population view | Discovery blocked until survivor-complete accounting is restored |
| Join future-leakage sentinel | Revoke or reject affected join/view admission | All descendants traced and blocked |
| Multiple eligible as-of matches | Fail the join unless an existing scientific precedence rule applies | No arbitrary row selection |
| Empty result | Treat as failure unless the frozen request explicitly permits and explains it | No successful empty publication by default |
| Deterministic replay mismatch | Quarantine snapshot or derived view | Reproducibility gate fails |
| MDM correction after admission | Preserve prior artifact; build successor; issue difference and impact report | Existing work remains bound; governance reviews affected evidence |
| Defect discovered after experimental use | Quarantine or revoke admission; freeze unstarted dependent work; trace descendants | Frozen governance handles rerun, evidence update, debt, supersession, or retraction |
| Storage/publication interruption | Preserve attempt record and staged evidence | Publish nothing partially |
| Downstream request outside admitted scope | Reject explicitly with violated scope or condition | No automatic widening or substitute dataset |

### 19.3 Failure record

Every failed attempt shall retain:

- permanent attempt ID;
- initiating request and owner;
- exact MDM, schema, mapping, and policy versions;
- start and failure time;
- affected datasets, partitions, records, securities, and dates where known;
- failure classification and diagnostic evidence;
- whether any partial payload was received;
- whether any downstream artifact was exposed;
- quarantine location and integrity fingerprint;
- reviewer decision;
- remediation or successor reference; and
- downstream consequence.

Retries do not erase prior failures. A later successful attempt links to, but does not replace, the failed attempt.

### 19.4 Correction and invalidation

Corrections are ordinary scientific events, not exceptional mutable updates. A correction workflow shall:

1. detect a changed source record, schema, mapping, or policy;
2. preserve the old snapshot and admission decision;
3. create a successor artifact;
4. compare records and fingerprints deterministically;
5. classify changes by scientific risk;
6. trace affected views, features, experiments, and findings through lineage;
7. prevent new execution on a revoked or quarantined view; and
8. hand the impact record to the frozen governance framework.

Availability-time, identity, listing/delisting, calendar, corporate-action, classification, membership, raw OHLCV, or fundamental-revision corrections receive high-priority review because they can change population or historical knowledge.

## 20. Validation and anti-bias sentinel suite

**Priority: Mandatory**

### 20.1 Validation layers

Validation is performed at four distinct layers:

1. **Source capture validation:** completeness, source version, schema, transport, counts, and fingerprints.
2. **Canonical dataset validation:** types, units, keys, temporal intervals, identity, domain invariants, and typed missingness.
3. **Cross-dataset validation:** calendar, lifecycle, actions, universe, classifications, memberships, revisions, and point-in-time consistency.
4. **Released-view validation:** join audits, population flow, outcome firewall, lineage, admission scope, deterministic replay, and sentinel tests.

Passing one layer cannot compensate for failing another.

### 20.2 Mandatory anti-bias sentinels

Synthetic, fixed, non-outcome-bearing fixtures shall deliberately attempt to introduce each major failure. They test platform behaviour without consuming discovery evidence.

| Sentinel | Required result |
|---|---|
| Future observation with a valid security ID | Excluded from every earlier cutoff |
| Completed daily close offered before session close | Rejected |
| After-hours public release | Unavailable at the earlier close cutoff under the declared policy |
| Old reporting period with a later restatement | Original historical vintage retained before restatement availability |
| Unknown publication time | Conservative documented lag or inadmissible result; never favourable imputation |
| Reused ticker for a different security | No cross-security linkage |
| One security with a dated ticker change | Continuous stable security identity where MDM establishes continuity |
| Multiple share classes of one issuer | Separate securities with explicit issuer relationship |
| Future sector reclassification | Earlier observations retain the earlier or unknown classification |
| Future index addition | No membership before the effective and available interval |
| Current constituent list projected backward | Rejected as a historical universe source |
| Delisted security | Retained in prior eligible populations and given a terminal state |
| Later split presented beside earlier raw prices | Raw observed prices remain unchanged |
| Return crossing a split or cash distribution | Return components reconcile to the governed action treatment |
| Corporate-action revision or cancellation | Successor snapshot created; prior snapshot unchanged |
| Holiday, early close, DST, or timezone boundary | Observation maps to the exact governed session and cutoff |
| Duplicate effective records | Join fails rather than choosing arbitrarily |
| Missing as-of match | Left row retained with a typed reason |
| MDM schema change | New capture quarantined pending contract review |
| Interrupted extraction | No partial snapshot published |
| Changed sealed payload | Fingerprint failure blocks use |
| Later MDM correction | Old snapshot remains replayable; new snapshot has a new identity |
| Outcome field offered to the observable panel | Rejected by the outcome firewall |
| Quarantined value requested by ordinary feature generation | Access denied |
| Unsupported field requested | Explicit unavailability; no alternate source or proxy substitution |

Every sentinel applicable to an activated capability must pass before its first scientific release. Failure blocks that release.

### 20.3 Deterministic replay tests

The foundation shall demonstrate:

- identical source snapshot and request produce identical capture inventory;
- identical canonical input, mapping, and software version produce identical canonical fingerprints;
- identical universe inputs and policy produce the same candidate/eligible rows and reasons;
- identical join inputs and rule produce identical match decisions and audit counts;
- identical feature-ready request produces identical row ordering, values, and fingerprints; and
- a historical snapshot remains reproducible after a successor is admitted.

### 20.4 Coverage and population tests

Coverage is reported at both the candidate-population and eligible-population levels. Required tests include:

- entries, exits, delistings, inactive securities, and terminal outcomes;
- missingness by date, exchange, security type, lifecycle, size, liquidity, and available sector;
- field-specific and vintage-specific coverage;
- newly listed and short-history populations;
- unexplained population discontinuities;
- action-window attrition;
- current-survivor-only comparisons as a diagnostic; and
- the fraction and characteristics of quarantined or unresolved identities.

An apparently high overall coverage rate is insufficient if missingness is concentrated in small, distressed, inactive, or delisted securities.

### 20.5 Acceptance evidence

Test definitions, fixtures, results, expected outcomes, software version, environment, reviewer, and fingerprints become permanent snapshot or capability evidence. Test reports are append-only and are referenced by the admissibility certificate.

## 21. Priority, deferral, and activation register

### 21.1 Mandatory before the first daily phenomenon experiment

- one read-only MDM-only gateway and capability contract;
- a ratified initial market, security population, daily research cutoff, and session convention;
- version-pinned bounded extraction;
- immutable source capture or exact MDM replay reference;
- stable security and required issuer/listing identity;
- lifecycle history, delistings, and terminal outcomes;
- MDM-sourced daily calendars;
- raw daily OHLCV with explicit units, currency, status, and price basis;
- ordinary corporate actions, action detection, and return reconciliation;
- historical candidate-population and universe manifests;
- temporal, schema, artifact, and policy versioning;
- immutable snapshots, manifests, fingerprints, correction lineage, and deterministic replay;
- governed point-in-time joins;
- scoped admissibility and quarantine enforcement;
- typed lifecycle, value, missingness, and quality states;
- an outcome-free feature-ready security-day panel;
- source-to-view lineage and descendant lookup;
- fail-closed release controls; and
- applicable anti-bias sentinels and acceptance tests.

### 21.2 Important within the first 12 months when research activates them

| Capability | Activation condition |
|---|---|
| Sector and industry history | Before any sector-, industry-, peer-, rotation-, or sector-neutral research; becomes Mandatory for that scope |
| Index membership and historical weights | Before index-relative or constituent research; becomes Mandatory for that scope |
| As-reported fundamentals | Before any accounting, valuation, quality, or fundamental-conditioned research |
| Earnings and corporate-event history | Before event-window or earnings-effect research |
| Shares outstanding and float history | Before turnover, issuance, float, ownership, or capacity-normalised measures |
| Quote/spread summaries | Before hypotheses whose interpretation materially depends on spread or quote liquidity |
| Multi-currency normalisation | Before a selected population contains incomparable currencies |
| Unscheduled closure history | Before affected venue-periods are included if not already in daily calendars |
| Complex-action economic treatment | Before research includes an unsupported action type across a return or continuity window |
| Incremental snapshot construction | When measured extraction or storage cost makes full bounded rebuilds materially burdensome |
| Automated correction-impact traversal | When snapshot and experiment volume makes manual lineage review unreliable |

The ability to report each unimplemented capability as `Unavailable` and block dependent use is itself Mandatory.

### 21.3 Safely postponed — Future

The following are explicitly outside the minimum first-year foundation unless a separately approved scientific requirement changes scope:

- intraday bars, ticks, quotes, order books, auction phases, and detailed halt reconstruction;
- streaming, real-time, and low-latency ingestion;
- broker, execution, position, portfolio, strategy, and live-trading data paths;
- options, derivatives, stock-loan, news, social, alternative, or non-MDM data;
- global beneficial-ownership and universal legal-entity graphs;
- investor-specific tax and tax-lot corporate-action treatment;
- exhaustive international-market and calendar coverage;
- a generic multi-vendor adapter or reconciliation framework;
- an unrestricted temporal-query language;
- a universal bitemporal database engine;
- enterprise workflow orchestration and event buses;
- a distributed lakehouse or cluster query fabric;
- a lineage graph database and universal per-cell lineage;
- live mutable feature stores;
- machine-learning anomaly detection or automated data repair;
- graphical catalogue and monitoring products;
- geographic replication and high-availability serving; and
- automatic scientific reinterpretation or rerunning after corrections.

Deferred capabilities shall not be approximated with current values, another source, or undocumented analyst transformations. Research requiring them remains blocked.

## 22. Minimum scientifically complete implementation roadmap

The roadmap deliberately delivers one bounded, reliable daily research path before adding data breadth.

### Phase 0 — Ratify scope and prove MDM capability

**Priority: Mandatory**

Deliver:

- one initial market or precisely bounded market set;
- eligible security types and share-class policy;
- daily observation clock and information cutoff;
- session and return-horizon conventions;
- MDM capability contracts for identity, lifecycle, inactive securities, delistings, calendars, OHLCV, actions, classifications, memberships, versions, revisions, and retention;
- exact supported and unavailable first-year fields; and
- a decision on native MDM replay versus retained bounded extracts.

Exit gate:

- the initial scientific population and clocks are unambiguous;
- every Mandatory capability is supported or its dependent pilot scope has been removed formally; and
- no undocumented MDM behaviour is assumed.

### Phase 1 — Establish immutable MDM intake

**Priority: Mandatory**

Deliver:

- the single read-only gateway contract;
- bounded version-pinned requests;
- attempt records and failure handling;
- source manifests, schema fingerprints, row/partition inventories, and content fingerprints;
- sealed source capture or exact replay reference; and
- basic successor and correction comparison.

Exit gate:

- a fixed request can be retrieved or reconstructed exactly;
- incomplete and incompatible extracts fail closed; and
- another source cannot enter the path.

### Phase 2 — Establish the temporal and identity spine

**Priority: Mandatory**

Deliver:

- canonical four-clock semantics and availability precision;
- stable security, issuer, listing, venue, symbol, and lifecycle history;
- daily exchange calendars and deterministic session mapping;
- raw daily market observations with explicit basis and quality states; and
- identity and calendar sentinels.

Exit gate:

- ticker reuse, ticker changes, share classes, venue changes, holidays, early closes, timezone boundaries, and inactive/delisted identities resolve deterministically or quarantine explicitly.

### Phase 3 — Establish actions, returns, and historical population

**Priority: Mandatory**

Deliver:

- corporate-action ledger;
- observed-price and return-consistent views;
- distribution and terminal-return components;
- complex-action detection and quarantine;
- daily candidate-population state;
- versioned universe policy and exact universe manifests; and
- survivor, action, delisting, and terminal-event tests.

Exit gate:

- corporate-action arithmetic reconciles within frozen tolerances;
- unsupported action windows are prevented from contaminating continuity-dependent work; and
- current survivors cannot determine a historical population.

### Phase 4 — Establish governed point-in-time assembly

**Priority: Mandatory**

Deliver:

- registered as-of join rules;
- classification and index-membership histories required by the selected pilot scope;
- explicit unknown and not-yet-public states;
- join audit reports and future-record sentinels;
- immutable universe and security-day observable panels; and
- outcome firewall.

Exit gate:

- future classifications, future fundamentals, future constituents, current master data, and completed future observations cannot enter an earlier research row;
- no multiple match is selected arbitrarily; and
- unmatched rows remain visible and typed.

### Phase 5 — Establish admission, replay, and impact control

**Priority: Mandatory**

Deliver:

- layered validation reports;
- scoped admissibility certificates;
- quarantine and revocation enforcement;
- source-to-view lineage and descendant lookup;
- deterministic snapshot and view replay;
- correction successor and impact records; and
- the complete applicable anti-bias sentinel suite.

Exit gate:

- every released row resolves to MDM source, stable identity, session, cutoff, quality, transformation, and snapshot;
- an independent reconstruction produces the same fingerprint;
- a correction does not mutate prior work; and
- every applicable Mandatory acceptance test passes.

### Phase 6 — Release the first research dataset

**Priority: Mandatory**

Deliver:

- one immutable, admitted, outcome-free daily feature-ready view;
- its exact universe, price basis, return basis, calendar, cutoff, join, and missingness policies;
- complete population-flow, quality, validation, lineage, and admission evidence; and
- a handoff contract to Stage 2 and Stage 2.5.

Exit gate:

- the view can support bounded daily price, volume, volatility, trend, gap, liquidity-proxy, or breadth phenomena without fundamentals or intraday data;
- the frozen governance layer can bind it by exact version and block it after expiry, quarantine, or revocation; and
- no strategy, optimisation, broker, portfolio, or live-trading component has been introduced.

### Phase 7 — Activate only evidence-backed extensions

**Priority: Important**

After the first reliable path exists, activate fundamentals, earnings/events, shares/float, quote summaries, additional classifications, currencies, markets, or complex actions only when a registered first-year scientific need requires them. Each activation repeats the capability, temporal, admissibility, lineage, and sentinel gates for that domain.

## 23. Release acceptance checklist

The first phenomenon-discovery experiment is blocked until every applicable Mandatory statement below is true.

### 23.1 Source, snapshot, and reproducibility

1. Every market fact derives solely from MDM.
2. Every source request binds exact fields, scope, and version.
3. Exact replay or authorised immutable retention is proven.
4. Captures, schemas, partitions, manifests, and views have verified fingerprints.
5. An incomplete capture cannot be published.
6. An MDM correction creates a successor without changing the predecessor.
7. The same inputs and rules reproduce the same ordered output and fingerprint.

### 23.2 Time, identity, and population

8. Every relevant record preserves applicable economic, publication, availability, effective, and vintage semantics.
9. Every research row has an explicit session and cutoff.
10. Stable identity survives symbol change and prevents ticker-reuse collisions.
11. Share classes, issuer relationships, listings, and venues remain distinguishable.
12. Pre-listing, active, halted, suspended, inactive, delisted, and terminal states are represented explicitly.
13. Historical populations include eligible inactive and delisted securities.
14. Every inclusion and exclusion has a point-in-time reason.
15. Current constituents, classifications, and security masters cannot be projected backward.

### 23.3 Calendars, actions, and joins

16. Holiday, early-close, closure, timezone, and DST cases map correctly.
17. Raw price history and return-consistent history have explicit distinct bases.
18. Splits, distributions, cancellations, successor events, and terminal outcomes reconcile or quarantine.
19. Unsupported complex-action windows cannot enter continuity-dependent work.
20. A future or not-yet-public record cannot pass an as-of join.
21. A later revision cannot replace the value historically available.
22. Multiple eligible matches fail; missing matches remain typed and counted.
23. Point-in-time join audits are complete and fingerprinted.

### 23.4 Admission, lineage, and downstream safety

24. Every released scope has a current admissibility certificate.
25. Conditional admission is mechanically confined to its declared scope.
26. Look-ahead, identity, survivor, source, lineage, or replay defects cannot receive conditional admission.
27. Missingness and quality are typed and stratified; null does not mean zero.
28. No source value has been silently repaired, deleted, winsorised, or imputed.
29. Every released value resolves through complete source-to-view lineage.
30. A corrected source identifies dependent views and governed experiments.
31. Quarantined, revoked, expired, or out-of-scope data cannot enter ordinary feature generation.
32. The feature-ready observable panel contains no forward outcomes or strategy artefacts.
33. Every applicable anti-bias sentinel passes.
34. The frozen Milestone 1 governance layer can bind the snapshot and view by immutable IDs and enforce their admissibility state.

## 24. Readiness assessment and implementation decision

### 24.1 Is the specification complete enough to begin implementation?

Yes. This specification is sufficiently complete to begin implementing the first MDM Data Foundation components. It defines the scientific boundary, the twelve required responsibilities, logical interfaces, temporal invariants, validation, admission, lineage, failure behaviour, explicit deferrals, and measurable release gates without prescribing a speculative enterprise platform.

### 24.2 Is the platform ready to begin phenomenon research now?

No. Design completion is not data admission. Phenomenon research must remain blocked until Phases 0–6 are complete for one bounded daily scope and the release checklist passes.

The first immediate action is Phase 0: ratify the initial market, security types, research cutoff, session convention, and actual MDM capabilities. This is an implementation input decision, not a redesign of the frozen Foundation or governance specification.

### 24.3 Minimum initial research envelope

Once the release gate passes, the scientifically defensible initial envelope is:

- daily observations;
- one bounded admitted equity population;
- stable identity and complete lifecycle accounting;
- raw and return-consistent price views;
- volume and daily liquidity proxies supported by MDM;
- historical universe and breadth construction;
- point-in-time classifications or memberships only where admitted; and
- deterministic feature-ready inputs for Stage 2 and Stage 2.5.

Fundamentals, earnings events, intraday behaviour, complex institutional measures, multiple currencies, and additional markets remain unavailable until their specific Important capabilities have been activated and admitted.

### 24.4 Governance sufficiency

Implementation has not revealed a genuine deficiency requiring the frozen governance framework to be expanded. The data foundation supplies the immutable snapshot, feature-view, validation, lineage, admission, correction, and failure evidence that Milestone 1 expects. Any future mismatch shall be raised as a concrete governance deficiency rather than used as a reason to redesign governance prospectively.

### 24.5 Final implementation principle

Build the shortest complete scientific path: one MDM source, one bounded daily scope, stable identities, exact clocks, immutable snapshots, survivor-complete populations, governed joins, explicit quality, deterministic replay, and fail-closed release. Add breadth only when a registered research need proves it necessary.
