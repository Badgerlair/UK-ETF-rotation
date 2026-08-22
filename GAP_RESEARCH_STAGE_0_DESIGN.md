# Project EDGE — Gap Research Programme
## Stage 0 Scientific Foundation and Architecture Review

**Document status:** Stage 0 design proposal  
**Document version:** 1.0  
**Review date:** 2026-08-03  
**Decision status:** Recommended for Stage 0 approval; implementation is not authorised  
**Repository:** D:\codex\equity_quant_research_platform  
**Scope:** US equity opening-gap phenomena  
**Out of scope:** trading strategies, entry and exit rules, portfolio construction, parameter optimisation, execution systems, alerts, and live trading  
**Authoritative market-data boundary:** Market Data Manager (MDM) only  
**Permitted regime boundary:** Universal Regime Engine (URE), read-only classifications only  

---

## Executive determination

The existing repository contains a strong scientific foundation but no implemented research platform. At audit start, the only authoritative substantive scientific design identified was PROJECT_EDGE_FOUNDATION_DOCUMENT.md. It establishes the right scientific control system: phenomenon-first research, point-in-time data, immutable experiment specifications, explicit evidence states, separated discovery and confirmation, dependence-aware inference, replication, and preservation of negative results. Those principles can be reused without modification.

The recommended architecture is a **dedicated Gap Research subsystem inside Project EDGE**, not a separate platform and not a collection of gap-specific scripts. Shared scientific services should remain owned by the Project EDGE core. The Gap Research subsystem should own only the semantics and measurements peculiar to opening gaps.

MDM does not yet expose every dataset or contract required for defensible gap research. Its daily and extended-hours minute archives are a substantial starting point, but the current repository state does not yet provide a certified combination of:

- official session calendars and opening semantics;
- complete security and ticker lifecycle history;
- complete corporate-action and delisting histories;
- broad point-in-time company size and classification history;
- halt history and legally applicable LULD history;
- uniformly acquired quote data;
- immutable, clean-room dataset snapshots with no downstream-project fallback.

These gaps do not justify importing data from any prohibited project. They define an MDM extension specification and implementation gate.

URE can be incorporated only through a narrow, classification-only, read-only interface. Gap events must be constructed independently of URE. A URE classification may be joined only if it was available before the relevant gap observation cutoff, normally by lagging a daily state to the preceding completed session. Policy, exposure, permission, or trading-action fields must never enter the subsystem.

No strategy is proposed by this document. The scientific unit is an observed gap event and its subsequent price path, not a trade.

### Primary decisions

| Question | Determination |
|---|---|
| Can the existing repository support the programme? | Conceptually yes; operationally not yet. It contains a detailed scientific constitution, not executable components. |
| What can be reused without modification? | The scientific ontology, control plane, point-in-time rules, registries, evidence pipeline, holdout rules, validation principles, replication rules, and negative-result requirements. |
| What requires extension? | MDM contracts and coverage, a classification-only URE export, shared executable EDGE services, and gap-specific event, feature, outcome, and diagnostic modules. |
| Extend the current architecture or build separately? | Extend Project EDGE with a bounded Gap Research subsystem. Do not create an independent architecture or repository. |
| Is current MDM coverage sufficient? | No. Raw price coverage is useful, but several scientific-critical datasets and contracts were not identified as certified complete and fit for Project EDGE use. |
| May URE generate or filter events? | No. It is an explanatory covariate only. |
| May Stage 0 tune thresholds or optimise returns? | No. Stage 0 defines measurements, estimands, controls, and future gates only. |

---

# 1. Scientific objectives

## 1.1 Central research question

The programme asks:

> Under what point-in-time observable market conditions are US equity opening gaps more likely to continue, reverse, fill, or exhibit persistent directional price paths?

The question is deliberately distributional and conditional. It is not “which gap setup makes money?” and it does not presume that a stable or actionable edge exists.

## 1.2 Scientific objects

The primary object is a **gap event**:

- a security on a defined primary-market session date;
- an authoritative prior reference price;
- an authoritative opening observation;
- the information set available at one or more frozen cutoffs;
- a subsequent price path observed over prespecified horizons;
- full provenance, quality, and censoring metadata.

The primary quantities of interest are:

1. the conditional distribution of signed post-open returns;
2. the probability and timing of partial or complete gap fill;
3. the probability and magnitude of continuation;
4. the magnitude and timing of adverse and favourable path excursions;
5. path persistence, reversal, and terminal retention;
6. how those quantities vary with gap size, premarket behaviour, company state, catalysts, market context, and pre-existing regimes.

## 1.3 Phenomena, not trades

Continuation, reversal, fill, and trend are path properties. They must be measured without assuming an entry, stop, target, position size, execution price, or transaction-cost model.

The following are not Stage 0 research outputs:

- a “gap-and-go” rule;
- a ranking or alert score;
- buy, sell, long, short, or avoid decisions;
- optimised opening-range lengths;
- optimised gap, volume, float, or price thresholds;
- backtested profit and loss;
- portfolio or risk limits;
- brokerage or live-market integration.

If a future study finds a phenomenon, it remains evidence about a distribution until it passes the separate evidence and governance gates required for any later strategy research.

## 1.4 Required scientific properties

Every future claim must be:

- **point-in-time valid:** no input was unavailable at its stated cutoff;
- **reproducible:** the exact data snapshots, code, configuration, and environment can be reconstructed;
- **falsifiable:** the claim includes a null, rival explanations, and failure criteria;
- **dependence-aware:** inference reflects common market dates, repeated issuers, overlapping horizons, and clustered catalysts;
- **multiplicity-aware:** the research family and search budget are registered;
- **role-separated:** exploration, confirmation, and replication use distinct time blocks and governance;
- **resolution-aware:** timestamps and path order are not asserted more precisely than the source permits;
- **negative-result preserving:** failed, null, and contradictory findings remain first-class records.

## 1.5 Core estimands

The programme should begin with estimands that do not require arbitrary binary thresholds:

- conditional mean, median, quantiles, and full distribution of signed post-open return;
- cumulative incidence and time-to-gap-fill curves;
- conditional distributions of gap retention at fixed horizons;
- conditional MFE and MAE distributions;
- interaction contrasts between a predeclared market state and a continuous gap exposure;
- changes in those quantities across future, non-overlapping time blocks.

Binary labels may be derived for communication after their definitions and negligible-movement tolerances are preregistered. Continuous outcomes remain primary.

## 1.6 Initial hypothesis families

Stage 0 authorises the definition, not the testing, of these broad families:

1. **Gap magnitude:** continuation and fill vary smoothly with action-neutral gap magnitude.
2. **Premarket participation:** volume, dollar volume, path persistence, and volatility modify the post-open distribution.
3. **Catalyst context:** timestamp-valid earnings, guidance, analyst, filing, and news events are associated with distinct path distributions.
4. **Market alignment:** gaps aligned with broad-market, sector, or peer moves differ from idiosyncratic gaps.
5. **Company and liquidity state:** market capitalisation, float, turnover, listing age, and microstructure affect path behaviour and measurement reliability.
6. **Regime interaction:** pre-existing URE trend, volatility, breadth, and risk states modify conditional distributions.
7. **Intraday state transition:** measurements at fixed post-open landmarks update the distribution of later outcomes.
8. **Temporal decay:** gap information may persist, decay, or reverse across the close and later sessions.

Each future experiment must narrow one family to an explicit exposure, comparator, outcome, horizon, population, estimand, and falsification rule.

## 1.7 Scientific success and failure

Scientific success does not require a positive effect. Stage 0 succeeds if it enables the programme to establish, with calibrated uncertainty, any of the following:

- a stable conditional phenomenon;
- a bounded phenomenon that exists only in stated populations or eras;
- a null result within a meaningful equivalence margin;
- a result explained by data quality, corporate actions, market-wide shocks, or other rival mechanisms;
- a discovery that fails confirmation or replication.

The last three are valid and must be retained.

## 1.8 Initial population constitution

The recommended primary population for the first general gap programme is:

- USD-denominated ordinary common shares and common-share REITs whose primary listing is on a recognised US national securities exchange;
- all historically eligible securities, including subsequently inactive or delisted names;
- security-level events with stable issuer linkage, multiway dependence treatment, and explicit multiple-share-class diagnostics.

The following should not be pooled into the primary confirmatory population:

- ETFs, ETNs, closed-end funds, preferred shares, warrants, rights, units, and other non-common instruments;
- OTC securities;
- ADRs, until home-market trading hours, foreign-market information, FX, holiday mismatch, and primary/secondary price discovery are available through certified MDM data;
- SPAC common shares and de-SPAC transition windows, which should be retained as a separately registered lifecycle population.

ADRs and SPACs may remain in the broad measurement census with typed population status, but their results are diagnostic or separately chartered. ETF observations may be used as MDM-certified market context, not as company-gap events in the initial population. Gate 0 must ratify this population before code or outcome access; any expansion requires a new versioned population charter.

---

# 2. Existing repository capabilities

## 2.1 Repository inventory

At audit start, the sole pre-existing authoritative substantive scientific artifact identified was:

- PROJECT_EDGE_FOUNDATION_DOCUMENT.md

It contains 2,249 lines of architectural and scientific policy. Supporting transfer/readme artifacts may coexist in the directory, but no executable platform components were identified. The foundation explicitly describes itself as architecture rather than implementation: there are no implemented modules, schemas, test suites, package manifests, databases, data snapshots, or MDM/URE connectors in this repository.

Consequently, “existing capability” means a documented conceptual contract, not runnable software.

## 2.2 Components reusable without modification

The following foundation components are directly applicable to Gap Research:

| Existing foundation component | Gap Research use | Reuse decision |
|---|---|---|
| Phenomenon-first mandate | Prevents premature strategy construction | Reuse unchanged |
| Scientific ontology and evidence states | Tracks conjecture, discovery, validation, replication, contradiction, and rejection | Reuse unchanged |
| One-way evidence pipeline | Controls movement from raw data to knowledge | Reuse unchanged |
| MDM-only data boundary | Provides a single auditable source of market observations | Reuse unchanged |
| Point-in-time and four-clock data model | Separates economic, publication, availability, and vintage time | Reuse unchanged |
| Stable identity and universe contracts | Prevents ticker, issuer, and survivorship errors | Reuse unchanged |
| Corporate-action and dual-price-view principles | Distinguishes observed gaps from action-created discontinuities | Reuse unchanged |
| Feature registry and availability metadata | Makes every variable cutoff-aware and versioned | Reuse unchanged |
| Immutable experiment specifications | Prevents retrospective changes to hypotheses or outcomes | Reuse unchanged |
| Discovery/confirmation separation | Protects holdouts and limits researcher degrees of freedom | Reuse unchanged |
| Dependence and multiplicity controls | Supports valid panel and event inference | Reuse unchanged |
| Walk-forward and replication sequence | Tests temporal stability and independent reproducibility | Reuse unchanged |
| Append-only knowledge base | Preserves all results, including negative findings | Reuse unchanged |
| Strategy firewall | Keeps Stage 0 separate from trading design | Reuse unchanged |

