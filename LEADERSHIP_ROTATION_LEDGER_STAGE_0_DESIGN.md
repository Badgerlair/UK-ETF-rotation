# Project EDGE — Leadership & Rotation Observation Ledger

## Stage 0 architectural design and implementation gate

**Design version:** `EDGE-LOBS-DESIGN-V1`  
**Design date:** 2026-08-11  
**Authorised project root:** `D:\codex\equity_quant_research_platform`  
**Phase A status:** architecture reviewed; initial review blocked; corrections applied; final review approved  
**Empirical status:** infrastructure only; no leadership hypothesis has been tested  

---

## 1. Decision

Project EDGE should add a small, independent **Leadership Observation Ledger**
(`edge_lobs`) beside the frozen Market Data Manager boundary. It should not
extend the MDM source contract, modify the evidence-bound `edge_mdm` package,
or place human/source observations in the MDM observable panel.

The ledger will make five layers physically and logically distinct:

1. immutable raw source bytes and source provenance;
2. immutable structured human/source observations;
3. separately versioned MDM-derived feature artifacts;
4. separately versioned forward-outcome artifacts; and
5. separately versioned model/user/research interpretations.

Phase B is consistent with the frozen Project EDGE foundation only under these
conditions:

- source capture and sealing may be implemented now;
- unresolved tickers remain explicitly unresolved until an admitted MDM
  identity history can resolve them point in time;
- the MDM enrichment interface is implemented fail closed, but no production
  feature result is emitted while the MDM and release gates remain blocked;
- group/constituent features remain blocked until admitted point-in-time sector,
  industry, theme, and membership histories exist;
- outcome contracts, maturity checks, and physically separate test-only storage
  may be implemented, but no real outcome is attached without an admitted MDM
  view and an elapsed trading-session horizon; and
- no exploratory or confirmatory leadership analysis is performed.

This creates a reliable capture system without implying that leadership exists,
is detectable, or improves any setup.

---

## 2. Repository confirmation and architectural evidence

The requested directory resolves exactly to:

`D:\codex\equity_quant_research_platform`

It contains the Project EDGE source, tests, governance documents, configuration,
artifacts, and evidence. It has no `.git` directory and therefore cannot be
verified as a Git worktree. Change accounting for this task must use an explicit
file inventory rather than Git status or diff.

No `AGENTS.md` is present. No TraderLion PDF, futures screenshot, article capture,
or filename matching the 2026-08-11 sources was found in an admissible repository
surface. PDFs are absent entirely. Images and HTML files that exist only under
completed unrelated research outputs are excluded and are not inputs.

The governing evidence reviewed was limited to the Project EDGE foundation,
MDM specification and implementation, configuration, README, generic evidence
mechanisms, and tests. Completed unrelated experiments, result files, prior
findings, external engines, and prohibited projects are not dependencies.

### 2.1 Binding foundation controls

The design implements the following existing Project EDGE requirements:

- clean-room, repository-only, MDM-exclusive market-data boundaries;
- one-way evidence flow with corrections represented by new versioned artifacts;
- artifacts that may be superseded but never overwritten;
- four-clock point-in-time semantics;
- stable security identity rather than ticker as the research key;
- point-in-time classifications and memberships, with unknown rather than
  present-day backfill;
- an outcome-free observation/feature layer;
- separate future-outcome views;
- full-distribution and right-tail-preserving research; and
- no strategy, optimisation, portfolio, broker, execution, or live-trading
  functionality.

### 2.2 Existing components to reuse

| Existing component | Reuse | Boundary |
|---|---|---|
| `edge_mdm.fingerprint.canonical_json_bytes` | Deterministic JSON encoding | Public helper only |
| `edge_mdm.fingerprint.sha256_bytes` / `sha256_file` | Content identity and verification | Public helper only |
| `edge_mdm.fingerprint.package_source_fingerprint` | Bind exact `edge_lobs` Python source by passing its package root | Do not use the default `edge_mdm` root |
| `edge_mdm.temporal` rules | Audited precedent for timezone-aware parsing, PIT selection, identity, and session shifts | These functions are not exported public APIs; `edge_lobs` uses local frozen equivalents for source validation and consumes identity/session decisions only from an admitted MDM read handle |
| `edge_mdm.source.verify_mdm_snapshot` | Authorised MDM intake | Never accept arbitrary market-data files |
| `VerifiedMdmSnapshot.assert_unchanged` | Verify-on-read source protection | Not sufficient by itself for production authority |
| MDM release materialisation pattern | Stage, hash, pre-write revalidate, refuse overwrite, atomic rename, verify on read | Reimplement generically for ledger bundles; do not call the MDM-specific materialiser |
| MDM chained release-register pattern | Tamper-evident append-only seals | Ledger-specific register and event schema |
| MDM validation-report pattern | Typed, fail-closed checks | Ledger-specific checks and codes |

