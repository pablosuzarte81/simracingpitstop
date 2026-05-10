#!/usr/bin/env python3
"""SimRacingPitStop · Launch Bay
Race-control dashboard. Catalog of every preset Pablo has built — race
configs and hotlap chases — each with a hero panel, scenario prose, goal
callout, spec tower, and one-click LAUNCH button that runs the matching
.cmd via Windows.

Run:  wsl python3 launcher_dashboard.py    # serves on http://localhost:8765/
Or:   LAUNCH_BAY.cmd                       # one-click entrypoint
"""

import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from datetime import date, datetime
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote


AC_DOC = Path(os.environ.get(
    "AC_DOC",
    "/mnt/c/Users/pablo/Documents/Assetto Corsa",
))
AC_INSTALL = Path(os.environ.get(
    "AC_INSTALL",
    "/mnt/d/SteamLibrary/steamapps/common/assettocorsa",
))
CARS_DIR = AC_INSTALL / "content" / "cars"
TRACKS_DIR = AC_INSTALL / "content" / "tracks"
LAUNCHER_DIR = AC_DOC / "launcher"
IMAGES_DIR = LAUNCHER_DIR / "images"
PORT = int(os.environ.get("LAUNCH_BAY_PORT", "8765"))

MOZA_DASH_ROOT = Path(os.environ.get(
    "MOZA_DASH_ROOT",
    "/mnt/c/Users/pablo/AppData/Local/MOZA Pit House/_dashes",
))
MOZA_ACCOUNT_HASH = "185dc19b73d3470cd1042f0f"

RACE_START = date(2026, 5, 14)
RACE_END = date(2026, 5, 17)


# -- Series catalog ----------------------------------------------------------
# Cards are grouped by racing series. SERIES order = render order.
SERIES = [
    {
        "id":    "NLS",
        "label": "NLS · NÜRBURGRING",
        "deck":  "Dress rehearsals for the real 24H Nürburgring at the Nordschleife — the same combo, the same field.",
        "countdown": {
            "start":  RACE_START,
            "end":    RACE_END,
            "title":  "24H NÜRBURGRING",
            "window": "14–17 MAY",
        },
    },
    {
        "id":    "F1_2026",
        "label": "FORMULA 1 · 2026",
        "deck":  "F1 hybrid laps and races on the 2026 calendar — chasing real qualifying and pole times.",
    },
    {
        "id":    "F1_2008",
        "label": "FORMULA 1 · 2008",
        "deck":  "Hamilton's title-decider season — McLaren MP4-23 vs Ferrari F2008 vs the rest of the 11-team grid. Recreate the moments that came down to one corner on the last lap.",
    },
    {
        "id":    "SCHUMACHER",
        "label": "SCHUMACHER · ICONIC RACES",
        "deck":  "Recreations of Michael Schumacher's defining moments — debut at Spa '91, Tifosi roar at Monza, the Imola seven-time, Suzuka title clinch, F2004 at Montreal.",
    },
    {
        "id":    "SENNA TRIBUTE",
        "label": "SENNA · TRIBUTE",
        "deck":  "Ayrton Senna's legendary moments in the McLaren MP4/8 — Donington 1993 wet masterclass, Monaco 1988 pole, Suzuka 1988 title clincher, Estoril '85 first pole.",
    },
    {
        "id":    "SUPERGT",
        "label": "SUPER GT · GT500",
        "deck":  "JGTC re-creations — wet-weather discipline at Fuji.",
    },
]


# -- Catalog -----------------------------------------------------------------

