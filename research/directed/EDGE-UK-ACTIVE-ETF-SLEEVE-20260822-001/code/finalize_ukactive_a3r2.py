"""Create the consolidated UKACTIVE-A3R2 decision and reproducibility manifest."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow

from ukactive_a3r2_core import PROGRAMME_ROOT, PLATFORM_ROOT, WARNING, audit_file, git_output, sha256_file, utc_now, write_csv, write_json, write_text


OVERALL_DECISION = "UKACTIVE_A3R2_REGIME_CONDITIONAL_CANDIDATE_FOUND"
BEST_ID = "INDUSTRY_PLUS_THEME|MH_LEVEL_3_6_12_REFERENCE|TOP_1|MONTHLY"


def main() -> int:
    u = json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2U_DECISION.json").read_text(encoding="utf-8"))
    s = json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2_SIGNAL_COUNT_CADENCE_DECISION.json").read_text(encoding="utf-8"))
    w = json.loads((PROGRAMME_ROOT / "UKACTIVE_A3R2W_DECISION.json").read_text(encoding="utf-8"))
    regime = json.loads((PROGRAMME_ROOT / "UKACTIVE_CURRENT_REGIME_STATE.json").read_text(encoding="utf-8"))
    five = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_RECENT_FIVE_YEAR_RESULTS.csv")
    three = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_RECENT_THREE_YEAR_RESULTS.csv")
    inference = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_MULTIPLE_TESTING_LEDGER.csv")
    sensitivities = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_UNIVERSE_EXPANSION_SENSITIVITY.csv")
    dependencies = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_DEPENDENCY_TESTS.csv")
    costs = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_TURNOVER_AND_COSTS.csv")
    counts = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_ACTIVE_FAMILY_COUNTS_BY_YEAR.csv")
    best = five.set_index("specification_id").loc[BEST_ID]
    best3 = three.sort_values("selected_net_excess_vs_pool_cagr", ascending=False).iloc[0]
    best_inference = inference.set_index("specification_id").loc[BEST_ID]
    best_sensitivity = sensitivities.loc[sensitivities["specification_id"].eq(BEST_ID)].set_index("universe_view")
    best_dependency = dependencies.loc[dependencies["specification_id"].eq(BEST_ID)].set_index("dependency_test")

    geo = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_GEOGRAPHIC_LEADERSHIP.csv")
    industry = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_INDUSTRY_LEADERSHIP.csv")
    theme = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_THEME_LEADERSHIP.csv")
    current_geo = geo.loc[geo["short_1_2_3_composite"].notna()].head(10)["economic_exposure_family_id"].tolist()
    current_industry = industry.loc[industry["short_1_2_3_composite"].notna()].head(10)["economic_exposure_family_id"].tolist()
    current_theme = theme.loc[theme["short_1_2_3_composite"].notna()].head(10)["economic_exposure_family_id"].tolist()

    pool_decisions = {
        "GEOGRAPHY": "MARKET_INTELLIGENCE_ONLY",
        "COUNTRY": "MARKET_INTELLIGENCE_ONLY",
        "SECTOR": "MARKET_INTELLIGENCE_ONLY",
        "INDUSTRY": "REGIME_CONDITIONAL_RESEARCH_CANDIDATE",
        "THEME": "REGIME_CONDITIONAL_RESEARCH_CANDIDATE",
        "INDUSTRY_PLUS_THEME": "REGIME_CONDITIONAL_RESEARCH_CANDIDATE",
        "ALL_EQUITY_OPPORTUNITIES": "MARKET_INTELLIGENCE_ONLY",
    }
    candidate_signals = [
        "INDUSTRY_PLUS_THEME|MH_LEVEL_3_6_12_REFERENCE|TOP_1|MONTHLY|EQUAL",
        "INDUSTRY|PAIRWISE_MAJORITY_5H|TOP_1|MONTHLY|EQUAL (SECONDARY)",
        "INDUSTRY|MH_LEVEL_3_6_12_REFERENCE|TOP_1|MONTHLY|EQUAL (SECONDARY)",
        "THEME|MH_LEVEL_EQ_OR_RECENCY_TILT|TOP_1_TO_2|MONTHLY (E1/E2-DEVELOPMENTAL)",
    ]
    rejected = [
        "GENERAL_SHORT_RS_1_2_3_SUPERIORITY_AFTER_COSTS",
        "GENERAL_60_DAY_CENTERED_SUPERIORITY",
        "GEOGRAPHY_AS_AUTOMATED_TRADE_PORTFOLIO",
        "BROAD_SECTOR_AS_AUTOMATED_TRADE_PORTFOLIO",
        "NON_EQUAL_WEIGHTING_IMPROVEMENT",
        "ACCELERATION_AS_PRIMARY_PORTFOLIO_SIGNAL",
    ]
    decision = {
        "stage_id": "UKACTIVE-A3R2",
        "run_id": "UKACTIVE-A3R2-20260823-001",
        "decision": OVERALL_DECISION,
        "decision_timestamp": utc_now(),
        "universe_refresh_decision": u["decision"],
        "signal_count_cadence_decision": s["decision"],
        "weighting_decision": w["decision"],
        "query_engine_decision": "UKACTIVE_A3R2Q_PASS",
        "pool_decisions": pool_decisions,
        "best_final_five_year_specification": BEST_ID,
        "best_final_three_year_specification": best3["specification_id"],
        "best_selection_count": "TOP_1",
        "best_cadence": "MONTHLY",
        "preferred_weighting_method": w["preferred_weighting_method"],
        "candidate_signals": candidate_signals,
        "rejected_claims_or_signal_families": rejected,
        "fdr_surviving_specification_count": s["fdr_surviving_primary_count"],
        "evidence_status": "E2_DEVELOPMENTAL_STATISTICALLY_UNRESOLVED_WITH_E1_REGIME_INTERPRETATION",
        "deployment_candidate": False,
        "historically_verified_uk_investable_strategy": False,
        "supports_later_controlled_confirmation_and_eligibility_reconstruction": True,
        "automatic_next_stage_authorised": False,
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3R2_DECISION.json", decision)

    candidate_md = f"""# UKACTIVE-A3R2 research candidates