### 2.3 Components that must remain frozen

The complete `src/edge_mdm` Python package is hashed into existing Project EDGE
artifacts. `pyproject.toml`, `requirements.lock`, existing MDM tests, and the
frozen configuration are also bound by retained Milestone 3 evidence. Phase B
will not modify any of them.

The new module is loaded using the repository's established `PYTHONPATH=src`
workflow:

```powershell
$env:PYTHONPATH = "src"
python -m edge_lobs --help
```

This avoids changing the frozen package-discovery and console-script contract.

---

## 3. Current MDM capability decision

The machine-readable Project EDGE state is explicitly blocked:

- MDM production gate: `BLOCKED`;
- population/time contract: `UNRATIFIED`;
- approved production scopes: none;
- production release authority: `NOT_CONFIGURED`;
- stable identity history: unavailable;
- authoritative equity calendar: unavailable;
- atomic immutable production snapshot/replay: unavailable; and
- point-in-time sector/industry history: `UNAVAILABLE_FOR_EDGE`.

The current `DailySliceRequest` supports only a post-close cutoff and an explicit
synthetic test policy bundle. It has no arbitrary morning
`information_cutoff_timestamp`. A pre-market observation on 2026-08-11 must not
request the 2026-08-11 completed daily bar merely because the calendar date
matches. The correct eligibility law is:

```text
session.cutoff_at <= observation.information_cutoff_timestamp
and every contributing record.available_at <= information_cutoff_timestamp
```

The ledger therefore captures source observations now and exposes an enrichment
contract that refuses production execution until an admitted MDM source and
release authority exist. Group membership, constituent breadth, group ranks,
and group-relative stock features additionally require admitted point-in-time
taxonomy history. ETF price-proxy observations are not constituent-based group
measurements.

The investing.com futures screenshot is authorised here only as evidence of
what that source displayed. It remains `SOURCE_DERIVED`; it is not objective MDM
market data and cannot enter an MDM feature or outcome. A governance amendment
would be required before treating it as an objective empirical covariate.

---

## 4. Final directory design

Authoritative records are content-addressed immutable bundles, not mutable daily
folders. Date-based views, indexes, and convenience exports are regenerable.

```text
equity_quant_research_platform/
  LEADERSHIP_ROTATION_LEDGER_STAGE_0_DESIGN.md
  src/
    edge_lobs/                         # new; sibling of frozen edge_mdm
      __init__.py
      __main__.py
      cli.py
      contracts.py
      errors.py
      jsonio.py
      validation.py
      ledger.py
      mdm.py
      outcomes.py
  observations/
    leadership_rotation/
      schemas/                         # observation, import, test-only MDM/outcome contracts
      inbox/                           # staging only; never authoritative
        README.md
      examples/
        2026-08-11/
          observation_batch.json
          import_manifest.template.json
      documentation/
        README.md
        CHATGPT_DAILY_OBSERVATION_CONTRACT.md
        DAILY_WORKFLOW.md
        LEAKAGE_TEST_MATRIX.md
      ledger/                          # created by import command
        batches/
          <observation_batch_id>/
            raw/<sha256>               # exact source bytes
            observation_batch.json     # canonical structured input
            source_manifest.json       # computed hashes and provenance
            validation_report.json
            batch_manifest.json
        registry/ledger_events.jsonl   # append-only hash chain
        indexes/ledger_index.json      # regenerable, not authority
  research/
    leadership_rotation/
      features/                        # MDM_DERIVED only
      outcomes/                        # future outcomes only
      interpretations/                 # MODEL/USER/RESEARCH_DERIVED only
      experiments/
      reports/
      STAGE_2_RESEARCH_PROPOSAL.md
  tests/
    test_lobs_contracts.py
    test_lobs_ledger.py
    test_lobs_mdm_outcomes.py
    test_lobs_cli.py
    test_lobs_initial_example.py
```