The foundation already identifies gap research as a suitable pilot and expressly calls for correct reference prices, corporate-action treatment, official sessions, premarket assignment, comparison groups, and outcome clocks.

## 2.3 Components that need concrete implementation later

The foundation defines logical responsibilities but intentionally does not implement them. Future work would therefore need concrete, shared services for:

- dataset and snapshot registry;
- security, issuer, ticker, listing, and universe identity;
- calendar and session service;
- corporate-action normalization;
- feature and outcome registries;
- immutable experiment specification storage;
- dataset, code, configuration, and environment fingerprinting;
- discovery and sealed-sample access control;
- inference, diagnostics, and multiplicity accounting;
- experiment artifact production;
- append-only finding and replication records.

These are shared Project EDGE capabilities, not Gap Research-specific services.

## 2.4 Gap-specific additions

The dedicated subsystem will require these logical modules:

1. **Gap measurement constitution:** canonical definitions of reference close, open, action treatment, sessions, delays, and path states.
2. **Gap event builder:** constructs one auditable event record per eligible security-session.
3. **Premarket measurement engine:** computes extended-hours variables at explicit cutoffs.
4. **Gap feature compiler:** derives only registered, point-in-time features.
5. **Catalyst linker:** attaches timestamp-qualified, multi-label event context without forcing single-cause attribution.
6. **Market and peer context builder:** supplies broad-market, sector, and peer-relative variables from MDM.
7. **URE explanatory adapter:** imports a frozen classification-only snapshot through a one-way read-only boundary.
8. **Intraday landmark builder:** creates post-open feature views at fixed, registered landmarks.
9. **Outcome engine:** computes continuation, retention, fill, reversal, excursion, and timing measures independently of feature generation.
10. **Gap-specific quality and falsification suite:** detects action gaps, stale closes, bad opens, sparse premarket observations, timestamp leakage, and other domain errors.
11. **Cohort and comparator builder:** creates point-in-time peers and non-event controls without optimisation.
12. **Gap result packager:** writes standard artifacts into the shared evidence and knowledge systems.

The names above describe responsibilities; they do not prescribe a package layout at Stage 0.

## 2.5 Governance conflict requiring resolution

The current foundation document broadly prohibits access to URE. The present programme brief grants a narrower exception: URE may provide read-only regime classifications.

This should not be handled as an undocumented override. Before implementation, Project EDGE should add an append-only, versioned governance amendment that:

- identifies the authorising decision;
- limits access to classification fields and their provenance;
- prohibits strategy-policy fields and write-back;
- specifies the permitted timing join;
- states that URE does not define events, samples, outcomes, or signals;
- records the amendment version in every affected experiment.

No other repository or previous experiment output is authorised.

## 2.6 Reuse assessment

The current architecture should be extended, because it already supplies the scientific control model required by this programme. A completely separate gap platform would duplicate governance, make evidence states inconsistent, and invite incompatible data semantics. Conversely, embedding gap semantics directly into a generic core would make the core domain-specific.

The correct boundary is:

- shared EDGE scientific infrastructure;
- a dedicated Gap Research domain subsystem;
- MDM and URE adapters with narrow, explicit contracts.

---

# 3. Required architecture

## 3.1 Logical architecture

The recommended information flow is:

    MDM immutable snapshot
        |
        v
    Shared EDGE identity, calendar, action, admissibility, and provenance layer
        |
        v
    Gap event builder --> cutoff-specific feature views
        |                         ^
        |                         |
        +--> separately governed outcome view

    URE classification snapshot --read-only, one-way--> explanatory join

    Feature view + outcome view
        |
        v
    Shared discovery / confirmation / replication services
        |
        v
    Append-only experiment artifacts and knowledge base

The outcome view must not be readable by feature construction. This is a structural control against accidental leakage, not merely a coding convention.

## 3.2 Ownership boundaries

| Responsibility | Owner |
|---|---|
| Market observations and reference datasets | MDM |
| Regime classification production | URE |
| Identity, calendar, availability, action, snapshot, and experiment governance | Shared EDGE core |
| Opening-gap semantics and event construction | Gap Research subsystem |
| Premarket and intraday feature definitions | Gap Research subsystem |
| Gap path outcomes | Gap Research subsystem |
| General statistical inference and multiplicity | Shared EDGE core |
| Evidence states and knowledge records | Shared EDGE core |

## 3.3 Dependency rules

1. Gap Research may read only versioned MDM exports and approved URE classification exports.
2. Gap Research must not read source-project directories, strategy outputs, completed experiment artifacts, or legacy findings databases.
3. MDM exports for this programme must not silently fall back to a downstream or unrelated project data root.
4. URE access must be classification-only and read-only.
5. No URE-derived value may determine whether a gap event exists or enters the base event census.
6. Feature construction must not access outcomes after its cutoff.
7. Every transformation must be registered and versioned.
8. Experiment records are immutable. Corrections create superseding records; they do not mutate history.
9. Data corrections produce a new MDM snapshot and, when material, a new experiment lineage.
10. Research code must not expose trading, execution, optimisation, or live-data interfaces.

## 3.4 Cutoff-specific feature views

One undifferentiated “feature table” is unsafe. The subsystem should expose explicit views:

| View | Latest admissible information | Example use |
|---|---|---|
| Prior-close view | Information available by the previous official close | Ex ante company and market context |
| Premarket view | Information available strictly before a registered pre-open cutoff | Premarket path and catalyst context |
| At-open view | Authoritative opening observation and information available at that instant | Gap magnitude studies |
| Landmark view | Information available at a fixed post-open landmark, such as 5, 15, 30, or 60 minutes | State-transition studies |
| Outcome view | Future observations after the relevant cutoff | Outcomes only; separately permissioned |

A variable must declare the earliest view in which it is valid. Cross-sectional ranks at the open require an additional synchronization rule because securities can open at different times.

## 3.5 Immutable artifact set

Every experiment should produce or reference:

- experiment charter and immutable specification;
- hypothesis family and registry identifiers;
- MDM snapshot and dataset fingerprints;
- URE snapshot and classification version, if used;
- code, configuration, environment, and calendar fingerprints;
- security-universe and event-census fingerprints;
- feature and outcome registry versions;
- data-quality and admissibility report;
- analysis-role assignment for every market date;
- complete attempted-test inventory;
- inference and multiplicity plan;
- results, diagnostics, and sensitivity artifacts;
- deviations and their timing;
- evidence-state decision;
- reproduction and replication links;
- negative-result record where applicable.

## 3.6 Dedicated subsystem decision

A dedicated Gap Research subsystem is warranted because opening gaps have special measurement hazards:

- an observed raw discontinuity may be a split or distribution;
- the previous close may be stale;
- the official open may differ from the first recorded trade;
- a security may open late after a halt;
- extended-hours liquidity can be sparse and venue-dependent;
- catalysts have heterogeneous timestamp precision;
- fill, reversal, and continuation can occur in the same path;
- intraday outcomes are sensitive to data resolution and event ordering.

These hazards deserve explicit domain logic and tests, while identity, governance, validation, and evidence storage remain shared.

---

# 4. Required MDM enhancements

## 4.1 Current MDM capability assessment

The authorised MDM repository was inspected read-only. The findings below describe current observable repository state, not a permanent limitation of MDM.

### Observed candidate assets, subject to certification

- Daily US equity aggregate archive from approximately May 2007 through July 2026.
- Minute US equity aggregate archive from approximately July 2016 through July 2026.
- Minute coverage includes labelled premarket, regular, and after-hours observations.
- Raw split records with execution dates and split factors.
- MDM-owned Benzinga source archives for news, earnings, analyst ratings, and guidance, primarily 2018–2025; timestamp fidelity, coverage, availability semantics, and clean-room lineage remain to be certified.
- A large recent Massive-derived dated reference snapshot series, primarily from May 2021; confirmatory point-in-time usability remains unverified.
- Limited targeted quote caches and code paths capable of reading quote flat files.
- VIX and Treasury-related inputs are visible in the authorised provider repositories, but no certified MDM-owned Project EDGE export was identified. Raw values remain unavailable to Gap Research until such an export passes the MDM contract.

### Material limitations

- The current MDM audit reports duplicate date-symbol rows, suspicious large moves, blank symbols, and zero-volume rows.
- Price data are documented as unadjusted; no certified adjusted/action-neutral view is currently exposed.
- Split data do not constitute a complete corporate-action ledger.
- The canonical point-in-time reference table has effectively absent market-cap, share, float, sector, and industry values.
- A newer Massive dated snapshot series appears to have substantially better recent coverage and begins only in 2021, but its first-availability, revision, replay, identity, and survivorship semantics have not yet established confirmatory point-in-time usability.
- Metadata and status artifacts disagree about point-in-time row counts and readiness.
- Quote data are targeted and sparse rather than a uniform, broad-universe historical archive.
- Lineage and configuration metadata reference unrelated downstream project locations. No such downstream artifact was opened or imported for this review.
- No complete source was identified for official equity calendars, ticker lifecycle, delistings, trading halts/LULD, float history, short interest, borrow, institutional ownership, options, or full PIT membership history.
- Some catalyst timestamps are reconstructed or defaulted and therefore require explicit timestamp-quality handling.
- Some canonical catalyst manifests declare downstream-project provenance and those artifacts must be quarantined from this programme. Candidate MDM-owned source archives remain uncertified until their own timestamp, coverage, availability, and clean-room checks pass.

### Scientific conclusion

MDM contains enough raw material to prototype data audits later, but it does **not** currently satisfy the minimum admissibility contract for general, confirmatory opening-gap research.

Any pre-existing scanner, selected cohort, strategy-oriented export, or downstream cache is inadmissible regardless of its filtering logic. Stage 0 requires a threshold-free base census built solely from certified raw MDM observations, followed by registered analytic cohorts.

## 4.2 Classification definitions

The requested classifications mean:

- **REQUIRED:** absence invalidates the general core study or forces a material, explicitly narrower scientific population.
- **USEFUL:** supports an important planned mechanism or condition, but the core price-path programme can proceed with the associated claim family deferred or bounded.
- **OPTIONAL:** supports a specialised secondary family and is not needed for the core programme.
- **UNNECESSARY:** has no credible role in the proposed programme.

No listed dataset is categorically unnecessary. That does not mean all should be acquired in the first implementation wave.

## 4.3 Dataset classification

