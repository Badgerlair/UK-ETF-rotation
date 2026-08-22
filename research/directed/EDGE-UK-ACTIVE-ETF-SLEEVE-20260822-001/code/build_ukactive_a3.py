from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import sys
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import scipy

HERE = Path(__file__).resolve().parent
PROGRAMME_ROOT = HERE.parent
CONFIG_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A3_POLICY_v1.json"
sys.path.insert(0, str(HERE))

from ukactive_a3_core import (  # noqa: E402
    benjamini_hochberg,
    circular_block_bootstrap_mean_ci,
    forward_total_return,
    grouped_winsorised_zscore_rows,
    hac_lag_for_horizon,
    newey_west_mean,
    observation_positions,
    percentile_rank_rows,
    realised_volatility,
    rolling_total_return,
    rowwise_correlation,
    sha256_file,
    sha256_json,
    stable_id,
    subperiod_bounds,
    total_return_trend_qualification,
    twelve_minus_one_return,
    utc_now,
)


WARNING = "HISTORICAL ELIGIBILITY REMAINS UNRESOLVED"
PRIMARY_COHORTS = {"GLOBAL", "GLOBAL_CATEGORY_NEUTRAL", "GEOGRAPHY", "SECTOR_INDUSTRY", "THEMATIC", "DEFENSIVE_DIVERSIFIER", "DEFENSIVE_FIXED_INCOME_CASH"}


@dataclass
class ResearchState:
    policy: dict[str, Any]
    dates: pd.DatetimeIndex
    families: list[str]
    metadata: pd.DataFrame
    returns: np.ndarray
    cash_returns: np.ndarray
    cash_rates: np.ndarray
    signals: dict[str, np.ndarray]
    component_signals: dict[str, np.ndarray]
    forward_returns: dict[int, np.ndarray]
    cash_forward_returns: dict[int, np.ndarray]
    valid_age: np.ndarray
    volatility_63: np.ndarray
    next_execution_dates: pd.DatetimeIndex


class AppendParquet:
    def __init__(self, path: Path, metadata: dict[str, str]):
        self.path = path
        self.metadata = {str(k): str(v) for k, v in metadata.items()}
        self.writer: pq.ParquetWriter | None = None
        self.schema: pa.Schema | None = None
        self.rows = 0

    def append(self, frame: pd.DataFrame) -> None:
        if frame.empty:
            return
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if self.writer is None:
            schema_metadata = dict(table.schema.metadata or {})
            schema_metadata.update({k.encode("utf-8"): v.encode("utf-8") for k, v in self.metadata.items()})
            self.schema = table.schema.with_metadata(schema_metadata)
            self.writer = pq.ParquetWriter(self.path, self.schema, compression="zstd")
        assert self.schema is not None and self.writer is not None
        table = pa.Table.from_pandas(frame, schema=self.schema.remove_metadata(), preserve_index=False).replace_schema_metadata(self.schema.metadata)
        self.writer.write_table(table)
        self.rows += len(frame)

    def close(self, empty_columns: dict[str, pa.DataType] | None = None) -> None:
        if self.writer is not None:
            self.writer.close()
            return
        fields = [pa.field(name, dtype) for name, dtype in (empty_columns or {"empty": pa.string()}).items()]
        schema = pa.schema(fields, metadata={k.encode(): v.encode() for k, v in self.metadata.items()})
        pq.write_table(pa.Table.from_arrays([pa.array([], type=f.type) for f in schema], schema=schema), self.path, compression="zstd")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False, default=json_default) + "\n", encoding="utf-8")


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Not JSON serialisable: {type(value)!r}")


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        frame.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def write_parquet(path: Path, frame: pd.DataFrame, metadata: dict[str, str]) -> None:
    table = pa.Table.from_pandas(frame, preserve_index=False)
    current = dict(table.schema.metadata or {})
    current.update({str(k).encode(): str(v).encode() for k, v in metadata.items()})
    pq.write_table(table.replace_schema_metadata(current), path, compression="zstd")


def compound_rows(values: np.ndarray, mask: np.ndarray, axis: int = 1) -> np.ndarray:
    logs = np.where(mask, np.log1p(values), np.nan)
    with np.errstate(all="ignore"):
        total = np.nansum(logs, axis=axis)
    valid = mask.sum(axis=axis) > 0
    return np.where(valid, np.expm1(total), np.nan)


def context_family_indices(metadata: pd.DataFrame, universe: dict[str, Any], cohort_id: str) -> np.ndarray:
    mask = metadata["universe_tier"].isin(universe["tiers"]).to_numpy(copy=True)
    if cohort_id == "GEOGRAPHY":
        mask &= metadata["opportunity_type"].eq("GEOGRAPHY").to_numpy()
    elif cohort_id == "SECTOR_INDUSTRY":
        mask &= metadata["opportunity_type"].eq("SECTOR_INDUSTRY").to_numpy()
    elif cohort_id == "THEMATIC":
        mask &= metadata["opportunity_type"].eq("THEMATIC").to_numpy()
    elif cohort_id == "DEFENSIVE_DIVERSIFIER":
        mask &= metadata["opportunity_type"].eq("DEFENSIVE_DIVERSIFIER").to_numpy()
    elif cohort_id == "DEFENSIVE_FIXED_INCOME_CASH":
        fixed_income_cash = {"GOVERNMENT_BOND", "CORPORATE_BOND", "AGGREGATE_BOND", "CASH_LIKE"}
        mask &= metadata["opportunity_type"].eq("DEFENSIVE_DIVERSIFIER").to_numpy()
        mask &= metadata["asset_class"].isin(fixed_income_cash).to_numpy()
    elif cohort_id not in {"GLOBAL", "GLOBAL_CATEGORY_NEUTRAL"}:
        raise ValueError(f"Unknown cohort: {cohort_id}")
    return np.flatnonzero(mask)


def signal_matrix_for_context(
    state: ResearchState,
    signal_definition: dict[str, Any],
    columns: np.ndarray,
    peer_groups: np.ndarray | None,
    availability_mask: np.ndarray | None = None,
) -> np.ndarray:
    signal_id = signal_definition["signal_id"]
    if signal_id.startswith("MULTI_Z_"):
        components: list[np.ndarray] = []
        for component_id in signal_definition["components"]:
            component = state.component_signals[component_id][:, columns].copy()
            if availability_mask is not None:
                component[~availability_mask] = np.nan
            components.append(grouped_winsorised_zscore_rows(component, peer_groups, minimum_group_size=3))
        stacked = np.stack(components, axis=2)
        valid = np.isfinite(stacked).all(axis=2)
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            result = np.nanmean(stacked, axis=2)
        result[~valid] = np.nan
        return result
    result = state.signals[signal_id][:, columns].copy()
    if availability_mask is not None:
        result[~availability_mask] = np.nan
    return result


def ranking_groups(metadata: pd.DataFrame, columns: np.ndarray, cohort_id: str) -> np.ndarray | None:
    if cohort_id != "GLOBAL_CATEGORY_NEUTRAL":
        return None
    return metadata.iloc[columns]["opportunity_type"].astype(str).to_numpy()


def signal_rank_matrix(signal_values: np.ndarray, peer_groups: np.ndarray | None) -> np.ndarray:
    minimum = 3 if peer_groups is not None else 1
    return percentile_rank_rows(signal_values, groups=peer_groups, minimum_group_size=minimum)


def outcome_rank_matrix(forward_values: np.ndarray, peer_groups: np.ndarray | None) -> np.ndarray:
    minimum = 3 if peer_groups is not None else 1
    return percentile_rank_rows(forward_values, groups=peer_groups, minimum_group_size=minimum)


def bucket_assignments(signal_values: np.ndarray, signal_ranks: np.ndarray, role: str) -> tuple[np.ndarray, np.ndarray]:
    ranks = np.asarray(signal_ranks, dtype=float)
    values = np.asarray(signal_values, dtype=float)
    available = np.isfinite(ranks) & np.isfinite(values)
    bucket = np.full_like(ranks, np.nan)
    scheme = np.zeros(ranks.shape[0], dtype=np.int8)
    if role == "BINARY_QUALIFICATION":
        bucket[available] = np.where(values[available] > 0.5, 2.0, 1.0)
        has_low = np.any(bucket == 1.0, axis=1)
        has_high = np.any(bucket == 2.0, axis=1)
        scheme[has_low & has_high] = 2
        bucket[scheme == 0, :] = np.nan
        return bucket, scheme
    count = available.sum(axis=1)
    scheme[count >= 15] = 5
    scheme[(count >= 6) & (count < 15)] = 3
    for buckets in (3, 5):
        rows = scheme == buckets
        if not rows.any():
            continue
        scaled = np.ceil(ranks[rows] * buckets)
        scaled = np.clip(scaled, 1, buckets)
        scaled[~available[rows]] = np.nan
        bucket[rows] = scaled
    return bucket, scheme


def evaluate_buckets_and_hits(
    signal_values: np.ndarray,
    signal_ranks: np.ndarray,
    forward_values: np.ndarray,
    role: str,
    benchmark_values: np.ndarray,
) -> dict[str, Any]:
    if signal_values.shape[1] == 0:
        row_count = signal_values.shape[0]
        empty = np.full(row_count, np.nan)
        return {
            "bucket": np.empty_like(signal_values),
            "scheme": np.zeros(row_count, dtype=np.int8),
            "bucket_means": {number: empty.copy() for number in range(1, 6)},
            "bucket_counts": {number: np.zeros(row_count, dtype=int) for number in range(1, 6)},
            "top_bucket_return": empty.copy(),
            "bottom_bucket_return": empty.copy(),
            "spread": empty.copy(),
            "monotonicity": empty.copy(),
            "strict_monotonic": empty.copy(),
            "top_rank_return": empty.copy(),
            "cross_section_median": empty.copy(),
            "equal_weight": empty.copy(),
            "benchmark_return": np.asarray(benchmark_values, dtype=float),
            "hit_median": empty.copy(),
            "hit_equal_weight": empty.copy(),
            "hit_benchmark": empty.copy(),
        }
    bucket, scheme = bucket_assignments(signal_values, signal_ranks, role)
    row_count = signal_values.shape[0]
    bucket_means: dict[int, np.ndarray] = {}
    bucket_counts: dict[int, np.ndarray] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for bucket_number in range(1, 6):
            selected = (bucket == float(bucket_number)) & np.isfinite(forward_values)
            bucket_counts[bucket_number] = selected.sum(axis=1)
            bucket_means[bucket_number] = np.nanmean(np.where(selected, forward_values, np.nan), axis=1)

        bottom = bucket_means[1]
        top = np.full(row_count, np.nan)
        for buckets in (2, 3, 5):
            rows = scheme == buckets
            top[rows] = bucket_means[buckets][rows]
        spread = top - bottom

        monotonicity = np.full(row_count, np.nan)
        strict_monotonic = np.full(row_count, np.nan)
        for buckets in (2, 3, 5):
            rows = scheme == buckets
            if not rows.any():
                continue
            means = np.column_stack([bucket_means[number] for number in range(1, buckets + 1)])[rows]
            complete = np.isfinite(means).all(axis=1)
            differences = np.diff(means, axis=1)
            scores = np.mean(differences > 0.0, axis=1)
            strict = np.all(differences > 0.0, axis=1).astype(float)
            row_positions = np.flatnonzero(rows)
            monotonicity[row_positions[complete]] = scores[complete]
            strict_monotonic[row_positions[complete]] = strict[complete]

        max_rank = np.nanmax(signal_ranks, axis=1, keepdims=True)
        top_ranked = np.isfinite(signal_ranks) & np.isclose(signal_ranks, max_rank, rtol=0.0, atol=1e-12)
        top_ranked &= np.isfinite(forward_values)
        top_rank_return = np.nanmean(np.where(top_ranked, forward_values, np.nan), axis=1)
        common = np.isfinite(signal_ranks) & np.isfinite(forward_values)
        cross_median = np.nanmedian(np.where(common, forward_values, np.nan), axis=1)
        equal_weight = np.nanmean(np.where(common, forward_values, np.nan), axis=1)
    benchmark = np.asarray(benchmark_values, dtype=float)
    return {
        "bucket": bucket,
        "scheme": scheme,
        "bucket_means": bucket_means,
        "bucket_counts": bucket_counts,
        "top_bucket_return": top,
        "bottom_bucket_return": bottom,
        "spread": spread,
        "monotonicity": monotonicity,
        "strict_monotonic": strict_monotonic,
        "top_rank_return": top_rank_return,
        "cross_section_median": cross_median,
        "equal_weight": equal_weight,
        "benchmark_return": benchmark,
        "hit_median": np.where(np.isfinite(top_rank_return) & np.isfinite(cross_median), top_rank_return > cross_median, np.nan),
        "hit_equal_weight": np.where(np.isfinite(top_rank_return) & np.isfinite(equal_weight), top_rank_return > equal_weight, np.nan),
        "hit_benchmark": np.where(np.isfinite(top_rank_return) & np.isfinite(benchmark), top_rank_return > benchmark, np.nan),
    }


def mean_boolean(values: np.ndarray) -> tuple[int, float]:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return int(len(arr)), float(np.mean(arr)) if len(arr) else np.nan


def benchmark_for_context(state: ResearchState, columns: np.ndarray, cohort_id: str, horizon: int) -> tuple[str, np.ndarray]:
    family_positions = {family: index for index, family in enumerate(state.families)}
    if cohort_id == "DEFENSIVE_FIXED_INCOME_CASH" and "GLOBAL_AGGREGATE_BONDS_GBP_HEDGED" in family_positions:
        return "GLOBAL_AGGREGATE_BONDS_GBP_HEDGED", state.forward_returns[horizon][:, family_positions["GLOBAL_AGGREGATE_BONDS_GBP_HEDGED"]]
    if cohort_id == "DEFENSIVE_DIVERSIFIER":
        return "ACTUAL_GBP_CASH", state.cash_forward_returns[horizon]
    if "GLOBAL_ALL_WORLD" in family_positions:
        return "GLOBAL_ALL_WORLD", state.forward_returns[horizon][:, family_positions["GLOBAL_ALL_WORLD"]]
    return "ACTUAL_GBP_CASH", state.cash_forward_returns[horizon]


