# SimRacingPitStop · Experiences

Canonical catalog of every preset Pablo runs in Assetto Corsa. Each subfolder holds:

- `README.md` — scenario, goal, specs
- `image.jpg` — hero image (matches the Launch Bay dashboard tile)
- `Launch.lnk` — double-click to run the experience
- (some) extra reference shots / video links

The Launch Bay dashboard at `../launcher/launcher_dashboard.py` reads from the same source-of-truth (`CONFIGS` list). When you add a new experience, mirror it in both places.

| # | Folder | Type | Track | Launcher |
|---|---|---|---|---|
| 01 | `01_24h_nurburgring_2026` | RACE  | Nordschleife · Endurance Cup | `launch_24h_nurburgring_2026.cmd` |
| 02 | `02_nls2_pole_chase`      | HOTLAP | Nordschleife · Endurance Cup | `launch_nls2_2026.cmd` |
| 03 | `03_verstappen_vs_haase`  | DUEL  | Nordschleife · Endurance Cup | `launch_verstappen_1v1.cmd` |
| 04 | `04_canadian_gp_2026`     | RACE  | Montreal · F1 2025 | `launch_canada_2026.cmd` |
| 05 | `05_montreal_hotlap`      | HOTLAP | Montreal · F1 2025 | `launch_hotlap_montreal_2026.cmd` |
| 06 | `06_super_gt_fuji_wet`    | DUEL  | Fuji Speedway 2017 (wet) | `launch_hotlap_super_gt_fuji_chase.cmd` |

## Pending

- **Crew Chief auto-launch** — when any of the .cmd launchers fires, also start `CrewChiefV4.exe` and auto-press its "Start Crew Chief" button. Wired through these `.cmd` files once approach is decided.