| Dataset | Classification | Current MDM assessment | Scientific justification and consequence if absent |
|---|---|---|---|
| Adjusted OHLC prices | REQUIRED | No certified adjusted view identified | Required as a versioned, return-consistent, action-aware companion view. Raw observed prices remain authoritative for the actual opening discontinuity; a globally back-adjusted series must never be the sole gap source. |
| Corporate actions | REQUIRED | Splits exist; complete ledger not identified | Splits, dividends, distributions, rights, spin-offs, mergers, symbol changes, and reorganisations can create false gaps or alter the correct reference basis. |
| Earnings calendar | USEFUL | Candidate MDM-owned Benzinga archive observed; fitness and timing remain uncertified | Essential for earnings-conditioned hypotheses, but an agnostic price-path census can proceed while that family is deferred. Scheduled and actual publication times must be distinguished. |
| Analyst upgrades/downgrades | USEFUL | Candidate MDM-owned Benzinga archive observed; fitness and timing remain uncertified | Supports analyst-catalyst conditioning; not required to establish the unconditional phenomenon. |
| SEC filings | USEFUL | CIK identifiers exist; complete filing-event history not identified | Provides authoritative catalyst timing and helps distinguish news from regulatory disclosures. Filing-conditioned claims must be deferred if absent. |
| News timestamps | USEFUL | Candidate MDM-owned Benzinga source archive observed; canonical downstream-derived artifacts are inadmissible and source fitness remains uncertified | Needed for news-conditioned attribution and for identifying post-open contamination. “Unknown catalyst” is valid only when coverage is adequate. |
| Float history | USEFUL | Not identified | Important for supply, turnover, and small-cap mechanisms. Static current float would create look-ahead bias. |
| Shares outstanding | USEFUL | Recent dated snapshots observed; confirmatory PIT usability is unverified and the canonical table is empty | Supports turnover, float, and size decomposition. Direct certified PIT market cap can support a narrower core size control if shares are unavailable. |
| Market capitalisation history | REQUIRED | Recent dated snapshots observed; canonical table is not ready and confirmatory PIT usability is unverified | Required for stable size measurement, population definition, stratification, and microcap dominance diagnostics. Must be point-in-time and share-class aware. |
| Short interest | USEFUL | Not identified | Supports squeeze and crowded-position hypotheses. Release date, settlement date, and reporting lag are mandatory. |
| Borrow availability | OPTIONAL | Not identified | Valuable for a narrow short-constraint mechanism, but historical coverage and vendor selection effects are severe. |
| Institutional ownership | OPTIONAL | Not identified | Supports ownership-structure hypotheses, but reporting lags and revisions make it unsuitable for the initial core. |
| Sector / industry history | REQUIRED | Canonical data absent; limited proxy data are not full-universe | Required for sector-relative gaps, peer comparators, sector regime, and composition controls. Must be effective-dated rather than current classification backfill. |
| ETF membership | USEFUL | No complete PIT history identified | Supports index/ETF flow and peer hypotheses. Current membership must not be backfilled historically. |
| Option-implied volatility | USEFUL | Not identified | Supports expected-move and uncertainty-normalised hypotheses. The core can use prior realised volatility while this family is deferred. |
| Historical spreads | USEFUL | No broad historical product identified | Critical for measurement-error and liquidity analyses, particularly in illiquid securities. Can be derived from certified quote data. |
| Quote data | USEFUL | Reader and targeted caches exist; broad uniform archive not identified | Needed for opening-quality, spread, and microstructure claims. A restricted liquid-security price-path study may proceed without it, with conclusions explicitly bounded. |
| Level II availability | OPTIONAL | Not identified | Useful for order-book mechanism studies, not for the core event/path programme. Venue coverage and feed changes make it a separate workstream. |
| LULD / trading halt history | REQUIRED | No certified complete source identified | Halt history is required throughout the study. LULD bands/events are required where the LULD regime was legally in force; earlier observations carry typed NOT_APPLICABLE rather than missing. Delayed openings, pauses, resumptions, and bands change the meaning of the open and censor path outcomes. |
| Exchange calendars | REQUIRED | No certified official calendar identified | Required for sessions, holidays, half-days, daylight-saving changes, scheduled opens/closes, and valid lags. Generic business-day logic is insufficient. |
| Delisting history | REQUIRED | Not identified | Required to prevent survivorship bias, define terminal outcomes, and reconstruct the eligible universe. |

## 4.4 Additional required datasets and contracts

The following are scientifically necessary even though they were not all explicit in the candidate list:

| Dataset or contract | Classification | Reason |
|---|---|---|
| Raw unadjusted regular and extended-hours OHLCV | REQUIRED | Preserves the price actually observed and supports premarket and intraday paths. Existing archives are promising but require certification. |
| Stable security, issuer, share-class, ticker, and venue lifecycle | REQUIRED | Prevents ticker reuse, issuer conflation, ADR/common-share confusion, and symbol-change errors. |
| Listing, suspension, relisting, and terminal status history | REQUIRED | Defines the PIT eligible population and outcome censoring. |
| Authoritative opening observation and source hierarchy | REQUIRED | Defines official auction open versus first eligible regular trade, with delay and fallback flags. |
| Dataset correction and vintage history | REQUIRED | Makes results reproducible after vendor corrections. |
| Official opening-auction data | USEFUL, potentially REQUIRED for auction-specific claims | Improves opening-price and participation semantics. If absent, auction claims are not permitted and fallback opens must be labelled. |
| Trade-condition and venue metadata | USEFUL | Helps exclude non-eligible prints and diagnose odd opens. |

## 4.5 Proposed MDM common export envelope

Every MDM dataset exposed to Project EDGE should carry:

- MDM dataset identifier and semantic version;
- schema version;
- immutable snapshot or vintage identifier;
- partition list and content hashes;
- source and redistribution/replay permissions;
- acquisition basis: full-universe, vendor-universe, or selected;
- explicit no-external-project-fallback declaration;
- stable security, issuer, share-class, ticker, venue, and currency identifiers as applicable;
- economic/effective time;
- publication time;
- first known availability time;
- source-ingestion time;
- vintage/correction time;
- original, corrected, superseded, or cancelled status;
- timestamp precision and timezone;
- typed missingness and quality flags;
- coverage start/end, universe counts, and known breaks;
- transformation lineage;
- validation and reconciliation status.

An export that cannot state acquisition basis or first availability is not confirmatory-grade.

## 4.6 Proposed MDM extension families

### A. Observed price and return-consistent views

Provide:

- immutable raw trades/quotes/aggregates;
- authoritative daily and minute session labels derived from the official calendar;
- a raw observed-price view;
- an action-neutral comparison view computed from an effective-dated action ledger;
- explicit adjustment factors and direction;
- opening-price source and fallback hierarchy;
- late-open, no-open, crossed-market, stale-reference, and sparse-observation flags.

The action-neutral view should map the prior reference price onto the share/value basis effective at the open. It must not rewrite the observed opening print.

### B. Corporate-action and lifecycle ledger

Provide effective-dated, revision-aware records for:

- splits and reverse splits;
- ordinary and special dividends;
- distributions and rights;
- spin-offs;
- mergers and acquisitions;
- ticker, venue, and share-class changes;
- listings, suspensions, relistings, bankruptcies, and delistings;
- cash/stock consideration and terminal value where available.

### C. Catalyst event store

Provide source-preserving, multi-label records for:

- earnings and guidance;
- analyst actions;
- SEC filings;
- material company news;
- FDA/regulatory decisions;
- acquisitions, financing, issuance, buybacks, litigation, management changes, products, and contracts.

Each event requires original text or identifier, event time, publication time, first availability, precision, timezone, revision lineage, source, affected securities/issuer, and timestamp-quality class. Midnight or date-only events must not be silently converted to pre-open events.

### D. Point-in-time company state

Provide effective- and availability-dated:

- market capitalisation;
- shares outstanding;
- float/free float;
- security type and ADR status;
- listing age;
- exchange;
- sector and industry;
- selected fundamental state if later justified.

Issuer values must not be blindly duplicated across share classes.

### E. Classification and membership history

Provide:

- sector and industry taxonomy/version;
- index and ETF membership intervals;
- announcement, effective, and first-availability dates;
- classification changes and revision lineage.

### F. Positioning and ownership

Provide release-aware histories for:

- short interest;
- borrow availability and cost;
- institutional ownership.

Observation dates and public availability dates must remain distinct.

### G. Options

Provide:

- option chain snapshots;
- underlying security mapping;
- expiry, strike, call/put, quote, volume, open interest, and IV;
- vendor model/version;
- availability and stale-quote flags.

Expected-move features must be computed only from contracts observable before the cutoff.

### H. Microstructure and interruptions

Provide:

- uniform best bid/offer quotes where scientifically feasible;
- spread and depth measures;
- auction data if licensed;
- halt, resume, and regulatory-status events throughout the study;
- LULD bands and events where the legal regime was in force, with typed NOT_APPLICABLE before inception;
- feed and venue coverage changes.

Level II should remain a separately governed optional dataset.

### I. Official calendars and sessions

Provide versioned:

- exchange trading dates;
- regular and extended-hours boundaries;
- half-days and exceptional closures;
- timezone and daylight-saving transitions;
- auction schedules;
- venue-specific deviations.

### J. Security master

Provide stable identity mappings and histories independent of every downstream project. It must cover inactive and delisted securities and distinguish issuer, security, and ticker.

## 4.7 Clean-room requirements

For this programme, MDM must expose explicitly named Project EDGE exports whose lineage terminates in MDM-owned sources. The adapter must fail closed if the requested dataset is unavailable. It must never substitute:

- a strategy scan;
- a selected strategy validation cache;
- a downstream project’s security master;
- any completed experiment output;
- any previous or legacy findings database;
- Project ICT (Forex);
- Futures Research Engine;
- Legacy Forex Research Engine.

Existing MDM configuration that indexes unrelated roots is not itself permission to use them.

## 4.8 MDM readiness gates

### Gate M1 — Measurement-minimum

Required before any outcome-bearing gap experiment:

- certified daily and minute raw bars;
- official calendar and session boundaries;
- authoritative open hierarchy;
- stable security/ticker lifecycle;
- complete action ledger for the study window;
- halt history, legally applicable LULD history, and delisting histories;
- immutable snapshots and correction lineage;
- data-quality tolerances and reconciliation report.

### Gate M2 — General cross-sectional context

Required before broad claims by company or sector:

- PIT market cap;
- PIT sector/industry;
- explicit security type and ADR state;
- listing status and age;
- adequate historical coverage for the proposed window.

### Gate M3 — Catalyst-conditioned research

Required before catalyst claims:

