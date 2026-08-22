from __future__ import annotations

import hashlib
import json
import math
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 16) -> str:
    payload = "|".join(str(part).strip().upper() for part in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length].upper()}"


def rolling_total_return(returns: np.ndarray, lookback: int) -> np.ndarray:
    """Total return ending at each row; every canonical-session return is required."""
    frame = pd.DataFrame(np.asarray(returns, dtype=float))
    if ((frame <= -1.0) & frame.notna()).any().any():
        raise ValueError("A valid total-return observation cannot be <= -100%")
    log_returns = np.log1p(frame)
    rolling = log_returns.rolling(int(lookback), min_periods=int(lookback)).sum()
    return np.expm1(rolling.to_numpy())


def twelve_minus_one_return(returns: np.ndarray, total_window: int = 252, skip: int = 21) -> np.ndarray:
    """TR(t-total_window,t-skip), while requiring the full total_window to be valid."""
    frame = pd.DataFrame(np.asarray(returns, dtype=float))
    if ((frame <= -1.0) & frame.notna()).any().any():
        raise ValueError("A valid total-return observation cannot be <= -100%")
    log_returns = np.log1p(frame)
    included = int(total_window) - int(skip)
    value = log_returns.shift(int(skip)).rolling(included, min_periods=included).sum()
    full_valid = frame.rolling(int(total_window), min_periods=int(total_window)).count().eq(int(total_window))
    value = value.where(full_valid)
    return np.expm1(value.to_numpy())


def realised_volatility(returns: np.ndarray, window: int = 63) -> np.ndarray:
    frame = pd.DataFrame(np.asarray(returns, dtype=float))
    return (frame.rolling(int(window), min_periods=int(window)).std(ddof=1) * math.sqrt(252.0)).to_numpy()


def total_return_trend_qualification(returns: np.ndarray, window: int = 252) -> np.ndarray:
    """Binary total-return index above trailing SMA; mask requires a fully valid window."""
    frame = pd.DataFrame(np.asarray(returns, dtype=float))
    log_returns = np.log1p(frame)
    cumulative_log = log_returns.fillna(0.0).cumsum()
    # Column-level centring avoids numerical overflow and does not change an index/SMA ratio.
    cumulative_log = cumulative_log - cumulative_log.iloc[0]
    wealth = np.exp(cumulative_log)
    moving_average = wealth.rolling(int(window), min_periods=int(window)).mean()
    full_valid = frame.rolling(int(window), min_periods=int(window)).count().eq(int(window))
    out = (wealth > moving_average).astype(float).where(full_valid)
    return out.to_numpy()


def forward_total_return(returns: np.ndarray, horizon: int) -> np.ndarray:
    """Product of returns t+1 through t+h; date-t return is excluded."""
    frame = pd.DataFrame(np.asarray(returns, dtype=float))
    log_returns = np.log1p(frame)
    ending_sum = log_returns.rolling(int(horizon), min_periods=int(horizon)).sum()
    forward = ending_sum.shift(-int(horizon))
    return np.expm1(forward.to_numpy())


def winsorised_zscore_rows(values: np.ndarray, lower: float = 0.05, upper: float = 0.95) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        low = np.nanquantile(arr, lower, axis=1, keepdims=True)
        high = np.nanquantile(arr, upper, axis=1, keepdims=True)
        clipped = np.clip(arr, low, high)
        mean = np.nanmean(clipped, axis=1, keepdims=True)
        std = np.nanstd(clipped, axis=1, ddof=0, keepdims=True)
    with np.errstate(all="ignore"):
        out = (clipped - mean) / std
    out[~np.isfinite(arr)] = np.nan
    out[(~np.isfinite(std) | (std <= 0)).repeat(arr.shape[1], axis=1)] = np.nan
    return out


def grouped_winsorised_zscore_rows(
    values: np.ndarray,
    groups: Sequence[str] | None,
    minimum_group_size: int = 3,
) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if groups is None:
        return winsorised_zscore_rows(arr)
    out = np.full_like(arr, np.nan, dtype=float)
    labels = np.asarray(groups, dtype=object)
    for label in sorted(set(labels.tolist())):
        cols = np.flatnonzero(labels == label)
        if len(cols) < int(minimum_group_size):
            continue
        part = arr[:, cols]
        z = winsorised_zscore_rows(part)
        valid_count = np.isfinite(part).sum(axis=1)
        z[valid_count < int(minimum_group_size), :] = np.nan
        out[:, cols] = z
    return out


