# SimRacingPitStop · Challenges Catalog

Full inventory of every dashboard tile, the car/track it loads, and the launcher chain. Source of truth for the dashboard `CONFIGS` list at `launcher/launcher_dashboard.py:90`.

**Total: 81 tiles across 8 series · all launchers wired with the full Crew Chief auto-start chain + AC-exit watcher.**

> **Active challenges (★):** every challenge card and challenge page has a star toggle. Starring pins the challenge to the **Active challenges** section (client-side, `localStorage` key `activeChallenges`, filled via `/api/active-cards`). **F1 · 2026 Calendar tab** (`/f1-2026`) lists the whole season in calendar order. Site typography is **Titillium Web** (the free stand-in for F1's official "Formula1" face) with the F1 red accent.

---

## NLS · NÜRBURGRING (8)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 1 | MINI 24H NÜRBURGRING | RACE | Mercedes-AMG GT3 #3 (Mercer V8) | Nordschleife · Endurance Cup | 16-car SP9 PRO grid · 2 laps · pole start |
| 4d | M3 TOURING · GREEN HELL | HOTLAP | BMW M3 Touring GT3 EVO 2025 #81 Schubert Motorsport (`cky_bmw_m3_gt3_evo` · `24h_NBR_BMW-Post-191` skin — renders as the real #81 Shell Helix car) | Nordschleife · 24h 2024 layout | Solo · ghost on · 2026 N24 SP-X class winner (5th overall) tribute · on `/event/n24_2026` · built to the hotlap-event template · Engstler 8:11.123 GT3-pole target |
| 2 | MINI 24H POLE CHASE | HOTLAP | Mercedes-AMG GT3 #3 | Nordschleife · Endurance Cup | Solo · ghost on |
| 2b | HOT LAP THE 24H NÜRBURGRING | HOTLAP | 16 × SP9 PRO GT3 (full 2026 entry list — Mercer, Aero, Protech, Hyperion, Lanzo) | Nordschleife · 24h 2024 layout | 16 launchers · one solo hot-lap per car · same Engstler 8:11.123 target as #2 · AC default setup per car |
| 3 | VERSTAPPEN VS HAASE | DUEL | Mercer #3 vs Audi R8 #16 | Nordschleife · 24h 2024 layout | 1-lap head-to-head |
| 4 | HAASE VS VERSTAPPEN | DUEL | Audi R8 #16 vs Mercer #3 (inverted) | Nordschleife · 24h 2024 layout | 1-lap head-to-head |
| 4b | HAASE VS VERSTAPPEN · NIGHT + RAIN | DUEL | Audi R8 #16 vs Mercer #3 (driver selector) | Nordschleife · 24h 2024 layout | 1-lap night wet drill · sol_36_heavy_rain |
| 4c | VERSTAPPEN VS HAASE · 3 LAPS · DUSK STORM | DUEL | Mercer #3 vs Audi R8 #16 (driver selector) | Nordschleife · 24h 2024 layout | 3-lap wet stint, starts at CSP deep dusk (SUN_ANGLE=88) in `sol_34_light_rain`, TIME_MULT=4× advances to full dark by lap 3. Pure rest of stack lives in race.ini — no Pure Planner dependency. |

## FORMULA 1 (52)

| # | Tile | Type | Car | Track | Format |
|---|---|---|---|---|---|
| 5 | CANADIAN GP 2026 | RACE | Red Bull RB21 (RSS Alpine) | Montreal · F1 2025 | 19-car real grid · 5 laps · charge from P19 |
| 6 | HOTLAP ANY 2026 F1 DRIVER | HOTLAP | RSS Formula Hybrid 2025 Alpine (`rss_formula_hybrid_2025_alpine`) — 2026 grid: 20 of 22 drivers (Verstappen+Hadjar @ RBR, Lawson+Lindblad @ RB, etc.); Cadillac (Pérez/Bottas) omitted — no livery on this car | Montreal · F1 2025 | Solo · ghost on · driver-index chooser (20 launchers) · shared `Montreal_Hotlap_v1` setup · keeps your PB Evolution |
| 7 | CANADIAN GP · VRC GRID | RACE | Red Bull RB21 (VRC Pro) | Montreal · F1 2025 | 20-car real grid · 5 laps · charge from P20 |
| 8 | CANADA POLE CHASE · VRC | HOTLAP | Red Bull RB21 (VRC Pro) | Montreal · F1 2025 | Solo · ghost on (PB 1:19.380) |
| 8b | VETTEL · RB7 · NORDSCHLEIFE | HOTLAP | F1 2011 Red Bull RB7 #1 (`cim_2011_redbull`) | Nordschleife · 24h 2024 layout | Solo · ghost on · V8 era tribute |
| 8d | STEWART · MARCH 701 · NORDSCHLEIFE | HOTLAP | RSS March 701 #1 Stewart (`rss_formula_70` · `1970_tyrrell_1_stewart` skin) | Nordschleife · 24h 2024 layout | Solo · ghost on · 1970 vintage-F1 tribute · on `/event/n24_2026` · sibling to the Vettel RB7 hotlap |
| 8c | HOTLAP ANY 2025 F1 DRIVER | HOTLAP | VRC Formula Alpha 2025 (`vrc_formula_alpha_2025_csp`) — full 2025 grid, all 20 drivers/10 teams | Montreal · F1 2025 | Solo · ghost on · driver-index chooser (20 launchers) · shared `Montreal_VRC_Hotlap` setup · on `/event/montreal_2026` |
| 8e | MONACO 2026 · POLE CHASE | HOTLAP | Antonelli Mercedes-AMG W16 (`rss_formula_hybrid_2025_alpine` · `Asi_W16_Antonelli_12` skin) | Monaco · F1 2025 (`monaco_2020`/`monaco_f1_2025`) | Solo · ghost on · built to the hotlap-event template · on `/event/monaco_2026` · TYPE=4 hotlap (spawns on track) · loads Pablo's own 25 May Monaco setup (`Monaco_Hotlap_2026`) by default via last.ini pre-write, but FIXED_SETUP=0 leaves the garage open so any setup can be chosen in-game · Evolution shows the climb to his 1:12.912 PB via `evolution_mode: "laps"` · target = Antonelli's 1:12.051 (2026 Monaco GP pole, verified 2026-06-07; portrait `antonelli_portrait.png`) · WATCH section embeds the self-hosted pole-lap video (`images/videos/monaco_2026_antonelli_pole.mp4`, FOM blocks the YouTube iframe) · in-game best-time cache corrected to 1:12.912 (personalbest.ini + LeaderboardHUD data.ini) |
| 8f | MONACO GP 2026 | RACE | Red Bull RB21 (`rss_formula_hybrid_2025_alpine` · `M17_RedBull_RB21_1` skin) | Monaco · F1 2025 (`monaco_2020`/`monaco_f1_2025`) | 19-car real 2026 grid (same roster as Canada) · 5 laps · **start P1 on pole** (AC forces player to CAR_0; at Monaco track position is the race — win from pole and defend) · on `/event/monaco_2026` · sibling to the 8e pole-chase hotlap · `launch_race_monaco_2026.cmd` → `cfg/race_monaco_2026.ini` · Monaco track verified: 30 pitboxes, fast_lane.ai + pit_lane.ai present |
| 8g | MONACO · FERRARI F2004 | HOTLAP | Ferrari F2004 V10 (`ks_ferrari_f2004` · `00_official` skin) | Monaco · F1 2025 (`monaco_2020`/`monaco_f1_2025`) | Solo · ghost on · Schumacher's 2004 championship V10 around Monte Carlo (analog F1, no aids) · on `/event/monaco_2026` · `launch_hotlap_monaco_f2004.cmd` → `cfg/hotlap_monaco_f2004.ini` · no historic ref (set your own bar) |
| 8h | MONACO · JORDAN 191 · SCHUMACHER | HOTLAP | Jordan 191 (`vrc_1991_jordan_191` · `32_schumacher` skin — verified on disk) | Monaco · F1 2025 (`monaco_2020`/`monaco_f1_2025`) | Solo · ghost on · tribute to Schumacher's 1991 debut car (he debuted it at Spa, never raced it at Monaco — what-if drive) · on `/event/monaco_2026` · `launch_hotlap_monaco_jordan.cmd` → `cfg/hotlap_monaco_jordan.ini` |
| 8i | MONACO · SENNA · McLAREN | HOTLAP | McLaren MP4/8 #8 Senna (`asr_1993_mclaren_mp4-8` · `8_senna_r1_r2_r4_r5_r6_r7` skin — verified; the older Senna duel references a non-existent `12_Senna_R02` skin) | Monaco · F1 2025 (`monaco_2020`/`monaco_f1_2025`) | Solo · ghost on · King of Monaco tribute (Senna's record 6 wins) · reuses the existing `launch_hotlap_senna_monaco.cmd` → `cfg/hotlap_senna_monaco.ini` · on `/event/monaco_2026` |
| 8j | SPANISH GP 2026 · POLE CHASE | HOTLAP | Antonelli Mercedes-AMG W16 (`rss_formula_hybrid_2025_alpine` · `Asi_W16_Antonelli_12` skin) | Barcelona-Catalunya (`fn_barcelona`/`layout_gp_2025_fnr` — 24 pitboxes, 4.657 km, AI verified) | Solo · ghost on · built to the hotlap-event template · on `/event/barcelona_2026` · TYPE=4 hotlap · FIXED_SETUP=0 (no saved setup yet, garage open) · Evolution `laps` mode · target = Antonelli's 2026 Spanish GP pole (**time PENDING** — awaiting verified figure) · `launch_hotlap_barcelona_2026.cmd` → `cfg/hotlap_barcelona_2026.ini` |
| 8k | SPANISH GP 2026 | RACE | Antonelli Mercedes-AMG W16 (`rss_formula_hybrid_2025_alpine` · `Asi_W16_Antonelli_12` skin) | Barcelona-Catalunya (`fn_barcelona`/`layout_gp_2025_fnr`) | 19-car real 2026 grid (player takes Antonelli's pole seat; Verstappen + 17 others fill the field) · 5 laps · **start P1 on pole** · on `/event/barcelona_2026` · sibling to the 8j pole-chase hotlap · `launch_race_barcelona_2026.cmd` → `cfg/race_barcelona_2026.ini` · benchmark Antonelli pole **time PENDING** |

### F1 2026 CALENDAR (38 tiles · 19 events)

Generated from `F1_2026_SPECS` in `launcher/launcher_dashboard.py` (one spec → a `/event/<slug>_2026` page with a pole-chase **HOTLAP** + a 5-lap **RACE**). Built to the exact Barcelona/Monaco pattern: player = Pablo in **Antonelli's Mercedes-AMG W16** (`Asi_W16_Antonelli_12`), starting P1 on pole; field = the same real 2026 grid as `race_barcelona_2026.ini`. Car = `rss_formula_hybrid_2025_alpine` for all. Pole lap times are **PENDING** (not invented). Card art = each AC track's `preview.png` (circuit photo) + `outline.png` (track map) — no car photos. Presets/launchers regenerated by `launcher/gen_f1_2026_assets.py`. **Madrid ("Gran Premio de España") has no Madring track in AC, so it runs at MotorLand Aragón (`fn_aragon/gp`) as a Spanish stand-in — clearly labelled on the tile.**

| Event slug | GP | Track / layout (all verified: AI + ≥30 pitboxes) |
|---|---|---|
| `austria_2026` | Austrian GP | `fn_redbullring` / `austria_f1_2025` |
| `britain_2026` | British GP | `ks_silverstone` / `silverstone_f1_2025` |
| `belgium_2026` | Belgian GP | `spa` / `layout_f1_2025` |
| `hungary_2026` | Hungarian GP | `fn_hungaroring` / `layout_f1_2025` |
| `netherlands_2026` | Dutch GP | `zandvoort2023` / `layout_f1_2025` |
| `australia_2026` | Australian GP | `fn_albertpark` / `layout_f1_2026` |
| `china_2026` | Chinese GP | `shanghai_v2_25` / `layout_f1_2026` |
| `japan_2026` | Japanese GP | `rt_suzuka` / `layout_f1_2026` |
| `miami_2026` | Miami GP | `miami_f1` / `layout_f1_2025` |
| `italy_2026` | Italian GP | `monza` / `monza_f1_2025` |
| `madrid_2026` | Spanish GP (Madrid) | `fn_aragon` / `gp` — **stand-in: no Madring track in AC**, run at MotorLand Aragón |
| `azerbaijan_2026` | Azerbaijan GP | `baku_2022` / `layout_f1_2025` |
| `singapore_2026` | Singapore GP | `singapore_2020` / `layout_f1_2025` |
| `usa_2026` | United States GP | `cota_2022` / `layout_f1_2025` |
| `mexico_2026` | Mexico City GP | `acu_mexico_2021` / `layout_f1_2025` |
| `brazil_2026` | São Paulo GP | `vhe_interlagos` / `layout_f1_2025` |
| `lasvegas_2026` | Las Vegas GP | `lasvegas23` / `layout_f1_2025` |
| `qatar_2026` | Qatar GP | `fn_losail` / `layout_f1_2025` |
| `abudhabi_2026` | Abu Dhabi GP | `chq_abu_dhabi_2024` / `layout_f1_2025` |

Each event = `hotlap_<slug>_2026` + `race_<slug>_2026` (tiles), `cfg/hotlap_<slug>_2026.ini` + `cfg/race_<slug>_2026.ini` (presets), `launch_hotlap_<slug>_2026.cmd` + `launch_race_<slug>_2026.cmd` (launchers).

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