- event-type coverage audit;
- timestamp precision and availability;
- revision/cancellation lineage;
- adequate negative-event coverage;
- a defensible distinction between no event, unknown event, and not assessable.

### Gate M4 — Microstructure research

Required before spread, auction, or illiquid-security claims:

- uniform quote or auction coverage;
- feed-break history;
- trade/quote condition rules;
- venue and timestamp-resolution validation.

Failure of a later gate should narrow the permitted hypothesis family, not be “fixed” with an unauthorised data source.

---

# 5. Regime integration design

## 5.1 Scientific role

URE is a source of pre-existing explanatory classifications. It is not:

- a gap detector;
- a sample filter;
- a signal;
- a target;
- a trading policy;
- a permission system;
- an outcome;
- a source of execution logic.

The base gap census must be identical whether or not URE is available. Regime analysis compares conditional outcome distributions within that independently constructed census.

## 5.2 Current URE assessment

The authorised URE repository was inspected read-only.

A generic historical equity series currently provides daily fields such as overall regime, risk state, trend state, volatility state, breadth state, SPY/QQQ trend, and VIX state. Its usable, non-warm-up history begins materially later than its first row and is substantially shorter than the MDM price archive.

Important constraints are:

- a same-date daily classification uses data through that date and is not available at that date’s open;
- breadth is an ETF-based proxy rather than full-market breadth;
- historical liquidity classification is not currently demonstrated as a reliable independent state;
- rates and macro stress are not consistently present in the generic equity export;
- sector regime is not currently a general, PIT, classification-only product;
- some route-specific outputs contain strategy-policy and exposure fields and are therefore inadmissible;
- a longer route-specific history is tied to an ETF-rotation context and should not be consumed directly by Gap Research.

Until a classification-only metadata and replay contract is available, URE-conditioned findings should be exploratory or diagnostic, not confirmatory.

## 5.3 Permitted initial fields

Subject to provenance and timing certification, the initial allow-list is:

- overall market regime label;
- trend or bull/bear state;
- volatility state;
- breadth state, labelled explicitly as an ETF-proxy breadth state;
- risk-on/risk-off state;
- source sub-states such as SPY trend, QQQ trend, and VIX state;
- URE quality, warm-up, and missingness flags.

The following require a future audited URE classification product before use:

- liquidity regime;
- macro-stress regime;
- interest-rate regime;
- sector regime.

## 5.4 Prohibited fields

The adapter must reject fields expressing or encoding:

- strategy policy;
- target exposure;
- new-buy permission;
- trade permission;
- allow/reduce/cash directives;
- position sizing;
- routing context;
- asset allocation;
- any transformation trained on gap outcomes.

Rejecting prohibited fields at schema validation is preferable to relying on analyst restraint.

## 5.5 Required URE export contract

The classification-only export should contain:

- URE export identifier and version;
- entity type and stable entity ID;
- regime-family identifier and native label value;
- classifier and threshold version;
- code and configuration hashes;
- MDM input snapshot identifiers and hashes;
- state date and effective interval;
- latest input-data timestamp;
- explicit knowledge cutoff;
- computation time;
- first availability time;
- provisional/final status;
- revision and supersession lineage;
- warm-up and data-quality flags;
- native classification fields;
- an explicit declaration that no strategy-policy fields are present.

The exported classification snapshot must be immutable and fingerprinted for each experiment. Schema handling is default-deny: every field not explicitly allow-listed is rejected, including raw URE market inputs, forecasts, allocation scores, policy-adjacent fields, and unregistered derived values.

The export must provide full underlying-input lineage. The governance amendment must explicitly resolve whether the URE exception permits a classification derived from any non-MDM market observation. Under the present MDM-only market-data mandate, an export lacking MDM input lineage is rejected; raw URE inputs never enter Gap Research.

## 5.6 Temporal join rule

For a gap on session D:

1. identify the registered information cutoff for the relevant feature view;
2. require first availability no later than that cutoff;
3. require the underlying input-data end no later than that cutoff;
4. require the label’s effective interval to be valid for the event;
5. select only from the frozen URE export version/vintage registered to the experiment;
6. if the URE record has only a date and no defensible availability time, lag it by at least one completed official session;
7. record the source state date, age, input-data end, knowledge cutoff, export vintage, and join rule on every event;
8. do not backfill a later revised label into an earlier experiment.

For the primary at-open view, the default should therefore be the state based on information through D−1 and available by the registered cutoff on D. A same-session label is admissible only if both its inputs and its classification were genuinely available before that cutoff.

## 5.7 One-way boundary

The permitted direction is:

    URE classification export --> Gap Research explanatory feature

The following directions are prohibited:

    Gap outcomes --> URE
    Gap labels --> URE classifier
    Gap findings --> retrospective URE relabelling
    URE policy fields --> Gap Research

URE may evolve independently, but a new classifier version creates a new explanatory-variable lineage. It must not silently replace the frozen version in an existing experiment.

## 5.8 Regime estimands

The scientifically relevant quantity is an interaction contrast, for example:

- change in the gap-magnitude/continuation relationship between high- and low-volatility states;
- difference in fill cumulative incidence between trend states at the same registered horizon;
- change in premarket-participation association across risk states.

“Significant in one regime and not significant in another” is not evidence of a regime difference. The interaction or contrast itself must be estimated, with uncertainty and multiplicity control.

## 5.9 Regime governance

Before a confirmatory regime experiment:

- the URE exception must be recorded in the Project EDGE governance record;
- the field allow-list must be frozen;
- timing and replay tests must pass;
- regime labels and thresholds must be native to URE and not redefined after seeing gap outcomes;
- classifier rules and thresholds must have been fixed externally or trained only on data preceding the applicable evaluation interval; a native full-history-fitted classification remains diagnostic rather than confirmatory;
- full underlying-input lineage must demonstrate compliance with the MDM-only market-data mandate;
- interaction hypotheses and permitted contrasts must be preregistered;
- sparse regimes and minimum effective sample sizes must be specified;
- missing or warm-up states must remain explicit;
- the base event population must be shown to be independent of the URE state.

---

# 6. Variable catalogue

## 6.1 Measurement constitution

Let:

- D be the primary exchange session date;
- t-c be the previous official regular-session close;
- C-raw be the observed prior official close;
- R-split be C-raw mapped onto the opening share-unit basis for splits, reverse splits, and stock distributions effective at the open;
- R be the economic action-neutral reference on the opening share-unit basis, after the registered treatment of cash and non-cash distributions;
- t-s be the scheduled regular-session open;
- t-o be the authoritative official opening observation, or a flagged fallback;
- O be the corresponding opening price;
- P(t) be an eligible subsequent price observation;
- g = log(O / R) be the action-neutral log gap;
- s = sign(g) be gap direction.

Both the raw print discontinuity log(O / C-raw) and action-neutral gap g must be retained. Neither may overwrite the other.

The action-neutral reference is governed as follows:

1. **Splits, reverse splits, and stock distributions:** apply the exact effective share-unit ratio to C-raw to obtain R-split.
2. **Ordinary and special cash distributions:** subtract the certified per-opening-share cash entitlement, after currency conversion under a registered source, from R-split. Ordinary and special distributions remain separately identified.
3. **Rights and spin-offs:** use only an authoritative MDM action term and a declared valuation available by the cutoff. If the distributed value cannot be determined without a future price or discretionary model, mark ACTION_REFERENCE_UNRESOLVED and exclude the event from the primary economic-gap estimand.
4. **Mergers, exchange offers, liquidations, and reorganisations:** do not force continuity across unlike securities or consideration. Assign a lifecycle-event state and analyse only under a separately ratified charter.
5. **Timing and vintage:** every action must be effective by the opening event, publicly known by the applicable market cutoff, and present in the frozen MDM vintage. Later vendor corrections create a superseding event/experiment lineage rather than silently rewriting R.

R-split, R, every component entitlement, action ID, effective time, first availability, and MDM vintage must be retained. The programme must not use a globally backward-adjusted history to construct either reference.

Let epsilon-g be the preregistered gap measurement-tolerance region. Events with |g| no greater than epsilon-g remain in the base census and may serve as non-directional comparators, but s is typed NOT_APPLICABLE for direction-conditioned outcomes; no retention ratio or signed excursion is computed for them.

An “all-time high” may be asserted only if the security’s complete valid price history is available. Otherwise the variable must be named “high since coverage start” or “rolling N-session high.”

## 6.2 Variable registry requirements

Every variable definition should record:

- stable variable identifier and semantic version;
- description, units, direction, and valid range;
- source dataset and fields;
- security and event keys;
- earliest admissible feature view;
- economic, publication, availability, and vintage times;
- lookback window and session rules;
- adjustment basis;
- missingness classes;
- quality and coverage flags;
- transformation formula;
- cross-sectional population, if ranked;
- winsorisation or robustification rule, fixed before outcome access;
- determinism and test fixtures;
- whether the variable is descriptive, explanatory, conditioning, or an outcome.

## 6.3 Mandatory event, identity, provenance, and quality variables

Each gap-event row should carry:

- immutable gap event ID;
- stable security ID, issuer ID, share-class ID, ticker, venue, and currency;
- primary listing and security type;
- common stock, ADR, ETF, fund, warrant, unit, preferred, or other classification;
- listing, suspension, and delisting state at D;
- official session date and calendar version;
- scheduled open and close;
- actual open time and opening delay;
- opening source: official auction, first eligible regular trade, aggregate fallback, or missing;
- prior-close source, time, and staleness;
- raw and action-neutral reference prices;
- applicable corporate-action IDs and factors;
- halt/LULD state around the open and during each horizon;
- MDM dataset and snapshot IDs;
- URE snapshot/version when applicable;
- feature and outcome registry versions;
- universe definition/version;
- premarket, regular-session, and outcome coverage flags;
- timestamp precision;
- correction/revision status;
- typed missingness;
- admissibility status and exclusion reason.

These are part of the scientific data, not operational metadata to be discarded.

## 6.4 Gap characteristics

### Core magnitude and direction

- raw simple and log gap;
- action-neutral simple and log gap;
- absolute gap;
- dollar gap;
- direction;
- opening price;
- gap in basis points;
- raw/action-neutral discrepancy;
- corporate-action-created-gap flag;
- stale-reference flag;
- delayed/open-fallback flag.

### Normalised magnitude

Using prior-only inputs:

- gap relative to ATR;
- gap relative to daily realised volatility;
- gap relative to overnight-volatility history;
- robust z-score within the security’s past;
- rolling percentile within the security’s past;
- point-in-time cross-sectional percentile at a synchronized landmark;
- gap relative to price level;
- gap relative to median spread, where quotes are certified.

### Reference and technical location

