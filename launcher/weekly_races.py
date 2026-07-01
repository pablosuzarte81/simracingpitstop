#!/usr/bin/env python3
"""Weekly Races — the rotating "This Week" home page engine.

Three races every ISO week, regenerated deterministically from the week number
(so the set auto-rotates with no cron / manual reset):

    1. F1       — proven RSS Formula Hybrid 2025 grid, real GP calendar.
    2. GT3      — mixed-brand field, one class.
    3. WILDCARD — theme cycles: Hypercar -> Group C -> DTM/Touring -> Vintage F1.

Each race is a real race vs an AI grid. Pablo's best finish of the week is kept
(re-run to improve). At week rollover the finished week freezes into a standalone
recap appended to dashboard/weekly/history.json.

This module is intentionally self-contained (no import of the 14k-line monolith)
so it can be unit-run:  `python3 weekly_races.py`  prints this week's plan.

See SPEC_weekly_races.md for the full design + the verified install facts behind
every car/track id used here.
"""
from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths (env-overridable, defaults match launcher_dashboard.py)
# --------------------------------------------------------------------------- #
AC_INSTALL = Path(os.environ.get(
    "AC_INSTALL",
    "/mnt/f/SteamLibrary/steamapps/common/assettocorsa",
))
AC_DOC = Path(os.environ.get(
    "AC_DOC",
    str(Path.home() / "Documents" / "Assetto Corsa"),
))
# When run under WSL the docs live on the Windows side; fall back to that.
if not AC_DOC.exists():
    AC_DOC = Path("/mnt/c/Users/pablo/Documents/Assetto Corsa")

CARS_DIR = AC_INSTALL / "content" / "cars"
TRACKS_DIR = AC_INSTALL / "content" / "tracks"
CFG_DIR = AC_DOC / "cfg"
LAUNCHER_DIR = AC_DOC / "launcher"
WEEKLY_DIR = AC_DOC / "dashboard" / "weekly"
HISTORY_FILE = WEEKLY_DIR / "history.json"
SNAPSHOTS_DIR = AC_DOC / "dashboard" / "results" / "snapshots"

PLAYER_NAME = "Pablo Suzarte"

# Tunable race defaults ----------------------------------------------------- #
AI_LEVEL = 90
AI_AGGRESSION = 40
LAPS = {"f1": 5, "gt3": 6, "wild": 6}
GRID = {"f1": 19, "gt3": 12, "wild": 10}

POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]  # F1-style top-10
FASTEST_LAP_BONUS = 1

# Epoch week used to phase the wildcard theme cycle deterministically.
_EPOCH = date(2026, 1, 5)  # a Monday

# --------------------------------------------------------------------------- #
# Pools — every id below was verified present in the install on 2026-06-09.
# --------------------------------------------------------------------------- #

# F1: the proven 19-car grid harvested from cfg/race_belgium_2026.ini.
# CAR_0 (player) drives the Antonelli W16 skin, exactly like the working preset.
F1_CAR = "rss_formula_hybrid_2025_alpine"
F1_PLAYER_SKIN = "Asi_W16_Antonelli_12"
F1_PLAYER_TEAM = "Mercedes-AMG Petronas F1"
# (skin, driver, nationality, nation_code, team)
F1_AI_GRID = [
    ("M17_RedBull_RB21_1", "Max Verstappen", "Netherlands", "NLD", "Red Bull Racing"),
    ("Asi_W16_Russell_63", "George Russell", "United Kingdom", "GBR", "Mercedes-AMG Petronas F1"),
    ("FRX_McLaren_MCL39_4_Norris", "Lando Norris", "United Kingdom", "GBR", "McLaren F1 Team"),
    ("FRX_McLaren_MCL39_81_Piastri", "Oscar Piastri", "Australia", "AUS", "McLaren F1 Team"),
    ("M17_Ferrari_SF25_16", "Charles Leclerc", "Monaco", "MCO", "Scuderia Ferrari"),
    ("M17_Ferrari_SF25_44", "Lewis Hamilton", "United Kingdom", "GBR", "Scuderia Ferrari"),
    ("M17_Alpine_A525_43", "Franco Colapinto", "Argentina", "ARG", "BWT Alpine F1"),
    ("A6_Haas_2025_87", "Oliver Bearman", "United Kingdom", "GBR", "MoneyGram Haas F1"),
    ("FRX_Williams_FW47_55_Sainz", "Carlos Sainz", "Spain", "ESP", "Williams Racing"),
    ("M17_Sauber_C45_5", "Gabriel Bortoleto", "Brazil", "BRA", "Audi F1 Team"),
    ("FRX_Williams_FW47_23_Albon", "Alex Albon", "Thailand", "THA", "Williams Racing"),
    ("M17_Alpine_A525_10", "Pierre Gasly", "France", "FRA", "BWT Alpine F1"),
    ("A6_Haas_2025_31", "Esteban Ocon", "France", "FRA", "MoneyGram Haas F1"),
    ("FRX_Racing_Bulls_VCARB02_30_Lawson", "Liam Lawson", "New Zealand", "NZL", "Racing Bulls"),
    ("FRX_Racing_Bulls_VCARB02_6_Hadjar", "Isack Hadjar", "France", "FRA", "Racing Bulls"),
    ("RBC_Aston_Martin_AMR25_14", "Fernando Alonso", "Spain", "ESP", "Aston Martin Aramco F1"),
    ("M17_Sauber_C45_27", "Nico Hulkenberg", "Germany", "DEU", "Audi F1 Team"),
    ("RBC_Aston_Martin_AMR25_18", "Lance Stroll", "Canada", "CAN", "Aston Martin Aramco F1"),
]