Raw bytes are stored inside the sealed batch so raw copy, structured extraction,
provenance, and validation can become visible through one same-volume atomic
rename. Global hash and source-identity duplicates are detected by scanning the
sealed manifests and ledger register under an exclusive ledger lock.

---

## 5. Immutable artifact hierarchy

### 5.1 Raw source object

Every stored source record contains:

- `source_id`;
- `observation_batch_id`;
- `source_type`;
- `source_name`;
- `source_title`;
- `source_original_filename`;
- `source_identity` (a stable source/event identity, distinct from filename);
- `source_capture_timestamp`;
- `source_publication_timestamp`, when known;
- `source_publication_date`, when only a date is known;
- timestamp precision;
- IANA timezone;
- `ingested_timestamp`;
- `capture_mode`;
- `historical_reconstruction`;
- `contemporaneous_capture_attested`;
- SHA-256 `original_hash`;
- byte length;
- immutable `storage_location`;
- `parser_version`, when applicable; and
- notes.

Source files are opened read only, hashed before copy, copied to a staging
directory, hashed again, and the original path is re-hashed immediately before
commit. A mismatch fails closed. Existing raw files are never opened for write.

### 5.2 Observation batch

Each daily set has one immutable ID matching:

```text
EDGE-LOBS-YYYYMMDD-<stable suffix>
```

Version 1 accepts an explicit suffix such as `001`; uniqueness is enforced by
the global ledger. It does not derive a circular identifier from a document that
already contains its own ID.

Required batch fields are:

- `observation_batch_id`;
- `schema_version`;
- `observation_date`;
- timezone-aware `information_cutoff_timestamp`;
- `information_cutoff_timezone`;
- `capture_mode`;
- `recorded_at`;
- `source_ids`;
- extractor actor, method, and version/model where applicable;
- validation status;
- optional `supersedes_batch_id` for a future new artifact, never an overwrite;
- notes; and
- independent arrays for market, instruments, groups, stocks, futures snapshots,
  and macro/source context.

Every atomic structured observation has its own immutable `observation_id`,
timestamp, origin, verbatim `source_text`, source ID/location, extraction
confidence, controlled category where faithful, and notes.

### 5.3 Seal and register

Import creates a batch manifest that binds:

- exact schema versions;
- observation and source-manifest hashes;
- all raw file hashes and byte counts;
- validation report hash;
- exact `edge_lobs` software-source fingerprint;
- capture-only versus research-admissibility state;
- immutable file inventory; and
- known limitations.

The final directory is created with a temporary sibling and `os.replace` only
after every byte has been verified. An existing batch path always raises
`IMMUTABLE_BATCH_ID_COLLISION`.

The seal register is JSON Lines with:

- the prior record hash;
- batch ID and batch-manifest hash;
- source IDs, identities, and content hashes;
- event time and actor; and
- the current record hash.

The register is appended with `O_APPEND` and `fsync`. Reads verify the complete
chain and every referenced artifact. Indexes can be deleted and rebuilt from
sealed artifacts; they are never the sole authority.

This provides application-level write-once behavior and tamper evidence. It
does not claim adversarial production immutability: protected storage,
authenticated roles, and an external trust anchor are not configured in the
current repository. A manual actor with unrestricted filesystem authority could
replace both payload and local register. That unresolved governance limitation
must remain visible and blocks a stronger production claim.

---

## 6. JSON contracts

Published Draft 2020-12 JSON Schemas document the interchange formats. Runtime
admission follows the existing Project EDGE approach: frozen exact-key checks,
typed validation, duplicate-JSON-key rejection, rejection of NaN/infinity, and
canonical JSON. No unpinned schema-validation dependency is added.

### 6.1 ChatGPT daily observation contract

Top-level arrays are table-like and independently keyed:

