# UKACTIVE A2 — A3 Readiness

Decision: `UKACTIVE_A2_PASS_WITH_OPEN_ITEMS`

A3-ready A0A1 families: **86**. The readiness rule requires at least 504 consecutive-valid-capable observations, an actual implementation history and no failed return/FX/price-unit gate. Tier metadata is preserved, so A3 can distinguish CORE from CORE + EXTENDED without rebuilding data.

A3 signal discovery authorised: **YES**.

If authorised, A3 is research-only and must use the point-in-time flags, prior-session information mapping and duplicate-safe economic-family rows. It may not call an uncertain historical eligibility state verified investability, may not splice the empty proxy panel into live histories and may not make deployment claims. Broker confirmation remains mandatory before any future `DEPLOYMENT_CANDIDATE` state.

Open items: 19. Families requiring a proxy for a 504-observation research window: 13.
