from __future__ import annotations


def apply_slippage(price: float, direction: str, side: str, slippage_bps: float = 0.0) -> float:
    multiplier = float(slippage_bps or 0.0) / 10000.0
    if direction == "long" and side == "entry":
        return float(price) * (1 + multiplier)
    if direction == "long" and side == "exit":
        return float(price) * (1 - multiplier)
    if direction == "short" and side == "entry":
        return float(price) * (1 - multiplier)
    if direction == "short" and side == "exit":
        return float(price) * (1 + multiplier)
    raise ValueError(f"Unsupported slippage direction/side: {direction}/{side}")


def slippage_amount(reference_price: float, filled_price: float, quantity: float) -> float:
    return abs(float(filled_price) - float(reference_price)) * abs(float(quantity))

