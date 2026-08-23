# UKACTIVE-A3R2 regime definitions

These definitions were frozen before portfolio results. Regimes are descriptive and cannot filter A3R2 portfolios.

| Regime | Frozen definition |
|---|---|
| Global trend | `GLOBAL_DEVELOPED_WORLD` GBP total-return wealth above/below its trailing 200-valid-session simple moving average. |
| Global volatility | Trailing 63-valid-session annualised realised volatility. LOW/NORMAL/HIGH use prior-only expanding 33rd/67th percentiles after at least 252 observations. |
| Cross-sectional dispersion | Standard deviation of valid all-equity RS63 values. LOW/NORMAL/HIGH use prior-only expanding weekly 33rd/67th percentiles after 52 observations. |
| Leadership breadth | Fraction of eligible all-equity families with positive RS63: NARROW below one-third; MEDIUM below two-thirds; BROAD otherwise. |
| Rotation intensity | Median absolute within-pool RS63 percentile-rank change over 21 XLON sessions. LOW/NORMAL/HIGH use prior-only expanding weekly 33rd/67th percentiles after 52 observations. |
| US technology dominance | DOMINANT when at least two of the all-equity top five are US-technology/semiconductor related and at least one is in the top two. |
| ETF-universe breadth | Contemporaneous eligible family, industry, theme, and recent-launch counts. |

At most two regime dimensions may be combined in one diagnostic. Thresholds are shifted so date-T classification cannot see date-T or future outcomes. Old-versus-recent disagreement is classified separately from the signal and may indicate structural change, universe expansion, data coverage, sample luck, or remain unresolved.