def percentile_rank_rows(
    values: np.ndarray,
    groups: Sequence[str] | None = None,
    minimum_group_size: int = 1,
) -> np.ndarray:
    """Date-level percentile ranks. Missing values remain missing."""
    arr = np.asarray(values, dtype=float)
    if groups is None:
        return pd.DataFrame(arr).rank(axis=1, method="average", pct=True).to_numpy()
    labels = np.asarray(groups, dtype=object)
    out = np.full_like(arr, np.nan, dtype=float)
    for label in sorted(set(labels.tolist())):
        cols = np.flatnonzero(labels == label)
        if len(cols) < int(minimum_group_size):
            continue
        part = arr[:, cols]
        ranked = pd.DataFrame(part).rank(axis=1, method="average", pct=True).to_numpy(copy=True)
        valid_count = np.isfinite(part).sum(axis=1)
        ranked[valid_count < int(minimum_group_size), :] = np.nan
        out[:, cols] = ranked
    return out


def rowwise_correlation(x: np.ndarray, y: np.ndarray, minimum_count: int = 5) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(x, dtype=float)
    right = np.asarray(y, dtype=float)
    mask = np.isfinite(left) & np.isfinite(right)
    count = mask.sum(axis=1).astype(np.int32)
    x0 = np.where(mask, left, 0.0)
    y0 = np.where(mask, right, 0.0)
    denom = np.maximum(count, 1)[:, None]
    x_mean = x0.sum(axis=1, keepdims=True) / denom
    y_mean = y0.sum(axis=1, keepdims=True) / denom
    xd = np.where(mask, left - x_mean, 0.0)
    yd = np.where(mask, right - y_mean, 0.0)
    numerator = (xd * yd).sum(axis=1)
    denominator = np.sqrt((xd * xd).sum(axis=1) * (yd * yd).sum(axis=1))
    corr = np.divide(numerator, denominator, out=np.full(len(left), np.nan), where=denominator > 0)
    corr[count < int(minimum_count)] = np.nan
    return corr, count


def newey_west_mean(values: Iterable[float], lag: int) -> dict[str, float | int]:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    n = int(len(x))
    if n == 0:
        return {
            "observation_count": 0,
            "mean": np.nan,
            "median": np.nan,
            "standard_deviation": np.nan,
            "information_ratio": np.nan,
            "positive_frequency": np.nan,
            "hac_lag": int(lag),
            "hac_standard_error": np.nan,
            "hac_t_statistic": np.nan,
            "hac_p_value": np.nan,
            "confidence_interval_low": np.nan,
            "confidence_interval_high": np.nan,
        }
    mean = float(np.mean(x))
    median = float(np.median(x))
    std = float(np.std(x, ddof=1)) if n > 1 else np.nan
    centred = x - mean
    gamma0 = float(np.dot(centred, centred) / n)
    effective_lag = min(max(int(lag), 0), max(n - 1, 0))
    long_run_variance = gamma0
    for current_lag in range(1, effective_lag + 1):
        weight = 1.0 - current_lag / (effective_lag + 1.0)
        gamma = float(np.dot(centred[current_lag:], centred[:-current_lag]) / n)
        long_run_variance += 2.0 * weight * gamma
    long_run_variance = max(long_run_variance, 0.0)
    standard_error = math.sqrt(long_run_variance / n) if n > 0 else np.nan
    t_stat = mean / standard_error if standard_error and np.isfinite(standard_error) else np.nan
    p_value = float(2.0 * norm.sf(abs(t_stat))) if np.isfinite(t_stat) else np.nan
    critical = float(norm.ppf(0.975))
    return {
        "observation_count": n,
        "mean": mean,
        "median": median,
        "standard_deviation": std,
        "information_ratio": mean / std if std and np.isfinite(std) else np.nan,
        "positive_frequency": float(np.mean(x > 0.0)),
        "hac_lag": effective_lag,
        "hac_standard_error": standard_error,
        "hac_t_statistic": t_stat,
        "hac_p_value": p_value,
        "confidence_interval_low": mean - critical * standard_error if np.isfinite(standard_error) else np.nan,
        "confidence_interval_high": mean + critical * standard_error if np.isfinite(standard_error) else np.nan,
    }