## Primary developmental candidate

`{candidate_signals[0]}`

- Final-five-year gross CAGR: {best['selected_gross_cagr']:.2%}
- Final-five-year net CAGR: {best['selected_net_cagr']:.2%}
- Equal-pool CAGR: {best['equal_pool_cagr']:.2%}
- Global developed benchmark CAGR: {best['global_benchmark_cagr']:.2%}
- Net excess versus pool: {best['selected_net_excess_vs_pool_cagr']:.2%} per year
- Selected-versus-unselected spread: {best['selected_vs_unselected_cagr_spread']:.2%} per year
- Maximum drawdown: {best['selected_net_maximum_drawdown']:.2%}
- Annual traded-notional turnover: {best['selected_net_annual_turnover_traded_notional']:.2f}x
- HAC p-value: {best_inference['p_value']:.3f}; block-bootstrap 95% interval [{best_inference['ci_low']:.2%}, {best_inference['ci_high']:.2%}]
- FDR status: not surviving q=0.10

Classification: **REGIME_CONDITIONAL_RESEARCH_CANDIDATE**, evidence level **E2-developmental / statistically unresolved**. It is not a deployment candidate or a historically verified UK-investable strategy.

## Secondary candidates

- Industry pairwise TOP_1 monthly.
- Industry 3/6/12 TOP_1 monthly.
- Theme equal-five-horizon / recency-tilt monthly evidence, treated cautiously because the contemporary sample and product population are newer.

## Rejected or not promoted

{chr(10).join(f'- `{item}`' for item in rejected)}

Equal weight remains the retained baseline; no non-equal weighting method passed the frozen stability rule.
"""
    write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2_RESEARCH_CANDIDATES.md", candidate_md)

    unresolved = pd.DataFrame(
        [
            {"item_id": "A3R2-OPEN-001", "severity": "BLOCKS_DEPLOYMENT_NOT_RESEARCH", "status": "OPEN", "item": "Historical UK retail, ISA/SIPP and broker availability remain unresolved", "next_control": "Point-in-time deployment eligibility reconstruction"},
            {"item_id": "A3R2-OPEN-002", "severity": "RESEARCH_LIMITATION", "status": "OPEN", "item": "Recent five-year lifecycle census is substantially complete, not complete", "next_control": "Acquire authoritative historical LSE listing/closure feed or continue primary-source census"},
            {"item_id": "A3R2-OPEN-003", "severity": "CLAIM_LIMITATION", "status": "OPEN", "item": "No A3R2 primary specification survives FDR q=0.10", "next_control": "Independent or prospectively isolated confirmation"},
            {"item_id": "A3R2-OPEN-004", "severity": "CLAIM_LIMITATION", "status": "OPEN", "item": "Top-three-family removal erases the headline excess", "next_control": "Right-tail attribution and out-of-sample confirmation without refitting"},
            {"item_id": "A3R2-OPEN-005", "severity": "IMPLEMENTATION_LIMITATION", "status": "OPEN", "item": "Bid/ask and fixed-fee model is standardised; historical realised spreads are unavailable", "next_control": "Deployment-route quote/spread reconstruction"},
        ]
    )
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_UNRESOLVED_ITEMS.csv", unresolved)

    dq = f"""# UKACTIVE-A3R2 consolidated data-quality report

