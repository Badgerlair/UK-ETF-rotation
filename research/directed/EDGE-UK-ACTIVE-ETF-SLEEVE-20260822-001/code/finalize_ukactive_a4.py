"""Finalize UKACTIVE-A4 governance, decision, and reproducibility artifacts."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow
import scipy

from ukactive_a3r2_core import PROGRAMME_ROOT, audit_file, git_output, sha256_file, utc_now, write_csv, write_json, write_text


RUN_ID = "UKACTIVE-A4-20260823-001"
DECISION = "UKACTIVE_A4_REGIME_CONDITIONAL_ONLY"
WARNING = "HISTORICAL UK RETAIL, ISA, ACCOUNT AND BROKER ELIGIBILITY REMAIN PARTLY UNRESOLVED"


def p(name: str) -> Path:
    return PROGRAMME_ROOT / name


def pct(value: float, digits: int = 2) -> str:
    return f"{100.0 * float(value):.{digits}f}%"


def pp(value: float, digits: int = 2) -> str:
    return f"{100.0 * float(value):+.{digits}f} pp"


def row(frame: pd.DataFrame, column: str, value: str) -> pd.Series:
    match = frame.loc[frame[column].eq(value)]
    if len(match) != 1:
        raise AssertionError(f"Expected one row for {column}={value}; found {len(match)}")
    return match.iloc[0]


def regime_row(frame: pd.DataFrame, dimension: str, state: str) -> pd.Series:
    match = frame.loc[frame["regime_dimension"].eq(dimension) & frame["regime_state"].eq(state)]
    if len(match) != 1:
        raise AssertionError(f"Expected one regime row for {dimension}/{state}")
    return match.iloc[0]


def episode_implementation_counts(history: pd.DataFrame) -> tuple[dict[str, int], dict[str, int]]:
    episodes = pd.read_csv(p("UKACTIVE_A4_HOLDING_EPISODES.csv"), parse_dates=["entry_signal_date"])
    primary = history.loc[history["model_id"].eq("A4_PRIMARY")].copy()
    primary["signal_date"] = pd.to_datetime(primary["signal_date"])
    merged = episodes.merge(
        primary,
        left_on=["entry_signal_date", "family"],
        right_on=["signal_date", "economic_exposure_family_id"],
        how="left",
        validate="one_to_one",
    )
    if merged["historical_uk_retail_status"].isna().any():
        raise AssertionError("Primary episode implementation evidence is incomplete")
    return (
        merged["historical_uk_retail_status"].value_counts().astype(int).to_dict(),
        merged["historical_isa_status"].value_counts().astype(int).to_dict(),
    )


def main() -> int:
    generated_at = utc_now()
    contribution = pd.read_csv(p("UKACTIVE_A4_RETURN_CONTRIBUTION_BY_FAMILY.csv"))
    comparison = pd.read_csv(p("UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv"))
    dependency = pd.read_csv(p("UKACTIVE_A4_RIGHT_TAIL_DEPENDENCY.csv"))
    tail = pd.read_csv(p("UKACTIVE_A4_RANK1_FUTURE_TAIL_PROBABILITY.csv"))
    capture = pd.read_csv(p("UKACTIVE_A4_TREND_CAPTURE_METRICS.csv"))
    skew = pd.read_csv(p("UKACTIVE_A4_RETURN_SKEW_ANALYSIS.csv"))
    full = pd.read_csv(p("UKACTIVE_A4_FULL_HISTORY_CONTEXT.csv"))
    years = pd.read_csv(p("UKACTIVE_A4_YEAR_BY_YEAR_RESULTS.csv"))
    rolling12 = pd.read_csv(p("UKACTIVE_A4_ROLLING_12M_RESULTS.csv"))
    rolling24 = pd.read_csv(p("UKACTIVE_A4_ROLLING_24M_RESULTS.csv"))
    leave_one = pd.read_csv(p("UKACTIVE_A4_LEAVE_ONE_YEAR_OUT.csv"))
    regimes = pd.read_csv(p("UKACTIVE_A4_REGIME_FORENSICS.csv"))
    transitions = pd.read_csv(p("UKACTIVE_A4_SHORT_HORIZON_TRANSITION_DIAGNOSTICS.csv"))
    weakening = pd.read_csv(p("UKACTIVE_A4_LEADING_WEAKENING_FORENSICS.csv"))
    costs = pd.read_csv(p("UKACTIVE_A4_COST_STRESS_RESULTS.csv"))
    implementation = pd.read_csv(p("UKACTIVE_A4_CURRENT_II_IMPLEMENTATION.csv"), dtype=str)
    history = pd.read_csv(p("UKACTIVE_A4_SELECTED_INSTRUMENT_HISTORY.csv"), dtype=str)
    interim = json.loads(p("UKACTIVE_A4_FORENSIC_INTERIM_DECISION.json").read_text(encoding="utf-8"))
    a5 = json.loads(p("config/ukactive_a5_frozen_candidate.json").read_text(encoding="utf-8"))

    top1 = row(comparison, "candidate_id", "A4_TOP1")
    top2 = row(comparison, "candidate_id", "A4_TOP2")
    top3 = row(comparison, "candidate_id", "A4_TOP3")
    latest5 = row(full, "window_id", "LATEST_5Y")
    latest3 = row(full, "window_id", "LATEST_3Y")
    pre2020 = row(full, "window_id", "PRE_2020")
    post2020 = row(full, "window_id", "POST_2020")
    fullhist = row(full, "window_id", "FULL_HISTORY")
    tail_summary = row(tail, "record_type", "SUMMARY")
    skew_episodes = row(skew, "distribution", "SELECTED_HOLDING_EPISODES")
    high_dispersion = regime_row(regimes, "dispersion_regime", "HIGH")
    medium_breadth = regime_row(regimes, "breadth_regime", "MEDIUM")
    high_rotation = regime_row(regimes, "rotation_intensity_regime", "HIGH")
    tech_dom = regime_row(regimes, "us_technology_dominance", "DOMINANT")
    tech_not_dom = regime_row(regimes, "us_technology_dominance", "NOT_DOMINANT")
    top_families = contribution.head(5).copy()
    retail_counts, isa_counts = episode_implementation_counts(history)

    current_pool = implementation.loc[implementation["current_pool_member"].str.lower().eq("true")]
    current_signal = implementation.loc[implementation["current_signal_eligible"].str.lower().eq("true")]
    ii_pool = current_pool["ii_current_tradable"].eq("CONFIRMED_BY_USER")
    ii_signal = current_signal["ii_current_tradable"].eq("CONFIRMED_BY_USER")
    unresolved_signal = current_signal["current_implementation_state"].eq("CURRENT_IMPLEMENTATION_UNRESOLVED")
    public_signal = current_signal["current_implementation_state"].eq("CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED")

    short_corr = transitions[["short_1_2_3_composite", "selected_minus_unselected_next_interval"]].corr(method="spearman").iloc[0, 1]
    rs21_corr = transitions[["RS21", "selected_minus_unselected_next_interval"]].corr(method="spearman").iloc[0, 1]
    last_before_exit = weakening.loc[weakening["review_periods_before_replacement"].eq(1)]
    weakening_fraction = float(last_before_exit["rotation_state"].eq("WEAKENING").mean())

    year_lines = []
    for item in years.itertuples(index=False):
        label = f"{int(item.calendar_year)}{' partial' if str(item.partial_year) == 'YES' else ''}"
        year_lines.append(
            f"- {label}: net {pct(item.selected_net_cagr)}, excess vs pool {pp(item.selected_net_excess_vs_pool_cagr)}, excess vs global {pp(item.selected_net_excess_vs_global_cagr)}."
        )
    winner_capture_lines = []
    for family in interim["top_three_actual_contributors"]:
        values = capture.loc[capture["family"].eq(family)]
        ratios = ", ".join(f"{item.episode_id} {pct(item.capture_ratio)} ({item.entry_timing_classification})" for item in values.itertuples(index=False))
        winner_capture_lines.append(f"- {family}: {ratios}.")

    top1_remove_actual = dependency.loc[
        dependency["candidate_id"].eq("A4_TOP1")
        & dependency["dependency_test"].eq("REMOVE_THREE_LARGEST_ACTUAL_PNL_CONTRIBUTORS")
    ].iloc[0]
    cost40 = costs.loc[costs["one_way_friction_bps"].eq(40.0) & costs["sleeve_size_gbp"].eq(250000.0)].iloc[0]

    research_director = f"""# UKACTIVE-A4 research director review

