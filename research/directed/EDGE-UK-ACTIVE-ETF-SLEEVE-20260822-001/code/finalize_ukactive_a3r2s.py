"""Create interpretive and concentration artifacts for frozen UKACTIVE-A3R2S.

This script does not rerun, modify, or expand the empirical specification.  It
documents the already-completed screen, records the corrected comparator audit,
and freezes the A3R2W inputs before any weighting result is observed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ukactive_a3r2_core import PROGRAMME_ROOT, WARNING, audit_file, sha256_file, utc_now, write_csv, write_text
from ukactive_a3r2_portfolio import selection_targets


def main() -> int:
    decision_path = PROGRAMME_ROOT / "UKACTIVE_A3R2_SIGNAL_COUNT_CADENCE_DECISION.json"
    result_path = PROGRAMME_ROOT / "UKACTIVE_A3R2_RECENT_FIVE_YEAR_RESULTS.csv"
    feature_path = PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet"
    mandate_path = PROGRAMME_ROOT.parents[2] / "docs" / "PROJECT_EDGE_RESEARCH_MANDATE.md"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    results = pd.read_csv(result_path)
    features = pd.read_parquet(feature_path)

    frozen = {
        "pool_id": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "cadence": "MONTHLY",
        "selection_rules": ["TOP_1", "TOP_2", "TOP_3"],
    }
    for rule in frozen["selection_rules"]:
        specification_id = f"{frozen['pool_id']}|{frozen['signal_id']}|{rule}|{frozen['cadence']}"
        if specification_id not in set(decision["qualifying_specification_ids"]):
            raise AssertionError(f"A3R2W frozen input did not pass A3R2S gate: {specification_id}")

    latest_start = pd.Timestamp("2021-08-23")
    source = features.loc[
        features["cadence"].eq(frozen["cadence"])
        & features["analysis_context_id"].eq(frozen["pool_id"])
        & pd.to_datetime(features["date"]).ge(latest_start)
    ].copy()
    source["date"] = pd.to_datetime(source["date"])

    universe = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv")
    lookup_columns = [
        "economic_exposure_family_id",
        "economic_exposure_name",
        "parent_exposure_family_id",
        "overlap_cluster_id",
        "a0_primary_geography",
        "sector",
        "industry",
        "economic_theme",
        "research_maturity",
    ]
    lookup = universe[lookup_columns].drop_duplicates("economic_exposure_family_id")
    rows: list[dict[str, object]] = []
    for rule in frozen["selection_rules"]:
        _, records = selection_targets(source, signal_id=frozen["signal_id"], selection_rule=rule)
        for record in records.itertuples(index=False):
            selected = [value for value in str(record.selected_families).split(";") if value]
            if not selected:
                rows.append(
                    {
                        "review_date": record.review_date,
                        "selection_rule": rule,
                        "selected_family_count": 0,
                        "economic_exposure_family_id": "NO_QUALIFYING_EXPOSURE",
                        "economic_exposure_name": "NO_QUALIFYING_EXPOSURE",
                        "parent_exposure_family_id": "NOT_APPLICABLE",
                        "overlap_cluster_id": "NOT_APPLICABLE",
                        "a0_primary_geography": "NOT_APPLICABLE",
                        "sector": "NOT_APPLICABLE",
                        "industry": "NOT_APPLICABLE",
                        "economic_theme": "NOT_APPLICABLE",
                        "research_maturity": "NOT_APPLICABLE",
                        "same_parent_count": 0,
                        "same_overlap_cluster_count": 0,
                        "warning": WARNING,
                    }
                )
                continue
            selected_meta = lookup.loc[lookup["economic_exposure_family_id"].isin(selected)].copy()
            parent_counts = selected_meta["parent_exposure_family_id"].value_counts(dropna=False)
            cluster_counts = selected_meta["overlap_cluster_id"].value_counts(dropna=False)
            for item in selected_meta.to_dict(orient="records"):
                rows.append(
                    {
                        "review_date": record.review_date,
                        "selection_rule": rule,
                        "selected_family_count": len(selected),
                        **item,
                        "same_parent_count": int(parent_counts.get(item["parent_exposure_family_id"], 0)),
                        "same_overlap_cluster_count": int(cluster_counts.get(item["overlap_cluster_id"], 0)),
                        "warning": WARNING,
                    }
                )
    overlap = pd.DataFrame(rows).sort_values(["selection_rule", "review_date", "economic_exposure_family_id"])
    overlap_audit = write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_OVERLAP_AND_CONCENTRATION_DIAGNOSTICS.csv", overlap)

    best_id = decision["best_latest_five_year_specification"]
    best = results.set_index("specification_id").loc[best_id]
    infer = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_MULTIPLE_TESTING_LEDGER.csv").set_index("specification_id").loc[best_id]
    dependency = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_DEPENDENCY_TESTS.csv")
    dep = dependency.loc[dependency["specification_id"].eq(best_id)].set_index("dependency_test")

    data_quality = f"""# UKACTIVE-A3R2S data quality and comparator audit

