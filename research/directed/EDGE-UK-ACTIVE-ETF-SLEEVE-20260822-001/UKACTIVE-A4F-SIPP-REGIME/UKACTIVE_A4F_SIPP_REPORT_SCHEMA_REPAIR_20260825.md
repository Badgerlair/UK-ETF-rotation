# UKACTIVE-A4F-SIPP report-schema repair — 2026-08-25

The first post-repair full build stopped before final output generation because the year-by-year narrative referenced the public CSV alias `absolute_support_count` on the in-memory canonical ledger, where the field remains `absolute_leadership_support` until export.

This repair changes only that narrative schema reference. It does not alter any signal, regime, threshold, allocation, return, gate, selection or evidence boundary. The failed mixed output set was not committed. A complete atomic rebuild and all correctness tests are required after this repair.