Generated: {generated_at}  
Decision: **{DECISION}**  
Evidence level: **E2 developmental; no E3 evidence exists**

## A. Empirical summary

The frozen A4_PRIMARY contract was not changed. Over the contemporary five-year window it delivered {pct(top1.selected_net_cagr)} net CAGR versus {pct(top1.equal_pool_cagr)} for the contemporaneous equal-weight pool and {pct(top1.global_benchmark_cagr)} for global developed equities. Net excess was {pp(top1.selected_net_excess_vs_pool_cagr)} versus the pool and {pp(top1.selected_net_excess_vs_global_cagr)} versus global; selected-versus-unselected spread was {pp(top1.selected_vs_unselected_cagr_spread)}. Maximum drawdown was {pct(top1.selected_net_maximum_drawdown)}, zero-cash-hurdle Sharpe {top1.selected_net_sharpe_zero_cash_hurdle:.2f}, annual traded-notional turnover {top1.selected_net_annual_turnover_traded_notional:.2f}x and trade legs {int(top1.selected_net_trade_legs)}.

The result is highly right-tailed. {top_families.iloc[0]['family']} contributed {pct(top_families.iloc[0]['share_of_total_net_portfolio_gain'])} of net wealth gain. The top three contributed {pct(top_families.head(3)['share_of_total_net_portfolio_gain'].sum())}; the top five {pct(top_families.head(5)['share_of_total_net_portfolio_gain'].sum())}. Values above 100% occur because losing families offset part of the gain. Removing the actual top three contributors changes net excess versus the pool to {pp(top1_remove_actual.net_excess_vs_pool_cagr)} and drawdown to {pct(top1_remove_actual.maximum_drawdown)}.

