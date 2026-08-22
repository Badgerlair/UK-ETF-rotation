"""Stable or time-bounded historical identity for ticker-keyed research data.

The raw US-equity archive is keyed by ticker.  This module prevents a later
reuse of the same ticker from reconnecting an earlier position or signal
history.  Existing point-in-time issuer identifiers are retained as evidence;
where they cannot establish universal security continuity, a deterministic
listing-lifetime key is used instead.  Cross-ticker continuity is admitted
only through an explicit, source-bound override.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd


IDENTITY_DIAGNOSTIC_COLUMNS = ["ticker", "date", "event_type", "severity", "message"]


@dataclass(frozen=True)
class StableIdentityBridgeResult:
    bars: pd.DataFrame
    pit: pd.DataFrame
    intervals: pd.DataFrame
    diagnostics: pd.DataFrame


def build_stable_identity_bridge(
    bars: pd.DataFrame,
    pit: pd.DataFrame,
    *,
    calendar: pd.DatetimeIndex | list | tuple | pd.Series,
    maximum_unexplained_gap_sessions: int = 20,
    forced_boundaries: pd.DataFrame | None = None,
    continuity_overrides: pd.DataFrame | None = None,
) -> StableIdentityBridgeResult:
    """Resolve raw ticker bars to stable or explicitly time-bounded keys.

    A new listing interval begins after more than ``maximum_unexplained_gap_sessions``
    missing market sessions or at an explicitly sourced forced boundary.  The
    PIT ``issuer_group_id`` is attached where an interval overlaps exactly one
    such identity.  It is evidence, not permission to bridge an unexplained
    gap.  Only ``continuity_overrides`` can deliberately join intervals.
    """

    if maximum_unexplained_gap_sessions < 1:
        raise ValueError("maximum_unexplained_gap_sessions must be positive")
    required_bars = {"date", "symbol"}
    required_pit = {"ticker", "snapshot_date", "issuer_group_id"}
    if missing := required_bars.difference(bars.columns):
        raise ValueError(f"Identity bridge bars are missing fields: {sorted(missing)}")
    if missing := required_pit.difference(pit.columns):
        raise ValueError(f"Identity bridge PIT data are missing fields: {sorted(missing)}")

    sessions = pd.DatetimeIndex(pd.to_datetime(calendar, errors="raise")).normalize().unique().sort_values()
    if sessions.empty:
        raise ValueError("Identity bridge requires a non-empty causal session calendar")
    session_positions = pd.Series(np.arange(len(sessions), dtype=int), index=sessions)

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["ticker_at_date"] = frame["symbol"].astype(str).str.upper().str.strip()
    if frame["ticker_at_date"].eq("").any():
        raise ValueError("Identity bridge received an empty ticker")
    if frame.duplicated(["ticker_at_date", "date"]).any():
        raise ValueError("Identity bridge requires one canonical bar per ticker/date")
    frame["_session_position"] = frame["date"].map(session_positions)
    if frame["_session_position"].isna().any():
        raise ValueError("Every bar date must exist in the supplied session calendar")
    frame = frame.sort_values(["ticker_at_date", "date"], kind="mergesort").reset_index(drop=True)

    boundaries = _normalise_boundaries(forced_boundaries)
    boundary_lookup = {
        ticker: tuple(group["effective_date"].sort_values())
        for ticker, group in boundaries.groupby("ticker", sort=False)
    }
    diagnostics: list[dict] = []
    interval_rows: list[dict] = []
    interval_ids = np.empty(len(frame), dtype=np.int64)
    next_interval_id = 1
    for ticker, index in frame.groupby("ticker_at_date", sort=False).groups.items():
        locations = np.asarray(list(index), dtype=int)
        group = frame.loc[locations]
        positions = group["_session_position"].to_numpy(dtype=int)
        dates = group["date"].to_numpy(dtype="datetime64[ns]")
        starts = np.zeros(len(group), dtype=bool)
        starts[0] = True
        if len(group) > 1:
            starts[1:] = np.diff(positions) - 1 > maximum_unexplained_gap_sessions
        for boundary in boundary_lookup.get(str(ticker), ()):
            boundary64 = np.datetime64(pd.Timestamp(boundary))
            location = int(np.searchsorted(dates, boundary64, side="left"))
            if 0 < location < len(group):
                starts[location] = True
        segment_numbers = np.cumsum(starts)
        for segment_number in np.unique(segment_numbers):
            mask = segment_numbers == segment_number
            segment_locations = locations[mask]
            interval_id = next_interval_id
            next_interval_id += 1
            interval_ids[segment_locations] = interval_id
            segment_dates = frame.loc[segment_locations, "date"]
            start_date = pd.Timestamp(segment_dates.min())
            end_date = pd.Timestamp(segment_dates.max())
            first_local = int(np.flatnonzero(mask)[0])
            gap_before = (
                int(positions[first_local] - positions[first_local - 1] - 1)
                if first_local > 0
                else 0
            )
            interval_rows.append(
                {
                    "interval_id": interval_id,
                    "ticker": str(ticker),
                    "interval_start": start_date,
                    "interval_end": end_date,
                    "observations": int(mask.sum()),
                    "gap_sessions_before": gap_before,
                }
            )

    frame["interval_id"] = interval_ids
    intervals = pd.DataFrame(interval_rows).sort_values(["ticker", "interval_start"], kind="mergesort")
    pit_frame = pit.copy()
    pit_frame["ticker_at_snapshot"] = pit_frame["ticker"].astype(str).str.upper().str.strip()
    pit_frame["snapshot_date"] = pd.to_datetime(pit_frame["snapshot_date"], errors="raise").dt.normalize()
    pit_frame["issuer_group_id"] = pit_frame["issuer_group_id"].fillna("").astype(str).str.strip()

    issuer_values: list[str] = []
    issuer_statuses: list[str] = []
    for interval in intervals.itertuples(index=False):
        candidates = pit_frame.loc[
            pit_frame["ticker_at_snapshot"].eq(interval.ticker)
            & pit_frame["snapshot_date"].between(interval.interval_start, interval.interval_end),
            "issuer_group_id",
        ]
        unique = sorted(value for value in candidates.unique() if value)
        if len(unique) == 1:
            issuer_values.append(unique[0])
            issuer_statuses.append("PIT_ISSUER_GROUP_EXACT_INTERVAL_OVERLAP")
        elif len(unique) == 0:
            issuer_values.append("")
            issuer_statuses.append("TIME_BOUNDED_TICKER_INTERVAL_ONLY")
        else:
            issuer_values.append("")
            issuer_statuses.append("TIME_BOUNDED_TICKER_INTERVAL_MULTIPLE_PIT_ISSUERS")
            diagnostics.append(
                _diagnostic(
                    interval.ticker,
                    interval.interval_start,
                    "multiple_pit_issuer_ids_within_bounded_interval",
                    "warning",
                    f"Bounded continuous ticker interval overlaps multiple PIT issuer IDs; no identity join was inferred: {unique}",
                )
            )
    intervals["stable_security_id"] = issuer_values
    intervals["identity_source"] = issuer_statuses
    intervals["security_key"] = [
        _security_key(
            f"TIME_BOUNDED|{row.ticker}|{pd.Timestamp(row.interval_start):%Y%m%d}|"
            f"{pd.Timestamp(row.interval_end):%Y%m%d}|{row.stable_security_id or 'UNRESOLVED'}"
        )
        for row in intervals.itertuples(index=False)
    ]

    overrides = _normalise_continuity_overrides(continuity_overrides)
    if not overrides.empty:
        for override in overrides.itertuples(index=False):
            mask = (
                intervals["ticker"].eq(override.ticker)
                & intervals["interval_end"].ge(override.effective_from)
                & intervals["interval_start"].le(override.effective_to)
            )
            if override.expected_issuer_group_id:
                mask &= intervals["stable_security_id"].eq(override.expected_issuer_group_id)
            if not mask.any():
                raise ValueError(f"Continuity override {override.continuity_id} matched no identity interval")
            intervals.loc[mask, "security_key"] = _security_key(f"STABLE_CONTINUITY|{override.continuity_id}")
            intervals.loc[mask, "stable_security_id"] = override.stable_security_id
            intervals.loc[mask, "identity_source"] = "SOURCE_BOUND_CROSS_TICKER_CONTINUITY"

    interval_map = intervals.set_index("interval_id")
    frame["security_key"] = frame["interval_id"].map(interval_map["security_key"])
    frame["stable_security_id"] = frame["interval_id"].map(interval_map["stable_security_id"])
    frame["identity_source"] = frame["interval_id"].map(interval_map["identity_source"])
    frame["symbol"] = frame["security_key"]
    frame = frame.drop(columns=["_session_position"])
    if frame.duplicated(["symbol", "date"]).any():
        duplicate = frame.loc[frame.duplicated(["symbol", "date"], keep=False), ["date", "ticker_at_date", "symbol"]]
        raise ValueError(f"Resolved stable identity has overlapping ticker observations: {duplicate.head(10).to_dict('records')}")

    pit_interval_ids: list[float] = []
    pit_security_keys: list[str] = []
    pit_stable_ids: list[str] = []
    pit_statuses: list[str] = []
    intervals_by_ticker = {ticker: group for ticker, group in intervals.groupby("ticker", sort=False)}
    for row in pit_frame.itertuples(index=False):
        candidates = intervals_by_ticker.get(row.ticker_at_snapshot)
        chosen = None
        status = "UNRESOLVED_NO_TICKER_INTERVAL"
        if candidates is not None:
            exact = candidates.loc[
                candidates["interval_start"].le(row.snapshot_date)
                & candidates["interval_end"].ge(row.snapshot_date)
            ]
            if len(exact) == 1:
                chosen = exact.iloc[0]
                status = "RESOLVED_POINT_IN_TIME"
            elif len(exact) == 0:
                distances = candidates.apply(
                    lambda candidate: min(
                        abs((row.snapshot_date - candidate["interval_start"]).days),
                        abs((row.snapshot_date - candidate["interval_end"]).days),
                    ),
                    axis=1,
                )
                nearest_index = distances.idxmin()
                if int(distances.loc[nearest_index]) <= 7:
                    chosen = candidates.loc[nearest_index]
                    status = "RESOLVED_NEAREST_SESSION_WITHIN_7_DAYS"
        if chosen is None:
            pit_interval_ids.append(np.nan)
            pit_security_keys.append("")
            pit_stable_ids.append("")
            pit_statuses.append(status)
            diagnostics.append(
                _diagnostic(row.ticker_at_snapshot, row.snapshot_date, "unresolved_pit_identity", "error", status)
            )
        else:
            pit_interval_ids.append(int(chosen["interval_id"]))
            pit_security_keys.append(str(chosen["security_key"]))
            pit_stable_ids.append(str(chosen["stable_security_id"]))
            pit_statuses.append(status)
    pit_frame["identity_interval_id"] = pit_interval_ids
    pit_frame["security_key"] = pit_security_keys
    pit_frame["stable_security_id"] = pit_stable_ids
    pit_frame["identity_resolution_status"] = pit_statuses
    pit_frame["research_ticker"] = pit_frame["ticker_at_snapshot"]
    pit_frame["ticker"] = pit_frame["security_key"]

    unresolved = pit_frame["security_key"].eq("")
    if unresolved.any():
        diagnostics.append(
            _diagnostic(
                "",
                pit_frame.loc[unresolved, "snapshot_date"].min(),
                "unresolved_pit_identity_summary",
                "error",
                f"{int(unresolved.sum())} PIT rows could not resolve to a bounded raw-price identity",
            )
        )
    return StableIdentityBridgeResult(
        bars=frame.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True),
        pit=pit_frame,
        intervals=intervals.reset_index(drop=True),
        diagnostics=pd.DataFrame(diagnostics, columns=IDENTITY_DIAGNOSTIC_COLUMNS),
    )


def map_events_to_security_identity(events: pd.DataFrame, intervals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map ticker-dated corporate actions onto the bounded security key."""

    if events is None or events.empty:
        return pd.DataFrame(columns=list(events.columns) if events is not None else []), pd.DataFrame(columns=IDENTITY_DIAGNOSTIC_COLUMNS)
    frame = events.copy()
    ticker_column = "ticker" if "ticker" in frame else "symbol"
    date_column = "execution_date" if "execution_date" in frame else "date"
    if ticker_column not in frame or date_column not in frame:
        raise ValueError("Corporate actions require ticker/symbol and execution_date/date")
    frame["ticker_at_event"] = frame[ticker_column].astype(str).str.upper().str.strip()
    frame[date_column] = pd.to_datetime(frame[date_column], errors="raise").dt.normalize()
    intervals_by_ticker = {ticker: group for ticker, group in intervals.groupby("ticker", sort=False)}
    keys: list[str] = []
    diagnostics: list[dict] = []
    for row in frame.itertuples(index=False):
        ticker = str(getattr(row, "ticker_at_event"))
        event_date = pd.Timestamp(getattr(row, date_column))
        candidates = intervals_by_ticker.get(ticker)
        key = ""
        if candidates is not None:
            exact = candidates.loc[
                candidates["interval_start"].le(event_date)
                & candidates["interval_end"].ge(event_date)
            ]
            if len(exact) == 1:
                key = str(exact.iloc[0]["security_key"])
            elif len(exact) == 0:
                future = candidates.loc[candidates["interval_start"].ge(event_date)].sort_values("interval_start")
                if len(future) and (future.iloc[0]["interval_start"] - event_date).days <= 7:
                    key = str(future.iloc[0]["security_key"])
        keys.append(key)
        if not key:
            diagnostics.append(
                _diagnostic(ticker, event_date, "unresolved_action_identity", "warning", "Action did not map to a bounded ticker interval")
            )
    frame["security_key"] = keys
    mapped = frame.loc[frame["security_key"].ne("")].copy()
    if ticker_column != "symbol":
        mapped = mapped.drop(columns=[ticker_column])
    mapped["symbol"] = mapped["security_key"]
    return mapped, pd.DataFrame(diagnostics, columns=IDENTITY_DIAGNOSTIC_COLUMNS)


