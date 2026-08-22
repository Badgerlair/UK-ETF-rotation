# UKACTIVE-A0A1 — Data-Source Audit for Future Total-Return Research

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

No return series was constructed and no strategy was run. This audit records what a later A2 stage must validate.

| Source | Current use / potential coverage | Distributions & corporate actions | Survivorship / depth | Licensing & cost | A2 suitability |
|---|---|---|---|---|---|
| London Stock Exchange Price Explorer | Primary current identity/listing discovery; 4,359 observed lines | No validated adjusted/total-return history in this endpoint | Current snapshot; cannot reconstruct delistings or historical eligibility | Public web/API access subject to LSE terms; redistribution must remain reviewed | Strong current discovery input; insufficient alone |
| Issuer product pages, KIDs/KIIDs, prospectuses, factsheets | Primary legal/product metadata, benchmarks, fees, share-class/listing dates, current disclosure | Issuer distribution histories may be available product by product; methods vary | Usually live products; removed products and old documents can disappear | Public documents, issuer terms apply | Essential identity/eligibility evidence; archive exact dated documents |
| iShares UK product catalogue/pages | Structured current issuer facts and product-specific primary evidence | NAV/performance fields exist but were deliberately not used; distribution validation still required | Mainly current products; no complete delisted-universe guarantee | Public issuer access; terms apply | Useful primary feed for covered provider, not a cross-provider history solution |
| Local market-data inventory (`D:\Codex\market_data_manager\outputs\archive_summary\discovered_all_symbols.csv`) | Read-only discovery overlap; 20,861 symbols in inventory | Not established by the inventory file | Inventory dates show observed coverage, not eligibility; delisted coverage unknown | Existing local entitlement; upstream source terms govern | Candidate input only after A2 validates adjusted prices, distributions, FX and symbol/ISIN mapping |
| EODHD (underlying local-source candidate) | Daily OHLC/adjusted fields and LSE symbols may be available under the existing service | Adjustment/distribution semantics require instrument-level reconciliation | Coverage and delisted ETF availability must be measured, not assumed | Paid subscription / existing account terms; exact incremental cost not determined here | Potential bulk history input after validation; not authoritative eligibility evidence |
| justETF and similar reputable ETF databases | Discovery/corroboration, index and fee cross-checks | Some distribution/performance information, methodology not an authoritative corporate-action ledger | Primarily current/survivor products | Database terms and redistribution restrictions; free/paid tiers vary | Secondary corroboration only |
| Stooq / Yahoo Finance-like public data | Quick secondary price cross-checks | Adjusted-close and cash-distribution completeness can change and must be reconciled | Symbols and delisted coverage inconsistent | Public access/terms; not a guaranteed research licence | Never the sole total-return source |
| LSEG Data & Analytics, Bloomberg, FactSet, Morningstar Direct | Licensed reference, corporate actions, delistings, fund histories and identifiers depending package | Stronger institutional corporate-action and total-return coverage | Potentially deep, but entitlement/package dependent | Commercial quotation / material cost | Preferred validation/reference layer if available |
| Bank of England / ECB official series | GBP rates, SONIA and selected FX reference data | Not fund distributions | Deep official macro/rate history | Public-source terms | Strong reference for cash benchmarks/FX; still requires timestamp and holiday alignment |
| Index-provider total-return indices | Benchmark-level gross/net total return for exposure validation | Embedded under index methodology | Often deep; product/index mapping and licensing matter | Frequently licensed, sometimes public factsheets only | Valuable family-signal proxy validation, never a substitute for investable ETF return |

## Required A2 controls

1. Establish identifier history across ticker changes, relistings, mergers, closures, and delistings.
2. Reconstruct point-in-time listing, retail-document, ISA/SIPP and broker eligibility; do not reuse this survivor snapshot.
3. Validate GBP versus GBX units before any return calculation.
4. Reconcile adjusted prices against cash distributions and corporate actions for representative accumulating and distributing share classes.
5. Translate non-GBP total returns with explicit, independently validated FX series and close-time convention.
6. Compare product total return with the correct benchmark (gross/net, hedged/unhedged) and explain residuals from fee, tax, tracking and sampling.
7. Quantify stale prices, missing days, zero volumes, bid/ask quality, assets under management and closure risk.
8. Preserve licensed-source provenance and redistribution constraints in every derived dataset.

The local inventory hash and exact source-capture hashes are in `UKACTIVE_A0A1_MANIFEST.json`. Price availability never changes an eligibility or broker state in this stage.