Rank 1 nevertheless shows repeated cross-sectional information across 59 evaluable decisions: future top-decile probability {pct(tail_summary.probability_rank1_future_top_decile)}, top-quintile {pct(tail_summary.probability_rank1_future_top_quintile)}, pool-median beat rate {pct(tail_summary.probability_rank1_beats_pool_median)}, global beat rate {pct(tail_summary.probability_rank1_beats_global)}, and equal-pool beat rate {pct(tail_summary.probability_rank1_beats_equal_weight_family_pool)}. Holding-episode returns have skewness {skew_episodes.skewness:.2f}; the best episode supplied {pct(skew_episodes.best_1_share_of_arithmetic_return_sum)} of the arithmetic episode-return sum.

## B. Benchmarks and conventional-method context

A4 compares the candidate with global developed equities, the contemporaneously eligible equal-weight industry/theme pool, the unselected pool, TOP_2/TOP_3 concentration controls, two frozen structural neighbours, 10,000 random-selection paths and 10,000 within-date rank permutations. These are stronger controls than a single passive benchmark because they separate industry/theme beta from selection information.

The economic mechanism is consistent with the established cross-sectional and industry-momentum literature, including Jegadeesh–Titman (1993) and Moskowitz–Grinblatt (1999), but A4 is not a replication and those papers cannot confirm this UK ETF implementation. The literature also documents momentum crashes and weak findings under alternative inference, so positive skew and regime dependence are treated as risks rather than proof.

References: https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x ; https://onlinelibrary.wiley.com/doi/full/10.1111/0022-1082.00146 ; https://www.sciencedirect.com/journal/journal-of-financial-economics/vol/122/issue/2 ; https://doi.org/10.1016%2Fj.jfineco.2019.08.004

## C. Economic and causal explanations

The leading explanation is gradual capital migration across industries/themes: a 3/6/12 rank can identify an exposure after leadership becomes persistent but before a large trend is exhausted. The three major contributors were generally entered mid-trend, not at inception. Their episode capture diagnostics are:

{chr(10).join(winner_capture_lines)}

Competing explanations remain credible: the richer post-2020 ETF opportunity set, launch-cohort effects, survivor incompleteness, and ordinary sample luck. Pre-2020 net excess versus the pool was {pp(pre2020.selected_net_excess_vs_pool_cagr)}, while post-2020 it was {pp(post2020.selected_net_excess_vs_pool_cagr)}. This is too large a structural break to call unconditional alpha.

## D. Falsification and robustness

The candidate sits at the {pct(interim['placebo_summary']['candidate_excess_vs_pool_percentile'])} percentile of valid random-selection paths and the {pct(interim['permutation_summary']['candidate_excess_vs_pool_percentile'])} percentile of valid within-date rank permutations. Those percentiles are conditional on fully valid paths: only {interim['placebo_summary']['valid_random_paths']}/10,000 placebo and {interim['permutation_summary']['valid_random_paths']}/10,000 permutation paths remained valid under the frozen endpoint rules. Invalid paths were never filled.

The date-level selected-minus-unselected mean is {pct(interim['selected_vs_unselected_inference']['mean'])} per monthly interval (Newey-West t={interim['selected_vs_unselected_inference']['t_stat']:.2f}, p={interim['selected_vs_unselected_inference']['p_value']:.3f}); the block-bootstrap 95% interval is [{pct(interim['selected_vs_unselected_inference']['ci_low'])}, {pct(interim['selected_vs_unselected_inference']['ci_high'])}], crossing zero. No multiple-testing-adjusted broad edge was established in A3R2.

TOP_2 retains {pct(top2.selected_net_excess_vs_pool_cagr / top1.selected_net_excess_vs_pool_cagr)} of TOP_1 excess but improves drawdown by only {pp(abs(top1.selected_net_maximum_drawdown) - abs(top2.selected_net_maximum_drawdown))}. TOP_3 retains {pct(top3.selected_net_excess_vs_pool_cagr / top1.selected_net_excess_vs_pool_cagr)} and improves drawdown by {pp(abs(top1.selected_net_maximum_drawdown) - abs(top3.selected_net_maximum_drawdown))}. Neither resolves top-three-family dependence.

## E. Friction and executability