# F1 calendar: (key, track_id, config_track, gp_name, location). All verified.
F1_TRACKS = [
    ("australia", "fn_albertpark", "layout_f1_2026", "Australian GP", "Albert Park, Melbourne"),
    ("china", "shanghai_v2_25", "layout_f1_2026", "Chinese GP", "Shanghai"),
    ("japan", "rt_suzuka", "layout_f1_2026", "Japanese GP", "Suzuka"),
    ("miami", "miami_f1", "layout_f1_2025", "Miami GP", "Miami"),
    ("canada", "montreal", "montreal_f1_2025", "Canadian GP", "Montréal"),
    ("austria", "fn_redbullring", "austria_f1_2026", "Austrian GP", "Red Bull Ring, Spielberg"),
    ("britain", "ks_silverstone", "silverstone_f1_2025", "British GP", "Silverstone"),
    ("hungary", "fn_hungaroring", "layout_f1_2025", "Hungarian GP", "Hungaroring, Budapest"),
    ("belgium", "spa", "layout_f1_2025", "Belgian GP", "Spa-Francorchamps"),
    ("netherlands", "zandvoort2023", "layout_f1_2025", "Dutch GP", "Zandvoort"),
    ("italy", "monza", "monza_f1_2025", "Italian GP", "Monza"),
    ("azerbaijan", "baku_2022", "layout_f1_2025", "Azerbaijan GP", "Baku"),
    ("singapore", "singapore_2020", "layout_f1_2025", "Singapore GP", "Marina Bay"),
    ("usa", "cota_2022", "layout_f1_2025", "United States GP", "COTA, Austin"),
    ("mexico", "acu_mexico_2021", "layout_f1_2025", "Mexico City GP", "Autódromo Hermanos Rodríguez"),
    ("brazil", "vhe_interlagos", "layout_f1_2025", "São Paulo GP", "Interlagos"),
    ("lasvegas", "lasvegas23", "layout_f1_2025", "Las Vegas GP", "Las Vegas Strip"),
    ("qatar", "fn_losail", "layout_f1_2025", "Qatar GP", "Lusail"),
    ("abudhabi", "chq_abu_dhabi_2024", "layout_f1_2025", "Abu Dhabi GP", "Yas Marina"),
    ("monaco", "monaco_2020", "monaco_f1_2025", "Monaco GP", "Monte Carlo"),
]

# GT3: mixed-brand field. (model, brand display)
GT3_CARS = [
    ("ks_audi_r8_lms_2016", "Audi R8 LMS"),
    ("ks_mercedes_amg_gt3", "Mercedes-AMG GT3"),
    ("ks_ferrari_488_gt3", "Ferrari 488 GT3"),
    ("ks_lamborghini_huracan_gt3", "Lamborghini Huracán GT3"),
    ("ks_nissan_gtr_gt3", "Nissan GT-R GT3"),
    ("ks_porsche_911_gt3_r_2016", "Porsche 911 GT3-R"),
    ("ks_mclaren_650_gt3", "McLaren 650S GT3"),
    ("bmw_z4_gt3", "BMW Z4 GT3"),
]
# GT3 venues (layout resolved from disk at generation time). (track_id, name)
GT3_TRACKS = [
    ("spa", "Spa-Francorchamps"),
    ("ks_brands_hatch", "Brands Hatch"),
    ("ks_silverstone", "Silverstone"),
    ("ks_barcelona", "Barcelona"),
    ("ks_red_bull_ring", "Red Bull Ring"),
    ("mugello", "Mugello"),
    ("ks_zandvoort", "Zandvoort"),
    ("kyalami", "Kyalami"),
    ("ks_vallelunga", "Vallelunga"),
    ("ks_laguna_seca", "Laguna Seca"),
    ("rt_suzuka", "Suzuka"),
    ("doningtonpark2018", "Donington Park"),
    ("paul_ricard", "Paul Ricard"),
    ("ks_nurburgring", "Nürburgring GP"),
]

# Wildcard themes. Each: id, label, blurb, car list [(model, display)], tracks.
WILDCARD_THEMES = [
    {
        "id": "hyper",
        "label": "Hypercar Shootout",
        "blurb": "Track-only monsters, no two alike. Tame them or be tamed.",
        "cars": [
            ("pagani_zonda_r", "Pagani Zonda R"),
            ("ks_ferrari_fxx_k", "Ferrari FXX-K"),
            ("ks_mclaren_p1_gtr", "McLaren P1 GTR"),
            ("ks_lamborghini_sesto_elemento", "Lamborghini Sesto Elemento"),
            ("ferrari_599xxevo", "Ferrari 599XX Evo"),
            ("ks_pagani_huayra_bc", "Pagani Huayra BC"),
        ],
        "tracks": [
            ("spa", "Spa-Francorchamps"),
            ("monza", "Monza"),
            ("mugello", "Mugello"),
            ("ks_red_bull_ring", "Red Bull Ring"),
            ("paul_ricard", "Paul Ricard"),
        ],
    },
    {
        "id": "groupc",
        "label": "Group C / Le Mans Legends",
        "blurb": "The greatest sportscars ever built, wheel to wheel.",
        "cars": [
            ("ks_mazda_787b", "Mazda 787B"),
            ("ks_porsche_962c_longtail", "Porsche 962C LT"),
            ("ks_mercedes_c9", "Mercedes-Benz C9"),
            ("ks_porsche_919_hybrid_2016", "Porsche 919 Hybrid"),
            ("ks_audi_r18_etron_quattro", "Audi R18 e-tron"),
            ("ks_porsche_962c_shorttail", "Porsche 962C ST"),
        ],
        "tracks": [
            ("sx_lemans", "Le Mans"),
            ("spa", "Spa-Francorchamps"),
            ("monza", "Monza"),
            ("fujispeedway_2017", "Fuji Speedway"),
            ("rt_sebring", "Sebring"),
        ],
    },
    {
        "id": "dtm",
        "label": "DTM & Touring Legends",
        "blurb": "Door-to-door brand war from touring's golden era.",
        "cars": [
            ("bmw_m3_e30_dtm", "BMW M3 E30 DTM"),
            ("ks_mercedes_190_evo2", "Mercedes 190E Evo II"),
            ("ks_alfa_romeo_155_v6", "Alfa Romeo 155 V6 TI"),
            ("pm3dm_volvo_s40_btcc", "Volvo S40 BTCC"),
        ],
        "tracks": [
            ("ks_nordschleife", "Nordschleife"),
            ("deutschlandring", "Deutschlandring"),
            ("ks_brands_hatch", "Brands Hatch"),
            ("ks_zandvoort", "Zandvoort"),
            ("magione", "Magione"),
        ],
    },
    {
        "id": "vintagef1",
        "label": "Vintage F1",
        "blurb": "Skinny tyres, no aids, infinite respect required.",
        "cars": [
            ("ferrari_312t", "Ferrari 312T"),
            ("lotus_72d", "Lotus 72D"),
            ("lotus_49", "Lotus 49"),
        ],
        "tracks": [
            ("ks_monza66", "Monza (1966)"),
            ("ks_silverstone1967", "Silverstone (1967)"),
            ("ks_nordschleife", "Nordschleife"),
            ("imola", "Imola"),
            ("spa", "Spa-Francorchamps"),
        ],
    },
]