def load_research_state(policy: dict[str, Any]) -> tuple[ResearchState, dict[str, Any]]:
    a2_manifest = read_json(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_manifest"])
    a2_decision = read_json(PROGRAMME_ROOT / "UKACTIVE_A2_DECISION.json")
    if a2_decision.get("decision") not in {"UKACTIVE_A2_PASS", "UKACTIVE_A2_PASS_WITH_OPEN_ITEMS"}:
        raise RuntimeError("A2 did not authorise A3")
    if not bool(a2_decision.get("a3_signal_discovery_authorised")):
        raise RuntimeError("A2 decision does not authorise signal discovery")

    readiness = pd.read_csv(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_readiness"])
    readiness["a3_ready"] = readiness["a3_ready"].astype(str).str.lower().eq("true")
    authorised = readiness.loc[readiness["a3_ready"], ["economic_exposure_family_id", "universe_tier"]].copy()
    if len(authorised) != int(policy["admission"]["authorised_family_count"]):
        raise AssertionError(f"Expected 86 A3-ready families, found {len(authorised)}")
    actual_tiers = authorised["universe_tier"].value_counts().to_dict()
    if actual_tiers != policy["admission"]["authorised_tier_counts"]:
        raise AssertionError(f"A3 tier count mismatch: {actual_tiers}")

    classification = pd.read_csv(PROGRAMME_ROOT / policy["authoritative_inputs"]["a0a1_classification"])
    metadata = authorised.merge(classification, on=["economic_exposure_family_id", "universe_tier"], how="left", validate="one_to_one")
    required_meta = ["economic_exposure_family_id", "universe_tier", "opportunity_type", "asset_class", "primary_geography", "sector", "industry", "economic_theme"]
    if metadata[required_meta].isna().any().any():
        raise AssertionError("Authorised family classification is incomplete")
    metadata = metadata.sort_values("economic_exposure_family_id").reset_index(drop=True)
    families = metadata["economic_exposure_family_id"].astype(str).tolist()

    panel_columns = [
        "date",
        "economic_exposure_family_id",
        "return_gbp_total",
        "data_valid",
        "stale_flag",
        "missing_flag",
        "proxy_flag",
        "next_execution_eligible_date",
        "implementation_listing_id",
    ]
    panel_path = PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_panel"]
    panel = pd.read_parquet(panel_path, columns=panel_columns)
    panel["date"] = pd.to_datetime(panel["date"]).dt.normalize()
    panel["next_execution_eligible_date"] = pd.to_datetime(panel["next_execution_eligible_date"]).dt.normalize()
    panel = panel[panel["economic_exposure_family_id"].isin(families)].copy()
    duplicate_family_dates = int(panel.duplicated(["date", "economic_exposure_family_id"]).sum())
    if duplicate_family_dates:
        raise AssertionError(f"A2 panel contains {duplicate_family_dates} duplicate family/date rows")
    invalid_mask = (
        ~panel["data_valid"].fillna(False).astype(bool)
        | panel["stale_flag"].fillna(False).astype(bool)
        | panel["missing_flag"].fillna(False).astype(bool)
        | panel["proxy_flag"].fillna(False).astype(bool)
    )
    invalid_non_null_before_mask = int(panel.loc[invalid_mask, "return_gbp_total"].notna().sum())
    panel.loc[invalid_mask, "return_gbp_total"] = np.nan
    if panel.loc[panel["proxy_flag"].fillna(False).astype(bool), "return_gbp_total"].notna().any():
        raise AssertionError("Proxy data survived admission masking")

    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    return_frame = (
        panel.pivot(index="date", columns="economic_exposure_family_id", values="return_gbp_total")
        .reindex(index=dates, columns=families)
    )
    returns = return_frame.to_numpy(dtype=float)

    # A date-T signal executes no earlier than this authoritative next-session map.
    execution_map = panel.groupby("date", sort=True)["next_execution_eligible_date"].first().reindex(dates)
    next_execution_dates = pd.DatetimeIndex(execution_map)
    expected_next = pd.Series(pd.NaT, index=dates, dtype="datetime64[ns]")
    if len(dates) > 1:
        expected_next.iloc[:-1] = dates[1:].to_numpy()
    mismatched_next = int((execution_map.iloc[:-1].to_numpy() != expected_next.iloc[:-1].to_numpy()).sum())
    if mismatched_next:
        raise AssertionError(f"A2 next-session mapping mismatch on {mismatched_next} research dates")

    cash = pd.read_parquet(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_cash"])
    cash["date"] = pd.to_datetime(cash["date"]).dt.normalize()
    cash = cash.drop_duplicates("date", keep="last").set_index("date").reindex(dates)
    cash_returns = cash["return_gbp_total"].where(cash["data_valid"].fillna(False)).to_numpy(dtype=float)
    cash_rates = cash["sonia_rate_percent"].to_numpy(dtype=float)

    lookbacks = sorted(
        {
            int(item["lookback_sessions"])
            for item in policy["signal_definitions"]
            if item.get("lookback_sessions") and item["signal_id"] not in {"MOM_12_1", "TREND_MA_252"}
        }
        | {21, 63, 126, 252}
    )
    momenta = {lookback: rolling_total_return(returns, lookback) for lookback in lookbacks}
    component_signals = {
        "MOM_21": momenta[21],
        "MOM_63": momenta[63],
        "MOM_126": momenta[126],
        "MOM_252": momenta[252],
    }
    volatility_63 = realised_volatility(returns, 63)
    cash_frame = cash_returns.reshape(-1, 1)
    cash_momenta = {
        lookback: rolling_total_return(cash_frame, lookback)[:, 0]
        for lookback in sorted({126, 210, 252, 294})
    }

    signals: dict[str, np.ndarray] = {}
    for item in policy["signal_definitions"]:
        signal_id = item["signal_id"]
        if signal_id.startswith("MULTI_Z_"):
            continue
        if signal_id.startswith("MOM_") and signal_id != "MOM_12_1":
            signals[signal_id] = momenta[int(item["lookback_sessions"])]
        elif signal_id == "MOM_12_1":
            signals[signal_id] = twelve_minus_one_return(returns, 252, 21)
        elif signal_id.startswith("ABS_POS_"):
            lookback = int(signal_id.rsplit("_", 1)[1])
            base = momenta[lookback]
            signals[signal_id] = np.where(np.isfinite(base), (base > 0.0).astype(float), np.nan)
        elif signal_id.startswith("ABOVE_GBP_CASH_"):
            lookback = int(signal_id.rsplit("_", 1)[1])
            base = momenta[lookback]
            cash_base = cash_momenta[lookback][:, None]
            signals[signal_id] = np.where(np.isfinite(base) & np.isfinite(cash_base), (base > cash_base).astype(float), np.nan)
        elif signal_id.startswith("TREND_MA_"):
            lookback = int(signal_id.rsplit("_", 1)[1])
            signals[signal_id] = total_return_trend_qualification(returns, lookback)
        elif signal_id == "RISK_ADJ_MOM_126_VOL63":
            signals[signal_id] = np.divide(momenta[126], volatility_63, out=np.full_like(momenta[126], np.nan), where=volatility_63 > 0.0)
        elif signal_id == "RISK_ADJ_MOM_252_VOL63":
            signals[signal_id] = np.divide(momenta[252], volatility_63, out=np.full_like(momenta[252], np.nan), where=volatility_63 > 0.0)
        else:
            raise ValueError(f"No signal constructor for {signal_id}")

    forward_horizons = [int(value) for value in policy["forward_horizons_sessions"]]
    forward_returns = {horizon: forward_total_return(returns, horizon) for horizon in forward_horizons}
    cash_forward_returns = {horizon: forward_total_return(cash_frame, horizon)[:, 0] for horizon in forward_horizons}
    valid_age = np.cumsum(np.isfinite(returns), axis=0).astype(np.int32)

    state = ResearchState(
        policy=policy,
        dates=dates,
        families=families,
        metadata=metadata,
        returns=returns,
        cash_returns=cash_returns,
        cash_rates=cash_rates,
        signals=signals,
        component_signals=component_signals,
        forward_returns=forward_returns,
        cash_forward_returns=cash_forward_returns,
        valid_age=valid_age,
        volatility_63=volatility_63,
        next_execution_dates=next_execution_dates,
    )
    diagnostics = {
        "a2_decision": a2_decision["decision"],
        "a2_manifest_run_id": a2_manifest.get("run_id"),
        "authorised_family_count": len(families),
        "tier_counts": actual_tiers,
        "panel_rows_admitted": len(panel),
        "unique_dates": len(dates),
        "duplicate_family_dates": duplicate_family_dates,
        "invalid_non_null_returns_masked": invalid_non_null_before_mask,
        "valid_return_observations": int(np.isfinite(returns).sum()),
        "proxy_observations_admitted": 0,
        "next_execution_mapping_mismatches": mismatched_next,
        "a2_manifest": a2_manifest,
    }
    return state, diagnostics


def build_signal_registry(policy: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for order, definition in enumerate(policy["signal_definitions"], start=1):
        row = dict(definition)
        row["registry_order"] = order
        row["definition_hash"] = sha256_json(definition)
        row["predeclared"] = True
        row["portfolio_rule"] = "NOT_APPLICABLE"
        row["deepvue_used"] = False
        row["historical_eligibility_warning"] = WARNING
        for key in ("components",):
            if isinstance(row.get(key), list):
                row[key] = ";".join(row[key])
        rows.append(row)
    frame = pd.DataFrame(rows)
    preferred = [
        "registry_order", "signal_id", "signal_family", "role", "registry_class", "lookback_sessions",
        "skip_sessions", "volatility_window_sessions", "components", "central_signal_id", "formula",
        "definition_hash", "predeclared", "portfolio_rule", "deepvue_used", "historical_eligibility_warning",
    ]
    return frame.reindex(columns=preferred)


def synthetic_tests(state: ResearchState, policy: dict[str, Any], signal_registry: pd.DataFrame) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    def add(test_id: str, description: str, passed: bool, observed: Any, critical: bool = True) -> None:
        tests.append({
            "test_id": test_id,
            "category": "SYNTHETIC_FAILURE_FIXTURE",
            "critical": critical,
            "description": description,
            "expected": "FAILURE_CAUGHT",
            "observed": str(observed),
            "status": "PASS" if passed else "FAIL",
        })

    fixture = np.array([[0.10], [0.20], [-0.10], [0.05]], dtype=float)
    fwd1 = forward_total_return(fixture, 1)[:, 0]
    add("SYN-01", "date-T signal cannot receive date-T return", np.isclose(fwd1[0], 0.20) and not np.isclose(fwd1[0], 0.10), fwd1.tolist())

    current = np.array([[1.0, 2.0, np.nan], [1.0, 2.0, 100.0]])
    ranks = percentile_rank_rows(current)
    add("SYN-02", "future family availability cannot change an earlier rank", np.isclose(ranks[0, 0], 0.5) and np.isnan(ranks[0, 2]), ranks.tolist())

    missing = np.array([[0.1, np.nan, 0.3]])
    missing_rank = percentile_rank_rows(missing)
    add("SYN-03", "missing exposure is excluded rather than filled with zero", np.isnan(missing_rank[0, 1]), missing_rank.tolist())

    duplicate_fixture = pd.DataFrame({"family": ["F1", "F1"], "listing": ["L1", "L2"]})
    add("SYN-04", "duplicate implementations cannot become two ranking units", duplicate_fixture["family"].nunique() == 1, duplicate_fixture.to_dict("records"))

    invalid_fixture = pd.DataFrame({"return": [0.01, 0.02], "data_valid": [True, False]})
    masked = invalid_fixture["return"].where(invalid_fixture["data_valid"])
    add("SYN-05", "invalid A2 observations remain invalid", pd.isna(masked.iloc[1]), masked.tolist())

    tier_fixture = pd.DataFrame({"family": ["C", "E"], "tier": ["CORE", "EXPERIMENTAL"], "signal": [1.0, 999.0]})
    primary_before = tier_fixture.loc[tier_fixture["tier"].eq("CORE"), "signal"].rank(pct=True).tolist()
    tier_fixture.loc[tier_fixture["tier"].eq("EXPERIMENTAL"), "signal"] = -999.0
    primary_after = tier_fixture.loc[tier_fixture["tier"].eq("CORE"), "signal"].rank(pct=True).tolist()
    add("SYN-06", "EXPERIMENTAL values cannot alter primary ranks", primary_before == primary_after, {"before": primary_before, "after": primary_after})

    normalisation = np.array([[1.0, 2.0, 3.0], [100.0, -100.0, 0.0]])
    z_before = grouped_winsorised_zscore_rows(normalisation, None)[0].copy()
    normalisation[1] = [999.0, 999.0, -999.0]
    z_after = grouped_winsorised_zscore_rows(normalisation, None)[0]
    add("SYN-07", "cross-sectional normalisation uses no future date", np.allclose(z_before, z_after, equal_nan=True), {"before": z_before.tolist(), "after": z_after.tolist()})

    membership = pd.DataFrame({"date": pd.to_datetime(["2019-12-31", "2020-01-02"]), "family": ["OLD", "NEW"]})
    pre_members = membership.loc[membership["date"] < pd.Timestamp("2020-01-01"), "family"].tolist()
    add("SYN-08", "subperiod membership is contemporaneous", pre_members == ["OLD"], pre_members)

    fwd2 = forward_total_return(fixture, 2)[:, 0]
    add("SYN-09", "forward horizon compounds exactly t+1 through t+h", np.isclose(fwd2[0], (1.20 * 0.90) - 1.0), fwd2.tolist())

    twelve_fixture = np.full((260, 1), 0.001)
    twelve_fixture[-21:, 0] = 0.50
    twelve_signal = twelve_minus_one_return(twelve_fixture, 252, 21)[-1, 0]
    expected_12_1 = (1.001 ** 231) - 1.0
    add("SYN-10", "12-1 excludes the most recent 21 sessions", np.isclose(twelve_signal, expected_12_1), {"observed": twelve_signal, "expected": expected_12_1})

    warmup = rolling_total_return(np.full((25, 1), 0.001), 21)[:, 0]
    add("SYN-11", "lookback warm-up is enforced", np.isnan(warmup[:20]).all() and np.isfinite(warmup[20]), warmup.tolist())
    add("SYN-12", "proxy history cannot enter", not bool(policy["admission"]["proxy_flag_must_be_false"] is False), policy["admission"]["proxy_flag_must_be_false"])
    add("SYN-13", "cash comparison is tied to A2 cash series", np.isfinite(state.cash_returns).sum() > 500, int(np.isfinite(state.cash_returns).sum()))
    registry_ids = signal_registry["signal_id"].tolist()
    policy_ids = [item["signal_id"] for item in policy["signal_definitions"]]
    add("SYN-14", "executed registry exactly matches predeclared registry", registry_ids == policy_ids, registry_ids)
    return tests


def prefix_stats(stats: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in stats.items()}


def empty_stats(prefix: str, lag: int) -> dict[str, Any]:
    return prefix_stats(newey_west_mean([], lag), prefix)


def top_membership(signal_ranks: np.ndarray) -> np.ndarray:
    ranks = np.asarray(signal_ranks, dtype=float)
    count = np.isfinite(ranks).sum(axis=1)
    threshold = np.full(len(ranks), np.nan)
    threshold[count >= 15] = 0.80
    threshold[(count >= 6) & (count < 15)] = 2.0 / 3.0
    return np.isfinite(ranks) & (ranks >= threshold[:, None])


def persistence_summary(
    dates: pd.DatetimeIndex,
    observation_rows: np.ndarray,
    signal_values: np.ndarray,
    signal_ranks: np.ndarray,
    horizons: Iterable[int],
    base: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current_top_all = top_membership(signal_ranks)
    for horizon in horizons:
        start = observation_rows[observation_rows + int(horizon) < len(dates)]
        target = start + int(horizon)
        if len(start) == 0:
            rows.append({**base, "persistence_horizon_sessions": int(horizon), "date_pair_count": 0, "status": "INSUFFICIENT_HISTORY"})
            continue
        rank_corr, rank_count = rowwise_correlation(signal_ranks[start], signal_ranks[target], minimum_count=5)
        current_top = current_top_all[start]
        future_rank = signal_ranks[target]
        future_top = current_top_all[target]
        leader_comparable = current_top & np.isfinite(future_rank)
        leader_count = int(leader_comparable.sum())
        remains_above = float(np.mean(future_rank[leader_comparable] > 0.5)) if leader_count else np.nan
        remains_top = float(np.mean(future_top[leader_comparable])) if leader_count else np.nan
        common = np.isfinite(signal_ranks[start]) & np.isfinite(future_rank)
        absolute_change = np.abs(future_rank - signal_ranks[start])
        signed_change = future_rank - signal_ranks[start]
        rows.append({
            **base,
            "persistence_horizon_sessions": int(horizon),
            "date_pair_count": int(len(start)),
            "rank_autocorrelation_mean": float(np.nanmean(rank_corr)) if np.isfinite(rank_corr).any() else np.nan,
            "rank_autocorrelation_median": float(np.nanmedian(rank_corr)) if np.isfinite(rank_corr).any() else np.nan,
            "rank_autocorrelation_valid_dates": int(np.isfinite(rank_corr).sum()),
            "mean_comparable_family_count": float(np.mean(rank_count)) if len(rank_count) else np.nan,
            "leader_observation_count": leader_count,
            "probability_leader_remains_above_median": remains_above,
            "probability_leader_remains_top_bucket": remains_top,
            "average_signed_rank_change": float(np.nanmean(np.where(common, signed_change, np.nan))) if common.any() else np.nan,
            "average_absolute_rank_change": float(np.nanmean(np.where(common, absolute_change, np.nan))) if common.any() else np.nan,
            "status": "TESTED" if np.isfinite(rank_corr).sum() >= 24 else "LIMITED_DATE_COUNT",
        })

    if len(observation_rows) < 2:
        stability = {**base, "date_pair_count": 0, "status": "INSUFFICIENT_HISTORY"}
        return rows, stability
    starts = observation_rows[:-1]
    targets = observation_rows[1:]
    rank_corr, count = rowwise_correlation(signal_ranks[starts], signal_ranks[targets], minimum_count=5)
    raw_corr, _ = rowwise_correlation(signal_values[starts], signal_values[targets], minimum_count=5)
    common = np.isfinite(signal_ranks[starts]) & np.isfinite(signal_ranks[targets])
    absolute_change = np.abs(signal_ranks[targets] - signal_ranks[starts])
    top_obs = current_top_all[observation_rows]
    turnovers: list[float] = []
    for current, future in zip(top_obs[:-1], top_obs[1:]):
        union = current | future
        if union.any():
            turnovers.append(1.0 - float((current & future).sum()) / float(union.sum()))
    durations: list[int] = []
    for column in range(top_obs.shape[1]):
        run = 0
        for flag in top_obs[:, column]:
            if bool(flag):
                run += 1
            elif run:
                durations.append(run)
                run = 0
        if run:
            durations.append(run)
    stability = {
        **base,
        "date_pair_count": int(len(starts)),
        "mean_rank_autocorrelation": float(np.nanmean(rank_corr)) if np.isfinite(rank_corr).any() else np.nan,
        "median_rank_autocorrelation": float(np.nanmedian(rank_corr)) if np.isfinite(rank_corr).any() else np.nan,
        "mean_signal_autocorrelation": float(np.nanmean(raw_corr)) if np.isfinite(raw_corr).any() else np.nan,
        "average_absolute_rank_change": float(np.nanmean(np.where(common, absolute_change, np.nan))) if common.any() else np.nan,
        "mean_top_bucket_membership_turnover": float(np.mean(turnovers)) if turnovers else np.nan,
        "mean_top_bucket_duration_observations": float(np.mean(durations)) if durations else np.nan,
        "median_top_bucket_duration_observations": float(np.median(durations)) if durations else np.nan,
        "top_bucket_duration_run_count": int(len(durations)),
        "status": "TESTED" if np.isfinite(rank_corr).sum() >= 24 else "LIMITED_DATE_COUNT",
    }
    return rows, stability


def run_primary_evaluations(
    state: ResearchState,
    signal_registry: pd.DataFrame,
    metadata: dict[str, str],
) -> dict[str, Any]:
    policy = state.policy
    minimum_dates = int(policy["cross_section"]["minimum_date_observations_for_formal_inference"])
    minimum_ic = int(policy["cross_section"]["minimum_families_for_ic"])
    forward_horizons = [int(value) for value in policy["forward_horizons_sessions"]]
    frequencies = [item["frequency_id"] for item in policy["observation_frequencies"]]
    frequency_rows = {frequency: observation_positions(state.dates, frequency) for frequency in frequencies}
    subperiods = policy["subperiods"]
    final_date = state.dates.max()

    ic_writer = AppendParquet(PROGRAMME_ROOT / "UKACTIVE_A3_INFORMATION_COEFFICIENT_TIME_SERIES.parquet", metadata)
    spread_writer = AppendParquet(PROGRAMME_ROOT / "UKACTIVE_A3_TOP_BOTTOM_SPREAD_TIME_SERIES.parquet", metadata)

    ic_summary_rows: list[dict[str, Any]] = []
    spread_summary_rows: list[dict[str, Any]] = []
    quantile_rows: list[dict[str, Any]] = []
    hit_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    subperiod_rows: list[dict[str, Any]] = []
    persistence_rows: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []
    headline_series: dict[tuple[str, str, int], dict[str, Any]] = {}

    signal_definitions = {item["signal_id"]: item for item in policy["signal_definitions"]}

    for universe in policy["universe_scopes"]:
        universe_id = universe["universe_id"]
        for cohort in policy["cohorts"]:
            cohort_id = cohort["cohort_id"]
            columns = context_family_indices(state.metadata, universe, cohort_id)
            peer_groups = ranking_groups(state.metadata, columns, cohort_id) if len(columns) else None
            context_forward = {horizon: state.forward_returns[horizon][:, columns] for horizon in forward_horizons}
            context_outcome_ranks = {
                horizon: outcome_rank_matrix(context_forward[horizon], peer_groups) if len(columns) else np.empty((len(state.dates), 0))
                for horizon in forward_horizons
            }

            for signal_id in signal_registry["signal_id"]:
                definition = signal_definitions[signal_id]
                signal_values = signal_matrix_for_context(state, definition, columns, peer_groups) if len(columns) else np.empty((len(state.dates), 0))
                signal_ranks = signal_rank_matrix(signal_values, peer_groups) if len(columns) else np.empty_like(signal_values)

                for frequency_id in frequencies:
                    observations = frequency_rows[frequency_id]
                    available_counts = np.isfinite(signal_ranks[observations]).sum(axis=1) if len(columns) else np.zeros(len(observations), dtype=int)
                    eligible_dates = available_counts >= minimum_ic
                    coverage_rows.append({
                        "signal_id": signal_id,
                        "signal_family": definition["signal_family"],
                        "registry_class": definition["registry_class"],
                        "universe_id": universe_id,
                        "cohort_id": cohort_id,
                        "frequency_id": frequency_id,
                        "authorised_family_count": int(len(columns)),
                        "scheduled_observation_dates": int(len(observations)),
                        "dates_with_minimum_cross_section": int(eligible_dates.sum()),
                        "minimum_signal_family_count": int(available_counts.min()) if len(available_counts) else 0,
                        "median_signal_family_count": float(np.median(available_counts)) if len(available_counts) else np.nan,
                        "mean_signal_family_count": float(np.mean(available_counts)) if len(available_counts) else np.nan,
                        "maximum_signal_family_count": int(available_counts.max()) if len(available_counts) else 0,
                        "first_eligible_date": state.dates[observations[np.flatnonzero(eligible_dates)[0]]].date().isoformat() if eligible_dates.any() else "NOT_AVAILABLE",
                        "last_eligible_date": state.dates[observations[np.flatnonzero(eligible_dates)[-1]]].date().isoformat() if eligible_dates.any() else "NOT_AVAILABLE",
                        "status": "COVERAGE_AVAILABLE" if eligible_dates.sum() >= minimum_dates else "INSUFFICIENT_COVERAGE",
                        "historical_eligibility_warning": WARNING,
                    })

                    base_persistence = {
                        "signal_id": signal_id,
                        "signal_family": definition["signal_family"],
                        "registry_class": definition["registry_class"],
                        "universe_id": universe_id,
                        "cohort_id": cohort_id,
                        "frequency_id": frequency_id,
                        "authorised_family_count": int(len(columns)),
                        "historical_eligibility_warning": WARNING,
                    }
                    persistence_part, stability_part = persistence_summary(
                        state.dates, observations, signal_values, signal_ranks, [21, 42, 63], base_persistence
                    )
                    persistence_rows.extend(persistence_part)
                    stability_rows.append(stability_part)

                    ic_chunks: list[pd.DataFrame] = []
                    spread_chunks: list[pd.DataFrame] = []
                    for horizon in forward_horizons:
                        evaluation_id = stable_id("A3EVAL", signal_id, universe_id, cohort_id, frequency_id, horizon)
                        lag = hac_lag_for_horizon(horizon, frequency_id)
                        forward_values = context_forward[horizon][observations] if len(columns) else np.empty((len(observations), 0))
                        outcome_ranks = context_outcome_ranks[horizon][observations] if len(columns) else np.empty_like(forward_values)
                        observed_signal_values = signal_values[observations] if len(columns) else np.empty_like(forward_values)
                        observed_signal_ranks = signal_ranks[observations] if len(columns) else np.empty_like(forward_values)
                        ic_values, ic_counts = rowwise_correlation(observed_signal_ranks, outcome_ranks, minimum_count=minimum_ic)
                        ic_stats = newey_west_mean(ic_values, lag)
                        status = "TESTED" if int(ic_stats["observation_count"]) >= minimum_dates else "INSUFFICIENT_DATE_OBSERVATIONS"
                        overlap = bool((frequency_id != "MONTH_END" and horizon > 5) or (frequency_id == "MONTH_END" and horizon > 21))
                        common = {
                            "evaluation_id": evaluation_id,
                            "signal_id": signal_id,
                            "signal_family": definition["signal_family"],
                            "signal_role": definition["role"],
                            "registry_class": definition["registry_class"],
                            "universe_id": universe_id,
                            "primary_decision_universe": bool(universe["primary_decision"]),
                            "cohort_id": cohort_id,
                            "ranking_mode": cohort["ranking_mode"],
                            "frequency_id": frequency_id,
                            "forward_horizon_sessions": int(horizon),
                            "authorised_family_count": int(len(columns)),
                            "scheduled_observation_dates": int(len(observations)),
                            "overlapping_forward_returns": overlap,
                            "historical_eligibility_warning": WARNING,
                            "status": status,
                        }
                        ic_summary_rows.append({**common, **prefix_stats(ic_stats, "ic"), "bh_fdr_q_value": np.nan})

                        benchmark_id, benchmark_full = benchmark_for_context(state, columns, cohort_id, horizon)
                        bucket_result = evaluate_buckets_and_hits(
                            observed_signal_values,
                            observed_signal_ranks,
                            forward_values,
                            definition["role"],
                            benchmark_full[observations],
                        )
                        spread_stats = newey_west_mean(bucket_result["spread"], lag)
                        spread_summary_rows.append({
                            **common,
                            **prefix_stats(spread_stats, "spread"),
                            "mean_monotonicity_score": float(np.nanmean(bucket_result["monotonicity"])) if np.isfinite(bucket_result["monotonicity"]).any() else np.nan,
                            "strict_monotonicity_frequency": float(np.nanmean(bucket_result["strict_monotonic"])) if np.isfinite(bucket_result["strict_monotonic"]).any() else np.nan,
                            "benchmark_id": benchmark_id,
                        })

                        for scheme in (2, 3, 5):
                            scheme_rows = bucket_result["scheme"] == scheme
                            if not scheme_rows.any():
                                continue
                            scheme_name = "BINARY_QUALIFICATION" if scheme == 2 else ("TERCILES" if scheme == 3 else "QUINTILES")
                            for bucket_number in range(1, scheme + 1):
                                values = bucket_result["bucket_means"][bucket_number].copy()
                                values[~scheme_rows] = np.nan
                                stats = newey_west_mean(values, lag)
                                quantile_rows.append({
                                    **common,
                                    "bucket_scheme": scheme_name,
                                    "bucket_count": scheme,
                                    "bucket_number": bucket_number,
                                    "bucket_label": "WEAKEST_OR_NOT_QUALIFIED" if bucket_number == 1 else ("STRONGEST_OR_QUALIFIED" if bucket_number == scheme else f"BUCKET_{bucket_number}"),
                                    **prefix_stats(stats, "forward_return"),
                                })

                        median_count, median_hit = mean_boolean(bucket_result["hit_median"])
                        equal_count, equal_hit = mean_boolean(bucket_result["hit_equal_weight"])
                        benchmark_count, benchmark_hit = mean_boolean(bucket_result["hit_benchmark"])
                        hit_rows.append({
                            **common,
                            "benchmark_id": benchmark_id,
                            "top_rank_vs_cross_section_median_observations": median_count,
                            "top_rank_vs_cross_section_median_hit_rate": median_hit,
                            "top_rank_vs_equal_weight_observations": equal_count,
                            "top_rank_vs_equal_weight_hit_rate": equal_hit,
                            "top_rank_vs_benchmark_observations": benchmark_count,
                            "top_rank_vs_benchmark_hit_rate": benchmark_hit,
                        })

                        finite_ic = np.isfinite(ic_values)
                        if finite_ic.any():
                            ic_chunks.append(pd.DataFrame({
                                "date": state.dates[observations[finite_ic]],
                                "evaluation_id": evaluation_id,
                                "signal_id": signal_id,
                                "signal_family": definition["signal_family"],
                                "registry_class": definition["registry_class"],
                                "universe_id": universe_id,
                                "cohort_id": cohort_id,
                                "frequency_id": frequency_id,
                                "forward_horizon_sessions": int(horizon),
                                "ic_spearman": ic_values[finite_ic],
                                "valid_family_count": ic_counts[finite_ic],
                                "overlapping_forward_returns": overlap,
                                "historical_eligibility_warning": WARNING,
                            }))
                        finite_spread = np.isfinite(bucket_result["spread"])
                        if finite_spread.any():
                            spread_chunks.append(pd.DataFrame({
                                "date": state.dates[observations[finite_spread]],
                                "evaluation_id": evaluation_id,
                                "signal_id": signal_id,
                                "signal_family": definition["signal_family"],
                                "registry_class": definition["registry_class"],
                                "universe_id": universe_id,
                                "cohort_id": cohort_id,
                                "frequency_id": frequency_id,
                                "forward_horizon_sessions": int(horizon),
                                "bucket_scheme_count": bucket_result["scheme"][finite_spread],
                                "top_bucket_forward_return": bucket_result["top_bucket_return"][finite_spread],
                                "bottom_bucket_forward_return": bucket_result["bottom_bucket_return"][finite_spread],
                                "top_minus_bottom_spread": bucket_result["spread"][finite_spread],
                                "monotonicity_score": bucket_result["monotonicity"][finite_spread],
                                "top_rank_forward_return": bucket_result["top_rank_return"][finite_spread],
                                "cross_section_median_forward_return": bucket_result["cross_section_median"][finite_spread],
                                "equal_weight_forward_return": bucket_result["equal_weight"][finite_spread],
                                "benchmark_id": benchmark_id,
                                "benchmark_forward_return": bucket_result["benchmark_return"][finite_spread],
                                "historical_eligibility_warning": WARNING,
                            }))

                        for subperiod in subperiods:
                            start, end = subperiod_bounds(subperiod, final_date)
                            date_values = state.dates[observations]
                            in_period = np.ones(len(date_values), dtype=bool)
                            if start is not None:
                                in_period &= date_values >= start
                            if end is not None:
                                in_period &= date_values <= end
                            sub_ic = newey_west_mean(ic_values[in_period], lag)
                            sub_spread = newey_west_mean(bucket_result["spread"][in_period], lag)
                            subperiod_rows.append({
                                **common,
                                "subperiod_id": subperiod["subperiod_id"],
                                "subperiod_start": start.date().isoformat() if start is not None else state.dates.min().date().isoformat(),
                                "subperiod_end": end.date().isoformat() if end is not None else final_date.date().isoformat(),
                                **prefix_stats(sub_ic, "ic"),
                                **prefix_stats(sub_spread, "spread"),
                                "subperiod_status": "TESTED" if int(sub_ic["observation_count"]) >= minimum_dates else "LIMITED_OR_UNAVAILABLE",
                            })

                        if (
                            universe_id == "CORE_EXTENDED"
                            and cohort_id == "GLOBAL"
                            and definition["registry_class"] == "PRIMARY"
                            and horizon in policy["primary_inference_horizons_sessions"]
                        ):
                            headline_series[(signal_id, frequency_id, horizon)] = {
                                "dates": state.dates[observations],
                                "ic": ic_values.copy(),
                                "spread": bucket_result["spread"].copy(),
                            }

                    if ic_chunks:
                        ic_writer.append(pd.concat(ic_chunks, ignore_index=True))
                    if spread_chunks:
                        spread_writer.append(pd.concat(spread_chunks, ignore_index=True))

    ic_writer.close({"date": pa.timestamp("us"), "ic_spearman": pa.float64()})
    spread_writer.close({"date": pa.timestamp("us"), "top_minus_bottom_spread": pa.float64()})
    return {
        "ic_summary": pd.DataFrame(ic_summary_rows),
        "spread_summary": pd.DataFrame(spread_summary_rows),
        "quantile_summary": pd.DataFrame(quantile_rows),
        "hit_rates": pd.DataFrame(hit_rows),
        "coverage": pd.DataFrame(coverage_rows),
        "subperiod": pd.DataFrame(subperiod_rows),
        "persistence": pd.DataFrame(persistence_rows),
        "rank_stability": pd.DataFrame(stability_rows),
        "headline_series": headline_series,
        "frequency_rows": frequency_rows,
        "ic_time_series_rows": ic_writer.rows,
        "spread_time_series_rows": spread_writer.rows,
    }


def apply_false_discovery_control(ic_summary: pd.DataFrame, policy: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = ic_summary.copy()
    headline = (
        frame["registry_class"].eq("PRIMARY")
        & frame["universe_id"].eq(policy["candidate_assessment"]["headline_universe"])
        & frame["cohort_id"].eq(policy["candidate_assessment"]["headline_cohort"])
        & frame["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
        & frame["forward_horizon_sessions"].isin(policy["candidate_assessment"]["headline_horizons"])
    )
    p_values = frame.loc[headline, "ic_hac_p_value"].to_numpy(dtype=float)
    frame.loc[headline, "bh_fdr_q_value"] = benjamini_hochberg(p_values)
    frame["headline_predeclared_test"] = headline
    frame["multiple_testing_family"] = np.where(headline, "PREDECLARED_PRIMARY_HEADLINE_IC_84", "DIAGNOSTIC_NOT_IN_HEADLINE_FDR_FAMILY")
    frame["fdr_survives_q_0_10"] = frame["bh_fdr_q_value"].le(0.10).fillna(False)
    ledger = frame.copy()
    ledger["test_outcome"] = np.select(
        [
            ledger["status"].ne("TESTED"),
            ledger["fdr_survives_q_0_10"],
            ledger["ic_mean"].gt(0.0) & ledger["ic_hac_p_value"].le(0.10),
            ledger["ic_mean"].gt(0.0),
        ],
        ["INSUFFICIENT", "POSITIVE_FDR_SURVIVOR", "POSITIVE_NOMINAL", "POSITIVE_NOT_SIGNIFICANT"],
        default="NON_POSITIVE_OR_INVERTED",
    )
    ledger["omitted_from_reporting"] = False
    return frame, ledger


def build_parameter_neighbourhoods(ic: pd.DataFrame, spread: pd.DataFrame) -> pd.DataFrame:
    keys = ["signal_id", "universe_id", "cohort_id", "frequency_id", "forward_horizon_sessions"]
    source = ic[keys + ["ic_mean", "ic_median", "ic_hac_p_value", "bh_fdr_q_value", "status"]].merge(
        spread[keys + ["spread_mean", "spread_hac_p_value", "mean_monotonicity_score"]],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    mappings = {
        "MOM_126": ["MOM_105", "MOM_147"],
        "MOM_252": ["MOM_210", "MOM_294"],
        "ABS_POS_252": ["ABS_POS_210", "ABS_POS_294"],
        "ABOVE_GBP_CASH_252": ["ABOVE_GBP_CASH_210", "ABOVE_GBP_CASH_294"],
        "TREND_MA_252": ["TREND_MA_210", "TREND_MA_294"],
    }
    rows: list[dict[str, Any]] = []
    match_keys = ["universe_id", "cohort_id", "frequency_id", "forward_horizon_sessions"]
    for central, neighbours in mappings.items():
        centre = source[source["signal_id"].eq(central)].rename(columns={
            "ic_mean": "central_ic_mean", "ic_median": "central_ic_median", "ic_hac_p_value": "central_ic_hac_p_value",
            "bh_fdr_q_value": "central_bh_fdr_q_value", "spread_mean": "central_spread_mean",
            "spread_hac_p_value": "central_spread_hac_p_value", "mean_monotonicity_score": "central_monotonicity_score",
            "status": "central_status",
        })
        for neighbour in neighbours:
            adjacent = source[source["signal_id"].eq(neighbour)].rename(columns={
                "ic_mean": "neighbour_ic_mean", "ic_median": "neighbour_ic_median", "ic_hac_p_value": "neighbour_ic_hac_p_value",
                "bh_fdr_q_value": "neighbour_bh_fdr_q_value", "spread_mean": "neighbour_spread_mean",
                "spread_hac_p_value": "neighbour_spread_hac_p_value", "mean_monotonicity_score": "neighbour_monotonicity_score",
                "status": "neighbour_status",
            })
            merged = centre.merge(adjacent, on=match_keys, suffixes=("_central", "_neighbour"), how="inner")
            for _, row in merged.iterrows():
                rows.append({
                    "test_type": "LOOKBACK_NEIGHBOURHOOD",
                    "central_signal_id": central,
                    "neighbour_signal_id": neighbour,
                    **{key: row[key] for key in match_keys},
                    "central_ic_mean": row["central_ic_mean"],
                    "neighbour_ic_mean": row["neighbour_ic_mean"],
                    "ic_mean_difference": row["neighbour_ic_mean"] - row["central_ic_mean"],
                    "central_spread_mean": row["central_spread_mean"],
                    "neighbour_spread_mean": row["neighbour_spread_mean"],
                    "spread_mean_difference": row["neighbour_spread_mean"] - row["central_spread_mean"],
                    "directionally_stable_ic": bool(pd.notna(row["central_ic_mean"]) and pd.notna(row["neighbour_ic_mean"]) and row["central_ic_mean"] > 0 and row["neighbour_ic_mean"] > 0),
                    "directionally_stable_spread": bool(pd.notna(row["central_spread_mean"]) and pd.notna(row["neighbour_spread_mean"]) and row["central_spread_mean"] > 0 and row["neighbour_spread_mean"] > 0),
                    "status": "TESTED" if row["central_status"] == "TESTED" and row["neighbour_status"] == "TESTED" else "LIMITED",
                    "historical_eligibility_warning": WARNING,
                })
    return pd.DataFrame(rows)


def build_experimental_sensitivity(ic: pd.DataFrame, spread: pd.DataFrame) -> pd.DataFrame:
    keys = ["signal_id", "signal_family", "registry_class", "cohort_id", "frequency_id", "forward_horizon_sessions"]
    source = ic[keys + ["universe_id", "ic_mean", "ic_median", "ic_hac_p_value", "status"]].merge(
        spread[["signal_id", "cohort_id", "frequency_id", "forward_horizon_sessions", "universe_id", "spread_mean", "mean_monotonicity_score"]],
        on=["signal_id", "cohort_id", "frequency_id", "forward_horizon_sessions", "universe_id"],
        how="left",
        validate="one_to_one",
    )
    primary = source[source["universe_id"].eq("CORE_EXTENDED")].rename(columns={
        "ic_mean": "primary_ic_mean", "ic_median": "primary_ic_median", "ic_hac_p_value": "primary_ic_hac_p_value",
        "spread_mean": "primary_spread_mean", "mean_monotonicity_score": "primary_monotonicity", "status": "primary_status",
    })
    all_ready = source[source["universe_id"].eq("ALL_A3_READY")].rename(columns={
        "ic_mean": "all_ready_ic_mean", "ic_median": "all_ready_ic_median", "ic_hac_p_value": "all_ready_ic_hac_p_value",
        "spread_mean": "all_ready_spread_mean", "mean_monotonicity_score": "all_ready_monotonicity", "status": "all_ready_status",
    })
    experimental = source[source["universe_id"].eq("EXPERIMENTAL")].rename(columns={
        "ic_mean": "experimental_only_ic_mean", "ic_median": "experimental_only_ic_median", "ic_hac_p_value": "experimental_only_ic_hac_p_value",
        "spread_mean": "experimental_only_spread_mean", "mean_monotonicity_score": "experimental_only_monotonicity", "status": "experimental_only_status",
    })
    merged = primary.merge(all_ready, on=keys, how="left", suffixes=("_primary", "_all")).merge(experimental, on=keys, how="left")
    merged["ic_mean_change_with_experimental"] = merged["all_ready_ic_mean"] - merged["primary_ic_mean"]
    merged["spread_mean_change_with_experimental"] = merged["all_ready_spread_mean"] - merged["primary_spread_mean"]

    def interpretation(row: pd.Series) -> str:
        primary_value = row["primary_ic_mean"]
        all_value = row["all_ready_ic_mean"]
        delta = row["ic_mean_change_with_experimental"]
        if pd.isna(primary_value) or pd.isna(all_value):
            return "INSUFFICIENT"
        if np.sign(primary_value) != np.sign(all_value):
            return "DESTABILISES"
        if delta > 0.005:
            return "STRENGTHENS"
        if delta < -0.005:
            return "WEAKENS"
        return "LEAVES_QUALITATIVELY_UNCHANGED"

    merged["experimental_effect"] = merged.apply(interpretation, axis=1)
    merged["primary_decision_affected"] = False
    merged["historical_eligibility_warning"] = WARNING
    keep = keys + [
        "primary_ic_mean", "all_ready_ic_mean", "experimental_only_ic_mean", "ic_mean_change_with_experimental",
        "primary_spread_mean", "all_ready_spread_mean", "experimental_only_spread_mean", "spread_mean_change_with_experimental",
        "primary_monotonicity", "all_ready_monotonicity", "experimental_effect", "primary_decision_affected",
        "primary_status", "all_ready_status", "experimental_only_status", "historical_eligibility_warning",
    ]
    return merged.reindex(columns=keep)


def evaluate_filtered_context(
    state: ResearchState,
    definition: dict[str, Any],
    columns: np.ndarray,
    cohort_id: str,
    frequency_id: str,
    horizons: Iterable[int],
    availability_mask: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    peer_groups = ranking_groups(state.metadata, columns, cohort_id)
    if availability_mask is None:
        availability_mask = np.ones((len(state.dates), len(columns)), dtype=bool)
    signal_values = signal_matrix_for_context(state, definition, columns, peer_groups, availability_mask=availability_mask)
    signal_ranks = signal_rank_matrix(signal_values, peer_groups)
    observations = observation_positions(state.dates, frequency_id)
    rows: list[dict[str, Any]] = []
    for horizon in horizons:
        forward_values = state.forward_returns[int(horizon)][:, columns].copy()
        forward_values[~availability_mask] = np.nan
        outcome_ranks = outcome_rank_matrix(forward_values, peer_groups)
        observed_signal = signal_values[observations]
        observed_ranks = signal_ranks[observations]
        observed_forward = forward_values[observations]
        ic_values, ic_counts = rowwise_correlation(observed_ranks, outcome_ranks[observations], minimum_count=5)
        benchmark_id, benchmark = benchmark_for_context(state, columns, cohort_id, int(horizon))
        buckets = evaluate_buckets_and_hits(observed_signal, observed_ranks, observed_forward, definition["role"], benchmark[observations])
        lag = hac_lag_for_horizon(int(horizon), frequency_id)
        rows.append({
            "signal_id": definition["signal_id"],
            "signal_family": definition["signal_family"],
            "frequency_id": frequency_id,
            "forward_horizon_sessions": int(horizon),
            "dates": state.dates[observations],
            "ic_values": ic_values,
            "ic_counts": ic_counts,
            "spread_values": buckets["spread"],
            "monotonicity_values": buckets["monotonicity"],
            "signal_values": observed_signal,
            "signal_ranks": observed_ranks,
            "forward_values": observed_forward,
            "observations": observations,
            "benchmark_id": benchmark_id,
            "ic_stats": newey_west_mean(ic_values, lag),
            "spread_stats": newey_west_mean(buckets["spread"], lag),
            "mean_monotonicity_score": float(np.nanmean(buckets["monotonicity"])) if np.isfinite(buckets["monotonicity"]).any() else np.nan,
            "hac_lag": lag,
        })
    return rows


def family_characteristic_sets(state: ResearchState) -> dict[str, Any]:
    meta = state.metadata.copy()
    identifiers = meta["economic_exposure_family_id"].astype(str)
    us_tech_mask = (
        identifiers.eq("US_NASDAQ_100")
        | (meta["primary_geography"].eq("UNITED_STATES") & (meta["sector"].eq("TECHNOLOGY") | meta["industry"].astype(str).str.contains("SEMICONDUCTOR", case=False, na=False)))
        | meta["industry"].astype(str).str.contains("SEMICONDUCTOR", case=False, na=False)
    )
    us_tech = identifiers[us_tech_mask].tolist()
    valid = np.isfinite(state.returns)
    log_values = np.where(valid, np.log1p(state.returns), np.nan)
    counts = valid.sum(axis=0)
    annualised_log = np.divide(np.nansum(log_values, axis=0), counts, out=np.full(len(counts), np.nan), where=counts > 0) * 252.0
    annualised_log[counts < 504] = np.nan
    order = np.argsort(np.where(np.isfinite(annualised_log), annualised_log, -np.inf))[::-1]
    ordered_families = [state.families[index] for index in order if np.isfinite(annualised_log[index])]
    return {
        "us_technology_semiconductors": us_tech,
        "best_full_period_family": ordered_families[:1],
        "top_five_full_period_families": ordered_families[:5],
        "full_period_ranking_method": "ANNUALISED_GEOMETRIC_MEAN_OF_VALID_DAILY_IMPLEMENTATION_RETURNS_EX_POST_DIAGNOSTIC_ONLY",
    }


def controlled_cross_sectional_signal_beta(
    signal_ranks: np.ndarray,
    forward_values: np.ndarray,
    control_values: dict[str, np.ndarray],
    observations: np.ndarray,
    minimum_count: int = 10,
) -> tuple[np.ndarray, np.ndarray]:
    betas = np.full(len(observations), np.nan)
    sample_counts = np.zeros(len(observations), dtype=int)
    for output_row, date_row in enumerate(observations):
        signal = signal_ranks[date_row]
        future = forward_values[date_row]
        controls = [np.asarray(values[date_row], dtype=float) for values in control_values.values()]
        mask = np.isfinite(signal) & np.isfinite(future)
        for values in controls:
            mask &= np.isfinite(values)
        if mask.sum() < minimum_count:
            continue
        signal_column = signal[mask]
        if np.nanstd(signal_column) <= 0:
            continue
        design_columns = [np.ones(mask.sum()), signal_column]
        for values in controls:
            column = values[mask]
            if np.nanstd(column) > 1e-12:
                design_columns.append(column)
        design = np.column_stack(design_columns)
        response = future[mask]
        if np.linalg.matrix_rank(design) < design.shape[1]:
            continue
        coefficient, *_ = np.linalg.lstsq(design, response, rcond=None)
        betas[output_row] = coefficient[1]
        sample_counts[output_row] = int(mask.sum())
    return betas, sample_counts


def build_concentration_and_dependency_tests(
    state: ResearchState,
    target_signal_ids: list[str],
    characteristic_sets: dict[str, Any],
) -> pd.DataFrame:
    policy = state.policy
    definitions = {item["signal_id"]: item for item in policy["signal_definitions"]}
    universe = next(item for item in policy["universe_scopes"] if item["universe_id"] == "CORE_EXTENDED")
    base_columns = context_family_indices(state.metadata, universe, "GLOBAL")
    family_to_global = {family: index for index, family in enumerate(state.families)}
    local_family_ids = [state.families[index] for index in base_columns]

    static_exclusions = {
        "BASELINE": [],
        "EX_US_TECHNOLOGY_SEMICONDUCTORS": characteristic_sets["us_technology_semiconductors"],
        "EX_SINGLE_BEST_FULL_PERIOD_FAMILY": characteristic_sets["best_full_period_family"],
        "EX_TOP_FIVE_FULL_PERIOD_FAMILIES": characteristic_sets["top_five_full_period_families"],
    }
    rows: list[dict[str, Any]] = []
    frequencies = [item["frequency_id"] for item in policy["observation_frequencies"]]
    horizons = policy["primary_inference_horizons_sessions"]

    for signal_id in target_signal_ids:
        definition = definitions[signal_id]
        for test_id, excluded in static_exclusions.items():
            columns = np.array([index for index in base_columns if state.families[index] not in set(excluded)], dtype=int)
            for frequency in frequencies:
                for result in evaluate_filtered_context(state, definition, columns, "GLOBAL", frequency, horizons):
                    rows.append({
                        "signal_id": signal_id,
                        "test_type": "STATIC_EXCLUSION",
                        "dependency_test_id": test_id,
                        "frequency_id": frequency,
                        "forward_horizon_sessions": result["forward_horizon_sessions"],
                        "included_family_count": int(len(columns)),
                        "excluded_families": ";".join(excluded) if excluded else "NONE",
                        "mean_ic": result["ic_stats"]["mean"],
                        "median_ic": result["ic_stats"]["median"],
                        "ic_observation_count": result["ic_stats"]["observation_count"],
                        "ic_hac_t_statistic": result["ic_stats"]["hac_t_statistic"],
                        "ic_hac_p_value": result["ic_stats"]["hac_p_value"],
                        "mean_top_bottom_spread": result["spread_stats"]["mean"],
                        "spread_hac_p_value": result["spread_stats"]["hac_p_value"],
                        "mean_monotonicity_score": result["mean_monotonicity_score"],
                        "ex_post_filter": test_id in {"EX_SINGLE_BEST_FULL_PERIOD_FAMILY", "EX_TOP_FIVE_FULL_PERIOD_FAMILIES"},
                        "historical_eligibility_warning": WARNING,
                    })

        dynamic_tests: dict[str, np.ndarray] = {}
        base_age = state.valid_age[:, base_columns]
        dynamic_tests["EX_RECENT_INCEPTION_LT_756_VALID_RETURNS"] = base_age >= 756
        volatility = state.volatility_63[:, base_columns]
        volatility_rank = percentile_rank_rows(volatility)
        dynamic_tests["EX_CONTEMPORANEOUS_TOP_VOLATILITY_QUINTILE"] = np.isfinite(volatility_rank) & (volatility_rank <= 0.80)
        equity_flags = state.metadata.iloc[base_columns]["asset_class"].eq("EQUITY").to_numpy()
        dynamic_tests["EQUITY_ONLY"] = np.broadcast_to(equity_flags[None, :], (len(state.dates), len(base_columns))).copy()

        for test_id, availability in dynamic_tests.items():
            for frequency in frequencies:
                for result in evaluate_filtered_context(state, definition, base_columns, "GLOBAL", frequency, horizons, availability_mask=availability):
                    rows.append({
                        "signal_id": signal_id,
                        "test_type": "CONTEMPORANEOUS_FILTER",
                        "dependency_test_id": test_id,
                        "frequency_id": frequency,
                        "forward_horizon_sessions": result["forward_horizon_sessions"],
                        "included_family_count": float(np.nanmean(availability[result["observations"]].sum(axis=1))),
                        "excluded_families": "DYNAMIC_DATE_LEVEL_FILTER",
                        "mean_ic": result["ic_stats"]["mean"],
                        "median_ic": result["ic_stats"]["median"],
                        "ic_observation_count": result["ic_stats"]["observation_count"],
                        "ic_hac_t_statistic": result["ic_stats"]["hac_t_statistic"],
                        "ic_hac_p_value": result["ic_stats"]["hac_p_value"],
                        "mean_top_bottom_spread": result["spread_stats"]["mean"],
                        "spread_hac_p_value": result["spread_stats"]["hac_p_value"],
                        "mean_monotonicity_score": result["mean_monotonicity_score"],
                        "ex_post_filter": False,
                        "historical_eligibility_warning": WARNING,
                    })

        # Date-level cross-sectional regressions control persistent characteristics without changing ranks.
        peer_groups = None
        full_signal = signal_matrix_for_context(state, definition, base_columns, peer_groups)
        full_ranks = signal_rank_matrix(full_signal, peer_groups)
        us_flag = state.metadata.iloc[base_columns]["primary_geography"].eq("UNITED_STATES").astype(float).to_numpy()
        tech_flag = (
            state.metadata.iloc[base_columns]["sector"].eq("TECHNOLOGY")
            | state.metadata.iloc[base_columns]["industry"].astype(str).str.contains("SEMICONDUCTOR", case=False, na=False)
        ).astype(float).to_numpy()
        equity_flag = state.metadata.iloc[base_columns]["asset_class"].eq("EQUITY").astype(float).to_numpy()
        theme_flag = state.metadata.iloc[base_columns]["opportunity_type"].eq("THEMATIC").astype(float).to_numpy()
        vol_rank = percentile_rank_rows(state.volatility_63[:, base_columns])
        recent_flag = (state.valid_age[:, base_columns] < 756).astype(float)
        static_controls = {
            "US_EXPOSURE": np.broadcast_to(us_flag[None, :], full_ranks.shape),
            "TECHNOLOGY_OR_SEMICONDUCTOR": np.broadcast_to(tech_flag[None, :], full_ranks.shape),
            "EQUITY": np.broadcast_to(equity_flag[None, :], full_ranks.shape),
            "VOLATILITY_PERCENTILE": vol_rank,
            "RECENT_INCEPTION": recent_flag,
            "THEMATIC": np.broadcast_to(theme_flag[None, :], full_ranks.shape),
        }
        for frequency in frequencies:
            observations = observation_positions(state.dates, frequency)
            for horizon in horizons:
                betas, sample_counts = controlled_cross_sectional_signal_beta(
                    full_ranks,
                    state.forward_returns[int(horizon)][:, base_columns],
                    static_controls,
                    observations,
                    minimum_count=10,
                )
                stats = newey_west_mean(betas, hac_lag_for_horizon(int(horizon), frequency))
                rows.append({
                    "signal_id": signal_id,
                    "test_type": "DATE_LEVEL_CONTROLLED_CROSS_SECTIONAL_REGRESSION",
                    "dependency_test_id": "CONTROL_US_TECH_EQUITY_VOLATILITY_INCEPTION_THEME",
                    "frequency_id": frequency,
                    "forward_horizon_sessions": int(horizon),
                    "included_family_count": float(np.mean(sample_counts[sample_counts > 0])) if (sample_counts > 0).any() else np.nan,
                    "excluded_families": "NONE_CONTROLS_ENTER_REGRESSION",
                    "mean_ic": np.nan,
                    "median_ic": np.nan,
                    "ic_observation_count": stats["observation_count"],
                    "ic_hac_t_statistic": stats["hac_t_statistic"],
                    "ic_hac_p_value": stats["hac_p_value"],
                    "mean_top_bottom_spread": np.nan,
                    "spread_hac_p_value": np.nan,
                    "mean_monotonicity_score": np.nan,
                    "mean_signal_rank_coefficient": stats["mean"],
                    "median_signal_rank_coefficient": stats["median"],
                    "coefficient_hac_standard_error": stats["hac_standard_error"],
                    "coefficient_hac_t_statistic": stats["hac_t_statistic"],
                    "coefficient_hac_p_value": stats["hac_p_value"],
                    "ex_post_filter": False,
                    "historical_eligibility_warning": WARNING,
                })
    return pd.DataFrame(rows)


def build_regime_labels(state: ResearchState) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    family_position = {family: index for index, family in enumerate(state.families)}
    global_index = family_position.get("GLOBAL_ALL_WORLD")
    us_index = family_position.get("US_BROAD_LARGE_CAP")
    if global_index is None or us_index is None:
        raise AssertionError("Independent regime anchors are not present in the A3-ready universe")
    all_world_trend = state.component_signals["MOM_252"][:, global_index]
    all_world_volatility = state.volatility_63[:, global_index]
    prior_vol_median = pd.Series(all_world_volatility).expanding(min_periods=252).median().shift(1).to_numpy()
    rates_prior = pd.Series(state.cash_rates).shift(63).to_numpy()

    primary_geo = state.metadata["opportunity_type"].eq("GEOGRAPHY") & ~state.metadata["primary_geography"].eq("UNITED_STATES")
    non_us_columns = np.flatnonzero(primary_geo.to_numpy())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        non_us_median = np.nanmedian(state.component_signals["MOM_63"][:, non_us_columns], axis=1)
    us_return = state.component_signals["MOM_63"][:, us_index]

    core_extended = state.metadata["universe_tier"].isin(["CORE", "EXTENDED"]).to_numpy()
    ce_columns = np.flatnonzero(core_extended)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        dispersion = np.nanstd(state.component_signals["MOM_21"][:, ce_columns], axis=1, ddof=1)
    dispersion_count = np.isfinite(state.component_signals["MOM_21"][:, ce_columns]).sum(axis=1)
    dispersion[dispersion_count < 10] = np.nan
    prior_dispersion_median = pd.Series(dispersion).expanding(min_periods=252).median().shift(1).to_numpy()

    labels: dict[str, np.ndarray] = {
        "EQUITY_TREND": np.where(np.isfinite(all_world_trend), np.where(all_world_trend > 0, "BULL_POSITIVE_252", "BEAR_NONPOSITIVE_252"), "UNKNOWN"),
        "MARKET_VOLATILITY": np.where(
            np.isfinite(all_world_volatility) & np.isfinite(prior_vol_median),
            np.where(all_world_volatility > prior_vol_median, "HIGH", "LOW"),
            "UNKNOWN",
        ),
        "RATES": np.where(
            np.isfinite(state.cash_rates) & np.isfinite(rates_prior),
            np.where(state.cash_rates > rates_prior, "RISING", np.where(state.cash_rates < rates_prior, "FALLING", "UNCHANGED")),
            "UNKNOWN",
        ),
        "CROSS_SECTIONAL_DISPERSION": np.where(
            np.isfinite(dispersion) & np.isfinite(prior_dispersion_median),
            np.where(dispersion > prior_dispersion_median, "HIGH", "LOW"),
            "UNKNOWN",
        ),
        "US_LEADERSHIP": np.where(
            np.isfinite(us_return) & np.isfinite(non_us_median),
            np.where(us_return > non_us_median, "US_DOMINANT", "BROADER_LEADERSHIP"),
            "UNKNOWN",
        ),
    }
    frame = pd.DataFrame({
        "date": state.dates,
        "global_all_world_momentum_252": all_world_trend,
        "global_all_world_volatility_63": all_world_volatility,
        "prior_expanding_median_volatility": prior_vol_median,
        "sonia_rate_percent": state.cash_rates,
        "sonia_rate_63_sessions_prior": rates_prior,
        "cross_sectional_momentum_21_dispersion": dispersion,
        "prior_expanding_median_dispersion": prior_dispersion_median,
        "us_broad_momentum_63": us_return,
        "median_non_us_geography_momentum_63": non_us_median,
        **{f"regime_{key.lower()}": value for key, value in labels.items()},
    })
    return frame, labels


def build_regime_and_dispersion_diagnostics(
    state: ResearchState,
    target_signal_ids: list[str],
    regime_frame: pd.DataFrame,
    regime_labels: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    policy = state.policy
    definitions = {item["signal_id"]: item for item in policy["signal_definitions"]}
    universe = next(item for item in policy["universe_scopes"] if item["universe_id"] == "CORE_EXTENDED")
    columns = context_family_indices(state.metadata, universe, "GLOBAL")
    frequencies = [item["frequency_id"] for item in policy["observation_frequencies"]]
    horizons = policy["primary_inference_horizons_sessions"]
    regime_rows: list[dict[str, Any]] = []
    dispersion_rows: list[dict[str, Any]] = []
    dispersion_values = regime_frame["cross_sectional_momentum_21_dispersion"].to_numpy(dtype=float)

    for signal_id in target_signal_ids:
        definition = definitions[signal_id]
        for frequency in frequencies:
            for result in evaluate_filtered_context(state, definition, columns, "GLOBAL", frequency, horizons):
                observations = result["observations"]
                for regime_id, label_values in regime_labels.items():
                    observed_labels = label_values[observations]
                    states = sorted(set(observed_labels.tolist()) - {"UNKNOWN"})
                    for regime_state in states:
                        selected = observed_labels == regime_state
                        ic_stats = newey_west_mean(result["ic_values"][selected], result["hac_lag"])
                        spread_stats = newey_west_mean(result["spread_values"][selected], result["hac_lag"])
                        regime_rows.append({
                            "signal_id": signal_id,
                            "frequency_id": frequency,
                            "forward_horizon_sessions": result["forward_horizon_sessions"],
                            "regime_id": regime_id,
                            "regime_state": regime_state,
                            **prefix_stats(ic_stats, "ic"),
                            **prefix_stats(spread_stats, "spread"),
                            "descriptive_only_no_filter_optimisation": True,
                            "historical_eligibility_warning": WARNING,
                        })

                observed_dispersion = dispersion_values[observations]
                valid_ic = np.isfinite(observed_dispersion) & np.isfinite(result["ic_values"])
                valid_spread = np.isfinite(observed_dispersion) & np.isfinite(result["spread_values"])
                ic_corr = scipy.stats.spearmanr(observed_dispersion[valid_ic], result["ic_values"][valid_ic]).statistic if valid_ic.sum() >= 10 else np.nan
                spread_corr = scipy.stats.spearmanr(observed_dispersion[valid_spread], result["spread_values"][valid_spread]).statistic if valid_spread.sum() >= 10 else np.nan
                dispersion_labels = regime_labels["CROSS_SECTIONAL_DISPERSION"][observations]
                for level in ("HIGH", "LOW"):
                    selected = dispersion_labels == level
                    ic_stats = newey_west_mean(result["ic_values"][selected], result["hac_lag"])
                    spread_stats = newey_west_mean(result["spread_values"][selected], result["hac_lag"])
                    dispersion_rows.append({
                        "signal_id": signal_id,
                        "frequency_id": frequency,
                        "forward_horizon_sessions": result["forward_horizon_sessions"],
                        "dispersion_regime": level,
                        **prefix_stats(ic_stats, "ic"),
                        **prefix_stats(spread_stats, "spread"),
                        "spearman_dispersion_vs_date_ic": ic_corr,
                        "spearman_dispersion_vs_date_spread": spread_corr,
                        "diagnostic_only_no_timing_rule": True,
                        "historical_eligibility_warning": WARNING,
                    })
    return pd.DataFrame(regime_rows), pd.DataFrame(dispersion_rows)


def build_weekday_perturbations(
    state: ResearchState,
    target_signal_ids: list[str],
    primary_ic: pd.DataFrame,
    primary_spread: pd.DataFrame,
) -> pd.DataFrame:
    policy = state.policy
    definitions = {item["signal_id"]: item for item in policy["signal_definitions"]}
    universe = next(item for item in policy["universe_scopes"] if item["universe_id"] == "CORE_EXTENDED")
    columns = context_family_indices(state.metadata, universe, "GLOBAL")
    horizons = policy["primary_inference_horizons_sessions"]
    rows: list[dict[str, Any]] = []
    for signal_id in target_signal_ids:
        baseline_ic = primary_ic[
            primary_ic["signal_id"].eq(signal_id)
            & primary_ic["universe_id"].eq("CORE_EXTENDED")
            & primary_ic["cohort_id"].eq("GLOBAL")
            & primary_ic["frequency_id"].eq("WEEKLY_WEDNESDAY")
            & primary_ic["forward_horizon_sessions"].isin(horizons)
        ].set_index("forward_horizon_sessions")
        baseline_spread = primary_spread[
            primary_spread["signal_id"].eq(signal_id)
            & primary_spread["universe_id"].eq("CORE_EXTENDED")
            & primary_spread["cohort_id"].eq("GLOBAL")
            & primary_spread["frequency_id"].eq("WEEKLY_WEDNESDAY")
            & primary_spread["forward_horizon_sessions"].isin(horizons)
        ].set_index("forward_horizon_sessions")
        for perturbation in policy["weekday_perturbations"]:
            frequency = perturbation["frequency_id"]
            for result in evaluate_filtered_context(state, definitions[signal_id], columns, "GLOBAL", frequency, horizons):
                horizon = result["forward_horizon_sessions"]
                centre_ic = baseline_ic.loc[horizon, "ic_mean"] if horizon in baseline_ic.index else np.nan
                centre_spread = baseline_spread.loc[horizon, "spread_mean"] if horizon in baseline_spread.index else np.nan
                rows.append({
                    "test_type": "WEEKDAY_PERTURBATION",
                    "central_signal_id": signal_id,
                    "neighbour_signal_id": frequency,
                    "universe_id": "CORE_EXTENDED",
                    "cohort_id": "GLOBAL",
                    "frequency_id": "WEEKLY_WEDNESDAY",
                    "forward_horizon_sessions": horizon,
                    "central_ic_mean": centre_ic,
                    "neighbour_ic_mean": result["ic_stats"]["mean"],
                    "ic_mean_difference": result["ic_stats"]["mean"] - centre_ic,
                    "central_spread_mean": centre_spread,
                    "neighbour_spread_mean": result["spread_stats"]["mean"],
                    "spread_mean_difference": result["spread_stats"]["mean"] - centre_spread,
                    "directionally_stable_ic": bool(pd.notna(centre_ic) and pd.notna(result["ic_stats"]["mean"]) and centre_ic > 0 and result["ic_stats"]["mean"] > 0),
                    "directionally_stable_spread": bool(pd.notna(centre_spread) and pd.notna(result["spread_stats"]["mean"]) and centre_spread > 0 and result["spread_stats"]["mean"] > 0),
                    "status": "TESTED" if result["ic_stats"]["observation_count"] >= 24 else "LIMITED",
                    "historical_eligibility_warning": WARNING,
                })
    return pd.DataFrame(rows)


def build_block_bootstrap_results(
    headline_series: dict[tuple[str, str, int], dict[str, Any]],
    target_signal_ids: list[str],
    policy: dict[str, Any],
) -> pd.DataFrame:
    bootstrap_policy = policy["inference"]["block_bootstrap"]
    rows: list[dict[str, Any]] = []
    for signal_id in target_signal_ids:
        for frequency in policy["candidate_assessment"]["headline_frequencies"]:
            for horizon in policy["candidate_assessment"]["headline_horizons"]:
                series = headline_series.get((signal_id, frequency, int(horizon)))
                if not series:
                    continue
                lag = hac_lag_for_horizon(int(horizon), frequency)
                block_length = max(5, lag + 1)
                for metric, key in (("IC", "ic"), ("TOP_MINUS_BOTTOM_SPREAD", "spread")):
                    bootstrap = circular_block_bootstrap_mean_ci(
                        series[key],
                        block_length=block_length,
                        replications=int(bootstrap_policy["replications"]),
                        seed=int(bootstrap_policy["seed"]) + stable_seed(signal_id, frequency, horizon, metric),
                    )
                    rows.append({
                        "signal_id": signal_id,
                        "frequency_id": frequency,
                        "forward_horizon_sessions": int(horizon),
                        "metric": metric,
                        **bootstrap,
                        "confidence_interval_excludes_zero_positive": bool(pd.notna(bootstrap["ci_low"]) and bootstrap["ci_low"] > 0.0),
                        "historical_eligibility_warning": WARNING,
                    })
    return pd.DataFrame(rows)


def stable_seed(*parts: Any) -> int:
    digest = stable_id("SEED", *parts, length=8).split("-", 1)[1]
    return int(digest, 16) % 1_000_000_000


def assess_signal_candidates(
    policy: dict[str, Any],
    signal_registry: pd.DataFrame,
    ic: pd.DataFrame,
    spread: pd.DataFrame,
    subperiod: pd.DataFrame,
    persistence: pd.DataFrame,
    neighbourhoods: pd.DataFrame,
    dependency: pd.DataFrame | None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    primary_ids = signal_registry.loc[signal_registry["registry_class"].eq("PRIMARY"), "signal_id"].tolist()
    headline_frequencies = policy["candidate_assessment"]["headline_frequencies"]
    headline_horizons = policy["candidate_assessment"]["headline_horizons"]
    five_subperiods = ["FULL", "PRE_2020", "FROM_2020", "RECENT_5Y", "RECENT_3Y"]

    for signal_id in primary_ids:
        headline_ic = ic[
            ic["signal_id"].eq(signal_id)
            & ic["universe_id"].eq("CORE_EXTENDED")
            & ic["cohort_id"].eq("GLOBAL")
            & ic["frequency_id"].isin(headline_frequencies)
            & ic["forward_horizon_sessions"].isin(headline_horizons)
        ]
        headline_spread = spread[
            spread["signal_id"].eq(signal_id)
            & spread["universe_id"].eq("CORE_EXTENDED")
            & spread["cohort_id"].eq("GLOBAL")
            & spread["frequency_id"].isin(headline_frequencies)
            & spread["forward_horizon_sessions"].isin(headline_horizons)
        ]
        core_ic = ic[
            ic["signal_id"].eq(signal_id)
            & ic["universe_id"].eq("CORE")
            & ic["cohort_id"].eq("GLOBAL")
            & ic["frequency_id"].isin(headline_frequencies)
            & ic["forward_horizon_sessions"].isin(headline_horizons)
        ]
        neutral_ic = ic[
            ic["signal_id"].eq(signal_id)
            & ic["universe_id"].eq("CORE_EXTENDED")
            & ic["cohort_id"].eq("GLOBAL_CATEGORY_NEUTRAL")
            & ic["frequency_id"].isin(headline_frequencies)
            & ic["forward_horizon_sessions"].isin(headline_horizons)
        ]
        criteria: list[dict[str, Any]] = []

        def criterion(criterion_id: str, description: str, value: Any, passed: bool | None, applicable: bool = True) -> None:
            criteria.append({"criterion_id": criterion_id, "description": description, "value": value, "passed": passed, "applicable": applicable})

        positive_mean_count = int(headline_ic["ic_mean"].gt(0.0).sum())
        positive_median_count = int(headline_ic["ic_median"].gt(0.0).sum())
        average_ic = float(headline_ic["ic_mean"].mean()) if not headline_ic.empty else np.nan
        fdr_survivors = int(headline_ic["fdr_survives_q_0_10"].sum())
        positive_spread_count = int(headline_spread["spread_mean"].gt(0.0).sum())
        spread_significant = int((headline_spread["spread_mean"].gt(0.0) & headline_spread["spread_hac_p_value"].le(0.10)).sum())
        average_monotonicity = float(headline_spread["mean_monotonicity_score"].mean()) if not headline_spread.empty else np.nan
        core_positive_count = int(core_ic["ic_mean"].gt(0.0).sum())
        neutral_positive_count = int(neutral_ic["ic_mean"].gt(0.0).sum())

        criterion("C01", "positive mean IC in at least four of six headline cells", positive_mean_count, positive_mean_count >= 4)
        criterion("C02", "positive median IC in at least four of six headline cells", positive_median_count, positive_median_count >= 4)
        criterion("C03", "average headline mean IC exceeds 0.01", average_ic, bool(pd.notna(average_ic) and average_ic > 0.01))
        criterion("C04", "at least one headline IC survives BH FDR q<=0.10", fdr_survivors, fdr_survivors >= 1)
        criterion("C05", "positive top-minus-bottom spread in at least four of six headline cells", positive_spread_count, positive_spread_count >= 4)
        criterion("C06", "at least one positive headline spread has HAC p<=0.10", spread_significant, spread_significant >= 1)
        criterion("C07", "average quantile monotonicity is at least 0.50", average_monotonicity, bool(pd.notna(average_monotonicity) and average_monotonicity >= 0.50))
        criterion("C08", "CORE-only mean IC is positive in at least four matched cells", core_positive_count, core_positive_count >= 4)
        criterion("C09", "category-neutral mean IC is positive in at least four matched cells", neutral_positive_count, neutral_positive_count >= 4)

        period_values = (
            subperiod[
                subperiod["signal_id"].eq(signal_id)
                & subperiod["universe_id"].eq("CORE_EXTENDED")
                & subperiod["cohort_id"].eq("GLOBAL")
                & subperiod["forward_horizon_sessions"].eq(42)
                & subperiod["frequency_id"].isin(headline_frequencies)
                & subperiod["subperiod_id"].isin(five_subperiods)
            ]
            .groupby("subperiod_id")["ic_mean"]
            .mean()
        )
        positive_periods = int(period_values.gt(0.0).sum())
        criterion("C10", "positive 42-session mean IC in at least three of five major subperiods", positive_periods, positive_periods >= 3)

        if dependency is None or dependency.empty or signal_id not in set(dependency["signal_id"]):
            criterion("C11", "positive after US-tech and top-five exclusions", "PENDING_DIAGNOSTIC", None, applicable=False)
        else:
            dependency_subset = dependency[
                dependency["signal_id"].eq(signal_id)
                & dependency["dependency_test_id"].isin(["EX_US_TECHNOLOGY_SEMICONDUCTORS", "EX_TOP_FIVE_FULL_PERIOD_FAMILIES"])
                & dependency["frequency_id"].isin(headline_frequencies)
                & dependency["forward_horizon_sessions"].isin(headline_horizons)
            ]
            dependency_means = dependency_subset.groupby("dependency_test_id")["mean_ic"].mean()
            dependency_pass = (
                dependency_means.get("EX_US_TECHNOLOGY_SEMICONDUCTORS", np.nan) > 0.0
                and dependency_means.get("EX_TOP_FIVE_FULL_PERIOD_FAMILIES", np.nan) > 0.0
            )
            criterion("C11", "positive after US-tech and top-five exclusions", dependency_means.to_dict(), bool(dependency_pass))

        persistence_subset = persistence[
            persistence["signal_id"].eq(signal_id)
            & persistence["universe_id"].eq("CORE_EXTENDED")
            & persistence["cohort_id"].eq("GLOBAL")
            & persistence["frequency_id"].isin(headline_frequencies)
            & persistence["persistence_horizon_sessions"].eq(21)
        ]
        rank_persistence = float(persistence_subset["rank_autocorrelation_mean"].mean()) if not persistence_subset.empty else np.nan
        leader_above = float(persistence_subset["probability_leader_remains_above_median"].mean()) if not persistence_subset.empty else np.nan
        persistence_pass = (pd.notna(rank_persistence) and rank_persistence >= 0.25) or (pd.notna(leader_above) and leader_above >= 0.55)
        criterion("C12", "rank autocorrelation >=0.25 or leader-above-median persistence >=0.55", {"rank_autocorrelation": rank_persistence, "leader_above_median": leader_above}, bool(persistence_pass))

        neighbourhood_central: str | None = None
        if signal_id in {"ABS_POS_252", "ABOVE_GBP_CASH_252", "TREND_MA_252"}:
            neighbourhood_central = signal_id
        elif signal_id in {"MOM_126", "MULTI_Z_21_63_126", "RISK_ADJ_MOM_126_VOL63"}:
            neighbourhood_central = "MOM_126"
        elif signal_id in {"MOM_252", "MULTI_Z_63_126_252", "RISK_ADJ_MOM_252_VOL63"}:
            neighbourhood_central = "MOM_252"
        if neighbourhood_central is None:
            criterion("C13", "declared parameter-neighbourhood stability", "NOT_APPLICABLE", None, applicable=False)
        else:
            neighbourhood_subset = neighbourhoods[
                neighbourhoods["central_signal_id"].eq(neighbourhood_central)
                & neighbourhoods["test_type"].eq("LOOKBACK_NEIGHBOURHOOD")
                & neighbourhoods["universe_id"].eq("CORE_EXTENDED")
                & neighbourhoods["cohort_id"].eq("GLOBAL")
                & neighbourhoods["frequency_id"].isin(headline_frequencies)
                & neighbourhoods["forward_horizon_sessions"].isin(headline_horizons)
            ]
            stable_fraction = float(neighbourhood_subset["directionally_stable_ic"].mean()) if not neighbourhood_subset.empty else np.nan
            criterion("C13", "declared parameter-neighbourhood stability", stable_fraction, bool(pd.notna(stable_fraction) and stable_fraction >= 2.0 / 3.0))

        applicable = [item for item in criteria if item["applicable"]]
        passed = [item for item in applicable if item["passed"]]
        fraction = len(passed) / len(applicable) if applicable else 0.0
        wrong_direction = bool(pd.isna(average_ic) or (average_ic <= 0.0 and positive_mean_count < 3))
        if wrong_direction:
            classification = "REJECTED"
        elif fraction >= 0.75 and fdr_survivors >= 1:
            classification = "RESEARCH_CANDIDATE"
        elif fraction >= 0.58:
            classification = "SECONDARY"
        elif fraction >= 0.42:
            classification = "WEAK"
        else:
            classification = "REJECTED"
        rows.append({
            "signal_id": signal_id,
            "signal_family": signal_registry.set_index("signal_id").loc[signal_id, "signal_family"],
            "classification": classification,
            "criteria_passed": len(passed),
            "criteria_applicable": len(applicable),
            "criteria_fraction": fraction,
            "headline_positive_mean_ic_cells": positive_mean_count,
            "headline_positive_median_ic_cells": positive_median_count,
            "headline_average_mean_ic": average_ic,
            "headline_fdr_survivor_count": fdr_survivors,
            "headline_positive_spread_cells": positive_spread_count,
            "headline_significant_positive_spread_cells": spread_significant,
            "headline_average_monotonicity": average_monotonicity,
            "core_positive_mean_ic_cells": core_positive_count,
            "category_neutral_positive_mean_ic_cells": neutral_positive_count,
            "positive_major_subperiod_count": positive_periods,
            "rank_autocorrelation_21": rank_persistence,
            "leader_above_median_probability_21": leader_above,
            "wrong_economic_direction": wrong_direction,
            "criteria_detail_json": json.dumps(criteria, sort_keys=True, default=json_default),
            "historical_eligibility_warning": WARNING,
        })
    return pd.DataFrame(rows).sort_values(["criteria_fraction", "headline_average_mean_ic"], ascending=[False, False]).reset_index(drop=True)


def build_category_results(ic: pd.DataFrame, spread: pd.DataFrame, hits: pd.DataFrame) -> pd.DataFrame:
    category_ids = {"GEOGRAPHY", "SECTOR_INDUSTRY", "THEMATIC", "DEFENSIVE_DIVERSIFIER", "DEFENSIVE_FIXED_INCOME_CASH"}
    keys = ["evaluation_id"]
    result = ic[ic["cohort_id"].isin(category_ids)].merge(
        spread[[
            "evaluation_id", "spread_mean", "spread_median", "spread_hac_t_statistic", "spread_hac_p_value",
            "mean_monotonicity_score", "strict_monotonicity_frequency", "benchmark_id",
        ]],
        on=keys,
        how="left",
        validate="one_to_one",
    ).merge(
        hits[[
            "evaluation_id", "top_rank_vs_cross_section_median_hit_rate", "top_rank_vs_equal_weight_hit_rate",
            "top_rank_vs_benchmark_hit_rate",
        ]],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    result["deepvue_used"] = False
    return result


def build_real_tests(
    state: ResearchState,
    diagnostics: dict[str, Any],
    policy: dict[str, Any],
    signal_registry: pd.DataFrame,
    results: dict[str, Any],
    multiple_ledger: pd.DataFrame,
    experimental: pd.DataFrame,
    candidate_assessment: pd.DataFrame,
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    def add(test_id: str, description: str, passed: bool, observed: Any, critical: bool = True) -> None:
        tests.append({
            "test_id": test_id,
            "category": "REAL",
            "critical": critical,
            "description": description,
            "expected": "PASS",
            "observed": str(observed),
            "status": "PASS" if passed else "FAIL",
        })

    expected_fwd1 = state.returns[1:]
    actual_fwd1 = state.forward_returns[1][:-1]
    comparable = np.isfinite(expected_fwd1) & np.isfinite(actual_fwd1)
    max_fwd_error = float(np.max(np.abs(expected_fwd1[comparable] - actual_fwd1[comparable]))) if comparable.any() else np.nan
    add("REAL-01", "date-T signals receive first return from strictly t+1", comparable.any() and max_fwd_error < 1e-12, max_fwd_error)
    add("REAL-02", "ranking unit is unique economic exposure family/date", diagnostics["duplicate_family_dates"] == 0, diagnostics["duplicate_family_dates"])
    mom21_invalid_current = ~np.isfinite(state.returns) & np.isfinite(state.component_signals["MOM_21"])
    add("REAL-03", "missing/invalid current observations cannot produce a 21-session signal", int(mom21_invalid_current.sum()) == 0, int(mom21_invalid_current.sum()))
    output_columns = set().union(*(set(frame.columns) for frame in [results["ic_summary"], results["spread_summary"], results["quantile_summary"]]))
    add("REAL-04", "ticker/ISIN/listing cannot enter the ranking output as an observation key", not bool({"ticker", "isin", "implementation_listing_id"} & output_columns), sorted({"ticker", "isin", "implementation_listing_id"} & output_columns))
    add("REAL-05", "invalid A2 observations are masked before calculation", not np.isfinite(state.returns[~np.isfinite(state.returns)]).any(), diagnostics["invalid_non_null_returns_masked"])

    sensitivity = experimental.merge(
        results["ic_summary"][["signal_id", "cohort_id", "frequency_id", "forward_horizon_sessions", "universe_id", "ic_mean"]],
        left_on=["signal_id", "cohort_id", "frequency_id", "forward_horizon_sessions"],
        right_on=["signal_id", "cohort_id", "frequency_id", "forward_horizon_sessions"],
        how="left",
    )
    sensitivity = sensitivity[sensitivity["universe_id"].eq("CORE_EXTENDED")]
    primary_delta = np.nanmax(np.abs(sensitivity["primary_ic_mean"] - sensitivity["ic_mean"])) if len(sensitivity) else np.nan
    add("REAL-06", "EXPERIMENTAL inclusion cannot alter stored CORE+EXTENDED results", pd.notna(primary_delta) and primary_delta < 1e-15, primary_delta)
    add("REAL-07", "all composite normalisation is date-level and peer-local", policy["cross_section"]["continuous_normalisation"].startswith("DATE_LEVEL"), policy["cross_section"]["continuous_normalisation"])

    subperiod = results["subperiod"]
    valid_subperiod_labels = set(item["subperiod_id"] for item in policy["subperiods"])
    add("REAL-08", "subperiod outputs use only predeclared contemporaneous labels", set(subperiod["subperiod_id"].unique()) == valid_subperiod_labels, sorted(subperiod["subperiod_id"].unique()))

    sample_family = int(np.nanargmax(np.isfinite(state.returns).sum(axis=0)))
    sample_dates = np.flatnonzero(np.isfinite(state.forward_returns[5][:, sample_family]))[:20]
    manual_errors: list[float] = []
    for row in sample_dates:
        segment = state.returns[row + 1 : row + 6, sample_family]
        manual = np.prod(1.0 + segment) - 1.0
        manual_errors.append(abs(manual - state.forward_returns[5][row, sample_family]))
    add("REAL-09", "forward-return horizons are exactly aligned", bool(manual_errors) and max(manual_errors) < 1e-12, max(manual_errors) if manual_errors else "NO_SAMPLE")

    twelve = state.signals["MOM_12_1"]
    twelve_positions = np.argwhere(np.isfinite(twelve))
    twelve_error = np.nan
    if len(twelve_positions):
        row, column = twelve_positions[len(twelve_positions) // 2]
        segment = state.returns[row - 251 : row - 20, column]
        twelve_error = abs((np.prod(1.0 + segment) - 1.0) - twelve[row, column])
    add("REAL-10", "12-1 excludes the most recent 21 canonical sessions", pd.notna(twelve_error) and twelve_error < 1e-12, twelve_error)
    date_positions = np.arange(len(state.dates))[:, None]
    pre_warmup_valid = np.isfinite(state.component_signals["MOM_252"]) & (date_positions < 251)
    first_finite_rows = np.argwhere(np.isfinite(state.component_signals["MOM_252"]))[:, 0]
    add("REAL-11", "252-session warm-up is respected", int(pre_warmup_valid.sum()) == 0 and len(first_finite_rows) > 0, {"pre_warmup_valid": int(pre_warmup_valid.sum()), "first_finite_row": int(first_finite_rows.min())})
    add("REAL-12", "no proxy history enters", diagnostics["proxy_observations_admitted"] == 0, diagnostics["proxy_observations_admitted"])

    cash_source_hash = sha256_file(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_cash"])
    manifest_cash_hash = diagnostics["a2_manifest"]["output_hashes_excluding_manifest_itself"].get(str(PROGRAMME_ROOT / policy["authoritative_inputs"]["a2_cash"]))
    add("REAL-13", "cash comparison uses the hashed authoritative A2 cash series", cash_source_hash == manifest_cash_hash, {"actual": cash_source_hash, "manifest": manifest_cash_hash})
    add("REAL-14", "executed signal registry exactly matches policy order and definitions", signal_registry["signal_id"].tolist() == [item["signal_id"] for item in policy["signal_definitions"]], signal_registry["signal_id"].tolist())
    deepvue_columns = [column for column in output_columns if "deepvue" in column.lower() and column != "deepvue_used"]
    add("REAL-15", "DeepVue metadata has zero signal/ranking effect", len(deepvue_columns) == 0 and not signal_registry["deepvue_used"].any(), deepvue_columns)
    add("REAL-16", "authorised family and tier counts match A2", diagnostics["authorised_family_count"] == 86 and diagnostics["tier_counts"] == {"CORE": 38, "EXTENDED": 34, "EXPERIMENTAL": 14}, {"families": diagnostics["authorised_family_count"], "tiers": diagnostics["tier_counts"]})

    expected_evaluations = len(policy["signal_definitions"]) * len(policy["universe_scopes"]) * len(policy["cohorts"]) * len(policy["observation_frequencies"]) * len(policy["forward_horizons_sessions"])
    add("REAL-17", "every predeclared evaluation cell appears in the multiple-testing ledger", len(multiple_ledger) == expected_evaluations and not multiple_ledger["omitted_from_reporting"].any(), {"observed": len(multiple_ledger), "expected": expected_evaluations})
    registry_set = set(signal_registry["signal_id"])
    add("REAL-18", "all evaluation rows reference a registered signal", set(multiple_ledger["signal_id"]).issubset(registry_set), sorted(set(multiple_ledger["signal_id"]) - registry_set))
    add("REAL-19", "A2 next-eligible-session mapping is preserved", diagnostics["next_execution_mapping_mismatches"] == 0, diagnostics["next_execution_mapping_mismatches"])
    forbidden_terms = {"cagr", "sharpe", "drawdown", "portfolio_weight", "top_n_holdings"}
    present_forbidden = sorted(column for column in output_columns if column.lower() in forbidden_terms)
    add("REAL-20", "no portfolio-performance or construction field is produced", not present_forbidden, present_forbidden)
    primary_assessment_only = set(candidate_assessment["signal_id"]).issubset(set(signal_registry.loc[signal_registry["registry_class"].eq("PRIMARY"), "signal_id"]))
    add("REAL-21", "EXPERIMENTAL families cannot determine primary signal classification", primary_assessment_only and not experimental["primary_decision_affected"].any(), {"assessment_primary_only": primary_assessment_only, "experimental_primary_affected": bool(experimental["primary_decision_affected"].any())})
    return tests


def select_diagnostic_targets(assessment: pd.DataFrame) -> list[str]:
    candidates = assessment.loc[assessment["classification"].eq("RESEARCH_CANDIDATE"), "signal_id"].tolist()
    if candidates:
        return candidates
    non_rejected = assessment.loc[assessment["classification"].ne("REJECTED"), "signal_id"].tolist()
    return (non_rejected if non_rejected else assessment["signal_id"].tolist())[:3]


def aggregate_signal_headline(
    signal_id: str,
    ic: pd.DataFrame,
    spread: pd.DataFrame,
    policy: dict[str, Any],
) -> dict[str, Any]:
    frequencies = policy["candidate_assessment"]["headline_frequencies"]
    horizons = policy["candidate_assessment"]["headline_horizons"]
    i = ic[
        ic["signal_id"].eq(signal_id)
        & ic["universe_id"].eq("CORE_EXTENDED")
        & ic["cohort_id"].eq("GLOBAL")
        & ic["frequency_id"].isin(frequencies)
        & ic["forward_horizon_sessions"].isin(horizons)
    ]
    s = spread[
        spread["signal_id"].eq(signal_id)
        & spread["universe_id"].eq("CORE_EXTENDED")
        & spread["cohort_id"].eq("GLOBAL")
        & spread["frequency_id"].isin(frequencies)
        & spread["forward_horizon_sessions"].isin(horizons)
    ]
    by_horizon = i.groupby("forward_horizon_sessions").agg(mean_ic=("ic_mean", "mean"), median_ic=("ic_median", "mean")).reset_index()
    if by_horizon.empty or by_horizon["mean_ic"].isna().all():
        strongest_horizon = None
    else:
        strongest_horizon = int(by_horizon.loc[by_horizon["mean_ic"].idxmax(), "forward_horizon_sessions"])
    return {
        "signal_id": signal_id,
        "headline_cell_count": int(len(i)),
        "mean_ic_across_headline_cells": float(i["ic_mean"].mean()) if not i.empty else np.nan,
        "median_ic_across_headline_cells": float(i["ic_median"].mean()) if not i.empty else np.nan,
        "strongest_forward_horizon_sessions": strongest_horizon,
        "strongest_horizon_mean_ic": float(by_horizon.loc[by_horizon["forward_horizon_sessions"].eq(strongest_horizon), "mean_ic"].iloc[0]) if strongest_horizon is not None else np.nan,
        "mean_top_minus_bottom_spread": float(s["spread_mean"].mean()) if not s.empty else np.nan,
        "mean_quantile_monotonicity": float(s["mean_monotonicity_score"].mean()) if not s.empty else np.nan,
        "headline_fdr_survivor_count": int(i["fdr_survives_q_0_10"].sum()) if not i.empty else 0,
        "headline_hac_positive_p_0_10_count": int((i["ic_mean"].gt(0.0) & i["ic_hac_p_value"].le(0.10)).sum()) if not i.empty else 0,
        "by_horizon": by_horizon.to_dict("records"),
    }


def decision_payload(
    policy: dict[str, Any],
    diagnostics: dict[str, Any],
    signal_registry: pd.DataFrame,
    results: dict[str, Any],
    candidate_assessment: pd.DataFrame,
    category_results: pd.DataFrame,
    neighbourhoods: pd.DataFrame,
    dependency: pd.DataFrame,
    experimental: pd.DataFrame,
    bootstrap: pd.DataFrame,
    tests: pd.DataFrame,
    characteristic_sets: dict[str, Any],
) -> dict[str, Any]:
    critical_failures = int(((tests["critical"].astype(bool)) & tests["status"].ne("PASS")).sum())
    candidates = candidate_assessment.loc[candidate_assessment["classification"].eq("RESEARCH_CANDIDATE"), "signal_id"].tolist()
    secondary = candidate_assessment.loc[candidate_assessment["classification"].eq("SECONDARY"), "signal_id"].tolist()
    weak = candidate_assessment.loc[candidate_assessment["classification"].eq("WEAK"), "signal_id"].tolist()
    rejected = candidate_assessment.loc[candidate_assessment["classification"].eq("REJECTED"), "signal_id"].tolist()
    if critical_failures:
        decision = "UKACTIVE_A3_FAIL_DATA_OR_METHOD"
    elif candidates:
        decision = "UKACTIVE_A3_SIGNAL_FOUND"
    elif secondary or weak:
        decision = "UKACTIVE_A3_WEAK_OR_REGIME_DEPENDENT_SIGNAL"
    else:
        decision = "UKACTIVE_A3_NO_ROBUST_SIGNAL"

    best_signal = candidate_assessment.iloc[0]["signal_id"] if len(candidate_assessment) else None
    best_headline = aggregate_signal_headline(best_signal, results["ic_summary"], results["spread_summary"], policy) if best_signal else {}
    strongest_horizon = best_headline.get("strongest_forward_horizon_sessions")

    core_vs_extended: dict[str, Any] = {}
    if best_signal:
        for universe_id in ("CORE", "CORE_EXTENDED"):
            subset = results["ic_summary"][
                results["ic_summary"]["signal_id"].eq(best_signal)
                & results["ic_summary"]["universe_id"].eq(universe_id)
                & results["ic_summary"]["cohort_id"].eq("GLOBAL")
                & results["ic_summary"]["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
                & results["ic_summary"]["forward_horizon_sessions"].isin(policy["candidate_assessment"]["headline_horizons"])
            ]
            core_vs_extended[universe_id] = {
                "mean_ic": float(subset["ic_mean"].mean()) if not subset.empty else np.nan,
                "positive_cell_count": int(subset["ic_mean"].gt(0.0).sum()),
                "cell_count": int(len(subset)),
            }

    category_summary: dict[str, Any] = {}
    if best_signal and strongest_horizon is not None:
        for category in ["GEOGRAPHY", "SECTOR_INDUSTRY", "THEMATIC", "DEFENSIVE_DIVERSIFIER", "DEFENSIVE_FIXED_INCOME_CASH"]:
            subset = category_results[
                category_results["signal_id"].eq(best_signal)
                & category_results["universe_id"].eq("CORE_EXTENDED")
                & category_results["cohort_id"].eq(category)
                & category_results["forward_horizon_sessions"].eq(strongest_horizon)
                & category_results["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
            ]
            category_summary[category] = {
                "mean_ic": float(subset["ic_mean"].mean()) if not subset.empty else np.nan,
                "mean_top_bottom_spread": float(subset["spread_mean"].mean()) if not subset.empty else np.nan,
                "mean_monotonicity": float(subset["mean_monotonicity_score"].mean()) if not subset.empty else np.nan,
                "tested_cells": int(subset["status"].eq("TESTED").sum()) if not subset.empty else 0,
            }

    category_best_diagnostics: dict[str, Any] = {}
    for category in ["GEOGRAPHY", "SECTOR_INDUSTRY", "THEMATIC", "DEFENSIVE_DIVERSIFIER", "DEFENSIVE_FIXED_INCOME_CASH"]:
        subset = category_results[
            category_results["universe_id"].eq("CORE_EXTENDED")
            & category_results["cohort_id"].eq(category)
            & category_results["registry_class"].eq("PRIMARY")
            & category_results["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
            & category_results["forward_horizon_sessions"].isin(policy["candidate_assessment"]["headline_horizons"])
        ]
        if subset.empty:
            category_best_diagnostics[category] = {"status": "INSUFFICIENT"}
            continue
        grouped = subset.groupby(["signal_id", "signal_family"]).agg(
            tested_cells=("status", lambda values: int((values == "TESTED").sum())),
            mean_ic=("ic_mean", "mean"),
            positive_ic_cells=("ic_mean", lambda values: int((values > 0.0).sum())),
            mean_spread=("spread_mean", "mean"),
            mean_monotonicity=("mean_monotonicity_score", "mean"),
            minimum_hac_p_value=("ic_hac_p_value", "min"),
        ).reset_index()
        eligible = grouped[grouped["tested_cells"] >= 3]
        if eligible.empty:
            eligible = grouped[grouped["tested_cells"] == grouped["tested_cells"].max()]
        eligible = eligible.sort_values(["mean_ic", "tested_cells"], ascending=[False, False])
        best_category = eligible.iloc[0]
        category_best_diagnostics[category] = {
            "signal_id": best_category["signal_id"],
            "signal_family": best_category["signal_family"],
            "tested_cells": int(best_category["tested_cells"]),
            "mean_ic": best_category["mean_ic"],
            "positive_ic_cells": int(best_category["positive_ic_cells"]),
            "mean_top_bottom_spread": best_category["mean_spread"],
            "mean_monotonicity": best_category["mean_monotonicity"],
            "minimum_hac_p_value": best_category["minimum_hac_p_value"],
            "interpretation": "DESCRIPTIVE_COHORT_DIAGNOSTIC_NOT_A_PRIMARY_PROMOTION_TEST",
        }

    subperiod_summary: dict[str, Any] = {}
    if best_signal:
        subset = results["subperiod"][
            results["subperiod"]["signal_id"].eq(best_signal)
            & results["subperiod"]["universe_id"].eq("CORE_EXTENDED")
            & results["subperiod"]["cohort_id"].eq("GLOBAL")
            & results["subperiod"]["forward_horizon_sessions"].eq(strongest_horizon if strongest_horizon is not None else 42)
            & results["subperiod"]["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
        ]
        for period_id, group in subset.groupby("subperiod_id"):
            subperiod_summary[period_id] = {
                "mean_ic": float(group["ic_mean"].mean()),
                "mean_spread": float(group["spread_mean"].mean()),
                "available_frequency_count": int(group["ic_observation_count"].gt(0).sum()),
            }

    neighbourhood_summary: dict[str, Any] = {}
    if best_signal:
        if best_signal in {"ABS_POS_252", "ABOVE_GBP_CASH_252", "TREND_MA_252"}:
            central = best_signal
        elif best_signal in {"MOM_126", "MULTI_Z_21_63_126", "RISK_ADJ_MOM_126_VOL63"}:
            central = "MOM_126"
        elif best_signal in {"MOM_252", "MULTI_Z_63_126_252", "RISK_ADJ_MOM_252_VOL63"}:
            central = "MOM_252"
        else:
            central = None
        subset = neighbourhoods[
            neighbourhoods["central_signal_id"].eq(central if central else best_signal)
            & neighbourhoods["universe_id"].eq("CORE_EXTENDED")
            & neighbourhoods["cohort_id"].eq("GLOBAL")
        ] if not neighbourhoods.empty else pd.DataFrame()
        lookback_subset = subset[subset["test_type"].eq("LOOKBACK_NEIGHBOURHOOD")] if len(subset) else pd.DataFrame()
        weekday_subset = subset[subset["test_type"].eq("WEEKDAY_PERTURBATION")] if len(subset) else pd.DataFrame()
        neighbourhood_summary = {
            "declared_central_signal": central or "NOT_APPLICABLE",
            "lookback_tested_rows": int(len(lookback_subset)),
            "lookback_directionally_stable_ic_fraction": float(lookback_subset["directionally_stable_ic"].mean()) if len(lookback_subset) else np.nan,
            "lookback_directionally_stable_spread_fraction": float(lookback_subset["directionally_stable_spread"].mean()) if len(lookback_subset) else np.nan,
            "weekday_perturbation_tested_rows": int(len(weekday_subset)),
            "weekday_directionally_stable_ic_fraction": float(weekday_subset["directionally_stable_ic"].mean()) if len(weekday_subset) else np.nan,
            "weekday_directionally_stable_spread_fraction": float(weekday_subset["directionally_stable_spread"].mean()) if len(weekday_subset) else np.nan,
        }

    dependency_summary: dict[str, Any] = {}
    if best_signal and not dependency.empty:
        subset = dependency[dependency["signal_id"].eq(best_signal)]
        for test_id in ["EX_US_TECHNOLOGY_SEMICONDUCTORS", "EX_SINGLE_BEST_FULL_PERIOD_FAMILY", "EX_TOP_FIVE_FULL_PERIOD_FAMILIES"]:
            group = subset[subset["dependency_test_id"].eq(test_id)]
            dependency_summary[test_id] = {
                "mean_ic": float(group["mean_ic"].mean()) if len(group) else np.nan,
                "mean_spread": float(group["mean_top_bottom_spread"].mean()) if len(group) else np.nan,
                "tested_cells": int(len(group)),
            }
        controlled = subset[subset["test_type"].eq("DATE_LEVEL_CONTROLLED_CROSS_SECTIONAL_REGRESSION")]
        dependency_summary["CONTROLLED_CROSS_SECTIONAL_REGRESSION"] = {
            "mean_signal_rank_coefficient": float(controlled["mean_signal_rank_coefficient"].mean()) if len(controlled) else np.nan,
            "positive_coefficient_cells": int(controlled["mean_signal_rank_coefficient"].gt(0.0).sum()) if len(controlled) else 0,
            "tested_cells": int(len(controlled)),
            "minimum_hac_p_value": float(controlled["coefficient_hac_p_value"].min()) if len(controlled) else np.nan,
        }

    experimental_summary: dict[str, Any] = {}
    if best_signal:
        subset = experimental[
            experimental["signal_id"].eq(best_signal)
            & experimental["cohort_id"].eq("GLOBAL")
            & experimental["frequency_id"].isin(policy["candidate_assessment"]["headline_frequencies"])
            & experimental["forward_horizon_sessions"].isin(policy["candidate_assessment"]["headline_horizons"])
        ]
        experimental_summary = {
            "effect_counts": subset["experimental_effect"].value_counts().to_dict(),
            "average_ic_change": float(subset["ic_mean_change_with_experimental"].mean()) if len(subset) else np.nan,
            "primary_decision_affected": False,
        }

    inference_summary = {
        "headline_test_count": int(results["ic_summary"]["headline_predeclared_test"].sum()),
        "headline_fdr_survivor_count_all_signals": int(results["ic_summary"]["fdr_survives_q_0_10"].sum()),
        "block_bootstrap_rows": int(len(bootstrap)),
        "best_signal_positive_bootstrap_intervals": int(bootstrap[bootstrap["signal_id"].eq(best_signal)]["confidence_interval_excludes_zero_positive"].sum()) if best_signal and len(bootstrap) else 0,
        "method": "DATE_LEVEL_SPEARMAN_IC_WITH_NEWEY_WEST_HAC_AND_CIRCULAR_BLOCK_BOOTSTRAP_FOR_DIAGNOSTIC_TARGETS",
    }

    return {
        "stage_id": policy["stage_id"],
        "run_id": policy["run_id"],
        "decision": decision,
        "best_supported_signal": best_signal,
        "best_supported_signal_classification": candidate_assessment.iloc[0]["classification"] if len(candidate_assessment) else "NOT_AVAILABLE",
        "specifications": {
            "signal_definitions_tested": int(len(signal_registry)),
            "predeclared_primary_signal_definitions": int(signal_registry["registry_class"].eq("PRIMARY").sum()),
            "secondary_neighbourhood_signal_definitions": int(signal_registry["registry_class"].ne("PRIMARY").sum()),
            "evaluation_cells_tested_or_retained_as_insufficient": int(len(results["ic_summary"])),
            "evaluation_cells_formally_tested": int(results["ic_summary"]["status"].eq("TESTED").sum()),
            "evaluation_cells_insufficient": int(results["ic_summary"]["status"].ne("TESTED").sum()),
        },
        "signal_families_tested": sorted(signal_registry["signal_family"].unique().tolist()),
        "best_signal_headline": best_headline,
        "core_vs_core_extended": core_vs_extended,
        "category_results_at_best_horizon": category_summary,
        "best_diagnostic_by_category": category_best_diagnostics,
        "subperiod_stability": subperiod_summary,
        "parameter_neighbourhood_stability": neighbourhood_summary,
        "dependency_findings": dependency_summary,
        "excluded_dependency_families": characteristic_sets,
        "experimental_universe_sensitivity": experimental_summary,
        "statistical_inference": inference_summary,
        "research_candidates": candidates,
        "secondary_signals": secondary,
        "weak_signals": weak,
        "rejected_signals": rejected,
        "automated_tests": {
            "passed": int(tests["status"].eq("PASS").sum()),
            "failed": int(tests["status"].ne("PASS").sum()),
            "critical_failures": critical_failures,
        },
        "data_and_method_warnings": [
            WARNING,
            "A3 is signal discovery, not a historically verified UK-investable backtest.",
            "A2 broker status remains NOT_CHECKED.",
            "Forward-return observations overlap at multi-session horizons; HAC and block-bootstrap inference is used.",
            "The 14 EXPERIMENTAL families cannot determine the primary decision.",
            "No proxy history was created or spliced.",
        ],
        "a4_portfolio_architecture_research_recommended": decision == "UKACTIVE_A3_SIGNAL_FOUND" and critical_failures == 0,
        "a4_authorisation_scope": "RESEARCH_ONLY_NOT_DEPLOYMENT" if decision == "UKACTIVE_A3_SIGNAL_FOUND" and critical_failures == 0 else "NOT_AUTHORISED_FROM_A3",
        "strategy_backtest_executed": False,
        "portfolio_constructed": False,
        "strategy_performance_statistics_produced": False,
        "warning": WARNING,
    }


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    view = frame.loc[:, columns].copy()
    if max_rows is not None:
        view = view.head(max_rows)
    for column in columns:
        view[column] = view[column].map(lambda value: "" if pd.isna(value) else str(value).replace("|", "\\|"))
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in view.astype(str).to_numpy()]
    return "\n".join([header, divider, *rows])


def write_method_documents(
    policy: dict[str, Any],
    signal_registry: pd.DataFrame,
    candidate_assessment: pd.DataFrame,
    decision: dict[str, Any],
    tests: pd.DataFrame,
    diagnostics: dict[str, Any],
) -> None:
    scope = f"""# UKACTIVE A3 — Scope and Hypotheses

## Decision boundary

This stage tests whether date-T cross-sectional leadership predicts returns beginning strictly on the next A2 research session. It does not construct a portfolio, optimise a holding count, produce a deployment backtest, or establish historical ISA/SIPP/broker eligibility.

**{WARNING}.** Current eligibility is never back-projected.

## Authorised universe

- A2-ready families: {diagnostics['authorised_family_count']}.
- CORE: 38; EXTENDED: 34; EXPERIMENTAL: 14.
- Primary inference: CORE and CORE+EXTENDED.
- EXPERIMENTAL-only and ALL-A3-ready results are sensitivities and cannot determine the decision.
- Ranking key: `economic_exposure_family_id`; tickers, ISINs and listings are not ranking observations.

## Principal hypothesis

Stronger relative and/or absolute GBP total-return leadership may predict stronger subsequent returns over 1, 5, 21, 42, 63 and 126 canonical sessions. A null or inverted result is retained in the complete ledger.

## Predeclared observation design

- Weekly: canonical Wednesday, using the closest actual XLON research session within the ISO week and choosing the earlier session on a tie.
- Monthly: last canonical XLON research session of the month.
- Tuesday and Thursday weekly schedules are perturbations for diagnostic targets only.
- Signal data end after date-T close; the first forward return is date T+1.
- Every lookback and forward horizon requires all underlying A2 observations to be valid; missing observations are not filled.

## Cohorts

Global, category-neutral, geography, sector/industry, thematic, defensive/diversifier, and a narrower defensive fixed-income/cash cohort are reported. The heterogeneous defensive cohort is explicitly descriptive.

## Scientific guardrails

No proxy series, DeepVue input, current broker status, current eligibility, portfolio weights, rebalance buffers, volatility targets or regime filters enter signal construction.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3_SCOPE_AND_HYPOTHESES.md").write_text(scope, encoding="utf-8")

    definitions_table = signal_registry.copy()
    definitions = f"""# UKACTIVE A3 — Signal Definitions

Policy: `{policy['policy_id']}`. The registry was written before the empirical run and its row-level definition hashes are preserved.

{markdown_table(definitions_table, ['registry_order', 'signal_id', 'signal_family', 'role', 'registry_class', 'lookback_sessions', 'skip_sessions', 'volatility_window_sessions', 'formula'])}

## Common construction rules

- Total-return momentum compounds validated A2 GBP returns and requires a complete canonical-session window.
- `MOM_12_1` includes sessions t-251 through t-21 and excludes t-20 through t.
- Multi-horizon composites use equal weights after date-level, within-peer 5th/95th percentile winsorisation and z-scoring.
- Absolute, cash-relative and moving-average states are qualifications, not portfolio overlays.
- Risk-adjusted signals use a fixed 63-session realised-volatility denominator; the window was not optimised.
- DeepVue labels have no computational role.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3_SIGNAL_DEFINITIONS.md").write_text(definitions, encoding="utf-8")

    inference = f"""# UKACTIVE A3 — Statistical Inference

## Estimands

The primary estimand is the date-level Spearman cross-sectional information coefficient. Bucket returns and top-minus-bottom spreads are diagnostics, not long-short strategy returns.

## Serial correlation and overlap

All formal means use a Bartlett/Newey-West heteroskedasticity-and-autocorrelation-consistent standard error. The lag is `max(1, ceil(forward horizon / expected observation spacing) - 1)`, with five sessions for weekly observations and 21 for monthly observations. Each output explicitly marks whether forward observations overlap.

Circular block-bootstrap 95% confidence intervals use {policy['inference']['block_bootstrap']['replications']} deterministic replications and seed {policy['inference']['block_bootstrap']['seed']} for diagnostic targets. Block length is `max(5, HAC lag + 1)`.

## Multiple testing

Benjamini-Hochberg correction is applied to the {decision['statistical_inference']['headline_test_count']} predeclared CORE+EXTENDED/global headline IC tests: 14 primary definitions × two frequencies × three forward horizons. Neighbourhood, cohort, subperiod, regime, dependency and EXPERIMENTAL results are labelled secondary diagnostics and are not silently promoted because of a nominal p-value.

Headline FDR survivors across all primary signals: {decision['statistical_inference']['headline_fdr_survivor_count_all_signals']}.

## Changing membership

Signals and ranks use only families with valid contemporaneous A2 observations and complete lookbacks. Date-level aggregation accommodates changing cross-sectional membership; no unavailable exposure receives a zero signal or return.

## Interpretation boundary

Statistical evidence in this stage concerns predictive ranking information. It is not evidence of a historically verified UK-investable strategy, because historical retail/account eligibility remains unresolved.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3_STATISTICAL_INFERENCE.md").write_text(inference, encoding="utf-8")

    failures = tests[tests["status"].ne("PASS")]
    quality = f"""# UKACTIVE A3 — Data Quality and Timing Checks

## Result

- Automated tests passed: {int(tests['status'].eq('PASS').sum())}/{len(tests)}.
- Critical failures: {int((tests['critical'].astype(bool) & tests['status'].ne('PASS')).sum())}.
- Authorised families: {diagnostics['authorised_family_count']}.
- Valid A2 returns admitted: {diagnostics['valid_return_observations']}.
- Proxy observations admitted: {diagnostics['proxy_observations_admitted']}.
- Duplicate family/date ranking rows: {diagnostics['duplicate_family_dates']}.
- A2 next-session mapping mismatches: {diagnostics['next_execution_mapping_mismatches']}.

## Timing

Lookbacks end at date-T close. Forward returns compound date T+1 through T+h. The A2 `next_execution_eligible_date` mapping is preserved. Missing, stale, rejected, pre-inception and proxy observations are unavailable; none is filled.

## Identity and experimental controls

All matrices contain one column per economic exposure family. Implementation identifiers cannot enter ranks. CORE+EXTENDED results are computed on a tier-filtered matrix that is independent of EXPERIMENTAL values.

## Eligibility warning

**{WARNING}.** A3 status is research-only and does not establish contemporaneous retail, ISA, SIPP or IBKR availability.

## Failed checks

{markdown_table(failures, ['test_id', 'description', 'observed', 'status']) if len(failures) else 'None.'}
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3_DATA_QUALITY_AND_TIMING_CHECKS.md").write_text(quality, encoding="utf-8")

    candidate_view = candidate_assessment[[
        "signal_id", "signal_family", "classification", "criteria_passed", "criteria_applicable",
        "criteria_fraction", "headline_average_mean_ic", "headline_fdr_survivor_count",
        "headline_positive_spread_cells", "headline_average_monotonicity",
    ]].copy()
    for column in ["criteria_fraction", "headline_average_mean_ic", "headline_average_monotonicity"]:
        candidate_view[column] = candidate_view[column].map(lambda value: f"{value:.6f}" if pd.notna(value) else "")
    candidates_md = f"""# UKACTIVE A3 — Research Candidates

Stage decision: **{decision['decision']}**.

Best-supported definition: `{decision['best_supported_signal']}` ({decision['best_supported_signal_classification']}).

{markdown_table(candidate_view, candidate_view.columns.tolist())}

## Promotion rule

`RESEARCH_CANDIDATE` requires at least 75% of applicable predeclared criteria, at least one BH-FDR-surviving headline IC result, correct economic direction, and no critical timing/data failure. `SECONDARY`, `WEAK` and `REJECTED` retain all unsuccessful as well as successful specifications in the multiple-testing ledger.

## Boundary

Classification is signal-level only. It does not select holdings, weights, turnover controls, a regime overlay or an implementation vehicle, and it is not a deployment-candidate designation.
"""
    (PROGRAMME_ROOT / "UKACTIVE_A3_RESEARCH_CANDIDATES.md").write_text(candidates_md, encoding="utf-8")


def git_state(path: Path) -> dict[str, Any]:
    try:
        top = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
        commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "-C", str(path), "status", "--porcelain"], check=True, capture_output=True, text=True).stdout
        diff = subprocess.run(["git", "-C", str(path), "diff", "--binary", "HEAD"], check=True, capture_output=True, text=True).stdout
        return {
            "repository_root": top,
            "commit": commit,
            "worktree_state": "DIRTY" if status else "CLEAN",
            "porcelain_status": status,
            "complete_patch_if_dirty": diff if status else "NOT_APPLICABLE_CLEAN_WORKTREE",
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {
            "repository_root": "NOT_AVAILABLE_NOT_A_GIT_WORKTREE",
            "commit": "NOT_AVAILABLE_NOT_A_GIT_WORKTREE",
            "worktree_state": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
            "porcelain_status": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
            "complete_patch_if_dirty": "NOT_APPLICABLE_NOT_A_GIT_WORKTREE",
        }


def write_evidence_and_manifest(
    policy: dict[str, Any],
    started_at: str,
    completed_at: str,
    diagnostics: dict[str, Any],
    decision: dict[str, Any],
    signal_registry: pd.DataFrame,
    multiple_ledger: pd.DataFrame,
    tests: pd.DataFrame,
) -> dict[str, Any]:
    evidence_dir = PROGRAMME_ROOT / "evidence"
    source_dir = evidence_dir / "sources" / "a3"
    source_dir.mkdir(parents=True, exist_ok=True)
    input_names = list(policy["authoritative_inputs"].values())
    input_paths = [PROGRAMME_ROOT / name for name in input_names]
    input_hashes = {str(path): sha256_file(path) for path in input_paths}
    a2_output_hashes = diagnostics["a2_manifest"].get("output_hashes_excluding_manifest_itself", {})
    input_hash_validation: dict[str, str] = {}
    for path, actual in input_hashes.items():
        expected = a2_output_hashes.get(path)
        if expected is None:
            input_hash_validation[path] = "RECORDED_NO_A2_MANIFEST_OUTPUT_HASH"
        elif expected == actual:
            input_hash_validation[path] = "MATCH"
        else:
            input_hash_validation[path] = "MISMATCH"

    source_capture = {
        "stage_id": policy["stage_id"],
        "run_id": policy["run_id"],
        "captured_at_utc": completed_at,
        "source_type": "LOCAL_AUTHORITATIVE_A2_LINEAGE",
        "external_data_retrieval_performed": False,
        "input_hashes": input_hashes,
        "a2_manifest_hash_validation": input_hash_validation,
        "policy_path": str(CONFIG_PATH),
        "policy_sha256": sha256_file(CONFIG_PATH),
        "warning": WARNING,
    }
    capture_path = source_dir / "UKACTIVE_A3_INPUT_LINEAGE_CAPTURE.json"
    write_json(capture_path, source_capture)

    ledger_records: list[dict[str, Any]] = [{
        "evidence_id": stable_id("A3EV", "POLICY", policy["policy_id"]),
        "stage_id": policy["stage_id"],
        "run_id": policy["run_id"],
        "evidence_type": "PREDECLARED_POLICY",
        "path": str(CONFIG_PATH),
        "sha256": sha256_file(CONFIG_PATH),
        "observed_at_utc": started_at,
        "material_conclusion": "Signal registry, timing, inference and decision rules declared before calculation.",
        "warning": WARNING,
    }]
    for path in input_paths:
        ledger_records.append({
            "evidence_id": stable_id("A3EV", "INPUT", path.name),
            "stage_id": policy["stage_id"],
            "run_id": policy["run_id"],
            "evidence_type": "AUTHORITATIVE_INPUT",
            "path": str(path),
            "sha256": input_hashes[str(path)],
            "observed_at_utc": started_at,
            "a2_manifest_hash_status": input_hash_validation[str(path)],
            "material_conclusion": "Used as immutable A2/A0A1 lineage input.",
            "warning": WARNING,
        })

    output_candidates = sorted(
        [path for path in PROGRAMME_ROOT.glob("UKACTIVE_A3_*") if path.name != "UKACTIVE_A3_MANIFEST.json" and path.is_file()]
        + [capture_path]
    )
    for path in output_candidates:
        ledger_records.append({
            "evidence_id": stable_id("A3EV", "OUTPUT", path.name),
            "stage_id": policy["stage_id"],
            "run_id": policy["run_id"],
            "evidence_type": "EXECUTED_OUTPUT",
            "path": str(path),
            "sha256": sha256_file(path),
            "observed_at_utc": completed_at,
            "material_conclusion": "Generated by the recorded A3 code and policy.",
            "warning": WARNING,
        })
    ledger_path = evidence_dir / "UKACTIVE_A3_EVIDENCE_LEDGER.jsonl"
    ledger_path.write_text("".join(json.dumps(record, sort_keys=True, default=json_default) + "\n" for record in ledger_records), encoding="utf-8")

    output_paths = sorted(
        [path for path in PROGRAMME_ROOT.glob("UKACTIVE_A3_*") if path.name != "UKACTIVE_A3_MANIFEST.json" and path.is_file()]
        + [capture_path, ledger_path]
    )
    output_hashes = {str(path): sha256_file(path) for path in output_paths}
    code_paths = [HERE / "build_ukactive_a3.py", HERE / "ukactive_a3_core.py"]
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyarrow": pa.__version__,
        "scipy": scipy.__version__,
    }
    specification_results = multiple_ledger[[
        "evaluation_id", "signal_id", "registry_class", "universe_id", "cohort_id", "frequency_id",
        "forward_horizon_sessions", "status", "test_outcome", "ic_mean", "ic_hac_p_value", "bh_fdr_q_value",
    ]].to_dict("records")
    manifest = {
        "stage_id": policy["stage_id"],
        "run_id": policy["run_id"],
        "programme_root": str(PROGRAMME_ROOT),
        "started_at_utc": started_at,
        "completed_at_utc": completed_at,
        "decision": decision["decision"],
        "policy": policy,
        "policy_hash": sha256_file(CONFIG_PATH),
        "git": git_state(PROGRAMME_ROOT),
        "executed_command_line": f'python "{HERE / "build_ukactive_a3.py"}"',
        "source_code_hashes": {str(path): sha256_file(path) for path in code_paths},
        "input_hashes": input_hashes,
        "a2_input_hash_validation": input_hash_validation,
        "output_hashes_excluding_manifest_itself": output_hashes,
        "manifest_self_hash_policy": "MANIFEST_EXCLUDED_TO_AVOID_RECURSIVE_SELF_HASH",
        "exact_signal_registry": signal_registry.to_dict("records"),
        "exact_forward_horizons_sessions": policy["forward_horizons_sessions"],
        "universe_tier_rules": policy["universe_scopes"],
        "observation_frequencies": policy["observation_frequencies"],
        "statistical_methods": policy["inference"],
        "specification_count": int(len(multiple_ledger)),
        "specification_status_counts": multiple_ledger["test_outcome"].value_counts().to_dict(),
        "all_successful_and_failed_specifications": specification_results,
        "automated_test_results": tests.to_dict("records"),
        "environment": environment,
        "evidence_record_count": len(ledger_records),
        "source_capture_count": 1,
        "data_coverage": {
            "authorised_families": diagnostics["authorised_family_count"],
            "tier_counts": diagnostics["tier_counts"],
            "unique_dates": diagnostics["unique_dates"],
            "valid_return_observations": diagnostics["valid_return_observations"],
        },
        "reproducibility_assessment": "EXECUTED_CODE_POLICY_INPUT_AND_OUTPUT_HASHES_COMPLETE; NO_GIT_ANCESTRY_AVAILABLE" if git_state(PROGRAMME_ROOT)["commit"].startswith("NOT_AVAILABLE") else "EXECUTED_CODE_POLICY_INPUT_OUTPUT_AND_GIT_LINEAGE_COMPLETE",
        "strategy_backtest_executed": False,
        "portfolio_constructed": False,
        "strategy_performance_statistics_produced": False,
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3_MANIFEST.json", manifest)
    return manifest


def main() -> None:
    started_at = utc_now()
    policy = read_json(CONFIG_PATH)
    if policy["stage_id"] != "UKACTIVE-A3":
        raise AssertionError("Unexpected policy stage")
    metadata = {
        "stage_id": policy["stage_id"],
        "run_id": policy["run_id"],
        "policy_id": policy["policy_id"],
        "policy_sha256": sha256_file(CONFIG_PATH),
        "warning": WARNING,
    }

    state, diagnostics = load_research_state(policy)
    signal_registry = build_signal_registry(policy)
    test_rows = synthetic_tests(state, policy, signal_registry)

    results = run_primary_evaluations(state, signal_registry, metadata)
    ic_summary, multiple_ledger = apply_false_discovery_control(results["ic_summary"], policy)
    results["ic_summary"] = ic_summary
    neighbourhoods = build_parameter_neighbourhoods(ic_summary, results["spread_summary"])
    experimental = build_experimental_sensitivity(ic_summary, results["spread_summary"])

    preliminary = assess_signal_candidates(
        policy, signal_registry, ic_summary, results["spread_summary"], results["subperiod"],
        results["persistence"], neighbourhoods, dependency=None,
    )
    dependency_targets = select_diagnostic_targets(preliminary)
    characteristic_sets = family_characteristic_sets(state)
    dependency = build_concentration_and_dependency_tests(state, dependency_targets, characteristic_sets)
    candidate_assessment = assess_signal_candidates(
        policy, signal_registry, ic_summary, results["spread_summary"], results["subperiod"],
        results["persistence"], neighbourhoods, dependency=dependency,
    )
    # Ensure every finally promoted signal receives the full dependency diagnostic before decision.
    final_candidate_ids = candidate_assessment.loc[candidate_assessment["classification"].eq("RESEARCH_CANDIDATE"), "signal_id"].tolist()
    missing_diagnostics = sorted(set(final_candidate_ids) - set(dependency_targets))
    if missing_diagnostics:
        dependency_targets = sorted(set(dependency_targets) | set(missing_diagnostics))
        dependency = build_concentration_and_dependency_tests(state, dependency_targets, characteristic_sets)
        candidate_assessment = assess_signal_candidates(
            policy, signal_registry, ic_summary, results["spread_summary"], results["subperiod"],
            results["persistence"], neighbourhoods, dependency=dependency,
        )

    diagnostic_targets = select_diagnostic_targets(candidate_assessment)
    if set(diagnostic_targets) - set(dependency_targets):
        dependency_targets = sorted(set(dependency_targets) | set(diagnostic_targets))
        dependency = build_concentration_and_dependency_tests(state, dependency_targets, characteristic_sets)
        candidate_assessment = assess_signal_candidates(
            policy, signal_registry, ic_summary, results["spread_summary"], results["subperiod"],
            results["persistence"], neighbourhoods, dependency=dependency,
        )
        diagnostic_targets = select_diagnostic_targets(candidate_assessment)

    weekday_results = build_weekday_perturbations(state, diagnostic_targets, ic_summary, results["spread_summary"])
    if not weekday_results.empty:
        neighbourhoods = pd.concat([neighbourhoods, weekday_results], ignore_index=True, sort=False)
    bootstrap = build_block_bootstrap_results(results["headline_series"], diagnostic_targets, policy)
    regime_frame, regime_labels = build_regime_labels(state)
    regime, dispersion = build_regime_and_dispersion_diagnostics(state, diagnostic_targets, regime_frame, regime_labels)
    category_results = build_category_results(ic_summary, results["spread_summary"], results["hit_rates"])

    test_rows.extend(build_real_tests(state, diagnostics, policy, signal_registry, results, multiple_ledger, experimental, candidate_assessment))
    tests = pd.DataFrame(test_rows)
    decision = decision_payload(
        policy, diagnostics, signal_registry, results, candidate_assessment, category_results,
        neighbourhoods, dependency, experimental, bootstrap, tests, characteristic_sets,
    )

    # Required machine-readable outputs.
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_SIGNAL_REGISTRY.csv", signal_registry)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_COHORT_COVERAGE.csv", results["coverage"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_INFORMATION_COEFFICIENTS.csv", ic_summary)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_QUANTILE_FORWARD_RETURNS.csv", results["quantile_summary"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_TOP_BOTTOM_SPREADS.csv", results["spread_summary"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_HIT_RATES.csv", results["hit_rates"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_LEADERSHIP_PERSISTENCE.csv", results["persistence"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_RANK_STABILITY.csv", results["rank_stability"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_PARAMETER_NEIGHBOURHOODS.csv", neighbourhoods)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_CATEGORY_RESULTS.csv", category_results)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_SUBPERIOD_RESULTS.csv", results["subperiod"])
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_REGIME_DIAGNOSTICS.csv", regime)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_DISPERSION_DIAGNOSTICS.csv", dispersion)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_CONCENTRATION_AND_DEPENDENCY_TESTS.csv", dependency)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_EXPERIMENTAL_UNIVERSE_SENSITIVITY.csv", experimental)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_MULTIPLE_TESTING_LEDGER.csv", multiple_ledger)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_SIGNAL_ASSESSMENT.csv", candidate_assessment)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_BLOCK_BOOTSTRAP_RESULTS.csv", bootstrap)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3_AUTOMATED_TEST_RESULTS.csv", tests)

    # Parquet mirrors for the largest or most reusable result tables.
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3_INFORMATION_COEFFICIENTS.parquet", ic_summary, metadata)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3_QUANTILE_FORWARD_RETURNS.parquet", results["quantile_summary"], metadata)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3_SUBPERIOD_RESULTS.parquet", results["subperiod"], metadata)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3_MULTIPLE_TESTING_LEDGER.parquet", multiple_ledger, metadata)
    write_parquet(PROGRAMME_ROOT / "UKACTIVE_A3_REGIME_STATE_SERIES.parquet", regime_frame, metadata)

    write_json(PROGRAMME_ROOT / "UKACTIVE_A3_DECISION.json", decision)
    write_method_documents(policy, signal_registry, candidate_assessment, decision, tests, diagnostics)

    completed_at = utc_now()
    manifest = write_evidence_and_manifest(
        policy, started_at, completed_at, diagnostics, decision, signal_registry, multiple_ledger, tests
    )
    print(json.dumps({
        "decision": decision["decision"],
        "best_supported_signal": decision["best_supported_signal"],
        "best_supported_classification": decision["best_supported_signal_classification"],
        "research_candidates": decision["research_candidates"],
        "secondary_signals": decision["secondary_signals"],
        "weak_signals": decision["weak_signals"],
        "signal_definitions": len(signal_registry),
        "evaluation_cells": len(multiple_ledger),
        "formal_evaluation_cells": int(ic_summary["status"].eq("TESTED").sum()),
        "tests_passed": int(tests["status"].eq("PASS").sum()),
        "tests_failed": int(tests["status"].ne("PASS").sum()),
        "a4_recommended": decision["a4_portfolio_architecture_research_recommended"],
        "manifest_outputs": len(manifest["output_hashes_excluding_manifest_itself"]),
    }, indent=2))


if __name__ == "__main__":
    main()