- A2R2 corrected calendar and return-validity chain retained unchanged.
- A3R2U: {u['tests_passed']}/{u['tests_total']} tests passed.
- A3R2S: {s['correctness_tests_passed']}/{s['correctness_tests_total']} tests passed after the preliminary comparator endpoint defect was corrected and discarded before the final screen.
- A3R2W: {w['correctness_tests_passed']}/{w['correctness_tests_total']} tests passed.
- A3R2Q: 8/8 tests passed.
- No prices or returns were forward-filled; stale observations remained invalid.
- Current ii confirmations are metadata dated 2026-08-23 and are never back-projected.
- The current LSE line reconciliation found {u['current_lse_line_count']:,} lines and no line-level change versus the prior official capture. The five-year lifecycle census is **{u['recent_five_year_census_classification']}**.
- Historical UK retail/account/broker eligibility is unresolved, so no output is a deployment backtest.
"""
    write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2_DATA_QUALITY_REPORT.md", dq)

    director = f"""# UKACTIVE-A3R2 research-director review

## A. What we now know

- Contemporary industry/theme leadership contains a large but statistically unresolved top-tail effect. The strongest frozen cell is `{BEST_ID}` with {best['selected_net_excess_vs_pool_cagr']:.2%} annualised net excess over its contemporaneous equal-weight pool.
- The effect survives static-start ({best_sensitivity.loc['FIVE_YEAR_START_STATIC','selected_net_excess_vs_pool_cagr']:.2%}) and MATURE-only ({best_sensitivity.loc['MATURE_ONLY','selected_net_excess_vs_pool_cagr']:.2%}) views, so universe expansion is not a complete explanation.
- It does not survive removal of the top three five-year families ({best_dependency.loc['REMOVE_TOP_THREE_FIVE_YEAR_FAMILIES','net_excess_vs_pool_cagr']:.2%}), indicating material right-tail dependence.
- Monthly 3/6/12 leadership is more coherent than broad short 1/2/3 or 60-day-centred superiority. Equal weighting remains the least-complex supported implementation baseline.
- Geography, country, and broad sectors remain valuable market intelligence even though portfolio efficacy is not established.

## B. What we can rule out

- No broad multiple-testing-adjusted portfolio edge is established: {s['fdr_surviving_primary_count']} of {s['preregistered_primary_combination_count']} primary cells survive FDR q=0.10.
- A universal short-horizon advantage, a robust acceleration rule, and a non-equal weighting improvement are not supported.
- Current ii visibility, LSE status, or public eligibility cannot be treated as historical account eligibility.

## C. What looks economically interesting

- The effect is strongest in high dispersion, medium breadth, high rotation, and especially non-US-technology-dominant observations; this is coherent with cross-industry capital rotation.
- TOP_1 produces the largest contemporary effect, suggesting the edge—if real—is sparse and right-tail dependent rather than a broad-ranking phenomenon.
- Themes show stronger recent evidence than in long-history A3R1R1, but their newer population and higher turnover require cautious interpretation.

## D. New edge hypotheses

1. Slow leadership selects the economic winner, while short 1/2/3 information may be useful only for entry, failure recognition, or state transition.
2. Rotation efficacy may be causal through cross-sectional dispersion and breadth rather than a generic risk-on effect.
3. The economically important component may be right-tail preservation: avoid diluting the rare leading industry/theme while controlling false-leader losses.
4. Parent/overlap diversity may improve portfolio robustness prospectively, but must not be retrofitted to this sample.

## E. Evidence status

- Frozen selection architecture: **E2 developmental**, statistically unresolved.
- Regime, right-tail, entry/failure, and overlap mechanisms: **E1 exploratory**.
- Query outputs: descriptive market intelligence, not empirical proof.
- E3 independent confirmation: absent.

## F. Highest-value next discrimination test

Prospectively freeze the smallest architecture—monthly 3/6/12 industry-plus-theme leadership, TOP_1 plus a TOP_2 robustness control, equal weight—and test it on genuinely isolated forward data or a walk-forward holdout. Pair it with point-in-time UK retail/broker eligibility and observed implementation-spread reconstruction. A separately registered test may examine short RS as entry/failure timing without changing the selection rule.

## G. Is more research worth the compute and time?

