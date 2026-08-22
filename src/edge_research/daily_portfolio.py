from __future__ import annotations

from dataclasses import dataclass, field
import re

import pandas as pd

from edge_research.commission import commission_model_from_config
from edge_research.fill_model import DailyFillModel
from edge_research.position import DailyPortfolioState, Position, Trade
from edge_research.trade_lifecycle import (
    apply_split_to_position,
    close_position,
    create_position,
    exit_signal,
    update_trailing_stop,
)


TRADE_COLUMNS = [
    "trade_id", "strategy_name", "symbol", "direction", "entry_signal_date", "entry_date",
    "entry_price", "exit_date", "exit_price", "exit_reason", "quantity", "gross_pnl",
    "commission", "slippage", "net_pnl", "R", "bars_held", "initial_stop",
    "final_stop", "target_price", "notes", "entry_reference_price",
    "exit_reference_price", "dividend_income",
]

DAILY_EQUITY_COLUMNS = [
    "date", "cash", "realised_pnl", "unrealised_pnl", "equity", "gross_exposure",
    "net_exposure", "number_open_positions", "drawdown", "daily_return",
]

DIAGNOSTIC_COLUMNS = ["date", "strategy_name", "symbol", "event_type", "severity", "message"]

PENDING_ORDER_COLUMNS = [
    "pending_type", "strategy_name", "symbol", "signal_date", "intended_entry_date",
    "intended_exit_date", "reason",
]


@dataclass
class SimulationResult:
    trades: pd.DataFrame
    daily_equity: pd.DataFrame
    diagnostics: pd.DataFrame
    rejected_orders: pd.DataFrame
    open_positions: pd.DataFrame = field(default_factory=pd.DataFrame)
    pending_orders: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass(frozen=True)
class PreparedDailyMarketData:
    data: pd.DataFrame
    bar_lookup: dict
    dates: tuple[str, ...]


@dataclass(frozen=True)
class PreparedCloseObservedExitOrders:
    lookup: dict[tuple[str, str], tuple[str, str, str]]
    row_count: int


def prepare_daily_market_data(data: pd.DataFrame) -> PreparedDailyMarketData:
    prepared = data.sort_values(["date", "symbol"], kind="mergesort").copy()
    if "terminal_proxy_only" not in prepared:
        prepared["terminal_proxy_only"] = False
    prepared["date"] = pd.to_datetime(prepared["date"], errors="raise").dt.strftime("%Y-%m-%d")
    prepared["symbol"] = prepared["symbol"].astype(str)
    if prepared.duplicated(["date", "symbol"]).any():
        raise ValueError("Daily simulator requires one canonical bar per symbol/date")
    return PreparedDailyMarketData(
        data=prepared,
        bar_lookup={(str(row.date), str(row.symbol)): row for row in prepared.itertuples(index=False)},
        dates=tuple(sorted(prepared["date"].unique())),
    )