```json
{
  "schema_version": "edge.leadership_observation_batch.v1",
  "observation_batch_id": "EDGE-LOBS-20260811-001",
  "observation_date": "2026-08-11",
  "information_cutoff_timestamp": "<timezone-aware timestamp>",
  "information_cutoff_timezone": "<IANA timezone>",
  "capture_mode": "PROSPECTIVE",
  "recorded_at": "<timezone-aware timestamp>",
  "source_ids": ["..."],
  "extractor": {"actor_type": "USER", "actor_id": "...", "method": "MANUAL_TRANSCRIPTION", "version": "..."},
  "validation_status": "AWAITING_RAW_SOURCES_AND_PROVENANCE",
  "supersedes_batch_id": null,
  "market": [],
  "instruments": [],
  "groups": [],
  "stocks": [],
  "futures_snapshot": [],
  "macro_context": [],
  "notes": ""
}
```

The controlled vocabulary never replaces verbatim source text. Unsupported
categorisation is represented by `OTHER` or a null controlled state, not a
stronger inferred meaning.

`AWAITING_RAW_SOURCES_AND_PROVENANCE` is the only template/draft status. It
must become `READY_FOR_IMPORT` only after the exact cutoff, record/source
clocks, timezones, locations, attestations, identities, and nonempty raw files
are complete. `READY_FOR_IMPORT` is still caller-authored descriptive state; it
does not confer authority. Only successful computed validation, sealing, and
register verification establish a ledger capture record.

### 6.2 Market records

Market records contain a `field` from a controlled vocabulary (trend status,
moving-average state, market description, short/intermediate/long-term state,
risk bias, breadth, leadership, weakness, event risk, current view, or additional
thought), optional `metric`, optional controlled `state`, and mandatory
`source_text`.

There is no mandatory numeric market score.

### 6.3 Instrument records

Instrument records preserve instrument symbol/name, instrument kind, optional
stable identity, identity-resolution state, observation type, optional
controlled state, verbatim source text, and provenance. Version 1 states include
the requested breakout, reconfirmation, building, coiling, range-building,
handle, pullback, weakening, trend, failed-breakout, down-off-level, and `OTHER`
terms. These categories are nominal; no ordinal ordering is encoded.

### 6.4 Group records

Group records keep source taxonomy separate from any future MDM taxonomy:

- `group_id` and `group_name`;
- `group_type`;
- `taxonomy_origin` (`SOURCE_TAXONOMY` or `USER_TAXONOMY`);
- optional source classification;
- verbatim source text and classification basis; and
- source provenance.

`MDM_TAXONOMY` is always forbidden in a source batch. A future formal MDM
classification belongs only in a separate `MDM_DERIVED` artifact linked to the
source group without mutating it. Source terms such as “cyber” and a future MDM
classification can coexist and are never silently reconciled.

Classifications are nominal. No initial order or composite leadership score is
defined.

### 6.5 Stock records

Each stock assertion is atomic and contains:

- batch and observation timestamps;
- ticker;
- nullable point-in-time `security_id`;
- `identity_resolution_status`;
- nullable company and source-group fields;
- source role;
- optional setup family/state;
- optional relative-strength, moving-average, price-action, and volume text;
- mandatory verbatim `source_text`;
- source ID and location;
- extraction confidence;
- derivation type; and
- capture mode.

A ticker is sufficient for source fidelity but never for a research join. The
2026-08-11 records remain `UNRESOLVED` until MDM resolution is possible.

### 6.6 Futures snapshot records

Printed numeric values are strings so their displayed precision is preserved.
The record contains instrument, value, absolute and percentage change when
shown, observation timestamp, IANA timezone, timestamp precision, source ID,
source type, and origin. A later MDM value would live in an independent
`MDM_DERIVED` artifact and could not overwrite this record.

### 6.7 Import manifest

The user-authored import manifest lists the observation JSON and every raw file.
`expected_sha256` may be null before first import; the sealed source manifest
always contains the computed SHA-256. If an expected value is supplied it must
match. All source paths must resolve inside the configured Project EDGE inbox,
and all output paths must resolve inside the repository.

### 6.8 Enrichment and outcome contracts

The enrichment request binds the immutable batch manifest, exact cutoff, exact
MDM snapshot/artifact and manifest hash, approved scope and policies, requested
feature-definition versions, entity identities, software version, and last
eligible completed session.

Each result row exposes:

- `derivation_type = MDM_DERIVED`;
- exact entity and feature version;
- value and typed value state;
- contributing MDM record IDs;
- MDM snapshot and manifest identity;
- maximum contributing economic/session time;
- maximum `available_at`;
- membership/classification effective and availability clocks when applicable;
- cutoff; and
- deterministic row hash.