# --------------------------------------------------------------------------- #
# Real-world motorsport calendar.
#
# When a marquee real event runs THIS week it is surfaced on the home page in
# place of the deterministic filler. Each event is pinned to a slot KEY
# (f1 / gt3 / wild) so the generated preset filenames (race_week_{slot}.ini) and
# the launch whitelist (launch_week_{slot}.cmd) stay valid without touching the
# monolith. Dates + track/car ids below are ALL verified on disk / against the
# official calendars — do NOT invent. To add an event: append a dict here with a
# date window and a real, on-disk track_id/config_track.
# --------------------------------------------------------------------------- #
# Verified 2026 F1 race-Sunday dates. Source: en.wikipedia.org/wiki/
# 2026_Formula_One_World_Championship (fetched 2026-07-01). Keyed by the
# F1_TRACKS / F1_2026_EXTRA_TRACKS slug. These drive the "This Week" home page:
# each GP auto-surfaces on the f1 slot during the ISO week of its race.
F1_2026_DATES = {
    "australia": date(2026, 3, 8), "china": date(2026, 3, 15),
    "japan": date(2026, 3, 29), "miami": date(2026, 5, 3),
    "canada": date(2026, 5, 24), "monaco": date(2026, 6, 7),
    "barcelona": date(2026, 6, 14), "austria": date(2026, 6, 28),
    "britain": date(2026, 7, 5), "belgium": date(2026, 7, 19),
    "hungary": date(2026, 7, 26), "netherlands": date(2026, 8, 23),
    "italy": date(2026, 9, 6), "madrid": date(2026, 9, 13),
    "azerbaijan": date(2026, 9, 26), "singapore": date(2026, 10, 11),
    "usa": date(2026, 10, 25), "mexico": date(2026, 11, 1),
    "brazil": date(2026, 11, 8), "lasvegas": date(2026, 11, 21),
    "qatar": date(2026, 11, 29), "abudhabi": date(2026, 12, 6),
}
# /event hub-page id per GP where it differs from the F1_TRACKS slug.
F1_2026_EVENT_ID = {"canada": "montreal_2026"}
# GPs not in F1_TRACKS: slug -> (track_id, config_track|None, gp_title, location, event_id).
# fn_barcelona/layout_gp_2026_fnr is the proven Spanish-GP track (verified in this
# project); fn_aragon is the labelled Madrid stand-in (no Madring in AC). Both are
# guarded by track_exists() in events_this_week(), so a missing folder simply drops.
F1_2026_EXTRA_TRACKS = {
    "barcelona": ("fn_barcelona", "layout_gp_2026_fnr",
                  "Barcelona-Catalunya Grand Prix",
                  "Circuit de Barcelona-Catalunya", "barcelona_2026"),
    "madrid": ("fn_aragon", None, "Spanish Grand Prix",
               "Madring · Madrid (Aragón stand-in)", "madrid_2026"),
}


def _f1_calendar_real_events() -> list:
    """Build one real F1 event per dated 2026 GP, windowed to its race ISO week,
    so the correct Grand Prix is surfaced on the home page every race weekend."""
    evs = []
    for key, race_date in F1_2026_DATES.items():
        row = next((t for t in F1_TRACKS if t[0] == key), None)
        if row:
            _, tid, cfg_track, gp, loc = row
            eid = F1_2026_EVENT_ID.get(key, f"{key}_2026")
            title = gp.replace(" GP", " Grand Prix")
        elif key in F1_2026_EXTRA_TRACKS:
            tid, cfg_track, title, loc, eid = F1_2026_EXTRA_TRACKS[key]
            if cfg_track is None:
                cfg_track = resolve_layout(tid)
        else:
            continue
        wk_mon = race_date - timedelta(days=race_date.weekday())
        wk_sun = wk_mon + timedelta(days=6)
        label = title.replace(" Grand Prix", "").replace("-Catalunya", "").upper()
        evs.append({
            "id": f"f1_{key}_2026", "slot": "f1", "kind": "f1",
            "start": wk_mon, "end": wk_sun,
            "slot_label": f"FORMULA 1 · {label}", "accent": "#e10600",
            "title": title, "location": loc,
            "track_id": tid, "config_track": cfg_track,
            "event_id": eid,
        })
    return evs


