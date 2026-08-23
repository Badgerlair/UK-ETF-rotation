"""Run A4C0-A4C2: baseline, drawdown forensics and early rotation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import ukactive_a4c_core as core


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]


def _write(frame: pd.DataFrame, name: str) -> None:
    frame.to_csv(PROGRAMME_ROOT / name, index=False, date_format="%Y-%m-%d")


def _curve_family(curve_row: pd.Series) -> str:
    try:
        weights = json.loads(str(curve_row.get("weights_json", "{}")))
    except json.JSONDecodeError:
        weights = {}
    return max(weights, key=weights.get) if weights else ""


def _asof_family(features: pd.DataFrame, family: str, date: pd.Timestamp) -> pd.Series:
    rows = features.loc[(features["economic_exposure_family_id"].eq(family)) & (features["date"].le(pd.Timestamp(date)))]
    return rows.iloc[-1] if len(rows) else pd.Series(dtype=object)


def _entry_exit_dates(sim: Any, family: str, peak: pd.Timestamp) -> tuple[pd.Timestamp | pd.NaT, pd.Timestamp | pd.NaT]:
    executed = sim.trades.loc[sim.trades["execution_status"].eq("EXECUTED")].copy()
    executed["execution_date"] = pd.to_datetime(executed["execution_date"])
    target_members = executed["target_weights_json"].map(lambda value: set(json.loads(value)))
    prior_members: set[str] = set()
    entries: list[pd.Timestamp] = []
    exits: list[pd.Timestamp] = []
    for (_, row), members in zip(executed.iterrows(), target_members):
        date = pd.Timestamp(row["execution_date"])
        if family in members and family not in prior_members:
            entries.append(date)
        if family not in members and family in prior_members:
            exits.append(date)
        prior_members = members
    entry = max((value for value in entries if value <= peak), default=pd.NaT)
    exit_date = min((value for value in exits if value > peak), default=pd.NaT)
    return entry, exit_date


def _drawdown_episodes(curve: pd.DataFrame) -> list[dict[str, Any]]:
    source = curve.loc[curve["date"].between(core.LATEST5_START, core.CUTOFF)].drop_duplicates("date").sort_values("date").reset_index(drop=True)
    value = source["portfolio_value"].astype(float)
    running_peak = value.cummax()
    drawdown = value / running_peak - 1.0
    episodes: list[dict[str, Any]] = []
    in_episode = False
    start_index = 0
    for index, dd in enumerate(drawdown):
        if dd < -1e-12 and not in_episode:
            in_episode = True
            start_index = index
        recovered = in_episode and dd >= -1e-12
        is_last = in_episode and index == len(source) - 1
        if recovered or is_last:
            end_index = index if recovered else len(source) - 1
            underwater = drawdown.iloc[start_index:end_index + 1]
            trough_index = int(underwater.idxmin())
            depth = float(drawdown.iloc[trough_index])
            peak_index = max(0, start_index - 1)
            if depth <= -0.05:
                onset_candidates = np.flatnonzero(drawdown.iloc[peak_index:end_index + 1].to_numpy() <= -0.05)
                onset_index = peak_index + int(onset_candidates[0]) if len(onset_candidates) else trough_index
                episodes.append({
                    "peak_index": peak_index,
                    "onset_index": onset_index,
                    "trough_index": trough_index,
                    "recovery_index": end_index if recovered else None,
                    "peak_date": pd.Timestamp(source.iloc[peak_index]["date"]),
                    "major_drawdown_onset_date": pd.Timestamp(source.iloc[onset_index]["date"]),
                    "trough_date": pd.Timestamp(source.iloc[trough_index]["date"]),
                    "recovery_date": pd.Timestamp(source.iloc[end_index]["date"]) if recovered else pd.NaT,
                    "maximum_drawdown": depth,
                    "peak_value": float(value.iloc[peak_index]),
                    "trough_value": float(value.iloc[trough_index]),
                    "recovered_by_cutoff": recovered,
                    "source": source,
                })
            in_episode = False
    return episodes


def build_drawdown_forensics(data: core.A4CData, baseline: Any) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    episodes = _drawdown_episodes(baseline.curve)
    calendar_position = {pd.Timestamp(date): index for index, date in enumerate(data.base.research.calendar)}
    warning_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    cause_rows: list[dict[str, Any]] = []
    global_wealth = data.base.research.wealth["GLOBAL_DEVELOPED_WORLD"]
    warning_specs = {
        "FAST_RS_DETERIORATION": lambda frame: frame["FAST_RS_CHANGE_4W"].lt(0),
        "LOSS_POSITIVE_RS21": lambda frame: frame["RS_21"].le(0),
        "LOSS_POSITIVE_RS42": lambda frame: frame["RS_42"].le(0),
        "RELATIVE_SLOPE_42_NEGATIVE": lambda frame: frame["RELATIVE_SLOPE_42"].lt(0),
        "CLOSE_BELOW_EMA21": lambda frame: frame["ABS_BELOW_EMA21"].fillna(False),
        "CLOSE_BELOW_EMA50": lambda frame: frame["ABS_BELOW_EMA50"].fillna(False),
        "CLOSE_BELOW_EMA200": lambda frame: frame["ABS_BELOW_EMA200"].fillna(False),
        "VOLATILITY_EXPANSION_1_5X": lambda frame: frame["VOL_EXPANSION_RATIO"].ge(1.5),
        "SLOW_RANK_LOSS_FROM_1": lambda frame: frame["SLOW_ORDINAL_RANK"].gt(1),
        "SLOW_RANK_OUTSIDE_TOP3": lambda frame: frame["SLOW_ORDINAL_RANK"].gt(3),
        "SLOW_RANK_OUTSIDE_TOP5": lambda frame: frame["SLOW_ORDINAL_RANK"].gt(5),
    }

    max_depth = min((row["maximum_drawdown"] for row in episodes), default=np.nan)
    for number, episode in enumerate(episodes, start=1):
        source = episode.pop("source")
        peak_row = source.iloc[episode["peak_index"]]
        family = _curve_family(peak_row)
        entry_date, actual_exit = _entry_exit_dates(baseline, family, episode["peak_date"])
        end_search = actual_exit if pd.notna(actual_exit) else core.CUTOFF
        family_weekly = data.weekly_features.loc[
            data.weekly_features["economic_exposure_family_id"].eq(family)
            & data.weekly_features["date"].between(entry_date if pd.notna(entry_date) else episode["peak_date"] - pd.Timedelta(days=365), end_search)
        ].sort_values("date")
        first_warning_dates: dict[str, pd.Timestamp | pd.NaT] = {}
        for warning_id, condition in warning_specs.items():
            matching = family_weekly.loc[condition(family_weekly)]
            first_date = pd.Timestamp(matching.iloc[0]["date"]) if len(matching) else pd.NaT
            first_warning_dates[warning_id] = first_date
            def _lead(reference: pd.Timestamp | pd.NaT) -> tuple[float, float]:
                if pd.isna(first_date) or pd.isna(reference):
                    return np.nan, np.nan
                calendar_lead = (pd.Timestamp(reference) - pd.Timestamp(first_date)).days
                session_lead = calendar_position.get(pd.Timestamp(reference), np.nan) - calendar_position.get(pd.Timestamp(first_date), np.nan)
                return float(calendar_lead), float(session_lead)
            peak_days, peak_sessions = _lead(episode["peak_date"])
            onset_days, onset_sessions = _lead(episode["major_drawdown_onset_date"])
            exit_days, exit_sessions = _lead(actual_exit)
            warning_rows.append({
                "drawdown_episode_id": f"DD_{number:02d}", "economic_exposure_family_id": family, "warning_signal": warning_id,
                "first_warning_date": first_date, "portfolio_peak_date": episode["peak_date"], "major_drawdown_onset_date": episode["major_drawdown_onset_date"],
                "actual_exit_date": actual_exit, "warning_lead_calendar_days_to_peak": peak_days, "warning_lead_xlon_sessions_to_peak": peak_sessions,
                "warning_lead_calendar_days_to_drawdown_onset": onset_days, "warning_lead_xlon_sessions_to_drawdown_onset": onset_sessions,
                "warning_lead_calendar_days_to_actual_exit": exit_days, "warning_lead_xlon_sessions_to_actual_exit": exit_sessions,
                "warning_available_before_drawdown_onset": bool(pd.notna(first_date) and first_date <= episode["major_drawdown_onset_date"]), "warning": core.WARNING,
            })

        peak_feature = _asof_family(data.weekly_features, family, episode["peak_date"])
        trough_feature = _asof_family(data.weekly_features, family, episode["trough_date"])
        if pd.notna(entry_date):
            values = data.base.research.wealth.loc[entry_date:episode["peak_date"], family].dropna()
            entry_level = float(data.base.research.wealth.loc[entry_date, family]) if pd.notna(data.base.research.wealth.loc[entry_date, family]) else np.nan
            prior_mfe = float(values.max() / entry_level - 1.0) if len(values) and pd.notna(entry_level) else np.nan
            sessions_since_entry = calendar_position.get(episode["peak_date"], 0) - calendar_position.get(pd.Timestamp(entry_date), 0)
        else:
            prior_mfe, sessions_since_entry = np.nan, np.nan
        global_peak = float(global_wealth.loc[episode["peak_date"]])
        global_trough = float(global_wealth.loc[episode["trough_date"]])
        global_dd = global_trough / global_peak - 1.0
        earliest_warning = min((value for key, value in first_warning_dates.items() if key in {"FAST_RS_DETERIORATION", "RELATIVE_SLOPE_42_NEGATIVE", "CLOSE_BELOW_EMA50", "VOLATILITY_EXPANSION_1_5X", "SLOW_RANK_LOSS_FROM_1"} and pd.notna(value)), default=pd.NaT)
        if pd.notna(earliest_warning):
            warning_curve = source.loc[source["date"].ge(earliest_warning)].iloc[0]
            loss_after_warning = float(episode["trough_value"] / float(warning_curve["portfolio_value"]) - 1.0)
            warning_to_exit_sessions = calendar_position.get(pd.Timestamp(actual_exit), np.nan) - calendar_position.get(pd.Timestamp(earliest_warning), np.nan) if pd.notna(actual_exit) else np.nan
        else:
            loss_after_warning, warning_to_exit_sessions = np.nan, np.nan

        flags = {
            "MARKET_WIDE_SHOCK": global_dd <= -0.05,
            "RIGHT_TAIL_GIVEBACK": pd.notna(prior_mfe) and prior_mfe >= 0.20 and episode["maximum_drawdown"] <= -0.10,
            "LATE_MONTHLY_EXIT": pd.notna(warning_to_exit_sessions) and warning_to_exit_sessions >= 10 and pd.notna(loss_after_warning) and loss_after_warning <= -0.03,
            "ABSOLUTE_TREND_FAILURE": pd.notna(first_warning_dates["CLOSE_BELOW_EMA50"]) and first_warning_dates["CLOSE_BELOW_EMA50"] <= episode["trough_date"],
            "LEADERSHIP_REVERSAL": any(pd.notna(first_warning_dates[key]) and first_warning_dates[key] <= episode["trough_date"] for key in ["FAST_RS_DETERIORATION", "RELATIVE_SLOPE_42_NEGATIVE", "SLOW_RANK_LOSS_FROM_1"]),
            "VOLATILITY_EXPANSION": pd.notna(first_warning_dates["VOLATILITY_EXPANSION_1_5X"]) and first_warning_dates["VOLATILITY_EXPANSION_1_5X"] <= episode["trough_date"],
            "WRONG_LEADER_SELECTION": pd.notna(prior_mfe) and prior_mfe <= 0.03 and pd.notna(sessions_since_entry) and sessions_since_entry <= 21,
        }
        if flags["MARKET_WIDE_SHOCK"] and abs(global_dd) >= 0.60 * abs(episode["maximum_drawdown"]):
            primary = "MARKET_WIDE_SHOCK"
        elif flags["RIGHT_TAIL_GIVEBACK"]:
            primary = "RIGHT_TAIL_GIVEBACK"
        elif flags["ABSOLUTE_TREND_FAILURE"]:
            primary = "ABSOLUTE_TREND_FAILURE"
        elif flags["LEADERSHIP_REVERSAL"]:
            primary = "LEADERSHIP_REVERSAL"
        elif flags["VOLATILITY_EXPANSION"]:
            primary = "VOLATILITY_EXPANSION"
        elif flags["LATE_MONTHLY_EXIT"]:
            primary = "LATE_MONTHLY_EXIT"
        elif flags["WRONG_LEADER_SELECTION"]:
            primary = "WRONG_LEADER_SELECTION"
        else:
            primary = "MULTIPLE_CAUSES"
        contributing = ";".join(key for key, value in flags.items() if value) or "UNRESOLVED"
        family_sequence = ";".join(sorted({value for value in source.loc[source["date"].between(episode["peak_date"], episode["trough_date"]), "holdings"] if value}))
        challenger_at_peak = data.weekly_features.loc[
            data.weekly_features["date"].eq(peak_feature.get("date", pd.NaT))
            & data.weekly_features["FAST_CROSSOVER_PRIMARY"].fillna(False)
            & data.weekly_features["economic_exposure_family_id"].ne(family), "economic_exposure_family_id"
        ].sort_values().tolist()
        episode_id = f"DD_{number:02d}"
        row = {
            "drawdown_episode_id": episode_id, "portfolio_peak_date": episode["peak_date"], "major_drawdown_onset_date": episode["major_drawdown_onset_date"],
            "trough_date": episode["trough_date"], "recovery_date": episode["recovery_date"], "recovered_by_cutoff": episode["recovered_by_cutoff"],
            "maximum_drawdown": episode["maximum_drawdown"], "reached_minus_5pct": True, "reached_minus_10pct": episode["maximum_drawdown"] <= -0.10,
            "reached_minus_15pct": episode["maximum_drawdown"] <= -0.15, "is_maximum_drawdown_episode": abs(episode["maximum_drawdown"] - max_depth) <= 1e-12,
            "primary_family_at_peak": family, "family_sequence_peak_to_trough": family_sequence, "holding_entry_date": entry_date, "actual_exit_date": actual_exit,
            "fast_rank_at_peak": peak_feature.get("FAST_ORDINAL_RANK", np.nan), "slow_rank_at_peak": peak_feature.get("SLOW_ORDINAL_RANK", np.nan),
            "rs21_at_peak": peak_feature.get("RS_21", np.nan), "rs42_at_peak": peak_feature.get("RS_42", np.nan), "rs63_at_peak": peak_feature.get("RS_63", np.nan),
            "rs126_at_peak": peak_feature.get("RS_126", np.nan), "rs252_at_peak": peak_feature.get("RS_252", np.nan),
            "relative_slope_42_at_peak": peak_feature.get("RELATIVE_SLOPE_42", np.nan), "absolute_distance_ema21_at_peak": peak_feature.get("ABS_DISTANCE_EMA_21", np.nan),
            "absolute_distance_ema50_at_peak": peak_feature.get("ABS_DISTANCE_EMA_50", np.nan), "absolute_distance_ema200_at_peak": peak_feature.get("ABS_DISTANCE_EMA_200", np.nan),
            "realised_vol_63_at_peak": peak_feature.get("REALISED_VOL_63", np.nan), "vol_expansion_ratio_at_peak": peak_feature.get("VOL_EXPANSION_RATIO", np.nan),
            "fast_rank_at_trough": trough_feature.get("FAST_ORDINAL_RANK", np.nan), "slow_rank_at_trough": trough_feature.get("SLOW_ORDINAL_RANK", np.nan),
            "prior_mfe_from_entry_to_peak": prior_mfe, "global_benchmark_peak_to_trough_return": global_dd,
            "loss_first_warning_to_trough": loss_after_warning, "challenger_existed_at_peak": bool(challenger_at_peak), "challengers_at_peak": ";".join(challenger_at_peak),
            "validated_open_gap_data_available": False, "gap_contribution_status": "NOT_DETERMINABLE_FROM_CLOSE_ONLY_PANEL",
            "primary_root_cause": primary, "contributing_causes": contributing, "warning": core.WARNING,
        }
        episode_rows.append(row)
        cause_rows.append({"drawdown_episode_id": episode_id, "primary_root_cause": primary, "contributing_causes": contributing, "drawdown_magnitude": abs(episode["maximum_drawdown"]), **{f"flag_{key.lower()}": value for key, value in flags.items()}, "warning": core.WARNING})

    episode_frame = pd.DataFrame(episode_rows)
    cause_detail = pd.DataFrame(cause_rows)
    if len(cause_detail):
        total_magnitude = cause_detail["drawdown_magnitude"].sum()
        summary = cause_detail.groupby("primary_root_cause", as_index=False).agg(material_drawdown_count=("drawdown_episode_id", "count"), aggregate_drawdown_magnitude=("drawdown_magnitude", "sum"))
        summary["percentage_of_material_drawdowns_by_count"] = summary["material_drawdown_count"] / len(cause_detail)
        summary["percentage_of_total_drawdown_magnitude"] = summary["aggregate_drawdown_magnitude"] / total_magnitude if total_magnitude else np.nan
        summary["record_type"] = "PRIMARY_CAUSE_SUMMARY"
        detail = cause_detail.copy()
        detail["record_type"] = "EPISODE_DETAIL"
        cause_frame = pd.concat([detail, summary], ignore_index=True, sort=False)
    else:
        cause_frame = cause_detail
    return episode_frame, cause_frame, pd.DataFrame(warning_rows)


def build_migration(data: core.A4CData) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    migration = data.weekly_features.copy().sort_values(["economic_exposure_family_id", "date"]).reset_index(drop=True)
    by_family = migration.groupby("economic_exposure_family_id", sort=False)
    for weeks in (4, 8):
        future_ranks = pd.concat([by_family["SLOW_ORDINAL_RANK"].shift(-offset) for offset in range(1, weeks + 1)], axis=1)
        migration[f"FUTURE_MIN_SLOW_RANK_{weeks}W"] = future_ranks.min(axis=1, skipna=True)
        for rank in (5, 3, 1):
            migration[f"BECOMES_SLOW_TOP{rank}_{weeks}W"] = migration[f"FUTURE_MIN_SLOW_RANK_{weeks}W"].le(rank)
    for horizon, weeks in ((21, 4), (42, 8)):
        matrix = data.base.research.matrices.forward_returns[horizon][data.base.members]
        part = core._long_matrix(matrix, pd.DatetimeIndex(migration["date"].unique()), data.base.members, f"FORWARD_RETURN_{weeks}W")
        migration = migration.merge(part, on=["date", "economic_exposure_family_id"], how="left", validate="one_to_one")
    migration["FAST_RANK_BAND"] = np.select(
        [migration["FAST_RS"].ge(0.95), migration["FAST_RS"].ge(0.90), migration["FAST_RS"].ge(0.80)],
        ["TOP_5PCT", "TOP_10PCT", "TOP_20PCT"], default="REMAINDER",
    )
    migration["FAST_CHANGE_BAND"] = np.select(
        [migration["FAST_RS_CHANGE_4W"].gt(0.20), migration["FAST_RS_CHANGE_4W"].ge(0.10), migration["FAST_RS_CHANGE_4W"].lt(0)],
        ["IMPROVING_GT20PT", "IMPROVING_10_TO_20PT", "DETERIORATING"], default="STABLE_0_TO_10PT",
    )
    migration["FAST_SLOW_GAP_BAND"] = np.select(
        [migration["FAST_MINUS_SLOW"].ge(0.15), migration["FAST_MINUS_SLOW"].le(-0.15)],
        ["FAST_SUBSTANTIALLY_AHEAD", "SLOW_SUBSTANTIALLY_AHEAD"], default="APPROXIMATELY_ALIGNED",
    )
    migration["SLOW_RANK1_ONSET"] = migration["SLOW_ORDINAL_RANK"].eq(1) & ~by_family["SLOW_ORDINAL_RANK"].shift(1).eq(1)
    migration["WARNING"] = core.WARNING

    trajectory_rows: list[dict[str, Any]] = []
    feature_columns = ["FAST_RS", "SLOW_RS", "FAST_MINUS_SLOW", "FAST_RS_CHANGE_1W", "FAST_RS_CHANGE_4W", "SLOW_RS_CHANGE_4W", "FAST_ORDINAL_RANK", "SLOW_ORDINAL_RANK", "RELATIVE_SLOPE_21", "RELATIVE_SLOPE_42", "RELATIVE_SLOPE_63", "RELATIVE_SLOPE_CHANGE", "POSITIVE_RECENT_RELATIVE_SEGMENTS", "REALISED_VOL_63"]
    event_number = 0
    for family, group in migration.groupby("economic_exposure_family_id", sort=False):
        group = group.sort_values("date").reset_index(drop=True)
        for target_index in np.flatnonzero(group["SLOW_RANK1_ONSET"].to_numpy()):
            if target_index < 12:
                continue
            event_number += 1
            target_date = pd.Timestamp(group.iloc[target_index]["date"])
            for offset in (12, 8, 6, 4, 3, 2, 1, 0):
                row = group.iloc[target_index - offset]
                base = {"leader_event_id": f"LEADER_{event_number:04d}", "target_slow_rank1_date": target_date, "weeks_before_slow_rank1": offset, "trajectory_cohort": "FUTURE_SLOW_RANK1", "economic_exposure_family_id": family, "observation_date": row["date"]}
                trajectory_rows.append({**base, **{column: row.get(column, np.nan) for column in feature_columns}, "warning": core.WARNING})
                controls = migration.loc[
                    migration["date"].eq(row["date"])
                    & migration["economic_exposure_family_id"].ne(family)
                    & ~migration["BECOMES_SLOW_TOP3_8W"].fillna(False)
                    & migration["FAST_RS"].notna()
                ]
                for control in controls.itertuples(index=False):
                    base_control = {"leader_event_id": f"LEADER_{event_number:04d}", "target_slow_rank1_date": target_date, "weeks_before_slow_rank1": offset, "trajectory_cohort": "NO_SLOW_TOP3_WITHIN_8W", "economic_exposure_family_id": control.economic_exposure_family_id, "observation_date": control.date}
                    trajectory_rows.append({**base_control, **{column: getattr(control, column, np.nan) for column in feature_columns}, "warning": core.WARNING})
    trajectories = pd.DataFrame(trajectory_rows)

    probability_rows: list[dict[str, Any]] = []
    valid = migration.loc[migration["FAST_RS"].notna()].copy()
    for dimension in ("FAST_RANK_BAND", "FAST_CHANGE_BAND", "FAST_SLOW_GAP_BAND"):
        for value, group in valid.groupby(dimension, sort=True):
            probability_rows.append(_conversion_row(dimension, str(value), group))
    for label, threshold in (("TOP_5_PERCENT", 0.95), ("TOP_10_PERCENT", 0.90), ("TOP_20_PERCENT", 0.80)):
        probability_rows.append(_conversion_row("FAST_RANK_CUMULATIVE", label, valid.loc[valid["FAST_RS"].ge(threshold)]))
    for keys, group in valid.groupby(["FAST_RANK_BAND", "FAST_CHANGE_BAND", "FAST_SLOW_GAP_BAND"], sort=True):
        probability_rows.append(_conversion_row("JOINT", "|".join(map(str, keys)), group))
    probabilities = pd.DataFrame(probability_rows)

    crossover_rows: list[dict[str, Any]] = []
    for variant in ("PRIMARY", "LOOSER", "TIGHTER"):
        selected = valid.loc[valid[f"FAST_CROSSOVER_{variant}"]]
        crossover_rows.append({"crossover_variant": variant, "observation_count": len(selected), "unique_family_count": selected["economic_exposure_family_id"].nunique(), **_conversion_stats(selected), "mean_forward_return_4w": selected["FORWARD_RETURN_4W"].mean(), "median_forward_return_4w": selected["FORWARD_RETURN_4W"].median(), "mean_forward_return_8w": selected["FORWARD_RETURN_8W"].mean(), "warning": core.WARNING})
    crossover = pd.DataFrame(crossover_rows)

    persistence_rows: list[dict[str, Any]] = []
    for weeks in (1, 2, 3):
        selected = valid.loc[valid["FAST_CROSSOVER_PERSISTENCE_PRIMARY"].ge(weeks)]
        persistence_rows.append({"persistence_weeks": weeks, "observation_count": len(selected), **_conversion_stats(selected), "false_positive_rate_not_slow_top3_8w": 1.0 - selected["BECOMES_SLOW_TOP3_8W"].mean() if len(selected) else np.nan, "average_return_before_slow_confirmation_proxy_4w": selected["FORWARD_RETURN_4W"].mean(), "warning": core.WARNING})
    persistence = pd.DataFrame(persistence_rows)
    return migration, trajectories, probabilities, crossover, persistence


def _conversion_stats(group: pd.DataFrame) -> dict[str, float]:
    return {f"probability_slow_top{rank}_{weeks}w": float(group[f"BECOMES_SLOW_TOP{rank}_{weeks}W"].mean()) if len(group) else np.nan for weeks in (4, 8) for rank in (5, 3, 1)}


def _conversion_row(dimension: str, value: str, group: pd.DataFrame) -> dict[str, Any]:
    return {"grouping_dimension": dimension, "grouping_value": value, "observation_count": len(group), "unique_family_count": group["economic_exposure_family_id"].nunique(), **_conversion_stats(group), "mean_forward_return_4w": group["FORWARD_RETURN_4W"].mean(), "mean_forward_return_8w": group["FORWARD_RETURN_8W"].mean(), "warning": core.WARNING}


def _episode_return(data: core.A4CData, family: str, start: pd.Timestamp, end: pd.Timestamp) -> float:
    values = data.base.research.wealth.loc[start:end, family].dropna()
    return float(values.iloc[-1] / values.iloc[0] - 1.0) if len(values) >= 2 else np.nan


def scout_episodes(plan: Any, simulation: Any, data: core.A4CData) -> pd.DataFrame:
    decisions = plan.decisions.sort_values("review_date").reset_index(drop=True)
    rows: list[dict[str, Any]] = []
    current = ""
    start_index = 0
    for index in range(len(decisions) + 1):
        challenger = str(decisions.iloc[index]["challenger"]) if index < len(decisions) else ""
        if challenger != current:
            if current:
                block = decisions.iloc[start_index:index]
                start_review = pd.Timestamp(block.iloc[0]["review_date"])
                end_review = pd.Timestamp(block.iloc[-1]["review_date"])
                start_exec_values = pd.to_datetime(block["execution_date"], errors="coerce").dropna()
                start_exec = pd.Timestamp(start_exec_values.iloc[0]) if len(start_exec_values) else start_review
                end_exec = pd.Timestamp(start_exec_values.iloc[-1]) if len(start_exec_values) else end_review
                inc = str(block.iloc[0]["monthly_incumbent"])
                feature = data.weekly_features.loc[(data.weekly_features["economic_exposure_family_id"].eq(current)) & (data.weekly_features["date"].between(start_review, end_review))].sort_values("date")
                def first_rank(max_rank: int) -> pd.Timestamp | pd.NaT:
                    match = feature.loc[feature["SLOW_ORDINAL_RANK"].le(max_rank)]
                    return pd.Timestamp(match.iloc[0]["date"]) if len(match) else pd.NaT
                top5, top3, rank1 = first_rank(5), first_rank(3), first_rank(1)
                candidate_return = _episode_return(data, current, start_exec, end_exec)
                incumbent_return = _episode_return(data, inc, start_exec, end_exec) if inc else np.nan
                average_weight = float(block["challenger_weight"].mean())
                before_confirm_end = rank1 if pd.notna(rank1) else end_exec
                before_confirm_return = _episode_return(data, current, start_exec, min(pd.Timestamp(before_confirm_end), end_exec))
                relevant_trades = simulation.trades.loc[pd.to_datetime(simulation.trades["execution_date"], errors="coerce").between(start_exec, end_exec)]
                incremental_cost = float(relevant_trades["transaction_cost_value"].fillna(0).sum())
                rows.append({
                    "module_id": plan.module_id, "scout_episode_id": f"{plan.module_id}_SCOUT_{len(rows)+1:03d}", "challenger_family": current, "incumbent_family": inc,
                    "entry_review_date": start_review, "entry_execution_date": start_exec, "episode_end_review_date": end_review, "episode_end_execution_date": end_exec,
                    "maximum_allocation": float(block["challenger_weight"].max()), "average_allocation": average_weight,
                    "slow_top5_date": top5, "slow_top3_date": top3, "slow_rank1_date": rank1, "converted_slow_top5": pd.notna(top5), "converted_slow_top3": pd.notna(top3), "converted_slow_rank1": pd.notna(rank1),
                    "false_start": pd.isna(top3), "candidate_episode_return": candidate_return, "incumbent_counterfactual_return": incumbent_return,
                    "weighted_return_captured_before_slow_rank1": average_weight * before_confirm_return if pd.notna(before_confirm_return) else np.nan,
                    "weighted_false_start_loss": -min(0.0, average_weight * candidate_return) if pd.isna(top3) and pd.notna(candidate_return) else 0.0,
                    "weighted_incumbent_return_sacrificed": average_weight * incumbent_return if pd.notna(incumbent_return) else np.nan,
                    "incremental_transaction_cost_value": incremental_cost,
                    "time_saved_xlon_sessions_to_slow_rank1": (data.base.research.calendar.get_loc(rank1) - data.base.research.calendar.get_loc(start_exec)) if pd.notna(rank1) and rank1 in data.base.research.calendar and start_exec in data.base.research.calendar else np.nan,
                    "warning": core.WARNING,
                })
            current = challenger
            start_index = index
    return pd.DataFrame(rows)


def _family_market_contribution(simulation: Any, family: str) -> float:
    curve = simulation.curve.loc[simulation.curve["date"].between(core.LATEST5_START, core.CUTOFF)]
    return float(sum(float(json.loads(value).get(family, 0.0)) for value in curve["family_market_pnl_json"]))


def run_early(data: core.A4CData, baseline: Any, comparators: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_metrics = core.metric_row(baseline, data, "A4_BASELINE", comparators=comparators)
    baseline_final = float(baseline.curve.loc[baseline.curve["date"].le(core.CUTOFF), "portfolio_value"].iloc[-1])
    result_rows: list[dict[str, Any]] = []
    episode_parts: list[pd.DataFrame] = []
    net_rows: list[dict[str, Any]] = []
    right_tail_rows: list[dict[str, Any]] = []
    top_families = ["GLOBAL_SILVER_MINERS", "EUROPE_BANKS", "GLOBAL_SEMICONDUCTORS"]
    baseline_contribution = {family: _family_market_contribution(baseline, family) for family in top_families}
    for architecture in ("EARLY_A", "EARLY_B", "EARLY_C"):
        for variant in ("PRIMARY", "LOOSER", "TIGHTER"):
            plan = core.build_early_plan(data, architecture, crossover_variant=variant)
            sim = core.simulate(plan, data)
            episodes = scout_episodes(plan, sim, data)
            episode_parts.append(episodes)
            metrics = core.metric_row(sim, data, plan.module_id, comparators=comparators)
            final_value = float(sim.curve.loc[sim.curve["date"].le(core.CUTOFF), "portfolio_value"].iloc[-1])
            metrics.update({
                "architecture": architecture, "crossover_variant": variant, "scout_episode_count": len(episodes),
                "false_start_rate": float(episodes["false_start"].mean()) if len(episodes) else np.nan,
                "slow_top3_conversion_rate": float(episodes["converted_slow_top3"].mean()) if len(episodes) else np.nan,
                "slow_rank1_conversion_rate": float(episodes["converted_slow_rank1"].mean()) if len(episodes) else np.nan,
                "terminal_wealth_relative_to_baseline": final_value / baseline_final - 1.0,
                "drawdown_change_vs_baseline": metrics["maximum_drawdown"] - baseline_metrics["maximum_drawdown"],
            })
            result_rows.append(metrics)
            captured = float(episodes["weighted_return_captured_before_slow_rank1"].fillna(0).clip(lower=0).sum()) if len(episodes) else 0.0
            false_losses = float(episodes["weighted_false_start_loss"].fillna(0).sum()) if len(episodes) else 0.0
            incumbent_sacrificed = float(episodes["weighted_incumbent_return_sacrificed"].fillna(0).sum()) if len(episodes) else 0.0
            extra_cost = max(0.0, float(sim.trades["transaction_cost_rate"].fillna(0).sum() - baseline.trades["transaction_cost_rate"].fillna(0).sum()))
            formula_value = captured - false_losses - incumbent_sacrificed - extra_cost
            exact_value = final_value / baseline_final - 1.0
            net_rows.append({
                "module_id": plan.module_id, "return_captured_before_slow_entry": captured, "false_start_losses": false_losses,
                "incumbent_return_sacrificed": incumbent_sacrificed, "incremental_costs": extra_cost,
                "component_formula_pre_path_reconciliation": formula_value, "net_early_participation_value": exact_value,
                "attribution_path_and_scale_reconciliation": exact_value - formula_value,
                "component_formula_units": "UNCOMPOUNDED_EPISODE_RETURN_EQUIVALENTS",
                "net_early_participation_value_units": "EXACT_TERMINAL_WEALTH_RELATIVE_TO_FROZEN_BASELINE",
                "promotion_net_value_positive": exact_value > 0,
                "warning": core.WARNING,
            })
            for family in top_families:
                contribution = _family_market_contribution(sim, family)
                right_tail_rows.append({"module_id": plan.module_id, "family": family, "module_market_pnl_contribution": contribution, "baseline_market_pnl_contribution": baseline_contribution[family], "additional_right_tail_contribution": contribution - baseline_contribution[family], "contribution_retention_ratio": contribution / baseline_contribution[family] if baseline_contribution[family] else np.nan, "warning": core.WARNING})
    results = pd.DataFrame(result_rows)
    # Promotion requires primary positive economics plus both neighbouring definitions not negative versus baseline.
    for architecture in results["architecture"].unique():
        subset = results.loc[results["architecture"].eq(architecture)]
        primary = subset.loc[subset["crossover_variant"].eq("PRIMARY")]
        robust = bool(len(primary) and primary.iloc[0]["terminal_wealth_relative_to_baseline"] > 0 and subset["terminal_wealth_relative_to_baseline"].gt(0).all())
        results.loc[results["architecture"].eq(architecture), "passes_neighbourhood_robustness"] = robust
    return results, pd.concat(episode_parts, ignore_index=True) if episode_parts else pd.DataFrame(), pd.DataFrame(net_rows), pd.DataFrame(right_tail_rows)


def write_drawdown_report(episodes: pd.DataFrame, causes: pd.DataFrame, warnings: pd.DataFrame) -> None:
    summaries = causes.loc[causes.get("record_type", pd.Series(dtype=str)).eq("PRIMARY_CAUSE_SUMMARY")]
    lines = [
        "# UKACTIVE-A4C drawdown forensic report", "", core.RESEARCH_WARNING, "",
        "Every final-five-year baseline underwater episode reaching -5% was reconstructed before exit or risk-rule testing. The analysis uses validated GBP total-return endpoints. No open-price panel passed the inherited validation contract, so a close-to-close jump is not relabelled as an executable opening gap; gap contribution remains `NOT_DETERMINABLE_FROM_CLOSE_ONLY_PANEL`.", "",
        f"Material episodes: {len(episodes)}. Episodes reaching -10%: {int(episodes['reached_minus_10pct'].sum()) if len(episodes) else 0}. Episodes reaching -15%: {int(episodes['reached_minus_15pct'].sum()) if len(episodes) else 0}.", "", "## Primary attribution", "",
    ]
    for row in summaries.itertuples(index=False):
        lines.append(f"- {row.primary_root_cause}: {int(row.material_drawdown_count)} episodes; {float(row.percentage_of_total_drawdown_magnitude):.1%} of aggregate episode depth.")
    if len(warnings):
        reliable = warnings.loc[warnings["warning_available_before_drawdown_onset"]].groupby("warning_signal").agg(coverage=("drawdown_episode_id", "nunique"), median_lead=("warning_lead_xlon_sessions_to_drawdown_onset", "median")).sort_values(["coverage", "median_lead"], ascending=[False, False])
        lines += ["", "## Warning clock", ""]
        for signal, row in reliable.head(5).iterrows():
            lines.append(f"- {signal}: available before onset in {int(row['coverage'])} episodes; median lead {float(row['median_lead']):.1f} XLON sessions.")
    lines += ["", "The classifications are causal diagnostics, not proof that a corresponding exit improves wealth. The preregistered exit modules are evaluated independently in A4C3."]
    (PROGRAMME_ROOT / "UKACTIVE_A4C_DRAWDOWN_FORENSIC_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = core.load_a4c_data()
    baseline_plan = core.build_baseline_plan(data)
    baseline = core.simulate(baseline_plan, data)
    reproduction = core.exact_baseline_reproduction(baseline)
    _write(reproduction, "UKACTIVE_A4C_BASELINE_REPRODUCTION.csv")
    if not reproduction["result"].eq("PASS").all():
        raise AssertionError("A4 baseline failed exact reproduction; A4C may not proceed")

    # Local ignored feature panel is a hash-addressed derivative used by later A4C work packages.
    data.daily_technical.to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4C_DAILY_TECHNICAL_FEATURES.parquet", index=False)

    episodes, causes, warnings = build_drawdown_forensics(data, baseline)
    _write(episodes, "UKACTIVE_A4C_DRAWDOWN_EPISODES.csv")
    _write(causes, "UKACTIVE_A4C_DRAWDOWN_ROOT_CAUSE.csv")
    _write(warnings, "UKACTIVE_A4C_WARNING_LEAD_TIMES.csv")
    write_drawdown_report(episodes, causes, warnings)

    migration, trajectories, probabilities, crossovers, persistence = build_migration(data)
    migration.to_parquet(PROGRAMME_ROOT / "UKACTIVE_A4C_FAST_TO_SLOW_MIGRATION.parquet", index=False)
    _write(trajectories, "UKACTIVE_A4C_PRE_LEADER_TRAJECTORIES.csv")
    _write(probabilities, "UKACTIVE_A4C_CONVERSION_PROBABILITIES.csv")
    _write(crossovers, "UKACTIVE_A4C_FAST_CROSSOVER_RESULTS.csv")
    _write(persistence, "UKACTIVE_A4C_FAST_PERSISTENCE_RESULTS.csv")

    comparators = core.comparator_curves(data)
    early, scouts, net_value, right_tail = run_early(data, baseline, comparators)
    _write(early, "UKACTIVE_A4C_EARLY_PARTICIPATION_RESULTS.csv")
    _write(scouts, "UKACTIVE_A4C_SCOUT_EPISODES.csv")
    _write(net_value, "UKACTIVE_A4C_NET_EARLY_PARTICIPATION_VALUE.csv")
    _write(right_tail, "UKACTIVE_A4C_EARLY_RIGHT_TAIL_CAPTURE.csv")


if __name__ == "__main__":
    main()