CONFIGS = [
    {
        "id": "nls_24h_2026",
        "type": "RACE",
        "series": "NLS",
        "tag": "MINI 24H SIMULATION",
        "title": "MINI 24H NÜRBURGRING",
        "subtitle": "16-car SP9 PRO grid · pole start",
        "scenario": (
            "A 16-car simulation of the actual SP9 PRO entry list. You drive Max's "
            "#33 Verstappen Racing Mercedes-AMG GT3, starting on pole. The aim is "
            "to stress-test your launch, lap-1 traffic instincts and stint pace "
            "against Christopher Mies (Scherer Sport PHX) and the rest of the 2026 "
            "field — the same scenario you'll face on race week."
        ),
        "goal": "Hold P1 from green. Don't bin it on lap 1.",
        "setup": {
            "trim":     "Endurance · stint",
            "priority": "Tyre + brake life over single-lap pace",
            "key":      "60L fuel · soft front ARB · narrow ducts · ABS 7 / TC 5",
        },
        "benchmarks": {
            "refs": [
                {"label": "Note", "time": "no Max ref on 24h layout yet"},
            ],
        },
        "specs": {
            "CAR":   "MERCEDES-AMG GT3 · #3 VERSTAPPEN",
            "TRACK": "Nordschleife · Endurance Cup",
            "GRID":  "16 cars · pole start",
            "LAPS":  "2 laps · AI 86–90",
        },
        "color_a": "#0a2417",
        "color_b": "#2d5a3e",
        "track_label": "NORDSCHLEIFE",
        "launcher": "launch_24h_nurburgring_2026.cmd",
        "dashboard_rel": "telemetry_archive/dashboard.html",
        "ac_car_id": "rss_gtm_mercer_v8",
        "ac_car_skin": "M17_Verstappen_Test_33",
        "ac_track_id": "ks_nordschleife",
        "ac_track_layout": "endurance_cup",
    },
    {
        "id": "nls2_2026",
        "type": "HOTLAP",
        "series": "NLS",
        "tag": "MINI 24H POLE CHASE",
        "title": "MINI 24H POLE CHASE",
        "subtitle": "Solo lap · beat Max's time on this layout",
        "scenario": (
            "Solo against the clock on the same Mini 24H Nürburgring layout as "
            "the SP9 PRO grid race — but you have the track to yourself. "
            "Mercedes-AMG GT3, Verstappen Racing #3. Chase Max's best lap from "
            "The Rematch 24h Qualifier dual onboard, then keep going."
        ),
        "goal": "Beat Max's lap. Then keep stitching cleaner ones.",
        "setup": {
            "trim":     "Hot-lap · pole chase",
            "priority": "Max corner grip; brakes survive 8-min repeat laps",
            "key":      "Max wing (9 of 11) · open ducts (3/3) · balanced ARB · ABS 5 / TC 3",
        },
        "benchmarks": {
            "refs": [
                {"label": "Reference", "time": "Max's lap from The Rematch (24h Q dual onboard)"},
            ],
        },
        "specs": {
            "CAR":   "MERCEDES-AMG GT3 · #3 VERSTAPPEN",
            "TRACK": "Nordschleife · Endurance Cup",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0c2540",
        "color_b": "#1f4870",
        "track_label": "NORDSCHLEIFE",
        "launcher": "launch_hotlap_nls2_2026.cmd",
        "dashboard_rel": "telemetry_archive/dashboard.html",
        "ac_car_id": "rss_gtm_mercer_v8",
        "ac_car_skin": "M17_Verstappen_Test_33",
        "ac_track_id": "ks_nordschleife",
        "ac_track_layout": "endurance_cup",
    },
    {
        "id": "verstappen_1v1",
        "type": "DUEL",
        "series": "NLS",
        "type_label": "1v1 RACE",
        "tag": "NLS · 1v1 · NÜRBURGRING SHOWDOWN",
        "title": "VERSTAPPEN VS HAASE",
        "subtitle": "Mercedes-AMG #3 vs Audi R8 LMS #16 · 1 lap of the Green Hell",
        "scenario": (
            "The 2026 NLS season's defining rivalry distilled to a single lap. "
            "Mercedes-AMG Team Verstappen Racing #3 against Scherer Sport PHX Audi #16. "
            "Same Nordschleife. Two factory liveries. No traffic, no strategy, no excuses."
        ),
        "hero_blurb": (
            "NLS 2026's defining grudge match. The four-time F1 world champion against "
            "the man who has owned the Nordschleife for two decades. Same circuit. "
            "Two factory teams. One lap to settle it."
        ),
        "goal": "Beat the rival to the line. Make every overtake count.",
        "setup": {
            "trim":     "Sprint · one shot",
            "priority": "Straight-line speed, minimum fuel weight",
            "key":      "Wing 6 (low drag) · 14L fuel (one Nord lap) · TC 2 · Audi runs default",
        },
        "benchmarks": {
            "refs": [
                {"label": "Last result", "time": "P1 vs Haase · 8 May 2026"},
            ],
        },
        "specs": {
            "CAR":   "MERCEDES-AMG GT3 #3 · vs · AUDI R8 LMS #16",
            "TRACK": "Nordschleife · Endurance Cup",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · AI 100 / aggression 85",
        },
        "color_a": "#3a0608",
        "color_b": "#7a0c0e",
        "track_label": "NORDSCHLEIFE",
        "launcher": "launch_verstappen_1v1.cmd",
        "dashboard_rel": None,
        "ac_car_id": "rss_gtm_mercer_v8",
        "ac_car_skin": "2026 NLS Verstappen Racing #3",
        "ac_rival_car_id": "rss_gtm_aero_v10_evo2",
        "ac_rival_car_skin": "2025_N24H_SchererPhoenix_15",
        "ac_track_id": "ks_nordschleife",
        "ac_track_layout": "endurance_cup",
        "images": [
            "verstappen_1v1_1.png",
            "verstappen_1v1_2.png",
            "verstappen_1v1_3.png",
            "verstappen_1v1_4.png",
            "verstappen_1v1_5.png",
        ],
        "videos": [
            {"label": "VIDEO 1", "url": "https://www.youtube.com/watch?v=80Ruo--4IcQ"},
            {"label": "VIDEO 2", "url": "https://www.youtube.com/watch?v=4_SguHHLSzk"},
            {"label": "VIDEO 3", "url": "https://www.youtube.com/watch?v=7z2SPcK540I"},
        ],
        "launchers": [
            {
                "label":    "BE VERSTAPPEN",
                "logo":     "verstappenracing",
                "cmd":      "launch_verstappen_1v1.cmd",
                "ac_car_id": "rss_gtm_mercer_v8",
                "skin":     "2026 NLS Verstappen Racing #3",
                "color":    "#D40E10",
                "driver":   "MAX VERSTAPPEN",
                "number":   "3",
                "team":     "Mercedes-AMG · Verstappen Racing · Red Bull",
                "tagline":  "F1 KING · GT3 ROOKIE",
                "quote":    "Four titles, six pole records, one Nordschleife. The Eifel takes none of that into account.",
                "portrait": "verstappen_nls_portrait.png",
            },
            {
                "label":    "BE HAASE",
                "logo":     "audi",
                "cmd":      "launch_haase_1v1.cmd",
                "ac_car_id": "rss_gtm_aero_v10_evo2",
                "skin":     "2025_N24H_SchererPhoenix_15",
                "color":    "#cc0000",
                "driver":   "CHRISTOPHER HAASE",
                "number":   "16",
                "team":     "Scherer Sport PHX",
                "tagline":  "THE NORDMEISTER",
                "quote":    "He's won everything. I've won this place. Defend the Karussell. Defend the Pflanzgarten. Defend.",
                "portrait": "haase_portrait.png",
            },
        ],
    },
    {
        "id": "canada_2026",
        "type": "RACE",
        "series": "F1_2026",
        "tag": "F1 · CHARGE FROM THE BACK",
        "title": "CANADIAN GP 2026",
        "subtitle": "5-lap sprint · real 2026 F1 grid",
        "scenario": (
            "Circuit Gilles Villeneuve in a Verstappen-livery Alpine 2025 hybrid "
            "against the actual 2026 F1 field as it stands post-Miami: Antonelli, "
            "Russell, Leclerc, Norris, Hamilton, Piastri. You start at the back of "
            "the grid (no qualifying) — see how far through the field you can climb "
            "in five laps."
        ),
        "goal": "Top 5 from P19. Last attempt: P5 (▲14 positions).",
        "setup": {
            "trim":     "Default · no tuning",
            "priority": "Pure race-craft test — no setup advantage",
            "key":      "All 19 cars on AC factory trim; pace comes from racing line, not damper clicks",
        },
        "benchmarks": {
            "you_history": "dashboard/montreal/hotlap_history.json",
            "you_section": "RSS_FORMULA_HYBRID_2025_ALPINE@MONTREAL-MONTREAL_F1_2025",
            "you_label":   "Your Hotlap PB",
            "refs": [
                {"label": "Russell pole",  "time": "1:10.899"},
            ],
        },
        "specs": {
            "CAR":   "RED BULL RB21 · F1 2025",
            "TRACK": "Montreal · F1 2025 layout",
            "GRID":  "19 cars · You start P19",
            "LAPS":  "5 laps · AI 80–99",
        },
        "color_a": "#3a060f",
        "color_b": "#c8102e",
        "track_label": "MONTREAL",
        "launcher": "launch_canada_2026.cmd",
        "dashboard_rel": "dashboard/montreal/dashboard.html",
        "ac_car_id": "rss_formula_hybrid_2025_alpine",
        "ac_car_skin": "M17_RedBull_RB21_1",
        "ac_track_id": "montreal",
        "ac_track_layout": "montreal_f1_2025",
    },
    {
        "id": "hotlap_montreal",
        "type": "HOTLAP",
        "series": "F1_2026",
        "tag": "F1 POLE-CHASE HOTLAP",
        "title": "MONTREAL HOTLAP",
        "subtitle": "Chasing Russell's 1:10.899 pole",
        "scenario": (
            "Solo against the clock at Circuit Gilles Villeneuve. Russell took the "
            "2025 Canadian GP pole at 1:10.899 — that's the line you're chasing. "
            "Your PB sits at 1:16.665 (session #3, C4 mediums), +5.766 to Russell. "
            "Goal is fresh lines, not better stitching of the same ones."
        ),
        "goal": "Crack 1:15. Then 1:14. Then keep going.",
        "setup": {
            "trim":     "Low-DF · Montreal special",
            "priority": "Top speed on the straights, soft enough for the chicanes",
            "key":      "Wings 3/4 (low drag) · 20L fuel · soft tyre pressures (23/22 F/R)",
        },
        "benchmarks": {
            "you_history": "dashboard/montreal/hotlap_history.json",
            "you_section": "RSS_FORMULA_HYBRID_2025_ALPINE@MONTREAL-MONTREAL_F1_2025",
            "you_label":   "Your PB",
            "refs": [
                {"label": "Russell pole",  "time": "1:10.899"},
            ],
        },
        "specs": {
            "CAR":   "RED BULL RB21 · F1 2025",
            "TRACK": "Montreal · F1 2025 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#1c1c1c",
        "color_b": "#c8102e",
        "track_label": "MONTREAL",
        "launcher": "launch_hotlap_montreal_2026.cmd",
        "dashboard_rel": "dashboard/montreal/dashboard.html",
        "ac_car_id": "rss_formula_hybrid_2025_alpine",
        "ac_car_skin": "M17_RedBull_RB21_1",
        "ac_track_id": "montreal",
        "ac_track_layout": "montreal_f1_2025",
    },
    {
        "id": "canada_vrc",
        "type": "RACE",
        "series": "F1_2026",
        "tag": "F1 · VRC GRID · CHARGE FROM THE BACK",
        "title": "CANADIAN GP · VRC GRID",
        "subtitle": "20-car real F1 grid · charge from P20",
        "scenario": (
            "Circuit Gilles Villeneuve in the Red Bull RB21 (2025 F1) — the "
            "highest-fidelity 2025 F1 mod available, with the actual 2026 grid in "
            "their real liveries. You drive Verstappen's Red Bull RB21 against "
            "Norris, Russell, Leclerc, Hamilton, Piastri, Antonelli and the rest "
            "of the field. No qualifying — you start at the back. Five laps to "
            "carve through twenty real F1 cars."
        ),
        "goal": "Top 5 from P20. Stretch: P1 by the flag.",
        "setup": {
            "trim":     "Race · low-DF Montreal trim",
            "priority": "Top speed for DRS overtakes; stable on the chicanes",
            "key":      "Wings 5/5 · 30L fuel · F-bias 58 · soft tyres",
        },
        "specs": {
            "CAR":   "RED BULL RB21 · F1 2025",
            "TRACK": "Montreal · F1 2025 layout",
            "GRID":  "20 cars · You start P20",
            "LAPS":  "5 laps · AI 82–99",
        },
        "color_a": "#23010a",
        "color_b": "#c8102e",
        "track_label": "MONTREAL",
        "launcher": "launch_canada_vrc.cmd",
        "dashboard_rel": "dashboard/montreal/dashboard.html",
        "ac_car_id": "vrc_formula_alpha_2025_csp",
        "ac_track_id": "montreal",
        "ac_track_layout": "montreal_f1_2025",
    },
    {
        "id": "hotlap_canada_vrc",
        "type": "HOTLAP",
        "series": "F1_2026",
        "tag": "F1 · VRC POLE-CHASE HOTLAP",
        "title": "CANADA POLE CHASE · VRC",
        "subtitle": "Solo · ghost on · pole-chase",
        "scenario": (
            "Solo against the clock at Circuit Gilles Villeneuve in the VRC "
            "Formula Alpha 2025 (Pro) — same chassis as the 20-car grid race "
            "but with the track to yourself. Setup is the Montreal_Hotlap_v1 "
            "low-DF trim: 14L fuel, soft tyres, wings dropped to 4/4 for "
            "straight-line speed. Russell took the 2025 Canadian GP pole at "
            "1:10.899 — that is the line you are chasing on this car."
        ),
        "goal": "Crack 1:18. Then 1:15. Then 1:13. Pole is the long game.",
        "setup": {
            "trim":     "Hotlap · low-DF Montreal special",
            "priority": "Max top speed; soft enough for the chicanes",
            "key":      "Wings 4/4 · 14L fuel · F-bias 58 · soft tyres",
        },
        "benchmarks": {
            "you_section": "VRC_FORMULA_ALPHA_2025_CSP@MONTREAL-MONTREAL_F1_2025",
            "you_label":   "Your PB",
            "refs": [
                {"label": "Theoretical (you)",  "time": "1:18.894"},
                {"label": "Russell 2025 pole",  "time": "1:10.899"},
            ],
        },
        "specs": {
            "CAR":   "RED BULL RB21 · F1 2025",
            "TRACK": "Montreal · F1 2025 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0c1c2c",
        "color_b": "#c8102e",
        "track_label": "MONTREAL",
        "launcher": "launch_hotlap_canada_vrc.cmd",
        "dashboard_rel": "dashboard/montreal/dashboard.html",
        "ac_car_id": "vrc_formula_alpha_2025_csp",
        "ac_track_id": "montreal",
        "ac_track_layout": "montreal_f1_2025",
    },
    {
        "id": "antonelli_vs_verstappen_nord",
        "type": "DUEL",
        "series": "F1_2026",
        "type_label": "1v1 RACE",
        "tag": "F1 · 1v1 · FANTASY NORD",
        "title": "ANTONELLI vs VERSTAPPEN",
        "subtitle": "Mercedes W16 #12 vs Red Bull RB21 #1 · 1 lap of the Nord 24h",
        "scenario": (
            "F1 cars where they were never meant to run. You are Kimi Antonelli "
            "in the Mercedes W16 #12; the AI is Max Verstappen in the Red Bull "
            "RB21 #1. Same VRC Formula Alpha 2025 (Pro) chassis under both "
            "liveries — pure fantasy match-up, identical hardware, no excuses. "
            "One green-flag lap of the Nordschleife 24h 2024 layout: GP loop, "
            "Mercedes-Arena, Adenauer Forst, Karussell, Döttinger Höhe, the lot. "
            "F1 downforce on Nord camber — beat Max to the line."
        ),
        "goal": "Beat Verstappen to the line. Stay on the grey stuff.",
        "setup": {
            "trim":     "Sprint · one shot",
            "priority": "Mechanical grip on the camber + commitment on Döttinger",
            "key":      "Default Pro setup · 30L fuel · soft tyres · no ballast",
        },
        "benchmarks": {
            "refs": [
                {"label": "F1 fantasy",  "time": "no historic ref"},
            ],
        },
        "specs": {
            "CAR":   "VRC Formula Alpha 2025 (Pro) · W16 vs RB21",
            "TRACK": "Nordschleife · 24h 2024 layout",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · AI 100 / aggression 80",
        },
        "color_a": "#0a1d3d",
        "color_b": "#c8102e",
        "track_label": "NORDSCHLEIFE",
        "launcher": "launch_duel_antonelli_vs_verstappen_nord.cmd",
        "dashboard_rel": None,
        "ac_car_id":         "vrc_formula_alpha_2025_csp",
        "ac_car_skin":       "d_Mercedes_W16_12_Antonelli",
        "ac_rival_car_id":   "vrc_formula_alpha_2025_csp",
        "ac_rival_car_skin": "e_Red_Bull_RB21_1_Verstappen",
        "ac_track_id":       "ks_nordschleife",
        "ac_track_layout":   "nordschleife_24hours_2024",
        "hero_blurb": (
            "The fastest F1 cars on the planet, in the hands of the era's two "
            "best drivers, turned loose on the Green Hell. One lap. No excuses."
        ),
        "images": [
            "antonelli_vs_verstappen_nord_1.png",
            "antonelli_vs_verstappen_nord_2.png",
            "antonelli_vs_verstappen_nord_3.png",
            "antonelli_vs_verstappen_nord_4.png",
            "antonelli_vs_verstappen_nord_5.png",
        ],
        "launchers": [
            {
                "label":   "BE ANTONELLI",
                "logo":    "mercedes",
                "cmd":     "launch_duel_antonelli_vs_verstappen_nord.cmd",
                "driver":  "ANDREA KIMI ANTONELLI",
                "number":  "12",
                "team":    "Mercedes-AMG Petronas F1",
                "tagline":  "THE ROOKIE",
                "quote":    "Hold the four-time champion for one lap. The headline writes itself.",
                "portrait": "antonelli_portrait.png",
                "skin":     "d_Mercedes_W16_12_Antonelli",
                "color":    "#00D2BE",
            },
            {
                "label":   "BE VERSTAPPEN",
                "logo":    "redbull",
                "cmd":     "launch_duel_verstappen_vs_antonelli_nord.cmd",
                "driver":  "MAX VERSTAPPEN",
                "number":  "1",
                "team":    "Oracle Red Bull Racing",
                "tagline":  "THE CHAMPION",
                "quote":    "Anything less than P1 needs explaining. The Karussell doesn't care who you are.",
                "portrait": "verstappen_portrait.png",
                "skin":     "e_Red_Bull_RB21_1_Verstappen",
                "color":    "#FFD700",
            },
        ],
    },
    # ============================================================
    # F1 2008 — Hamilton's title-decider season at Interlagos.
    # 11 teams installed, full grid available.
    # ============================================================
    {
        "id": "f1_2008_brazil_grid",
        "type": "RACE",
        "series": "F1_2008",
        "tag": "TITLE DECIDER · 11-TEAM GRID",
        "title": "INTERLAGOS 2008",
        "subtitle": "Real 2008 grid · 5-lap sprint",
        "scenario": (
            "2 November 2008, the season finale. Massa needed to win and have "
            "Hamilton finish lower than P5. Hamilton was on track to fifth — "
            "until rain hit. He overtook Glock at turn 12 on the very last lap "
            "to clinch the title by one point. You drive Hamilton's #22 "
            "MP4-23 against the actual 11-team 2008 field: Ferrari, McLaren, "
            "BMW Sauber, Renault, Toyota, Williams, Honda, Red Bull, Toro "
            "Rosso, Force India and Super Aguri. Start at the back — climb."
        ),
        "goal": "Top 5 from the back. Stretch: P1, the Hamilton way.",
        "setup": {
            "trim":     "Race · low-DF Brazil trim",
            "priority": "Top speed for the long uphill drag; Senna S commitment",
            "key":      "Wing 5/5 · 30 L fuel · soft springs for the bumps",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Massa pole 2008",       "time": "1:12.368"},
                {"label": "Hamilton race fastest", "time": "1:13.736"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4-23 · Hamilton #22",
            "TRACK": "Interlagos · GP",
            "GRID":  "20 cars · You start P20",
            "LAPS":  "5 laps · AI 80–99",
        },
        "color_a": "#1c0c12",
        "color_b": "#c8102e",
        "track_label": "INTERLAGOS",
        "launcher": "launch_f1_2008_brazil.cmd",
        "dashboard_rel": None,
        "ac_car_id":      "cim_2008_mclaren",
        "ac_car_skin":    "22_Hamilton",
        "ac_track_id":    "vhe_interlagos",
        "ac_track_layout": "gp",
    },
    {
        "id": "hotlap_montreal_f2004",
        "type": "HOTLAP",
        "series": "SCHUMACHER",
        "tag": "CANADIAN GP · F2004 V10",
        "title": "MONTREAL · F2004",
        "subtitle": "Ferrari F2004 · 2004 championship V10",
        "scenario": (
            "Solo against the clock at Circuit Gilles Villeneuve in the "
            "Ferrari F2004 — Michael Schumacher's 2004 championship-winning "
            "V10. Pure analog F1: no hybrid, no DRS, just 19,000 RPM and "
            "you. First session 2026-05-09 set a 1:18.810 (theoretical "
            "1:18.531) over 4 laps, default setup."
        ),
        "goal": "Crack 1:18. Then 1:17. The V10 still has more in it.",
        "benchmarks": {
            "you_section": "KS_FERRARI_F2004@MONTREAL-MONTREAL_F1_2025",
            "you_label":   "Your PB",
            "refs": [
                {"label": "Theoretical (you)",  "time": "1:18.531"},
            ],
        },
        "specs": {
            "CAR":   "FERRARI F2004 · 2004 V10",
            "TRACK": "Montreal · F1 2025 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "MONTREAL",
        "launcher": "launch_hotlap_montreal_f2004.cmd",
        "dashboard_rel": "dashboard/montreal/dashboard.html",
        "ac_car_id": "ks_ferrari_f2004",
        "ac_track_id": "montreal",
        "ac_track_layout": "montreal_f1_2025",
    },
    {
        "id": "hotlap_spa_1991_debut",
        "type": "HOTLAP",
        "series": "SCHUMACHER",
        "tag": "1991 BELGIAN GP · DEBUT",
        "title": "SPA · 1991 DEBUT",
        "subtitle": "Jordan 191 #32 · Schumacher's F1 debut",
        "scenario": (
            "Spa-Francorchamps in the Jordan 191 #32 livery — Schumacher's "
            "actual F1 debut car at the 1991 Belgian GP. He qualified P7 on "
            "his very first F1 weekend, then retired lap 1 with a clutch "
            "failure. Benetton signed him before the next race. This is "
            "where the legend started."
        ),
        "goal": "Lap clean. Crack 2:00. Then 1:55. Honour the Eau Rouge.",
        "benchmarks": {
            "you_section": "VRC_1991_JORDAN_191@SPA-LAYOUT_F1_2020",
            "you_label":   "Your PB",
            "refs": [],
        },
        "specs": {
            "CAR":   "JORDAN 191 · #32 SCHUMACHER",
            "TRACK": "Spa-Francorchamps · F1 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0a2014",
        "color_b": "#f4d300",
        "track_label": "SPA",
        "launcher": "launch_hotlap_spa_1991_debut.cmd",
        "ac_car_id": "vrc_1991_jordan_191",
        "ac_track_id": "spa",
        "ac_track_layout": "layout_f1_2020",
    },
    {
        "id": "hotlap_monza_schumacher",
        "type": "HOTLAP",
        "series": "SCHUMACHER",
        "tag": "ITALIAN GP · TIFOSI MOMENT",
        "title": "MONZA · TIFOSI",
        "subtitle": "Ferrari F2001 · the Tifosi's roar",
        "scenario": (
            "Monza in the Ferrari F2001 with the special #3 Schumacher Monza "
            "livery — the V10 era at full song. The Italian GP was Schumacher's "
            "home race for the Tifosi, and Monza's long straights and Parabolica "
            "reward the F2001's engine and brakes equally. No traction control "
            "switching, no DRS. Just commitment."
        ),
        "goal": "Crack 1:25 in the F2001. Then 1:23. Then unleash the V10.",
        "benchmarks": {
            "you_section": "FERRARI_F2001@MONZA-MONZA_F1_2025",
            "you_label":   "Your PB",
            "refs": [],
        },
        "specs": {
            "CAR":   "FERRARI F2001 · #3 SCHUMACHER MONZA",
            "TRACK": "Monza · F1 2025 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "MONZA",
        "launcher": "launch_hotlap_monza_schumacher.cmd",
        "ac_car_id": "ferrari_f2001",
        "ac_track_id": "monza",
        "ac_track_layout": "monza_f1_2025",
    },
    {
        "id": "hotlap_imola_schumacher",
        "type": "HOTLAP",
        "series": "SCHUMACHER",
        "tag": "SAN MARINO GP · 7 WINS",
        "title": "IMOLA · 7-TIME KING",
        "subtitle": "Ferrari F2001 · Schumacher's most-won track",
        "scenario": (
            "Imola in the Ferrari F2001. Schumacher won at Imola SEVEN times "
            "in his career, more than at any other circuit. Tamburello, "
            "Villeneuve, the Variante Alta — every corner carries Senna's "
            "ghost and Schumacher's victories. The F2001 V10 is the soundtrack."
        ),
        "goal": "Crack 1:23 in the F2001. Then 1:21. Honour the seven wins.",
        "benchmarks": {
            "you_section": "FERRARI_F2001@IMOLA-IMOLA_F1_2022",
            "you_label":   "Your PB",
            "refs": [],
        },
        "specs": {
            "CAR":   "FERRARI F2001 · #1 SCHUMACHER",
            "TRACK": "Imola · F1 2022 layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "IMOLA",
        "launcher": "launch_hotlap_imola_schumacher.cmd",
        "ac_car_id": "ferrari_f2001",
        "ac_track_id": "imola",
        "ac_track_layout": "imola_f1_2022",
    },
    {
        "id": "hotlap_suzuka_schumacher",
        "type": "HOTLAP",
        "series": "SCHUMACHER",
        "tag": "JAPANESE GP · TITLE CLINCH",
        "title": "SUZUKA · 2001 TITLE",
        "subtitle": "Ferrari F2001 · 4th championship clinched",
        "scenario": (
            "Suzuka in the Ferrari F2001. The 2001 Japanese GP was where "
            "Schumacher mathematically clinched his 4th World Championship "
            "in dominant style — Ferrari's run was starting to feel "
            "inevitable. The figure-eight layout rewards precision through "
            "130R and the Esses; the F2001 V10 makes it sing."
        ),
        "goal": "Crack 1:35 in the F2001. Then 1:32. Then chase Senna.",
        "benchmarks": {
            "you_section": "FERRARI_F2001@RT_SUZUKA-SUZUKAGP",
            "you_label":   "Your PB",
            "refs": [],
        },
        "specs": {
            "CAR":   "FERRARI F2001 · #1 SCHUMACHER",
            "TRACK": "Suzuka · GP layout",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "SUZUKA",
        "launcher": "launch_hotlap_suzuka_schumacher.cmd",
        "ac_car_id": "ferrari_f2001",
        "ac_track_id": "rt_suzuka",
        "ac_track_layout": "suzukagp",
    },
    {
        "id": "duel_spa_1993_schumacher_berger",
        "type": "DUEL",
        "type_label": "1v1 RACE",
        "series": "SCHUMACHER",
        "tag": "1v1 · 1993 SEASON",
        "title": "BENETTON vs FERRARI · '93",
        "subtitle": "Schumacher's Benetton B193 vs Berger's Ferrari",
        "scenario": (
            "Schumacher's first full F1 season at Benetton. Spa's Eau Rouge "
            "and Pouhon decide who carries momentum — the Benetton B193 "
            "(Ford V8) against Berger's Ferrari F93A (V12). One lap to "
            "settle who owns Belgium."
        ),
        "goal": "Beat Berger's Ferrari to La Source. Don't lose it at Eau Rouge.",
        "specs": {
            "CAR":   "BENETTON B193 · #5 SCHUMACHER",
            "TRACK": "Spa · F1 2025 layout",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · cross-team duel",
        },
        "color_a": "#0a2014",
        "color_b": "#f4d300",
        "track_label": "SPA",
        "launcher": "launch_duel_spa_1993.cmd",
        "ac_car_id": "f1_1993_benetton",
        "ac_track_id": "spa",
        "ac_track_layout": "layout_f1_2020",
    },
    {
        "id": "duel_imola_f2001_teammates",
        "type": "DUEL",
        "type_label": "1v1 RACE",
        "series": "SCHUMACHER",
        "tag": "1v1 · INTRA-FERRARI 2001",
        "title": "IMOLA · TEAMMATE DUEL",
        "subtitle": "Schumacher F2001 #1 vs Barichello F2001 #2",
        "scenario": (
            "The 2002 San Marino GP famously ended with the Ferrari one-two "
            "and a scripted finish that earned the team a fine. This is the "
            "inverse: no team orders, no codes — Schumacher #1 against "
            "Barichello #2 in matched F2001s, one lap, fastest car wins."
        ),
        "goal": "Beat Barichello to the line. Imola decides at Tamburello.",
        "specs": {
            "CAR":   "FERRARI F2001 · #1 SCHUMACHER",
            "TRACK": "Imola · F1 2022 layout",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · teammate duel",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "IMOLA",
        "launcher": "launch_duel_imola_f2001.cmd",
        "ac_car_id": "ferrari_f2001",
        "ac_track_id": "imola",
        "ac_track_layout": "imola_f1_2022",
    },
    {
        "id": "race_1993_spa_grid",
        "type": "RACE",
        "series": "SCHUMACHER",
        "tag": "5-LAP · 1993 SEASON GRID",
        "title": "1993 GRID · SPA",
        "subtitle": "6-car 1993 F1 field · Schumacher's first full season",
        "scenario": (
            "The full 1993 F1 grid as installed: Schumacher / Patrese "
            "(Benetton), Berger / Alesi (Ferrari), Barrichello / Boutsen "
            "(Jordan). Six cars, five laps at Spa-Francorchamps — "
            "Schumacher's first full F1 season compressed into a Sunday "
            "afternoon. No qualifying, you start P6 and carve through the "
            "period grid."
        ),
        "goal": "Top 3 from P6. Stretch: P1 by the flag. Eau Rouge in 4th gear.",
        "specs": {
            "CAR":   "BENETTON B193 · #5 SCHUMACHER",
            "TRACK": "Spa · F1 2025 layout",
            "GRID":  "6 cars · cross-team 1993 grid",
            "LAPS":  "5 laps · charge from P6",
        },
        "color_a": "#0a2014",
        "color_b": "#f4d300",
        "track_label": "SPA",
        "launcher": "launch_race_1993_spa.cmd",
        "ac_car_id": "f1_1993_benetton",
        "ac_track_id": "spa",
        "ac_track_layout": "layout_f1_2020",
    },
    {
        "id": "race_monza_f2001",
        "type": "RACE",
        "series": "SCHUMACHER",
        "tag": "5-LAP · TIFOSI MOMENT",
        "title": "MONZA · F2001 TIFOSI",
        "subtitle": "Ferrari F2001 4-car battle at Monza",
        "scenario": (
            "Monza in matched Ferrari F2001s — the 2001 Italian GP weekend "
            "framed as a sprint. Schumacher and Barrichello in their Monza-"
            "special liveries plus two more F2001s for chaos in Lesmo. "
            "Five laps, no qualifying, starting from the back. The Tifosi "
            "don't care if you're Schumacher — beat the field or hear about it."
        ),
        "goal": "Top 2 from P4. The Tifosi expect a #1 finish.",
        "specs": {
            "CAR":   "FERRARI F2001 · #3 SCHUMACHER MONZA",
            "TRACK": "Monza · F1 2025 layout",
            "GRID":  "4 cars · all F2001",
            "LAPS":  "5 laps · charge from P4",
        },
        "color_a": "#3a0608",
        "color_b": "#c8102e",
        "track_label": "MONZA",
        "launcher": "launch_race_monza_f2001.cmd",
        "ac_car_id": "ferrari_f2001",
        "ac_track_id": "monza",
        "ac_track_layout": "monza_f1_2025",
    },
    {
        "id": "hotlap_supergt_fuji",
        "type": "DUEL",
        "series": "SUPERGT",
        "type_label": "1v1 RACE",
        "tag": "1v1 WET DRILL",
        "title": "SUPER GT FUJI · WET",
        "subtitle": "Verstappen-Miyake re-creation",
        "scenario": (
            "A re-creation of Max's March 2026 Red Bull promo test at Fuji in heavy "
            "rain. Nissan Z NISMO GT500 on Bridgestone wets, Pure LCS storm, JST "
            "sun. Atsushi Miyake (Kondo Racing) set the pro benchmark at 1:44.075. "
            "Max went 1:42.290 on his second lap. Wet-weather discipline at Fuji."
        ),
        "goal": "Crack Miyake's 1:44.075. Stretch: Max's 1:42.290.",
        "setup": {
            "trim":     "Default + Bridgestone wets",
            "priority": "Throttle discipline on a soaked track",
            "key":      "GT500 stock trim · wet tyres selected in the pit-tyre menu before driving",
        },
        "benchmarks": {
            "you_label":   "Your PB",
            "refs": [
                {"label": "Miyake (Pro)",  "time": "1:44.075"},
                {"label": "Max",           "time": "1:42.290"},
            ],
        },
        "specs": {
            "CAR":   "NISSAN Z NISMO GT500",
            "TRACK": "Fuji Speedway 2017",
            "GRID":  "Solo · ghost on · wet",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0a1d3d",
        "color_b": "#1f3a5e",
        "track_label": "FUJI · WET",
        "launcher": "launch_hotlap_super_gt_fuji_chase.cmd",
        "dashboard_rel": None,
        "ac_car_id": "urd_jt5_shiro_2022",
        "ac_track_id": "fujispeedway_2017",
        "images": [
            "hotlap_supergt_fuji_1.png",
            "hotlap_supergt_fuji_2.png",
            "hotlap_supergt_fuji_3.png",
        ],
        "videos": [
            {"label": "WATCH", "url": "https://www.youtube.com/watch?v=h8hG4_B-ACY"},
        ],
    },
    # ============================================================
    # SENNA TRIBUTE — four hotlap chases at Senna's iconic venues,
    # using the exact Senna-named skins Pablo has installed.
    # Lap times sourced from FIA / official records.
    # ============================================================
    {
        "id": "senna_donington_1993",
        "type": "HOTLAP",
        "series": "SENNA TRIBUTE",
        "tag": "THE LAP OF GOD",
        "title": "DONINGTON 1993",
        "subtitle": "MP4/8 · the wet-weather masterclass",
        "scenario": (
            "11 April 1993, European GP. Senna's McLaren MP4/8 in soaking-wet "
            "Donington. On the opening lap alone he passed Schumacher, Wendlinger, "
            "Hill, and Prost — fifth on the grid to first by Redgate. He set "
            "fastest race lap 1:18.029 in mixed conditions. The lap that defines "
            "wet-weather mastery."
        ),
        "goal": "Crack 1:20 in the wet. Then chase Senna's 1:18.029.",
        "setup": {
            "trim":     "Wet · race-car defaults",
            "priority": "Throttle and brake patience over outright pace",
            "key":      "Wets selected · 30 L fuel · soft springs to ride the kerbs",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna race fastest", "time": "1:18.029"},
                {"label": "Prost pole (dry)",   "time": "1:10.458"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Donington Park · GP layout",
            "GRID":  "Solo · ghost on · wet",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#2c0a14",
        "color_b": "#a40000",
        "track_label": "DONINGTON",
        "launcher": "launch_hotlap_senna_donington.cmd",
        "dashboard_rel": None,
        "ac_car_id":    "asr_1993_mclaren_mp4-8",
        "ac_car_skin":  "8_senna_r1_r2_r4_r5_r6_r7",
        "ac_track_id":  "doningtonpark2018",
        "ac_track_layout": "gp",
    },
    {
        "id": "senna_suzuka_1988",
        "type": "HOTLAP",
        "series": "SENNA TRIBUTE",
        "tag": "TITLE-CLINCHER POLE",
        "title": "SUZUKA 1988",
        "subtitle": "MP4/4 · the championship lap",
        "scenario": (
            "30 October 1988, Japanese GP. Senna took pole at 1:41.853 in the "
            "all-conquering McLaren MP4/4. He stalled at the lights, dropped to "
            "P14, then drove through the field to win — clinching his first "
            "World Championship in the country he'd come to call a second home."
        ),
        "goal": "Beat 1:43. Then build to Senna's 1:41.853.",
        "setup": {
            "trim":     "Hot-lap · qualifying trim",
            "priority": "Mechanical grip through 130R and Spoon; brake stability into the chicane",
            "key":      "Low fuel · soft tyres · 1.5-bar boost · max-attack engine map",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna pole",         "time": "1:41.853"},
                {"label": "Prost (sister car)", "time": "1:42.177"},
                {"label": "Race fastest",       "time": "1:46.326"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Suzuka · GP",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#1c0c0c",
        "color_b": "#c8102e",
        "track_label": "SUZUKA",
        "launcher": "launch_hotlap_senna_suzuka.cmd",
        "dashboard_rel": None,
        "ac_car_id":    "asr_1993_mclaren_mp4-8",
        "ac_car_skin":  "12_Senna_R08",
        "ac_track_id":  "rt_suzuka",
        "ac_track_layout": "suzukagp",
    },
    {
        "id": "senna_monaco_1988",
        "type": "HOTLAP",
        "series": "SENNA TRIBUTE",
        "tag": "1.4 SECONDS OVER PROST",
        "title": "MONACO 1988",
        "subtitle": "MP4/4 · the qualifying lap nobody understood",
        "scenario": (
            "14 May 1988, Monaco qualifying. Same car, same tyres, same fuel — "
            "Senna 1:23.998, Prost 1:25.425. A 1.427-second margin between "
            "teammates that Senna himself later described as drifting outside "
            "his conscious mind. Pole, but the race ended in the wall on lap 67."
        ),
        "goal": "Crack 1:30 around the houses. Senna's 1:23.998 is the line.",
        "setup": {
            "trim":     "Monaco · max downforce",
            "priority": "Confidence through Casino, Tabac, swimming pool",
            "key":      "Wing 11/11 · soft tyres · short gear · fuel for 5 laps only",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna pole",  "time": "1:23.998"},
                {"label": "Prost (P2)",  "time": "1:25.425"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Monaco · F1 2025 layout (closest to '88 circuit)",
            "GRID":  "Solo · ghost on",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0a1530",
        "color_b": "#c8102e",
        "track_label": "MONACO",
        "launcher": "launch_hotlap_senna_monaco.cmd",
        "dashboard_rel": None,
        "ac_car_id":    "asr_1993_mclaren_mp4-8",
        "ac_car_skin":  "12_Senna_R02",
        "ac_track_id":  "monaco_2020",
        "ac_track_layout": "monaco_f1_2025",
    },
    {
        "id": "senna_estoril_1985",
        "type": "HOTLAP",
        "series": "SENNA TRIBUTE",
        "tag": "FIRST WIN · MONSOON",
        "title": "ESTORIL 1985",
        "subtitle": "Lotus turbo · the breakthrough",
        "scenario": (
            "21 April 1985, Portuguese GP. Senna's first F1 win, and one of the "
            "most dominant wet drives in F1 history — 1m02.978s ahead of "
            "Alboreto in monsoon conditions. He drove the Lotus-Renault 97T that "
            "weekend; you'll be in its '86 sister, the 98T (same Renault turbo "
            "formula, near-identical cockpit and feel)."
        ),
        "goal": "Land a clean lap in the rain. Then chase Senna's race pace.",
        "setup": {
            "trim":     "Wet · turbo era",
            "priority": "Throttle modulation; turbos punish lift-and-coast",
            "key":      "Wets · 40 L fuel · medium boost (the 1985 turbos ran 4-5 bar in qualy)",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna pole (dry)",       "time": "1:21.007"},
                {"label": "Senna fastest race lap", "time": "1:23.226"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Estoril",
            "GRID":  "Solo · ghost on · wet",
            "LAPS":  "Open · hotlap mode",
        },
        "color_a": "#0a2a14",
        "color_b": "#1d6e3f",
        "track_label": "ESTORIL",
        "launcher": "launch_hotlap_senna_estoril.cmd",
        "dashboard_rel": None,
        "ac_car_id":    "asr_1993_mclaren_mp4-8",
        "ac_track_id":  "estoril",
    },
    # ============================================================
    # SENNA TRIBUTE — 1 VS 1 duels.
    # Player drives Senna; AI rival drives the historical opponent
    # in their actual livery (both skins installed).
    # ============================================================
    {
        "id": "senna_vs_prost_monaco_1988",
        "type": "DUEL",
        "type_label": "1 vs 1",
        "series": "SENNA TRIBUTE",
        "tag": "TEAMMATES · POLE GAP",
        "title": "SENNA VS PROST · MONACO '88",
        "subtitle": "Same car. 1.4 seconds apart.",
        "scenario": (
            "Monaco qualifying, 1988. McLaren-Honda MP4/4 — same chassis, same "
            "Honda turbo, same Goodyears, same fuel load. Senna 1:23.998. Prost "
            "1:25.425. Senna later said he was 'driving outside himself, like in "
            "a different dimension.' Run a head-to-head qualifying drill against "
            "your teammate, on the streets where he found that other place."
        ),
        "goal": "Out-qualify Prost. The 1.4 s reference is just a milestone.",
        "setup": {
            "trim":     "Monaco · max downforce · qualifying trim",
            "priority": "Confidence through Casino, Tabac, swimming pool",
            "key":      "Wing 11/11 · low fuel · soft tyres · max-attack engine map",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna pole",  "time": "1:23.998"},
                {"label": "Prost (P2)",  "time": "1:25.425"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Monaco · F1 2025 layout",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · Prost AI calibrated",
        },
        "color_a": "#0a1530",
        "color_b": "#c8102e",
        "track_label": "MONACO",
        "launcher": "launch_duel_senna_vs_prost_monaco.cmd",
        "dashboard_rel": None,
        "ac_car_id":         "asr_1993_mclaren_mp4-8",
        "ac_car_skin":       "12_Senna_R02",
        "ac_rival_car_id":   "asr_1993_mclaren_mp4-8",
        "ac_rival_car_skin": "11_Prost_R02",
        "ac_track_id":       "monaco_2020",
        "ac_track_layout":   "monaco_f1_2025",
    },
    {
        "id": "senna_vs_prost_suzuka_1988",
        "type": "DUEL",
        "type_label": "1 vs 1",
        "series": "SENNA TRIBUTE",
        "tag": "CHAMPIONSHIP DECIDER",
        "title": "SENNA VS PROST · SUZUKA '88",
        "subtitle": "Title race. 1 lap. Same MP4/4.",
        "scenario": (
            "Round 15 of 16, Japanese GP. Prost leads the championship by 6 "
            "points; Senna needs the win. He took pole 1:41.853. Real race: "
            "Senna stalled at lights, dropped to P14, drove through 13 cars, "
            "won, took the title. Re-create the 1-on-1 fight for that title "
            "in a single Suzuka lap — same car as Prost, no team orders."
        ),
        "goal": "Beat Prost on track. Take the imaginary title.",
        "setup": {
            "trim":     "Hot-lap · qualifying trim",
            "priority": "Mechanical grip through 130R + Spoon; brake stability into the chicane",
            "key":      "Low fuel · soft tyres · 1.5-bar boost · max-attack engine map",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna pole",         "time": "1:41.853"},
                {"label": "Prost (sister car)", "time": "1:42.177"},
                {"label": "Race fastest",       "time": "1:46.326"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Suzuka · GP",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · Prost AI calibrated",
        },
        "color_a": "#1c0c0c",
        "color_b": "#c8102e",
        "track_label": "SUZUKA",
        "launcher": "launch_duel_senna_vs_prost_suzuka.cmd",
        "dashboard_rel": None,
        "ac_car_id":         "asr_1993_mclaren_mp4-8",
        "ac_car_skin":       "12_Senna_R08",
        "ac_rival_car_id":   "asr_1993_mclaren_mp4-8",
        "ac_rival_car_skin": "11_Prost_R08",
        "ac_track_id":       "rt_suzuka",
        "ac_track_layout":   "suzukagp",
    },
    {
        "id": "senna_vs_schumacher_donington_1993",
        "type": "DUEL",
        "type_label": "1 vs 1",
        "series": "SENNA TRIBUTE",
        "tag": "WET · LAP-1 ATTACK",
        "title": "SENNA VS SCHUMI · DONINGTON '93",
        "subtitle": "MP4/8 vs Benetton B193. Soaking wet.",
        "scenario": (
            "11 April 1993, European GP, Donington. Schumacher started P3, Senna "
            "P4 — both behind the Williams pair. On lap 1 in pouring rain, Senna "
            "passed Schumacher into Redgate, then Wendlinger, Hill, and Prost — "
            "P5 to P1 in one lap. Recreate the duel: your MP4/8 against "
            "Schumacher's Benetton B193, lap 1 only, full wet."
        ),
        "goal": "Pass Schumacher into Redgate. Hold him off through Craner Curves.",
        "setup": {
            "trim":     "Wet · race-car defaults",
            "priority": "Throttle and brake patience; the MP4/8 active suspension is your edge",
            "key":      "Wets · 30 L fuel · soft springs to ride the kerbs",
        },
        "benchmarks": {
            "you_label": "Your PB",
            "refs": [
                {"label": "Senna race fastest (wet)", "time": "1:18.029"},
                {"label": "Prost pole (dry)",         "time": "1:10.458"},
            ],
        },
        "specs": {
            "CAR":   "McLaren MP4/8 · Senna #8",
            "TRACK": "Donington Park · GP layout",
            "GRID":  "2 cars · head-to-head · wet",
            "LAPS":  "1 lap · Schumacher AI calibrated",
        },
        "color_a": "#2c0a14",
        "color_b": "#a40000",
        "track_label": "DONINGTON",
        "launcher": "launch_duel_senna_vs_schumacher_donington.cmd",
        "dashboard_rel": None,
        "ac_car_id":         "asr_1993_mclaren_mp4-8",
        "ac_car_skin":       "8_senna_r1_r2_r4_r5_r6_r7",
        "ac_rival_car_id":   "f1_1993_benetton",
        "ac_rival_car_skin": "Schumacher",
        "ac_track_id":       "doningtonpark2018",
        "ac_track_layout":   "gp",
    },
]


# -- Render ------------------------------------------------------------------

CSS = """
:root{
  /* Surface scale — warm off-white paper, not pure gray */
  --paper:#faf9f6;
  --surface:#ffffff;
  /* Ink scale — slate-tinted neutrals, easier on the eyes than pure black.
     Body copy uses --ink-2 for AAA contrast on white (12.6:1). */
  --ink:#0f172a;
  --ink-2:#1f2937;
  --ink-3:#475569;
  --ink-4:#94a3b8;
  --border:#e2e8f0;
  --rule:rgba(15,23,42,0.10);
  --rule-hair:rgba(15,23,42,0.06);
  /* Accent — softened red-600 for chips/borders, full Verstappen red kept
     only on the primary LAUNCH CTA so it stays the brightest pixel. */
  --accent:#dc2626;
  --accent-strong:#b91c1c;
  --max:#D40E10;
  --gold:#fde68a;        /* warm yellow, no vibration */
  --gold-rim:#ca8a04;
  --green:#16a34a;
  /* Type — Big Shoulders only on display titles, Inter on everything else
     for legibility at small sizes. JetBrains Mono on tabular numbers. */
  --display:'Big Shoulders Display',sans-serif;
  --body:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono',monospace;
}
*{box-sizing:border-box}
html{background:var(--paper)}
body{margin:0;background:var(--paper);color:var(--ink-2);font:15px/1.55 var(--body);background-image:radial-gradient(circle at 1px 1px,rgba(15,23,42,0.04) 1px,transparent 0);background-size:24px 24px;padding:0;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased}

/* Ticker */
.ticker{background:var(--ink);color:#fff;font:600 11px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;padding:10px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid var(--max);position:relative;overflow:hidden}
.ticker::before{content:"";position:absolute;top:0;bottom:0;right:-2px;width:220px;background:repeating-linear-gradient(90deg,var(--max) 0,var(--max) 12px,var(--ink) 12px,var(--ink) 24px);opacity:.95}
.ticker-l,.ticker-r{position:relative;z-index:1}
.ticker-r{background:var(--ink);padding:6px 12px;margin-right:220px}

/* Hero — compact band */
.hero{padding:28px 24px 22px;border-bottom:2px solid var(--ink);position:relative;display:grid;grid-template-columns:2fr 1fr;gap:32px;align-items:end;max-width:1280px;margin:0 auto}
.hero::after{content:"";position:absolute;left:0;right:0;bottom:-2px;height:4px;background:repeating-linear-gradient(90deg,var(--ink) 0,var(--ink) 16px,var(--max) 16px,var(--max) 20px,var(--ink) 20px,var(--ink) 36px,var(--paper) 36px,var(--paper) 40px)}
.hero-kicker{font:600 10px/1.2 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-3);margin-bottom:10px}
.hero-kicker .pos{display:inline-block;background:var(--ink);color:#fff;padding:3px 7px 2px;margin-right:8px;letter-spacing:0.8px;font-weight:700}
.hero-title{font:900 60px/0.9 var(--display);letter-spacing:-1.2px;text-transform:uppercase;color:var(--ink);margin:0;font-stretch:condensed}
.hero-title .accent{color:var(--max)}
.hero-sub{font:500 14px/1.4 var(--body);color:var(--ink-3);margin:10px 0 14px;letter-spacing:0}
.hero-strip{display:inline-flex;gap:0;font:600 10px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;color:var(--ink);border:1.5px solid var(--ink);background:#fff;border-radius:2px;overflow:hidden}
.hero-strip span{padding:7px 11px;border-right:1.5px solid var(--ink)}
.hero-strip span:last-child{border-right:0}
.hero-strip .countdown{background:var(--gold)}
.hero-strip .live{background:var(--max);color:#fff}

.hero-r{border-left:2px solid var(--ink);padding-left:24px;position:relative}
.hero-r::before{content:"LAUNCH BAY";position:absolute;left:24px;top:-18px;font:700 9.5px/1 var(--body);letter-spacing:1.8px;color:var(--paper);background:var(--ink);padding:4px 9px}
.hero-count{font:800 64px/0.85 var(--mono);font-variant-numeric:tabular-nums;color:var(--ink);letter-spacing:-3px;margin:0}
.hero-count-lbl{font:600 10px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-3);margin:6px 0 0}
.hero-count-meta{font:500 11px/1.4 var(--body);letter-spacing:0.4px;color:var(--ink-3);margin-top:10px;border-top:1px solid var(--rule-hair);padding-top:8px}
.hero-count-meta strong{color:var(--ink);font-weight:700}

/* ====== HOME HERO V2 — full-bleed cinematic pit-wall ====== */
.bighero{position:relative;width:100%;min-height:600px;background:#000;color:#fff;overflow:hidden;border-bottom:3px solid var(--max);isolation:isolate}
.bh-bg{position:absolute;inset:0;width:100%;height:100%;z-index:1}
.bh-bg .carousel-slide{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity 1.1s ease-in-out;transform:scale(1.06);animation:bh-kenburns 18s ease-in-out infinite alternate}
.bh-bg .carousel-slide.is-active{opacity:1}
@keyframes bh-kenburns{0%{transform:scale(1.04) translate3d(0,0,0)}100%{transform:scale(1.12) translate3d(-1.5%,-1%,0)}}
.bh-overlay{position:absolute;inset:0;z-index:2;pointer-events:none;background:
  radial-gradient(ellipse at 18% 38%,rgba(0,0,0,0.15) 0%,rgba(0,0,0,0.78) 70%),
  linear-gradient(180deg,rgba(0,0,0,0.55) 0%,rgba(0,0,0,0.22) 28%,rgba(0,0,0,0.55) 72%,rgba(0,0,0,0.96) 100%),
  linear-gradient(90deg,rgba(0,0,0,0.55) 0%,rgba(0,0,0,0) 60%)}
.bh-overlay::after{content:"";position:absolute;inset:0;background-image:radial-gradient(circle at 1px 1px,rgba(255,255,255,0.05) 1px,transparent 0);background-size:22px 22px;opacity:0.55;mix-blend-mode:overlay}
.bh-grain{position:absolute;inset:0;z-index:3;pointer-events:none;opacity:0.16;mix-blend-mode:overlay;background:
  repeating-linear-gradient(0deg,rgba(255,255,255,0.06) 0,rgba(255,255,255,0.06) 1px,transparent 1px,transparent 3px)}
.bh-stripe{position:absolute;left:0;right:0;bottom:0;z-index:4;height:6px;background:repeating-linear-gradient(90deg,var(--max) 0,var(--max) 22px,#0f172a 22px,#0f172a 44px,#fff 44px,#fff 48px,#0f172a 48px,#0f172a 70px)}

.bh-wrap{position:relative;z-index:5;max-width:1280px;margin:0 auto;padding:48px 28px 28px;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);column-gap:48px;align-items:end;min-height:600px}
@media (max-width:980px){ .bh-wrap{grid-template-columns:1fr;padding:40px 22px 26px;min-height:auto;row-gap:30px} }

/* LEFT — pitch */
.bh-l{display:flex;flex-direction:column;gap:20px;min-width:0}
.bh-tag{align-self:flex-start;display:inline-flex;align-items:center;gap:9px;font:900 11px/1 var(--body);letter-spacing:3.6px;text-transform:uppercase;color:#fff;background:var(--max);padding:9px 13px 8px;border:1px solid #fff;box-shadow:0 4px 14px rgba(212,14,16,0.45);border-radius:2px}
.bh-tag::before{content:"";width:7px;height:7px;border-radius:50%;background:#fff;box-shadow:0 0 0 3px rgba(255,255,255,0.18);animation:bh-blink 1.4s ease-in-out infinite}
@keyframes bh-blink{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.55;transform:scale(0.85)}}
.bh-bib{display:inline-flex;gap:10px;align-items:center;font:700 10.5px/1 var(--body);letter-spacing:1.6px;text-transform:uppercase;color:rgba(255,255,255,0.78);margin-bottom:-2px}
.bh-bib .bh-num{font:900 12px/1 var(--display);color:#fff;background:rgba(255,255,255,0.10);border:1px solid rgba(255,255,255,0.30);padding:5px 8px 4px;letter-spacing:1.4px;border-radius:2px}
.bh-bib .bh-rule{flex:0 0 36px;height:1px;background:rgba(255,255,255,0.30)}
.bh-title{margin:0;font:900 92px/0.86 var(--display);letter-spacing:-1.5px;text-transform:uppercase;color:#fff;text-shadow:0 6px 28px rgba(0,0,0,0.55);font-stretch:condensed}
.bh-title .ln{display:block}
.bh-title .accent{color:var(--max);text-shadow:0 6px 18px rgba(212,14,16,0.45),0 0 1px rgba(255,255,255,0.25)}
.bh-title .underline{position:relative;display:inline-block}
.bh-title .underline::after{content:"";position:absolute;left:0;right:0;bottom:-6px;height:5px;background:var(--max)}
@media (max-width:1180px){ .bh-title{font-size:72px} }
@media (max-width:760px){ .bh-title{font-size:46px;letter-spacing:-0.8px} }

.bh-blurb{margin:0;max-width:58ch;font:500 italic 16.5px/1.55 var(--body);color:rgba(255,255,255,0.93);border-left:3px solid var(--max);padding:4px 0 4px 16px;text-shadow:0 2px 10px rgba(0,0,0,0.55)}
.bh-blurb b{font-weight:700;font-style:normal;color:#fff}

.bh-loop{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0;border:1px solid rgba(255,255,255,0.30);background:rgba(0,0,0,0.45);backdrop-filter:blur(6px);border-radius:2px;overflow:hidden;max-width:640px;box-shadow:0 6px 22px rgba(0,0,0,0.4)}
.bh-step{display:grid;grid-template-columns:auto 1fr;align-items:center;gap:11px;padding:13px 14px;border-right:1px solid rgba(255,255,255,0.18);position:relative;min-width:0}
.bh-step:last-child{border-right:0}
.bh-step-n{font:900 22px/1 var(--display);font-variant-numeric:tabular-nums;color:var(--max);background:#fff;width:30px;height:30px;display:flex;align-items:center;justify-content:center;border-radius:50%;box-shadow:0 0 0 3px rgba(255,255,255,0.20)}
.bh-step-txt{display:flex;flex-direction:column;gap:1px;min-width:0}
.bh-step-k{font:900 11.5px/1 var(--body);letter-spacing:2px;text-transform:uppercase;color:#fff}
.bh-step-d{font:500 11px/1.3 var(--body);color:rgba(255,255,255,0.65);white-space:normal;overflow:hidden}
.bh-step::after{content:"›";position:absolute;right:-10px;top:50%;transform:translateY(-50%);font:900 22px/1 var(--display);color:var(--max);background:#0f172a;width:20px;height:20px;display:flex;align-items:center;justify-content:center;border-radius:50%;border:2px solid rgba(255,255,255,0.85);z-index:2}
.bh-step:last-child::after{display:none}
@media (max-width:640px){ .bh-loop{grid-template-columns:1fr;max-width:none}
  .bh-step{border-right:0;border-bottom:1px solid rgba(255,255,255,0.18)}
  .bh-step:last-child{border-bottom:0}
  .bh-step::after{display:none} }

/* RIGHT — stat slab + CTA */
.bh-r{display:flex;flex-direction:column;align-items:stretch;gap:14px;min-width:0;align-self:end}
.bh-slab{position:relative;background:rgba(15,23,42,0.78);border:1px solid rgba(255,255,255,0.28);border-left:4px solid var(--max);padding:20px 22px 18px;backdrop-filter:blur(8px);border-radius:2px;box-shadow:0 8px 28px rgba(0,0,0,0.45)}
.bh-slab::before{content:"CATALOG";position:absolute;left:18px;top:-10px;font:800 9.5px/1 var(--body);letter-spacing:2.4px;color:#fff;background:var(--ink);padding:5px 9px 4px;border:1px solid var(--max)}
.bh-slab-lbl{font:700 10px/1 var(--body);letter-spacing:2.4px;text-transform:uppercase;color:rgba(255,255,255,0.62);margin:6px 0 4px}
.bh-slab-num{font:800 92px/0.85 var(--mono);font-variant-numeric:tabular-nums;color:#fff;letter-spacing:-4px;margin:0;text-shadow:0 4px 24px rgba(0,0,0,0.4)}
.bh-slab-num .small{font-size:36px;color:var(--max);letter-spacing:-1px;margin-left:4px;vertical-align:5px}
.bh-slab-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:rgba(255,255,255,0.22);border:1px solid rgba(255,255,255,0.22);margin-top:14px;border-radius:2px;overflow:hidden}
.bh-slab-cell{display:flex;flex-direction:column;align-items:center;gap:3px;padding:9px 4px;background:rgba(15,23,42,0.85);min-width:0}
.bh-slab-cell-v{font:800 18px/1 var(--mono);font-variant-numeric:tabular-nums;color:#fff;letter-spacing:-0.5px}
.bh-slab-cell-l{font:800 9px/1 var(--body);letter-spacing:1.6px;text-transform:uppercase;color:rgba(255,255,255,0.55)}
.bh-slab-cell.is-race .bh-slab-cell-v{color:#fca5a5}
.bh-slab-cell.is-hot  .bh-slab-cell-v{color:#fde68a}
.bh-slab-cell.is-duel .bh-slab-cell-v{color:#bef264}
.bh-slab-cell.is-ser  .bh-slab-cell-v{color:#a5f3fc}

/* Section header above grid */
.section-head{display:flex;align-items:flex-end;justify-content:space-between;border-bottom:1.5px solid var(--ink);padding:28px 24px 10px;margin:0 auto;gap:14px;max-width:1280px}
.section-head-l{display:flex;flex-direction:column;align-items:flex-start;gap:9px}
.section-title{font:800 22px/1 var(--display);letter-spacing:-0.4px;text-transform:uppercase;color:var(--ink);margin:0}
.section-deck{font:400 12.5px/1.5 var(--body);color:var(--ink-3);max-width:50ch;text-align:right;margin:0}

/* Grid — 3 cols, capped narrow */
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;padding:24px 24px 64px;max-width:1280px;margin:0 auto}

/* Card */
.card{background:var(--surface);border:1px solid var(--ink);position:relative;display:flex;flex-direction:column;overflow:hidden;transition:transform 0.15s ease,box-shadow 0.15s ease;box-shadow:3px 3px 0 var(--ink)}
.card:hover{transform:translate(-2px,-2px);box-shadow:5px 5px 0 var(--ink)}

.card-img{aspect-ratio:16/9;position:relative;overflow:hidden;border-bottom:1px solid var(--ink);background:var(--ink)}
.card-img > img{width:100%;height:100%;object-fit:cover;display:block}

/* Auto-rotating carousel inside a card-img */
.carousel{position:absolute;inset:0;overflow:hidden;background:#000}
.carousel-slide{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity 0.7s ease-in-out;display:block}
.carousel-slide.is-active{opacity:1}
.carousel-dots{position:absolute;bottom:7px;left:50%;transform:translateX(-50%);display:flex;gap:4px;z-index:3}
.carousel-dot{width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,0.4);transition:background 0.2s,transform 0.2s;border:1px solid rgba(0,0,0,0.4)}
.carousel-dot.is-active{background:#fff;transform:scale(1.3)}
.card-img-fallback{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:flex-end;padding:14px;background:linear-gradient(135deg,var(--ca,#0a0a0a) 0%,var(--cb,#2a2a2a) 100%)}
.card-img-fallback::before{content:"";position:absolute;top:0;right:0;height:10px;width:55%;background:repeating-linear-gradient(90deg,var(--max) 0,var(--max) 10px,#0a0a0a 10px,#0a0a0a 20px)}
.card-img-fallback .fb-track{font:900 30px/0.9 var(--display);text-transform:uppercase;letter-spacing:-0.4px;color:#fff;margin:0;font-stretch:condensed;text-shadow:0 2px 12px rgba(0,0,0,0.55)}
.card-img-fallback .fb-meta{font:600 10px/1.3 var(--body);letter-spacing:0.5px;color:rgba(255,255,255,0.85);margin-top:6px}

.card-country-chip{position:absolute;top:10px;right:10px;background:rgba(15,23,42,0.92);color:#fff;font:700 9.5px/1 var(--body);letter-spacing:1.2px;padding:5px 8px 4px;text-transform:uppercase;z-index:2;border-radius:2px;display:inline-flex;align-items:center;gap:6px;box-shadow:0 1px 2px rgba(0,0,0,0.25)}
.card-country-chip .ccc-flag{display:inline-flex;width:20px;height:14px;box-shadow:0 0 0 1px rgba(255,255,255,0.3);overflow:hidden;border-radius:1px}
.card-country-chip .ccc-flag svg{width:100%;height:100%;display:block}
.card-country-chip .ccc-code{font-weight:700}
.card-type-chip{position:absolute;top:10px;left:10px;background:var(--ink);color:#fff;font:700 9.5px/1 var(--body);letter-spacing:1.2px;padding:5px 9px 4px;text-transform:uppercase;z-index:2;border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,0.25)}
.card-type-chip.race{background:var(--accent);color:#fff}
.card-type-chip.hotlap{background:var(--gold-rim);color:#fff}
.card-type-chip.duel{background:var(--ink);color:#fff}

.card-body{padding:14px 16px 14px;display:flex;flex-direction:column;gap:10px;flex:1}
.card-tag{font:700 10px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;color:var(--accent);margin:0}
.card-title{font:800 22px/1 var(--display);letter-spacing:-0.3px;text-transform:uppercase;color:var(--ink);margin:0;font-stretch:condensed}
.card-car{font:700 14px/1.2 var(--display);text-transform:uppercase;color:var(--ink);margin:4px 0 0;letter-spacing:0.2px;display:flex;align-items:baseline;gap:8px}
.card-car::before{content:"CAR";font:700 9px/1 var(--body);letter-spacing:1.4px;color:var(--accent);background:var(--paper);border:1px solid var(--border);padding:3px 6px 2px;border-radius:2px;flex-shrink:0}
.card-sub{font:500 12.5px/1.35 var(--body);color:var(--ink-3);margin:0;letter-spacing:0}
.card-scenario{font:400 13px/1.55 var(--body);color:var(--ink-2);margin:2px 0 0;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;letter-spacing:0}
.card-goal{font:500 12px/1.4 var(--body);color:var(--ink);background:var(--gold);padding:8px 10px 8px 11px;border-left:3px solid var(--gold-rim);margin:2px 0 0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;letter-spacing:0}
.card-goal .goal-lbl{font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:9.5px;color:var(--gold-rim);margin-right:6px;display:inline-block}
.card-setup{background:var(--paper);border:1px solid var(--border);border-left:3px solid var(--ink-3);border-radius:2px;margin:2px 0 0;padding:7px 10px 8px 11px;display:grid;grid-template-columns:auto 1fr;column-gap:10px;row-gap:3px;font:500 11.5px/1.35 var(--body);color:var(--ink-2);letter-spacing:0}
.card-setup .setup-head{grid-column:1/-1;font:700 9.5px/1 var(--body);text-transform:uppercase;letter-spacing:1.4px;color:var(--ink-3);margin-bottom:3px}
.card-setup .setup-row-lbl{font:700 9px/1.45 var(--body);text-transform:uppercase;letter-spacing:1px;color:var(--ink-4);align-self:start;padding-top:1px;white-space:nowrap}
.card-setup .setup-row-val{color:var(--ink-2);overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.card-setup .setup-row-val.is-trim{color:var(--ink);font-weight:600}

/* Lap-times block — monospace lap-board feel */
.card-times{background:var(--ink);color:#fff;border-radius:2px;margin:2px 0 0;padding:8px 10px 9px;display:flex;flex-direction:column;gap:3px;font-family:var(--mono);box-shadow:0 1px 2px rgba(0,0,0,0.18)}
.card-times .times-head{font:700 9.5px/1 var(--body);text-transform:uppercase;letter-spacing:1.4px;color:rgba(255,255,255,0.55);margin-bottom:4px}
.card-times .time-row{display:grid;grid-template-columns:1fr auto auto;column-gap:10px;align-items:baseline;font:500 12px/1.35 var(--mono);color:rgba(255,255,255,0.78)}
.card-times .time-row .time-lbl{font:500 11px/1.35 var(--body);color:rgba(255,255,255,0.62);letter-spacing:0.2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card-times .time-row .time-val{font-variant-numeric:tabular-nums;font-weight:600;color:#fff;letter-spacing:0.3px}
.card-times .time-row .time-diff{font-variant-numeric:tabular-nums;color:var(--max);min-width:62px;text-align:right;font-weight:600;font-size:11px}
.card-times .time-row.is-you .time-lbl{color:var(--gold);font-weight:700;text-transform:uppercase;font-size:10px;letter-spacing:1px}
.card-times .time-row.is-you .time-val{color:var(--gold);font-size:14px}
.card-times .time-row.is-you .time-diff{display:none}

/* Spec strip — minimal label : value pills */
.spec-strip{display:flex;flex-wrap:wrap;gap:0;border:1px solid var(--border);background:var(--surface);margin:0;font:500 11.5px/1.3 var(--body);border-radius:2px}
.spec-pill{flex:1 1 auto;padding:7px 10px;border-right:1px solid var(--border);color:var(--ink-2);min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.spec-pill:last-child{border-right:0}
.spec-pill .lbl{color:var(--ink-4);margin-right:5px;font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px}

.card-actions{display:flex;flex-direction:column;gap:6px;margin-top:auto;padding-top:4px}
.card-secondary{display:flex;gap:6px}
.card-secondary > *{flex:1 1 0;min-width:0}
.btn-launch{width:100%;background:var(--max);color:#fff;font:700 13px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;padding:12px 14px;border:1px solid var(--ink);border-radius:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;transition:background 0.12s,transform 0.05s;box-shadow:0 1px 2px rgba(0,0,0,0.15)}
.btn-launch:hover{background:var(--accent-strong)}
.btn-launch:active{transform:translateY(1px)}
.btn-launch::before{content:"▶";font-size:10px}
.btn-dash{background:var(--surface);color:var(--ink);font:600 10.5px/1 var(--body);letter-spacing:1px;text-transform:uppercase;padding:10px 10px;border:1px solid var(--ink);border-radius:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;text-decoration:none;white-space:nowrap;transition:background 0.12s;overflow:hidden;text-overflow:ellipsis}
.btn-dash:hover{background:var(--paper)}
.btn-watch{background:var(--ink);color:#fff;font:600 10.5px/1 var(--body);letter-spacing:1px;text-transform:uppercase;padding:10px 10px;border:1px solid var(--ink);border-radius:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;text-decoration:none;white-space:nowrap;transition:background 0.12s;overflow:hidden;text-overflow:ellipsis;gap:5px}
.btn-watch:hover{background:var(--accent)}

/* ====== CARD V2 — UI/UX Pro Max ====== */
.cv2{background:var(--surface);border:1px solid var(--ink);position:relative;display:flex;flex-direction:column;overflow:hidden;box-shadow:3px 3px 0 var(--ink);transition:transform 0.18s ease,box-shadow 0.18s ease}
.cv2:hover{transform:translate(-3px,-3px);box-shadow:6px 6px 0 var(--ink)}
.cv2:hover .cv2-img > img,
.cv2:hover .cv2-img .carousel-slide.is-active{transform:scale(1.05)}
.cv2:hover .cv2-title::after{width:64px}

.cv2-img{aspect-ratio:16/9;position:relative;overflow:hidden;border-bottom:2px solid var(--ink);background:#0a0a0a}
.cv2-img > img,.cv2-img .carousel-slide{transition:transform 0.5s ease}
.cv2-shade{position:absolute;inset:0;z-index:2;pointer-events:none;background:
  linear-gradient(180deg,rgba(0,0,0,0.10) 0%,rgba(0,0,0,0) 30%,rgba(0,0,0,0.55) 65%,rgba(0,0,0,0.92) 100%)}
.cv2-title{position:absolute;left:14px;right:60px;bottom:12px;margin:0;z-index:3;font:900 24px/0.95 var(--display);letter-spacing:-0.4px;text-transform:uppercase;color:#fff;text-shadow:0 3px 14px rgba(0,0,0,0.85),0 1px 2px rgba(0,0,0,0.9);font-stretch:condensed;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.cv2-title::after{content:"";display:block;margin-top:8px;width:34px;height:3px;background:var(--max);transition:width 0.25s ease}

/* Body — info table → CTAs → details → stats */
.cv2-body{padding:14px 16px 14px;display:flex;flex-direction:column;gap:11px;flex:1}
.cv2-meta{margin:0;display:grid;grid-template-columns:auto 1fr;column-gap:14px;row-gap:0}
.cv2-meta dt{margin:0;align-self:center;padding:9px 0;font:800 9px/1.2 var(--body);letter-spacing:1.8px;text-transform:uppercase;color:var(--ink-4);border-bottom:1px solid var(--rule-hair);min-width:48px}
.cv2-meta dd{margin:0;align-self:center;padding:9px 0;font:600 12.5px/1.35 var(--body);color:var(--ink);border-bottom:1px solid var(--rule-hair);overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.cv2-meta dt:first-of-type,.cv2-meta dd:first-of-type{border-top:1px solid var(--rule-hair)}
.cv2-meta dd b{font-weight:700;color:var(--ink)}
.cv2-meta dd .sep{color:var(--ink-4);margin:0 5px;font-weight:400}

/* Actions stack — primary CTAs first, then secondary details link */
.cv2-actions{display:flex;flex-direction:column;gap:7px;margin-top:2px}
.cv2-more{align-self:flex-start;font:700 10.5px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;color:var(--ink-3);text-decoration:none;padding:6px 0 5px;border-bottom:1px solid var(--ink-4);transition:color 0.12s,border-color 0.12s}
.cv2-more:hover{color:var(--max);border-color:var(--max)}
.cv2-more::after{content:" →"}

/* Stats — slim, dark, gold-on-ink, no chrome */
.cv2-stats{margin-top:auto;background:var(--ink);border:1px solid var(--ink);border-radius:2px;padding:9px 12px;display:grid;grid-template-columns:auto 1fr auto;column-gap:12px;row-gap:5px;align-items:baseline;font-family:var(--mono);position:relative;overflow:hidden}
.cv2-stats::before{content:"";position:absolute;top:0;left:0;width:3px;height:100%;background:var(--gold)}
.cv2-stats .row{display:contents}
.cv2-stats .you-k{font:800 9.5px/1 var(--body);letter-spacing:1.6px;text-transform:uppercase;color:var(--gold)}
.cv2-stats .you-v{font:700 18px/1 var(--mono);font-variant-numeric:tabular-nums;color:var(--gold);text-align:right;letter-spacing:-0.5px}
.cv2-stats .you-d{font:700 10px/1 var(--mono);font-variant-numeric:tabular-nums;color:rgba(255,255,255,0.45);text-align:right}
.cv2-stats .ref-k{font:700 9px/1.2 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:rgba(255,255,255,0.55);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cv2-stats .ref-v{font:600 12.5px/1 var(--mono);font-variant-numeric:tabular-nums;color:rgba(255,255,255,0.85);text-align:right;letter-spacing:-0.2px}
.cv2-stats .ref-d{font:700 10.5px/1 var(--mono);font-variant-numeric:tabular-nums;color:var(--max);text-align:right;min-width:48px}
.cv2-stats .empty{grid-column:1/-1;font:600 italic 11px/1.4 var(--body);color:rgba(255,255,255,0.55);text-align:center;padding:2px 0}

/* Mini accent bar between sections */
.cv2-divider{height:0;border:0;border-top:1px solid var(--rule-hair);margin:0}

/* Team-branded LAUNCH CTAs (dual-driver duels: Be Antonelli / Be Verstappen) */
.card-launchers{display:flex;flex-direction:column;gap:6px;width:100%}
.btn-launch-team{width:100%;color:#fff;font:800 12.5px/1 var(--body);letter-spacing:1.6px;text-transform:uppercase;padding:11px 12px;border:1px solid var(--ink);border-radius:2px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:9px;transition:filter 0.12s,transform 0.05s;box-shadow:0 1px 2px rgba(0,0,0,0.18);position:relative;overflow:hidden}
.btn-launch-team:hover{filter:brightness(1.18)}
.btn-launch-team:active{transform:translateY(1px)}
.btn-launch-team .team-logo{width:18px;height:18px;flex:0 0 auto}
.btn-launch-team .team-go{font-size:9.5px;letter-spacing:2px;opacity:0.7;font-weight:700}
.btn-launch-team.mercedes{background:linear-gradient(115deg,#00D2BE 0%,#0a2a2c 55%,#000 100%);border-color:#00D2BE}
.btn-launch-team.mercedes .team-logo{color:#fff}
.btn-launch-team.redbull{background:linear-gradient(115deg,#1E1E5C 0%,#0a0a3a 55%,#000 100%);border-color:#FFD700}
.btn-launch-team.redbull .team-logo{color:#FFD700}
.btn-launch-team.redbull::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,#D40E10 0%,#FFD700 100%)}
.btn-launch-team.verstappenracing{background:linear-gradient(115deg,#D40E10 0%,#0a1d2c 50%,#00D2BE 100%);border-color:#fff;border-image:linear-gradient(90deg,#D40E10 0%,#fff 50%,#00D2BE 100%) 1}
.btn-launch-team.verstappenracing .team-logo{color:#fff}
.btn-launch-team.verstappenracing::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,#D40E10 0%,#fff 50%,#00D2BE 100%)}
.btn-launch-team.audi{background:linear-gradient(115deg,#1a1a1a 0%,#0a0a0a 70%,#000 100%);border-color:#cc0000}
.btn-launch-team.audi .team-logo{color:#fff}
.btn-launch-team.audi::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,#cc0000 0%,#ffffff 50%,#cc0000 100%)}

/* Dual hero launchers on /challenge/<id> — side-by-side, larger than the card variant */
.cd-launchers{display:flex;gap:10px;flex-wrap:wrap;width:100%}
.cd-btn-launch-team{flex:1 1 0;min-width:220px;padding:15px 22px;font-size:14px;letter-spacing:2px}
.cd-btn-launch-team .team-logo{width:22px;height:22px}

/* Hero carousel takes the full hero media area on /challenge/<id> */
.cd-hero-carousel{position:absolute;inset:0;width:100%;height:100%;min-height:340px}
.cd-hero-carousel .carousel-slide{object-fit:cover}
.cd-hero-carousel .carousel-dots{bottom:14px}

/* === FULL-BLEED HERO V2 (duels with launchers) === */
.cd-hero-v2{position:relative;width:100%;min-height:560px;margin:0 0 28px;overflow:hidden;background:#000;border-bottom:1px solid var(--ink)}
@media (min-width: 1100px){ .cd-hero-v2{min-height:640px} }
.cd-hero-bg{position:absolute;inset:0;width:100%;height:100%}
.cd-hero-bg .carousel,.cd-hero-bg .cd-hero-carousel{position:absolute;inset:0;width:100%;height:100%}
.cd-hero-bg .carousel-slide,.cd-hero-bg img.cd-hero-img{width:100%;height:100%;object-fit:cover;display:block}
.cd-hero-overlay{position:absolute;inset:0;pointer-events:none;background:linear-gradient(180deg,rgba(0,0,0,0.55) 0%,rgba(0,0,0,0.15) 32%,rgba(0,0,0,0.55) 68%,rgba(0,0,0,0.95) 100%)}
.cd-back-floating{position:absolute;top:18px;left:24px;z-index:3;color:rgba(255,255,255,0.92);font:700 11px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;text-decoration:none;padding:8px 14px;background:rgba(0,0,0,0.45);border:1px solid rgba(255,255,255,0.22);border-radius:2px;backdrop-filter:blur(4px)}
.cd-back-floating:hover{background:rgba(0,0,0,0.7);border-color:#fff}
.cd-hero-content{position:relative;z-index:2;display:grid;grid-template-columns:1fr auto;gap:32px;align-items:end;max-width:1180px;margin:0 auto;padding:90px 28px 44px;color:#fff}
@media (min-width: 1100px){ .cd-hero-content{padding:140px 28px 56px} }
@media (max-width: 800px){ .cd-hero-content{grid-template-columns:1fr} }
.cd-hero-text{display:flex;flex-direction:column;gap:14px;align-items:flex-start;min-width:0}
.cd-tag-chip{font:800 11px/1 var(--body);letter-spacing:3px;text-transform:uppercase;padding:8px 12px;background:var(--max);color:#fff;border:1px solid #fff;border-radius:2px;box-shadow:0 2px 8px rgba(212,14,16,0.4)}
.cd-title-xl{margin:0;font:900 72px/0.92 var(--display);letter-spacing:-1px;text-transform:uppercase;color:#fff;text-shadow:0 4px 24px rgba(0,0,0,0.6);max-width:100%}
@media (min-width: 1100px){ .cd-title-xl{font-size:96px} }
@media (max-width: 700px){ .cd-title-xl{font-size:42px} }
.cd-blurb{margin:6px 0 0;font:500 italic 17px/1.5 var(--body);color:rgba(255,255,255,0.94);max-width:640px;text-shadow:0 2px 10px rgba(0,0,0,0.7);border-left:3px solid var(--max);padding-left:14px}
@media (min-width: 1100px){ .cd-blurb{font-size:19px} }
.cd-hero-track{display:flex;flex-direction:column;align-items:flex-end;gap:6px;padding:14px 16px;background:rgba(0,0,0,0.5);border:1px solid rgba(255,255,255,0.22);border-radius:2px;backdrop-filter:blur(6px);min-width:240px;max-width:300px}
.cd-hero-track-lbl{font:800 10px/1 var(--body);letter-spacing:2.5px;text-transform:uppercase;color:rgba(255,255,255,0.65)}
.cd-hero-track-name{font:900 22px/1 var(--display);letter-spacing:1px;text-transform:uppercase;color:#fff}
.cd-hero-track-outline{width:100%;display:flex;justify-content:center;padding-top:6px}
.cd-hero-track-outline img{width:100%;height:auto;max-height:140px;object-fit:contain;filter:invert(1) brightness(1.05) drop-shadow(0 0 6px rgba(255,255,255,0.18))}
@media (max-width: 800px){ .cd-hero-track{align-self:flex-start;align-items:flex-start;max-width:100%;width:100%} }

/* === Enriched perspective panel internals === */
.dp-panel{padding:0}  /* override: portrait fills top, body has padding */
.dp-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:rgba(255,255,255,0.18);border:1px solid rgba(255,255,255,0.18);border-radius:2px;margin:6px 0 2px;overflow:hidden}
.dp-stat{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:11px 6px;background:rgba(0,0,0,0.32);min-width:0}
.dp-stat-val{font:700 18px/1 var(--mono);color:#fff;letter-spacing:-0.5px}
.dp-stat-lbl{font:700 9.5px/1 var(--body);letter-spacing:1.8px;text-transform:uppercase;color:rgba(255,255,255,0.6)}
.dp-chart-wrap{margin:8px 0 4px;padding:10px 12px;background:rgba(0,0,0,0.28);border:1px solid rgba(255,255,255,0.12);border-radius:2px}
.dp-chart-lbl{font:700 9.5px/1.2 var(--body);letter-spacing:1.5px;text-transform:uppercase;color:rgba(255,255,255,0.55);margin-bottom:6px}
.dp-chart{display:block;width:100%;height:auto}
.dp-chart-empty{font:500 italic 12.5px/1.4 var(--body);color:rgba(255,255,255,0.55);padding:22px 8px;text-align:center}
.dp-chart-empty-em{color:rgba(255,255,255,0.85);font-weight:700;font-style:normal;letter-spacing:0.5px}

/* === Head-to-head section === */
.h2h-section{padding-top:8px}
.h2h-bar{display:flex;width:100%;height:14px;border:1.5px solid var(--ink);border-radius:2px;overflow:hidden;background:var(--ink-4);margin-bottom:14px}
.h2h-bar-seg{height:100%;transition:flex-basis 0.4s ease}
.h2h-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.h2h-card{position:relative;display:grid;grid-template-columns:auto 1fr;align-items:center;gap:14px;padding:16px 18px;background:var(--surface);border:1px solid var(--ink);border-left:4px solid var(--accent);border-radius:2px}
.h2h-team-logo{display:flex;align-items:center;justify-content:center;width:42px;height:42px;border:1px solid var(--ink);border-radius:50%;background:#000;color:var(--accent);grid-row:span 2}
.h2h-team-logo .team-logo{width:24px;height:24px}
.h2h-tally{display:flex;align-items:baseline;gap:4px;color:var(--ink)}
.h2h-wins{font:900 38px/1 var(--mono);color:var(--accent)}
.h2h-of{font:700 14px/1 var(--mono);color:var(--ink-3)}
.h2h-label{font:800 10px/1 var(--body);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3)}
@media (max-width: 700px){ .h2h-cards{grid-template-columns:1fr} }

/* === Drivers section (bios only — no CTA) === */
.dr-section{padding-top:6px}
.dr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.dr-panel{position:relative;display:grid;grid-template-columns:130px 1fr;gap:0;border:1px solid var(--ink);border-radius:3px;overflow:hidden;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.18)}
.dr-mercedes{background:linear-gradient(155deg,#00D2BE 0%,#0e2d31 30%,#0a1416 100%);border-color:#00D2BE}
.dr-redbull{background:linear-gradient(155deg,#1E1E5C 0%,#0c0c2e 50%,#000 100%);border-color:#FFD700}
.dr-redbull::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,#D40E10 0%,#FFD700 100%);z-index:2}
.dr-verstappenracing{background:linear-gradient(155deg,#D40E10 0%,#1a0608 28%,#0a1d2c 60%,#00D2BE 100%);border-color:#fff}
.dr-verstappenracing::before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(90deg,#D40E10 0%,#fff 50%,#00D2BE 100%);z-index:2}
.dr-verstappenracing .dr-portrait-fallback .dr-num-big{color:#D40E10;text-shadow:0 0 16px rgba(212,14,16,0.55)}
.dr-verstappenracing .dr-num-inline{color:#fff}
.dr-verstappenracing .dr-team-logo{color:#fff}
.dr-verstappenracing .dr-team-logo .team-logo-combo{width:38px;height:auto}
.dr-verstappenracing .dr-quote{border-left-color:#fff}
.dr-audi{background:linear-gradient(155deg,#1a1a1a 0%,#0a0a0a 35%,#000 100%);border-color:#cc0000}
.dr-audi::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,#cc0000 0%,#ffffff 50%,#cc0000 100%);z-index:2}
.dr-audi .dr-portrait-fallback .dr-num-big{color:#cc0000}
.dr-audi .dr-num-inline{color:#cc0000}
.dr-audi .dr-team-logo{color:#fff}
.dr-audi .dr-quote{border-left-color:#cc0000}
.dr-portrait{position:relative;background:#000;overflow:hidden}
.dr-portrait img{width:100%;height:100%;object-fit:cover;display:block}
.dr-portrait-fallback{display:flex;align-items:center;justify-content:center;height:100%}
.dr-portrait-fallback .dr-num-big{font:900 90px/1 var(--display);letter-spacing:-3px;color:rgba(255,255,255,0.92)}
.dr-mercedes .dr-portrait-fallback .dr-num-big{color:#00D2BE}
.dr-redbull .dr-portrait-fallback .dr-num-big{color:#FFD700}
.dr-body{padding:14px 16px;display:flex;flex-direction:column;gap:6px;min-width:0}
.dr-tag{align-self:flex-start;font:800 9.5px/1 var(--body);letter-spacing:2.4px;text-transform:uppercase;padding:5px 8px;background:rgba(0,0,0,0.45);border:1px solid rgba(255,255,255,0.18);border-radius:2px}
.dr-name{margin:2px 0 0;font:900 18px/1.05 var(--display);letter-spacing:1px;text-transform:uppercase;color:#fff;display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.dr-num-inline{font:900 18px/1 var(--display);letter-spacing:0.5px}
.dr-mercedes .dr-num-inline{color:#00D2BE}
.dr-redbull .dr-num-inline{color:#FFD700}
.dr-team{display:flex;align-items:center;gap:8px;font:600 10.5px/1.25 var(--body);letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.8)}
.dr-team-logo{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;color:currentColor}
.dr-mercedes .dr-team-logo{color:#fff}
.dr-redbull .dr-team-logo{color:#FFD700}
.dr-team-logo .team-logo{width:18px;height:18px}
.dr-quote{margin:4px 0 0;font:500 italic 12.5px/1.45 var(--body);color:#fff;border-left:2px solid currentColor;padding-left:9px}
.dr-mercedes .dr-quote{border-left-color:#00D2BE}
.dr-redbull .dr-quote{border-left-color:#FFD700}
@media (max-width: 900px){
  .dr-grid{grid-template-columns:1fr}
  .dr-panel{grid-template-columns:100px 1fr}
}

/* === Cars section (chassis + two liveries) === */
.cs-section{padding-top:6px}
.cs-chassis{background:var(--surface);border:1px solid var(--ink);border-radius:2px;padding:14px 18px;margin-bottom:12px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center}
.cs-chassis-lbl{grid-column:1;font:800 10px/1 var(--body);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3)}
.cs-chassis-name{grid-column:1;font:900 22px/1 var(--display);letter-spacing:1px;text-transform:uppercase;color:var(--ink)}
.cs-chassis-brand{grid-column:1;font:600 11px/1.2 var(--body);letter-spacing:1px;text-transform:uppercase;color:var(--ink-3)}
.cs-chassis-specs{grid-column:2;grid-row:1/-1;display:grid;grid-template-columns:repeat(4,minmax(70px,auto));gap:1px;background:var(--ink);border:1px solid var(--ink);align-self:center}
.cs-spec{display:flex;flex-direction:column;align-items:center;gap:2px;padding:8px 10px;background:var(--paper)}
.cs-spec-lbl{font:800 8.5px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;color:var(--ink-3)}
.cs-spec-val{font:700 14px/1 var(--mono);color:var(--ink)}
@media (max-width: 800px){ .cs-chassis{grid-template-columns:1fr} .cs-chassis-specs{grid-row:auto;grid-column:1;grid-template-columns:repeat(2,1fr)} }
.cs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.cs-card{position:relative;border:1px solid var(--ink);border-left:3px solid var(--accent);border-radius:2px;background:#000;overflow:hidden;display:flex;flex-direction:column;color:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.2)}
.cs-livery-wrap{position:relative;aspect-ratio:16/9;background:#000;overflow:hidden}
.cs-livery-img{width:100%;height:100%;object-fit:cover;display:block}
.cs-livery-fallback{background:linear-gradient(135deg,#1a1a1a,#000)}
.cs-meta{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;padding:12px 14px;align-items:center}
.cs-meta-num{font:900 32px/1 var(--display);letter-spacing:-1px;color:var(--accent);grid-row:span 2}
.cs-meta-team{font:800 11px/1.2 var(--body);letter-spacing:1.2px;text-transform:uppercase;color:#fff}
.cs-meta-driver{font:600 11px/1.2 var(--body);letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.65)}
@media (max-width: 700px){ .cs-grid{grid-template-columns:1fr} }
/* Different-chassis variant: each card carries its own chassis info above the meta */
.cs-chassis-versus{padding:10px 14px}
.cs-chassis-inline{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,0.18);background:rgba(0,0,0,0.4);color:#fff}
.cs-chassis-inline-name{font:900 16px/1.05 var(--display);letter-spacing:1px;text-transform:uppercase;color:#fff}
.cs-chassis-inline-brand{font:600 9.5px/1.2 var(--body);letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.65);margin-top:2px}
.cs-chassis-inline-specs{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}
.cs-chassis-inline-specs .cs-spec{flex:1 1 auto;background:rgba(255,255,255,0.06);border:none;padding:4px 8px}
.cs-chassis-inline-specs .cs-spec-lbl{color:rgba(255,255,255,0.55)}
.cs-chassis-inline-specs .cs-spec-val{color:#fff;font-size:12px}

/* === Choose your seat (final CTA section) === */
.ch-section{padding-top:6px}
.ch-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.ch-card{position:relative;border:1.5px solid var(--accent);border-radius:3px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;color:#fff;box-shadow:0 4px 14px rgba(0,0,0,0.3)}
.ch-mercedes{background:linear-gradient(140deg,#00D2BE 0%,#0a2628 35%,#000 100%)}
.ch-redbull{background:linear-gradient(140deg,#1E1E5C 0%,#080826 45%,#000 100%)}
.ch-redbull::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,#D40E10 0%,#FFD700 100%)}
.ch-verstappenracing{background:linear-gradient(140deg,#D40E10 0%,#1a0608 35%,#0a1d2c 65%,#00D2BE 100%)}
.ch-verstappenracing::before{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(90deg,#D40E10 0%,#fff 50%,#00D2BE 100%)}
.ch-audi{background:linear-gradient(140deg,#262626 0%,#0a0a0a 50%,#000 100%)}
.ch-audi::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,#cc0000 0%,#ffffff 50%,#cc0000 100%)}
.ch-card-head{display:flex;align-items:center;gap:12px}
.ch-team-mark{display:flex;align-items:center;justify-content:center;width:42px;height:42px;border:1.5px solid currentColor;border-radius:50%;background:rgba(0,0,0,0.5);color:var(--accent);flex:0 0 auto}
.ch-team-mark .team-logo{width:24px;height:24px}
.ch-card-tagline{font:800 9.5px/1 var(--body);letter-spacing:2.5px;text-transform:uppercase;color:var(--accent)}
.ch-card-driver{font:900 18px/1 var(--display);letter-spacing:1px;text-transform:uppercase;color:#fff;margin-top:3px}
.ch-cta{margin-top:6px;padding:13px 16px;font-size:13px;letter-spacing:2px;border-width:2px}
@media (max-width: 700px){ .ch-grid{grid-template-columns:1fr} }

/* Real-logo image fallback (replaces stylized SVG when PNG file exists) */
.team-logo-img{display:block;object-fit:contain;width:100%;height:100%;max-width:100%;max-height:100%}
/* Combo logo (Mercedes × Red Bull) is wider — give it room to breathe */
.team-logo-combo{width:auto;height:18px;max-width:46px}
.dp-logo .team-logo-combo,.ch-team-mark .team-logo-combo{height:20px;max-width:52px}
.btn-launch-team .team-logo-combo{height:20px;max-width:50px}

/* === Ongoing challenges featured row (top of home page) === */
.ongoing-section{background:linear-gradient(180deg,#0f172a 0%,#1f2937 100%);color:#fff;border-bottom:3px solid var(--max);padding:28px 28px 36px;margin:0 0 8px}
.ongoing-head{max-width:1180px;margin:0 auto 18px;display:flex;flex-direction:column;gap:6px}
.ongoing-tag{display:inline-flex;align-self:flex-start;align-items:center;gap:8px;font:900 11px/1 var(--body);letter-spacing:3px;text-transform:uppercase;background:var(--max);color:#fff;padding:7px 11px;border-radius:2px;box-shadow:0 2px 8px rgba(212,14,16,0.4)}
.ongoing-title{margin:0;font:900 38px/1 var(--display);letter-spacing:1.2px;text-transform:uppercase;color:#fff}
.ongoing-deck{margin:0;font:500 13px/1.5 var(--body);color:rgba(255,255,255,0.7);max-width:680px}
.ongoing-grid{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
@media (max-width: 1000px){ .ongoing-grid{grid-template-columns:repeat(2,1fr)} }
@media (max-width: 700px){ .ongoing-grid{grid-template-columns:1fr} .ongoing-section{padding:22px 16px 28px} .ongoing-title{font-size:28px} }
/* Force ongoing cards onto a dark surface — invert the body palette so they pop */
.ongoing-grid .card{background:var(--surface);border-color:var(--max)}

/* === Track section (carousel + facts) === */
.tk-section{padding-top:6px}
.tk-grid{display:grid;grid-template-columns:1.7fr 1fr;gap:14px;align-items:stretch}
.tk-photos{position:relative;border:1px solid var(--ink);border-radius:2px;overflow:hidden;background:#000;aspect-ratio:16/9;min-height:240px}
.tk-carousel{position:absolute;inset:0;width:100%;height:100%}
.tk-carousel-empty{background:linear-gradient(135deg,#1a1a1a,#000)}
.tk-side{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--ink);border-radius:2px;padding:14px 16px}
.tk-name{font:900 26px/1 var(--display);letter-spacing:1px;text-transform:uppercase;color:var(--ink);padding-bottom:6px;border-bottom:1px solid var(--border)}
.tk-outline{display:flex;align-items:center;justify-content:center;background:#0a0a0a;border:1px solid var(--ink);padding:10px;border-radius:2px;min-height:120px}
.tk-outline img{max-width:100%;max-height:140px;width:auto;height:auto;filter:invert(1) brightness(0.95);object-fit:contain}
.tk-facts{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--ink);border:1px solid var(--ink);align-self:stretch}
.tk-fact{display:flex;flex-direction:column;gap:3px;padding:10px 12px;background:var(--paper)}
.tk-fact-lbl{font:800 9px/1 var(--body);letter-spacing:1.8px;text-transform:uppercase;color:var(--ink-3)}
.tk-fact-val{font:700 16px/1 var(--mono);color:var(--ink)}
.tk-desc{margin:14px 0 0;font:500 italic 13.5px/1.55 var(--body);color:var(--ink-2);max-width:880px;border-left:3px solid var(--ink-4);padding-left:14px}
@media (max-width: 800px){ .tk-grid{grid-template-columns:1fr} }

/* === Setup "1" section === */
.su-section{padding-top:6px}
.su-deck{margin:-4px 0 14px;font:500 13px/1.5 var(--body);color:var(--ink-3);max-width:780px}
.su-deck code{background:var(--paper);border:1px solid var(--border);padding:1px 5px;border-radius:2px;font-size:0.92em}
.su-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:10px}
.su-group{background:var(--surface);border:1px solid var(--ink);border-radius:2px;overflow:hidden;display:flex;flex-direction:column}
.su-group-head{padding:10px 14px;border-bottom:1.5px solid var(--ink);background:var(--ink);color:#fff}
.su-group-name{font:900 13px/1 var(--display);letter-spacing:2px;text-transform:uppercase}
.su-group-deck{font:500 10.5px/1.3 var(--body);color:rgba(255,255,255,0.65);margin-top:3px}
.su-rows{display:flex;flex-direction:column}
.su-row{display:grid;grid-template-columns:1fr auto;grid-template-rows:auto auto;gap:1px 10px;padding:10px 14px;border-bottom:1px solid var(--border)}
.su-row:last-child{border-bottom:0}
.su-row-label{font:700 12px/1.2 var(--body);color:var(--ink);grid-column:1;grid-row:1}
.su-row-value{font:700 14px/1 var(--mono);color:var(--max);grid-column:2;grid-row:1;align-self:center;background:var(--paper);padding:5px 10px;border:1px solid var(--ink);border-radius:2px}
.su-row-blurb{font:500 11px/1.4 var(--body);color:var(--ink-3);grid-column:1/-1;grid-row:2;margin-top:2px}

/* === Choose-section H2H bar (replaces standalone H2H) === */
.ch-h2h{display:flex;flex-direction:column;gap:6px;margin-bottom:14px}
.ch-h2h-lbl{font:800 9.5px/1 var(--body);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3)}
.ch-h2h-bar{display:flex;width:100%;height:12px;border:1.5px solid var(--ink);border-radius:2px;overflow:hidden;background:var(--ink-4)}
.ch-h2h-seg{height:100%;transition:flex-basis 0.4s ease}
.ch-h2h-totals{display:flex;justify-content:space-between;gap:14px}
.ch-h2h-total{display:flex;align-items:baseline;gap:5px;color:var(--ink)}
.ch-h2h-total-val{font:900 18px/1 var(--mono);color:var(--accent)}
.ch-h2h-total-of{font:700 11px/1 var(--mono);color:var(--ink-3)}
.ch-h2h-total-lbl{font:800 9.5px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;color:var(--ink-3);margin-left:2px}

/* Inline rival record on each Choose card */
.ch-card-head{display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px}
.ch-record{display:flex;flex-direction:column;align-items:flex-end;line-height:1;gap:1px}
.ch-record-mine{font:900 18px/1 var(--mono);color:var(--accent)}
.ch-record-vs{font:700 9px/1 var(--body);letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.45);margin:1px 0}
.ch-record-rival{font:700 13px/1 var(--mono);color:rgba(255,255,255,0.55)}
.ch-record-lbl{font:700 8px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;color:rgba(255,255,255,0.4);margin-top:2px}

/* === Track DNA === */
.td-section{padding-top:8px}
.td-grid{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;align-items:stretch;background:var(--surface);border:1px solid var(--ink);border-radius:2px;padding:18px 22px}
.td-name{grid-column:1/-1;font:900 28px/1 var(--display);letter-spacing:1px;text-transform:uppercase;color:var(--ink);padding-bottom:8px;border-bottom:1px solid var(--border)}
.td-outline{display:flex;align-items:center;justify-content:center;background:#0a0a0a;border:1px solid var(--ink);padding:14px;border-radius:2px;min-height:160px}
.td-outline img{max-width:100%;max-height:240px;width:auto;height:auto;filter:invert(1) brightness(0.85);object-fit:contain}
.td-facts{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--ink);border:1px solid var(--ink);align-self:start}
.td-fact{display:flex;flex-direction:column;gap:4px;padding:14px 16px;background:var(--paper)}
.td-fact-lbl{font:800 9.5px/1 var(--body);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3)}
.td-fact-val{font:700 22px/1 var(--mono);color:var(--ink)}
@media (max-width: 800px){ .td-grid{grid-template-columns:1fr} }

/* "Choose your driver" — compact panels, side-by-side portrait + content */
.dp-section{padding-top:6px}
.dp-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.dp-panel{position:relative;display:grid;grid-template-columns:120px 1fr;gap:0;border:1px solid var(--ink);border-radius:3px;color:#fff;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.2)}
.dp-mercedes{background:linear-gradient(155deg,#00D2BE 0%,#0e2d31 30%,#0a1416 100%);border-color:#00D2BE}
.dp-redbull{background:linear-gradient(155deg,#1E1E5C 0%,#0c0c2e 50%,#000 100%);border-color:#FFD700}
.dp-redbull::before{content:"";position:absolute;left:0;right:0;top:0;height:2px;background:linear-gradient(90deg,#D40E10 0%,#FFD700 100%);z-index:2}
.dp-portrait{position:relative;background:#000;overflow:hidden}
.dp-portrait img{width:100%;height:100%;object-fit:cover;display:block}
.dp-portrait-fallback{display:flex;align-items:center;justify-content:center;height:100%}
.dp-portrait-fallback .dp-num-big{font:900 80px/1 var(--display);letter-spacing:-3px;color:rgba(255,255,255,0.92)}
.dp-mercedes .dp-portrait-fallback .dp-num-big{color:#00D2BE}
.dp-redbull .dp-portrait-fallback .dp-num-big{color:#FFD700}
.dp-body{padding:12px 14px;display:flex;flex-direction:column;gap:5px;min-width:0}
.dp-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:1px}
.dp-logo{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border:1px solid rgba(255,255,255,0.25);border-radius:50%;background:rgba(0,0,0,0.3)}
.dp-mercedes .dp-logo{color:#fff}
.dp-redbull .dp-logo{color:#FFD700}
.dp-logo .team-logo{width:17px;height:17px}
.dp-tag{font:800 9.5px/1 var(--body);letter-spacing:2.4px;text-transform:uppercase;padding:5px 8px;background:rgba(0,0,0,0.45);border:1px solid rgba(255,255,255,0.18);border-radius:2px}
.dp-driver{margin:0;font:900 16px/1.05 var(--display);letter-spacing:1px;text-transform:uppercase;color:#fff;display:flex;align-items:baseline;gap:7px;flex-wrap:wrap}
.dp-num-inline{font:900 16px/1 var(--display);letter-spacing:0.5px}
.dp-mercedes .dp-num-inline{color:#00D2BE}
.dp-redbull .dp-num-inline{color:#FFD700}
.dp-team{font:600 9.5px/1.25 var(--body);letter-spacing:1px;text-transform:uppercase;color:rgba(255,255,255,0.7);margin-bottom:3px}
.dp-quote{margin:2px 0;font:500 italic 12px/1.45 var(--body);color:#fff;border-left:2px solid currentColor;padding-left:8px}
.dp-mercedes .dp-quote{border-left-color:#00D2BE}
.dp-redbull .dp-quote{border-left-color:#FFD700}
.dp-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:rgba(255,255,255,0.16);border:1px solid rgba(255,255,255,0.16);border-radius:2px;margin:3px 0 1px;overflow:hidden}
.dp-stat{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;padding:6px 4px;background:rgba(0,0,0,0.32);min-width:0}
.dp-stat-val{font:700 13px/1 var(--mono);color:#fff;letter-spacing:-0.3px}
.dp-stat-lbl{font:700 8px/1 var(--body);letter-spacing:1.3px;text-transform:uppercase;color:rgba(255,255,255,0.55)}
.dp-chart-wrap{margin:4px 0 2px;padding:6px 8px;background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1);border-radius:2px}
.dp-chart-lbl{font:700 8px/1.2 var(--body);letter-spacing:1.2px;text-transform:uppercase;color:rgba(255,255,255,0.5);margin-bottom:3px}
.dp-chart{display:block;width:100%;height:auto;max-height:48px}
.dp-chart-empty{font:500 italic 10.5px/1.3 var(--body);color:rgba(255,255,255,0.55);padding:10px 4px;text-align:center}
.dp-chart-empty-em{color:rgba(255,255,255,0.85);font-weight:700;font-style:normal;letter-spacing:0.4px}
.dp-cta{margin-top:6px;padding:9px 12px;font-size:11px;letter-spacing:1.6px;border-width:2px}
.dp-mercedes .dp-cta{border-color:#00D2BE;background:linear-gradient(115deg,#00D2BE 0%,#0a2a2c 70%,#000 100%)}
.dp-redbull .dp-cta{border-color:#FFD700;background:linear-gradient(115deg,#1E1E5C 0%,#0a0a3a 65%,#000 100%)}
@media (max-width: 900px){
  .dp-grid{grid-template-columns:1fr}
  .dp-panel{grid-template-columns:90px 1fr}
}

.toast{position:fixed;bottom:36px;right:36px;background:var(--ink);color:#fff;font:700 13px/1.4 var(--body);letter-spacing:1.5px;text-transform:uppercase;padding:14px 22px;border:2.5px solid var(--max);max-width:420px;opacity:0;transform:translateY(20px);transition:all 0.25s;z-index:99;pointer-events:none}
.toast.show{opacity:1;transform:translateY(0)}
.toast.err{border-color:var(--gold);background:var(--max)}

/* Top nav strip — sits above ticker */
.topnav{display:flex;background:#fff;border-bottom:1px solid var(--border);padding:0 24px;font:600 11px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;gap:0;position:sticky;top:0;z-index:30}
.nav-link{padding:14px 18px;color:var(--ink-3);text-decoration:none;border-bottom:2.5px solid transparent;transition:color .15s,border-color .15s,background .15s;display:inline-flex;align-items:center}
.nav-link:hover{color:var(--ink);background:var(--paper)}
.nav-link.is-active{color:var(--ink);border-bottom-color:var(--max)}

/* Garage pages */
.garage-hero{padding:24px 24px 18px}

/* Sticky toolbar — search, sort, count, reset */
.garage-toolbar{position:sticky;top:42px;z-index:25;background:rgba(250,249,246,0.97);backdrop-filter:blur(8px);max-width:1280px;margin:14px auto 0;padding:12px 24px;display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--border)}
.garage-search{flex:1 1 320px;min-width:200px;font:500 13.5px/1 var(--body);padding:10px 14px;border:1.5px solid var(--ink);border-radius:3px;background:#fff;color:var(--ink);outline:none;transition:box-shadow .15s}
.garage-search:focus{box-shadow:0 0 0 3px rgba(220,38,38,0.18)}
.garage-sort{font:500 12.5px/1 var(--body);padding:9px 30px 9px 12px;border:1.5px solid var(--ink);border-radius:3px;background:#fff url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='8' height='6' viewBox='0 0 8 6'><path fill='%23475569' d='M4 6L0 0h8z'/></svg>") no-repeat right 10px center;color:var(--ink);cursor:pointer;outline:none;appearance:none;-webkit-appearance:none}
.garage-stats{font:500 12.5px/1 var(--body);color:var(--ink-3);white-space:nowrap}
.garage-stats strong{color:var(--ink);font-weight:700}
.garage-reset{font:600 11.5px/1 var(--body);letter-spacing:0.4px;padding:9px 14px;background:transparent;border:1.5px solid var(--ink-4);color:var(--ink-3);border-radius:3px;cursor:pointer;transition:all .12s}
.garage-reset:hover{background:var(--ink);color:#fff;border-color:var(--ink)}

/* Active filter pills */
.garage-active-pills{max-width:1280px;margin:0 auto;padding:0 24px;display:flex;flex-wrap:wrap;gap:8px;min-height:0;transition:padding .15s,min-height .15s}
.garage-active-pills.has-pills{padding:12px 24px}
.apill{display:inline-flex;align-items:center;gap:6px;background:var(--ink);color:#fff;font:500 11.5px/1 var(--body);padding:6px 4px 6px 10px;border-radius:14px}
.apill button{background:rgba(255,255,255,0.18);border:0;color:#fff;width:18px;height:18px;border-radius:50%;cursor:pointer;font-size:14px;line-height:1;display:flex;align-items:center;justify-content:center;padding:0;transition:background .12s}
.apill button:hover{background:var(--accent)}
.apill-series{background:var(--accent)}
.apill-category{background:var(--accent)}
.apill-era{background:#0369a1}
.apill-brand{background:#475569}
.apill-country{background:#475569}

/* Two-column layout: sidebar + grid */
.garage-layout{display:grid;grid-template-columns:230px minmax(0,1fr);gap:20px;max-width:1280px;margin:0 auto;padding:14px 24px 64px}
.garage-sidebar{position:sticky;top:118px;align-self:start;max-height:calc(100vh - 138px);overflow-y:auto;padding-right:8px}

.ffacet{margin-bottom:18px;border-bottom:1px solid var(--border);padding-bottom:14px}
.ffacet:last-child{border-bottom:0}
.ffacet-h{font:700 10.5px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-3);margin:0 0 10px;display:flex;justify-content:space-between;align-items:center}
.ffacet-c{background:var(--border);color:var(--ink-3);font-weight:700;font-size:10px;padding:2px 6px;border-radius:8px}
.ffacet-search{width:100%;font:500 12px/1 var(--body);padding:7px 10px;border:1px solid var(--border);border-radius:3px;background:#fff;color:var(--ink);outline:none;margin-bottom:8px;transition:border-color .12s}
.ffacet-search:focus{border-color:var(--ink-3)}
.ffacet-list{display:flex;flex-direction:column;gap:2px}
.ffacet-list-scroll{max-height:280px;overflow-y:auto;padding-right:4px}
.fopt{display:flex;justify-content:space-between;align-items:center;gap:8px;font:500 12.5px/1.2 var(--body);padding:6px 10px;background:transparent;border:0;color:var(--ink-2);cursor:pointer;border-radius:3px;text-align:left;transition:background .1s,color .1s;width:100%}
.fopt:hover{background:var(--paper)}
.fopt.is-active{background:var(--ink);color:#fff;font-weight:600}
.fopt-label{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fopt-count{font:600 10.5px/1 var(--body);color:var(--ink-4);background:rgba(15,23,42,0.05);padding:2px 6px;border-radius:8px;flex-shrink:0}
.fopt.is-active .fopt-count{background:rgba(255,255,255,0.18);color:rgba(255,255,255,0.85)}

/* Tile year chip */
.tile-year{position:absolute;bottom:6px;left:6px;background:rgba(255,255,255,0.92);color:var(--ink);font:700 10px/1 var(--mono);padding:3px 6px;border-radius:2px}

.garage-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;padding:0;max-width:none;margin:0}
.tile{background:var(--surface);border:1px solid var(--border);overflow:hidden;display:flex;flex-direction:column;transition:transform .12s,box-shadow .12s,border-color .12s}
.tile:hover{transform:translateY(-2px);box-shadow:2px 4px 0 var(--ink);border-color:var(--ink)}
.tile-img{aspect-ratio:16/9;background:#000;position:relative;overflow:hidden}
.tile-img > img{width:100%;height:100%;object-fit:cover;display:block}
.tile-img-fallback{position:absolute;inset:0;background:linear-gradient(135deg,#1f2937,#0f172a);display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,0.3);font:700 11px/1 var(--body);text-transform:uppercase;letter-spacing:1.5px}
.tile-img-fallback::before{content:"NO PREVIEW"}
.tile-badge{position:absolute;top:6px;right:6px;background:rgba(15,23,42,0.85);color:#fff;font:700 9px/1 var(--body);letter-spacing:0.8px;text-transform:uppercase;padding:3px 6px;border-radius:2px}

/* Series chip on tile (top-left, like a class badge) */
.tile-series{position:absolute;top:6px;left:6px;background:var(--ink);color:#fff;font:800 9px/1 var(--body);letter-spacing:1px;padding:4px 7px 3px;text-transform:uppercase;border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,0.3)}
/* Series-specific color tint — F1 + GT3 + LMP get accent, others slate */
.tile-series.s-f1{background:#dc2626}
.tile-series.s-open-wheel{background:#ea580c}
.tile-series.s-indycar{background:#ea580c}
.tile-series.s-gt3{background:#16a34a}
.tile-series.s-gt4{background:#15803d}
.tile-series.s-gte{background:#0891b2}
.tile-series.s-gt500{background:#7c3aed}
.tile-series.s-gt300{background:#a855f7}
.tile-series.s-lmp1{background:#0c4a6e}
.tile-series.s-lmp2{background:#0369a1}
.tile-series.s-lmp{background:#0369a1}
.tile-series.s-hypercar{background:#a16207}
.tile-series.s-dtm{background:#365314}
.tile-series.s-stock{background:#7c2d12}
.tile-series.s-rally{background:#854d0e}
.tile-series.s-drift{background:#b91c1c}
.tile-series.s-vintage{background:#6b7280}
.tile-series.s-touring{background:#075985}
.tile-series.s-tcr{background:#0e7490}
.tile-series.s-street{background:#475569}
.tile-series.s-hot-hatch{background:#a16207}
.tile-series.s-supercar{background:#9a3412}
.tile-series.s-race{background:#374151}
.tile-series.s-other{background:#6b7280}
/* Track categories */
.tile-series.s-f1-gp{background:#dc2626}
.tile-series.s-nord{background:#15803d}
.tile-series.s-le-mans{background:#0c4a6e}
.tile-series.s-endurance{background:#0369a1}
.tile-series.s-oval{background:#7c2d12}
.tile-series.s-rally{background:#854d0e}
.tile-series.s-road{background:#475569}

.tile-skins{position:absolute;bottom:6px;right:6px;background:rgba(15,23,42,0.78);color:#fff;font:600 9px/1 var(--body);letter-spacing:0.6px;padding:3px 6px;border-radius:2px;text-transform:uppercase}

/* Filter chip count badge */
.fcount{display:inline-block;margin-left:6px;background:rgba(15,23,42,0.08);color:var(--ink-3);font-size:9.5px;font-weight:700;padding:1px 5px;border-radius:8px;line-height:1.4}
.fchip.is-active .fcount{background:rgba(255,255,255,0.18);color:rgba(255,255,255,0.85)}
.fchip-series{font-weight:700}
.tile-body{padding:9px 11px 10px;display:flex;flex-direction:column;gap:3px}
.tile-brand{font:700 9.5px/1.2 var(--body);letter-spacing:1px;text-transform:uppercase;color:var(--ink-4);margin:0}
.tile-title{font:700 14px/1.2 var(--body);color:var(--ink);margin:0;letter-spacing:-0.1px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tile-meta{display:flex;gap:8px;flex-wrap:wrap;font:500 11px/1.2 var(--body);color:var(--ink-3);margin-top:3px;letter-spacing:0}
.tile-meta span:not(:empty){display:inline-block}
.tile-meta span:empty{display:none}

@media (max-width:900px){
  .garage-layout{grid-template-columns:1fr;padding:14px 16px 60px;gap:14px}
  .garage-sidebar{position:static;max-height:none;padding-right:0;border-bottom:1px solid var(--border);padding-bottom:14px}
  .garage-toolbar{flex-wrap:wrap;top:42px}
  .garage-search{flex:1 1 100%}
  .garage-stats{order:3}
}
@media (max-width:680px){
  .garage-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .topnav{padding:0 12px;overflow-x:auto}
  .nav-link{padding:12px 10px}
}

/* ============================================================
   Unified Challenge Detail page (/challenge/<id>)
   ============================================================ */
.cd-page{max-width:1080px;margin:0 auto;padding:0 24px 80px}
.cd-hero{display:grid;grid-template-columns:1.2fr 1fr;gap:0;align-items:stretch;margin:24px 0 36px;border:1px solid var(--ink);box-shadow:5px 5px 0 var(--ink);background:var(--surface);overflow:hidden}
.cd-hero-media{position:relative;min-height:340px;overflow:hidden;background:#000}
.cd-hero-img{width:100%;height:100%;object-fit:cover;display:block;min-height:340px}
.cd-hero-fallback{width:100%;height:100%;min-height:340px}
.cd-hero-body{padding:28px 30px 28px;display:flex;flex-direction:column;gap:14px}
.cd-back{display:inline-flex;align-self:flex-start;font:600 11px/1 var(--body);letter-spacing:0.6px;color:var(--ink-3);text-decoration:none;padding:5px 0;transition:color .12s}
.cd-back:hover{color:var(--ink)}
.cd-tag{font:700 10.5px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--accent);margin:0}
.cd-title{font:800 42px/1 var(--display);letter-spacing:-0.6px;text-transform:uppercase;color:var(--ink);margin:0;font-stretch:condensed}
.cd-sub{font:500 14px/1.4 var(--body);color:var(--ink-3);margin:-4px 0 4px;letter-spacing:0}
.cd-scenario{font:400 14px/1.65 var(--body);color:var(--ink-2);margin:0}
.cd-goal{font:500 13px/1.5 var(--body);color:var(--ink);background:var(--gold);padding:10px 12px 10px 13px;border-left:3px solid var(--gold-rim);margin:6px 0 0;display:flex;flex-wrap:wrap;align-items:baseline;gap:8px}
.cd-goal-lbl{font-weight:700;text-transform:uppercase;letter-spacing:1px;font-size:9.5px;color:var(--gold-rim)}
.cd-actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.cd-btn-launch{flex:0 0 auto;width:auto;padding:13px 26px;letter-spacing:2px}

.cd-section{margin:0 0 36px}
.cd-h2{font:800 22px/1.05 var(--display);letter-spacing:-0.3px;text-transform:uppercase;color:var(--ink);margin:0 0 16px;padding:0 0 8px;border-bottom:1px solid var(--border)}

.cd-times{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.cd-time{padding:18px 18px 16px;background:var(--surface);border:1px solid var(--border);border-radius:3px;display:flex;flex-direction:column;gap:5px;transition:border-color .12s}
.cd-time:hover{border-color:var(--ink-3)}
.cd-time-you{border-color:var(--ink);background:#fff;border-left:4px solid var(--max);padding-left:16px}
.cd-time-lbl{font:700 9.5px/1 var(--body);letter-spacing:1.3px;text-transform:uppercase;color:var(--ink-3)}
.cd-time-val{font:800 36px/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-1.5px;color:var(--ink)}
.cd-time-ctx{font:500 11.5px/1.4 var(--body);color:var(--ink-3);margin-top:2px}
.cd-time-gap{font:700 13px/1 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:0;margin-top:4px;color:var(--ink-3);padding:4px 8px;align-self:flex-start;border-radius:2px;background:var(--paper)}
.cd-time-gap.is-under{background:#dcfce7;color:#15803d}
.cd-time-gap.is-near{background:#fef9c3;color:#854d0e}
.cd-time-gap.is-mid{background:#ffedd5;color:#9a3412}
.cd-time-gap.is-far{background:#fee2e2;color:#991b1b}

.cd-specs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:0;border:1px solid var(--border);border-radius:3px;background:#fff;overflow:hidden}
.cd-spec{padding:12px 16px;border-right:1px solid var(--border);border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:4px;min-width:0}
.cd-spec:last-child{border-right:0}
.cd-spec-lbl{font:700 9.5px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-4)}
.cd-spec-val{font:600 14px/1.3 var(--body);color:var(--ink);overflow:hidden;text-overflow:ellipsis}

.cd-setup{display:flex;flex-direction:column;gap:0;border:1px solid var(--border);border-radius:3px;background:#fff}
.cd-setup-row{display:grid;grid-template-columns:140px 1fr;gap:16px;padding:12px 16px;border-bottom:1px solid var(--border);align-items:baseline}
.cd-setup-row:last-child{border-bottom:0}
.cd-setup-lbl{font:700 10px/1 var(--body);letter-spacing:1.3px;text-transform:uppercase;color:var(--ink-4)}
.cd-setup-val{font:500 13.5px/1.5 var(--body);color:var(--ink-2)}

.cd-tbl{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--border);border-radius:3px;overflow:hidden}
.cd-tbl th{font:700 9.5px/1 var(--body);letter-spacing:1.3px;text-transform:uppercase;color:var(--ink-4);text-align:left;padding:11px 14px;background:var(--paper);border-bottom:1px solid var(--border);white-space:nowrap}
.cd-tbl td{font:500 13px/1.5 var(--body);color:var(--ink-2);padding:10px 14px;border-bottom:1px solid var(--border);vertical-align:top}
.cd-tbl tr:last-child td{border-bottom:0}
.cd-tbl tr:hover td{background:var(--paper)}
.cd-tbl-num{color:var(--ink-4);font-weight:700}
.cd-tbl-pb{font-weight:700;color:var(--ink)}
.cd-tbl-delta.is-under,.cd-tbl-gap.is-under{color:#15803d}
.cd-tbl-delta.is-near,.cd-tbl-gap.is-near{color:#854d0e}
.cd-tbl-delta.is-mid,.cd-tbl-gap.is-mid{color:#9a3412}
.cd-tbl-delta.is-far,.cd-tbl-gap.is-far{color:#991b1b}
.cd-tbl-note{color:var(--ink-3);font-size:12.5px;font-style:italic}

/* Weapon · Circuit panel — shows the actual car & track previews */
.cd-machines{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.cd-machine{background:#fff;border:1px solid var(--border);border-radius:3px;overflow:hidden;display:flex;flex-direction:column;transition:border-color .12s,box-shadow .12s}
.cd-machine:hover{border-color:var(--ink-3);box-shadow:0 1px 3px rgba(0,0,0,0.06)}
.cd-machine-img-wrap{aspect-ratio:16/9;position:relative;overflow:hidden;background:#0f172a}
.cd-machine-img{width:100%;height:100%;object-fit:cover;display:block}
.cd-machine-fallback{background:linear-gradient(135deg,#1f2937,#0f172a)}
.cd-machine-tag{position:absolute;top:8px;left:8px;background:var(--ink);color:#fff;font:700 9px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;padding:4px 8px 3px;border-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,0.25)}
.cd-machine-body{padding:12px 14px 14px;display:flex;flex-direction:column;gap:5px}
.cd-machine-chassis-lbl{font:700 8.5px/1 var(--body);letter-spacing:1.5px;text-transform:uppercase;color:var(--ink-4);margin:0}
.cd-machine-name{font:700 15px/1.25 var(--body);color:var(--ink);margin:0;letter-spacing:-0.1px}
.cd-machine-sub{font:500 11px/1.3 var(--body);color:var(--ink-3);margin:0;letter-spacing:0.2px;text-transform:uppercase}
.cd-livery{font:500 11.5px/1.4 var(--body);color:var(--ink-2);margin:6px 0 0;padding:7px 9px;background:var(--paper);border-left:3px solid var(--max);display:flex;flex-wrap:wrap;align-items:baseline;gap:6px}
.cd-livery-lbl{font:700 8.5px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--ink-4);margin-right:4px}
.cd-livery-num{font-family:var(--mono);font-weight:700;color:var(--max)}
.cd-livery-driver{font-weight:600}
.cd-machine-meta{display:flex;flex-wrap:wrap;gap:0;border-top:1px solid var(--border);margin-top:6px;padding-top:8px}
.cd-machine-meta-row{flex:1 1 50%;display:flex;justify-content:space-between;align-items:baseline;gap:8px;padding:3px 0;font:500 11.5px/1.3 var(--body);min-width:0}
.cd-machine-meta-row span{color:var(--ink-4);font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:1px}
.cd-machine-meta-row strong{color:var(--ink);font-weight:700;font-size:12.5px;font-family:var(--mono);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

.cd-story-empty{background:var(--paper);border:1px dashed var(--ink-4);padding:22px 24px;border-radius:3px}
.cd-story-empty .cd-h2{border:0;padding:0;margin:0 0 8px}
.cd-empty-msg{font:500 14px/1.5 var(--body);color:var(--ink-2);margin:0 0 8px}
.cd-empty-hint{font:400 12.5px/1.5 var(--body);color:var(--ink-3);margin:0}

@media (max-width:920px){
  .cd-hero{grid-template-columns:1fr}
  .cd-hero-media,.cd-hero-img,.cd-hero-fallback{min-height:240px}
  .cd-title{font-size:32px}
  .cd-page{padding:0 16px 60px}
}

/* Footer signature */
.foot{padding:24px 28px 40px;border-top:1px solid var(--rule);font:600 11px/1.4 var(--body);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.foot a{color:var(--ink);text-decoration:none;border-bottom:2px solid var(--max);padding-bottom:1px}

/* Always 3 columns. Cards shrink with the viewport. */
@media (max-width:920px){
  .hero{grid-template-columns:1fr;gap:18px}
  .hero-r{border-left:0;border-top:2.5px solid var(--ink);padding:18px 0 0}
  .hero-r::before{left:0;top:-13px}
  .hero-title{font-size:44px}
}
@media (max-width:680px){
  .hero-title{font-size:34px}
  .hero-count{font-size:48px}
  .grid{padding:14px 10px 48px;gap:8px}
  .card-body{padding:8px 9px}
  .card-title{font-size:16px}
  .section-head{padding:14px 10px 6px;flex-direction:column;align-items:flex-start;gap:6px}
  .section-deck{text-align:left}
}
"""

JS = """
async function launchConfig(id, title, cmd){
  const t = document.getElementById('toast');
  t.textContent = 'LAUNCHING ' + title + ' …';
  t.classList.remove('err');
  t.classList.add('show');
  try {
    let url = '/launch?id=' + encodeURIComponent(id);
    if (cmd) { url += '&cmd=' + encodeURIComponent(cmd); }
    const r = await fetch(url, {method:'POST'});
    const j = await r.json();
    if (j.ok){
      t.textContent = 'LAUNCHED · ' + title + ' · AC STARTING';
    } else {
      t.classList.add('err');
      t.textContent = 'ERROR · ' + (j.msg || 'unknown');
    }
  } catch(e){
    t.classList.add('err');
    t.textContent = 'ERROR · ' + e.message;
  }
  setTimeout(() => t.classList.remove('show'), 4500);
}

async function openDash(rel, title){
  const t = document.getElementById('toast');
  try {
    const r = await fetch('/open?path=' + encodeURIComponent(rel), {method:'POST'});
    const j = await r.json();
    if (j.ok){
      t.textContent = 'OPENED · ' + title + ' DASHBOARD';
      t.classList.remove('err');
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 3000);
    } else {
      t.classList.add('err');
      t.textContent = 'ERROR · ' + (j.msg || 'unknown');
      t.classList.add('show');
      setTimeout(() => t.classList.remove('show'), 4000);
    }
  } catch(e){
    t.classList.add('err');
    t.textContent = 'ERROR · ' + e.message;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 4000);
  }
}

function startCarousels(){
  document.querySelectorAll('.carousel').forEach((c, idx) => {
    const slides = c.querySelectorAll('.carousel-slide');
    const dots = c.querySelectorAll('.carousel-dot');
    if (slides.length < 2) return;
    let i = 0;
    const interval = 3500 + idx * 350; // stagger when multiple carousels
    setInterval(() => {
      slides[i].classList.remove('is-active');
      if (dots[i]) dots[i].classList.remove('is-active');
      i = (i + 1) % slides.length;
      slides[i].classList.add('is-active');
      if (dots[i]) dots[i].classList.add('is-active');
    }, interval);
  });
}
document.addEventListener('DOMContentLoaded', startCarousels);
"""


def _series_countdown_html(series, today=None):
    """Return a small T-MINUS / LIVE chip for a series with a countdown spec, else ''."""
    cd = series.get("countdown")
    if not cd:
        return ""
    today = today or date.today()
    start, end = cd["start"], cd["end"]
    title = cd.get("title", "")
    window = cd.get("window", "")
    if today < start:
        d = (start - today).days
        head = f'<span class="countdown">T-MINUS {d}D</span>'
        tail = f'<span>{escape(window)} · {escape(title)}</span>' if (window or title) else ""
        return f'<div class="hero-strip">{head}{tail}</div>'
    if today <= end:
        return f'<div class="hero-strip"><span class="live">LIVE NOW</span><span>{escape(title)}</span></div>'
    return ""


def render_ticker():
    today = date.today().strftime("%a %d %b %Y").upper()
    return (
        '<div class="ticker">'
        f'<div class="ticker-l">PABLO SUZARTE · SIM RACING CHALLENGES · {today}</div>'
        f'<div class="ticker-r">{len(CONFIGS)} CHALLENGES LOADED</div>'
        '</div>'
    )


_BH_BG_PHOTOS = (
    "senna_vs_prost_suzuka_1988.jpg",
    "race_1993_spa_grid.jpg",
    "verstappen_1v1.jpg",
    "hotlap_supergt_fuji.jpg",
    "senna_donington_1993.jpg",
)

def render_hero():
    series_count = len({c.get("series") for c in CONFIGS if c.get("series")})
    n_race  = sum(1 for c in CONFIGS if c["type"] == "RACE")
    n_hot   = sum(1 for c in CONFIGS if c["type"] == "HOTLAP")
    n_duel  = sum(1 for c in CONFIGS if c["type"] == "DUEL")
    total   = len(CONFIGS)

    # Cinematic background carousel — reuses the existing .carousel JS.
    bg_slides = "".join(
        f'<img src="/images/{escape(name)}" alt="" '
        f'class="carousel-slide{" is-active" if i == 0 else ""}" '
        f'loading="{"eager" if i == 0 else "lazy"}">'
        for i, name in enumerate(_BH_BG_PHOTOS)
    )

    return (
        '<header class="bighero">'
        f'<div class="bh-bg carousel">{bg_slides}</div>'
        '<div class="bh-overlay"></div>'
        '<div class="bh-grain"></div>'
        '<div class="bh-stripe"></div>'

        '<div class="bh-wrap">'

        # LEFT — pitch
        '<div class="bh-l">'
        '<div class="bh-bib">'
        '<span class="bh-num">#33</span>'
        '<span>Pablo Suzarte · Multi-series Sim Racing</span>'
        '<span class="bh-rule"></span>'
        '</div>'
        '<span class="bh-tag">The catalog · live</span>'
        '<h1 class="bh-title">'
        '<span class="ln">Pick a challenge.</span>'
        '<span class="ln">Go racing.</span>'
        '<span class="ln">Leave <span class="accent">your time.</span></span>'
        '</h1>'
        '<p class="bh-blurb">'
        f'A personal archive of <b>{total} recreated scenarios</b> — F1 grids, hotlap chases and 1v1 grudge matches. '
        'One click launches Assetto Corsa with the right car, livery, weather and AI baked in. '
        'Drive the lap, log the time, then come back and beat it.'
        '</p>'
        '<div class="bh-loop">'
        '<div class="bh-step">'
        '<div class="bh-step-n">1</div>'
        '<div class="bh-step-txt">'
        '<div class="bh-step-k">Pick</div>'
        '<div class="bh-step-d">A grid, a hotlap or a 1v1 duel</div>'
        '</div></div>'
        '<div class="bh-step">'
        '<div class="bh-step-n">2</div>'
        '<div class="bh-step-txt">'
        '<div class="bh-step-k">Race</div>'
        '<div class="bh-step-d">AC opens with the scenario pre-loaded</div>'
        '</div></div>'
        '<div class="bh-step">'
        '<div class="bh-step-n">3</div>'
        '<div class="bh-step-txt">'
        '<div class="bh-step-k">Beat it</div>'
        '<div class="bh-step-d">Lap auto-logged · chase the benchmark</div>'
        '</div></div>'
        '</div>'
        '</div>'

        # RIGHT — stat slab + CTA
        '<div class="bh-r">'
        '<div class="bh-slab">'
        '<div class="bh-slab-lbl">Challenges loaded · ready to launch</div>'
        f'<div class="bh-slab-num">{total:02d}</div>'
        '<div class="bh-slab-row">'
        f'<div class="bh-slab-cell is-race"><span class="bh-slab-cell-v">{n_race}</span><span class="bh-slab-cell-l">Race</span></div>'
        f'<div class="bh-slab-cell is-hot"><span class="bh-slab-cell-v">{n_hot}</span><span class="bh-slab-cell-l">Hotlap</span></div>'
        f'<div class="bh-slab-cell is-duel"><span class="bh-slab-cell-v">{n_duel}</span><span class="bh-slab-cell-l">1v1</span></div>'
        f'<div class="bh-slab-cell is-ser"><span class="bh-slab-cell-v">{series_count}</span><span class="bh-slab-cell-l">Series</span></div>'
        '</div>'
        '</div>'
        '</div>'
        '</div>'
        '</header>'
        '<a id="challenges"></a>'
    )


def render_series_head(series, today=None):
    countdown = _series_countdown_html(series, today)
    return (
        '<div class="section-head">'
        '<div class="section-head-l">'
        f'<h2 class="section-title">{escape(series["label"])}</h2>'
        f'{countdown}'
        '</div>'
        f'<p class="section-deck">{escape(series.get("deck", ""))}</p>'
        '</div>'
    )


def _img_block(cfg):
    images = cfg.get("images") or []
    if images:
        slides = "".join(
            f'<img src="/images/{escape(name)}" alt="{escape(cfg["title"])}" '
            f'class="carousel-slide{" is-active" if i == 0 else ""}">'
            for i, name in enumerate(images)
        )
        dots = "".join(
            f'<span class="carousel-dot{" is-active" if i == 0 else ""}"></span>'
            for i in range(len(images))
        )
        return (
            f'<div class="carousel">{slides}'
            f'<div class="carousel-dots">{dots}</div></div>'
        )
    img_path = IMAGES_DIR / f"{cfg['id']}.jpg"
    if img_path.exists():
        return f'<img src="/images/{cfg["id"]}.jpg" alt="{escape(cfg["title"])}">'
    style = f"--ca:{cfg['color_a']};--cb:{cfg['color_b']}"
    return (
        f'<div class="card-img-fallback" style="{style}">'
        f'<div class="fb-track">{escape(cfg["track_label"])}</div>'
        f'<div class="fb-meta">{escape(cfg["specs"]["CAR"])}</div>'
        f'</div>'
    )


_SETUP_ROWS = (
    ("trim",     "Trim",     "is-trim"),
    ("priority", "Priority", ""),
    ("key",      "Key",      ""),
)


# ---- Lap-time helpers ------------------------------------------------------

def _fmt_ms(ms):
    """Format ms → 'M:SS.mmm' (or 'SS.mmm' if under a minute)."""
    if ms is None or ms <= 0:
        return None
    total_s, rem = divmod(int(ms), 1000)
    m, s = divmod(total_s, 60)
    if m:
        return f"{m}:{s:02d}.{rem:03d}"
    return f"{s}.{rem:03d}"


def _parse_time_str(t):
    """Parse 'M:SS.mmm' or 'SS.mmm' → ms. None on failure."""
    if not t:
        return None
    try:
        if ":" in t:
            mm, ss = t.split(":", 1)
            return int(mm) * 60_000 + int(round(float(ss) * 1000))
        return int(round(float(t) * 1000))
    except (ValueError, TypeError):
        return None


def _fmt_diff(ms_you, ms_ref):
    if ms_you is None or ms_ref is None:
        return ""
    delta = ms_you - ms_ref
    sign = "+" if delta >= 0 else "−"
    secs = abs(delta) / 1000.0
    return f"{sign}{secs:.3f}"


_PB_INI_CACHE = {"path": None, "mtime": 0, "data": {}}


def _load_personal_best():
    """Parse personalbest.ini once per file mtime. Returns {section: ms}."""
    pb_path = AC_DOC / "personalbest.ini"
    try:
        st = pb_path.stat()
    except FileNotFoundError:
        return {}
    if _PB_INI_CACHE["path"] == str(pb_path) and _PB_INI_CACHE["mtime"] == st.st_mtime:
        return _PB_INI_CACHE["data"]
    data = {}
    section = None
    try:
        for line in pb_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
            elif line.startswith("TIME=") and section:
                try:
                    data[section] = int(line.split("=", 1)[1])
                except ValueError:
                    pass
    except OSError:
        return {}
    _PB_INI_CACHE.update({"path": str(pb_path), "mtime": st.st_mtime, "data": data})
    return data


def _best_from_history(rel_path):
    """Read the lowest pb_ms from a hotlap history JSON. None on failure."""
    if not rel_path:
        return None
    p = AC_DOC / rel_path
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    best = None
    for r in rows or []:
        v = r.get("pb_ms")
        if isinstance(v, (int, float)) and v > 0 and (best is None or v < best):
            best = int(v)
    return best


def _resolve_your_ms(bm):
    """Pick the best available time for 'you': history JSON beats personalbest.ini."""
    h_ms = _best_from_history(bm.get("you_history"))
    if h_ms is not None:
        return h_ms
    section = bm.get("you_section")
    if section:
        return _load_personal_best().get(section)
    return None


def _load_results_index():
    """Load dashboard/results/index.json (latest result per tile, written by
    launcher/update_results.py after every AC session)."""
    p = AC_DOC / "dashboard" / "results" / "index.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _render_times_block(cfg):
    bm = cfg.get("benchmarks") or {}
    your_ms = _challenge_pb_ms(cfg) if bm else None
    your_str = _fmt_ms(your_ms) if your_ms else None
    refs = bm.get("refs") or []

    # Latest auto-captured result for this tile (post-AC-exit snapshot).
    last = _load_results_index().get(cfg.get("id"))
    last_summary = last.get("summary") if last else None
    last_ts = last.get("ts") if last else None

    # If neither benchmarks nor a captured last-result exists, render nothing.
    if not bm and not last_summary:
        return ""

    rows_html = []

    # Your row first — bold, larger
    you_lbl = bm.get("you_label", "Your PB") if bm else "Your PB"
    rows_html.append(
        '<div class="time-row is-you">'
        f'<span class="time-lbl">{escape(you_lbl)}</span>'
        f'<span class="time-val">{escape(your_str) if your_str else "—"}</span>'
        '<span class="time-diff"></span>'
        '</div>'
    )

    # Auto-captured "Last session" / "Last result" row.
    if last_summary:
        # Format last_ts (yyyyMMdd-HHmmss) → "DD MMM"
        ts_label = ""
        if last_ts and len(last_ts) >= 8:
            try:
                dt = datetime.strptime(last_ts[:8], "%Y%m%d")
                ts_label = dt.strftime("%d %b").upper()
            except Exception:
                pass

        finish = last_summary.get("finish")
        field = last_summary.get("field")
        best = last_summary.get("best_lap")
        is_solo = (cfg.get("type") == "HOTLAP") or (field and field <= 1)
        if is_solo:
            row_lbl = "Last session"
            row_val = best or "—"
            row_diff = ts_label
        else:
            # RACE / DUEL: show finish position prominently
            pos_str = f"P{finish}/{field}" if finish and field else "—"
            row_lbl = "Last result"
            row_val = pos_str
            row_diff = (best or "") + ((" · " + ts_label) if best and ts_label else (ts_label or ""))
        rows_html.append(
            '<div class="time-row is-last">'
            f'<span class="time-lbl">{escape(row_lbl)}</span>'
            f'<span class="time-val">{escape(row_val)}</span>'
            f'<span class="time-diff">{escape(row_diff)}</span>'
            '</div>'
        )

    # Reference rows with diff vs you
    for r in refs:
        ref_str = r.get("time")
        ref_ms = _parse_time_str(ref_str)
        diff = _fmt_diff(your_ms, ref_ms) if (your_ms and ref_ms) else ""
        rows_html.append(
            '<div class="time-row">'
            f'<span class="time-lbl">{escape(r.get("label", "REF"))}</span>'
            f'<span class="time-val">{escape(ref_str or "—")}</span>'
            f'<span class="time-diff">{escape(diff)}</span>'
            '</div>'
        )
    return (
        '<div class="card-times">'
        '<div class="times-head">Lap Times</div>'
        + "".join(rows_html) +
        '</div>'
    )


def _render_setup_block(cfg):
    setup = cfg.get("setup")
    if not setup:
        return ""
    if isinstance(setup, str):
        # Backwards-compat: legacy string form renders as a single Trim row.
        setup = {"trim": setup}
    rows = "".join(
        f'<span class="setup-row-lbl">{lbl}</span>'
        f'<span class="setup-row-val {cls}">{escape(setup[k])}</span>'
        for (k, lbl, cls) in _SETUP_ROWS if setup.get(k)
    )
    if not rows:
        return ""
    title_text = " · ".join(
        f"{lbl}: {setup[k]}" for (k, lbl, _) in _SETUP_ROWS if setup.get(k)
    )
    return (
        f'<div class="card-setup" title="Car Setup — {escape(title_text)}">'
        f'<div class="setup-head">Car Setup</div>'
        f'{rows}'
        f'</div>'
    )


# Tracks → ISO-2 country code, derived from the spec-strip TRACK string.
_COUNTRY_BY_TRACK_KEYWORD = (
    ("nordschleife",                "DE"),
    ("nürburgring",                 "DE"),
    ("nurburgring",                 "DE"),
    ("montreal",                    "CA"),
    ("circuit gilles villeneuve",   "CA"),
    ("fuji",                        "JP"),
    ("miami",                       "US"),
    ("monza",                       "IT"),
    ("silverstone",                 "GB"),
    ("spa",                         "BE"),
    ("zandvoort",                   "NL"),
    ("suzuka",                      "JP"),
    ("interlagos",                  "BR"),
    ("austin",                      "US"),
    ("cota",                        "US"),
    ("mexico",                      "MX"),
    ("baku",                        "AZ"),
    ("singapore",                   "SG"),
    ("shanghai",                    "CN"),
    ("losail",                      "QA"),
    ("jeddah",                      "SA"),
    ("bahrain",                     "BH"),
    ("abu dhabi",                   "AE"),
    ("imola",                       "IT"),
    ("le mans",                     "FR"),
    ("paul ricard",                 "FR"),
    ("hungaroring",                 "HU"),
)


def _country_for(cfg):
    track = (cfg.get("specs", {}).get("TRACK") or "").lower()
    for kw, code in _COUNTRY_BY_TRACK_KEYWORD:
        if kw in track:
            return code
    return None


_COUNTRY_NAMES = {
    "DE": "GER", "CA": "CAN", "JP": "JPN", "US": "USA", "IT": "ITA",
    "GB": "GBR", "BE": "BEL", "NL": "NED", "BR": "BRA", "MX": "MEX",
    "AZ": "AZE", "SG": "SGP", "CN": "CHN", "QA": "QAT", "SA": "SAU",
    "BH": "BHR", "AE": "UAE", "FR": "FRA", "HU": "HUN",
}


def _flag_svg(code):
    """Inline SVG flag — kept simple so they scale crisply at the chip size."""
    if code == "DE":
        return ('<svg viewBox="0 0 5 3" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="5" height="1" y="0" fill="#000"/>'
                '<rect width="5" height="1" y="1" fill="#DD0000"/>'
                '<rect width="5" height="1" y="2" fill="#FFCE00"/></svg>')
    if code == "JP":
        return ('<svg viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="30" height="20" fill="#fff"/>'
                '<circle cx="15" cy="10" r="6" fill="#BC002D"/></svg>')
    if code == "CA":
        return ('<svg viewBox="0 0 50 25" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="12.5" height="25" fill="#FF0000"/>'
                '<rect x="12.5" width="25" height="25" fill="#fff"/>'
                '<rect x="37.5" width="12.5" height="25" fill="#FF0000"/>'
                '<path d="M25 5 L26.4 9.4 L31 9 L28.5 12.7 L31.7 15.4 L27 14.6 '
                'L26.4 19 L25 16.5 L23.6 19 L23 14.6 L18.3 15.4 L21.5 12.7 '
                'L19 9 L23.6 9.4 Z" fill="#FF0000"/></svg>')
    if code == "US":
        return ('<svg viewBox="0 0 19 10" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="19" height="10" fill="#B22234"/>'
                '<rect width="19" height="0.77" y="0.77" fill="#fff"/>'
                '<rect width="19" height="0.77" y="2.31" fill="#fff"/>'
                '<rect width="19" height="0.77" y="3.85" fill="#fff"/>'
                '<rect width="19" height="0.77" y="5.39" fill="#fff"/>'
                '<rect width="19" height="0.77" y="6.93" fill="#fff"/>'
                '<rect width="19" height="0.77" y="8.47" fill="#fff"/>'
                '<rect width="7.6" height="5.39" fill="#3C3B6E"/></svg>')
    if code == "IT":
        return ('<svg viewBox="0 0 3 2" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="1" height="2" fill="#009246"/>'
                '<rect x="1" width="1" height="2" fill="#fff"/>'
                '<rect x="2" width="1" height="2" fill="#CE2B37"/></svg>')
    if code == "GB":
        return ('<svg viewBox="0 0 60 30" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="60" height="30" fill="#012169"/>'
                '<path d="M0 0 L60 30 M60 0 L0 30" stroke="#fff" stroke-width="6"/>'
                '<path d="M0 0 L60 30 M60 0 L0 30" stroke="#C8102E" stroke-width="2"/>'
                '<path d="M30 0 V30 M0 15 H60" stroke="#fff" stroke-width="10"/>'
                '<path d="M30 0 V30 M0 15 H60" stroke="#C8102E" stroke-width="6"/></svg>')
    if code == "BE":
        return ('<svg viewBox="0 0 3 2" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="1" height="2" fill="#000"/>'
                '<rect x="1" width="1" height="2" fill="#FAE042"/>'
                '<rect x="2" width="1" height="2" fill="#ED2939"/></svg>')
    if code == "NL":
        return ('<svg viewBox="0 0 9 6" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="9" height="2" fill="#AE1C28"/>'
                '<rect width="9" height="2" y="2" fill="#fff"/>'
                '<rect width="9" height="2" y="4" fill="#21468B"/></svg>')
    if code == "FR":
        return ('<svg viewBox="0 0 3 2" xmlns="http://www.w3.org/2000/svg" '
                'preserveAspectRatio="none">'
                '<rect width="1" height="2" fill="#0055A4"/>'
                '<rect x="1" width="1" height="2" fill="#fff"/>'
                '<rect x="2" width="1" height="2" fill="#EF4135"/></svg>')
    return ('<svg viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="30" height="20" fill="#1a1a1a"/></svg>')


def _team_logo_svg(slug: str) -> str:
    """Team mark for dual-driver duel CTAs. Prefers a real logo PNG dropped at
    `launcher/images/<slug>_logo.png` (transparent recommended); falls back to
    a simplified inline SVG so the UI never breaks."""
    if slug:
        custom = IMAGES_DIR / f"{slug}_logo.png"
        if custom.exists():
            return (
                f'<img class="team-logo team-logo-img" '
                f'src="/images/{slug}_logo.png" alt="" loading="lazy">'
            )
    if slug == "mercedes":
        # 3-pointed star inscribed in a circle (Mercedes-AMG mark)
        return (
            '<svg class="team-logo" viewBox="0 0 24 24" '
            'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<circle cx="12" cy="12" r="10.5" fill="none" '
            'stroke="currentColor" stroke-width="1.4"/>'
            '<line x1="12" y1="12" x2="12" y2="2.5" '
            'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
            '<line x1="12" y1="12" x2="20.23" y2="16.75" '
            'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
            '<line x1="12" y1="12" x2="3.77" y2="16.75" '
            'stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>'
            '</svg>'
        )
    if slug == "redbull":
        # Two charging-bull horn silhouettes — abstract enough for inline SVG,
        # recognizably Red Bull when paired with the navy/yellow CTA.
        return (
            '<svg class="team-logo" viewBox="0 0 32 18" '
            'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<path d="M2,16 L8,3 Q9,1.6 10,3 L16,16 Q14,15 13,15 '
            'Q11.5,15 10,16 Q8.5,15 7,15 Q5.5,15 4,16 Q3,15.5 2,16 Z" '
            'fill="currentColor"/>'
            '<path d="M16,16 L22,3 Q23,1.6 24,3 L30,16 Q28,15 27,15 '
            'Q25.5,15 24,16 Q22.5,15 21,15 Q19.5,15 18,16 Q17,15.5 16,16 Z" '
            'fill="currentColor"/>'
            '</svg>'
        )
    if slug == "verstappenracing":
        # Mercedes × Red Bull collab — 3-pointed star + charging-bull horns,
        # split by a thin red divider so both team marks read on one chip.
        return (
            '<svg class="team-logo team-logo-combo" viewBox="0 0 60 22" '
            'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
            'preserveAspectRatio="xMidYMid meet">'
            '<g transform="translate(11,11)">'
            '<circle cx="0" cy="0" r="9" fill="none" stroke="currentColor" stroke-width="1.4"/>'
            '<line x1="0" y1="0" x2="0" y2="-8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
            '<line x1="0" y1="0" x2="6.93" y2="4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
            '<line x1="0" y1="0" x2="-6.93" y2="4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
            '</g>'
            '<line x1="29" y1="3" x2="29" y2="19" stroke="#D40E10" stroke-width="1.5"/>'
            '<g transform="translate(33,5)">'
            '<path d="M2,15 L7,3 Q8,1.6 9,3 L14,15 Q12.5,14 11.5,14 '
            'Q10.3,14 9,15 Q7.7,14 6.5,14 Q5.3,14 4,15 Q3,14.5 2,15 Z" '
            'fill="currentColor"/>'
            '<path d="M14,15 L19,3 Q20,1.6 21,3 L26,15 Q24.5,14 23.5,14 '
            'Q22.3,14 21,15 Q19.7,14 18.5,14 Q17.3,14 16,15 Q15,14.5 14,15 Z" '
            'fill="currentColor"/>'
            '</g>'
            '</svg>'
        )
    if slug == "audi":
        # Four interlocking rings — the iconic Audi mark.
        return (
            '<svg class="team-logo" viewBox="0 0 36 10" '
            'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" '
            'preserveAspectRatio="xMidYMid meet">'
            '<circle cx="5" cy="5" r="3.6" fill="none" '
            'stroke="currentColor" stroke-width="1"/>'
            '<circle cx="13" cy="5" r="3.6" fill="none" '
            'stroke="currentColor" stroke-width="1"/>'
            '<circle cx="21" cy="5" r="3.6" fill="none" '
            'stroke="currentColor" stroke-width="1"/>'
            '<circle cx="29" cy="5" r="3.6" fill="none" '
            'stroke="currentColor" stroke-width="1"/>'
            '</svg>'
        )
    return ""


def _render_card_stats_v2(cfg):
    """Slim 2-row stats block for v2 cards: YOUR PB on top (gold), best
    reference below (muted, with diff). Returns empty string if no data."""
    bm = cfg.get("benchmarks") or {}
    your_ms = _challenge_pb_ms(cfg) if bm else None
    your_str = _fmt_ms(your_ms) if your_ms else None
    refs = bm.get("refs") or []

    # Pick the first ref with a usable time (some refs are notes only).
    ref = None
    for r in refs:
        if r.get("time") and _parse_time_str(r["time"]) is not None:
            ref = r
            break

    if not your_str and not ref and not refs:
        return ""

    rows = []
    if your_str:
        rows.append(
            '<div class="row">'
            '<span class="you-k">Your PB</span>'
            f'<span class="you-v">{escape(your_str)}</span>'
            '<span class="you-d"></span>'
            '</div>'
        )
    elif refs or bm:
        rows.append('<div class="empty">No lap logged yet · go set one</div>')

    if ref:
        ref_str = ref["time"]
        ref_ms = _parse_time_str(ref_str)
        diff = _fmt_diff(your_ms, ref_ms) if (your_ms and ref_ms) else ""
        rows.append(
            '<div class="row">'
            f'<span class="ref-k">{escape(ref.get("label", "Ref"))}</span>'
            f'<span class="ref-v">{escape(ref_str)}</span>'
            f'<span class="ref-d">{escape(diff)}</span>'
            '</div>'
        )
    elif refs and refs[0].get("time"):
        # Note-only ref (e.g., "no Max ref on 24h layout yet"): show as caption.
        rows.append(
            '<div class="empty">'
            f'{escape(refs[0].get("label", "Ref"))} · {escape(refs[0]["time"])}'
            '</div>'
        )

    if not rows:
        return ""
    return f'<div class="cv2-stats">{"".join(rows)}</div>'


def _build_meta_row(label, value):
    if not value:
        return ""
    return (
        f'<dt>{escape(label)}</dt>'
        f'<dd title="{escape(value)}">{escape(value)}</dd>'
    )


def render_card(cfg):
    type_cls = cfg["type"].lower()
    type_label = cfg.get("type_label", cfg["type"])
    specs = cfg.get("specs", {})

    # WHERE → TRACK · CAR → CAR · AI → GRID + LAPS combined into one tight line.
    grid = specs.get("GRID", "").strip()
    laps = specs.get("LAPS", "").strip()
    if grid and laps:
        ai_value = f"{grid} · {laps}"
    else:
        ai_value = grid or laps

    meta_html = (
        _build_meta_row("Where", specs.get("TRACK", ""))
        + _build_meta_row("Car",  specs.get("CAR", ""))
        + _build_meta_row("AI",   ai_value)
    )

    # Launch CTA(s): if the cfg defines `launchers: [{label, logo, cmd}, ...]`,
    # render one team-branded CTA per entry. Otherwise fall back to a single
    # red LAUNCH button that fires the primary `launcher` field.
    launchers = cfg.get("launchers")
    if launchers:
        launch_block = '<div class="card-launchers">'
        for lc in launchers:
            label = lc.get("label", "LAUNCH")
            logo = lc.get("logo", "")
            cmd = lc.get("cmd", "")
            launch_block += (
                f'<button class="btn-launch-team {escape(logo)}" '
                f'onclick="launchConfig({escape(json.dumps(cfg["id"]))},'
                f'{escape(json.dumps(cfg["title"] + " · " + label))},'
                f'{escape(json.dumps(cmd))})">'
                f'{_team_logo_svg(logo)}'
                f'<span>{escape(label)}</span>'
                f'<span class="team-go">GO ▶</span>'
                f'</button>'
            )
        launch_block += '</div>'
    else:
        launch_block = (
            f'<button class="btn-launch" onclick="launchConfig('
            f'{escape(json.dumps(cfg["id"]))},'
            f'{escape(json.dumps(cfg["title"]))})">LAUNCH</button>'
        )

    # Optional WATCH video links — kept as small text-only links beside MORE DETAILS.
    video_links = ""
    for v in cfg.get("videos") or []:
        if isinstance(v, str):
            label, url = "WATCH", v
        else:
            label, url = v.get("label", "WATCH"), v["url"]
        video_links += (
            f'<a class="cv2-more" target="_blank" rel="noopener noreferrer" '
            f'href="{escape(url)}" title="Watch context video"'
            f' style="margin-left:14px">{escape(label)} ▶</a>'
        )

    cc = _country_for(cfg)
    if cc:
        country_name = _COUNTRY_NAMES.get(cc, cc)
        country_chip = (
            f'<span class="card-country-chip" title="{escape(country_name)}">'
            f'<span class="ccc-flag">{_flag_svg(cc)}</span>'
            f'<span class="ccc-code">{escape(country_name)}</span>'
            f'</span>'
        )
    else:
        country_chip = ""

    return (
        f'<article class="card cv2 cv2-{type_cls}">'
        '<div class="card-img cv2-img">'
        f'<span class="card-type-chip {type_cls}">{escape(type_label)}</span>'
        f'{country_chip}'
        f'{_img_block(cfg)}'
        '<div class="cv2-shade"></div>'
        f'<h3 class="cv2-title">{escape(cfg["title"])}</h3>'
        '</div>'
        '<div class="cv2-body">'
        f'<dl class="cv2-meta">{meta_html}</dl>'
        '<div class="cv2-actions">'
        f'{launch_block}'
        '</div>'
        '<div>'
        f'<a class="cv2-more" href="/challenge/{escape(cfg["id"])}" '
        f'title="Open the unified challenge dashboard">More details</a>'
        f'{video_links}'
        '</div>'
        + _render_card_stats_v2(cfg) +
        '</div>'
        '</article>'
    )


def render_foot():
    return (
        '<footer class="foot">'
        '<div>PABLO SUZARTE · SIM RACING CHALLENGES · LOCALHOST:' + str(PORT) + '</div>'
        '<div>DROP IMAGES INTO <code>launcher/images/&lt;ID&gt;.JPG</code> TO REPLACE FALLBACKS</div>'
        '</footer>'
    )


def render_nav(active="challenges"):
    """Top nav strip — sits above the ticker on every page."""
    items = [
        ("challenges", "/", "CHALLENGES"),
        ("cars", "/cars", "GARAGE · CARS"),
        ("tracks", "/tracks", "GARAGE · TRACKS"),
        ("moza", "/moza", "WHEEL · MOZA"),
    ]
    links = "".join(
        f'<a class="nav-link{" is-active" if k == active else ""}" '
        f'href="{href}">{label}</a>'
        for k, href, label in items
    )
    return f'<nav class="topnav">{links}</nav>'


def _common_head(title):
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        f'<title>{escape(title)}</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
        '<link rel="alternate icon" href="/favicon.ico">'
        '<meta name="theme-color" content="#D40E10">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900&family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">'
        f'<style>{CSS}</style>'
        '</head><body>'
    )


SERIES_ORDER = [
    "F1", "OPEN-WHEEL", "INDYCAR",
    "GT3", "GT4", "GTE", "GT500", "GT300", "GT1",
    "LMP1", "LMP2", "LMP", "HYPERCAR", "SUPERCAR",
    "DTM", "TCR", "TOURING", "STOCK",
    "RALLY", "DRIFT", "VINTAGE",
    "RACE",
    "HOT HATCH", "STREET", "OTHER",
]
ERA_ORDER = ["2020s", "2010s", "2000s", "1990s", "1980s", "1970s", "1960s", "Pre-1960"]


def _fopt(filter_key, value, count):
    return (
        f'<button class="fopt" data-filter="{escape(filter_key)}" '
        f'data-value="{escape(value)}">'
        f'<span class="fopt-label">{escape(value)}</span>'
        f'<span class="fopt-count">{count}</span></button>'
    )


def render_cars_page():
    cars = _index_cars()
    from collections import Counter
    brands = Counter(c["brand"] for c in cars if c["brand"])
    series = Counter(c["series"] for c in cars)
    eras = Counter(c.get("era") for c in cars if c.get("era"))
    series_present = [s for s in SERIES_ORDER if series.get(s)]
    eras_present = [e for e in ERA_ORDER if eras.get(e)]
    sorted_brands = [b for b, _ in brands.most_common()]

    cards = "".join(_render_car_tile(c) for c in cars)
    series_opts = "".join(_fopt("series", s, series[s]) for s in series_present)
    era_opts = "".join(_fopt("era", e, eras[e]) for e in eras_present)
    brand_opts = "".join(_fopt("brand", b, brands[b]) for b in sorted_brands)

    return (
        f'{_common_head("Garage · Cars · " + str(len(cars)))}'
        f'{render_nav("cars")}'
        f'{render_ticker()}'
        '<header class="hero garage-hero">'
        '<div class="hero-l">'
        '<div class="hero-kicker">PABLO\'S GARAGE</div>'
        '<h1 class="hero-title">YOUR <span class="accent">CARS</span></h1>'
        f'<div class="hero-sub">{len(cars)} cars · {len(series_present)} series · '
        f'{len(eras_present)} eras · {len(sorted_brands)} brands</div>'
        '</div>'
        '<div class="hero-r">'
        '<div class="hero-count-lbl">CARS INDEXED</div>'
        f'<div class="hero-count">{len(cars)}</div>'
        '<div class="hero-count-meta">use the sidebar to drill down</div>'
        '</div>'
        '</header>'
        '<div class="garage-toolbar">'
        '<input id="garage-search" class="garage-search" type="search" '
        f'placeholder="Search {len(cars)} cars by name, brand, tag, ID…">'
        '<select id="garage-sort" class="garage-sort">'
        '<option value="name">Sort: A → Z</option>'
        '<option value="year-new">Sort: Newest first</option>'
        '<option value="year-old">Sort: Oldest first</option>'
        '<option value="bhp-high">Sort: BHP (high → low)</option>'
        '</select>'
        f'<div class="garage-stats">Showing <strong id="garage-count">{len(cars)}</strong> of {len(cars)}</div>'
        '<button class="garage-reset" type="button">Reset</button>'
        '</div>'
        '<div class="garage-active-pills" id="active-pills"></div>'
        '<div class="garage-layout">'
        '<aside class="garage-sidebar">'
        f'<div class="ffacet"><h4 class="ffacet-h">Series<span class="ffacet-c">{len(series_present)}</span></h4>'
        f'<div class="ffacet-list">{series_opts}</div></div>'
        f'<div class="ffacet"><h4 class="ffacet-h">Era<span class="ffacet-c">{len(eras_present)}</span></h4>'
        f'<div class="ffacet-list">{era_opts}</div></div>'
        f'<div class="ffacet"><h4 class="ffacet-h">Brand<span class="ffacet-c">{len(sorted_brands)}</span></h4>'
        '<input id="brand-search" class="ffacet-search" type="search" placeholder="Filter brands…">'
        f'<div class="ffacet-list ffacet-list-scroll">{brand_opts}</div></div>'
        '</aside>'
        f'<main class="garage-grid">{cards}</main>'
        '</div>'
        '<div id="toast" class="toast"></div>'
        f'<script>{JS}{GARAGE_JS}</script>'
        '</body></html>'
    )


def render_tracks_page():
    tracks = _index_tracks()
    from collections import Counter
    countries = Counter(t["country"] for t in tracks if t["country"])
    cats = Counter(t["category"] for t in tracks)
    eras = Counter(t.get("era") for t in tracks if t.get("era"))
    CAT_ORDER = ["F1 GP", "NORD", "LE MANS", "ENDURANCE", "OVAL",
                 "STREET", "RALLY", "DRIFT", "ROAD"]
    cats_present = [c for c in CAT_ORDER if cats.get(c)]
    eras_present = [e for e in ERA_ORDER if eras.get(e)]
    sorted_countries = [c for c, _ in countries.most_common()]

    cards = "".join(_render_track_tile(t) for t in tracks)
    cat_opts = "".join(_fopt("category", c, cats[c]) for c in cats_present)
    era_opts = "".join(_fopt("era", e, eras[e]) for e in eras_present)
    country_opts = "".join(_fopt("country", c, countries[c]) for c in sorted_countries)

    return (
        f'{_common_head("Garage · Tracks · " + str(len(tracks)))}'
        f'{render_nav("tracks")}'
        f'{render_ticker()}'
        '<header class="hero garage-hero">'
        '<div class="hero-l">'
        '<div class="hero-kicker">PABLO\'S GARAGE</div>'
        '<h1 class="hero-title">YOUR <span class="accent">TRACKS</span></h1>'
        f'<div class="hero-sub">{len(tracks)} tracks · {len(cats_present)} categories · '
        f'{len(eras_present)} eras · {len(sorted_countries)} countries</div>'
        '</div>'
        '<div class="hero-r">'
        '<div class="hero-count-lbl">TRACKS INDEXED</div>'
        f'<div class="hero-count">{len(tracks)}</div>'
        '<div class="hero-count-meta">use the sidebar to drill down</div>'
        '</div>'
        '</header>'
        '<div class="garage-toolbar">'
        '<input id="garage-search" class="garage-search" type="search" '
        f'placeholder="Search {len(tracks)} tracks by name, country, city, ID…">'
        '<select id="garage-sort" class="garage-sort">'
        '<option value="name">Sort: A → Z</option>'
        '<option value="year-new">Sort: Newest first</option>'
        '<option value="year-old">Sort: Oldest first</option>'
        '<option value="length-long">Sort: Length (long → short)</option>'
        '</select>'
        f'<div class="garage-stats">Showing <strong id="garage-count">{len(tracks)}</strong> of {len(tracks)}</div>'
        '<button class="garage-reset" type="button">Reset</button>'
        '</div>'
        '<div class="garage-active-pills" id="active-pills"></div>'
        '<div class="garage-layout">'
        '<aside class="garage-sidebar">'
        f'<div class="ffacet"><h4 class="ffacet-h">Category<span class="ffacet-c">{len(cats_present)}</span></h4>'
        f'<div class="ffacet-list">{cat_opts}</div></div>'
        f'<div class="ffacet"><h4 class="ffacet-h">Era<span class="ffacet-c">{len(eras_present)}</span></h4>'
        f'<div class="ffacet-list">{era_opts}</div></div>'
        f'<div class="ffacet"><h4 class="ffacet-h">Country<span class="ffacet-c">{len(sorted_countries)}</span></h4>'
        '<input id="brand-search" class="ffacet-search" type="search" placeholder="Filter countries…">'
        f'<div class="ffacet-list ffacet-list-scroll">{country_opts}</div></div>'
        '</aside>'
        f'<main class="garage-grid tracks">{cards}</main>'
        '</div>'
        '<div id="toast" class="toast"></div>'
        f'<script>{JS}{GARAGE_JS}</script>'
        '</body></html>'
    )


# -- WHEEL · MOZA tab --------------------------------------------------------

# Hand-curated description for each custom dashboard we've built. Stock dashes
# fall through to a plain folder-name listing in the Pit House state section.
MOZA_CUSTOM_DASHES = {
    "RSS Formula Hybrid Alpine 2025": {
        "tag": "F1 2026 · MIAMI & MONTREAL CHASE",
        "subtitle": "On-wheel mirror of the FHA mod display",
        "story": [
            (
                "RSS authored a beautiful in-cockpit wheel display for the FHA "
                "2025 mod — Lua + PNG assets, 1024×605 native canvas, three "
                "pages (Race · Qualy · Extra). The catch: it only renders "
                "inside AC's cockpit view. None of it reaches the FSR V2 LCD "
                "on your wheel."
            ),
            (
                "So we read the mod's <code>display.lua</code>, scanned every "
                "PNG asset for x/y coordinates, and rebuilt the layout as MOZA "
                "<code>.mzdash</code> JSON at 847×480. Gridlines were redrawn "
                "as native <code>Rectangle.qml</code> — PNG hairlines anti-"
                "alias to nothing under MOZA's image scaler. MGUK / brake-mig / "
                "diff-entry slots fall back to closest-proxy MOZA telemetry "
                "keys; their real values live inside the mod's private CSP "
                "shared-memory struct, invisible to the wheel."
            ),
        ],
        "chase": (
            '<strong>MIAMI</strong> 1:27.869 (real F1 sprint qualy) · '
            'your PB <strong>1:32.769</strong> · gap <strong>+4.900</strong>'
            '<br>'
            '<strong>MONTREAL</strong> 1:10.899 (Russell ’25 pole) · '
            'your PB <strong>1:16.665</strong> · gap <strong>+5.766</strong>'
        ),
        "specs": [
            ("CAR",    "rss_formula_hybrid_2025_alpine"),
            ("PAGES",  "3 · Race / Qualy / Extra"),
            ("SOURCE", "RSS Lua + PNG → MOZA JSON"),
            ("CANVAS", "1024×605 → 847×480"),
        ],
    },
    "Mercer V8 Verstappen Spec": {
        "tag": "GT3 · VERSTAPPEN RACING #33 · NORD",
        "subtitle": "Endurance layout for NLS 2 / 1v1 / 24H Nürburgring",
        "story": [
            (
                "Built for the SimRacingPitStop dress rehearsal of the 2026 "
                "24h Nürburgring (race week 14–17 May). RSS Mercer V8 = "
                "Mercedes-AMG GT3 Evo, running the Verstappen Racing livery — "
                "the same chassis Max drove to NLS 2 pole on 20 March 2026."
            ),
            (
                "Endurance discipline over single-lap pace: lap-time + delta "
                "hero, three sector pills (purple = session best, green = PB, "
                "grey = pending), brake-temp quad showing rear-pad heat, "
                "fuel-laps countdown in green, ABS / TC level pills. Nothing "
                "that distracts during a 16-car SP9 PRO stint. The wheel "
                "reads like a real Mercer pit-board."
            ),
        ],
        "chase": (
            '<strong>NORDSCHLEIFE — POLE</strong> 7:51.751 (Verstappen NLS 2, '
            '20 Mar 2026) · race best 7:59.268'
            '<br>'
            'your PB <strong>8:19.177</strong> · gap <strong>+27.426</strong> · '
            'rival <strong>HAASE #16</strong> (Scherer Sport PHX, R8 GT3 Evo II)'
        ),
        "specs": [
            ("CAR",    "rss_gtm_mercer_v8 · M17 #33 livery"),
            ("PAGES",  "1 · Race / endurance"),
            ("SOURCE", "Custom-authored layout"),
            ("USED",   "24H · NLS 2 · 1v1 vs Haase"),
        ],
    },
    "VRC Formula Alpha 2025": {
        "tag": "F1 2025 · VRC PRO · MONTREAL BACKUP",
        "subtitle": "Ported from the VRC FA25 PCU-8D-emulating cockpit display",
        "story": [
            (
                "VRC explicitly badges their 2025 chassis display as "
                "<code>FA25 · pcu8</code> — they're emulating the McLaren Applied "
                "PCU-8D, the FIA-mandated single-supplier dashboard module every "
                "real F1 team has run since 2014. The native canvas is 1024×1024 "
                "with content packed into the bottom 1024×580 rectangle. KERS "
                "charge / deploy / regen as vertical bars on each edge, big gear "
                "in the center, F1-spec laptime + brake-bias columns on the right."
            ),
            (
                "We extracted the layout from <code>extension/data_override/"
                "display/styles/style_0/pages.lua</code>, mapped every "
                "<code>di:drawValue</code> call to its (x, y, size, alignment, "
                "color) tuple, then re-rendered the whole thing at the FSR V2's "
                "847×480. Color palette pulled straight from VRC's "
                "<code>config.lua</code> — <code>racingBlue</code> for KERS "
                "deploy, <code>activeGreen</code> for regen, <code>orange</code> "
                "for the brake-bias indicator. The values shown are from your "
                "first Montreal session in this car: P5 finish, lap 5/5, "
                "10750 rpm, gear 5, +0.486 performance, last 1:19.380."
            ),
        ],
        "chase": (
            '<strong>MONTREAL · VRC PB</strong> 1:19.380 · '
            'theoretical opt 1:18.894 · <strong>+2.715</strong> vs your RSS PB '
            '(1:16.665)'
            '<br>'
            '<strong>MIAMI · VRC CEILING</strong> 1:37.901 (mod cap) · '
            'your VRC PB <strong>1:38.448</strong> — RSS gets to 1:32.769 same combo'
        ),
        "specs": [
            ("CAR",    "vrc_formula_alpha_2025_csp"),
            ("PAGES",  "Race / Quali (parity layouts)"),
            ("SOURCE", "VRC Lua + assets.zip → MOZA"),
            ("CANVAS", "1024×580 → 847×480"),
        ],
        "status": {
            "label": "LAYOUT MOCKED · MZDASH WIP",
            "color": "#d97706",
        },
    },
}


def _moza_state():
    """Read live state from MOZA Pit House data folders."""
    cloud_root = MOZA_DASH_ROOT / MOZA_ACCOUNT_HASH
    studio_root = MOZA_DASH_ROOT / "dashes"

    def _list(p):
        if not p.exists():
            return []
        out = []
        for entry in sorted(p.iterdir()):
            if not entry.is_dir():
                continue
            name = entry.name
            if name.startswith("_") or name in ("ads", "brzsimdash"):
                continue
            mzdash = entry / f"{name}.mzdash"
            has_thumb = (entry / "1.png").exists()
            out.append({
                "name": name,
                "has_mzdash": mzdash.exists(),
                "has_thumb": has_thumb,
                "is_custom": name in MOZA_CUSTOM_DASHES,
            })
        return out

    cloud = _list(cloud_root)
    studio = _list(studio_root)
    cloud_names = {d["name"] for d in cloud}

    studio_only = [d for d in studio if d["name"] not in cloud_names]

    version = "—"
    vfile = studio_root / "version.ini"
    if vfile.exists():
        try:
            for line in vfile.read_text(errors="ignore").splitlines():
                if "=" in line and "Display" in line:
                    version = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass

    return {
        "cloud": cloud,
        "studio_only": studio_only,
        "w13_display_version": version,
    }


def _moza_mock_svg(name):
    """Synthesized FSR V2 dashboard preview when no real thumbnail exists.
    Renders an SVG mock of the layout described in MOZA_CUSTOM_DASHES so the
    card carries visual weight matching cards that DO have thumbnails."""
    if name == "Mercer V8 Verstappen Spec":
        return (
            '<svg viewBox="0 0 847 480" preserveAspectRatio="xMidYMid slice" '
            'style="width:100%;height:100%;display:block;background:#070707" '
            'xmlns="http://www.w3.org/2000/svg" font-family="Inter,sans-serif">'
            '<rect x="40" y="34" width="767" height="16" fill="#1a1a1a"/>'
            '<rect x="40" y="34" width="600" height="16" fill="#14D900"/>'
            '<rect x="640" y="34" width="100" height="16" fill="#FFF200"/>'
            '<rect x="740" y="34" width="67" height="16" fill="#FA3939"/>'
            '<text x="40" y="100" fill="#FA3939" font-size="48" font-weight="900" '
            'letter-spacing="-1.5">#33</text>'
            '<text x="40" y="120" fill="#888" font-size="10" letter-spacing="2">VERSTAPPEN RACING</text>'
            '<text x="807" y="98" text-anchor="end" fill="#fff" font-size="56" '
            'font-weight="800" font-family="JetBrains Mono,monospace">214</text>'
            '<text x="807" y="120" text-anchor="end" fill="#888" font-size="10" letter-spacing="2">KMH</text>'
            '<text x="423" y="240" text-anchor="middle" fill="#fff" font-size="200" '
            'font-weight="900" font-family="JetBrains Mono,monospace">4</text>'
            '<text x="40" y="310" fill="#888" font-size="10" letter-spacing="2">LAP TIME</text>'
            '<text x="40" y="354" fill="#fff" font-size="44" font-weight="700" '
            'font-family="JetBrains Mono,monospace">8:14.521</text>'
            '<text x="40" y="384" fill="#14D900" font-size="22" font-weight="700" '
            'font-family="JetBrains Mono,monospace">−4.656</text>'
            '<rect x="500" y="280" width="90" height="36" fill="#9333ea" rx="3"/>'
            '<text x="545" y="304" text-anchor="middle" fill="#fff" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">2:41.8</text>'
            '<rect x="600" y="280" width="90" height="36" fill="#14D900" rx="3"/>'
            '<text x="645" y="304" text-anchor="middle" fill="#fff" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">3:01.4</text>'
            '<rect x="700" y="280" width="90" height="36" fill="#1a1a1a" stroke="#444" rx="3"/>'
            '<text x="745" y="304" text-anchor="middle" fill="#888" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">— : —</text>'
            '<text x="500" y="340" fill="#888" font-size="9" letter-spacing="2">BRAKE °C</text>'
            '<rect x="500" y="350" width="42" height="32" fill="#FFF200" rx="2"/>'
            '<text x="521" y="372" text-anchor="middle" fill="#000" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">412</text>'
            '<rect x="546" y="350" width="42" height="32" fill="#FFF200" rx="2"/>'
            '<text x="567" y="372" text-anchor="middle" fill="#000" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">408</text>'
            '<rect x="500" y="386" width="42" height="32" fill="#FA3939" rx="2"/>'
            '<text x="521" y="408" text-anchor="middle" fill="#fff" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">521</text>'
            '<rect x="546" y="386" width="42" height="32" fill="#FA3939" rx="2"/>'
            '<text x="567" y="408" text-anchor="middle" fill="#fff" font-size="14" '
            'font-weight="700" font-family="JetBrains Mono,monospace">517</text>'
            '<text x="40" y="430" fill="#888" font-size="10" letter-spacing="2">ABS</text>'
            '<text x="80" y="432" fill="#fff" font-size="20" font-weight="700" '
            'font-family="JetBrains Mono,monospace">7</text>'
            '<text x="120" y="430" fill="#888" font-size="10" letter-spacing="2">TC</text>'
            '<text x="150" y="432" fill="#fff" font-size="20" font-weight="700" '
            'font-family="JetBrains Mono,monospace">5</text>'
            '<text x="220" y="430" fill="#888" font-size="10" letter-spacing="2">FUEL LAPS</text>'
            '<text x="320" y="432" fill="#14D900" font-size="20" font-weight="700" '
            'font-family="JetBrains Mono,monospace">12.3</text>'
            '<text x="807" y="450" text-anchor="end" fill="#444" font-size="10" '
            'letter-spacing="2">FSR V2 · 847×480</text>'
            '</svg>'
        )
    return (
        '<svg viewBox="0 0 847 480" preserveAspectRatio="xMidYMid slice" '
        'style="width:100%;height:100%;display:block;background:#070707" '
        'xmlns="http://www.w3.org/2000/svg" font-family="Inter,sans-serif">'
        '<rect x="40" y="34" width="767" height="16" fill="#1a1a1a"/>'
        '<rect x="40" y="34" width="500" height="16" fill="#dc2626"/>'
        f'<text x="423" y="260" text-anchor="middle" fill="#fff" font-size="44" '
        f'font-weight="900" letter-spacing="-1">{escape(name.upper())}</text>'
        '<text x="423" y="300" text-anchor="middle" fill="#888" font-size="12" '
        'letter-spacing="3">FSR V2 · 847×480</text>'
        '</svg>'
    )


def _render_moza_card(name, info, has_thumb):
    from urllib.parse import quote
    if has_thumb:
        thumb_path = MOZA_DASH_ROOT / MOZA_ACCOUNT_HASH / name / "1.png"
        try:
            mtime = int(thumb_path.stat().st_mtime)
        except Exception:
            mtime = 0
        img = (
            f'<img src="/moza/thumb/{quote(name)}/1.png?v={mtime}" '
            f'alt="{escape(name)}">'
        )
    else:
        img = _moza_mock_svg(name)
    status = info.get("status") or {"label": "REGISTERED ✓", "color": "#16a34a"}
    specs = "".join(
        f'<div class="spec-pill" title="{escape(k)}: {escape(v)}">'
        f'<span class="lbl">{escape(k)}</span>{escape(v)}</div>'
        for k, v in info["specs"]
    )
    # story is rendered with limited inline HTML allowed (<code>, <strong>) — the
    # source dict is hand-curated, never user-controlled, so we pass through
    # without escaping but still tag it visually as story prose.
    story_paras = "".join(
        f'<p class="moza-story">{para}</p>' for para in info["story"]
    )
    download_url = f'/moza/download/{quote(name)}.zip'
    return (
        '<article class="card moza-card">'
        '<div class="card-img">'
        f'<span class="card-type-chip" style="background:{status["color"]}">{escape(status["label"])}</span>'
        f'{img}'
        '</div>'
        '<div class="card-body">'
        f'<div class="card-tag">{escape(info["tag"])}</div>'
        f'<h3 class="card-title">{escape(name)}</h3>'
        f'<div class="card-sub">{escape(info["subtitle"])}</div>'
        f'{story_paras}'
        '<div class="moza-chase">'
        '<span class="moza-chase-lbl">The chase</span>'
        f'<div class="moza-chase-body">{info["chase"]}</div>'
        '</div>'
        f'<div class="spec-strip">{specs}</div>'
        '<div class="moza-actions">'
        f'<a class="btn-moza-download" href="{download_url}" download '
        f'title="Download {escape(name)} as a .zip you can drop into MOZA Dashboard Studio">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2.5" stroke-linecap="round" '
        'stroke-linejoin="round" style="margin-right:6px;flex-shrink:0">'
        '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
        '<polyline points="7 10 12 15 17 10"/>'
        '<line x1="12" y1="15" x2="12" y2="3"/>'
        '</svg>'
        'DOWNLOAD .MZDASH</a>'
        '<span class="moza-install-hint">Unzip into '
        '<code>MOZA Pit House/_dashes/&lt;account&gt;/</code> '
        'then re-open in Dashboard Studio to register</span>'
        '</div>'
        '</div>'
        '</article>'
    )


MOZA_PAGE_CSS = """
.moza-list{max-width:1280px;margin:0 auto;padding:0 24px 16px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.moza-panel{background:var(--surface);border:1px solid var(--ink);box-shadow:3px 3px 0 var(--ink);padding:18px 20px}
.moza-panel h3{font:800 14px/1.1 var(--display);letter-spacing:0.5px;text-transform:uppercase;color:var(--ink);margin:0 0 12px;padding-bottom:8px;border-bottom:1.5px solid var(--ink)}
.moza-row{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px dashed var(--rule-hair);font:500 13px/1.3 var(--body);color:var(--ink-2)}
.moza-row:last-child{border-bottom:0}
.moza-row .nm{font-weight:600;color:var(--ink)}
.moza-row .pill{font:700 9.5px/1 var(--body);letter-spacing:1.2px;text-transform:uppercase;padding:4px 8px;border-radius:2px}
.moza-row .pill.stock{background:var(--paper);border:1px solid var(--border);color:var(--ink-3)}
.moza-row .pill.custom{background:#16a34a;color:#fff}
.moza-row .pill.warn{background:var(--gold);color:var(--gold-rim);border:1px solid var(--gold-rim)}
.moza-ref{max-width:1280px;margin:0 auto;padding:0 24px 64px}
.moza-ref-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:14px}
.moza-ref-grid .moza-panel h4{font:700 10px/1.1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:var(--accent);margin:0 0 8px}
.moza-ref-grid p{font:400 13px/1.5 var(--body);color:var(--ink-2);margin:0 0 8px}
.moza-ref-grid code{font:600 11.5px/1.5 var(--mono);background:var(--paper);padding:1px 5px;border-radius:2px;color:var(--ink)}
.moza-ref-grid ul{margin:0;padding-left:18px;font:400 12.5px/1.55 var(--body);color:var(--ink-2)}
.moza-ref-grid li{margin-bottom:3px}
/* Featured-card overrides — scenarios on /moza must NOT clamp like home cards */
.moza-card .moza-story{font:400 13.5px/1.55 var(--body);color:var(--ink-2);margin:6px 0 0;letter-spacing:0;display:block;-webkit-line-clamp:none;overflow:visible}
.moza-card .moza-story:first-of-type{margin-top:4px}
.moza-card .moza-story code{font:600 11.5px/1.4 var(--mono);background:var(--paper);padding:1px 5px;border-radius:2px;color:var(--ink);white-space:nowrap}
.moza-chase{background:#0f172a;color:#f1f5f9;border-left:3px solid var(--max);padding:10px 12px 11px;margin:6px 0 0;font:500 12.5px/1.5 var(--body);letter-spacing:0;border-radius:2px}
.moza-chase strong{color:#fff;font-weight:700;letter-spacing:0.3px}
.moza-chase-lbl{display:block;font:700 9.5px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;color:#fde68a;margin-bottom:6px}
.moza-chase-body{font:500 12.5px/1.55 var(--mono);color:#e2e8f0}
.moza-actions{display:flex;flex-direction:column;gap:6px;margin:4px 0 0;padding-top:12px;border-top:1px solid var(--rule-hair)}
.btn-moza-download{display:inline-flex;align-items:center;justify-content:center;gap:0;font:700 12px/1 var(--body);letter-spacing:1.4px;text-transform:uppercase;padding:11px 14px;background:var(--ink);color:#fff;border:1.5px solid var(--ink);border-radius:2px;text-decoration:none;cursor:pointer;transition:background .15s,transform .12s,box-shadow .15s;box-shadow:2px 2px 0 var(--accent-strong)}
.btn-moza-download:hover{background:var(--max);border-color:var(--max);transform:translate(-1px,-1px);box-shadow:3px 3px 0 var(--ink)}
.btn-moza-download:active{transform:translate(0,0);box-shadow:1px 1px 0 var(--ink)}
.moza-install-hint{font:400 10.5px/1.4 var(--body);color:var(--ink-3);text-align:center;letter-spacing:0.2px}
.moza-install-hint code{font:600 10px/1.3 var(--mono);background:var(--paper);padding:1px 4px;border-radius:2px;color:var(--ink-2);border:1px solid var(--rule-hair)}
@media (max-width:880px){.moza-list,.moza-ref-grid{grid-template-columns:1fr}}
"""


def render_moza_page():
    state = _moza_state()
    cloud = state["cloud"]
    studio_only = state["studio_only"]

    custom_count = sum(1 for d in cloud if d["is_custom"])
    stock_count = len(cloud) - custom_count

    featured = "".join(
        _render_moza_card(d["name"], MOZA_CUSTOM_DASHES[d["name"]], d["has_thumb"])
        for d in cloud
        if d["is_custom"] and d["name"] in MOZA_CUSTOM_DASHES
    )

    def _row(d, badge):
        return (
            '<div class="moza-row">'
            f'<span class="nm">{escape(d["name"])}</span>'
            f'{badge}'
            '</div>'
        )

    cloud_rows = "".join(
        _row(
            d,
            '<span class="pill custom">CUSTOM ✓</span>'
            if d["is_custom"]
            else '<span class="pill stock">STOCK</span>',
        )
        for d in cloud
    )
    if studio_only:
        studio_rows = "".join(
            _row(d, '<span class="pill warn">STUDIO ONLY · NOT REGISTERED</span>')
            for d in studio_only
        )
    else:
        studio_rows = (
            '<div class="moza-row" style="color:var(--ink-3)">'
            '<span>(none — every Studio dashboard is also registered)</span>'
            '<span></span></div>'
        )

    return (
        f'{_common_head("Wheel · MOZA · Pit House")}'
        f'<style>{MOZA_PAGE_CSS}</style>'
        f'{render_nav("moza")}'
        f'{render_ticker()}'
        '<header class="hero garage-hero">'
        '<div class="hero-l">'
        '<div class="hero-kicker">PABLO\'S WHEEL · MOZA FSR V2</div>'
        '<h1 class="hero-title">PIT HOUSE <span class="accent">DASHBOARDS</span></h1>'
        f'<div class="hero-sub">847×480 LCD · {custom_count} custom deployed · '
        f'{stock_count} stock · W13 Display v{escape(state["w13_display_version"])}</div>'
        '</div>'
        '<div class="hero-r">'
        '<div class="hero-count-lbl">CUSTOM DASHES</div>'
        f'<div class="hero-count">{custom_count:02d}</div>'
        f'<div class="hero-count-meta"><strong>{len(cloud)}</strong> registered total · '
        f'<strong>{len(studio_only)}</strong> studio-only</div>'
        '</div>'
        '</header>'
        '<div class="section-head">'
        '<h2 class="section-title">DEPLOYED CUSTOM DASHES</h2>'
        '<p class="section-deck">RSS car mods ship with their own Lua + PNG wheel '
        'displays — but those only render inside AC\'s cockpit view. To put the '
        'same UI on the FSR V2 LCD itself, we read the mod source, decoded the '
        'layout, rebuilt it as MOZA\'s <code>.mzdash</code> JSON, and registered '
        'it to the cloud. Two cars, two ports, both alive on the wheel.</p>'
        '</div>'
        f'<main class="grid">{featured}</main>'
        '<div class="section-head">'
        '<h2 class="section-title">PIT HOUSE STATE</h2>'
        '<p class="section-deck">Live read of <code>_dashes/</code>. Cloud-cache list = '
        'what shows on the wheel; Studio-only = exists in the editor but never registered.</p>'
        '</div>'
        '<div class="moza-list">'
        '<div class="moza-panel">'
        f'<h3>Cloud cache · visible on wheel ({len(cloud)})</h3>'
        f'{cloud_rows}'
        '</div>'
        '<div class="moza-panel">'
        f'<h3>Studio root · editor only ({len(studio_only)})</h3>'
        f'{studio_rows}'
        '</div>'
        '</div>'
        '<div class="section-head">'
        '<h2 class="section-title">REFERENCE — WHAT WE LEARNED</h2>'
        '<p class="section-deck">Locked-in lessons from the 2026-05-07 build session, '
        'kept here so we don\'t pay for them twice.</p>'
        '</div>'
        '<div class="moza-ref">'
        '<div class="moza-ref-grid">'
        '<div class="moza-panel">'
        '<h4>Cloud-registration gotcha</h4>'
        '<p>Pit House shows ONLY dashboards registered to the cloud account. '
        'Dropping a <code>.mzdash</code> in the folder is not enough — the resync '
        'on app upgrade silently wipes anything not in the cloud GUID list. '
        'Two ways to register: (1) log in to MOZA cloud → it syncs locals up. '
        '(2) Open the file in MOZA Dashboard Studio and save — it registers '
        'locally even offline.</p>'
        '</div>'
        '<div class="moza-panel">'
        '<h4>Bindings that actually work</h4>'
        '<p>Anything else silently breaks the dashboard:</p>'
        '<ul>'
        '<li><code>text.text</code></li>'
        '<li><code>text.fontColor</code></li>'
        '<li><code>general.backgroundColor</code></li>'
        '<li><code>general.visible</code></li>'
        '<li><code>linearGauge.value</code></li>'
        '<li><code>chart.currentValue</code></li>'
        '</ul>'
        '<p style="margin-top:8px">For dynamic-height bars, use vertical '
        '<code>LinearGauge</code> with <code>AlignBottom</code>, never '
        '<code>general.height</code>.</p>'
        '</div>'
        '<div class="moza-panel">'
        '<h4>Schema gotchas</h4>'
        '<ul>'
        '<li>PNG hairlines (5–7 px) anti-alias to nothing under MOZA\'s scaler — '
        'draw gridlines as native <code>Rectangle.qml</code>.</li>'
        '<li>Don\'t lay label + value as separate <code>Text.qml</code> at adjacent '
        'x — later children paint over earlier. Combine into one binding.</li>'
        '<li>JSON line endings must be CRLF (<code>\\r\\n</code>).</li>'
        '<li><code>window.GUID</code> must be unique per dashboard.</li>'
        '<li>Mod-internal data (MGUK, brake-mig, diff entry/mid/exit, throttle map) '
        'is NOT exposed — use closest-proxy MOZA keys.</li>'
        '</ul>'
        '</div>'
        '</div>'
        '</div>'
        '</body></html>'
    )


def _serve_moza_thumb(handler, dashboard_name, filename):
    """Serve 1.png / 2.png from the cloud-cache dashboard folder, sandboxed."""
    if filename not in ("1.png", "2.png"):
        handler.send_error(400, "bad thumb name")
        return
    base = (MOZA_DASH_ROOT / MOZA_ACCOUNT_HASH).resolve()
    target = (base / dashboard_name / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        handler.send_error(400, "path escapes sandbox")
        return
    if not target.exists():
        handler.send_error(404)
        return
    handler._file(target, "image/png")


def _serve_moza_download(handler, dashboard_name):
    """Bundle .mzdash + thumbnails into a ZIP and stream it back. The archive
    contains a single top-level folder named after the dashboard, so unzipping
    drops cleanly into Pit House's _dashes/<account>/ tree."""
    import io
    import zipfile
    from urllib.parse import quote

    base = (MOZA_DASH_ROOT / MOZA_ACCOUNT_HASH).resolve()
    src_dir = (base / dashboard_name).resolve()
    try:
        src_dir.relative_to(base)
    except ValueError:
        handler.send_error(400, "path escapes sandbox")
        return
    if not src_dir.is_dir():
        handler.send_error(404, "dashboard folder not found")
        return

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in sorted(src_dir.iterdir()):
            if not entry.is_file():
                continue
            arcname = f"{dashboard_name}/{entry.name}"
            zf.write(entry, arcname=arcname)
    payload = buf.getvalue()

    safe = dashboard_name.replace('"', "_") + ".zip"
    handler.send_response(200)
    handler.send_header("Content-Type", "application/zip")
    handler.send_header(
        "Content-Disposition",
        f'attachment; filename="{safe}"; filename*=UTF-8\'\'{quote(safe)}',
    )
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(payload)


def _bhp_int(s):
    """Pull the numeric portion from '500bhp' / '500 bhp' / etc."""
    if not s:
        return 0
    m = re.search(r'\d+', str(s))
    return int(m.group()) if m else 0


def _render_car_tile(c):
    img = (
        f'<img loading="lazy" src="/content/cars/{escape(c["id"])}/preview" alt="">'
        if c["has_preview"]
        else '<div class="tile-img-fallback"></div>'
    )
    series_chip = (
        f'<span class="tile-series s-{escape(c["series"].lower().replace(" ", "-"))}">'
        f'{escape(c["series"])}</span>'
    )
    bhp = escape(c["bhp"]) if c["bhp"] else ""
    weight = escape(c["weight"]) if c["weight"] else ""
    year_chip = f'<span class="tile-year">{c["year"]}</span>' if c.get("year") else ""
    skins = f'<span class="tile-skins">{c["skin_count"]} skins</span>' if c.get("skin_count") else ""
    tags = " ".join(c["tags"]).lower()
    haystack = f'{c["name"]} {c["brand"]} {c["class"]} {c["series"]} {c["id"]} {tags} {c.get("year") or ""}'.lower()
    title_attr = ""
    if not c["real_name"]:
        title_attr = ' title="No metadata in ui_car.json — folder ID shown"'
    return (
        f'<article class="tile" '
        f'data-haystack="{escape(haystack)}" '
        f'data-name="{escape(c["name"].lower())}" '
        f'data-year="{c.get("year") or ""}" '
        f'data-era="{escape(c.get("era") or "")}" '
        f'data-bhp="{_bhp_int(c["bhp"])}" '
        f'data-brand="{escape(c["brand"])}" '
        f'data-series="{escape(c["series"])}">'
        f'<div class="tile-img">{img}{series_chip}{year_chip}{skins}</div>'
        '<div class="tile-body">'
        f'<div class="tile-brand">{escape(c["brand"]) or "—"}</div>'
        f'<h3 class="tile-title"{title_attr}>{escape(c["name"])}</h3>'
        '<div class="tile-meta">'
        f'<span>{bhp}</span>'
        f'<span>{weight}</span>'
        '</div>'
        '</div>'
        '</article>'
    )


def _length_m(s):
    """Parse 'X.YYY km' or 'NNNN m' into meters for sorting."""
    if not s:
        return 0
    s = str(s).strip().lower()
    m = re.search(r'([\d.,]+)\s*(km|m\b)', s)
    if not m:
        m = re.search(r'[\d.,]+', s)
        if not m:
            return 0
        try:
            v = float(m.group().replace(",", "."))
        except ValueError:
            return 0
        return int(v if v > 100 else v * 1000)
    try:
        v = float(m.group(1).replace(",", "."))
    except ValueError:
        return 0
    return int(v * 1000) if m.group(2) == "km" else int(v)


def _render_track_tile(t):
    img = (
        f'<img loading="lazy" src="/content/tracks/{escape(t["id"])}/preview" alt="">'
        if t["has_preview"]
        else '<div class="tile-img-fallback"></div>'
    )
    cat_chip = (
        f'<span class="tile-series s-{escape(t["category"].lower().replace(" ", "-"))}">'
        f'{escape(t["category"])}</span>'
    )
    layouts = ""
    if t["layouts"]:
        layouts = f'<span class="tile-skins">{len(t["layouts"]) + 1} layouts</span>'
    year_chip = f'<span class="tile-year">{t["year"]}</span>' if t.get("year") else ""
    haystack = f'{t["name"]} {t["country"]} {t["city"]} {t["category"]} {t["id"]} {t.get("year") or ""}'.lower()
    pits = f'<span>{t["pitboxes"]} pits</span>' if t["pitboxes"] else ""
    length = f'<span>{escape(t["length"])}</span>' if t["length"] else ""
    title_attr = ""
    if not t["real_name"]:
        title_attr = ' title="No metadata in ui_track.json — folder ID shown"'
    return (
        f'<article class="tile track-tile" '
        f'data-haystack="{escape(haystack)}" '
        f'data-name="{escape(t["name"].lower())}" '
        f'data-year="{t.get("year") or ""}" '
        f'data-era="{escape(t.get("era") or "")}" '
        f'data-length="{_length_m(t["length"])}" '
        f'data-country="{escape(t["country"])}" '
        f'data-category="{escape(t["category"])}">'
        f'<div class="tile-img">{img}{cat_chip}{year_chip}{layouts}</div>'
        '<div class="tile-body">'
        f'<div class="tile-brand">{escape(t["country"]) or "—"}'
        f'{(" · " + escape(t["city"])) if t["city"] else ""}</div>'
        f'<h3 class="tile-title"{title_attr}>{escape(t["name"])}</h3>'
        f'<div class="tile-meta">{length}{pits}</div>'
        '</div>'
        '</article>'
    )


GARAGE_JS = """
(function(){
  const search = document.getElementById('garage-search');
  if (!search) return;
  const grid = document.querySelector('.garage-grid');
  const tiles = Array.from(grid.querySelectorAll('.tile'));
  const pillsRow = document.getElementById('active-pills');
  const countLbl = document.getElementById('garage-count');
  const sortSel = document.getElementById('garage-sort');
  const FACET_KEYS = ['series','era','brand','category','country'];
  const FACET_LABELS = {
    series: 'Series', era: 'Era', brand: 'Brand',
    category: 'Category', country: 'Country',
  };
  const state = {q: '', sort: 'name', filter: {}};

  function apply(){
    let shown = 0;
    tiles.forEach(t => {
      const okQ = !state.q || t.dataset.haystack.includes(state.q);
      const okF = FACET_KEYS.every(k =>
        !state.filter[k] || t.dataset[k] === state.filter[k]);
      const show = okQ && okF;
      t.style.display = show ? '' : 'none';
      if (show) shown++;
    });
    if (countLbl) countLbl.textContent = shown;

    document.querySelectorAll('.fopt').forEach(b => {
      const k = b.dataset.filter, v = b.dataset.value;
      b.classList.toggle('is-active', state.filter[k] === v);
    });

    pillsRow.innerHTML = '';
    let pillCount = 0;
    function addPill(label, onRemove, klass){
      const p = document.createElement('span');
      p.className = 'apill ' + (klass || '');
      const labelSpan = document.createElement('span');
      labelSpan.textContent = label;
      const x = document.createElement('button');
      x.type = 'button'; x.setAttribute('aria-label', 'Remove filter');
      x.textContent = '×';
      x.addEventListener('click', onRemove);
      p.appendChild(labelSpan);
      p.appendChild(x);
      pillsRow.appendChild(p);
      pillCount++;
    }
    if (state.q) {
      addPill('Search: "' + state.q + '"', () => {
        state.q = ''; search.value = ''; apply();
      });
    }
    FACET_KEYS.forEach(k => {
      if (state.filter[k]) {
        addPill(FACET_LABELS[k] + ': ' + state.filter[k], () => {
          delete state.filter[k]; apply();
        }, 'apill-' + k);
      }
    });
    pillsRow.classList.toggle('has-pills', pillCount > 0);
  }

  function applySort(){
    const order = state.sort;
    const sorted = tiles.slice().sort((a, b) => {
      if (order === 'year-new') {
        return (parseInt(b.dataset.year) || 0) - (parseInt(a.dataset.year) || 0);
      }
      if (order === 'year-old') {
        return (parseInt(a.dataset.year) || 9999) - (parseInt(b.dataset.year) || 9999);
      }
      if (order === 'bhp-high') {
        return (parseInt(b.dataset.bhp) || 0) - (parseInt(a.dataset.bhp) || 0);
      }
      if (order === 'length-long') {
        return (parseInt(b.dataset.length) || 0) - (parseInt(a.dataset.length) || 0);
      }
      return (a.dataset.name || '').localeCompare(b.dataset.name || '');
    });
    sorted.forEach(t => grid.appendChild(t));
  }

  search.addEventListener('input', e => {
    state.q = e.target.value.toLowerCase().trim(); apply();
  });
  if (sortSel) sortSel.addEventListener('change', e => {
    state.sort = e.target.value; applySort();
  });

  document.querySelectorAll('.fopt').forEach(b => {
    b.addEventListener('click', () => {
      const k = b.dataset.filter, v = b.dataset.value;
      if (state.filter[k] === v) delete state.filter[k];
      else state.filter[k] = v;
      apply();
    });
  });

  const reset = document.querySelector('.garage-reset');
  if (reset) reset.addEventListener('click', () => {
    state.q = ''; state.filter = {}; search.value = ''; apply();
  });

  // Brand/country search inside the long facet list
  const facetSearch = document.getElementById('brand-search');
  if (facetSearch) {
    facetSearch.addEventListener('input', e => {
      const q = e.target.value.toLowerCase().trim();
      facetSearch.parentElement
        .querySelectorAll('.ffacet-list .fopt')
        .forEach(b => {
          const label = (b.querySelector('.fopt-label').textContent || '')
            .toLowerCase();
          b.style.display = !q || label.includes(q) ? '' : 'none';
        });
    });
  }

  // Initial apply
  apply();
})();
"""


def _render_series_sections():
    """Group cards by series in SERIES order; trailing un-tagged cards as 'OTHER'."""
    today = date.today()
    rendered_ids = set()
    parts = []
    for s in SERIES:
        cards = [c for c in CONFIGS if c.get("series") == s["id"]]
        if not cards:
            continue
        cards_html = "".join(render_card(c) for c in cards)
        parts.append(
            f'{render_series_head(s, today)}'
            f'<main class="grid">{cards_html}</main>'
        )
        rendered_ids.update(c["id"] for c in cards)
    leftovers = [c for c in CONFIGS if c["id"] not in rendered_ids]
    if leftovers:
        s = {"label": "OTHER", "deck": "Uncategorised challenges."}
        parts.append(
            f'{render_series_head(s, today)}'
            f'<main class="grid">{"".join(render_card(c) for c in leftovers)}</main>'
        )
    return "".join(parts)


# Pinned-ongoing-challenge tile IDs — these render in a featured row above
# the regular series sections on the home page.
ONGOING_TILE_IDS = [
    "antonelli_vs_verstappen_nord",
    "verstappen_1v1",
    "hotlap_montreal",
]


def _render_ongoing_section():
    tiles = []
    for tid in ONGOING_TILE_IDS:
        cfg = next((c for c in CONFIGS if c["id"] == tid), None)
        if cfg:
            tiles.append(cfg)
    if not tiles:
        return ""
    cards_html = "".join(render_card(c) for c in tiles)
    return (
        '<section class="ongoing-section">'
        '<header class="ongoing-head">'
        '<div class="ongoing-tag">▶ ONGOING</div>'
        '<h2 class="ongoing-title">Active challenges</h2>'
        '<p class="ongoing-deck">What you\'re actively chasing right now. Pinned to the top until you swap them out.</p>'
        '</header>'
        f'<div class="ongoing-grid">{cards_html}</div>'
        '</section>'
    )


def render_html():
    return (
        f'{_common_head("Pablo Suzarte\'s Sim Racing Challenges")}'
        f'{render_nav("challenges")}'
        f'{render_ticker()}'
        f'{render_hero()}'
        f'{_render_ongoing_section()}'
        f'{_render_series_sections()}'
        f'{render_foot()}'
        '<div id="toast" class="toast"></div>'
        f'<script>{JS}</script>'
        '</body></html>'
    )


# -- Garage (cars/tracks browser) -------------------------------------------

_INDEX_CACHE = {"cars": None, "tracks": None}
_INDEX_CACHE_FILE = LAUNCHER_DIR / ".content_index.json"


_CACHE_SCHEMA = 2  # bump when entry shape changes — forces re-scan


def _load_disk_cache():
    """Load on-disk cache from previous run if present and schema matches."""
    try:
        if _INDEX_CACHE_FILE.exists():
            data = json.loads(_INDEX_CACHE_FILE.read_text(encoding="utf-8"))
            if data.get("schema") == _CACHE_SCHEMA:
                _INDEX_CACHE["cars"] = data.get("cars")
                _INDEX_CACHE["tracks"] = data.get("tracks")
    except Exception:
        pass


def _save_disk_cache():
    try:
        payload = dict(_INDEX_CACHE)
        payload["schema"] = _CACHE_SCHEMA
        _INDEX_CACHE_FILE.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _escape_ctrl_in_strings(text: str) -> str:
    """AC mod ui_*.json files commonly contain raw \\n / tabs inside string
    literals (descriptions especially). Walk a tiny state machine that
    escapes any control char that appears inside a JSON string, leaving
    structural whitespace alone."""
    out = []
    i = 0
    n = len(text)
    in_str = False
    while i < n:
        c = text[i]
        if c == '"':
            out.append(c)
            in_str = not in_str
        elif in_str and c == '\\' and i + 1 < n:
            out.append(c)
            out.append(text[i + 1])
            i += 2
            continue
        elif in_str and c == '\n':
            out.append('\\n')
        elif in_str and c == '\r':
            out.append('\\r')
        elif in_str and c == '\t':
            out.append('\\t')
        elif in_str and ord(c) < 0x20:
            out.append(f'\\u{ord(c):04x}')
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def _read_ui_json(path: Path):
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        text = text.replace("\x00", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Many AC mods have raw control chars in description strings —
        # escape them and retry. Recovers ~10% of the catalog from "no name".
        try:
            return json.loads(_escape_ctrl_in_strings(text))
        except Exception:
            return {}
    except Exception:
        return {}


_YEAR_RE = re.compile(r'\b(19[5-9]\d|20[0-2]\d)\b')


def _extract_year(ui, fallback_text=""):
    """Find a 4-digit year on the car: ui.year first, then name/tags/folder."""
    y = ui.get("year")
    if isinstance(y, int) and 1900 < y < 2100:
        return y
    if isinstance(y, str):
        s = y.strip()
        if s.isdigit() and 1900 < int(s) < 2100:
            return int(s)
        m = _YEAR_RE.search(s)
        if m:
            return int(m.group(1))
    haystack = " ".join([
        str(ui.get("name") or ""),
        " ".join(ui.get("tags") or []),
        str(fallback_text),
    ])
    m = _YEAR_RE.search(haystack)
    return int(m.group(1)) if m else None


def _era_from_year(y):
    if not y or y < 1950:
        return None
    if y >= 2020:
        return "2020s"
    if y >= 2010:
        return "2010s"
    if y >= 2000:
        return "2000s"
    if y >= 1990:
        return "1990s"
    if y >= 1980:
        return "1980s"
    if y >= 1970:
        return "1970s"
    if y >= 1960:
        return "1960s"
    return "Pre-1960"


def _classify_car_series(car):
    """Pick a single high-level series label using tags + name + id."""
    tags = " ".join(t.lower() for t in (car.get("tags") or []))
    cls = (car.get("class") or "").lower()
    name = (car.get("name") or "").lower()
    cid = car.get("id", "").lower()
    blob = f" {tags}  {cls}  {name}  {cid} "

    # Order matters — most specific first.
    rules = [
        ("GT3",       ("gt3", "gte-gt3")),
        ("GT4",       ("gt4",)),
        ("GTE",       (" gte ", "gt2 ", " lmgte")),
        ("GT500",     ("gt500", "super gt", "supergt")),
        ("GT300",     ("gt300",)),
        ("GT1",       (" gt1 ",)),
        ("LMP1",      ("lmp1", "lmh", "lmdh")),
        ("LMP2",      ("lmp2",)),
        ("LMP",       (" lmp ", "le mans prototype")),
        ("HYPERCAR",  ("hypercar", "lmh ")),
        ("F1",        ("formula 1", " f1 ", "f1_", "f1 1", "f1 2", "grand prix", "rss formula hybrid")),
        ("INDYCAR",   ("indycar", "indy car")),
        ("OPEN-WHEEL",("singleseater", "single seater", "open-wheel", "open wheel", " gp ", "formula ", "single-seater")),
        ("DTM",       ("dtm",)),
        ("TCR",       ("tcr ", " tcr", "wtcr", "btcc")),
        ("STOCK",     ("nascar", "stock car")),
        ("RALLY",     ("rally", "rallycross")),
        ("DRIFT",     ("drift",)),
        ("VINTAGE",   ("vintage", "classic", "1960", "1970", "1980")),
        ("SUPERCAR",  ("supercar",)),
        ("HOT HATCH", ("hot hatch", "hatchback")),
        ("TOURING",   ("touring", "ts ")),
        ("RACE",      ("race", "racecar")),
        ("STREET",    ("street", "road")),
    ]
    for label, needles in rules:
        for n in needles:
            if n in blob:
                return label
    return "OTHER"


def _classify_track_category(track):
    tags = " ".join(t.lower() for t in (track.get("tags") or []))
    name = (track.get("name") or "").lower()
    cid = (track.get("id") or "").lower()
    blob = f" {tags}  {name}  {cid} "
    rules = [
        ("NORD",      ("nordschleife", "nord", "nuerburgring 24h", "nurburgring 24h")),
        ("LE MANS",   ("le mans", "lemans")),
        ("F1 GP",     ("f1", "grand prix", " gp ", "circuit gilles", "spa-fr", "monza", "silverstone", "monaco")),
        ("ENDURANCE", ("endurance", "24h", "12h")),
        ("OVAL",      ("oval", "speedway")),
        ("RALLY",     ("rally",)),
        ("DRIFT",     ("drift",)),
        ("STREET",    ("street circuit",)),
    ]
    for label, needles in rules:
        for n in needles:
            if n in blob:
                return label
    return "ROAD"


def _car_preview(car_dir: Path):
    skins = car_dir / "skins"
    if skins.exists():
        for s in sorted(skins.iterdir()):
            if s.is_dir():
                p = s / "preview.jpg"
                if p.exists():
                    return p
    for name in ("preview.jpg", "ui/preview.png", "ui/preview.jpg"):
        p = car_dir / name
        if p.exists():
            return p
    return None


def _track_preview(track_dir: Path):
    ui = track_dir / "ui"
    if ui.exists():
        p = ui / "preview.png"
        if p.exists():
            return p
        for s in sorted(ui.iterdir()):
            if s.is_dir():
                p = s / "preview.png"
                if p.exists():
                    return p
    return None


def _index_cars(force=False):
    if not force and _INDEX_CACHE["cars"] is not None:
        return _INDEX_CACHE["cars"]
    out = []
    if CARS_DIR.exists():
        for d in sorted(CARS_DIR.iterdir()):
            if not d.is_dir():
                continue
            ui = _read_ui_json(d / "ui" / "ui_car.json")
            specs = ui.get("specs", {}) or {}
            real_name = (ui.get("name") or "").strip()
            year = _extract_year(ui, d.name)
            entry = {
                "id": d.name,
                "name": real_name or d.name.replace("_", " ").title(),
                "real_name": bool(real_name),
                "brand": (ui.get("brand") or "").strip(),
                "class": (ui.get("class") or "").strip(),
                "year": year,
                "era": _era_from_year(year),
                "country": (ui.get("country") or "").strip(),
                "version": (ui.get("version") or "").strip(),
                "author": (ui.get("author") or "").strip(),
                "tags": ui.get("tags") or [],
                "bhp": (specs.get("bhp") or "").strip(),
                "torque": (specs.get("torque") or "").strip(),
                "weight": (specs.get("weight") or "").strip(),
                "topspeed": (specs.get("topspeed") or "").strip(),
                "acceleration": (specs.get("acceleration") or "").strip(),
                "pwratio": (specs.get("pwratio") or "").strip(),
                "skin_count": _count_skins(d),
                "has_preview": _car_preview(d) is not None,
            }
            entry["series"] = _classify_car_series(entry)
            out.append(entry)
    _INDEX_CACHE["cars"] = out
    _save_disk_cache()
    return out


def _count_skins(car_dir: Path):
    skins = car_dir / "skins"
    if not skins.exists():
        return 0
    return sum(1 for s in skins.iterdir() if s.is_dir())


def _index_tracks(force=False):
    if not force and _INDEX_CACHE["tracks"] is not None:
        return _INDEX_CACHE["tracks"]
    out = []
    if TRACKS_DIR.exists():
        for d in sorted(TRACKS_DIR.iterdir()):
            if not d.is_dir():
                continue
            ui_dir = d / "ui"
            if not ui_dir.exists():
                continue
            primary = _read_ui_json(ui_dir / "ui_track.json")
            layouts = []
            if primary:
                layouts.append(("default", primary))
            for sub in sorted(ui_dir.iterdir()):
                if sub.is_dir():
                    j = _read_ui_json(sub / "ui_track.json")
                    if j:
                        layouts.append((sub.name, j))
            if not layouts:
                continue
            _, p = layouts[0]
            real_name = (p.get("name") or "").strip()
            year = _extract_year(p, d.name)
            entry = {
                "id": d.name,
                "name": real_name or d.name.replace("_", " ").title(),
                "real_name": bool(real_name),
                "country": (p.get("country") or "").strip(),
                "city": (p.get("city") or "").strip(),
                "length": (p.get("length") or "").strip(),
                "width": (p.get("width") or "").strip(),
                "pitboxes": p.get("pitboxes"),
                "run": (p.get("run") or "").strip(),
                "year": year,
                "era": _era_from_year(year),
                "tags": p.get("tags") or [],
                "layouts": [n for n, _u in layouts if n != "default"],
                "has_preview": _track_preview(d) is not None,
            }
            entry["category"] = _classify_track_category(entry)
            out.append(entry)
    _INDEX_CACHE["tracks"] = out
    _save_disk_cache()
    return out


def _serve_content_preview(handler, kind, item_id, *, skin=None, layout=None):
    if kind == "cars":
        base, finder = CARS_DIR, _car_preview
        mime_default = "image/jpeg"
    elif kind == "tracks":
        base, finder = TRACKS_DIR, _track_preview
        mime_default = "image/png"
    else:
        handler.send_error(404)
        return
    item_dir = (base / item_id).resolve()
    try:
        item_dir.relative_to(base.resolve())
    except ValueError:
        handler.send_error(400, "outside content dir")
        return
    if not item_dir.exists():
        handler.send_error(404)
        return
    p = None
    # Specific skin / layout request — sandbox by ensuring no path components
    if kind == "cars" and skin and "/" not in skin and ".." not in skin:
        candidate = item_dir / "skins" / skin / "preview.jpg"
        if candidate.exists():
            p = candidate
    if kind == "tracks" and layout and "/" not in layout and ".." not in layout:
        candidate = item_dir / "ui" / layout / "preview.png"
        if candidate.exists():
            p = candidate
    if not p:
        p = finder(item_dir)
    if not p:
        handler.send_error(404)
        return
    ext = p.suffix.lower()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, mime_default)
    handler._file(p, mime)


# -- Unified challenge dashboard --------------------------------------------

def _parse_time_ms(s):
    """'1:10.899' or '7:51.751' or '76665' (ms) → integer ms."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    if not s:
        return None
    if ":" in s:
        try:
            mins, rest = s.split(":", 1)
            return int(int(mins) * 60_000 + float(rest) * 1000)
        except Exception:
            return None
    try:
        return int(float(s))
    except Exception:
        return None


def _fmt_ms(ms):
    if ms is None or ms <= 0:
        return "—"
    s = ms / 1000.0
    m = int(s // 60)
    sec = s - m * 60
    return f"{m}:{sec:06.3f}"


def _fmt_gap(delta_ms):
    if delta_ms is None:
        return "—"
    sign = "+" if delta_ms >= 0 else "−"
    return f"{sign}{abs(delta_ms) / 1000:.3f}s"


def _gap_class(delta_ms):
    if delta_ms is None:
        return ""
    if delta_ms <= 0:
        return "is-under"
    if delta_ms < 1000:
        return "is-near"
    if delta_ms < 5000:
        return "is-mid"
    return "is-far"


def _read_personalbest():
    """Parse Documents/Assetto Corsa/personalbest.ini → {SECTION_KEY: ms}."""
    path = AC_DOC / "personalbest.ini"
    out = {}
    if not path.exists():
        return out
    section = None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
            elif line.startswith("TIME=") and section:
                try:
                    out[section] = int(line.split("=", 1)[1].strip())
                except ValueError:
                    pass
    except Exception:
        pass
    return out


def _challenge_pb_ms(cfg):
    """Resolve the player's PB for this challenge.

    `current_pb_ms` is an explicit override and wins outright. Otherwise return
    the best (lowest) ms across every known source: hand-curated `you_history`
    file, AC's `personalbest.ini` section, and the auto-results index written
    by `launcher/update_results.py` after each AC session. The index path means
    a fresh hotlap shows up on the detail page even when AC didn't write a
    matching `personalbest.ini` section (different naming, hotlap-mode quirks).
    """
    bm = cfg.get("benchmarks") or {}
    if cfg.get("current_pb_ms"):
        return int(cfg["current_pb_ms"])

    candidates = []

    history = bm.get("you_history")
    if history:
        try:
            data = json.loads((AC_DOC / history).read_text(encoding="utf-8"))
            mss = [d.get("pb_ms") for d in data if d.get("pb_ms")]
            if mss:
                candidates.append(min(mss))
        except Exception:
            pass

    sect = bm.get("you_section")
    if sect:
        pb_ini = _read_personalbest().get(sect)
        if pb_ini:
            candidates.append(pb_ini)

    last = _load_results_index().get(cfg.get("id"))
    if last:
        last_ms = _parse_time_ms((last.get("summary") or {}).get("best_lap"))
        if last_ms:
            candidates.append(last_ms)

    return min(candidates) if candidates else None


def _load_history(cfg):
    """Return (kind, list[entries]) — 'hotlap' or 'race' depending on data shape."""
    bm = cfg.get("benchmarks") or {}
    rel = bm.get("you_history")
    if not rel:
        return None, []
    path = AC_DOC / rel
    if not path.exists():
        return None, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not data:
            return None, []
        sample = data[0]
        if "pb_ms" in sample:
            return "hotlap", data
        if "finish" in sample:
            return "race", data
    except Exception:
        pass
    return None, []


def _load_duel_history(cfg):
    """Scan dashboard/results/snapshots/ and return per-skin history for a duel.
    Matches by skin (since duels with different chassis per launcher would be
    missed if we filtered by ac_car_id). Track filter still applies — we don't
    want a different track's snapshot to leak in. Returns:
    {skin: [{ts, finish, win, best_ms, field}], ...}, sorted oldest→newest."""
    snaps_dir = AC_DOC / "dashboard" / "results" / "snapshots"
    if not snaps_dir.exists():
        return {}
    # Build allowed (car, skin, track) tuples from the launchers; fall back to
    # cfg-level fields when launchers list is missing.
    allowed_tracks = set()
    track_main = f"{cfg.get('ac_track_id','')}-{cfg.get('ac_track_layout','')}"
    if track_main and track_main != "-":
        allowed_tracks.add(track_main)
    skin_set = set()
    car_set = set()
    for lc in cfg.get("launchers") or []:
        if lc.get("skin"):
            skin_set.add(lc["skin"])
        if lc.get("ac_car_id"):
            car_set.add(lc["ac_car_id"])
    if not skin_set:
        skin_set.add(cfg.get("ac_car_skin", ""))
    if not car_set:
        car_set.add(cfg.get("ac_car_id", ""))
    skin_set.discard("")
    car_set.discard("")
    history = {}
    for f in sorted(snaps_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        players = d.get("players") or []
        if not players: continue
        p0 = players[0]
        if d.get("track") not in allowed_tracks: continue
        if p0.get("car") not in car_set: continue
        skin = p0.get("skin", "")
        if skin not in skin_set: continue
        sessions = d.get("sessions") or []
        s = sessions[0] if sessions else {}
        if s.get("type") != 3: continue  # race only
        if len(players) != 2: continue   # duel only
        laps = s.get("laps") or []
        valid = [l for l in laps if l.get("car") == 0 and not l.get("cuts") and l.get("time")]
        best = min((l["time"] for l in valid), default=None)
        rr = s.get("raceResult") or []
        finish = (rr.index(0) + 1) if (rr and 0 in rr) else None
        history.setdefault(skin, []).append({
            "ts":      f.stem,
            "finish":  finish,
            "win":     finish == 1,
            "best_ms": best,
            "field":   len(players),
        })
    return history


def _render_lap_sparkline(runs, accent_color, width=320, height=72):
    """Inline SVG mini chart of best-lap-ms across sessions.
    runs: list of {ts, best_ms, finish, win} oldest→newest. Empty/None lap times
    are rendered as 'no data' baseline ticks. Always renders something —
    never empty, so the panel layout stays balanced."""
    n = len(runs)
    if n == 0:
        return (
            f'<div class="dp-chart-empty">No sessions yet · '
            f'<span class="dp-chart-empty-em">launch to start your record</span></div>'
        )
    pad_l, pad_r, pad_t, pad_b = 6, 6, 8, 18
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    times = [r.get("best_ms") for r in runs if r.get("best_ms")]
    has_times = len(times) > 0
    if has_times:
        tmin, tmax = min(times), max(times)
        if tmin == tmax:
            tmin -= 1000; tmax += 1000  # avoid zero range
        def y_for(ms):
            return pad_t + plot_h * (1 - (tmax - ms) / (tmax - tmin))
    points = []
    dots = ""
    finishes = ""
    for i, r in enumerate(runs):
        x = pad_l + (plot_w * i / max(n - 1, 1))
        if has_times and r.get("best_ms"):
            y = y_for(r["best_ms"])
            points.append(f"{x:.1f},{y:.1f}")
            dots += (
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" '
                f'fill="{accent_color}" stroke="#000" stroke-width="1.2"/>'
            )
        # finish-position dots along the bottom edge
        fy = height - 6
        fcolor = accent_color if r.get("win") else "rgba(255,255,255,0.32)"
        finishes += (
            f'<circle cx="{x:.1f}" cy="{fy:.1f}" r="2.6" fill="{fcolor}"/>'
        )
    line = ""
    if len(points) >= 2:
        line = (
            f'<polyline points="{" ".join(points)}" fill="none" '
            f'stroke="{accent_color}" stroke-width="1.7" stroke-linejoin="round"/>'
        )
    elif len(points) == 1:
        # single point: show as standalone dot only (already in `dots`)
        pass
    if not has_times:
        # baseline placeholder line
        ymid = pad_t + plot_h / 2
        line = (
            f'<line x1="{pad_l}" y1="{ymid}" x2="{pad_l + plot_w}" y2="{ymid}" '
            f'stroke="rgba(255,255,255,0.22)" stroke-width="1" stroke-dasharray="3 3"/>'
        )
    return (
        f'<svg class="dp-chart" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">'
        f'{line}{dots}{finishes}'
        f'</svg>'
    )


def _render_driver_stats(runs):
    """Compact stats strip: sessions · wins · best lap."""
    n = len(runs)
    wins = sum(1 for r in runs if r.get("win"))
    times = [r["best_ms"] for r in runs if r.get("best_ms")]
    best = min(times) if times else None
    best_str = _fmt_ms(best) if best else "—"
    return (
        f'<div class="dp-stats">'
        f'<div class="dp-stat"><span class="dp-stat-val mono">{n}</span>'
        f'<span class="dp-stat-lbl">Sessions</span></div>'
        f'<div class="dp-stat"><span class="dp-stat-val mono">{wins}</span>'
        f'<span class="dp-stat-lbl">Wins</span></div>'
        f'<div class="dp-stat"><span class="dp-stat-val mono">{best_str}</span>'
        f'<span class="dp-stat-lbl">Best lap</span></div>'
        f'</div>'
    )


def _render_h2h(cfg, history):
    """Head-to-head tally + last-5 timeline for dual-driver duels."""
    launchers = cfg.get("launchers") or []
    if len(launchers) < 2:
        return ""
    rows = []
    for lc in launchers:
        skin = lc.get("skin", "")
        runs = history.get(skin, [])
        wins = sum(1 for r in runs if r.get("win"))
        rows.append({
            "label":  lc.get("label", ""),
            "color":  lc.get("color", "#fff"),
            "logo":   lc.get("logo", ""),
            "wins":   wins,
            "runs":   len(runs),
            "skin":   skin,
        })
    if all(r["runs"] == 0 for r in rows):
        return ""
    total_wins = sum(r["wins"] for r in rows) or 1
    bar_segments = ""
    for r in rows:
        pct = (r["wins"] / total_wins) * 100 if total_wins else 50
        bar_segments += (
            f'<div class="h2h-bar-seg" '
            f'style="flex-basis:{pct:.1f}%;background:{r["color"]}" '
            f'title="{escape(r["label"])}: {r["wins"]} wins"></div>'
        )
    cards = ""
    for r in rows:
        cards += (
            f'<div class="h2h-card" style="--accent:{r["color"]}">'
            f'<div class="h2h-team-logo">{_team_logo_svg(r["logo"])}</div>'
            f'<div class="h2h-tally">'
            f'<span class="h2h-wins mono">{r["wins"]}</span>'
            f'<span class="h2h-of mono">/ {r["runs"]}</span>'
            f'</div>'
            f'<div class="h2h-label">{escape(r["label"])} WINS</div>'
            f'</div>'
        )
    return (
        '<section class="cd-section h2h-section">'
        '<h2 class="cd-h2">Head-to-head</h2>'
        f'<div class="h2h-bar">{bar_segments}</div>'
        f'<div class="h2h-cards">{cards}</div>'
        '</section>'
    )


def _render_track_section(cfg):
    """Track section: photo carousel + facts + outline. Pulls bcr*.jpg from the
    track ui folder + extension/backgrounds for the carousel."""
    ac_root = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa")
    if not ac_root.exists(): return ""
    track_id = cfg.get("ac_track_id", "")
    layout = cfg.get("ac_track_layout", "")
    if not track_id: return ""
    ui_dir = ac_root / "content" / "tracks" / track_id / "ui" / layout
    j = ui_dir / "ui_track.json"
    if not j.exists(): return ""
    try:
        ui = json.loads(_escape_ctrl_in_strings(j.read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        return ""
    name = ui.get("name") or layout
    length = ui.get("length") or "—"
    width = ui.get("width") or "—"
    pitboxes = ui.get("pitboxes") or "—"
    country = ui.get("country") or ""
    description = (ui.get("description") or "").strip()

    # Collect photos: (1) bcr0..N.jpg in the layout ui folder (highest priority);
    # (2) <track_id>_*.jpg from extension/backgrounds; (3) preview.png as fallback
    photos = []
    for n in range(10):
        p = ui_dir / f"bcr{n}.jpg"
        if p.exists():
            photos.append(("track-asset", f"track={track_id}&layout={layout}&file=bcr{n}.jpg"))
    bg_dir = ac_root / "extension" / "backgrounds"
    if bg_dir.exists():
        for p in sorted(bg_dir.glob(f"{track_id}_*.jpg")):
            photos.append(("ext-asset", f"file={p.name}"))
    if not photos:
        preview = ui_dir / "preview.png"
        if preview.exists():
            photos.append(("track-asset", f"track={track_id}&layout={layout}&file=preview.png"))
    slides_html = ""
    dots_html = ""
    if photos:
        slides_html = "".join(
            f'<img src="/{kind}?{q}" alt="{escape(name)}" loading="lazy" '
            f'class="carousel-slide{" is-active" if i == 0 else ""}">'
            for i, (kind, q) in enumerate(photos)
        )
        dots_html = "".join(
            f'<span class="carousel-dot{" is-active" if i == 0 else ""}"></span>'
            for i in range(len(photos))
        )
    carousel_html = (
        f'<div class="carousel tk-carousel">{slides_html}'
        f'<div class="carousel-dots">{dots_html}</div></div>'
    ) if photos else (
        f'<div class="tk-carousel tk-carousel-empty"></div>'
    )
    facts = [
        ("LENGTH",    str(length) + (" m" if str(length).replace('.','',1).isdigit() else "")),
        ("WIDTH",     str(width) + (" m" if str(width).replace('.','',1).isdigit() else "")),
        ("PIT BOXES", str(pitboxes)),
        ("COUNTRY",   str(country) or "—"),
    ]
    facts_html = "".join(
        f'<div class="tk-fact"><span class="tk-fact-lbl">{escape(k)}</span>'
        f'<span class="tk-fact-val mono">{escape(v)}</span></div>'
        for k, v in facts
    )
    outline_path = ui_dir / "outline.png"
    outline_html = ""
    if outline_path.exists():
        outline_html = (
            f'<div class="tk-outline">'
            f'<img src="/track-asset?track={escape(track_id)}'
            f'&amp;layout={escape(layout)}&amp;file=outline.png" alt="">'
            f'</div>'
        )
    desc_html = ""
    if description:
        # Strip basic HTML tags from AC descriptions
        plain = re.sub(r"<[^>]+>", " ", description)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            desc_html = f'<p class="tk-desc">{escape(plain[:280])}{"…" if len(plain) > 280 else ""}</p>'
    return (
        '<section class="cd-section tk-section">'
        '<h2 class="cd-h2">The track</h2>'
        '<div class="tk-grid">'
        f'<div class="tk-photos">{carousel_html}</div>'
        '<div class="tk-side">'
        f'<div class="tk-name">{escape(name)}</div>'
        f'{outline_html}'
        f'<div class="tk-facts">{facts_html}</div>'
        '</div>'
        '</div>'
        f'{desc_html}'
        '</section>'
    )


# Curated explainer for AC setup keys. Each entry: (display label, group, blurb).
_SETUP_KEY_INFO = {
    "TYRES":           ("Tyre compound",     "TYRES",      "0 = Hard slick · 1 = Wet (no Soft/Medium on this car)"),
    "FUEL":            ("Fuel load",         "TYRES",      "Litres on board at race start. Lighter = quicker but limited range."),
    "WING_1":          ("Front wing",        "AERO",       "Higher = more front downforce + drag. Adds turn-in grip."),
    "WING_2":          ("Rear wing",         "AERO",       "Higher = more rear downforce + drag. Cuts top speed but stabilises."),
    "BRAKE_DUCT_F":    ("Front brake duct",  "AERO",       "Cooling. Smaller = less drag, hotter brakes."),
    "FRONT_BIAS":      ("Brake bias",        "BRAKES",     "% of braking force on the front axle. Higher = stable, locks fronts."),
    "DIFF_PRELOAD":    ("Diff preload",      "DIFF",       "Static lock-up. More = stable on entry, more push on exit."),
    "MGUK_DELIVERY":   ("MGU-K delivery",    "DIFF",       "ERS hybrid deployment mode."),
    "ARB_F":           ("Front anti-roll",   "SUSPENSION", "Stiffer = less front roll, more understeer."),
    "ARB_R":           ("Rear anti-roll",    "SUSPENSION", "Stiffer = less rear roll, more oversteer."),
    "SPRING_RATE_LF_C1": ("Front spring",    "SUSPENSION", "Front-axle spring rate. Stiffer = sharper response, harsher kerbs."),
    "SPRING_RATE_LR_C1": ("Rear spring",     "SUSPENSION", "Rear-axle spring rate. Stiffer = better traction off curbs."),
    "TORSION_RATE_LF_0": ("Front torsion",   "SUSPENSION", "Front torsion-bar stiffness."),
    "TORSION_RATE_LR_0": ("Rear torsion",    "SUSPENSION", "Rear torsion-bar stiffness."),
    "DAMPER_BUMP_LF_C0":     ("F bump (slow)",    "DAMPERS",    "Slow-bump damping front."),
    "DAMPER_BUMP_LR_C0":     ("R bump (slow)",    "DAMPERS",    "Slow-bump damping rear."),
    "DAMPER_REBOUND_LF_C0":  ("F rebound (slow)", "DAMPERS",    "Slow-rebound damping front."),
    "DAMPER_REBOUND_LR_C0":  ("R rebound (slow)", "DAMPERS",    "Slow-rebound damping rear."),
    "DAMPER_FAST_BUMP_LF_C0":    ("F bump (fast)",    "DAMPERS", "High-speed bump (curbs/jumps)."),
    "DAMPER_FAST_REBOUND_LF_C0": ("F rebound (fast)", "DAMPERS", "High-speed rebound front."),
    "CAMBER_LF":       ("Camber LF",         "ALIGNMENT",  "Negative tilts top of tyre inward — more cornering grip, less straight-line traction."),
    "CAMBER_RF":       ("Camber RF",         "ALIGNMENT",  "Symmetrical to LF on most setups."),
    "CAMBER_LR":       ("Camber LR",         "ALIGNMENT",  "Less negative on the rear for traction."),
    "CAMBER_RR":       ("Camber RR",         "ALIGNMENT",  "Symmetrical to LR."),
    "PRESSURE_LF":     ("Pressure LF",       "PRESSURES",  "Cold tyre PSI front-left. Lower = more grip, higher wear."),
    "PRESSURE_RF":     ("Pressure RF",       "PRESSURES",  "Cold PSI front-right."),
    "PRESSURE_LR":     ("Pressure LR",       "PRESSURES",  "Cold PSI rear-left."),
    "PRESSURE_RR":     ("Pressure RR",       "PRESSURES",  "Cold PSI rear-right."),
    "BUMPSTOP_LF_C0":  ("F bumpstop",        "SUSPENSION", "Length of bumpstop rubber — caps suspension travel."),
    "BUMPSTOP_LR_C0":  ("R bumpstop",        "SUSPENSION", "Rear bumpstop length."),
}

_SETUP_GROUP_ORDER = ["TYRES", "AERO", "BRAKES", "DIFF", "SUSPENSION", "DAMPERS", "ALIGNMENT", "PRESSURES"]
_SETUP_GROUP_META = {
    "TYRES":      ("TYRES & FUEL",  "What the car is wearing and how heavy it starts"),
    "AERO":       ("AERO",          "Wings, brake ducts — drag vs downforce"),
    "BRAKES":     ("BRAKES",        "Where the stopping power lives"),
    "DIFF":       ("DIFFERENTIAL",  "How the rear wheels share torque"),
    "SUSPENSION": ("SUSPENSION",    "Springs, anti-roll bars, bump-stops"),
    "DAMPERS":    ("DAMPERS",       "Slow + fast compression/rebound"),
    "ALIGNMENT":  ("ALIGNMENT",     "Camber — wheel tilt for cornering"),
    "PRESSURES":  ("TYRE PRESSURES","Cold PSI · 4 corners"),
}


def _render_ac_setup_section(cfg):
    """Read a setup ini under setups/<car>/<track>/ and present the user-facing
    values grouped by category with explainers. Skips CUSTOM_SCRIPT_ITEM_* keys
    (those are mod-internal power maps / gear ratios, not user setup).
    Lookup order: cfg["setup_file"] → 1.ini → first *.ini alphabetically."""
    car = cfg.get("ac_car_id")
    track = cfg.get("ac_track_id")
    if not car or not track:
        return ""
    setup_dir = AC_DOC / "setups" / car / track
    if not setup_dir.is_dir():
        return ""
    setup_path = None
    if cfg.get("setup_file"):
        cand = setup_dir / cfg["setup_file"]
        if cand.exists():
            setup_path = cand
    if not setup_path:
        cand = setup_dir / "1.ini"
        if cand.exists():
            setup_path = cand
    if not setup_path:
        inis = sorted(setup_dir.glob("*.ini"))
        if inis:
            setup_path = inis[0]
    if not setup_path:
        return ""
    parsed = {}
    try:
        text = setup_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    cur = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            continue
        if "=" in line and cur:
            k, v = line.split("=", 1)
            if k.strip() == "VALUE":
                parsed[cur] = v.strip()
    # Build group → rows
    groups = {g: [] for g in _SETUP_GROUP_ORDER}
    for key, val in parsed.items():
        info = _SETUP_KEY_INFO.get(key)
        if not info:
            continue
        label, group, blurb = info
        if group not in groups:
            continue
        # Format value with helpful suffixes
        display = val
        if key == "TYRES":
            display = "Hard (slick)" if val == "0" else ("Wet" if val == "1" else val)
        elif key == "FUEL":
            display = f"{val} L"
        elif key == "FRONT_BIAS":
            display = f"{val}%"
        elif key.startswith("PRESSURE_"):
            display = f"{val} psi"
        elif key.startswith("CAMBER_"):
            try:
                display = f"{float(val) / 10:.1f}°" if val.lstrip("-").isdigit() else val
            except Exception:
                pass
        elif key.startswith("WING_"):
            display = f"{val}/11" if val.isdigit() else val
        groups[group].append({"key": key, "label": label, "value": display, "blurb": blurb})
    # Render
    blocks = ""
    for g in _SETUP_GROUP_ORDER:
        rows = groups.get(g) or []
        if not rows:
            continue
        meta = _SETUP_GROUP_META.get(g, (g, ""))
        rows_html = "".join(
            f'<div class="su-row">'
            f'<div class="su-row-label">{escape(r["label"])}</div>'
            f'<div class="su-row-value mono">{escape(str(r["value"]))}</div>'
            f'<div class="su-row-blurb">{escape(r["blurb"])}</div>'
            f'</div>'
            for r in rows
        )
        blocks += (
            f'<article class="su-group">'
            f'<header class="su-group-head">'
            f'<div class="su-group-name">{escape(meta[0])}</div>'
            f'<div class="su-group-deck">{escape(meta[1])}</div>'
            f'</header>'
            f'<div class="su-rows">{rows_html}</div>'
            f'</article>'
        )
    if not blocks:
        return ""
    setup_name = setup_path.stem
    return (
        '<section class="cd-section su-section">'
        f'<h2 class="cd-h2">Setup · "{escape(setup_name)}"</h2>'
        f'<p class="su-deck">Reading the live setup saved as <code>{escape(setup_path.name)}</code> in your '
        f'<code>setups/{escape(car)}/{escape(track)}/</code> folder. Edit it in CM and reload to see your changes here.</p>'
        f'<div class="su-grid">{blocks}</div>'
        '</section>'
    )


def _render_track_dna(cfg):
    """Visual track-fact card. Reads ui_track.json from the AC install."""
    ac_root = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa")
    if not ac_root.exists(): return ""
    track_id = cfg.get("ac_track_id", "")
    layout = cfg.get("ac_track_layout", "")
    ui_dir = ac_root / "content" / "tracks" / track_id / "ui" / layout
    j = ui_dir / "ui_track.json"
    if not j.exists(): return ""
    try:
        ui = json.loads(_escape_ctrl_in_strings(j.read_text(encoding="utf-8", errors="ignore")))
    except Exception:
        return ""
    name = ui.get("name") or layout
    length = ui.get("length") or "—"
    width = ui.get("width") or "—"
    pitboxes = ui.get("pitboxes") or "—"
    country = ui.get("country") or ""
    geo = ui.get("geotags") or ""
    outline_url = f"/content/tracks/{track_id}/preview?layout={layout}"
    facts = [
        ("LENGTH",     str(length) + (" m" if str(length).isdigit() else "")),
        ("WIDTH",      str(width) + (" m" if str(width).replace('.','',1).isdigit() else "")),
        ("PIT BOXES",  str(pitboxes)),
        ("COUNTRY",    str(country) or "—"),
    ]
    facts_html = "".join(
        f'<div class="td-fact"><span class="td-fact-lbl">{escape(k)}</span>'
        f'<span class="td-fact-val mono">{escape(v)}</span></div>'
        for k, v in facts
    )
    outline_path = ui_dir / "outline.png"
    outline_html = ""
    if outline_path.exists():
        outline_html = (
            f'<div class="td-outline">'
            f'<img src="/track-asset?track={escape(track_id)}'
            f'&amp;layout={escape(layout)}&amp;file=outline.png" alt="Track outline">'
            f'</div>'
        )
    return (
        '<section class="cd-section td-section">'
        '<h2 class="cd-h2">Track DNA</h2>'
        '<div class="td-grid">'
        f'<div class="td-name">{escape(name)}</div>'
        f'{outline_html}'
        f'<div class="td-facts">{facts_html}</div>'
        '</div>'
        '</section>'
    )


def _render_drivers_section(cfg):
    """DRIVERS — portrait + tagline + name + team + quote. No CTA, no stats."""
    launchers = cfg.get("launchers") or []
    rich = [lc for lc in launchers if lc.get("driver") and lc.get("quote")]
    if len(rich) < 2:
        return ""
    panels = ""
    for lc in rich:
        logo = lc.get("logo", "")
        portrait = lc.get("portrait")
        if portrait and (IMAGES_DIR / portrait).exists():
            portrait_html = (
                f'<div class="dr-portrait">'
                f'<img src="/images/{escape(portrait)}" alt="{escape(lc.get("driver", ""))}">'
                f'</div>'
            )
        else:
            portrait_html = (
                f'<div class="dr-portrait dr-portrait-fallback">'
                f'<div class="dr-num-big">#{escape(lc.get("number", ""))}</div>'
                f'</div>'
            )
        panels += (
            f'<article class="dr-panel dr-{escape(logo)}">'
            f'{portrait_html}'
            f'<div class="dr-body">'
            f'<div class="dr-tag">{escape(lc.get("tagline", ""))}</div>'
            f'<h3 class="dr-name">{escape(lc.get("driver", ""))} '
            f'<span class="dr-num-inline">#{escape(lc.get("number", ""))}</span></h3>'
            f'<div class="dr-team">'
            f'<span class="dr-team-logo">{_team_logo_svg(logo)}</span>'
            f'<span>{escape(lc.get("team", ""))}</span>'
            f'</div>'
            f'<p class="dr-quote">"{escape(lc.get("quote", ""))}"</p>'
            f'</div>'
            f'</article>'
        )
    return (
        '<section class="cd-section dr-section">'
        '<h2 class="cd-h2">The drivers</h2>'
        f'<div class="dr-grid">{panels}</div>'
        '</section>'
    )


def _render_cars_section(cfg):
    """CARS — handles two cases:
       (a) Same chassis, two liveries (e.g. Antonelli/Verstappen on VRC Alpha 2025)
       (b) Different chassis per launcher (e.g. Verstappen Mercedes vs Haase Audi)
    """
    launchers = cfg.get("launchers") or []
    if len(launchers) < 2:
        return ""
    # Resolve each launcher's car_id (fall back to cfg.ac_car_id)
    enriched = []
    for lc in launchers:
        car_id = lc.get("ac_car_id") or cfg.get("ac_car_id")
        enriched.append({**lc, "_car_id": car_id})
    same_chassis = len({e["_car_id"] for e in enriched if e["_car_id"]}) == 1

    def car_card(e):
        car_id = e["_car_id"]
        skin = e.get("skin", "")
        logo = e.get("logo", "")
        accent = e.get("color", "#fff")
        car_meta = _ac_car_meta(car_id) if car_id else None
        chassis_name = car_meta.get("name", car_id) if car_meta else (car_id or "")
        brand = car_meta.get("brand", "") if car_meta else ""
        # Specs strip for this individual car (only when chassis differs per CTA)
        specs_html = ""
        if car_meta:
            year = car_meta.get("year", "")
            bhp = car_meta.get("bhp", "")
            weight = car_meta.get("weight", "")
            bits = []
            if year:    bits.append(("YEAR", str(year)))
            if bhp:     bits.append(("POWER", str(bhp)))
            if weight:  bits.append(("WEIGHT", str(weight)))
            specs_html = "".join(
                f'<div class="cs-spec"><span class="cs-spec-lbl">{escape(k)}</span>'
                f'<span class="cs-spec-val mono">{escape(v)}</span></div>'
                for k, v in bits
            )
        img_url = None
        if car_id and skin and (CARS_DIR / car_id / "skins" / skin / "preview.jpg").exists():
            img_url = f"/content/cars/{car_id}/preview?skin={quote(skin, safe='')}"
        elif car_id and skin and (CARS_DIR / car_id / "skins" / skin / "livery.png").exists():
            img_url = f"/content/cars/{car_id}/preview?skin={quote(skin, safe='')}"
        elif car_id:
            img_url = f"/content/cars/{car_id}/preview"
        img_html = (
            f'<img class="cs-livery-img" src="{img_url}" alt="" loading="lazy">'
            if img_url else
            '<div class="cs-livery-img cs-livery-fallback"></div>'
        )
        chassis_block = ""
        if not same_chassis:
            chassis_block = (
                f'<div class="cs-chassis-inline">'
                f'<div class="cs-chassis-inline-name">{escape(chassis_name)}</div>'
                f'<div class="cs-chassis-inline-brand">{escape(brand)}</div>'
                f'<div class="cs-chassis-inline-specs">{specs_html}</div>'
                f'</div>'
            )
        return (
            f'<article class="cs-card cs-{escape(logo)}" style="--accent:{accent}">'
            f'<div class="cs-livery-wrap">{img_html}</div>'
            f'{chassis_block}'
            f'<div class="cs-meta">'
            f'<div class="cs-meta-num mono">#{escape(e.get("number", ""))}</div>'
            f'<div class="cs-meta-team">{escape(e.get("team", ""))}</div>'
            f'<div class="cs-meta-driver">{escape(e.get("driver", ""))}</div>'
            f'</div>'
            f'</article>'
        )

    cards_html = "".join(car_card(e) for e in enriched)

    if same_chassis:
        car_id = enriched[0]["_car_id"]
        car_meta = _ac_car_meta(car_id) if car_id else None
        chassis_name = car_meta.get("name", car_id) if car_meta else car_id
        brand = car_meta.get("brand", "") if car_meta else ""
        chassis_meta_html = ""
        if car_meta:
            bits = []
            for k, v in (("YEAR", car_meta.get("year", "")),
                         ("POWER", car_meta.get("bhp", "")),
                         ("WEIGHT", car_meta.get("weight", "")),
                         ("TOP SPEED", car_meta.get("topspeed", ""))):
                if v: bits.append((k, str(v)))
            chassis_meta_html = "".join(
                f'<div class="cs-spec"><span class="cs-spec-lbl">{escape(k)}</span>'
                f'<span class="cs-spec-val mono">{escape(v)}</span></div>'
                for k, v in bits
            )
        chassis_header = (
            '<div class="cs-chassis">'
            '<div class="cs-chassis-lbl">Same chassis · two liveries</div>'
            f'<div class="cs-chassis-name">{escape(chassis_name)}</div>'
            f'<div class="cs-chassis-brand">{escape(brand)}</div>'
            f'<div class="cs-chassis-specs">{chassis_meta_html}</div>'
            '</div>'
        )
    else:
        chassis_header = (
            '<div class="cs-chassis cs-chassis-versus">'
            '<div class="cs-chassis-lbl">Two factory chassis · head-to-head</div>'
            '</div>'
        )
    return (
        '<section class="cd-section cs-section">'
        '<h2 class="cd-h2">The cars</h2>'
        f'{chassis_header}'
        f'<div class="cs-grid">{cards_html}</div>'
        '</section>'
    )


def _render_choose_section(cfg, history=None):
    """CTA — compact launch buttons with per-driver stats + sparkline."""
    launchers = cfg.get("launchers") or []
    if len(launchers) < 2:
        return ""
    history = history or {}
    # Total wins to compute the H2H bar split
    totals = []
    for lc in launchers:
        runs = history.get(lc.get("skin", ""), [])
        totals.append({
            "lc":     lc,
            "runs":   runs,
            "wins":   sum(1 for r in runs if r.get("win")),
            "color":  lc.get("color", "#fff"),
        })
    total_wins_sum = sum(t["wins"] for t in totals)
    bar_segments = ""
    if total_wins_sum > 0:
        for t in totals:
            pct = (t["wins"] / total_wins_sum) * 100
            bar_segments += (
                f'<div class="ch-h2h-seg" '
                f'style="flex-basis:{pct:.1f}%;background:{t["color"]}" '
                f'title="{escape(t["lc"].get("label",""))}: {t["wins"]} wins"></div>'
            )
    else:
        # No wins yet — split 50/50 with muted shade so the bar isn't empty
        for t in totals:
            bar_segments += (
                f'<div class="ch-h2h-seg ch-h2h-empty" '
                f'style="flex-basis:50%;background:{t["color"]};opacity:0.25"></div>'
            )
    h2h_bar_html = (
        '<div class="ch-h2h">'
        '<div class="ch-h2h-lbl">Head-to-head record</div>'
        f'<div class="ch-h2h-bar">{bar_segments}</div>'
        '<div class="ch-h2h-totals">'
        + ''.join(
            f'<span class="ch-h2h-total" style="--accent:{t["color"]}">'
            f'<span class="ch-h2h-total-val mono">{t["wins"]}</span>'
            f'<span class="ch-h2h-total-of mono">/ {len(t["runs"])}</span>'
            f'<span class="ch-h2h-total-lbl">{escape(t["lc"].get("label",""))}</span>'
            f'</span>'
            for t in totals
        )
        + '</div>'
        '</div>'
    )
    cards = ""
    for t in totals:
        lc = t["lc"]
        logo = lc.get("logo", "")
        accent = t["color"]
        runs = t["runs"]
        wins = t["wins"]
        rival_wins = total_wins_sum - wins
        stats_html = _render_driver_stats(runs)
        chart_html = _render_lap_sparkline(runs, accent, width=320, height=56)
        # Inline rival-comparison row (replaces standalone H2H section)
        record_html = (
            f'<div class="ch-record">'
            f'<span class="ch-record-mine mono">{wins}W</span>'
            f'<span class="ch-record-vs">vs</span>'
            f'<span class="ch-record-rival mono">{rival_wins}W</span>'
            f'<span class="ch-record-lbl">RIVAL</span>'
            f'</div>'
        )
        cards += (
            f'<article class="ch-card ch-{escape(logo)}" style="--accent:{accent}">'
            f'<div class="ch-card-head">'
            f'<div class="ch-team-mark">{_team_logo_svg(logo)}</div>'
            f'<div class="ch-card-title">'
            f'<div class="ch-card-tagline">{escape(lc.get("tagline", ""))}</div>'
            f'<div class="ch-card-driver">{escape(lc.get("driver", ""))}</div>'
            f'</div>'
            f'{record_html}'
            f'</div>'
            f'{stats_html}'
            f'<div class="dp-chart-wrap">'
            f'<div class="dp-chart-lbl">Best-lap progression · finish dots</div>'
            f'{chart_html}'
            f'</div>'
            f'<button class="btn-launch-team ch-cta {escape(logo)}" '
            f'onclick="launchConfig({escape(json.dumps(cfg["id"]))},'
            f'{escape(json.dumps(cfg["title"] + " · " + lc.get("label", "LAUNCH")))},'
            f'{escape(json.dumps(lc.get("cmd", "")))})">'
            f'{_team_logo_svg(logo)}'
            f'<span>{escape(lc.get("label", "LAUNCH"))}</span>'
            f'<span class="team-go">GO ▶</span>'
            f'</button>'
            f'</article>'
        )
    return (
        '<section class="cd-section ch-section">'
        '<h2 class="cd-h2">Choose your seat</h2>'
        f'{h2h_bar_html}'
        f'<div class="ch-grid">{cards}</div>'
        '</section>'
    )


def _render_driver_perspectives(cfg, history=None):
    """Two side-by-side perspective panels for dual-driver duels — now with
    per-skin stats + lap-time sparklines. Returns empty string for cfgs without
    2+ launchers carrying driver/quote data."""
    launchers = cfg.get("launchers") or []
    rich = [lc for lc in launchers if lc.get("driver") and lc.get("quote")]
    if len(rich) < 2:
        return ""
    history = history or {}
    panels = ""
    for lc in rich:
        logo = lc.get("logo", "")
        accent = lc.get("color", "#fff")
        portrait = lc.get("portrait")
        if portrait and (IMAGES_DIR / portrait).exists():
            portrait_html = (
                f'<div class="dp-portrait">'
                f'<img src="/images/{escape(portrait)}" alt="{escape(lc.get("driver", ""))}">'
                f'</div>'
            )
        else:
            portrait_html = (
                f'<div class="dp-portrait dp-portrait-fallback">'
                f'<div class="dp-num-big">#{escape(lc.get("number", ""))}</div>'
                f'</div>'
            )
        runs = history.get(lc.get("skin", ""), [])
        stats_html = _render_driver_stats(runs)
        chart_html = _render_lap_sparkline(runs, accent)
        panels += (
            f'<article class="dp-panel dp-{escape(logo)}">'
            f'{portrait_html}'
            f'<div class="dp-body">'
            f'<div class="dp-head">'
            f'<div class="dp-logo">{_team_logo_svg(logo)}</div>'
            f'<div class="dp-tag">{escape(lc.get("tagline", ""))}</div>'
            f'</div>'
            f'<h3 class="dp-driver">{escape(lc.get("driver", ""))} '
            f'<span class="dp-num-inline">#{escape(lc.get("number", ""))}</span></h3>'
            f'<div class="dp-team">{escape(lc.get("team", ""))}</div>'
            f'<p class="dp-quote">"{escape(lc.get("quote", ""))}"</p>'
            f'{stats_html}'
            f'<div class="dp-chart-wrap">'
            f'<div class="dp-chart-lbl">Best-lap progression · finish-pos dots</div>'
            f'{chart_html}'
            f'</div>'
            f'<button class="btn-launch-team dp-cta {escape(logo)}" '
            f'onclick="launchConfig({escape(json.dumps(cfg["id"]))},'
            f'{escape(json.dumps(cfg["title"] + " · " + lc.get("label", "LAUNCH")))},'
            f'{escape(json.dumps(lc.get("cmd", "")))})">'
            f'{_team_logo_svg(logo)}'
            f'<span>{escape(lc.get("label", "LAUNCH"))}</span>'
            f'<span class="team-go">GO ▶</span>'
            f'</button>'
            f'</div>'
            f'</article>'
        )
    return (
        '<section class="cd-section dp-section">'
        '<h2 class="cd-h2">Choose your driver</h2>'
        f'<div class="dp-grid">{panels}</div>'
        '</section>'
    )


def render_challenge_page(cfg):
    title_full = f"{cfg['title']} · Challenge"
    type_cls = cfg["type"].lower()
    type_label = cfg.get("type_label", cfg["type"])
    bm = cfg.get("benchmarks") or {}
    setup = cfg.get("setup") or {}
    refs = bm.get("refs") or []
    you_label = bm.get("you_label", "Your PB")
    pb_ms = _challenge_pb_ms(cfg)
    primary_ref_ms = _parse_time_ms(refs[0]["time"]) if refs else None
    delta_to_primary = (pb_ms - primary_ref_ms) if (pb_ms and primary_ref_ms) else None

    # Hero image: full carousel of all images (auto-rotates), with fallbacks.
    images = cfg.get("images") or []
    if images:
        slides = "".join(
            f'<img src="/images/{escape(name)}" alt="{escape(cfg["title"])}" '
            f'class="carousel-slide{" is-active" if i == 0 else ""}">'
            for i, name in enumerate(images)
        )
        dots = "".join(
            f'<span class="carousel-dot{" is-active" if i == 0 else ""}"></span>'
            for i in range(len(images))
        )
        hero_img = (
            f'<div class="carousel cd-hero-carousel">{slides}'
            f'<div class="carousel-dots">{dots}</div></div>'
        )
    elif (IMAGES_DIR / f"{cfg['id']}.jpg").exists():
        hero_img = (
            f'<img class="cd-hero-img" src="/images/{escape(cfg["id"])}.jpg" alt="">'
        )
    else:
        hero_img = (
            f'<div class="cd-hero-img cd-hero-fallback" '
            f'style="background:linear-gradient(135deg,{cfg["color_a"]},{cfg["color_b"]})"></div>'
        )

    # PB + reference cards
    pb_card = (
        f'<div class="cd-time cd-time-you">'
        f'<div class="cd-time-lbl">{escape(you_label)}</div>'
        f'<div class="cd-time-val mono">{_fmt_ms(pb_ms)}</div>'
        f'<div class="cd-time-ctx">latest combo PB</div>'
        '</div>'
    )
    ref_cards = ""
    for ref in refs:
        rms = _parse_time_ms(ref["time"])
        gap = (pb_ms - rms) if (pb_ms and rms) else None
        gap_cls = _gap_class(gap)
        ref_cards += (
            f'<div class="cd-time cd-time-ref">'
            f'<div class="cd-time-lbl">{escape(ref["label"])}</div>'
            f'<div class="cd-time-val mono">{_fmt_ms(rms)}</div>'
            f'<div class="cd-time-gap {gap_cls} mono">{_fmt_gap(gap)}</div>'
            '</div>'
        )

    # Specs strip
    specs_html = "".join(
        f'<div class="cd-spec"><span class="cd-spec-lbl">{escape(k)}</span>'
        f'<span class="cd-spec-val">{escape(v)}</span></div>'
        for k, v in (cfg.get("specs") or {}).items()
    )

    # Setup philosophy panel
    setup_html = ""
    if setup:
        rows = []
        for k, label in (("trim", "Trim"), ("priority", "Priority"), ("key", "Key choices")):
            if setup.get(k):
                rows.append(
                    f'<div class="cd-setup-row"><span class="cd-setup-lbl">{label}</span>'
                    f'<span class="cd-setup-val">{escape(setup[k])}</span></div>'
                )
        if rows:
            setup_html = (
                '<section class="cd-section">'
                '<h2 class="cd-h2">Setup philosophy</h2>'
                '<div class="cd-setup">' + "".join(rows) + '</div>'
                '</section>'
            )

    # Storytelling: history-driven progression
    story_html = _render_challenge_story(cfg, pb_ms, refs)

    # Per-skin history → enriched perspectives + head-to-head tally
    duel_history = _load_duel_history(cfg) if cfg.get("launchers") else {}
    drivers_html = _render_drivers_section(cfg) if cfg.get("launchers") else ""
    cars_html = _render_cars_section(cfg) if cfg.get("launchers") else ""
    choose_html = _render_choose_section(cfg, duel_history) if cfg.get("launchers") else ""
    h2h_html = _render_h2h(cfg, duel_history) if cfg.get("launchers") else ""
    track_dna_html = _render_track_dna(cfg) if cfg.get("launchers") else ""

    # Hero launch CTA(s) — dual team CTAs if launchers list exists, else single LAUNCH
    launchers = cfg.get("launchers")
    if launchers:
        hero_launch_html = '<div class="cd-launchers">'
        for lc in launchers:
            label = lc.get("label", "LAUNCH")
            logo = lc.get("logo", "")
            cmd = lc.get("cmd", "")
            hero_launch_html += (
                f'<button class="btn-launch-team cd-btn-launch-team {escape(logo)}" '
                f'onclick="launchConfig({escape(json.dumps(cfg["id"]))},'
                f'{escape(json.dumps(cfg["title"] + " · " + label))},'
                f'{escape(json.dumps(cmd))})">'
                f'{_team_logo_svg(logo)}'
                f'<span>{escape(label)}</span>'
                f'<span class="team-go">GO ▶</span>'
                f'</button>'
            )
        hero_launch_html += '</div>'
    else:
        hero_launch_html = (
            f'<button class="btn-launch cd-btn-launch" '
            f'onclick="launchConfig({escape(json.dumps(cfg["id"]))},{escape(json.dumps(cfg["title"]))})">'
            'LAUNCH</button>'
        )

    # Videos
    videos_html = ""
    for v in cfg.get("videos") or []:
        url = v["url"] if isinstance(v, dict) else v
        label = v.get("label", "WATCH") if isinstance(v, dict) else "WATCH"
        videos_html += (
            f'<a class="btn-watch" target="_blank" rel="noopener noreferrer" '
            f'href="{escape(url)}">{escape(label)} ▶</a>'
        )

    is_duel = bool(cfg.get("launchers"))
    if is_duel:
        # FULL-BLEED hero for duels: photo covers the whole top, atmospheric copy
        # + a track-outline thumbnail on the right. No CTAs, no goal pill — those
        # live in the perspective panels below.
        hero_blurb = cfg.get("hero_blurb") or cfg.get("subtitle", "")
        track_id = cfg.get("ac_track_id", "")
        track_layout = cfg.get("ac_track_layout", "")
        track_thumb = ""
        if track_id and track_layout:
            track_thumb = (
                f'<aside class="cd-hero-track">'
                f'<div class="cd-hero-track-lbl">CIRCUIT</div>'
                f'<div class="cd-hero-track-name">{escape(cfg.get("track_label", track_id.upper()))}</div>'
                f'<div class="cd-hero-track-outline">'
                f'<img src="/track-asset?track={escape(track_id)}'
                f'&amp;layout={escape(track_layout)}&amp;file=outline.png" '
                f'alt="Track outline" '
                f'onerror="this.style.display=\'none\'">'
                f'</div>'
                f'</aside>'
            )
        hero_html = (
            '<header class="cd-hero-v2">'
            f'<div class="cd-hero-bg">{hero_img}</div>'
            '<div class="cd-hero-overlay"></div>'
            '<a class="cd-back cd-back-floating" href="/">← All challenges</a>'
            '<div class="cd-hero-content">'
            '<div class="cd-hero-text">'
            f'<div class="cd-tag-chip">{escape(cfg["tag"])}</div>'
            f'<h1 class="cd-title-xl">{escape(cfg["title"])}</h1>'
            f'<p class="cd-blurb">{escape(hero_blurb)}</p>'
            '</div>'
            f'{track_thumb}'
            '</div>'
            '</header>'
        )
        # Track section now includes a photo carousel; setup section reads
        # the actual AC setup file (`1.ini`) and explains the values.
        track_section_html = _render_track_section(cfg)
        setup_section_html = _render_ac_setup_section(cfg)
        # New order: Drivers → Choose (with H2H inline) → Track (carousel) → Cars → Setup
        body_html = (
            f'{drivers_html}'
            f'{choose_html}'
            f'{track_section_html}'
            f'{cars_html}'
            f'{setup_section_html}'
        )
    else:
        # Existing layout (image + side-by-side text) for non-duel tiles
        hero_html = (
            '<header class="cd-hero">'
            '<div class="cd-hero-media">'
            f'{hero_img}'
            f'<span class="card-type-chip {type_cls}">{escape(type_label)}</span>'
            '</div>'
            '<div class="cd-hero-body">'
            f'<a class="cd-back" href="/">← All challenges</a>'
            f'<div class="cd-tag">{escape(cfg["tag"])}</div>'
            f'<h1 class="cd-title">{escape(cfg["title"])}</h1>'
            f'<p class="cd-sub">{escape(cfg["subtitle"])}</p>'
            f'<p class="cd-scenario">{escape(cfg["scenario"])}</p>'
            f'<div class="cd-goal"><span class="cd-goal-lbl">Goal</span>{escape(cfg["goal"])}</div>'
            '<div class="cd-actions">'
            f'{hero_launch_html}'
            f'{videos_html}'
            '</div>'
            '</div>'
            '</header>'
        )
        body_html = (
            '<section class="cd-section cd-times-section">'
            '<h2 class="cd-h2">Where you stand</h2>'
            f'<div class="cd-times">{pb_card}{ref_cards}</div>'
            '</section>'
            '<section class="cd-section">'
            '<h2 class="cd-h2">The combo</h2>'
            f'<div class="cd-specs">{specs_html}</div>'
            '</section>'
            f'{_render_weapon_section(cfg)}'
            f'{setup_html}'
            f'{story_html}'
        )

    return (
        f'{_common_head(title_full)}'
        f'{render_nav("challenges")}'
        f'{render_ticker()}'
        '<article class="cd-page">'
        f'{hero_html}'
        f'{body_html}'
        '</article>'
        '<div id="toast" class="toast"></div>'
        f'<script>{JS}</script>'
        '</body></html>'
    )


def _ac_car_meta(car_id):
    if not car_id:
        return None
    car_dir = CARS_DIR / car_id
    if not car_dir.exists():
        return None
    ui = _read_ui_json(car_dir / "ui" / "ui_car.json")
    return {
        "id": car_id,
        "name": (ui.get("name") or car_id).strip(),
        "brand": (ui.get("brand") or "").strip(),
        "class": (ui.get("class") or "").strip(),
        "year": ui.get("year"),
        "bhp": ((ui.get("specs") or {}).get("bhp") or "").strip(),
        "weight": ((ui.get("specs") or {}).get("weight") or "").strip(),
        "topspeed": ((ui.get("specs") or {}).get("topspeed") or "").strip(),
    }


def _ac_skin_meta(car_id, skin_id):
    """Read ui_skin.json — team/driver/number/country for the livery."""
    if not car_id or not skin_id:
        return None
    skin_dir = CARS_DIR / car_id / "skins" / skin_id
    if not skin_dir.exists():
        return None
    ui = _read_ui_json(skin_dir / "ui_skin.json")
    if not ui:
        return None
    return {
        "team":    (ui.get("team") or "").strip(),
        "driver":  (ui.get("drivername") or ui.get("driver") or "").strip(),
        "number":  str(ui.get("number") or "").strip(),
        "country": (ui.get("country") or "").strip(),
        "name":    (ui.get("name") or ui.get("skinname") or skin_id).strip(),
    }


def _ac_track_meta(track_id, layout=None):
    if not track_id:
        return None
    tdir = TRACKS_DIR / track_id
    if not tdir.exists():
        return None
    # Try the requested layout first, then default
    candidates = []
    if layout:
        candidates.append(tdir / "ui" / layout / "ui_track.json")
    candidates.append(tdir / "ui" / "ui_track.json")
    ui = {}
    for c in candidates:
        if c.exists():
            ui = _read_ui_json(c)
            if ui:
                break
    return {
        "id": track_id,
        "layout": layout,
        "name": (ui.get("name") or track_id).strip(),
        "country": (ui.get("country") or "").strip(),
        "city": (ui.get("city") or "").strip(),
        "length": (ui.get("length") or "").strip(),
        "pitboxes": ui.get("pitboxes"),
    }


def _car_preview_url(cfg, car_id_key="ac_car_id", skin_key="ac_car_skin"):
    """Resolve to the car preview URL, preferring a specific skin if set."""
    car_id = cfg.get(car_id_key)
    if not car_id or not (CARS_DIR / car_id).exists():
        return None
    skin = cfg.get(skin_key)
    if skin and (CARS_DIR / car_id / "skins" / skin / "preview.jpg").exists():
        return f"/content/cars/{car_id}/preview?skin={quote(skin, safe='')}"
    return f"/content/cars/{car_id}/preview"


def _track_preview_url(cfg):
    track_id = cfg.get("ac_track_id")
    if not track_id or not (TRACKS_DIR / track_id).exists():
        return None
    layout = cfg.get("ac_track_layout")
    if layout and (TRACKS_DIR / track_id / "ui" / layout / "preview.png").exists():
        return f"/content/tracks/{track_id}/preview?layout={layout}"
    return f"/content/tracks/{track_id}/preview"


def _render_machine_card(label, name, sub_text, img_url, meta_pairs, livery=None):
    img_html = (
        f'<img class="cd-machine-img" src="{img_url}" alt="" loading="lazy">'
        if img_url else
        '<div class="cd-machine-img cd-machine-fallback"></div>'
    )
    meta_html = "".join(
        f'<div class="cd-machine-meta-row"><span>{escape(k)}</span><strong>{escape(str(v))}</strong></div>'
        for k, v in meta_pairs if v
    )
    livery_html = ""
    if livery:
        team = livery.get("team")
        driver = livery.get("driver")
        number = livery.get("number")
        bits = []
        if number:
            bits.append(f'<span class="cd-livery-num">#{escape(number)}</span>')
        if team:
            bits.append(f'<span>{escape(team)}</span>')
        if driver:
            bits.append(f'<span class="cd-livery-driver">{escape(driver)}</span>')
        if bits:
            livery_html = (
                '<div class="cd-livery">'
                '<span class="cd-livery-lbl">Livery</span>'
                + " · ".join(bits) +
                '</div>'
            )
    return (
        '<div class="cd-machine">'
        f'<div class="cd-machine-img-wrap">{img_html}'
        f'<span class="cd-machine-tag">{escape(label)}</span></div>'
        '<div class="cd-machine-body">'
        f'<div class="cd-machine-chassis-lbl">Chassis</div>'
        f'<h3 class="cd-machine-name">{escape(name)}</h3>'
        f'{("<p class=\"cd-machine-sub\">" + escape(sub_text) + "</p>") if sub_text else ""}'
        f'{livery_html}'
        f'<div class="cd-machine-meta">{meta_html}</div>'
        '</div>'
        '</div>'
    )


def _render_weapon_section(cfg):
    """Show the actual car(s) + track from the user's AC install."""
    cards = []
    car = _ac_car_meta(cfg.get("ac_car_id"))
    rival = _ac_car_meta(cfg.get("ac_rival_car_id"))
    track = _ac_track_meta(cfg.get("ac_track_id"), cfg.get("ac_track_layout"))

    if car:
        sub = " · ".join(filter(None, [car["brand"], car["class"].upper() or ""]))
        livery = _ac_skin_meta(cfg.get("ac_car_id"), cfg.get("ac_car_skin"))
        cards.append(_render_machine_card(
            "Your car",
            car["name"],
            sub,
            _car_preview_url(cfg),
            [
                ("BHP",       car["bhp"]),
                ("WEIGHT",    car["weight"]),
                ("TOP SPEED", car["topspeed"]),
                ("YEAR",      car["year"]),
            ],
            livery=livery,
        ))
    if rival:
        sub = " · ".join(filter(None, [rival["brand"], rival["class"].upper() or ""]))
        rival_livery = _ac_skin_meta(cfg.get("ac_rival_car_id"), cfg.get("ac_rival_car_skin"))
        cards.append(_render_machine_card(
            "Rival car",
            rival["name"],
            sub,
            _car_preview_url(cfg, "ac_rival_car_id", "ac_rival_car_skin"),
            [
                ("BHP",    rival["bhp"]),
                ("WEIGHT", rival["weight"]),
                ("YEAR",   rival["year"]),
            ],
            livery=rival_livery,
        ))
    if track:
        sub = " · ".join(filter(None, [track["country"], track["city"]]))
        cards.append(_render_machine_card(
            "Circuit",
            track["name"],
            sub,
            _track_preview_url(cfg),
            [
                ("LENGTH",   track["length"]),
                ("PITBOXES", track["pitboxes"]),
                ("LAYOUT",   track["layout"] or ""),
            ],
        ))
    if not cards:
        return ""
    return (
        '<section class="cd-section">'
        '<h2 class="cd-h2">Your weapon · Your circuit</h2>'
        '<div class="cd-machines">'
        + "".join(cards) +
        '</div>'
        '</section>'
    )


def _render_challenge_story(cfg, pb_ms, refs):
    kind, history = _load_history(cfg)
    primary_ref_ms = _parse_time_ms(refs[0]["time"]) if refs else None

    if kind == "hotlap" and history:
        # Sort by ts ascending
        sessions = sorted(history, key=lambda d: d.get("ts", ""))
        rows = []
        prev_pb = None
        for i, s in enumerate(sessions):
            ms = s.get("pb_ms")
            delta_prev = (ms - prev_pb) if (ms and prev_pb) else None
            delta_ref = (ms - primary_ref_ms) if (ms and primary_ref_ms) else None
            note = escape(s.get("note", "") or "")
            ts = escape((s.get("ts") or "")[:10])
            rows.append(
                '<tr>'
                f'<td class="cd-tbl-num mono">#{i + 1}</td>'
                f'<td class="cd-tbl-date mono">{ts}</td>'
                f'<td class="cd-tbl-pb mono">{_fmt_ms(ms)}</td>'
                f'<td class="cd-tbl-delta mono {_gap_class(delta_prev)}">'
                f'{_fmt_gap(delta_prev) if delta_prev is not None else "—"}</td>'
                f'<td class="cd-tbl-gap mono {_gap_class(delta_ref)}">'
                f'{_fmt_gap(delta_ref) if delta_ref is not None else "—"}</td>'
                f'<td class="cd-tbl-laps mono">{s.get("lap_count", "—")}</td>'
                f'<td class="cd-tbl-note">{note}</td>'
                '</tr>'
            )
            if ms:
                prev_pb = ms
        ref_lbl = escape(refs[0]["label"]) if refs else "ref"
        return (
            '<section class="cd-section cd-story">'
            '<h2 class="cd-h2">Session ladder · the climb</h2>'
            '<table class="cd-tbl"><thead><tr>'
            '<th>#</th><th>Date</th><th>PB</th><th>Δ vs prev</th>'
            f'<th>Δ vs {ref_lbl}</th><th>Laps</th><th>Note</th>'
            '</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            '</section>'
        )

    if kind == "race" and history:
        sessions = sorted(history, key=lambda d: d.get("ts", ""))
        rows = []
        for i, r in enumerate(sessions):
            grid = r.get("grid")
            finish = r.get("finish")
            delta = (grid - finish) if (grid and finish) else None
            arrow = ""
            if delta is not None:
                arrow = (f'<span class="is-under">▲{delta}</span>'
                         if delta > 0 else
                         f'<span class="is-far">▼{abs(delta)}</span>'
                         if delta < 0 else
                         '<span>—</span>')
            ts = escape((r.get("ts") or "")[:10])
            note = escape(r.get("note", "") or "")
            rows.append(
                '<tr>'
                f'<td class="cd-tbl-num mono">#{i + 1}</td>'
                f'<td class="cd-tbl-date mono">{ts}</td>'
                f'<td class="cd-tbl-pb mono">P{finish or "?"}</td>'
                f'<td class="cd-tbl-grid mono">P{grid or "?"}</td>'
                f'<td class="cd-tbl-delta mono">{arrow}</td>'
                f'<td class="cd-tbl-gap mono">{_fmt_ms(r.get("fastest_lap_ms"))}</td>'
                f'<td class="cd-tbl-note">{note}</td>'
                '</tr>'
            )
        return (
            '<section class="cd-section cd-story">'
            '<h2 class="cd-h2">Race log</h2>'
            '<table class="cd-tbl"><thead><tr>'
            '<th>#</th><th>Date</th><th>Finish</th><th>Grid</th>'
            '<th>Δ pos</th><th>Fastest lap</th><th>Note</th>'
            '</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
            '</section>'
        )

    # Empty state — when no history exists yet
    msg = "No telemetry logged for this challenge yet."
    if cfg.get("type") == "DUEL":
        msg = "1v1 sessions aren't auto-logged yet — drive one and the videos above show the reference."
    elif cfg.get("series") == "NLS":
        msg = "Session telemetry lives in telemetry_archive/ — drive a Mercer/Nord session and the launcher will pick it up next time."
    return (
        '<section class="cd-section cd-story cd-story-empty">'
        '<h2 class="cd-h2">Logbook</h2>'
        f'<p class="cd-empty-msg">{escape(msg)}</p>'
        '<p class="cd-empty-hint">When you click LAUNCH, AC opens with the preset already applied. '
        'Run a session, archive it, and this page will fill in.</p>'
        '</section>'
    )


# -- Launch helpers ----------------------------------------------------------

def _to_windows_path(p: Path) -> str:
    """Map /mnt/c/... → C:\\..."""
    s = str(p)
    if s.startswith("/mnt/"):
        drive = s[5]
        rest = s[6:].replace("/", "\\")
        return f"{drive.upper()}:\\{rest}"
    return s.replace("/", "\\")


def launch_cmd(cfg_id: str, cmd_name: str = ""):
    cfg = next((c for c in CONFIGS if c["id"] == cfg_id), None)
    if not cfg:
        return False, f"unknown config {cfg_id}"
    # Allowed launchers: the primary `launcher` field + every entry in `launchers`.
    # Anything else is rejected (no path traversal via ?cmd=).
    allowed = {cfg.get("launcher", "")}
    for lc in cfg.get("launchers") or []:
        if isinstance(lc, dict) and lc.get("cmd"):
            allowed.add(lc["cmd"])
    allowed.discard("")
    if cmd_name:
        if cmd_name not in allowed:
            return False, f"cmd not allowed for {cfg_id}: {cmd_name}"
        chosen = cmd_name
    else:
        chosen = cfg.get("launcher", "")
        if not chosen:
            return False, f"no launcher configured for {cfg_id}"
    cmd_path = AC_DOC / chosen
    if not cmd_path.exists():
        return False, f"launcher not found: {cmd_path.name}"
    win_path = _to_windows_path(cmd_path)
    win_dir = _to_windows_path(AC_DOC)
    # PowerShell Start-Process is the WSL→Windows path that works for Pablo.
    ps_cmd = (
        f"Start-Process -FilePath '{win_path}' "
        f"-WorkingDirectory '{win_dir}'"
    )
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True, f"launched {cfg['title']}"
    except Exception as e:
        return False, str(e)


def open_dash(rel: str):
    target = (AC_DOC / rel).resolve()
    try:
        ac_doc_resolved = AC_DOC.resolve()
        target.relative_to(ac_doc_resolved)
    except ValueError:
        return False, "path outside AC_DOC"
    if not target.exists():
        return False, f"not found: {rel}"
    win_path = _to_windows_path(target)
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command",
             f"Start-Process '{win_path}'"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True, "opened"
    except Exception as e:
        return False, str(e)


# -- HTTP server -------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[launch-bay] %s - %s\n" % (
            self.address_string(), fmt % args))

    def _cors(self):
        """Allow any origin so a Vercel-hosted page can POST /launch here."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _html(self, body):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, mime: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            self._html(render_html())
            return
        if u.path in ("/favicon.svg", "/favicon.ico"):
            target = LAUNCHER_DIR / "favicon.svg"
            if target.exists():
                self._file(target, "image/svg+xml")
                return
            self.send_error(404)
            return
        if u.path == "/cars":
            self._html(render_cars_page())
            return
        if u.path == "/tracks":
            self._html(render_tracks_page())
            return
        if u.path.startswith("/challenge/"):
            cid = u.path[len("/challenge/"):].strip("/")
            cfg = next((c for c in CONFIGS if c["id"] == cid), None)
            if cfg:
                self._html(render_challenge_page(cfg))
                return
            self.send_error(404, "unknown challenge")
            return
        if u.path == "/moza":
            self._html(render_moza_page())
            return
        if u.path.startswith("/moza/thumb/"):
            from urllib.parse import unquote
            rest = u.path[len("/moza/thumb/"):]
            if "/" not in rest:
                self.send_error(400, "bad thumb path")
                return
            dash_name, _, fname = rest.rpartition("/")
            _serve_moza_thumb(self, unquote(dash_name), fname)
            return
        if u.path.startswith("/moza/download/"):
            from urllib.parse import unquote
            rest = u.path[len("/moza/download/"):]
            if not rest.endswith(".zip"):
                self.send_error(400, "bad download path")
                return
            dash_name = unquote(rest[:-len(".zip")])
            _serve_moza_download(self, dash_name)
            return
        if u.path == "/ext-asset":
            q = parse_qs(u.query)
            fn = (q.get("file") or [""])[0]
            if not fn or any(c in fn for c in ("/", "\\", "..")):
                self.send_error(400, "bad ext-asset path")
                return
            ac_root = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa")
            target = ac_root / "extension" / "backgrounds" / fn
            if target.exists() and target.is_file():
                ext = target.suffix.lower()
                ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext.lstrip("."), "application/octet-stream")
                self._file(target, ctype)
                return
            self.send_error(404, "ext asset not found")
            return
        if u.path == "/track-asset":
            q = parse_qs(u.query)
            t = (q.get("track") or [""])[0]
            la = (q.get("layout") or [""])[0]
            fn = (q.get("file") or [""])[0]
            if not t or not fn or any(c in t + la + fn for c in ("/", "\\", "..")):
                self.send_error(400, "bad track-asset path")
                return
            ac_root = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa")
            target = ac_root / "content" / "tracks" / t / "ui" / la / fn
            if target.exists() and target.is_file():
                ext = target.suffix.lower()
                ctype = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext.lstrip("."), "application/octet-stream")
                self._file(target, ctype)
                return
            self.send_error(404, "track asset not found")
            return
        if u.path.startswith("/images/"):
            name = u.path[len("/images/"):]
            if "/" in name or "\\" in name or ".." in name:
                self.send_error(400, "bad image path")
                return
            target = IMAGES_DIR / name
            if not target.exists():
                self.send_error(404)
                return
            ext = target.suffix.lower()
            mime = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif",
            }.get(ext, "application/octet-stream")
            self._file(target, mime)
            return
        if u.path.startswith("/content/"):
            parts = u.path.strip("/").split("/")
            # /content/<kind>/<id>/preview  (?skin=…  ?layout=…)
            if len(parts) == 4 and parts[3] == "preview":
                q = parse_qs(u.query)
                _serve_content_preview(
                    self, parts[1], parts[2],
                    skin=(q.get("skin") or [None])[0],
                    layout=(q.get("layout") or [None])[0],
                )
                return
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/launch":
            cfg_id = (q.get("id") or [""])[0]
            cmd_name = (q.get("cmd") or [""])[0]
            ok, msg = launch_cmd(cfg_id, cmd_name)
            self._json(200, {"ok": ok, "msg": msg})
            return
        if u.path == "/open":
            rel = (q.get("path") or [""])[0]
            ok, msg = open_dash(rel)
            self._json(200, {"ok": ok, "msg": msg})
            return
        self.send_error(404)


def _port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _watch_and_reload():
    """Daemon thread: re-exec the process if launcher_dashboard.py changes."""
    src = Path(__file__)
    try:
        mt = src.stat().st_mtime
    except Exception:
        return
    while True:
        time.sleep(1)
        try:
            new_mt = src.stat().st_mtime
        except Exception:
            continue
        if new_mt > mt + 0.2:
            print("[launch-bay] code changed — restarting server...")
            sys.stdout.flush()
            os.execv(sys.executable, [sys.executable] + sys.argv)


def main():
    _load_disk_cache()
    port = PORT
    while not _port_free(port) and port < PORT + 20:
        port += 1
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}/"
    print("=" * 60)
    print("  Pablo Suzarte's Sim Racing Challenges")
    print(f"  Serving:    {url}")
    print(f"  Challenges: {len(CONFIGS)}")
    print(f"  AC_DOC:     {AC_DOC}")
    print("  Auto-reload: ON (server restarts on code change)")
    print("  Ctrl+C to stop.")
    print("=" * 60)
    threading.Thread(target=_watch_and_reload, daemon=True).start()
    if "--no-browser" not in sys.argv:
        def _open():
            try:
                subprocess.Popen(
                    ["powershell.exe", "-NoProfile", "-Command",
                     f"Start-Process '{url}'"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                print(f"[launch-bay] could not auto-open browser: {e}")
                print(f"[launch-bay] open manually: {url}")
        threading.Timer(0.6, _open).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[launch-bay] shutting down")
        server.server_close()


if __name__ == "__main__":
    main()
