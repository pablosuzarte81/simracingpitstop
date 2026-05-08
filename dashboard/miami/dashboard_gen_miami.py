#!/usr/bin/env python3
"""Miami GP 2026 hotlap dashboard generator.
Pulls Pablo's latest session from out/laps.ini + race_out.json, decodes the
track AI line for sector-colored racing line, lays it over the track outline,
writes a self-contained HTML dashboard.

Run:    wsl python3 dashboard/miami/dashboard_gen_miami.py
Output: Documents/Assetto Corsa/dashboard/miami/dashboard.html
"""
from __future__ import annotations
import struct, configparser, json, base64
from pathlib import Path
from datetime import datetime

# ----- Paths -----
HOME = Path("/mnt/c/Users/pablo/Documents/Assetto Corsa")
TRACK = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa/content/tracks/miami_f1")
LAYOUT = TRACK / "layout_f1_2025"
OUT_DIR = HOME / "dashboard/miami"

# ----- Constants (the chase) -----
DRIVER_NAME = "PABLO SUZARTE"
CAR_NAME = "FORMULA HYBRID ALPINE 2025"
TRACK_NAME = "MIAMI INTERNATIONAL AUTODROME"
SKIN_NAME = "RB21 #1 VERSTAPPEN"
F1_REF_MS = 87869       # 1:27.869 — real F1 2026 Miami Sprint Qualy fastest
F1_REF_LABEL = "F1 SPRINT QUALY 2026"
MOD_BEST_MS = 87796     # 1:27.796 — RSS Hybrid 2023 documented Miami hotlap
MOD_BEST_LABEL = "AC MOD CEILING (RSS HYBRID '23)"

# ----- Miami corner library (real-track reference, drives the turn-guide cards) -----
# Each turn: type, sector, brief generic advice, gear range, brake intensity (0-3)
MIAMI_CORNERS = {
    1:  {"sector": 1, "type": "Heavy brake — slow R",       "gear": "8→3", "brake": 3,
         "advice": "Big stop from main-straight DRS. Trail-brake to apex, exit kerb-left to set up T2. Don't carry too much on entry — kills T2."},
    2:  {"sector": 1, "type": "Quick L kink",                "gear": "4",   "brake": 0,
         "advice": "Almost flat, settle the car for T3. Don't lift mid-corner."},
    3:  {"sector": 1, "type": "Long R, increasing radius",   "gear": "5→4", "brake": 1,
         "advice": "Brake into apex, stay patient — corner opens up. Late throttle is fine."},
    4:  {"sector": 1, "type": "Tight L hairpin",             "gear": "3",   "brake": 3,
         "advice": "Slowest of the opening complex. Late apex, get the car rotated before throttle."},
    5:  {"sector": 1, "type": "Quick R esses",               "gear": "4",   "brake": 1,
         "advice": "Flow with weight transfer, ride the inside curb. Don't over-rotate."},
    6:  {"sector": 1, "type": "L esses",                     "gear": "5",   "brake": 0,
         "advice": "Almost flat, momentum is everything here."},
    7:  {"sector": 1, "type": "Mid-speed R",                 "gear": "5→4", "brake": 1,
         "advice": "Set up for T8, the line is later than it feels."},
    8:  {"sector": 1, "type": "Mid-speed L (S1 exit)",       "gear": "5",   "brake": 1,
         "advice": "Late apex T8 is the SECTOR 1 EXIT — bad here costs the long T9 straight."},
    9:  {"sector": 2, "type": "Fast R sweep",                "gear": "7→6", "brake": 1,
         "advice": "Heavy downforce zone. Trust the car, brush the brake. Set up T10."},
    10: {"sector": 2, "type": "Fast R, decreasing",          "gear": "6→5", "brake": 1,
         "advice": "Brake later than it looks. Apex on the inside curb, exit wide for T11 entry."},
    11: {"sector": 2, "type": "Hairpin chicane entry — slowest corner", "gear": "5→2", "brake": 3,
         "advice": "Slowest corner of the lap. LATE-APEX, brake into the apex not before. Get rotated, then full throttle. This is where S2 lives or dies."},
    12: {"sector": 2, "type": "Tight R after T11",           "gear": "2→3", "brake": 2,
         "advice": "Fluid transition out of T11 — don't unsettle the car with steering input."},
    13: {"sector": 2, "type": "Chicane L",                   "gear": "3",   "brake": 1,
         "advice": "Ride the inside curb. Use track on exit."},
    14: {"sector": 2, "type": "Chicane R",                   "gear": "3→4", "brake": 0,
         "advice": "Continue chicane flow. Stay tight, set up T15."},
    15: {"sector": 2, "type": "Quick L (target: flat)",      "gear": "4",   "brake": 0,
         "advice": "Should be FLAT-OUT once you trust it. Eyes on T16 entry."},
    16: {"sector": 2, "type": "L exit-onto-straight (S2 exit)", "gear": "4→6", "brake": 1,
         "advice": "S2 EXIT — earliest possible throttle pickup, this corner sets up the entire 1.3km flat-out section to T17."},
    17: {"sector": 3, "type": "Fast R, building",            "gear": "8",   "brake": 0,
         "advice": "Flat-out R, ride the inside line. Last full-grip moment before braking."},
    18: {"sector": 3, "type": "Heavy brake — slow L",        "gear": "8→3", "brake": 3,
         "advice": "Hardest braking of the lap from top speed. Trail-brake hard, slow apex, perfect exit critical."},
    19: {"sector": 3, "type": "Final R onto main straight",  "gear": "3→4", "brake": 2,
         "advice": "EVERYTHING for the lap time hinges on T19 exit — clean apex, full throttle, every km/h here = 7s on the next lap's main straight."},
}

