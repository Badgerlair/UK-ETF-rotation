from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from edge_research.contracts import CANDIDATE_COLUMNS, ORDER_COLUMNS
from edge_research.strategy_base import StrategyModule


EXIT_SIGNAL_COLUMNS = [
    "strategy_name",
    "symbol",
    "signal_date",
    "signal_observation_time",
    "earliest_information_availability",
    "order_submission_time",
    "intended_exit_date",
    "assumed_fill_time",
    "fill_price_field",
    "reason",
]


@dataclass(frozen=True)
class ExtremeMoveProbabilityConfig:
    """Frozen source-replication parameters; no optimisation defaults live here."""

    return_window: int = 3
    history_sessions: int = 1260
    minimum_history_sessions: int = 1260
    qp_threshold: float = 15.0
    trend_sma: int = 200
    liquidity_definition: str = "LIQ_A"
    liquidity_window: int = 20
    maximum_positions: int = 10
    position_size_pct: float = 10.0
    parameter_set_id: str = "MR-QP-A1_SOURCE_REPLICATION"

    def __post_init__(self) -> None:
        if self.return_window <= 0:
            raise ValueError("return_window must be positive")
        if self.history_sessions <= 0:
            raise ValueError("history_sessions must be positive")
        if not 1 <= self.minimum_history_sessions <= self.history_sessions:
            raise ValueError("minimum_history_sessions must be within the history window")
        if self.qp_threshold <= 0 or self.qp_threshold >= 100:
            raise ValueError("qp_threshold must be strictly between 0 and 100")
        if self.trend_sma <= 0 or self.liquidity_window <= 0:
            raise ValueError("rolling windows must be positive")
        if self.liquidity_definition not in {"LIQ_A", "LIQ_B"}:
            raise ValueError("liquidity_definition must be LIQ_A or LIQ_B")


def execution_timing_metadata() -> dict[str, str]:
    return {
        "signal_observation_time": "Close(t)",
        "earliest_information_availability": "After Close(t)",
        "entry_order_submission_time": "After Close(t), for next regular session",
        "entry_assumed_fill_time": "Open(t+1)",
        "entry_fill_price_field": "raw executable open(t+1)",
        "exit_signal_observation_time": "Close(t)",
        "exit_earliest_information_availability": "After Close(t)",
        "exit_order_submission_time": "After Close(t), for next regular session",
        "exit_assumed_fill_time": "Open(t+1)",
        "exit_fill_price_field": "raw executable open(t+1)",
    }


def extreme_move_probability(
    returns: pd.Series,
    history_sessions: int,
    minimum_history_sessions: int | None = None,
) -> pd.Series:
    """Calculate the source QP tail percentage using only observations before t.

    A negative current return is compared with prior negative returns using an
    inclusive lower tail. A positive current return uses an inclusive upper
    tail of prior positive returns. Zero returns and empty sign denominators
    produce no QP value. Rolling ranks make the calculation practical on a
    panel without materialising every historical window.
    """

    if history_sessions <= 0:
        raise ValueError("history_sessions must be positive")
    minimum = history_sessions if minimum_history_sessions is None else int(minimum_history_sessions)
    if not 1 <= minimum <= history_sessions:
        raise ValueError("minimum_history_sessions must be within the history window")

    values = pd.to_numeric(returns, errors="coerce").astype(float)
    rolling = values.rolling(history_sessions + 1, min_periods=minimum + 1)
    rank_max = rolling.rank(method="max", ascending=True)
    rank_min = rolling.rank(method="min", ascending=True)
    rolling_count = rolling.count()

    prior = values.shift(1)
    prior_valid = prior.notna().astype(float).where(prior.notna())
    negative = prior.lt(0).astype(float).where(prior.notna())
    positive = prior.gt(0).astype(float).where(prior.notna())
    history_count = prior_valid.rolling(history_sessions, min_periods=minimum).sum()
    negative_count = negative.rolling(history_sessions, min_periods=minimum).sum()
    positive_count = positive.rolling(history_sessions, min_periods=minimum).sum()

    negative_tail = rank_max - 1.0
    positive_tail = rolling_count - rank_min
    qp = pd.Series(np.nan, index=values.index, dtype=float)
    enough_history = history_count.ge(minimum)
    negative_mask = values.lt(0) & enough_history & negative_count.gt(0)
    positive_mask = values.gt(0) & enough_history & positive_count.gt(0)
    qp.loc[negative_mask] = 100.0 * negative_tail.loc[negative_mask] / negative_count.loc[negative_mask]
    qp.loc[positive_mask] = 100.0 * positive_tail.loc[positive_mask] / positive_count.loc[positive_mask]
    return qp