At the frozen 20 bp/£250k convention, net CAGR is {pct(top1.selected_net_cagr)}. At 40 bp/£250k it remains {pct(cost40.net_cagr)}, {pp(cost40.net_excess_vs_equal_pool_cagr)} above the pool. This is a modelled friction sensitivity, not realised historical spread evidence. NEXT_OPEN is unreported because no validated open-price execution route exists.

Historical implementation identities are exact and return-valid. Across 21 primary holding episodes, retail evidence is {json.dumps(retail_counts, sort_keys=True)} and ISA evidence is {json.dumps(isa_counts, sort_keys=True)}; historical platform evidence is zero verified. Current ii confirmation covers {int(ii_pool.sum())}/27 pool families and {int(ii_signal.sum())}/25 currently signal-eligible families. This blocks deployment.

## F. Evidence classification

- E1: causal/regime interpretation and short-horizon transition diagnostics.
- E2: all frozen historical returns, concentration tests, falsification, costs, and implementation reconstruction.
- E3: none. Historical rolling, leave-one-year-out and walk-forward-style diagnostics are not independent confirmation.

## G. Recommended next experiment

Proceed only to **UKACTIVE-A5 — prospective shadow forward test**, not deployment. The v1 model, universe policy, calculation, month-end review, TOP_1 rule, timing, benchmark, costs and post-rank implementation check are frozen in `config/ukactive_a5_frozen_candidate.json`. The first possible signal is 2026-08-28, after the model tag; nothing is backfilled. Primary review requires 24 completed monthly decisions. Unconfirmed ii implementation is logged as non-executable and never causes rank substitution. Any rule change terminates the v1 confirmation lineage.
"""

    evidence_classification = f"""# UKACTIVE-A4 evidence classification

Decision: **{DECISION}**

| Evidence | A4 content | Permitted interpretation |
|---|---|---|
| E1 — exploratory | High-dispersion/high-rotation mechanism, short-horizon transition fields, LEADING→WEAKENING interpretation | Hypothesis-generation only. |
| E2 — developmental | Frozen A4_PRIMARY history; TOP_1/2/3; right-tail decomposition; random/permutation falsification; cost and implementation reconstruction | A regime-conditional research candidate with material concentration and eligibility risk. |
| E3 — confirmatory | None | No confirmed edge, historically verified UK-investable strategy, or deployment candidate may be claimed. |

The five-year result, rolling windows, pre/post-2020 comparison and leave-one-year-out results all use data previously observed by the programme. They remain E2 even though the A4 candidate was frozen before this stage. The approximately 96th-percentile placebo/permutation position is a useful falsification result, not proof of alpha, particularly because the confidence interval crosses zero and complete-path validity is only about 55%.

The only authorised route toward E3 is the tagged A5 prospective shadow lineage. It begins after the freeze and prohibits backfill, performance-based early stopping and rule changes.
"""

    data_quality = f"""# UKACTIVE-A4 data-quality report

Generated: {generated_at}

## Result

No new price, return, calendar, lineage, stale-data or lookahead defect was found. A4 consumes the A2R2 corrected XLON endpoint/wealth chain; no price or return was forward-filled. Contribution reconciliation difference is exactly {interim['contribution_reconciliation_difference']:.1f}. The frozen primary contract and regime-history hash passed.

## Controls

- Date-T close never earns date-T return; executable decisions use the next valid XLON session.
- Dynamic point-in-time membership and one-row-per-economic-family ranking remain intact.
- TOP_2/TOP_3 use the same frozen rank sequence.
- Random/permutation paths retain contemporaneous membership; invalid endpoints invalidate a path rather than manufacture a return.
- Exact episode-time listing/share-class IDs are reconstructed from A2R2 endpoint history. FCBR is retained for the 2021 cybersecurity episode rather than current CYSE.
- Current ii observations remain dated 2026-08-23 and never become historical evidence.
- The A5 runner rejects dates at or before 2026-08-21 and contains no broker/order/scheduler route.

## Remaining limitations

