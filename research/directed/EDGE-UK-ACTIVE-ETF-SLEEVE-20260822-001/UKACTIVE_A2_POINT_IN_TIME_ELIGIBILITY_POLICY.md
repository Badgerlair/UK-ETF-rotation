# UKACTIVE A2 — Point-in-Time Eligibility Policy

Historical states are stored independently for fund existence, share-class existence, listing existence, listing activity, price availability, return availability, warm-up availability, structural evidence, UK retail knowledge and account-eligibility knowledge.

`HISTORICALLY_VERIFIED_INVESTABLE` is reserved for contemporaneous dated evidence. The current run has no basis for assigning that state retrospectively. `HISTORICALLY_PROBABLE` is a low-confidence research label used only when a currently verified share class also has an exact-identity contemporaneous LSE price observation. It does not mean historical ISA, SIPP or broker eligibility was verified. All other extant routes are `HISTORICALLY_UNCERTAIN` unless affirmative dated evidence establishes another state.

`NOT_YET_EXISTING` is used only before an evidenced inception date. Unknown pre-observation periods remain unknown rather than being converted into a negative claim.

CURRENT ELIGIBILITY MUST NOT BE BACK-PROJECTED HISTORICALLY.
