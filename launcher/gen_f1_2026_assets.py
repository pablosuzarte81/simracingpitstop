#!/usr/bin/env python3
"""Generate cfg .ini + launch .cmd + card art for the 14 F1 2026 calendar events.

Uses the verified Barcelona presets as templates (so the 19-car grid and the
Crew Chief launch chain are identical everywhere), swapping only the track id,
layout, geotag and labels. Card art = the AC track's own preview.png (circuit
photo) and outline.png (track map) -> launcher/images/. No car photos.

Idempotent: safe to re-run. Run from anywhere:
    python3 "launcher/gen_f1_2026_assets.py"
"""
import os, shutil, sys

AC_DOC = os.path.expanduser("~/Documents/Assetto Corsa")
if not os.path.isdir(AC_DOC):
    AC_DOC = "/mnt/c/Users/pablo/Documents/Assetto Corsa"
TRACKS = "/mnt/f/SteamLibrary/steamapps/common/assettocorsa/content/tracks"
CFG = os.path.join(AC_DOC, "cfg")
IMAGES = os.path.join(AC_DOC, "launcher", "images")

# slug, GP title, short LOC, track_id, layout, lat, lng
SPECS = [
    ("austria",     "AUSTRIAN GP 2026",      "RED BULL RING", "fn_redbullring",     "austria_f1_2026",     "47.2197", "14.7647"),
    ("britain",     "BRITISH GP 2026",       "SILVERSTONE",   "ks_silverstone",     "silverstone_f1_2025", "52.0733", "-1.0147"),
    ("belgium",     "BELGIAN GP 2026",       "SPA",           "spa",                "layout_f1_2025",      "50.4372", "5.9714"),
    ("hungary",     "HUNGARIAN GP 2026",     "HUNGARORING",   "fn_hungaroring",     "layout_f1_2025",      "47.5789", "19.2486"),
    ("netherlands", "DUTCH GP 2026",         "ZANDVOORT",     "zandvoort2023",      "layout_f1_2025",      "52.3888", "4.5409"),
    ("italy",       "ITALIAN GP 2026",       "MONZA",         "monza",              "monza_f1_2025",       "45.6156", "9.2811"),
    ("madrid",      "MADRID GP 2026",        "MOTORLAND ARAGON","fn_aragon",         "gp",                  "41.0786", "-0.2042"),
    ("azerbaijan",  "AZERBAIJAN GP 2026",    "BAKU",          "baku_2022",          "layout_f1_2025",      "40.3725", "49.8533"),
    ("singapore",   "SINGAPORE GP 2026",     "MARINA BAY",    "singapore_2020",     "layout_f1_2025",      "1.2914",  "103.8640"),
    ("usa",         "UNITED STATES GP 2026", "COTA",          "cota_2022",          "layout_f1_2025",      "30.1328", "-97.6411"),
    ("mexico",      "MEXICO CITY GP 2026",   "MEXICO CITY",   "acu_mexico_2021",    "layout_f1_2025",      "19.4042", "-99.0907"),
    ("brazil",      "SAO PAULO GP 2026",     "INTERLAGOS",    "vhe_interlagos",     "layout_f1_2025",      "-23.7036","-46.6997"),
    ("lasvegas",    "LAS VEGAS GP 2026",     "LAS VEGAS",     "lasvegas23",         "layout_f1_2025",      "36.1147", "-115.1728"),
    ("qatar",       "QATAR GP 2026",         "LOSAIL",        "fn_losail",          "layout_f1_2025",      "25.4900", "51.4542"),
    ("abudhabi",    "ABU DHABI GP 2026",     "YAS MARINA",    "chq_abu_dhabi_2024", "layout_f1_2025",      "24.4672", "54.6031"),
    ("australia",   "AUSTRALIAN GP 2026",    "ALBERT PARK",   "fn_albertpark",      "layout_f1_2026",      "-37.8497","144.9680"),
    ("china",       "CHINESE GP 2026",       "SHANGHAI",      "shanghai_v2_25",     "layout_f1_2026",      "31.3389", "121.2200"),
    ("japan",       "JAPANESE GP 2026",      "SUZUKA",        "rt_suzuka",          "layout_f1_2026",      "34.8431", "136.5410"),
    ("miami",       "MIAMI GP 2026",         "MIAMI",         "miami_f1",           "layout_f1_2025",      "25.9581", "-80.2389"),
]

# Barcelona templates (verified working, authored by hand earlier this session)
RACE_TPL   = os.path.join(CFG, "race_barcelona_2026.ini")
HOTLAP_TPL = os.path.join(CFG, "hotlap_barcelona_2026.ini")
RACE_CMD_TPL   = os.path.join(AC_DOC, "launch_race_barcelona_2026.cmd")
HOTLAP_CMD_TPL = os.path.join(AC_DOC, "launch_hotlap_barcelona_2026.cmd")