Outcome documents additionally bind horizon in trading sessions, start/end
sessions, maturity timestamp, calculation timestamp, outcome definition and
version, complete path/terminal state, and MDM lineage. They live only under
`research/leadership_rotation/outcomes`.

---

## 7. Temporal and provenance rules

### 7.1 Four clocks

The source ledger keeps, where applicable:

1. economic/observation time;
2. publication time;
3. source-capture/availability time; and
4. ingestion/seal time.

MDM artifacts additionally bind the MDM vintage. Ingestion time never replaces
availability time.

### 7.2 Timezone law

Every required timestamp must include a UTC offset. Every accompanying timezone
must be an IANA identifier. The offset in the timestamp must equal the IANA zone
offset at that instant, including daylight-saving transitions. Naive timestamps,
missing zones, invalid zones, and offset/zone mismatches fail closed.

### 7.3 Information-cutoff law

Every structured observation timestamp must be no later than the batch cutoff.
For a prospective batch, every raw source must have been captured no later than
the cutoff. A publication timestamp later than cutoff is always rejected.

An unknown publication timestamp can be retained when a contemporaneous raw
capture proves the exact content existed by cutoff. Date-only metadata is not
assigned a favourable intraday time. Without a contemporaneous capture or a
defensible publication time, that source is inadmissible for the prospective
batch and may only enter a retrospective successor batch.

### 7.4 Prospective/retrospective law

`capture_mode` is mandatory at batch, manifest, source, and every market,
instrument, group, stock, futures, and macro record level and must agree
everywhere.

For `PROSPECTIVE`:

- `historical_reconstruction` must be false;
- `contemporaneous_capture_attested` must be true;
- `recorded_at <= information_cutoff_timestamp`;
- every source capture is no later than the cutoff; and
- no source publication is later than the cutoff.

For `RETROSPECTIVE`:

- `historical_reconstruction` must be true;
- retrospective status remains permanently filterable; and
- it can never be relabelled prospective by a later amendment.

Late copying into the repository is not itself proof of retrospective capture;
the manifest records the original capture time and attestation. False
attestation cannot be solved cryptographically by this software and remains a
human-governance responsibility.

### 7.5 Derivation-layer law

Manual transcription of TraderLion or another named source remains
`SOURCE_DERIVED`; `extractor.actor_type = USER` records who performed the
extraction and does not change its origin. A genuinely contemporaneous
`USER_DERIVED` discretionary observation is allowed only with an explicit
`CONTEMPORANEOUS_HUMAN_OBSERVATION` subtype and an immutable analyst-note or
structured-manual raw source. It cannot rewrite, strengthen, or relabel a
`SOURCE_DERIVED` assertion. User interpretation, like model and research
interpretation, belongs in the separate interpretation layer.

`MODEL_DERIVED`, `MDM_DERIVED`, and `RESEARCH_DERIVED` values are always rejected
from the source bundle. They have independent schemas and storage roots.

The validator recursively rejects outcome-bearing keys, including forward
returns, MFE, MAE, threshold hits, outcome labels, targets, future values, and
subsequent-success fields. A legitimate contemporaneous source phrase such as
“failed breakout” remains permitted as verbatim text; the firewall governs
field identity and lineage, not market-language tokens inside source text.

---

## 8. Import and validation transaction

The CLI surface is intentionally small:

```powershell
$env:PYTHONPATH = "src"
python -m edge_lobs validate <observation-json> [--allow-draft]
python -m edge_lobs validate-manifest <import-manifest> --repository-root . [--allow-template] [--observation <observation-json>]
python -m edge_lobs import <import-manifest> --repository-root .
python -m edge_lobs verify-ledger --repository-root .
python -m edge_lobs rebuild-index --repository-root .
python -m edge_lobs mdm-status --repository-root .
python -m edge_lobs validate-enrichment <result-json> --batch-manifest <manifest> --sessions <session-view>
python -m edge_lobs validate-outcomes <outcome-json> --batch-manifest <manifest> --sessions <session-view>
python -m edge_lobs materialise-test-outcomes <outcome-json> --batch-manifest <manifest> --sessions <session-view> --repository-root .
```