def install_bounded_terminal_proxies(
    market_panel: pd.DataFrame,
    calendar: pd.DatetimeIndex | list | tuple | pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Install the predeclared last-valid-close bound at each ended identity."""

    required = {"date", "symbol", "close"}
    if missing := required.difference(market_panel.columns):
        raise ValueError(f"Terminal proxy panel is missing fields: {sorted(missing)}")
    panel = market_panel.copy()
    panel["date"] = pd.to_datetime(panel["date"], errors="raise").dt.normalize()
    panel["terminal_proxy_only"] = False
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar, errors="raise")).normalize().unique().sort_values()
    last_indices = panel.groupby("symbol", sort=False)["date"].idxmax()
    proxies: list[dict] = []
    evidence: list[dict] = []
    for row in panel.loc[last_indices].itertuples(index=False):
        last_date = pd.Timestamp(row.date)
        position = int(np.searchsorted(sessions.to_numpy(dtype="datetime64[ns]"), np.datetime64(last_date), side="right"))
        if position >= len(sessions):
            continue
        settlement_date = pd.Timestamp(sessions[position])
        record = row._asdict()
        for column in ("open", "high", "low", "close"):
            if column in record:
                record[column] = float(row.close)
        record.update(
            {
                "date": settlement_date,
                "volume": 0.0,
                "split_factor_at_open": 1.0,
                "cash_dividend_per_share": 0.0,
                "terminal_proxy_only": True,
            }
        )
        proxies.append(record)
        evidence.append(
            {
                "security_key": str(row.symbol),
                "ticker_at_last_observation": str(getattr(row, "ticker_at_date", "")),
                "stable_security_id": str(getattr(row, "stable_security_id", "")),
                "last_observed_date": last_date,
                "settlement_date": settlement_date,
                "last_valid_close_bound": float(row.close),
                "treatment": "TERMINAL_ECONOMICS_BOUNDED_LAST_VALID_CLOSE",
            }
        )
    if proxies:
        panel = pd.concat([panel, pd.DataFrame(proxies)], ignore_index=True)
    if panel.duplicated(["symbol", "date"]).any():
        raise ValueError("Terminal proxy collided with an executable same-security bar")
    return (
        panel.sort_values(["symbol", "date"], kind="mergesort").reset_index(drop=True),
        pd.DataFrame(evidence),
    )


def build_component_transition_rows(
    resolved_bars: pd.DataFrame,
    intervals: pd.DataFrame,
    transitions: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Value an old-holder position through a documented successor basket.

    These rows are execution/marking rows only.  They must be appended after
    signal construction so that a terminated security never acquires a new
    regression history through its distributed components.
    """

    required = {"date", "ticker_at_date", "open", "high", "low", "close"}
    if missing := required.difference(resolved_bars.columns):
        raise ValueError(f"Component transition bars are missing fields: {sorted(missing)}")
    bars = resolved_bars.copy()
    bars["date"] = pd.to_datetime(bars["date"], errors="raise").dt.normalize()
    rows: list[dict] = []
    evidence: list[dict] = []
    for transition in transitions:
        transition_id = str(transition["transition_id"])
        old_ticker = str(transition["old_ticker"]).upper()
        old_end = pd.Timestamp(transition["old_identity_effective_to"]).normalize()
        old_interval = intervals.loc[
            intervals["ticker"].eq(old_ticker) & intervals["interval_end"].eq(old_end)
        ]
        if len(old_interval) != 1:
            raise ValueError(f"Complex transition {transition_id} expected one old identity interval, found {len(old_interval)}")
        old = old_interval.iloc[0]
        start = pd.Timestamp(transition["synthetic_value_effective_from"]).normalize()
        end = pd.Timestamp(transition["synthetic_value_effective_to"]).normalize()
        component_frames: list[pd.DataFrame] = []
        for component in transition["components_per_old_share"]:
            ticker = str(component["ticker"]).upper()
            quantity = float(component["quantity"])
            if not np.isfinite(quantity) or quantity <= 0:
                raise ValueError(f"Complex transition {transition_id} has an invalid component quantity")
            component_frame = bars.loc[
                bars["ticker_at_date"].eq(ticker) & bars["date"].between(start, end),
                ["date", "open", "high", "low", "close"],
            ].copy()
            component_frame = component_frame.rename(
                columns={field: f"{ticker}_{field}" for field in ("open", "high", "low", "close")}
            )
            component_frame[f"{ticker}_quantity"] = quantity
            component_frames.append(component_frame)
        if not component_frames:
            raise ValueError(f"Complex transition {transition_id} has no components")
        combined = component_frames[0]
        for component_frame in component_frames[1:]:
            combined = combined.merge(component_frame, on="date", how="inner", validate="one_to_one")
        if combined.empty:
            raise ValueError(f"Complex transition {transition_id} has no common executable component sessions")
        for combined_row in combined.itertuples(index=False):
            record = {
                "date": pd.Timestamp(combined_row.date),
                "symbol": str(old["security_key"]),
                "security_key": str(old["security_key"]),
                "ticker_at_date": f"SYNTHETIC:{transition_id}",
                "stable_security_id": str(old["stable_security_id"]),
                "identity_source": "SOURCE_BOUND_COMPONENT_TRANSITION",
                "interval_id": int(old["interval_id"]),
                "volume": 0.0,
                "split_factor_at_open": 1.0,
                "cash_dividend_per_share": 0.0,
                "terminal_proxy_only": False,
                "complex_transition_only": True,
                "complex_transition_id": transition_id,
            }
            for field in ("open", "high", "low", "close"):
                total = 0.0
                for component in transition["components_per_old_share"]:
                    ticker = str(component["ticker"]).upper()
                    total += float(getattr(combined_row, f"{ticker}_{field}")) * float(component["quantity"])
                record[field] = total
            rows.append(record)
            evidence.append(
                {
                    "transition_id": transition_id,
                    "old_security_key": str(old["security_key"]),
                    "date": pd.Timestamp(combined_row.date),
                    "synthetic_open_per_old_share": record["open"],
                    "synthetic_close_per_old_share": record["close"],
                    "component_definition": transition["components_per_old_share"],
                    "source": str(transition["source"]),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(evidence)


def _normalise_boundaries(boundaries: pd.DataFrame | None) -> pd.DataFrame:
    columns = ["ticker", "effective_date", "reason", "source"]
    if boundaries is None or boundaries.empty:
        return pd.DataFrame(columns=columns)
    frame = boundaries.copy()
    missing = {"ticker", "effective_date"}.difference(frame.columns)
    if missing:
        raise ValueError(f"Forced identity boundaries are missing fields: {sorted(missing)}")
    if "reason" not in frame:
        frame["reason"] = "UNSPECIFIED"
    if "source" not in frame:
        frame["source"] = "UNSPECIFIED"
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["effective_date"] = pd.to_datetime(frame["effective_date"], errors="raise").dt.normalize()
    return frame[columns].drop_duplicates().sort_values(["ticker", "effective_date"])


def _normalise_continuity_overrides(overrides: pd.DataFrame | None) -> pd.DataFrame:
    columns = [
        "continuity_id",
        "ticker",
        "effective_from",
        "effective_to",
        "expected_issuer_group_id",
        "stable_security_id",
        "source",
    ]
    if overrides is None or overrides.empty:
        return pd.DataFrame(columns=columns)
    frame = overrides.copy()
    missing = set(columns[:-1]).difference(frame.columns)
    if missing:
        raise ValueError(f"Continuity overrides are missing fields: {sorted(missing)}")
    if "source" not in frame:
        frame["source"] = "UNSPECIFIED"
    frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    frame["effective_from"] = pd.to_datetime(frame["effective_from"], errors="raise").dt.normalize()
    frame["effective_to"] = pd.to_datetime(frame["effective_to"], errors="raise").dt.normalize()
    for column in ("continuity_id", "expected_issuer_group_id", "stable_security_id", "source"):
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    if (frame["effective_to"] < frame["effective_from"]).any():
        raise ValueError("Continuity override effective_to cannot precede effective_from")
    return frame[columns].drop_duplicates().sort_values(["continuity_id", "ticker", "effective_from"])


def _security_key(payload: str) -> str:
    return "SEC_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20].upper()


def _diagnostic(ticker: str, date, event_type: str, severity: str, message: str) -> dict:
    parsed = pd.to_datetime(date, errors="coerce")
    return {
        "ticker": str(ticker),
        "date": "" if pd.isna(parsed) else pd.Timestamp(parsed).strftime("%Y-%m-%d"),
        "event_type": event_type,
        "severity": severity,
        "message": message,
    }
