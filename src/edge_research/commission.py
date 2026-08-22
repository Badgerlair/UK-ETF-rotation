from __future__ import annotations


class CommissionModel:
    def calculate(self, quantity: float, price: float) -> float:
        raise NotImplementedError


class ZeroCommissionModel(CommissionModel):
    def calculate(self, quantity: float, price: float) -> float:
        return 0.0


def commission_model_from_config(config: dict) -> CommissionModel:
    model = str(config.get("execution_model", {}).get("commission_model", "zero")).lower()
    if model in {"zero", "0", "none", "placeholder"}:
        return ZeroCommissionModel()
    raise NotImplementedError(f"Commission model is not implemented yet: {model}")