- open location relative to prior open, high, low, close, and VWAP;
- distance above/below prior-day range;
- distance to prior close and prior-session midpoint;
- distance to registered rolling support/resistance definitions;
- distance to rolling 20-, 60-, 126-, and 252-session highs/lows;
- distance to high/low since verified coverage start;
- distance to verified all-time high/low only where complete history permits;
- gap above resistance or below support under a deterministic, prior-only definition;
- number of prior sessions since the referenced level was observed;
- prior-session trend, range, close location, volume, and volatility;
- count and signed magnitude of recent gaps using fixed lookbacks;
- prior gap-fill history computed only from events whose outcome window had matured.

### Relative gap

- SPY, QQQ, and applicable sector-ETF gap;
- residual gap after a predeclared prior-only market/sector model;
- security gap minus market, sector, and peer median;
- alignment versus broad market and sector;
- cross-sectional market gap dispersion;
- issuer-level duplicate/share-class event flag.

## 6.5 After-hours, overnight, premarket, and opening-auction variables

Extended-hours intervals must follow official session definitions. Every aggregate needs a coverage and zero-observation indicator. Variables available strictly before the registered pre-open cutoff are separated from descriptors that require O or the eventual gap direction.

### Prior after-hours decomposition

- prior close to first eligible after-hours return;
- after-hours share and dollar volume, trade count, active minutes, VWAP, high, low, range, and last price;
- last after-hours to first premarket return;
- prior close to last eligible pre-open observation return;
- explicit close → after-hours → premarket → auction price decomposition;
- after-hours and premarket coverage-break flags.

### Participation and liquidity

- premarket share volume;
- premarket dollar volume;
- trade count;
- active minutes;
- minutes since first and last eligible observation;
- turnover versus PIT shares and float;
- premarket volume relative to prior regular-session volume;
- same-clock relative volume versus prior comparable sessions;
- dollar-volume relative volume;
- volume in fixed subintervals, such as 04:00–07:00, 07:00–08:00, 08:00–09:00, and the final 30 minutes, subject to calendar validation;
- concentration of volume near the open;
- zero-volume and sparse-coverage flags;
- median and end-of-premarket spread, if quotes are certified;
- quoted depth, imbalance, and auction indication, if scientifically available.

### Price path

- prior-close-to-first-premarket return;
- first-to-last-premarket return;
- prior-close-to-last-eligible-premarket return, named pre-open overnight return;
- premarket high, low, range, and range relative to prior volatility;
- premarket VWAP;
- last premarket price relative to VWAP;
- time of premarket high and low;
- realised variance and semivariance;
- maximum drawdown and run-up;
- jump count under a fixed resolution-aware rule;
- path slope;
- path efficiency signed only by the premarket path’s own first-to-last direction;
- monotonicity/run statistics;
- premarket return relative to SPY, QQQ, sector ETF, and peers;
- stale-last-price and price-source flags.

### At-open descriptors derived from the pre-open path

These variables enter the at-open view, never the premarket view:

- O relative to the premarket high, low, midpoint, last price, and VWAP;
- premarket path efficiency and interval-direction fraction aligned to s;
- action-neutral pre-open traversal/fill relative to R and O;
- raw-gap pre-open traversal retained only as a corporate-action diagnostic;
- last premarket-to-auction return;
- opening price location within the premarket range.

### Opening-auction variables

Where certified MDM auction data exist:

- executed opening-auction share volume and notional;
- auction volume as a fraction of premarket volume and prior ADV;
- clearing price relative to R, last premarket price, premarket VWAP, and the final indicative price;
- indicative-price path, revision count, range, and convergence to the clearing price;
- imbalance sign, size, notional, paired quantity, and revision path;
- auction source, venue coverage, timestamp precision, and missingness quality.

If auction data are not certified, these variables are unavailable; a bar or first-trade fallback must not be described as auction evidence.

## 6.6 Company and security variables

All values must be point-in-time and available by the relevant cutoff:

- prior-close point-in-time market capitalisation and log market capitalisation, the default explanatory size state;
- market-cap percentile;
- shares outstanding;
- float and free float;
- price × float value;
- security price level;
- average daily share and dollar volume;
- turnover;
- median spread and quote coverage;
- exchange and venue;
- security type;
- ADR status and home-market link where known;
- primary versus secondary listing;
- listing age;
- recent suspension or relisting;
- sector and industry, including taxonomy version;
- index and ETF membership;
- issuer with multiple listed share classes;
- short interest, short ratio, release age, and coverage;
- borrow availability/cost and observation age;
- institutional ownership and report age;
- known upcoming earnings date as of the cutoff;
- point-in-time data coverage and staleness.

Open price multiplied by shares or float is a contemporaneous, gap-affected descriptor. It may be reported in the at-open view but must not replace prior-close capitalisation when estimating company-state effect modification.

ADRs require home-market session, holiday, FX, and information-arrival controls supplied through certified MDM exports. Until those data exist, ADRs remain a separate diagnostic population rather than pooled with domestic common shares.

### Deferred option-implied variables

After the MDM options gate passes, the registry may include:

- latest pre-cutoff at-the-money implied volatility at registered tenors;
- option-implied expected move over the gap outcome horizon;
- absolute gap divided by expected move;
- call/put skew and wing slope;
- implied-volatility term-structure slope;
- change in IV from a prior registered cutoff;
- option volume, open interest, bid/ask width, quote age, and stale/crossed flags;
- number and moneyness range of valid contracts contributing to the measure;
- vendor IV method, rate/dividend convention, corporate-action mapping, and chain-coverage quality.

These variables are unavailable, not zero, until a certified MDM options history exists.

## 6.7 Catalyst variables

Catalysts should be multi-label. A gap may have several associated events.

### Event families

- earnings;
- revenue surprise;
- guidance;
- FDA or other regulatory decision;
- acquisition, merger, or strategic transaction;
- analyst upgrade, downgrade, initiation, price-target change, or reiteration;
- SEC filing;
- financing, issuance, offering, or debt event;
- buyback;
- dividend or distribution;
- split or reverse split;
- litigation or investigation;
- management change;
- product, customer, contract, or partnership;
- index/ETF addition or removal;
- sector-sympathy or peer event;
- macro announcement;
- general company news;
- unknown catalyst;
- not assessable due to inadequate coverage.

### Event measurements

- source event ID;
- issuer/security mapping;
- original event type and normalised taxonomy;
- scheduled/unscheduled state;
- economic event time;
- publication time;
- first availability;
- timestamp precision;
- timezone;
- minutes from event availability to scheduled and actual open;
- exact temporal bucket under the interval rules below;
- revision, cancellation, and duplicate-link status;
- numeric earnings, estimate, guidance, price-target, or financing terms in original units;
- surprise measures using only estimates available before the event;
- number and diversity of concurrent events;
- source coverage and confidence;
- post-open catalyst flag for outcome-contamination analysis.

“No observed catalyst” and “unknown catalyst” are not interchangeable. The latter requires an adequate monitored source set and still does not prove absence.

Let A be event first availability, t-c the prior official close, t-pre the registered pre-open feature cutoff, t-s the scheduled session open, and t-o the actual security open. Assign:

- previously known: A no later than t-c;
- post-close/overnight: t-c < A no later than t-pre;
- final pre-open: t-pre < A < t-s;
- post-session-start/pre-security-open: t-s no later than A < t-o for a delayed security;
- concurrent/ambiguous at open: A and t-o cannot be ordered at the source timestamp precision;
- post-security-open: A > t-o.

The exact endpoint convention and timestamp-resolution tie rule must be versioned. Date-only events cannot enter a confirmatory intraday bucket. A post-session-start/pre-security-open catalyst is not pooled with ordinary overnight news.

## 6.8 Market, sector, peer, and macro variables

Measured at the relevant prior-close, premarket, or open cutoff. Raw VIX, Treasury, futures, and macro-calendar values may enter only through a certified MDM-owned Project EDGE export; URE may provide only its approved classified states:

- SPY and QQQ prior-session, overnight, premarket, and opening returns;
- sector ETF equivalent returns;
- security minus market/sector/peer returns;
- broad-market and sector realised volatility;
- VIX level, change, term structure if available, and state;
- Treasury yields and changes at registered maturities;
- interest-rate environment under a registered classification;
- market breadth and dispersion;
- cross-sectional fraction of securities gapping up/down;
- gap-magnitude dispersion;
- average cross-sectional correlation;
- sector concentration of gap events;
- peer-event density;
- index futures only if MDM later becomes an authorised native source; no Futures Research Engine dependency;
- calendar context: day of week, month-end, quarter-end, options expiration, half-day, and days around market holidays;
- scheduled macro-event context only with point-in-time calendars;
- market liquidity measures where valid.

Calendar effects are controls or descriptive conditions, not a licence to mine seasonal rules.

## 6.9 URE variables

Subject to Section 5:

- URE overall regime;
- trend/bull-bear state;
- volatility state;
- ETF-proxy breadth state;
- risk-on/risk-off state;
- SPY trend state;
- QQQ trend state;
- VIX state;
- classification age in sessions;
- URE version and input-vintage IDs;
- warm-up, provisional, missing, and quality flags.

Future liquidity, macro-stress, rate, or sector states may enter only after they are native, audited URE classifications with valid availability metadata.

## 6.10 Intraday landmark variables

Stage 0 proposes a small fixed landmark dictionary for later ratification: 5, 15, 30, and 60 elapsed wall-clock minutes after the actual eligible open, plus the official close. Wall-clock time is primary and includes halt time because information and opportunity continue to evolve while the security cannot trade. The landmark price is the latest eligible observation at or before the landmark within a registered staleness tolerance; otherwise it is missing or censored.

A supplementary trading-time view may count eligible traded minutes, but it is a separately named sensitivity. For a late-opening security, SPY, QQQ, sector, and peer returns use the same wall-clock interval beginning at that security’s actual open. A landmark beyond the official close is NOT_APPLICABLE. Primary multi-session fill clocks observe regular sessions only; extended-hours fills are separately named outcomes.

At each landmark:

- open-to-landmark raw and signed return;
- reference-to-landmark signed gap retention;
- running MFE and MAE;
- partial/full fill state and time if already observed;
- opening-range high, low, width, and close location;
- volume, dollar volume, relative volume, and trade count;
- VWAP and price-to-VWAP distance;
- number and direction of VWAP crossings under a fixed rule;
- realised volatility and semivariance;
- path slope and signed efficiency;
- maximum pullback and rebound;
- relative return versus SPY, QQQ, sector, and peers;
- spread and quote quality where available;
- halt/LULD exposure;
- post-open catalyst arrival;
- observation completeness.

### Path-event variables

The following require deterministic definitions and an explicit confirmation time:

- opening-range break time and direction;
- failed opening-range break;
- breakout distance and persistence;
- first higher low;
- first lower high;
- VWAP reclaim, rejection, or loss;
- first partial and full gap fill;
- first reversal through the open;
- first reversal through the action-neutral reference.

