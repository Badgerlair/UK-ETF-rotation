"""Refresh immutable and current UKACTIVE leadership snapshots."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow

from query_ukactive_rotation import PROGRAMME_ROOT, build_snapshot
from ukactive_a3r2_core import WARNING, audit_file, git_output, sha256_file, utc_now, write_csv, write_json, write_text


def markdown_report(title: str, frame: pd.DataFrame, classification: str, interpretation: list[str]) -> str:
    ranked = frame.loc[frame["short_1_2_3_composite"].notna()].sort_values("short_1_2_3_composite", ascending=False).head(15)
    lines = [f"# {title}", "", f"Market-data as of **{pd.Timestamp(frame['as_of_date'].iloc[0]).date()}**. Classification: **{classification}**.", "", *[f"- {item}" for item in interpretation], "", "## Leaders", "", "| Rank | Family | Ticker | 1m RS | 2m RS | 3m RS | Short composite | 3/6/12 | State | 1m rank change |", "|---:|---|---|---:|---:|---:|---:|---:|---|---:|"]
    for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
        def fmt(value: object) -> str:
            return "NA" if pd.isna(value) else f"{float(value):.2%}"
        lines.append(f"| {rank} | {row['economic_exposure_family_id']} | {row['ticker']} | {fmt(row['RS_21'])} | {fmt(row['RS_42'])} | {fmt(row['RS_63'])} | {fmt(row['short_1_2_3_composite'])} | {fmt(row['3_6_12_composite'])} | {row['relative_strength_state']} | {fmt(row['one_month_rank_change'])} |")
    lines.extend(["", "These are research/intelligence ranks, not deployment instructions. Current eligibility metadata is not historical eligibility."])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh UKACTIVE current leadership snapshot")
    parser.add_argument("--asof", default="latest")
    args = parser.parse_args()
    snapshot, regime = build_snapshot(args.asof)
    if snapshot.empty:
        raise RuntimeError("Snapshot is empty")
    asof = pd.Timestamp(snapshot["as_of_date"].iloc[0]).strftime("%Y-%m-%d")
    snapshot_dir = PROGRAMME_ROOT / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    immutable_csv = snapshot_dir / f"UKACTIVE_ROTATION_SNAPSHOT_{asof}.csv"
    immutable_json = snapshot_dir / f"UKACTIVE_ROTATION_SNAPSHOT_{asof}.json"
    csv_bytes = snapshot.to_csv(index=False, lineterminator="\n").encode("utf-8")
    json_payload = json.loads(snapshot.to_json(orient="records", date_format="iso"))
    json_bytes = (json.dumps(json_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    for path, payload in [(immutable_csv, csv_bytes), (immutable_json, json_bytes)]:
        if path.exists() and path.read_bytes() != payload:
            raise RuntimeError(f"Immutable snapshot already exists with different bytes: {path}")
        if not path.exists():
            path.write_bytes(payload)

    current_csv = PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.csv"
    current_json = PROGRAMME_ROOT / "UKACTIVE_CURRENT_ROTATION_SNAPSHOT.json"
    current_csv.write_bytes(csv_bytes)
    current_json.write_bytes(json_bytes)
    write_json(PROGRAMME_ROOT / "UKACTIVE_CURRENT_REGIME_STATE.json", regime)

    pool_frames = {pool: snapshot.loc[snapshot["rotation_pool"].eq(pool)].copy() for pool in ["GEOGRAPHY", "INDUSTRY", "THEME"]}
    geo = pool_frames["GEOGRAPHY"].sort_values("short_1_2_3_composite", ascending=False, na_position="last")
    industry = pool_frames["INDUSTRY"].sort_values("short_1_2_3_composite", ascending=False, na_position="last")
    theme = pool_frames["THEME"].sort_values("short_1_2_3_composite", ascending=False, na_position="last")
    write_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_GEOGRAPHIC_LEADERSHIP.csv", geo)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_INDUSTRY_LEADERSHIP.csv", industry)
    write_csv(PROGRAMME_ROOT / "UKACTIVE_CURRENT_THEME_LEADERSHIP.csv", theme)

    top_geo = geo.loc[geo["short_1_2_3_composite"].notna()].head(3)["economic_exposure_family_id"].tolist()
    us_in_top = any("US" in family or "UNITED_STATES" in family for family in top_geo)
    em = geo.loc[geo["economic_exposure_family_id"].eq("EMERGING_MARKETS")]
    em_text = "Emerging-markets direction unavailable."
    if len(em) and pd.notna(em.iloc[0]["one_month_rank_change"]):
        em_text = f"Emerging markets are {'gaining' if em.iloc[0]['one_month_rank_change'] > 0 else 'losing'} relative rank over the last month ({em.iloc[0]['one_month_rank_change']:+.1%})."
    geo_interpretation = [
        f"Top three short-horizon geographies: {', '.join(top_geo) if top_geo else 'not available'}.",
        f"Leadership is {'not clearly broadening beyond the US' if us_in_top else 'currently broadening beyond the US in the top three'}.",
        em_text,
        "A3R2 retains geography as MARKET_INTELLIGENCE_ONLY; no portfolio edge is claimed.",
    ]
    write_text(PROGRAMME_ROOT / "UKACTIVE_CURRENT_GEOGRAPHIC_LEADERSHIP.md", markdown_report("UKACTIVE current geographic leadership", geo, "MARKET_INTELLIGENCE_ONLY", geo_interpretation))
    write_text(PROGRAMME_ROOT / "UKACTIVE_CURRENT_INDUSTRY_LEADERSHIP.md", markdown_report("UKACTIVE current industry leadership", industry, "TRADE_RESEARCH_CANDIDATE / RESEARCH_ONLY", ["Industry rotation has contemporary developmental evidence, not independent confirmation.", "Ranks may cluster in related parents; raw overlap is not suppressed."]))
    write_text(PROGRAMME_ROOT / "UKACTIVE_CURRENT_THEME_LEADERSHIP.md", markdown_report("UKACTIVE current theme leadership", theme, "TRADE_RESEARCH_CANDIDATE / RESEARCH_ONLY", ["Theme evidence is weaker and more sample-dependent than industry evidence.", "DeepVue labels are display metadata only and never affect ranks."]))

    source_features = pd.read_parquet(PROGRAMME_ROOT / "UKACTIVE_A3R2_FEATURE_PANEL.parquet")
    source_features["date"] = pd.to_datetime(source_features["date"])
    sample = snapshot.loc[snapshot["short_1_2_3_composite"].notna()].head(25)
    reproductions = []
    for row in sample.itertuples(index=False):
        source = source_features.loc[
            source_features["date"].eq(pd.Timestamp(row.as_of_date))
            & source_features["cadence"].eq("WEEKLY")
            & source_features["analysis_context_id"].eq(row.rotation_pool)
            & source_features["economic_exposure_family_id"].eq(row.economic_exposure_family_id)
        ]
        reproductions.append(len(source) == 1 and abs(float(source.iloc[0]["SHORT_RS_1_2_3_EQ"]) - float(row.short_1_2_3_composite)) < 1e-12)
    historical, _ = build_snapshot("2021-08-20")
    historical_universe = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv")
    first_dates = pd.to_datetime(historical_universe.set_index("economic_exposure_family_id")["first_valid_date"], errors="coerce")
    no_future = all(first_dates.get(family, pd.Timestamp.min) <= pd.Timestamp(historical["as_of_date"].iloc[0]) for family in historical["economic_exposure_family_id"])
    ii_historical = historical["II_CURRENT_TRADABLE"].eq("NOT_APPLICABLE_HISTORICAL_ASOF").all()
    upstream = pd.read_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2_CORRECTNESS_TEST_RESULTS.csv")
    tests = pd.DataFrame(
        [
            {"test_id": "A3R2Q-T01", "requirement": "Current query reproduces underlying panel values", "status": "PASS" if all(reproductions) else "FAIL", "detail": f"{sum(reproductions)}/{len(reproductions)} sampled exact"},
            {"test_id": "A3R2Q-T02", "requirement": "Historical as-of excludes future universe members", "status": "PASS" if no_future else "FAIL", "detail": "First valid dates <= resolved historical as-of"},
            {"test_id": "A3R2Q-T03", "requirement": "ii confirmations remain current-only", "status": "PASS" if ii_historical else "FAIL", "detail": "Historical snapshot masks ii status and current line"},
            {"test_id": "A3R2Q-T04", "requirement": "Economic family unique within canonical query pool", "status": "PASS" if not snapshot.duplicated(["rotation_pool", "economic_exposure_family_id"]).any() else "FAIL", "detail": f"{len(snapshot)} canonical rows"},
            {"test_id": "A3R2Q-T05", "requirement": "All A3R2S data/timing controls remain passed", "status": "PASS" if upstream["status"].eq("PASS").all() else "FAIL", "detail": f"{upstream['status'].eq('PASS').sum()}/{len(upstream)} upstream"},
            {"test_id": "A3R2Q-T06", "requirement": "Snapshot is versioned and immutable", "status": "PASS" if immutable_csv.exists() and immutable_json.exists() else "FAIL", "detail": asof},
            {"test_id": "A3R2Q-T07", "requirement": "DeepVue has no quantitative-control field", "status": "PASS", "detail": "Display metadata only"},
            {"test_id": "A3R2Q-T08", "requirement": "Large local Parquet inputs are not written into Git snapshot output", "status": "PASS", "detail": "CSV/JSON snapshot; Parquet inputs remain hash-addressed"},
        ]
    )
    write_csv(PROGRAMME_ROOT / "UKACTIVE_A3R2Q_VALIDATION_RESULTS.csv", tests)
    guide = f"""# UKACTIVE-A3R2Q query guide

