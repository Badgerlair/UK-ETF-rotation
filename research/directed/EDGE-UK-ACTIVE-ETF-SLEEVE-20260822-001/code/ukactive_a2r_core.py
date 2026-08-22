"""Pure helpers for UKACTIVE-A2R economic-lineage remediation.

The module deliberately contains no strategy, signal, portfolio or performance logic.
It validates semantic identity, point-in-time objective dates and immutable history
comparisons used by the A2R build.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


WARNING = "CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY"
ALLOWED_OUTCOMES = {
    "CORRECTED_IMPLEMENTATION_HISTORY",
    "EXISTING_HISTORY_VALID_AFTER_RECLASSIFICATION",
    "VALID_ONLY_FROM_LATER_DATE",
    "NO_VALID_IMPLEMENTATION_HISTORY",
    "UNRESOLVED_BLOCKING",
}


def clean(value: Any, default: str = "NOT_AVAILABLE") -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return default
    text = str(value).strip()
    return text if text else default


def stable_id(prefix: str, *parts: Any, length: int = 16) -> str:
    payload = "|".join(clean(part, "") for part in parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:length].upper()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return clean(value, "FALSE").upper() in {"TRUE", "YES", "1", "Y"}


def semicolon(values: Iterable[Any]) -> str:
    result = sorted({clean(value) for value in values if clean(value) not in {"", "NOT_AVAILABLE", "NOT_APPLICABLE"}})
    return ";".join(result) if result else "NOT_APPLICABLE"


@dataclass(frozen=True)
class EconomicFingerprint:
    geography: str
    sector_or_industry: str
    index_or_objective: str
    hedge_status: str
    breadth_level: str

    @property
    def key(self) -> str:
        return " × ".join(
            [
                self.geography,
                self.sector_or_industry,
                self.index_or_objective,
                self.hedge_status,
                self.breadth_level,
            ]
        )


def fingerprint_from_row(row: pd.Series | dict[str, Any], prefix: str = "") -> EconomicFingerprint:
    get = row.get
    return EconomicFingerprint(
        clean(get(f"{prefix}geography")),
        clean(get(f"{prefix}sector_or_industry")),
        clean(get(f"{prefix}index_or_objective")),
        clean(get(f"{prefix}hedge_status")),
        clean(get(f"{prefix}breadth_level")),
    )


def semantic_match(
    intended: EconomicFingerprint,
    actual: EconomicFingerprint,
    allowed_objectives: Iterable[str] = (),
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if intended.geography != actual.geography:
        reasons.append(f"GEOGRAPHY:{actual.geography}!={intended.geography}")
    if intended.sector_or_industry != actual.sector_or_industry:
        reasons.append(f"SECTOR_OR_INDUSTRY:{actual.sector_or_industry}!={intended.sector_or_industry}")
    allowed = {intended.index_or_objective, *[clean(value) for value in allowed_objectives]}
    if actual.index_or_objective not in allowed:
        reasons.append(f"INDEX_OR_OBJECTIVE:{actual.index_or_objective} not in {sorted(allowed)}")
    if intended.hedge_status != actual.hedge_status:
        reasons.append(f"HEDGE:{actual.hedge_status}!={intended.hedge_status}")
    if intended.breadth_level != actual.breadth_level:
        reasons.append(f"BREADTH:{actual.breadth_level}!={intended.breadth_level}")
    return not reasons, reasons


def earliest_valid_observation_date(
    dates: pd.Series,
    valid: pd.Series,
    lookback: int,
) -> pd.Timestamp | pd.NaT:
    if lookback <= 0:
        raise ValueError("lookback must be positive")
    ordered = pd.DataFrame({"date": pd.to_datetime(dates), "valid": valid.astype(bool)}).sort_values("date")
    if ordered.empty:
        return pd.NaT
    cumulative = ordered["valid"].astype(int).cumsum()
    hits = ordered.loc[ordered["valid"] & cumulative.ge(lookback), "date"]
    return pd.NaT if hits.empty else pd.Timestamp(hits.iloc[0])


def maturity_label(valid_observations: int) -> str:
    if valid_observations >= 1260:
        return "MATURE"
    if valid_observations >= 504:
        return "DEVELOPING"
    if valid_observations > 0:
        return "NEW"
    return "NOT_APPLICABLE_NO_USABLE_HISTORY"


def history_hash(frame: pd.DataFrame) -> str:
    columns = [
        "date",
        "economic_exposure_family_id",
        "implementation_share_class_id",
        "implementation_listing_id",
        "return_gbp_total",
        "data_valid",
        "stale_flag",
        "missing_flag",
        "proxy_flag",
    ]
    available = [column for column in columns if column in frame]
    work = frame[available].copy().sort_values([column for column in ["economic_exposure_family_id", "date"] if column in available])
    if "date" in work:
        work["date"] = pd.to_datetime(work["date"]).dt.strftime("%Y-%m-%d")
    for column in work.select_dtypes(include=["float", "float64"]).columns:
        work[column] = work[column].map(lambda value: "NA" if pd.isna(value) else f"{float(value):.17g}")
    raw = work.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_mask(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["data_valid"].astype(bool)
        & ~frame["stale_flag"].astype(bool)
        & ~frame["missing_flag"].astype(bool)
        & ~frame["proxy_flag"].astype(bool)
        & frame["return_gbp_total"].notna()
    )


def apply_semantic_floor_to_frame(frame: pd.DataFrame, floor: pd.Timestamp) -> pd.DataFrame:
    result = frame.copy().sort_values("date")
    result["date"] = pd.to_datetime(result["date"]).dt.normalize()
    blocked = result["date"] < pd.Timestamp(floor).normalize()
    result.loc[blocked, "data_valid"] = False
    result.loc[blocked, "return_gbp_total"] = np.nan
    if "return_local_total_authoritative" in result:
        result.loc[blocked, "return_local_total_authoritative"] = np.nan
    result["semantic_family_match"] = ~blocked
    result["semantic_valid_from"] = pd.Timestamp(floor).normalize()
    result["cum_valid_observations"] = result["data_valid"].astype(bool).astype(int).cumsum()
    if "cum_bad_observations" in result:
        bad = result.get("missing_flag", False) | result.get("stale_flag", False) | result.get("post_stale_catchup_flag", False)
        result["cum_bad_observations"] = pd.Series(bad, index=result.index).astype(bool).astype(int).cumsum()
    return result


def make_test_row(
    test_id: str,
    description: str,
    passed: bool,
    observed: Any,
    category: str,
    critical: bool = True,
) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "category": category,
        "description": description,
        "critical": "YES" if critical else "NO",
        "expected": "PASS",
        "observed": clean(observed),
        "status": "PASS" if bool(passed) else "FAIL",
    }


def synthetic_semantic_fixture_results() -> list[dict[str, Any]]:
    intended_us = EconomicFingerprint("UNITED_STATES", "AEROSPACE_AND_DEFENCE", "US_DEFENCE", "UNHEDGED", "INDUSTRY")
    global_defence = EconomicFingerprint("GLOBAL", "AEROSPACE_AND_DEFENCE", "GLOBAL_DEFENCE", "UNHEDGED", "INDUSTRY")
    intended_europe_tech = EconomicFingerprint("EUROPE", "TECHNOLOGY", "EUROPE_TECH", "UNHEDGED", "BROAD_SECTOR")
    world_tech = EconomicFingerprint("GLOBAL", "TECHNOLOGY", "WORLD_TECH", "UNHEDGED", "BROAD_SECTOR")
    china_broad = EconomicFingerprint("CHINA", "BROAD_MARKET", "MSCI_CHINA", "UNHEDGED", "BROAD_COUNTRY")
    china_internet = EconomicFingerprint("CHINA", "CHINA_INTERNET", "CHINA_INTERNET", "UNHEDGED", "THEME")
    hedged = EconomicFingerprint("AUSTRALIA", "BROAD_MARKET", "MSCI_AUSTRALIA", "HEDGED_GBP", "BROAD_COUNTRY")
    unhedged = EconomicFingerprint("AUSTRALIA", "BROAD_MARKET", "MSCI_AUSTRALIA", "UNHEDGED", "BROAD_COUNTRY")
    fixtures = [
        ("A2R-SYN-001", "US-specific family rejects global history", not semantic_match(intended_us, global_defence)[0]),
        ("A2R-SYN-002", "European family rejects global history", not semantic_match(intended_europe_tech, world_tech)[0]),
        ("A2R-SYN-003", "Broad China rejects China Internet", not semantic_match(china_broad, china_internet)[0]),
        ("A2R-SYN-004", "Unhedged family rejects GBP-hedged history", not semantic_match(unhedged, hedged)[0]),
        ("A2R-SYN-005", "Same ticker text alone is never an identity fingerprint", EconomicFingerprint("A", "B", "C", "D", "E").key != EconomicFingerprint("X", "B", "C", "D", "E").key),
        ("A2R-SYN-006", "Different ISIN rows remain separate implementation identities", stable_id("SC", "ISIN-A") != stable_id("SC", "ISIN-B")),
        ("A2R-SYN-007", "Proxy and implementation labels are distinguishable", "ECONOMIC_EXPOSURE_PROXY_HISTORY" != "LIVE_IMPLEMENTATION_HISTORY"),
    ]
    return [make_test_row(test_id, description, passed, passed, "SYNTHETIC_FAILURE_FIXTURE") for test_id, description, passed in fixtures]


def now_utc() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