An event may become a feature only after it is confirmed. Outcomes for that experiment must begin after confirmation. “ORB timing” is not an at-open variable.

The path-event registry must define a finite state machine. It must state the initial-excursion threshold, touch/cross tolerance, confirmation delay, persistence requirement, earliest-tie rule, and transitions for open → extension → fill → recovery/re-continuation or reversal. Those constants are measurement conventions fixed before outcome access, never optimised cutoffs.

## 6.11 Outcome catalogue

Let H be a preregistered horizon. For intraday outcomes, P-H is the last eligible regular-session trade or bar close at or before t-o + H within the registered staleness tolerance. End-of-day P-H is the authoritative official close. Quote midpoint outcomes, if used, are separately named and never substituted silently. The path includes O and eligible regular-session observations through H.

For |g| greater than epsilon-g, define:

- q-open(t) = s × log(P(t) / O), signed movement from the open;
- q-ref(t) = s × log(P(t) / R), signed distance from the action-neutral reference.

### Continuous primary outcomes

- **Signed continuation return:** q-open(H).
- **Signed reference return:** q-ref(H).
- **Gap retention ratio:** q-ref(H) divided by |g|; it equals one at O and zero at R.
- **Maximum favourable excursion:** max(0, max q-open(t)) through H, reported as a non-negative magnitude.
- **Maximum adverse excursion:** max(0, max −q-open(t)) through H, reported as a non-negative magnitude. The signed path minimum is retained separately.
- **Time to MFE and MAE:** resolution-aware first times of the extrema.
- **End-of-day open-to-close return.**
- **End-of-day reference-to-close return.**
- **Market-, sector-, and peer-residual outcomes.**
- **Realised volatility, signed path efficiency, and terminal range location.**

### Fill and reversal outcomes

- **Unclipped maximum fill fraction:** maximum of −q-open(t) / |g| over O through H. Including O makes this measure at least zero.
- **Bounded achieved fill fraction:** minimum of one and the unclipped maximum fill fraction.
- **Overshoot beyond reference:** max(0, unclipped maximum fill fraction − 1).
- **Full fill:** first t at which q-ref(t) is no greater than the registered log-price touch tolerance. Equivalently, an up-gap reaches at or below the tolerated R boundary and a down-gap reaches at or above it.
- **Time to first full fill:** elapsed wall-clock time from t-o, including halts, and right-censored at the registered horizon. A separately named trading-time duration may be diagnostic.
- **Partial fill:** first crossing of a small, preregistered set of fill fractions; no fraction may be selected from outcomes.
- **Open-relative reversal:** only after q-open first reaches a registered favourable initial-excursion threshold, a later observation crosses below the registered adverse open threshold.
- **Reference reversal:** after the required initial excursion, q-ref later crosses beyond R by the registered reference tolerance.
- **Continuation then fill:** the confirmed initial-extension time precedes the full-fill time.
- **Fill then re-continuation:** the full-fill time precedes a later crossing back to a preregistered positive fraction of the original gap on the gap side.
- **Magnitude beyond reference after fill:** maximum negative q-ref magnitude after the first fill.

### Later horizons

- close-to-next-open and next-session returns;
- retention/fill at fixed later-session closes;
- time to eventual fill within a fixed maximum follow-up;
- delisting or terminal-event outcome;
- multi-session decay curve.

Continuation, reversal, and fill are not mutually exclusive. The event record should preserve every transition time and the joint path state. Extended-hours observations do not count toward primary later-session fills; an explicitly registered extended-hours outcome may measure them separately.

For |g| no greater than epsilon-g, all direction-conditioned and gap-normalised outcomes above are typed NOT_APPLICABLE. The row remains available for unsigned return, volatility, liquidity, and comparator analyses.

## 6.12 Resolution and tolerance

A negligible-movement tolerance may be necessary to distinguish measurement noise from a real crossing. It must be:

- justified by price increment, spread, and data resolution;
- fixed before outcome analysis;
- treated as a measurement tolerance, not a profit threshold;
- subjected to a small, prespecified sensitivity range.

With minute bars, the order of multiple within-bar events may be unknowable. Such order must be interval-censored or marked ambiguous, not guessed from OHLC values.

---

# 7. Proposed experiment pipeline

## 7.1 Phase-separated pipeline

1. **Ratify the measurement charter.** Freeze event identity, reference price, open hierarchy, sessions, cutoffs, path semantics, outcome horizons, and measurement tolerances.
2. **Certify MDM and URE capabilities.** Produce field-level coverage, timing, revision, identity, and clean-room reports.
3. **Allocate analysis roles.** Assign whole market-date blocks to discovery, sealed confirmation, and later replication before outcome inspection.
4. **Register the research family.** Freeze the exposure set, outcome set, candidate interactions, standard segments, search budget, and multiplicity family.
5. **Build the PIT eligible census.** Include inactive and delisted securities and record every inclusion/exclusion reason.
6. **Run data and leakage sentinels.** Stop on action mismatches, future membership, any URE record whose input-data end or first availability exceeds the feature cutoff, timestamp anomalies, or external-project provenance.
7. **Freeze feature and outcome views.** Create cutoff-specific feature snapshots and separately governed future-outcome snapshots.
8. **Conduct bounded discovery.** Describe distributions, functional form, missingness, heterogeneity, and rival explanations without optimising a trade rule.
9. **Preserve all attempts.** Record models, transformations, segments, nulls, failures, and specification changes.
10. **Apply a promotion gate.** Promote only a small, mechanism-supported, fully specified candidate to confirmation.
11. **Run one-time confirmation.** Execute the frozen analysis on the sealed time block with no discretionary redesign.
12. **Reproduce and replicate.** Reproduce from the same snapshot, independently reimplement, then directly replicate on new time data.
13. **Update the knowledge base.** Store claim, scope, uncertainty, contradictions, nulls, and revalidation status.

## 7.2 Base event census

The base census should be as threshold-free as data quality permits:

- all eligible US primary-listed common-equity sessions;
- a valid prior official close;
- a valid authoritative open or a typed missing/delayed-open state;
- adequate identity and corporate-action resolution;
- full retention of zero, small, and large gaps.

Analytic exclusions may be necessary for a particular estimand, but they must be declared scientifically. Fixed scanner filters must not define the historical population.

## 7.3 Comparator designs

Depending on the hypothesis:

- use continuous gap magnitude from near-zero through the tails;
- compare the same security’s prior non-event sessions;
- use same-date, point-in-time eligible peers;
- use sector/industry peers under historical classification;
- match on strictly pre-gap covariates;
- compare aligned and idiosyncratic gaps;
- compare positive and negative gaps with direction-symmetric definitions;
- use pseudo-event dates for falsification.

Comparator construction must precede outcome access and must not condition on post-open variables.

## 7.4 Statistical design families

Permitted scientific approaches include:

- distributional summaries and empirical cumulative distributions;
- continuous dose-response models;
- quantile regression;
- panel and repeated-event models;
- survival and cumulative-incidence analysis for time to fill;
- multi-state models for continue/fill/reverse order;
- fixed-horizon event studies;
- direct interaction models for regime or catalyst modifiers;
- matched or weighted comparisons based only on pre-event covariates;
- date-block bootstrap and randomisation procedures preserving dependence;
- two-way issuer/date clustered uncertainty where appropriate.

Model complexity must be commensurate with effective sample size. Predictive model tuning is not part of Stage 0.

## 7.5 Exploratory analysis

Exploration should answer:

- Are definitions behaving as intended?
- Where are missingness and measurement error concentrated?
- Is the exposure-outcome relationship plausibly continuous, monotone, nonlinear, or null?
- Which rival explanations account for apparent effects?
- Are effects dominated by a small number of dates, issuers, sectors, or microcaps?
- Are proposed horizons and tolerances scientifically meaningful?

Exploratory findings are labelled as such. They may refine a future preregistration but cannot be promoted retrospectively to confirmed evidence.

## 7.6 Confirmatory experiment specification

An immutable specification should include:

- question and falsifiable hypothesis;
- scientific rationale and rival explanations;
- population, exclusions, and PIT universe;
- exposure, comparator, and conditioning variables;
- reference-price and opening rules;
- feature cutoff and outcome start;
- primary and secondary outcomes and horizons;
- output role for every reported quantity: primary, ordered confirmatory secondary, diagnostic, safety sentinel, or exploratory;
- estimand and minimum relevant effect/equivalence margin;
- design-to-estimator row, uncertainty estimator, and dependence handling;
- minimum effective dates, issuers, sectors/event clusters, cluster-aware power, minimum detectable effect, and not-inferable rule;
- missingness, censoring, and halt handling;
- standard and hypothesis-specific segments;
- URE fields and interaction contrasts, if any;
- multiplicity family and correction;
- discovery/confirmation/replication date roles;
- robustness and negative controls;
- success, failure, ambiguity, contradiction, replication, and joint decision rules;
- permitted outputs;
- complete artifact fingerprints.

Any post-freeze deviation must be logged and ordinarily turns the affected result exploratory.

## 7.7 Promotion gate

A discovery may be proposed for confirmation only if:

- the event and outcome definitions are stable;
- data lineage and timing are auditable;
- the apparent result is not explained by a known action, identity, open, or coverage defect;
- the effect is meaningful relative to a preregistered minimum relevant magnitude;
- dependence-aware uncertainty is adequate;
- the result survives a small set of theory-led robustness checks;
- the hypothesis has a plausible mechanism;
- the exact test is included in the multiplicity inventory;
- no sealed outcomes have been inspected.

## 7.8 Knowledge outputs

The programme should emit claim-centric records, not “best setups.” A finding record should state:

- what distributional relationship was tested;
- the applicable population, dates, and cutoffs;
- magnitude and uncertainty;
- dependence and multiplicity treatment;
- data-quality limitations;
- rival explanations;
- confirmation and replication state;
- contradictory or null studies;
- expiry/revalidation conditions.

---

# 8. Potential sources of bias

## 8.1 Bias-control matrix

