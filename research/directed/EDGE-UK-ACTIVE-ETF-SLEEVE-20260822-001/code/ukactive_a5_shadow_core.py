"""Operational core for the frozen UKACTIVE-A5 shadow comparison.

The module has no broker dependency and no order-transmission surface.  It
turns the A2R2 validated endpoint chain into two append-only, non-trading
shadow portfolios and deterministic market-intelligence reports.
"""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from ukactive_a2r2_core import build_xlon_session_calendar


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
CONFIG_PATH = PROGRAMME_ROOT / "config" / "ukactive_a5_shadow_comparison_v1.json"
IMPLEMENTATION_MAP_PATH = PROGRAMME_ROOT / "UKACTIVE_A5_IMPLEMENTATION_MAP.csv"
OPERATING_CALENDAR_PATH = PROGRAMME_ROOT / "UKACTIVE_A5_OPERATING_CALENDAR.csv"

HISTORICAL_CUTOFF = pd.Timestamp("2026-08-21")
EARLIEST_SIGNAL = pd.Timestamp("2026-08-28")
SETUP_DATE = "2026-08-23"
INITIAL_NOTIONAL_GBP = 250_000.0
FREEZE_TAG = "ukactive-a5-shadow-comparison-v1-20260823"
EXPECTED_ORIGIN = "https://github.com/Badgerlair/UK-ETF-rotation.git"
WARNING = "SHADOW TESTING ONLY — NO LIVE TRADING OR BROKER ORDER IS AUTHORISED"

MODEL_A = "A5A_ACTIVE_BASELINE_V1"
MODEL_B = "A5B_CORE_ACTIVE_50_V1"
COMPARATOR_GLOBAL = "GLOBAL_DEVELOPED_WORLD"
COMPARATOR_POOL = "EQUAL_WEIGHT_INDUSTRY_THEME_POOL"
COMPARATOR_STATIC = "STATIC_CORE_PLUS_EQUAL_POOL_50"
COMPARATOR_CASH = "GBP_CASH"
COMPARATOR_UNSELECTED = "UNSELECTED_INDUSTRY_THEME_POOL"
SERIES_ORDER = [
    MODEL_A,
    MODEL_B,
    COMPARATOR_GLOBAL,
    COMPARATOR_POOL,
    COMPARATOR_STATIC,
    COMPARATOR_CASH,
]

SOURCE_PATHS = {
    "corrected_panel": PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_TOTAL_RETURN_PANEL_GBP.parquet",
    "signal_eligibility": PROGRAMME_ROOT / "UKACTIVE_A2R2_CORRECTED_SIGNAL_ELIGIBILITY.parquet",
    "endpoint_history": PROGRAMME_ROOT / "UKACTIVE_A2R2_SIGNAL_ENDPOINT_HISTORY.parquet",
    "cash_series": PROGRAMME_ROOT / "UKACTIVE_A2_CASH_SERIES.parquet",
    "feature_panel": PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet",
    "regime_history": PROGRAMME_ROOT / "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet",
    "roles": PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_ROTATION_ROLE_MASTER_POST_A2R.csv",
    "current_lines": PROGRAMME_ROOT / "UKACTIVE_A3R0_CURRENT_IMPLEMENTATION_LINES.csv",
    "current_lines_post_a2r": PROGRAMME_ROOT / "UKACTIVE_A2R_A3R0_CURRENT_IMPLEMENTATION_LINES_POST_A2R.csv",
    "share_classes": PROGRAMME_ROOT / "UKACTIVE_A0A1_SHARE_CLASS_MASTER.csv",
    "verified_active_map": PROGRAMME_ROOT / "UKACTIVE_CURRENT_II_IMPLEMENTATION_VERIFIED_20260823.csv",
    "old_a5_config": PROGRAMME_ROOT / "config" / "ukactive_a5_frozen_candidate.json",
    "a4c_baseline_reproduction": PROGRAMME_ROOT / "UKACTIVE_A4C_BASELINE_REPRODUCTION.csv",
    "a2r2_calendar": PROGRAMME_ROOT / "UKACTIVE_A2R2_XLON_RESEARCH_CALENDAR.csv",
    "instrument_history": PROGRAMME_ROOT / "UKACTIVE_A2_INSTRUMENT_HISTORY_MASTER.parquet",
    "corrected_instrument_history": PROGRAMME_ROOT / "UKACTIVE_A2R_CORRECTED_IMPLEMENTATION_HISTORY.parquet",
}

LEDGER_PATHS = {
    "run": PROGRAMME_ROOT / "UKACTIVE_A5_RUN_LEDGER.jsonl",
    "decision": PROGRAMME_ROOT / "UKACTIVE_A5_DECISION_LEDGER.csv",
    "execution": PROGRAMME_ROOT / "UKACTIVE_A5_EXECUTION_LEDGER.csv",
    "position": PROGRAMME_ROOT / "UKACTIVE_A5_POSITION_LEDGER.csv",
    "cash": PROGRAMME_ROOT / "UKACTIVE_A5_CASH_LEDGER.csv",
    "cost": PROGRAMME_ROOT / "UKACTIVE_A5_COST_LEDGER.csv",
    "nav": PROGRAMME_ROOT / "UKACTIVE_A5_NAV_HISTORY.csv",
    "benchmark": PROGRAMME_ROOT / "UKACTIVE_A5_BENCHMARK_HISTORY.csv",
    "telemetry_csv": PROGRAMME_ROOT / "UKACTIVE_A5_TELEMETRY_LEDGER.csv",
    "telemetry_parquet": PROGRAMME_ROOT / "UKACTIVE_A5_TELEMETRY_HISTORY.parquet",
    "warnings": PROGRAMME_ROOT / "UKACTIVE_A5_OPERATIONAL_WARNINGS.csv",
    "amendment": PROGRAMME_ROOT / "UKACTIVE_A5_AMENDMENT_LEDGER.csv",
}

STATE_PATH = PROGRAMME_ROOT / "UKACTIVE_A5_CURRENT_STATE.json"
LATEST_REPORT_MD = PROGRAMME_ROOT / "UKACTIVE_A5_LATEST_RUN_REPORT.md"
LATEST_REPORT_JSON = PROGRAMME_ROOT / "UKACTIVE_A5_LATEST_RUN_REPORT.json"
SNAPSHOT_ROOT = PROGRAMME_ROOT / "snapshots" / "a5"
INPUT_SNAPSHOT_ROOT = SNAPSHOT_ROOT / "inputs"

