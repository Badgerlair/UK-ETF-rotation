"""Shared deterministic utilities for UKACTIVE-A3R2.

The module deliberately contains no strategy parameters. Those are frozen in
config/UKACTIVE_A3R2_POLICY_v1.json before portfolio results are calculated.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROGRAMME_ROOT = Path(__file__).resolve().parents[1]
PLATFORM_ROOT = PROGRAMME_ROOT.parents[2]
POLICY_PATH = PROGRAMME_ROOT / "config" / "UKACTIVE_A3R2_POLICY_v1.json"
WARNING = "HISTORICAL UK RETAIL, ACCOUNT AND BROKER ELIGIBILITY REMAIN UNRESOLVED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=PLATFORM_ROOT, text=True).strip()


def write_csv(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    check = pd.read_csv(path, nrows=5)
    if list(check.columns) != list(frame.columns):
        raise AssertionError(f"CSV round-trip schema mismatch: {path}")
    return audit_file(path, rows=len(frame), columns=len(frame.columns))


def write_parquet(path: Path, frame: pd.DataFrame) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, compression="zstd")
    check = pd.read_parquet(path)
    if len(check) != len(frame) or list(check.columns) != list(frame.columns):
        raise AssertionError(f"Parquet round-trip mismatch: {path}")
    return audit_file(path, rows=len(frame), columns=len(frame.columns))


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    return audit_file(path)


def write_text(path: Path, value: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8")
    return audit_file(path)


def audit_file(path: Path, *, rows: int | None = None, columns: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if rows is not None:
        result["rows"] = int(rows)
    if columns is not None:
        result["columns"] = int(columns)
    return result


def stable_id(prefix: str, *parts: object) -> str:
    text = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16].upper()}"


def bool_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def expanding_prior_quantile(values: pd.Series, quantile: float, minimum: int) -> pd.Series:
    """Prior-only expanding quantile; date T never participates in its threshold."""
    shifted = values.shift(1)
    return shifted.expanding(min_periods=minimum).quantile(quantile)


def newey_west_mean(values: pd.Series | np.ndarray, lags: int) -> dict[str, float | int]:
    array = np.asarray(pd.Series(values).dropna(), dtype=float)
    n = len(array)
    if n == 0:
        return {"n": 0, "mean": np.nan, "standard_error": np.nan, "t_stat": np.nan, "p_value": np.nan}
    mean = float(array.mean())
    centered = array - mean
    gamma0 = float(np.dot(centered, centered) / n)
    variance = gamma0
    for lag in range(1, min(int(lags), n - 1) + 1):
        covariance = float(np.dot(centered[lag:], centered[:-lag]) / n)
        variance += 2.0 * (1.0 - lag / (lags + 1.0)) * covariance
    standard_error = float(np.sqrt(max(variance, 0.0) / n))
    t_stat = mean / standard_error if standard_error > 0 else np.nan
    try:
        from scipy.stats import norm

        p_value = float(2.0 * norm.sf(abs(t_stat))) if np.isfinite(t_stat) else np.nan
    except Exception:
        p_value = np.nan
    return {"n": n, "mean": mean, "standard_error": standard_error, "t_stat": t_stat, "p_value": p_value}


def circular_block_bootstrap_mean_ci(
    values: pd.Series | np.ndarray,
    *,
    block_length: int,
    replications: int,
    seed: int,
) -> dict[str, float | int]:
    array = np.asarray(pd.Series(values).dropna(), dtype=float)
    n = len(array)
    if n < 2 or replications <= 0:
        return {"n": n, "ci_low": np.nan, "ci_high": np.nan, "replications": 0}
    rng = np.random.default_rng(seed)
    length = max(1, min(int(block_length), n))
    starts_needed = int(np.ceil(n / length))
    means = np.empty(replications, dtype=float)
    offsets = np.arange(length)
    for index in range(replications):
        starts = rng.integers(0, n, size=starts_needed)
        sample_index = ((starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        means[index] = array[sample_index].mean()
    return {
        "n": n,
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
        "replications": int(replications),
    }


def benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=p_values.index, dtype=float)
    valid = p_values.dropna().astype(float)
    if valid.empty:
        return result
    ordered = valid.sort_values()
    m = len(ordered)
    raw = ordered.to_numpy() * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(raw[::-1])[::-1].clip(0, 1)
    result.loc[ordered.index] = adjusted
    return result
