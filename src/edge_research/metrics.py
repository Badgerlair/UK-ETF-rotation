"""Focused performance metrics for deterministic research parity."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


TRADING_DAYS = 252.0


def performance_metrics(
    daily_equity: pd.DataFrame,
    trades: pd.DataFrame | None = None,
    open_positions: pd.DataFrame | None = None,
) -> dict[str, float | int | str]:
    equity = _normalise_equity(daily_equity)
    if equity.empty:
        return {"start_date": "", "end_date": "", "observations": 0}
    returns = equity["daily_return"].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    curve = equity["equity"].astype(float)
    years = max((equity["date"].iloc[-1] - equity["date"].iloc[0]).days / 365.2425, 1.0 / TRADING_DAYS)
    start_value = float(curve.iloc[0])
    end_value = float(curve.iloc[-1])
    cagr = (end_value / start_value) ** (1.0 / years) - 1.0 if start_value > 0 and end_value >= 0 else float("nan")
    annualised_return = float(returns.mean() * TRADING_DAYS)
    annualised_volatility = float(returns.std(ddof=1) * math.sqrt(TRADING_DAYS)) if len(returns) > 1 else 0.0
    sharpe = annualised_return / annualised_volatility if annualised_volatility > 0 else 0.0
    drawdown = curve / curve.cummax() - 1.0
    metrics: dict[str, float | int | str] = {
        "start_date": equity["date"].iloc[0].strftime("%Y-%m-%d"),
        "end_date": equity["date"].iloc[-1].strftime("%Y-%m-%d"),
        "observations": int(len(equity)),
        "years": years,
        "starting_equity": start_value,
        "ending_equity": end_value,
        "total_return": end_value / start_value - 1.0 if start_value else float("nan"),
        "cagr": cagr,
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "time_in_market": float(equity["number_open_positions"].gt(0).mean()),
        "average_concurrent_positions": float(equity["number_open_positions"].mean()),
        "maximum_concurrent_positions": int(equity["number_open_positions"].max()),
        "capital_utilisation": float((equity["gross_exposure"] / equity["equity"].replace(0, np.nan)).mean()),
        "open_positions_at_end": int(len(open_positions)) if open_positions is not None else 0,
    }
    metrics.update(trade_metrics(trades, years, float(curve.mean()), open_positions))
    return metrics


def trade_metrics(
    trades: pd.DataFrame | None,
    years: float,
    average_equity: float,
    open_positions: pd.DataFrame | None = None,
) -> dict[str, float | int]:
    if trades is None or trades.empty:
        return {"profit_factor": 0.0, "win_rate": 0.0, "trade_count": 0, "trades_per_year": 0.0}
    frame = trades.copy()
    pnl = pd.to_numeric(frame["net_pnl"], errors="coerce").fillna(0.0)
    entry_reference = pd.to_numeric(frame.get("entry_reference_price", frame["entry_price"]), errors="coerce")
    quantity = pd.to_numeric(frame["quantity"], errors="coerce")
    exit_reference = pd.to_numeric(frame.get("exit_reference_price", frame["exit_price"]), errors="coerce")
    positive_pnl = float(pnl[pnl > 0].sum())
    negative_pnl = float(pnl[pnl < 0].sum())
    traded_notional = float((entry_reference.abs() * quantity.abs()).sum() + (exit_reference.abs() * quantity.abs()).sum())
    if open_positions is not None and not open_positions.empty:
        open_entry = pd.to_numeric(open_positions.get("entry_reference_price", open_positions.get("entry_price")), errors="coerce")
        open_quantity = pd.to_numeric(open_positions.get("quantity"), errors="coerce")
        traded_notional += float((open_entry.abs() * open_quantity.abs()).sum())
    return {
        "profit_factor": positive_pnl / abs(negative_pnl) if negative_pnl < 0 else float("inf") if positive_pnl > 0 else 0.0,
        "win_rate": float((pnl > 0).mean()),
        "trade_count": int(len(frame)),
        "trades_per_year": float(len(frame) / years) if years else 0.0,
        "turnover": traded_notional / average_equity / years if average_equity > 0 and years > 0 else 0.0,
    }


def _normalise_equity(daily_equity: pd.DataFrame) -> pd.DataFrame:
    if daily_equity is None or daily_equity.empty:
        return pd.DataFrame()
    frame = daily_equity.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.sort_values("date", kind="mergesort").drop_duplicates("date", keep="last").reset_index(drop=True)
    if "daily_return" not in frame:
        frame["daily_return"] = pd.to_numeric(frame["equity"], errors="coerce").pct_change().fillna(0.0)
    return frame
