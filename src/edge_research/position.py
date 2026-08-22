from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Position:
    position_id: str
    strategy_name: str
    symbol: str
    direction: str
    entry_signal_date: str
    entry_date: str
    entry_price: float
    quantity: float
    entry_reference_price: float | None = None
    entry_slippage: float = 0.0
    entry_commission: float = 0.0
    dividend_income: float = 0.0
    last_mark_price: float | None = None
    last_mark_date: str | None = None
    initial_stop: float | None = None
    trailing_stop: float | None = None
    target_price: float | None = None
    time_stop_bars: int | None = None
    bars_held: int = 0
    status: str = "open"
    exit_date: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    realised_pnl: float = 0.0
    realised_R: float = 0.0
    highest_close: float | None = None
    highest_high: float | None = None
    lowest_close: float | None = None
    lowest_low: float | None = None

    def stop_price(self) -> float | None:
        stops = [value for value in [self.initial_stop, self.trailing_stop] if value is not None]
        if not stops:
            return None
        return max(stops) if self.direction == "long" else min(stops)

    def risk_per_share(self) -> float:
        stop = self.initial_stop
        if stop is None:
            return max(abs(self.entry_price) * 0.01, 0.01)
        return max(abs(self.entry_price - stop), 0.01)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trade:
    trade_id: str
    strategy_name: str
    symbol: str
    direction: str
    entry_signal_date: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    exit_reason: str
    quantity: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    R: float
    bars_held: int
    initial_stop: float | None
    final_stop: float | None
    target_price: float | None
    notes: str = ""
    entry_reference_price: float | None = None
    exit_reference_price: float | None = None
    dividend_income: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DailyPortfolioState:
    date: str
    cash: float
    realised_pnl: float
    unrealised_pnl: float
    equity: float
    gross_exposure: float
    net_exposure: float
    number_open_positions: int
    drawdown: float
    daily_return: float

    def to_dict(self) -> dict:
        return asdict(self)

