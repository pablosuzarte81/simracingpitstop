# SimRacingPitStop · Challenges Catalog

Full inventory of every dashboard tile, the car/track it loads, and the launcher chain. Source of truth for the dashboard `CONFIGS` list at `launcher/launcher_dashboard.py:90`.

**Total: 33 tiles across 8 series · all launchers wired with the full Crew Chief auto-start chain + AC-exit watcher.**

---

## NLS · NÜRBURGRING (7)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 1 | MINI 24H NÜRBURGRING | RACE | Mercedes-AMG GT3 #3 (Mercer V8) | Nordschleife · Endurance Cup | 16-car SP9 PRO grid · 2 laps · pole start |
| 2 | MINI 24H POLE CHASE | HOTLAP | Mercedes-AMG GT3 #3 | Nordschleife · Endurance Cup | Solo · ghost on |
| 2b | HOT LAP THE 24H NÜRBURGRING | HOTLAP | 16 × SP9 PRO GT3 (full 2026 entry list — Mercer, Aero, Protech, Hyperion, Lanzo) | Nordschleife · 24h 2024 layout | 16 launchers · one solo hot-lap per car · same Engstler 8:11.123 target as #2 · AC default setup per car |
| 3 | VERSTAPPEN VS HAASE | DUEL | Mercer #3 vs Audi R8 #16 | Nordschleife · 24h 2024 layout | 1-lap head-to-head |
| 4 | HAASE VS VERSTAPPEN | DUEL | Audi R8 #16 vs Mercer #3 (inverted) | Nordschleife · 24h 2024 layout | 1-lap head-to-head |
| 4b | HAASE VS VERSTAPPEN · NIGHT + RAIN | DUEL | Audi R8 #16 vs Mercer #3 (driver selector) | Nordschleife · 24h 2024 layout | 1-lap night wet drill · sol_36_heavy_rain |
| 4c | VERSTAPPEN VS HAASE · 3 LAPS · DUSK STORM | DUEL | Mercer #3 vs Audi R8 #16 (driver selector) | Nordschleife · 24h 2024 layout | 3-lap wet stint, starts at CSP deep dusk (SUN_ANGLE=88) in `sol_34_light_rain`, TIME_MULT=4× advances to full dark by lap 3. Pure rest of stack lives in race.ini — no Pure Planner dependency. |

## FORMULA 1 (5)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 5 | CANADIAN GP 2026 | RACE | Red Bull RB21 (RSS Alpine) | Montreal · F1 2025 | 19-car real grid · 5 laps · charge from P19 |
| 6 | MONTREAL HOTLAP | HOTLAP | Red Bull RB21 (RSS Alpine) | Montreal · F1 2025 | Solo · ghost on |
| 7 | CANADIAN GP · VRC GRID | RACE | Red Bull RB21 (VRC Pro) | Montreal · F1 2025 | 20-car real grid · 5 laps · charge from P20 |
| 8 | CANADA POLE CHASE · VRC | HOTLAP | Red Bull RB21 (VRC Pro) | Montreal · F1 2025 | Solo · ghost on (PB 1:19.380) |
| 8b | VETTEL · RB7 · NORDSCHLEIFE | HOTLAP | F1 2011 Red Bull RB7 #1 (`cim_2011_redbull`) | Nordschleife · 24h 2024 layout | Solo · ghost on · V8 era tribute |