`--observation` is accepted only with `--allow-template` when the template's
`observation_path` is null. It cannot override a bound or import-ready
manifest. Draft/template switches produce explicitly non-authoritative
structural reports and are never accepted by `import`.

Import order:

1. resolve and verify repository, inbox, ledger, and manifest containment;
2. strict-load JSON with duplicate-key and non-finite-number rejection;
3. validate schema, IDs, timestamps, timezones, cutoff, capture mode, origins,
   and source lineage;
4. recursively apply the outcome firewall;
5. hash every source and verify optional expected hashes;
6. acquire an exclusive ledger lock;
7. verify the existing complete register and all sealed manifests;
8. reject batch ID, observation ID, source ID, source identity, or raw-content
   duplicates, including identical bytes under a different filename;
9. stage canonical observation, raw bytes, computed source manifest, validation
   report, and artifact manifest;
10. re-hash source and staged bytes immediately before commit;
11. atomically rename the complete batch into place;
12. append and `fsync` the chained seal event;
13. rebuild the convenience index atomically; and
14. verify the committed batch from disk before reporting success.

Every validation failure occurs before a visible batch is created. A crash
between batch rename and register append produces a detectable unregistered
bundle. Every reader and index requires bidirectional register-to-bundle
correspondence and excludes it with `UNREGISTERED_BATCH_PRESENT`. Stage 1 never
automatically admits or deletes such a bundle. Its deterministic safe state is
fail-closed exclusion pending explicit operator review. A future authorised
recovery tool may append a seal only after complete byte, manifest, provenance,
and duplicate revalidation, or may move the bundle to
`ledger/quarantine/unregistered/`; neither future path may silently admit it.

Import also requires exact set equality among batch `source_ids`, import-manifest
source IDs, and computed source-provenance entries. PDF, image, screenshot, and
web-capture sources must be real nonempty files; inline/manual notes cannot stand
in for missing named evidence. The input `validation_status` is descriptive and
never grants authority. Only the computed validation report, immutable batch
manifest, and verified seal register determine state.

---

## 9. MDM enrichment boundary

The enrichment module must never accept caller-supplied market rows as if a
`source_authority = MDM` string were sufficient. Production enrichment consumes
only an admitted feature-ready MDM artifact/read handle after
`verify_production_access()` verifies the artifact bytes, protected release
register, exact source snapshot, approved scope, repository production gate,
and independent rebuild. A freshly verified raw MDM snapshot is not a downstream
alternative; it must first pass the existing MDM gateway, admission, and release
boundary.

Because those gates are presently closed, `mdm-status` reports typed blockers
and production materialisation raises `MDM_ENRICHMENT_PRODUCTION_BLOCKED`.

`validate-enrichment` performs structural/test-only validation only and can
never confer `MDM_DERIVED`, admitted, or research-usable status on caller-authored
values. Production results must be recomputed or verified against the admitted
read handle. The same restriction applies to `validate-outcomes`.

Execution derives the last eligible completed session from the admitted session
rows; it never trusts the request value. A session is eligible only when it is
tradable, `session.available_at <= information_cutoff_timestamp`, and
`session.cutoff_at <= information_cutoff_timestamp`. Any request value must
equal this derived value. Every artifact row is independently filtered by the
observation cutoff because an admitted post-close artifact may contain later
sessions. A timestamp-to-session convenience function that maps a pre-market
time to the upcoming session is not sufficient.

Test-only row validators are permitted and explicitly labelled
`TEST_ONLY_NON_PRODUCTION`. They prove the following invariants:

- snapshot cutoff is not substituted for observation cutoff;
- `available_at <= information_cutoff_timestamp` for every input;
- only sessions whose governed cutoff has elapsed are consumed;
- ticker resolution uses exchange, effective time, cutoff, and stable identity;
- later revisions are excluded rather than exposed through a future-data marker;
- group features require point-in-time membership effective and available by
  cutoff;
- current membership cannot be a fallback;
- cross-sectional ranks retain contemporaneous denominators and coverage;
- no feature ID has an outcome/target/label role; and
- corrected MDM data create a new feature artifact rather than rewriting one.

No composite leadership score or hard-coded `EMERGING`, `ACCELERATING`,
`ESTABLISHED`, `EXTENDED`, or `DETERIORATING` state is created in Stage 1.

