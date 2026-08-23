from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

import numpy as np
import pandas as pd
from dateutil.easter import easter
from pandas.tseries.offsets import MonthEnd


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _first_monday(year: int, month: int) -> pd.Timestamp:
    date = pd.Timestamp(year, month, 1)
    return date + pd.Timedelta(days=(7 - date.weekday()) % 7)


def _last_monday(year: int, month: int) -> pd.Timestamp:
    date = pd.Timestamp(year, month, 1) + MonthEnd(0)
    return date - pd.Timedelta(days=date.weekday())


def england_wales_bank_holidays(year: int) -> dict[pd.Timestamp, str]:
    """Deterministic England/Wales holiday rules plus dated one-off closures."""
    holidays: dict[pd.Timestamp, str] = {}
    new_year = pd.Timestamp(year, 1, 1)
    new_year_observed = new_year if new_year.weekday() < 5 else new_year + pd.Timedelta(days=7 - new_year.weekday())
    holidays[new_year_observed] = "NEW_YEAR_BANK_HOLIDAY"

    easter_sunday = pd.Timestamp(easter(year))
    holidays[easter_sunday - pd.Timedelta(days=2)] = "GOOD_FRIDAY"
    holidays[easter_sunday + pd.Timedelta(days=1)] = "EASTER_MONDAY"
    if year == 2020:
        holidays[pd.Timestamp("2020-05-08")] = "EARLY_MAY_BANK_HOLIDAY_VE_DAY"
    else:
        holidays[_first_monday(year, 5)] = "EARLY_MAY_BANK_HOLIDAY"

    exceptional_spring = {
        2002: {
            pd.Timestamp("2002-06-03"): "SPRING_BANK_HOLIDAY_MOVED",
            pd.Timestamp("2002-06-04"): "GOLDEN_JUBILEE_BANK_HOLIDAY",
        },
        2012: {
            pd.Timestamp("2012-06-04"): "SPRING_BANK_HOLIDAY_MOVED",
            pd.Timestamp("2012-06-05"): "DIAMOND_JUBILEE_BANK_HOLIDAY",
        },
        2022: {
            pd.Timestamp("2022-06-02"): "SPRING_BANK_HOLIDAY_MOVED",
            pd.Timestamp("2022-06-03"): "PLATINUM_JUBILEE_BANK_HOLIDAY",
        },
    }
    if year in exceptional_spring:
        holidays.update(exceptional_spring[year])
    else:
        holidays[_last_monday(year, 5)] = "SPRING_BANK_HOLIDAY"
    holidays[_last_monday(year, 8)] = "SUMMER_BANK_HOLIDAY"

    christmas = pd.Timestamp(year, 12, 25)
    boxing = pd.Timestamp(year, 12, 26)
    actual = [(christmas, "CHRISTMAS_DAY"), (boxing, "BOXING_DAY")]
    reserved = {date for date, _ in actual if date.weekday() < 5}
    for date, label in actual:
        if date.weekday() < 5:
            holidays[date] = label
    for date, label in actual:
        if date.weekday() >= 5:
            substitute = date
            while True:
                substitute += pd.Timedelta(days=1)
                if substitute.weekday() < 5 and substitute not in reserved and substitute not in holidays:
                    holidays[substitute] = f"{label}_SUBSTITUTE"
                    reserved.add(substitute)
                    break

    one_off = {
        pd.Timestamp("2011-04-29"): "ROYAL_WEDDING_BANK_HOLIDAY",
        pd.Timestamp("2022-09-19"): "STATE_FUNERAL_BANK_HOLIDAY",
        pd.Timestamp("2023-05-08"): "CORONATION_BANK_HOLIDAY",
    }
    for date, label in one_off.items():
        if date.year == year:
            holidays[date] = label
    return holidays