## SCHUMACHER · ICONIC RACES (9)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 9 | MONTREAL · F2004 | HOTLAP | Ferrari F2004 #1 | Montreal · F1 2025 | Solo · ghost on (PB 1:18.810) |
| 10 | SPA · 1991 DEBUT | HOTLAP | Jordan 191 #32 Schumacher | Spa · F1 2025 layout | Solo · debut weekend tribute |
| 11 | MONZA · TIFOSI | HOTLAP | Ferrari F2001 #3 Schumacher Monza | Monza · F1 2025 | Solo · ghost on |
| 12 | IMOLA · 7-TIME KING | HOTLAP | Ferrari F2001 #1 Schumacher | Imola · F1 2022 | Solo · ghost on |
| 13 | SUZUKA · 2001 TITLE | HOTLAP | Ferrari F2001 #1 Schumacher | Suzuka GP | Solo · ghost on |
| 14 | BENETTON vs FERRARI · '93 | DUEL | Benetton B193 #5 vs Ferrari F93A | Spa · F1 2025 layout | 1-lap cross-team |
| 15 | IMOLA · TEAMMATE DUEL | DUEL | F2001 #1 vs F2001 #2 | Imola · F1 2022 | 1-lap intra-Ferrari |
| 16 | 1993 GRID · SPA | RACE | Benetton/Ferrari/Jordan 1993 | Spa · F1 2025 layout | 6-car cross-team grid · 5 laps · P6 start |
| 17 | MONZA · F2001 TIFOSI | RACE | 4× Ferrari F2001 | Monza · F1 2025 | 4-car sprint · 5 laps · P4 start |

## SENNA TRIBUTE (7) — all in McLaren MP4/8 (1993)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 18 | DONINGTON 1993 | HOTLAP | McLaren MP4/8 #8 Senna | Donington Park 2018 GP | Solo · "Lap of God" homage |
| 19 | SUZUKA 1988 | HOTLAP | McLaren MP4/8 #8 Senna | Suzuka GP | Solo · ghost on |
| 20 | MONACO 1988 | HOTLAP | McLaren MP4/8 #8 Senna | Monaco | Solo · ghost on |
| 21 | ESTORIL 1985 | HOTLAP | McLaren MP4/8 #8 Senna | Estoril | Solo · ghost on |
| 22 | SENNA VS PROST · MONACO '88 | DUEL | MP4/8 #8 Senna vs MP4/8 #7 Andretti (livery) | Monaco | 1-lap teammate duel |
| 23 | SENNA VS PROST · SUZUKA '88 | DUEL | MP4/8 #8 Senna vs MP4/8 #7 Andretti (livery) | Suzuka GP | 1-lap teammate duel |
| 24 | SENNA VS SCHUMI · DONINGTON '93 | DUEL | MP4/8 #8 Senna vs Benetton B193 Schumacher | Donington Park 2018 GP | 1-lap wet drill |

## F1 2008 (1)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 25 | INTERLAGOS 2008 | RACE | McLaren MP4-23 #22 Hamilton | Interlagos | Hamilton's title clincher |

## SUPER GT · GT500 (1)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 26 | SUPER GT FUJI · WET | DUEL | Nissan Z NISMO GT500 | Fuji Speedway 2017 | Verstappen-Miyake re-creation |

## DAVE CAM TRIBUTES (1)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 28 | AUDI 90 GTO · NORDSCHLEIFE | RACE | Audi 90 Quattro IMSA GTO 1989 (ORS mod) | Nordschleife · standalone (iRacing layout) | 6-car GTO grid · 2 laps · standing start · beat Dave Cam's 6:43.683 on lap 2 ([source video](https://www.youtube.com/watch?v=DIl_vf5tdgE)) |

## FAN HEROES · N24 (1)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 29 | THE SHOPPING CART AT THE GREEN HELL | HOTLAP | Dacia Logan 1.6 #300 (`rlr_logan_2008cup` · Ollis Garage Racing skin) | Nordschleife · 24h 2024 layout | Solo · ghost on · 2026 N24 SP 3T tribute · car runs ~12 min vs GT3 8:11 — finish the lap, wave the GT3s past |

---

## How a tile launches (the chain)

Every launcher follows the same template. From dashboard click → race in AC:

