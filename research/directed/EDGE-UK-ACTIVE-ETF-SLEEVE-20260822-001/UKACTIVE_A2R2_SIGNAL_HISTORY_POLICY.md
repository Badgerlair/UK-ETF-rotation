# UKACTIVE-A2R2 signal-history policy

For an h-session formation return, A2R2 compares the exact valid signal-date GBP total-return-index endpoint with the nominal h-session historical endpoint. If that historical boundary is unavailable, only the nearest **previous** valid endpoint within **3** genuine XLON sessions may be used. The actual date and elapsed sessions are recorded.

The signal-date endpoint must be exact. A future endpoint is never used at a formation boundary. Forward returns require exact endpoints at T and T+h and exclude date-T return.

A missing daily return does not imply that all later formation endpoints lack information. Conversely, an adjusted-wealth endpoint is valid only when the price exists, is non-stale, non-proxy, post-inception, semantically valid and belongs to a total-return route that passed A2/A2R validation.

No price, return or relative-strength series is forward-filled. No zero return is manufactured. No proxy enters. A gap exceeding **3** XLON sessions resets the continuity segment, so formation and forward returns cannot cross a long suspension.