| Bias or failure mode | How it distorts gap research | Required control |
|---|---|---|
| Future-adjusted prices | Rewrites the historical reference using later actions | Preserve raw observations; build an effective-date action-neutral reference using only then-known actions |
| Split/dividend false gaps | Treats a mechanical discontinuity as information | Complete action ledger, raw/action-neutral pair, reconciliation sentinels |
| Stale prior close | Inflates apparent gap magnitude | Reference staleness, prior trading status, last eligible close hierarchy |
| Bad or late open | Uses an odd print or ignores delayed discovery | Authoritative open hierarchy, actual-open timestamp, fallback and delay flags |
| Halt/LULD censoring | Makes paths and event times incomparable | Full halt history, LULD where legally applicable, wall-clock primary/trading-time sensitivity, and typed censoring/NOT_APPLICABLE |
| Bid-ask bounce and minimum tick | Creates false fills/reversals in illiquid names | Quote/spread diagnostics, tolerance rules, liquid-population sensitivity |
| Survivorship bias | Removes failed and delisted securities | PIT universe with inactive and delisted names and terminal outcomes |
| Ticker reuse and issuer conflation | Joins unrelated histories | Stable security/issuer/share-class identity and lifecycle |
| Current membership backfill | Assigns future sector/index membership to the past | Effective- and availability-dated classifications |
| Share-class duplication | Double-counts one issuer event | Security-level census plus issuer clustering and duplicate diagnostics |
| ADR/home-market confounding | Mixes foreign trading hours, FX, holidays, and home-market price discovery into the US overnight clock | Separate ADR population until certified MDM home-market/FX controls exist |
| Selected-vendor or scanner universe | Conditions on a strategy-like historical filter | Full/unselected MDM acquisition basis; threshold-free census |
| External-project fallback | Imports prohibited transformations or prior research choices | Fail-closed clean-room MDM export and lineage validation |
| Systematic single-source MDM error | Independent code and later dates can reproduce the same vendor/source defect | Lineage audit, internal source reconciliation, deliberate sentinels, correction tracking, residual-risk disclosure, and evidence downgrade when unresolved |
| Premarket coverage selection | Mistakes missing trading/feeds for low activity | Explicit coverage, active-minute, feed, and zero-observation states |
| Catalyst time leakage | Treats a post-open or revised event as pre-open | Economic/publication/availability/vintage clocks and precision classes |
| Date-only catalyst coercion | Assigns an invented intraday time | Preserve date-only status; exclude or use conservative bucket |
| Catalyst source undercoverage | Labels unobserved events as “no catalyst” | Separate observed none, unknown, and not-assessable states |
| Revised earnings/fundamental data | Uses later corrected values | Vintage-aware event and PIT company-state snapshots |
| Float, short, and ownership reporting lag | Uses observation date rather than public date | Release-aware availability and age fields |
| URE hindsight | Joins a same-day close-based regime to that morning’s gap | Latest available classification only; one-session lag if time is ambiguous |
| URE policy contamination | Smuggles a trading decision into an explanatory study | Classification allow-list and prohibited-field schema rejection |
| Regime redefinition | Tunes state thresholds to gap outcomes | Native frozen URE classifier/version only |
| Asynchronous security opens | Makes at-open cross-sectional ranks partially future-informed | Synchronized landmark or explicitly delayed cross-section |
| Common market dates | Understates uncertainty across thousands of securities | Date clustering/block resampling and date-level influence diagnostics |
| Repeated issuer events | Treats correlated events as independent | Issuer clustering, event-spacing sensitivity, issuer influence checks |
| Overlapping outcome horizons | Duplicates information across events | Purging/embargo where needed and overlap-aware inference |
| Clustered catalysts | Attributes a market shock to company gaps | Same-date controls, market/sector/peer variables, event-density diagnostics |
| Microcap dominance | Lets noisy small names drive pooled results | PIT size/liquidity distributions, predeclared standard segments, weighted sensitivity |
| Post-treatment conditioning | Conditions on opening-range or volume variables when estimating at-open effects | Cutoff-specific views; landmark studies start outcomes after the landmark |
| Collider selection | Selects on variables caused by both gap and latent outcome drivers | Causal diagrams and predeclared population rules |
| Threshold searching | Manufactures “best” gap/volume/float cutoffs | Continuous primary analysis; small theory-led descriptive bins only |
| Multiple regimes and horizons | Inflates false discoveries | Registered research family, hierarchical testing, false-discovery or familywise control |
| Researcher degrees of freedom | Chooses definitions after viewing outcomes | Immutable specification and complete attempt log |
| Winner’s curse | Overstates exploratory effect size | Sealed confirmation and shrinkage-aware reporting |
| Holdout exhaustion | Turns the holdout into a second discovery sample | Access ledger, one-time test, prospective replenishment |
| Missing-not-at-random outcomes | Drops halts, delistings, or data failures selectively | Typed missingness, censoring models, worst-case/bounding sensitivity |
| Intrabar event ordering | Invents whether fill or MFE occurred first | Higher-resolution data or interval-censored/ambiguous path state |
| Vendor correction drift | Makes reruns differ silently | Immutable MDM vintage and superseding experiment lineage |
| Cleaning discretion | Removes inconvenient observations after inspection | Frozen admissibility rules and exclusion audit |
| Publication bias | Preserves only interesting results | Append-only registry of all hypotheses, attempts, nulls, and failures |
| Causal overclaim | Interprets conditional association as treatment effect | Associational language unless identification assumptions are justified |

## 8.2 Look-ahead sentinels

Automated future implementation should include tests that deliberately attempt to detect:

- future corporate actions in past features;
- current sector or ETF membership applied historically;
- URE records whose input-data end or first-availability timestamp exceeds the feature cutoff;
- catalyst revisions or later timestamps;
- outcome columns visible to feature code;
- full-sample scalers, ranks, residual models, or imputation;
- delisting-based removal from earlier universes;
- after-open news in premarket features;
- cross-sectional values calculated before all required observations were available.

The pipeline should fail, not warn, when a hard leakage sentinel is triggered.

## 8.3 Interpretation hazards

Several distinctions must remain explicit:

- association is not causation;
- no observed catalyst is not no catalyst;
- no fill by H is not never fill;
- non-significance is not evidence of equivalence;
- a regime-specific p-value is not a regime interaction;
- a raw opening discontinuity is not necessarily an information gap;
- a high-since-2007 is not an all-time high;
- a first recorded minute is not necessarily the official open;
- a descriptive threshold is not a scientifically validated boundary.

---

# 9. Validation methodology

## 9.1 Analysis-role separation

Allocate **whole market-date blocks**, not random security rows, to:

1. discovery;
2. sealed confirmation;
3. direct replication on later, genuinely new time data.

Random row splits leak common shocks and repeated issuer structure. If the available history cannot support all three roles with adequate effective sample size, the correct response is prospective data accumulation, not weaker separation.

## 9.2 Temporal validation

Use rolling-origin or expanding-window analyses in which:

- feature scalers, ranks, imputers, residual models, and classifications use prior data only;
- outcome windows have fully matured before a fold is analysed;
- overlapping training/test outcome horizons are purged where relevant;
- every fold is retained, including adverse eras;
- calendar and market-structure changes are documented;
- no later fold informs an earlier specification.

## 9.3 Dependence-aware inference

Inference should consider:

- date-level dependence from common market shocks;
- repeated securities and issuers;
- sector and catalyst clusters;
- overlapping event horizons;
- unequal event density by date;
- persistent regime blocks.

Depending on the estimand, use date-block bootstrap, issuer/date multiway clustering, cluster-aware randomisation, or hierarchical models. Report both nominal event counts and effective independent date/issuer counts.

Every confirmatory specification must select a row from a preregistered design-to-estimator matrix. It must state minimum effective counts for market dates, issuers, and relevant sector/catalyst clusters; a dependence-aware power or minimum-detectable-effect calculation; and a small-cluster fallback. If those gates fail, the run finding is INCONCLUSIVE/NOT INFERABLE rather than a less conservative estimate.

## 9.4 Survival and path outcomes

For time to fill or reversal:

- define time origin and trading-time versus wall-clock time;
- retain right-censored events;
- treat delisting, suspension, and data loss explicitly;
- distinguish competing terminal events where necessary;
- report cumulative incidence or survival curves, not only a binary horizon;
- preserve interval censoring when bar resolution does not identify event order.

## 9.5 Multiplicity

Before confirmation, define the family across:

- exposures;
- outcomes;
- horizons;
- directions;
- catalysts;
- company segments;
- regimes;
- functional forms;
- robustness variants.

Multiplicity control has distinct layers:

- the bounded discovery campaign uses its registered false-discovery-rate budget;
- a finite sealed confirmatory family uses strong familywise-error control or another foundation-approved dependence-aware confirmatory procedure;
- ordered secondary outcomes and contrasts are tested only through a frozen gatekeeping sequence;
- repeated confirmation opportunities draw from a programme-level sequential error budget and may not reset it;
- diagnostic and exploratory outputs are reported but cannot change the confirmatory decision.

Report the complete unadjusted and adjusted inventory, including untested ordered secondary hypotheses whose gate did not open.

## 9.6 Effect magnitude and equivalence

Every confirmatory experiment should define a minimum scientifically relevant effect or equivalence margin. Report:

- point estimate;
- uncertainty interval;
- adjusted significance where applicable;
- probability or evidence relative to the relevance threshold;
- absolute and relative effect scales;
- distributional consequences, not only averages.

A precise estimate inside the equivalence margin supports a bounded null. A wide interval crossing it is inconclusive.

## 9.7 Standard robustness set

A small, preregistered robustness set should include:

- raw versus action-neutral gap diagnostics;
- official-open versus permitted fallback-open sensitivity;
- alternative defensible measurement tolerance;
- liquid-only and complete-quote subsets where available;
- exclusion of delayed opens and separate delayed-open analysis;
- leave-one-date, leave-one-issuer, and leave-one-sector influence checks;
- period stability around documented market/data regime changes;
- market/sector residual outcome;
- complete-case versus registered missingness treatment;
- alternate dependence estimator.

Robustness is not an invitation to search until a result survives.

## 9.8 Negative and falsification controls

Controls must be assigned one of three roles with a preregistered expected result:

1. **Deliberately leaked positive/safety sentinels.** Examples are future-dated URE records, future membership, future corporate actions, or an outcome column offered to the feature layer. Success means the pipeline rejects or quarantines them; these are not null hypotheses.
2. **Inferential negative-control exposures/outcomes.** Carefully justified shifted catalysts, pseudo-events, lead outcomes, or dependence-preserving permutations may have an expected null under the registered model. Their exchangeability and expected-null rationale must be stated; they are not automatically valid controls.
3. **Data-stress and bias-demonstration subsets.** Pseudo-opens, current-constituent/survivor-only samples, no-premarket-coverage securities, and raw split discontinuities demonstrate sensitivity or known bias. They are not expected-null populations.

A failed safety sentinel blocks the run. An inferential negative control or stress subset triggers the preregistered challenge rule, investigation, scope reduction, or evidence downgrade; it does not receive an undefined blanket pass/fail interpretation.

## 9.9 Reproducibility and replication ladder

1. **Exact reproduction:** same code, configuration, environment, and frozen MDM/URE snapshots.
2. **Independent reimplementation:** separate code path from the written specification against the same snapshots.
3. **Direct temporal replication:** frozen specification on later, previously unavailable dates.