---

## 10. Independent outcome boundary

Forward outcomes are separate immutable artifacts that reference, but never
modify, an observation batch. The source observation schema does not contain an
outcome slot.

The initial allowed horizon dictionary is 1, 3, 5, 10, 20, 40, and 60 trading
sessions. The outcome-definition version must supply an approved mechanical
start rule; there is no favourable default. For the initial interface, the first
contributing path instant is the open of the first admitted tradable session
whose `open_at` is strictly after the information cutoff. If a prior completed
close is used as a return baseline, it is baseline state only: no return, MFE,
MAE, high/low interval, threshold path, or other outcome contribution may begin
before that first permissible instant. The existing one-session
`return_consistent_view` is historical measurement input, not automatically a
forward outcome.

An outcome is eligible only when:

- the observation-to-first-outcome clock is frozen;
- the exact exchange-session sequence comes from admitted MDM data;
- the final required session and its approved cutoff have elapsed;
- every price, action, terminal, benchmark, and membership record used was
  available by calculation time;
- terminal and missing paths are typed rather than dropped; and
- the result binds exact MDM and definition versions.

The raw source distribution is never winsorised or trimmed by the outcome
engine. Any later trimmed sensitivity is a secondary, explicitly labelled
research view and cannot replace the raw outcome.

The Stage 1 implementation supplies schemas, maturity/lineage validators, and
separate test-only materialisation. Real calculations remain blocked until the
MDM production gates and required horizon data are available.

---

## 11. Leakage and hindsight threat model

| Threat | Mandatory control |
|---|---|
| Source published after cutoff | Reject publication/capture later than cutoff |
| Same-day post-close bar in morning feature | Require session cutoff and record availability no later than batch cutoff |
| Forward return in observation JSON | Exact schema plus recursive outcome firewall |
| Outcome-derived source label | Reject invalid derivation type and outcome lineage in source layer |
| Historical batch edit | Refuse existing ID; verify file hashes and register on every read |
| Current constituent/group membership | Require effective and availability intervals from admitted MDM history |
| Duplicate raw bytes renamed | Global SHA-256 duplicate check independent of filename |
| Missing/false timezone | IANA zone plus offset consistency |
| Retrospective capture marked prospective | Capture-mode rules, source clocks, reconstruction flag, attestation |
| Later article content attached to earlier batch | Immutable captured bytes, content hash, cutoff check, refuse batch mutation |
| Ticker reuse | Resolve via stable security/listing identity point in time |
| Source taxonomy reconciled with future winning theme | Retain source and MDM taxonomy as independent fields/artifacts |
| Full-history rank/threshold | Require contemporaneous denominator and prior-only fitting |
| Later correction rewrites a feature/outcome | New version and supersession link; no in-place rebuild |
| Extreme winner discarded | Preserve raw outcomes; secondary sensitivity only |

---

## 12. Test plan

All new tests use explicit synthetic/test-only bytes and records. They create no
empirical market evidence.

Mandatory negative tests:

1. source publication after information cutoff;
2. MDM input bar/revision after cutoff;
3. forward return in observation JSON;
4. outcome-derived lineage in source classification;
5. changed observation under an existing batch ID and post-import byte tamper;
6. future/current membership used for a point-in-time group;
7. identical raw source imported under a different filename;
8. missing, naive, invalid, or offset-inconsistent timezone;
9. retrospective provenance labelled prospective; and
10. later article content attached to an already sealed earlier batch.

Additional tests cover duplicate JSON keys, non-finite numbers, path escape,
source change during import, partial-transaction absence, source-ID mismatch,
duplicate observation IDs, origin-layer separation, register-chain tamper,
index rebuild, immutable result bundles, horizon maturity, and CLI failure JSON.

The complete existing test suite must continue to pass unchanged. New evidence,
if retained, receives a separate `evidence/leadership_rotation` namespace; the
Milestone 3 evidence bundle is never rewritten.

---

## 13. Initial 2026-08-11 observation

The supplied transcription is sufficient to create a non-authoritative
structured draft/template containing:

- exact TraderLion market, ETF/index, group/theme, stock, watchlist, and focus
  statements;
- screenshot values exactly as displayed, including approximate timestamp and
  printed precision;