REAL_EVENTS = [
    {
        # 24 Hours of Le Mans 2026 — race 13–14 Jun, Circuit de la Sarthe.
        # Verified: 24h-lemans.com + Wikipedia "2026 24 Hours of Le Mans".
        "id": "lemans_2026", "slot": "gt3", "kind": "endurance",
        "start": date(2026, 6, 8), "end": date(2026, 6, 14),
        "slot_label": "LE MANS 24H", "accent": "#c98a00",
        "title": "24 Hours of Le Mans", "location": "Circuit de la Sarthe",
        "track_id": "sx_lemans", "config_track": "24h_2026",
        "player_car": "ks_porsche_919_hybrid_2016",
        "player_display": "Porsche 919 Hybrid",
        "field_theme": "groupc", "laps": 6,
        "event_id": "lemans_2026",  # /event/ hub page to "enter the event"
    },
]
# The full dated F1 calendar is appended to REAL_EVENTS at the end of this module
# (after resolve_layout is defined) via _f1_calendar_real_events().


def _theme_by_id(theme_id: str) -> dict | None:
    return next((t for t in WILDCARD_THEMES if t["id"] == theme_id), None)


def events_this_week(d: date | None = None) -> list:
    """Real events whose date window overlaps the ISO week of d (and exist on disk)."""
    d = d or date.today()
    start, _ = week_bounds(d)
    wk_mon = start.date()
    wk_sun = wk_mon + timedelta(days=6)
    return [
        ev for ev in REAL_EVENTS
        if ev["start"] <= wk_sun and ev["end"] >= wk_mon and track_exists(ev["track_id"])
    ]


def _event_for_slot(events: list, slot: str) -> dict | None:
    return next((e for e in events if e["slot"] == slot), None)


def _event_url(ev: dict | None) -> str | None:
    """The /event/ hub URL for a real event so the card can link into it."""
    if ev and ev.get("event_id"):
        return f"/event/{ev['event_id']}"
    return None


# AI driver name pools for generated (GT3/wildcard) fields.
_AI_NAMES = [
    "Kenji Sato", "Lukas Brandt", "Marco Rossi", "Diego Herrera", "Tom Fielding",
    "Niklas Berg", "Hugo Laurent", "Sven Larsson", "Paolo Greco", "Andrei Volkov",
    "Sam Whitlock", "Felix Maier", "Joao Ferreira", "Mika Nieminen", "Ben Carter",
    "Rafael Costa", "Otto Kaufmann", "Liam Doyle", "Tobias Reiner", "Cesar Mendez",
]


# --------------------------------------------------------------------------- #
# Install introspection (no guessing — read the disk)
# --------------------------------------------------------------------------- #
_PREFERRED = ("gp", "grand_prix", "endurance", "full", "circuit")
_AVOID = ("wet", "drift", "rally", "oval", "drag", "short", "indy", "_rev", "reverse", "kart")

# Install introspection is stable for the life of the process — the AC content
# folder doesn't change while the server runs — and each lookup is a slow stat
# over the WSL→Windows filesystem. Memoize every disk hit. A .py save reloads the
# server (clearing these); a real content change just needs a restart.
_LAYOUT_CACHE: dict[str, str] = {}
_SKIN_CACHE: dict[str, str] = {}
_EXISTS_CACHE: dict[str, bool] = {}
# Plans are deterministic per ISO week → memoize so archive_if_rolled_over's
# look-back doesn't regenerate 8 weeks of disk scans on every page load.
_PLAN_CACHE: dict[tuple[int, int], dict] = {}


def resolve_layout(track_id: str) -> str:
    """CONFIG_TRACK for a track id, read from disk (memoized)."""
    if track_id not in _LAYOUT_CACHE:
        _LAYOUT_CACHE[track_id] = _resolve_layout(track_id)
    return _LAYOUT_CACHE[track_id]


def _resolve_layout(track_id: str) -> str:
    """Root ui/ui_track.json -> "" (default). Else best layout subfolder that has
    ui_track.json, preferring full GP configs and avoiding wet/drift/oval."""
    ui = TRACKS_DIR / track_id / "ui"
    if (ui / "ui_track.json").exists():
        return ""
    layouts = []
    if ui.exists():
        for d in sorted(ui.iterdir()):
            if d.is_dir() and (d / "ui_track.json").exists():
                layouts.append(d.name)
    if not layouts:
        return ""
    # Prefer a clean GP layout, else the first that isn't an avoided variant.
    for name in layouts:
        low = name.lower()
        if any(p in low for p in _PREFERRED) and not any(a in low for a in _AVOID):
            return name
    for name in layouts:
        if not any(a in name.lower() for a in _AVOID):
            return name
    return layouts[0]


def first_skin(car_id: str) -> str:
    """First skin folder of a car (alphabetical), or '' if none (memoized)."""
    if car_id not in _SKIN_CACHE:
        skin = ""
        skins = CARS_DIR / car_id / "skins"
        if skins.exists():
            for d in sorted(skins.iterdir()):
                if d.is_dir():
                    skin = d.name
                    break
        _SKIN_CACHE[car_id] = skin
    return _SKIN_CACHE[car_id]


def car_exists(car_id: str) -> bool:
    k = "c:" + car_id
    if k not in _EXISTS_CACHE:
        _EXISTS_CACHE[k] = (CARS_DIR / car_id).is_dir()
    return _EXISTS_CACHE[k]


def track_exists(track_id: str) -> bool:
    k = "t:" + track_id
    if k not in _EXISTS_CACHE:
        _EXISTS_CACHE[k] = (TRACKS_DIR / track_id).is_dir()
    return _EXISTS_CACHE[k]


# --------------------------------------------------------------------------- #
# Deterministic weekly generation
# --------------------------------------------------------------------------- #
def week_id(d: date | None = None) -> tuple[int, int]:
    """ISO (year, week) — the rotation key."""
    iso = (d or date.today()).isocalendar()
    return iso[0], iso[1]


def week_bounds(d: date | None = None) -> tuple[datetime, datetime]:
    """UTC datetime bounds [Mon 00:00, next Mon 00:00) for the week of d."""
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=7)


def _rng(year: int, week: int) -> random.Random:
    return random.Random(year * 100 + week)


