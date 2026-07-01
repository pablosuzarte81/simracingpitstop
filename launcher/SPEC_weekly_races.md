# Spec — Weekly Races ("This Week") home page

> Brainstormed & approved 2026-06-09. Source of truth for the build.
> Inspired by acevo.gg/SimGrid daily racing (see `RESEARCH_acevo_simgrid.md`),
> localised to Pablo's actual AC library (316 cars / 85 tracks).

## Concept
A rotating home page showing **3 races per week**:
1. **F1** — real 2025 grid, real GP calendar.
2. **GT3** — mixed-brand field, one class.
3. **Wildcard** — theme rotates: Hypercar Shootout → Group C/Le Mans → DTM/Touring → Vintage F1.

Each race is a **real race vs an AI grid**. Pablo's **best finish of the week is
kept** and he can re-run to improve it. Week resets automatically; the finished
week freezes into a **standalone recap** that joins a "Past weeks" history strip.
No cumulative career/level (decided: standalone weeks).

## Mechanics (all verified against the install)
- **Launch chain (existing):** a `.cmd` copies a preset `race_*.ini` → `cfg/race.ini`,
  fires Crew Chief, runs `acs.exe`, watches for exit. Reused as-is.
- **Mixed-brand grids:** `race.ini` `[CAR_N]` each carry their own `MODEL=` / `SKIN=` /
  `DRIVER_NAME=`. Verified in `race_nls_24h_2026.ini` (Mercer V8 vs Aero V10).
- **F1 field:** reuse the proven 19-car grid block from `race_belgium_2026.ini`
  (RSS Formula Hybrid 2025 + real-team skins, Pablo = CAR_0). NOT the raw
  `gp_2025_*` folders. Only TRACK/CONFIG_TRACK swap per week.
- **F1 tracks/layouts:** harvested from existing `race_*_2026.ini` (verified
  TRACK + CONFIG_TRACK pairs across the GP calendar).
- **GT3/Wildcard fields:** generated. Player + AI, each AI a different brand.
  Skins = first skin in `content/cars/<id>/skins/`. Layout resolved from disk:
  root `ui/ui_track.json` ⇒ `CONFIG_TRACK=""`, else a `ui/<layout>/ui_track.json`.
- **Results:** AC writes `out/race_out.json`; launcher snapshots to
  `dashboard/results/snapshots/<ts>.json` (`track`, `players[]`, `sessions[]`).
  Finishing position from race session (`type=3`) `raceResult` (car-index finishing
  order) → player is CAR_0 ⇒ `position = raceResult.index(0)+1`.
  **⚠ Assumption to validate on first real race:** recent snapshots are all
  hotlaps (`type=4`), so the exact `raceResult` shape is parsed defensively
  (fallbacks: bestLaps ordering, else P1).

## Generation (deterministic — this IS the auto-reset)
- Week id = ISO `(year, week)` from `date.isocalendar()`.
- `Random(year*100 + week)` seeds picks → same week = same 3 races; new week rotates
  with no cron/manual step.
- Wildcard theme = `weeks_since_epoch % 4` so all four themes cycle in order.
- Player car assigned deterministically per week (variety without a picker).
  Car picker = explicit follow-up, not v1.

## Scoring
- Per race, F1 points by finish: 25-18-15-12-10-8-6-4-2-1, +1 fastest lap.
- Weekly score = sum of 3 races (max ~78). Best result per race counts; re-runs only improve.

## Defaults (constants, tunable)
- AI strength 90. Race length: F1 5 laps, GT3 6, Wildcard 6. Grid: F1 19, GT3 12, Wildcard ~10.

## Files
- **New module** `launcher/weekly_races.py`: pools (data), layout/skin resolvers,
  deterministic generator, `race.ini` + `.cmd` writers, scoring, history & results parse.
- **Generated** `cfg/race_week_{f1,gt3,wild}.ini`, `launch_week_{f1,gt3,wild}.cmd`
  (overwritten on week change).
- **Archive** `dashboard/weekly/history.json`.
- **Integration** in `launcher_dashboard.py`: `render_weekly_page()`, route, nav item,
  `/` becomes "This Week" (old 81-tile grid → "Browse All" link), `/launch-weekly?slot=`.

## Placement
"This Week" is the new landing at `/`. Existing grid moves behind a **Browse All** link.

## Out of scope (v1)
Per-race car picker · adjustable AI per race · cumulative career/level · multiclass fields.
