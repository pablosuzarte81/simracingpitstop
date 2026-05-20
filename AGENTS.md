# Agents — Project Rules

Rules for any AI agent (Claude, Codex, or other) working on this project. Read this file before touching anything.

## The Verify-First Rule (hard requirement)

**Before claiming any of the following exists, verify it on disk or in the docs:**

- An AC `race.ini` / preset key
- A CSP feature, key, or behaviour
- A Content Manager convention
- A mod's car ID, track ID, layout, skin name, or behaviour
- A `.cmd` launch chain step
- Any file path in this project

**Acceptable verification:**

```bash
# 1. Grep the AC install for the actual key
grep -rE "<key>" /mnt/f/SteamLibrary/steamapps/common/assettocorsa/extension/

# 2. Read the file
Read /mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/launcher_dashboard.py

# 3. Read CHALLENGES.md, ARCHITECTURE.md, README.md
Read /mnt/c/Users/pablo/Documents/Assetto Corsa/CHALLENGES.md

# 4. Check the running dashboard
curl -s http://localhost:8765/
```

**Unacceptable:**

- "This is the standard CSP pattern"
- "Content Manager writes this"
- "AC supports this via [KEY]" (without grepping CSP/acs.exe for [KEY])
- Any "in my experience" / "typically" / "should be" claim

## The Audit Phrase

If Pablo asks **"where did you verify that?"** the only acceptable answer is a file path + grep result + line number. Never "from the docs" without a URL, never "this is standard."

If you can't produce that, you were guessing. Retract and verify before continuing.

## Why This File Exists

The Audi 90 GTO Nordschleife challenge (`dave_cam_audi_90_nordschleife`) was nearly broken by a confident fabrication: `[EXTRA_RULES] RACE_FORMATION_LAP=1` was inserted into the preset claiming it would deliver a rolling start. CSP has no such key — grepped after the fact. AC + CSP has no rolling-start feature at all.

The cost of inventing config keys for this project is wasted time and broken races. The cost of "let me grep first" is 30 seconds. Always pay the 30 seconds.

## Project-Specific Anti-Patterns (from CHALLENGES.md)

Pablo has already documented these in `CHALLENGES.md`. Re-stated here so they're impossible to miss:

- **Don't run `launcher/scaffold_new_presets.py` blind** — it overwrites launchers with bare templates (no Crew Chief chain) and rewrites `.ini` files to CARS=1 stripped configs.
- **Don't repoint launcher `PRESET=` to a different filename** without confirming the target `.ini` has a real grid.
- **Don't switch a track `CONFIG_TRACK=` without verifying `fast_lane.ai` + `pit_lane.ai` exist** for that layout in `/mnt/f/SteamLibrary/steamapps/common/assettocorsa/content/tracks/<id>/<layout>/ai/`.
- **Don't add config keys you can't grep** in the CSP install or `acs.exe` strings.

## Adding A New Challenge

The full process (verified by working through it):

1. **Pick the car** — confirm the car ID exists: `ls /mnt/f/SteamLibrary/steamapps/common/assettocorsa/content/cars/ | grep <car>`
2. **Pick the track + layout** — confirm AI files: `ls /mnt/f/SteamLibrary/steamapps/common/assettocorsa/content/tracks/<id>/<layout>/ai/` must contain `fast_lane.ai` + `pit_lane.ai`
3. **Add entry to `CONFIGS`** in `launcher/launcher_dashboard.py` — copy the shape of an existing race/hotlap/duel entry
4. **Add the series to `SERIES`** if new — series ID must match exactly between SERIES and CONFIGS entry
5. **Write `cfg/race_<id>.ini`** (multi-car), `cfg/hotlap_<id>.ini` (solo), or `cfg/duel_<id>.ini` (2-car) — copy from a working preset of the same type, do NOT scaffold
6. **Write `launch_<id>.cmd`** — copy from a working `.cmd`, must include the full Crew Chief chain: backup → install → `start_crew_chief.cmd` → `acs.exe` direct → `wait_and_close_cc.ps1`
7. **Add card image** at `launcher/images/<id>.jpg` — copy from the car's skin `preview.jpg`
8. **Update `CHALLENGES.md`** — add the row to the catalog table, bump the total count
9. **Verify the dashboard renders** — `curl -s http://localhost:8765/ | grep <id>` should return content

## Definite Facts (verified 2026-05-13, do not invent past this)

- AC + CSP has **no rolling-start mechanism**. Standing starts only. Verified by `grep -riE "rolling|formation_lap|race.start" /mnt/f/SteamLibrary/steamapps/common/assettocorsa/extension/` → zero matches.
- AC requires the player to be `CAR_0`. Non-pole start needs a qualifying session, as noted in `cfg/canada_2026.ini`.
- Layouts confirmed with AI files for `ks_nordschleife`: `endurance_cup`, `nordschleife`, `nordschleife_24hours_2024`.
- Python dashboard hot-reloads `CONFIGS` on each request — no server restart needed after editing `launcher_dashboard.py`.

## When You Don't Know

The correct answer is: **"I don't know — to confirm this I would need to grep X / read Y / fetch Z."** Never invent.
