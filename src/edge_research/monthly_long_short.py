"""Causal raw-open accounting for monthly signed research portfolios.

This is a focused extension of the admitted ``CLOSE_OBSERVED_NEXT_OPEN`` and
``SPLIT_CONTINUOUS_SIGNAL_RAW_OPEN_EXECUTION`` capabilities.  It supports the
variable equal weights and signed books required by MR-RESID-A1 without
altering the existing daily strategy simulator or any frozen experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


EXECUTION_COLUMNS = [
    "execution_id",
    "event_id",
    "timing_variant",
    "formation_date",
    "intended_rebalance_date",
    "fill_date",
    "symbol",
    "portfolio_leg",
    "action",
    "transition",
    "old_quantity",
    "target_quantity",
    "delta_quantity",
    "fill_raw_open",
    "signed_executed_notional",
    "executed_notional",
    "cost_bps_per_leg",
    "cost",
    "target_weight",
    "target_notional",
    "anchor_equity",
    "carry_sessions",
    "terminal_proxy_fill",
    "reason",
]

DAILY_EQUITY_COLUMNS = [
    "date",
    "cash",
    "long_market_value",
    "short_market_value",
    "net_market_value",
    "equity",
    "gross_exposure",
    "net_exposure",
    "gross_exposure_ratio",
    "net_exposure_ratio",
    "number_open_positions",
    "cumulative_cost",
    "daily_return",
    "drawdown",
]

DIAGNOSTIC_COLUMNS = ["date", "symbol", "event_type", "severity", "message"]


class IdentityContinuityError(RuntimeError):
    """A queued order or holding crossed the admitted identity tolerance."""


@dataclass(frozen=True)
class PreparedSignedMarketData:
    data: pd.DataFrame
    bar_lookup: dict
    dates: tuple[str, ...]


@dataclass(frozen=True)
class SignedMonthlySimulationResult:
    executions: pd.DataFrame
    daily_equity: pd.DataFrame
    diagnostics: pd.DataFrame
    event_audit: pd.DataFrame
    open_positions: pd.DataFrame
    pending_targets: pd.DataFrame


@dataclass
class _SignedPosition:
    symbol: str
    quantity: float
    last_mark: float
    last_mark_date: str


@dataclass
class _PendingTarget:
    symbol: str
    target_weight: float
    target_notional: float
    anchor_equity: float
    intended_date: str
    formation_date: str
    timing_variant: str
    event_id: str
    portfolio_leg: str
    reason: str


def prepare_signed_market_data(
    data: pd.DataFrame,
    *,
    calendar: list | tuple | pd.Series | pd.DatetimeIndex | None = None,
) -> PreparedSignedMarketData:
    required = {"date", "symbol", "open", "close"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Signed monthly market data are missing fields: {sorted(missing)}")
    frame = data.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    if "split_factor_at_open" not in frame:
        frame["split_factor_at_open"] = 1.0
    if "terminal_proxy_only" not in frame:
        frame["terminal_proxy_only"] = False
    else:
        frame["terminal_proxy_only"] = frame["terminal_proxy_only"].fillna(False).astype(bool)
    for column in ("open", "close", "split_factor_at_open"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    invalid = (
        frame["symbol"].eq("")
        | frame[["open", "close", "split_factor_at_open"]].isna().any(axis=1)
        | frame[["open", "close", "split_factor_at_open"]].le(0).any(axis=1)
    )
    if invalid.any():
        raise ValueError("Signed monthly market data contain invalid symbols, prices, or split factors")
    if frame.duplicated(["date", "symbol"]).any():
        raise ValueError("Signed monthly market data require one bar per symbol/date")
    frame = frame.sort_values(["date", "symbol"], kind="mergesort").reset_index(drop=True)
    if calendar is None:
        dates = tuple(sorted(frame["date"].unique()))
    else:
        dates = tuple(
            pd.DatetimeIndex(pd.to_datetime(calendar, errors="raise"))
            .normalize()
            .unique()
            .sort_values()
            .strftime("%Y-%m-%d")
        )
    return PreparedSignedMarketData(
        data=frame,
        bar_lookup={(str(row.date), str(row.symbol)): row for row in frame.itertuples(index=False)},
        dates=dates,
    )


class SignedMonthlyRebalancer:
    """Execute precomputed signed weights at raw monthly opens.

    Target notional is fixed from equity marked at the intended rebalance open.
    A missing symbol bar queues that fixed notional until its next available raw
    open.  Costs are charged exactly once on each absolute quantity delta.
    """

    def __init__(
        self,
        *,
        initial_equity: float = 1_000_000.0,
        cost_bps_per_leg: float = 10.0,
        maximum_carry_sessions: int | None = None,
    ):
        if initial_equity <= 0:
            raise ValueError("initial_equity must be positive")
        if cost_bps_per_leg < 0:
            raise ValueError("cost_bps_per_leg cannot be negative")
        if maximum_carry_sessions is not None and maximum_carry_sessions < 1:
            raise ValueError("maximum_carry_sessions must be positive when supplied")
        self.initial_equity = float(initial_equity)
        self.cost_bps_per_leg = float(cost_bps_per_leg)
        self.maximum_carry_sessions = maximum_carry_sessions

    def simulate(
        self,
        targets: pd.DataFrame,
        events: pd.DataFrame,
        market: pd.DataFrame | PreparedSignedMarketData,
        *,
        calendar: list | tuple | pd.Series | pd.DatetimeIndex | None = None,
    ) -> SignedMonthlySimulationResult:
        prepared = market if isinstance(market, PreparedSignedMarketData) else prepare_signed_market_data(market, calendar=calendar)
        event_frame = self._normalise_events(events)
        target_frame = self._normalise_targets(targets, event_frame)
        if event_frame.empty:
            return self._empty_result()
        event_lookup = {str(row.rebalance_date): row for row in event_frame.itertuples(index=False)}
        target_lookup = {
            str(date): group.sort_values("symbol", kind="mergesort")
            for date, group in target_frame.groupby("rebalance_date", sort=False)
        }
        first_event_date = str(event_frame["rebalance_date"].min())
        final_event_date = str(event_frame["rebalance_date"].max())
        if first_event_date not in prepared.dates:
            raise ValueError("Rebalance dates must exist in the supplied causal session calendar")
        first_event_position = prepared.dates.index(first_event_date)
        dates = list(prepared.dates[max(0, first_event_position - 1) :])

        cash = self.initial_equity
        positions: dict[str, _SignedPosition] = {}
        pending: dict[str, _PendingTarget] = {}
        executions: list[dict] = []
        diagnostics: list[dict] = []
        states: list[dict] = []
        event_audit: list[dict] = []
        previous_equity = self.initial_equity
        peak_equity = self.initial_equity
        cumulative_cost = 0.0
        calendar_positions = {date: index for index, date in enumerate(prepared.dates)}

        for current_date in dates:
            # Apply overnight split/reverse-split quantity changes before any
            # target uses this session's raw executable open.
            for symbol, position in list(positions.items()):
                bar = prepared.bar_lookup.get((current_date, symbol))
                if bar is None:
                    continue
                factor = float(getattr(bar, "split_factor_at_open", 1.0) or 1.0)
                if factor != 1.0:
                    old_quantity = position.quantity
                    position.quantity *= factor
                    diagnostics.append(
                        _diagnostic(
                            current_date,
                            symbol,
                            "position_split_adjustment",
                            "info",
                            f"quantity {old_quantity:.12g} -> {position.quantity:.12g}; factor={factor:.12g}",
                        )
                    )

            # The disclosed terminal proxy is usable only to settle an already
            # open holding; it can never create a new position.
            for symbol, position in list(positions.items()):
                bar = prepared.bar_lookup.get((current_date, symbol))
                if bar is None or not bool(getattr(bar, "terminal_proxy_only", False)):
                    continue
                terminal_target = _PendingTarget(
                    symbol=symbol,
                    target_weight=0.0,
                    target_notional=0.0,
                    anchor_equity=self._equity_at_open(cash, positions, prepared.bar_lookup, current_date),
                    intended_date=current_date,
                    formation_date=position.last_mark_date,
                    timing_variant="TERMINAL_PROXY",
                    event_id=f"TERMINAL-{current_date}-{symbol}",
                    portfolio_leg="LONG" if position.quantity > 0 else "SHORT",
                    reason="TERMINAL_LAST_OBSERVED_CLOSE_PROXY",
                )
                cash, cost = self._execute_target(
                    terminal_target,
                    current_date,
                    bar,
                    cash,
                    positions,
                    executions,
                    calendar_positions,
                    terminal_proxy=True,
                )
                cumulative_cost += cost
                pending.pop(symbol, None)
                diagnostics.append(
                    _diagnostic(
                        current_date,
                        symbol,
                        "terminal_proxy_settlement",
                        "warning",
                        "No governed terminal proceeds were available; holding settled at the disclosed last-close proxy.",
                    )
                )

            event = event_lookup.get(current_date)
            if event is not None:
                # A newly observed formation supersedes any older unfilled
                # target.  Existing holdings absent from the new target receive
                # an explicit zero target.
                for stale in list(pending.values()):
                    diagnostics.append(
                        _diagnostic(
                            current_date,
                            stale.symbol,
                            "pending_target_superseded",
                            "warning",
                            f"Unfilled target from {stale.intended_date} superseded by {current_date} rebalance.",
                        )
                    )
                pending = {}
                current_targets = target_lookup.get(current_date, target_frame.iloc[0:0])
                target_by_symbol = {str(row.symbol): row for row in current_targets.itertuples(index=False)}
                anchor_equity = self._equity_at_open(cash, positions, prepared.bar_lookup, current_date)
                symbols = sorted(set(positions).union(target_by_symbol))
                event_cost_before = cumulative_cost
                execution_count_before = len(executions)
                for symbol in symbols:
                    target_row = target_by_symbol.get(symbol)
                    weight = float(getattr(target_row, "target_weight", 0.0)) if target_row is not None else 0.0
                    leg = str(getattr(target_row, "portfolio_leg", "FLAT")) if target_row is not None else "FLAT"
                    target = _PendingTarget(
                        symbol=symbol,
                        target_weight=weight,
                        target_notional=weight * anchor_equity,
                        anchor_equity=anchor_equity,
                        intended_date=current_date,
                        formation_date=str(event.formation_date),
                        timing_variant=str(event.timing_variant),
                        event_id=str(event.event_id),
                        portfolio_leg=leg,
                        reason=str(event.event_type),
                    )
                    bar = prepared.bar_lookup.get((current_date, symbol))
                    if bar is None:
                        pending[symbol] = target
                        diagnostics.append(
                            _diagnostic(
                                current_date,
                                symbol,
                                "next_open_target_carried",
                                "warning",
                                "No executable raw-open bar; fixed target notional remains queued.",
                            )
                        )
                        continue
                    if bool(getattr(bar, "terminal_proxy_only", False)):
                        if symbol in positions:
                            target.target_weight = 0.0
                            target.target_notional = 0.0
                            target.reason = "TERMINAL_LAST_OBSERVED_CLOSE_PROXY"
                        else:
                            diagnostics.append(
                                _diagnostic(
                                    current_date,
                                    symbol,
                                    "terminal_proxy_entry_rejected",
                                    "warning",
                                    "Terminal proxy is not an executable entry observation.",
                                )
                            )
                            continue
                    cash, cost = self._execute_target(
                        target,
                        current_date,
                        bar,
                        cash,
                        positions,
                        executions,
                        calendar_positions,
                        terminal_proxy=bool(getattr(bar, "terminal_proxy_only", False)),
                    )
                    cumulative_cost += cost
                event_audit.append(
                    {
                        "event_id": str(event.event_id),
                        "timing_variant": str(event.timing_variant),
                        "formation_date": str(event.formation_date),
                        "rebalance_date": current_date,
                        "event_type": str(event.event_type),
                        "anchor_equity": anchor_equity,
                        "target_count": int(len(current_targets)),
                        "target_gross_weight": float(current_targets["target_weight"].abs().sum()) if not current_targets.empty else 0.0,
                        "target_net_weight": float(current_targets["target_weight"].sum()) if not current_targets.empty else 0.0,
                        "executions": int(len(executions) - execution_count_before),
                        "queued_targets": int(len(pending)),
                        "event_cost": float(cumulative_cost - event_cost_before),
                    }
                )
            elif pending:
                for symbol, target in sorted(list(pending.items())):
                    carry_sessions = calendar_positions[current_date] - calendar_positions[target.intended_date]
                    if self.maximum_carry_sessions is not None and carry_sessions > self.maximum_carry_sessions:
                        raise IdentityContinuityError(
                            "TERMINAL_OR_IDENTITY_EVENT_REQUIRES_RESOLUTION: "
                            f"{symbol} target from {target.intended_date} remained unfilled for "
                            f"{carry_sessions} sessions"
                        )
                    bar = prepared.bar_lookup.get((current_date, symbol))
                    if bar is None:
                        continue
                    if bool(getattr(bar, "terminal_proxy_only", False)) and symbol not in positions:
                        diagnostics.append(
                            _diagnostic(
                                current_date,
                                symbol,
                                "terminal_proxy_entry_rejected",
                                "warning",
                                "Carried entry reached only a terminal proxy and was cancelled.",
                            )
                        )
                        pending.pop(symbol, None)
                        continue
                    if bool(getattr(bar, "terminal_proxy_only", False)):
                        target.target_weight = 0.0
                        target.target_notional = 0.0
                        target.reason = "TERMINAL_LAST_OBSERVED_CLOSE_PROXY"
                    cash, cost = self._execute_target(
                        target,
                        current_date,
                        bar,
                        cash,
                        positions,
                        executions,
                        calendar_positions,
                        terminal_proxy=bool(getattr(bar, "terminal_proxy_only", False)),
                    )
                    cumulative_cost += cost
                    pending.pop(symbol, None)

            for symbol, position in list(positions.items()):
                bar = prepared.bar_lookup.get((current_date, symbol))
                if bar is not None:
                    position.last_mark = float(bar.close)
                    position.last_mark_date = current_date
                elif self.maximum_carry_sessions is not None:
                    stale_sessions = calendar_positions[current_date] - calendar_positions[position.last_mark_date]
                    if stale_sessions > self.maximum_carry_sessions:
                        raise IdentityContinuityError(
                            "TERMINAL_OR_IDENTITY_EVENT_REQUIRES_RESOLUTION: "
                            f"{symbol} position has no same-identity observation for {stale_sessions} sessions"
                        )
            long_value, short_value, net_value = self._market_values(positions)
            equity = cash + net_value
            peak_equity = max(peak_equity, equity)
            daily_return = equity / previous_equity - 1.0 if previous_equity else np.nan
            states.append(
                {
                    "date": current_date,
                    "cash": cash,
                    "long_market_value": long_value,
                    "short_market_value": short_value,
                    "net_market_value": net_value,
                    "equity": equity,
                    "gross_exposure": long_value + short_value,
                    "net_exposure": net_value,
                    "gross_exposure_ratio": (long_value + short_value) / equity if equity else np.nan,
                    "net_exposure_ratio": net_value / equity if equity else np.nan,
                    "number_open_positions": len(positions),
                    "cumulative_cost": cumulative_cost,
                    "daily_return": daily_return,
                    "drawdown": equity / peak_equity - 1.0 if peak_equity else np.nan,
                }
            )
            previous_equity = equity
            if current_date >= final_event_date and not positions and not pending:
                break

        open_positions = pd.DataFrame(
            [
                {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "last_mark": position.last_mark,
                    "last_mark_date": position.last_mark_date,
                    "signed_market_value": position.quantity * position.last_mark,
                }
                for position in sorted(positions.values(), key=lambda item: item.symbol)
            ]
        )
        pending_frame = pd.DataFrame([vars(item) for item in sorted(pending.values(), key=lambda item: item.symbol)])
        return SignedMonthlySimulationResult(
            executions=pd.DataFrame(executions, columns=EXECUTION_COLUMNS),
            daily_equity=pd.DataFrame(states, columns=DAILY_EQUITY_COLUMNS),
            diagnostics=pd.DataFrame(diagnostics, columns=DIAGNOSTIC_COLUMNS),
            event_audit=pd.DataFrame(event_audit),
            open_positions=open_positions,
            pending_targets=pending_frame,
        )

    def _normalise_events(self, events: pd.DataFrame) -> pd.DataFrame:
        required = {"event_id", "timing_variant", "formation_date", "rebalance_date", "event_type"}
        missing = required.difference(events.columns)
        if missing:
            raise ValueError(f"Monthly rebalance events are missing fields: {sorted(missing)}")
        frame = events.copy()
        frame["formation_date"] = pd.to_datetime(frame["formation_date"], errors="raise").dt.strftime("%Y-%m-%d")
        frame["rebalance_date"] = pd.to_datetime(frame["rebalance_date"], errors="raise").dt.strftime("%Y-%m-%d")
        if frame["rebalance_date"].duplicated().any():
            raise ValueError("Monthly rebalance events require one event per date")
        if not (pd.to_datetime(frame["rebalance_date"]) > pd.to_datetime(frame["formation_date"])).all():
            raise ValueError("Causal monthly targets must execute strictly after formation close")
        return frame.sort_values("rebalance_date", kind="mergesort").reset_index(drop=True)

    def _normalise_targets(self, targets: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
        required = {"rebalance_date", "symbol", "portfolio_leg", "target_weight"}
        missing = required.difference(targets.columns)
        if missing:
            raise ValueError(f"Monthly signed targets are missing fields: {sorted(missing)}")
        frame = targets.copy()
        frame["rebalance_date"] = pd.to_datetime(frame["rebalance_date"], errors="raise").dt.strftime("%Y-%m-%d")
        frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
        frame["target_weight"] = pd.to_numeric(frame["target_weight"], errors="coerce")
        if frame["symbol"].eq("").any() or frame["target_weight"].isna().any():
            raise ValueError("Monthly signed targets contain an invalid symbol or weight")
        if frame.duplicated(["rebalance_date", "symbol"]).any():
            raise ValueError("Monthly signed targets require one target per symbol/event")
        event_dates = set(events["rebalance_date"])
        if not set(frame["rebalance_date"]).issubset(event_dates):
            raise ValueError("Every target date must have a registered rebalance event")
        return frame.sort_values(["rebalance_date", "symbol"], kind="mergesort").reset_index(drop=True)

    def _equity_at_open(self, cash: float, positions: dict[str, _SignedPosition], lookup: dict, date: str) -> float:
        market_value = 0.0
        for symbol, position in positions.items():
            bar = lookup.get((date, symbol))
            mark = float(bar.open) if bar is not None else position.last_mark
            market_value += position.quantity * mark
        return cash + market_value

    def _execute_target(
        self,
        target: _PendingTarget,
        current_date: str,
        bar,
        cash: float,
        positions: dict[str, _SignedPosition],
        executions: list[dict],
        calendar_positions: dict[str, int],
        *,
        terminal_proxy: bool,
    ) -> tuple[float, float]:
        price = float(bar.open)
        position = positions.get(target.symbol)
        old_quantity = float(position.quantity) if position is not None else 0.0
        target_quantity = float(target.target_notional / price) if target.target_notional else 0.0
        if terminal_proxy:
            target_quantity = 0.0
        delta_quantity = target_quantity - old_quantity
        if abs(delta_quantity) <= 1e-12:
            if position is not None:
                position.last_mark = price
                position.last_mark_date = current_date
            return cash, 0.0
        signed_notional = delta_quantity * price
        executed_notional = abs(signed_notional)
        cost = executed_notional * self.cost_bps_per_leg / 10_000.0
        cash -= signed_notional + cost
        transition = _transition(old_quantity, target_quantity)
        if abs(target_quantity) <= 1e-12:
            positions.pop(target.symbol, None)
        else:
            positions[target.symbol] = _SignedPosition(
                symbol=target.symbol,
                quantity=target_quantity,
                last_mark=price,
                last_mark_date=current_date,
            )
        executions.append(
            {
                "execution_id": f"MR-RESID-A1-E-{len(executions) + 1:09d}",
                "event_id": target.event_id,
                "timing_variant": target.timing_variant,
                "formation_date": target.formation_date,
                "intended_rebalance_date": target.intended_date,
                "fill_date": current_date,
                "symbol": target.symbol,
                "portfolio_leg": target.portfolio_leg,
                "action": "BUY" if delta_quantity > 0 else "SELL",
                "transition": transition,
                "old_quantity": old_quantity,
                "target_quantity": target_quantity,
                "delta_quantity": delta_quantity,
                "fill_raw_open": price,
                "signed_executed_notional": signed_notional,
                "executed_notional": executed_notional,
                "cost_bps_per_leg": self.cost_bps_per_leg,
                "cost": cost,
                "target_weight": target.target_weight,
                "target_notional": target.target_notional,
                "anchor_equity": target.anchor_equity,
                "carry_sessions": int(calendar_positions[current_date] - calendar_positions[target.intended_date]),
                "terminal_proxy_fill": bool(terminal_proxy),
                "reason": target.reason,
            }
        )
        return cash, cost

    @staticmethod
    def _market_values(positions: dict[str, _SignedPosition]) -> tuple[float, float, float]:
        values = [position.quantity * position.last_mark for position in positions.values()]
        long_value = float(sum(value for value in values if value > 0))
        short_value = float(sum(-value for value in values if value < 0))
        return long_value, short_value, long_value - short_value

    @staticmethod
    def _empty_result() -> SignedMonthlySimulationResult:
        return SignedMonthlySimulationResult(
            executions=pd.DataFrame(columns=EXECUTION_COLUMNS),
            daily_equity=pd.DataFrame(columns=DAILY_EQUITY_COLUMNS),
            diagnostics=pd.DataFrame(columns=DIAGNOSTIC_COLUMNS),
            event_audit=pd.DataFrame(),
            open_positions=pd.DataFrame(),
            pending_targets=pd.DataFrame(),
        )


def monthly_return_series(
    daily_equity: pd.DataFrame,
    *,
    initial_equity: float,
    active_start: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    if daily_equity.empty:
        return pd.DataFrame(columns=["month", "month_end_date", "ending_equity", "monthly_return"])
    frame = daily_equity.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    if active_start is not None:
        frame = frame.loc[frame["date"].ge(pd.Timestamp(active_start))].copy()
    frame["month"] = frame["date"].dt.to_period("M")
    month_end = frame.sort_values("date", kind="mergesort").groupby("month", sort=True).tail(1).copy()
    previous = pd.to_numeric(month_end["equity"], errors="coerce").shift(1)
    if len(previous):
        previous.iloc[0] = float(initial_equity)
    month_end["monthly_return"] = pd.to_numeric(month_end["equity"], errors="coerce") / previous - 1.0
    return month_end.rename(columns={"date": "month_end_date", "equity": "ending_equity"})[
        ["month", "month_end_date", "ending_equity", "monthly_return"]
    ].reset_index(drop=True)


def signed_portfolio_metrics(
    result: SignedMonthlySimulationResult,
    *,
    initial_equity: float,
    active_start: str | pd.Timestamp,
    active_end: str | pd.Timestamp,
) -> dict[str, float | int | str]:
    daily = result.daily_equity.copy()
    daily["date"] = pd.to_datetime(daily["date"], errors="raise")
    daily = daily.loc[daily["date"].between(pd.Timestamp(active_start), pd.Timestamp(active_end))].copy()
    if daily.empty:
        return {"observations": 0}
    returns = pd.to_numeric(daily["daily_return"], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    ending_equity = float(daily["equity"].iloc[-1])
    years = max((pd.Timestamp(active_end) - pd.Timestamp(active_start)).days / 365.2425, 1.0 / 252.0)
    cagr = (ending_equity / initial_equity) ** (1.0 / years) - 1.0 if ending_equity > 0 else np.nan
    annualised_return = float(returns.mean() * 252.0) if len(returns) else 0.0
    annualised_volatility = float(returns.std(ddof=1) * math.sqrt(252.0)) if len(returns) > 1 else 0.0
    sharpe = annualised_return / annualised_volatility if annualised_volatility > 0 else np.nan
    downside_deviation = float(np.sqrt(np.mean(np.minimum(returns.to_numpy(dtype=float), 0.0) ** 2)) * math.sqrt(252.0)) if len(returns) else 0.0
    sortino = annualised_return / downside_deviation if downside_deviation > 0 else np.nan
    curve_with_initial = pd.Series([float(initial_equity), *pd.to_numeric(daily["equity"], errors="coerce").tolist()])
    drawdown = curve_with_initial / curve_with_initial.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 and np.isfinite(cagr) else np.nan
    monthly = monthly_return_series(daily, initial_equity=initial_equity, active_start=active_start)
    month_returns = pd.to_numeric(monthly["monthly_return"], errors="coerce").dropna()
    gains = float(month_returns[month_returns > 0].sum())
    losses = float(month_returns[month_returns < 0].sum())
    average_equity = float(pd.to_numeric(daily["equity"], errors="coerce").mean())
    executions = result.executions.copy()
    if not executions.empty:
        executions["fill_date"] = pd.to_datetime(executions["fill_date"], errors="raise")
        executions = executions.loc[executions["fill_date"].between(pd.Timestamp(active_start), pd.Timestamp(active_end))]
    traded_notional = float(pd.to_numeric(executions.get("executed_notional", pd.Series(dtype=float)), errors="coerce").sum())
    formation_rebalances = int(
        result.event_audit.get("event_type", pd.Series(dtype=str)).astype(str).eq("FORMATION_REBALANCE").sum()
    )
    return {
        "start_date": pd.Timestamp(active_start).strftime("%Y-%m-%d"),
        "end_date": pd.Timestamp(active_end).strftime("%Y-%m-%d"),
        "observations": int(len(daily)),
        "years": years,
        "starting_equity": float(initial_equity),
        "ending_equity": ending_equity,
        "total_return": ending_equity / initial_equity - 1.0,
        "cagr": float(cagr),
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": max_drawdown,
        "calmar": float(calmar),
        "average_monthly_return": float(month_returns.mean()) if len(month_returns) else np.nan,
        "monthly_volatility": float(month_returns.std(ddof=1)) if len(month_returns) > 1 else 0.0,
        "monthly_win_rate": float((month_returns > 0).mean()) if len(month_returns) else np.nan,
        "monthly_profit_factor": gains / abs(losses) if losses < 0 else np.inf if gains > 0 else 0.0,
        "best_month": float(month_returns.max()) if len(month_returns) else np.nan,
        "best_month_date": str(monthly.loc[monthly["monthly_return"].idxmax(), "month"]) if len(month_returns) else "",
        "worst_month": float(month_returns.min()) if len(month_returns) else np.nan,
        "worst_month_date": str(monthly.loc[monthly["monthly_return"].idxmin(), "month"]) if len(month_returns) else "",
        "annual_turnover": traded_notional / average_equity / years if average_equity > 0 else np.nan,
        "average_monthly_turnover": traded_notional / average_equity / max(len(month_returns), 1) if average_equity > 0 else np.nan,
        "executed_notional": traded_notional,
        "execution_count": int(len(executions)),
        "rebalance_count": formation_rebalances,
        "average_gross_exposure": float(pd.to_numeric(daily["gross_exposure_ratio"], errors="coerce").mean()),
        "average_net_exposure": float(pd.to_numeric(daily["net_exposure_ratio"], errors="coerce").mean()),
        "average_long_exposure": float((pd.to_numeric(daily["long_market_value"], errors="coerce") / pd.to_numeric(daily["equity"], errors="coerce")).mean()),
        "average_short_exposure": float((pd.to_numeric(daily["short_market_value"], errors="coerce") / pd.to_numeric(daily["equity"], errors="coerce")).mean()),
        "capital_utilisation": float(pd.to_numeric(daily["gross_exposure"], errors="coerce").gt(0).mean()),
        "total_cost": float(pd.to_numeric(executions.get("cost", pd.Series(dtype=float)), errors="coerce").sum()),
        "terminal_proxy_executions": int(executions.get("terminal_proxy_fill", pd.Series(dtype=bool)).astype(bool).sum()),
        "open_positions_at_end": int(len(result.open_positions)),
        "pending_targets_at_end": int(len(result.pending_targets)),
    }


def drawdown_periods(daily_equity: pd.DataFrame, *, initial_equity: float) -> pd.DataFrame:
    """Return deterministic peak/trough/recovery records for every drawdown."""

    if daily_equity.empty:
        return pd.DataFrame(columns=["peak_date", "start_date", "trough_date", "recovery_date", "end_date", "maximum_drawdown", "duration_days", "recovered"])
    frame = daily_equity.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    equity = pd.to_numeric(frame["equity"], errors="coerce").to_numpy(dtype=float)
    dates = frame["date"].tolist()
    peak_value = float(initial_equity)
    peak_date = dates[0]
    in_drawdown = False
    start_date = None
    trough_date = None
    trough_drawdown = 0.0
    rows: list[dict] = []
    for date, value in zip(dates, equity):
        if value >= peak_value:
            if in_drawdown:
                rows.append(
                    _drawdown_row(peak_date, start_date, trough_date, date, date, trough_drawdown, True)
                )
                in_drawdown = False
            peak_value = float(value)
            peak_date = date
            continue
        drawdown = value / peak_value - 1.0
        if not in_drawdown:
            in_drawdown = True
            start_date = date
            trough_date = date
            trough_drawdown = float(drawdown)
        elif drawdown < trough_drawdown:
            trough_date = date
            trough_drawdown = float(drawdown)
    if in_drawdown:
        rows.append(_drawdown_row(peak_date, start_date, trough_date, pd.NaT, dates[-1], trough_drawdown, False))
    return pd.DataFrame(rows).sort_values("maximum_drawdown", kind="mergesort").reset_index(drop=True)


def _transition(old_quantity: float, target_quantity: float) -> str:
    old_sign = int(np.sign(old_quantity))
    new_sign = int(np.sign(target_quantity))
    if old_sign == 0 and new_sign > 0:
        return "OPEN_LONG"
    if old_sign == 0 and new_sign < 0:
        return "OPEN_SHORT"
    if old_sign > 0 and new_sign == 0:
        return "CLOSE_LONG"
    if old_sign < 0 and new_sign == 0:
        return "CLOSE_SHORT"
    if old_sign != new_sign:
        return "CROSS_SIGN"
    if abs(target_quantity) > abs(old_quantity):
        return "INCREASE_LONG" if new_sign > 0 else "INCREASE_SHORT"
    if abs(target_quantity) < abs(old_quantity):
        return "REDUCE_LONG" if new_sign > 0 else "REDUCE_SHORT"
    return "RESIZE"


def _diagnostic(date: str, symbol: str, event_type: str, severity: str, message: str) -> dict:
    return {
        "date": str(date),
        "symbol": str(symbol),
        "event_type": str(event_type),
        "severity": str(severity),
        "message": str(message),
    }


def _drawdown_row(peak_date, start_date, trough_date, recovery_date, end_date, maximum_drawdown, recovered: bool) -> dict:
    end = pd.Timestamp(recovery_date) if recovered else pd.Timestamp(end_date)
    return {
        "peak_date": pd.Timestamp(peak_date),
        "start_date": pd.Timestamp(start_date),
        "trough_date": pd.Timestamp(trough_date),
        "recovery_date": pd.Timestamp(recovery_date) if recovered else pd.NaT,
        "end_date": pd.Timestamp(end_date),
        "maximum_drawdown": float(maximum_drawdown),
        "duration_days": int((end - pd.Timestamp(start_date)).days),
        "recovered": bool(recovered),
    }
