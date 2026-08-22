# UKACTIVE-A0A1 — Scope and Method

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

## Decision boundary

This is a new, greenfield directed-research programme. `EDGE-UKETF-20260822-001` was used only to identify methodological defects that must not recur. No legacy strategy universe, signal, parameter, rank, portfolio construction, or execution assumption is imported.

This stage constructs a current identity, eligibility, classification, and duplicate-controlled research master. It is **not** a backtest, momentum study, optimisation, portfolio-selection exercise, or evidence that ETF rotation works. No performance result is produced.

## Current discovery scope

The run captured 4,359 current LSE ETF/ETC/ETN listing lines representing 2,821 distinct published ISINs. That full raw catalogue is retained in `UKACTIVE_A0A1_DISCOVERY_REGISTRY.csv`; it is broader than the curated long-only master and includes negative controls and instruments outside the proposed sleeve.

The curated master contains 296 share classes, 478 LSE implementation lines, and 99 economic exposure families. A product can be discovered without being admitted to the curated master, and a candidate can be curated without being called currently investable.

## Mandatory architecture

```text
FUND LEGAL ENTITY
  → SHARE CLASS / ISIN
    → EXCHANGE LISTING / MIC + TICKER + PRICE UNIT

ECONOMIC OPPORTUNITY
  → FUTURE SIGNAL / RANK (NOT BUILT HERE)
    → SELECTED ECONOMIC EXPOSURE (NOT BUILT HERE)
      → BEST ELIGIBLE UK IMPLEMENTATION VEHICLE (CANDIDATE ARCHITECTURE ONLY)
```

Ticker is never an identity key. GBP and GBX are separate price units; GBX is represented as GBP currency with a 0.01 multiplier. Multiple listings of one ISIN remain one share class. Accumulating and distributing share classes remain distinct price identities but normally share one family. Currency-hedged and unhedged products are distinct economic families.

## Discovery and verification workflow

1. Capture the full live LSE Price Explorer ETF, ETC, and ETN catalogues.
2. Apply structural negative-control rules for leverage, inverse, daily-reset, volatility-linked, direct-crypto note, and unsecured note structures.
3. Match economically coherent products into an ordered provider-neutral taxonomy; omit style variants from the initial rotation scope without treating them as proof of unsuitability.
4. Keep several provider/share-class implementations per economic family, but count the family once.
5. Enrich selected iShares share classes with the current UK individual product catalogue, product page, listing table, ISA/SIPP flags, UCITS fact, fees, benchmark, replication, and an HTTP-verified KID/KIID when available.
6. Leave other providers `CURRENT_CANDIDATE_UNVERIFIED` until equivalent product-specific primary evidence is captured.
7. Use the local market-data symbol inventory only as additional discovery metadata. It does not establish eligibility, broker availability, or total-return quality.
8. Run deterministic identity, classification, eligibility, duplicate, and negative-control tests.

## Eligibility semantics

- `CURRENTLY_INVESTABLE`: current LSE snapshot presence, long-only structural suitability, issuer product evidence, issuer ISA eligibility, and a current HTTP-verified KID/KIID. This is still not a guarantee that every broker or SIPP provider carries it.
- `CURRENT_CANDIDATE_UNVERIFIED`: economically relevant current LSE candidate whose full product/account evidence is incomplete.
- `NOT_ELIGIBLE`: structurally unsuitable for the ordinary long-only canonical universe, or deliberately outside the initial scope with a reason code.

No state in this stage is a historical eligibility state. IBKR was not queried because the available local connector was not an exact LSE-ISIN read-only route; every broker field is therefore `NOT_CHECKED`.

## Tier meaning

- `CORE`: broad, persistent, economically distinct exposure with credible implementations.
- `EXTENDED`: narrower but coherent regional, sector, industry, thematic, or diversifying exposure.
- `EXPERIMENTAL`: short-history, concentrated, structurally less settled, or more weakly verified opportunity that merits continued observation.
- `EXCLUDED`: instrument/exposure outside the canonical research master, retained with a reason code.

Tiers are research breadth controls, not recommendations or portfolio weights.
