#!/usr/bin/env python3
"""Verify Super GT Fuji Chase mod install and patch the preset.

Scans Assetto Corsa content/cars and content/tracks for the installed
Nissan Z GT500 and Fuji Speedway folders, then rewrites the placeholders
in cfg/hotlap_super_gt_fuji_chase.ini and inserts the matching combo key
into apps/python/verstappen_delta/combo_targets.json.

Idempotent — safe to re-run after every install attempt.

Run from WSL or any Python 3 host that can see /mnt/c and /mnt/d.
"""

import json
import re
import sys
from pathlib import Path

AC_INSTALL = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa")
AC_DOC = Path("/mnt/c/Users/pablo/Documents/Assetto Corsa")
PRESET = AC_DOC / "cfg" / "hotlap_super_gt_fuji_chase.ini"
COMBO_TARGETS = AC_INSTALL / "apps" / "python" / "verstappen_delta" / "combo_targets.json"

CAR_HINTS = ("urd_jt5_shiro", "jt5_shiro", "nissan_z", "z_gt500", "z_nismo", "rz34", "z_super_gt")
TRACK_HINTS = ("fuji",)


def _scan_cars():
    cars_dir = AC_INSTALL / "content" / "cars"
    if not cars_dir.exists():
        return []
    found = []
    for d in sorted(cars_dir.iterdir()):
        if not d.is_dir():
            continue
        name = d.name.lower()
        ui = d / "ui" / "ui_car.json"
        ui_name = ""
        ui_tags = []
        if ui.exists():
            try:
                ui_data = json.loads(ui.read_text(encoding="utf-8", errors="ignore"))
                ui_name = (ui_data.get("name") or "").lower()
                ui_tags = [t.lower() for t in (ui_data.get("tags") or [])]
            except Exception:
                pass
        # Require strong signal in either the folder name OR the ui name field.
        # GT-R / GT3 cars sometimes drop "GT500" in their description for flavor;
        # don't count those.
        score = 0
        if "urd_jt5_shiro" in name: score += 8
        if "jt5_shiro" in name: score += 6
        if "gt500" in name: score += 5
        if "rz34" in name: score += 3
        if "z_super_gt" in name or "z_supergt" in name: score += 4
        if any(h in name for h in CAR_HINTS): score += 1
        if "gt500" in ui_name: score += 4
        if "rz34" in ui_name: score += 3
        if "super gt" in ui_name and ("nissan z" in ui_name or "rz34" in ui_name): score += 4
        if "shiro" in ui_name and "z" in ui_name: score += 4
        if "gt500" in ui_tags: score += 3
        if score >= 4:
            found.append((score, d.name))
    found.sort(reverse=True)
    return [name for _, name in found]


def _scan_tracks():
    tracks_dir = AC_INSTALL / "content" / "tracks"
    if not tracks_dir.exists():
        return []
    found = []
    for d in sorted(tracks_dir.iterdir()):
        if not d.is_dir():
            continue
        name = d.name.lower()
        if any(h in name for h in TRACK_HINTS):
            layouts = []
            ui = d / "ui"
            if ui.exists():
                if (ui / "ui_track.json").exists():
                    layouts.append("")
                for sub in ui.iterdir():
                    if sub.is_dir() and (sub / "ui_track.json").exists():
                        layouts.append(sub.name)
            if not layouts:
                layouts = [""]
            found.append((d.name, layouts))
    return found


def _patch_preset(track, layout, car):
    if not PRESET.exists():
        return False, "preset missing: {0}".format(PRESET)
    text = PRESET.read_text(encoding="utf-8")
    new = re.sub(r"^TRACK=.*$", "TRACK={0}".format(track), text, count=1, flags=re.M)
    new = re.sub(r"^CONFIG_TRACK=.*$", "CONFIG_TRACK={0}".format(layout), new, count=1, flags=re.M)
    new = re.sub(r"^MODEL=.*$", "MODEL={0}".format(car), new, count=1, flags=re.M)
    if new == text:
        return False, "no placeholders matched (already patched?)"
    PRESET.write_text(new, encoding="utf-8")
    return True, "patched preset: TRACK={0} CONFIG_TRACK={1} MODEL={2}".format(track, layout, car)


def _patch_combo_targets(combo_key):
    if not COMBO_TARGETS.exists():
        return False, "combo_targets.json missing: {0}".format(COMBO_TARGETS)
    try:
        data = json.loads(COMBO_TARGETS.read_text(encoding="utf-8"))
    except Exception as e:
        return False, "combo_targets.json parse error: {0}".format(e)
    entry = {
        "rival_label": "MIYAKE 1:44.075",
        "rival_ms": 104075,
        "target_label": "VERSTAPPEN 1:42.290",
        "target_ms": 102290,
    }
    data[combo_key] = entry
    COMBO_TARGETS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return True, "combo_targets.json now keyed for {0}".format(combo_key)


def main():
    print("Super GT Fuji Chase — install verifier")
    print("=" * 50)

    cars = _scan_cars()
    tracks = _scan_tracks()

    print("\n[1/3] Cars (sorted by likelihood):")
    if not cars:
        print("  - none found that look like a Nissan Z GT500 mod.")
    else:
        for c in cars:
            print("  + {0}".format(c))

    print("\n[2/3] Tracks:")
    if not tracks:
        print("  - none found matching 'fuji'.")
    else:
        for tname, layouts in tracks:
            print("  + {0}  layouts={1}".format(tname, layouts))

    if not cars or not tracks:
        print("\n=> incomplete. Install the mods then re-run.")
        return 1

    car = cars[0]
    track, layouts = tracks[0]
    layout = ""
    for cand in ("gp", "racing", "full", "Racing"):
        if cand in layouts:
            layout = cand
            break
    if not layout and layouts:
        # Pick the longest non-empty layout name (usually the GP / full layout)
        nonempty = [L for L in layouts if L]
        layout = max(nonempty, key=len) if nonempty else ""

    print("\n[3/3] Picking: car={0} track={1} layout={2}".format(car, track, layout or "(none)"))

    ok, msg = _patch_preset(track, layout, car)
    print("  preset: {0}{1}".format("OK " if ok else "?? ", msg))

    combo_key = "{0}__{1}".format(car, track) + (("__" + layout) if layout else "")
    ok2, msg2 = _patch_combo_targets(combo_key)
    print("  HUD:    {0}{1}".format("OK " if ok2 else "?? ", msg2))

    print("\nDone. You can now run launch_hotlap_super_gt_fuji_chase.cmd.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