- The recent five-year lifecycle census is `RECENT_FIVE_YEAR_CENSUS_SUBSTANTIALLY_COMPLETE`, not complete.
- {interim['placebo_summary']['invalid_random_paths']} placebo and {interim['permutation_summary']['invalid_random_paths']} permutation paths were invalid under strict endpoint continuity. Percentiles are conditional on valid paths.
- Historical retail documentation is verified for only {retail_counts.get('HISTORICALLY_VERIFIED_UK_RETAIL', 0)} of 21 episodes; the rest are probable. Historical ISA evidence is probable, not verified, for all 21.
- Historical broker/platform availability is unverified.
- Only {int(ii_pool.sum())}/27 pool families have current user-confirmed ii status; {int(unresolved_signal.sum())} of 25 currently signal-eligible families have incomplete public/ii implementation evidence and {int(public_signal.sum())} more remain ii-unchecked.
- NEXT_OPEN and realised historical spreads are unavailable; only the validated endpoint convention and explicit cost sensitivities are reported.
"""

    unresolved = pd.DataFrame(
        [
            ["A4-U001", "RIGHT_TAIL", "Actual top-three contributors account for 90.45% of net gain; removing them makes excess negative.", "HIGH", "NO", "NO", "YES", "A5_PROSPECTIVE", "OPEN"],
            ["A4-U002", "REGIME", "Pre-2020 excess is negative while post-2020 excess is strongly positive.", "HIGH", "NO", "NO", "YES", "A5_PROSPECTIVE", "OPEN"],
            ["A4-U003", "STATISTICS", "HAC p is 0.052 and block-bootstrap interval crosses zero; no broad FDR edge.", "HIGH", "NO", "NO", "YES", "A5_PROSPECTIVE", "OPEN"],
            ["A4-U004", "FALSIFICATION", "About 45% of random/permuted paths are invalid under strict endpoint continuity; percentiles are conditional.", "MEDIUM", "NO", "NO", "NO", "FUTURE_DATA_REFRESH", "OPEN"],
            ["A4-U005", "HISTORICAL_RETAIL", "20/21 primary episodes are retail-probable, not verified.", "MEDIUM", "NO", "NO", "YES", "ARCHIVE_EVIDENCE_PASS", "OPEN"],
            ["A4-U006", "HISTORICAL_ISA", "0/21 primary episodes have product/account-specific verified historical ISA evidence.", "HIGH", "NO", "NO", "YES", "ARCHIVE_EVIDENCE_PASS", "OPEN"],
            ["A4-U007", "HISTORICAL_BROKER", "Historical broker/platform availability is unverified for every episode.", "HIGH", "NO", "NO", "YES", "BROKER_ARCHIVE_OR_DEPLOYMENT", "OPEN"],
            ["A4-U008", "CURRENT_II", "Only 2/27 pool families are current user-confirmed on ii; only 1/25 current signal-eligible families is confirmed.", "HIGH", "NO", "NO", "YES", "CURRENT_BROKER_VERIFICATION", "OPEN"],
            ["A4-U009", "EXECUTION", "No validated NEXT_OPEN route or realised historical spread series exists.", "MEDIUM", "NO", "NO", "YES", "EXECUTION_DATA_STAGE", "OPEN"],
            ["A4-U010", "SURVIVORSHIP", "Recent five-year lifecycle census is substantially complete rather than complete.", "MEDIUM", "NO", "NO", "YES", "POINT_IN_TIME_CENSUS", "OPEN"],
            ["A4-U011", "CONFIRMATION", "No prospective E3 observations exist yet.", "HIGH", "NO", "NO", "YES", "A5_PROSPECTIVE", "OPEN"],
        ],
        columns=["item_id", "category", "description", "severity", "blocks_a4_decision", "blocks_a5_shadow", "blocks_deployment", "resolution_stage", "status"],
    )

    original_tests = pd.read_csv(p("UKACTIVE_A4_CORRECTNESS_TEST_RESULTS.csv"))
    implementation_tests = pd.read_csv(p("UKACTIVE_A4_IMPLEMENTATION_CORRECTNESS_TEST_RESULTS.csv"))
    extra_tests = []

    def add(test_id: str, test: str, passed: bool, detail: str) -> None:
        extra_tests.append({"test_id": test_id, "test": test, "status": "PASS" if passed else "FAIL", "detail": detail})

    add("A4-F01", "Final decision uses an allowed state", DECISION in {
        "UKACTIVE_A4_CANDIDATE_SURVIVES", "UKACTIVE_A4_CANDIDATE_SURVIVES_WITH_CONCENTRATION_RISK",
        "UKACTIVE_A4_REGIME_CONDITIONAL_ONLY", "UKACTIVE_A4_CANDIDATE_REJECTED", "UKACTIVE_A4_FAIL_DATA_OR_METHOD",
    }, DECISION)
    add("A4-F02", "All historical evidence remains E2 or E1", interim["evidence_level"].startswith("E2"), interim["evidence_level"])
    add("A4-F03", "A5 prospective date is after historical cutoff", pd.Timestamp(a5["prospective_signal_not_before"]) > pd.Timestamp(a5["historical_development_cutoff"]), f"{a5['prospective_signal_not_before']} > {a5['historical_development_cutoff']}")
    add("A4-F04", "A5 primary candidate exactly matches A4_PRIMARY", a5["candidate"]["economic_pool"] == "INDUSTRY_PLUS_THEME" and a5["candidate"]["signal"] == "MH_LEVEL_3_6_12_REFERENCE" and a5["candidate"]["selection"] == "TOP_1" and a5["candidate"]["review_cadence"] == "MONTHLY_FINAL_VALID_XLON_SESSION", "frozen pool/signal/count/cadence")
    add("A4-F05", "A5 has no order or scheduler authority", not a5["implementation"]["orders_permitted"] and not a5["implementation"]["scheduler_permitted"], "both false")
    add("A4-F06", "A5 requires 24 decisions and forbids performance early stopping", a5["evaluation"]["minimum_completed_monthly_decisions_for_primary_review"] == 24 and a5["evaluation"]["early_performance_stop"] == "PROHIBITED", "24 decisions; no performance stop")
    add("A4-F07", "Query-engine validation remains passed", pd.read_csv(p("UKACTIVE_A3R2Q_VALIDATION_RESULTS.csv"))["status"].eq("PASS").all(), "A3R2Q validation file")
    latest_ledger = pd.read_csv(p("UKACTIVE_A4_MONTHLY_DECISION_LEDGER.csv")).iloc[-1]
    latest_feature = pd.read_parquet(p("UKACTIVE_A3R2_FEATURE_PANEL.parquet"))
    latest_feature = latest_feature.loc[
        latest_feature["cadence"].eq("MONTHLY")
        & latest_feature["analysis_context_id"].eq("INDUSTRY_PLUS_THEME")
        & latest_feature["date"].eq(pd.Timestamp(latest_ledger["signal_date"]))
        & latest_feature["MH_LEVEL_3_6_12_REFERENCE"].notna()
    ].sort_values(["MH_LEVEL_3_6_12_REFERENCE", "economic_exposure_family_id"], ascending=[False, True])
    add("A4-F08", "Queryable frozen 3/6/12 latest rank reproduces A4 ledger", not latest_feature.empty and latest_feature.iloc[0]["economic_exposure_family_id"] == latest_ledger["rank_1_family"], f"feature={latest_feature.iloc[0]['economic_exposure_family_id']}; ledger={latest_ledger['rank_1_family']}")
    runner_text = p("code/run_ukactive_a5_shadow.py").read_text(encoding="utf-8")
    add("A4-F09", "A5 runner has no broker/order API", all(token not in runner_text for token in ["ib_insync", "placeOrder", "reqContractDetails", "submit_order"]), "no broker API tokens")
    add("A4-F10", "Current ii confirmation remains current-only", implementation.loc[implementation["ii_current_tradable"].eq("CONFIRMED_BY_USER"), "historical_back_projection"].eq("PROHIBITED").all(), "all confirmed rows prohibit back-projection")
    combined_tests = pd.concat([original_tests, implementation_tests, pd.DataFrame(extra_tests)], ignore_index=True)
    combined_tests = combined_tests.drop_duplicates("test_id", keep="last").sort_values("test_id").reset_index(drop=True)
    if not combined_tests["status"].eq("PASS").all():
        raise AssertionError("Final A4 correctness suite contains a failure")

    write_text(p("UKACTIVE_A4_RESEARCH_DIRECTOR_REVIEW.md"), research_director)
    write_text(p("UKACTIVE_A4_EVIDENCE_CLASSIFICATION.md"), evidence_classification)
    write_text(p("UKACTIVE_A4_DATA_QUALITY_REPORT.md"), data_quality)
    write_csv(p("UKACTIVE_A4_UNRESOLVED_ITEMS.csv"), unresolved)
    write_csv(p("UKACTIVE_A4_CORRECTNESS_TEST_RESULTS.csv"), combined_tests)

    decision = {
        "stage_id": "UKACTIVE-A4",
        "run_id": RUN_ID,
        "decision": DECISION,
        "decision_timestamp": generated_at,
        "frozen_primary_unchanged": True,
        "primary_candidate": "INDUSTRY_PLUS_THEME|MH_LEVEL_3_6_12_REFERENCE|TOP_1|MONTHLY|EQUAL",
        "evidence_level": "E2_DEVELOPMENTAL_WITH_E1_MECHANISM; NO_E3",
        "deployment_candidate": False,
        "right_tail_repeatability": "FEW_LARGE_BUT_PLAUSIBLE_WINNERS",
        "five_year": {
            "gross_cagr": float(top1.selected_gross_cagr), "net_cagr": float(top1.selected_net_cagr),
            "equal_pool_cagr": float(top1.equal_pool_cagr), "global_cagr": float(top1.global_benchmark_cagr),
            "net_excess_vs_pool": float(top1.selected_net_excess_vs_pool_cagr),
            "net_excess_vs_global": float(top1.selected_net_excess_vs_global_cagr),
            "selected_vs_unselected_spread": float(top1.selected_vs_unselected_cagr_spread),
            "maximum_drawdown": float(top1.selected_net_maximum_drawdown),
        },
        "top_contributors": contribution.head(5)[["family", "share_of_total_net_portfolio_gain", "share_of_total_excess_pnl_vs_equal_pool"]].to_dict(orient="records"),
        "rank1_future_tail": {
            "top_decile_probability": float(tail_summary.probability_rank1_future_top_decile),
            "top_quintile_probability": float(tail_summary.probability_rank1_future_top_quintile),
            "beats_pool_median_probability": float(tail_summary.probability_rank1_beats_pool_median),
        },
        "falsification": {"random_selection": interim["placebo_summary"], "rank_permutation": interim["permutation_summary"], "selected_vs_unselected_inference": interim["selected_vs_unselected_inference"]},
        "concentration_controls": interim["concentration_control_results"],
        "historical_retail_episode_counts": retail_counts,
        "historical_isa_episode_counts": isa_counts,
        "current_ii_confirmed_pool_families": int(ii_pool.sum()),
        "current_pool_families": int(len(current_pool)),
        "current_ii_confirmed_signal_eligible_families": int(ii_signal.sum()),
        "current_signal_eligible_families": int(len(current_signal)),
        "a5_prospective_shadow_justified": True,
        "a5_started": False,
        "a5_backfilled": False,
        "a5_specification": "config/ukactive_a5_frozen_candidate.json",
        "automatic_deployment_authorised": False,
        "automatic_next_stage_execution_authorised": False,
        "correctness_tests_passed": int(combined_tests["status"].eq("PASS").sum()),
        "correctness_tests_total": int(len(combined_tests)),
        "warning": WARNING,
    }
    write_json(p("UKACTIVE_A4_DECISION.json"), decision)

    required = [
        "UKACTIVE_A4_SCOPE_AND_FROZEN_SPECIFICATION.md", "UKACTIVE_A4_MONTHLY_DECISION_LEDGER.csv", "UKACTIVE_A4_MONTHLY_TOP5_RANKS.csv",
        "UKACTIVE_A4_HOLDING_EPISODES.csv", "UKACTIVE_A4_RETURN_CONTRIBUTION_BY_FAMILY.csv", "UKACTIVE_A4_RETURN_CONTRIBUTION_BY_EPISODE.csv",
        "UKACTIVE_A4_RETURN_CONTRIBUTION_BY_YEAR.csv", "UKACTIVE_A4_TOP3_WINNER_FORENSICS.md", "UKACTIVE_A4_MEDIAN_SELECTION_FORENSICS.md",
        "UKACTIVE_A4_LOSER_SELECTION_FORENSICS.md", "UKACTIVE_A4_TREND_CAPTURE_METRICS.csv", "UKACTIVE_A4_RIGHT_TAIL_REPEATABILITY.md",
        "UKACTIVE_A4_RANK1_FUTURE_TAIL_PROBABILITY.csv", "UKACTIVE_A4_RETURN_SKEW_ANALYSIS.csv", "UKACTIVE_A4_TOP1_TOP2_TOP3_COMPARISON.csv",
        "UKACTIVE_A4_CONCENTRATION_AND_DRAWDOWN.csv", "UKACTIVE_A4_RIGHT_TAIL_DEPENDENCY.csv", "UKACTIVE_A4_CONCENTRATION_DECISION.md",
        "UKACTIVE_A4_REGIME_FORENSICS.csv", "UKACTIVE_A4_REGIME_RIGHT_TAIL_INTERACTION.csv", "UKACTIVE_A4_YEAR_BY_YEAR_RESULTS.csv",
        "UKACTIVE_A4_ROLLING_12M_RESULTS.csv", "UKACTIVE_A4_ROLLING_24M_RESULTS.csv", "UKACTIVE_A4_LEAVE_ONE_YEAR_OUT.csv",
        "UKACTIVE_A4_FULL_HISTORY_CONTEXT.csv", "UKACTIVE_A4_SHORT_HORIZON_TRANSITION_DIAGNOSTICS.csv", "UKACTIVE_A4_LEADING_WEAKENING_FORENSICS.csv",
        "UKACTIVE_A4_RANDOM_SELECTION_PLACEBO.csv", "UKACTIVE_A4_RANK_PERMUTATION_TEST.csv", "UKACTIVE_A4_FALSIFICATION_REPORT.md",
        "UKACTIVE_A4_SELECTED_INSTRUMENT_HISTORY.csv", "UKACTIVE_A4_HISTORICAL_UK_RETAIL_EVIDENCE.csv", "UKACTIVE_A4_HISTORICAL_ISA_EVIDENCE.csv",
        "UKACTIVE_A4_CURRENT_II_IMPLEMENTATION.csv", "UKACTIVE_A4_CURRENT_IMPLEMENTABILITY_GAPS.csv", "UKACTIVE_A4_EXECUTION_MODEL_RESULTS.csv",
        "UKACTIVE_A4_COST_STRESS_RESULTS.csv", "UKACTIVE_A4_IMPLEMENTATION_RECONSTRUCTION_REPORT.md", "UKACTIVE_A5_PROSPECTIVE_FORWARD_TEST_SPEC.md",
        "config/ukactive_a5_frozen_candidate.json", "code/run_ukactive_a5_shadow.py", "UKACTIVE_A5_DECISION_LEDGER_SCHEMA.md",
        "UKACTIVE_A4_RESEARCH_DIRECTOR_REVIEW.md", "UKACTIVE_A4_EVIDENCE_CLASSIFICATION.md", "UKACTIVE_A4_DATA_QUALITY_REPORT.md",
        "UKACTIVE_A4_UNRESOLVED_ITEMS.csv", "UKACTIVE_A4_DECISION.json", "UKACTIVE_A4_CORRECTNESS_TEST_RESULTS.csv",
    ]
    missing = [name for name in required if not p(name).exists()]
    if missing:
        raise AssertionError(f"Required A4 outputs missing: {missing}")
    manifest = {
        "stage_id": "UKACTIVE-A4",
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "decision": DECISION,
        "git": {
            "branch": git_output("branch", "--show-current"),
            "preflight_commit": "6397c22e30d4fbe420ea3646348a3e4ac39c7e10",
            "freeze_commit": "f8c8b5e5c0e93396b83216b6e8bef11c94fd47a6",
            "right_tail_commit": "94b4b20",
            "implementation_commit": "5587d08",
            "final_result_commit": "PENDING_FINAL_COMMIT",
            "final_provenance_commit": "PENDING_FINAL_PROVENANCE_COMMIT",
            "a5_freeze_tag": a5["model_freeze_git_tag"],
            "remote": git_output("remote", "get-url", "origin"),
            "push_status": "PENDING_FINAL_PUSH",
        },
        "authoritative_inputs": [audit_file(p(name)) for name in [
            "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet", "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
            "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet", "UKACTIVE_A3R2_FEATURE_PANEL.parquet",
            "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet", "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv",
            "config/UKACTIVE_A4_POLICY_v1.json", "config/UKACTIVE_A4_IMPLEMENTATION_EVIDENCE_v1.json",
        ]],
        "source_code": [audit_file(p(name)) for name in [
            "code/build_ukactive_a4_forensics.py", "code/build_ukactive_a4_implementation.py", "code/finalize_ukactive_a4.py", "code/run_ukactive_a5_shadow.py",
        ]],
        "outputs": [audit_file(p(name)) for name in required],
        "large_local_data_policy": "Large Parquet panels remain excluded from Git and are represented by exact path, SHA-256 and size.",
        "source_urls": sorted(set(
            [
                "https://www.ii.co.uk/our-charges", "https://www.gov.uk/guidance/stocks-and-shares-investments-for-isa-managers",
                "https://www.gov.uk/guidance/recognised-stock-exchanges",
                "https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1993.tb04702.x",
                "https://onlinelibrary.wiley.com/doi/full/10.1111/0022-1082.00146",
                "https://www.sciencedirect.com/journal/journal-of-financial-economics/vol/122/issue/2",
                "https://doi.org/10.1016%2Fj.jfineco.2019.08.004",
            ]
            + [url for item in json.loads(p("config/UKACTIVE_A4_IMPLEMENTATION_EVIDENCE_v1.json").read_text(encoding="utf-8"))["exact_historical_isin_evidence"].values() for url in item["source_urls"]]
        )),
        "source_retrieval_date": "2026-08-23",
        "policies": {
            "primary": "INDUSTRY_PLUS_THEME|MH_LEVEL_3_6_12_REFERENCE|TOP_1|MONTHLY|EQUAL",
            "evidence": "LOW_FRICTION_TO_EXPLORE_HIGH_FRICTION_TO_CLAIM",
            "historical_level": "E2_NOT_E3",
            "execution": "A2R2_NEXT_ELIGIBLE_SESSION_ENDPOINT",
            "random_seeds": {"placebo": 20260823, "rank_permutation": 20260824},
            "simulations_each": 10000,
        },
        "reproducibility_commands": [
            "python code/build_ukactive_a4_forensics.py",
            "python code/build_ukactive_a4_implementation.py",
            "python code/finalize_ukactive_a4.py",
        ],
        "package_versions": {
            "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "scipy": scipy.__version__, "pyarrow": pyarrow.__version__,
        },
        "correctness_tests": combined_tests.to_dict(orient="records"),
        "unresolved_items": unresolved.to_dict(orient="records"),
        "reproducibility_status": "PENDING_FINAL_COMMIT_PROVENANCE_UPDATE",
        "a5": {"specified": True, "started": False, "backfilled": False, "minimum_decisions": 24},
        "warning": WARNING,
    }
    write_json(p("UKACTIVE_A4_MANIFEST.json"), manifest)

    print(json.dumps({
        "decision": DECISION,
        "tests": combined_tests["status"].value_counts().to_dict(),
        "five_year_net_cagr": float(top1.selected_net_cagr),
        "top_three_gain_share": float(top_families.head(3)["share_of_total_net_portfolio_gain"].sum()),
        "random_percentile": float(interim["placebo_summary"]["candidate_excess_vs_pool_percentile"]),
        "permutation_percentile": float(interim["permutation_summary"]["candidate_excess_vs_pool_percentile"]),
        "a5_justified": True,
        "a5_started": False,
        "current_ii_confirmed_pool": int(ii_pool.sum()),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
