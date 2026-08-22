"""Source-faithful monthly factor-residual reversal research primitives.

The module is intentionally narrow.  It computes the frozen MR-RESID-A1
Fama-French three-factor residual signal, deterministic cross-sectional tails,
causal monthly execution schedules, and forward raw-open outcomes.  Portfolio
accounting lives in :mod:`edge_research.monthly_long_short`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd


FACTOR_COLUMNS = ("mkt_rf", "smb", "hml")


@dataclass(frozen=True)
class ResidualSignalResult:
    signals: pd.DataFrame
    formation_summary: pd.DataFrame


@dataclass(frozen=True)
class ResidualExecutionSchedule:
    signals: pd.DataFrame
    targets: pd.DataFrame
    events: pd.DataFrame


def load_french_monthly_factors(path: str | Path) -> pd.DataFrame:
    """Parse the monthly section of the official Kenneth French FF3 CSV.

    The provider file also contains an annual section.  Only rows whose first
    field is exactly ``YYYYMM`` are admitted, and percentage values are changed
    to decimal monthly returns.
    """

    source = Path(path)
    rows: list[dict] = []
    for line in source.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        fields = [item.strip() for item in line.split(",")]
        if len(fields) < 5 or re.fullmatch(r"\d{6}", fields[0]) is None:
            continue
        try:
            month = pd.Period(fields[0], freq="M")
            values = [float(value) / 100.0 for value in fields[1:5]]
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "month": month,
                "mkt_rf": values[0],
                "smb": values[1],
                "hml": values[2],
                "rf": values[3],
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No monthly Fama-French observations were parsed from {source}")
    if frame["month"].duplicated().any():
        raise ValueError("Fama-French monthly input contains duplicate YYYYMM observations")
    return frame.sort_values("month", kind="mergesort").reset_index(drop=True)


def build_monthly_price_returns(signal_panel: pd.DataFrame) -> pd.DataFrame:
    """Create split-consistent, price-only month-end close returns.

    The existing corporate-action bridge supplies ``adjusted_close`` solely for
    signals and leaves raw ``close`` intact for the formation-price screen.
    Returns are admitted only when the preceding observation is the immediately
    preceding calendar month.
    """

    required = {"date", "symbol", "close", "adjusted_close"}
    missing = required.difference(signal_panel.columns)
    if missing:
        raise ValueError(f"Monthly return construction is missing fields: {sorted(missing)}")
    frame = signal_panel.loc[:, sorted(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["month"] = frame["date"].dt.to_period("M")
    frame = (
        frame.sort_values(["symbol", "date"], kind="mergesort")
        .groupby(["symbol", "month"], sort=False, as_index=False)
        .tail(1)
        .sort_values(["symbol", "month"], kind="mergesort")
        .reset_index(drop=True)
    )
    previous_close = frame.groupby("symbol", sort=False)["adjusted_close"].shift(1)
    previous_month = frame.groupby("symbol", sort=False)["month"].shift(1)
    consecutive = np.array(
        [
            previous is not None and not pd.isna(previous) and int(current.ordinal - previous.ordinal) == 1
            for current, previous in zip(frame["month"], previous_month)
        ],
        dtype=bool,
    )
    frame["monthly_price_return"] = np.where(
        consecutive,
        pd.to_numeric(frame["adjusted_close"], errors="coerce") / previous_close - 1.0,
        np.nan,
    )
    return frame.rename(
        columns={
            "date": "formation_date",
            "close": "raw_formation_close",
            "adjusted_close": "adjusted_formation_close",
        }
    )[
        [
            "month",
            "formation_date",
            "symbol",
            "raw_formation_close",
            "adjusted_formation_close",
            "monthly_price_return",
        ]
    ]


def compute_residual_signals(
    monthly_returns: pd.DataFrame,
    factors: pd.DataFrame,
    pit: pd.DataFrame,
    *,
    window_months: int = 36,
    residual_ddof: int = 1,
    tail_fraction: float = 0.20,
    diagnostic_buckets: int = 10,
) -> ResidualSignalResult:
    """Estimate rolling FF3 residual shocks inside the causal PIT membership.

    The formation month is the final row in each 36-observation OLS window, as
    specified by the frozen A1 source-replication protocol.
    """

    if window_months != 36:
        raise ValueError("MR-RESID-A1 is frozen to a 36-month regression window")
    if residual_ddof != 1:
        raise ValueError("MR-RESID-A1 is frozen to sample residual volatility (ddof=1)")
    required_monthly = {
        "month",
        "formation_date",
        "symbol",
        "raw_formation_close",
        "monthly_price_return",
    }
    required_factors = {"month", "mkt_rf", "smb", "hml", "rf"}
    required_pit = {"ticker", "snapshot_date", "liquidity_rank"}
    for name, frame, required in (
        ("monthly returns", monthly_returns, required_monthly),
        ("factor data", factors, required_factors),
        ("PIT membership", pit, required_pit),
    ):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} are missing fields: {sorted(missing)}")

    monthly = monthly_returns.copy()
    monthly["month"] = pd.PeriodIndex(monthly["month"], freq="M")
    monthly["formation_date"] = pd.to_datetime(monthly["formation_date"], errors="raise").dt.normalize()
    monthly["symbol"] = monthly["symbol"].astype(str).str.upper().str.strip()
    if monthly.duplicated(["month", "symbol"]).any():
        raise ValueError("Monthly returns require one observation per symbol/month")

    factor_frame = factors.copy()
    factor_frame["month"] = pd.PeriodIndex(factor_frame["month"], freq="M")
    factor_frame = factor_frame.set_index("month").sort_index()
    if factor_frame.index.duplicated().any():
        raise ValueError("Factor data require one observation per month")

    pit_frame = pit.copy()
    pit_frame["ticker"] = pit_frame["ticker"].astype(str).str.upper().str.strip()
    if "research_ticker" not in pit_frame:
        pit_frame["research_ticker"] = pit_frame["ticker"]
    pit_frame["research_ticker"] = pit_frame["research_ticker"].astype(str).str.upper().str.strip()
    pit_frame["snapshot_date"] = pd.to_datetime(pit_frame["snapshot_date"], errors="raise").dt.normalize()
    structural_mask = pd.Series(True, index=pit_frame.index)
    if "type" in pit_frame:
        structural_mask &= pit_frame["type"].astype(str).str.upper().eq("CS")
    if "market" in pit_frame:
        structural_mask &= pit_frame["market"].astype(str).str.lower().eq("stocks")
    if "locale" in pit_frame:
        structural_mask &= pit_frame["locale"].astype(str).str.lower().eq("us")
    if "currency_name" in pit_frame:
        structural_mask &= pit_frame["currency_name"].astype(str).str.lower().eq("usd")
    if "is_primary_trading_ticker" in pit_frame:
        structural_mask &= pit_frame["is_primary_trading_ticker"].map(_as_bool)
    pit_frame["a1_structurally_eligible"] = structural_mask
    snapshots = list(pit_frame.groupby("snapshot_date", sort=True))
    snapshot_dates = np.array([np.datetime64(date) for date, _ in snapshots], dtype="datetime64[ns]")

    return_pivot = monthly.pivot(index="month", columns="symbol", values="monthly_price_return").sort_index()
    raw_close_pivot = monthly.pivot(index="month", columns="symbol", values="raw_formation_close").sort_index()
    formation_dates = monthly.groupby("month", sort=True)["formation_date"].max()

    signal_frames: list[pd.DataFrame] = []
    summary_rows: list[dict] = []
    for month, formation_date in formation_dates.items():
        history = pd.period_range(end=month, periods=window_months, freq="M")
        if not history.isin(factor_frame.index).all() or not history.isin(return_pivot.index).all():
            continue
        snapshot_position = int(np.searchsorted(snapshot_dates, np.datetime64(formation_date), side="right") - 1)
        if snapshot_position < 0:
            continue
        snapshot_date, snapshot = snapshots[snapshot_position]
        structural = snapshot.loc[snapshot["a1_structurally_eligible"]].copy()
        membership_symbols = structural["ticker"].astype(str).tolist()
        available_symbols = [symbol for symbol in membership_symbols if symbol in return_pivot.columns]
        if not available_symbols:
            continue

        stock_window = return_pivot.reindex(index=history, columns=available_symbols)
        current_raw_close = raw_close_pivot.reindex(index=[month], columns=available_symbols).iloc[0]
        complete_history = stock_window.notna().all(axis=0) & np.isfinite(stock_window).all(axis=0)
        price_screen = pd.to_numeric(current_raw_close, errors="coerce").gt(1.0)
        eligible_symbols = [
            symbol for symbol in available_symbols if bool(complete_history.get(symbol, False) and price_screen.get(symbol, False))
        ]
        base_summary = {
            "formation_month": str(month),
            "formation_date": pd.Timestamp(formation_date),
            "pit_snapshot_date": pd.Timestamp(snapshot_date),
            "parent_members": int(len(snapshot)),
            "structurally_eligible_members": int(len(structural)),
            "members_with_monthly_observation": int(len(available_symbols)),
            "members_with_complete_36_month_history": int(complete_history.sum()),
            "members_passing_raw_price_above_1": int(price_screen.sum()),
        }
        if not eligible_symbols:
            summary_rows.append({**base_summary, "eligible_signals": 0, "tail_count_per_leg": 0})
            continue

        factor_window = factor_frame.loc[history, [*FACTOR_COLUMNS, "rf"]].astype(float)
        x = np.column_stack([np.ones(window_months), factor_window.loc[:, FACTOR_COLUMNS].to_numpy(dtype=float)])
        if np.linalg.matrix_rank(x) < x.shape[1]:
            summary_rows.append({**base_summary, "eligible_signals": 0, "tail_count_per_leg": 0, "reason": "rank_deficient_ff3_design"})
            continue
        stock_matrix = stock_window.loc[:, eligible_symbols].to_numpy(dtype=float)
        y = stock_matrix - factor_window["rf"].to_numpy(dtype=float)[:, None]
        coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
        fitted = x @ coefficients
        residuals = y - fitted
        residual_sigma = residuals.std(axis=0, ddof=residual_ddof)
        latest_residual = residuals[-1, :]
        finite = np.isfinite(residual_sigma) & (residual_sigma > 0) & np.isfinite(latest_residual)
        eligible_array = np.asarray(eligible_symbols, dtype=object)[finite]
        if len(eligible_array) == 0:
            summary_rows.append({**base_summary, "eligible_signals": 0, "tail_count_per_leg": 0, "reason": "nonpositive_residual_volatility"})
            continue
        residual_sigma = residual_sigma[finite]
        latest_residual = latest_residual[finite]
        coefficients = coefficients[:, finite]
        fitted = fitted[:, finite]
        y = y[:, finite]
        residuals = residuals[:, finite]
        total_ss = ((y - y.mean(axis=0)) ** 2).sum(axis=0)
        residual_ss = (residuals**2).sum(axis=0)
        r_squared = np.where(total_ss > 0, 1.0 - residual_ss / total_ss, np.nan)
        rank_map = dict(
            zip(
                snapshot["ticker"].astype(str),
                pd.to_numeric(snapshot["liquidity_rank"], errors="coerce"),
            )
        )
        ticker_map = dict(zip(snapshot["ticker"].astype(str), snapshot["research_ticker"].astype(str)))
        current_returns = return_pivot.loc[month, eligible_array].to_numpy(dtype=float)
        raw_closes = raw_close_pivot.loc[month, eligible_array].to_numpy(dtype=float)
        cross_section = pd.DataFrame(
            {
                "formation_month": str(month),
                "formation_date": pd.Timestamp(formation_date),
                "pit_snapshot_date": pd.Timestamp(snapshot_date),
                "symbol": eligible_array.astype(str),
                "ticker_at_formation": [ticker_map.get(str(symbol), str(symbol)) for symbol in eligible_array],
                "pit_liquidity_rank": [rank_map.get(str(symbol), np.nan) for symbol in eligible_array],
                "raw_formation_close": raw_closes,
                "monthly_price_return": current_returns,
                "rf": float(factor_window["rf"].iloc[-1]),
                "actual_excess_return": y[-1, :],
                "model_expected_excess_return": fitted[-1, :],
                "latest_residual": latest_residual,
                "residual_volatility": residual_sigma,
                "resid_z": latest_residual / residual_sigma,
                "alpha": coefficients[0, :],
                "beta_mkt": coefficients[1, :],
                "beta_smb": coefficients[2, :],
                "beta_hml": coefficients[3, :],
                "r_squared": r_squared,
                "regression_observations": window_months,
            }
        ).sort_values(["resid_z", "ticker_at_formation", "symbol"], kind="mergesort").reset_index(drop=True)
        count = len(cross_section)
        tail_count = max(1, int(np.floor(count * tail_fraction)))
        cross_section["cross_section_size"] = count
        cross_section["resid_rank"] = np.arange(1, count + 1, dtype=int)
        cross_section["resid_bucket"] = np.floor(np.arange(count) * diagnostic_buckets / count).astype(int) + 1
        cross_section["portfolio_leg"] = "NOT_SELECTED"
        cross_section.loc[cross_section.index[:tail_count], "portfolio_leg"] = "LONG"
        cross_section.loc[cross_section.index[-tail_count:], "portfolio_leg"] = "SHORT"
        cross_section["target_weight"] = 0.0
        cross_section.loc[cross_section["portfolio_leg"].eq("LONG"), "target_weight"] = 1.0 / tail_count
        cross_section.loc[cross_section["portfolio_leg"].eq("SHORT"), "target_weight"] = -1.0 / tail_count
        signal_frames.append(cross_section)
        summary_rows.append(
            {
                **base_summary,
                "eligible_signals": int(count),
                "tail_count_per_leg": int(tail_count),
                "long_target_weight_sum": float(cross_section.loc[cross_section["portfolio_leg"].eq("LONG"), "target_weight"].sum()),
                "short_target_weight_sum": float(cross_section.loc[cross_section["portfolio_leg"].eq("SHORT"), "target_weight"].sum()),
            }
        )

    signals = pd.concat(signal_frames, ignore_index=True) if signal_frames else pd.DataFrame()
    if not signals.empty:
        signals = signals.sort_values(
            ["formation_date", "resid_z", "ticker_at_formation", "symbol"], kind="mergesort"
        ).reset_index(drop=True)
        signals.insert(0, "signal_id", [f"MR-RESID-A1-S-{index:09d}" for index in range(1, len(signals) + 1)])
    return ResidualSignalResult(signals=signals, formation_summary=pd.DataFrame(summary_rows))


def build_execution_schedule(
    signals: pd.DataFrame,
    calendar: list | tuple | pd.Series | pd.DatetimeIndex,
    timing_variant: str,
) -> ResidualExecutionSchedule:
    """Freeze first-open or skip-one-session monthly target dates.

    A formation is retained only when both its next-month entry and following-
    month exit session exist.  Exit dates are also emitted as empty target
    events when no following formation replaces the portfolio.
    """

    timing = str(timing_variant).upper()
    session_offset = {"A1_CANONICAL": 0, "A1_SKIP1": 1}.get(timing)
    if session_offset is None:
        raise ValueError("timing_variant must be A1_CANONICAL or A1_SKIP1")
    if signals.empty:
        return ResidualExecutionSchedule(signals=signals.copy(), targets=pd.DataFrame(), events=pd.DataFrame())
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar, errors="raise")).normalize().unique().sort_values()
    sessions_by_month = {month: group for month, group in pd.Series(sessions).groupby(sessions.to_period("M"))}
    schedules: list[dict] = []
    for formation_date in sorted(pd.to_datetime(signals["formation_date"], errors="raise").dt.normalize().unique()):
        formation = pd.Timestamp(formation_date)
        entry_sessions = sessions_by_month.get(formation.to_period("M") + 1)
        exit_sessions = sessions_by_month.get(formation.to_period("M") + 2)
        if entry_sessions is None or exit_sessions is None or len(entry_sessions) <= session_offset or len(exit_sessions) <= session_offset:
            continue
        schedules.append(
            {
                "timing_variant": timing,
                "formation_month": str(formation.to_period("M")),
                "formation_date": formation,
                "intended_entry_date": pd.Timestamp(entry_sessions.iloc[session_offset]),
                "intended_exit_date": pd.Timestamp(exit_sessions.iloc[session_offset]),
            }
        )
    schedule = pd.DataFrame(schedules)
    if schedule.empty:
        return ResidualExecutionSchedule(signals=signals.iloc[0:0].copy(), targets=pd.DataFrame(), events=pd.DataFrame())
    admitted = signals.merge(schedule, on=["formation_month", "formation_date"], how="inner", validate="many_to_one")
    selected = admitted.loc[admitted["portfolio_leg"].isin(["LONG", "SHORT"])].copy()
    selected["rebalance_date"] = selected["intended_entry_date"]
    selected["timing_variant"] = timing
    target_columns = [
        "timing_variant",
        "formation_month",
        "formation_date",
        "rebalance_date",
        "intended_exit_date",
        "signal_id",
        "symbol",
        "portfolio_leg",
        "target_weight",
        "resid_z",
        "resid_rank",
        "cross_section_size",
    ]
    for optional in ("ticker_at_formation", "stable_security_id", "identity_interval_id"):
        if optional in selected.columns:
            target_columns.append(optional)
    targets = selected[target_columns].sort_values(["rebalance_date", "portfolio_leg", "symbol"], kind="mergesort")

    entry_rows = schedule.rename(columns={"intended_entry_date": "rebalance_date"}).copy()
    entry_rows["event_type"] = "FORMATION_REBALANCE"
    exit_rows = schedule.rename(columns={"intended_exit_date": "rebalance_date"}).copy()
    exit_rows["event_type"] = "HOLDING_PERIOD_EXIT"
    all_event_dates = pd.concat(
        [
            entry_rows[["rebalance_date", "event_type", "formation_date", "formation_month", "timing_variant"]],
            exit_rows[["rebalance_date", "event_type", "formation_date", "formation_month", "timing_variant"]],
        ],
        ignore_index=True,
    ).sort_values(["rebalance_date", "event_type", "formation_date"], kind="mergesort")
    rows: list[dict] = []
    target_dates = set(pd.to_datetime(targets["rebalance_date"]).dt.normalize())
    for date, frame in all_event_dates.groupby("rebalance_date", sort=True):
        event_type = "FORMATION_REBALANCE" if pd.Timestamp(date) in target_dates else "LIQUIDATE"
        formation_row = frame.sort_values("formation_date", kind="mergesort").iloc[-1]
        rows.append(
            {
                "event_id": f"MR-RESID-A1-{timing}-{pd.Timestamp(date):%Y%m%d}",
                "timing_variant": timing,
                "rebalance_date": pd.Timestamp(date),
                "formation_date": pd.Timestamp(formation_row["formation_date"]),
                "formation_month": str(formation_row["formation_month"]),
                "event_type": event_type,
            }
        )
    events = pd.DataFrame(rows).sort_values("rebalance_date", kind="mergesort").reset_index(drop=True)
    if not (events["rebalance_date"] > events["formation_date"]).all():
        raise ValueError("Every MR-RESID target event must execute after its source formation close")
    return ResidualExecutionSchedule(signals=admitted, targets=targets.reset_index(drop=True), events=events)


def attach_forward_open_returns(
    scheduled_signals: pd.DataFrame,
    market_panel: pd.DataFrame,
    *,
    calendar: list | tuple | pd.Series | pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Attach causal raw-open holding returns with split lifecycle continuity."""

    required_signal = {"symbol", "intended_entry_date", "intended_exit_date"}
    required_market = {"date", "symbol", "open", "split_factor_at_open"}
    if missing := required_signal.difference(scheduled_signals.columns):
        raise ValueError(f"Scheduled signals are missing fields: {sorted(missing)}")
    if missing := required_market.difference(market_panel.columns):
        raise ValueError(f"Market panel is missing fields: {sorted(missing)}")
    market = market_panel.copy()
    market["date"] = pd.to_datetime(market["date"], errors="raise").dt.normalize()
    market["symbol"] = market["symbol"].astype(str).str.upper().str.strip()
    if "terminal_proxy_only" not in market:
        market["terminal_proxy_only"] = False
    if market.duplicated(["symbol", "date"]).any():
        raise ValueError("Forward-return market panel requires one bar per symbol/date")
    lookups: dict[str, dict] = {}
    for symbol, group in market.sort_values(["symbol", "date"], kind="mergesort").groupby("symbol", sort=False):
        dates = group["date"].to_numpy(dtype="datetime64[ns]")
        split_cumulative = pd.to_numeric(group["split_factor_at_open"], errors="coerce").fillna(1.0).cumprod().to_numpy(dtype=float)
        lookups[str(symbol)] = {
            "dates": dates,
            "open": pd.to_numeric(group["open"], errors="coerce").to_numpy(dtype=float),
            "split_cumulative": split_cumulative,
            "terminal": group["terminal_proxy_only"].fillna(False).astype(bool).to_numpy(),
        }
    calendar_index = pd.DatetimeIndex(pd.to_datetime(calendar if calendar is not None else market["date"].unique())).normalize().unique().sort_values()
    calendar_positions = {np.datetime64(date): index for index, date in enumerate(calendar_index)}

    rows: list[dict] = []
    for row in scheduled_signals.itertuples(index=False):
        symbol = str(row.symbol)
        intended_entry = pd.Timestamp(row.intended_entry_date).normalize()
        intended_exit = pd.Timestamp(row.intended_exit_date).normalize()
        lookup = lookups.get(symbol)
        outcome = {
            "actual_entry_date": pd.NaT,
            "actual_exit_date": pd.NaT,
            "entry_raw_open": np.nan,
            "exit_raw_open": np.nan,
            "intervening_split_factor": np.nan,
            "forward_open_return": np.nan,
            "entry_carry_sessions": np.nan,
            "exit_carry_sessions": np.nan,
            "terminal_proxy_exit": False,
            "entry_month_boundary_breach": False,
            "exit_month_boundary_breach": False,
            "security_identity_continuity_unresolved": False,
            "outcome_status": "NO_MARKET_HISTORY",
        }
        if lookup is not None:
            dates = lookup["dates"]
            entry_position = int(np.searchsorted(dates, np.datetime64(intended_entry), side="left"))
            while entry_position < len(dates) and bool(lookup["terminal"][entry_position]):
                entry_position += 1
            exit_position = int(np.searchsorted(dates, np.datetime64(intended_exit), side="left"))
            terminal_positions = np.flatnonzero(
                lookup["terminal"]
                & (dates > np.datetime64(intended_entry))
                & (dates <= np.datetime64(intended_exit))
            )
            if len(terminal_positions):
                exit_position = int(terminal_positions[0])
            if entry_position >= len(dates):
                outcome["outcome_status"] = "NO_EXECUTABLE_ENTRY"
            elif exit_position >= len(dates):
                outcome["outcome_status"] = "NO_EXECUTABLE_EXIT"
            elif dates[entry_position] >= dates[exit_position]:
                outcome["outcome_status"] = "ENTRY_NOT_BEFORE_EXIT"
            else:
                entry_open = float(lookup["open"][entry_position])
                exit_open = float(lookup["open"][exit_position])
                entry_cumulative = float(lookup["split_cumulative"][entry_position])
                exit_cumulative = float(lookup["split_cumulative"][exit_position])
                split_factor = exit_cumulative / entry_cumulative
                actual_entry = pd.Timestamp(dates[entry_position])
                actual_exit = pd.Timestamp(dates[exit_position])
                outcome.update(
                    {
                        "actual_entry_date": actual_entry,
                        "actual_exit_date": actual_exit,
                        "entry_raw_open": entry_open,
                        "exit_raw_open": exit_open,
                        "intervening_split_factor": split_factor,
                        "forward_open_return": exit_open * split_factor / entry_open - 1.0,
                        "entry_carry_sessions": _session_gap(calendar_positions, intended_entry, actual_entry),
                        "exit_carry_sessions": max(
                            0, _session_gap(calendar_positions, intended_exit, actual_exit)
                        ),
                        "terminal_proxy_exit": bool(lookup["terminal"][exit_position]),
                        "entry_month_boundary_breach": bool(
                            actual_entry.to_period("M") != intended_entry.to_period("M")
                        ),
                        "exit_month_boundary_breach": bool(
                            actual_exit.to_period("M") != intended_exit.to_period("M")
                        ),
                        "security_identity_continuity_unresolved": bool(
                            not lookup["terminal"][exit_position]
                            and (
                                actual_entry.to_period("M") != intended_entry.to_period("M")
                                or actual_exit.to_period("M") != intended_exit.to_period("M")
                            )
                        ),
                        "outcome_status": "COMPLETE",
                    }
                )
        rows.append(outcome)
    return pd.concat([scheduled_signals.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def newey_west_mean_test(values: pd.Series | np.ndarray | list[float], lags: int = 3) -> dict[str, float | int]:
    """Return a Bartlett-kernel Newey-West test of a time-series mean."""

    series = np.asarray(pd.Series(values).dropna(), dtype=float)
    count = len(series)
    if count == 0:
        return {"observations": 0, "mean": np.nan, "standard_error": np.nan, "t_stat": np.nan}
    mean = float(series.mean())
    centred = series - mean
    gamma_zero = float(np.dot(centred, centred) / count)
    long_run_variance = gamma_zero
    effective_lags = min(max(int(lags), 0), count - 1)
    for lag in range(1, effective_lags + 1):
        covariance = float(np.dot(centred[lag:], centred[:-lag]) / count)
        weight = 1.0 - lag / (effective_lags + 1.0)
        long_run_variance += 2.0 * weight * covariance
    long_run_variance = max(long_run_variance, 0.0)
    standard_error = float(np.sqrt(long_run_variance / count))
    t_stat = mean / standard_error if standard_error > 0 else np.nan
    return {
        "observations": int(count),
        "mean": mean,
        "standard_error": standard_error,
        "t_stat": float(t_stat),
        "hac_lags": int(effective_lags),
    }


def _as_bool(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _session_gap(positions: dict[np.datetime64, int], intended: pd.Timestamp, actual: pd.Timestamp) -> float:
    intended_position = positions.get(np.datetime64(intended))
    actual_position = positions.get(np.datetime64(actual))
    if intended_position is None or actual_position is None:
        return np.nan
    return float(actual_position - intended_position)
