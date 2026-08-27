#!/usr/bin/env python3
"""Generate deterministic UKACTIVE scientific-paper tables and figures.

The script is deliberately downstream of the immutable A1--A5C lineage.  It
does not alter a canonical artefact, change a model parameter, or extend the
historical sample.  New calculations are restricted to deterministic
reformatting, exact reproduction, and explanatory diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT = Path(__file__).resolve()
PAPER_ROOT = SCRIPT.parents[1]
RESEARCH_ROOT = PAPER_ROOT.parent
REPO_ROOT = RESEARCH_ROOT.parents[2]
TABLES = PAPER_ROOT / "tables"
FIGURES = PAPER_ROOT / "figures"
QA = PAPER_ROOT / "qa"

CUTOFF = pd.Timestamp("2026-08-21")
COMMON_START = pd.Timestamp("2017-03-01")
LATEST5_START = pd.Timestamp("2021-09-01")
GENERATION_DATE = "2026-08-27"
PAPER_VERSION = "1.0.0"

FREEZE_COMMIT = "a8008f7709af3000a889bb234a86f8c520c4ed73"
RESULTS_COMMIT = "beb8d49828b9819aa167d2e07ffdc2b92581b36b"
MANIFEST_COMMIT = "df30c9be430c4a746a6e3ec0d97690612badd4fa"

BLUE = "#1f4e79"
TEAL = "#2b7a78"
ORANGE = "#d97706"
RED = "#b91c1c"
GREEN = "#3f7d20"
GREY = "#667085"
LIGHT = "#e9eef4"

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#374151",
        "axes.labelcolor": "#1f2937",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.labelsize": 10,
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "grid.color": "#d1d5db",
        "grid.alpha": 0.55,
        "legend.frameon": False,
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
        "savefig.dpi": 220,
    }
)


def canonical(relative: str) -> Path:
    return RESEARCH_ROOT / relative


def read_csv(relative: str) -> pd.DataFrame:
    return pd.read_csv(canonical(relative), low_memory=False)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def source_commit(relative: str) -> str:
    path = canonical(relative)
    rel = path.relative_to(REPO_ROOT).as_posix()
    commit = git("log", "-1", "--format=%H", "--", rel)
    if commit:
        return commit
    # Large canonical parquets are intentionally git-excluded; cite the final
    # immutable stage manifest commit that hashes and governs them.
    fallbacks = [
        ("UKACTIVE_A0A1_", "2c26ad3639e4e025477d9415f4f7b707e9856b55"),
        ("UKACTIVE_A2R2_", "88c0ba161a3bb2556187948b556737403c04ccf1"),
        ("UKACTIVE_A2R_", "2c26ad3639e4e025477d9415f4f7b707e9856b55"),
        ("UKACTIVE_A2_", "2c26ad3639e4e025477d9415f4f7b707e9856b55"),
        ("UKACTIVE_A3R1R1_", "c30de89d0ceee74ea024708e7c95270bae38d150"),
        ("UKACTIVE_A3R1_", "fc5d2b1e31d6a335f20c5d68bea7787a0911e982"),
        ("UKACTIVE_A3R2U_", "3275e83f10df9bbd0a2ad293099d768bcccced8d"),
        ("UKACTIVE_A3R2W_", "32e6388a02689fd932b348aa20695f93c6199d5e"),
        ("UKACTIVE_A3R2_", "957b164ea7d24dd2ff46e8f9bf36b7643d75c464"),
        ("UKACTIVE_A3R0_", "2c26ad3639e4e025477d9415f4f7b707e9856b55"),
        ("UKACTIVE_A3_", "2c26ad3639e4e025477d9415f4f7b707e9856b55"),
        ("UKACTIVE_A4B_", "d18fef020bb0082ac199b7a202f90882e23b1bbd"),
        ("UKACTIVE_A4C_", "67d4ae055f37e2844c1ee0e780a3ee3ba68e524d"),
        ("UKACTIVE_A4D_", "48cb69ffbaae25eb0dccc3226f47f5a7491e8bd7"),
        ("UKACTIVE_A4_", "93b45ba474c0bfd7df9c7e5ce083df1ce0e74c29"),
        ("UKACTIVE-A4E-SIPP/", "ce6136f52ca646698a56e4ff4bbb8577214a684d"),
        ("UKACTIVE-A4F-SIPP-REGIME/", "6dba072dce65da56284a8c02f9f380301048d492"),
        ("UKACTIVE-A5C-SIPP/", MANIFEST_COMMIT),
    ]
    for prefix, fallback in fallbacks:
        if relative.startswith(prefix):
            return fallback
    return "UNTRACKED_CANONICAL_SOURCE_COMMIT_NOT_RESOLVED"


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.12g")


def save_figure(fig: plt.Figure, filename: str) -> Path:
    path = FIGURES / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, metadata={"Software": "UKACTIVE deterministic paper build"})
    plt.close(fig)
    return path


def pct(value: Any) -> float:
    return float(value) * 100.0


def clean_label(value: str) -> str:
    replacements = {
        "GLOBAL_": "",
        "M2_TOP7_CASH0_": "M2 ",
        "_": " ",
        "CASH 0 ALWAYS INVESTED": "CASH0",
    }
    result = str(value)
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result.title().replace("M2 100", "100% M2")


def portfolio_metrics(value: pd.Series) -> dict[str, float]:
    """Explanatory path metrics from an already canonical wealth series."""

    value = value.dropna().astype(float)
    value = value / value.iloc[0]
    daily = value.pct_change(fill_method=None).dropna()
    years = max((value.index[-1] - value.index[0]).days / 365.2425, 1e-9)
    drawdown = value / value.cummax() - 1.0
    underwater_start: pd.Timestamp | None = None
    longest = 0
    for date, dd in drawdown.items():
        if dd < -1e-12 and underwater_start is None:
            underwater_start = pd.Timestamp(date)
        if dd >= -1e-12 and underwater_start is not None:
            longest = max(longest, (pd.Timestamp(date) - underwater_start).days)
            underwater_start = None
    if underwater_start is not None:
        longest = max(longest, (pd.Timestamp(value.index[-1]) - underwater_start).days)
    return {
        "net_cagr": float(value.iloc[-1] ** (1.0 / years) - 1.0),
        "terminal_wealth_per_100k": float(value.iloc[-1] * 100000.0),
        "maximum_drawdown": float(drawdown.min()),
        "ulcer_index": float(np.sqrt(np.mean(np.square(drawdown)))),
        "annualised_volatility": float(daily.std(ddof=1) * np.sqrt(252.0)),
        "longest_underwater_days": int(longest),
    }


@dataclass(frozen=True)
class Claim:
    claim_id: str
    paper_section: str
    claim_or_metric: str
    source_stage: str
    source_file: str
    source_table_or_field: str
    sample_start: str = ""
    sample_end: str = ""
    metric_definition: str = ""
    status: str = "RECONCILED"
    reconciliation_note: str = ""


def claim_frame(claims: Iterable[Claim]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in claims:
        row = item.__dict__.copy()
        row["source_commit"] = source_commit(item.source_file)
        rows.append(row)
    columns = [
        "claim_id",
        "paper_section",
        "claim_or_metric",
        "source_stage",
        "source_file",
        "source_table_or_field",
        "source_commit",
        "sample_start",
        "sample_end",
        "metric_definition",
        "status",
        "reconciliation_note",
    ]
    return pd.DataFrame(rows)[columns]


def build_lineage_table() -> pd.DataFrame:
    stages = [
        ("A0/A1", "Specify the research problem and construct the instrument/share-class/family hierarchy", "Audited universe, taxonomies, current-investability separation", "No strategy test", "DATA_FOUNDATION_ONLY", "Build causal total-return histories"),
        ("A2", "Construct GBP total-return, FX, cash, implementation and point-in-time panels", "Vendor routing, distributions, stale/missing controls", "Readiness and data-quality tests", "CONDITIONAL_READY", "Remediate identity and history defects"),
        ("A3R0", "Audit A3 competition pools against economic identity", "Detected 14 material family/history mismatches", "Semantic and automated lineage audit", "FAIL_BLOCKED", "Repair lineage before interpreting signals"),
        ("A2R", "Repair family identity and implementation histories", "13 of 14 blocking families remediated; no proxy for the remaining family", "27 automated and 17 semantic tests", "PASS_WITH_ONE_EXCLUSION", "Re-run readiness"),
        ("A3R1", "Re-run signal construction after A2R", "Exposed calendar/session defect", "Timing and endpoint checks", "FAIL_BLOCKED", "Reconstruct the XLON research calendar"),
        ("A2R2", "Repair false vendor sessions and endpoint logic", "Deterministic XLON calendar; three-session prior-only tolerance", "Synthetic, benchmark-validity and affected-family audits", "PASS", "Repeat signal discovery causally"),
        ("A3R1R1", "Repeat the preregistered signal tests on corrected data", "180 formal cells with HAC/bootstrap/FDR accounting", "Cross-sectional predictive tests", "NO_FDR_SURVIVOR", "Permit bounded portfolio exploration"),
        ("A3R2/U/S/W/Q", "Explore causal role pools, breadth, signal families and weighting controls", "Dynamic current census, role taxonomy and equal-weight result", "315 specifications plus controls", "EXPLORATORY_LEAD_ONLY", "Forensic TOP1 implementation test"),
        ("A4", "Test the initial concentrated monthly rotation candidate", "Executable portfolio, costs, randomisation and contribution attribution", "TOP1 3/6/12 momentum", "RIGHT_TAIL_DEPENDENT", "Test diversified breadth"),
        ("A4B/A4C", "Test lifecycle, exit, regime, early-entry and core/satellite hypotheses", "Failure-mode and drawdown decomposition", "Fast exits, locks, sizing, 50/50 architecture", "NO_EXIT_OR_REGIME_PROMOTION", "Construct parsimonious multi-horizon stage"),
        ("A4D", "Compare multi-horizon signal, breadth, frequency, cash and weighting", "M1/M2/M3; TOP3--10; daily/weekly/monthly; CASH0--4", "Staged economic and statistical gates", "SELECT_M2_TOP7_MONTHLY_CASH0_EQUAL", "Falsify defence and whole-SIPP claims"),
        ("A4E-SIPP", "Test SIPP implementation, matched exposure, cash timing and static controls", "Matched exposure/risk, live cost map, crisis limitations", "CASH1 and global/cash timing falsification", "STATIC_75_25_CONTROL_ONLY", "Test causal regime policies"),
        ("A4F-SIPP", "Test causal regime telemetry and dynamic allocation policies", "Four regimes, six policies, static frontier, influence tests", "HAC/bootstrap, cost/year/family/spell gates", "NO_DYNAMIC_POLICY_PASSED", "Choose limited static pilot wrapper"),
        ("A5C-SIPP", "Freeze the scientific model and specify prospective operations", "Immutable spec, cost restatement, ledger, runbook and blockers", "26/26 correctness checks; zero prospective events", "FROZEN_AWAITING_HOLDINGS_INPUT", "Observe prospectively; do not reopen development"),
    ]
    return pd.DataFrame(
        stages,
        columns=["stage", "objective", "principal_new_capability", "principal_test", "decision", "consequence"],
    )


def build_universe_funnel() -> pd.DataFrame:
    rows = [
        ("Raw LSE discovery lines", 4359, "Listings observed in the current discovery census; not a historical investable universe", "A0/A1"),
        ("Distinct raw ISINs", 2821, "Raw current identifiers before curation", "A0/A1"),
        ("Curated share classes", 296, "Canonical share-class records", "A0/A1"),
        ("Curated listings", 478, "Exchange lines linked to share classes", "A0/A1"),
        ("Economic-exposure families", 99, "Research units before role/pool restrictions", "A0/A1"),
        ("Usable historical families", 90, "At least one accepted causal history in A2", "A2"),
        ("A3-ready families", 86, "Met the then-current signal-readiness rule", "A2"),
        ("Frozen structural M2 families", 27, "Industry-and-theme economic families in A5C", "A5C"),
        ("Signal-ready at cutoff", 25, "Five-horizon score available at 2026-08-21", "A5C"),
        ("Warm-up/not signal-ready at cutoff", 2, "Structurally admitted but lacking complete formation history", "A5C"),
    ]
    return pd.DataFrame(rows, columns=["funnel_step", "count", "definition", "source_stage"])


def build_assumptions_table() -> pd.DataFrame:
    rows = [
        ("Economic family is the ranked unit", "Suppresses ticker/share-class duplication", "A0/A1 onward", "Taxonomy error can merge or split exposures", "AMBIGUOUS", "Documented master and duplicate groups", "Taxonomy remains judgemental"),
        ("Adjusted close accepted after validation", "Creates total-return-like wealth histories", "A2 onward", "Vendor adjustments or missed events can bias returns", "AMBIGUOUS", "Distribution/event and overlapping-source checks", "Not every event was independently reconstructed"),
        ("GBP/GBX unit conversion is explicit", "GBX quotes are one-hundredth of GBP", "A2 onward", "A unit mistake would be catastrophic", "UPWARD_OR_DOWNWARD", "Automated currency/unit tests", "Source metadata can still be wrong"),
        ("Foreign lines converted to GBP once", "Measures UK-investor wealth consistently", "A2 onward", "FX alignment error can bias relative returns", "AMBIGUOUS", "ECB pair validation and same-date conversion", "Unhedged economic currency exposure remains"),
        ("No forward filling across gaps", "Prevents invented tradability and returns", "A2R2 onward", "May reduce sample and exclude temporarily missing families", "PROBABLY_DOWNWARD_OR_NEUTRAL", "Invalid endpoints become missing; >3-session gaps reset", "Missingness may be non-random"),
        ("Historical endpoint may use nearest prior true XLON session within three sessions", "Accommodates genuine non-trading dates without look-ahead", "A2R2 onward", "Stale endpoints may soften measured moves", "AMBIGUOUS", "Never future; tolerance logged", "Different local-market holidays remain"),
        ("Current broker availability is current-only", "Avoids back-projecting 2026 account state", "A3R2U/A4/A5C", "Historical implementability may be overstated", "PROBABLY_UPWARD", "Historical eligibility kept separate and disclosed", "Complete past UK retail/SIPP availability is unresolved"),
        ("Unresolved/closed instrument receives no invented proxy", "Preserves economic identity", "A2R onward", "Reduces breadth/history", "PROBABLY_DOWNWARD_OR_NEUTRAL", "Exclude or allocate unavailable live slot to CSH2", "Closure timing and substitute quality remain uncertain"),
        ("Historical cash uses time-varying GBP overnight rates", "Avoids constant-yield hindsight", "A2 onward", "Proxy/basis differences can affect defence comparisons", "AMBIGUOUS", "SONIA series checked against compounded index", "RLON/CSH2 live tracking differs from proxy"),
        ("Execution at first following valid XLON session", "Enforces causal separation from signal close", "A4 onward", "Opening/market execution can differ from close-to-close proxy", "AMBIGUOUS", "No same-close; three-session window; cost stress", "Intraday implementation shortfall remains"),
        ("20 bps one-way market friction", "Conservative common execution assumption", "A4D onward", "May over- or understate realised spread/impact", "AMBIGUOUS", "Doubled-cost tests and live cost restatement", "No canonical structured spot-spread sample"),
        ("TER is not deducted a second time", "Adjusted market prices already reflect fund expenses", "A5C", "Double deduction would bias performance downward", "PROBABLY_DOWNWARD_IF_VIOLATED", "Frozen cost contract", "Tracking difference can deviate from TER"),
        ("Subscription is separated from incremental M2 cost", "The platform plan supports the whole account", "A5C", "Attribution is account-specific", "AMBIGUOUS", "Both subscription-separate and included results shown", "Future plan/fees may change"),
    ]
    return pd.DataFrame(
        rows,
        columns=["assumption", "rationale", "affected_stage", "potential_bias", "direction_of_possible_bias", "mitigation", "residual_limitation"],
    )


def build_signal_table() -> pd.DataFrame:
    gate = read_csv("UKACTIVE_A4D_STAGE_A_SIGNAL_GATE.csv")
    robust = read_csv("UKACTIVE_A4D_ROBUSTNESS_RESULTS.csv")
    robust = robust.loc[
        robust["window_id"].isin(["FULL_HISTORY", "LATEST_5Y"])
        & robust["cost_scenario"].eq("BASE")
        & robust["excluded_families"].isna()
    ].copy()
    pivot = robust.pivot_table(
        index="signal_id",
        columns="window_id",
        values=["net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "annual_turnover_traded_notional"],
        aggfunc="first",
    )
    rows = []
    names = {
        "M1_EQUAL_5H": "M1: equal five-horizon composite",
        "M2_INTERMEDIATE_5H": "M2: intermediate-weighted five-horizon composite",
        "M3_STRUCTURAL_DETERIORATION": "M3: M2 with deterioration penalty",
    }
    for sid in names:
        g = gate.loc[gate.signal_id.eq(sid)]
        rows.append(
            {
                "signal_id": sid,
                "description": names[sid],
                "positive_ic_horizons": int(g.iloc[0].positive_ic_horizons) if len(g) else np.nan,
                "positive_top_quintile_horizons": int(g.iloc[0].positive_top_quintile_horizons) if len(g) else np.nan,
                "stage_a_gate": bool(g.iloc[0].passes_gate) if len(g) else np.nan,
                "full_net_cagr": pivot.loc[sid, ("net_cagr", "FULL_HISTORY")],
                "full_pool_excess_cagr": pivot.loc[sid, ("net_excess_vs_equal_pool", "FULL_HISTORY")],
                "full_mdd": pivot.loc[sid, ("maximum_drawdown", "FULL_HISTORY")],
                "latest5_net_cagr": pivot.loc[sid, ("net_cagr", "LATEST_5Y")],
                "latest5_pool_excess_cagr": pivot.loc[sid, ("net_excess_vs_equal_pool", "LATEST_5Y")],
                "latest5_mdd": pivot.loc[sid, ("maximum_drawdown", "LATEST_5Y")],
                "full_turnover": pivot.loc[sid, ("annual_turnover_traded_notional", "FULL_HISTORY")],
            }
        )
    return pd.DataFrame(rows)


def build_breadth_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE_A4D_BREADTH_RESULTS.csv")
    data = data.loc[
        data.signal_id.eq("M2_INTERMEDIATE_5H")
        & data.window_id.isin(["FULL_HISTORY", "LATEST_5Y"])
    ].copy()
    fields = ["net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "calmar_mar", "ulcer_index", "annual_turnover_traded_notional", "cost_drag_cagr"]
    wide = data.pivot(index="breadth", columns="window_id", values=fields)
    rows = []
    for breadth in sorted(data.breadth.unique()):
        row = {"breadth": int(breadth), "region_status": "TOP6--TOP9 PLATEAU" if 6 <= int(breadth) <= 9 else "OUTSIDE PLATEAU"}
        for field in fields:
            row[f"full_{field}"] = wide.loc[breadth, (field, "FULL_HISTORY")]
            row[f"latest5_{field}"] = wide.loc[breadth, (field, "LATEST_5Y")]
        row["selection_status"] = "FROZEN REPRESENTATIVE" if int(breadth) == 7 else ("RECENT CAGR MAXIMUM" if int(breadth) == 8 else "NOT SELECTED")
        rows.append(row)
    return pd.DataFrame(rows)


def build_frequency_table() -> pd.DataFrame:
    base = read_csv("UKACTIVE_A4D_FREQUENCY_RESULTS.csv")
    double = read_csv("UKACTIVE_A4D_FREQUENCY_DOUBLE_COST_RESULTS.csv")
    selector = lambda d: d.loc[
        d.signal_id.eq("M2_INTERMEDIATE_5H")
        & d.breadth.eq(7)
        & d.window_id.isin(["FULL_HISTORY", "LATEST_5Y"])
    ].copy()
    base, double = selector(base), selector(double)
    rows = []
    for frequency in ["DAILY", "WEEKLY", "MONTHLY"]:
        row: dict[str, Any] = {"frequency": frequency}
        for window, prefix in [("FULL_HISTORY", "full"), ("LATEST_5Y", "latest5")]:
            b = base.loc[(base.frequency.eq(frequency)) & base.window_id.eq(window)].iloc[0]
            d = double.loc[(double.frequency.eq(frequency)) & double.window_id.eq(window)].iloc[0]
            for field in ["gross_cagr", "net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "ulcer_index", "annual_turnover_traded_notional", "cost_drag_cagr", "average_holding_period_calendar_days", "average_etf_replacement_rate", "trade_legs"]:
                row[f"{prefix}_{field}"] = b[field]
            row[f"{prefix}_double_cost_net_cagr"] = d.net_cagr
            row[f"{prefix}_double_cost_pool_excess"] = d.net_excess_vs_equal_pool
            row[f"{prefix}_double_cost_mdd"] = d.maximum_drawdown
        row["decision"] = "SELECTED" if frequency == "MONTHLY" else "REJECTED"
        rows.append(row)
    return pd.DataFrame(rows)


def build_cash_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE_A4D_CASH_DEFENCE_RESULTS.csv")
    data = data.loc[data.breadth.eq(7) & data.window_id.isin(["FULL_HISTORY", "LATEST_5Y"])].copy()
    fields = ["net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "ulcer_index", "calmar_mar", "average_cash_weight", "percentage_time_with_cash", "annual_turnover_traded_notional"]
    wide = data.pivot(index="cash_architecture", columns="window_id", values=fields)
    names = {
        "CASH_0_ALWAYS_INVESTED": "CASH0 always invested",
        "CASH_1_INDIVIDUAL_ABOVE_CASH_252": "CASH1 family above cash (252 sessions)",
        "CASH_2_POOL_BREADTH": "CASH2 pool breadth defence",
        "CASH_3_GLOBAL_CONFIRMATION": "CASH3 global confirmation",
        "CASH_4_PARSIMONIOUS_COMBINED": "CASH4 combined defence",
    }
    rows = []
    for architecture in names:
        row: dict[str, Any] = {"cash_architecture": architecture, "description": names[architecture]}
        for field in fields:
            row[f"full_{field}"] = wide.loc[architecture, (field, "FULL_HISTORY")]
            row[f"latest5_{field}"] = wide.loc[architecture, (field, "LATEST_5Y")]
        row["decision"] = "SELECTED" if architecture == "CASH_0_ALWAYS_INVESTED" else "REJECTED"
        rows.append(row)
    return pd.DataFrame(rows)


def build_weighting_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE_A4D_WEIGHTING_RESULTS.csv")
    data = data.loc[data.window_id.isin(["FULL_HISTORY", "LATEST_5Y"])].copy()
    fields = ["net_cagr", "net_excess_vs_equal_pool", "maximum_drawdown", "ulcer_index", "annual_turnover_traded_notional"]
    wide = data.pivot(index="weighting_method", columns="window_id", values=fields)
    rows = []
    for method in ["W0_EQUAL", "W1_RANK_DECAY", "W2_FIXED_TOP_HEAVY"]:
        row: dict[str, Any] = {"weighting_method": method, "decision": "SELECTED" if method == "W0_EQUAL" else "REJECTED"}
        for field in fields:
            row[f"full_{field}"] = wide.loc[method, (field, "FULL_HISTORY")]
            row[f"latest5_{field}"] = wide.loc[method, (field, "LATEST_5Y")]
        rows.append(row)
    return pd.DataFrame(rows)


def build_common_window_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv")
    data = data.loc[
        data.window_id.eq("FULL_COMMON_HISTORY") & data.cost_scenario.eq("BASE")
    ].copy()
    ids = [
        "GLOBAL_100",
        "GLOBAL_75_CASH25",
        "M2_TOP7_CASH0_100",
        "GLOBAL_50_M2_50",
        "GLOBAL_50_M2_25_CASH25",
        "M2_TOP7_CASH0_50_CASH50",
        "M2_TOP7_CASH0_75_CASH25",
    ]
    labels = {
        "GLOBAL_100": "100% SWDA/global developed equities",
        "GLOBAL_75_CASH25": "75% SWDA / 25% cash control",
        "M2_TOP7_CASH0_100": "100% M2 TOP7 active strategy",
        "GLOBAL_50_M2_50": "50% SWDA / 50% M2 research blend",
        "GLOBAL_50_M2_25_CASH25": "50% SWDA / 25% M2 / 25% cash",
        "M2_TOP7_CASH0_50_CASH50": "50% M2 / 50% cash",
        "M2_TOP7_CASH0_75_CASH25": "75% M2 / 25% cash",
    }
    rows = []
    for sid in ids:
        row = data.loc[data.strategy_id.eq(sid)].iloc[0]
        rows.append(
            {
                "strategy_id": sid,
                "description": labels[sid],
                "sample_start": COMMON_START.date().isoformat(),
                "sample_end": CUTOFF.date().isoformat(),
                "net_cagr": row.net_cagr,
                "terminal_wealth_per_100k": row.terminal_wealth_per_100k,
                "maximum_drawdown": row.maximum_drawdown,
                "calmar": row.net_cagr / abs(row.maximum_drawdown),
                "ulcer_index": row.ulcer_index,
                "annualised_volatility": row.annualised_volatility,
                "longest_underwater_days": row.longest_underwater_days,
                "annual_turnover": row.turnover,
                "cost_drag_cagr": row.cost_drag,
                "source_status": "CANONICAL_A4F",
            }
        )

    curve = pd.read_parquet(canonical("UKACTIVE_A4D_EQUITY_CURVES.parquet"))
    local = curve.loc[
        curve.series_id.eq("EQUAL_WEIGHT_OPPORTUNITY_POOL")
        & pd.to_datetime(curve.date).between(COMMON_START, CUTOFF)
    ].copy()
    local["date"] = pd.to_datetime(local.date)
    wealth = local.drop_duplicates("date").set_index("date").portfolio_value
    metrics = portfolio_metrics(wealth)
    rows.append(
        {
            "strategy_id": "EQUAL_WEIGHT_OPPORTUNITY_POOL",
            "description": "Contemporaneous equal-weight industry/theme opportunity pool",
            "sample_start": COMMON_START.date().isoformat(),
            "sample_end": CUTOFF.date().isoformat(),
            "net_cagr": metrics["net_cagr"],
            "terminal_wealth_per_100k": metrics["terminal_wealth_per_100k"],
            "maximum_drawdown": metrics["maximum_drawdown"],
            "calmar": metrics["net_cagr"] / abs(metrics["maximum_drawdown"]),
            "ulcer_index": metrics["ulcer_index"],
            "annualised_volatility": metrics["annualised_volatility"],
            "longest_underwater_days": metrics["longest_underwater_days"],
            "annual_turnover": np.nan,
            "cost_drag_cagr": np.nan,
            "source_status": "DERIVED_DIAGNOSTIC_FROM_CANONICAL_A4D_EQUITY_CURVE",
        }
    )
    return pd.DataFrame(rows)


def build_calendar_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv")
    ids = [
        "GLOBAL_100",
        "GLOBAL_50_M2_50",
        "M2_TOP7_CASH0_100",
        "EQUAL_WEIGHT_OPPORTUNITY_POOL",
        "GLOBAL_75_CASH25",
    ]
    data = data.loc[data.strategy_id.isin(ids)].copy()
    wide = data.pivot(index=["year", "partial_year"], columns="strategy_id", values="net_return").reset_index()
    wide = wide.rename(
        columns={
            "GLOBAL_100": "swda_return",
            "GLOBAL_50_M2_50": "blend_50_50_return",
            "M2_TOP7_CASH0_100": "m2_return",
            "EQUAL_WEIGHT_OPPORTUNITY_POOL": "equal_pool_return",
            "GLOBAL_75_CASH25": "control_75_25_return",
        }
    )
    wide["m2_minus_swda_compounded_difference"] = wide.m2_return - wide.swda_return
    pilot = read_csv("UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_WHOLE_PORTFOLIO_DRAG.csv")
    pilot = pilot.loc[
        pilot.diagnostic.eq("CALENDAR_YEAR")
        & pilot.m2_allocation.eq(0.10)
        & pilot.ii_plan.eq("II_PLUS")
        & pilot.subscription_treatment.eq("SUBSCRIPTION_REPORTED_SEPARATELY")
    ].copy()
    pilot["year"] = pd.to_datetime(pilot.period_end).dt.year
    pilot = pilot[["year", "actual_blend_minus_continuity"]].rename(
        columns={"actual_blend_minus_continuity": "pilot_10_minus_control"}
    )
    return wide.merge(pilot, on="year", how="left")


def build_regime_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv")
    data = data.loc[
        data.strategy_id.eq("M2_TOP7_CASH0_100")
        & data.summary_level.eq("FOUR_STATE_REGIME")
        & data.risk_score_substate.eq("ALL_SUBSTATES")
    ].copy()
    return data[
        [
            "regime",
            "months",
            "episodes",
            "average_episode_months",
            "annualised_return",
            "realised_volatility",
            "worst_month",
            "episode_mdd",
            "m2_minus_global",
            "excess_vs_equal_pool",
            "sample_status",
        ]
    ].sort_values("regime")


def build_dynamic_policy_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv")
    data = data.loc[
        data.window_id.eq("FULL_COMMON_HISTORY") & data.cost_scenario.eq("BASE")
    ].copy()
    columns = [
        "policy_id",
        "switch_mode",
        "net_cagr",
        "maximum_drawdown",
        "ulcer_index",
        "calmar",
        "annualised_volatility",
        "longest_underwater_days",
        "turnover",
        "average_global_weight",
        "average_m2_weight",
        "average_cash_weight",
        "return_retention",
        "promotion_status",
        "all_mandatory_gates",
        "eligible_for_selection",
    ]
    return data[columns].sort_values(["policy_id", "switch_mode"])


def build_randomisation_table() -> pd.DataFrame:
    return read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_RANDOM_SELECTION_CONTROL.csv")


def build_contribution_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    family = read_csv("UKACTIVE_A4D_CONTRIBUTION_BY_FAMILY.csv").sort_values(
        "share_of_gross_family_market_pnl", ascending=False
    )
    rank = read_csv("UKACTIVE_A4D_CONTRIBUTION_BY_RANK.csv")
    spell = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv")
    spell = spell.sort_values("normalised_arithmetic_return_contribution", ascending=False)
    influence = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv")
    influence = influence.loc[
        influence.policy_id.eq("M2_TOP7_CASH0_100")
        & influence.switch_mode.eq("STATIC_MONTHLY")
    ].copy()
    return family, rank, spell, influence


def build_influence_summary() -> pd.DataFrame:
    family = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv")
    spell = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv")
    f = family.loc[
        family.policy_id.eq("M2_TOP7_CASH0_100")
        & family.switch_mode.eq("STATIC_MONTHLY")
        & family.window_id.eq("FULL_COMMON_HISTORY")
    ].copy()
    rows = []
    for exclusion_type, label in [
        ("LEAVE_ONE_FAMILY_OUT", "Leave one family out (minimum)"),
        ("EXCLUDE_TOP_1_FAMILY_CONTRIBUTORS", "Exclude top one family"),
        ("EXCLUDE_TOP_3_FAMILY_CONTRIBUTORS", "Exclude top three families"),
        ("EXCLUDE_TOP_5_FAMILY_CONTRIBUTORS", "Exclude top five families"),
    ]:
        local = f.loc[f.exclusion_type.eq(exclusion_type)]
        if local.empty:
            continue
        row = local.sort_values("incremental_vs_replacement_control").iloc[0]
        rows.append(
            {
                "test": label,
                "exclusion_detail": row.excluded_families,
                "net_cagr": row.net_cagr,
                "maximum_drawdown": row.maximum_drawdown,
                "incremental_vs_control": row.incremental_vs_replacement_control,
                "outcome": row.dependency_status,
                "evidence_type": "FAMILY_EXCLUSION",
            }
        )
    local_spell = spell.loc[
        spell.policy_id.eq("M2_TOP7_CASH0_100") & spell.switch_mode.eq("STATIC_MONTHLY")
    ].sort_values("exclusion_count")
    for row in local_spell.itertuples(index=False):
        rows.append(
            {
                "test": f"Delete top {int(row.exclusion_count)} holding spell(s)",
                "exclusion_detail": row.excluded_families_and_dates,
                "net_cagr": row.net_cagr,
                "maximum_drawdown": row.maximum_drawdown,
                "incremental_vs_control": row.incremental_vs_replacement_control,
                "outcome": row.dependency_status,
                "evidence_type": "HOLDING_SPELL_DELETION",
            }
        )
    return pd.DataFrame(rows)


def build_uncertainty_table() -> pd.DataFrame:
    block = read_csv("UKACTIVE_A4D_REPRESENTATIVE_BLOCK_BOOTSTRAP.csv")
    rows = []
    for item in block.itertuples(index=False):
        rows.append(
            {
                "test": "Six-month circular block bootstrap",
                "comparator": item.comparator_id,
                "sample_start": item.window_start,
                "sample_end": item.window_end,
                "observations": item.monthly_observation_count,
                "block_length_months": item.block_months,
                "paths": item.simulation_count,
                "estimate": item.observed_annualised_excess,
                "lower_95": item.bootstrap_2_5_percentile,
                "upper_95": item.bootstrap_97_5_percentile,
                "probability_positive": item.bootstrap_probability_excess_positive,
                "adjustment_or_status": "Interval includes zero",
            }
        )
    hac = read_csv("UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv")
    m2 = hac.loc[
        hac.signal_id.eq("M2_INTERMEDIATE_5H")
        & hac.window_id.eq("FULL_HISTORY")
        & hac.metric.isin(["IC", "TOP_QUINTILE_ADVANTAGE"])
    ].copy()
    for item in m2.itertuples(index=False):
        rows.append(
            {
                "test": "HAC weekly signal diagnostic",
                "comparator": f"{item.metric} at {int(item.forward_horizon_sessions)} sessions",
                "sample_start": "2017-02-03",
                "sample_end": CUTOFF.date().isoformat(),
                "observations": item.observation_count,
                "block_length_months": np.nan,
                "paths": np.nan,
                "estimate": item.estimate,
                "lower_95": np.nan,
                "upper_95": np.nan,
                "probability_positive": np.nan,
                "adjustment_or_status": f"BH q={item.bh_q_value_within_window_metric:.4f}; no q<=0.10",
            }
        )
    return pd.DataFrame(rows)


def build_robustness_table() -> pd.DataFrame:
    a4d = read_csv("UKACTIVE_A4D_PRIMARY_ECONOMIC_SCORECARD.csv")
    a4d = a4d.loc[a4d.specification_id.str.startswith("M2_INTERMEDIATE_5H|TOP_7|MONTHLY|CASH_0")].copy()
    rows: list[dict[str, Any]] = []
    labels = {
        "PRE_2020": "Pre-2020",
        "POST_2020": "Post-2020",
        "LATEST_5Y": "Latest five years",
        "LATEST_3Y": "Latest three years",
        "FULL_HISTORY": "Full common history",
    }
    for item in a4d.loc[a4d.window_id.isin(labels)].itertuples(index=False):
        value = float(item.net_excess_vs_global)
        rows.append(
            {
                "test": labels[item.window_id],
                "net_cagr": item.net_cagr,
                "incremental_vs_swda": value,
                "maximum_drawdown": item.maximum_drawdown,
                "cost_scenario": item.cost_scenario,
                "assessment": "PRESERVES" if value > 0.0025 else ("MATERIALLY_WEAKENS" if value >= 0 else "REVERSES"),
                "source": "A4D_PRIMARY_ECONOMIC_SCORECARD",
            }
        )
    year = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv")
    year = year.loc[
        year.policy_id.eq("M2_TOP7_CASH0_100")
        & year.switch_mode.eq("STATIC_MONTHLY")
        & year.excluded_period.isin(["EXCLUDE_2020", "EXCLUDE_2025", "EXCLUDE_2020_AND_2025"])
    ].copy()
    for item in year.itertuples(index=False):
        value = float(item.excess_vs_global)
        rows.append(
            {
                "test": item.excluded_period.replace("_", " ").title(),
                "net_cagr": item.net_cagr,
                "incremental_vs_swda": value,
                "maximum_drawdown": item.maximum_drawdown,
                "cost_scenario": "BASE",
                "assessment": "PRESERVES" if value > 0.0025 else ("MATERIALLY_WEAKENS" if value >= 0 else "REVERSES"),
                "source": "A4F_YEAR_EXCLUSION_RESULTS",
            }
        )
    static = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv")
    for cost in ["BASE", "DOUBLE"]:
        item = static.loc[
            static.strategy_id.eq("M2_TOP7_CASH0_100")
            & static.window_id.eq("FULL_COMMON_HISTORY")
            & static.cost_scenario.eq(cost)
        ].iloc[0]
        swda = static.loc[
            static.strategy_id.eq("GLOBAL_100")
            & static.window_id.eq("FULL_COMMON_HISTORY")
            & static.cost_scenario.eq(cost)
        ].iloc[0]
        value = float(item.net_cagr - swda.net_cagr)
        rows.append(
            {
                "test": "Baseline costs" if cost == "BASE" else "Doubled costs",
                "net_cagr": item.net_cagr,
                "incremental_vs_swda": value,
                "maximum_drawdown": item.maximum_drawdown,
                "cost_scenario": cost,
                "assessment": "PRESERVES" if value > 0.0025 else ("MATERIALLY_WEAKENS" if value >= 0 else "REVERSES"),
                "source": "A4F_STATIC_FRONTIER",
            }
        )
    return pd.DataFrame(rows).drop_duplicates(["test", "cost_scenario"], keep="last")


def build_wrapper_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv")
    ids = [
        "GLOBAL_75_DEFENSIVE_25",
        "GLOBAL_65_M2_10_DEFENSIVE_25",
        "GLOBAL_60_M2_15_DEFENSIVE_25",
        "GLOBAL_50_M2_25_DEFENSIVE_25",
        "M2_100_DIAGNOSTIC",
        "GLOBAL_100",
    ]
    data = data.loc[
        data.strategy_id.isin(ids)
        & data.ii_plan.eq("II_PLUS")
        & data.window_id.isin(["FULL_HISTORY", "LATEST_FIVE_YEARS"])
    ].copy()
    return data[
        [
            "strategy_id",
            "control_id",
            "window_id",
            "notional_gbp",
            "one_way_friction_bps",
            "gross_cagr",
            "net_cagr_subscription_reported_separately",
            "net_cagr_full_subscription_deducted",
            "net_incremental_cagr_vs_control",
            "maximum_drawdown",
            "ulcer_index",
            "annual_turnover",
            "trade_legs",
            "total_dealing_charges_gbp",
            "total_subscription_gbp",
            "historical_total_market_friction_gbp",
            "current_scale_annual_market_friction_gbp",
            "current_scale_annual_all_in_including_friction_gbp",
        ]
    ].sort_values(["window_id", "strategy_id"])


def build_live_map_table() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv")
    columns = [
        "economic_exposure_family_id",
        "fund_name",
        "ticker",
        "isin",
        "trading_currency",
        "currency_hedging_status",
        "alternate_ticker",
        "alternate_isin",
        "alternate_trading_currency",
        "signal_status_at_2026_08_21",
        "implementation_role",
        "a5c_current_status",
        "automatic_alternate_permitted",
        "historical_back_projection",
    ]
    return data[columns].sort_values(["implementation_role", "economic_exposure_family_id"])


def build_relative_regret_summary() -> pd.DataFrame:
    data = read_csv("UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv")
    data = data.loc[
        data.diagnostic.isin(["MAXIMUM_RELATIVE_DRAWDOWN", "LONGEST_RELATIVE_UNDERPERFORMANCE_DAYS"])
    ].copy()
    return data[
        [
            "candidate_id",
            "control_id",
            "diagnostic",
            "period_start",
            "period_end",
            "months",
            "relative_return",
            "m2_allocation",
            "value",
            "unit",
        ]
    ].sort_values(["candidate_id", "diagnostic"])


def figure_footer(fig: plt.Figure, text: str) -> None:
    fig.text(0.01, 0.008, text, ha="left", va="bottom", fontsize=7.3, color="#4b5563")


def plot_lineage(lineage: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(13.2, 8.0))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 4)
    ax.axis("off")
    stages = lineage.stage.tolist()
    positions = []
    for i in range(len(stages)):
        row, col = divmod(i, 4)
        x = col + 0.5 if row % 2 == 0 else 3.5 - col
        y = 3.45 - row
        positions.append((x, y))
    colors = ["#dbeafe", "#dbeafe", "#fee2e2", "#dcfce7", "#fee2e2", "#dcfce7", "#fef3c7", "#fef3c7", "#fef3c7", "#fef3c7", "#dbeafe", "#e0e7ff", "#e0e7ff", "#dcfce7"]
    for i, (stage, position) in enumerate(zip(stages, positions)):
        x, y = position
        decision = lineage.iloc[i].decision.replace("_", " ")
        ax.text(
            x,
            y,
            f"{stage}\n{decision}",
            ha="center",
            va="center",
            fontsize=8,
            weight="bold" if i in {10, 13} else "normal",
            bbox=dict(boxstyle="round,pad=0.45", facecolor=colors[i], edgecolor="#475569", linewidth=0.8),
        )
        if i < len(stages) - 1:
            nx, ny = positions[i + 1]
            ax.annotate("", xy=(nx, ny + (0.17 if ny < y else 0)), xytext=(x, y - (0.17 if ny < y else 0)), arrowprops=dict(arrowstyle="->", color="#64748b", lw=1.0))
    ax.set_title("Figure 1. UKACTIVE research lineage and decision chronology", pad=14)
    ax.text(2.0, 0.13, "Red = blocking defect; amber = exploratory/developmental; blue = structured test; green = repair/freeze", ha="center", fontsize=8, color="#475569")
    figure_footer(fig, "Sample: lineage through historical cutoff 2026-08-21 | Costs/frequency/performance basis: not applicable | No post-cutoff evidence used")
    fig.subplots_adjust(bottom=0.08, top=0.92)
    return save_figure(fig, "FIGURE_01_RESEARCH_LINEAGE.png")


def plot_causal_timeline() -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(12.8, 6.6), gridspec_kw={"height_ratios": [1.05, 1.0]})
    ax = axes[0]
    ax.set_xlim(pd.Timestamp("2009-01-01"), pd.Timestamp("2027-01-01"))
    ax.set_ylim(0, 4)
    ax.set_yticks([])
    ax.grid(axis="x")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    spans = [
        (pd.Timestamp("2010-01-08"), CUTOFF, 3.0, "SWDA/core history\n(longer context; conflicted final table)"),
        (pd.Timestamp("2017-02-03"), CUTOFF, 2.0, "Five-horizon formation chain"),
        (COMMON_START, CUTOFF, 1.0, "Common executable strategy window"),
    ]
    for left, right, y, label in spans:
        ax.plot([left, right], [y, y], lw=8, solid_capstyle="butt", color={3.0: GREY, 2.0: ORANGE, 1.0: BLUE}[y])
        ax.text(left, y + 0.25, label, fontsize=8.4, va="bottom")
    ax.axvline(CUTOFF, color=RED, lw=1.5, ls="--")
    ax.text(CUTOFF, 3.65, "Historical cutoff\n2026-08-21", color=RED, ha="right", va="top", fontsize=8.5)
    ax.set_title("Figure 2. Data windows and causal monthly execution contract")

    ax = axes[1]
    ax.set_xlim(0, 7.4)
    ax.set_ylim(0, 1)
    ax.axis("off")
    events = [
        (0.45, "Last valid\nXLON session", "Total-return data\nbecome observable"),
        (2.10, "Review date", "Eligibility + five\nrelative-strength ranks"),
        (3.75, "TOP7 fixed", "Deterministic ties;\nno same-close trade"),
        (5.35, "Next XLON session", "First valid execution;\nmarket-price assumption"),
        (6.85, "Holding interval", "Returns measured\nafter execution"),
    ]
    for i, (x, title, note) in enumerate(events):
        ax.scatter([x], [0.60], s=140, color=BLUE if i < 4 else TEAL, zorder=3)
        ax.text(x, 0.85, title, ha="center", va="top", weight="bold", fontsize=8.5)
        ax.text(x, 0.36, note, ha="center", va="top", fontsize=7.8, color="#4b5563")
        if i < len(events) - 1:
            ax.annotate("", xy=(events[i + 1][0] - 0.12, 0.60), xytext=(x + 0.12, 0.60), arrowprops=dict(arrowstyle="->", color="#64748b"))
    ax.text(3.75, 0.08, "Unavailable/suspended slot -> CSH2; execution must occur within three valid sessions; otherwise suspend", ha="center", fontsize=8.2, color=RED)
    figure_footer(fig, "Sample: causal contract frozen at 2026-08-21 | Frequency: monthly | Configuration: M2 TOP7 CASH0 equal weight | Return basis: after-cost results begin only after next-session execution")
    fig.subplots_adjust(hspace=0.35, bottom=0.11, top=0.91)
    return save_figure(fig, "FIGURE_02_DATA_CAUSAL_TIMELINE.png")


def plot_breadth(table: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.4), sharex=True)
    x = table.breadth
    for ax, prefix, title in [
        (axes[0], "full", "Full common history"),
        (axes[1], "latest5", "Latest five years"),
    ]:
        ax.axvspan(5.5, 9.5, color="#dbeafe", alpha=0.55, label="TOP6--TOP9 region")
        ax.plot(x, 100 * table[f"{prefix}_net_cagr"], marker="o", color=BLUE, label="Net CAGR")
        ax.plot(x, 100 * table[f"{prefix}_net_excess_vs_equal_pool"], marker="s", color=ORANGE, label="CAGR difference vs pool")
        ax.axhline(0, color="#111827", lw=0.8)
        ax.axvline(7, color=RED, ls="--", lw=1.1, label="Frozen TOP7")
        ax.set_title(title)
        ax.set_xlabel("Selected families")
        ax.set_ylabel("Percent / percentage points")
        ax.set_xticks(x)
        ax.grid(True)
    axes[1].legend(loc="best", fontsize=8)
    fig.suptitle("Figure 3. Breadth frontier: the result is a region, not a unique optimum", fontsize=14, weight="bold")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 and 2021-09-01–2026-08-21 | Net of 20 bps one-way + fixed dealing fee | Monthly | M2 CASH0 equal weight")
    fig.subplots_adjust(bottom=0.15, top=0.83, wspace=0.22)
    return save_figure(fig, "FIGURE_03_BREADTH_FRONTIER.png")


def plot_frequency(table: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.5))
    colors = {"DAILY": RED, "WEEKLY": ORANGE, "MONTHLY": GREEN}
    for row in table.itertuples(index=False):
        axes[0].scatter(row.full_annual_turnover_traded_notional, 100 * row.full_net_cagr, s=125, color=colors[row.frequency], label=row.frequency.title())
        axes[0].annotate(row.frequency.title(), (row.full_annual_turnover_traded_notional, 100 * row.full_net_cagr), xytext=(5, 5), textcoords="offset points", fontsize=8)
    axes[0].set_xlabel("Annual traded-notional turnover (x)")
    axes[0].set_ylabel("Net CAGR (%)")
    axes[0].set_title("Return versus turnover")
    axes[0].grid(True)
    x = np.arange(len(table))
    width = 0.36
    axes[1].bar(x - width / 2, 100 * table.full_net_excess_vs_equal_pool, width, color=BLUE, label="Baseline-cost pool excess")
    axes[1].bar(x + width / 2, 100 * table.full_double_cost_pool_excess, width, color=ORANGE, label="Doubled-cost pool excess")
    axes[1].axhline(0, color="#111827", lw=0.8)
    axes[1].set_xticks(x, table.frequency.str.title())
    axes[1].set_ylabel("CAGR difference vs equal pool (pp)")
    axes[1].set_title("Cost survivability")
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y")
    fig.suptitle("Figure 4. Rebalance frequency, turnover and cost drag", fontsize=14, weight="bold")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | Baseline 20 bps one-way and doubled 40 bps stress, fixed dealing fee retained | M2 TOP7 CASH0 equal weight | Net returns")
    fig.subplots_adjust(bottom=0.15, top=0.83, wspace=0.28)
    return save_figure(fig, "FIGURE_04_FREQUENCY_TURNOVER_COST.png")


def _common_wealth_series() -> dict[str, pd.Series]:
    data = pd.read_parquet(canonical("UKACTIVE_A4D_EQUITY_CURVES.parquet"))
    data["date"] = pd.to_datetime(data.date)
    ids = {
        "SWDA / global developed": "GLOBAL_DEVELOPED_WORLD",
        "Equal-weight opportunity pool": "EQUAL_WEIGHT_OPPORTUNITY_POOL",
        "M2 TOP7": "REPRESENTATIVE_ALWAYS_INVESTED",
    }
    date_sets = []
    for sid in ids.values():
        date_sets.append(set(data.loc[data.series_id.eq(sid) & data.date.between(COMMON_START, CUTOFF), "date"]))
    dates = pd.DatetimeIndex(sorted(set.intersection(*date_sets)))
    result = {}
    for label, sid in ids.items():
        value = data.loc[data.series_id.eq(sid)].drop_duplicates("date").set_index("date").portfolio_value.reindex(dates).astype(float)
        result[label] = value / value.iloc[0]
    return result


def plot_equity_and_drawdown() -> tuple[Path, Path]:
    series = _common_wealth_series()
    colors = {"SWDA / global developed": GREY, "Equal-weight opportunity pool": ORANGE, "M2 TOP7": BLUE}
    fig, ax = plt.subplots(figsize=(12.0, 6.2))
    for label, value in series.items():
        ax.plot(value.index, value.values * 100000, lw=1.9, color=colors[label], label=label)
    ax.set_title("Figure 5. Growth of £100,000 on the common executable window")
    ax.set_ylabel("Portfolio value (£)")
    ax.yaxis.set_major_formatter(lambda x, pos: f"£{x:,.0f}")
    ax.grid(True)
    ax.legend(loc="upper left")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | M2 net of 20 bps one-way + fixed fee; benchmarks as canonical references | Monthly M2 TOP7 CASH0 equal weight | Net M2 path")
    fig.subplots_adjust(bottom=0.13, top=0.90)
    equity = save_figure(fig, "FIGURE_05_EQUITY_CURVES.png")

    fig, ax = plt.subplots(figsize=(12.0, 6.2))
    for label, value in series.items():
        drawdown = value / value.cummax() - 1.0
        ax.plot(drawdown.index, 100 * drawdown.values, lw=1.8, color=colors[label], label=label)
    ax.set_title("Figure 6. Drawdown paths on the common executable window")
    ax.set_ylabel("Drawdown from own prior high (%)")
    ax.grid(True)
    ax.legend(loc="lower left")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | M2 net of 20 bps one-way + fixed fee | Monthly M2 TOP7 CASH0 equal weight | Drawdown from each series' own net wealth peak")
    fig.subplots_adjust(bottom=0.13, top=0.90)
    drawdown = save_figure(fig, "FIGURE_06_DRAWDOWN_CURVES.png")
    return equity, drawdown


def plot_calendar(table: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(12.5, 6.3))
    x = np.arange(len(table))
    width = 0.19
    columns = [
        ("swda_return", "SWDA", GREY),
        ("blend_50_50_return", "50/50 SWDA/M2", TEAL),
        ("m2_return", "100% M2", BLUE),
        ("equal_pool_return", "Equal pool", ORANGE),
    ]
    for j, (column, label, color) in enumerate(columns):
        ax.bar(x + (j - 1.5) * width, 100 * table[column], width, label=label, color=color)
    labels = [f"{int(y)}*" if bool(p) else str(int(y)) for y, p in zip(table.year, table.partial_year)]
    ax.set_xticks(x, labels)
    ax.axhline(0, color="#111827", lw=0.9)
    ax.set_ylabel("Calendar-year net return (%)")
    ax.set_title("Figure 7. Calendar-year returns (* partial year)")
    ax.legend(ncol=4, loc="upper left", fontsize=8)
    ax.grid(axis="y")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21; 2017 and 2026 partial | Baseline costs | Monthly M2 TOP7 CASH0 equal weight | Net returns")
    fig.subplots_adjust(bottom=0.14, top=0.90)
    return save_figure(fig, "FIGURE_07_CALENDAR_YEAR_RETURNS.png")


def plot_rolling_excess() -> Path:
    data = read_csv("UKACTIVE_A4D_ROLLING_EXCESS_RESULTS.csv")
    fig, axes = plt.subplots(2, 1, figsize=(12.3, 7.1), sharex=True)
    comparators = [("GLOBAL_DEVELOPED_WORLD", "SWDA/global developed"), ("EQUAL_POOL", "equal-weight opportunity pool")]
    palette = {12: ORANGE, 24: TEAL, 36: BLUE}
    for ax, (comparator, title) in zip(axes, comparators):
        local = data.loc[data.comparator_id.eq(comparator) & data.rolling_months.isin([12, 24, 36])].copy()
        for months, group in local.groupby("rolling_months"):
            date = pd.to_datetime(dict(year=group.end_year, month=group.end_month, day=1)) + pd.offsets.MonthEnd(0)
            ax.plot(date, 100 * group.excess_return, color=palette[int(months)], lw=1.35, label=f"{int(months)} months")
        ax.axhline(0, color="#111827", lw=0.8)
        ax.set_ylabel("Compounded excess (%)")
        ax.set_title(f"M2 minus {title}")
        ax.grid(True)
    axes[0].legend(ncol=3, fontsize=8)
    fig.suptitle("Figure 8. Rolling 12-, 24- and 36-month excess returns", fontsize=14, weight="bold")
    figure_footer(fig, "Sample: rolling windows ending within 2017-03-01–2026-08-21 | Baseline costs | Monthly M2 TOP7 CASH0 equal weight | Compounded net-return difference")
    fig.subplots_adjust(bottom=0.11, top=0.88, hspace=0.30)
    return save_figure(fig, "FIGURE_08_ROLLING_EXCESS.png")


def plot_family_contribution(family: pd.DataFrame) -> Path:
    local = family.head(14).sort_values("share_of_gross_family_market_pnl")
    fig, ax = plt.subplots(figsize=(11.4, 6.6))
    colors = [BLUE if value >= 0 else RED for value in local.share_of_gross_family_market_pnl]
    ax.barh(local.economic_exposure_family_id.str.replace("_", " ").str.title(), 100 * local.share_of_gross_family_market_pnl, color=colors)
    ax.set_xlabel("Share of gross family market P&L (%)")
    ax.set_title("Figure 9. Largest family contributions to M2 gross market P&L")
    ax.axvline(0, color="#111827", lw=0.8)
    ax.grid(axis="x")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | Gross family market P&L before portfolio transaction costs | Monthly M2 TOP7 CASH0 equal weight | Shares can exceed 100% collectively when other families detract")
    fig.subplots_adjust(left=0.27, bottom=0.13, top=0.90)
    return save_figure(fig, "FIGURE_09_CONTRIBUTION_BY_FAMILY.png")


def plot_rank_contribution(rank: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9.6, 5.5))
    values = 100 * rank.share_of_gross_family_market_pnl
    display_labels = {
        "RANK_1": "Rank 1",
        "RANK_2_3": "Ranks 2–3",
        "RANK_4_5": "Ranks 4–5",
        "RANK_6_10": "Ranks 6–10",
        "UNATTRIBUTED_HELD_OUTSIDE_CURRENT_SELECTED_RANKS": "Other /\nunattributed",
    }
    labels = [display_labels.get(str(bucket), str(bucket)) for bucket in rank.rank_bucket]
    ax.bar(labels, values, color=[BLUE, TEAL, "#6b8e23", ORANGE, GREY][: len(rank)])
    ax.axhline(0, color="#111827", lw=0.8)
    ax.set_ylabel("Share of gross family market P&L (%)")
    ax.set_title("Figure 10. Contribution by selected rank bucket")
    ax.grid(axis="y")
    for i, value in enumerate(values):
        ax.text(i, value + (1 if value >= 0 else -1), f"{value:.1f}%", ha="center", va="bottom" if value >= 0 else "top", fontsize=8)
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | Gross family market P&L | Monthly M2 TOP7 CASH0 equal weight | Rank buckets refer to selection-time M2 order")
    fig.subplots_adjust(bottom=0.15, top=0.88)
    return save_figure(fig, "FIGURE_10_CONTRIBUTION_BY_RANK.png")


def _exact_randomisation_arrays() -> dict[str, dict[str, np.ndarray | float]]:
    """Exact A4F CASH0 falsification rerun, extended only to retain path arrays."""

    code_dir = canonical("code")
    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))
    import ukactive_a4f_sipp_core as a4f_core  # type: ignore
    import ukactive_a4e_sipp_core as a4e_core  # type: ignore

    data = a4f_core.load_data()
    m2_result = a4e_core.simulate_rotation(data, "M2_BASE", 7, False, cost_scenario="BASE")
    baseline_targets = dict(m2_result.targets)
    canonical_summary = build_randomisation_table().set_index("control_id")
    dates = sorted(baseline_targets)
    calendar = pd.DatetimeIndex(data.base.research.calendar)
    position = {pd.Timestamp(date): i for i, date in enumerate(calendar)}
    decision_dates: list[pd.Timestamp] = []
    execution_dates: list[pd.Timestamp] = []
    for date in dates:
        pos = position[pd.Timestamp(date)] + 1
        if pos < len(calendar) and pd.Timestamp(calendar[pos]) <= CUTOFF:
            decision_dates.append(pd.Timestamp(date))
            execution_dates.append(pd.Timestamp(calendar[pos]))
    members = list(data.members)
    member_index = {family: i for i, family in enumerate(members)}
    feature = a4e_core.monthly_features(data).set_index("date")
    wealth = data.base.research.wealth[members]
    segment = data.base.research.segment[members]
    cash = data.base.cash_index
    interval_count = len(execution_dates) - 1
    asset_factors = np.full((interval_count, len(members)), np.nan, dtype=float)
    cash_factors = np.ones(interval_count, dtype=float)
    for k in range(interval_count):
        left, right = execution_dates[k], execution_dates[k + 1]
        left_value = wealth.loc[left].to_numpy(float)
        right_value = wealth.loc[right].to_numpy(float)
        same = segment.loc[left].to_numpy(object) == segment.loc[right].to_numpy(object)
        valid = np.isfinite(left_value) & np.isfinite(right_value) & same
        asset_factors[k, valid] = right_value[valid] / left_value[valid]
        cash_factors[k] = float(cash.loc[right] / cash.loc[left])

    def selection_frame(date: pd.Timestamp) -> pd.DataFrame:
        frame = a4e_core._selection_frame(data, feature.loc[date].reset_index(), "M2_BASE").copy()
        frame["ABOVE_CASH_252"] = 1.0
        return frame

    def run(targets: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        paths = targets.shape[1]
        nav = np.ones(paths, dtype=float)
        high = np.ones(paths, dtype=float)
        maximum_drawdown = np.zeros(paths, dtype=float)
        current_weights = np.zeros((paths, len(members)), dtype=float)
        total_turnover = np.zeros(paths, dtype=float)
        for k in range(interval_count):
            target = targets[k]
            delta = target - current_weights
            turnover = np.abs(delta).sum(axis=1)
            legs = (np.abs(delta) > 1e-12).sum(axis=1)
            cost = turnover * 20.0 / 10000.0 + legs * 3.99 / 250000.0
            nav *= np.maximum(0.0, 1.0 - cost)
            total_turnover += turnover
            cash_weight = np.maximum(0.0, 1.0 - target.sum(axis=1))
            factor_matrix = np.where(np.isfinite(asset_factors[k]), asset_factors[k], 1.0)
            risky_end = target * factor_matrix[None, :]
            cash_end = cash_weight * cash_factors[k]
            portfolio_factor = risky_end.sum(axis=1) + cash_end
            nav *= portfolio_factor
            current_weights = np.divide(risky_end, portfolio_factor[:, None], out=np.zeros_like(risky_end), where=portfolio_factor[:, None] > 0)
            high = np.maximum(high, nav)
            maximum_drawdown = np.minimum(maximum_drawdown, nav / high - 1.0)
        years = interval_count / 12.0
        return np.power(nav, 1.0 / years) - 1.0, maximum_drawdown, total_turnover / years

    result: dict[str, dict[str, np.ndarray | float]] = {}
    for mode, row in canonical_summary.iterrows():
        simulations = int(row.simulation_count)
        rng = np.random.default_rng(int(row.seed))
        target_cube = np.zeros((interval_count, simulations, len(members)), dtype=float)
        baseline_cube = np.zeros((interval_count, 1, len(members)), dtype=float)
        for k in range(interval_count):
            date = decision_dates[k]
            frame = selection_frame(date)
            eligible = frame.economic_exposure_family_id.astype(str).tolist()
            qualifying = frame.loc[frame.ABOVE_CASH_252.eq(1.0), "economic_exposure_family_id"].astype(str).tolist()
            valid_interval = np.isfinite(asset_factors[k])
            for family, weight in baseline_targets.get(date, {}).items():
                idx = member_index[family]
                if valid_interval[idx]:
                    baseline_cube[k, 0, idx] = float(weight)
            if mode == "RANDOM_SELECTION_SAME_RISKY_COUNT":
                pool = np.asarray(qualifying, dtype=object)
                count = min(len(baseline_targets.get(date, {})), len(pool))
                scores = rng.random((simulations, len(pool)))
                selected_positions = np.argpartition(scores, count - 1, axis=1)[:, :count]
                for path_index in range(simulations):
                    for family in pool[selected_positions[path_index]]:
                        idx = member_index[str(family)]
                        if valid_interval[idx]:
                            target_cube[k, path_index, idx] = 1.0 / 7.0
            elif mode == "MONTHLY_RANK_SHUFFLE":
                pool = np.asarray(eligible, dtype=object)
                count = min(7, len(pool))
                scores = rng.random((simulations, len(pool)))
                selected_positions = np.argpartition(scores, count - 1, axis=1)[:, :count]
                for path_index in range(simulations):
                    for family in pool[selected_positions[path_index]]:
                        idx = member_index[str(family)]
                        if valid_interval[idx]:
                            target_cube[k, path_index, idx] = 1.0 / count
            else:
                raise AssertionError(mode)
        random_cagr, random_mdd, random_turnover = run(target_cube)
        candidate_cagr, candidate_mdd, candidate_turnover = run(baseline_cube)
        checks = {
            "candidate_diagnostic_cagr": float(candidate_cagr[0]),
            "candidate_diagnostic_maximum_drawdown": float(candidate_mdd[0]),
            "candidate_diagnostic_turnover": float(candidate_turnover[0]),
            "candidate_cagr_percentile": float(np.mean(random_cagr <= candidate_cagr[0])),
            "candidate_drawdown_percentile_less_severe": float(np.mean(random_mdd <= candidate_mdd[0])),
        }
        for field, value in checks.items():
            if not np.isclose(value, float(row[field]), atol=1e-12, rtol=0):
                raise AssertionError(f"Randomisation reproduction mismatch {mode} {field}: {value} vs {row[field]}")
        result[mode] = {
            "cagr": random_cagr,
            "mdd": random_mdd,
            "turnover": random_turnover,
            "candidate_cagr": float(candidate_cagr[0]),
            "candidate_mdd": float(candidate_mdd[0]),
        }
        del target_cube
    return result


def plot_randomisation(paths: dict[str, dict[str, np.ndarray | float]]) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.6), sharey=True)
    names = {"RANDOM_SELECTION_SAME_RISKY_COUNT": "Matched-count random selection", "MONTHLY_RANK_SHUFFLE": "Monthly rank shuffle"}
    for ax, (mode, label) in zip(axes, names.items()):
        cagr = np.asarray(paths[mode]["cagr"], dtype=float)
        candidate = float(paths[mode]["candidate_cagr"])
        ax.hist(100 * cagr, bins=42, color="#a7c7e7", edgecolor="white", density=True)
        ax.axvline(100 * candidate, color=RED, lw=2.0, label=f"M2: {100*candidate:.2f}%")
        percentile = 100 * np.mean(cagr <= candidate)
        ax.set_title(f"{label}\nM2 CAGR percentile: {percentile:.2f}")
        ax.set_xlabel("Diagnostic net CAGR (%)")
        ax.grid(axis="y")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Density across 10,000 paths")
    fig.suptitle("Figure 11. Matched opportunity-set falsification distributions", fontsize=14, weight="bold")
    figure_footer(fig, "Sample: first/last diagnostic executions 2017-03-01–2026-08-03 | 20 bps one-way + £3.99/leg on £250,000 | Monthly TOP7 CASH0 eligibility | Exact A4F vectorised diagnostic, net returns")
    fig.subplots_adjust(bottom=0.15, top=0.82, wspace=0.14)
    return save_figure(fig, "FIGURE_11_RANDOM_SELECTION_DISTRIBUTION.png")


def plot_spell_concentration(spell: pd.DataFrame) -> Path:
    local = spell.loc[spell.normalised_arithmetic_return_contribution.gt(0)].copy().head(18)
    local["label"] = local.family.str.replace("GLOBAL_", "", regex=False).str.replace("_", " ").str.title() + "\n" + pd.to_datetime(local.entry_date).dt.strftime("%Y-%m")
    local["cumulative"] = local.normalised_arithmetic_return_contribution.cumsum()
    fig, ax1 = plt.subplots(figsize=(12.5, 6.2))
    x = np.arange(len(local))
    ax1.bar(x, 100 * local.normalised_arithmetic_return_contribution, color=BLUE, alpha=0.82, label="Spell contribution")
    ax1.set_ylabel("Normalised arithmetic return contribution (%)")
    ax1.set_xticks(x, local.label, rotation=55, ha="right", fontsize=7.2)
    ax1.grid(axis="y")
    ax2 = ax1.twinx()
    ax2.plot(x, 100 * local.cumulative, color=ORANGE, marker="o", lw=1.7, label="Cumulative top-spell contribution")
    ax2.set_ylabel("Cumulative contribution (%)")
    ax1.set_title("Figure 12. Holding-spell contribution concentration")
    handles, labels = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles + handles2, labels + labels2, loc="upper right", fontsize=8)
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | Contribution is a gross/arithmetic explanatory attribution, not CAGR | Monthly M2 TOP7 CASH0 equal weight | Holding spells ranked ex post only")
    fig.subplots_adjust(bottom=0.28, top=0.90, right=0.88)
    return save_figure(fig, "FIGURE_12_HOLDING_SPELL_CONCENTRATION.png")


def plot_regime_timeline() -> Path:
    data = read_csv("UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv")
    data["decision_date"] = pd.to_datetime(data.decision_date)
    colors = {
        "R1_BROAD_RISK_ON": "#9ecae1",
        "R2_LEADERSHIP_RISK_ON": "#31a354",
        "R3_ISOLATED_LEADERSHIP": "#fdae6b",
        "R4_CAPITAL_PRESERVATION": "#de2d26",
    }
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(12.5, 6.4), sharex=True, gridspec_kw={"height_ratios": [0.85, 1.25]})
    for item in data.itertuples(index=False):
        start = pd.Timestamp(item.decision_date)
        end = start + pd.offsets.MonthEnd(1)
        ax0.axvspan(start, end, color=colors[item.regime], alpha=0.9)
    ax0.set_yticks([])
    ax0.set_title("Figure 13. Causal A4F regime telemetry timeline")
    from matplotlib.patches import Patch
    ax0.legend([Patch(facecolor=color, label=label.replace("_", " ").title()) for label, color in colors.items()], [label.replace("_", " ").title() for label in colors], ncol=4, fontsize=7.4, loc="upper left")
    ax1.step(data.decision_date, data.risk_score, where="post", color=RED, lw=1.5, label="Risk score (0–3)")
    ax1.scatter(data.decision_date, data.leadership_strong.astype(int), color=BLUE, s=9, alpha=0.7, label="Leadership strong (1/0)")
    ax1.set_yticks([0, 1, 2, 3])
    ax1.set_ylabel("Causal state inputs")
    ax1.grid(True)
    ax1.legend(ncol=2, fontsize=8)
    figure_footer(fig, "Sample: monthly decisions 2017-02-28–2026-07-31; cutoff 2026-08-21 | Costs/performance: not applicable | A4F prior-only thresholds | Regimes retained as telemetry, not allocation controls")
    fig.subplots_adjust(bottom=0.13, top=0.90, hspace=0.18)
    return save_figure(fig, "FIGURE_13_REGIME_TIMELINE.png")


def plot_dynamic_static(policy: pd.DataFrame, common: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(11.3, 6.3))
    ax.scatter(100 * common.maximum_drawdown.abs(), 100 * common.net_cagr, color=GREY, marker="s", s=75, label="Static controls/comparators")
    for row in common.itertuples(index=False):
        if row.strategy_id in {"GLOBAL_100", "GLOBAL_75_CASH25", "M2_TOP7_CASH0_100", "GLOBAL_50_M2_50"}:
            ax.annotate(row.strategy_id.replace("_", " "), (100 * abs(row.maximum_drawdown), 100 * row.net_cagr), xytext=(4, 4), textcoords="offset points", fontsize=7)
    marker = {"SWITCH_IMMEDIATE_MONTHLY": "o", "SWITCH_ASYMMETRIC_HYSTERESIS": "^"}
    dynamic_only = policy.loc[~policy.policy_id.eq("POLICY_0_STATIC_DEFENSIVE_CONTROL")].copy()
    for switch, group in dynamic_only.groupby("switch_mode"):
        ax.scatter(100 * group.maximum_drawdown.abs(), 100 * group.net_cagr, s=90, marker=marker[switch], label=switch.replace("SWITCH_", "").replace("_", " ").title(), alpha=0.85)
        suffix = "I" if switch == "SWITCH_IMMEDIATE_MONTHLY" else "H"
        offset = (4, 3) if suffix == "I" else (4, -10)
        for row in group.itertuples(index=False):
            label = row.policy_id.replace("POLICY_", "P").split("_")[0] + f"-{suffix}"
            ax.annotate(label, (100 * abs(row.maximum_drawdown), 100 * row.net_cagr), xytext=offset, textcoords="offset points", fontsize=7)
    ax.set_xlabel("Maximum drawdown magnitude (%) — lower is left")
    ax.set_ylabel("Net CAGR (%)")
    ax.set_title("Figure 14. Dynamic policies versus static controls")
    ax.grid(True)
    ax.legend(fontsize=8)
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 | Baseline 20 bps one-way + fixed fee | Monthly M2/SWDA/cash policies | Net returns; no dynamic policy passed all gates")
    fig.subplots_adjust(bottom=0.14, top=0.90)
    return save_figure(fig, "FIGURE_14_DYNAMIC_VS_STATIC.png")


def plot_wrapper_frontier(wrapper: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.5), sharey=False)
    ids = ["GLOBAL_75_DEFENSIVE_25", "GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25"]
    labels = {"GLOBAL_75_DEFENSIVE_25": "0% M2 control", "GLOBAL_65_M2_10_DEFENSIVE_25": "10% M2 pilot", "GLOBAL_60_M2_15_DEFENSIVE_25": "15% M2 comparator", "GLOBAL_50_M2_25_DEFENSIVE_25": "25% M2 comparator"}
    colors = {ids[0]: GREY, ids[1]: GREEN, ids[2]: ORANGE, ids[3]: RED}
    for ax, window, title in zip(axes, ["FULL_HISTORY", "LATEST_FIVE_YEARS"], ["Full history", "Latest five years"]):
        local = wrapper.loc[
            wrapper.window_id.eq(window)
            & wrapper.strategy_id.isin(ids)
            & wrapper.notional_gbp.eq(563000)
        ].copy()
        for row in local.itertuples(index=False):
            ax.scatter(100 * abs(row.maximum_drawdown), 100 * row.net_cagr_subscription_reported_separately, s=120, color=colors[row.strategy_id])
            ax.annotate(labels[row.strategy_id], (100 * abs(row.maximum_drawdown), 100 * row.net_cagr_subscription_reported_separately), xytext=(5, 4), textcoords="offset points", fontsize=7.5)
        ax.set_xlabel("Maximum drawdown magnitude (%)")
        ax.set_ylabel("Net CAGR, subscription separate (%)")
        ax.set_title(title)
        ax.grid(True)
    fig.suptitle("Figure 15. Whole-SIPP M2 allocation return–drawdown frontier", fontsize=14, weight="bold")
    figure_footer(fig, "Sample: 2017-03-01–2026-08-21 and 2021-09-01–2026-08-21 | £563,000, II Plus, 20 bps one-way; subscription separate | Monthly M2 TOP7; 25% defensive fixed | Net returns")
    fig.subplots_adjust(bottom=0.15, top=0.82, wspace=0.28)
    return save_figure(fig, "FIGURE_15_WHOLE_SIPP_FRONTIER.png")


def plot_relative_regret() -> Path:
    data = read_csv("UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv")
    data = data.loc[data.diagnostic.eq("ROLLING_12M_RELATIVE_RETURN")].copy()
    data["period_end"] = pd.to_datetime(data.period_end)
    order = ["M2_100_DIAGNOSTIC", "GLOBAL_65_M2_10_DEFENSIVE_25", "GLOBAL_60_M2_15_DEFENSIVE_25", "GLOBAL_50_M2_25_DEFENSIVE_25"]
    labels = {"M2_100_DIAGNOSTIC": "100% M2 vs SWDA", "GLOBAL_65_M2_10_DEFENSIVE_25": "10% M2 pilot vs control", "GLOBAL_60_M2_15_DEFENSIVE_25": "15% M2 vs control", "GLOBAL_50_M2_25_DEFENSIVE_25": "25% M2 vs control"}
    colors = {order[0]: BLUE, order[1]: GREEN, order[2]: ORANGE, order[3]: RED}
    fig, ax = plt.subplots(figsize=(12.3, 6.2))
    for candidate in order:
        local = data.loc[data.candidate_id.eq(candidate)].sort_values("period_end")
        ax.plot(local.period_end, 100 * local.relative_return, lw=1.5, color=colors[candidate], label=labels[candidate])
    ax.axhline(0, color="#111827", lw=0.8)
    ax.set_ylabel("Rolling 12-month compounded relative return (%)")
    ax.set_title("Figure 16. Relative regret and benchmark underperformance")
    ax.grid(True)
    ax.legend(ncol=2, fontsize=8)
    figure_footer(fig, "Sample: rolling windows ending within 2017-03-01–2026-08-21 | II Plus, £563,000, subscription separate | Monthly M2 TOP7; wrappers retain 25% defensive | Net relative returns")
    fig.subplots_adjust(bottom=0.14, top=0.90)
    return save_figure(fig, "FIGURE_16_RELATIVE_REGRET.png")


def build_evidence_matrix(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    claims: list[Claim] = []
    lineage_sources = {
        "A0/A1": "UKACTIVE_A0A1_DECISION.json",
        "A2": "UKACTIVE_A2_DECISION.json",
        "A3R0": "UKACTIVE_A3R0_DECISION.json",
        "A2R": "UKACTIVE_A2R_DECISION.json",
        "A3R1": "UKACTIVE_A3R1_DECISION.json",
        "A2R2": "UKACTIVE_A2R2_DECISION.json",
        "A3R1R1": "UKACTIVE_A3R1R1_DECISION.json",
        "A3R2/U/S/W/Q": "UKACTIVE_A3R2_DECISION.json",
        "A4": "UKACTIVE_A4_DECISION.json",
        "A4B/A4C": "UKACTIVE_A4C_DECISION.json",
        "A4D": "UKACTIVE_A4D_DECISION.json",
        "A4E-SIPP": "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_DECISION.json",
        "A4F-SIPP": "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_DECISION.json",
        "A5C-SIPP": "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_DECISION.json",
    }
    for row in tables["lineage"].itertuples(index=False):
        claims.append(
            Claim(
                f"LIN-{row.stage.replace('/', '-').replace(' ', '')}",
                "3 Research lineage and decision chronology",
                f"{row.stage}: {row.decision}",
                row.stage,
                lineage_sources[row.stage],
                "final decision/disposition fields",
                metric_definition="Chronological programme disposition",
            )
        )
    funnel_sources = {
        "A0/A1": "UKACTIVE_A0A1_MANIFEST.json",
        "A2": "UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv",
        "A5C": "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json",
    }
    for index, row in tables["universe_funnel"].iterrows():
        claims.append(
            Claim(
                f"DATA-{index+1:02d}",
                "4 Dataset and investable universe",
                f"{row.funnel_step}: {int(row['count'])}",
                row.source_stage,
                funnel_sources[row.source_stage],
                f"count/manifest field for {row.funnel_step}",
                metric_definition=row.definition,
            )
        )
    claims.extend(
        [
            Claim("DATA-A2-COVERAGE", "4 Dataset and investable universe", "A2 usable-history coverage: 89 one-year, 86 three-year, 77 five-year, 59 ten-year families", "A2", "UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv", "coverage-year aggregate rows", metric_definition="Families with accepted history at each trailing horizon"),
            Claim("DATA-A2-PANEL", "5 Construction of the research data", "A2 validated routes/histories/panel counts", "A2", "UKACTIVE_A2_MANIFEST.json", "summary counts: 367 routes, 357 histories, 667700 panel rows"),
            Claim("DATA-A2-MISSING", "5 Construction of the research data", "1,842 stale observations invalidated and 62,667 in-life missing observations retained as missing", "A2", "UKACTIVE_A2_STALE_AND_MISSING_DATA_REPORT.csv", "aggregate status counts"),
            Claim("DATA-A2R-BLOCK", "5 Construction of the research data", "A3R0 found 14 material family/history mismatches; A2R remediated 13 without proxying the remaining family", "A3R0/A2R", "UKACTIVE_A2R_BEFORE_AFTER_HISTORY_AUDIT.csv", "blocking-family before/after status"),
            Claim("DATA-A2R2-CALENDAR", "5 Construction of the research data", "A2R2 removed 29 false vendor sessions and rebuilt a true XLON calendar", "A2R2", "UKACTIVE_A2R2_ROOT_CAUSE_REPORT.md", "false-session root-cause findings"),
            Claim("DATA-A2R2-ENDPOINT", "5 Construction of the research data", "Prior-only endpoint tolerance is at most three true XLON sessions; gaps over three reset the segment", "A2R2", "UKACTIVE_A2R2_GAP_AND_STALENESS_POLICY.md", "endpoint tolerance and segment-reset rules"),
            Claim("DATA-A2R2-ELIG", "5 Construction of the research data", "Cutoff eligibility: 81 families for 21/42/63/126 and 80 for 252 sessions in the broader corrected panel", "A2R2", "UKACTIVE_A2R2_HORIZON_COVERAGE_BY_YEAR.csv", "2026/latest horizon eligible-family counts"),
            Claim("CASH-SONIA", "7 Benchmark and cash definitions", "Historical cash is a time-varying GBP SONIA series, not a constant 4%", "A2", "UKACTIVE_A2_CASH_MODEL.md", "accepted series and ACT/365 compounding contract"),
            Claim("COST-HIST", "10 Transaction-cost model", "20 bps one-way market-price friction and fixed dealing fee; no double TER deduction", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "historical_cost_model/live_cost_contract"),
            Claim("M2-FORMULA", "8 Signal construction", "M2 weights 0.10/0.15/0.25/0.30/0.20 on 21/42/63/126/252-session percentile relative strength", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "scientific_active_strategy.signal", metric_definition="Weighted sum of cross-sectional average-tie percentile ranks of benchmark-relative total returns"),
            Claim("M2-TIMING", "6 Causal timing and execution contract", "Final valid XLON month-end review, first following valid session execution, maximum three-session window, no same-close", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "execution_contract"),
            Claim("M2-FROZEN", "26 Exact frozen strategy", "INDUSTRY_PLUS_THEME | M2_BASE | TOP7 | MONTHLY | CASH0_ALWAYS_INVESTED | EQUAL", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "scientific_active_strategy"),
        ]
    )
    for row in tables["signal"].itertuples(index=False):
        claims.append(Claim(f"SIG-{row.signal_id}", "13 Multi-horizon signal comparison", f"{row.signal_id} gate and full/latest-five-year portfolio metrics", "A4D", "UKACTIVE_A4D_ROBUSTNESS_RESULTS.csv", f"signal_id={row.signal_id}; BASE; no family exclusion", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, CAGR difference versus equal pool, MDD, turnover; subwindow identified in fields"))
    for row in tables["breadth"].itertuples(index=False):
        claims.append(Claim(f"BR-{int(row.breadth)}", "14 Breadth frontier", f"TOP{int(row.breadth)} full-history and latest-five-year after-cost metrics", "A4D", "UKACTIVE_A4D_BREADTH_RESULTS.csv", f"signal=M2_INTERMEDIATE_5H; breadth={int(row.breadth)}; FULL_HISTORY and LATEST_5Y; BASE", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, CAGR difference versus pool, MDD, Calmar, Ulcer, turnover, cost drag"))
    for row in tables["frequency"].itertuples(index=False):
        claims.append(Claim(f"FREQ-{row.frequency}", "15 Rebalance-frequency tests", f"{row.frequency} baseline/doubled-cost full-history and latest-five-year metrics", "A4D", "UKACTIVE_A4D_FREQUENCY_RESULTS.csv", f"M2 TOP7 {row.frequency}; BASE plus paired UKACTIVE_A4D_FREQUENCY_DOUBLE_COST_RESULTS.csv", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Gross/net CAGR, pool CAGR difference, MDD, Ulcer, turnover, cost drag, holding period, replacement rate, legs", reconciliation_note="Doubled-cost fields join the canonical doubled-cost scorecard"))
    for row in tables["cash"].itertuples(index=False):
        claims.append(Claim(f"CASH-{row.cash_architecture.split('_')[1]}", "16 Cash and defensive-overlay tests", f"{row.description} full-history/latest-five-year economics", "A4D", "UKACTIVE_A4D_CASH_DEFENCE_RESULTS.csv", f"breadth=7; {row.cash_architecture}; FULL_HISTORY and LATEST_5Y; BASE", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, pool CAGR difference, MDD, Ulcer, Calmar, average cash weight, time with cash, turnover"))
    for row in tables["weighting"].itertuples(index=False):
        claims.append(Claim(f"WT-{row.weighting_method}", "17 Weighting, deterioration and momentum-age tests", f"{row.weighting_method} full/latest-five-year economics", "A4D", "UKACTIVE_A4D_WEIGHTING_RESULTS.csv", f"M2 TOP7 monthly CASH0; {row.weighting_method}", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, pool CAGR difference, MDD, Ulcer, turnover"))
    for row in tables["common"].itertuples(index=False):
        source = "UKACTIVE_A4D_EQUITY_CURVES.parquet" if row.strategy_id == "EQUAL_WEIGHT_OPPORTUNITY_POOL" else "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv"
        status = "DERIVED_DIAGNOSTIC" if row.strategy_id == "EQUAL_WEIGHT_OPPORTUNITY_POOL" else "RECONCILED"
        claims.append(Claim(f"ECON-{row.strategy_id}", "18 Full-history economic results", f"{row.description}: common-window statistical profile", "A4D/A4F", source, f"strategy_id={row.strategy_id}; FULL_COMMON_HISTORY; BASE", row.sample_start, row.sample_end, "Net CAGR, terminal wealth, MDD, Calmar, Ulcer, volatility, underwater duration, turnover and cost drag", status, "Opportunity-pool path metrics are deterministic diagnostics from its canonical wealth series; other rows are canonical A4F fields"))
    for row in tables["calendar"].itertuples(index=False):
        claims.append(Claim(f"YEAR-{int(row.year)}", "19 Year-by-year performance", f"Calendar {int(row.year)} returns for SWDA, 50/50, M2, equal pool, 75/25 and 10% pilot-control difference", "A4F/A5C", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv", f"year={int(row.year)}; static strategy rows; pilot difference joined from A5C WHOLE_PORTFOLIO_DRAG", str(int(row.year)), str(int(row.year)), "Compounded within-calendar-period net return; 2017 and 2026 partial", reconciliation_note="Pilot-control difference joins UKACTIVE_A5C_SIPP_WHOLE_PORTFOLIO_DRAG.csv"))
    for row in tables["regime"].itertuples(index=False):
        claims.append(Claim(f"REG-{row.regime}", "20 Regime analysis", f"{row.regime}: months, episodes and M2 differential", "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv", f"M2_TOP7_CASH0_100; FOUR_STATE_REGIME; regime={row.regime}", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Causal monthly-regime descriptive return statistics"))
    for row in tables["dynamic_policy"].itertuples(index=False):
        claims.append(Claim(f"POL-{row.policy_id}-{row.switch_mode}", "20 Regime analysis", f"{row.policy_id}/{row.switch_mode} full-history outcome", "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv", f"{row.policy_id}; {row.switch_mode}; FULL_COMMON_HISTORY; BASE", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, MDD, Ulcer, allocation, turnover, return retention and promotion gates"))
    for row in tables["randomisation"].itertuples(index=False):
        claims.append(Claim(f"RAND-{row.control_id}", "21 Randomisation and falsification evidence", f"{row.control_id}: candidate and 10,000-path percentiles", "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_RANDOM_SELECTION_CONTROL.csv", f"control_id={row.control_id}", str(row.diagnostic_first_execution_date), str(row.diagnostic_last_execution_date), "Matched causal vectorised diagnostic CAGR, MDD and turnover percentiles"))
    for index, row in tables["family_contribution"].head(12).iterrows():
        claims.append(Claim(f"CONTRIB-FAM-{index+1:02d}", "22 Right-tail dependence and contribution analysis", f"{row.economic_exposure_family_id} contribution share", "A4D", "UKACTIVE_A4D_CONTRIBUTION_BY_FAMILY.csv", f"economic_exposure_family_id={row.economic_exposure_family_id}", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Share of gross family market P&L"))
    for row in tables["rank_contribution"].itertuples(index=False):
        claims.append(Claim(f"CONTRIB-RANK-{row.rank_bucket}", "22 Right-tail dependence and contribution analysis", f"Rank bucket {row.rank_bucket} contribution", "A4D", "UKACTIVE_A4D_CONTRIBUTION_BY_RANK.csv", f"rank_bucket={row.rank_bucket}", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Share of gross family market P&L"))
    for index, row in tables["holding_spells"].head(10).iterrows():
        claims.append(Claim(f"SPELL-{index+1:02d}", "22 Right-tail dependence and contribution analysis", f"{row.holding_spell_id} {row.family} contribution and held return", "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv", f"holding_spell_id={row.holding_spell_id}", str(row.entry_date), str(row.exit_date), "Ex-post explanatory normalised arithmetic contribution and held total return"))
    for index, row in tables["influence"].iterrows():
        claims.append(Claim(f"INFL-{index+1:02d}", "22 Right-tail dependence and contribution analysis", str(row.test), "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv" if row.evidence_type == "HOLDING_SPELL_DELETION" else "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv", str(row.exclusion_detail), COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Counterfactual net CAGR/MDD and incremental CAGR versus replacement control"))
    for index, row in tables["uncertainty"].iterrows():
        source = "UKACTIVE_A4D_REPRESENTATIVE_BLOCK_BOOTSTRAP.csv" if row.test.startswith("Six") else "UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv"
        claims.append(Claim(f"UNC-{index+1:02d}", "23 Statistical uncertainty", f"{row.test}: {row.comparator}", "A4D", source, f"filtered row: {row.comparator}", str(row.sample_start), str(row.sample_end), "HAC or block-bootstrap estimate with stated adjustment/interval"))
    for index, row in tables["robustness"].iterrows():
        sources = {"A4D_PRIMARY_ECONOMIC_SCORECARD": "UKACTIVE_A4D_PRIMARY_ECONOMIC_SCORECARD.csv", "A4F_YEAR_EXCLUSION_RESULTS": "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_YEAR_EXCLUSION_RESULTS.csv", "A4F_STATIC_FRONTIER": "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv"}
        claims.append(Claim(f"ROB-{index+1:02d}", "24 Robustness and influence tests", f"{row.test}: {row.assessment}", "A4D/A4F", sources[row.source], f"M2 TOP7 row; {row.test}; cost={row.cost_scenario}", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, CAGR difference versus SWDA, MDD; exclusion CAGR is a non-contiguous diagnostic when applicable"))
    for row in tables["wrapper"].itertuples(index=False):
        notional = int(row.notional_gbp)
        claims.append(Claim(f"WRAP-{row.strategy_id}-{row.window_id}-{notional}", "27 Detailed frozen-strategy statistics", f"{row.strategy_id} {row.window_id} II Plus £{notional:,} cost/performance profile", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv", f"strategy_id={row.strategy_id}; window={row.window_id}; ii_plan=II_PLUS; notional_gbp={notional}", COMMON_START.date().isoformat() if row.window_id == "FULL_HISTORY" else LATEST5_START.date().isoformat(), CUTOFF.date().isoformat(), "Gross and net CAGR with subscription separate/included, MDD, Ulcer, turnover and GBP costs"))
    claims.extend(
        [
            Claim("A3-INF-180", "12 Initial signal tests", "A3R1R1 tested 180 multiple-testing cells; no BH q-value at or below 0.10 and no positive bootstrap lower-bound survivor", "A3R1R1", "UKACTIVE_A3R1R1_MULTIPLE_TESTING_LEDGER.csv", "all executed rows plus final disposition", metric_definition="Predeclared inference-cell count and false-discovery disposition"),
            Claim("A3-INF-315", "12 Initial signal tests", "A3R2 tested 315 portfolio specifications; none survived BH q-value 0.10", "A3R2", "UKACTIVE_A3R2_MULTIPLE_TESTING_LEDGER.csv", "all rows; fdr_survives_q_0_10", metric_definition="Portfolio-specification count and false-discovery disposition"),
            Claim("SIG-HAC-REP", "13 Multi-horizon signal comparison", "Representative M2 weekly 21/42/63-session IC and top-quintile diagnostics; no q-value at or below 0.10", "A4D", "UKACTIVE_A4D_SIGNAL_HAC_INFERENCE.csv", "M2_BASE weekly 21/42/63-session rows", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Rank IC/top-tail estimates with HAC inference and multiple-testing adjustment"),
            Claim("MATCH-CASH1", "16 Cash and defensive-overlay tests", "CASH1 underperformed static same-exposure and global/cash matched-exposure controls on full history", "A4E-SIPP", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_MATCHED_EXPOSURE_CONTROLS.csv", "CASH1 matched-exposure rows", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR and MDD at matched average risky exposure"),
            Claim("CORE1-BINARY", "16 Cash and defensive-overlay tests", "Binary 252-session global/cash rule compounded at 6.82%, MDD -25.58%, return retention 58.8%; failed", "A4E-SIPP", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_CORE_RESULTS.csv", "CORE1 binary global/cash row", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Net CAGR, MDD and return-retention diagnostic"),
            Claim("COST-PLAN", "10 Transaction-cost model", "II Plus and Premium dealing fees, credits and subscriptions; subscription separated from incremental M2 cost", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "cost_policy/ii_plan fields", metric_definition="Current frozen retail fee schedule used by A5C"),
            Claim("PILOT-563K", "10 Transaction-cost model", "£563,000 illustration: £365,950 SWDA, £56,300 M2, £140,750 defensive and £8,042.86 per M2 family", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "initial_whole_sipp_pilot/current_notional illustration", metric_definition="Deterministic target illustration; not an order"),
            Claim("RELREG-M2", "31 Performance expectations and relative underperformance", "Standalone M2 maximum relative drawdown versus SWDA -26.78% and longest relative underperformance 1,595 days", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv", "candidate_id=M2_100_DIAGNOSTIC summary rows", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Relative-wealth drawdown and calendar-day underperformance duration"),
            Claim("RELREG-WRAPPERS", "31 Performance expectations and relative underperformance", "10%/15%/25% wrapper maximum relative drawdowns -3.10%/-4.54%/-7.37% and longest spans 1,595/1,595/1,594 days", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv", "wrapper candidate summary rows", COMMON_START.date().isoformat(), CUTOFF.date().isoformat(), "Relative to 75/25 control; subscription-separated II Plus £563,000"),
            Claim("SUSPENSION-RULES", "32 Suspension and governance", "Frozen data, rank, availability, execution-window and 40 bps cost-breach suspensions; no performance-only stop", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_MONTHLY_RUNBOOK.md", "Suspensions and manual execution pack", metric_definition="Operational control; does not change historical 20 bps baseline"),
            Claim("DEFENSIVE-ROLES", "29 Defensive implementation", "RLON strategic identity unresolved; CSH2 LU1230136894 tactical; broker cash operational residual", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv", "implementation_role DEFENSIVE_STRATEGIC/DEFENSIVE_TACTICAL/BROKER_CASH_OPERATIONAL", metric_definition="Current-only implementation identities and readiness"),
            Claim("LIVE-MAP", "28 Live instrument implementation", "31 frozen implementation roles including 27 M2 families; preferred and alternate GBP/GBX controls", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv", "all rows/implementation roles", metric_definition="Current-only implementation map; historical_back_projection=PROHIBITED"),
            Claim("PILOT-ALLOCATION", "30 How the strategy should be used", "65% SWDA, 10% M2, 25% defensive; each M2 family approximately 1.43% of whole SIPP", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "initial_whole_sipp_pilot", metric_definition="Risk-budgeted wrapper, separate from ranking signal"),
            Claim("PILOT-CAP", "30 How the strategy should be used", "Total active/thematic exposure cap 25%", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "governance.active_thematic_cap"),
            Claim("A5C-READINESS", "33 Prospective evidence plan", "Readiness AWAITING_CURRENT_HOLDINGS_INPUT; pilot_operationally_ready=false", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_DECISION.json", "current_readiness/pilot_operationally_ready"),
            Claim("A5C-LEDGER", "33 Prospective evidence plan", "Prospective ledger contains zero data rows at freeze", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_PROSPECTIVE_LEDGER.csv", "header-only ledger", status="RECONCILED"),
            Claim("A5C-CHECKS", "33 Prospective evidence plan", "A5C correctness suite passed 26 of 26 checks", "A5C", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_CORRECTNESS_TESTS.csv", "all test rows/status"),
            Claim("LONG-CORE-CONFLICT", "18 Full-history economic results", "A4F longer core-only result table is unusable because final CSV covers only 2010-03-01 to 2010-03-09 while narrative says 2010-01-08 to 2026-08-21", "A4F", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv", "first_date/last_date/net_cagr versus reproduction-audit stated window", "2010-01-08", CUTOFF.date().isoformat(), "Source-conflict audit", "UNRESOLVED_SOURCE_CONFLICT", "No longer-window return is reported; common-window comparisons remain authoritative"),
        ]
    )
    return claim_frame(claims)


def canonical_source_audit() -> dict[str, Any]:
    files = [
        "UKACTIVE_A0A1_MANIFEST.json", "UKACTIVE_A0A1_DECISION.json", "UKACTIVE_A0A1_SCOPE_AND_METHOD.md", "UKACTIVE_A0A1_ECONOMIC_EXPOSURE_MASTER.csv",
        "UKACTIVE_A2_MANIFEST.json", "UKACTIVE_A2_DECISION.json", "UKACTIVE_A2_DATA_QUALITY_REPORT.md", "UKACTIVE_A2_FAMILY_COVERAGE_AND_READINESS.csv", "UKACTIVE_A2_POINT_IN_TIME_ELIGIBILITY.parquet", "UKACTIVE_A2_TOTAL_RETURN_PANEL_GBP.parquet", "UKACTIVE_A2_CASH_SERIES.parquet",
        "UKACTIVE_A3R0_MANIFEST.json", "UKACTIVE_A3R0_DECISION.json", "UKACTIVE_A2R_MANIFEST.json", "UKACTIVE_A2R_DECISION.json", "UKACTIVE_A2R_BEFORE_AFTER_HISTORY_AUDIT.csv",
        "UKACTIVE_A3R1_MANIFEST.json", "UKACTIVE_A3R1_DECISION.json", "UKACTIVE_A2R2_MANIFEST.json", "UKACTIVE_A2R2_DECISION.json", "UKACTIVE_A2R2_ROOT_CAUSE_REPORT.md", "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet",
        "UKACTIVE_A3R1R1_MANIFEST.json", "UKACTIVE_A3R1R1_DECISION.json", "UKACTIVE_A3R2_MANIFEST.json", "UKACTIVE_A3R2_DECISION.json", "UKACTIVE_A3R2U_MANIFEST.json", "UKACTIVE_A3R2W_MANIFEST.json",
        "UKACTIVE_A4_MANIFEST.json", "UKACTIVE_A4_DECISION.json", "UKACTIVE_A4B_MANIFEST.json", "UKACTIVE_A4B_DECISION.json", "UKACTIVE_A4C_MANIFEST.json", "UKACTIVE_A4C_DECISION.json",
        "UKACTIVE_A4D_MANIFEST.json", "UKACTIVE_A4D_DECISION.json", "UKACTIVE_A4D_PRIMARY_ECONOMIC_SCORECARD.csv", "UKACTIVE_A4D_BREADTH_RESULTS.csv", "UKACTIVE_A4D_FREQUENCY_RESULTS.csv", "UKACTIVE_A4D_CASH_DEFENCE_RESULTS.csv", "UKACTIVE_A4D_WEIGHTING_RESULTS.csv", "UKACTIVE_A4D_ROBUSTNESS_RESULTS.csv", "UKACTIVE_A4D_EQUITY_CURVES.parquet",
        "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_MANIFEST.json", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_DECISION.json", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_MATCHED_EXPOSURE_CONTROLS.csv", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_RANDOM_SELECTION_CONTROL.csv", "UKACTIVE-A4E-SIPP/UKACTIVE_A4E_SIPP_LIVE_INSTRUMENT_MAP.csv",
        "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_MANIFEST.json", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_DECISION.json", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_STATIC_FRONTIER.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_DYNAMIC_POLICY_RESULTS.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_REGIME_SUMMARY.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_RANDOM_SELECTION_CONTROL.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_FAMILY_INFLUENCE.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_HOLDING_SPELL_INFLUENCE.csv", "UKACTIVE-A4F-SIPP-REGIME/UKACTIVE_A4F_SIPP_LONGER_CORE_ONLY_RESULTS.csv",
        "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_MANIFEST.json", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_DECISION.json", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_FROZEN_SPEC.json", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_LIVE_INSTRUMENT_MAP_V2.csv", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_PROSPECTIVE_LEDGER.csv", "UKACTIVE-A5C-SIPP/UKACTIVE_A5C_SIPP_CORRECTNESS_TESTS.csv",
    ]
    records = []
    for relative in files:
        path = canonical(relative)
        record: dict[str, Any] = {
            "source_file": relative,
            "source_commit": source_commit(relative),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, low_memory=False)
            record.update({"rows": len(frame), "columns": list(map(str, frame.columns))})
        elif path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
            record.update({"rows": len(frame), "columns": list(map(str, frame.columns))})
        elif path.suffix.lower() == ".json":
            parsed = json.loads(path.read_text(encoding="utf-8"))
            record["top_level_fields"] = sorted(parsed) if isinstance(parsed, dict) else []
        records.append(record)
    return {
        "audit_date": GENERATION_DATE,
        "historical_cutoff": CUTOFF.date().isoformat(),
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "source_commits": {"freeze": FREEZE_COMMIT, "results": RESULTS_COMMIT, "final_manifest": MANIFEST_COMMIT},
        "files": records,
    }


def write_json(path: Path, value: Any) -> None:
    def default(item: Any) -> Any:
        if isinstance(item, (pd.Timestamp, np.datetime64)):
            return pd.Timestamp(item).isoformat()
        if isinstance(item, (np.integer,)):
            return int(item)
        if isinstance(item, (np.floating,)):
            return None if not np.isfinite(item) else float(item)
        if isinstance(item, Path):
            return str(item)
        raise TypeError(type(item).__name__)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=default) + "\n", encoding="utf-8")


def build_figure_manifest(paths: list[Path]) -> pd.DataFrame:
    metadata = [
        (1, "Research lineage and decision chronology", "Lineage through 2026-08-21", "Not applicable", "Stage-dependent", "A0/A1 through A5C", "Not applicable", "Canonical decisions/manifests"),
        (2, "Data windows and causal execution contract", "Formation 2017-02-03; executable 2017-03-01–2026-08-21", "Not applicable", "Monthly", "M2 TOP7 causal contract", "Not applicable", "A2R2 policies and A5C frozen spec"),
        (3, "Breadth frontier", "2017-03-01–2026-08-21; latest five years from 2021-09-01", "20 bps one-way plus fixed fee", "Monthly", "M2 TOP3–TOP10, CASH0, equal", "Net", "UKACTIVE_A4D_BREADTH_RESULTS.csv"),
        (4, "Frequency versus turnover and cost", "2017-03-01–2026-08-21", "20 bps baseline and 40 bps doubled stress plus fixed fee", "Daily/weekly/monthly", "M2 TOP7 CASH0 equal", "Net; gross used in source table", "A4D frequency scorecards"),
        (5, "M2, SWDA and equal-pool equity curves", "2017-03-01–2026-08-21", "M2 baseline costs; benchmark reference paths", "Monthly M2", "M2 TOP7 CASH0 equal", "Net M2 wealth", "UKACTIVE_A4D_EQUITY_CURVES.parquet"),
        (6, "Drawdown curves", "2017-03-01–2026-08-21", "M2 baseline costs; benchmark reference paths", "Monthly M2", "M2 TOP7 CASH0 equal", "Net wealth drawdown", "UKACTIVE_A4D_EQUITY_CURVES.parquet"),
        (7, "Calendar-year returns", "2017-03-01–2026-08-21; 2017/2026 partial", "Baseline", "Monthly M2", "M2 TOP7, SWDA, 50/50, equal pool", "Net", "UKACTIVE_A4F_SIPP_YEAR_BY_YEAR_SCORECARD.csv"),
        (8, "Rolling excess returns", "Rolling endpoints within 2017-03-01–2026-08-21", "Baseline", "Monthly", "M2 TOP7 CASH0 equal", "Compounded net excess", "UKACTIVE_A4D_ROLLING_EXCESS_RESULTS.csv"),
        (9, "Contribution by family", "2017-03-01–2026-08-21", "Before portfolio transaction costs", "Monthly", "M2 TOP7 CASH0 equal", "Gross attribution", "UKACTIVE_A4D_CONTRIBUTION_BY_FAMILY.csv"),
        (10, "Contribution by rank bucket", "2017-03-01–2026-08-21", "Before portfolio transaction costs", "Monthly", "M2 TOP7 CASH0 equal", "Gross attribution", "UKACTIVE_A4D_CONTRIBUTION_BY_RANK.csv"),
        (11, "Random-selection distribution", "Diagnostic executions 2017-03-01–2026-08-03", "20 bps one-way plus £3.99/leg on £250,000", "Monthly", "Matched TOP7 CASH0", "Net diagnostic", "Exact reproduction of A4F vectorised falsification"),
        (12, "Holding-spell contribution concentration", "2017-03-01–2026-08-21", "Attribution before portfolio costs", "Monthly", "M2 TOP7 CASH0 equal", "Gross/arithmetic explanatory contribution", "UKACTIVE_A4F_SIPP_HOLDING_SPELL_LEDGER.csv"),
        (13, "Regime timeline", "Monthly decisions 2017-02-28–2026-07-31", "Not applicable", "Monthly", "A4F causal regime telemetry", "Not applicable", "UKACTIVE_A4F_SIPP_MONTHLY_REGIME_LEDGER.csv"),
        (14, "Dynamic versus static performance", "2017-03-01–2026-08-21", "Baseline", "Monthly", "A4F policies and static controls", "Net", "A4F dynamic-policy and static-frontier scorecards"),
        (15, "10%/15%/25% whole-SIPP frontier", "Full and latest-five-year windows to 2026-08-21", "II Plus £563,000; 20 bps; subscription separate", "Monthly", "25% defensive, varying M2 sleeve", "Net", "UKACTIVE_A5C_SIPP_COST_RESTATEMENT.csv"),
        (16, "Relative regret", "Rolling endpoints within 2017-03-01–2026-08-21", "II Plus £563,000; subscription separate", "Monthly", "M2 and 10%/15%/25% wrappers", "Net relative", "UKACTIVE_A5C_SIPP_RELATIVE_REGRET.csv"),
    ]
    rows = []
    for values, path in zip(metadata, sorted(paths, key=lambda value: value.name)):
        figure_id, title, sample, cost, frequency, configuration, return_basis, sources = values
        rows.append(
            {
                "figure_id": figure_id,
                "file": path.relative_to(PAPER_ROOT).as_posix(),
                "title": title,
                "sample": sample,
                "cost_assumption": cost,
                "frequency": frequency,
                "strategy_configuration": configuration,
                "return_basis": return_basis,
                "source_files": sources,
                "derivation_status": "DETERMINISTIC_FORMAT_OR_EXACT_REPRODUCTION",
                "sha256": sha256(path),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-random-figure", action="store_true", help="Skip the expensive exact randomisation rerun (diagnostic use only)")
    args = parser.parse_args()
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    if git("branch", "--show-current") != "docs/ukactive-frozen-strategy-scientific-paper":
        raise AssertionError("Paper assets must be generated on the frozen documentation branch")
    subprocess.run(["git", "merge-base", "--is-ancestor", MANIFEST_COMMIT, "HEAD"], cwd=REPO_ROOT, check=True)

    family, rank, spells, spell_influence = build_contribution_tables()
    tables: dict[str, pd.DataFrame] = {
        "lineage": build_lineage_table(),
        "universe_funnel": build_universe_funnel(),
        "assumptions": build_assumptions_table(),
        "signal": build_signal_table(),
        "breadth": build_breadth_table(),
        "frequency": build_frequency_table(),
        "cash": build_cash_table(),
        "weighting": build_weighting_table(),
        "common": build_common_window_table(),
        "calendar": build_calendar_table(),
        "regime": build_regime_table(),
        "dynamic_policy": build_dynamic_policy_table(),
        "randomisation": build_randomisation_table(),
        "family_contribution": family,
        "rank_contribution": rank,
        "holding_spells": spells,
        "holding_spell_influence": spell_influence,
        "influence": build_influence_summary(),
        "uncertainty": build_uncertainty_table(),
        "robustness": build_robustness_table(),
        "wrapper": build_wrapper_table(),
        "live_map": build_live_map_table(),
        "relative_regret": build_relative_regret_summary(),
    }
    table_names = {
        "lineage": "TABLE_01_RESEARCH_LINEAGE.csv",
        "universe_funnel": "TABLE_02_UNIVERSE_FUNNEL.csv",
        "assumptions": "TABLE_03_ASSUMPTIONS.csv",
        "signal": "TABLE_04_SIGNAL_COMPARISON.csv",
        "breadth": "TABLE_05_BREADTH_FRONTIER.csv",
        "frequency": "TABLE_06_FREQUENCY_COMPARISON.csv",
        "cash": "TABLE_07_CASH_ARCHITECTURES.csv",
        "weighting": "TABLE_08_WEIGHTING_COMPARISON.csv",
        "common": "TABLE_09_COMMON_WINDOW_ECONOMICS.csv",
        "calendar": "TABLE_10_CALENDAR_RETURNS.csv",
        "regime": "TABLE_11_REGIME_SUMMARY.csv",
        "dynamic_policy": "TABLE_12_DYNAMIC_POLICIES.csv",
        "randomisation": "TABLE_13_RANDOMISATION.csv",
        "family_contribution": "TABLE_14_FAMILY_CONTRIBUTION.csv",
        "rank_contribution": "TABLE_15_RANK_CONTRIBUTION.csv",
        "holding_spells": "TABLE_16_HOLDING_SPELL_LEDGER.csv",
        "holding_spell_influence": "TABLE_17_HOLDING_SPELL_INFLUENCE.csv",
        "influence": "TABLE_18_INFLUENCE_SUMMARY.csv",
        "uncertainty": "TABLE_19_STATISTICAL_UNCERTAINTY.csv",
        "robustness": "TABLE_20_ROBUSTNESS.csv",
        "wrapper": "TABLE_21_WHOLE_SIPP_COMPARISON.csv",
        "live_map": "TABLE_22_LIVE_IMPLEMENTATION_MAP.csv",
        "relative_regret": "TABLE_23_RELATIVE_REGRET_SUMMARY.csv",
    }
    for key, frame in tables.items():
        write_csv(TABLES / table_names[key], frame)

    paths: list[Path] = []
    paths.append(plot_lineage(tables["lineage"]))
    paths.append(plot_causal_timeline())
    paths.append(plot_breadth(tables["breadth"]))
    paths.append(plot_frequency(tables["frequency"]))
    equity, drawdown = plot_equity_and_drawdown()
    paths.extend([equity, drawdown])
    paths.append(plot_calendar(tables["calendar"]))
    paths.append(plot_rolling_excess())
    paths.append(plot_family_contribution(tables["family_contribution"]))
    paths.append(plot_rank_contribution(tables["rank_contribution"]))
    if args.skip_random_figure:
        random_path = FIGURES / "FIGURE_11_RANDOM_SELECTION_DISTRIBUTION.png"
        if not random_path.exists():
            raise FileNotFoundError("--skip-random-figure requires an existing exact Figure 11")
        paths.append(random_path)
    else:
        paths.append(plot_randomisation(_exact_randomisation_arrays()))
    paths.append(plot_spell_concentration(tables["holding_spells"]))
    paths.append(plot_regime_timeline())
    paths.append(plot_dynamic_static(tables["dynamic_policy"], tables["common"]))
    paths.append(plot_wrapper_frontier(tables["wrapper"]))
    paths.append(plot_relative_regret())

    figure_manifest = build_figure_manifest(paths)
    write_csv(PAPER_ROOT / "UKACTIVE_PAPER_FIGURE_MANIFEST.csv", figure_manifest)
    evidence = build_evidence_matrix(tables)
    write_csv(PAPER_ROOT / "UKACTIVE_PAPER_SOURCE_EVIDENCE_MATRIX.csv", evidence)
    source_audit = canonical_source_audit()
    write_json(QA / "UKACTIVE_PAPER_CANONICAL_SOURCE_AUDIT.json", source_audit)

    checks = {
        "status": "PASS",
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "manifest_commit_is_ancestor": True,
        "historical_cutoff": CUTOFF.date().isoformat(),
        "table_count": len(tables),
        "figure_count": len(paths),
        "evidence_claim_count": len(evidence),
        "all_figure_files_exist": all(path.is_file() for path in paths),
        "all_table_files_exist": all((TABLES / name).is_file() for name in table_names.values()),
        "randomisation_exact_reproduction": not args.skip_random_figure,
        "unresolved_source_conflicts": ["A4F_LONGER_CORE_ONLY_RESULTS_WINDOW_AND_METRICS"],
        "prohibited_actions": {"new_model_search": False, "post_cutoff_data": False, "canonical_artifact_modification": False},
    }
    write_json(QA / "UKACTIVE_PAPER_ASSET_BUILD_CHECKS.json", checks)
    print(json.dumps(checks, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
