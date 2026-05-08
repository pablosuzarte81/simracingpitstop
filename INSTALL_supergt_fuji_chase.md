# Super GT Fuji Chase 2026 — install guide

Re-creating the March 2026 Red Bull promotional test:
**Max Verstappen vs Atsushi Miyake's 1:44.075 in a Nissan Z NISMO GT500 at a soaking-wet Fuji Speedway.** Verstappen's best on the day was **1:42.290** on his second flying lap.

This guide gets you from no mods to "press launch" in about 30 minutes.

## What you're installing

| # | Slot | Mod | Folder name | Cost |
|---|---|---|---|---|
| 1 | Track | **Fuji International Speedway 0.0.9 Update 1** — Tiago Lima | `fujispeedway_2017` | free |
| 2 | Car | **JT5 Shiro Z GT500** — URD | `urd_jt5_shiro_2022` | paid (~€8) |
| 3 | Skin pack | **2023 Nissan Z Super GT GT500 Pack** (for URD Shiro Z) | drops into URD car's `skins/` | free |
| 4 | Sound | car ships with URD's own sound; OverTake "Nissan Z GT500 Sound Mod" can be applied on top | replaces sound files | free |

The earlier free TheNuvolari mod (`z_gt500_2022`) is unmaintained and only distributed via Discord/Patreon links from his YouTube. URD's JT5 Shiro Z is the canonical paid version, well documented, has the right physics, and matches the OverTake skin pack folder layout. Pick the URD path.

## Download links

- Fuji track (free): https://www.overtake.gg/downloads/fuji-international-speedway.2554/
- **URD JT5 Shiro Z (paid):** https://shop.unitedracingdesign.com/p/ac-jt5-shiro-z-gt500/
- 2023 GT500 Skin Pack for URD (free, includes Kondo Racing #56 = Miyake's car): https://www.overtake.gg/downloads/2023-nissan-z-super-gt-gt500-pack-urd-shiro-z.68182/
- Sound mod (optional, free): https://www.overtake.gg/downloads/nissan-z-gt500-sound-mod.68222/

## Install order

Use **Content Manager → Install mod** for each `.7z` / `.zip` (drag and drop into CM works too). CM places folders correctly and avoids manual copy mistakes.

1. **Fuji track first** — install the base Tiago Lima mod into `content/tracks/`.
2. **Fuji texture update** on top — installs into the same track folder.
3. **Nissan Z GT500 car** into `content/cars/`.
4. **Sound mod** on top of the car (replaces audio files inside the car folder).

If CM complains about a missing dependency for the texture update, install the base Fuji mod first, then re-run the texture installer.

## After install — patch the preset

Run **once** from a Windows command prompt:

    verify_install_supergt.cmd

This will:
- Scan `content/cars/` and `content/tracks/` for the installed mods
- Pick the strongest match for each
- Rewrite `cfg/hotlap_super_gt_fuji_chase.ini` with the actual folder names
- Add the resolved combo key to `apps/python/verstappen_delta/combo_targets.json`

It's idempotent — safe to re-run any time.

If something doesn't match (e.g. you have multiple Fuji mods), open the script's output and edit the preset by hand: the placeholder lines are `TRACK=__FUJI_TRACK__` and `MODEL=__Z_GT500_CAR__`.

## Launch

    launch_hotlap_super_gt_fuji_chase.cmd

What to expect on track:
- Hotlap session, single car, no AI
- Pure LCS heavy rain, 14 °C ambient / 16 °C road, JST sun position
- Verstappen Delta HUD shows three live deltas:
  - **vs PB** — your personal best on this combo (auto-saved per combo)
  - **vs MIYAKE 1:44.075** — the benchmark to beat
  - **vs VERSTAPPEN 1:42.290** — Max's actual lap from the test, your stretch goal
- Restore your old race.ini afterwards with `restore_race_ini.cmd`

## Optional — Verstappen Red Bull livery

The real test ran a one-off Red Bull livery on the Z GT500. No public AC skin exists yet (the test was March 2026, only ~6 weeks ago). The preset references skin name `M17_Verstappen_RedBull_Test`. If absent at launch, AC falls back to the default NISMO skin without complaint.

To paint one: copy `content/cars/<nissan_z_gt500_folder>/skins/<default>/` into a new folder `M17_Verstappen_RedBull_Test/`, then edit `livery.png` (or unpack the mod's PSD template if shipped) using Red Bull blue + the bull motifs. Reference photos are easy to find under "Verstappen Fuji GT500 test".

## Telemetry archive note

`archive_telemetry.cmd` works as-is for capturing the AIM dump, CMRT laps, personal best, and `race_out.json`. The replay-matcher and ghost-matcher in that script are still hardcoded for Mercer + Nordschleife — Fuji session replays/ghosts won't auto-copy. The HUD ghost JSON for this combo is saved alongside `verstappen_delta.py` as `reference_lap_<combo>.json`, copy it manually if you want it in the archive folder.

## Sanity check before you launch

- [ ] CM Drive page shows car = Nissan Z GT500, track = Fuji
- [ ] CSP weather FX is on (RainFX + WaterFX), Pure LCS active
- [ ] Verstappen Delta HUD column 2 says "vs MIYAKE 1:44.075"
- [ ] Verstappen Delta HUD column 3 says "vs VERSTAPPEN 1:42.290"
- [ ] Standing water visible at Turn 1 on the formation lap

If column 2/3 still say "vs RIVAL" / "vs Verstappen 7:51.751" — combo key didn't match. Re-run `verify_install_supergt.cmd` after AC has loaded the session at least once (it logs the actual combo key to `Documents/Assetto Corsa/logs/log.txt`).