**Yes, but only narrowly.** The contemporary magnitude and coherent regime pattern justify a controlled confirmation/implementation-reconstruction stage. The lack of FDR survival, wide interval, top-winner dependence, and unresolved historical eligibility make further broad optimisation low-value and deployment premature.
"""
    write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2_RESEARCH_DIRECTOR_REVIEW.md", director)

    # Update child manifests with their now-known result commits. A final
    # provenance commit will contain these manifest updates.
    for name, field, commit in [
        ("UKACTIVE_A3R2_S_MANIFEST.json", "post_a3r2s_commit", "d41a7f6744c613484894d7dd4da5e1d66718fd21"),
        ("UKACTIVE_A3R2W_MANIFEST.json", "post_a3r2w_commit", "0898f509be951e9b792345aa1bcf7289e2133bac"),
    ]:
        path = PROGRAMME_ROOT / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload[field] = commit
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    tracked_outputs = []
    for path in sorted(PROGRAMME_ROOT.glob("UKACTIVE_A3R2*")):
        if path.is_file() and path.name != "UKACTIVE_A3R2_MANIFEST.json" and path.suffix.lower() in {".csv", ".json", ".md"}:
            tracked_outputs.append(audit_file(path))
    code_outputs = [audit_file(path) for path in sorted((PROGRAMME_ROOT / "code").glob("*ukactive*a3r2*.py"))]
    code_outputs.extend(audit_file(path) for path in [PROGRAMME_ROOT / "code" / "query_ukactive_rotation.py", PROGRAMME_ROOT / "code" / "refresh_ukactive_current_snapshot.py"])
    manifest = {
        "stage_id": "UKACTIVE-A3R2",
        "run_id": "UKACTIVE-A3R2-20260823-001",
        "created_at": utc_now(),
        "decision": OVERALL_DECISION,
        "repository_root": str(PLATFORM_ROOT),
        "branch": git_output("branch", "--show-current"),
        "origin": git_output("remote", "get-url", "origin"),
        "commits": {
            "preflight": "c30de89d0ceee74ea024708e7c95270bae38d150",
            "preregistration": "3ed64a2240a1fc7c6f6b573ef27e436e13d53671",
            "universe_refresh_result": "44911118125916ed66b48a8eea7bb03cadfe2153",
            "universe_refresh_provenance": "3275e83f10df9bbd0a2ad293099d768bcccced8d",
            "signal_count_cadence": "d41a7f6744c613484894d7dd4da5e1d66718fd21",
            "weighting": "0898f509be951e9b792345aa1bcf7289e2133bac",
            "query_and_final_results": "PENDING_NEXT_COMMIT",
            "final_provenance": "FOLLOWUP_COMMIT_CONTAINING_THIS_MANIFEST",
        },
        "preflight_tag": "ukactive-a3r2-preflight-20260823",
        "policy": audit_file(PROGRAMME_ROOT / "config" / "UKACTIVE_A3R2_POLICY_v1.json"),
        "project_edge_mandate": audit_file(PLATFORM_ROOT / "docs" / "PROJECT_EDGE_RESEARCH_MANDATE.md"),
        "child_decisions": {"A3R2U": u["decision"], "A3R2S": s["decision"], "A3R2W": w["decision"], "A3R2Q": "UKACTIVE_A3R2Q_PASS"},
        "tracked_outputs": tracked_outputs,
        "code_outputs": code_outputs,
        "large_local_input_or_output_inventory": [
            audit_file(PROGRAMME_ROOT / name)
            for name in ["UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet", "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet", "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet", "UKACTIVE_A3R2_FEATURE_PANEL.parquet", "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet"]
        ],
        "official_current_sources": [
            {"url": "https://www.ii.co.uk/our-charges", "retrieval_date": "2026-08-23", "purpose": "Target-platform charges and FX schedule"},
            {"url": "https://hanetf.com/closed-funds/", "retrieval_date": "2026-08-23", "purpose": "Primary issuer closure/merger lifecycle evidence"},
            {"url": "https://hanetf.com/fund/gijo-future-of-us-defence-etf/", "retrieval_date": "2026-08-23", "purpose": "US defence mandate-change evidence"},
            {"url": "https://www.ishares.com/uk/individual/en/literature/annual-report/ishares-vii-plc-en-annual-report-2025.pdf", "retrieval_date": "2026-08-23", "purpose": "Primary issuer cessation evidence"},
        ],
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "current_snapshot": {"as_of": regime["date"], "rows": 82, "current_leading_geographies": current_geo, "current_leading_industries": current_industry, "current_leading_themes": current_theme, "regime": regime},
        "active_family_counts_by_year": counts.to_dict(orient="records"),
        "unresolved_items": unresolved.to_dict(orient="records"),
        "large_or_licensed_data_committed": False,
        "automatic_next_stage_executed": False,
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3R2_MANIFEST.json", manifest)
    print(json.dumps(decision, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