# ----- Helpers -----
def ms_to_str(ms: int, with_sign=False) -> str:
    sign = ""
    if with_sign:
        sign = "+" if ms >= 0 else "-"
        ms = abs(ms)
    m, rem = divmod(int(ms), 60000)
    s = rem / 1000
    if m > 0:
        return f"{sign}{m}:{s:06.3f}"
    return f"{sign}{s:.3f}"

def sec_to_str(ms: int) -> str:
    return f"{ms/1000:.3f}"

# ----- AI line decode -----
def decode_ai(path: Path):
    """AC fast_lane.ai format: header(8) + 8 zeros + waypoints(20 bytes each: x,y,z,?,?)."""
    data = path.read_bytes()
    version, count = struct.unpack_from('<II', data, 0)
    pts = []
    for i in range(count):
        off = 16 + i * 20
        x, y, z, *_ = struct.unpack_from('<fffff', data, off)
        pts.append((x, y, z))
    return pts

# ----- Map transform -----
def load_map():
    cfg = configparser.ConfigParser()
    cfg.read(LAYOUT / "data/map.ini")
    p = cfg['PARAMETERS']
    return {
        'W': int(p['WIDTH']), 'H': int(p['HEIGHT']),
        'X_OFF': float(p['X_OFFSET']), 'Z_OFF': float(p['Z_OFFSET']),
        'SCALE': float(p['SCALE_FACTOR']), 'MARGIN': int(p['MARGIN'])
    }

def w2s(x, z, m):
    return ((x + m['X_OFF']) * m['SCALE'] + m['MARGIN'],
            (z + m['Z_OFF']) * m['SCALE'] + m['MARGIN'])

# ----- Sections (turn labels) -----
def load_turns():
    cfg = configparser.ConfigParser()
    cfg.read(LAYOUT / "data/sections.ini")
    out = []
    for s in cfg.sections():
        out.append({'in': float(cfg[s]['IN']),
                    'out': float(cfg[s]['OUT']),
                    'text': cfg[s]['TEXT']})
    return out

# ----- DRS zones -----
def load_drs():
    cfg = configparser.ConfigParser()
    cfg.read(LAYOUT / "data/drs_zones.ini")
    zones = []
    for s in cfg.sections():
        zones.append({'start': float(cfg[s]['START']),
                      'end':   float(cfg[s]['END'])})
    return zones

# ----- Lap data -----
def load_laps():
    cfg = configparser.ConfigParser()
    cfg.read(HOME / "out/laps.ini")
    laps = []
    for sec in cfg.sections():
        if sec.startswith('LAP_'):
            laps.append({
                'time': int(cfg[sec]['TIME']),
                's1':   int(cfg[sec]['SPLIT_0']),
                's2':   int(cfg[sec]['SPLIT_1']),
                's3':   int(cfg[sec]['SPLIT_2']),
            })
    return laps

def load_race_out():
    p = HOME / "out/race_out.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

def load_alltime_pb():
    """Read personalbest.ini for the RSS Hybrid Alpine Miami combo."""
    p = HOME / "personalbest.ini"
    if not p.exists():
        return None
    try:
        text = p.read_text()
    except Exception:
        return None
    import re
    m = re.search(r'\[RSS_FORMULA_HYBRID_2025_ALPINE@MIAMI_F1[^\]]*\]\nDATE=(\d+)\nTIME=(\d+)', text)
    if m:
        return {'date_ms': int(m.group(1)), 'time_ms': int(m.group(2))}
    return None

# ----- Build SVG -----
def build_track_svg(ai_pts, m, turns, drs, sector_split_pcts):
    # Compute cumulative arc length to assign each point a lap-distance pct
    total = 0.0
    cum = [0.0]
    for i in range(1, len(ai_pts)):
        x0, _, z0 = ai_pts[i-1]
        x1, _, z1 = ai_pts[i]
        d = ((x1-x0)**2 + (z1-z0)**2) ** 0.5
        total += d
        cum.append(total)
    pcts = [c/total for c in cum]

    # screen coords
    sxs = []
    for x, _, z in ai_pts:
        sxs.append(w2s(x, z, m))

    def sector_of_pct(p):
        if p < sector_split_pcts[0]: return 1
        if p < sector_split_pcts[1]: return 2
        return 3

    # split into 3 sectors
    seg = {1: [], 2: [], 3: []}
    last = None
    for (sx, sy), pct in zip(sxs, pcts):
        sec = sector_of_pct(pct)
        # ensure no jumps between segments
        if last is not None and last != sec:
            seg[last].append(None)  # path break marker
        seg[sec].append((sx, sy))
        last = sec

    def to_path(pts):
        if not pts: return ""
        out = []
        moving = True
        for p in pts:
            if p is None:
                moving = True
                continue
            if moving:
                out.append(f"M{p[0]:.1f},{p[1]:.1f}")
                moving = False
            else:
                out.append(f"L{p[0]:.1f},{p[1]:.1f}")
        return " ".join(out)

    # Find screen pos for each turn (midpoint of section)
    turn_marks = []
    for t in turns:
        target = (t['in'] + t['out']) / 2
        # binary-style nearest pct
        idx = min(range(len(pcts)), key=lambda i: abs(pcts[i] - target))
        x, y = sxs[idx]
        # extract turn number from text "T1", "T19" etc
        try:
            tnum = int(''.join(c for c in t['text'] if c.isdigit()))
        except ValueError:
            tnum = -1
        turn_marks.append({'name': t['text'], 'num': tnum, 'x': x, 'y': y, 'sector': sector_of_pct(target)})

    # Sector boundary screen positions (for circular markers)
    sector_marks = []
    for i, p in enumerate(sector_split_pcts):
        idx = min(range(len(pcts)), key=lambda i_: abs(pcts[i_] - p))
        x, y = sxs[idx]
        sector_marks.append((f"S{i+1}/S{i+2}", x, y))

    # DRS zone segments
    drs_paths = []
    for d in drs:
        dpts = []
        for i, pct in enumerate(pcts):
            in_zone = (d['start'] <= d['end'] and d['start'] <= pct <= d['end']) or \
                      (d['start'] >  d['end'] and (pct >= d['start'] or pct <= d['end']))
            if in_zone:
                dpts.append(sxs[i])
        drs_paths.append(to_path(dpts))

    return {
        'W': m['W'], 'H': m['H'],
        'p1': to_path(seg[1]), 'p2': to_path(seg[2]), 'p3': to_path(seg[3]),
        'turns': turn_marks, 'sectors': sector_marks, 'drs': drs_paths,
    }

