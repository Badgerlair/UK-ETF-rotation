# UKACTIVE-A0A1 — Source and Evidence Policy

> CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY

## Precedence

Material claims use the following order:

1. Exchange, regulator, tax authority, issuer legal document, issuer product page, and index methodology.
2. Issuer catalogue/factsheet and broker instrument record.
3. Reputable ETF database for discovery or corroboration.
4. Local market-data symbols as discovery evidence only.
5. Name-based classification rules only when the wording itself is unambiguous; names never establish UCITS, ISA/SIPP, broker, or historical status.

Conflicts are resolved in favour of the more product-specific primary source, with the conflict left visible. Absence of evidence is represented as `NOT_VERIFIED`, `NOT_DETERMINED`, or `NOT_CHECKED`, never converted to a favourable boolean.

## Claim-level requirements

| Claim | Minimum acceptable evidence in this stage | Prohibited inference |
|---|---|---|
| Listing identity/status | Current LSE catalogue plus ISIN/MIC/ticker/price unit | Price data alone implies broker access |
| UCITS | Issuer/regulatory product fact or legal document | “UCITS” in fund name |
| UK retail document | Current KID/KIID/product-summary URL, checked successfully | LSE listing implies retail eligibility |
| ISA | Issuer product flag or product-specific broker/account evidence, interpreted under current HMRC rules | LSE listing alone |
| SIPP | Issuer flag and, ultimately, scheme/provider confirmation | General pension tax rules imply provider availability |
| IBKR | Exact contract/account read-only result | Local prices or symbol existence |
| Geography | Index objective/methodology and holdings context | Listing currency or domicile |
| Sector/industry/theme | Index methodology, objective, issuer category, and holdings where ambiguous | Theme and sector treated as one field |
| DeepVue | Exact user-confirmed or official/public current label | Similar-sounding invented label |
| Duplicate equivalence | Index objective, hedge state, distribution/share-class identity, and economic equivalence rule | Ticker count equals opportunity count |

## Evidence ledger

`evidence/UKACTIVE_A0A1_EVIDENCE_LEDGER.jsonl` is append-style JSONL with deterministic evidence IDs, URL, publisher, source tier, retrieval timestamp, content hash/capture, supported claims, confidence, and the historical-use warning. Product rows reference evidence IDs rather than embedding unsupported conclusions.

Source captures under `evidence/sources/` include the exact LSE API responses, the iShares catalogue, parsed issuer product facts, and retrieval metadata/hashes for policy pages. KID/KIID PDFs are HTTP-checked and content-hashed but not redistributed.

## Current regulatory interpretation

- HMRC’s current ISA guidance defines qualifying investment categories; it does not justify product-level ISA inference from an exchange line.
- HMRC’s SIPP manual leaves actual scheme investment availability subject to scheme/provider rules.
- During the FCA Consumer Composite Investments transition, permitted current disclosure documents can include the applicable product summary/KID/KIID. This programme records the exact document URL and check result rather than requiring one filename convention.
- Eligibility and rules can change. All conclusions are dated 2026-08-22.

## DeepVue boundary

DeepVue Theme Tracker is descriptive workflow metadata only. The confirmed 31-label list is admitted exactly as supplied by the user. Public DeepVue documentation establishes that themes are curated and separate from GICS, but did not provide a complete current public label export. No additional label was invented.
