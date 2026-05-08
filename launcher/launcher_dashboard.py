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
from datetime import date
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs


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
        "id":    "F1",
        "label": "FORMULA 1 · 2026",
        "deck":  "F1 hybrid laps and races on the 2026 calendar — chasing real qualifying and pole times.",
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
            "TRACK": "Nordschleife · 24h 2024 layout",
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
            "TRACK": "Nordschleife · 24h 2024 layout",
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
        "tag": "1v1 RACE-CRAFT DRILL",
        "title": "VERSTAPPEN VS HAASE",
        "subtitle": "Max #33 vs Haase #16 · 1 lap",
        "scenario": (
            "The 2026 NLS season's defining rivalry distilled to a single lap. You "
            "(Mercedes-AMG GT3, the Verstappen #33) versus Christopher Haase (Audi R8 "
            "GT3 Evo II, Scherer Sport PHX #16). No traffic, no strategy, no excuses "
            "— just race-craft under pressure on the Nord."
        ),
        "goal": "Beat Haase to the line. Make every overtake count.",
        "setup": {
            "trim":     "Sprint · one shot",
            "priority": "Straight-line speed, minimum fuel weight",
            "key":      "Wing 6 (low drag) · 14L fuel (one Nord lap) · TC 2 · Audi runs default",
        },
        "benchmarks": {
            "refs": [
                {"label": "Note", "time": "1-lap drill on 24h layout"},
            ],
        },
        "specs": {
            "CAR":   "MERCEDES-AMG GT3 · #3 VERSTAPPEN",
            "TRACK": "Nordschleife · 24h 2024 layout",
            "GRID":  "2 cars · head-to-head",
            "LAPS":  "1 lap · AI calibrated to Haase",
        },
        "color_a": "#3a0608",
        "color_b": "#7a0c0e",
        "track_label": "NORDSCHLEIFE",
        "launcher": "launch_verstappen_1v1.cmd",
        "dashboard_rel": None,
        "ac_car_id": "rss_gtm_mercer_v8",
        "ac_car_skin": "M17_Verstappen_Test_33",
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
    },
    {
        "id": "canada_2026",
        "type": "RACE",
        "series": "F1",
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
        "series": "F1",
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
        "series": "F1",
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
        "series": "F1",
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
async function launchConfig(id, title){
  const t = document.getElementById('toast');
  t.textContent = 'LAUNCHING ' + title + ' …';
  t.classList.remove('err');
  t.classList.add('show');
  try {
    const r = await fetch('/launch?id=' + encodeURIComponent(id), {method:'POST'});
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


def render_hero():
    series_count = len({c.get("series") for c in CONFIGS if c.get("series")})
    return (
        '<header class="hero">'
        '<div class="hero-l">'
        '<div class="hero-kicker"><span class="pos">#33</span>PABLO SUZARTE · MULTI-SERIES SIM RACING</div>'
        '<h1 class="hero-title">SIM RACING<br><span class="accent">CHALLENGES</span></h1>'
        '<div class="hero-sub">Pick a series · pick a scenario · go racing</div>'
        '</div>'
        '<div class="hero-r">'
        '<div class="hero-count-lbl">CHALLENGES BUILT</div>'
        f'<div class="hero-count">{len(CONFIGS):02d}</div>'
        '<div class="hero-count-meta">'
        f'<strong>{sum(1 for c in CONFIGS if c["type"] == "RACE")}</strong> RACES · '
        f'<strong>{sum(1 for c in CONFIGS if c["type"] == "HOTLAP")}</strong> HOTLAPS · '
        f'<strong>{sum(1 for c in CONFIGS if c["type"] == "DUEL")}</strong> 1v1 · '
        f'<strong>{series_count}</strong> SERIES'
        '</div>'
        '</div>'
        '</header>'
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


def _render_times_block(cfg):
    bm = cfg.get("benchmarks")
    if not bm:
        return ""
    your_ms = _resolve_your_ms(bm)
    your_str = _fmt_ms(your_ms) if your_ms else None
    refs = bm.get("refs") or []

    rows_html = []
    # Your row first — bold, larger
    you_lbl = bm.get("you_label", "Your PB")
    rows_html.append(
        '<div class="time-row is-you">'
        f'<span class="time-lbl">{escape(you_lbl)}</span>'
        f'<span class="time-val">{escape(your_str) if your_str else "—"}</span>'
        '<span class="time-diff"></span>'
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


def render_card(cfg):
    type_cls = cfg["type"].lower()
    type_label = cfg.get("type_label", cfg["type"])
    # CAR is rendered as a prominent line above the spec strip, so the strip
    # only needs TRACK/GRID/LAPS.
    pill_keys = [k for k in ("TRACK", "GRID", "LAPS") if k in cfg["specs"]]
    pills = "".join(
        f'<div class="spec-pill" title="{escape(k)}: {escape(cfg["specs"][k])}">'
        f'<span class="lbl">{escape(k)}</span>{escape(cfg["specs"][k])}'
        f'</div>'
        for k in pill_keys
    )
    secondary = ""
    # DASH button now points at the unified internal /challenge/<id> view
    # rather than each preset's separate external HTML dashboard.
    secondary += (
        f'<a class="btn-dash" title="Open the unified challenge dashboard" '
        f'href="/challenge/{escape(cfg["id"])}">DASH ↗</a>'
    )
    for v in cfg.get("videos") or []:
        if isinstance(v, str):
            label, url = "WATCH", v
        else:
            label, url = v.get("label", "WATCH"), v["url"]
        secondary += (
            f'<a class="btn-watch" target="_blank" rel="noopener noreferrer" '
            f'href="{escape(url)}" title="Watch context video">'
            f'{escape(label)} ▶</a>'
        )
    secondary_block = (
        f'<div class="card-secondary">{secondary}</div>' if secondary else ""
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

    # Title attribute on the article so Pablo can hover for the long scenario
    return (
        '<article class="card">'
        '<div class="card-img">'
        f'<span class="card-type-chip {type_cls}">{escape(type_label)}</span>'
        f'{country_chip}'
        f'{_img_block(cfg)}'
        '</div>'
        '<div class="card-body">'
        f'<h3 class="card-title">{escape(cfg["title"])}</h3>'
        f'<div class="card-car">{escape(cfg["specs"].get("CAR", ""))}</div>'
        f'<div class="card-sub">{escape(cfg["subtitle"])}</div>'
        + _render_times_block(cfg) +
        f'<div class="spec-strip">{pills}</div>'
        '<div class="card-actions">'
        f'{secondary_block}'
        f'<button class="btn-launch" onclick="launchConfig({escape(json.dumps(cfg["id"]))},'
        f'{escape(json.dumps(cfg["title"]))})">LAUNCH</button>'
        '</div>'
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


def render_html():
    return (
        f'{_common_head("Pablo Suzarte\'s Sim Racing Challenges")}'
        f'{render_nav("challenges")}'
        f'{render_ticker()}'
        f'{render_hero()}'
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
    """Resolve the player's PB for this challenge: explicit > history > personalbest.ini."""
    bm = cfg.get("benchmarks") or {}
    if cfg.get("current_pb_ms"):
        return int(cfg["current_pb_ms"])
    history = bm.get("you_history")
    if history:
        try:
            data = json.loads((AC_DOC / history).read_text(encoding="utf-8"))
            mss = [d.get("pb_ms") for d in data if d.get("pb_ms")]
            if mss:
                return min(mss)
        except Exception:
            pass
    sect = bm.get("you_section")
    if sect:
        return _read_personalbest().get(sect)
    return None


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

    # Hero image (first available image / single image / fallback)
    images = cfg.get("images") or []
    if images:
        hero_img = (
            f'<img class="cd-hero-img" src="/images/{escape(images[0])}" alt="">'
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

    # Videos
    videos_html = ""
    for v in cfg.get("videos") or []:
        url = v["url"] if isinstance(v, dict) else v
        label = v.get("label", "WATCH") if isinstance(v, dict) else "WATCH"
        videos_html += (
            f'<a class="btn-watch" target="_blank" rel="noopener noreferrer" '
            f'href="{escape(url)}">{escape(label)} ▶</a>'
        )

    return (
        f'{_common_head(title_full)}'
        f'{render_nav("challenges")}'
        f'{render_ticker()}'
        '<article class="cd-page">'
        # ---- Hero
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
        f'<button class="btn-launch cd-btn-launch" '
        f'onclick="launchConfig({json.dumps(cfg["id"])},{json.dumps(cfg["title"])})">'
        'LAUNCH</button>'
        f'{videos_html}'
        '</div>'
        '</div>'
        '</header>'
        # ---- Times row (PB + references with gaps)
        '<section class="cd-section cd-times-section">'
        '<h2 class="cd-h2">Where you stand</h2>'
        f'<div class="cd-times">{pb_card}{ref_cards}</div>'
        '</section>'
        # ---- Specs
        '<section class="cd-section">'
        '<h2 class="cd-h2">The combo</h2>'
        f'<div class="cd-specs">{specs_html}</div>'
        '</section>'
        # ---- Weapon (car + track from AC install)
        f'{_render_weapon_section(cfg)}'
        # ---- Setup
        f'{setup_html}'
        # ---- Story (progression / log / empty state)
        f'{story_html}'
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
        return f"/content/cars/{car_id}/preview?skin={skin}"
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


def launch_cmd(cfg_id: str):
    cfg = next((c for c in CONFIGS if c["id"] == cfg_id), None)
    if not cfg:
        return False, f"unknown config {cfg_id}"
    cmd_path = AC_DOC / cfg["launcher"]
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
            ok, msg = launch_cmd(cfg_id)
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