def b64_png(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode('ascii')

# ----- HTML -----
HTML_TPL = r"""<!doctype html><html><head><meta charset="utf-8">
<title>MIAMI HOTLAP — {driver}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800;900&family=Saira:wght@400;600;800&family=Saira+Condensed:wght@500;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --red: #D40E10; --black: #0a0a0a; --bg: #f3f1ec; --paper: #ffffff;
  --line: #0a0a0a; --grey: #999; --soft-grey: #d8d4cb;
  --purple: #6d3aa8; --green: #1f8a4c; --yellow: #d8a000; --orange: #d65a00;
  --s1: #d40e10; --s2: #1c2a8a; --s3: #1f8a4c;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background: var(--bg); color: var(--black); font-family: "Saira", sans-serif; -webkit-font-smoothing: antialiased; }}
.bg-checker {{ background-image: linear-gradient(45deg, transparent 49%, var(--black) 49% 51%, transparent 51%), linear-gradient(-45deg, transparent 49%, var(--black) 49% 51%, transparent 51%); background-size: 12px 12px; }}

/* TICKER STRIPE */
.ticker {{ background: var(--black); color: #fff; height: 38px; display:flex; align-items:center; padding: 0 24px; font-family: "Big Shoulders Display"; font-weight:800; letter-spacing:.08em; font-size: 13px; gap: 20px; border-bottom: 2px solid var(--red); }}
.ticker .red {{ color: var(--red); }}
.ticker .pad {{ flex: 1 }}
.ticker .checker {{ width: 80px; height: 100%; background: repeating-linear-gradient(90deg, var(--red) 0 12px, #000 12px 24px); }}

/* HERO PIT-BOARD */
.hero {{ display: grid; grid-template-columns: 1.6fr 1fr; border-bottom: 2px solid var(--black); background: var(--paper); }}
.hero-left {{ padding: 28px 36px 20px; border-right: 2px solid var(--black); position: relative; }}
.hero-left::before {{ content: "Pos"; position:absolute; top: 10px; left: 36px; font-family:"Saira Condensed"; font-weight: 700; font-size: 10px; letter-spacing: .2em; color: var(--grey); }}
.hero-pos {{ font-family: "Big Shoulders Display"; font-weight:900; font-size: 38px; color: var(--red); line-height: 1; }}
.hero-driver {{ font-family: "Big Shoulders Display"; font-weight:900; font-size: 88px; line-height:.95; letter-spacing: -.01em; margin: 6px 0 12px; text-transform: uppercase; }}
.hero-meta {{ font-family: "Saira Condensed"; font-weight:500; font-size: 12px; letter-spacing:.18em; color: var(--black); text-transform: uppercase; }}
.hero-meta b {{ color: var(--red); }}
.hero-time {{ display:flex; align-items: baseline; gap: 18px; margin-top: 18px; }}
.hero-time .label {{ font-family:"Saira Condensed"; font-weight:700; font-size: 11px; letter-spacing:.22em; color: var(--grey); border-left: 4px solid var(--red); padding-left: 10px; }}
.hero-time .value {{ font-family:"JetBrains Mono"; font-weight:700; font-size: 56px; line-height: 1; letter-spacing: -.02em; }}
.hero-right {{ padding: 22px 28px; display: flex; flex-direction: column; justify-content: space-between; background: var(--black); color: #fff; }}
.hero-right .gap-block .label {{ font-family:"Saira Condensed"; font-weight:700; font-size: 11px; letter-spacing:.22em; color: #aaa; }}
.hero-right .gap-block .ref {{ font-family: "Big Shoulders Display"; font-weight: 800; font-size: 16px; letter-spacing: .04em; }}
.hero-right .gap-block .num {{ font-family: "JetBrains Mono"; font-weight: 700; font-size: 46px; color: var(--red); line-height: 1.05; }}
.hero-right .gap-block .num.green {{ color: #5ac96a; }}
.hero-right .gap-block.small .num {{ font-size: 28px; color: #fff; }}

/* SECTION HEADERS */
.sec-head {{ background: var(--black); color: #fff; padding: 14px 36px; display: flex; align-items: center; gap: 18px; }}
.sec-head .num {{ background: var(--red); color: #fff; font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; padding: 4px 14px; }}
.sec-head .title {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 28px; letter-spacing: .04em; text-transform: uppercase; }}
.sec-head .sub {{ margin-left: auto; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .2em; color: #aaa; }}

/* TRACK MAP */
.map-wrap {{ padding: 24px 36px; background: var(--paper); border-bottom: 2px solid var(--black); }}
.map-svg {{ width: 100%; height: auto; display:block; background: #faf8f3; border: 2px solid var(--black); }}
.map-legend {{ display:flex; gap: 28px; padding: 16px 0 0; flex-wrap: wrap; font-family:"Saira Condensed"; font-weight: 600; font-size: 12px; letter-spacing: .14em; text-transform: uppercase; }}
.map-legend .swatch {{ display:inline-block; width: 22px; height: 4px; vertical-align: middle; margin-right: 8px; }}
.map-stats {{ display:grid; grid-template-columns: repeat(4, 1fr); gap: 0; margin-top: 16px; border-top: 2px solid var(--black); }}
.map-stats .stat {{ padding: 10px 14px; border-right: 1px solid var(--soft-grey); }}
.map-stats .stat:last-child {{ border-right: none; }}
.map-stats .label {{ font-family:"Saira Condensed"; font-weight:600; font-size: 10px; letter-spacing: .2em; color: var(--grey); }}
.map-stats .value {{ font-family:"Big Shoulders Display"; font-weight:800; font-size: 22px; line-height: 1; margin-top: 4px; }}

/* SECTOR TOWER */
.tower {{ padding: 24px 36px; background: var(--paper); border-bottom: 2px solid var(--black); }}
.tower table {{ width: 100%; border-collapse: collapse; font-family:"JetBrains Mono"; font-weight:500; font-size: 14px; }}
.tower th {{ background: var(--black); color: #fff; text-align: left; padding: 8px 12px; font-family:"Saira Condensed"; font-weight:700; letter-spacing: .14em; font-size: 11px; }}
.tower td {{ padding: 10px 12px; border-bottom: 1px solid var(--soft-grey); }}
.tower .cell {{ position: relative; }}
.tower .bar {{ height: 22px; display:flex; }}
.tower .bar > div {{ height: 100%; }}
.tower .b1 {{ background: var(--s1); }}
.tower .b2 {{ background: var(--s2); }}
.tower .b3 {{ background: var(--s3); }}
.tower .laptime {{ font-weight: 700; font-size: 16px; }}
.tower .pb-row {{ background: #fff7d8; }}
.tower .opt-row {{ background: #efeae0; font-style: italic; }}
.tag {{ display:inline-block; padding: 2px 8px; font-family:"Saira Condensed"; font-weight:700; font-size: 10px; letter-spacing: .14em; }}
.tag.purple {{ background: var(--purple); color: #fff; }}
.tag.green {{ background: var(--green); color: #fff; }}
.tag.yellow {{ background: var(--yellow); color: #000; }}
.tag.red {{ background: var(--red); color: #fff; }}

/* COACHING */
.coach {{ padding: 28px 36px; background: var(--paper); border-bottom: 2px solid var(--black); display:grid; grid-template-columns: 1fr 1fr; gap: 36px; }}
.coach h3 {{ font-family:"Big Shoulders Display"; font-weight: 900; font-size: 18px; letter-spacing:.06em; text-transform: uppercase; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid var(--red); }}
.coach p {{ font-family:"Saira"; font-weight: 400; font-size: 15px; line-height: 1.55; margin: 0 0 12px; }}
.coach p b {{ color: var(--red); }}

/* PIT-BOARD ORDERS */
.orders {{ padding: 24px 36px; background: var(--bg); border-bottom: 2px solid var(--black); }}
.orders .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.order {{ background: var(--paper); border: 2px solid var(--black); padding: 14px 18px; display:flex; gap: 14px; align-items: flex-start; }}
.order .num {{ background: var(--black); color: #fff; font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; width: 36px; height: 36px; display:flex; align-items: center; justify-content: center; flex-shrink: 0; }}
.order:nth-child(odd) .num {{ background: var(--red); }}
.order .body {{ font-family:"Saira"; font-weight: 400; font-size: 14px; line-height: 1.45; }}
.order .body b {{ font-family:"Saira Condensed"; font-weight: 700; letter-spacing: .04em; }}

/* TURN GUIDE */
.turn-guide-wrap {{ padding: 24px 36px; background: var(--paper); border-bottom: 2px solid var(--black); }}
.turn-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
.turn-card {{ border: 2px solid var(--black); background: #fff; transition: transform .12s ease, box-shadow .12s ease; cursor: pointer; }}
.turn-card .tc-head {{ display:flex; gap: 14px; padding: 10px 14px; color: #fff; align-items: flex-start; }}
.turn-card .tc-num {{ font-family:"Big Shoulders Display"; font-weight: 900; font-size: 36px; line-height: 1; }}
.turn-card .tc-type {{ font-family:"Saira Condensed"; font-weight:700; letter-spacing:.1em; font-size: 12px; text-transform: uppercase; }}
.turn-card .tc-tags {{ font-family:"Saira Condensed"; font-weight:500; font-size: 10px; letter-spacing:.18em; opacity:.9; margin-top: 4px; display:flex; gap: 12px; }}
.turn-card .tc-tags span {{ background: rgba(0,0,0,.25); padding: 1px 6px; }}
.turn-card .tc-body {{ padding: 12px 14px; font-family:"Saira"; font-weight:400; font-size: 13px; line-height: 1.45; }}
.turn-card.active {{ box-shadow: 0 0 0 3px var(--red); transform: translateY(-2px); }}

/* TURN-REF inline links */
.turn-ref {{ display: inline-block; padding: 1px 6px; border: 2px solid var(--black); background: #fff; font-family:"JetBrains Mono"; font-weight:700; font-size: .9em; line-height: 1; cursor: pointer; transition: all .1s ease; user-select: none; }}
.turn-ref:hover, .turn-ref.active {{ background: var(--red); color: #fff; border-color: var(--red); }}

/* SVG turn-mark interactivity */
.turn-mark {{ cursor: pointer; transition: opacity .15s ease; }}
.turn-mark.coached circle {{ animation: pulse-ring 2.4s ease-in-out infinite; }}
.turn-mark.active circle:first-child, .turn-mark:hover circle:first-child {{ stroke: var(--red) !important; stroke-width: 4 !important; r: 16 !important; }}
.turn-mark.active text, .turn-mark:hover text {{ font-weight: 900 !important; }}
@keyframes pulse-ring {{ 0%,100% {{ stroke-opacity: 1; }} 50% {{ stroke-opacity: 0.45; }} }}

/* FOOTER */
.foot {{ padding: 18px 36px; background: var(--black); color: #aaa; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; display:flex; gap: 24px; }}
.foot .red {{ color: var(--red); }}
.foot .pad {{ flex:1 }}
</style></head>
<body>

<!-- TICKER -->
<div class="ticker">
  <span>HOTLAP CHASE</span>
  <span class="red">●</span>
  <span>{track_name}</span>
  <span class="red">●</span>
  <span>F1 SPRINT QUALY 2026 — TARGET <span class="red">{f1_ref_str}</span></span>
  <span class="pad"></span>
  <span>SESSION {session_ts}</span>
  <div class="checker"></div>
</div>

<!-- HERO -->
<div class="hero">
  <div class="hero-left">
    <div class="hero-pos">P1 · YOUR PB</div>
    <div class="hero-driver">{driver}</div>
    <div class="hero-meta"><b>{car}</b> · {skin} · {track_name} · LAYOUT F1 2025</div>
    <div class="hero-time">
      <div class="label">PERSONAL BEST<br>{laps_count}</div>
      <div class="value">{pb_str}</div>
    </div>
  </div>
  <div class="hero-right">
    <div class="gap-block">
      <div class="label">GAP TO POLE</div>
      <div class="ref">{f1_ref_label}</div>
      <div class="num">+{gap_f1}</div>
    </div>
    <div class="gap-block small">
      <div class="label">{mod_best_label}</div>
      <div class="num">{mod_best_str} → +{gap_mod}</div>
    </div>
    <div class="gap-block small">
      <div class="label">THEORETICAL OPTIMUM (YOUR SECTORS)</div>
      <div class="num">{theo_str} → headroom −{theo_gain}</div>
    </div>
  </div>
</div>

<!-- TRACK MAP -->
<div class="sec-head">
  <span class="num">01</span>
  <span class="title">THE CIRCUIT</span>
  <span class="sub">5,410 M · 19 TURNS · 3 DRS ZONES</span>
</div>
<div class="map-wrap">
  <svg class="map-svg" viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="turn-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="3" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    <!-- background outline image (very faint, for context) -->
    <image href="data:image/png;base64,{outline_b64}" x="0" y="0" width="{svg_w}" height="{svg_h}" opacity="0.12"/>

    <!-- DRS zones (thick gold halo) -->
    {drs_svg}

    <!-- Racing line, sector colored -->
    <path d="{p1}" stroke="var(--s1)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="{p2}" stroke="var(--s2)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="{p3}" stroke="var(--s3)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>

    <!-- Sector boundary markers -->
    {sector_markers_svg}

    <!-- Turn labels -->
    {turn_labels_svg}

    <!-- Start/Finish line -->
    <g>
      <line x1="{sf_x1}" y1="{sf_y1}" x2="{sf_x2}" y2="{sf_y2}" stroke="#000" stroke-width="3"/>
      <rect x="{sf_lx}" y="{sf_ly}" width="60" height="18" fill="#000"/>
      <text x="{sf_tx}" y="{sf_ty}" font-family="Big Shoulders Display" font-weight="900" fill="#fff" font-size="14" letter-spacing="2">START</text>
    </g>
  </svg>
  <div class="map-legend">
    <span><span class="swatch" style="background:var(--s1)"></span>SECTOR 1 — T1–T8 OPENING COMPLEX</span>
    <span><span class="swatch" style="background:var(--s2)"></span>SECTOR 2 — T9–T16 INFIELD + CHICANE</span>
    <span><span class="swatch" style="background:var(--s3)"></span>SECTOR 3 — T17–T19 + MAIN STRAIGHT</span>
    <span><span class="swatch" style="background:#d8a000"></span>DRS ZONE</span>
  </div>
  <div class="map-stats">
    <div class="stat"><div class="label">LENGTH</div><div class="value">5.410 KM</div></div>
    <div class="stat"><div class="label">TURNS</div><div class="value">19</div></div>
    <div class="stat"><div class="label">LONGEST FLAT-OUT</div><div class="value">~1.3 KM (T17→T1)</div></div>
    <div class="stat"><div class="label">DRS ZONES</div><div class="value">3</div></div>
  </div>
</div>

<!-- SECTOR TOWER -->
<div class="sec-head">
  <span class="num">02</span>
  <span class="title">SECTOR TOWER</span>
  <span class="sub">PER LAP · F1 TIMING COLOURS</span>
</div>
<div class="tower">
  <table>
    <thead>
      <tr><th>LAP</th><th>S1</th><th>S2</th><th>S3</th><th>LAP TIME</th><th>BAR</th></tr>
    </thead>
    <tbody>
      {laps_html}
      <tr class="opt-row">
        <td>OPT</td>
        <td>{opt_s1}</td><td>{opt_s2}</td><td>{opt_s3}</td>
        <td class="laptime">{theo_str}</td>
        <td><span style="font-family:Saira Condensed; font-size:11px; letter-spacing:.14em; color:var(--grey)">SUM OF BEST SECTORS</span></td>
      </tr>
    </tbody>
  </table>
</div>

<!-- COACHING -->
<div class="sec-head">
  <span class="num">03</span>
  <span class="title">DRIVER NOTE</span>
  <span class="sub">RACE ENGINEER READ</span>
</div>
<div class="coach">
  <div>
    <h3>SESSION STORY</h3>
    {story_html}
  </div>
  <div>
    <h3>WHERE THE TIME LIVES</h3>
    {strategy_html}
  </div>
</div>

<!-- ORDERS -->
<div class="sec-head">
  <span class="num">04</span>
  <span class="title">PIT-BOARD ORDERS</span>
  <span class="sub">NEXT STINT · HOVER ANY <span style="background:#fff;color:#000;padding:1px 6px;font-family:JetBrains Mono">T#</span> TO LIGHT IT ON THE MAP</span>
</div>
<div class="orders">
  <div class="grid">
    {orders_html}
  </div>
</div>

<!-- TURN-BY-TURN GUIDE -->
<div class="sec-head">
  <span class="num">05</span>
  <span class="title">TURN-BY-TURN GUIDE</span>
  <span class="sub">RED-RINGED TURNS ON THE MAP · CARDS ARE LIVE-LINKED</span>
</div>
<div class="turn-guide-wrap">
  <div class="turn-grid">
  {turn_cards_html}
  </div>
</div>

<!-- FOOTER -->
<div class="foot">
  <span>MIAMI HOTLAP DASHBOARD</span>
  <span class="red">●</span>
  <span>BUILT {build_ts}</span>
  <span class="pad"></span>
  <span>NORTH-STAR: F1 SPRINT QUALY 2026 · <span class="red">{f1_ref_str}</span></span>
</div>

<script>
(function() {{
  const setActive = (n, on) => {{
    document.querySelectorAll('[data-turn="' + n + '"]').forEach(el => {{
      el.classList.toggle('active', on);
    }});
    const card = document.getElementById('card-' + n);
    if (card) card.classList.toggle('active', on);
    const turn = document.getElementById('turn-' + n);
    if (turn) turn.classList.toggle('active', on);
  }};
  const wire = (sel) => {{
    document.querySelectorAll(sel).forEach(el => {{
      const n = el.getAttribute('data-turn');
      if (!n) return;
      el.addEventListener('mouseenter', () => setActive(n, true));
      el.addEventListener('mouseleave', () => setActive(n, false));
      el.addEventListener('click', () => {{
        const card = document.getElementById('card-' + n);
        if (card) card.scrollIntoView({{behavior: 'smooth', block: 'center'}});
        // briefly pulse
        setActive(n, true);
        setTimeout(() => setActive(n, false), 1400);
      }});
    }});
  }};
  wire('.turn-ref');
  wire('.turn-mark');
  wire('.turn-card');
}})();
</script>

</body></html>
"""

# ----- Build payload -----
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    laps = load_laps()
    if not laps:
        print("No laps in out/laps.ini — drive a session first")
        return
    session_pb_ms = min(l['time'] for l in laps)
    session_best_s1 = min(l['s1'] for l in laps)
    session_best_s2 = min(l['s2'] for l in laps)
    session_best_s3 = min(l['s3'] for l in laps)
    session_theo = session_best_s1 + session_best_s2 + session_best_s3

    # All-time PB takes precedence for hero; falls back to session if missing
    at = load_alltime_pb()
    pb_ms = at['time_ms'] if at and at['time_ms'] < session_pb_ms else session_pb_ms
    pb_is_alltime = (at is not None and at['time_ms'] <= session_pb_ms)

    # For sector tower / coaching, use session data
    best_s1, best_s2, best_s3 = session_best_s1, session_best_s2, session_best_s3
    theo = session_theo
    theo_gain = session_pb_ms - theo

    gap_f1 = pb_ms - F1_REF_MS
    gap_mod = pb_ms - MOD_BEST_MS

    # Estimate sector-split lap-distance % from time proportion of best lap
    pct1 = best_s1 / session_pb_ms
    pct2 = (best_s1 + best_s2) / session_pb_ms

    m = load_map()
    ai = decode_ai(LAYOUT / "ai/fast_lane.ai")
    turns = load_turns()
    drs = load_drs()
    svg = build_track_svg(ai, m, turns, drs, [pct1, pct2])

    # Find start/finish line approx (lap 0% — pick first AI point)
    sf_x = svg['turns'][0]['x'] if svg['turns'] else m['MARGIN'] + 100
    sf_y = svg['turns'][0]['y'] if svg['turns'] else m['MARGIN'] + 100

    # DRS as halo paths
    drs_svg = "\n    ".join(
        f'<path d="{p}" stroke="#d8a000" stroke-width="14" fill="none" opacity="0.55" stroke-linecap="round"/>'
        for p in svg['drs'] if p
    )

    # Sector boundary markers
    sector_markers_svg = "\n    ".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#000" stroke="#fff" stroke-width="2"/>'
        f'<text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" font-family="Big Shoulders Display" font-weight="900" font-size="11" fill="#fff">{i+1}|{i+2}</text>'
        for i, (label, x, y) in enumerate(svg['sectors'])
    )

    # Lap rows
    max_time = max(l['time'] for l in laps)
    lap_rows = []
    for i, l in enumerate(laps):
        is_pb = (l['time'] == pb_ms)
        # tag colors
        def tag(val, best, others):
            if val == best:
                return 'purple', 'P'  # session best
            elif val == min([best] + others):  # not relevant for single lap; keep simple
                return 'green', 'PB'
            elif val - best < 700:
                return 'yellow', '+'+sec_to_str(val-best)
            else:
                return 'red', '+'+sec_to_str(val-best)
        s1_class, s1_lab = tag(l['s1'], best_s1, [x['s1'] for j,x in enumerate(laps) if j!=i])
        s2_class, s2_lab = tag(l['s2'], best_s2, [x['s2'] for j,x in enumerate(laps) if j!=i])
        s3_class, s3_lab = tag(l['s3'], best_s3, [x['s3'] for j,x in enumerate(laps) if j!=i])
        # bar widths proportional to sectors
        w_total = 100
        w1 = l['s1'] / l['time'] * w_total
        w2 = l['s2'] / l['time'] * w_total
        w3 = l['s3'] / l['time'] * w_total
        scale_w = l['time'] / max_time * 100
        lap_rows.append(f"""
      <tr{' class="pb-row"' if is_pb else ''}>
        <td><b>L{i+1}</b>{' <span class="tag purple">PB</span>' if is_pb else ''}</td>
        <td>{sec_to_str(l['s1'])} <span class="tag {s1_class}">{s1_lab}</span></td>
        <td>{sec_to_str(l['s2'])} <span class="tag {s2_class}">{s2_lab}</span></td>
        <td>{sec_to_str(l['s3'])} <span class="tag {s3_class}">{s3_lab}</span></td>
        <td class="laptime">{ms_to_str(l['time'])}</td>
        <td><div class="bar" style="width:{scale_w:.1f}%"><div class="b1" style="width:{w1:.1f}%"></div><div class="b2" style="width:{w2:.1f}%"></div><div class="b3" style="width:{w3:.1f}%"></div></div></td>
      </tr>""")
    laps_html = "\n".join(lap_rows)

    # Coaching auto-prose
    n = len(laps)
    progression = laps[-1]['time'] - laps[0]['time']
    sector_gains = {
        'S1': laps[0]['s1'] - laps[-1]['s1'],
        'S2': laps[0]['s2'] - laps[-1]['s2'],
        'S3': laps[0]['s3'] - laps[-1]['s3'],
    }
    biggest_gain_sec = max(sector_gains, key=lambda k: sector_gains[k])
    smallest_gain_sec = min(sector_gains, key=lambda k: sector_gains[k])

    session_vs_alltime = session_pb_ms - (at['time_ms'] if at else session_pb_ms)
    alltime_clause = ""
    if at and session_pb_ms > at['time_ms']:
        alltime_clause = (f" Session best <b>{ms_to_str(session_pb_ms)}</b> is "
                          f"<b>+{ms_to_str(session_vs_alltime)}</b> off your all-time PB "
                          f"<b>{ms_to_str(at['time_ms'])}</b> — likely the compound switch (C5/softs vs C6/super-softs costs ~1 sec).")

    if progression < 0:
        story = (f"<p>{n} laps this session, all clean. From <b>{ms_to_str(laps[0]['time'])}</b> to "
                 f"<b>{ms_to_str(laps[-1]['time'])}</b> — that's <b>{ms_to_str(abs(progression))} faster</b> "
                 f"in {n-1} hot laps.{alltime_clause}</p>"
                 f"<p>Theoretical optimum (your best sectors stitched): <b>{ms_to_str(theo)}</b> — "
                 f"headroom inside this session: <b>{ms_to_str(theo_gain)}</b>.</p>")
    else:
        story = (f"<p>{n} laps this session. Session best <b>{ms_to_str(session_pb_ms)}</b>. "
                 f"Theoretical optimum <b>{ms_to_str(theo)}</b> — headroom "
                 f"<b>{ms_to_str(theo_gain)}</b>.{alltime_clause}</p>")

    strategy = (f"<p>Money sector next stint: <b>{smallest_gain_sec}</b>. It improved only "
                f"<b>{ms_to_str(sector_gains[smallest_gain_sec])}</b> across the session while "
                f"<b>{biggest_gain_sec}</b> took <b>{ms_to_str(sector_gains[biggest_gain_sec])}</b>. "
                f"<b>{smallest_gain_sec}</b> is where you stop improving first — that's where the next 2 seconds live.</p>"
                f"<p>Cuts: <b>0 across all laps</b>. You're not even on the kerbs yet. Free time "
                f"available by using more track on exits (T11, T16, T17). And — <b>stay on C6 "
                f"(super-soft)</b> for hotlap chasing. Harder compounds cost 1–2 sec/lap by design "
                f"(qualifying-tyre vs race-tyre delta). Switch only when practising stint deg.</p>")

    # Pick smallest-improvement-sector → corresponding "money" turns
    sector_to_focus_turns = {
        'S1': [1, 4, 8],          # T1 entry, T4 hairpin, T8 exit-to-S1-end
        'S2': [11, 13, 15, 16],   # the chicane complex
        'S3': [17, 18, 19],       # main-straight setup
    }
    money_turns = sector_to_focus_turns.get(smallest_gain_sec, [11, 16])
    target_sector_best = {'S1': best_s1, 'S2': best_s2, 'S3': best_s3}[smallest_gain_sec]
    target_str = sec_to_str(max(target_sector_best - 300, 0))

    # Helper to wrap T# refs in interactive spans
    import re as _re
    def linkify_turns(text: str) -> str:
        return _re.sub(r'\bT(\d+)\b', r'<span class="turn-ref" data-turn="\1">T\1</span>', text)

    orders_raw = [
        ("Run a <b>6-lap stint</b>: 1 outlap + 4 hot + 1 cooldown. Don't chase one perfect lap — chain sectors.", []),
        (f"<b>{smallest_gain_sec} focus.</b> Money sector. Aim ≤ <b>{target_str}</b> in {smallest_gain_sec} next session — push the red-ringed turns below.", money_turns),
        ("<b>Tyres = C6 (super-soft).</b> Hotlap only — don't switch down to softs/mediums unless practising stint deg.", []),
        ("<b>Use the kerbs.</b> 0 cuts so far — free time at T11, T16, T17 exits. Push 1 wheel over the white line on apex.", [11, 16, 17]),
        (f"<b>Lap target next stint:</b> <span style=\"color:var(--red);font-weight:800\">{ms_to_str(session_pb_ms - 1000)}</span>.", []),
        ("<b>If a sector regresses</b> by &gt;0.3 s, back off two laps, reset, then push again. Don't grind through degraded grip.", []),
    ]

    # Build coached_turns set (union of all turns referenced in orders + strategy)
    coached_turns = set()
    for _, ts in orders_raw:
        coached_turns.update(ts)
    # also pick up any T# in story/strategy text
    for txt in [story, strategy]:
        for m_ in _re.finditer(r'\bT(\d+)\b', txt):
            coached_turns.add(int(m_.group(1)))

    # Linkify story & strategy AFTER scanning
    story = linkify_turns(story)
    strategy = linkify_turns(strategy)

    orders_html = "\n    ".join(
        f'<div class="order"><div class="num">{i+1}</div><div class="body">{linkify_turns(text)}</div></div>'
        for i, (text, _ts) in enumerate(orders_raw)
    )

    # Turn labels (with id and coached class for highlighting)
    turn_labels_svg_parts = []
    for tm in svg['turns']:
        is_coached = tm['num'] in coached_turns
        ring_color = "#D40E10" if is_coached else "#000"
        ring_w = "3" if is_coached else "2"
        bg = "#fff"
        text_color = "#000"
        radius = "12" if is_coached else "9"
        glow_filter = ' filter="url(#turn-glow)"' if is_coached else ''
        turn_labels_svg_parts.append(
            f'<g class="turn-mark{" coached" if is_coached else ""}" id="turn-{tm["num"]}" data-turn="{tm["num"]}">'
            f'<circle cx="{tm["x"]:.1f}" cy="{tm["y"]:.1f}" r="{radius}" fill="{bg}" stroke="{ring_color}" stroke-width="{ring_w}"{glow_filter}/>'
            f'<text x="{tm["x"]:.1f}" y="{tm["y"]+3:.1f}" text-anchor="middle" font-family="JetBrains Mono" font-weight="700" font-size="9" fill="{text_color}">{tm["name"].replace("T","")}</text>'
            f'</g>'
        )
    turn_labels_svg = "\n    ".join(turn_labels_svg_parts)

    # Turn guide cards (one card per coached turn)
    coached_sorted = sorted(coached_turns)
    turn_cards_html_parts = []
    for tnum in coached_sorted:
        if tnum not in MIAMI_CORNERS: continue
        c = MIAMI_CORNERS[tnum]
        sec_color = ['s1','s2','s3'][c['sector']-1]
        brake_dots = '●' * c['brake'] + '○' * (3 - c['brake'])
        turn_cards_html_parts.append(
            f'<div class="turn-card" id="card-{tnum}" data-turn="{tnum}">'
            f'  <div class="tc-head" style="background:var(--{sec_color})">'
            f'    <div class="tc-num">T{tnum}</div>'
            f'    <div class="tc-meta"><div class="tc-type">{c["type"]}</div>'
            f'    <div class="tc-tags"><span>S{c["sector"]}</span><span>GEAR {c["gear"]}</span><span>BRAKE {brake_dots}</span></div></div>'
            f'  </div>'
            f'  <div class="tc-body">{c["advice"]}</div>'
            f'</div>'
        )
    turn_cards_html = "\n  ".join(turn_cards_html_parts) if turn_cards_html_parts else '<p style="color:#999;font-family:Saira Condensed;letter-spacing:.14em">No turns flagged this session — drive a stint and return.</p>'

    outline_b64 = b64_png(LAYOUT.parent / "ui/layout_f1_2025/outline.png")

    # Get session timestamp
    ro = load_race_out()
    if ro:
        session_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    else:
        session_ts = "—"

    pb_subtitle = ("ALL-TIME PB · COMBO" if pb_is_alltime else f"{len(laps)} LAPS · ALL CLEAN")
    if pb_is_alltime and len(laps) > 0:
        pb_subtitle += f" · SESSION BEST {ms_to_str(session_pb_ms)}"
    html = HTML_TPL.format(
        driver=DRIVER_NAME, car=CAR_NAME, skin=SKIN_NAME, track_name=TRACK_NAME,
        f1_ref_str=ms_to_str(F1_REF_MS), f1_ref_label=F1_REF_LABEL,
        mod_best_str=ms_to_str(MOD_BEST_MS), mod_best_label=MOD_BEST_LABEL,
        pb_str=ms_to_str(pb_ms), laps_count=pb_subtitle,
        gap_f1=ms_to_str(gap_f1, with_sign=False).lstrip('+'),
        gap_mod=ms_to_str(gap_mod, with_sign=False).lstrip('+'),
        theo_str=ms_to_str(theo),
        theo_gain=ms_to_str(theo_gain) if theo_gain > 0 else "0.000 (already optimal in dataset)",
        opt_s1=sec_to_str(best_s1), opt_s2=sec_to_str(best_s2), opt_s3=sec_to_str(best_s3),
        outline_b64=outline_b64,
        svg_w=svg['W'], svg_h=svg['H'],
        p1=svg['p1'], p2=svg['p2'], p3=svg['p3'],
        drs_svg=drs_svg,
        sector_markers_svg=sector_markers_svg,
        turn_labels_svg=turn_labels_svg,
        sf_x1=sf_x-30, sf_y1=sf_y-15, sf_x2=sf_x+30, sf_y2=sf_y+15,
        sf_lx=sf_x-30, sf_ly=sf_y-30, sf_tx=sf_x-22, sf_ty=sf_y-17,
        laps_html=laps_html, story_html=story, strategy_html=strategy, orders_html=orders_html,
        turn_cards_html=turn_cards_html,
        session_ts=session_ts,
        build_ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    out_path = OUT_DIR / "dashboard.html"
    out_path.write_text(html, encoding='utf-8')
    print(f"Wrote {out_path}")
    print(f"PB: {ms_to_str(pb_ms)}  |  Gap to F1: +{ms_to_str(gap_f1)}  |  Theoretical: {ms_to_str(theo)}")

if __name__ == "__main__":
    main()