def prepare_qp_indicators(data: pd.DataFrame, params: ExtremeMoveProbabilityConfig) -> pd.DataFrame:
    out = prepare_qp_static_fields(data, (params.return_window,), params)
    return attach_qp_distribution(out, params)


def prepare_qp_static_fields(
    data: pd.DataFrame,
    return_windows: tuple[int, ...] = (2, 3, 5),
    params: ExtremeMoveProbabilityConfig | None = None,
) -> pd.DataFrame:
    """Prepare fields shared by canonical and preregistered QP cells once."""
    params = params or ExtremeMoveProbabilityConfig()
    required = {
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "adjusted_high",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"MR-QP requires explicit adjusted signal and raw execution fields; missing {sorted(missing)}")

    out = data.copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise")
    out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
    if out["symbol"].eq("").any():
        raise ValueError("MR-QP input contains an empty symbol")
    if out.duplicated(["symbol", "date"]).any():
        raise ValueError("MR-QP requires one canonical bar per symbol/date")
    numeric = ["open", "high", "low", "close", "volume", "adjusted_close", "adjusted_high"]
    for column in numeric:
        out[column] = pd.to_numeric(out[column], errors="coerce")
    if out[["open", "close", "adjusted_close", "adjusted_high"]].isna().any().any():
        raise ValueError("MR-QP input contains missing required price values")
    if out[["open", "close", "adjusted_close", "adjusted_high"]].le(0).any().any():
        raise ValueError("MR-QP input contains non-positive required price values")
    if out["volume"].lt(0).any():
        raise ValueError("MR-QP input contains negative volume")

    out = out.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)
    for return_window in sorted(set(int(value) for value in return_windows)):
        if return_window <= 0:
            raise ValueError("QP return windows must be positive")
        out[f"r{return_window}"] = out.groupby("symbol", sort=False)["adjusted_close"].transform(
            lambda series, window=return_window: series.pct_change(window, fill_method=None)
        )
    out[f"sma{params.trend_sma}"] = out.groupby("symbol", sort=False)["adjusted_close"].transform(
        lambda series: series.rolling(params.trend_sma, min_periods=params.trend_sma).mean()
    )
    out["previous_adjusted_high"] = out.groupby("symbol", sort=False)["adjusted_high"].shift(1)
    out["dollar_turnover_close"] = out["close"] * out["volume"]
    out["median_dollar_turnover_20"] = out.groupby("symbol", sort=False)["dollar_turnover_close"].transform(
        lambda series: series.rolling(params.liquidity_window, min_periods=params.liquidity_window).median()
    )

    calendar = pd.Index(sorted(out["date"].dropna().unique()))
    next_map = dict(zip(calendar[:-1], calendar[1:]))
    out["next_session_date"] = out["date"].map(next_map)
    out["signal_observation_time"] = "Close(t)"
    out["earliest_information_availability"] = "After Close(t)"
    out["entry_order_submission_time"] = "After Close(t)"
    out["entry_assumed_fill_time"] = "Open(t+1)"
    out["entry_fill_price_field"] = "open"
    out["exit_signal_observation_time"] = "Close(t)"
    out["exit_order_submission_time"] = "After Close(t)"
    out["exit_assumed_fill_time"] = "Open(t+1)"
    out["exit_fill_price_field"] = "open"
    return out


def attach_qp_distribution(data: pd.DataFrame, params: ExtremeMoveProbabilityConfig) -> pd.DataFrame:
    """Attach the signed empirical-tail probability for one frozen history cell."""
    out = data.copy()
    return_column = f"r{params.return_window}"
    if return_column not in out:
        raise ValueError(f"QP static panel is missing {return_column}")
    out["qp"] = out.groupby("symbol", sort=False)[return_column].transform(
        lambda series: extreme_move_probability(
            series,
            params.history_sessions,
            params.minimum_history_sessions,
        )
    )
    return out


