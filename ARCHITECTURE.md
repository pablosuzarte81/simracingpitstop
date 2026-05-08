# SimRacingPitStop · Architecture

How the dashboard, launchers, and auto-results pipeline fit together.

```
                 ┌──────────────────┐
                 │  Browser tab     │
                 │  localhost:8765  │
                 └────────┬─────────┘
                          │ click LAUNCH
                          ▼
              ┌───────────────────────┐
              │  launcher_dashboard.py│ ── POST /launch?id=<tile_id>
              │  Python HTTP server   │
              └────────────┬──────────┘
                           │ powershell.exe Start-Process
                           ▼
                ┌────────────────────────┐
                │  launch_<tile>.cmd     │   1) backup race.ini
                │  (in project root)     │   2) copy preset → race.ini
                └────────────┬───────────┘   3) call start_crew_chief.cmd
                             │                4) start "" acs.exe
                             │                5) spawn wait_and_close_cc.ps1
       ┌─────────────────────┴────────────────────────┐
       ▼                                              ▼
┌───────────────────────┐                  ┌────────────────────────┐
│ start_crew_chief.cmd  │                  │  acs.exe (game)        │
│   launches CC         │                  │  loads race.ini        │
│   click_cc_start.ps1  │                  │  player drives         │
│     (UI Automation)   │                  │  writes race_out.json  │
│     real mouse click  │                  │  writes personalbest   │
│     on Start button   │                  │  exits                 │
└───────────────────────┘                  └────────────┬───────────┘
                                                        │
                                                        ▼
                                          ┌─────────────────────────┐
                                          │ wait_and_close_cc.ps1   │
                                          │  (background watcher)   │
                                          │  - Wait-Process acs     │
                                          │  - kill CrewChiefV4     │
                                          │  - copy race_out.json → │
                                          │    dashboard/results/   │
                                          │    snapshots/<ts>.json  │
                                          │  - run update_results.py│
                                          └────────────┬────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │ launcher/update_results │
                                          │ - reads all snapshots   │
                                          │ - matches each to a tile│
                                          │   by car + track +      │
                                          │   session.type + field  │
                                          │ - writes by_tile/<id>   │
                                          │ - writes index.json     │
                                          └─────────────────────────┘
                                                       │
                                                       ▼
                                          ┌─────────────────────────┐
                                          │ Next dashboard render   │
                                          │ pulls index.json + the  │
                                          │ personalbest.ini and    │
                                          │ shows "Last result" /   │
                                          │ "Last session" on each  │
                                          │ card.                   │
                                          └─────────────────────────┘
```

## Files in play

### Dashboard server
- **`launcher/launcher_dashboard.py`** — Python HTTP server. Holds the `CONFIGS` list (every tile + its metadata) and the `SERIES` list (section grouping). Renders cards via `render_card(cfg)` and `_render_times_block(cfg)`.
- **`launcher/build_static.py`** — exports a static HTML build to `launcher/vercel_build/` for Vercel hosting (currently broken-by-design due to mixed-content blocking; use localhost).

### Launchers (one `.cmd` per tile)
Each follows the template documented in `CHALLENGES.md`. Naming:
- `launch_<basename>.cmd` mirrors `cfg/<basename>.ini`
- Multi-car races: `cfg/race_<id>.ini` (CARS≥2)
- Solo hotlaps: `cfg/hotlap_<id>.ini` (CARS=1, TYPE=4, SPAWN_SET=HOTLAP_START)
- 1v1 duels: `cfg/duel_<id>.ini` (CARS=2, TYPE=3, RACE_LAPS=1)

### Crew Chief auto-start
- **`launcher/start_crew_chief.cmd`** — synchronously launches `CrewChiefV4.exe` if not running, then runs the clicker.
- **`launcher/click_cc_start.ps1`** — UI Automation: finds the "Start Crew Chief" pane element, falls back to a real `SetCursorPos + mouse_event` click at the pane center (the pane has no `InvokePattern`).

### AC-exit watcher + auto-results
- **`launcher/wait_and_close_cc.ps1`** — async watcher. Polls for `acs.exe`, waits for it to exit, then:
  1. Kills CrewChiefV4 (so next launch starts fresh)
  2. Copies `out/race_out.json` to `dashboard/results/snapshots/<yyyyMMdd-HHmmss>.json`
  3. Runs `update_results.py` via WSL python
- **`launcher/update_results.py`** — scans all snapshots, matches each to a tile in `CONFIGS`, writes per-tile + index files.

### Results storage
- **`dashboard/results/snapshots/`** — raw `race_out.json` snapshots (timestamped). Source of truth, never deleted.
- **`dashboard/results/by_tile/<tile_id>.json`** — most recent per tile.
- **`dashboard/results/index.json`** — flat map `{tile_id: {ts, tile, summary, snapshot_file}}`. Loaded by the dashboard on every render.

