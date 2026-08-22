# Project EDGE — MDM Data Foundation

This repository now contains the first implemented Project EDGE data slice: a
strict, read-only boundary from an authorised Market Data Manager snapshot to an
immutable, outcome-free daily equity panel and a separate return-consistent
view.

Production research is deliberately blocked at present. The audited MDM state
does not yet provide every Mandatory identity, calendar, corporate-action,
terminal-outcome, universe, and immutable-replay capability, and the Project
EDGE Population and Time Contract has not been ratified. Synthetic acceptance
evidence proves the implementation mechanics only; it contains no empirical
market evidence and cannot pass the production-use gate. The protected release
authority and mutation-safe consumer read boundary are also not configured.

## Implemented boundary

The only accepted source is a strict five-table Parquet snapshot whose manifest
identifies MDM as the authority and binds exact schemas, types, row counts,
physical hashes, logical hashes, source vintage, cutoff, replayability,
completeness, classification, and authorisation scope.

The implemented daily path performs:

1. verified, read-only MDM intake;
2. point-in-time stable identity and ticker resolution;
3. exchange-session and cutoff enforcement;
4. historical candidate and eligible population reconstruction;
5. raw unadjusted OHLCV assembly without dropping missing or terminal rows;
6. split, cash-distribution, and terminal-return reconciliation in a separate
   return view;
7. governed point-in-time joins and an outcome firewall;
8. fourteen fail-closed Mandatory admissibility checks;
9. field- and dataset-level lineage;
10. deterministic replay, immediate pre-write revalidation, and
    software-source fingerprints;
11. immutable candidate artifacts, exact disk re-verification, independent
    fresh verification from the scope-bound MDM root, source rebuild before any
    production release, chained release records, revocation/supersession, and
    access-time integrity checks;
12. append-only evidence for failed CLI build attempts.

The Milestone 3 package under `src/edge_mdm` contains no discovery engine,
hypothesis test, feature generator, optimiser, strategy, portfolio, broker,
execution, or live-trading component. Pre-existing or concurrent material under
`research/` is outside this milestone and is not an implementation input,
dependency, or part of the retained M3 test-evidence binding.

## Runtime

- Python 3.12
- DuckDB 1.5.3

The runtime dependency is pinned in `requirements.lock`.

## Commands

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m edge_mdm audit-status --repository-root .
python -m pytest -q --basetemp tests/.pytest_tmp
```

The current result is `79 passed`. The in-repository base-temp argument keeps
all generated test evidence inside Project EDGE.

The audit command currently exits with status 2 because production prerequisites
are unresolved. This is the correct fail-closed state.

To verify a future production MDM snapshot:

```powershell
python -m edge_mdm verify-source `
  --manifest <MDM-SNAPSHOT-MANIFEST> `
  --mdm-root <AUTHORISED-MDM-ROOT>
```

To build a future production candidate, a ratified production policy and an
independent approved scope are both required. The command below is prospective:
the current executable allowlist contains only the synthetic test policy. After
ratification, the exact production policy identifiers and semantics must still
be code-bound and pass the Mandatory policy tests before this command can
execute a production bundle.

```powershell
python -m edge_mdm build-daily-slice `
  --manifest <MDM-SNAPSHOT-MANIFEST> `
  --mdm-root <AUTHORISED-MDM-ROOT> `
  --policy <RATIFIED-DAILY-SLICE-POLICY> `
  --production-scope <APPROVED-PRODUCTION-SCOPE> `
  --repository-root . `
  --output-root artifacts/production `
  --builder-id <BUILDER-ID>
```

Test-only verification requires the explicit `--allow-test-only` flag and still
cannot produce a production release.

## Current evidence and decision

- Machine-readable MDM capability audit:
  `config/mdm_capability_audit.v1.json`
- Population/time decision gate:
  `config/population_time_contract.v1.json`
- Production release-authority gate:
  `config/production_release_authority.v1.json`
- Governance traceability limitation: no canonical Milestone 1 Scientific
  Governance Specification file or governing hash is currently present in this
  repository; it must be bound before production research.
- Synthetic acceptance evidence:
  `artifacts/milestone3/synthetic_acceptance/acceptance_summary.json`
- Content-addressed full test evidence:
  `evidence/milestone3/EDGE-M3-PYTEST-D8958518BCA763637BB5874DC082A89100F8A3FB9F878C4D09950BB6166CD69B/manifest.json`
- Full milestone result and remaining work:
  `PROJECT_EDGE_MILESTONE_3_IMPLEMENTATION_REPORT.md`

The implementation is ready to attempt a bounded conforming snapshot and fail
closed on any source-contract deficiency. The scientific platform is not yet
ready for its first empirical phenomenon-discovery experiment because no real
MDM snapshot currently passes the frozen Mandatory release gates and production
authority is not yet operationally protected.

## Directed research capability admission

Prospective directed research capabilities are governed separately from the
frozen Milestone 3 production-release boundary. The machine-readable policy and
registry at `config/research_capability_registry.v1.json` admits the authorised
lagged-liquidity PIT Top-500 interface, causal close-observed/next-open
execution, and split-continuous-signal/raw-open execution for new research.
This admission does not retroactively change older experiments or grant a
production promotion.

The authoritative home for future Mean Reversion research is
`research/directed/EDGE-MEAN-REVERSION-20260822-001`. Its canonical QP parity
run is a retained research/control result; QP remains not promoted to
production.