def _theme_for_week(d: date, avoid: str | None = None) -> dict:
    monday = d - timedelta(days=d.weekday())
    weeks_since = (monday - _EPOCH).days // 7
    themes = [t for t in WILDCARD_THEMES if t["id"] != avoid] if avoid else WILDCARD_THEMES
    return themes[weeks_since % len(themes)]


def _build_real_endurance(ev: dict, rng: random.Random) -> dict:
    """Build a featured real-world endurance race (Le Mans etc.).

    Player drives the event's pinned car; the AI field is drawn from the named
    wildcard theme pool (e.g. Group C / LMP). Keeps the event's slot KEY so the
    preset filename + launch whitelist stay valid.
    """
    theme = _theme_by_id(ev.get("field_theme", "groupc")) or WILDCARD_THEMES[0]
    _, ai = build_field(theme["cars"], GRID["gt3"], rng)
    player_car = ev["player_car"]
    return {
        "slot": ev["slot"], "slot_label": ev["slot_label"], "accent": ev["accent"],
        "title": ev["title"], "location": ev["location"],
        "track_id": ev["track_id"], "config_track": ev["config_track"],
        "player_car": player_car, "player_skin": first_skin(player_car),
        "player_display": ev.get("player_display", player_car),
        "grid": len(ai), "laps": ev.get("laps", LAPS["gt3"]), "field": ai,
        "real": True, "event_url": _event_url(ev),
    }


def build_field(cars: list, n: int, rng: random.Random, player_idx: int = 0):
    """Build a grid of n entries by cycling a car list (AI may share a model).

    Returns (player_entry, ai_entries) where each entry is a dict with
    model/skin/driver/team. cars items are (model, display)."""
    usable = [(m, disp) for m, disp in cars if car_exists(m)]
    if not usable:
        return None, []
    rng.shuffle(usable)
    player_model, player_disp = usable[0]
    entries = []
    names = _AI_NAMES[:]
    rng.shuffle(names)
    for i in range(n):
        model, disp = usable[i % len(usable)]
        entries.append({
            "model": model,
            "display": disp,
            "skin": first_skin(model),
            "driver": names[i % len(names)],
        })
    player = {
        "model": player_model,
        "display": player_disp,
        "skin": first_skin(player_model),
        "driver": PLAYER_NAME,
    }
    return player, entries


def generate_week(d: date | None = None) -> dict:
    """Deterministically produce this week's three races (data only)."""
    d = d or date.today()
    year, week = week_id(d)
    cached = _PLAN_CACHE.get((year, week))
    if cached is not None:
        return cached
    rng = _rng(year, week)
    start, end = week_bounds(d)
    events = events_this_week(d)

    # --- Slot 1 · F1: the real Grand Prix this week, else rotate the calendar ---
    f1_ev = _event_for_slot(events, "f1")
    if f1_ev:
        ftid, fcfg = f1_ev["track_id"], f1_ev["config_track"]
        fname, floc = f1_ev["title"], f1_ev["location"]
        f1_label, f1_accent = f1_ev["slot_label"], f1_ev["accent"]
    else:
        f1t = [t for t in F1_TRACKS if track_exists(t[1])]
        _, ftid, fcfg, fname, floc = rng.choice(f1t)
        f1_label, f1_accent = "FORMULA 1", "#e10600"
    f1 = {
        "slot": "f1", "slot_label": f1_label, "accent": f1_accent,
        "title": fname, "location": floc,
        "track_id": ftid, "config_track": fcfg,
        "player_car": F1_CAR, "player_skin": F1_PLAYER_SKIN,
        "player_display": "Mercedes-AMG W16 #12",
        "grid": GRID["f1"], "laps": LAPS["f1"], "real": bool(f1_ev),
        "event_url": _event_url(f1_ev),
    }

    # --- Slot 2 · a marquee real endurance event this week, else the GT3 round ---
    end_ev = _event_for_slot(events, "gt3")
    if end_ev:
        slot2 = _build_real_endurance(end_ev, rng)
    else:
        gt3_tid, gt3_name = rng.choice([t for t in GT3_TRACKS if track_exists(t[0])])
        g_player, g_ai = build_field(GT3_CARS, GRID["gt3"], rng)
        slot2 = {
            "slot": "gt3", "slot_label": "GT3", "accent": "#1f8fff",
            "title": "GT3 Championship Round", "location": gt3_name,
            "track_id": gt3_tid, "config_track": resolve_layout(gt3_tid),
            "player_car": g_player["model"], "player_skin": g_player["skin"],
            "player_display": g_player["display"],
            "grid": len(g_ai), "laps": LAPS["gt3"], "field": g_ai, "real": False,
        }

    # --- Slot 3 · the fun one: themed wildcard (skip the endurance race's theme) ---
    avoid = end_ev.get("field_theme") if end_ev else None
    theme = _theme_for_week(d, avoid=avoid)
    w_tid, w_name = rng.choice([t for t in theme["tracks"] if track_exists(t[0])])
    w_player, w_ai = build_field(theme["cars"], GRID["wild"], rng)
    wild = {
        "slot": "wild", "slot_label": theme["label"].upper(), "accent": "#b14bff",
        "title": theme["label"], "location": w_name, "blurb": theme["blurb"],
        "theme": theme["id"],
        "track_id": w_tid, "config_track": resolve_layout(w_tid),
        "player_car": w_player["model"], "player_skin": w_player["skin"],
        "player_display": w_player["display"],
        "grid": len(w_ai), "laps": LAPS["wild"], "field": w_ai, "real": False,
    }

    plan = {
        "year": year, "week": week,
        "start": start.isoformat(), "end": end.isoformat(),
        "races": [f1, slot2, wild],
    }
    _PLAN_CACHE[(year, week)] = plan
    return plan