def build_xlon_session_calendar(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DatetimeIndex, dict[pd.Timestamp, str]]:
    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    holiday_map: dict[pd.Timestamp, str] = {}
    for year in range(start.year, end.year + 1):
        holiday_map.update(england_wales_bank_holidays(year))
    weekdays = pd.bdate_range(start, end)
    sessions = pd.DatetimeIndex([date for date in weekdays if date not in holiday_map], name="date")
    return sessions, holiday_map


def endpoint_valid_mask(frame: pd.DataFrame) -> pd.Series:
    semantic = frame.get("semantic_family_match", pd.Series(np.nan, index=frame.index))
    semantic_failure = semantic.notna() & semantic.astype(str).str.lower().eq("false")
    validation = frame.get("total_return_validation_status", pd.Series("", index=frame.index)).fillna("").astype(str)
    wealth = pd.to_numeric(frame.get("adjusted_wealth_gbp"), errors="coerce")
    return (
        frame.get("price_available", False).fillna(False).astype(bool)
        & ~frame.get("missing_flag", True).fillna(True).astype(bool)
        & ~frame.get("stale_flag", False).fillna(False).astype(bool)
        & ~frame.get("proxy_flag", False).fillna(False).astype(bool)
        & ~frame.get("price_before_inception_flag", False).fillna(False).astype(bool)
        & wealth.gt(0)
        & np.isfinite(wealth)
        & validation.str.startswith("PASS")
        & ~semantic_failure
    )


def build_continuous_family_history(
    selected_endpoints: pd.DataFrame,
    maximum_gap_sessions: int,
) -> pd.DataFrame:
    """Create a past-only continuous index; missing rows remain missing.

    A gap of at most ``maximum_gap_sessions`` may be bridged by the selected
    listing's own adjusted-wealth endpoints. The intervening observations are
    never filled. A longer gap starts a new, non-comparable continuity segment.
    """
    output: list[dict[str, object]] = []
    for family, group in selected_endpoints.groupby("economic_exposure_family_id", sort=True):
        chain_level = np.nan
        segment = 0
        prior_family_position: int | None = None
        prior_selection: str | None = None
        for row in group.sort_values("session_position", kind="mergesort").itertuples(index=False):
            endpoint_valid = bool(row.endpoint_valid)
            chain_return = np.nan
            chain_level_out = np.nan
            return_span = np.nan
            continuity_reason = str(row.endpoint_failure_reason)
            transition_flag = prior_selection is not None and str(row.effective_listing_id) != prior_selection
            if endpoint_valid:
                listing_prior_position = row.previous_listing_valid_session_position
                listing_prior_wealth = row.previous_listing_valid_wealth_gbp
                listing_span = (
                    int(row.session_position - listing_prior_position)
                    if pd.notna(listing_prior_position)
                    else None
                )
                family_span = (
                    int(row.session_position - prior_family_position)
                    if prior_family_position is not None
                    else None
                )
                can_continue = (
                    listing_span is not None
                    and family_span is not None
                    and 1 <= listing_span <= int(maximum_gap_sessions)
                    and 1 <= family_span <= int(maximum_gap_sessions)
                    and pd.notna(listing_prior_wealth)
                    and float(listing_prior_wealth) > 0
                    and np.isfinite(float(listing_prior_wealth))
                )
                if can_continue:
                    chain_return = float(row.adjusted_wealth_gbp) / float(listing_prior_wealth) - 1.0
                    if not np.isfinite(chain_return) or chain_return <= -1.0:
                        can_continue = False
                if can_continue:
                    chain_level = float(chain_level) * (1.0 + chain_return)
                    chain_level_out = chain_level
                    return_span = listing_span
                    if transition_flag:
                        continuity_reason = "SEMANTICALLY_IDENTICAL_IMPLEMENTATION_TRANSITION"
                    elif listing_span == 1:
                        continuity_reason = "EXACT_PREVIOUS_XLON_SESSION_ENDPOINT"
                    else:
                        continuity_reason = f"PRIOR_VALID_ENDPOINT_WITHIN_{listing_span}_XLON_SESSIONS"
                else:
                    segment += 1
                    chain_level = 100.0
                    chain_level_out = chain_level
                    continuity_reason = "CONTINUITY_SEGMENT_START_OR_RESET"
                prior_family_position = int(row.session_position)
                prior_selection = str(row.effective_listing_id)
            output.append(
                {
                    **row._asdict(),
                    "signal_wealth_index_gbp": chain_level_out,
                    "continuity_segment_id": int(segment),
                    "return_since_prior_valid_endpoint": chain_return,
                    "return_span_xlon_sessions": return_span,
                    "implementation_transition_flag": bool(transition_flag and endpoint_valid),
                    "continuity_reason": continuity_reason,
                }
            )
    return pd.DataFrame(output)


