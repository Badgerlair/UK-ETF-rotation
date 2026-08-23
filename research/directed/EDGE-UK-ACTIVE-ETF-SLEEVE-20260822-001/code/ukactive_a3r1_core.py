from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(*parts: object, base: int = 20260823) -> int:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return (base + int(hashlib.sha256(payload).hexdigest()[:8], 16)) % (2**32 - 1)


def _validate_returns(frame: pd.DataFrame) -> pd.DataFrame:
    values = frame.astype(float)
    if ((values <= -1.0) & values.notna()).any().any():
        raise ValueError("A valid total-return observation cannot be <= -100%")
    return values


def strict_rolling_total_return(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    """Return over the latest ``window`` rows, requiring every row to be valid."""
    values = _validate_returns(frame)
    logs = np.log1p(values)
    total = logs.rolling(int(window), min_periods=int(window)).sum()
    count = values.notna().rolling(int(window), min_periods=int(window)).sum()
    return np.expm1(total).where(count.eq(int(window)))


def strict_segment_total_return(frame: pd.DataFrame, start_lag: int, end_lag: int) -> pd.DataFrame:
    """Non-overlapping trailing segment: lags ``start_lag`` through ``end_lag-1``."""
    if int(start_lag) < 0 or int(end_lag) <= int(start_lag):
        raise ValueError("Segment lags must satisfy 0 <= start_lag < end_lag")
    values = _validate_returns(frame).shift(int(start_lag))
    width = int(end_lag) - int(start_lag)
    logs = np.log1p(values)
    total = logs.rolling(width, min_periods=width).sum()
    count = values.notna().rolling(width, min_periods=width).sum()
    return np.expm1(total).where(count.eq(width))


def strict_forward_total_return(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Product of returns t+1...t+h; the date-t return is excluded."""
    values = _validate_returns(frame)
    logs = np.log1p(values)
    ending = logs.rolling(int(horizon), min_periods=int(horizon)).sum()
    count = values.notna().rolling(int(horizon), min_periods=int(horizon)).sum()
    return np.expm1(ending.where(count.eq(int(horizon))).shift(-int(horizon)))


def relative_return(exposure: pd.DataFrame, benchmark: pd.Series) -> pd.DataFrame:
    return (1.0 + exposure).div(1.0 + benchmark, axis=0) - 1.0


def weekly_last_positions(dates: Sequence[pd.Timestamp]) -> np.ndarray:
    index = pd.DatetimeIndex(dates)
    frame = pd.DataFrame({"date": index, "position": np.arange(len(index), dtype=int)})
    iso = frame["date"].dt.isocalendar()
    frame["iso_year"] = iso["year"].astype(int)
    frame["iso_week"] = iso["week"].astype(int)
    return (
        frame.groupby(["iso_year", "iso_week"], sort=True)
        .tail(1)["position"]
        .to_numpy(dtype=int)
    )


def percentile_rank(frame: pd.DataFrame, minimum_count: int = 1) -> pd.DataFrame:
    ranked = frame.rank(axis=1, method="average", pct=True)
    ranked[frame.notna().sum(axis=1) < int(minimum_count)] = np.nan
    return ranked


def row_zscore(frame: pd.DataFrame, minimum_count: int = 3) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    std = frame.std(axis=1, ddof=0)
    out = frame.sub(mean, axis=0).div(std.where(std > 0), axis=0)
    out[frame.notna().sum(axis=1) < int(minimum_count)] = np.nan
    return out


def rolling_ols_slope_r2(frame: pd.DataFrame, window: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rolling OLS y~time slope/R2 using prefix sums and no future observations."""
    values = frame.astype(float).to_numpy()
    n, m = values.shape
    width = int(window)
    filled = np.where(np.isfinite(values), values, 0.0)
    valid = np.isfinite(values).astype(float)
    row_index = np.arange(n, dtype=float)[:, None]

    def prefix_window(array: np.ndarray) -> np.ndarray:
        prefix = np.vstack([np.zeros((1, m)), np.cumsum(array, axis=0)])
        result = np.full((n, m), np.nan)
        if n >= width:
            result[width - 1 :] = prefix[width:] - prefix[:-width]
        return result

    sum_y = prefix_window(filled)
    sum_y2 = prefix_window(filled * filled)
    sum_jy = prefix_window(filled * row_index)
    count = prefix_window(valid)
    ending = np.arange(n, dtype=float)[:, None]
    starting = ending - (width - 1)
    sum_xy = sum_jy - starting * sum_y
    mean_x = (width - 1) / 2.0
    sxx = width * (width**2 - 1.0) / 12.0
    numerator = sum_xy - mean_x * sum_y
    slope = numerator / sxx
    sst = sum_y2 - (sum_y * sum_y) / width
    r2 = np.divide(
        slope * slope * sxx,
        sst,
        out=np.full_like(slope, np.nan),
        where=sst > 0,
    )
    complete = count == width
    slope[~complete] = np.nan
    r2[~complete] = np.nan
    return (
        pd.DataFrame(slope, index=frame.index, columns=frame.columns),
        pd.DataFrame(r2, index=frame.index, columns=frame.columns),
    )


def pairwise_majority_win_rate(values: np.ndarray, minimum_competitors: int = 2) -> np.ndarray:
    """Rows are competitors and columns are horizons; majority requires >=3/5 wins."""
    array = np.asarray(values, dtype=float)
    n = array.shape[0]
    result = np.full(n, np.nan)
    fully_valid = np.isfinite(array).all(axis=1)
    valid_indices = np.flatnonzero(fully_valid)
    if len(valid_indices) < int(minimum_competitors) + 1:
        return result
    subset = array[valid_indices]
    comparison = subset[:, None, :] - subset[None, :, :]
    wins = (comparison > 0).sum(axis=2)
    losses = (comparison < 0).sum(axis=2)
    majority = wins >= 3
    ties = (wins == losses) & ~np.eye(len(subset), dtype=bool)
    denominator = len(subset) - 1
    scores = (majority.sum(axis=1) + 0.5 * ties.sum(axis=1)) / denominator
    result[valid_indices] = scores
    return result


def rowwise_spearman(signal: np.ndarray, forward: np.ndarray, minimum_count: int = 5) -> tuple[np.ndarray, np.ndarray]:
    left = pd.DataFrame(signal).rank(axis=1, method="average", pct=True).to_numpy()
    right = pd.DataFrame(forward).rank(axis=1, method="average", pct=True).to_numpy()
    mask = np.isfinite(left) & np.isfinite(right)
    count = mask.sum(axis=1).astype(int)
    x = np.where(mask, left, 0.0)
    y = np.where(mask, right, 0.0)
    denom = np.maximum(count, 1)[:, None]
    xm = x.sum(axis=1, keepdims=True) / denom
    ym = y.sum(axis=1, keepdims=True) / denom
    xd = np.where(mask, left - xm, 0.0)
    yd = np.where(mask, right - ym, 0.0)
    denominator = np.sqrt((xd * xd).sum(axis=1) * (yd * yd).sum(axis=1))
    corr = np.divide((xd * yd).sum(axis=1), denominator, out=np.full(len(left), np.nan), where=denominator > 0)
    corr[count < int(minimum_count)] = np.nan
    return corr, count


def newey_west_mean(values: Iterable[float], lag: int) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    n = int(len(array))
    empty = {
        "observation_count": 0,
        "mean": np.nan,
        "median": np.nan,
        "standard_deviation": np.nan,
        "positive_frequency": np.nan,
        "hac_lag": int(lag),
        "hac_standard_error": np.nan,
        "hac_t_statistic": np.nan,
        "hac_p_value": np.nan,
        "confidence_interval_low": np.nan,
        "confidence_interval_high": np.nan,
    }
    if n == 0:
        return empty
    mean = float(array.mean())
    median = float(np.median(array))
    std = float(array.std(ddof=1)) if n > 1 else np.nan
    centred = array - mean
    gamma0 = float(np.dot(centred, centred) / n)
    effective_lag = min(max(int(lag), 0), max(n - 1, 0))
    long_run_variance = gamma0
    for current_lag in range(1, effective_lag + 1):
        weight = 1.0 - current_lag / (effective_lag + 1.0)
        gamma = float(np.dot(centred[current_lag:], centred[:-current_lag]) / n)
        long_run_variance += 2.0 * weight * gamma
    standard_error = math.sqrt(max(long_run_variance, 0.0) / n)
    t_stat = mean / standard_error if standard_error > 0 else np.nan
    p_value = float(2.0 * norm.sf(abs(t_stat))) if np.isfinite(t_stat) else np.nan
    critical = float(norm.ppf(0.975))
    return {
        "observation_count": n,
        "mean": mean,
        "median": median,
        "standard_deviation": std,
        "positive_frequency": float(np.mean(array > 0)),
        "hac_lag": effective_lag,
        "hac_standard_error": standard_error,
        "hac_t_statistic": t_stat,
        "hac_p_value": p_value,
        "confidence_interval_low": mean - critical * standard_error,
        "confidence_interval_high": mean + critical * standard_error,
    }


def circular_block_bootstrap_mean_ci(
    values: Iterable[float], block_length: int, replications: int, seed: int
) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    n = len(array)
    if n < 2:
        return {"bootstrap_count": int(n), "block_length": int(block_length), "replications": 0, "bootstrap_ci_low": np.nan, "bootstrap_ci_high": np.nan}
    length = min(max(1, int(block_length)), n)
    blocks = int(math.ceil(n / length))
    rng = np.random.default_rng(int(seed))
    offsets = np.arange(length)
    means = np.empty(int(replications))
    for rep in range(int(replications)):
        starts = rng.integers(0, n, size=blocks)
        indices = ((starts[:, None] + offsets) % n).ravel()[:n]
        means[rep] = array[indices].mean()
    return {
        "bootstrap_count": int(n),
        "block_length": int(length),
        "replications": int(replications),
        "bootstrap_ci_low": float(np.quantile(means, 0.025)),
        "bootstrap_ci_high": float(np.quantile(means, 0.975)),
    }


def benjamini_hochberg(values: Sequence[float]) -> np.ndarray:
    p = np.asarray(values, dtype=float)
    adjusted = np.full_like(p, np.nan)
    finite = np.isfinite(p)
    observed = p[finite]
    if observed.size == 0:
        return adjusted
    order = np.argsort(observed)
    ordered = observed[order]
    m = len(ordered)
    q = ordered * m / np.arange(1, m + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    restored = np.empty_like(q)
    restored[order] = np.clip(q, 0.0, 1.0)
    adjusted[finite] = restored
    return adjusted


def hac_lag(horizon: int) -> int:
    return max(1, int(math.ceil(int(horizon) / 5.0)) - 1)


def top_tail_size(definition: str, cohort_count: int) -> int | None:
    n = int(cohort_count)
    fixed = {"RANK_1": 1, "TOP_2": 2, "TOP_3": 3, "TOP_5": 5}
    if definition in fixed:
        return fixed[definition] if n >= fixed[definition] else None
    if definition == "TOP_10_PERCENT":
        return max(1, int(math.ceil(n * 0.10))) if n >= 10 else None
    if definition == "TOP_QUINTILE":
        return max(1, int(math.ceil(n * 0.20))) if n >= 10 else None
    raise ValueError(f"Unknown top-tail definition: {definition}")


def annualised_geometric_return(returns: pd.Series) -> float:
    values = returns.dropna().astype(float)
    if len(values) == 0 or (values <= -1).any():
        return np.nan
    return float(np.expm1(np.log1p(values).sum() * 252.0 / len(values)))