# --------------------------------------------------------------------------- #
# race.ini generation
# --------------------------------------------------------------------------- #
def _ini_header(race: dict) -> str:
    cfg = race["config_track"]
    return f"""; AUTO-GENERATED weekly race — {race['slot_label']} — do not hand-edit.
[HEADER]
VERSION=2
__CM_FEATURE_SET=2

[RACE]
TRACK={race['track_id']}
CONFIG_TRACK={cfg}
MODEL={race['player_car']}
MODEL_CONFIG=
CARS={race['grid'] + 1}
AI_LEVEL={AI_LEVEL}
FIXED_SETUP=0
PENALTIES=1
SKIN={race['player_skin']}
DRIFT_MODE=0
RACE_LAPS={race['laps']}
JUMP_START_PENALTY=1
AI_AGGRESSION={AI_AGGRESSION}
RACE_GAS_PENALTY_DISABLED=0
OPPONENTS_VARIETY=1
__CM_WEATHER_TYPE=-1
__CM_WEATHER_CONTROLLER=base

[OPTIONS]
USE_MPH=0

[LAP_INVALIDATOR]
ALLOWED_TYRES_OUT=-1

[TEMPERATURE]
AMBIENT=20
ROAD=28

[WEATHER]
NAME=3_clear

[LIGHTING]
SUN_ANGLE=20.00
TIME_MULT=1.0
CLOUD_SPEED=0.200

[GROOVE]
VIRTUAL_LAPS=10
MAX_LAPS=1
STARTING_LAPS=1

[DYNAMIC_TRACK]
SESSION_START=92
SESSION_TRANSFER=100
RANDOMNESS=1
LAP_GAIN=1

[REMOTE]
ACTIVE=0

[GHOST_CAR]
RECORDING=0
PLAYING=0
ENABLED=0

[REPLAY]
FILENAME=
ACTIVE=0

[SESSION_0]
NAME=Race
TYPE=3
DURATION_MINUTES=0
LAPS={race['laps']}
SPAWN_SET=START
"""


def _car_section(idx: int, model: str, skin: str, driver: str,
                 nationality: str = "", nation_code: str = "",
                 team: str = "", is_player: bool = False) -> str:
    model_line = "-" if is_player else model
    return f"""
[CAR_{idx}]
SETUP=
SKIN={skin}
MODEL={model_line}
MODEL_CONFIG=
DRIVER_NAME={driver}
NATIONALITY={nationality}
NATION_CODE={nation_code}
TEAM={team}
BALLAST=0
RESTRICTOR=0
AI_LEVEL={AI_LEVEL}
"""


def render_race_ini(race: dict) -> str:
    """Full race.ini text for a generated weekly race."""
    out = [_ini_header(race)]
    # CAR_0 — player on pole.
    out.append(_car_section(
        0, race["player_car"], race["player_skin"], PLAYER_NAME,
        is_player=True,
    ))
    if race["slot"] == "f1":
        for i, (skin, drv, nat, code, team) in enumerate(F1_AI_GRID, start=1):
            out.append(_car_section(i, F1_CAR, skin, drv, nat, code, team))
    else:
        for i, ai in enumerate(race.get("field", []), start=1):
            out.append(_car_section(i, ai["model"], ai["skin"], ai["driver"],
                                    team=ai["display"]))
    return "".join(out)


def render_hotlap_ini(race: dict) -> str:
    """Solo hotlap preset for a weekly race — single car, ghost on, garage open.

    Mirrors the proven hotlap format (cfg/hotlap_barcelona_2026.ini): TYPE=4,
    CARS=1, no penalties, ghost recording+playing, SPAWN_SET=HOTLAP_START.
    """
    return f"""; AUTO-GENERATED weekly HOTLAP — {race['slot_label']} — do not hand-edit.
[HEADER]
VERSION=2
__CM_FEATURE_SET=2

[RACE]
TRACK={race['track_id']}
CONFIG_TRACK={race['config_track']}
MODEL={race['player_car']}
MODEL_CONFIG=
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=0
SKIN={race['player_skin']}
DRIFT_MODE=0
RACE_LAPS=0
JUMP_START_PENALTY=0
AI_AGGRESSION=0
RACE_GAS_PENALTY_DISABLED=0
OPPONENTS_VARIETY=0
__CM_WEATHER_TYPE=-1
__CM_WEATHER_CONTROLLER=base

[OPTIONS]
USE_MPH=0

[LAP_INVALIDATOR]
ALLOWED_TYRES_OUT=-1

[TEMPERATURE]
AMBIENT=20
ROAD=28

[WEATHER]
NAME=3_clear

[LIGHTING]
SUN_ANGLE=20.00
TIME_MULT=1.0
CLOUD_SPEED=0.200

[GROOVE]
VIRTUAL_LAPS=10
MAX_LAPS=1
STARTING_LAPS=1

[DYNAMIC_TRACK]
SESSION_START=100
SESSION_TRANSFER=100
RANDOMNESS=0
LAP_GAIN=1

[REMOTE]
ACTIVE=0

[GHOST_CAR]
RECORDING=1
PLAYING=1
SECONDS_ADVANTAGE=0
LOAD=1
ENABLED=1

[REPLAY]
FILENAME=
ACTIVE=0

[SESSION_0]
; TYPE=4 (Hotlap): spawns straight onto the track, garage setup unlocked.
NAME=Hotlap
TYPE=4
DURATION_MINUTES=0
SPAWN_SET=HOTLAP_START

[CAR_0]
SETUP=
SKIN={race['player_skin']}
MODEL=-
MODEL_CONFIG=
DRIVER_NAME={PLAYER_NAME}
NATIONALITY=
NATION_CODE=
TEAM=
BALLAST=0
RESTRICTOR=0
AI_LEVEL=100
"""


