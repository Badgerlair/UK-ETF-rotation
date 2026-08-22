from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
import pandas as pd


BRIDGE_DIAGNOSTIC_COLUMNS = ["date", "symbol", "event_type", "severity", "message"]


@dataclass(frozen=True)
class CorporateActionBridgeResult:
    """Raw executable bars plus economically continuous signal fields.

    Raw OHLC fields are never overwritten.  ``adjusted_*`` fields are used only
    for research signals; fills remain on raw ``open``/``close`` prices.  Split
    events are also attached to the first executable bar on or after their
    execution date so the portfolio lifecycle can adjust an overnight holding
    before that bar's open is used.
    """

    panel: pd.DataFrame
    diagnostics: pd.DataFrame
    split_events: pd.DataFrame
    dividend_events: pd.DataFrame


def apply_split_event_corrections(
    events: pd.DataFrame | None,
    corrections: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply source-bound replacements/additions to a downstream split layer.

    Corrections are explicit data lineage, not inferred from price movements.
    Supported operations are ``REPLACE`` (remove one ticker/date event and add
    the corrected event) and ``ADD`` (add a documented missing event).
    """

    diagnostics: list[dict] = []
    normalised = _normalise_splits(events, diagnostics).rename(columns={"symbol": "ticker"})
    required = {
        "correction_id",
        "operation",
        "ticker",
        "corrected_execution_date",
        "split_factor",
        "source",
    }
    if missing := required.difference(corrections.columns):
        raise ValueError(f"Split corrections are missing fields: {sorted(missing)}")
    fixes = corrections.copy()
    if "existing_execution_date" not in fixes:
        fixes["existing_execution_date"] = pd.NaT
    fixes["operation"] = fixes["operation"].astype(str).str.upper().str.strip()
    fixes["ticker"] = fixes["ticker"].astype(str).str.upper().str.strip()
    fixes["existing_execution_date"] = pd.to_datetime(
        fixes["existing_execution_date"], errors="coerce"
    ).dt.normalize()
    fixes["corrected_execution_date"] = pd.to_datetime(
        fixes["corrected_execution_date"], errors="raise"
    ).dt.normalize()
    fixes["split_factor"] = pd.to_numeric(fixes["split_factor"], errors="raise")
    if (~fixes["operation"].isin(["REPLACE", "ADD"])).any():
        raise ValueError("Split correction operation must be REPLACE or ADD")
    if (~np.isfinite(fixes["split_factor"]) | fixes["split_factor"].le(0)).any():
        raise ValueError("Split correction factors must be finite and positive")

    audit_rows: list[dict] = []
    corrected = normalised.copy()
    for fix in fixes.itertuples(index=False):
        removed = 0
        if fix.operation == "REPLACE":
            if pd.isna(fix.existing_execution_date):
                raise ValueError(f"REPLACE correction {fix.correction_id} requires existing_execution_date")
            remove_mask = corrected["ticker"].eq(fix.ticker) & corrected["execution_date"].eq(
                fix.existing_execution_date
            )
            removed = int(remove_mask.sum())
            if removed != 1:
                raise ValueError(
                    f"REPLACE correction {fix.correction_id} expected one normalised event, found {removed}"
                )
            corrected = corrected.loc[~remove_mask].copy()
        addition = pd.DataFrame(
            [
                {
                    "ticker": fix.ticker,
                    "execution_date": fix.corrected_execution_date,
                    "split_factor": float(fix.split_factor),
                    "source": str(fix.source),
                }
            ]
        )
        corrected = pd.concat([corrected, addition], ignore_index=True)
        audit_rows.append(
            {
                "correction_id": str(fix.correction_id),
                "operation": fix.operation,
                "ticker": fix.ticker,
                "existing_execution_date": fix.existing_execution_date,
                "corrected_execution_date": fix.corrected_execution_date,
                "split_factor": float(fix.split_factor),
                "normalised_events_removed": removed,
                "source": str(fix.source),
                "status": "APPLIED",
            }
        )
    corrected = (
        corrected.drop_duplicates(["ticker", "execution_date", "split_factor", "source"])
        .sort_values(["ticker", "execution_date"], kind="mergesort")
        .reset_index(drop=True)
    )
    duplicate_dates = corrected.duplicated(["ticker", "execution_date"], keep=False)
    if duplicate_dates.any():
        combined = (
            corrected.groupby(["ticker", "execution_date"], as_index=False)
            .agg(
                split_factor=("split_factor", "prod"),
                source=("source", lambda values: "|".join(sorted(set(map(str, values))))),
            )
        )
        corrected = combined.sort_values(["ticker", "execution_date"], kind="mergesort").reset_index(drop=True)
    return corrected, pd.DataFrame(audit_rows)


def build_adjusted_signal_panel(
    bars: pd.DataFrame,
    split_events: pd.DataFrame | None = None,
    dividend_events: pd.DataFrame | None = None,
) -> CorporateActionBridgeResult:
    required = {"date", "symbol", "open", "high", "low", "close", "volume"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"Corporate-action bridge is missing bar fields: {sorted(missing)}")

    panel = bars.copy()
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    panel["symbol"] = panel["symbol"].astype(str).str.upper().str.strip()
    if panel["symbol"].eq("").any():
        raise ValueError("Corporate-action bridge received an empty symbol")
    if panel.duplicated(["symbol", "date"]).any():
        raise ValueError("Corporate-action bridge requires one canonical bar per symbol/date")
    for column in ("open", "high", "low", "close", "volume"):
        panel[column] = pd.to_numeric(panel[column], errors="coerce")
    if panel[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("Corporate-action bridge received a missing executable price")
    if panel[["open", "high", "low", "close"]].le(0).any().any():
        raise ValueError("Corporate-action bridge received a non-positive executable price")

    diagnostics: list[dict] = []
    splits = _normalise_splits(split_events, diagnostics)
    dividends = _normalise_dividends(dividend_events, diagnostics)
    panel = panel.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)

    panel["split_factor_at_open"] = 1.0
    panel["cash_dividend_per_share"] = 0.0
    panel["split_adjustment_factor"] = 1.0
    panel["dividend_adjustment_factor"] = 1.0

    output_groups: list[pd.DataFrame] = []
    split_effective_rows: list[dict] = []
    dividend_effective_rows: list[dict] = []
    split_by_symbol = {symbol: group for symbol, group in splits.groupby("symbol", sort=False)}
    dividend_by_symbol = {symbol: group for symbol, group in dividends.groupby("symbol", sort=False)}

    for symbol, source_group in panel.groupby("symbol", sort=False):
        group = source_group.sort_values("date", kind="mergesort").copy()
        dates = group["date"].to_numpy(dtype="datetime64[ns]")
        split_factors = np.ones(len(group), dtype=float)
        cash_dividends = np.zeros(len(group), dtype=float)

        for event in split_by_symbol.get(symbol, pd.DataFrame()).itertuples(index=False):
            position = int(np.searchsorted(dates, np.datetime64(event.execution_date), side="left"))
            if position >= len(group):
                diagnostics.append(_diagnostic(event.execution_date, symbol, "unmatched_split_event", "warning", "No executable bar exists on or after the split execution date"))
                continue
            effective_date = pd.Timestamp(group.iloc[position]["date"])
            split_factors[position] *= float(event.split_factor)
            split_effective_rows.append(
                {
                    "symbol": symbol,
                    "execution_date": pd.Timestamp(event.execution_date),
                    "effective_bar_date": effective_date,
                    "split_factor": float(event.split_factor),
                    "source": str(event.source),
                }
            )
            if effective_date != pd.Timestamp(event.execution_date):
                diagnostics.append(_diagnostic(effective_date, symbol, "deferred_split_application", "warning", f"Split dated {pd.Timestamp(event.execution_date).date()} attached to first subsequent executable bar"))

        for event in dividend_by_symbol.get(symbol, pd.DataFrame()).itertuples(index=False):
            position = int(np.searchsorted(dates, np.datetime64(event.ex_dividend_date), side="left"))
            if position >= len(group):
                diagnostics.append(_diagnostic(event.ex_dividend_date, symbol, "unmatched_dividend_event", "warning", "No executable bar exists on or after the ex-dividend date"))
                continue
            effective_date = pd.Timestamp(group.iloc[position]["date"])
            cash_dividends[position] += float(event.dividend_amount)
            dividend_effective_rows.append(
                {
                    "symbol": symbol,
                    "ex_dividend_date": pd.Timestamp(event.ex_dividend_date),
                    "effective_bar_date": effective_date,
                    "dividend_amount": float(event.dividend_amount),
                    "source": str(event.source),
                }
            )
            if effective_date != pd.Timestamp(event.ex_dividend_date):
                diagnostics.append(_diagnostic(effective_date, symbol, "deferred_dividend_application", "warning", f"Dividend dated {pd.Timestamp(event.ex_dividend_date).date()} attached to first subsequent executable bar"))

        group["split_factor_at_open"] = split_factors
        group["cash_dividend_per_share"] = cash_dividends

        inclusive_future_splits = pd.Series(split_factors).iloc[::-1].cumprod().iloc[::-1].to_numpy()
        exclusive_future_splits = inclusive_future_splits / split_factors
        split_price_factor = 1.0 / exclusive_future_splits

        dividend_event_factors = np.ones(len(group), dtype=float)
        raw_close = group["close"].to_numpy(dtype=float)
        for index, amount in enumerate(cash_dividends):
            if amount == 0:
                continue
            if index == 0 or not math.isfinite(raw_close[index - 1]) or raw_close[index - 1] <= amount:
                diagnostics.append(_diagnostic(group.iloc[index]["date"], symbol, "missing_dividend_adjustment_factor", "warning", "Dividend cash amount is available but a valid prior close is not"))
                continue
            dividend_event_factors[index] = (raw_close[index - 1] - amount) / raw_close[index - 1]
        inclusive_future_dividends = pd.Series(dividend_event_factors).iloc[::-1].cumprod().iloc[::-1].to_numpy()
        exclusive_future_dividends = inclusive_future_dividends / dividend_event_factors

        group["split_adjustment_factor"] = split_price_factor
        group["dividend_adjustment_factor"] = exclusive_future_dividends
        combined_price_factor = split_price_factor * exclusive_future_dividends
        for column in ("open", "high", "low", "close"):
            group[f"adjusted_{column}"] = group[column].to_numpy(dtype=float) * combined_price_factor
        group["adjusted_volume"] = group["volume"].to_numpy(dtype=float) * exclusive_future_splits
        output_groups.append(group)

    bridged = pd.concat(output_groups, ignore_index=True) if output_groups else panel
    bridged = bridged.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True)
    return CorporateActionBridgeResult(
        panel=bridged,
        diagnostics=pd.DataFrame(diagnostics, columns=BRIDGE_DIAGNOSTIC_COLUMNS),
        split_events=pd.DataFrame(split_effective_rows),
        dividend_events=pd.DataFrame(dividend_effective_rows),
    )


def _normalise_splits(events: pd.DataFrame | None, diagnostics: list[dict]) -> pd.DataFrame:
    columns = ["symbol", "execution_date", "split_factor", "source"]
    if events is None or events.empty:
        return pd.DataFrame(columns=columns)
    frame = events.copy().rename(columns={"ticker": "symbol", "date": "execution_date", "ratio": "split_factor"})
    if "symbol" not in frame or "execution_date" not in frame:
        raise ValueError("Split events require symbol/ticker and execution_date/date")
    if "split_factor" not in frame and {"split_from", "split_to"}.issubset(frame.columns):
        frame["split_factor"] = pd.to_numeric(frame["split_to"], errors="coerce") / pd.to_numeric(frame["split_from"], errors="coerce")
    if "split_factor" not in frame:
        frame["split_factor"] = np.nan
    if "source" not in frame:
        frame["source"] = "unspecified"
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["execution_date"] = pd.to_datetime(frame["execution_date"], errors="coerce").dt.normalize()
    frame["split_factor"] = pd.to_numeric(frame["split_factor"], errors="coerce")
    invalid = frame["symbol"].eq("") | frame["execution_date"].isna() | ~np.isfinite(frame["split_factor"]) | frame["split_factor"].le(0)
    for row in frame.loc[invalid].itertuples(index=False):
        diagnostics.append(_diagnostic(getattr(row, "execution_date", ""), getattr(row, "symbol", ""), "missing_split_adjustment_factor", "warning", "Split event has a missing, non-finite, or non-positive factor and was not applied"))
    valid = frame.loc[~invalid, columns].drop_duplicates(columns).copy()
    if valid.empty:
        return valid
    return (
        valid.groupby(["symbol", "execution_date"], as_index=False)
        .agg(split_factor=("split_factor", "prod"), source=("source", lambda values: "|".join(sorted(set(map(str, values))))))
        .sort_values(["symbol", "execution_date"])
        .reset_index(drop=True)
    )


def _normalise_dividends(events: pd.DataFrame | None, diagnostics: list[dict]) -> pd.DataFrame:
    columns = ["symbol", "ex_dividend_date", "dividend_amount", "source"]
    if events is None or events.empty:
        return pd.DataFrame(columns=columns)
    frame = events.copy().rename(
        columns={
            "ticker": "symbol",
            "date": "ex_dividend_date",
            "execution_date": "ex_dividend_date",
            "cash_amount": "dividend_amount",
        }
    )
    if "symbol" not in frame or "ex_dividend_date" not in frame or "dividend_amount" not in frame:
        raise ValueError("Dividend events require symbol/ticker, ex_dividend_date/date, and dividend_amount/cash_amount")
    if "source" not in frame:
        frame["source"] = "unspecified"
    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    frame["ex_dividend_date"] = pd.to_datetime(frame["ex_dividend_date"], errors="coerce").dt.normalize()
    frame["dividend_amount"] = pd.to_numeric(frame["dividend_amount"], errors="coerce")
    invalid = frame["symbol"].eq("") | frame["ex_dividend_date"].isna() | ~np.isfinite(frame["dividend_amount"]) | frame["dividend_amount"].lt(0)
    for row in frame.loc[invalid].itertuples(index=False):
        diagnostics.append(_diagnostic(getattr(row, "ex_dividend_date", ""), getattr(row, "symbol", ""), "missing_dividend_amount", "warning", "Dividend event has a missing, non-finite, or negative cash amount and was not applied"))
    valid = frame.loc[~invalid, columns].drop_duplicates(columns).copy()
    if valid.empty:
        return valid
    return (
        valid.groupby(["symbol", "ex_dividend_date"], as_index=False)
        .agg(dividend_amount=("dividend_amount", "sum"), source=("source", lambda values: "|".join(sorted(set(map(str, values))))))
        .sort_values(["symbol", "ex_dividend_date"])
        .reset_index(drop=True)
    )


def _diagnostic(date, symbol: str, event_type: str, severity: str, message: str) -> dict:
    parsed = pd.to_datetime(date, errors="coerce")
    return {
        "date": "" if pd.isna(parsed) else pd.Timestamp(parsed).strftime("%Y-%m-%d"),
        "symbol": str(symbol),
        "event_type": event_type,
        "severity": severity,
        "message": message,
    }
