# UKACTIVE-A5C-SIPP data-cutoff audit

- Authoritative historical research cutoff: **2026-08-21**.
- A4F result commit: `6dba072dce65da56284a8c02f9f380301048d492`.
- No post-cutoff observation is permitted in historical model choice or specification changes.
- The prospective lineage is empty at freeze.
- The first official decision must be a month-end strictly after the freeze commit and must be recorded before the following eligible execution-session close is known.
- No prospective decision, execution, NAV, cost, or performance row is created by the setup/freeze stage.

## Canonical input hashes

| Input | SHA-256 |
|---|---|
| A4F manifest | `0e54cd1bf80fd8a3ca8fe72fd0e94e7479d7ff3135bd9f266bac4e4064940d3d` |
| A4F selected strategy | `9099374eb6ac32f470a92e5a34dede60116ff96cd80ba62e3ab774772bcc1dbe` |
| A4F static frontier | `7c844a6f209913c56fbb5b096054b08714a4a5610fa0168d77baa4b0f3f39414` |
| A4F M2 incremental value | `0f98849f29ef47cb8a7c8215bccbad828ebda22b936deaff4b8a8aabc7f14097` |
| A4E live instrument map | `066bfa7e838bfa5fb8be69fe225fb369f444e23c937a6aec45d486877fdf510` |
| Corrected GBP total-return panel | `76cf0dc9c2fc1644954e7628d9d82f50ee0c4792896565c9ad48ee2fad5086a3` |
| Corrected signal eligibility | `335661815c1102b5985802a6ed37db359257148db9159b3759691aac92ae8bff` |
| Signal endpoint history | `af2beafded2c190700360dbc2f3615f0c2c98759e920bf232b213f20e7df31bf` |
| Dynamic universe | `6b9a500a41dc1fe7b7c8bedb5d9a2c9087b53855d5e8f32a1790a340f0768044` |
| 27-family role master | `8fd81aca2dd90ad2090282839243072dec276228d1c546559ffe3883dbb3c61b` |

## Audit result

`PASS — FREEZE CONTAINS NO POST-CUTOFF MODEL INPUT AND NO PROSPECTIVE EVENT`