def benjamini_hochberg(p_values: Sequence[float]) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    out = np.full_like(p, np.nan)
    finite = np.isfinite(p)
    values = p[finite]
    if values.size == 0:
        return out
    order = np.argsort(values)
    ordered = values[order]
    m = len(ordered)
    adjusted = ordered * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    restored = np.empty_like(adjusted)
    restored[order] = adjusted
    out[finite] = restored
    return out


def circular_block_bootstrap_mean_ci(
    values: Iterable[float],
    block_length: int,
    replications: int,
    seed: int,
    confidence: float = 0.95,
) -> dict[str, float | int]:
    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 2:
        return {"observation_count": int(n), "block_length": int(block_length), "replications": 0, "ci_low": np.nan, "ci_high": np.nan}
    length = min(max(1, int(block_length)), n)
    blocks_needed = int(math.ceil(n / length))
    rng = np.random.default_rng(int(seed))
    means = np.empty(int(replications), dtype=float)
    offsets = np.arange(length)
    for rep in range(int(replications)):
        starts = rng.integers(0, n, size=blocks_needed)
        indices = ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]
        means[rep] = float(np.mean(x[indices]))
    alpha = (1.0 - float(confidence)) / 2.0
    return {
        "observation_count": int(n),
        "block_length": int(length),
        "replications": int(replications),
        "ci_low": float(np.quantile(means, alpha)),
        "ci_high": float(np.quantile(means, 1.0 - alpha)),
    }


def observation_positions(dates: pd.DatetimeIndex, frequency_id: str) -> np.ndarray:
    dates = pd.DatetimeIndex(dates)
    frame = pd.DataFrame({"date": dates, "position": np.arange(len(dates), dtype=int)})
    if frequency_id == "MONTH_END":
        selected = frame.groupby(frame["date"].dt.to_period("M"), sort=True).tail(1)
        return selected["position"].to_numpy(dtype=int)
    weekday_targets = {
        "WEEKLY_MONDAY": 0,
        "WEEKLY_TUESDAY": 1,
        "WEEKLY_WEDNESDAY": 2,
        "WEEKLY_THURSDAY": 3,
        "WEEKLY_FRIDAY": 4,
    }
    if frequency_id not in weekday_targets:
        raise ValueError(f"Unsupported observation frequency: {frequency_id}")
    target = weekday_targets[frequency_id]
    iso = frame["date"].dt.isocalendar()
    frame["iso_year"] = iso["year"].astype(int)
    frame["iso_week"] = iso["week"].astype(int)
    frame["distance"] = (frame["date"].dt.weekday - target).abs()
    frame["after_target"] = (frame["date"].dt.weekday > target).astype(int)
    # Closest session; ties choose the earlier session and therefore cannot use a later close unnecessarily.
    selected = (
        frame.sort_values(["iso_year", "iso_week", "distance", "after_target", "date"])
        .groupby(["iso_year", "iso_week"], sort=True)
        .head(1)
        .sort_values("date")
    )
    return selected["position"].to_numpy(dtype=int)


def hac_lag_for_horizon(horizon: int, frequency_id: str) -> int:
    spacing = 21 if frequency_id == "MONTH_END" else 5
    return max(1, int(math.ceil(int(horizon) / spacing)) - 1)


def subperiod_bounds(
    subperiod: dict[str, Any],
    final_date: pd.Timestamp,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if subperiod.get("start_relative_years") is not None:
        start = final_date - pd.DateOffset(years=int(subperiod["start_relative_years"]))
    else:
        start = pd.Timestamp(subperiod["start"]) if subperiod.get("start") else None
    end = pd.Timestamp(subperiod["end"]) if subperiod.get("end") else None
    return start, end


def safe_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan
