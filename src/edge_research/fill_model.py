from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from edge_research.slippage import apply_slippage, slippage_amount


@dataclass(frozen=True)
class Fill:
    date: str
    reference_price: float
    fill_price: float
    slippage_cost: float
    timing: str


class DailyFillModel:
    def __init__(self, slippage_bps: float = 0.0):
        self.slippage_bps = float(slippage_bps or 0.0)

    def entry_fill(self, bar: pd.Series, direction: str, timing: str, quantity: float) -> Fill:
        reference = self._reference_price(bar, timing, entry=True)
        fill = apply_slippage(reference, direction, "entry", self.slippage_bps)
        return Fill(str(bar["date"]), reference, fill, slippage_amount(reference, fill, quantity), timing)

    def exit_fill(self, bar: pd.Series, direction: str, timing: str, quantity: float, stop_or_target_price: float | None = None) -> Fill:
        reference = float(stop_or_target_price) if stop_or_target_price is not None else self._reference_price(bar, timing, entry=False)
        fill = apply_slippage(reference, direction, "exit", self.slippage_bps)
        return Fill(str(bar["date"]), reference, fill, slippage_amount(reference, fill, quantity), timing)

    @staticmethod
    def _reference_price(bar: pd.Series, timing: str, *, entry: bool) -> float:
        if timing == "next_open":
            return float(bar["open"])
        if timing == "same_close":
            return float(bar["close"])
        if timing in {"stop_intraday", "time_stop"}:
            return float(bar["close"])
        if timing == "intraday_trigger":
            raise NotImplementedError("intraday_trigger is not implemented for 1D simulation")
        raise ValueError(f"Unsupported {'entry' if entry else 'exit'} timing: {timing}")