1. **Dashboard POST** `/launch?id=<tile_id>` → server calls `launch_<...>.cmd` via `powershell.exe Start-Process`
2. **Backup current `cfg/race.ini`** → `cfg/race.ini.bak`
3. **Install the preset** — copies `cfg/<race|hotlap|duel>_<id>.ini` → `cfg/race.ini`
4. **`call launcher\start_crew_chief.cmd`** which:
   - launches `CrewChiefV4.exe` if not running
   - runs `launcher\click_cc_start.ps1` (UI Automation auto-presses the **Start Crew Chief** button — has to be a real mouse click; the button doesn't expose `InvokePattern`)
5. **`start "" /D "%ACINSTALL%" "%ACINSTALL%\acs.exe"`** — launches AC directly (bypasses Steam launcher)
6. **`launcher\wait_and_close_cc.ps1`** — async watcher: waits for `acs.exe` to exit, then kills CrewChiefV4 so the next launch starts fresh

## Naming conventions (so things stay wired)

- **Multi-car races** → `cfg/race_<id>.ini` (CARS≥2, full grid with per-CAR_n driver/skin/team/MODEL)
- **Solo hotlaps** → `cfg/hotlap_<id>.ini` (CARS=1, ghost on, TYPE=4, SPAWN_SET=HOTLAP_START)
- **1v1 duels** → `cfg/duel_<id>.ini` (CARS=2, TYPE=3 race, RACE_LAPS=1)
- **Each launcher** → `launch_<basename>.cmd` matching the .ini basename
- **Tile ID** in CONFIGS → matches launcher base (used by dashboard to fire the right .cmd)

## Track-config gotchas (learned the hard way)

| Track / config | AI files? | Notes |
|---|---|---|
| `ks_nordschleife/endurance_cup` | YES | NLS combo, default working layout |
| `ks_nordschleife/nordschleife` | YES (`fast_lane.ai` + `pit_lane.ai`) | Standalone 20.8 km layout — matches iRacing's Nordschleife. Use this for benchmark-style references like Dave Cam's 6:43. |
| `ks_nordschleife/nordschleife_24hours_2024` | YES (incl. `pit_lane_with_grid.ai`) | 24h-specific layout — works for 2-car duels |
| `spa/layout_f1_2020` | **NO** | Pick `spa/layout_f1_2025` instead |
| `spa/layout_f1_2025` | YES | Works for races + hotlap |
| `monza/monza_f1_2025` | YES | |
| `imola/imola_f1_2022` | YES | |
| `rt_suzuka/suzukagp` | YES | Classic GP layout |
| `doningtonpark2018/gp` | YES | |
| `montreal/montreal_f1_2025` | YES | |
| `fuji/fuji_2017` | YES | |

**Rule:** every race/duel needs `fast_lane.ai` + `pit_lane.ai` in the track's config dir. If they're missing, AI cars sit on grid → "alone on track" symptom.

## Anti-patterns I learned by breaking things

- **Don't run `launcher/scaffold_new_presets.py` blind** — it overwrites launchers with bare templates (no Crew Chief chain) and rewrites `.ini` files to CARS=1 stripped configs (no skin, no GHOST_CAR, no proper grid). When this happens, races load 1 car instead of the full grid → "alone on track".
- **Don't repoint launcher PRESET= to a different filename without verifying that .ini has the proper grid** — the scaffold did this (e.g. `launch_canada_2026.cmd` → `cfg/canada_2026.ini` instead of `cfg/race_canada_2026.ini`).
- **Don't switch a track config without verifying `fast_lane.ai` exists.** I switched 3 Nürburgring tiles to `nordschleife_24hours_2024` thinking it would help; the layout works for 1v1 (has grid AI) but not all combinations behave the same — verify each tile's grid loads.
- **Don't change a working tile's CONFIG_TRACK without cause.** If the user says "the race layout is wrong", clarify which tile and which direction; don't blanket-update.

## Recovery

The full project is in git (`/mnt/c/Users/pablo/Documents/Assetto Corsa/.git`). To roll any tile back:

```bash
cd "/mnt/c/Users/pablo/Documents/Assetto Corsa"
git log --oneline -- cfg/<file>.ini
git checkout <commit> -- cfg/<file>.ini
```

To restore the entire dashboard or every preset:
```bash
git diff HEAD -- launcher/ cfg/   # see what changed
git checkout HEAD -- launcher/ cfg/   # nuke local edits
```
