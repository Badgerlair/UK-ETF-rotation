# UKACTIVE-A2R2 gap and staleness policy

- Latest formation endpoint: exact signal-date observation only.
- Historical boundary: exact nominal session, or nearest previous valid endpoint within 3 sessions.
- Continuity bridge: at most 3 genuine XLON sessions, calculated from two validated endpoints of the same listing.
- Missing intervening rows remain missing.
- Stale observations remain invalid and are never assigned a zero return.
- Longer gaps reset the continuity segment and cannot be crossed by formation or forward returns.
- Implementation transitions continue only when both lines remain in the same frozen A2R economic fingerprint and the incoming line has a recent prior validated endpoint; otherwise the segment resets.

The three-session tolerance was selected before the corrected A3R1 results were run. It covers ordinary international fund holidays and short vendor timing gaps without bridging a material suspension; it was not chosen to improve a signal result.
