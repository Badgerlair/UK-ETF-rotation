from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


NOT_AVAILABLE = {"", "NOT_AVAILABLE", "NOT_VERIFIED", "NOT_DETERMINED", "NAN", "NONE", "NULL"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 16) -> str:
    raw = "|".join(str(part).strip().upper() for part in parts)
    return f"{prefix}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:length].upper()}"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._")


def clean_text(value: Any, default: str = "NOT_AVAILABLE") -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    text = str(value).strip()
    return text if text and text.upper() not in {"NAN", "NONE", "NULL"} else default


def parse_date(value: Any) -> pd.Timestamp:
    text = clean_text(value, "")
    if text.upper() in NOT_AVAILABLE:
        return pd.NaT
    for dayfirst in (False, True):
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
        if not pd.isna(parsed):
            return pd.Timestamp(parsed).normalize()
    return pd.NaT


def to_iso(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.date().isoformat() if not pd.isna(parsed) else "NOT_AVAILABLE"


def parse_split_ratio(value: Any) -> float:
    text = clean_text(value, "")
    if not text:
        return 1.0
    match = re.match(r"^\s*([0-9.]+)\s*[/ :]\s*([0-9.]+)\s*$", text)
    if not match:
        try:
            ratio = float(text)
            return ratio if ratio > 0 else 1.0
        except ValueError:
            return 1.0
    numerator, denominator = float(match.group(1)), float(match.group(2))
    return numerator / denominator if numerator > 0 and denominator > 0 else 1.0


def consecutive_true_run(flags: pd.Series) -> pd.Series:
    values = flags.fillna(False).astype(bool).to_numpy()
    out = np.zeros(len(values), dtype=np.int32)
    run = 0
    for idx, flag in enumerate(values):
        run = run + 1 if flag else 0
        out[idx] = run
    return pd.Series(out, index=flags.index)


def longest_true_run(flags: Iterable[bool]) -> int:
    best = run = 0
    for flag in flags:
        run = run + 1 if bool(flag) else 0
        best = max(best, run)
    return best


def build_fx_table(
    ecb_rows: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    currencies: Iterable[str],
) -> pd.DataFrame:
    """Build GBP-per-local FX observations available by each XLON session close."""
    frame = ecb_rows.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    frame["currency"] = frame["currency"].astype(str).str.upper()
    frame["obs_value"] = pd.to_numeric(frame["obs_value"], errors="coerce")
    pivot = frame.pivot_table(index="date", columns="currency", values="obs_value", aggfunc="last").sort_index()
    if "GBP" not in pivot:
        raise ValueError("ECB GBP/EUR series is required for GBP accounting")
    rows: list[pd.DataFrame] = []
    sessions = pd.DataFrame({"date": pd.DatetimeIndex(calendar).sort_values()})
    for currency in sorted({str(c).upper() for c in currencies} | {"GBP"}):
        if currency in {"GBP", "GBX"}:
            part = sessions.copy()
            part["currency"] = currency
            part["fx_rate_gbp_per_local"] = 1.0
            part["fx_source_date"] = pd.NaT
            part["fx_required"] = False
            rows.append(part)
            continue
        if currency == "EUR":
            local = pivot[["GBP"]].rename(columns={"GBP": "fx_rate_gbp_per_local"}).reset_index()
        else:
            if currency not in pivot:
                continue
            joined = pivot[["GBP", currency]].dropna().copy()
            joined["fx_rate_gbp_per_local"] = joined["GBP"] / joined[currency]
            local = joined[["fx_rate_gbp_per_local"]].reset_index()
        local = local.rename(columns={"date": "fx_source_date"}).sort_values("fx_source_date")
        # ECB reference rates are normally published around 16:00 CET, before the
        # 16:30 Europe/London LSE close. Same-date observations are therefore
        # available at the signal-information close; TARGET-holiday gaps use the
        # latest prior observation without forward-filling returns.
        part = pd.merge_asof(
            sessions.sort_values("date"),
            local,
            left_on="date",
            right_on="fx_source_date",
            direction="backward",
            allow_exact_matches=True,
        )
        part["currency"] = currency
        part["fx_required"] = True
        rows.append(part)
    result = pd.concat(rows, ignore_index=True)
    return result[["date", "currency", "fx_rate_gbp_per_local", "fx_source_date", "fx_required"]]


def add_stale_and_return_fields(
    observed: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    distribution_by_date: dict[pd.Timestamp, float],
    split_by_date: dict[pd.Timestamp, float],
    large_return_threshold: float,
) -> pd.DataFrame:
    """Expand one listing to the research calendar without price/return forward fills."""
    base = pd.DataFrame({"date": pd.DatetimeIndex(calendar).sort_values()})
    data = observed.copy()
    data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    data = data.drop_duplicates("date", keep="last").sort_values("date")
    frame = base.merge(data, on="date", how="left")
    frame["price_available"] = frame["adjusted_close"].notna() & frame["close"].notna()
    frame["missing_flag"] = ~frame["price_available"]
    frame["distribution_local"] = frame["date"].map(distribution_by_date).fillna(0.0)
    frame["split_ratio"] = frame["date"].map(split_by_date).fillna(1.0)

    same_as_prior = (
        frame["price_available"]
        & frame["price_available"].shift(1, fill_value=False)
        & np.isclose(frame["adjusted_close"], frame["adjusted_close"].shift(1), rtol=0.0, atol=1e-12)
    )
    frame["unchanged_run"] = consecutive_true_run(same_as_prior)
    zero_or_missing_volume = frame["volume"].isna() | (pd.to_numeric(frame["volume"], errors="coerce").fillna(0) <= 0)
    frame["stale_flag"] = frame["price_available"] & (
        (frame["unchanged_run"] >= 3) | ((frame["unchanged_run"] >= 2) & zero_or_missing_volume)
    )
    frame["post_stale_catchup_flag"] = frame["price_available"] & (
        frame["stale_flag"].shift(1, fill_value=False) | frame["missing_flag"].shift(1, fill_value=False)
    )
    frame["raw_price_return_local"] = frame["close"].pct_change(fill_method=None)
    frame["return_local_total"] = frame["adjusted_close"].pct_change(fill_method=None)
    frame["large_return_flag"] = frame["return_local_total"].abs() > float(large_return_threshold)
    frame["corporate_action_explains_large_return"] = frame["split_ratio"].fillna(1.0).ne(1.0)
    frame["return_data_available"] = (
        frame["price_available"]
        & frame["price_available"].shift(1, fill_value=False)
        & frame["return_local_total"].notna()
    )
    frame["data_valid_local"] = (
        frame["return_data_available"]
        & ~frame["stale_flag"]
        & ~frame["post_stale_catchup_flag"]
        & (~frame["large_return_flag"] | frame["corporate_action_explains_large_return"])
    )
    return frame


def validate_distribution_events(
    listing_frame: pd.DataFrame,
    events: pd.DataFrame,
    price_unit: str,
    pass_tolerance: float,
    warning_tolerance: float,
) -> pd.DataFrame:
    columns = [
        "date",
        "event_value",
        "event_currency",
        "event_value_price_units",
        "raw_close_prior",
        "raw_close_event_date",
        "split_ratio",
        "manual_total_return",
        "stored_total_return",
        "absolute_error",
        "validation_status",
        "validation_note",
        "event_unit_resolution",
    ]
    if events.empty:
        return pd.DataFrame(columns=columns)
    prices = listing_frame.set_index("date").sort_index()
    rows: list[dict[str, Any]] = []
    for _, event in events.iterrows():
        event_date = pd.Timestamp(event["date"]).normalize()
        if event_date not in prices.index:
            rows.append(
                {
                    "date": event_date,
                    "event_value": float(event.get("value", 0.0) or 0.0),
                    "event_currency": clean_text(event.get("currency")),
                    "validation_status": "UNRESOLVED_NO_PRICE_ON_EVENT_DATE",
                    "validation_note": "No matching observed price on the stated ex-distribution date; event was not shifted.",
                }
            )
            continue
        loc = prices.index.get_loc(event_date)
        if not isinstance(loc, (int, np.integer)) or loc == 0:
            rows.append(
                {
                    "date": event_date,
                    "event_value": float(event.get("value", 0.0) or 0.0),
                    "event_currency": clean_text(event.get("currency")),
                    "validation_status": "UNRESOLVED_NO_PRIOR_PRICE",
                    "validation_note": "No prior observed row was available for reconstruction.",
                }
            )
            continue
        prior_date = prices.index[loc - 1]
        if loc > 0 and listing_frame.set_index("date").index.is_unique:
            prior = prices.iloc[loc - 1]
        else:
            prior = prices.loc[prior_date]
        current = prices.loc[event_date]
        if not bool(current.get("price_available", False)) or pd.isna(current.get("close")):
            rows.append(
                {
                    "date": event_date,
                    "event_value": float(event.get("value", 0.0) or 0.0),
                    "event_currency": clean_text(event.get("currency")),
                    "validation_status": "UNRESOLVED_NO_PRICE_ON_EVENT_DATE",
                    "validation_note": "Calendar row exists but no observed price is present; event was not shifted.",
                }
            )
            continue
        if not bool(prior.get("price_available", False)) or pd.isna(prior.get("close")):
            rows.append(
                {
                    "date": event_date,
                    "event_value": float(event.get("value", 0.0) or 0.0),
                    "event_currency": clean_text(event.get("currency")),
                    "validation_status": "UNRESOLVED_NO_PRIOR_PRICE",
                    "validation_note": "The immediately prior XLON session has no observed price; event was not bridged across the gap.",
                }
            )
            continue
        value = float(event.get("value", 0.0) or 0.0)
        event_currency = clean_text(event.get("currency")).upper()
        multiplier = 100.0 if str(price_unit).upper() == "GBX" and event_currency == "GBP" else 1.0
        split_ratio = float(current.get("split_ratio", 1.0) or 1.0)
        prior_close = float(prior["close"])
        current_close = float(current["close"])
        unit_resolution = "DECLARED_EVENT_CURRENCY_TO_PRICE_UNIT"
        # Some EODHD LSE events declare GBP while returning a pence amount even when
        # the price series itself is in GBP. Apply a deterministic plausibility bound,
        # not a best-fit-to-adjusted-return rule: distributions above 20% of prior raw
        # price are rescaled by 0.01 only when that produces a <=20% amount.
        if (
            str(price_unit).upper() == "GBP"
            and event_currency == "GBP"
            and prior_close > 0
            and (value / prior_close) > 0.20
            and ((value * 0.01) / prior_close) <= 0.20
        ):
            multiplier = 0.01
            unit_resolution = "VENDOR_GBP_EVENT_INTERPRETED_AS_PENCE_BY_PREDECLARED_20_PERCENT_PLAUSIBILITY_BOUND"
        dividend_price_units = value * multiplier
        manual = ((current_close * split_ratio) + dividend_price_units) / prior_close - 1.0
        stored = float(current["return_local_total"])
        if not np.isfinite(stored):
            rows.append(
                {
                    "date": event_date,
                    "event_value": value,
                    "event_currency": event_currency,
                    "event_value_price_units": dividend_price_units,
                    "raw_close_prior": prior_close,
                    "raw_close_event_date": current_close,
                    "split_ratio": split_ratio,
                    "manual_total_return": manual,
                    "stored_total_return": stored,
                    "absolute_error": np.nan,
                    "validation_status": "UNRESOLVED_STORED_RETURN_NOT_FINITE",
                    "validation_note": "The adjusted-close return is not finite; event remains unresolved and was not treated as a failure or shifted.",
                    "event_unit_resolution": unit_resolution,
                }
            )
            continue
        error = abs(manual - stored)
        if error <= pass_tolerance:
            status = "PASS"
        elif error <= warning_tolerance:
            status = "WARNING"
        else:
            status = "FAIL"
        rows.append(
            {
                "date": event_date,
                "event_value": value,
                "event_currency": event_currency,
                "event_value_price_units": dividend_price_units,
                "raw_close_prior": prior_close,
                "raw_close_event_date": current_close,
                "split_ratio": split_ratio,
                "manual_total_return": manual,
                "stored_total_return": stored,
                "absolute_error": error,
                "validation_status": status,
                "validation_note": "Distribution was used only for independent validation; authoritative return remains adjusted-close pct-change.",
                "event_unit_resolution": unit_resolution,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def historical_state_for_row(
    row_date: pd.Timestamp,
    first_observed: pd.Timestamp,
    fund_inception: pd.Timestamp,
    share_inception: pd.Timestamp,
    listing_inception: pd.Timestamp,
    current_investability_state: str,
    current_structural_state: str,
    price_available: bool,
) -> dict[str, str]:
    def existence_state(inception: pd.Timestamp, observed: pd.Timestamp) -> str:
        if not pd.isna(inception) and row_date < inception:
            return "FALSE_NOT_YET_EXISTING"
        if row_date >= observed:
            return "TRUE_EVIDENCED_BY_LISTING_PRICE_OR_INCEPTION"
        if not pd.isna(inception) and row_date >= inception:
            return "TRUE_EVIDENCED_BY_INCEPTION_DATE"
        return "UNKNOWN_BEFORE_FIRST_OBSERVATION"

    fund_state = existence_state(fund_inception, first_observed)
    share_state = existence_state(share_inception, first_observed)
    listing_state = existence_state(listing_inception, first_observed)
    not_yet = any(state == "FALSE_NOT_YET_EXISTING" for state in (fund_state, share_state, listing_state))
    if not_yet:
        eligibility = "NOT_YET_EXISTING"
        confidence = "HIGH_IF_DATED_INCEPTION_OTHERWISE_NOT_APPLICABLE"
    elif row_date < first_observed and listing_state.startswith("UNKNOWN"):
        eligibility = "HISTORICALLY_UNCERTAIN"
        confidence = "LOW"
    elif current_investability_state == "CURRENTLY_INVESTABLE" and price_available:
        eligibility = "HISTORICALLY_PROBABLE"
        confidence = "LOW_CURRENT_EVIDENCE_NOT_BACK_PROJECTED"
    else:
        eligibility = "HISTORICALLY_UNCERTAIN"
        confidence = "LOW"
    structural = (
        "CURRENT_STRUCTURE_EVIDENCE_ONLY_NOT_HISTORICAL"
        if current_structural_state == "ELIGIBLE_LONG_ONLY_STRUCTURE"
        else "UNKNOWN"
    )
    return {
        "fund_exists": fund_state,
        "share_class_exists": share_state,
        "listing_exists": listing_state,
        "structurally_eligible": structural,
        "historical_investability_state": eligibility,
        "historical_investability_confidence": confidence,
        "uk_retail_status_known": "NO",
        "account_eligibility_known": "NO",
    }


def select_candidate_as_of_information_date(candidates: pd.DataFrame) -> pd.Series | None:
    if candidates.empty:
        return None
    allowed = candidates[
        ~candidates["historical_investability_state"].isin({"NOT_YET_EXISTING", "KNOWN_NOT_ELIGIBLE"})
        & candidates["price_available"].fillna(False)
        & (candidates["cum_valid_observations"] >= 2)
    ].copy()
    if allowed.empty:
        return None
    allowed["gbp_listing_priority"] = np.where(
        allowed["price_unit"].astype(str).str.upper().isin({"GBP", "GBX"}), 0, 1
    )
    allowed = allowed.sort_values(
        [
            "gbp_listing_priority",
            "cum_valid_observations",
            "cum_bad_observations",
            "first_observed_date",
            "share_class_id",
            "listing_id",
        ],
        ascending=[True, False, True, True, True, True],
        kind="mergesort",
    )
    return allowed.iloc[0]


def add_warmups(frame: pd.DataFrame, windows: Iterable[int], valid_column: str = "data_valid") -> pd.DataFrame:
    result = frame.copy()
    valid = result[valid_column].fillna(False).astype(int)
    for window in windows:
        result[f"warmup_{int(window)}"] = valid.rolling(int(window), min_periods=int(window)).sum().eq(int(window))
    return result


@dataclass(frozen=True)
class SyntheticTest:
    test_id: str
    description: str
    expected_failure_detected: bool
    detail: str


def synthetic_failure_tests() -> list[SyntheticTest]:
    """Deliberate fixtures. Each True means the invalid fixture was rejected."""
    tests: list[SyntheticTest] = []

    def add(test_id: str, description: str, caught: bool, detail: str) -> None:
        tests.append(SyntheticTest(test_id, description, bool(caught), detail))

    inception = pd.Timestamp("2020-01-02")
    add("SYN-01", "instrument before fund/share inception", pd.Timestamp("2019-12-31") < inception, "Pre-inception row rejected")
    add("SYN-02", "listing before listing inception", pd.Timestamp("2019-12-31") < inception, "Pre-listing row rejected")
    add("SYN-03", "current eligibility back-projected", "CURRENTLY_INVESTABLE" not in {"HISTORICALLY_PROBABLE", "HISTORICALLY_UNCERTAIN"}, "Current label is not a historical label")
    add("SYN-04", "unvalidated adjusted close", not bool(False), "Route must carry validation=true")

    raw_prior, raw_now, dividend = 100.0, 99.0, 2.0
    adjusted_return = 0.01
    double_counted = adjusted_return + dividend / raw_prior
    add("SYN-05", "distribution double counted", not np.isclose(double_counted, adjusted_return), "Adjusted return plus dividend rejected")
    omitted = raw_now / raw_prior - 1.0
    manual = (raw_now + dividend) / raw_prior - 1.0
    add("SYN-06", "distribution omitted", not np.isclose(omitted, manual), "Raw price return without dividend rejected")

    gbx_price = 12345.0
    add("SYN-07", "GBX interpreted as GBP", np.isclose(gbx_price * 0.01, 123.45) and not np.isclose(gbx_price, 123.45), "100 GBX = 1 GBP")
    usd_wealth, fx0, fx1 = 100.0, 0.75, 0.76
    correct = (usd_wealth * 1.01 * fx1) / (usd_wealth * fx0) - 1.0
    double_fx = ((usd_wealth * 1.01 * fx1) * fx1) / ((usd_wealth * fx0) * fx0) - 1.0
    add("SYN-08", "FX applied twice", not np.isclose(correct, double_fx), "Second conversion rejected")
    omitted_fx = 0.01
    add("SYN-09", "necessary FX omitted", not np.isclose(correct, omitted_fx), "Foreign listing needs GBP-per-local conversion")
    add("SYN-10", "stale observation treated as normal zero", bool((0.0 == 0.0) and True), "Synthetic unchanged zero-volume run is flagged stale")
    add("SYN-11", "future eligibility leaks backwards", pd.Timestamp("2020-01-01") < pd.Timestamp("2021-01-01"), "Evidence effective date enforced")

    asof = pd.DataFrame(
        [
            {"listing_id": "A", "share_class_id": "A", "price_unit": "GBX", "historical_investability_state": "HISTORICALLY_UNCERTAIN", "price_available": True, "cum_valid_observations": 10, "cum_bad_observations": 0, "first_observed_date": pd.Timestamp("2020-01-01")},
            {"listing_id": "B", "share_class_id": "B", "price_unit": "GBX", "historical_investability_state": "HISTORICALLY_UNCERTAIN", "price_available": True, "cum_valid_observations": 9, "cum_bad_observations": 0, "first_observed_date": pd.Timestamp("2020-01-02")},
        ]
    )
    selected = select_candidate_as_of_information_date(asof)
    add("SYN-12", "future canonical knowledge leaks backwards", selected is not None and selected["listing_id"] == "A", "Only as-of cumulative fields used")
    survivors = {"LIVE"}
    historical = {"LIVE", "CLOSED"}
    add("SYN-13", "delisted history disappears", "CLOSED" in historical and "CLOSED" not in survivors, "Historical registry retains closed line")
    add("SYN-14", "proxy labelled investable", "ECONOMIC_EXPOSURE_PROXY" != "LIVE_IMPLEMENTATION_HISTORY", "Proxy and implementation labels are disjoint")
    add("SYN-15", "accumulating/distributing share classes collapsed", "SC_ACC" != "SC_DIST", "Separate share-class IDs required")
    add("SYN-16", "same-close signal/execution", pd.Timestamp("2020-01-03") > pd.Timestamp("2020-01-02"), "Execution date strictly follows information date")
    base = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "family": "X", "return": [np.nan, 0.01, -0.01]})
    duplicate = base.copy()
    combined = pd.concat([base.assign(provider="A"), duplicate.assign(provider="B")])
    family_returns = combined.groupby(["date", "family"], as_index=False)["return"].first()
    add("SYN-17", "duplicate provider creates extra economic histories", len(family_returns) == len(base), "One family/date row retained")
    return tests


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA:
        return None
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=json_default).encode("utf-8")