### Personal best
- **`personalbest.ini`** — AC writes this when the user sets a new PB. The dashboard's `_resolve_your_ms(bm)` reads it via `bm.you_section` (matching `<CAR_UPPER>@<TRACK_UPPER>-<CONFIG_UPPER>`) for hotlap tiles.

## Tile→snapshot matching logic

`update_results.py:match_tile()` resolves which dashboard tile a given race_out.json snapshot belongs to:

1. **Required match**: `ac_car_id == snapshot.players[0].car` AND `f"{ac_track_id}-{ac_track_layout}" == snapshot.track`
2. **Session type filter**:
   - `session.type == 4` → only `HOTLAP` tiles
   - `session.type == 3` and `field == 2` → prefer `DUEL`, fall back to `RACE`
   - `session.type == 3` and `field > 2` → prefer `RACE`, fall back to `DUEL`
3. **Tiebreaker**: `ac_car_skin == snapshot.players[0].skin` if multiple still match
4. **Final fallback**: first remaining candidate

This handles the common ambiguity case: same car + same track exists as both HOTLAP and DUEL tiles (e.g. `senna_suzuka_1988` HOTLAP and `senna_vs_prost_suzuka_1988` DUEL both use `asr_1993_mclaren_mp4-8` at `rt_suzuka/suzukagp`). The session type splits them.

## Data flow on a single launch

1. Browser POST `/launch?id=hotlap_canada_vrc`
2. Server `launch_cmd("hotlap_canada_vrc")` → spawns `launch_hotlap_canada_vrc.cmd`
3. .cmd installs `cfg/hotlap_canada_vrc.ini` → `cfg/race.ini`, calls `start_crew_chief.cmd` (synchronous: CC opens, click_cc_start.ps1 presses Start), then `start "" acs.exe` and spawns `wait_and_close_cc.ps1` (async)
4. Pablo drives session. AC writes `out/race_out.json` and updates `personalbest.ini` if PB
5. Pablo exits AC → `wait_and_close_cc.ps1` snapshots `race_out.json` to `dashboard/results/snapshots/<ts>.json`, then `wsl python update_results.py` rewrites `index.json`
6. Pablo refreshes dashboard → tile shows new "Last session" or "Last result" row alongside the existing Your PB / reference rows

## What survives across launches

- `dashboard/results/snapshots/` accumulates every session. Useful for future history graphs.
- `dashboard/results/by_tile/<id>.json` always holds the most recent for that tile.
- `personalbest.ini` accumulates a row per car+track combo (AC manages it).
- Replays land in `replay/temp/` (gitignored).

## What gets nuked each launch

- `cfg/race.ini` — overwritten by the preset install
- `cfg/race.ini.bak` — overwritten with the previous race.ini before install
- `out/race_out.json` — AC overwrites at session start

## Series list (sections in the dashboard)

Defined in `launcher_dashboard.py:SERIES`. Order = render order.

| id | label | tiles |
|---|---|---|
| `NLS` | NLS · NÜRBURGRING | 4 |
| `F1_2026` | FORMULA 1 · 2026 | 4 |
| `F1_2008` | FORMULA 1 · 2008 | 1 |
| `SCHUMACHER` | SCHUMACHER · ICONIC RACES | 9 |
| `SENNA TRIBUTE` | SENNA · TRIBUTE | 7 |
| `SUPERGT` | SUPER GT · GT500 | 1 |

Tiles with a `series` not in `SERIES` fall into a leftover "OTHER" bucket.

## Key project paths

| What | Where |
|---|---|
| Dashboard server | `launcher/launcher_dashboard.py` |
| Launchers | `launch_*.cmd` (project root) |
| Presets | `cfg/race_*.ini`, `cfg/hotlap_*.ini`, `cfg/duel_*.ini` |
| CC chain | `launcher/start_crew_chief.cmd`, `launcher/click_cc_start.ps1` |
| Post-AC watcher | `launcher/wait_and_close_cc.ps1` |
| Results updater | `launcher/update_results.py` |
| Result snapshots | `dashboard/results/snapshots/<yyyyMMdd-HHmmss>.json` |
| Latest per tile | `dashboard/results/by_tile/<tile_id>.json` |
| Master index | `dashboard/results/index.json` |
| AC personal bests | `personalbest.ini` (project root) |
| Tile experience folders | `experiences/01..09_<id>/` |
| Catalog doc | `CHALLENGES.md` |
| This doc | `ARCHITECTURE.md` |

## Recovery

```bash
cd "/mnt/c/Users/pablo/Documents/Assetto Corsa"

# See what's been touched
git status -s

# Compare against last good save
git diff HEAD -- launcher/ cfg/

# Roll back a single tile
git checkout HEAD -- cfg/race_canada_2026.ini

# Re-snapshot every existing race_out.json into the pipeline
cp out/race_out.json "dashboard/results/snapshots/$(date +%Y%m%d-%H%M%S).json"
python3 launcher/update_results.py
```