def prepare_close_observed_exit_orders(exit_orders: pd.DataFrame) -> PreparedCloseObservedExitOrders:
    frame = exit_orders.copy()
    required = {"strategy_name", "symbol", "signal_date", "intended_exit_date", "reason"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Exit orders are missing fields: {sorted(missing)}")
    frame["signal_date"] = pd.to_datetime(frame["signal_date"], errors="raise").dt.strftime("%Y-%m-%d")
    frame["intended_exit_date"] = pd.to_datetime(frame["intended_exit_date"], errors="raise").dt.strftime("%Y-%m-%d")
    if not (pd.to_datetime(frame["intended_exit_date"]) > pd.to_datetime(frame["signal_date"])).all():
        raise ValueError("CLOSE_OBSERVED_NEXT_OPEN exit orders must execute strictly after their signal date")
    lookup: dict[tuple[str, str], tuple[str, str, str]] = {}
    ordered = frame.sort_values(["intended_exit_date", "symbol", "signal_date"], kind="mergesort")
    for row in ordered[["intended_exit_date", "symbol", "strategy_name", "signal_date", "reason"]].itertuples(index=False):
        lookup.setdefault(
            (str(row.intended_exit_date), str(row.symbol)),
            (str(row.strategy_name), str(row.signal_date), str(row.reason)),
        )
    return PreparedCloseObservedExitOrders(lookup=lookup, row_count=len(frame))


class DailyPortfolioSimulator:
    def __init__(self, config: dict):
        self.config = config
        portfolio = config.get("portfolio", {}) or {}
        execution = config.get("execution_model", {}) or {}
        self.initial_cash = float(portfolio.get("initial_cash", 100000.0))
        self.cash = self.initial_cash
        self.max_positions = int(portfolio.get("max_positions", 10))
        self.sizing_mode = str(portfolio.get("sizing_mode", "fixed_fractional")).lower()
        self.position_size_pct = self._pct(portfolio.get("position_size_pct", 10))
        self.fixed_notional = float(portfolio.get("fixed_notional", portfolio.get("fixed_notional_amount", 10000.0)) or 10000.0)
        self.fixed_risk_pct = self._pct(portfolio.get("fixed_risk_pct", portfolio.get("risk_per_trade_pct", 1.0)))
        self.max_strategy_exposure_pct = self._pct(portfolio.get("max_strategy_exposure_pct", 100))
        self.max_total_exposure_pct = self._pct(portfolio.get("max_total_exposure_pct", 100))
        self.allow_overlap = bool(portfolio.get("allow_overlap", False))
        self.allow_reentry = bool(portfolio.get("allow_reentry", True))
        self.safety = config.get("safety", {}) or {}
        self.record_rejected_orders = bool(self.safety.get("record_rejected_orders", True))
        self.record_info_diagnostics = bool(self.safety.get("record_info_diagnostics", True))
        self.reentry_cooldown_days = int(self.safety.get("allow_same_symbol_reentry_within_days", 0) or 0)
        self.max_single_trade_pct_equity_warning = float(self.safety.get("max_single_trade_pct_equity_warning", 0) or 0)
        self.reject_split_like_moves_above_pct = float(self.safety.get("reject_split_like_moves_above_pct", 0) or 0)
        self.hard_cap_gross_exposure_pct = self._pct(self.safety.get("hard_cap_gross_exposure_pct", 100))
        self.borrow_cost_bps_per_year = float(execution.get("borrow_cost_bps_per_year", 0.0) or 0.0)
        self.fill_model = DailyFillModel(float(execution.get("slippage_bps", 0.0) or 0.0))
        self.commission_model = commission_model_from_config(config)
        self.diagnostics: list[dict] = []
        self.rejected_orders: list[dict] = []
        if str(config.get("strategy", {}).get("direction", "")).lower() == "short":
            self._diagnostic("", config.get("strategy", {}).get("name", ""), "", "model_warning", "warning", f"Borrow cost placeholder active at {self.borrow_cost_bps_per_year} bps/year; locate availability is not modelled")

    def simulate(
        self,
        orders: pd.DataFrame,
        data: pd.DataFrame | PreparedDailyMarketData,
        exit_orders: pd.DataFrame | PreparedCloseObservedExitOrders | None = None,
    ) -> SimulationResult:
        """Run daily orders without changing legacy execution modes.

        Strategy exits supplied through ``exit_orders`` are close-observed order
        intents.  They are evaluated only against positions that existed at the
        signal close and are filled at the intended next open.  No next-session
        bar is consulted while deciding whether an order exists.
        """
        self.cash = self.initial_cash
        self.diagnostics = []
        self.rejected_orders = []
        market = data if isinstance(data, PreparedDailyMarketData) else prepare_daily_market_data(data)
        prepared_data = market.data
        bar_lookup = market.bar_lookup
        dates = list(market.dates)
        execution = self.config.get("execution_model", {}) or {}
        entry_timing = str(execution.get("entry_timing", "next_open"))
        orders = orders.copy()
        exit_orders = pd.DataFrame() if exit_orders is None else exit_orders
        if orders.empty:
            return self._empty_result(prepared_data)
        orders["intended_entry_date"] = pd.to_datetime(orders["intended_entry_date"], errors="raise").dt.strftime("%Y-%m-%d")
        orders["signal_date"] = pd.to_datetime(orders["signal_date"], errors="raise").dt.strftime("%Y-%m-%d")
        if entry_timing == "next_open" and not (
            pd.to_datetime(orders["intended_entry_date"]) > pd.to_datetime(orders["signal_date"])
        ).all():
            raise ValueError("CLOSE_OBSERVED_NEXT_OPEN entry orders must execute strictly after their signal date")
        if entry_timing == "same_close" and not (
            pd.to_datetime(orders["intended_entry_date"]) >= pd.to_datetime(orders["signal_date"])
        ).all():
            raise ValueError("A same-close entry cannot execute before its signal date")
        if "rank" in orders.columns:
            orders["rank_sort"] = pd.to_numeric(orders["rank"], errors="coerce").fillna(999999)
        else:
            orders["rank_sort"] = 999999
        pending = {
            date: frame.sort_values(["rank_sort", "symbol"], kind="mergesort")
            for date, frame in orders.groupby("intended_entry_date", sort=False)
        }
        if isinstance(exit_orders, PreparedCloseObservedExitOrders):
            exit_lookup = exit_orders.lookup
        elif exit_orders.empty:
            exit_lookup = {}
        else:
            exit_lookup = prepare_close_observed_exit_orders(exit_orders).lookup

        open_positions: list[Position] = []
        trades: list[Trade] = []
        states: list[DailyPortfolioState] = []
        peak_equity = self.initial_cash
        previous_equity = self.initial_cash
        realised_total = 0.0
        last_exit_by_symbol: dict[str, str] = {}
        held_at_close: dict[str, set[str]] = {}
        carried_entries: list[pd.Series] = []
        carried_exits: dict[str, tuple[str, str, str]] = {}
        missing_policy = str(execution.get("missing_next_open_policy", "reject")).lower()
        require_not_held_at_signal = bool((self.config.get("portfolio", {}) or {}).get("require_not_held_at_signal", False))

        for current_date in dates:
            entered_today: set[str] = set()

            # Corporate actions effective at this session boundary are applied
            # before any next-open exit or entry uses the raw executable open.
            for position in list(open_positions):
                bar = bar_lookup.get((current_date, position.symbol))
                if bar is None:
                    continue
                split_factor = float(getattr(bar, "split_factor_at_open", 1.0) or 1.0)
                if split_factor != 1.0:
                    apply_split_to_position(position, split_factor)
                    self._diagnostic(current_date, position.strategy_name, position.symbol, "position_split_adjustment", "info", f"Overnight position adjusted before open; factor={split_factor:.12g}")
                dividend = float(getattr(bar, "cash_dividend_per_share", 0.0) or 0.0)
                if dividend:
                    cash_flow = position.quantity * dividend * (1.0 if position.direction == "long" else -1.0)
                    position.dividend_income += cash_flow
                    self._diagnostic(current_date, position.strategy_name, position.symbol, "position_dividend_accrual", "info", f"Ex-date cash flow accrued to position; amount={cash_flow:.6f}")
                position.last_mark_price = float(bar.close)
                position.last_mark_date = current_date

            # Close-observed exits execute before intraday lifecycle rules and
            # before new entries at the same open.
            for position in list(open_positions):
                request = carried_exits.get(position.symbol)
                if request is None:
                    request = exit_lookup.get((current_date, position.symbol))
                if request is None or request[0] != position.strategy_name:
                    continue
                signal_date = request[1]
                if position.symbol not in held_at_close.get(signal_date, set()):
                    carried_exits.pop(position.symbol, None)
                    continue
                bar = bar_lookup.get((current_date, position.symbol))
                if bar is None:
                    if missing_policy == "carry_to_next_available_open":
                        carried_exits[position.symbol] = request
                        self._diagnostic(current_date, position.strategy_name, position.symbol, "next_open_exit_carried", "warning", "No executable bar at intended open; exit remains queued for the next available open")
                    else:
                        carried_exits.pop(position.symbol, None)
                        self._diagnostic(current_date, position.strategy_name, position.symbol, "next_open_exit_unfilled", "warning", "No executable bar at intended open; deterministic reject policy applied")
                    continue
                bar_series = pd.Series(bar._asdict())
                commission = self.commission_model.calculate(position.quantity, float(bar_series["open"]))
                trade = close_position(position, bar_series, request[2], None, "next_open", self.fill_model, commission, f"T{len(trades) + 1:06d}")
                trade.notes = f"close signal {signal_date}; queued after close; filled next available open"
                self._post_trade_diagnostics(trade, previous_equity)
                self.cash += trade.net_pnl
                realised_total += trade.net_pnl
                trades.append(trade)
                last_exit_by_symbol[position.symbol] = trade.exit_date
                open_positions.remove(position)
                carried_exits.pop(position.symbol, None)

            for position in list(open_positions):
                bar = bar_lookup.get((current_date, position.symbol))
                if bar is None:
                    continue
                bar_series = pd.Series(bar._asdict())
                update_trailing_stop(position, bar_series, self.config)
                if self._stop_and_target_hit(position, bar_series):
                    self._diagnostic(current_date, position.strategy_name, position.symbol, "same_day_stop_target", "warning", "Stop and target both hit on daily bar; conservative stop-first assumption used")
                signal = exit_signal(position, bar_series, self.config)
                if signal is None:
                    continue
                reason, reference, timing = signal
                commission = self.commission_model.calculate(position.quantity, float(bar_series["close"]))
                trade = close_position(position, bar_series, reason, reference, timing, self.fill_model, commission, f"T{len(trades) + 1:06d}")
                self._post_trade_diagnostics(trade, previous_equity)
                self.cash += trade.net_pnl
                realised_total += trade.net_pnl
                trades.append(trade)
                last_exit_by_symbol[position.symbol] = trade.exit_date
                open_positions.remove(position)

            realised_total += self._enforce_exposure_cap(open_positions, bar_lookup, current_date, trades, last_exit_by_symbol, previous_equity)

            scheduled = pending.get(current_date)
            todays_rows = carried_entries + ([] if scheduled is None else [row for _, row in scheduled.iterrows()])
            carried_entries = []
            if todays_rows:
                todays_rows = sorted(todays_rows, key=lambda row: (float(row.get("rank_sort", 999999)), str(row.get("symbol", ""))))
                for order in todays_rows:
                    if require_not_held_at_signal and str(order["symbol"]) in held_at_close.get(str(order["signal_date"]), set()):
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "info", "symbol was held at the signal close")
                        self._reject_order(current_date, order, "symbol was held at the signal close")
                        continue
                    if len(open_positions) >= self.max_positions:
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "info", "max_positions reached")
                        self._reject_order(current_date, order, "max_positions reached")
                        continue
                    if not self.allow_overlap and (any(p.symbol == order["symbol"] for p in open_positions) or str(order["symbol"]) in entered_today):
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "info", "duplicate symbol ignored because allow_overlap=false")
                        self._reject_order(current_date, order, "duplicate symbol ignored because allow_overlap=false")
                        continue
                    previous_exit = last_exit_by_symbol.get(str(order["symbol"]))
                    if previous_exit and self.reentry_cooldown_days:
                        gap = (pd.Timestamp(current_date) - pd.Timestamp(previous_exit)).days
                        if 0 <= gap < self.reentry_cooldown_days:
                            self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "warning", f"same-symbol reentry cooldown active; gap_days={gap}")
                            self._reject_order(current_date, order, f"same-symbol reentry cooldown active; gap_days={gap}")
                            continue
                    bar = bar_lookup.get((current_date, str(order["symbol"])))
                    if bar is None:
                        if missing_policy == "carry_to_next_available_open":
                            carried_entries.append(order)
                            self._diagnostic(current_date, order["strategy_name"], order["symbol"], "next_open_entry_carried", "warning", "No executable bar at intended open; entry remains queued for the next available open")
                        else:
                            self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_failed", "warning", "No daily bar available for intended entry date")
                            self._reject_order(current_date, order, "No daily bar available for intended entry date")
                        continue
                    if bool(getattr(bar, "terminal_proxy_only", False)):
                        reason = "terminal settlement proxy is not an executable entry observation"
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "terminal_proxy_entry_rejected", "warning", reason)
                        self._reject_order(current_date, order, reason)
                        continue
                    valuation_field = "open" if entry_timing == "next_open" else "close"
                    current_equity = self.cash + self._unrealised(
                        open_positions,
                        bar_lookup,
                        current_date,
                        price_field=valuation_field,
                    )
                    reference_price = float(getattr(bar, valuation_field))
                    allocation = self._allocation_for_order(order, reference_price, current_equity)
                    quantity = int(allocation // reference_price)
                    if quantity <= 0:
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "warning", f"{self.sizing_mode} sizing produced zero quantity")
                        self._reject_order(current_date, order, f"{self.sizing_mode} sizing produced zero quantity")
                        continue
                    projected_notional = quantity * reference_price
                    if not self._projected_exposure_room(
                        open_positions,
                        bar_lookup,
                        current_date,
                        current_equity,
                        projected_notional,
                        price_field=valuation_field,
                    ):
                        reason = "projected gross exposure would breach configured cap"
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_skipped", "warning", reason)
                        self._reject_order(current_date, order, reason, projected_notional=projected_notional, current_equity=current_equity)
                        continue
                    entry_commission = self.commission_model.calculate(quantity, reference_price)
                    position, entry_slippage = create_position(
                        order,
                        pd.Series(bar._asdict()),
                        self.config,
                        f"P{len(trades) + len(open_positions) + 1:06d}",
                        quantity,
                        self.fill_model,
                        entry_commission,
                    )
                    open_positions.append(position)
                    entered_today.add(position.symbol)
                    if entry_slippage:
                        self._diagnostic(current_date, order["strategy_name"], order["symbol"], "entry_fill", "info", f"entry slippage cost {entry_slippage:.4f}")
                    if self._stop_and_target_hit(position, pd.Series(bar._asdict())):
                        self._diagnostic(current_date, position.strategy_name, position.symbol, "same_day_stop_target", "warning", "Stop and target both hit on daily bar; conservative stop-first assumption used")
                    entry_day_signal = exit_signal(position, pd.Series(bar._asdict()), self.config)
                    if entry_day_signal is not None:
                        reason, reference, timing = entry_day_signal
                        commission = self.commission_model.calculate(position.quantity, float(bar.close))
                        trade = close_position(position, pd.Series(bar._asdict()), reason, reference, timing, self.fill_model, commission, f"T{len(trades) + 1:06d}")
                        self._post_trade_diagnostics(trade, previous_equity)
                        self.cash += trade.net_pnl
                        realised_total += trade.net_pnl
                        trades.append(trade)
                        last_exit_by_symbol[position.symbol] = trade.exit_date
                        open_positions.remove(position)

            realised_total += self._enforce_exposure_cap(open_positions, bar_lookup, current_date, trades, last_exit_by_symbol, previous_equity)

            unrealised = self._unrealised(open_positions, bar_lookup, current_date)
            gross_exposure, net_exposure = self._exposures(open_positions, bar_lookup, current_date)
            borrow_cost = self._borrow_cost(open_positions, bar_lookup, current_date)
            if borrow_cost:
                self.cash -= borrow_cost
                realised_total -= borrow_cost
                self._diagnostic(current_date, config_strategy_name(self.config), "", "borrow_cost", "info", f"daily borrow cost applied; cost={borrow_cost:.6f}")
                unrealised = self._unrealised(open_positions, bar_lookup, current_date)
            equity = self.cash + unrealised
            peak_equity = max(peak_equity, equity)
            drawdown = equity / peak_equity - 1 if peak_equity else 0.0
            daily_return = equity / previous_equity - 1 if previous_equity else 0.0
            if abs(daily_return) > 0.20:
                self._diagnostic(current_date, config_strategy_name(self.config), "", "equity_jump", "warning", f"daily equity return exceeded 20%; daily_return={daily_return:.6f}")
            states.append(DailyPortfolioState(current_date, self.cash, realised_total, unrealised, equity, gross_exposure, net_exposure, len(open_positions), drawdown, daily_return))
            previous_equity = equity
            for position in open_positions:
                if (current_date, position.symbol) in bar_lookup:
                    position.bars_held += 1
            held_at_close[current_date] = {position.symbol for position in open_positions}

        end_of_data_policy = str(execution.get("end_of_data_position_policy", "close_same_close")).lower()
        if end_of_data_policy not in {"close_same_close", "leave_open_mark_to_market"}:
            raise ValueError(f"Unsupported end_of_data_position_policy: {end_of_data_policy}")
        if open_positions and end_of_data_policy == "close_same_close":
            last_date = dates[-1]
            for position in list(open_positions):
                bar = bar_lookup.get((last_date, position.symbol))
                if bar is None:
                    continue
                commission = self.commission_model.calculate(position.quantity, float(bar.close))
                trade = close_position(position, pd.Series(bar._asdict()), "end_of_data", None, "same_close", self.fill_model, commission, f"T{len(trades) + 1:06d}")
                self._post_trade_diagnostics(trade, previous_equity)
                self.cash += trade.net_pnl
                realised_total += trade.net_pnl
                trades.append(trade)
                open_positions.remove(position)

            if states:
                unrealised = self._unrealised(open_positions, bar_lookup, last_date)
                gross_exposure, net_exposure = self._exposures(open_positions, bar_lookup, last_date)
                equity = self.cash + unrealised
                prior_equity = states[-2].equity if len(states) > 1 else self.initial_cash
                peak_before = max((state.equity for state in states[:-1]), default=self.initial_cash)
                peak_final = max(peak_before, equity)
                states[-1] = DailyPortfolioState(
                    last_date,
                    self.cash,
                    realised_total,
                    unrealised,
                    equity,
                    gross_exposure,
                    net_exposure,
                    len(open_positions),
                    equity / peak_final - 1 if peak_final else 0.0,
                    equity / prior_equity - 1 if prior_equity else 0.0,
                )

        pending_rows = [dict(row) | {"pending_type": "entry"} for row in carried_entries]
        pending_rows.extend(
            {
                "strategy_name": request[0],
                "signal_date": request[1],
                "reason": request[2],
                "symbol": symbol,
                "pending_type": "exit",
            }
            for symbol, request in carried_exits.items()
        )

        open_position_frame = pd.DataFrame(
            [position.to_dict() for position in open_positions],
            columns=list(Position.__dataclass_fields__),
        )
        pending_order_frame = pd.DataFrame(pending_rows)
        if pending_order_frame.empty:
            pending_order_frame = pd.DataFrame(columns=PENDING_ORDER_COLUMNS)

        return SimulationResult(
            trades=pd.DataFrame([trade.to_dict() for trade in trades], columns=TRADE_COLUMNS),
            daily_equity=pd.DataFrame([state.to_dict() for state in states], columns=DAILY_EQUITY_COLUMNS),
            diagnostics=pd.DataFrame(self.diagnostics, columns=DIAGNOSTIC_COLUMNS),
            rejected_orders=pd.DataFrame(self.rejected_orders),
            open_positions=open_position_frame,
            pending_orders=pending_order_frame,
        )

    def _empty_result(self, data: pd.DataFrame) -> SimulationResult:
        states = []
        for date in sorted(data["date"].astype(str).unique()):
            states.append(DailyPortfolioState(date, self.cash, 0.0, 0.0, self.cash, 0.0, 0.0, 0, 0.0, 0.0).to_dict())
        return SimulationResult(
            trades=pd.DataFrame(columns=TRADE_COLUMNS),
            daily_equity=pd.DataFrame(states, columns=DAILY_EQUITY_COLUMNS),
            diagnostics=pd.DataFrame(self.diagnostics, columns=DIAGNOSTIC_COLUMNS),
            rejected_orders=pd.DataFrame(self.rejected_orders),
        )

    def _equity(self, positions: list[Position], bar_lookup: dict, date: str, realised_total: float) -> float:
        return self.cash + self._unrealised(positions, bar_lookup, date)

    @staticmethod
    def _unrealised(
        positions: list[Position],
        bar_lookup: dict,
        date: str,
        price_field: str = "close",
    ) -> float:
        total = 0.0
        for position in positions:
            bar = bar_lookup.get((date, position.symbol))
            price = float(getattr(bar, price_field)) if bar is not None else position.last_mark_price
            if price is None:
                continue
            if position.direction == "long":
                price_pnl = (price - position.entry_price) * position.quantity
            else:
                price_pnl = (position.entry_price - price) * position.quantity
            total += price_pnl + position.dividend_income - position.entry_commission
        return total

    @staticmethod
    def _exposures(positions: list[Position], bar_lookup: dict, date: str) -> tuple[float, float]:
        gross = 0.0
        net = 0.0
        for position in positions:
            bar = bar_lookup.get((date, position.symbol))
            close = float(bar.close) if bar is not None else position.last_mark_price
            if close is None:
                continue
            value = float(close) * position.quantity
            gross += abs(value)
            net += value if position.direction == "long" else -value
        return gross, net

    def _exposure_room(self, positions: list[Position], equity: float) -> bool:
        if equity <= 0:
            return False
        gross = sum(abs(p.entry_price * p.quantity) for p in positions)
        return gross / equity < self._active_exposure_cap()

    def _projected_exposure_room(
        self,
        positions: list[Position],
        bar_lookup: dict,
        date: str,
        equity: float,
        projected_notional: float,
        price_field: str = "close",
    ) -> bool:
        if equity <= 0:
            return False
        gross = 0.0
        for position in positions:
            bar = bar_lookup.get((date, position.symbol))
            price = float(getattr(bar, price_field)) if bar is not None else position.last_mark_price
            if price is not None:
                gross += abs(price * position.quantity)
        projected_pct = (gross + abs(projected_notional)) / equity
        return projected_pct <= self._active_exposure_cap() + 1e-12

    def _active_exposure_cap(self) -> float:
        return min(self.max_total_exposure_pct, self.max_strategy_exposure_pct, self.hard_cap_gross_exposure_pct)

    def _allocation_for_order(self, order: pd.Series, reference_price: float, equity: float) -> float:
        equity = max(float(equity), 0.0)
        if self.sizing_mode == "fixed_fractional":
            return equity * self.position_size_pct
        if self.sizing_mode == "fixed_notional":
            return max(self.fixed_notional, 0.0)
        if self.sizing_mode == "fixed_risk":
            stop = pd.to_numeric(pd.Series([order.get("stop_price")]), errors="coerce").iloc[0]
            if pd.isna(stop) or float(stop) <= 0 or reference_price <= 0:
                return 0.0
            stop_distance = abs(reference_price - float(stop))
            if stop_distance <= 0:
                return 0.0
            risk_amount = equity * self.fixed_risk_pct
            return int(risk_amount // stop_distance) * reference_price
        self._diagnostic("", config_strategy_name(self.config), "", "sizing_mode", "warning", f"Unknown sizing_mode={self.sizing_mode}; falling back to fixed_fractional")
        return equity * self.position_size_pct

    def _borrow_cost(self, positions: list[Position], bar_lookup: dict, date: str) -> float:
        if self.borrow_cost_bps_per_year <= 0:
            return 0.0
        gross_short = 0.0
        for position in positions:
            if position.direction != "short":
                continue
            bar = bar_lookup.get((date, position.symbol))
            close = float(bar.close) if bar is not None else position.last_mark_price
            if close is not None:
                gross_short += abs(float(close) * position.quantity)
        return gross_short * (self.borrow_cost_bps_per_year / 10000.0) / 252.0

    def _enforce_exposure_cap(
        self,
        positions: list[Position],
        bar_lookup: dict,
        date: str,
        trades: list[Trade],
        last_exit_by_symbol: dict[str, str],
        previous_equity: float,
    ) -> float:
        realised_delta = 0.0
        while positions:
            equity = self.cash + self._unrealised(positions, bar_lookup, date)
            gross, _ = self._exposures(positions, bar_lookup, date)
            if equity > 0 and gross / equity <= self._active_exposure_cap() + 1e-12:
                break
            candidates = []
            for position in positions:
                bar = bar_lookup.get((date, position.symbol))
                if bar is not None:
                    candidates.append((abs(float(bar.close) * position.quantity), position, bar))
            if not candidates:
                break
            _, position, bar = max(candidates, key=lambda item: item[0])
            commission = self.commission_model.calculate(position.quantity, float(bar.close))
            trade = close_position(position, pd.Series(bar._asdict()), "exposure_cap", None, "same_close", self.fill_model, commission, f"T{len(trades) + 1:06d}")
            self._post_trade_diagnostics(trade, previous_equity)
            self.cash += trade.net_pnl
            realised_delta += trade.net_pnl
            trades.append(trade)
            last_exit_by_symbol[position.symbol] = trade.exit_date
            positions.remove(position)
            self._diagnostic(date, position.strategy_name, position.symbol, "forced_exposure_reduction", "warning", "closed position to enforce hard gross exposure cap")
        return realised_delta

    @staticmethod
    def _pct(value) -> float:
        value = float(value)
        return value / 100.0 if value > 1 else value

    def _diagnostic(self, date: str, strategy_name: str, symbol: str, event_type: str, severity: str, message: str) -> None:
        if severity == "info" and not self.record_info_diagnostics:
            return
        self.diagnostics.append({
            "date": date,
            "strategy_name": strategy_name,
            "symbol": symbol,
            "event_type": event_type,
            "severity": severity,
            "message": message,
        })

    def _reject_order(self, date: str, order: pd.Series, reason: str, projected_notional: float | None = None, current_equity: float | None = None) -> None:
        if not self.record_rejected_orders:
            return
        self.rejected_orders.append({
            "date": date,
            "order_id": order.get("order_id", ""),
            "strategy_name": order.get("strategy_name", ""),
            "symbol": order.get("symbol", ""),
            "direction": order.get("direction", ""),
            "signal_date": order.get("signal_date", ""),
            "intended_entry_date": order.get("intended_entry_date", ""),
            "rank": order.get("rank", ""),
            "reason": reason,
            "projected_notional": projected_notional,
            "current_equity": current_equity,
            "active_exposure_cap_pct": self._active_exposure_cap() * 100.0,
        })

    def _post_trade_diagnostics(self, trade: Trade, equity_reference: float) -> None:
        max_trade_r = self.safety.get("max_trade_R_warning")
        if max_trade_r and abs(float(trade.R)) > float(max_trade_r):
            self._diagnostic(trade.exit_date, trade.strategy_name, trade.symbol, "extreme_trade_R", "warning", f"trade R exceeded threshold; R={trade.R:.6f}")
        if self.max_single_trade_pct_equity_warning and equity_reference:
            pct = abs(float(trade.net_pnl)) / abs(float(equity_reference)) * 100.0
            if pct > self.max_single_trade_pct_equity_warning:
                self._diagnostic(trade.exit_date, trade.strategy_name, trade.symbol, "large_trade_pct_equity", "warning", f"single trade PnL exceeded threshold pct of equity; pct={pct:.6f}")
        if self.reject_split_like_moves_above_pct:
            move_pct = abs(float(trade.exit_price) / float(trade.entry_price) - 1.0) * 100.0 if trade.entry_price else 0.0
            if move_pct > self.reject_split_like_moves_above_pct:
                self._diagnostic(trade.exit_date, trade.strategy_name, trade.symbol, "abnormal_gap_or_split_like_move", "warning", f"trade price move exceeded split-like threshold; move_pct={move_pct:.6f}")

    @staticmethod
    def _stop_and_target_hit(position: Position, bar: pd.Series) -> bool:
        stop = position.stop_price()
        target = position.target_price
        if stop is None or target is None:
            return False
        if position.direction == "long":
            return float(bar["low"]) <= stop and float(bar["high"]) >= target
        return float(bar["high"]) >= stop and float(bar["low"]) <= target


def config_strategy_name(config: dict) -> str:
    return str(config.get("strategy", {}).get("name", ""))