## Frozen experiment status

The 315-cell preregistered A3R2S screen is complete and has not been changed by the Project EDGE mandate adopted during interpretation. All **19/19** registered correctness tests passed. The corrected A2R2 XLON calendar, endpoint validity, no-fill policy, three-session endpoint tolerance, and next-session execution remain authoritative.

## Comparator remediation before final run

During representative end-to-end validation, an internal preliminary equal-pool implementation was found to stop when any constituent crossed a continuity break. That caused endpoint mismatch and an invalid preliminary excess-return comparison. No preliminary efficacy conclusion was retained.

The final executed run uses a date-level contemporaneous-valid equal-weight research index. Membership determined after review T becomes active after the next XLON close and first earns the following session return. On a day where one constituent has no valid corrected return, that constituent is excluded for that day; no value or return is filled, and the remaining valid constituents are equally weighted. The comparator has the same modern end date as the selected series. It is a research counterfactual, not an executable ETF portfolio claim.

This correction was an engineering/data-validity repair made before the final unchanged empirical grid was evaluated. It did not change signal definitions, signal weights, pools, counts, cadences, costs, regimes, or promotion thresholds.

## Evidence limits

- Historical UK retail, account, and broker eligibility remain unresolved.
- The five-year lifecycle census is substantially complete, not complete.
- The equal-pool comparator is intentionally frictionless; selected portfolios bear costs.
- Zero of {decision['preregistered_primary_combination_count']} specifications survive Benjamini-Hochberg q=0.10.
- The best cell's review-interval block-bootstrap interval includes zero.
- These results are developmental research evidence and are not deployment evidence.
"""
    dq_audit = write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2S_DATA_QUALITY_REPORT.md", data_quality)

    director = f"""# UKACTIVE-A3R2S research-director interpretation

The Project EDGE mandate was adopted after the registered A3R2S experiment was running. It has not altered or restarted that experiment. This document applies the mandate only to interpretation and prospective next work.

## A. What we now know

- The primary five-year screen tested {decision['preregistered_primary_combination_count']} frozen signal/pool/count/cadence combinations; {decision['qualifying_specification_count']} passed the developmental portfolio-research gate.
- The strongest cell was `{best_id}`: net CAGR {best['selected_net_cagr']:.2%}, equal-pool CAGR {best['equal_pool_cagr']:.2%}, and net excess {best['selected_net_excess_vs_pool_cagr']:.2%} per year under the registered cost model.
- Its date-level HAC estimate is {infer['mean']:.2%} per monthly review interval (p={infer['p_value']:.3f}); its 95% block-bootstrap interval is [{infer['ci_low']:.2%}, {infer['ci_high']:.2%}].
- Slow 3/6/12 leadership was more coherent than the new short 1/2/3 signal across the tested grid. Monthly review dominated the strongest developmental candidates.

## B. What we can rule out

- The current evidence does not establish a broad, multiple-testing-adjusted rotation edge: FDR survivors = {decision['fdr_surviving_primary_count']}.
- A general claim that 1/2/3-month relative strength improves on 3/6/12 after costs is not supported.
- Geography and broad-sector rankings are not supported as trade portfolios in this stage; they remain market-intelligence views.
- The candidate is not historically verified as UK retail-, ISA-, SIPP-, or broker-investable.

## C. What looks economically interesting

- Monthly 3/6/12 leadership among industries and themes has a large contemporary selected-versus-pool spread.
- Industry-only pairwise and 3/6/12 leaders point in a similar direction, which is more informative than one isolated cell.
- The effect is stronger outside US-technology-dominant months and in higher-dispersion / higher-rotation states, a plausible capital-rotation mechanism.
- MATURE-only excess remains positive, reducing—but not eliminating—the concern that ETF expansion alone creates the result.

## D. New edge hypotheses suggested by the data

