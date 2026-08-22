from __future__ import annotations

import pandas as pd

from edge_research.security_identity import (
    build_component_transition_rows,
    build_stable_identity_bridge,
    install_bounded_terminal_proxies,
    map_events_to_security_identity,
)


def _bars(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": date,
                "symbol": ticker,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 1_000.0,
            }
            for date, ticker, price in rows
        ]
    )


def _pit(rows: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "snapshot_date": date,
                "ticker": ticker,
                "issuer_group_id": issuer,
                "liquidity_rank": index + 1,
            }
            for index, (date, ticker, issuer) in enumerate(rows)
        ]
    )


def test_ordinary_security_resolves_to_one_time_bounded_identity() -> None:
    calendar = pd.bdate_range("2026-01-02", "2026-01-08")
    bars = _bars([(str(date.date()), "AAA", 100.0 + index) for index, date in enumerate(calendar)])
    result = build_stable_identity_bridge(
        bars,
        _pit([("2026-01-02", "AAA", "CIK:1")]),
        calendar=calendar,
    )
    assert result.bars["symbol"].nunique() == 1
    assert result.intervals.iloc[0]["stable_security_id"] == "CIK:1"
    assert result.pit.iloc[0]["identity_resolution_status"] == "RESOLVED_POINT_IN_TIME"


def test_long_gap_creates_distinct_identity_and_terminal_bound() -> None:
    calendar = pd.bdate_range("2011-01-03", "2011-04-15")
    bars = _bars(
        [
            ("2011-01-03", "BEZ", 63.0),
            ("2011-01-27", "BEZ", 63.5),
            ("2011-04-15", "BEZ", 24.92),
        ]
    )
    pit = _pit(
        [
            ("2011-01-03", "BEZ", "CIK:9342"),
            ("2011-04-15", "BEZ", "CIK:999999"),
        ]
    )
    result = build_stable_identity_bridge(bars, pit, calendar=calendar, maximum_unexplained_gap_sessions=20)
    assert result.intervals["security_key"].nunique() == 2
    old_key = result.pit.loc[result.pit["issuer_group_id"].eq("CIK:9342"), "security_key"].iloc[0]
    new_key = result.pit.loc[result.pit["issuer_group_id"].eq("CIK:999999"), "security_key"].iloc[0]
    assert old_key != new_key
    panel, evidence = install_bounded_terminal_proxies(result.bars, calendar)
    old_proxy = panel.loc[panel["symbol"].eq(old_key) & panel["terminal_proxy_only"]].iloc[0]
    assert old_proxy["date"] == pd.Timestamp("2011-01-28")
    assert old_proxy["open"] == 63.5
    assert evidence.loc[evidence["security_key"].eq(old_key), "treatment"].iloc[0] == (
        "TERMINAL_ECONOMICS_BOUNDED_LAST_VALID_CLOSE"
    )


def test_source_bound_successor_tickers_share_identity() -> None:
    calendar = pd.bdate_range("2015-02-17", "2015-03-03")
    bars = _bars(
        [
            ("2015-02-17", "NU", 51.23),
            ("2015-02-18", "NU", 52.54),
            ("2015-02-19", "ES", 53.23),
            ("2015-03-02", "ES", 51.50),
        ]
    )
    pit = _pit(
        [
            ("2015-02-17", "NU", "CIK:72741"),
            ("2015-03-02", "ES", "CIK:72741"),
        ]
    )
    overrides = pd.DataFrame(
        [
            {
                "continuity_id": "NU_ES_20150219",
                "ticker": ticker,
                "effective_from": start,
                "effective_to": end,
                "expected_issuer_group_id": "CIK:72741",
                "stable_security_id": "CIK:72741",
                "source": "issuer filing",
            }
            for ticker, start, end in (
                ("NU", "2000-01-01", "2015-02-18"),
                ("ES", "2015-02-19", "2030-01-01"),
            )
        ]
    )
    result = build_stable_identity_bridge(bars, pit, calendar=calendar, continuity_overrides=overrides)
    assert result.bars["symbol"].nunique() == 1
    assert result.pit["security_key"].nunique() == 1


def test_forced_security_transition_splits_continuous_ticker() -> None:
    calendar = pd.bdate_range("2016-06-29", "2016-07-05")
    bars = _bars(
        [
            ("2016-06-29", "HTZ", 10.77),
            ("2016-06-30", "HTZ", 11.07),
            ("2016-07-01", "HTZ", 44.50),
            ("2016-07-05", "HTZ", 43.87),
        ]
    )
    pit = _pit(
        [
            ("2016-06-29", "HTZ", "CIK:1364479"),
            ("2016-07-05", "HTZ", "CIK:1657853"),
        ]
    )
    boundaries = pd.DataFrame(
        [{"ticker": "HTZ", "effective_date": "2016-07-01", "reason": "separation", "source": "SEC"}]
    )
    result = build_stable_identity_bridge(bars, pit, calendar=calendar, forced_boundaries=boundaries)
    before = result.bars.loc[result.bars["date"].eq(pd.Timestamp("2016-06-30")), "symbol"].iloc[0]
    after = result.bars.loc[result.bars["date"].eq(pd.Timestamp("2016-07-01")), "symbol"].iloc[0]
    assert before != after


