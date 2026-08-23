"""Portfolio-research primitives for UKACTIVE-A3R2.

The functions operate on A2R2 endpoint wealth. Missing valuations remain
missing; no price or return is forward-filled. A trade is scheduled only at a
common valid endpoint after the review close and within the frozen tolerance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Iterable

import numpy as np
import pandas as pd

import build_ukactive_a3r1 as a3
import build_ukactive_a3r1r1 as a3r1r1
from ukactive_a3r1_core import percentile_rank


PORTFOLIO_SIGNALS = [
    "MH_LEVEL_3_6_12_REFERENCE",
    "MH_LEVEL_EQ",
    "MH_LEVEL_60D_CENTERED",
    "MH_LEVEL_RECENCY_TILT",
    "PAIRWISE_MAJORITY_5H",
    "SHORT_RS_1_2_3_EQ",
    "SHORT_RS_1_2_3_PERSISTENT",
]
PORTFOLIO_POOLS = ["INDUSTRY", "THEME", "INDUSTRY_PLUS_THEME"]
INTELLIGENCE_POOLS = ["GEOGRAPHY", "COUNTRY", "SECTOR", "ALL_EQUITY_OPPORTUNITIES"]
SELECTION_RULES = ["TOP_1", "TOP_2", "TOP_3", "TOP_5", "VARIABLE_THRESHOLD"]
CADENCES = ["WEEKLY", "FORTNIGHTLY", "MONTHLY"]


@dataclass
class ResearchData:
    inputs: a3.Inputs
    matrices: a3.Matrices
    metadata: pd.DataFrame
    eligibility: pd.DataFrame
    wealth: pd.DataFrame
    valid: pd.DataFrame
    segment: pd.DataFrame
    daily_returns: pd.DataFrame
    calendar: pd.DatetimeIndex
    definitions: list[dict[str, Any]]
    membership: pd.DataFrame


@dataclass
class SimulationResult:
    curve: pd.DataFrame
    trades: pd.DataFrame
    targets: pd.DataFrame


def schedule_positions(calendar: pd.DatetimeIndex, cadence: str) -> np.ndarray:
    dates = pd.DatetimeIndex(calendar)
    if cadence == "WEEKLY":
        return a3.weekly_last_positions(dates)
    if cadence == "FORTNIGHTLY":
        weekly = a3.weekly_last_positions(dates)
        weekly_dates = dates[weekly]
        week_number = ((weekly_dates - pd.Timestamp("1970-01-05")).days // 7).astype(int)
        return weekly[(week_number % 2) == 0]
    if cadence == "MONTHLY":
        frame = pd.DataFrame({"date": dates, "position": np.arange(len(dates), dtype=int)})
        return frame.groupby([frame["date"].dt.year, frame["date"].dt.month], sort=True).tail(1)["position"].to_numpy(int)
    raise ValueError(f"Unknown cadence: {cadence}")


def load_research_data() -> ResearchData:
    inputs = a3r1r1.load_inputs()
    metadata = a3.candidate_metadata(inputs)
    matrices, eligibility = a3r1r1.build_matrices(inputs, metadata)
    definitions, membership = a3.contexts(metadata)
    industry = set(metadata.loc[metadata["research_group_id"].eq("INDUSTRY"), "economic_exposure_family_id"])
    theme = set(metadata.loc[metadata["research_group_id"].eq("THEME"), "economic_exposure_family_id"])
    definitions.append(
        {
            "context_id": "INDUSTRY_PLUS_THEME",
            "context_type": "COMBINED_ROLE_GROUP",
            "members": sorted(industry | theme),
            "primary_group": False,
        }
    )
    meta_index = metadata.set_index("economic_exposure_family_id")
    extra = []
    for family in sorted(industry | theme):
        row = meta_index.loc[family]
        extra.append(
            {
                "analysis_context_id": "INDUSTRY_PLUS_THEME",
                "analysis_context_type": "COMBINED_ROLE_GROUP",
                "context_primary_for_a3r1": "NO",
                "economic_exposure_family_id": family,
                "economic_exposure_name": row["economic_exposure_name"],
                "primary_rotation_role": row["primary_rotation_role"],
                "a2r_primary_competition_pool_id": row["primary_competition_pool_id"],
                "universe_tier": row["universe_tier"],
                "a2r_research_maturity": row["research_maturity"],
                "parent_exposure_family_id": row["parent_exposure_family_id"],
                "parent_benchmark_family_id": row["effective_parent_benchmark_family_id"],
                "overlap_cluster_id": row["overlap_cluster_id"],
                "warning": a3.WARNING,
            }
        )
    membership = pd.concat([membership, pd.DataFrame(extra)], ignore_index=True)

    all_needed = sorted(set(metadata["economic_exposure_family_id"]) | {"GLOBAL_DEVELOPED_WORLD", "GLOBAL_ALL_WORLD"})
    wealth = (
        eligibility.loc[eligibility["economic_exposure_family_id"].isin(all_needed)]
        .pivot(index="date", columns="economic_exposure_family_id", values="signal_wealth_index_gbp")
        .reindex(index=inputs.calendar, columns=all_needed)
        .astype(float)
    )
    valid = (
        eligibility.loc[eligibility["economic_exposure_family_id"].isin(all_needed)]
        .pivot(index="date", columns="economic_exposure_family_id", values="endpoint_valid")
        .reindex(index=inputs.calendar, columns=all_needed)
        .fillna(False)
        .astype(bool)
    )
    wealth = wealth.where(valid)
    segment = (
        eligibility.loc[eligibility["economic_exposure_family_id"].isin(all_needed)]
        .pivot(index="date", columns="economic_exposure_family_id", values="continuity_segment_id")
        .reindex(index=inputs.calendar, columns=all_needed)
    )
    daily_panel = inputs.panel.loc[inputs.panel["economic_exposure_family_id"].isin(all_needed)].copy()
    daily_valid = (
        daily_panel["data_valid"].astype(bool)
        & ~daily_panel["stale_flag"].astype(bool)
        & ~daily_panel["missing_flag"].astype(bool)
        & ~daily_panel["proxy_flag"].astype(bool)
        & daily_panel["return_gbp_total"].notna()
    )
    daily_panel.loc[~daily_valid, "return_gbp_total"] = np.nan
    daily_returns = (
        daily_panel.pivot(index="date", columns="economic_exposure_family_id", values="return_gbp_total")
        .reindex(index=inputs.calendar, columns=all_needed)
        .astype(float)
    )
    return ResearchData(inputs, matrices, metadata, eligibility, wealth, valid, segment, daily_returns, inputs.calendar, definitions, membership)


def definitions_for(data: ResearchData, context_ids: Iterable[str]) -> list[dict[str, Any]]:
    requested = set(context_ids)
    return [definition for definition in data.definitions if definition["context_id"] in requested]


def features_for_cadence(
    data: ResearchData,
    cadence: str,
    context_ids: Iterable[str],
    weights: dict[str, dict[str, float]],
) -> pd.DataFrame:
    positions = schedule_positions(data.calendar, cadence)
    matrices = replace(data.matrices, weekly_positions=positions, weekly_dates=data.calendar[positions])
    inputs = replace(data.inputs, policy={**data.inputs.policy, "multi_horizon_weights": weights})
    definitions = definitions_for(data, context_ids)
    features = a3.build_group_features(inputs, matrices, data.metadata, definitions)
    features["SHORT_RS_1_2_3_EQ"] = features[["RANK_RS_21", "RANK_RS_42", "RANK_RS_63"]].mean(axis=1, skipna=False)
    features["SHORT_RS_1_2_3_PERSISTENT"] = features["SHORT_RS_1_2_3_EQ"].where(features["RECENT_POSITIVE_SEGMENTS"].ge(2))
    features["short_persistent_base_eligible"] = (
        features["SHORT_RS_1_2_3_EQ"].notna() & features["RECENT_POSITIVE_SEGMENTS"].notna()
    )

    change_parts = []
    for definition in definitions:
        members = definition["members"]
        if not members:
            continue
        ranks = percentile_rank(data.matrices.relative_strength[63][members], minimum_count=3)
        change = ranks - ranks.shift(21)
        sampled = change.iloc[positions].copy()
        sampled.index = data.calendar[positions]
        long = sampled.stack(future_stack=True).rename("RS63_RANK_CHANGE_21").reset_index()
        long.columns = ["date", "economic_exposure_family_id", "RS63_RANK_CHANGE_21"]
        long["analysis_context_id"] = definition["context_id"]
        change_parts.append(long)
    changes = pd.concat(change_parts, ignore_index=True)
    features = features.merge(
        changes,
        on=["date", "economic_exposure_family_id", "analysis_context_id"],
        how="left",
        validate="one_to_one",
    )
    features["cadence"] = cadence
    if features.duplicated(["date", "analysis_context_id", "economic_exposure_family_id"]).any():
        raise AssertionError("Feature identity duplicated")
    return features.sort_values(["cadence", "analysis_context_id", "date", "economic_exposure_family_id"]).reset_index(drop=True)


def selection_targets(
    features: pd.DataFrame,
    *,
    signal_id: str,
    selection_rule: str,
    allowed_families: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
    excluded_families: set[str] | None = None,
    weighting_method: str = "EQUAL",
    volatility: pd.DataFrame | None = None,
    maximum_weight: float = 0.5,
) -> tuple[dict[pd.Timestamp, dict[str, float]], pd.DataFrame]:
    if signal_id not in PORTFOLIO_SIGNALS:
        raise ValueError(signal_id)
    excluded = excluded_families or set()
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    records: list[dict[str, Any]] = []
    for date, source in features.groupby("date", sort=True):
        frame = source.copy()
        if allowed_families is not None:
            frame = frame.loc[frame["economic_exposure_family_id"].isin(allowed_families)]
        if excluded:
            frame = frame.loc[~frame["economic_exposure_family_id"].isin(excluded)]
        if maturity_scope == "MATURE_ONLY":
            frame = frame.loc[frame["contemporaneous_research_maturity"].eq("MATURE")]
        elif maturity_scope == "MATURE_PLUS_DEVELOPING":
            frame = frame.loc[frame["contemporaneous_research_maturity"].isin(["MATURE", "DEVELOPING"])]
        elif maturity_scope != "DYNAMIC_POINT_IN_TIME":
            raise ValueError(maturity_scope)

        if signal_id == "SHORT_RS_1_2_3_PERSISTENT":
            eligible = frame.loc[frame["short_persistent_base_eligible"]].copy()
        else:
            eligible = frame.loc[frame[signal_id].notna()].copy()
        qualified = eligible.loc[eligible[signal_id].notna()].copy()
        qualified = qualified.sort_values([signal_id, "economic_exposure_family_id"], ascending=[False, True])

        if selection_rule.startswith("TOP_"):
            requested = int(selection_rule.split("_")[1])
            selected = qualified.head(requested)
        elif selection_rule == "VARIABLE_THRESHOLD":
            selected = qualified.loc[qualified[signal_id].ge(0.80) & qualified["RS_63"].gt(0)].head(5)
        else:
            raise ValueError(selection_rule)

        raw_scores = selected.set_index("economic_exposure_family_id")[signal_id].astype(float)
        if len(raw_scores) == 0:
            weights = pd.Series(dtype=float)
        elif len(raw_scores) == 1:
            weights = pd.Series(1.0, index=raw_scores.index)
        elif weighting_method == "EQUAL":
            weights = pd.Series(1.0 / len(raw_scores), index=raw_scores.index)
        elif weighting_method == "RANK_DECAY":
            ranks = pd.Series(np.arange(1, len(raw_scores) + 1), index=raw_scores.index, dtype=float)
            raw_rank_weights = (1.0 / ranks) / (1.0 / ranks).sum()
            weights = _cap_weights(raw_rank_weights, maximum_weight)
        elif weighting_method == "SCORE_PROPORTIONAL_CAPPED":
            threshold = 0.80 if selection_rule == "VARIABLE_THRESHOLD" else float(raw_scores.min()) - 1e-12
            conviction = (raw_scores - threshold).clip(lower=1e-9)
            weights = _cap_weights(conviction / conviction.sum(), maximum_weight)
        elif weighting_method in {"INVERSE_VOLATILITY_CAPPED", "SIGNAL_X_INVERSE_VOLATILITY"}:
            if volatility is None or date not in volatility.index:
                weights = pd.Series(dtype=float)
            else:
                vol = volatility.loc[date, raw_scores.index].astype(float)
                if vol.isna().any() or (vol <= 0).any():
                    weights = pd.Series(dtype=float)
                else:
                    base = 1.0 / vol
                    if weighting_method == "SIGNAL_X_INVERSE_VOLATILITY":
                        threshold = 0.80 if selection_rule == "VARIABLE_THRESHOLD" else float(raw_scores.min()) - 1e-12
                        base = base * (raw_scores - threshold).clip(lower=1e-9)
                    weights = _cap_weights(base / base.sum(), maximum_weight)
        else:
            raise ValueError(weighting_method)
        targets[pd.Timestamp(date)] = weights.to_dict()
        records.append(
            {
                "review_date": pd.Timestamp(date),
                "eligible_family_count": int(len(eligible)),
                "qualified_family_count": int(len(qualified)),
                "selected_family_count": int(len(weights)),
                "selected_families": ";".join(weights.index),
                "target_weights": ";".join(f"{key}:{value:.12g}" for key, value in weights.items()),
                "selection_rule": selection_rule,
                "signal_id": signal_id,
                "maturity_scope": maturity_scope,
                "weighting_method": weighting_method,
            }
        )
    return targets, pd.DataFrame(records)


def _cap_weights(weights: pd.Series, cap: float) -> pd.Series:
    result = weights.astype(float).copy()
    if len(result) <= 1:
        return pd.Series(1.0, index=result.index)
    cap = float(cap)
    for _ in range(20):
        over = result > cap + 1e-12
        if not over.any():
            break
        excess = float((result[over] - cap).sum())
        result.loc[over] = cap
        under = ~over
        if not under.any() or result.loc[under].sum() <= 0:
            break
        result.loc[under] += excess * result.loc[under] / result.loc[under].sum()
    return result / result.sum()


def equal_pool_targets(
    target_records: pd.DataFrame,
    features: pd.DataFrame,
    signal_id: str,
    allowed: set[str] | None = None,
    maturity_scope: str = "DYNAMIC_POINT_IN_TIME",
) -> dict[pd.Timestamp, dict[str, float]]:
    targets: dict[pd.Timestamp, dict[str, float]] = {}
    records = target_records.set_index("review_date")
    for date, group in features.groupby("date", sort=True):
        frame = group
        if allowed is not None:
            frame = frame.loc[frame["economic_exposure_family_id"].isin(allowed)]
        if maturity_scope == "MATURE_ONLY":
            frame = frame.loc[frame["contemporaneous_research_maturity"].eq("MATURE")]
        elif maturity_scope == "MATURE_PLUS_DEVELOPING":
            frame = frame.loc[frame["contemporaneous_research_maturity"].isin(["MATURE", "DEVELOPING"])]
        elif maturity_scope != "DYNAMIC_POINT_IN_TIME":
            raise ValueError(maturity_scope)
        if signal_id == "SHORT_RS_1_2_3_PERSISTENT":
            frame = frame.loc[frame["short_persistent_base_eligible"]]
        else:
            frame = frame.loc[frame[signal_id].notna()]
        families = sorted(frame["economic_exposure_family_id"].unique())
        # Match the selected portfolio's activation date, including a legitimate
        # zero-invested variable-threshold review.
        if pd.Timestamp(date) not in records.index or int(records.loc[pd.Timestamp(date), "eligible_family_count"]) == 0:
            targets[pd.Timestamp(date)] = {}
        else:
            targets[pd.Timestamp(date)] = {family: 1.0 / len(families) for family in families} if families else {}
    return targets


def unselected_targets(
    selected_targets: dict[pd.Timestamp, dict[str, float]],
    pool_targets: dict[pd.Timestamp, dict[str, float]],
) -> dict[pd.Timestamp, dict[str, float]]:
    result: dict[pd.Timestamp, dict[str, float]] = {}
    for date, pool in pool_targets.items():
        families = sorted(set(pool) - set(selected_targets.get(date, {})))
        result[date] = {family: 1.0 / len(families) for family in families} if families else {}
    return result


def simulate_targets(
    targets: dict[pd.Timestamp, dict[str, float]],
    *,
    calendar: pd.DatetimeIndex,
    wealth: pd.DataFrame,
    segment: pd.DataFrame | None = None,
    friction_bps: float = 0.0,
    fixed_fee_gbp: float = 0.0,
    sleeve_size_gbp: float = 250_000.0,
    non_gbp_families: set[str] | None = None,
    fx_rate: float = 0.0,
    max_execution_lag: int = 3,
    rebalance_same_members: bool = False,
) -> SimulationResult:
    non_gbp = non_gbp_families or set()
    date_position = {pd.Timestamp(date): index for index, date in enumerate(calendar)}
    review_targets = {pd.Timestamp(date): dict(value) for date, value in targets.items() if pd.Timestamp(date) in date_position}
    wealth = wealth.reindex(calendar)
    segment = segment.reindex(calendar) if segment is not None else None
    column_position = {name: index for index, name in enumerate(wealth.columns)}
    wealth_array = wealth.to_numpy(float)
    segment_array = segment.to_numpy() if segment is not None else None
    planned_events: list[dict[str, Any]] = []
    cancelled_events: list[dict[str, Any]] = []
    planned_members: set[str] = set()
    planned_entry_segments: dict[str, Any] = {}
    started = False
    for review_date, target in sorted(review_targets.items()):
        if not started and not target:
            continue
        if not (rebalance_same_members or set(target) != planned_members):
            continue
        review_position = date_position[review_date]
        execution_position = None
        for step in range(1, max_execution_lag + 1):
            candidate_position = review_position + step
            if candidate_position >= len(calendar):
                break
            valid = True
            for family in planned_members | set(target):
                column = column_position[family]
                valid &= np.isfinite(wealth_array[candidate_position, column])
                if family in planned_members and segment_array is not None:
                    valid &= segment_array[candidate_position, column] == planned_entry_segments[family]
            if valid:
                execution_position = candidate_position
                break
        if execution_position is None:
            status = "CANCELLED_PANEL_END_NO_EXECUTION_SESSION" if review_position + 1 >= len(calendar) else "CANCELLED_NO_COMMON_VALID_ENDPOINT_WITHIN_3_XLON_SESSIONS"
            cancelled_events.append(
                {
                    "review_date": review_date,
                    "execution_date": pd.NaT,
                    "execution_lag_xlon_sessions": np.nan,
                    "same_close_execution": False,
                    "execution_status": status,
                    "selected_families": ";".join(sorted(target)),
                    "selected_count": len(target),
                    "traded_notional_fraction": np.nan,
                    "trade_legs": 0,
                    "fx_traded_notional_fraction": np.nan,
                    "transaction_cost_rate": 0.0,
                    "transaction_cost_value": 0.0,
                    "pre_trade_portfolio_value": np.nan,
                    "fixed_cost_value": 0.0,
                }
            )
            continue
        planned_events.append(
            {
                "review_date": review_date,
                "execution_position": int(execution_position),
                "execution_date": pd.Timestamp(calendar[execution_position]),
                "lag": int(execution_position - review_position),
                "target": target,
            }
        )
        planned_members = set(target)
        if segment_array is not None:
            planned_entry_segments = {
                family: segment_array[execution_position, column_position[family]] for family in target
            }
        started = True

    if not planned_events:
        curve = pd.DataFrame(columns=["date", "portfolio_value", "invested_fraction", "cash_fraction", "holding_count", "concentration_hhi", "holdings", "decision_review_date"])
        trades = pd.DataFrame(cancelled_events, columns=["review_date", "execution_date", "execution_lag_xlon_sessions", "same_close_execution", "execution_status", "selected_families", "selected_count", "traded_notional_fraction", "trade_legs", "fx_traded_notional_fraction", "transaction_cost_rate", "transaction_cost_value", "pre_trade_portfolio_value", "fixed_cost_value"])
        target_rows = [{"review_date": date, "target_members": ";".join(sorted(target)), "target_count": len(target), "target_weight_sum": float(sum(target.values()))} for date, target in review_targets.items()]
        return SimulationResult(curve, trades, pd.DataFrame(target_rows))

    portfolio_value = np.full(len(calendar), np.nan)
    invested_fraction = np.full(len(calendar), np.nan)
    cash_fraction = np.full(len(calendar), np.nan)
    holding_count = np.full(len(calendar), np.nan)
    concentration_hhi = np.full(len(calendar), np.nan)
    holdings_text = np.full(len(calendar), None, dtype=object)
    decision_review = np.full(len(calendar), np.datetime64("NaT"), dtype="datetime64[ns]")
    units: dict[str, float] = {}
    entry_segments: dict[str, Any] = {}
    cash = 1.0
    trade_rows: list[dict[str, Any]] = []

    for event_index, event in enumerate(planned_events):
        position = event["execution_position"]
        target = event["target"]
        if units:
            current_component = {
                family: quantity * wealth_array[position, column_position[family]] for family, quantity in units.items()
            }
            pre_value = float(cash + sum(current_component.values()))
        else:
            current_component = {}
            pre_value = float(cash)
        if not np.isfinite(pre_value) or pre_value <= 0:
            raise AssertionError("Execution cannot bridge an invalid continuity segment")
        current_weights = {family: value / pre_value for family, value in current_component.items()}
        families = sorted(set(current_weights) | set(target))
        deltas = {family: float(target.get(family, 0.0) - current_weights.get(family, 0.0)) for family in families}
        traded_notional = float(sum(abs(value) for value in deltas.values()))
        trade_legs = int(sum(abs(value) > 1e-12 for value in deltas.values()))
        fx_notional = float(sum(abs(value) for family, value in deltas.items() if family in non_gbp))
        variable_cost_rate = traded_notional * float(friction_bps) / 10_000.0 + fx_notional * float(fx_rate)
        fixed_cost_value = trade_legs * float(fixed_fee_gbp) / float(sleeve_size_gbp)
        cost_amount = min(pre_value * variable_cost_rate + fixed_cost_value, pre_value)
        post_value = pre_value - cost_amount
        cost_rate = cost_amount / pre_value
        cash = post_value * max(0.0, 1.0 - float(sum(target.values())))
        units = {
            family: post_value * float(weight) / wealth_array[position, column_position[family]]
            for family, weight in target.items()
        }
        entry_segments = {
            family: segment_array[position, column_position[family]] if segment_array is not None else None for family in target
        }
        trade_rows.append(
            {
                "review_date": event["review_date"],
                "execution_date": event["execution_date"],
                "execution_lag_xlon_sessions": event["lag"],
                "same_close_execution": False,
                "execution_status": "EXECUTED",
                "selected_families": ";".join(sorted(target)),
                "selected_count": len(target),
                "traded_notional_fraction": traded_notional,
                "trade_legs": trade_legs,
                "fx_traded_notional_fraction": fx_notional,
                "transaction_cost_rate": cost_rate,
                "transaction_cost_value": cost_amount,
                "pre_trade_portfolio_value": pre_value,
                "fixed_cost_value": fixed_cost_value,
            }
        )
        end_position = planned_events[event_index + 1]["execution_position"] if event_index + 1 < len(planned_events) else len(calendar) - 1
        row_slice = slice(position, end_position + 1)
        if units:
            family_names = list(units)
            columns = [column_position[family] for family in family_names]
            quantities = np.asarray([units[family] for family in family_names], dtype=float)
            block = wealth_array[row_slice, :][:, columns]
            valid_rows = np.isfinite(block).all(axis=1)
            if segment_array is not None:
                segment_block = segment_array[row_slice, :][:, columns]
                expected = np.asarray([entry_segments[family] for family in family_names], dtype=object)
                valid_rows &= (segment_block == expected[None, :]).all(axis=1)
            components = block * quantities[None, :]
            values = cash + np.nansum(components, axis=1)
            values[~valid_rows] = np.nan
            invested = np.nansum(components, axis=1)
            invested[~valid_rows] = np.nan
            hhi = np.nansum(np.square(components / values[:, None]), axis=1)
            hhi[~valid_rows] = np.nan
        else:
            length = end_position - position + 1
            values = np.full(length, cash)
            invested = np.zeros(length)
            hhi = np.zeros(length)
            valid_rows = np.ones(length, dtype=bool)
        values[0] = post_value
        portfolio_value[row_slice] = values
        invested_fraction[row_slice] = invested / values
        cash_fraction[row_slice] = cash / values
        holding_count[row_slice] = len(units)
        concentration_hhi[row_slice] = hhi
        holdings_text[row_slice] = ";".join(sorted(units))
        decision_review[row_slice] = np.datetime64(event["review_date"])

    observed = np.isfinite(portfolio_value)
    curve = pd.DataFrame(
        {
            "date": calendar[observed],
            "portfolio_value": portfolio_value[observed],
            "invested_fraction": invested_fraction[observed],
            "cash_fraction": cash_fraction[observed],
            "holding_count": holding_count[observed].astype(int),
            "concentration_hhi": concentration_hhi[observed],
            "holdings": holdings_text[observed],
            "decision_review_date": pd.to_datetime(decision_review[observed]),
        }
    )
    trades = pd.DataFrame(trade_rows + cancelled_events, columns=["review_date", "execution_date", "execution_lag_xlon_sessions", "same_close_execution", "execution_status", "selected_families", "selected_count", "traded_notional_fraction", "trade_legs", "fx_traded_notional_fraction", "transaction_cost_rate", "transaction_cost_value", "pre_trade_portfolio_value", "fixed_cost_value"]).sort_values(["review_date", "execution_date"], na_position="last").reset_index(drop=True)
    target_rows = []
    for date, target in review_targets.items():
        target_rows.append({"review_date": date, "target_members": ";".join(sorted(target)), "target_count": len(target), "target_weight_sum": float(sum(target.values()))})
    return SimulationResult(curve, trades, pd.DataFrame(target_rows))


def simulate_equal_weight_benchmark(
    targets: dict[pd.Timestamp, dict[str, float]],
    *,
    calendar: pd.DatetimeIndex,
    daily_returns: pd.DataFrame,
) -> SimulationResult:
    """Contemporaneous-valid equal-weight research index.

    Membership decided after review date T becomes effective after the next
    XLON close, so it first earns the following session's return. Within a
    membership set, an invalid constituent-day is excluded rather than filled;
    valid constituents are equally weighted for that date. This comparator is
    a research index, not a claim of frictionless implementation.
    """
    positions = {pd.Timestamp(date): index for index, date in enumerate(calendar)}
    members: set[str] = set()
    started = False
    value = 1.0
    changes: dict[int, tuple[pd.Timestamp, set[str]]] = {}
    target_rows = []
    prior_target: set[str] = set()
    for review_date, target in sorted(targets.items()):
        review_date = pd.Timestamp(review_date)
        target_members = set(target)
        target_rows.append({"review_date": review_date, "target_members": ";".join(sorted(target_members)), "target_count": len(target_members), "target_weight_sum": 1.0 if target_members else 0.0})
        if review_date not in positions or target_members == prior_target:
            continue
        execution_position = positions[review_date] + 1
        if execution_position >= len(calendar):
            continue
        changes[execution_position] = (review_date, target_members)
        prior_target = target_members

    rows = []
    trade_rows = []
    active_review = pd.NaT
    return_array = daily_returns.reindex(calendar).to_numpy(float)
    column_position = {name: index for index, name in enumerate(daily_returns.columns)}
    for position, date in enumerate(calendar):
        if started:
            if members:
                values = return_array[position, [column_position[family] for family in sorted(members)]]
                valid = values[np.isfinite(values)]
                if len(valid):
                    value *= 1.0 + float(valid.mean())
                    rows.append({"date": pd.Timestamp(date), "portfolio_value": value, "invested_fraction": 1.0, "cash_fraction": 0.0, "holding_count": len(members), "concentration_hhi": 1.0 / len(valid), "holdings": ";".join(sorted(members)), "decision_review_date": active_review})
            else:
                rows.append({"date": pd.Timestamp(date), "portfolio_value": value, "invested_fraction": 0.0, "cash_fraction": 1.0, "holding_count": 0, "concentration_hhi": 0.0, "holdings": "", "decision_review_date": active_review})
        if position in changes:
            review_date, new_members = changes[position]
            members = new_members
            active_review = review_date
            if not started:
                started = True
                rows.append({"date": pd.Timestamp(date), "portfolio_value": value, "invested_fraction": 1.0 if members else 0.0, "cash_fraction": 0.0 if members else 1.0, "holding_count": len(members), "concentration_hhi": 1.0 / len(members) if members else 0.0, "holdings": ";".join(sorted(members)), "decision_review_date": active_review})
            trade_rows.append({"review_date": review_date, "execution_date": pd.Timestamp(date), "execution_lag_xlon_sessions": 1, "same_close_execution": False, "execution_status": "RESEARCH_INDEX_MEMBERSHIP_CHANGE", "selected_families": ";".join(sorted(members)), "selected_count": len(members), "traded_notional_fraction": np.nan, "trade_legs": 0, "fx_traded_notional_fraction": 0.0, "transaction_cost_rate": 0.0, "transaction_cost_value": 0.0, "pre_trade_portfolio_value": value, "fixed_cost_value": 0.0})
    curve = pd.DataFrame(rows).drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True) if rows else pd.DataFrame(columns=["date", "portfolio_value", "invested_fraction", "cash_fraction", "holding_count", "concentration_hhi", "holdings", "decision_review_date"])
    trades = pd.DataFrame(trade_rows, columns=["review_date", "execution_date", "execution_lag_xlon_sessions", "same_close_execution", "execution_status", "selected_families", "selected_count", "traded_notional_fraction", "trade_legs", "fx_traded_notional_fraction", "transaction_cost_rate", "transaction_cost_value", "pre_trade_portfolio_value", "fixed_cost_value"])
    return SimulationResult(curve, trades, pd.DataFrame(target_rows))


def performance_metrics(
    simulation: SimulationResult,
    *,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    calendar: pd.DatetimeIndex,
) -> dict[str, Any]:
    curve = simulation.curve.copy()
    if curve.empty:
        return _empty_metrics()
    if start is not None:
        curve = curve.loc[curve["date"].ge(pd.Timestamp(start))]
    if end is not None:
        curve = curve.loc[curve["date"].le(pd.Timestamp(end))]
    curve = curve.drop_duplicates("date").sort_values("date")
    if len(curve) < 2:
        return _empty_metrics()
    value = curve.set_index("date")["portfolio_value"].astype(float)
    returns = value.pct_change(fill_method=None).dropna()
    years = max((value.index[-1] - value.index[0]).days / 365.2425, 1.0 / 365.2425)
    cagr = float((value.iloc[-1] / value.iloc[0]) ** (1.0 / years) - 1.0)
    date_positions = pd.Series(np.arange(len(calendar)), index=calendar)
    spans = date_positions.reindex(value.index).diff().dropna().astype(float)
    mean_span = float(spans.mean()) if len(spans) else 1.0
    annualised_vol = float(returns.std(ddof=1) * math.sqrt(252.0 / max(mean_span, 1e-12))) if len(returns) > 1 else np.nan
    downside = returns.loc[returns < 0]
    downside_vol = float(downside.std(ddof=1) * math.sqrt(252.0 / max(mean_span, 1e-12))) if len(downside) > 1 else np.nan
    normalised = value / value.iloc[0]
    drawdown = normalised / normalised.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    ulcer = float(np.sqrt(np.mean(np.square(drawdown))))
    month_end = value.groupby([value.index.year, value.index.month]).last()
    month_returns = month_end.pct_change(fill_method=None).dropna()
    rolling3 = (1.0 + month_returns).rolling(3, min_periods=3).apply(np.prod, raw=True) - 1.0
    trades = simulation.trades.loc[simulation.trades["execution_status"].eq("EXECUTED")].copy()
    if start is not None:
        trades = trades.loc[pd.to_datetime(trades["execution_date"]).ge(pd.Timestamp(start))]
    if end is not None:
        trades = trades.loc[pd.to_datetime(trades["execution_date"]).le(pd.Timestamp(end))]
    underwater_start = None
    max_recovery_days = 0
    for date, dd in drawdown.items():
        if dd < -1e-12 and underwater_start is None:
            underwater_start = date
        elif dd >= -1e-12 and underwater_start is not None:
            max_recovery_days = max(max_recovery_days, (date - underwater_start).days)
            underwater_start = None
    if underwater_start is not None:
        max_recovery_days = max(max_recovery_days, (drawdown.index[-1] - underwater_start).days)
    holding_changes = trades.loc[trades["traded_notional_fraction"].fillna(0).gt(1e-12), "execution_date"]
    holding_period = pd.to_datetime(holding_changes).sort_values().diff().dt.days.dropna()
    return {
        "first_observation_date": value.index[0],
        "last_observation_date": value.index[-1],
        "observation_count": len(value),
        "calendar_years": years,
        "cagr": cagr,
        "annualised_return": cagr,
        "annualised_volatility": annualised_vol,
        "sharpe_zero_cash_hurdle": cagr / annualised_vol if annualised_vol and annualised_vol > 0 else np.nan,
        "sortino_zero_cash_hurdle": cagr / downside_vol if downside_vol and downside_vol > 0 else np.nan,
        "maximum_drawdown": max_drawdown,
        "calmar": cagr / abs(max_drawdown) if max_drawdown < 0 else np.nan,
        "ulcer_index": ulcer,
        "worst_month": float(month_returns.min()) if len(month_returns) else np.nan,
        "worst_rolling_three_months": float(rolling3.min()) if len(rolling3.dropna()) else np.nan,
        "maximum_recovery_duration_calendar_days": int(max_recovery_days),
        "annual_turnover_traded_notional": float(trades["traded_notional_fraction"].fillna(0).sum() / years),
        "executed_rebalances": int(len(trades)),
        "trade_legs": int(trades["trade_legs"].fillna(0).sum()),
        "average_holding_period_calendar_days": float(holding_period.mean()) if len(holding_period) else np.nan,
        "percentage_invested": float(curve["invested_fraction"].mean()),
        "average_holding_count": float(curve["holding_count"].mean()),
        "average_concentration_hhi": float(curve["concentration_hhi"].mean()),
        "total_transaction_cost_rate": float(trades["transaction_cost_rate"].fillna(0).sum()),
        "cancelled_rebalances": int(simulation.trades["execution_status"].str.startswith("CANCELLED", na=False).sum()),
        "mean_observation_span_xlon_sessions": mean_span,
    }


def _empty_metrics() -> dict[str, Any]:
    names = [
        "first_observation_date", "last_observation_date", "observation_count", "calendar_years", "cagr", "annualised_return",
        "annualised_volatility", "sharpe_zero_cash_hurdle", "sortino_zero_cash_hurdle", "maximum_drawdown", "calmar",
        "ulcer_index", "worst_month", "worst_rolling_three_months", "maximum_recovery_duration_calendar_days",
        "annual_turnover_traded_notional", "executed_rebalances", "trade_legs", "average_holding_period_calendar_days",
        "percentage_invested", "average_holding_count", "average_concentration_hhi", "total_transaction_cost_rate",
        "cancelled_rebalances", "mean_observation_span_xlon_sessions",
    ]
    result = {name: np.nan for name in names}
    result["observation_count"] = 0
    result["executed_rebalances"] = 0
    result["trade_legs"] = 0
    result["cancelled_rebalances"] = 0
    return result


def aligned_excess_returns(left: SimulationResult, right: SimulationResult) -> pd.Series:
    if left.curve.empty or right.curve.empty:
        return pd.Series(dtype=float)
    joined = left.curve.set_index("date")[["portfolio_value"]].rename(columns={"portfolio_value": "left"}).join(
        right.curve.set_index("date")[["portfolio_value"]].rename(columns={"portfolio_value": "right"}), how="inner"
    )
    returns = joined.pct_change(fill_method=None).dropna()
    return returns["left"] - returns["right"]


def review_interval_returns(simulation: SimulationResult, review_dates: Iterable[pd.Timestamp]) -> pd.DataFrame:
    """Observed portfolio returns between review dates, with no valuation fill.

    A review receives the latest genuinely observed portfolio value at or before
    that close. The following interval return is assigned to the earlier review.
    """
    if simulation.curve.empty:
        return pd.DataFrame(columns=["review_date", "next_review_date", "interval_return"])
    reviews = pd.DataFrame({"review_date": sorted(pd.DatetimeIndex(review_dates).unique())})
    values = simulation.curve[["date", "portfolio_value"]].dropna().sort_values("date")
    aligned = pd.merge_asof(reviews, values, left_on="review_date", right_on="date", direction="backward")
    aligned["next_review_date"] = aligned["review_date"].shift(-1)
    aligned["interval_return"] = aligned["portfolio_value"].shift(-1) / aligned["portfolio_value"] - 1.0
    return aligned[["review_date", "next_review_date", "interval_return"]].dropna(subset=["interval_return"])