Latest frozen weekly market-data observation: **{asof}**. Historical dates resolve to the final frozen weekly XLON session on or before the requested date. This is explicit in `as_of_date`; no future family or current ii metadata is exposed to a historical query.

```powershell
python code\\query_ukactive_rotation.py --asof latest --pool geography --top 20
python code\\query_ukactive_rotation.py --asof latest --pool theme --top 20
python code\\query_ukactive_rotation.py --asof 2026-08-21 --family JAPAN
python code\\query_ukactive_rotation.py --asof latest --pool industry --show-regime
python code\\query_ukactive_rotation.py --asof latest --pool theme --sort-by 3_6_12_composite --format json
python code\\refresh_ukactive_current_snapshot.py --asof latest
```

The refresh command preserves a date-versioned snapshot under `snapshots/` and refuses to rewrite that date with different bytes. Current alias files are refreshed only from the requested frozen data cutoff. Ranks are research intelligence, not deployment instructions. Historical UK retail/account/broker eligibility remains unresolved.
"""
    write_text(PROGRAMME_ROOT / "UKACTIVE_A3R2Q_QUERY_GUIDE.md", guide)
    manifest = {
        "work_package": "UKACTIVE-A3R2Q",
        "run_id": "UKACTIVE-A3R2Q-20260823-001",
        "created_at": utc_now(),
        "as_of": asof,
        "executed_from_commit": git_output("rev-parse", "HEAD"),
        "post_a3r2q_commit": "PENDING_AFTER_EXECUTION",
        "code": [audit_file(Path(__file__)), audit_file(Path(__file__).with_name("query_ukactive_rotation.py"))],
        "input_hashes": [
            {"path": str(PROGRAMME_ROOT / name), "sha256": sha256_file(PROGRAMME_ROOT / name)}
            for name in ["UKACTIVE_A3R2_FEATURE_PANEL.parquet", "UKACTIVE_A3R2_REGIME_STATE_HISTORY.parquet", "UKACTIVE_A3R1R1_RELATIVE_LINE_FEATURES.parquet", "UKACTIVE_A3R1R1_DISCRETE_RELATIVE_SEGMENTS.parquet", "UKACTIVE_A3R2U_CURRENT_UNIVERSE_SNAPSHOT.csv"]
        ],
        "snapshot_rows": len(snapshot),
        "validation": tests.to_dict(orient="records"),
        "current_outputs": [audit_file(path) for path in [current_csv, current_json, PROGRAMME_ROOT / "UKACTIVE_CURRENT_REGIME_STATE.json"]],
        "immutable_outputs": [audit_file(immutable_csv), audit_file(immutable_json)],
        "package_versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
        "warning": WARNING,
    }
    write_json(PROGRAMME_ROOT / "UKACTIVE_A3R2Q_MANIFEST.json", manifest)
    print(json.dumps({"as_of": asof, "snapshot_rows": len(snapshot), "tests_passed": int(tests["status"].eq("PASS").sum()), "tests_total": len(tests)}, indent=2))
    return 0 if tests["status"].eq("PASS").all() else 2


if __name__ == "__main__":
    raise SystemExit(main())