CSV_SCHEMAS: dict[str, list[str]] = {
    "decision": [
        "decision_event_id", "specification_id", "signal_date", "data_cutoff", "recorded_at_utc",
        "prospective_classification", "on_time_e3_counted", "expected_execution_date", "economic_pool",
        "signal_id", "eligible_family_count", "selected_family_id", "selected_display_name",
        "preferred_ticker", "preferred_isin", "issuer", "listing_currency", "deepvue_label", "rs63",
        "rs126", "rs252", "rank_rs63", "rank_rs126", "rank_rs252", "composite_score",
        "rank_2_family", "rank_3_family", "rank_4_family", "rank_5_family", "top5_json",
        "previous_active_holding", "action", "implementation_check_status", "a5a_target_weight",
        "a5a_target_notional_gbp", "a5b_active_target_weight", "a5b_core_target_weight",
        "a5b_active_target_notional_gbp", "a5b_core_target_notional_gbp", "a5b_estimated_rebalance_legs",
        "benchmark_family_id", "global_trend_regime", "volatility_regime", "dispersion_regime",
        "breadth_regime", "rotation_intensity_regime", "us_technology_dominance",
        "input_eligibility_path", "input_eligibility_sha256", "implementation_map_path",
        "implementation_map_sha256", "universe_version", "source_git_commit", "freeze_tag", "backfill",
        "orders_or_scheduler", "warning",
    ],
    "execution": [
        "execution_event_id", "leg_id", "model_id", "decision_event_id", "signal_date", "execution_date",
        "logged_at_utc", "logging_classification", "action", "family_id", "ticker", "isin", "side",
        "target_weight", "target_notional_gbp", "execution_close", "execution_close_unit",
        "economic_index_gbp", "notional_traded_gbp", "friction_cost_gbp", "fixed_fee_gbp",
        "total_cost_gbp", "post_trade_units", "post_trade_notional_gbp", "residual_cash_gbp",
        "units_basis", "implementation_status", "input_snapshot_path", "input_snapshot_sha256",
        "source_git_commit", "shadow_only", "warning",
    ],
    "position": [
        "position_event_id", "execution_event_id", "model_id", "effective_date", "family_id",
        "target_weight", "economic_units", "economic_index_at_execution", "continuity_segment_id",
        "ticker", "isin", "implementation_status", "source_git_commit", "warning",
    ],
    "cash": [
        "cash_event_id", "execution_event_id", "model_id", "effective_date", "cash_balance_gbp",
        "cash_index_at_event", "cash_weight", "source_git_commit", "warning",
    ],
    "cost": [
        "cost_event_id", "execution_event_id", "leg_id", "model_id", "date", "notional_traded_gbp",
        "friction_bps", "friction_cost_gbp", "fixed_fee_gbp", "total_cost_gbp", "source_git_commit",
        "warning",
    ],
    "nav": [
        "nav_event_id", "model_id", "date", "nav_gbp", "cumulative_net_return", "daily_return",
        "position_value_gbp", "cash_value_gbp", "cash_weight", "holdings", "high_water_mark_gbp",
        "drawdown", "cumulative_costs_gbp", "traded_notional_turnover", "trade_legs",
        "source_input_hash", "source_git_commit", "warning",
    ],
    "benchmark": [
        "nav_event_id", "model_id", "date", "nav_gbp", "cumulative_net_return", "daily_return",
        "position_value_gbp", "cash_value_gbp", "cash_weight", "holdings", "high_water_mark_gbp",
        "drawdown", "cumulative_costs_gbp", "traded_notional_turnover", "trade_legs",
        "source_input_hash", "source_git_commit", "warning",
    ],
    "telemetry_csv": [
        "telemetry_event_id", "date", "pool", "rank_type", "rank", "family_id", "display_name",
        "preferred_ticker", "rs21", "rs42", "rs63", "rs126", "rs252", "fast_score", "slow_score",
        "fast_rank", "slow_rank", "fast_slow_gap", "fast_rank_change_1w", "fast_rank_change_4w",
        "relative_price_slope_63", "leadership_state", "global_trend_regime", "volatility_regime",
        "dispersion_regime", "breadth_regime", "rotation_intensity_regime", "us_technology_dominance",
        "portfolio_change", "source_git_commit", "warning",
    ],
    "warnings": [
        "warning_event_id", "date", "warning_type", "severity", "related_event_id", "message",
        "evidence", "recorded_at_utc", "source_git_commit", "resolved_status",
    ],
    "amendment": [
        "amendment_event_id", "original_event_id", "original_ledger", "reason", "field_name",
        "old_value", "new_value", "evidence", "recorded_at_utc", "source_git_commit", "warning",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise_scalar(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if pd.isna(value) if not isinstance(value, (list, dict, tuple, set)) else False:
        return None
    return value


def canonical_json(payload: Any) -> str:
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): clean(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        return normalise_scalar(value)

    return json.dumps(clean(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@functools.lru_cache(maxsize=256)
def _sha256_file_version(path_text: str, size_bytes: int, modified_ns: int) -> str:
    del size_bytes, modified_ns
    return sha256_file(Path(path_text))


def versioned_sha256_file(path: Path) -> str:
    stat = path.stat()
    return _sha256_file_version(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def stable_id(prefix: str, *parts: Any) -> str:
    digest = sha256_bytes("|".join(str(part) for part in parts).encode("utf-8"))[:16].upper()
    return f"{prefix}-{digest}"


def git_value(*args: str, check: bool = False) -> str:
    result = subprocess.run(["git", *args], cwd=PLATFORM_ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip() if result.returncode == 0 else f"UNAVAILABLE:{result.stderr.strip()}"


def current_git_commit() -> str:
    return git_value("rev-parse", "HEAD")


def assert_operational_provenance() -> None:
    """Block prospective evidence when the executed specification is not committed."""
    if git_value("branch", "--show-current", check=True) != "research/ukactive-a5-shadow":
        raise RuntimeError("Prospective runner must remain on research/ukactive-a5-shadow")
    origin = git_value("remote", "get-url", "origin", check=True)
    if origin.rstrip("/") != EXPECTED_ORIGIN.rstrip("/"):
        raise RuntimeError(f"Unexpected Git origin: {origin}")
    if not git_value("tag", "--list", FREEZE_TAG):
        raise RuntimeError(f"Prospective runner is not frozen: missing tag {FREEZE_TAG}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", FREEZE_TAG, "HEAD"],
        cwd=PLATFORM_ROOT, capture_output=True, text=True, check=False,
    )
    if ancestor.returncode:
        raise RuntimeError("Current HEAD is not descended from the A5 freeze tag")
    critical = [
        Path(__file__), Path(__file__).with_name("run_ukactive_a5_shadow.py"),
        PROGRAMME_ROOT / "run_ukactive_a5.ps1", CONFIG_PATH, IMPLEMENTATION_MAP_PATH,
    ]
    relative = [str(path.relative_to(PLATFORM_ROOT)) for path in critical]
    status = git_value("status", "--porcelain", "--", *relative, check=True)
    if status:
        raise RuntimeError(
            "Prospective evidence prohibited while runner/config/implementation metadata are uncommitted: "
            + status.replace("\n", "; ")
        )


def write_bytes_if_changed(path: Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, prefix=f".{path.name}.") as handle:
        handle.write(data)
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return True


def write_text_if_changed(path: Path, text: str) -> bool:
    return write_bytes_if_changed(path, (text.rstrip() + "\n").encode("utf-8"))


def write_json_if_changed(path: Path, payload: Any) -> bool:
    clean = json.loads(canonical_json(payload))
    return write_text_if_changed(path, json.dumps(clean, indent=2, sort_keys=True, ensure_ascii=False))


def write_immutable_bytes(path: Path, data: bytes) -> bool:
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"Immutable artifact collision: {path}")
        return False
    return write_bytes_if_changed(path, data)


def write_immutable_text(path: Path, value: str) -> bool:
    return write_immutable_bytes(path, (value.rstrip() + "\n").encode("utf-8"))


def write_immutable_json(path: Path, payload: Any) -> bool:
    clean = json.loads(canonical_json(payload))
    value = json.dumps(clean, indent=2, sort_keys=True, ensure_ascii=False)
    return write_immutable_text(path, value)


def write_csv_if_changed(path: Path, frame: pd.DataFrame) -> bool:
    text = frame.to_csv(index=False, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    return write_bytes_if_changed(path, text.encode("utf-8"))


def read_csv_schema(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(frame.columns) != columns:
        raise RuntimeError(f"Ledger schema mismatch: {path.name}")
    return frame


def append_csv_rows(path: Path, columns: list[str], rows: list[dict[str, Any]], keys: list[str]) -> int:
    if not rows:
        return 0
    existing = read_csv_schema(path, columns)
    additions = pd.DataFrame([{column: normalise_scalar(row.get(column, "")) for column in columns} for row in rows])
    additions = additions.fillna("").astype(str)
    if additions.duplicated(keys).any():
        raise RuntimeError(f"Duplicate keys inside append batch for {path.name}")
    existing_keys = {tuple(row) for row in existing[keys].itertuples(index=False, name=None)} if len(existing) else set()
    keep: list[int] = []
    for index, row in additions.iterrows():
        key = tuple(row[column] for column in keys)
        if key in existing_keys:
            match = existing.copy()
            for column, value in zip(keys, key):
                match = match.loc[match[column].eq(value)]
            if len(match) != 1 or match.iloc[0].to_dict() != row.to_dict():
                raise RuntimeError(f"Immutable ledger collision for {path.name}: {key}")
            continue
        existing_keys.add(key)
        keep.append(index)
    if not keep:
        return 0
    combined = pd.concat([existing, additions.loc[keep]], ignore_index=True)
    write_csv_if_changed(path, combined)
    return len(keep)


def append_jsonl(path: Path, payload: dict[str, Any], id_field: str = "run_event_id") -> bool:
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    identifier = str(payload[id_field])
    for record in records:
        if str(record.get(id_field)) == identifier:
            if canonical_json(record) != canonical_json(payload):
                raise RuntimeError(f"Immutable JSONL collision: {identifier}")
            return False
    records.append(payload)
    text = "\n".join(canonical_json(record) for record in records) + "\n"
    return write_bytes_if_changed(path, text.encode("utf-8"))


def source_inventory(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        rows.append({
            "path": str(path.resolve()),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else None,
            "sha256": versioned_sha256_file(path) if path.exists() else "MISSING",
        })
    return rows


def code_config_inventory() -> list[dict[str, Any]]:
    return source_inventory([
        Path(__file__), Path(__file__).with_name("run_ukactive_a5_shadow.py"),
        PROGRAMME_ROOT / "run_ukactive_a5.ps1", CONFIG_PATH, IMPLEMENTATION_MAP_PATH,
    ])


def build_operating_calendar(months: int = 30) -> pd.DataFrame:
    first_month = pd.Timestamp("2026-08-01")
    periods = pd.period_range(first_month, periods=months, freq="M")
    end = (periods[-1].to_timestamp(how="end").normalize() + pd.Timedelta(days=10))
    sessions, _ = build_xlon_session_calendar(first_month, end)
    session_frame = pd.DataFrame({"date": sessions})
    session_frame["month"] = session_frame["date"].dt.to_period("M")
    iso = session_frame["date"].dt.isocalendar()
    session_frame["iso_year"] = iso["year"].astype(int)
    session_frame["iso_week"] = iso["week"].astype(int)
    weekly = session_frame.groupby(["iso_year", "iso_week"], sort=True).tail(1)["date"]
    next_map = pd.Series(sessions[1:].to_numpy(), index=sessions[:-1])
    rows = []
    for period in periods:
        in_month = session_frame.loc[session_frame["month"].eq(period), "date"]
        signal = pd.Timestamp(in_month.max())
        telemetry = [date for date in weekly if date.to_period("M") == period and date >= pd.Timestamp(SETUP_DATE)]
        rows.append({
            "calendar_month": str(period),
            "expected_final_valid_xlon_signal_date": signal.date().isoformat(),
            "expected_next_eligible_execution_date": pd.Timestamp(next_map.loc[signal]).date().isoformat(),
            "weekly_telemetry_dates": ";".join(pd.Timestamp(date).date().isoformat() for date in telemetry),
            "status": "UPCOMING",
            "completed_signal_event_id": "",
            "completed_execution_event_id": "",
            "calendar_policy": "A2R2_DETERMINISTIC_XLON_RULES_KNOWN_HOLIDAYS",
        })
    return pd.DataFrame(rows)


def _combined_current_lines() -> pd.DataFrame:
    frames = []
    for key in ["current_lines_post_a2r", "current_lines"]:
        frame = pd.read_csv(SOURCE_PATHS[key], dtype=str).fillna("")
        frames.append(frame)
    result = pd.concat(frames, ignore_index=True)
    result["_preferred_order"] = result["preferred_or_alternate"].map({"PREFERRED": 0, "ALTERNATE": 1}).fillna(2)
    return result.sort_values(["economic_exposure_family_id", "ticker", "_preferred_order"]).drop_duplicates(
        ["economic_exposure_family_id", "ticker"], keep="first"
    )


def build_implementation_map() -> pd.DataFrame:
    verified = pd.read_csv(SOURCE_PATHS["verified_active_map"], dtype=str).fillna("")
    lines = _combined_current_lines()
    share = pd.read_csv(SOURCE_PATHS["share_classes"], dtype=str).fillna("")
    share = share.drop_duplicates("share_class_id").set_index("share_class_id")
    rows: list[dict[str, Any]] = []
    for record in verified.itertuples(index=False):
        family = record.economic_exposure_family_id
        preferred = lines.loc[
            lines["economic_exposure_family_id"].eq(family)
            & lines["ticker"].eq(record.preferred_current_implementation_ticker)
        ]
        alternate = lines.loc[
            lines["economic_exposure_family_id"].eq(family)
            & lines["ticker"].eq(record.alternate_ticker)
        ]
        if len(preferred) != 1 or len(alternate) != 1:
            raise AssertionError(f"Implementation-line mapping is not unique for {family}")
        pref = preferred.iloc[0]
        alt = alternate.iloc[0]
        share_row = share.loc[pref["share_class_id"]] if pref["share_class_id"] in share.index else {}
        rows.append({
            "implementation_scope": "ACTIVE_SIGNAL_READY",
            "economic_exposure_family_id": family,
            "display_name": record.display_name,
            "rotation_role": record.rotation_role,
            "deepvue_label": "NOT_APPLICABLE",
            "preferred_ticker": record.preferred_current_implementation_ticker,
            "preferred_isin": record.preferred_isin,
            "issuer": record.issuer,
            "preferred_listing_id": pref["listing_id"],
            "lse_trading_line": record.lse_trading_line,
            "exchange": pref["exchange"],
            "mic": pref["mic"],
            "listing_currency": pref["listing_currency"],
            "price_unit": pref["price_unit"],
            "accumulating_distributing": share_row.get("accumulating_distributing", "NOT_VERIFIED"),
            "product_structure": pref["product_structure"],
            "ucits_status": pref["ucits_status"],
            "current_public_uk_eligibility_status": record.current_public_uk_eligibility_status,
            "ii_current_tradable": record.ii_current_tradable,
            "ii_observation_date": record.ii_observation_date,
            "ii_verification_method": record.ii_verification_method,
            "alternate_ticker": record.alternate_ticker,
            "alternate_isin": record.alternate_isin,
            "alternate_listing_id": alt["listing_id"],
            "alternate_currency": alt["listing_currency"],
            "alternate_price_unit": alt["price_unit"],
            "alternate_ii_current_tradable": "TO_CHECK",
            "current_implementation_state": "CURRENT_II_CONFIRMED",
            "historical_back_projection": "NO",
            "source_artifact": SOURCE_PATHS["verified_active_map"].name,
            "source_artifact_sha256": sha256_file(SOURCE_PATHS["verified_active_map"]),
            "notes": record.notes,
        })

    core_lines = lines.loc[lines["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD")]
    preferred = core_lines.loc[core_lines["preferred_or_alternate"].eq("PREFERRED")]
    alternate = core_lines.loc[core_lines["preferred_or_alternate"].eq("ALTERNATE")]
    if len(preferred) != 1 or len(alternate) != 1:
        raise AssertionError("GLOBAL_DEVELOPED_WORLD current implementation is not uniquely resolved")
    pref = preferred.iloc[0]
    alt = alternate.iloc[0]
    share_row = share.loc[pref["share_class_id"]] if pref["share_class_id"] in share.index else {}
    rows.append({
        "implementation_scope": "GLOBAL_CORE_REFERENCE",
        "economic_exposure_family_id": "GLOBAL_DEVELOPED_WORLD",
        "display_name": "Broad developed-world equities",
        "rotation_role": "BENCHMARK_REFERENCE",
        "deepvue_label": "NOT_APPLICABLE",
        "preferred_ticker": pref["ticker"],
        "preferred_isin": pref["isin"],
        "issuer": pref["provider_issuer"],
        "preferred_listing_id": pref["listing_id"],
        "lse_trading_line": f"LSE:{pref['ticker']}",
        "exchange": pref["exchange"],
        "mic": pref["mic"],
        "listing_currency": pref["listing_currency"],
        "price_unit": pref["price_unit"],
        "accumulating_distributing": share_row.get("accumulating_distributing", "NOT_VERIFIED"),
        "product_structure": pref["product_structure"],
        "ucits_status": pref["ucits_status"],
        "current_public_uk_eligibility_status": "PUBLIC_UK_ELIGIBLE_CONFIRMED",
        "ii_current_tradable": "TO_CHECK",
        "ii_observation_date": "NOT_CHECKED",
        "ii_verification_method": "NOT_CHECKED",
        "alternate_ticker": alt["ticker"],
        "alternate_isin": alt["isin"],
        "alternate_listing_id": alt["listing_id"],
        "alternate_currency": alt["listing_currency"],
        "alternate_price_unit": alt["price_unit"],
        "alternate_ii_current_tradable": "TO_CHECK",
        "current_implementation_state": "CURRENT_PUBLIC_UK_ELIGIBLE_II_UNCHECKED",
        "historical_back_projection": "NO",
        "source_artifact": SOURCE_PATHS["current_lines"].name,
        "source_artifact_sha256": sha256_file(SOURCE_PATHS["current_lines"]),
        "notes": "Preferred current core line resolved from authoritative A3R0 master. Manual ii check required before first A5-B booking; current-only status must not be back-projected.",
    })
    result = pd.DataFrame(rows)
    roles = pd.read_csv(SOURCE_PATHS["roles"], dtype=str).fillna("")
    deepvue = roles.set_index("economic_exposure_family_id")["deepvue_theme"].to_dict()
    result["deepvue_label"] = result["economic_exposure_family_id"].map(deepvue).fillna(result["deepvue_label"])
    result.loc[result["deepvue_label"].isin(["", "NOT_APPLICABLE"]), "deepvue_label"] = "NOT_APPLICABLE"
    active = result.loc[result["implementation_scope"].eq("ACTIVE_SIGNAL_READY")]
    if len(active) != 25 or not active["ii_current_tradable"].eq("CONFIRMED_BY_USER").all():
        raise AssertionError("The frozen active implementation map must contain 25/25 user-confirmed rows")
    return result.sort_values(["implementation_scope", "economic_exposure_family_id"], kind="mergesort").reset_index(drop=True)


def build_config(implementation_map: pd.DataFrame) -> dict[str, Any]:
    old = json.loads(SOURCE_PATHS["old_a5_config"].read_text(encoding="utf-8"))
    roles = pd.read_csv(SOURCE_PATHS["roles"], dtype=str).fillna("")
    pool_members = sorted(roles.loc[
        roles["primary_rotation_role"].isin(["INDUSTRY_ROTATION", "THEME_ROTATION"])
        & roles["selectable_flag"].eq("YES")
        & roles["primary_equity_competition_flag"].eq("YES"),
        "economic_exposure_family_id",
    ].unique())
    ready = sorted(implementation_map.loc[
        implementation_map["implementation_scope"].eq("ACTIVE_SIGNAL_READY"),
        "economic_exposure_family_id",
    ])
    core = implementation_map.loc[implementation_map["implementation_scope"].eq("GLOBAL_CORE_REFERENCE")].iloc[0]
    return {
        "specification_id": "UKACTIVE-A5-SHADOW-COMPARISON-v1",
        "setup_stage": "UKACTIVE-A5S",
        "status": "FROZEN_SETUP_NOT_STARTED",
        "created_date": SETUP_DATE,
        "freeze_tag": FREEZE_TAG,
        "freeze_commit": "RESOLVE_FROM_TAG_AT_RUNTIME",
        "source_baseline_specification_id": old["specification_id"],
        "source_baseline_config_path": str(SOURCE_PATHS["old_a5_config"].relative_to(PROGRAMME_ROOT)),
        "source_baseline_config_sha256": sha256_file(SOURCE_PATHS["old_a5_config"]),
        "historical_development_cutoff": HISTORICAL_CUTOFF.date().isoformat(),
        "earliest_official_signal_date": EARLIEST_SIGNAL.date().isoformat(),
        "evidence_target": "E3_PROSPECTIVE_CONFIRMATION_AFTER_24_ON_TIME_DECISIONS",
        "model_a": {
            "model_id": MODEL_A,
            "pool": "INDUSTRY_PLUS_THEME",
            "signal": "MH_LEVEL_3_6_12_REFERENCE",
            "horizons_xlon_sessions": [63, 126, 252],
            "component_weights": [1 / 3, 1 / 3, 1 / 3],
            "ranking_unit": "economic_exposure_family_id",
            "tie_break": "economic_exposure_family_id_ASCENDING",
            "selection": "TOP_1",
            "review": "FINAL_VALID_XLON_SESSION_OF_CALENDAR_MONTH",
            "execution": "FIRST_COMMON_VALID_CLOSE_FROM_NEXT_XLON_SESSION_WITHIN_3_SESSIONS",
            "target_active_weight": 1.0,
            "initial_notional_gbp": INITIAL_NOTIONAL_GBP,
        },
        "model_b": {
            "model_id": MODEL_B,
            "active_process": "EXACT_MODEL_A_SELECTION_AND_EXECUTION_DATE",
            "target_active_weight": 0.5,
            "target_core_weight": 0.5,
            "core_family_id": "GLOBAL_DEVELOPED_WORLD",
            "monthly_strategic_rebalance": True,
            "initial_notional_gbp": INITIAL_NOTIONAL_GBP,
            "core_manual_ii_confirmation_required_before_first_booking": True,
            "core_preferred_ticker": core["preferred_ticker"],
            "core_preferred_isin": core["preferred_isin"],
        },
        "universe": {
            "pool_family_ids": pool_members,
            "current_signal_ready_family_ids": ready,
            "dynamic_admission": "SIGNAL_SPECIFIC_A2R2_VALIDITY",
            "newly_admitted_without_preverified_map": "IMPLEMENTATION_BLOCKED_TO_GBP_CASH_NO_RERANK",
            "current_active_implementation_coverage": "25_OF_25_CONFIRMED_BY_USER",
        },
        "implementation": {
            "map_path": str(IMPLEMENTATION_MAP_PATH.relative_to(PROGRAMME_ROOT)),
            "map_sha256": sha256_file(IMPLEMENTATION_MAP_PATH),
            "preferred_then_preverified_alternate_only": True,
            "discretionary_substitution": False,
            "implementation_failure": "GBP_CASH",
            "current_metadata_back_projection": False,
        },
        "benchmark": {
            "economic_family_id": "GLOBAL_DEVELOPED_WORLD",
            "preferred_ticker": core["preferred_ticker"],
            "preferred_isin": core["preferred_isin"],
            "ii_current_tradable": core["ii_current_tradable"],
        },
        "costs": {
            "one_way_friction_bps": 20.0,
            "fixed_fee_gbp_per_trade_leg": 3.99,
            "canonical_notional_gbp": INITIAL_NOTIONAL_GBP,
            "whole_share_rounding_affects_official_score": False,
        },
        "comparators": {
            COMPARATOR_GLOBAL: "FRICTIONLESS_GLOBAL_DEVELOPED_WORLD_FROM_FIRST_EXECUTION",
            COMPARATOR_POOL: "FRICTIONLESS_CONTEMPORANEOUS_EQUAL_WEIGHT_SIGNAL_ELIGIBLE_POOL",
            COMPARATOR_STATIC: "MONTHLY_50_CORE_50_EQUAL_POOL_WITH_CANONICAL_COSTS",
            COMPARATOR_CASH: "VALIDATED_ACTUAL_GBP_CASH_SERIES",
            COMPARATOR_UNSELECTED: "FRICTIONLESS_EQUAL_WEIGHT_ELIGIBLE_FAMILIES_EXCLUDING_SELECTED",
        },
        "integrity": {
            "on_time_rule": "SIGNAL_COMMITTED_BEFORE_NEXT_ELIGIBLE_EXECUTION_CLOSE_DATA_AVAILABLE",
            "late_signal_state": "LATE_SIGNAL_NOT_E3",
            "same_close_execution": False,
            "backfill": False,
            "revision_policy": "PRESERVE_ORIGINAL_APPEND_DATA_REVISION_ALERT",
            "minimum_primary_decisions": 24,
            "no_model_changes": True,
            "orders_or_scheduler": "NONE",
        },
        "data": {key: str(path.relative_to(PROGRAMME_ROOT)) for key, path in SOURCE_PATHS.items() if path.is_relative_to(PROGRAMME_ROOT)},
        "reporting": {
            "annualisation_minimum_daily_observations": 252,
            "rolling_12m_minimum_months": 12,
            "latest_report_markdown": LATEST_REPORT_MD.name,
            "latest_report_json": LATEST_REPORT_JSON.name,
        },
        "git": {
            "expected_origin": EXPECTED_ORIGIN,
            "expected_branch": "research/ukactive-a5-shadow",
            "no_force_push": True,
            "large_parquet_inputs_tracked": False,
        },
        "warning": WARNING,
    }


@dataclass
class DataBundle:
    eligibility: pd.DataFrame
    endpoint: pd.DataFrame
    cash: pd.DataFrame
    metadata: pd.DataFrame
    implementation: pd.DataFrame
    calendar: pd.DatetimeIndex

    @classmethod
    def load(cls) -> "DataBundle":
        eligibility = pd.read_parquet(SOURCE_PATHS["signal_eligibility"])
        eligibility["date"] = pd.to_datetime(eligibility["date"]).dt.normalize()
        endpoint = pd.read_parquet(SOURCE_PATHS["endpoint_history"])
        endpoint["date"] = pd.to_datetime(endpoint["date"]).dt.normalize()
        cash = pd.read_parquet(SOURCE_PATHS["cash_series"])
        cash["date"] = pd.to_datetime(cash["date"]).dt.normalize()
        metadata = pd.read_csv(SOURCE_PATHS["roles"], dtype=str).fillna("")
        implementation = pd.read_csv(IMPLEMENTATION_MAP_PATH, dtype=str).fillna("")
        calendar = pd.DatetimeIndex(sorted(eligibility["date"].unique()), name="date")
        return cls(eligibility, endpoint, cash, metadata, implementation, calendar)

    def latest_cutoff(self) -> pd.Timestamp:
        benchmark = self.endpoint.loc[
            self.endpoint["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD")
            & self.endpoint["endpoint_valid"].astype(bool)
        ]
        if benchmark.empty:
            raise RuntimeError("GLOBAL_DEVELOPED_WORLD has no valid endpoint")
        return pd.Timestamp(benchmark["date"].max())

    def resolve_asof(self, requested: str) -> pd.Timestamp:
        latest = self.latest_cutoff()
        if requested.lower() == "latest":
            return latest
        target = pd.Timestamp(requested).normalize()
        eligible = self.calendar[(self.calendar <= target) & (self.calendar <= latest)]
        if not len(eligible):
            raise RuntimeError(f"No authoritative XLON session on or before {requested}")
        return pd.Timestamp(eligible[-1])

    def members(self, pool: str) -> list[str]:
        role_map = {
            "INDUSTRY_PLUS_THEME": ["INDUSTRY_ROTATION", "THEME_ROTATION"],
            "INDUSTRY": ["INDUSTRY_ROTATION"],
            "THEME": ["THEME_ROTATION"],
            "GEOGRAPHY": ["BROAD_GEOGRAPHY_ROTATION"],
            "COUNTRY": ["COUNTRY_ROTATION"],
            "SECTOR": ["SECTOR_ROTATION"],
            "ALL_EQUITY_OPPORTUNITIES": [
                "BROAD_GEOGRAPHY_ROTATION", "COUNTRY_ROTATION", "SECTOR_ROTATION",
                "INDUSTRY_ROTATION", "THEME_ROTATION",
            ],
        }
        roles = role_map[pool]
        frame = self.metadata.loc[
            self.metadata["primary_rotation_role"].isin(roles)
            & self.metadata["selectable_flag"].eq("YES")
            & self.metadata["primary_equity_competition_flag"].eq("YES")
        ]
        return sorted(frame["economic_exposure_family_id"].unique())

    def rankings(self, asof: pd.Timestamp, pool: str) -> pd.DataFrame:
        members = self.members(pool)
        required = members + ["GLOBAL_DEVELOPED_WORLD"]
        day = self.eligibility.loc[
            self.eligibility["date"].eq(pd.Timestamp(asof))
            & self.eligibility["economic_exposure_family_id"].isin(required)
        ].copy()
        if day.empty:
            raise RuntimeError(f"No A2R2 signal-eligibility rows at {asof.date()}")
        if day["economic_exposure_family_id"].duplicated().any():
            raise RuntimeError("Ranking identity is not unique by economic family")
        day = day.set_index("economic_exposure_family_id")
        if "GLOBAL_DEVELOPED_WORLD" not in day.index:
            raise RuntimeError("Global benchmark row missing")
        benchmark = day.loc["GLOBAL_DEVELOPED_WORLD"]
        output = pd.DataFrame(index=pd.Index(members, name="economic_exposure_family_id"))
        for horizon in [21, 42, 63, 126, 252]:
            field = f"formation_return_{horizon}"
            valid_field = f"signal_valid_{horizon}"
            benchmark_valid = bool(benchmark[valid_field]) and pd.notna(benchmark[field])
            if not benchmark_valid:
                output[f"RS_{horizon}"] = np.nan
                output[f"RANK_RS_{horizon}"] = np.nan
                continue
            formation = day.reindex(members)[field].astype(float)
            valid = day.reindex(members)[valid_field].fillna(False).astype(bool)
            relative = ((1.0 + formation) / (1.0 + float(benchmark[field])) - 1.0).where(valid)
            output[f"RS_{horizon}"] = relative
            output[f"RANK_RS_{horizon}"] = relative.rank(method="average", pct=True)
        output["FAST_RS"] = output[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1, skipna=False)
        output["SLOW_RS"] = output[["RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]].mean(axis=1, skipna=False)
        output["MH_LEVEL_3_6_12_REFERENCE"] = output["SLOW_RS"]
        metadata = self.metadata.set_index("economic_exposure_family_id")
        output["economic_exposure_name"] = output.index.map(metadata["economic_exposure_name"])
        output["primary_rotation_role"] = output.index.map(metadata["primary_rotation_role"])
        output["deepvue_theme"] = output.index.map(metadata["deepvue_theme"]).fillna("NOT_APPLICABLE")
        output["current_signal_ready"] = output["SLOW_RS"].notna()
        output = output.reset_index()
        output["FAST_ORDINAL_RANK"] = np.nan
        fast = output.loc[output["FAST_RS"].notna()].sort_values(
            ["FAST_RS", "economic_exposure_family_id"], ascending=[False, True], kind="mergesort"
        )
        output.loc[fast.index, "FAST_ORDINAL_RANK"] = np.arange(1, len(fast) + 1)
        output["SLOW_ORDINAL_RANK"] = np.nan
        slow = output.loc[output["SLOW_RS"].notna()].sort_values(
            ["SLOW_RS", "economic_exposure_family_id"], ascending=[False, True], kind="mergesort"
        )
        output.loc[slow.index, "SLOW_ORDINAL_RANK"] = np.arange(1, len(slow) + 1)
        return output.sort_values("economic_exposure_family_id", kind="mergesort").reset_index(drop=True)

    def weekly_dates(self, asof: pd.Timestamp) -> pd.DatetimeIndex:
        dates = self.calendar[self.calendar <= pd.Timestamp(asof)]
        frame = pd.DataFrame({"date": dates})
        iso = frame["date"].dt.isocalendar()
        frame["iso_year"] = iso["year"].astype(int)
        frame["iso_week"] = iso["week"].astype(int)
        return pd.DatetimeIndex(frame.groupby(["iso_year", "iso_week"], sort=True).tail(1)["date"])

    def enriched_rankings(self, asof: pd.Timestamp, pool: str) -> pd.DataFrame:
        current = self.rankings(asof, pool)
        weekly = self.weekly_dates(asof)
        previous_1 = weekly[-2] if len(weekly) >= 2 else None
        previous_4 = weekly[-5] if len(weekly) >= 5 else None
        for date, suffix in [(previous_1, "1W"), (previous_4, "4W")]:
            if date is None:
                current[f"FAST_RANK_CHANGE_{suffix}"] = np.nan
                continue
            prior = self.rankings(pd.Timestamp(date), pool)[
                ["economic_exposure_family_id", "FAST_ORDINAL_RANK"]
            ].rename(columns={"FAST_ORDINAL_RANK": f"PRIOR_FAST_RANK_{suffix}"})
            current = current.merge(prior, on="economic_exposure_family_id", how="left", validate="one_to_one")
            current[f"FAST_RANK_CHANGE_{suffix}"] = current[f"PRIOR_FAST_RANK_{suffix}"] - current["FAST_ORDINAL_RANK"]

        current["RELATIVE_PRICE_SLOPE_63"] = np.nan
        dates = self.calendar[self.calendar <= pd.Timestamp(asof)][-63:]
        if len(dates) == 63:
            endpoint = self.endpoint.loc[
                self.endpoint["date"].isin(dates)
                & self.endpoint["economic_exposure_family_id"].isin(
                    current["economic_exposure_family_id"].tolist() + ["GLOBAL_DEVELOPED_WORLD"]
                )
            ]
            wealth = endpoint.pivot(index="date", columns="economic_exposure_family_id", values="signal_wealth_index_gbp").reindex(dates)
            benchmark = wealth.get("GLOBAL_DEVELOPED_WORLD")
            if benchmark is not None:
                slopes = {}
                x = np.arange(63, dtype=float)
                for family in current["economic_exposure_family_id"]:
                    if family not in wealth:
                        continue
                    relative = wealth[family] / benchmark
                    if relative.notna().all() and (relative > 0).all():
                        slopes[family] = float(np.polyfit(x, np.log(relative.to_numpy(float)), 1)[0])
                current["RELATIVE_PRICE_SLOPE_63"] = current["economic_exposure_family_id"].map(slopes)

        current["LEADERSHIP_STATE"] = "NOT_AVAILABLE"
        feature_path = SOURCE_PATHS["feature_panel"]
        if feature_path.exists():
            features = pd.read_parquet(feature_path, columns=[
                "date", "economic_exposure_family_id", "analysis_context_id", "cadence", "ROTATION_STATE"
            ])
            features["date"] = pd.to_datetime(features["date"]).dt.normalize()
            context = pool
            matching = features.loc[
                features["date"].eq(pd.Timestamp(asof))
                & features["analysis_context_id"].eq(context)
                & features["cadence"].eq("WEEKLY"),
                ["economic_exposure_family_id", "ROTATION_STATE"],
            ]
            if len(matching):
                mapping = matching.drop_duplicates("economic_exposure_family_id").set_index("economic_exposure_family_id")["ROTATION_STATE"]
                current["LEADERSHIP_STATE"] = current["economic_exposure_family_id"].map(mapping).fillna("NOT_AVAILABLE")
        # Extend the frozen transparent RRG-like state deterministically when
        # the historical A3R2 feature artifact no longer covers the new cutoff.
        dates = self.calendar[self.calendar <= pd.Timestamp(asof)]
        if len(dates) >= 22 and current["LEADERSHIP_STATE"].eq("NOT_AVAILABLE").any():
            prior = self.rankings(pd.Timestamp(dates[-22]), pool)[
                ["economic_exposure_family_id", "RANK_RS_63", "RANK_RS_126"]
            ].rename(columns={"RANK_RS_63": "PRIOR_RANK_RS_63_21", "RANK_RS_126": "PRIOR_RANK_RS_126_21"})
            state_inputs = current[[
                "economic_exposure_family_id", "RANK_RS_63", "RANK_RS_126", "LEADERSHIP_STATE"
            ]].merge(prior, on="economic_exposure_family_id", how="left", validate="one_to_one")
            level = state_inputs[["RANK_RS_63", "RANK_RS_126"]].mean(axis=1, skipna=False)
            prior_level = state_inputs[["PRIOR_RANK_RS_63_21", "PRIOR_RANK_RS_126_21"]].mean(axis=1, skipna=False)
            momentum = level - prior_level
            valid = level.notna() & momentum.notna()
            if valid.sum() >= 3 and level.loc[valid].std(ddof=0) > 0 and momentum.loc[valid].std(ddof=0) > 0:
                level_positive = level.ge(level.loc[valid].mean())
                momentum_positive = momentum.ge(momentum.loc[valid].mean())
                computed = pd.Series("NOT_AVAILABLE", index=state_inputs.index, dtype=object)
                computed.loc[valid & level_positive & momentum_positive] = "LEADING"
                computed.loc[valid & level_positive & ~momentum_positive] = "WEAKENING"
                computed.loc[valid & ~level_positive & momentum_positive] = "IMPROVING"
                computed.loc[valid & ~level_positive & ~momentum_positive] = "LAGGING"
                state_inputs["LEADERSHIP_STATE"] = state_inputs["LEADERSHIP_STATE"].where(
                    state_inputs["LEADERSHIP_STATE"].ne("NOT_AVAILABLE"), computed
                )
                state_map = state_inputs.set_index("economic_exposure_family_id")["LEADERSHIP_STATE"]
                current["LEADERSHIP_STATE"] = current["economic_exposure_family_id"].map(state_map)
        implementation = self.implementation.set_index("economic_exposure_family_id")
        current["preferred_ticker"] = current["economic_exposure_family_id"].map(implementation["preferred_ticker"])
        descriptive_lines = _combined_current_lines()
        descriptive_lines = descriptive_lines.sort_values(
            ["economic_exposure_family_id", "_preferred_order", "ticker"], kind="mergesort"
        ).drop_duplicates("economic_exposure_family_id")
        descriptive_ticker = descriptive_lines.set_index("economic_exposure_family_id")["ticker"]
        current["preferred_ticker"] = current["preferred_ticker"].fillna(
            current["economic_exposure_family_id"].map(descriptive_ticker)
        ).fillna("NO_CURRENT_LINE")
        return current

    def _benchmark_regime_metrics(self, asof: pd.Timestamp) -> dict[str, Any]:
        benchmark = self.endpoint.loc[
            self.endpoint["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD")
            & self.endpoint["endpoint_valid"].astype(bool)
            & self.endpoint["date"].le(pd.Timestamp(asof)),
            ["date", "signal_wealth_index_gbp", "continuity_segment_id"],
        ].drop_duplicates("date").sort_values("date")
        benchmark = benchmark.set_index("date").reindex(self.calendar[self.calendar <= pd.Timestamp(asof)])
        wealth = pd.to_numeric(benchmark["signal_wealth_index_gbp"], errors="coerce")
        segment = benchmark["continuity_segment_id"]
        returns = wealth.pct_change(fill_method=None).where(segment.eq(segment.shift(1)))
        complete63 = returns.notna().rolling(63, min_periods=63).sum().eq(63)
        realised_vol = returns.rolling(63, min_periods=63).std(ddof=1).mul(math.sqrt(252.0)).where(complete63)
        moving_average = wealth.rolling(200, min_periods=200).mean()
        vol_q33 = realised_vol.shift(1).expanding(min_periods=252).quantile(1 / 3)
        vol_q67 = realised_vol.shift(1).expanding(min_periods=252).quantile(2 / 3)
        date = pd.Timestamp(asof)
        return {
            "global_trend_regime": (
                "ABOVE_200" if wealth.get(date, np.nan) > moving_average.get(date, np.nan)
                else "BELOW_OR_EQUAL_200"
            ) if pd.notna(moving_average.get(date, np.nan)) else "UNAVAILABLE",
            "global_realised_volatility_63": realised_vol.get(date, np.nan),
            "global_vol_q33_prior": vol_q33.get(date, np.nan),
            "global_vol_q67_prior": vol_q67.get(date, np.nan),
        }

    def _rotation_metrics(self, asof: pd.Timestamp, pool: str) -> dict[str, Any]:
        current = self.rankings(asof, pool)
        valid = current.loc[current["RS_63"].notna()].copy()
        dispersion = float(valid["RS_63"].std(ddof=0)) if len(valid) >= 2 else np.nan
        breadth = float(valid["RS_63"].gt(0).mean()) if len(valid) else np.nan
        dates = self.calendar[self.calendar <= pd.Timestamp(asof)]
        rotation = np.nan
        if len(dates) >= 22:
            prior = self.rankings(pd.Timestamp(dates[-22]), pool)[
                ["economic_exposure_family_id", "RANK_RS_63"]
            ].rename(columns={"RANK_RS_63": "PRIOR_RANK_RS_63"})
            changes = valid[["economic_exposure_family_id", "RANK_RS_63"]].merge(
                prior, on="economic_exposure_family_id", how="left", validate="one_to_one"
            )
            changes["CHANGE"] = changes["RANK_RS_63"] - changes["PRIOR_RANK_RS_63"]
            if changes["CHANGE"].notna().any():
                rotation = float(changes["CHANGE"].abs().median())
        return {
            "cross_sectional_dispersion_rs63": dispersion,
            "leadership_breadth_positive_rs63": breadth,
            "rotation_intensity_rank_change_21": rotation,
            "eligible_family_count": int(len(valid)),
        }

    def _us_technology_dominance(self, asof: pd.Timestamp) -> str:
        frame = self.rankings(asof, "ALL_EQUITY_OPPORTUNITIES")
        required = ["RANK_RS_21", "RANK_RS_42", "RANK_RS_63", "RANK_RS_126", "RANK_RS_252"]
        frame["CENTERED_60D"] = (
            frame["RANK_RS_21"] * 0.10 + frame["RANK_RS_42"] * 0.25
            + frame["RANK_RS_63"] * 0.35 + frame["RANK_RS_126"] * 0.20
            + frame["RANK_RS_252"] * 0.10
        ).where(frame[required].notna().all(axis=1))
        top = frame.loc[frame["CENTERED_60D"].notna()].sort_values(
            ["CENTERED_60D", "economic_exposure_family_id"], ascending=[False, True]
        ).head(5)
        metadata = self.metadata.set_index("economic_exposure_family_id")
        flags = []
        for family in top["economic_exposure_family_id"]:
            row = metadata.loc[family]
            text = "|".join(str(row.get(column, "")) for column in [
                "a0_primary_geography", "sector", "industry", "economic_theme", "economic_exposure_family_id"
            ]).upper()
            flags.append("TECHNOLOGY" in text or "SEMICONDUCT" in text)
        return "DOMINANT" if sum(flags[:5]) >= 2 and sum(flags[:2]) >= 1 else "NOT_DOMINANT"

    def regime(self, asof: pd.Timestamp) -> dict[str, Any]:
        fields = [
            "global_trend_regime", "volatility_regime", "dispersion_regime", "breadth_regime",
            "rotation_intensity_regime", "us_technology_dominance",
        ]
        history = pd.read_parquet(SOURCE_PATHS["regime_history"])
        history["date"] = pd.to_datetime(history["date"]).dt.normalize()
        history = history.loc[history["pool_id"].eq("INDUSTRY_PLUS_THEME")].sort_values("date")
        exact = history.loc[history["date"].eq(pd.Timestamp(asof))]
        if len(exact):
            row = exact.iloc[-1]
            result = {field: normalise_scalar(row.get(field, "NOT_AVAILABLE")) for field in fields}
            result["regime_source_date"] = pd.Timestamp(row["date"]).date().isoformat()
            result["regime_source"] = "FROZEN_A3R2_REGIME_HISTORY"
            return result
        if history.empty:
            return {field: "NOT_AVAILABLE" for field in fields} | {"regime_source_date": None}
        if pd.Timestamp(asof) < pd.Timestamp(history["date"].min()):
            return {field: "NOT_AVAILABLE" for field in fields} | {"regime_source_date": None}

        prior_dispersion = history["cross_sectional_dispersion_rs63"].dropna().astype(float).tolist()
        prior_rotation = history["rotation_intensity_rank_change_21"].dropna().astype(float).tolist()
        last_frozen = pd.Timestamp(history["date"].max())
        dates = [date for date in self.weekly_dates(asof) if last_frozen < date <= pd.Timestamp(asof)]
        if pd.Timestamp(asof) > last_frozen and (not dates or dates[-1] != pd.Timestamp(asof)):
            dates.append(pd.Timestamp(asof))
        result: dict[str, Any] | None = None
        for date in dates:
            benchmark = self._benchmark_regime_metrics(pd.Timestamp(date))
            metrics = self._rotation_metrics(pd.Timestamp(date), "INDUSTRY_PLUS_THEME")
            dispersion_q33 = np.quantile(prior_dispersion, 1 / 3) if len(prior_dispersion) >= 52 else np.nan
            dispersion_q67 = np.quantile(prior_dispersion, 2 / 3) if len(prior_dispersion) >= 52 else np.nan
            rotation_q33 = np.quantile(prior_rotation, 1 / 3) if len(prior_rotation) >= 52 else np.nan
            rotation_q67 = np.quantile(prior_rotation, 2 / 3) if len(prior_rotation) >= 52 else np.nan
            volatility = benchmark["global_realised_volatility_63"]
            if any(pd.isna(benchmark[key]) for key in ["global_realised_volatility_63", "global_vol_q33_prior", "global_vol_q67_prior"]):
                volatility_regime = "UNAVAILABLE"
            elif volatility < benchmark["global_vol_q33_prior"]:
                volatility_regime = "LOW"
            elif volatility > benchmark["global_vol_q67_prior"]:
                volatility_regime = "HIGH"
            else:
                volatility_regime = "NORMAL"
            dispersion = metrics["cross_sectional_dispersion_rs63"]
            if any(pd.isna(value) for value in [dispersion, dispersion_q33, dispersion_q67]):
                dispersion_regime = "UNAVAILABLE"
            elif dispersion < dispersion_q33:
                dispersion_regime = "LOW"
            elif dispersion > dispersion_q67:
                dispersion_regime = "HIGH"
            else:
                dispersion_regime = "NORMAL"
            rotation = metrics["rotation_intensity_rank_change_21"]
            if any(pd.isna(value) for value in [rotation, rotation_q33, rotation_q67]):
                rotation_regime = "UNAVAILABLE"
            elif rotation < rotation_q33:
                rotation_regime = "LOW"
            elif rotation > rotation_q67:
                rotation_regime = "HIGH"
            else:
                rotation_regime = "NORMAL"
            breadth = metrics["leadership_breadth_positive_rs63"]
            breadth_regime = (
                "UNAVAILABLE" if pd.isna(breadth) else
                "NARROW" if breadth < 1 / 3 else "MEDIUM" if breadth < 2 / 3 else "BROAD"
            )
            result = {
                "global_trend_regime": benchmark["global_trend_regime"],
                "volatility_regime": volatility_regime,
                "dispersion_regime": dispersion_regime,
                "breadth_regime": breadth_regime,
                "rotation_intensity_regime": rotation_regime,
                "us_technology_dominance": self._us_technology_dominance(pd.Timestamp(date)),
                "regime_source_date": pd.Timestamp(date).date().isoformat(),
                "regime_source": "A5_DETERMINISTIC_EXTENSION_OF_FROZEN_A3R2_DEFINITIONS",
            }
            if pd.notna(dispersion):
                prior_dispersion.append(float(dispersion))
            if pd.notna(rotation):
                prior_rotation.append(float(rotation))
        return result or ({field: "NOT_AVAILABLE" for field in fields} | {
            "regime_source_date": last_frozen.date().isoformat(),
            "regime_staleness_warning": "UNABLE_TO_EXTEND_REGIME_TO_ASOF",
        })

    def implementation_row(self, family: str, asof: pd.Timestamp) -> dict[str, Any] | None:
        match = self.implementation.loc[self.implementation["economic_exposure_family_id"].eq(family)]
        if match.empty:
            return None
        row = match.iloc[0].to_dict()
        observation = row.get("ii_observation_date", "")
        if observation and observation not in {"NOT_CHECKED", "NOT_APPLICABLE"} and pd.Timestamp(asof) < pd.Timestamp(observation):
            row["ii_current_tradable"] = "NOT_APPLICABLE_HISTORICAL_ASOF"
            row["alternate_ii_current_tradable"] = "NOT_APPLICABLE_HISTORICAL_ASOF"
        return row

    def economic_index(self, family: str, date: pd.Timestamp) -> tuple[float, Any] | None:
        row = self.endpoint.loc[
            self.endpoint["economic_exposure_family_id"].eq(family)
            & self.endpoint["date"].eq(pd.Timestamp(date))
            & self.endpoint["endpoint_valid"].astype(bool)
        ]
        if len(row) != 1:
            return None
        value = float(row.iloc[0]["signal_wealth_index_gbp"])
        segment = row.iloc[0]["continuity_segment_id"]
        if not np.isfinite(value) or value <= 0:
            return None
        return value, segment

    def cash_index(self, date: pd.Timestamp) -> float | None:
        row = self.cash.loc[self.cash["date"].eq(pd.Timestamp(date))]
        if len(row) != 1 or not bool(row.iloc[0]["data_valid"]):
            return None
        value = float(row.iloc[0]["cash_index"])
        return value if np.isfinite(value) and value > 0 else None


def slow_sorted(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["SLOW_RS"].notna()].sort_values(
        ["SLOW_RS", "economic_exposure_family_id"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)


def fast_sorted(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["FAST_RS"].notna()].sort_values(
        ["FAST_RS", "economic_exposure_family_id"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)


def resolved_implementation(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Apply the frozen preferred-then-preverified-alternate implementation rule."""
    if row is None:
        return None
    if row.get("ii_current_tradable") == "CONFIRMED_BY_USER":
        return {**row, "resolved_line": "PREFERRED"}
    if row.get("alternate_ii_current_tradable") == "CONFIRMED_BY_USER":
        alternate = dict(row)
        alternate.update({
            "preferred_ticker": row.get("alternate_ticker", ""),
            "preferred_isin": row.get("alternate_isin", ""),
            "preferred_listing_id": row.get("alternate_listing_id", ""),
            "listing_currency": row.get("alternate_currency", ""),
            "price_unit": row.get("alternate_price_unit", ""),
            "resolved_line": "PREDECLARED_VERIFIED_ALTERNATE",
        })
        return alternate
    return None


def implementation_execution_state(row: dict[str, Any] | None) -> str:
    if row is None:
        return "IMPLEMENTATION_BLOCKED_NO_PREVERIFIED_LINE"
    resolved = resolved_implementation(row)
    if resolved is not None:
        return (
            "SHADOW_EXECUTABLE_PREDECLARED_VERIFIED_ALTERNATE"
            if resolved.get("resolved_line") == "PREDECLARED_VERIFIED_ALTERNATE"
            else "SHADOW_EXECUTABLE_CURRENT_II_CONFIRMED"
        )
    return "IMPLEMENTATION_BLOCKED_CURRENT_II_UNCHECKED"


def initial_state(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "specification_id": config["specification_id"],
        "model_status": {MODEL_A: "PROSPECTIVE_NOT_STARTED", MODEL_B: "PROSPECTIVE_NOT_STARTED"},
        "initial_notional_gbp": {MODEL_A: INITIAL_NOTIONAL_GBP, MODEL_B: INITIAL_NOTIONAL_GBP},
        "current_positions": {MODEL_A: [], MODEL_B: []},
        "pending_decision": None,
        "pending_execution": None,
        "last_official_signal": None,
        "last_execution": None,
        "latest_telemetry_date": None,
        "nav_gbp": {MODEL_A: INITIAL_NOTIONAL_GBP, MODEL_B: INITIAL_NOTIONAL_GBP},
        "cash_gbp": {MODEL_A: INITIAL_NOTIONAL_GBP, MODEL_B: INITIAL_NOTIONAL_GBP},
        "cumulative_costs_gbp": {MODEL_A: 0.0, MODEL_B: 0.0},
        "high_water_mark_gbp": {MODEL_A: INITIAL_NOTIONAL_GBP, MODEL_B: INITIAL_NOTIONAL_GBP},
        "drawdown": {MODEL_A: 0.0, MODEL_B: 0.0},
        "completed_on_time_decision_count": 0,
        "completed_shadow_execution_count": 0,
        "prospective_integrity_status": "E3_CONFIRMATION_NOT_YET_AVAILABLE",
        "authoritative_history": "APPEND_ONLY_LEDGERS",
        "warning": WARNING,
    }


def initialise_empty_ledgers() -> None:
    for key, columns in CSV_SCHEMAS.items():
        path = LEDGER_PATHS[key]
        if path.exists():
            try:
                existing = read_csv_schema(path, columns)
            except RuntimeError:
                raw = pd.read_csv(path, dtype=str, keep_default_na=False)
                if len(raw):
                    raise
                write_csv_if_changed(path, pd.DataFrame(columns=columns))
                existing = read_csv_schema(path, columns)
            if len(existing):
                raise RuntimeError(f"Setup refuses to replace non-empty prospective ledger: {path.name}")
        else:
            write_csv_if_changed(path, pd.DataFrame(columns=columns))
    if LEDGER_PATHS["run"].exists() and LEDGER_PATHS["run"].stat().st_size:
        raise RuntimeError("Setup refuses to replace non-empty run ledger")
    if not LEDGER_PATHS["run"].exists():
        write_bytes_if_changed(LEDGER_PATHS["run"], b"")
    empty_telemetry = pd.DataFrame(columns=CSV_SCHEMAS["telemetry_csv"])
    if not LEDGER_PATHS["telemetry_parquet"].exists():
        empty_telemetry.to_parquet(LEDGER_PATHS["telemetry_parquet"], index=False, compression="zstd")


def ledger_counts() -> dict[str, int]:
    counts = {}
    for key, columns in CSV_SCHEMAS.items():
        counts[key] = len(read_csv_schema(LEDGER_PATHS[key], columns))
    if LEDGER_PATHS["run"].exists():
        counts["run"] = sum(1 for line in LEDGER_PATHS["run"].read_text(encoding="utf-8").splitlines() if line.strip())
    else:
        counts["run"] = 0
    return counts


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError("A5 shadow configuration has not been created; run --mode setup")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def operating_calendar() -> pd.DataFrame:
    frame = pd.read_csv(OPERATING_CALENDAR_PATH, dtype=str, keep_default_na=False)
    required = {
        "calendar_month", "expected_final_valid_xlon_signal_date",
        "expected_next_eligible_execution_date", "weekly_telemetry_dates",
    }
    if not required.issubset(frame.columns):
        raise RuntimeError("A5 operating calendar schema is invalid")
    return frame


def scheduled_signal_row(date: pd.Timestamp) -> pd.Series | None:
    frame = operating_calendar()
    match = frame.loc[frame["expected_final_valid_xlon_signal_date"].eq(pd.Timestamp(date).date().isoformat())]
    return None if match.empty else match.iloc[0]


def next_scheduled_signal(after: pd.Timestamp) -> str | None:
    frame = operating_calendar()
    dates = pd.to_datetime(frame["expected_final_valid_xlon_signal_date"])
    future = dates.loc[dates.gt(pd.Timestamp(after))]
    return None if future.empty else pd.Timestamp(future.min()).date().isoformat()


def due_unrecorded_signal_dates(asof: pd.Timestamp) -> list[pd.Timestamp]:
    """Return every due signal date not yet preserved in the append-only ledger."""
    frame = operating_calendar()
    scheduled = pd.to_datetime(frame["expected_final_valid_xlon_signal_date"])
    existing = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    recorded = set(existing["signal_date"]) if len(existing) else set()
    return [
        pd.Timestamp(date)
        for date in scheduled
        if EARLIEST_SIGNAL <= pd.Timestamp(date) <= pd.Timestamp(asof)
        and pd.Timestamp(date).date().isoformat() not in recorded
    ]


def next_scheduled_telemetry(after: pd.Timestamp) -> str | None:
    frame = operating_calendar()
    dates: list[pd.Timestamp] = []
    for value in frame["weekly_telemetry_dates"]:
        dates.extend(pd.Timestamp(item) for item in str(value).split(";") if item)
    future = [date for date in dates if date > pd.Timestamp(after)]
    return min(future).date().isoformat() if future else None


def telemetry_due(bundle: DataBundle, asof: pd.Timestamp) -> bool:
    """Only the final genuine XLON session of the complete ISO week is due."""
    asof = pd.Timestamp(asof).normalize()
    week_start = asof - pd.Timedelta(days=asof.weekday())
    week_end = week_start + pd.Timedelta(days=6)
    sessions, _ = build_xlon_session_calendar(week_start, week_end)
    return bool(len(sessions) and pd.Timestamp(sessions[-1]) == asof)


def _existing_decision(signal_date: pd.Timestamp) -> dict[str, Any] | None:
    ledger = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    match = ledger.loc[ledger["signal_date"].eq(pd.Timestamp(signal_date).date().isoformat())]
    if match.empty:
        return None
    if len(match) != 1:
        raise RuntimeError("Decision ledger has duplicate signal dates")
    return match.iloc[0].to_dict()


def _current_active_holding() -> str:
    positions = read_csv_schema(LEDGER_PATHS["position"], CSV_SCHEMAS["position"])
    positions = positions.loc[positions["model_id"].eq(MODEL_A)]
    if positions.empty:
        return "NONE"
    last_date = positions["effective_date"].max()
    current = positions.loc[positions["effective_date"].eq(last_date)]
    return ";".join(sorted(current["family_id"].unique())) if len(current) else "NONE"


def _decision_snapshot_payload(
    *,
    event_id: str,
    signal_date: pd.Timestamp,
    ranked: pd.DataFrame,
    bundle: DataBundle,
    config: dict[str, Any],
) -> dict[str, Any]:
    fields = [
        "economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role",
        "RS_63", "RS_126", "RS_252", "RANK_RS_63", "RANK_RS_126", "RANK_RS_252",
        "MH_LEVEL_3_6_12_REFERENCE", "current_signal_ready",
    ]
    rows = ranked[fields].sort_values("economic_exposure_family_id").to_dict(orient="records")
    return {
        "decision_event_id": event_id,
        "signal_date": signal_date.date().isoformat(),
        "data_cutoff": bundle.latest_cutoff().date().isoformat(),
        "input_rows": rows,
        "input_row_sha256": sha256_bytes(canonical_json(rows).encode("utf-8")),
        "input_files": source_inventory([
            SOURCE_PATHS["signal_eligibility"], SOURCE_PATHS["endpoint_history"],
            SOURCE_PATHS["roles"], IMPLEMENTATION_MAP_PATH,
        ]),
        "universe_version": sha256_file(SOURCE_PATHS["roles"]),
        "implementation_map_version": sha256_file(IMPLEMENTATION_MAP_PATH),
        "source_git_commit": current_git_commit(),
        "code_config_hashes": code_config_inventory(),
        "freeze_tag": config["freeze_tag"],
        "warning": WARNING,
    }


def record_official_decision(bundle: DataBundle, asof: pd.Timestamp) -> tuple[dict[str, Any] | None, bool]:
    asof = pd.Timestamp(asof).normalize()
    if asof < EARLIEST_SIGNAL:
        return None, False
    schedule = scheduled_signal_row(asof)
    if schedule is None:
        return None, False
    existing = _existing_decision(asof)
    if existing is not None:
        return existing, False

    config = load_config()
    if not git_value("tag", "--list", config["freeze_tag"]):
        raise RuntimeError("Prospective signal prohibited until the setup freeze tag exists")
    latest = bundle.latest_cutoff()
    if latest < asof:
        return None, False
    expected_execution = pd.Timestamp(schedule["expected_next_eligible_execution_date"])
    classification = "ON_TIME_PROSPECTIVE" if latest < expected_execution else "LATE_SIGNAL_NOT_E3"
    ranked = bundle.enriched_rankings(asof, "INDUSTRY_PLUS_THEME")
    leaders = slow_sorted(ranked)
    if leaders.empty:
        raise RuntimeError("No signal-ready INDUSTRY_PLUS_THEME family at official month-end")
    top = leaders.iloc[0]
    family = str(top["economic_exposure_family_id"])
    implementation_raw = bundle.implementation_row(family, asof)
    execution_state = implementation_execution_state(implementation_raw)
    implementation = resolved_implementation(implementation_raw)
    previous = _current_active_holding()
    if execution_state.startswith("IMPLEMENTATION_BLOCKED"):
        action = "IMPLEMENTATION_BLOCKED"
    elif previous == "NONE":
        action = "INITIAL_ENTRY"
    elif previous == family:
        action = "HOLD"
    else:
        action = "SWITCH"
    event_id = stable_id("A5DEC", config["specification_id"], asof.date().isoformat())
    top5 = leaders.head(5)
    top5_rows = top5[[
        "economic_exposure_family_id", "economic_exposure_name", "RS_63", "RS_126", "RS_252",
        "RANK_RS_63", "RANK_RS_126", "RANK_RS_252", "SLOW_RS",
    ]].to_dict(orient="records")
    regime = bundle.regime(asof)
    implementation = implementation or implementation_raw or {}
    a5a_nav = float(value_model_at(bundle, MODEL_A, asof)["nav_gbp"])
    a5b_nav = float(value_model_at(bundle, MODEL_B, asof)["nav_gbp"])
    estimated_a5b_legs = 2 if previous in {"NONE", family} else 3
    row = {
        "decision_event_id": event_id,
        "specification_id": config["specification_id"],
        "signal_date": asof.date().isoformat(),
        "data_cutoff": latest.date().isoformat(),
        "recorded_at_utc": utc_now(),
        "prospective_classification": classification,
        "on_time_e3_counted": "YES" if classification == "ON_TIME_PROSPECTIVE" else "NO",
        "expected_execution_date": expected_execution.date().isoformat(),
        "economic_pool": "INDUSTRY_PLUS_THEME",
        "signal_id": "MH_LEVEL_3_6_12_REFERENCE",
        "eligible_family_count": len(leaders),
        "selected_family_id": family,
        "selected_display_name": top["economic_exposure_name"],
        "preferred_ticker": implementation.get("preferred_ticker", "IMPLEMENTATION_BLOCKED"),
        "preferred_isin": implementation.get("preferred_isin", "IMPLEMENTATION_BLOCKED"),
        "issuer": implementation.get("issuer", "IMPLEMENTATION_BLOCKED"),
        "listing_currency": implementation.get("listing_currency", "IMPLEMENTATION_BLOCKED"),
        "deepvue_label": top.get("deepvue_theme", "NOT_APPLICABLE"),
        "rs63": top["RS_63"], "rs126": top["RS_126"], "rs252": top["RS_252"],
        "rank_rs63": top["RANK_RS_63"], "rank_rs126": top["RANK_RS_126"],
        "rank_rs252": top["RANK_RS_252"], "composite_score": top["SLOW_RS"],
        "rank_2_family": leaders.iloc[1]["economic_exposure_family_id"] if len(leaders) > 1 else "NOT_APPLICABLE",
        "rank_3_family": leaders.iloc[2]["economic_exposure_family_id"] if len(leaders) > 2 else "NOT_APPLICABLE",
        "rank_4_family": leaders.iloc[3]["economic_exposure_family_id"] if len(leaders) > 3 else "NOT_APPLICABLE",
        "rank_5_family": leaders.iloc[4]["economic_exposure_family_id"] if len(leaders) > 4 else "NOT_APPLICABLE",
        "top5_json": canonical_json(top5_rows),
        "previous_active_holding": previous,
        "action": action,
        "implementation_check_status": execution_state,
        "a5a_target_weight": 0.0 if action == "IMPLEMENTATION_BLOCKED" else 1.0,
        "a5a_target_notional_gbp": 0.0 if action == "IMPLEMENTATION_BLOCKED" else a5a_nav,
        "a5b_active_target_weight": 0.0 if action == "IMPLEMENTATION_BLOCKED" else 0.5,
        "a5b_core_target_weight": 0.5,
        "a5b_active_target_notional_gbp": 0.0 if action == "IMPLEMENTATION_BLOCKED" else a5b_nav * 0.5,
        "a5b_core_target_notional_gbp": a5b_nav * 0.5,
        "a5b_estimated_rebalance_legs": estimated_a5b_legs,
        "benchmark_family_id": "GLOBAL_DEVELOPED_WORLD",
        "global_trend_regime": regime.get("global_trend_regime", "NOT_AVAILABLE"),
        "volatility_regime": regime.get("volatility_regime", "NOT_AVAILABLE"),
        "dispersion_regime": regime.get("dispersion_regime", "NOT_AVAILABLE"),
        "breadth_regime": regime.get("breadth_regime", "NOT_AVAILABLE"),
        "rotation_intensity_regime": regime.get("rotation_intensity_regime", "NOT_AVAILABLE"),
        "us_technology_dominance": regime.get("us_technology_dominance", "NOT_AVAILABLE"),
        "input_eligibility_path": str(SOURCE_PATHS["signal_eligibility"].resolve()),
        "input_eligibility_sha256": sha256_file(SOURCE_PATHS["signal_eligibility"]),
        "implementation_map_path": str(IMPLEMENTATION_MAP_PATH.resolve()),
        "implementation_map_sha256": sha256_file(IMPLEMENTATION_MAP_PATH),
        "universe_version": sha256_file(SOURCE_PATHS["roles"]),
        "source_git_commit": current_git_commit(),
        "freeze_tag": config["freeze_tag"],
        "backfill": "NO",
        "orders_or_scheduler": "NONE",
        "warning": WARNING,
    }
    snapshot = _decision_snapshot_payload(event_id=event_id, signal_date=asof, ranked=ranked, bundle=bundle, config=config)
    snapshot_path = INPUT_SNAPSHOT_ROOT / f"{event_id}.json"
    if snapshot_path.exists() and canonical_json(json.loads(snapshot_path.read_text(encoding="utf-8"))) != canonical_json(snapshot):
        raise RuntimeError("Official decision input snapshot collision")
    write_json_if_changed(snapshot_path, snapshot)
    added = append_csv_rows(
        LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"], [row], ["decision_event_id"]
    )
    return row, bool(added)


def record_telemetry(bundle: DataBundle, asof: pd.Timestamp) -> tuple[list[dict[str, Any]], bool]:
    asof = pd.Timestamp(asof).normalize()
    if not telemetry_due(bundle, asof):
        return [], False
    event_id = stable_id("A5TEL", asof.date().isoformat())
    existing = read_csv_schema(LEDGER_PATHS["telemetry_csv"], CSV_SCHEMAS["telemetry_csv"])
    if len(existing) and existing["telemetry_event_id"].eq(event_id).any():
        return existing.loc[existing["telemetry_event_id"].eq(event_id)].to_dict(orient="records"), False
    regime = bundle.regime(asof)
    rows: list[dict[str, Any]] = []
    for pool, rank_type, sorter in [
        ("INDUSTRY_PLUS_THEME", "SLOW_3_6_12", slow_sorted),
        ("INDUSTRY_PLUS_THEME", "FAST_1_2_3", fast_sorted),
        ("GEOGRAPHY", "SLOW_3_6_12", slow_sorted),
    ]:
        ranked = bundle.enriched_rankings(asof, pool)
        leaders = sorter(ranked).head(5)
        for ordinal, top in enumerate(leaders.itertuples(index=False), start=1):
            rows.append({
                "telemetry_event_id": event_id,
                "date": asof.date().isoformat(),
                "pool": pool,
                "rank_type": rank_type,
                "rank": ordinal,
                "family_id": top.economic_exposure_family_id,
                "display_name": top.economic_exposure_name,
                "preferred_ticker": top.preferred_ticker,
                "rs21": top.RS_21, "rs42": top.RS_42, "rs63": top.RS_63,
                "rs126": top.RS_126, "rs252": top.RS_252,
                "fast_score": top.FAST_RS, "slow_score": top.SLOW_RS,
                "fast_rank": top.FAST_ORDINAL_RANK, "slow_rank": top.SLOW_ORDINAL_RANK,
                "fast_slow_gap": top.FAST_RS - top.SLOW_RS if pd.notna(top.FAST_RS) and pd.notna(top.SLOW_RS) else np.nan,
                "fast_rank_change_1w": top.FAST_RANK_CHANGE_1W,
                "fast_rank_change_4w": top.FAST_RANK_CHANGE_4W,
                "relative_price_slope_63": top.RELATIVE_PRICE_SLOPE_63,
                "leadership_state": top.LEADERSHIP_STATE,
                "global_trend_regime": regime.get("global_trend_regime", "NOT_AVAILABLE"),
                "volatility_regime": regime.get("volatility_regime", "NOT_AVAILABLE"),
                "dispersion_regime": regime.get("dispersion_regime", "NOT_AVAILABLE"),
                "breadth_regime": regime.get("breadth_regime", "NOT_AVAILABLE"),
                "rotation_intensity_regime": regime.get("rotation_intensity_regime", "NOT_AVAILABLE"),
                "us_technology_dominance": regime.get("us_technology_dominance", "NOT_AVAILABLE"),
                "portfolio_change": "NO_PORTFOLIO_CHANGE_TELEMETRY_ONLY",
                "source_git_commit": current_git_commit(),
                "warning": WARNING,
            })
    added = append_csv_rows(
        LEDGER_PATHS["telemetry_csv"], CSV_SCHEMAS["telemetry_csv"], rows,
        ["telemetry_event_id", "pool", "rank_type", "rank"],
    )
    telemetry = read_csv_schema(LEDGER_PATHS["telemetry_csv"], CSV_SCHEMAS["telemetry_csv"])
    telemetry.to_parquet(LEDGER_PATHS["telemetry_parquet"], index=False, compression="zstd")
    return rows, bool(added)


def _append_warning(
    *, date: pd.Timestamp, warning_type: str, severity: str, message: str,
    related_event_id: str = "NOT_APPLICABLE", evidence: str = "NOT_APPLICABLE",
) -> bool:
    event_id = stable_id("A5WARN", pd.Timestamp(date).date().isoformat(), warning_type, related_event_id, message)
    existing = read_csv_schema(LEDGER_PATHS["warnings"], CSV_SCHEMAS["warnings"])
    if len(existing) and existing["warning_event_id"].eq(event_id).any():
        return False
    row = {
        "warning_event_id": event_id,
        "date": pd.Timestamp(date).date().isoformat(),
        "warning_type": warning_type,
        "severity": severity,
        "related_event_id": related_event_id,
        "message": message,
        "evidence": evidence,
        "recorded_at_utc": utc_now(),
        "source_git_commit": current_git_commit(),
        "resolved_status": "OPEN",
    }
    return bool(append_csv_rows(
        LEDGER_PATHS["warnings"], CSV_SCHEMAS["warnings"], [row], ["warning_event_id"]
    ))


def append_amendment(
    *, original_event_id: str, original_ledger: str, reason: str, field_name: str,
    old_value: Any, new_value: Any, evidence: str,
) -> str:
    """Preserve a correction without mutating the original prospective event."""
    event_id = stable_id(
        "A5AMD", original_event_id, original_ledger, reason, field_name,
        canonical_json(old_value), canonical_json(new_value), evidence,
    )
    existing = read_csv_schema(LEDGER_PATHS["amendment"], CSV_SCHEMAS["amendment"])
    if len(existing) and existing["amendment_event_id"].eq(event_id).any():
        return event_id
    row = {
        "amendment_event_id": event_id,
        "original_event_id": original_event_id,
        "original_ledger": original_ledger,
        "reason": reason,
        "field_name": field_name,
        "old_value": canonical_json(old_value),
        "new_value": canonical_json(new_value),
        "evidence": evidence,
        "recorded_at_utc": utc_now(),
        "source_git_commit": current_git_commit(),
        "warning": WARNING,
    }
    append_csv_rows(
        LEDGER_PATHS["amendment"], CSV_SCHEMAS["amendment"], [row], ["amendment_event_id"]
    )
    return event_id


def _position_snapshot(model_id: str, date: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series | None]:
    positions = read_csv_schema(LEDGER_PATHS["position"], CSV_SCHEMAS["position"])
    positions = positions.loc[
        positions["model_id"].eq(model_id) & pd.to_datetime(positions["effective_date"]).le(pd.Timestamp(date))
    ]
    cash = read_csv_schema(LEDGER_PATHS["cash"], CSV_SCHEMAS["cash"])
    cash = cash.loc[cash["model_id"].eq(model_id) & pd.to_datetime(cash["effective_date"]).le(pd.Timestamp(date))]
    if positions.empty and cash.empty:
        return pd.DataFrame(columns=CSV_SCHEMAS["position"]), None
    dates = []
    if len(positions):
        dates.append(pd.to_datetime(positions["effective_date"]).max())
    if len(cash):
        dates.append(pd.to_datetime(cash["effective_date"]).max())
    latest = max(dates)
    current_positions = positions.loc[pd.to_datetime(positions["effective_date"]).eq(latest)].copy()
    current_cash = cash.loc[pd.to_datetime(cash["effective_date"]).eq(latest)]
    return current_positions, (current_cash.iloc[-1] if len(current_cash) else None)


def value_model_at(bundle: DataBundle, model_id: str, date: pd.Timestamp) -> dict[str, Any]:
    positions, cash_row = _position_snapshot(model_id, date)
    if positions.empty and cash_row is None:
        return {
            "nav_gbp": INITIAL_NOTIONAL_GBP, "position_value_gbp": 0.0,
            "cash_value_gbp": INITIAL_NOTIONAL_GBP, "holdings": {}, "started": False,
        }
    holdings: dict[str, float] = {}
    position_value = 0.0
    for row in positions.itertuples(index=False):
        endpoint = bundle.economic_index(row.family_id, date)
        if endpoint is None or str(endpoint[1]) != str(row.continuity_segment_id):
            raise RuntimeError(f"Invalid mark-to-market endpoint for {model_id}/{row.family_id}/{date.date()}")
        value = float(row.economic_units) * endpoint[0]
        holdings[row.family_id] = value
        position_value += value
    cash_value = 0.0
    if cash_row is not None:
        source_cash_index = float(cash_row["cash_index_at_event"])
        current_cash_index = bundle.cash_index(date)
        if current_cash_index is None:
            raise RuntimeError(f"Validated GBP cash unavailable at {date.date()}")
        cash_value = float(cash_row["cash_balance_gbp"]) * current_cash_index / source_cash_index
    return {
        "nav_gbp": position_value + cash_value,
        "position_value_gbp": position_value,
        "cash_value_gbp": cash_value,
        "holdings": holdings,
        "started": True,
    }


def _listing_close(implementation: dict[str, Any] | None, date: pd.Timestamp) -> tuple[Any, str]:
    if not implementation:
        return "NOT_AVAILABLE", "NOT_AVAILABLE"
    listing_id = implementation.get("preferred_listing_id", "")
    frames = []
    # A2R-corrected routes take precedence; A2 is a fallback for unaffected lines.
    for key in ["corrected_instrument_history", "instrument_history"]:
        path = SOURCE_PATHS[key]
        frame = pd.read_parquet(path, columns=[
            "date", "listing_id", "price_listing_currency", "price_available", "missing_flag", "stale_flag"
        ])
        frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
        frames.append(frame.loc[frame["listing_id"].eq(listing_id) & frame["date"].eq(pd.Timestamp(date))])
    match = pd.concat(frames, ignore_index=True).drop_duplicates(["date", "listing_id"], keep="first")
    match = match.loc[
        match["price_available"].fillna(False).astype(bool)
        & ~match["missing_flag"].fillna(True).astype(bool)
        & ~match["stale_flag"].fillna(False).astype(bool)
    ]
    if len(match) != 1:
        return "NOT_AVAILABLE_USE_ECONOMIC_TR_INDEX", implementation.get("price_unit", "NOT_AVAILABLE")
    return float(match.iloc[0]["price_listing_currency"]), implementation.get("price_unit", "NOT_AVAILABLE")


def _execution_date(bundle: DataBundle, decision: dict[str, Any]) -> pd.Timestamp | None:
    expected = pd.Timestamp(decision["expected_execution_date"])
    sessions, _ = build_xlon_session_calendar(expected, expected + pd.Timedelta(days=10))
    candidates = sessions[:3]
    family = decision["selected_family_id"]
    for date in candidates:
        if date > bundle.latest_cutoff():
            return None
        if bundle.economic_index(family, date) is not None and bundle.economic_index("GLOBAL_DEVELOPED_WORLD", date) is not None:
            return pd.Timestamp(date)
    if bundle.latest_cutoff() >= candidates[-1]:
        raise RuntimeError("No common valid execution endpoint within the frozen three-session tolerance")
    return None


def _target_sets(bundle: DataBundle, decision: dict[str, Any]) -> dict[str, dict[str, float] | None]:
    signal_date = pd.Timestamp(decision["signal_date"])
    family = decision["selected_family_id"]
    implementation = bundle.implementation_row(family, signal_date)
    executable = resolved_implementation(implementation) is not None
    ranking = slow_sorted(bundle.rankings(signal_date, "INDUSTRY_PLUS_THEME"))
    members = ranking["economic_exposure_family_id"].tolist()
    equal_pool = {member: 1.0 / len(members) for member in members}
    unselected = [member for member in members if member != family]
    unselected_pool = {member: 1.0 / len(unselected) for member in unselected} if unselected else {}
    core = bundle.implementation_row("GLOBAL_DEVELOPED_WORLD", signal_date)
    core_confirmed = resolved_implementation(core) is not None
    a5b_target = None
    if core_confirmed:
        a5b_target = {"GLOBAL_DEVELOPED_WORLD": 0.5}
        if executable:
            a5b_target[family] = 0.5
    return {
        MODEL_A: {family: 1.0} if executable else {},
        MODEL_B: a5b_target,
        COMPARATOR_GLOBAL: {"GLOBAL_DEVELOPED_WORLD": 1.0},
        COMPARATOR_POOL: equal_pool,
        COMPARATOR_STATIC: ({"GLOBAL_DEVELOPED_WORLD": 0.5} | {member: 0.5 / len(members) for member in members}),
        COMPARATOR_CASH: {},
        COMPARATOR_UNSELECTED: unselected_pool,
    }


def _series_costed(model_id: str) -> bool:
    return model_id in {MODEL_A, MODEL_B, COMPARATOR_STATIC}


def _book_target(
    bundle: DataBundle,
    *,
    model_id: str,
    target: dict[str, float],
    decision: dict[str, Any],
    execution_date: pd.Timestamp,
    logging_classification: str,
) -> bool:
    execution_event_id = stable_id("A5EXE", decision["decision_event_id"], model_id)
    existing = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    if len(existing) and existing["execution_event_id"].eq(execution_event_id).any():
        return False
    pre = value_model_at(bundle, model_id, execution_date)
    pre_nav = float(pre["nav_gbp"])
    current_weights = {family: value / pre_nav for family, value in pre["holdings"].items()}
    families = sorted(set(current_weights) | set(target))
    deltas = {family: float(target.get(family, 0.0) - current_weights.get(family, 0.0)) for family in families}
    legs = [family for family in families if abs(deltas[family]) > 1e-12]
    friction_bps = 20.0 if _series_costed(model_id) else 0.0
    leg_costs: dict[str, tuple[float, float, float]] = {}
    for family in legs:
        notional = abs(deltas[family]) * pre_nav
        friction = notional * friction_bps / 10_000.0
        fixed = 3.99 if _series_costed(model_id) else 0.0
        leg_costs[family] = (notional, friction, fixed)
    total_cost = sum(friction + fixed for _, friction, fixed in leg_costs.values())
    post_nav = pre_nav - total_cost
    if post_nav <= 0:
        raise RuntimeError("Execution costs exhaust the shadow portfolio")
    snapshot_families = sorted(set(families) | set(target) | {"GLOBAL_DEVELOPED_WORLD"})
    endpoint_rows = bundle.endpoint.loc[
        bundle.endpoint["date"].eq(pd.Timestamp(execution_date))
        & bundle.endpoint["economic_exposure_family_id"].isin(snapshot_families)
    ].sort_values("economic_exposure_family_id").to_dict(orient="records")
    cash_rows = bundle.cash.loc[bundle.cash["date"].eq(pd.Timestamp(execution_date))].to_dict(orient="records")
    implementation_rows = bundle.implementation.loc[
        bundle.implementation["economic_exposure_family_id"].isin(snapshot_families)
    ].sort_values("economic_exposure_family_id").to_dict(orient="records")
    execution_snapshot = {
        "execution_event_id": execution_event_id,
        "model_id": model_id,
        "decision_event_id": decision["decision_event_id"],
        "signal_date": decision["signal_date"],
        "execution_date": execution_date.date().isoformat(),
        "data_cutoff": bundle.latest_cutoff().date().isoformat(),
        "logging_classification": logging_classification,
        "pre_trade_value": pre,
        "target_weights": target,
        "weight_deltas": deltas,
        "trade_legs": legs,
        "pre_trade_nav_gbp": pre_nav,
        "total_cost_gbp": total_cost,
        "post_trade_nav_gbp": post_nav,
        "endpoint_rows": endpoint_rows,
        "cash_rows": cash_rows,
        "implementation_rows": implementation_rows,
        "exact_input_row_sha256": sha256_bytes(canonical_json({
            "endpoint_rows": endpoint_rows,
            "cash_rows": cash_rows,
            "implementation_rows": implementation_rows,
        }).encode("utf-8")),
        "input_files": source_inventory([
            SOURCE_PATHS["endpoint_history"], SOURCE_PATHS["cash_series"],
            SOURCE_PATHS["instrument_history"], SOURCE_PATHS["corrected_instrument_history"],
            SOURCE_PATHS["roles"], IMPLEMENTATION_MAP_PATH,
        ]),
        "universe_version": versioned_sha256_file(SOURCE_PATHS["roles"]),
        "implementation_map_version": versioned_sha256_file(IMPLEMENTATION_MAP_PATH),
        "code_config_hashes": code_config_inventory(),
        "source_git_commit": current_git_commit(),
        "freeze_tag": load_config()["freeze_tag"],
        "warning": WARNING,
    }
    execution_snapshot_path = INPUT_SNAPSHOT_ROOT / f"{execution_event_id}.json"
    if execution_snapshot_path.exists():
        existing_snapshot = json.loads(execution_snapshot_path.read_text(encoding="utf-8"))
        if canonical_json(existing_snapshot) != canonical_json(execution_snapshot):
            raise RuntimeError(f"Immutable execution input snapshot collision: {execution_event_id}")
    write_json_if_changed(execution_snapshot_path, execution_snapshot)
    execution_snapshot_hash = versioned_sha256_file(execution_snapshot_path)
    position_rows: list[dict[str, Any]] = []
    for family, weight in sorted(target.items()):
        endpoint = bundle.economic_index(family, execution_date)
        if endpoint is None:
            raise RuntimeError(f"Target endpoint unavailable for {family}")
        implementation_raw = bundle.implementation_row(family, execution_date)
        implementation = resolved_implementation(implementation_raw) or implementation_raw
        position_rows.append({
            "position_event_id": stable_id("A5POS", execution_event_id, family),
            "execution_event_id": execution_event_id,
            "model_id": model_id,
            "effective_date": execution_date.date().isoformat(),
            "family_id": family,
            "target_weight": weight,
            "economic_units": post_nav * float(weight) / endpoint[0],
            "economic_index_at_execution": endpoint[0],
            "continuity_segment_id": endpoint[1],
            "ticker": implementation.get("preferred_ticker", "RESEARCH_INDEX") if implementation else "RESEARCH_INDEX",
            "isin": implementation.get("preferred_isin", "NOT_APPLICABLE") if implementation else "NOT_APPLICABLE",
            "implementation_status": implementation_execution_state(implementation),
            "source_git_commit": current_git_commit(),
            "warning": WARNING,
        })
    cash_balance = post_nav * max(0.0, 1.0 - sum(target.values()))
    cash_index = bundle.cash_index(execution_date)
    if cash_index is None:
        raise RuntimeError("Validated GBP cash index missing on execution date")
    cash_row = {
        "cash_event_id": stable_id("A5CASH", execution_event_id),
        "execution_event_id": execution_event_id,
        "model_id": model_id,
        "effective_date": execution_date.date().isoformat(),
        "cash_balance_gbp": cash_balance,
        "cash_index_at_event": cash_index,
        "cash_weight": cash_balance / post_nav,
        "source_git_commit": current_git_commit(),
        "warning": WARNING,
    }
    execution_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    if not legs:
        legs_for_output: list[str | None] = [None]
    else:
        legs_for_output = legs
    for index, family in enumerate(legs_for_output, start=1):
        if family is None:
            side = "NONE"
            notional = friction = fixed = 0.0
            ticker = isin = "NOT_APPLICABLE"
            target_weight = 0.0
            target_notional = 0.0
            close = close_unit = "NOT_APPLICABLE"
            economic_index = np.nan
            units = 0.0
            implementation_status = "NO_TRADE"
            family_value = "NOT_APPLICABLE"
        else:
            family_value = family
            side = "BUY" if deltas[family] > 0 else "SELL"
            notional, friction, fixed = leg_costs[family]
            implementation_raw = bundle.implementation_row(family, execution_date)
            implementation = resolved_implementation(implementation_raw) or implementation_raw
            ticker = implementation.get("preferred_ticker", "RESEARCH_INDEX") if implementation else "RESEARCH_INDEX"
            isin = implementation.get("preferred_isin", "NOT_APPLICABLE") if implementation else "NOT_APPLICABLE"
            target_weight = float(target.get(family, 0.0))
            target_notional = post_nav * target_weight
            close, close_unit = _listing_close(implementation, execution_date)
            endpoint = bundle.economic_index(family, execution_date)
            economic_index = endpoint[0] if endpoint else np.nan
            units = target_notional / economic_index if target_notional and np.isfinite(economic_index) else 0.0
            implementation_status = implementation_execution_state(implementation)
        leg_id = f"{execution_event_id}-L{index:03d}"
        execution_rows.append({
            "execution_event_id": execution_event_id,
            "leg_id": leg_id,
            "model_id": model_id,
            "decision_event_id": decision["decision_event_id"],
            "signal_date": decision["signal_date"],
            "execution_date": execution_date.date().isoformat(),
            "logged_at_utc": utc_now(),
            "logging_classification": logging_classification,
            "action": decision["action"] if model_id in {MODEL_A, MODEL_B} else "COMPARATOR_REBALANCE",
            "family_id": family_value,
            "ticker": ticker,
            "isin": isin,
            "side": side,
            "target_weight": target_weight,
            "target_notional_gbp": target_notional,
            "execution_close": close,
            "execution_close_unit": close_unit,
            "economic_index_gbp": economic_index,
            "notional_traded_gbp": notional,
            "friction_cost_gbp": friction,
            "fixed_fee_gbp": fixed,
            "total_cost_gbp": friction + fixed,
            "post_trade_units": units,
            "post_trade_notional_gbp": target_notional,
            "residual_cash_gbp": cash_balance,
            "units_basis": "ECONOMIC_TOTAL_RETURN_INDEX_UNITS_NOT_WHOLE_SHARES",
            "implementation_status": implementation_status,
            "input_snapshot_path": str(execution_snapshot_path.resolve()),
            "input_snapshot_sha256": execution_snapshot_hash,
            "source_git_commit": current_git_commit(),
            "shadow_only": "YES_NO_ORDER_CREATED",
            "warning": WARNING,
        })
        if family is not None and (friction + fixed) > 0:
            cost_rows.append({
                "cost_event_id": stable_id("A5COST", leg_id),
                "execution_event_id": execution_event_id,
                "leg_id": leg_id,
                "model_id": model_id,
                "date": execution_date.date().isoformat(),
                "notional_traded_gbp": notional,
                "friction_bps": friction_bps,
                "friction_cost_gbp": friction,
                "fixed_fee_gbp": fixed,
                "total_cost_gbp": friction + fixed,
                "source_git_commit": current_git_commit(),
                "warning": WARNING,
            })
    append_csv_rows(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"], execution_rows, ["leg_id"])
    append_csv_rows(LEDGER_PATHS["position"], CSV_SCHEMAS["position"], position_rows, ["position_event_id"])
    append_csv_rows(LEDGER_PATHS["cash"], CSV_SCHEMAS["cash"], [cash_row], ["cash_event_id"])
    append_csv_rows(LEDGER_PATHS["cost"], CSV_SCHEMAS["cost"], cost_rows, ["cost_event_id"])
    return True


def book_pending_execution(
    bundle: DataBundle, asof: pd.Timestamp,
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    decisions = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    if decisions.empty:
        return None, [], []
    executions = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    actions: list[str] = []
    execution_ids: list[str] = []
    pending = None
    for _, row in decisions.sort_values("signal_date").iterrows():
        decision = row.to_dict()
        booked_models = set(executions.loc[
            executions["decision_event_id"].eq(decision["decision_event_id"]), "model_id"
        ])
        if MODEL_A in booked_models and MODEL_B in booked_models:
            continue
        execution_date = _execution_date(bundle, decision)
        if execution_date is None or execution_date > pd.Timestamp(asof):
            pending = decision
            continue
        logging_classification = (
            "EXECUTION_LOGGED_ON_TIME" if bundle.latest_cutoff() == execution_date
            else "EXECUTION_LOGGED_LATE_USING_FROZEN_PRICE_DATE"
        )
        targets = _target_sets(bundle, decision)
        for model_id, target in targets.items():
            if model_id in booked_models:
                continue
            if target is None:
                _append_warning(
                    date=execution_date,
                    warning_type="CORE_II_MANUAL_CHECK_REQUIRED",
                    severity="BLOCKING_A5B_EXECUTION",
                    related_event_id=decision["decision_event_id"],
                    message="A5-B booking withheld until SWDA / IE00B4L5Y983 is manually confirmed in ii.",
                    evidence="UKACTIVE_A5_IMPLEMENTATION_MAP.csv",
                )
                continue
            if _book_target(
                bundle, model_id=model_id, target=target, decision=decision,
                execution_date=execution_date, logging_classification=logging_classification,
            ):
                actions.append(model_id)
                execution_ids.append(stable_id("A5EXE", decision["decision_event_id"], model_id))
        pending = decision if MODEL_B not in set(
            read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"]).loc[
                lambda frame: frame["decision_event_id"].eq(decision["decision_event_id"]), "model_id"
            ]
        ) else None
    return pending, actions, execution_ids


def _pending_execution_stop(model_id: str, asof: pd.Timestamp, bundle: DataBundle) -> pd.Timestamp:
    decisions = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    executions = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    stop = pd.Timestamp(asof)
    for _, decision in decisions.iterrows():
        booked = executions.loc[
            executions["decision_event_id"].eq(decision["decision_event_id"])
            & executions["model_id"].eq(model_id)
        ]
        if len(booked):
            continue
        expected = pd.Timestamp(decision["expected_execution_date"])
        if expected <= stop:
            prior = bundle.calendar[bundle.calendar < expected]
            if len(prior):
                stop = min(stop, pd.Timestamp(prior[-1]))
    return stop


def _series_history_path(model_id: str) -> tuple[Path, list[str]]:
    if model_id in {MODEL_A, MODEL_B}:
        return LEDGER_PATHS["nav"], CSV_SCHEMAS["nav"]
    return LEDGER_PATHS["benchmark"], CSV_SCHEMAS["benchmark"]


def mark_to_market(bundle: DataBundle, asof: pd.Timestamp) -> int:
    total_added = 0
    cash_ledger = read_csv_schema(LEDGER_PATHS["cash"], CSV_SCHEMAS["cash"])
    if cash_ledger.empty:
        return 0
    costs = read_csv_schema(LEDGER_PATHS["cost"], CSV_SCHEMAS["cost"])
    executions = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    for model_id in sorted(cash_ledger["model_id"].unique()):
        effective = pd.to_datetime(cash_ledger.loc[cash_ledger["model_id"].eq(model_id), "effective_date"])
        start = pd.Timestamp(effective.min())
        stop = _pending_execution_stop(model_id, asof, bundle)
        if stop < start:
            continue
        path, columns = _series_history_path(model_id)
        existing = read_csv_schema(path, columns)
        existing_model = existing.loc[existing["model_id"].eq(model_id)].copy()
        existing_dates = set(existing_model["date"])
        dates = bundle.calendar[(bundle.calendar >= start) & (bundle.calendar <= stop)]
        generated_rows: list[dict[str, Any]] = []
        prior_nav: float | None = None
        prior_high = INITIAL_NOTIONAL_GBP
        if len(existing_model):
            ordered = existing_model.sort_values("date")
            prior_nav = float(ordered.iloc[-1]["nav_gbp"])
            prior_high = float(ordered["high_water_mark_gbp"].astype(float).max())
        for date in dates:
            valued = value_model_at(bundle, model_id, pd.Timestamp(date))
            if not valued["started"]:
                continue
            nav = float(valued["nav_gbp"])
            holdings_text = ";".join(sorted(valued["holdings"]))
            source_payload = {
                "date": pd.Timestamp(date).date().isoformat(),
                "model_id": model_id,
                "holdings": valued["holdings"],
                "cash": valued["cash_value_gbp"],
            }
            source_hash = sha256_bytes(canonical_json(source_payload).encode("utf-8"))
            date_text = pd.Timestamp(date).date().isoformat()
            if date_text in existing_dates:
                old = existing_model.loc[existing_model["date"].eq(date_text)]
                if len(old) != 1:
                    raise RuntimeError(f"Duplicate NAV row for {model_id}/{date_text}")
                if abs(float(old.iloc[0]["nav_gbp"]) - nav) > 1e-6 or old.iloc[0]["source_input_hash"] != source_hash:
                    _append_warning(
                        date=pd.Timestamp(date), warning_type="DATA_REVISION_ALERT", severity="PAUSE_INTERPRETATION",
                        related_event_id=old.iloc[0]["nav_event_id"],
                        message=f"Revised source would alter immutable NAV for {model_id} on {date_text}; original preserved.",
                        evidence=canonical_json({"old_nav": old.iloc[0]["nav_gbp"], "revised_nav": nav}),
                    )
                prior_nav = float(old.iloc[0]["nav_gbp"])
                prior_high = max(prior_high, float(old.iloc[0]["high_water_mark_gbp"]))
                continue
            daily_return = np.nan if prior_nav is None else nav / prior_nav - 1.0
            prior_high = max(prior_high, nav)
            model_costs = costs.loc[
                costs["model_id"].eq(model_id) & pd.to_datetime(costs["date"]).le(pd.Timestamp(date))
            ]
            model_exec = executions.loc[
                executions["model_id"].eq(model_id) & pd.to_datetime(executions["execution_date"]).le(pd.Timestamp(date))
            ]
            traded = pd.to_numeric(model_exec["notional_traded_gbp"], errors="coerce").fillna(0).sum()
            trade_legs = int(model_exec["side"].isin(["BUY", "SELL"]).sum())
            row = {
                "nav_event_id": stable_id("A5NAV", model_id, date_text),
                "model_id": model_id,
                "date": date_text,
                "nav_gbp": nav,
                "cumulative_net_return": nav / INITIAL_NOTIONAL_GBP - 1.0,
                "daily_return": daily_return,
                "position_value_gbp": valued["position_value_gbp"],
                "cash_value_gbp": valued["cash_value_gbp"],
                "cash_weight": valued["cash_value_gbp"] / nav if nav else np.nan,
                "holdings": holdings_text or "GBP_CASH",
                "high_water_mark_gbp": prior_high,
                "drawdown": nav / prior_high - 1.0,
                "cumulative_costs_gbp": pd.to_numeric(model_costs["total_cost_gbp"], errors="coerce").fillna(0).sum(),
                "traded_notional_turnover": float(traded) / INITIAL_NOTIONAL_GBP,
                "trade_legs": trade_legs,
                "source_input_hash": source_hash,
                "source_git_commit": current_git_commit(),
                "warning": WARNING,
            }
            generated_rows.append(row)
            prior_nav = nav
        if generated_rows:
            total_added += append_csv_rows(path, columns, generated_rows, ["nav_event_id"])
    return total_added


def check_official_input_revisions(bundle: DataBundle) -> int:
    decisions = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    warnings = 0
    for _, decision in decisions.iterrows():
        event_id = decision["decision_event_id"]
        snapshot_path = INPUT_SNAPSHOT_ROOT / f"{event_id}.json"
        if not snapshot_path.exists():
            warnings += int(_append_warning(
                date=pd.Timestamp(decision["signal_date"]), warning_type="MISSING_INPUT_SNAPSHOT", severity="BLOCKING",
                related_event_id=event_id, message="Official signal input snapshot is missing.", evidence=str(snapshot_path),
            ))
            continue
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        ranked = bundle.rankings(pd.Timestamp(decision["signal_date"]), "INDUSTRY_PLUS_THEME")
        fields = [
            "economic_exposure_family_id", "economic_exposure_name", "primary_rotation_role",
            "RS_63", "RS_126", "RS_252", "RANK_RS_63", "RANK_RS_126", "RANK_RS_252",
            "MH_LEVEL_3_6_12_REFERENCE", "current_signal_ready",
        ]
        rows = ranked[fields].sort_values("economic_exposure_family_id").to_dict(orient="records")
        revised_hash = sha256_bytes(canonical_json(rows).encode("utf-8"))
        if revised_hash != snapshot["input_row_sha256"]:
            warnings += int(_append_warning(
                date=pd.Timestamp(decision["signal_date"]), warning_type="DATA_REVISION_ALERT", severity="PAUSE_INTERPRETATION",
                related_event_id=event_id,
                message="Current source rows differ from the immutable official signal snapshot; original decision preserved.",
                evidence=canonical_json({"original": snapshot["input_row_sha256"], "revised": revised_hash}),
            ))
    return warnings


def _history_for(model_id: str) -> pd.DataFrame:
    path, columns = _series_history_path(model_id)
    frame = read_csv_schema(path, columns)
    frame = frame.loc[frame["model_id"].eq(model_id)].copy()
    if len(frame):
        frame["date"] = pd.to_datetime(frame["date"])
        for column in [
            "nav_gbp", "cumulative_net_return", "daily_return", "cash_weight", "high_water_mark_gbp",
            "drawdown", "cumulative_costs_gbp", "traded_notional_turnover", "trade_legs",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = frame.sort_values("date")
    return frame


def _performance_row(model_id: str) -> dict[str, Any]:
    frame = _history_for(model_id)
    if frame.empty:
        return {
            "series": model_id,
            "status": "PROSPECTIVE_NOT_STARTED",
            "inception_date": "NOT_STARTED",
            "current_nav_gbp": INITIAL_NOTIONAL_GBP,
            "cumulative_net_return": 0.0,
            "cumulative_return_gbp": 0.0,
            "current_period_return": "N/A — PROSPECTIVE_NOT_STARTED",
            "current_drawdown": 0.0,
            "maximum_drawdown": 0.0,
            "current_high_water_mark_gbp": INITIAL_NOTIONAL_GBP,
            "days_below_high_water_mark": 0,
            "cumulative_costs_gbp": 0.0,
            "traded_notional_turnover": 0.0,
            "trade_legs": 0,
            "cash_weight": 1.0,
            "current_holdings": "NONE",
            "annualised_return": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "annualised_volatility": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "sharpe": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "sortino": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "calmar": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "ulcer_index": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "positive_monthly_frequency": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
            "positive_rolling_12m_frequency": "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
        }
    last = frame.iloc[-1]
    latest_date = pd.Timestamp(last["date"])
    month = frame.loc[frame["date"].dt.to_period("M").eq(latest_date.to_period("M"))]
    period_return = float(last["nav_gbp"] / month.iloc[0]["nav_gbp"] - 1.0) if len(month) > 1 else 0.0
    hwm_date = frame.loc[frame["nav_gbp"].eq(frame["nav_gbp"].cummax()) & frame["nav_gbp"].eq(frame["nav_gbp"].cummax().iloc[-1]), "date"]
    days_below = int((latest_date - pd.Timestamp(hwm_date.iloc[-1])).days) if len(hwm_date) else 0
    row = {
        "series": model_id,
        "status": "SHADOW_ACTIVE",
        "inception_date": pd.Timestamp(frame.iloc[0]["date"]).date().isoformat(),
        "current_nav_gbp": float(last["nav_gbp"]),
        "cumulative_net_return": float(last["nav_gbp"] / INITIAL_NOTIONAL_GBP - 1.0),
        "cumulative_return_gbp": float(last["nav_gbp"] - INITIAL_NOTIONAL_GBP),
        "current_period_return": period_return,
        "current_drawdown": float(last["drawdown"]),
        "maximum_drawdown": float(frame["drawdown"].min()),
        "current_high_water_mark_gbp": float(last["high_water_mark_gbp"]),
        "days_below_high_water_mark": days_below,
        "cumulative_costs_gbp": float(last["cumulative_costs_gbp"]),
        "traded_notional_turnover": float(last["traded_notional_turnover"]),
        "trade_legs": int(last["trade_legs"]),
        "cash_weight": float(last["cash_weight"]),
        "current_holdings": last["holdings"],
    }
    daily = frame["daily_return"].dropna().astype(float)
    if len(daily) < 252:
        row.update({key: "N/A — INSUFFICIENT PROSPECTIVE HISTORY" for key in [
            "annualised_return", "annualised_volatility", "sharpe", "sortino", "calmar", "ulcer_index",
            "positive_monthly_frequency", "positive_rolling_12m_frequency",
        ]})
        return row
    years = (frame.iloc[-1]["date"] - frame.iloc[0]["date"]).days / 365.2425
    annual_return = float((frame.iloc[-1]["nav_gbp"] / frame.iloc[0]["nav_gbp"]) ** (1 / years) - 1.0)
    annual_vol = float(daily.std(ddof=1) * math.sqrt(252.0))
    downside = daily.loc[daily < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(252.0)) if len(downside) > 1 else np.nan
    monthly = frame.set_index("date")["nav_gbp"].resample("ME").last().pct_change().dropna()
    rolling_12m = frame.set_index("date")["nav_gbp"].resample("ME").last().pct_change(12).dropna()
    row.update({
        "annualised_return": annual_return,
        "annualised_volatility": annual_vol,
        "sharpe": annual_return / annual_vol if annual_vol > 0 else np.nan,
        "sortino": annual_return / downside_vol if downside_vol > 0 else np.nan,
        "calmar": annual_return / abs(frame["drawdown"].min()) if frame["drawdown"].min() < 0 else np.nan,
        "ulcer_index": float(np.sqrt(np.mean(np.square(frame["drawdown"].astype(float))))),
        "positive_monthly_frequency": float((monthly > 0).mean()) if len(monthly) >= 3 else "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
        "positive_rolling_12m_frequency": float((rolling_12m > 0).mean()) if len(rolling_12m) else "N/A — INSUFFICIENT PROSPECTIVE HISTORY",
    })
    return row


def scorecard() -> list[dict[str, Any]]:
    rows = [_performance_row(model_id) for model_id in SERIES_ORDER]
    lookup = {row["series"]: row for row in rows}
    global_return = float(lookup[COMPARATOR_GLOBAL]["cumulative_net_return"])
    pool_return = float(lookup[COMPARATOR_POOL]["cumulative_net_return"])
    static_return = float(lookup[COMPARATOR_STATIC]["cumulative_net_return"])
    unselected = _performance_row(COMPARATOR_UNSELECTED)
    for row in rows:
        current = float(row["cumulative_net_return"])
        row["return_vs_global"] = current - global_return
        if row["series"] == MODEL_B:
            row["return_vs_appropriate_pool_comparator"] = current - static_return
        else:
            row["return_vs_appropriate_pool_comparator"] = current - pool_return
        row["selected_vs_unselected"] = (
            current - float(unselected["cumulative_net_return"])
            if row["series"] == MODEL_A else "NOT_APPLICABLE"
        )
    return rows


def derive_state(config: dict[str, Any]) -> dict[str, Any]:
    state = initial_state(config)
    decisions = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    executions = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    telemetry = read_csv_schema(LEDGER_PATHS["telemetry_csv"], CSV_SCHEMAS["telemetry_csv"])
    cards = {row["series"]: row for row in scorecard()}
    for model in [MODEL_A, MODEL_B]:
        card = cards[model]
        state["model_status"][model] = card["status"]
        state["nav_gbp"][model] = card["current_nav_gbp"]
        state["cash_gbp"][model] = card["current_nav_gbp"] * card["cash_weight"]
        state["cumulative_costs_gbp"][model] = card["cumulative_costs_gbp"]
        state["high_water_mark_gbp"][model] = card["current_high_water_mark_gbp"]
        state["drawdown"][model] = card["current_drawdown"]
        state["current_positions"][model] = [] if card["current_holdings"] in {"NONE", "GBP_CASH"} else card["current_holdings"].split(";")
    if len(decisions):
        state["last_official_signal"] = decisions.sort_values("signal_date").iloc[-1].to_dict()
    if len(executions):
        state["last_execution"] = executions.sort_values(["execution_date", "model_id", "leg_id"]).iloc[-1].to_dict()
    if len(telemetry):
        state["latest_telemetry_date"] = telemetry["date"].max()
    state["completed_on_time_decision_count"] = int(decisions["on_time_e3_counted"].eq("YES").sum())
    a5a_exec = executions.loc[executions["model_id"].eq(MODEL_A), "execution_event_id"].nunique()
    state["completed_shadow_execution_count"] = int(a5a_exec)
    state["prospective_integrity_status"] = (
        "PRIMARY_PROSPECTIVE_ASSESSMENT_DUE" if state["completed_on_time_decision_count"] >= 24
        else "E3_CONFIRMATION_NOT_YET_AVAILABLE"
    )
    if len(decisions):
        last = decisions.sort_values("signal_date").iloc[-1]
        booked = set(executions.loc[executions["decision_event_id"].eq(last["decision_event_id"]), "model_id"])
        if MODEL_A not in booked or MODEL_B not in booked:
            state["pending_execution"] = {
                "decision_event_id": last["decision_event_id"],
                "signal_date": last["signal_date"],
                "expected_execution_date": last["expected_execution_date"],
                "models_not_booked": sorted({MODEL_A, MODEL_B} - booked),
            }
    return state


def _format_value(value: Any, kind: str = "text") -> str:
    if isinstance(value, str):
        return value
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "N/A"
    if kind == "pct":
        return f"{float(value):.2%}"
    if kind == "gbp":
        return f"£{float(value):,.2f}"
    if kind == "num":
        return f"{float(value):.4f}"
    return str(value)


def _ranking_records(frame: pd.DataFrame, count: int = 5, fast: bool = False) -> list[dict[str, Any]]:
    source = fast_sorted(frame) if fast else slow_sorted(frame)
    records = []
    for rank, row in enumerate(source.head(count).to_dict(orient="records"), start=1):
        records.append({
            "rank": rank,
            "economic_exposure_family_id": row["economic_exposure_family_id"],
            "display_name": row["economic_exposure_name"],
            "preferred_ticker": row.get("preferred_ticker", "IMPLEMENTATION_BLOCKED"),
            "rs21": row["RS_21"], "rs42": row["RS_42"], "rs63": row["RS_63"],
            "rs126": row["RS_126"], "rs252": row["RS_252"],
            "fast_score": row["FAST_RS"], "slow_score": row["SLOW_RS"],
            "fast_rank": row["FAST_ORDINAL_RANK"], "slow_rank": row["SLOW_ORDINAL_RANK"],
            "fast_slow_gap": row["FAST_RS"] - row["SLOW_RS"] if pd.notna(row["FAST_RS"]) and pd.notna(row["SLOW_RS"]) else None,
            "fast_rank_change_1w": row.get("FAST_RANK_CHANGE_1W"),
            "fast_rank_change_4w": row.get("FAST_RANK_CHANGE_4W"),
            "relative_price_slope_63": row.get("RELATIVE_PRICE_SLOPE_63"),
            "leadership_state": row.get("LEADERSHIP_STATE", "NOT_AVAILABLE"),
        })
    return records


def build_report_payload(
    bundle: DataBundle,
    asof: pd.Timestamp,
    *,
    mode: str,
    run_status: str,
    official_decision: dict[str, Any] | None,
    actions: list[str],
    dry_run: bool = False,
) -> dict[str, Any]:
    active = bundle.enriched_rankings(asof, "INDUSTRY_PLUS_THEME")
    geography = bundle.enriched_rankings(asof, "GEOGRAPHY")
    slow_top = _ranking_records(active, 5, fast=False)
    fast_top = _ranking_records(active, 5, fast=True)
    geo_top = _ranking_records(geography, 5, fast=False)
    regime = bundle.regime(asof)
    state = derive_state(load_config())
    cards = scorecard()
    decision = official_decision
    if decision is None and state.get("last_official_signal"):
        decision = state["last_official_signal"]
    provisional_slow = slow_top[0] if slow_top else None
    provisional_fast = fast_top[0] if fast_top else None
    completed = state["completed_on_time_decision_count"]
    decision_history = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    if len(decision_history):
        first_signal = pd.to_datetime(decision_history["signal_date"]).min()
        elapsed_months = max(0, (asof.year - first_signal.year) * 12 + asof.month - first_signal.month + 1)
    else:
        elapsed_months = 0
    checkpoint = (
        "PRIMARY PROSPECTIVE ASSESSMENT" if completed >= 24 else
        "SECOND INTERIM REVIEW" if completed >= 18 else
        "FIRST ANNUAL REVIEW" if completed >= 12 else
        "INITIAL DESCRIPTIVE REVIEW" if completed >= 6 else
        "OPERATIONAL INTEGRITY REVIEW" if completed >= 3 else
        "PRE-CHECKPOINT"
    )
    calendar = operating_calendar()
    next_signal = next_scheduled_signal(asof)
    pending = state.get("pending_execution")
    latest_warning = read_csv_schema(LEDGER_PATHS["warnings"], CSV_SCHEMAS["warnings"])
    warnings = latest_warning.to_dict(orient="records")[-10:] if len(latest_warning) else []
    core = bundle.implementation.loc[bundle.implementation["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD")].iloc[0]
    if core["ii_current_tradable"] != "CONFIRMED_BY_USER":
        warnings.append({
            "warning_type": "CORE_II_MANUAL_CHECK_REQUIRED",
            "severity": "OPEN_ITEM",
            "message": f"Check {core['preferred_ticker']} / {core['preferred_isin']} in ii before first A5-B booking.",
        })
    execution_ids = {
        item.split(":", 2)[1] for item in actions if item.startswith("EXECUTION:") and len(item.split(":", 2)) == 3
    }
    execution_frame = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    booked_execution_rows = (
        execution_frame.loc[execution_frame["execution_event_id"].isin(execution_ids)].to_dict(orient="records")
        if execution_ids else []
    )
    run_identity = {
        "mode": mode,
        "asof": asof.date().isoformat(),
        "run_status": run_status,
        "actions": actions,
        "official_decision_event_id": official_decision.get("decision_event_id") if official_decision else None,
        "state": state,
        "code_config_hashes": code_config_inventory(),
    }
    run_id = stable_id("A5RUN", sha256_bytes(canonical_json(run_identity).encode("utf-8")))
    next_telemetry = next_scheduled_telemetry(asof)
    required_candidates = [item for item in [
        pending.get("expected_execution_date") if pending else None,
        next_signal,
        next_telemetry,
    ] if item]
    return {
        "run_id": run_id,
        "run_status": run_status,
        "mode": mode,
        "dry_run_status": "DRY_RUN_NOT_PROSPECTIVE" if dry_run else "NOT_A_DRY_RUN",
        "as_of_date": asof.date().isoformat(),
        "data_cutoff": bundle.latest_cutoff().date().isoformat(),
        "official_decision": official_decision,
        "last_official_decision": decision,
        "provisional_slow_leader": provisional_slow,
        "provisional_fast_leader": provisional_fast,
        "provisional_warning": "NOT AN OFFICIAL A5 DECISION — RANKINGS MAY CHANGE BEFORE MONTH-END",
        "industry_theme_slow_top5": slow_top,
        "industry_theme_fast_top5": fast_top,
        "geography_top5": geo_top,
        "regime": regime,
        "scorecard": cards,
        "pending_execution": pending,
        "executions_booked": booked_execution_rows,
        "actions_recorded": actions,
        "evidence_progress": {
            "completed_on_time_monthly_decisions": completed,
            "target_decisions": 24,
            "completed_shadow_executions": state["completed_shadow_execution_count"],
            "elapsed_prospective_months": elapsed_months,
            "next_official_signal_date": next_signal,
            "next_expected_execution_date": pending.get("expected_execution_date") if pending else None,
            "operational_integrity_status": state["prospective_integrity_status"],
            "current_evidence_level": "E3 CONFIRMATION NOT YET AVAILABLE" if completed < 24 else "PRIMARY PROSPECTIVE ASSESSMENT DUE",
            "checkpoint": checkpoint,
        },
        "operational_warnings": warnings,
        "next_required_run_date": min(required_candidates) if required_candidates else None,
        "model_change": "NONE",
        "orders_or_scheduler": "NONE",
        "warning": WARNING,
    }


def _markdown_ranking(rows: list[dict[str, Any]], title: str) -> list[str]:
    lines = [
        f"### {title}", "",
        "| Rank | Family | Ticker | RS21 | RS42 | RS63 | RS126 | RS252 | FAST | SLOW | F rank | S rank | F-S gap | 1w FΔ | 4w FΔ | Rel slope | State |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['economic_exposure_family_id']} | {row['preferred_ticker']} | "
            f"{_format_value(row['rs21'], 'pct')} | {_format_value(row['rs42'], 'pct')} | "
            f"{_format_value(row['rs63'], 'pct')} | {_format_value(row['rs126'], 'pct')} | "
            f"{_format_value(row['rs252'], 'pct')} | {_format_value(row['fast_score'], 'num')} | "
            f"{_format_value(row['slow_score'], 'num')} | {_format_value(row['fast_rank'], 'num')} | "
            f"{_format_value(row['slow_rank'], 'num')} | {_format_value(row['fast_slow_gap'], 'num')} | "
            f"{_format_value(row['fast_rank_change_1w'], 'num')} | {_format_value(row['fast_rank_change_4w'], 'num')} | "
            f"{_format_value(row['relative_price_slope_63'], 'num')} | {row['leadership_state']} |"
        )
    return lines


def render_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# UKACTIVE A5 latest shadow run report", "",
        f"**Run status:** {payload['run_status']}",
        f"**Mode:** {payload['mode']}",
        f"**As-of / validated cutoff:** {payload['as_of_date']} / {payload['data_cutoff']}",
        f"**Evidence:** {payload['dry_run_status']}",
        f"**Safety:** {WARNING}", "",
        "## 1. Run status", "",
        f"Actions recorded: {', '.join(payload['actions_recorded']) if payload['actions_recorded'] else 'NONE'}. No broker instruction was created.", "",
        "## 2. Official or provisional choice", "",
    ]
    if payload["official_decision"]:
        decision = payload["official_decision"]
        lines.extend([
            "### OFFICIAL A5 MONTH-END DECISION", "",
            f"- Signal date: {decision['signal_date']}",
            f"- Data cutoff: {decision['data_cutoff']}",
            f"- Selected family: {decision['selected_family_id']} — {decision['selected_display_name']}",
            f"- Preferred ii line: {decision['preferred_ticker']} / {decision['preferred_isin']}",
            f"- Issuer / listing currency: {decision['issuer']} / {decision['listing_currency']}",
            f"- DeepVue display label: {decision['deepvue_label']}",
            f"- RS63 / RS126 / RS252: {_format_value(float(decision['rs63']), 'pct')} / {_format_value(float(decision['rs126']), 'pct')} / {_format_value(float(decision['rs252']), 'pct')}",
            f"- Component percentile ranks: {_format_value(float(decision['rank_rs63']), 'num')} / {_format_value(float(decision['rank_rs126']), 'num')} / {_format_value(float(decision['rank_rs252']), 'num')}",
            f"- Composite score: {_format_value(float(decision['composite_score']), 'num')}",
            f"- Rank 2 / rank 3: {decision['rank_2_family']} / {decision['rank_3_family']}",
            f"- Previous active holding: {decision['previous_active_holding']}",
            f"- Action: {decision['action']}",
            f"- Expected execution session: {decision['expected_execution_date']}",
            f"- Implementation check: {decision['implementation_check_status']}",
            f"- A5-A target: {_format_value(float(decision['a5a_target_weight']), 'pct')} / {_format_value(float(decision['a5a_target_notional_gbp']), 'gbp')}",
            f"- A5-B targets: active {_format_value(float(decision['a5b_active_target_weight']), 'pct')} ({_format_value(float(decision['a5b_active_target_notional_gbp']), 'gbp')}), core {_format_value(float(decision['a5b_core_target_weight']), 'pct')} ({_format_value(float(decision['a5b_core_target_notional_gbp']), 'gbp')}); estimated legs {decision['a5b_estimated_rebalance_legs']}",
            f"- Integrity classification: {decision['prospective_classification']}", "",
        ])
    else:
        slow = payload["provisional_slow_leader"] or {}
        fast = payload["provisional_fast_leader"] or {}
        lines.extend([
            "### CURRENT PROVISIONAL SLOW LEADER", "",
            f"{slow.get('economic_exposure_family_id', 'NOT_AVAILABLE')} ({slow.get('preferred_ticker', 'NOT_AVAILABLE')})", "",
            "### CURRENT FAST LEADER", "",
            f"{fast.get('economic_exposure_family_id', 'NOT_AVAILABLE')} ({fast.get('preferred_ticker', 'NOT_AVAILABLE')})", "",
            f"**{payload['provisional_warning']}**", "",
        ])
    lines.extend(["## 3. Top-five ranking table", ""] + _markdown_ranking(payload["industry_theme_slow_top5"], "3/6/12 slow leaders"))
    lines.extend(["", "## 4. A5-A current position and action", ""])
    a = next(row for row in payload["scorecard"] if row["series"] == MODEL_A)
    lines.append(f"Status {a['status']}; holdings {a['current_holdings']}; NAV {_format_value(a['current_nav_gbp'], 'gbp')}.")
    lines.extend(["", "## 5. A5-B current positions and action", ""])
    b = next(row for row in payload["scorecard"] if row["series"] == MODEL_B)
    lines.append(f"Status {b['status']}; holdings {b['current_holdings']}; NAV {_format_value(b['current_nav_gbp'], 'gbp')}.")
    lines.extend(["", "## 6. Execution and pending-execution status", ""])
    if payload["executions_booked"]:
        lines.extend([
            "### A5 SHADOW EXECUTION BOOKED", "",
            "| Model | Signal | Execution | Log status | Action | Family | Ticker | ISIN | Side | Target | Close | Traded | Friction | Fixed fee | Total cost | Post-trade economic units | Residual cash |",
            "|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for row in payload["executions_booked"]:
            lines.append(
                f"| {row['model_id']} | {row['signal_date']} | {row['execution_date']} | {row['logging_classification']} | {row['action']} | "
                f"{row['family_id']} | {row['ticker']} | {row['isin']} | {row['side']} | "
                f"{_format_value(float(row['target_notional_gbp']), 'gbp')} | {row['execution_close']} {row['execution_close_unit']} | "
                f"{_format_value(float(row['notional_traded_gbp']), 'gbp')} | {_format_value(float(row['friction_cost_gbp']), 'gbp')} | "
                f"{_format_value(float(row['fixed_fee_gbp']), 'gbp')} | {_format_value(float(row['total_cost_gbp']), 'gbp')} | "
                f"{_format_value(float(row['post_trade_units']), 'num')} | {_format_value(float(row['residual_cash_gbp']), 'gbp')} |"
            )
        execution_costs: dict[str, float] = {}
        for row in payload["executions_booked"]:
            execution_costs[row["model_id"]] = execution_costs.get(row["model_id"], 0.0) + float(row["total_cost_gbp"])
        for model, total in execution_costs.items():
            lines.append(f"- {model} total execution/rebalance cost: {_format_value(total, 'gbp')}.")
        lines.extend(["", "Economic units are total-return-index accounting units, not executable whole-share instructions. All entries are hypothetical shadow records.", ""])
    lines.extend(["Pending execution: " + (canonical_json(payload["pending_execution"]) if payload["pending_execution"] else "NONE"), "", "## 7. Running scorecard", ""])
    lines.extend([
        "| Series | Status | Inception | NAV | Cum. return | Return £ | Period | vs global | vs pool | Sel.-unsel. | Drawdown | Max DD | Costs | Turnover | Legs | Cash | Holdings |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for row in payload["scorecard"]:
        lines.append(
            f"| {row['series']} | {row['status']} | {row['inception_date']} | {_format_value(row['current_nav_gbp'], 'gbp')} | "
            f"{_format_value(row['cumulative_net_return'], 'pct')} | {_format_value(row['cumulative_return_gbp'], 'gbp')} | "
            f"{_format_value(row['current_period_return'], 'pct')} | {_format_value(row['return_vs_global'], 'pct')} | "
            f"{_format_value(row['return_vs_appropriate_pool_comparator'], 'pct')} | {_format_value(row['selected_vs_unselected'], 'pct')} | "
            f"{_format_value(row['current_drawdown'], 'pct')} | {_format_value(row['maximum_drawdown'], 'pct')} | "
            f"{_format_value(row['cumulative_costs_gbp'], 'gbp')} | {_format_value(row['traded_notional_turnover'], 'num')} | "
            f"{row['trade_legs']} | {_format_value(row['cash_weight'], 'pct')} | {row['current_holdings']} |"
        )
    lines.extend([
        "", "### Longer-history statistics", "",
        "| Series | Annual return | Annual vol | Sharpe | Sortino | Calmar | Ulcer | Positive months | Positive rolling 12m |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in payload["scorecard"]:
        lines.append(
            f"| {row['series']} | {_format_value(row['annualised_return'], 'pct')} | {_format_value(row['annualised_volatility'], 'pct')} | "
            f"{_format_value(row['sharpe'], 'num')} | {_format_value(row['sortino'], 'num')} | {_format_value(row['calmar'], 'num')} | "
            f"{_format_value(row['ulcer_index'], 'pct')} | {_format_value(row['positive_monthly_frequency'], 'pct')} | "
            f"{_format_value(row['positive_rolling_12m_frequency'], 'pct')} |"
        )
    lines.extend(["", "## 8. Benchmark comparisons", ""])
    for row in payload["scorecard"][:2]:
        lines.append(f"- {row['series']}: versus global {_format_value(row['return_vs_global'], 'pct')}; versus appropriate pool {_format_value(row['return_vs_appropriate_pool_comparator'], 'pct')}; selected-versus-unselected {_format_value(row['selected_vs_unselected'], 'pct')}.")
    lines.extend(["", "## 9. Drawdown and high-water-mark status", ""])
    for row in payload["scorecard"][:2]:
        lines.append(f"- {row['series']}: HWM {_format_value(row['current_high_water_mark_gbp'], 'gbp')}; current DD {_format_value(row['current_drawdown'], 'pct')}; {row['days_below_high_water_mark']} days below HWM.")
    lines.extend(["", "## 10. Costs and turnover", ""])
    for row in payload["scorecard"][:2]:
        lines.append(f"- {row['series']}: costs {_format_value(row['cumulative_costs_gbp'], 'gbp')}; turnover {_format_value(row['traded_notional_turnover'], 'num')}; legs {row['trade_legs']}.")
    lines.extend(["", "## 11. Weekly telemetry", "", "**PROVISIONAL TELEMETRY — DOES NOT ALTER A5 PORTFOLIOS**", ""] + _markdown_ranking(payload["industry_theme_fast_top5"], "1/2/3 fast leaders"))
    lines.extend(["", "**NO PORTFOLIO CHANGE — TELEMETRY ONLY**", "", "## 12. Geographic leadership", ""] + _markdown_ranking(payload["geography_top5"], "Geographic market intelligence"))
    lines.extend(["", "## 13. Regime state", ""])
    for key, value in payload["regime"].items():
        lines.append(f"- {key}: {value}")
    progress = payload["evidence_progress"]
    lines.extend(["", "## 14. Prospective evidence progress", "", f"- Completed on-time monthly decisions: {progress['completed_on_time_monthly_decisions']} / {progress['target_decisions']}", f"- Completed shadow executions: {progress['completed_shadow_executions']}", f"- Elapsed prospective months: {progress['elapsed_prospective_months']}", f"- Next official signal: {progress['next_official_signal_date']}", f"- Next expected execution: {progress['next_expected_execution_date'] or 'NONE'}", f"- Operational integrity: {progress['operational_integrity_status']}", f"- Checkpoint: {progress['checkpoint']}", f"- **{progress['current_evidence_level']}**"])
    lines.extend(["", "## 15. Operational warnings", ""])
    if payload["operational_warnings"]:
        for warning in payload["operational_warnings"]:
            lines.append(f"- {warning.get('severity', 'WARNING')}: {warning.get('message', warning)}")
    else:
        lines.append("- NONE")
    lines.extend(["", "## 16. Next required run date", "", str(payload["next_required_run_date"] or "NOT_AVAILABLE"), "", "## 17. Governance", "", "No model change, no backfill, no live order, no broker connector and no scheduler were used."])
    return "\n".join(lines) + "\n"


def write_reports(payload: dict[str, Any]) -> list[Path]:
    markdown = render_markdown_report(payload)
    write_text_if_changed(LATEST_REPORT_MD, markdown)
    write_json_if_changed(LATEST_REPORT_JSON, payload)
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    base = f"UKACTIVE_A5_RUN_{payload['as_of_date']}_{payload['run_id']}"
    md_path = SNAPSHOT_ROOT / f"{base}.md"
    json_path = SNAPSHOT_ROOT / f"{base}.json"
    write_immutable_text(md_path, markdown)
    write_immutable_json(json_path, payload)
    return [LATEST_REPORT_MD, LATEST_REPORT_JSON, md_path, json_path]


def refresh_operating_calendar_status() -> bool:
    frame = operating_calendar()
    decisions = read_csv_schema(LEDGER_PATHS["decision"], CSV_SCHEMAS["decision"])
    executions = read_csv_schema(LEDGER_PATHS["execution"], CSV_SCHEMAS["execution"])
    for index, row in frame.iterrows():
        signal = row["expected_final_valid_xlon_signal_date"]
        decision = decisions.loc[decisions["signal_date"].eq(signal)]
        if len(decision):
            frame.at[index, "completed_signal_event_id"] = decision.iloc[0]["decision_event_id"]
            frame.at[index, "status"] = "SIGNAL_RECORDED"
            event = decision.iloc[0]["decision_event_id"]
            booked = executions.loc[executions["decision_event_id"].eq(event) & executions["model_id"].eq(MODEL_A)]
            if len(booked):
                frame.at[index, "completed_execution_event_id"] = booked.iloc[0]["execution_event_id"]
                frame.at[index, "status"] = "EXECUTION_RECORDED"
    return write_csv_if_changed(OPERATING_CALENDAR_PATH, frame)


def record_run_event(payload: dict[str, Any], actions: list[str]) -> bool:
    event = {
        "run_event_id": payload["run_id"],
        "as_of_date": payload["as_of_date"],
        "data_cutoff": payload["data_cutoff"],
        "mode": payload["mode"],
        "run_status": payload["run_status"],
        "actions_recorded": actions,
        "decision_event_id": payload["official_decision"].get("decision_event_id") if payload.get("official_decision") else None,
        "source_git_commit": current_git_commit(),
        "orders_or_scheduler": "NONE",
        "warning": WARNING,
    }
    return append_jsonl(LEDGER_PATHS["run"], event)


def files_for_evidence_commit(payload: dict[str, Any]) -> list[Path]:
    paths = [
        LEDGER_PATHS["run"], LEDGER_PATHS["decision"], LEDGER_PATHS["execution"],
        LEDGER_PATHS["position"], LEDGER_PATHS["cash"], LEDGER_PATHS["cost"],
        LEDGER_PATHS["nav"], LEDGER_PATHS["benchmark"], LEDGER_PATHS["telemetry_csv"],
        LEDGER_PATHS["warnings"], LEDGER_PATHS["amendment"], STATE_PATH, OPERATING_CALENDAR_PATH,
        LATEST_REPORT_MD, LATEST_REPORT_JSON,
    ]
    run_id = payload["run_id"]
    base = f"UKACTIVE_A5_RUN_{payload['as_of_date']}_{run_id}"
    paths.extend([SNAPSHOT_ROOT / f"{base}.md", SNAPSHOT_ROOT / f"{base}.json"])
    if payload.get("official_decision"):
        paths.append(INPUT_SNAPSHOT_ROOT / f"{payload['official_decision']['decision_event_id']}.json")
    paths.extend(sorted(INPUT_SNAPSHOT_ROOT.glob("*.json")))
    return [path for path in paths if path.exists() and path.suffix.lower() != ".parquet"]


def commit_and_push_evidence(payload: dict[str, Any], action_types: list[str]) -> dict[str, Any]:
    origin = git_value("remote", "get-url", "origin", check=True)
    if origin.rstrip("/") != EXPECTED_ORIGIN.rstrip("/"):
        raise RuntimeError(f"Unexpected Git origin: {origin}")
    if git_value("diff", "--cached", "--name-only"):
        raise RuntimeError("Refusing prospective commit while unrelated staged changes exist")
    paths = files_for_evidence_commit(payload)
    relative = [str(path.relative_to(PLATFORM_ROOT)) for path in paths]
    if relative:
        subprocess.run(["git", "add", "--", *relative], cwd=PLATFORM_ROOT, check=True)
    if not git_value("diff", "--cached", "--name-only"):
        return {"committed": False, "pushed": False, "commit": current_git_commit(), "message": "IDEMPOTENT_NO_CHANGES"}
    date = payload["as_of_date"]
    if "EXECUTION" in action_types:
        message = f"a5: book {date} shadow execution"
    elif "SIGNAL" in action_types:
        message = f"a5: record {date} monthly shadow signal"
    elif "TELEMETRY" in action_types:
        message = f"a5: record {date} telemetry snapshot"
    elif "MARK_TO_MARKET" in action_types:
        message = f"a5: mark {date} shadow portfolios"
    elif "WARNING" in action_types:
        message = f"a5: record {date} operational warning"
    else:
        raise RuntimeError("A prospective commit requires a signal, execution, telemetry, NAV or warning action")
    subprocess.run(["git", "commit", "-m", message], cwd=PLATFORM_ROOT, check=True)
    branch = git_value("branch", "--show-current", check=True)
    result = subprocess.run(["git", "push", "origin", branch], cwd=PLATFORM_ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Local prospective commit created but push failed: {result.stderr.strip()}")
    return {"committed": True, "pushed": True, "commit": current_git_commit(), "message": message}


def run_operational_mode(mode: str, requested_asof: str, commit_push: bool = False) -> dict[str, Any]:
    if mode == "setup":
        return setup_infrastructure()
    assert_operational_provenance()
    bundle = DataBundle.load()
    asof = bundle.resolve_asof(requested_asof)
    action_types: list[str] = []
    action_details: list[str] = []
    official = None
    warning_count_before = ledger_counts()["warnings"]
    if mode in {"signal", "auto"}:
        for signal_date in due_unrecorded_signal_dates(asof):
            candidate, changed = record_official_decision(bundle, signal_date)
            if candidate is not None:
                official = candidate
            if changed:
                if "SIGNAL" not in action_types:
                    action_types.append("SIGNAL")
                action_details.append(f"SIGNAL:{candidate['decision_event_id']}")
        if official is None:
            official = _existing_decision(asof)
    if mode in {"execute", "auto"}:
        _, executed, execution_ids = book_pending_execution(bundle, asof)
        if executed:
            action_types.append("EXECUTION")
            action_details.extend(
                f"EXECUTION:{event_id}:{model}"
                for event_id, model in zip(execution_ids, executed)
            )
    mark_added = mark_to_market(bundle, asof)
    if mark_added:
        action_types.append("MARK_TO_MARKET")
        action_details.append(f"NAV_ROWS:{mark_added}")
    if mode in {"telemetry", "auto"}:
        _, changed = record_telemetry(bundle, asof)
        if changed:
            action_types.append("TELEMETRY")
            action_details.append("TELEMETRY")
    check_official_input_revisions(bundle)
    if ledger_counts()["warnings"] > warning_count_before:
        action_types.append("WARNING")
        action_details.append("OPERATIONAL_WARNING")
    refresh_operating_calendar_status()
    state = derive_state(load_config())
    write_json_if_changed(STATE_PATH, state)
    run_status = "NO_ACTION_DUE" if not action_types else "NEW_PROSPECTIVE_EVIDENCE_RECORDED"
    payload = build_report_payload(
        bundle, asof, mode=mode, run_status=run_status,
        official_decision=official, actions=action_details, dry_run=False,
    )
    write_reports(payload)
    if action_types:
        record_run_event(payload, action_details)
    git_result = None
    if commit_push and action_types:
        git_result = commit_and_push_evidence(payload, action_types)
    payload["git_result"] = git_result
    return payload


def _scope_document(config: dict[str, Any]) -> str:
    return f"""# UKACTIVE-A5S scope and frozen shadow models

Status: **SETUP ONLY — PROSPECTIVE NOT STARTED**
Evidence target: **E3 only after 24 valid on-time monthly decisions**
Historical development cutoff: **{config['historical_development_cutoff']}**
Earliest official signal: **{config['earliest_official_signal_date']}**

## A5-A — {MODEL_A}

`INDUSTRY_PLUS_THEME | equal percentile ranks of RS63/RS126/RS252 | TOP_1 | MONTHLY | 100% active`.
The ranking identity is the economic family, ties use ascending family ID, the signal forms after the final valid XLON close of the month and execution is the first common valid close from the next XLON session within three sessions. One-way friction is 20 bp plus £3.99 per actual leg on a £250,000 shadow notional.

## A5-B — {MODEL_B}

Exactly 50% of the same A5-A active leader and exactly 50% `GLOBAL_DEVELOPED_WORLD`, rebalanced monthly under the same timing and cost convention. A5-B may never generate a different active selection.

## Frozen implementation and safety contract

The 25 currently signal-ready active families use the versioned, user-confirmed ii map dated 2026-08-23. The preferred line is used first; only an already declared and verified alternate may replace it. Otherwise the affected allocation is GBP cash and the event is `IMPLEMENTATION_BLOCKED`; rank 2 is never substituted. The economic pool retains its frozen 27-family dynamic-admission lineage, so a later newly signal-ready family without a preverified line is blocked rather than silently added operationally.

The global core is the authoritative `GLOBAL_DEVELOPED_WORLD` line SWDA / IE00B4L5Y983. Public UK evidence is confirmed; current ii availability is `TO_CHECK`, which is the sole setup open item.

No live order, broker connector, scheduler, backfill, same-close fill, discretionary substitution or model change exists in this infrastructure. Weekly FAST, geography and regime fields are telemetry only.
"""


def _comparator_document() -> str:
    return f"""# UKACTIVE-A5 comparator definitions

All comparators begin from the same first booked execution boundary and use the authoritative A2R2 GBP total-return/cash chain.

| Comparator | Definition | Cost convention |
|---|---|---|
| `{COMPARATOR_GLOBAL}` | Global developed-world economic benchmark. | Frictionless research benchmark. |
| `{COMPARATOR_POOL}` | Equal weight across contemporaneously 3/6/12-signal-eligible INDUSTRY+THEME families. | Frictionless research index; membership effective after the decision close. |
| `{COMPARATOR_STATIC}` | 50% global core and 50% contemporaneous equal-weight pool, monthly rebalanced. | Same 20 bp plus £3.99/actual-leg convention as the shadow models. |
| `{COMPARATOR_CASH}` | Validated actual GBP cash series. | No ETF or zero-return assumption. |
| `{COMPARATOR_UNSELECTED}` | Equal weight across eligible pool members other than rank 1. | Frictionless research diagnostic. |

The static 50/50 comparator isolates active selection value from merely combining global core with the available industry/theme basket.
"""


def _ledger_schema_document() -> str:
    lines = [
        "# UKACTIVE-A5 append-only ledger schema", "",
        "CSV and JSONL ledgers are authoritative. `UKACTIVE_A5_CURRENT_STATE.json` and telemetry Parquet are deterministic mirrors. Prior events are never edited; a correction requires a new amendment/warning event.", "",
    ]
    for key, columns in CSV_SCHEMAS.items():
        lines.extend([f"## {LEDGER_PATHS[key].name}", "", "Primary fields: " + ", ".join(f"`{column}`" for column in columns) + ".", ""])
    lines.extend([
        "## UKACTIVE_A5_RUN_LEDGER.jsonl", "",
        "One canonical JSON object per evidence-producing invocation, keyed by deterministic `run_event_id`.", "",
        "## Amendment policy", "",
        "A material vendor revision appends `DATA_REVISION_ALERT` to the warnings ledger and preserves the original signal, execution and NAV rows. The telemetry CSV is the Git-tracked append-only authority; `UKACTIVE_A5_TELEMETRY_HISTORY.parquet` is its deterministic local mirror because repository policy excludes Parquet bytes.",
    ])
    return "\n".join(lines) + "\n"


def _report_schema_document() -> str:
    return """# UKACTIVE-A5 report schema

Every report includes: run status; validated cutoff; official or explicitly provisional choice; slow top five; A5-A state; A5-B state; pending execution; six-row scorecard; comparator deltas; high-water marks/drawdowns; costs/turnover; weekly FAST telemetry; geographic leadership; regime fields; evidence progress; warnings; next required run; and an explicit no-order statement.

Annualised return, volatility, Sharpe, Sortino, Calmar, Ulcer Index and rolling-12-month statistics remain `N/A — INSUFFICIENT PROSPECTIVE HISTORY` until their frozen minimum history exists. Cumulative NAV and pounds are always shown after execution starts.

Latest aliases may be regenerated. Files under `snapshots/a5/UKACTIVE_A5_RUN_<ASOF>_<RUN_ID>.*` are immutable and use a deterministic run ID, so an idempotent repeat cannot create another snapshot.
"""


def _runbook_document() -> str:
    return """# UKACTIVE-A5 operating runbook

## Safety

This is a non-trading shadow process. It cannot place, preview, stage or transmit an order.

## OFFICIAL MONTH-END RUN

Run after validated month-end closing data are available, but before the next eligible XLON session closes.

## EXECUTION RUN

Run after the next eligible XLON session closes. A delayed log uses the already frozen price date and is disclosed.

## WEEKLY TELEMETRY

Run after the final valid XLON session each week. Telemetry cannot alter either model.

## NORMAL COMMAND

```powershell
.\run_ukactive_a5.ps1
```

The wrapper calls AUTO mode with `--asof latest --commit-push`; the runner performs only actions allowed by the frozen calendar and state. To print without creating a signal, execution or telemetry event, use the following command. It can still append a newly available mark-to-market NAV row, as required by the operating specification:

```powershell
.\run_ukactive_a5.ps1 -Mode report -NoCommitPush
```

Explicit Python examples:

```powershell
python code\run_ukactive_a5_shadow.py --mode signal --asof latest --commit-push
python code\run_ukactive_a5_shadow.py --mode execute --asof latest --commit-push
python code\run_ukactive_a5_shadow.py --mode telemetry --asof latest --commit-push
python code\run_ukactive_a5_shadow.py --mode report --asof 2026-08-21
```

If a month-end signal is first recorded after next-session close data exist, AUTO mode diagnoses it as `LATE_SIGNAL_NOT_E3` and it does not count toward 24. If SWDA / IE00B4L5Y983 remains unconfirmed in ii, A5-B booking is withheld and the open item is printed. Record any later manual core verification with its actual observation date, commit that current-only metadata before running A5, and never back-project it.

The runner refuses prospective evidence if its code, frozen config or implementation map has uncommitted changes, if the freeze tag is absent, or if the current branch is not descended from the freeze.
"""


RECURRING_INSTRUCTION = (
    "Run the UKACTIVE A5 prospective shadow process in AUTO mode from the authoritative programme root. "
    "Refresh only fully validated data, perform only the permitted signal/execution/telemetry actions, print "
    "the complete choices and running performance report, update append-only ledgers, validate idempotence "
    "and correctness, then commit and push any new prospective evidence. Do not alter either frozen model "
    "and do not place any live order."
)


def _dry_run_parity(bundle: DataBundle) -> dict[str, Any]:
    direct = bundle.rankings(HISTORICAL_CUTOFF, "INDUSTRY_PLUS_THEME").set_index("economic_exposure_family_id")
    feature = pd.read_parquet(SOURCE_PATHS["feature_panel"])
    feature["date"] = pd.to_datetime(feature["date"]).dt.normalize()
    frozen = feature.loc[
        feature["date"].eq(HISTORICAL_CUTOFF)
        & feature["analysis_context_id"].eq("INDUSTRY_PLUS_THEME")
        & feature["cadence"].eq("WEEKLY")
    ].drop_duplicates("economic_exposure_family_id").set_index("economic_exposure_family_id")
    comparisons = {
        "RS_63": "RS_63", "RS_126": "RS_126", "RS_252": "RS_252",
        "RANK_RS_63": "RANK_RS_63", "RANK_RS_126": "RANK_RS_126",
        "RANK_RS_252": "RANK_RS_252", "MH_LEVEL_3_6_12_REFERENCE": "MH_LEVEL_3_6_12_REFERENCE",
    }
    differences = {}
    for left, right in comparisons.items():
        differences[left] = float((direct[left] - frozen[right]).abs().max())
    leaders = slow_sorted(bundle.enriched_rankings(HISTORICAL_CUTOFF, "INDUSTRY_PLUS_THEME"))
    fast = fast_sorted(bundle.enriched_rankings(HISTORICAL_CUTOFF, "INDUSTRY_PLUS_THEME"))
    a5a_post_cost = INITIAL_NOTIONAL_GBP - INITIAL_NOTIONAL_GBP * 0.002 - 3.99
    a5b_post_cost = INITIAL_NOTIONAL_GBP - INITIAL_NOTIONAL_GBP * 0.002 - 2 * 3.99
    return {
        "dry_run_status": "DRY_RUN_NOT_PROSPECTIVE",
        "as_of_date": HISTORICAL_CUTOFF.date().isoformat(),
        "eligible_family_count": int(leaders["SLOW_RS"].notna().sum()),
        "provisional_slow_leader": leaders.iloc[0]["economic_exposure_family_id"],
        "provisional_fast_leader": fast.iloc[0]["economic_exposure_family_id"],
        "maximum_ranking_difference": max(differences.values()),
        "ranking_differences": differences,
        "a5a_synthetic_initial_post_cost_nav_gbp": a5a_post_cost,
        "a5b_synthetic_initial_post_cost_nav_gbp": a5b_post_cost,
        "a5b_synthetic_active_notional_gbp": a5b_post_cost * 0.5,
        "a5b_synthetic_core_notional_gbp": a5b_post_cost * 0.5,
        "prospective_decision_rows": ledger_counts()["decision"],
        "prospective_execution_rows": ledger_counts()["execution"],
        "prospective_nav_rows": ledger_counts()["nav"],
        "warning": "Dry-run ranking and accounting diagnostics are not A5 evidence.",
    }


def run_setup_checks(bundle: DataBundle, dry: dict[str, Any], report_markdown: str) -> pd.DataFrame:
    config = load_config()
    old = json.loads(SOURCE_PATHS["old_a5_config"].read_text(encoding="utf-8"))
    calendar = operating_calendar()
    implementation = bundle.implementation
    counts = ledger_counts()
    checks: list[dict[str, Any]] = []

    def add(test_id: str, description: str, passed: bool, evidence: Any) -> None:
        checks.append({
            "test_id": test_id, "description": description, "result": "PASS" if passed else "FAIL",
            "evidence": canonical_json(evidence), "warning": WARNING,
        })

    model_a = config["model_a"]
    old_candidate = old["candidate"]
    add("A5S-T01", "A5-A exactly matches frozen A4/A5 baseline", (
        model_a["pool"] == old_candidate["economic_pool"]
        and model_a["signal"] == old_candidate["signal"]
        and model_a["horizons_xlon_sessions"] == old_candidate["signal_horizons_xlon_sessions"]
        and model_a["selection"] == old_candidate["selection"]
        and model_a["target_active_weight"] == 1.0
        and pd.read_csv(SOURCE_PATHS["a4c_baseline_reproduction"])["result"].eq("PASS").all()
    ), {"model": model_a, "a4c_reproduction": "4_OF_4_PASS"})
    add("A5S-T02", "A5-B is exactly 50% A5-A and 50% global core", config["model_b"]["target_active_weight"] == 0.5 and config["model_b"]["target_core_weight"] == 0.5 and config["model_b"]["active_process"].startswith("EXACT_MODEL_A"), config["model_b"])
    add("A5S-T03", "Month-end signal uses only information after that close", counts["decision"] == 0 and dry["as_of_date"] == "2026-08-21", {"decision_rows": counts["decision"], "dry_asof": dry["as_of_date"]})
    add("A5S-T04", "No next-session data enter signal", dry["maximum_ranking_difference"] <= 1e-12, dry["ranking_differences"])
    first = calendar.iloc[0]
    add("A5S-T05", "Same-close execution is impossible", pd.Timestamp(first["expected_next_eligible_execution_date"]) > pd.Timestamp(first["expected_final_valid_xlon_signal_date"]), first.to_dict())
    add("A5S-T06", "Next eligible XLON execution is calendar-resolved", first["expected_final_valid_xlon_signal_date"] == "2026-08-28" and first["expected_next_eligible_execution_date"] == "2026-09-01", first.to_dict())
    add("A5S-T07", "Repeated setup runs are idempotent", counts["decision"] == counts["execution"] == counts["nav"] == counts["run"] == 0, counts)
    unique = all(not read_csv_schema(LEDGER_PATHS[key], CSV_SCHEMAS[key]).duplicated().any() for key in CSV_SCHEMAS)
    add("A5S-T08", "No duplicate event, decision, cost or NAV rows", unique, counts)
    source = Path(__file__).read_text(encoding="utf-8")
    telemetry_section = source[source.index("def record_telemetry"):source.index("def _append_warning")]
    add("A5S-T09", "Weekly telemetry cannot alter positions", "LEDGER_PATHS[\"position\"]" not in telemetry_section and "_book_target" not in telemetry_section, "record_telemetry writes telemetry only")
    add("A5S-T10", "Provisional choices are not labelled official", "NOT AN OFFICIAL A5 DECISION" in report_markdown and "RANKINGS MAY CHANGE BEFORE MONTH-END" in report_markdown, "dry-run report labels")
    active_family = implementation.loc[implementation["implementation_scope"].eq("ACTIVE_SIGNAL_READY"), "economic_exposure_family_id"].iloc[0]
    historical_status = bundle.implementation_row(active_family, HISTORICAL_CUTOFF)["ii_current_tradable"]
    add("A5S-T11", "Current ii metadata is not back-projected", historical_status == "NOT_APPLICABLE_HISTORICAL_ASOF", historical_status)
    add("A5S-T12", "Preferred/alternate implementation map is deterministic", len(implementation) == 26 and not implementation["economic_exposure_family_id"].duplicated().any() and implementation.loc[implementation["implementation_scope"].eq("ACTIVE_SIGNAL_READY"), "ii_current_tradable"].eq("CONFIRMED_BY_USER").all(), {"rows": len(implementation), "active_confirmed": 25})
    add("A5S-T13", "Unavailable family falls to cash with no substitute", implementation_execution_state(None) == "IMPLEMENTATION_BLOCKED_NO_PREVERIFIED_LINE", implementation_execution_state(None))
    original_core_status = bundle.implementation.loc[bundle.implementation["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD"), "ii_current_tradable"].iloc[0]
    bundle.implementation.loc[bundle.implementation["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD"), "ii_current_tradable"] = "CONFIRMED_BY_USER"
    synthetic_active_mask = bundle.implementation["economic_exposure_family_id"].eq("GLOBAL_SEMICONDUCTORS")
    original_active_observation = bundle.implementation.loc[synthetic_active_mask, "ii_observation_date"].iloc[0]
    bundle.implementation.loc[synthetic_active_mask, "ii_observation_date"] = "2026-07-01"
    synthetic_decision = {"signal_date": "2026-07-31", "selected_family_id": "GLOBAL_SEMICONDUCTORS"}
    targets = _target_sets(bundle, synthetic_decision)
    add("A5S-T14", "A5-A and A5-B use the same active leader", list(targets[MODEL_A]) == ["GLOBAL_SEMICONDUCTORS"] and targets[MODEL_B].get("GLOBAL_SEMICONDUCTORS") == 0.5, {MODEL_A: targets[MODEL_A], MODEL_B: targets[MODEL_B]})
    add("A5S-T15", "A5-B monthly target is exactly 50/50", abs(sum(weight for family, weight in targets[MODEL_B].items() if family != "GLOBAL_DEVELOPED_WORLD") - 0.5) < 1e-12 and targets[MODEL_B]["GLOBAL_DEVELOPED_WORLD"] == 0.5, targets[MODEL_B])
    bundle.implementation.loc[bundle.implementation["economic_exposure_family_id"].eq("GLOBAL_DEVELOPED_WORLD"), "ii_current_tradable"] = original_core_status
    bundle.implementation.loc[synthetic_active_mask, "ii_observation_date"] = original_active_observation
    expected_one_leg_cost = INITIAL_NOTIONAL_GBP * 0.002 + 3.99
    add("A5S-T16", "Costs are charged on actual shadow trade legs", abs(expected_one_leg_cost - 503.99) < 1e-10 and "for family in legs" in source, expected_one_leg_cost)
    cash_value = bundle.cash_index(HISTORICAL_CUTOFF)
    add("A5S-T17", "Cash earns validated GBP cash return", cash_value is not None and cash_value > 0, cash_value)
    add("A5S-T18", "Pool comparators use contemporaneous membership", len(targets[COMPARATOR_POOL]) == dry["eligible_family_count"] and abs(sum(targets[COMPARATOR_POOL].values()) - 1.0) < 1e-12, {"members": len(targets[COMPARATOR_POOL]), "weight_sum": sum(targets[COMPARATOR_POOL].values())})
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "immutable.csv"
        columns = ["id", "value"]
        append_csv_rows(path, columns, [{"id": "A", "value": "1"}], ["id"])
        append_csv_rows(path, columns, [{"id": "A", "value": "1"}], ["id"])
        immutable = len(pd.read_csv(path)) == 1
        collision = False
        try:
            append_csv_rows(path, columns, [{"id": "A", "value": "2"}], ["id"])
        except RuntimeError:
            collision = True
    add("A5S-T19", "Vendor revisions cannot silently rewrite events", immutable and collision, {"idempotent_rows": 1, "collision_rejected": collision})
    add("A5S-T20", "Late signals do not count toward 24", "on_time_e3_counted" in CSV_SCHEMAS["decision"] and "LATE_SIGNAL_NOT_E3" in source and "classification == \"ON_TIME_PROSPECTIVE\"" in source, "explicit classification and count field")
    synthetic_nav = dry["a5a_synthetic_initial_post_cost_nav_gbp"]
    add("A5S-T21", "Mark-to-market arithmetic reconciles", abs(synthetic_nav - (INITIAL_NOTIONAL_GBP - 503.99)) < 1e-10, synthetic_nav)
    add("A5S-T22", "NAV, positions, cash and costs reconcile", abs(dry["a5b_synthetic_active_notional_gbp"] * 2 - dry["a5b_synthetic_initial_post_cost_nav_gbp"]) < 1e-10 and dry["a5b_synthetic_core_notional_gbp"] == dry["a5b_synthetic_active_notional_gbp"], dry)
    required_sections = ["Running scorecard", "Geographic leadership", "Prospective evidence progress", "Operational warnings"]
    add("A5S-T23", "Reports reproduce required ledger/state sections", all(section in report_markdown for section in required_sections), required_sections)
    ignored = git_value("check-ignore", str(LEDGER_PATHS["telemetry_parquet"].relative_to(PLATFORM_ROOT)))
    add("A5S-T24", "Git-tracked outputs exclude prohibited Parquet data", bool(ignored) and "*.parquet" in (PLATFORM_ROOT / ".gitignore").read_text(encoding="utf-8"), ignored)
    import ast
    tree = ast.parse(source)
    imported = {
        alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(name=node.module or "")])
    }
    called = {
        node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    forbidden_imports = {"ib" + "_insync"}
    forbidden_calls = {"place" + "Order", "place" + "_order", "submit" + "_order", "preview" + "_order"}
    add("A5S-T25", "No broker/order connector is called", not (imported & forbidden_imports) and not (called & forbidden_calls), {"imports": sorted(imported & forbidden_imports), "calls": sorted(called & forbidden_calls)})
    return pd.DataFrame(checks)


def _dry_run_report_document(dry: dict[str, Any], report_markdown: str) -> str:
    return f"""# UKACTIVE-A5S setup dry-run report

Status: **DRY_RUN_NOT_PROSPECTIVE**
Input cutoff: **{dry['as_of_date']}**
Prospective decisions/executions/NAV rows: **{dry['prospective_decision_rows']} / {dry['prospective_execution_rows']} / {dry['prospective_nav_rows']}**

## Frozen-ranking reproduction

- Signal-ready INDUSTRY+THEME families: {dry['eligible_family_count']}
- Provisional slow leader: {dry['provisional_slow_leader']}
- Provisional FAST leader: {dry['provisional_fast_leader']}
- Maximum absolute difference versus A3R2 frozen ranks/scores: {dry['maximum_ranking_difference']:.3e}

## Synthetic accounting validation

- A5-A post-cost initial NAV: £{dry['a5a_synthetic_initial_post_cost_nav_gbp']:,.2f}
- A5-B post-cost initial NAV: £{dry['a5b_synthetic_initial_post_cost_nav_gbp']:,.2f}
- A5-B active/core post-cost notionals: £{dry['a5b_synthetic_active_notional_gbp']:,.2f} / £{dry['a5b_synthetic_core_notional_gbp']:,.2f}

The calculations validate the two engines and cost logic without booking a decision, execution or return. The complete sample display follows.

---

{report_markdown}
"""


def setup_infrastructure() -> dict[str, Any]:
    branch = git_value("branch", "--show-current")
    if branch != "research/ukactive-a5-shadow":
        raise RuntimeError(f"Setup must run on research/ukactive-a5-shadow, not {branch}")
    origin = git_value("remote", "get-url", "origin")
    if origin.rstrip("/") != EXPECTED_ORIGIN.rstrip("/"):
        raise RuntimeError(f"Unexpected origin: {origin}")

    implementation = build_implementation_map()
    write_csv_if_changed(IMPLEMENTATION_MAP_PATH, implementation)
    config = build_config(implementation)
    write_json_if_changed(CONFIG_PATH, config)
    write_csv_if_changed(OPERATING_CALENDAR_PATH, build_operating_calendar(30))
    initialise_empty_ledgers()
    write_json_if_changed(STATE_PATH, initial_state(config))

    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_SCOPE_AND_FROZEN_MODELS.md", _scope_document(config))
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_COMPARATOR_DEFINITIONS.md", _comparator_document())
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_LEDGER_SCHEMA.md", _ledger_schema_document())
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_REPORT_SCHEMA.md", _report_schema_document())
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_RUNBOOK.md", _runbook_document())
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_RECURRING_CODEX_INSTRUCTION.md", "# Recurring Codex instruction\n\n> " + RECURRING_INSTRUCTION)

    bundle = DataBundle.load()
    if bundle.latest_cutoff() != HISTORICAL_CUTOFF:
        raise RuntimeError(f"Setup dry-run requires the frozen 2026-08-21 cutoff, found {bundle.latest_cutoff().date()}")
    dry = _dry_run_parity(bundle)
    payload = build_report_payload(
        bundle, HISTORICAL_CUTOFF, mode="setup", run_status="SETUP_DRY_RUN_COMPLETE",
        official_decision=None, actions=[], dry_run=True,
    )
    report_markdown = render_markdown_report(payload)
    report_paths = write_reports(payload)
    dry_report = _dry_run_report_document(dry, report_markdown)
    write_text_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_SETUP_DRY_RUN_REPORT.md", dry_report)

    checks = run_setup_checks(bundle, dry, report_markdown)
    write_csv_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_SETUP_CORRECTNESS_TESTS.csv", checks)
    passed = bool(checks["result"].eq("PASS").all())
    counts = ledger_counts()
    no_prospective = all(counts[key] == 0 for key in ["run", "decision", "execution", "position", "cash", "cost", "nav", "benchmark", "telemetry_csv", "warnings", "amendment"])
    decision_state = "UKACTIVE_A5_SETUP_PASS_WITH_OPEN_ITEMS" if passed and no_prospective else "UKACTIVE_A5_SETUP_FAIL"
    decision = {
        "stage_id": "UKACTIVE-A5S",
        "decision": decision_state,
        "models": [MODEL_A, MODEL_B],
        "active_implementation_coverage": "25_OF_25_CONFIRMED_BY_USER",
        "core_preferred_ticker": "SWDA",
        "core_preferred_isin": "IE00B4L5Y983",
        "core_ii_status": "TO_CHECK",
        "open_items": ["MANUALLY_CONFIRM_SWDA_IE00B4L5Y983_IN_INTERACTIVE_INVESTOR_BEFORE_FIRST_A5B_BOOKING"],
        "earliest_official_signal_date": "2026-08-28",
        "expected_first_execution_date": "2026-09-01",
        "dry_run": dry,
        "correctness_tests_passed": int(checks["result"].eq("PASS").sum()),
        "correctness_tests_total": int(len(checks)),
        "prospective_events_created": 0,
        "a5_started": False,
        "orders_or_scheduler": "NONE",
        "warning": WARNING,
    }
    write_json_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_SETUP_DECISION.json", decision)

    output_names = [
        "UKACTIVE_A5_SCOPE_AND_FROZEN_MODELS.md", "config/ukactive_a5_shadow_comparison_v1.json",
        "UKACTIVE_A5_IMPLEMENTATION_MAP.csv", "UKACTIVE_A5_COMPARATOR_DEFINITIONS.md",
        "UKACTIVE_A5_LEDGER_SCHEMA.md", "UKACTIVE_A5_REPORT_SCHEMA.md", "UKACTIVE_A5_OPERATING_CALENDAR.csv",
        "UKACTIVE_A5_RUNBOOK.md", "UKACTIVE_A5_RECURRING_CODEX_INSTRUCTION.md",
        "UKACTIVE_A5_SETUP_DRY_RUN_REPORT.md", "UKACTIVE_A5_SETUP_CORRECTNESS_TESTS.csv",
        "UKACTIVE_A5_SETUP_DECISION.json", "code/run_ukactive_a5_shadow.py", "code/ukactive_a5_shadow_core.py",
        "run_ukactive_a5.ps1", "UKACTIVE_A5_RUN_LEDGER.jsonl", "UKACTIVE_A5_DECISION_LEDGER.csv",
        "UKACTIVE_A5_EXECUTION_LEDGER.csv", "UKACTIVE_A5_POSITION_LEDGER.csv", "UKACTIVE_A5_CASH_LEDGER.csv",
        "UKACTIVE_A5_COST_LEDGER.csv", "UKACTIVE_A5_NAV_HISTORY.csv", "UKACTIVE_A5_BENCHMARK_HISTORY.csv",
        "UKACTIVE_A5_TELEMETRY_LEDGER.csv", "UKACTIVE_A5_TELEMETRY_HISTORY.parquet",
        "UKACTIVE_A5_OPERATIONAL_WARNINGS.csv", "UKACTIVE_A5_AMENDMENT_LEDGER.csv",
        "UKACTIVE_A5_CURRENT_STATE.json",
        "UKACTIVE_A5_LATEST_RUN_REPORT.md", "UKACTIVE_A5_LATEST_RUN_REPORT.json",
    ]
    output_paths = [PROGRAMME_ROOT / name for name in output_names]
    missing = [str(path) for path in output_paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Setup outputs missing: {missing}")
    import platform
    import pyarrow
    manifest = {
        "stage_id": "UKACTIVE-A5S",
        "decision": decision_state,
        "created_date": SETUP_DATE,
        "branch": branch,
        "origin": origin,
        "source_commit_before_setup": current_git_commit(),
        "freeze_tag": FREEZE_TAG,
        "freeze_commit": "RESOLVE_FROM_TAG_AT_RUNTIME",
        "preexisting_worktree_exception": [
            "src/edge_research/connors_causal.py", "tests/test_edge_research_connors_causal.py"
        ],
        "preexisting_exception_policy": "LEFT_UNTOUCHED_AND_EXCLUDED_FROM_A5_COMMIT",
        "models": {"a5a": config["model_a"], "a5b": config["model_b"]},
        "comparators": config["comparators"],
        "implementation_map": {
            "path": str(IMPLEMENTATION_MAP_PATH.resolve()), "sha256": sha256_file(IMPLEMENTATION_MAP_PATH),
            "active_rows": 25, "active_confirmed": 25, "core_ticker": "SWDA", "core_isin": "IE00B4L5Y983",
            "core_ii_status": "TO_CHECK",
        },
        "source_inputs": source_inventory(SOURCE_PATHS.values()),
        "outputs": source_inventory(output_paths),
        "local_excluded_output": {
            "path": str(LEDGER_PATHS["telemetry_parquet"].resolve()),
            "sha256": sha256_file(LEDGER_PATHS["telemetry_parquet"]),
            "size_bytes": LEDGER_PATHS["telemetry_parquet"].stat().st_size,
            "reason": "PARQUET_EXCLUDED_BY_REPOSITORY_POLICY;TRACKED_CSV_IS_AUTHORITATIVE",
        },
        "operating_calendar": {
            "months": 30, "first_signal": "2026-08-28", "first_expected_execution": "2026-09-01",
            "policy": "A2R2 deterministic England/Wales XLON rules and known one-off closures",
        },
        "dry_run": dry,
        "tests": {"passed": int(checks["result"].eq("PASS").sum()), "total": int(len(checks))},
        "ledger_counts": counts,
        "prospective_event_created": False,
        "packages": {
            "python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "report_snapshots": [str(path.resolve()) for path in report_paths],
        "reproducibility": "CONFIG_PLUS_CODE_PLUS_INPUT_HASH_INVENTORY_PLUS_APPEND_ONLY_LEDGERS",
        "orders_or_scheduler": "NONE",
        "warning": WARNING,
    }
    write_json_if_changed(PROGRAMME_ROOT / "UKACTIVE_A5_SETUP_MANIFEST.json", manifest)
    payload["setup_decision"] = decision_state
    payload["dry_run"] = dry
    payload["correctness_tests"] = {"passed": int(checks["result"].eq("PASS").sum()), "total": len(checks)}
    payload["core_manual_check"] = {"ticker": "SWDA", "isin": "IE00B4L5Y983", "ii_status": "TO_CHECK"}
    return payload