- the article title as source metadata/context only; and
- unresolved stock security IDs.

It is not sufficient to establish the exact timezone-aware batch information
cutoff, exact `recorded_at`, per-source capture/publication clocks and
attestation, or raw evidence hashes. The example will therefore be labelled
`AWAITING_RAW_SOURCES_AND_PROVENANCE` and will not appear under the authoritative
ledger `batches/` directory. It is not called validated, admissible, sealed, or
imported. The screenshot's visible approximate time is retained specifically as
`Europe/Rome` with `APPROXIMATE_MINUTE` precision; it does not establish the
batch cutoff. The article title alone does not establish article content at the
cutoff.

The import template will require the user to place the original files, without
renaming if possible, beneath:

```text
observations/leadership_rotation/inbox/EDGE-LOBS-20260811-001/
```

Required inputs are:

1. original TraderLion / Richard Moglen Trade Lab PDF;
2. original futures screenshot/image;
3. an immutable article capture or exact article metadata/text file; and
4. the provided structured `observation_batch.json`.

The user must replace manifest placeholders for original filenames, paths,
source capture times, publication times when known, timezone, and optional
expected hashes. The importer computes and seals hashes; it never fabricates
them.

---

## 14. Stage 2 scientific handoff

Stage 2 is a proposal only. No hypothesis is tested in this implementation.
The separate proposal will preregister candidate questions including:

- group relative-strength acceleration and future group excess return;
- breadth expansion and leadership persistence;
- momentum-stock density and future group leadership;
- rank transition versus static high rank;
- setup outcomes conditional on independently measured group state;
- incrementality beyond stock RS and setup quality;
- human classifications beyond quantitative features; and
- leadership deterioration and member setup failure.

Continuous variables, persistence, transition matrices, changepoints, hidden
states, clustering, survival, and hazard models are future hypothesis families,
not Stage 1 labels. Any analysis must preserve raw right tails, report full
distributions and dependence-aware uncertainty, retain negative/null/inconclusive
results, control multiplicity, use time-respecting holdouts, and remain
strategy-neutral.

---

## 15. Acceptance mapping

| Acceptance criterion | Design control |
|---|---|
| Raw observations immutable | Exclusive staging, hashes, atomic seal, refuse overwrite, verify on read |
| Point-in-time provenance | Cutoff, capture/publication/ingestion clocks, IANA timezone, source lineage |
| Prospective/retrospective explicit | Mandatory cross-layer capture mode and provenance rules |
| Source isolated from interpretation | Separate schemas and storage roots; origin whitelist |
| No MDM future information | Per-record availability and completed-session cutoff checks |
| Outcomes separate | Independent outcome schema/root; no outcome field in source schema |
| Future setup joins possible | Stable batch/observation/entity IDs and versioned join keys |
| Group and stock separate | Independent arrays, records, IDs, and taxonomies |
| No silent historical edit | Immutable ID collision, file inventory, chained seal verification |
| Leakage tests | Ten mandatory failures plus adversarial integrity tests |
| First observation | Non-authoritative draft plus awaiting-source/provenance manifest; no fabricated validation or import |
| No strategy claim | Infrastructure and Stage 2 proposal only |

---

## 16. Phase B implementation gate

Implementation may proceed only after an internal reviewer confirms:

- no frozen MDM/package/project-contract file will change;
- the observation ledger is capture infrastructure, not a parallel market-data
  vendor;
- screenshot values remain source evidence only;
- MDM enrichment and real outcomes fail closed under current configuration;
- current group membership cannot enter through any fallback;
- source, model/user interpretation, MDM features, outcomes, and research
  conclusions cannot share a mutable record;
- the initial batch cannot be sealed without its original raw files; and
- application-level immutability is not misrepresented as protected production
  authority.

The first review returned `BLOCK` and required: (1) admitted MDM read handles
only; (2) honest draft status for 2026-08-11; (3) precise `USER_DERIVED`
semantics; (4) exclusion/recovery of unregistered crash orphans; (5) derived
last-completed-session and outcome-start clocks; and (6) structural validators
that cannot self-authorise caller-authored MDM/outcome values. All six
corrections are incorporated above.

**Internal review decision:** `APPROVED` by architecture, MDM-boundary, and
adversarial-test reviewers after correction.