class ExtremeMoveProbabilityQP(StrategyModule):
    name = "mr_qp_a1_source_replication"
    timeframe = "1d"
    required_columns = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
        "adjusted_high",
    ]

    def prepare_indicators(self, data: pd.DataFrame, config: dict) -> pd.DataFrame:
        return prepare_qp_indicators(data, _params_from_config(config))

    def generate_candidates(self, data: pd.DataFrame, config: dict) -> pd.DataFrame:
        params = _params_from_config(config)
        return_column = f"r{params.return_window}"
        trend_column = f"sma{params.trend_sma}"
        liquidity_column = "dollar_turnover_close" if params.liquidity_definition == "LIQ_A" else "median_dollar_turnover_20"
        mask = (
            data[return_column].lt(0)
            & data["qp"].lt(params.qp_threshold)
            & data["adjusted_close"].gt(data[trend_column])
            & data["next_session_date"].notna()
            & data[liquidity_column].notna()
        )
        selected = data.loc[mask].copy()
        if selected.empty:
            return pd.DataFrame(columns=CANDIDATE_COLUMNS)
        selected["score"] = selected[liquidity_column]
        selected = selected.sort_values(["date", "score", "symbol"], ascending=[True, False, True], kind="mergesort")
        selected["rank"] = selected.groupby("date", sort=False).cumcount() + 1
        out = pd.DataFrame(
            {
                "as_of_date": selected["date"].dt.strftime("%Y-%m-%d"),
                "symbol": selected["symbol"],
                "strategy_name": self.name,
                "direction": "long",
                "timeframe": self.timeframe,
                "signal_date": selected["date"].dt.strftime("%Y-%m-%d"),
                "intended_entry_date": selected["next_session_date"].dt.strftime("%Y-%m-%d"),
                "intended_entry_timing": "next_open",
                "rank": selected["rank"].astype(int),
                "score": selected["score"],
                "close": selected["close"],
                "reason": (
                    "negative extreme-move QP below threshold; adjusted close above SMA; "
                    f"ranked by {params.liquidity_definition}"
                ),
                "stop_reference": pd.NA,
                "target_reference": pd.NA,
                "data_warnings": "not-held-at-signal and free-slot gates must be enforced by the portfolio lifecycle",
            }
        )
        return out[CANDIDATE_COLUMNS]

    def rank_candidates(self, candidates: pd.DataFrame, config: dict) -> pd.DataFrame:
        if candidates.empty:
            return candidates.reindex(columns=CANDIDATE_COLUMNS)
        ranked = candidates.sort_values(["signal_date", "score", "symbol"], ascending=[True, False, True], kind="mergesort").copy()
        ranked["rank"] = ranked.groupby("signal_date", sort=False).cumcount() + 1
        return ranked[CANDIDATE_COLUMNS]

    def build_orders(self, candidates: pd.DataFrame, portfolio_state, config: dict) -> pd.DataFrame:
        if candidates.empty:
            return pd.DataFrame(columns=ORDER_COLUMNS)
        orders = candidates.copy()
        orders["order_id"] = [f"MR-QP-A1-{index:08d}" for index in range(1, len(orders) + 1)]
        orders["asset_class"] = "equities"
        orders["order_type"] = "market_on_open"
        orders["entry_reference_price"] = orders["close"]
        orders["stop_price"] = pd.NA
        orders["target_price"] = pd.NA
        orders["sizing_model"] = "ten_percent_equity_slot"
        orders["status"] = "research_candidate_only"
        orders["notes"] = "Signal after Close(t); earliest fill raw Open(t+1); no same-close fill"
        return orders[ORDER_COLUMNS]

    def generate_exit_signals(self, data: pd.DataFrame, config: dict) -> pd.DataFrame:
        selected = data.loc[
            data["adjusted_close"].gt(data["previous_adjusted_high"])
            & data["next_session_date"].notna()
        ].copy()
        if selected.empty:
            return pd.DataFrame(columns=EXIT_SIGNAL_COLUMNS)
        out = pd.DataFrame(
            {
                "strategy_name": self.name,
                "symbol": selected["symbol"],
                "signal_date": selected["date"].dt.strftime("%Y-%m-%d"),
                "signal_observation_time": "Close(t)",
                "earliest_information_availability": "After Close(t)",
                "order_submission_time": "After Close(t)",
                "intended_exit_date": selected["next_session_date"].dt.strftime("%Y-%m-%d"),
                "assumed_fill_time": "Open(t+1)",
                "fill_price_field": "open",
                "reason": "adjusted_close(t) strictly above adjusted_high(t-1)",
            }
        )
        return out[EXIT_SIGNAL_COLUMNS]


def _params_from_config(config: dict[str, Any]) -> ExtremeMoveProbabilityConfig:
    raw = dict(config.get("signals", {}).get("parameters", {}) or {})
    ranking = config.get("ranking", {}) or {}
    portfolio = config.get("portfolio", {}) or {}
    raw.setdefault("liquidity_definition", ranking.get("definition", ranking.get("metric", "LIQ_A")))
    raw.setdefault("maximum_positions", portfolio.get("max_positions", 10))
    raw.setdefault("position_size_pct", portfolio.get("position_size_pct", 10.0))
    allowed = ExtremeMoveProbabilityConfig.__dataclass_fields__.keys()
    return ExtremeMoveProbabilityConfig(**{key: raw[key] for key in allowed if key in raw})