for p in (RACE_TPL, HOTLAP_TPL, RACE_CMD_TPL, HOTLAP_CMD_TPL):
    if not os.path.isfile(p):
        sys.exit(f"Template missing: {p}")

race_tpl   = open(RACE_TPL,   encoding="utf-8").read()
hotlap_tpl = open(HOTLAP_TPL, encoding="utf-8").read()
race_cmd   = open(RACE_CMD_TPL,   encoding="utf-8").read()
hotlap_cmd = open(HOTLAP_CMD_TPL, encoding="utf-8").read()

BCN_LAT, BCN_LNG = "41.5700", "2.2611"


def find_preview(tid, layout):
    for p in (f"{TRACKS}/{tid}/ui/{layout}/preview.png", f"{TRACKS}/{tid}/ui/preview.png"):
        if os.path.isfile(p):
            return p
    return None


def find_outline(tid, layout):
    for p in (f"{TRACKS}/{tid}/ui/{layout}/outline.png", f"{TRACKS}/{tid}/ui/outline.png"):
        if os.path.isfile(p):
            return p
    return None


def ini_swap(tpl, track_id, layout, lat, lng):
    out = tpl
    out = out.replace("TRACK=fn_barcelona", f"TRACK={track_id}")
    out = out.replace("CONFIG_TRACK=layout_gp_2025_fnr", f"CONFIG_TRACK={layout}")
    out = out.replace(f"__TRACK_GEOTAG_LAT={BCN_LAT}", f"__TRACK_GEOTAG_LAT={lat}")
    out = out.replace(f"__TRACK_GEOTAG_LONG={BCN_LNG}", f"__TRACK_GEOTAG_LONG={lng}")
    return out


def cmd_swap(tpl, slug, gp, loc, kind):
    out = tpl.replace("barcelona", slug)
    out = out.replace("No saved Pablo Barcelona setup yet", "No saved Pablo setup yet")
    if kind == "race":
        out = out.replace("[SPANISH GP 2026 - BARCELONA-CATALUNYA]", f"[{gp} - {loc}]")
        out = out.replace("SPANISH GP 2026 — BARCELONA-CATALUNYA", f"{gp} — {loc}")
        out = out.replace("SPANISH GP 2026", gp)
    else:
        out = out.replace("[BARCELONA HOTLAP 2026 - MERCEDES-AMG W16]", f"[{loc} HOTLAP 2026 - MERCEDES-AMG W16]")
        out = out.replace("BARCELONA HOTLAP 2026", f"{loc} HOTLAP 2026")
    return out


n_ini = n_cmd = n_img = 0
for slug, gp, loc, tid, layout, lat, lng in SPECS:
    # --- cfg .ini ---
    with open(os.path.join(CFG, f"race_{slug}_2026.ini"), "w", encoding="utf-8", newline="") as f:
        f.write(ini_swap(race_tpl, tid, layout, lat, lng)); n_ini += 1
    with open(os.path.join(CFG, f"hotlap_{slug}_2026.ini"), "w", encoding="utf-8", newline="") as f:
        f.write(ini_swap(hotlap_tpl, tid, layout, lat, lng)); n_ini += 1
    # --- launch .cmd (CRLF for Windows batch) ---
    with open(os.path.join(AC_DOC, f"launch_race_{slug}_2026.cmd"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(cmd_swap(race_cmd, slug, gp, loc, "race")); n_cmd += 1
    with open(os.path.join(AC_DOC, f"launch_hotlap_{slug}_2026.cmd"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(cmd_swap(hotlap_cmd, slug, gp, loc, "hotlap")); n_cmd += 1
    # --- card art: circuit photo + track map ---
    prev = find_preview(tid, layout)
    out = find_outline(tid, layout)
    if prev:
        for dst in (f"hotlap_{slug}_2026.jpg", f"race_{slug}_2026.jpg"):
            shutil.copyfile(prev, os.path.join(IMAGES, dst)); n_img += 1
    else:
        print(f"  WARN: no preview.png for {slug} ({tid}/{layout})")
    if out:
        shutil.copyfile(out, os.path.join(IMAGES, f"{slug}_2026_map.jpg")); n_img += 1
    else:
        print(f"  WARN: no outline.png for {slug} ({tid}/{layout})")
    print(f"  OK {slug:<11} -> {tid}/{layout}")

print(f"\nDone: {n_ini} .ini, {n_cmd} .cmd, {n_img} images for {len(SPECS)} events.")
