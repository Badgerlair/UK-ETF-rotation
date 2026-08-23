# UKACTIVE-A5 report schema

Every report includes: run status; validated cutoff; official or explicitly provisional choice; slow top five; A5-A state; A5-B state; pending execution; six-row scorecard; comparator deltas; high-water marks/drawdowns; costs/turnover; weekly FAST telemetry; geographic leadership; regime fields; evidence progress; warnings; next required run; and an explicit no-order statement.

Annualised return, volatility, Sharpe, Sortino, Calmar, Ulcer Index and rolling-12-month statistics remain `N/A — INSUFFICIENT PROSPECTIVE HISTORY` until their frozen minimum history exists. Cumulative NAV and pounds are always shown after execution starts.

Latest aliases may be regenerated. Files under `snapshots/a5/UKACTIVE_A5_RUN_<ASOF>_<RUN_ID>.*` are immutable and use a deterministic run ID, so an idempotent repeat cannot create another snapshot.
