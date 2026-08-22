from __future__ import annotations

import math

import pandas as pd

from edge_research.fill_model import DailyFillModel
from edge_research.position import Position, Trade


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value)


def pct_value(value: float | int | None) -> float | None:
    if value is None or is_missing(value):
        return None
    value = float(value)
    return value / 100.0 if value > 1 else value


def create_position(
    order: pd.Series,
    bar: pd.Series,
    config: dict,
    position_id: str,
    quantity: float,
    fill_model: DailyFillModel,
    entry_commission: float = 0.0,
) -> tuple[Position, float]:
    direction = str(order["direction"])
    entry_timing = str(config.get("execution_model", {}).get("entry_timing", "next_open"))
    fill = fill_model.entry_fill(bar, direction, entry_timing, quantity)
    initial_stop = initial_stop_price(order, fill.fill_price, direction, config)
    target = none_if_missing(order.get("target_price"))
    position = Position(
        position_id=position_id,
        strategy_name=str(order["strategy_name"]),
        symbol=str(order["symbol"]),
        direction=direction,
        entry_signal_date=str(order["signal_date"]),
        entry_date=fill.date,
        entry_price=fill.fill_price,
        quantity=float(quantity),
        entry_reference_price=fill.reference_price,
        entry_slippage=fill.slippage_cost,
        entry_commission=float(entry_commission),
        last_mark_price=float(bar["close"]),
        last_mark_date=str(bar["date"]),
        initial_stop=initial_stop,
        trailing_stop=None,
        target_price=target,
        time_stop_bars=none_if_missing(config.get("risk", {}).get("time_stop_bars")),
        highest_close=float(bar["close"]),
        highest_high=float(bar["high"]),
        lowest_close=float(bar["close"]),
        lowest_low=float(bar["low"]),
    )
    update_trailing_stop(position, bar, config)
    return position, fill.slippage_cost


def initial_stop_price(order: pd.Series, entry_price: float, direction: str, config: dict) -> float | None:
    order_stop = none_if_missing(order.get("stop_price"))
    if order_stop is not None:
        return float(order_stop)
    rule = config.get("risk", {}).get("initial_stop", {}) or {}
    stop_type = str(rule.get("type", "none")).lower()
    value = rule.get("value")
    if stop_type in {"none", "", "null"}:
        return None
    if stop_type in {"percent", "pct"}:
        pct = pct_value(value)
        if pct is None:
            return None
        return entry_price * (1 - pct) if direction == "long" else entry_price * (1 + pct)
    raise ValueError(f"Initial stop type requires order stop_reference or prepared ATR support: {stop_type}")


def update_trailing_stop(position: Position, bar: pd.Series, config: dict) -> None:
    close = float(bar["close"])
    high = float(bar["high"])
    low = float(bar["low"])
    position.highest_close = max(position.highest_close or close, close)
    position.highest_high = max(position.highest_high or high, high)
    position.lowest_close = min(position.lowest_close or close, close)
    position.lowest_low = min(position.lowest_low or low, low)
    rule = config.get("risk", {}).get("trailing_stop", {}) or {}
    stop_type = str(rule.get("type", "none")).lower()
    value = rule.get("value")
    if stop_type in {"none", "", "null"}:
        return
    if stop_type in {"percent", "pct"}:
        pct = pct_value(value)
        if pct is None:
            return
        if position.direction == "long":
            candidate = (position.highest_close or close) * (1 - pct)
            position.trailing_stop = max(position.trailing_stop, candidate) if position.trailing_stop is not None else candidate
        else:
            candidate = (position.lowest_close or close) * (1 + pct)
            position.trailing_stop = min(position.trailing_stop, candidate) if position.trailing_stop is not None else candidate
        return
    if stop_type in {"atr", "atr_multiple"}:
        return
    raise ValueError(f"Unsupported trailing stop type: {stop_type}")


def exit_signal(position: Position, bar: pd.Series, config: dict) -> tuple[str, float | None, str] | None:
    stop = position.stop_price()
    target = position.target_price
    if position.direction == "long":
        stop_hit = stop is not None and float(bar["low"]) <= stop
        target_hit = target is not None and float(bar["high"]) >= target
    else:
        stop_hit = stop is not None and float(bar["high"]) >= stop
        target_hit = target is not None and float(bar["low"]) <= target
    if stop_hit:
        return "stop", stop, "stop_intraday"
    if target_hit:
        return "target", target, "stop_intraday"
    time_stop = position.time_stop_bars
    if time_stop is not None and position.bars_held >= int(time_stop):
        exit_timing = str(config.get("execution_model", {}).get("exit_timing", "same_close"))
        if exit_timing in {"time_stop_placeholder", "time_stop_or_next_open_placeholder"}:
            exit_timing = "same_close"
        return "time_stop", None, exit_timing
    return None


def close_position(
    position: Position,
    bar: pd.Series,
    reason: str,
    reference_price: float | None,
    timing: str,
    fill_model: DailyFillModel,
    commission: float,
    trade_id: str,
) -> Trade:
    fill = fill_model.exit_fill(bar, position.direction, timing, position.quantity, reference_price)
    entry_reference = position.entry_reference_price if position.entry_reference_price is not None else position.entry_price
    if position.direction == "long":
        price_gross = (fill.reference_price - entry_reference) * position.quantity
    else:
        price_gross = (entry_reference - fill.reference_price) * position.quantity
    gross = price_gross + position.dividend_income
    total_commission = float(position.entry_commission) + float(commission)
    total_slippage = float(position.entry_slippage) + float(fill.slippage_cost)
    net = gross - total_commission - total_slippage
    risk_dollars = position.risk_per_share() * position.quantity
    realised_r = net / risk_dollars if risk_dollars else 0.0
    position.status = "closed"
    position.exit_date = fill.date
    position.exit_price = fill.fill_price
    position.exit_reason = reason
    position.realised_pnl = net
    position.realised_R = realised_r
    return Trade(
        trade_id=trade_id,
        strategy_name=position.strategy_name,
        symbol=position.symbol,
        direction=position.direction,
        entry_signal_date=position.entry_signal_date,
        entry_date=position.entry_date,
        entry_price=position.entry_price,
        exit_date=fill.date,
        exit_price=fill.fill_price,
        exit_reason=reason,
        quantity=position.quantity,
        gross_pnl=gross,
        commission=total_commission,
        slippage=total_slippage,
        net_pnl=net,
        R=realised_r,
        bars_held=position.bars_held,
        initial_stop=position.initial_stop,
        final_stop=position.stop_price(),
        target_price=position.target_price,
        entry_reference_price=entry_reference,
        exit_reference_price=fill.reference_price,
        dividend_income=position.dividend_income,
    )


def apply_split_to_position(position: Position, split_factor: float) -> None:
    """Move an overnight holding onto the post-split executable share scale."""
    factor = float(split_factor)
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError(f"Invalid split factor for open position: {split_factor}")
    if factor == 1.0:
        return
    position.quantity *= factor
    for field in (
        "entry_price",
        "entry_reference_price",
        "initial_stop",
        "trailing_stop",
        "target_price",
        "highest_close",
        "highest_high",
        "lowest_close",
        "lowest_low",
        "last_mark_price",
    ):
        value = getattr(position, field)
        if value is not None:
            setattr(position, field, float(value) / factor)


def none_if_missing(value):
    return None if is_missing(value) else value