def test_source_defined_component_transition_values_old_holder_without_joining_signal_history() -> None:
    calendar = pd.bdate_range("2016-06-29", "2016-07-05")
    bars = _bars(
        [
            ("2016-06-29", "HTZ", 10.77),
            ("2016-06-30", "HTZ", 11.07),
            ("2016-07-01", "HTZ", 44.50),
            ("2016-07-01", "HRI", 34.40),
            ("2016-07-05", "HTZ", 43.87),
            ("2016-07-05", "HRI", 33.75),
        ]
    )
    pit = _pit(
        [
            ("2016-06-29", "HTZ", "CIK:1364479"),
            ("2016-07-05", "HTZ", "CIK:1657853"),
            ("2016-07-05", "HRI", "CIK:1657853-HRI"),
        ]
    )
    boundaries = pd.DataFrame(
        [{"ticker": "HTZ", "effective_date": "2016-07-01", "reason": "separation", "source": "SEC"}]
    )
    identity = build_stable_identity_bridge(bars, pit, calendar=calendar, forced_boundaries=boundaries)
    synthetic, evidence = build_component_transition_rows(
        identity.bars,
        identity.intervals,
        [
            {
                "transition_id": "HTZ_HRI_NEW_HTZ_20160701",
                "old_ticker": "HTZ",
                "old_identity_effective_to": "2016-06-30",
                "synthetic_value_effective_from": "2016-07-01",
                "synthetic_value_effective_to": "2016-07-05",
                "components_per_old_share": [
                    {"ticker": "HRI", "quantity": 1.0 / 15.0},
                    {"ticker": "HTZ", "quantity": 1.0 / 5.0},
                ],
                "source": "issuer filing",
            }
        ],
    )
    old_key = identity.bars.loc[
        identity.bars["ticker_at_date"].eq("HTZ")
        & identity.bars["date"].eq(pd.Timestamp("2016-06-30")),
        "symbol",
    ].iloc[0]
    new_key = identity.bars.loc[
        identity.bars["ticker_at_date"].eq("HTZ")
        & identity.bars["date"].eq(pd.Timestamp("2016-07-01")),
        "symbol",
    ].iloc[0]
    first = synthetic.loc[synthetic["date"].eq(pd.Timestamp("2016-07-01"))].iloc[0]
    assert old_key != new_key
    assert first["symbol"] == old_key
    assert first["open"] == 34.40 / 15.0 + 44.50 / 5.0
    assert evidence.iloc[0]["transition_id"] == "HTZ_HRI_NEW_HTZ_20160701"


def test_ticker_dated_action_maps_to_one_stable_symbol_column() -> None:
    calendar = pd.bdate_range("2017-11-08", "2017-11-10")
    identity = build_stable_identity_bridge(
        _bars([("2017-11-08", "WLL", 6.61), ("2017-11-09", "WLL", 25.40)]),
        _pit([("2017-11-08", "WLL", "CIK:1255474")]),
        calendar=calendar,
    )
    mapped, diagnostics = map_events_to_security_identity(
        pd.DataFrame(
            [
                {
                    "ticker": "WLL",
                    "execution_date": "2017-11-09",
                    "split_factor": 0.25,
                    "source": "issuer filing",
                }
            ]
        ),
        identity.intervals,
    )
    assert list(mapped.columns).count("symbol") == 1
    assert mapped.iloc[0]["symbol"] == identity.bars.iloc[0]["symbol"]
    assert mapped.iloc[0]["ticker_at_event"] == "WLL"
    assert diagnostics.empty


def test_multiple_pit_issuer_ids_use_bounded_ticker_fallback_without_inferred_join() -> None:
    calendar = pd.bdate_range("2020-01-02", "2020-01-10")
    bars = _bars([(str(date.date()), "AAA", 50.0) for date in calendar])
    result = build_stable_identity_bridge(
        bars,
        _pit(
            [
                ("2020-01-02", "AAA", "CIK:OLD"),
                ("2020-01-08", "AAA", "CIK:NEW"),
            ]
        ),
        calendar=calendar,
    )
    assert result.bars["symbol"].nunique() == 1
    assert result.intervals.iloc[0]["stable_security_id"] == ""
    assert result.intervals.iloc[0]["identity_source"] == "TIME_BOUNDED_TICKER_INTERVAL_MULTIPLE_PIT_ISSUERS"
    assert result.diagnostics.iloc[0]["severity"] == "warning"
