# UKACTIVE-A4F-SIPP correctness repair — 2026-08-25

This repair was identified during the pre-commit audit of the first A4F result build. No A4F result build had been committed.

## Defects

1. `POLICY_5_HIGHER_ALPHA_DIAGNOSTIC` is not eligible for selection, but its missing gate value was rendered as truthy in one output table. The selection hierarchy itself already excluded Policy 5.
2. Static M2 fallback candidates that passed the preceding full-history, 2025-exclusion and doubled-cost screens still displayed `PENDING_FAMILY_ROBUSTNESS`. The frozen hierarchy requires the family-removal gate to be complete before a static M2 fallback can be selected.
3. Family-contributor robustness included the largest one and three contributors but omitted the preregistered largest-five diagnostic.

## Repair

- Missing policy-gate values now fail closed, and Policy 5 is explicitly labelled `NOT_ELIGIBLE_HIGHER_ALPHA_DIAGNOSTIC`.
- Every selectable dynamic M2 policy is tested under both immediate and asymmetric-hysteresis switching for leave-one-family-out robustness.
- A static M2 candidate proceeds to family-removal simulation only after passing the earlier staged economic screens. It is ineligible for final selection unless every leave-one-family-out incremental result remains non-negative versus its frozen SWDA replacement control.
- Largest one, three and five family-contributor exclusions are recorded.
- Cost-gate status is keyed by both policy and switch mode.

## Scientific effect

No signal, threshold, allocation map, cost assumption, timing rule, universe rule or promotion threshold changed. The repair completes and correctly reports tests already required by the frozen protocol. All results and the final selection are regenerated from scratch after this repair.