Agreement at step 1 alone is operational reproducibility, not independent scientific replication.

Before the direct replication is opened, freeze a prediction or compatibility interval, an equivalence/relevance region, and the rule for acceptable heterogeneity or meta-analytic synthesis. Replication is not adjudicated by whether a second isolated p-value crosses 0.05.

Independent code and later MDM dates cannot eliminate systematic single-source MDM error. Every synthesis must disclose that residual risk and may downgrade evidence when lineage reconciliation or source-defect sentinels remain unresolved.

## 9.10 Evidence-state decisions

A study must use the foundation’s three distinct evidence levels:

| Level | Canonical states |
|---|---|
| Run finding | Supported; precise null; contradicted; inconclusive with reason such as underpowered/not inferable; invalid |
| Hypothesis decision | Confirmed on locked evidence; confirmed conditional; not confirmed; contradicted; unresolved |
| Phenomenon maturity | Proposed; candidate; provisionally confirmed; directly replicated; validated; validated conditional; superseded; retracted |

Terms from one level may not substitute for another. “Directly replicated” and “superseded” are phenomenon-maturity/workflow states, not run findings. Only the foundation’s governed evidence-synthesis stage may assign validated.

Every output must be frozen as primary, ordered confirmatory secondary, diagnostic, safety sentinel, or exploratory. The specification’s decision function maps the joint primary/secondary results, data-quality gates, negative controls, and replication criterion to the run finding and hypothesis decision.

No result should disappear because it is inconvenient.

## 9.11 Mandatory transportability panel

Every valid run should report a point-in-time descriptive panel across:

- capitalisation;
- liquidity;
- sector and industry;
- exchange;
- lifecycle and listing age;
- security type, including REIT status and separately chartered ADR/SPAC groups;
- index/ETF membership;
- catalyst coverage and timestamp quality.

Sparse cells and unknown classifications remain visible. This panel is diagnostic transportability evidence unless a specific interaction was preregistered as confirmatory; it does not create post hoc subgroup claims.

---

# 10. Recommended implementation roadmap

This is a future roadmap only. No implementation or data acquisition is authorised by this Stage 0 document.

## Phase 0 — Governance reconciliation

Deliverables:

- versioned amendment permitting URE classification-only read access;
- reaffirmed MDM-only market-data boundary;
- prohibited-source and no-fallback policy;
- Stage 0 scope and strategy firewall;
- ratified primary and separately chartered security populations from Section 1.8;
- ownership map for shared EDGE versus Gap Research responsibilities.

Exit gate:

- all exceptions and prohibitions are machine-testable and approved.

## Phase 1 — Provider capability certification

Deliverables:

- MDM dataset capability matrix;
- field-level coverage and quality report;
- provenance scan for prohibited downstream dependencies;
- MDM extension backlog by Gates M1–M4;
- URE classification allow-list, full MDM input-lineage proof, replay/timing report, and pre-evaluation classifier/threshold training audit;
- explicit study-window feasibility assessment.

Exit gate:

- a defensible date range and population can be stated without hidden fallback.

## Phase 2 — Gap measurement constitution

Deliverables:

- official definitions of prior close, action-neutral reference, and open;
- session and late-open rules;
- security identity and universe rules;
- premarket and landmark cutoffs;
- continuous outcome definitions;
- fill/reversal state machine;
- censoring, ambiguity, and tolerance rules;
- fixed initial horizon dictionary.

Exit gate:

- independent reviewers can derive the same event and outcome from test fixtures.

## Phase 3 — Artifact and registry contracts

Deliverables:

- event, feature, outcome, catalyst, URE, experiment, and finding schemas;
- immutable snapshot and fingerprint contract;
- analysis-role and holdout access contract;
- typed missingness and exclusion taxonomy;
- complete attempt and deviation records;
- negative-result record.

Exit gate:

- a synthetic experiment can be represented end to end without real outcome analysis.

## Phase 4 — Deterministic research core

Future implementation, after separate authorisation:

- MDM adapter;
- identity/calendar/action layer;
- gap event builder;
- cutoff feature views;
- outcome isolation and engine;
- URE classification adapter;
- quality and leakage sentinels;
- standard artifact generation.

Exit gate:

- deterministic reruns match fingerprints and all leakage tests pass.

## Phase 5 — Measurement verification

Deliverables:

- hand-labelled event fixtures covering splits, dividends, ticker changes, halts, late opens, sparse premarket data, half-days, delistings, and catalyst timestamp edge cases;
- aggregate reconciliation against MDM source records;
- missingness and coverage maps;
- sensitivity to source resolution;
- independent implementation comparison.

Exit gate:

- predefined measurement-error tolerances are met; unresolved cases are typed and bounded.

## Phase 6 — Bounded discovery programme

Recommended order:

1. unconditional action-neutral gap distributions;
2. gap-magnitude dose response;
3. fill and retention survival/path analysis;
4. premarket participation and path context;
5. market, sector, and company-state heterogeneity;
6. catalyst-conditioned families after Gate M3;
7. URE interaction families after the URE confirmatory gate;
8. microstructure families after Gate M4;
9. post-open landmark transition studies.

Exit gate:

- a small number of fully specified, mechanism-supported candidates or explicit negative findings.

## Phase 7 — Locked confirmation and replication

Deliverables:

- one-time sealed confirmation;
- dependence- and multiplicity-aware report;
- independent reimplementation;
- prospective direct replication under a frozen compatibility/prediction and heterogeneity rule;
- contradiction and null records.

Exit gate:

- evidence state assigned without retrospective specification changes.

## Phase 8 — Knowledge maintenance

Deliverables:

- append-only synthesis;
- finding expiry and revalidation rules;
- data-version impact assessment;
- scheduled temporal stability reviews;
- preserved evidence graph linking hypotheses, experiments, replications, and contradictions.

Exit gate:

- every active claim is traceable, current, bounded, and reproducible.

## 10.1 Priority order for MDM work

1. Official calendars, opening semantics, security lifecycle, corporate actions, halts, legally applicable LULD history, delistings, and immutable clean-room snapshots.
2. Certified raw/action-neutral price views and quality reconciliation.
3. PIT market cap and sector/industry history.
4. Catalyst timing and coverage certification.
5. Broad quote/spread coverage.
6. Float/shares, ETF membership, options IV, short interest.
7. Borrow, institutional ownership, and Level II for specialised studies.

This order reflects scientific necessity, not anticipated trading value.

## 10.2 Stop conditions

Future work should stop or narrow scope if:

- MDM provenance crosses a prohibited project boundary;
- reference/open/action semantics cannot be reconciled;
- identity or delisting coverage makes the PIT universe unreliable;
- URE availability cannot be reconstructed at the open;
- outcomes are visible during feature construction;
- the study window cannot support independent time blocks;
- a required dataset is missing and the proposed conclusion is not narrowed accordingly.

## 10.3 Final Stage 0 recommendation

Proceed eventually with a **Gap Research subsystem within Project EDGE**, subject to the governance and data gates above.

Do not begin empirical gap testing merely because raw bars exist. The first authorised implementation work should establish the measurement constitution, provider contracts, clean-room provenance, and immutable artifact schemas. Data acquisition extensions should follow only after their specifications are approved.

The programme should be judged by the credibility of what it can rule in, rule out, or bound—not by whether it produces a trading setup.

---

## Appendix A — Minimum first experiment concept

When implementation and data gates are later approved, the safest first scientific experiment would be:

- population: the ratified primary population in Section 1.8 with valid PIT identity, action, prior-close, and opening observations; zero/near-zero events remain in the census but have no directional outcome;
- exposure: continuous action-neutral log gap;
- feature cutoff: authoritative open;
- single primary outcome/horizon: signed open-to-official-close return;
- ordered secondary outcomes: close gap-retention ratio followed by regular-session time to full fill, under a frozen gatekeeping and multiplicity rule;
- diagnostic outcomes: intraday retention/excursion paths at the ratified landmarks;
- conditioning: prior-only size, liquidity, sector, market gap, and basic data-quality variables;
- no catalyst or URE conditioning in the first measurement-validation run;
- whole-date chronological discovery and sealed confirmation blocks;
- date/issuer dependence-aware inference;
- raw/action-neutral and open-quality falsification checks;
- no threshold optimisation and no trading metrics.

This is a measurement-validation experiment, not a strategy backtest.

## Appendix B — Stage 0 acceptance checklist

- [x] Active repository boundary identified.
- [x] Existing Project EDGE foundation reviewed.
- [x] Reusable components identified.
- [x] Missing modules identified.
- [x] Dedicated-subsystem architecture selected.
- [x] MDM reviewed read-only.
- [x] Required MDM enhancements specified without acquisition.
- [x] Candidate datasets classified.
- [x] URE reviewed as a read-only explanatory source.
- [x] URE timing, allow-list, and policy-field exclusions defined.
- [x] Comprehensive variable catalogue produced.
- [x] Experiment pipeline proposed.
- [x] Bias and leakage controls catalogued.
- [x] Validation and replication methodology specified.
- [x] Future implementation roadmap and stop conditions defined.
- [x] No trading strategy, optimisation, or live-trading component designed.

## Appendix C — Read-only audit provenance

Audit date: 2026-08-03.

| Repository/provider | Audit identity | Read-only evidence basis |
|---|---|---|
| Project EDGE target | D:\codex\equity_quant_research_platform; not a Git worktree at audit | PROJECT_EDGE_FOUNDATION_DOCUMENT.md and supporting repository inventory |
| MDM | Git commit e7c9b63b2a05b7b356bc3af044ed756b4acf57a7; clean working tree at final status check | Archive partitions and schemas; outputs/data_manager_audit/latest_status.json; outputs/reference_pit/pit_reference_status.json; outputs/reference_pit/massive_monthly_build/massive_monthly_pit_build_summary.json; outputs/reference_pit/massive_monthly_build_review/massive_monthly_build_review_summary.json; data/canonical_catalysts/canonical_catalyst_build_manifest.json; configuration and lineage metadata |
| URE | Git commit 0f33e01b7d6dcf6a6320cd5d93a3c64fa20c6867; working tree reported six existing status entries at final read-only check | outputs/regime/historical_equity_series/historical_equity_regime_daily.csv; outputs/regime/phase6_10y_history_extension_native_xlc_rerun/ure_native_xlc_historical_regime_series.csv; associated summary/manifest and implementation metadata |

No MDM or URE data were copied into Project EDGE, and neither provider repository was modified. Downstream-project artifacts named in lineage/configuration metadata were not opened or imported. Current-state claims in this document are an architectural audit snapshot, not a substitute for the formal field-level capability and provenance certification required by Phase 1.