def render_launch_cmd(slot: str, preset_name: str, label: str) -> str:
    """A .cmd mirroring the proven RACE launcher chain."""
    return f"""@echo off
REM AUTO-GENERATED weekly race launcher — {label}
setlocal enableextensions
set "ACDOC=%USERPROFILE%\\Documents\\Assetto Corsa"
set "ACINSTALL=F:\\SteamLibrary\\steamapps\\common\\assettocorsa"
set "PRESET=%ACDOC%\\cfg\\{preset_name}"
set "TARGET=%ACDOC%\\cfg\\race.ini"
set "BACKUP=%ACDOC%\\cfg\\race.ini.bak"

echo  [WEEKLY · {label}]
if not exist "%PRESET%" ( echo ERROR: preset not found: %PRESET% & pause & exit /b 1 )
if not exist "%ACINSTALL%\\acs.exe" ( echo ERROR: AC not found & pause & exit /b 1 )
if exist "%TARGET%" copy /Y "%TARGET%" "%BACKUP%" >nul
copy /Y "%PRESET%" "%TARGET%" >nul
call "%~dp0launcher\\start_crew_chief.cmd"
start "" /D "%ACINSTALL%" "%ACINSTALL%\\acs.exe"
start "" /B powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher\\wait_and_close_cc.ps1"
endlocal
exit /b 0
"""


def write_week_files(plan: dict) -> dict:
    """Write the 3 race.ini presets + .cmd launchers for the given plan.

    Returns {slot: {"preset": name, "cmd": name}}.
    """
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    LAUNCHER_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for race in plan["races"]:
        slot = race["slot"]
        preset = f"race_week_{slot}.ini"
        cmd = f"launch_week_{slot}.cmd"
        hl_preset = f"hotlap_week_{slot}.ini"
        hl_cmd = f"launch_week_{slot}_hotlap.cmd"
        # Race: full grid (TYPE=3). Hotlap: solo vs the clock (TYPE=4).
        (CFG_DIR / preset).write_text(render_race_ini(race), encoding="utf-8")
        (CFG_DIR / hl_preset).write_text(render_hotlap_ini(race), encoding="utf-8")
        # .cmd files live in AC_DOC root (alongside the other launch_*.cmd).
        (AC_DOC / cmd).write_text(
            render_launch_cmd(slot, preset, race["slot_label"]),
            encoding="utf-8",
        )
        (AC_DOC / hl_cmd).write_text(
            render_launch_cmd(slot, hl_preset, race["slot_label"] + " · HOTLAP"),
            encoding="utf-8",
        )
        written[slot] = {"preset": preset, "cmd": cmd,
                         "hl_preset": hl_preset, "hl_cmd": hl_cmd}
    return written


# --------------------------------------------------------------------------- #
# Results — read finishing position from race snapshots
# --------------------------------------------------------------------------- #
def _player_finish(snap: dict) -> tuple[int | None, int | None]:
    """(finish_position, best_lap_ms) for the human in a race snapshot.

    Defensive: race-result schema validated on first real race. CAR_0 is the
    player; raceResult lists car indices in finishing order.
    """
    best_ms = None
    pos = None
    for s in snap.get("sessions", []):
        if s.get("type") != 3:  # race session only
            continue
        rr = s.get("raceResult")
        if isinstance(rr, list) and rr:
            try:
                pos = rr.index(0) + 1  # player car index = 0
            except ValueError:
                pos = None
        bl = s.get("bestLaps")
        if isinstance(bl, list):
            for entry in bl:
                car = entry.get("car") if isinstance(entry, dict) else None
                t = entry.get("time") if isinstance(entry, dict) else None
                if car == 0 and isinstance(t, int) and t > 0:
                    best_ms = t
        # Fallback: if no raceResult, infer from number of laps lists.
        if pos is None and isinstance(s.get("laps"), list) and s["laps"]:
            pos = 1
    return pos, best_ms


def _snapshot_matches(snap: dict, race: dict) -> bool:
    track = (snap.get("track") or "")
    want = race["track_id"]
    if race["config_track"]:
        want = f"{race['track_id']}-{race['config_track']}"
    if track != want and not track.startswith(race["track_id"]):
        return False
    players = snap.get("players") or []
    if players and isinstance(players[0], dict):
        return players[0].get("car") == race["player_car"]
    return True


# Snapshots are write-once timestamped files. Two-level cache:
#  - index: [(ts, Path)] read from FILENAMES only (no JSON parse), by dir sig.
#  - parse: path -> dict, parsed lazily and only for files actually needed
#    (in a week window we care about). The home page therefore parses ~0–3
#    JSONs instead of all ~184 — the timestamp prefix lets us skip the rest.
_SNAP_INDEX_CACHE: dict = {"sig": None, "data": []}
_SNAP_PARSE_CACHE: dict = {}


def _snap_signature():
    try:
        names = [n for n in os.listdir(SNAPSHOTS_DIR) if n.endswith(".json")]
    except OSError:
        return None
    try:
        mtime = SNAPSHOTS_DIR.stat().st_mtime_ns
    except OSError:
        mtime = 0
    return (mtime, len(names))