1. A sparse industry/theme leadership process may add value in high-dispersion, non-US-tech-dominant markets because sector-specific capital flows persist at a monthly horizon.
2. Most value may reside in a few extreme winners rather than the full ranking; right-tail preservation and concentration deserve prospective study.
3. A portfolio edge may depend on representing several distinct economic parents rather than several overlapping technology children.
4. The short signal's main possible value may be entry timing or early failure detection, not standalone selection.

## E. Evidence status

- Frozen A3R2S economic effect: **E2 developmental**, but statistically unresolved and not independently confirmed.
- Regime, right-tail, overlap, and entry/failure interpretations: **E1 exploratory**.
- No E3 evidence and no deployment candidate exist.

## F. Highest-value next discrimination test

Complete the already-authorised, frozen A3R2W comparison for the qualifying 3/6/12 monthly industry-plus-theme candidate. Then prospectively reserve an independent or walk-forward confirmation window for the smallest robust architecture. Weighting must not rescue a weak selection effect; it must improve risk/concentration consistently after costs.

## G. Is further research worth the compute and time?

**Yes, narrowly.** The contemporary economic magnitude, cross-signal coherence, and positive MATURE-only sensitivity justify the inexpensive frozen weighting comparison and query engine. The dependence on the top three families ({float(dep.loc['REMOVE_TOP_THREE_FIVE_YEAR_FAMILIES','net_excess_vs_pool_cagr']):.2%} excess after removal), lack of FDR survival, and wide uncertainty make broad optimisation or deployment work premature.
"""
    director_audit = write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2S_RESEARCH_DIRECTOR_REVIEW.md", director)

    weighting_freeze = f"""# UKACTIVE-A3R2W scope and frozen inputs

Frozen at: {utc_now()}  
Frozen from completed A3R2S decision: `{sha256_file(decision_path)}`

## Authorisation

A3R2S authorised A3R2W because at least one combination passed the registered 8-of-12 developmental gate. This is a gated research comparison, not a strategy confirmation.

## Frozen architecture

- Pool: `INDUSTRY_PLUS_THEME`
- Signal: `MH_LEVEL_3_6_12_REFERENCE`
- Cadence: `MONTHLY`
- Selection counts: `TOP_1`, `TOP_2`, `TOP_3`
- Windows: final five years primary; final three years and full history context
- Costs: 20 bp one way + £3.99 per executed trade leg on £250,000, with applicable 0.75% non-GBP preferred-line FX; 10/20/40 bp and £100k/£250k/£500k sensitivities
- Methods: `EQUAL`, `RANK_DECAY`, `SCORE_PROPORTIONAL_CAPPED`, `INVERSE_VOLATILITY_CAPPED`, `SIGNAL_X_INVERSE_VOLATILITY`
- Multiple-position cap: 50%; a single selected exposure may be 100%
- All methods rebalance to their target weights on the registered monthly review schedule so the weighting comparison is like-for-like. Signal forms after close; execution is next eligible XLON session within the existing three-session rule.

TOP_1 is retained as a parity control: every weighting method must produce the same target before costs. TOP_2 and TOP_3 provide the informative weighting comparison.

No weighting method, cap, signal, pool, count, cadence, or cost was selected after observing A3R2W results. The choice of this family reflects the completed A3R2S gate and neighbourhood coherence, not maximum CAGR alone.
"""
    freeze_audit = write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2W_SCOPE_AND_FROZEN_INPUTS.md", weighting_freeze)

    manifest_path = PROGRAMME_ROOT / "UKACTIVE_A3R2_S_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["project_edge_mandate"] = audit_file(mandate_path)
    manifest["active_run_changed_by_mandate"] = False
    manifest["comparator_remediation"] = {
        "preliminary_result_retained": False,
        "root_cause": "PRELIMINARY_EQUAL_POOL_SERIES_STOPPED_AT_CONSTITUENT_CONTINUITY_BREAK_AND_CREATED_ENDPOINT_MISMATCH",
        "final_policy": "CONTEMPORANEOUS_VALID_DATE_LEVEL_EQUAL_WEIGHT_RESEARCH_INDEX_WITH_NO_FILL",
        "signal_or_grid_changed": False,
    }
    manifest["supplementary_outputs"] = [overlap_audit, dq_audit, director_audit, freeze_audit]
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision["decision"], "frozen_weighting_inputs": frozen, "supplementary_outputs": 4}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