def endpoint_formation_matrices(
    level: pd.DataFrame,
    segment: pd.DataFrame,
    horizons: Iterable[int],
    target_backward_tolerance_sessions: int,
) -> tuple[dict[int, pd.DataFrame], dict[int, pd.DataFrame], dict[int, pd.DataFrame]]:
    levels = level.astype(float).to_numpy()
    segments = segment.astype(float).to_numpy()
    n_dates, n_families = levels.shape
    returns: dict[int, pd.DataFrame] = {}
    target_positions: dict[int, pd.DataFrame] = {}
    target_offsets: dict[int, pd.DataFrame] = {}
    for horizon_value in horizons:
        horizon = int(horizon_value)
        values = np.full((n_dates, n_families), np.nan)
        targets = np.full((n_dates, n_families), -1, dtype=np.int32)
        offsets = np.full((n_dates, n_families), -1, dtype=np.int16)
        for current in range(horizon, n_dates):
            current_values = levels[current]
            current_segments = segments[current]
            for offset in range(int(target_backward_tolerance_sessions) + 1):
                target = current - horizon - offset
                if target < 0:
                    continue
                target_values = levels[target]
                valid = (
                    np.isfinite(current_values)
                    & ~np.isfinite(values[current])
                    & np.isfinite(target_values)
                    & (current_segments == segments[target])
                )
                values[current, valid] = current_values[valid] / target_values[valid] - 1.0
                targets[current, valid] = target
                offsets[current, valid] = offset
        returns[horizon] = pd.DataFrame(values, index=level.index, columns=level.columns)
        target_positions[horizon] = pd.DataFrame(targets, index=level.index, columns=level.columns)
        target_offsets[horizon] = pd.DataFrame(offsets, index=level.index, columns=level.columns)
    return returns, target_positions, target_offsets


def endpoint_forward_matrices(
    level: pd.DataFrame,
    segment: pd.DataFrame,
    horizons: Iterable[int],
) -> dict[int, pd.DataFrame]:
    levels = level.astype(float).to_numpy()
    segments = segment.astype(float).to_numpy()
    n_dates, _ = levels.shape
    output: dict[int, pd.DataFrame] = {}
    for horizon_value in horizons:
        horizon = int(horizon_value)
        values = np.full_like(levels, np.nan, dtype=float)
        if horizon < n_dates:
            current = levels[:-horizon]
            future = levels[horizon:]
            valid = np.isfinite(current) & np.isfinite(future) & (segments[:-horizon] == segments[horizon:])
            block = np.divide(future, current, out=np.full_like(current, np.nan), where=valid) - 1.0
            values[:-horizon] = np.where(valid, block, np.nan)
        output[horizon] = pd.DataFrame(values, index=level.index, columns=level.columns)
    return output


def same_segment_complete_window(valid: pd.DataFrame, segment: pd.DataFrame, window: int) -> pd.DataFrame:
    count = valid.astype(int).rolling(int(window), min_periods=int(window)).sum().eq(int(window))
    minimum = segment.rolling(int(window), min_periods=int(window)).min()
    maximum = segment.rolling(int(window), min_periods=int(window)).max()
    return count & minimum.eq(maximum)
