# SimRacingPitStop

A one-click challenge dashboard for [Assetto Corsa](https://www.assettocorsa.it/) that turns 26 hand-built scenarios — 24h Nürburgring SP9 PRO grids, F1 hot-lap pole chases, Schumacher's iconic moments, the Senna MP4/8 — into a single browser tab.

```
+---------------------------+        +-------------+        +----------------+
|  localhost:8765           |   -->  |  launcher   |   -->  |  acs.exe       |
|  pick scenario · LAUNCH   |        |  .cmd       |        |  (the game)    |
+---------------------------+        +-------------+        +----------------+
            ^                              |                        |
            |                              v                        v
            |                       +-------------+        +----------------+
            |                       | Crew Chief  |        |  race_out.json |
            |                       | auto-press  |        |  per session   |
            |                       | Start (UIA) |        +-------+--------+
            |                                                      |
            |                       +----------------------+       |
            +------------------- < -|  results aggregator  | < ----+
              "Last result · P2/2"  +----------------------+
              shows up on the card     match by car+track+
              automatically            session.type+field
```

Public repo: **<https://github.com/pablosuzarte81/simracingpitstop>**

---

## The problem this solves

Sim racing in Assetto Corsa with mods is **logistically expensive**. Every realistic scenario needs a chain of correct things:

- a specific **car mod** (RSS, VRC, ASR, URD, Kunos), often a specific **livery**,
- a specific **track layout** (`spa/layout_f1_2025` works, `spa/layout_f1_2020` has no AI race line and silently breaks every grid),
- a multi-line `race.ini` with the right **CARS=N**, per-`CAR_n` driver/skin/team metadata, the right **SESSION_0 TYPE** (3=race, 4=hotlap), the right **SPAWN_SET**,
- a saved **car setup** for that car/track combination,
- **Crew Chief** running and pointed at the right game profile, with the **Start Crew Chief** button actually pressed (not just open and silent),
- and after the race, a way to **see what happened** — best lap, sectors, finish position vs. the AI grid — without parsing AC's binary replay or its overwritten-every-session `race_out.json`.

The default workflow falls apart almost immediately:

1. Content Manager rewrites `cfg/race.ini` on every Drive launch, blowing away your hand-tuned 16-car SP9 PRO grid the moment you click "GO".
2. Crew Chief opens but stays silent until you alt-tab and click Start; it stays running between sessions and gets buggy until you kill it.
3. Half the mod tracks ship without `fast_lane.ai` for a given layout, so AI cars sit on the grid forever and you race alone without knowing why.
4. There's no central record of "what did I drive last, what did I set, what did I beat".

You end up reinstalling the same `.ini` files over and over, juggling `restore_race_ini.cmd` scripts, and never quite trusting the launcher.

## What this is

A single repo that turns each scenario into a tile with a LAUNCH button, a card image, real reference lap times, and an auto-updated "Last session / Last result" line — backed by a launcher chain that fixes every one of the pain points above.

```
LAUNCH click  ->  back up race.ini             (race.ini.bak)
              ->  install cfg/<preset>.ini     (full grid, real liveries)
              ->  start CrewChiefV4.exe        (if not running)
              ->  UI-Automation real-mouse-click on the "Start Crew Chief"
                  button (it has no InvokePattern; SetCursorPos+mouse_event
                  is the only thing that actually presses it)
              ->  start "" /D ACINSTALL acs.exe
              ->  spawn wait_and_close_cc.ps1 watcher (background)
                  --> when AC exits: kill CrewChiefV4 (so the next launch
                      starts fresh), snapshot race_out.json, run
                      update_results.py, dashboard auto-shows the result
```

Every tile follows the same template. The dashboard at `http://localhost:8765` reflects state in real time (auto-reload on code change). The site stays out of your way while you drive.

## The catalog (26 tiles, 6 series)

| Series | Tiles | What it is |
|---|---|---|
| NLS · NÜRBURGRING | 4 | Mini 24h Nürburgring race + pole-chase hotlap + Verstappen-vs-Haase 1v1 (and the inverted Haase-vs-Verstappen) on the actual SP9 PRO field. |
| FORMULA 1 · 2026 | 4 | Canadian GP race with the real 2026 F1 grid (RSS Alpine + VRC Pro variants), plus solo Montreal hotlaps chasing Russell's `1:10.899` pole. |
| FORMULA 1 · 2008 | 1 | Hamilton's Interlagos title-decider, McLaren MP4-23 vs the period field. |
| SCHUMACHER · ICONIC RACES | 9 | Spa 1991 debut (Jordan 191 #32) · Monza Tifosi (F2001 #3) · Imola 7-time (F2001 #1) · Suzuka 2001 title clinch · Montreal F2004 · Benetton-vs-Ferrari '93 duel · Imola teammate duel · 1993 6-car cross-team grid race · Monza F2001 4-car sprint. |
| SENNA · TRIBUTE | 7 | All in the McLaren MP4/8 (1993). Donington "Lap of God" hotlap, Suzuka/Monaco '88 hotlaps, Estoril '85, Senna-vs-Prost duels, Senna-vs-Schumi at Donington 1993. |
| SUPER GT · GT500 | 1 | Verstappen-Miyake re-creation at Fuji in the wet (Nissan Z NISMO GT500). |

Full per-tile inventory with car/track/grid/laps in [`CHALLENGES.md`](CHALLENGES.md).

## How the launch chain actually works

There are five .ps1/.cmd files in [`launcher/`](launcher/) that compose every tile's launch:

| File | Role |
|---|---|
| [`launcher_dashboard.py`](launcher/launcher_dashboard.py) | Python HTTP server. Holds `CONFIGS` (every tile + metadata) and `SERIES` (section grouping). Renders cards, serves `/launch?id=<tile_id>` POST endpoints. |
| `launch_<tile>.cmd` (project root) | Per-tile launcher. Backs up `race.ini`, installs the preset, calls `start_crew_chief.cmd`, runs `acs.exe`, spawns the AC-exit watcher. |
| [`launcher/start_crew_chief.cmd`](launcher/start_crew_chief.cmd) | Synchronous Crew Chief launcher. Skips if CC is already running, otherwise starts it and runs the clicker. |
| [`launcher/click_cc_start.ps1`](launcher/click_cc_start.ps1) | UI-Automation pane finder + real-mouse-click on "Start Crew Chief". The button has no `InvokePattern`, so the only thing that works is `SetCursorPos` + `mouse_event(LEFTDOWN/LEFTUP)` at the pane's center. |
| [`launcher/wait_and_close_cc.ps1`](launcher/wait_and_close_cc.ps1) | Background watcher. Waits for `acs.exe` to exit, kills `CrewChiefV4.exe`, snapshots `race_out.json`, runs the results updater. |
| [`launcher/update_results.py`](launcher/update_results.py) | Snapshot → tile matcher. Disambiguates HOTLAP vs DUEL vs RACE by `session.type` (3=race, 4=hotlap) and `field` size, writes per-tile + index files. |

The whole flow is documented end-to-end in [`ARCHITECTURE.md`](ARCHITECTURE.md), including the data-flow diagram and recovery commands.

## Auto-results pipeline

After every session, the right card on the dashboard updates itself. No manual logging.

```
out/race_out.json          (AC writes this every session)
        |
        v   (after AC exits, wait_and_close_cc.ps1 copies it)
dashboard/results/snapshots/<yyyyMMdd-HHmmss>.json
        |
        v   (update_results.py reads every snapshot)
dashboard/results/by_tile/<tile_id>.json   <-- most recent per tile
dashboard/results/index.json               <-- master map { id -> latest }
        |
        v   (dashboard reads on every render)
card-times block
   "Your PB         1:18.810"   <-- from personalbest.ini auto-pull
   "Last session    1:18.260   09 MAY"   <-- HOTLAP variant
   "Last result     P2/2  1:48.260  09 MAY"   <-- DUEL/RACE variant
   "Senna pole      1:41.853"
```

The matcher picks the right tile when multiple share car + track:

| Snapshot signal | Resolves to |
|---|---|
| `session.type == 4` | HOTLAP tile |
| `session.type == 3`, `field == 2` | DUEL tile (fallback to RACE) |
| `session.type == 3`, `field > 2` | RACE tile (fallback to DUEL) |
| `ac_car_skin` matches `players[0].skin` | tiebreaker among the above |

So the same `asr_1993_mclaren_mp4-8` at `rt_suzuka/suzukagp` cleanly splits into two tiles: the HOTLAP card (`senna_suzuka_1988`) and the DUEL card (`senna_vs_prost_suzuka_1988`).

## Quick start

Prerequisites:

- Windows 11 + Steam + Assetto Corsa installed at `D:\SteamLibrary\steamapps\common\assettocorsa` (path can be edited in any `launch_*.cmd`)
- WSL2 with Python 3 (the dashboard server runs in WSL, browser hits via WSL→Windows port forward)
- Optional but recommended: [Crew Chief V4](https://thecrewchief.org/) at `C:\Program Files (x86)\Britton IT Ltd\CrewChiefV4\`

```bash
# clone into the AC user-data folder (matches the existing ACDOC paths)
git clone https://github.com/pablosuzarte81/simracingpitstop.git "/mnt/c/Users/pablo/Documents/Assetto Corsa"

# start the dashboard
cd "/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher"
python3 launcher_dashboard.py
```

Open `http://localhost:8765` in any browser. Click LAUNCH on a tile. The launcher does the rest.

Two desktop shortcuts also ship with the project:

- `SimRacingPitStop.lnk` — opens a WSL terminal in `~` with Claude Code (for editing the catalog).
- `SimRacingPitStop Dashboard.lnk` — opens the localhost dashboard in your default browser.

## Anti-patterns (things that bit me, baked into the docs)

The hard-won knowledge lives in [`ARCHITECTURE.md`](ARCHITECTURE.md) and the project-memory note at `~/.claude/projects/-home-pablosu/memory/srps_launch_chain.md`. The main traps:

1. **`launcher/scaffold_new_presets.py`** generates bare templates that strip the Crew Chief chain and rewrite `.ini` files to `CARS=1`. Re-run `for f in launch_*.cmd; do grep -c start_crew_chief "$f"; done` after it ever fires; should be `1` for every file.
2. **Switching `CONFIG_TRACK` blindly**. Some Spa layouts (`layout_f1_2020`, `layout_24h_2024`) have no `fast_lane.ai`; AI cars stay parked. Always pick layouts with valid AI files. Map of working layouts is in `ARCHITECTURE.md`.
3. **Repointing `PRESET=`** in a launcher to a stripped `<id>.ini` instead of the proper `cfg/race_<id>.ini`. The shortened-name presets the scaffold writes are 1-car solo configs without skin/team metadata; the full-grid versions live at `cfg/race_*.ini`, `cfg/duel_*.ini`, `cfg/hotlap_*.ini`.
4. **Using emojis or AC's `:start_grid` ID across mod tracks**. Spawn-points across mods aren't always portable. When in doubt, copy a working tile's `[SESSION_0]` block.

## Project layout

```
Assetto Corsa/
├── launch_*.cmd                 # per-tile launchers (27 of them)
├── archive_telemetry.cmd        # post-session telemetry archive utility
├── restore_race_ini.cmd         # roll back race.ini if a launch errored
├── cfg/                         # race.ini presets
│   ├── race_<id>.ini            #   multi-car grids (CARS≥2)
│   ├── hotlap_<id>.ini          #   solo hotlaps (TYPE=4, ghost on)
│   └── duel_<id>.ini            #   1v1 (CARS=2, TYPE=3, RACE_LAPS=1)
├── setups/                      # per-car-track .ini setups
├── launcher/
│   ├── launcher_dashboard.py    # the HTTP server + CONFIGS + SERIES
│   ├── start_crew_chief.cmd     # CC auto-start
│   ├── click_cc_start.ps1       # UIA real-mouse-click on Start
│   ├── wait_and_close_cc.ps1    # AC-exit watcher + result snapshot
│   ├── update_results.py        # snapshot → tile match → index.json
│   └── images/                  # tile images (skin previews, race shots)
├── dashboard/
│   └── results/
│       ├── snapshots/           # raw race_out.json snapshots (history)
│       ├── by_tile/<id>.json    # latest per tile
│       └── index.json           # master index (read by render_card)
├── experiences/                 # per-tile sub-folder catalog
│   └── 0N_<id>/                 #   README.md + image.jpg + Launch.lnk
├── personalbest.ini             # AC's per-(car,track) PB store
├── CHALLENGES.md                # 26-tile catalog inventory
├── ARCHITECTURE.md              # data-flow diagram + match logic
└── README.md                    # this file
```

## Stack

| Layer | Tech |
|---|---|
| Sim | Assetto Corsa + CSP 0.2.11 + Pure LCS weather |
| Modded cars | RSS GTM (Mercer V8 / Aero V10), VRC Formula Alpha 2025 (Pro), ASR 1993 McLaren MP4/8, VRC 1991 Jordan 191, VRC 1988 McLaren MP4/4, ferrari_f2001, ks_ferrari_f2004, f1_1993_benetton/ferrari/jordan, URD JT5 GT500 |
| Tracks | Kunos `ks_nordschleife/endurance_cup`, Pyyer `nordschleife_24hours_2024`, modern Spa/Monza/Imola/Suzuka, `montreal/montreal_f1_2025`, `doningtonpark2018/gp`, `fuji/fuji_2017` |
| Dashboard | Python 3 stdlib HTTP server, vanilla CSS + Big Shoulders Display / Saira Condensed / JetBrains Mono |
| Launchers | Windows `cmd.exe` batch + PowerShell + UIAutomationClient |
| Crew Chief | CrewChief V4.19.2.48 + Win32 mouse_event for the Start press |
| Bridge | WSL2 (the dashboard runs Linux-side, talks to Windows via `powershell.exe Start-Process` and `wsl.exe -e bash -lc "python3 ..."`) |
| Memory | `personalbest.ini` (AC), CMRT-Essential-HUD `.lap` files, `aim/telemetry_dump.act` |

## Hardware this is built for

- Wheel: MOZA R9 base (9 Nm direct drive), MOZA CRP load-cell pedals
- Display: single 4K @ 119 Hz, FOV 37° (calibrated, lives globally in `cfg/camera_onboard.ini`)
- Crew Chief output: LG TV via NVIDIA HDMI, mic = PRO X Wireless headset

## Acknowledgments

Modders whose work makes this catalog possible:

- **RSS Modding Team** — RSS GTM Mercer V8 (Mercedes-AMG GT3 Evo), RSS GTM Aero V10 (Audi R8 GT3 Evo II), RSS Formula Hybrid 2025 Alpine, RSS GTM Hyperion / Lanzo / Protech / Akuro / Lux / Furiano (the entire SP9 PRO field)
- **VRC Modding Team** — VRC Formula Alpha 2025 (Pro), VRC 1991 Jordan 191, VRC 1988 McLaren MP4-4
- **ASR** — ASR 1993 McLaren MP4/8 (the Senna car)
- **Pyyer** — `nordschleife_24hours_2024` Nürburgring 24h layout extension
- **URD** — URD JT5 Shiro Z GT500
- **Kunos Simulazioni** — Assetto Corsa, Ferrari F2001, Ferrari F2004, ks_silverstone, ks_monza, ks_nordschleife, etc.
- **Crew Chief team** (Britton IT Ltd) — for the spotter we automate-start.

Driver/team data and reference lap times are from real-world race results (NLS 2 2026, 2025 Canadian GP, 2024 24h Nürburgring qualifiers, etc.) where applicable.

## License

Source code in this repo: MIT, do whatever. Mod content (cars, tracks, skins) belongs to its respective authors and is **not** redistributed here — the launchers reference Steam-installed content paths.

## Status

Active. Built around the 14–17 May 2026 24h Nürburgring race week. Real driver: **Pablo Suzarte**. Sim driver of record: Max Verstappen, Mercedes-AMG Team Verstappen Racing #3.