def _snapshot_index():
    """[(ts, Path)] for every snapshot — timestamps from filenames, no parsing."""
    sig = _snap_signature()
    if _SNAP_INDEX_CACHE["sig"] == sig:
        return _SNAP_INDEX_CACHE["data"]
    data = []
    if SNAPSHOTS_DIR.exists():
        for f in SNAPSHOTS_DIR.glob("*.json"):
            try:
                ts = datetime.strptime(f.stem[:15], "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            data.append((ts, f))
    _SNAP_INDEX_CACHE["sig"] = sig
    _SNAP_INDEX_CACHE["data"] = data
    return data


def _load_snap(path):
    """Parse one snapshot, cached by path (write-once files never change)."""
    key = str(path)
    if key not in _SNAP_PARSE_CACHE:
        try:
            _SNAP_PARSE_CACHE[key] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _SNAP_PARSE_CACHE[key] = None
    return _SNAP_PARSE_CACHE[key]


def results_for_week(plan: dict) -> dict:
    """Best finish per slot from snapshots inside the week window."""
    start = datetime.fromisoformat(plan["start"])
    end = datetime.fromisoformat(plan["end"])
    out = {r["slot"]: None for r in plan["races"]}
    for ts, path in _snapshot_index():
        if not (start <= ts < end):
            continue
        snap = _load_snap(path)
        if snap is None:
            continue
        for race in plan["races"]:
            if not _snapshot_matches(snap, race):
                continue
            pos, best_ms = _player_finish(snap)
            if pos is None:
                continue
            cur = out[race["slot"]]
            if cur is None or pos < cur["finish"]:
                out[race["slot"]] = {"finish": pos, "best_lap_ms": best_ms}
    return out


def points_for_finish(pos: int | None, fastest: bool = False) -> int:
    if not pos or pos > len(POINTS):
        base = 0
    else:
        base = POINTS[pos - 1]
    return base + (FASTEST_LAP_BONUS if fastest else 0)


def weekly_score(plan: dict, results: dict) -> int:
    total = 0
    for race in plan["races"]:
        r = results.get(race["slot"])
        if r:
            total += points_for_finish(r["finish"])
    return total


# --------------------------------------------------------------------------- #
# History (standalone weeks)
# --------------------------------------------------------------------------- #
def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
    return []


def save_history(history: list) -> None:
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False),
                            encoding="utf-8")


def archive_if_rolled_over(current_plan: dict) -> list:
    """If history's newest week predates an unarchived past week, freeze it.

    Called on each page load. Re-generates the *previous* week's plan, reads its
    results, and appends a frozen recap if not already stored.
    """
    history = load_history()
    have = {(h["year"], h["week"]) for h in history}
    current_wk = (current_plan["year"], current_plan["week"])

    # Only PAST weeks that actually have race snapshots can be archived. Derive
    # those weeks straight from the (cached) snapshot timestamps instead of
    # regenerating 8 weeks of plans + disk scans on every cold load.
    snap_weeks = set()
    for ts, _path in _snapshot_index():
        iso = ts.isocalendar()
        snap_weeks.add((iso[0], iso[1]))

    changed = False
    for y, w in snap_weeks:
        if (y, w) == current_wk or (y, w) in have:
            continue
        # A Thursday is always inside its ISO week → safe seed date.
        d = date.fromisocalendar(y, w, 4)
        past = generate_week(d)
        res = results_for_week(past)
        if not any(res.get(r["slot"]) for r in past["races"]):
            continue
        history.append(_freeze(past, res))
        have.add((y, w))
        changed = True

    history.sort(key=lambda h: (h["year"], h["week"]), reverse=True)
    if changed:
        save_history(history)
    return history


def _freeze(plan: dict, results: dict) -> dict:
    races = []
    for race in plan["races"]:
        r = results.get(race["slot"])
        races.append({
            "slot": race["slot"],
            "slot_label": race["slot_label"],
            "title": race["title"],
            "location": race["location"],
            "finish": r["finish"] if r else None,
            "points": points_for_finish(r["finish"]) if r else 0,
            "best_lap_ms": r["best_lap_ms"] if r else None,
        })
    return {
        "year": plan["year"], "week": plan["week"],
        "races": races, "total": sum(x["points"] for x in races),
    }


# --------------------------------------------------------------------------- #
# Public convenience
# --------------------------------------------------------------------------- #
# Bundle cache: the home page recomputes only when the week rolls over or a new
# race snapshot lands. Both are captured by (week_id, snapshots signature).
_BUNDLE_CACHE: dict = {"key": None, "bundle": None, "files_week": None}


def current_week(refresh_files: bool = True) -> dict:
    """Full bundle for the home page: plan + live results + score + history.

    Cached by (ISO week, snapshots signature) so a plain reload is O(1); it only
    recomputes when the week changes or Pablo posts a new race result.
    """
    wk = week_id()
    key = (wk, _snap_signature())
    if _BUNDLE_CACHE["key"] == key and _BUNDLE_CACHE["bundle"] is not None:
        return _BUNDLE_CACHE["bundle"]

    plan = generate_week()
    # Preset/launcher files only need (re)writing once per week, not per request.
    if refresh_files and _BUNDLE_CACHE["files_week"] != wk:
        try:
            write_week_files(plan)
            _BUNDLE_CACHE["files_week"] = wk
        except OSError:
            pass
    history = archive_if_rolled_over(plan)
    results = results_for_week(plan)
    bundle = {
        "plan": plan,
        "results": results,
        "score": weekly_score(plan, results),
        "history": history,
    }
    _BUNDLE_CACHE["key"] = key
    _BUNDLE_CACHE["bundle"] = bundle
    return bundle


def fmt_lap(ms: int | None) -> str:
    if not ms:
        return "—"
    m, s = divmod(ms / 1000.0, 60)
    return f"{int(m)}:{s:06.3f}"


# Append the full dated F1 calendar now that resolve_layout is defined, so the
# correct Grand Prix surfaces on the "This Week" home page every race weekend.
REAL_EVENTS += _f1_calendar_real_events()


if __name__ == "__main__":
    bundle = current_week(refresh_files=False)
    p = bundle["plan"]
    print(f"\n=== WEEK {p['year']}-W{p['week']:02d} ===")
    for race in p["races"]:
        res = bundle["results"].get(race["slot"])
        fin = f"P{res['finish']}" if res else "not raced"
        print(f"  [{race['slot_label']}] {race['title']} @ {race['location']}")
        print(f"      car={race['player_car']} skin={race['player_skin']}")
        print(f"      track={race['track_id']} cfg='{race['config_track']}' "
              f"grid={race['grid']} laps={race['laps']}  -> {fin}")
    print(f"  weekly score: {bundle['score']}")
    print(f"  history weeks: {len(bundle['history'])}")
