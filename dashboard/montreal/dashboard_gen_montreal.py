#!/usr/bin/env python3
"""Canadian GP 2026 hotlap dashboard generator (Circuit Gilles Villeneuve, Montreal).
Mirrors the Miami dashboard pattern. North-star: 2025 Canadian GP qualy pole.

Run:    wsl python3 dashboard/montreal/dashboard_gen_montreal.py
Output: Documents/Assetto Corsa/dashboard/montreal/dashboard.html
"""
from __future__ import annotations
import struct, configparser, json, base64
from pathlib import Path
from datetime import datetime

# ----- Paths -----
HOME = Path("/mnt/c/Users/pablo/Documents/Assetto Corsa")
TRACK = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa/content/tracks/montreal")
LAYOUT = TRACK / "montreal_f1_2025"
OUT_DIR = HOME / "dashboard/montreal"
HISTORY_FILE = OUT_DIR / "hotlap_history.json"

# ----- Constants (the chase) -----
DRIVER_NAME = "PABLO SUZARTE"
CAR_NAME = "FORMULA HYBRID ALPINE 2025"
TRACK_NAME = "CIRCUIT GILLES VILLENEUVE"
SKIN_NAME = "RB21 #1 VERSTAPPEN"
F1_REF_MS = 70899       # 1:10.899 — 2025 Canadian GP pole (Russell, Mercedes)
                        #   Beat Verstappen by 0.160s on C5 mediums.
F1_REF_LABEL = "F1 POLE 2025 — RUSSELL"
F1_REF_DRIVER = "GEORGE RUSSELL · MERCEDES W16 · 1:10.899"

# ----- Montreal corner library -----
# Lap-distance percentages calibrated from sections.ini landmarks (Senna 7-10%,
# Epingle 60-65%, Casino Droit 68-86%, Wall of Champions 88-91%).
MONTREAL_CORNERS = {
    1:  {"sector": 1, "type": "Senna chicane R — heavy brake", "gear": "8→3", "brake": 3,
         "advice": "Big stop from DRS-assisted main straight. Trail-brake to apex, kerb on exit to set up T2."},
    2:  {"sector": 1, "type": "Senna chicane L exit",          "gear": "3→4", "brake": 1,
         "advice": "Get the car straight, throttle ON early — exit speed sets up the short run to T3."},
    3:  {"sector": 1, "type": "Long R, Île Notre-Dame entry",  "gear": "5→4", "brake": 2,
         "advice": "Brake at the boards, late apex, full throttle out toward T4."},
    4:  {"sector": 1, "type": "L kink",                        "gear": "5",   "brake": 0,
         "advice": "Almost flat, settle the car for T5. Don't lift mid-corner."},
    5:  {"sector": 1, "type": "R, short straight to esses",    "gear": "5",   "brake": 1,
         "advice": "Brush brake, trust the front end, set up the esses flow."},
    6:  {"sector": 1, "type": "L ess",                         "gear": "5",   "brake": 0,
         "advice": "Momentum corner — flow with weight transfer, ride the inside curb."},
    7:  {"sector": 1, "type": "R ess, S1 exit",                "gear": "5→4", "brake": 1,
         "advice": "Last S1 turn. Late apex, get straight, full throttle for the run to T8 chicane."},
    8:  {"sector": 2, "type": "Pont chicane L entry",          "gear": "5→3", "brake": 2,
         "advice": "Brake at the bridge marker. Tight L into chicane — kerb on apex, kerb on exit."},
    9:  {"sector": 2, "type": "Pont chicane R exit",           "gear": "3→4", "brake": 0,
         "advice": "Roll through. Exit straight onto the run to L'Epingle."},
    10: {"sector": 2, "type": "L'EPINGLE — slowest corner of the lap", "gear": "4→2", "brake": 3,
         "advice": "Hairpin. Heavy brake, second gear, get the car rotated, EARLIEST possible throttle. This is where S2 lives or dies — Casino straight is 1.1km long."},
    11: {"sector": 2, "type": "R sweep onto Casino straight",  "gear": "2→4", "brake": 0,
         "advice": "Build throttle progressively. Casino Droit is the longest flat-out at the track."},
    12: {"sector": 2, "type": "L kink mid-Casino",             "gear": "8",   "brake": 0,
         "advice": "Should be flat at full speed. Don't lift — every lift = car-length lost into T13."},
    13: {"sector": 3, "type": "Wall of Champions L — heavy brake", "gear": "8→3", "brake": 3,
         "advice": "Hardest brake of the lap from peak speed. Trail-brake, late apex L, ride the inside kerb. Wall on left exit — zero margin."},
    14: {"sector": 3, "type": "Wall of Champions R — onto pit straight", "gear": "3→5", "brake": 1,
         "advice": "Get it STRAIGHT before throttle. The wall on the left has eaten Schumacher, Hill, Villeneuve. Patience here = lap-time on the next lap."},
}

# Synthetic turn map (sections.ini only has 5 named landmarks; we need 14 turn markers).
# Lap-distance percentages aligned with the real-track sections.ini reference points.
def synth_turns():
    return [
        {'in': 0.070, 'out': 0.080, 'text': 'T1'},
        {'in': 0.085, 'out': 0.095, 'text': 'T2'},
        {'in': 0.130, 'out': 0.140, 'text': 'T3'},
        {'in': 0.175, 'out': 0.185, 'text': 'T4'},
        {'in': 0.215, 'out': 0.225, 'text': 'T5'},
        {'in': 0.295, 'out': 0.305, 'text': 'T6'},
        {'in': 0.330, 'out': 0.340, 'text': 'T7'},
        {'in': 0.395, 'out': 0.405, 'text': 'T8'},
        {'in': 0.440, 'out': 0.450, 'text': 'T9'},
        {'in': 0.610, 'out': 0.625, 'text': 'T10'},
        {'in': 0.660, 'out': 0.670, 'text': 'T11'},
        {'in': 0.690, 'out': 0.700, 'text': 'T12'},
        {'in': 0.890, 'out': 0.900, 'text': 'T13'},
        {'in': 0.915, 'out': 0.925, 'text': 'T14'},
    ]

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
        'W': int(float(p['WIDTH'])), 'H': int(float(p['HEIGHT'])),
        'X_OFF': float(p['X_OFFSET']), 'Z_OFF': float(p['Z_OFFSET']),
        'SCALE': float(p['SCALE_FACTOR']), 'MARGIN': int(p['MARGIN'])
    }

def w2s(x, z, m):
    return ((x + m['X_OFF']) * m['SCALE'] + m['MARGIN'],
            (z + m['Z_OFF']) * m['SCALE'] + m['MARGIN'])

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
    """Read laps from out/race_out.json (Hotlap mode doesn't always write laps.ini)."""
    p = HOME / "out/race_out.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except Exception:
        return []
    laps = []
    for sess in data.get('sessions', []):
        for lap in sess.get('laps', []):
            sectors = lap.get('sectors', [])
            if len(sectors) >= 3 and lap.get('time'):
                laps.append({
                    'time': int(lap['time']),
                    's1': int(sectors[0]),
                    's2': int(sectors[1]),
                    's3': int(sectors[2]),
                    'cuts': int(lap.get('cuts', 0)),
                    'tyre': lap.get('tyre', '?'),
                })
    return laps

def load_hotlap_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []

def save_hotlap_history(history):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

def update_hotlap_history(session_pb_ms, best_s1, best_s2, best_s3, lap_count):
    """Append this session's PB. Dedup on (pb_ms, lap_count). Returns progression context."""
    history = load_hotlap_history()
    new_entry = {
        "ts": datetime.now().isoformat(timespec='seconds'),
        "pb_ms": int(session_pb_ms),
        "s1_ms": int(best_s1),
        "s2_ms": int(best_s2),
        "s3_ms": int(best_s3),
        "lap_count": int(lap_count),
    }
    last = history[-1] if history else None
    is_dup = (last
              and last.get("pb_ms") == new_entry["pb_ms"]
              and last.get("lap_count") == new_entry["lap_count"])
    if is_dup:
        prev = history[-2] if len(history) >= 2 else None
        session_number = len(history)
    else:
        prev = last
        history.append(new_entry)
        save_hotlap_history(history)
        session_number = len(history)
    return {"current": new_entry, "previous": prev,
            "session_number": session_number, "history": history}

def load_alltime_pb():
    """Read personalbest.ini for the RSS Hybrid Alpine Montreal combo."""
    p = HOME / "personalbest.ini"
    if not p.exists():
        return None
    try:
        text = p.read_text()
    except Exception:
        return None
    import re
    m = re.search(r'\[RSS_FORMULA_HYBRID_2025_ALPINE@MONTREAL[^\]]*\]\nDATE=(\d+)\nTIME=(\d+)', text)
    if m:
        return {'date_ms': int(m.group(1)), 'time_ms': int(m.group(2))}
    return None

# ----- Build SVG -----
def build_track_svg(ai_pts, m, turns, drs, sector_split_pcts):
    total = 0.0
    cum = [0.0]
    for i in range(1, len(ai_pts)):
        x0, _, z0 = ai_pts[i-1]
        x1, _, z1 = ai_pts[i]
        d = ((x1-x0)**2 + (z1-z0)**2) ** 0.5
        total += d
        cum.append(total)
    pcts = [c/total for c in cum]

    sxs = []
    for x, _, z in ai_pts:
        sxs.append(w2s(x, z, m))

    def sector_of_pct(p):
        if p < sector_split_pcts[0]: return 1
        if p < sector_split_pcts[1]: return 2
        return 3

    seg = {1: [], 2: [], 3: []}
    last = None
    for (sx, sy), pct in zip(sxs, pcts):
        sec = sector_of_pct(pct)
        if last is not None and last != sec:
            seg[last].append(None)
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

    turn_marks = []
    for t in turns:
        target = (t['in'] + t['out']) / 2
        idx = min(range(len(pcts)), key=lambda i: abs(pcts[i] - target))
        x, y = sxs[idx]
        try:
            tnum = int(''.join(c for c in t['text'] if c.isdigit()))
        except ValueError:
            tnum = -1
        turn_marks.append({'name': t['text'], 'num': tnum, 'x': x, 'y': y, 'sector': sector_of_pct(target)})

    sector_marks = []
    for i, p in enumerate(sector_split_pcts):
        idx = min(range(len(pcts)), key=lambda i_: abs(pcts[i_] - p))
        x, y = sxs[idx]
        sector_marks.append((f"S{i+1}/S{i+2}", x, y))

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
<title>MONTREAL HOTLAP — {driver}</title>
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

.ticker {{ background: var(--black); color: #fff; height: 38px; display:flex; align-items:center; padding: 0 24px; font-family: "Big Shoulders Display"; font-weight:800; letter-spacing:.08em; font-size: 13px; gap: 20px; border-bottom: 2px solid var(--red); }}
.ticker .red {{ color: var(--red); }}
.ticker .pad {{ flex: 1 }}
.ticker .checker {{ width: 80px; height: 100%; background: repeating-linear-gradient(90deg, var(--red) 0 12px, #000 12px 24px); }}

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
.hero-tagline {{ margin-top: 18px; padding-top: 14px; border-top: 2px solid var(--black); font-family:"Saira"; font-weight: 400; font-size: 16px; line-height: 1.45; max-width: 640px; }}
.hero-tagline b {{ color: var(--red); font-family:"JetBrains Mono"; font-weight: 700; }}
.hero-right {{ padding: 22px 28px; display: flex; flex-direction: column; justify-content: space-between; background: var(--black); color: #fff; }}
.hero-right .gap-block .label {{ font-family:"Saira Condensed"; font-weight:700; font-size: 11px; letter-spacing:.22em; color: #aaa; }}
.hero-right .gap-block .ref {{ font-family: "Big Shoulders Display"; font-weight: 800; font-size: 16px; letter-spacing: .04em; }}
.hero-right .gap-block .num {{ font-family: "JetBrains Mono"; font-weight: 700; font-size: 46px; color: var(--red); line-height: 1.05; }}
.hero-right .gap-block .num.green {{ color: #5ac96a; }}
.hero-right .gap-block .num.red {{ color: #ff4848; }}
.hero-right .gap-block.small .num {{ font-size: 28px; color: #fff; }}
.hero-right .gap-block.progression .num {{ font-size: 34px; }}
.hero-right .gap-block.progression .num.green {{ color: #5ac96a; }}
.hero-right .gap-block.progression .num.red {{ color: #ff4848; }}
.session-tag {{ background: var(--red); color:#fff; padding: 2px 8px; font-family:"Big Shoulders Display"; font-weight:900; font-size: 12px; letter-spacing: .12em; margin-left: 10px; }}

.sec-head {{ background: var(--black); color: #fff; padding: 14px 36px; display: flex; align-items: center; gap: 18px; }}
.sec-head .num {{ background: var(--red); color: #fff; font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; padding: 4px 14px; }}
.sec-head .title {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 28px; letter-spacing: .04em; text-transform: uppercase; }}
.sec-head .sub {{ margin-left: auto; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .2em; color: #aaa; }}

.map-wrap {{ padding: 24px 36px; background: var(--paper); border-bottom: 2px solid var(--black); display: grid; grid-template-columns: 220px 1fr; gap: 28px; align-items: start; }}
.map-svg {{ width: 100%; max-height: 420px; height: auto; display:block; background: #faf8f3; border: 2px solid var(--black); }}
.map-side {{ display: flex; flex-direction: column; gap: 16px; }}
.map-legend {{ display:flex; flex-direction: column; gap: 8px; font-family:"Saira Condensed"; font-weight: 600; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }}
.map-legend .row {{ display:flex; align-items: center; gap: 10px; }}
.map-legend .swatch {{ display:inline-block; width: 22px; height: 4px; flex-shrink: 0; }}
.map-stats {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 0; border-top: 2px solid var(--black); border-bottom: 2px solid var(--black); }}
.map-stats .stat {{ padding: 10px 14px; border-right: 1px solid var(--soft-grey); border-bottom: 1px solid var(--soft-grey); }}
.map-stats .stat:nth-child(2n) {{ border-right: none; }}
.map-stats .stat:nth-child(n+3) {{ border-bottom: none; }}
.map-stats .label {{ font-family:"Saira Condensed"; font-weight:600; font-size: 10px; letter-spacing: .18em; color: var(--grey); }}
.map-stats .value {{ font-family:"Big Shoulders Display"; font-weight:800; font-size: 18px; line-height: 1; margin-top: 4px; }}
.key-turns {{ font-family:"Saira Condensed"; font-weight: 500; font-size: 12px; letter-spacing: .04em; line-height: 1.5; color: var(--black); padding: 12px 14px; background: var(--bg); border: 2px solid var(--black); }}
.key-turns h4 {{ margin: 0 0 6px; font-family:"Big Shoulders Display"; font-weight: 900; font-size: 13px; letter-spacing: .12em; color: var(--red); text-transform: uppercase; }}
.key-turns b {{ font-family:"JetBrains Mono"; font-weight:700; font-size: 11px; }}

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

.coach {{ padding: 28px 36px; background: var(--paper); border-bottom: 2px solid var(--black); display:grid; grid-template-columns: 1fr 1fr; gap: 36px; }}
.coach h3 {{ font-family:"Big Shoulders Display"; font-weight: 900; font-size: 18px; letter-spacing:.06em; text-transform: uppercase; margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid var(--red); }}
.coach p {{ font-family:"Saira"; font-weight: 400; font-size: 15px; line-height: 1.55; margin: 0 0 12px; }}
.coach p b {{ color: var(--red); }}

/* WHERE TIME HIDES — combined map + analysis */
.where {{ padding: 28px 36px; background: var(--paper); border-bottom: 2px solid var(--black); display:grid; grid-template-columns: 240px 1fr; gap: 32px; align-items: start; }}
.where .map-svg {{ width: 100%; max-height: 420px; height: auto; display:block; background: #faf8f3; border: 2px solid var(--black); }}
.where .map-stats {{ display:grid; grid-template-columns: repeat(2, 1fr); gap: 0; border-top: 2px solid var(--black); border-bottom: 2px solid var(--black); margin-top: 12px; }}
.where .map-stats .stat {{ padding: 8px 12px; border-right: 1px solid var(--soft-grey); border-bottom: 1px solid var(--soft-grey); }}
.where .map-stats .stat:nth-child(2n) {{ border-right: none; }}
.where .map-stats .stat:nth-child(n+3) {{ border-bottom: none; }}
.where .map-stats .label {{ font-family:"Saira Condensed"; font-weight:600; font-size: 9px; letter-spacing: .18em; color: var(--grey); }}
.where .map-stats .value {{ font-family:"Big Shoulders Display"; font-weight:800; font-size: 16px; line-height: 1; margin-top: 3px; }}
.where .legend {{ display:flex; flex-direction: column; gap: 5px; padding-top: 12px; font-family:"Saira Condensed"; font-weight: 600; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; }}
.where .legend .row {{ display:flex; align-items: center; gap: 8px; }}
.where .legend .swatch {{ display:inline-block; width: 18px; height: 3px; flex-shrink: 0; }}
.where .analysis h3 {{ font-family:"Big Shoulders Display"; font-weight: 900; font-size: 22px; letter-spacing:.04em; text-transform: uppercase; margin: 0 0 10px; padding-bottom: 8px; border-bottom: 2px solid var(--red); }}
.where .analysis p {{ font-family:"Saira"; font-weight: 400; font-size: 15px; line-height: 1.55; margin: 0 0 14px; }}
.where .analysis p b {{ color: var(--red); }}
.where .money-block {{ background: var(--bg); border: 2px solid var(--black); padding: 14px 18px; margin: 16px 0; }}
.where .money-block h4 {{ margin: 0 0 6px; font-family:"Big Shoulders Display"; font-weight: 900; font-size: 14px; letter-spacing: .12em; text-transform: uppercase; color: var(--red); }}
.where .money-block .turns {{ font-family:"Saira Condensed"; font-weight: 600; font-size: 13px; letter-spacing: .04em; line-height: 1.6; }}
.where .money-block .turns b {{ font-family:"JetBrains Mono"; font-weight: 700; }}

.orders {{ padding: 24px 36px; background: var(--bg); border-bottom: 2px solid var(--black); }}
.orders .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.order {{ background: var(--paper); border: 2px solid var(--black); padding: 14px 18px; display:flex; gap: 14px; align-items: flex-start; }}
.order .num {{ background: var(--black); color: #fff; font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; width: 36px; height: 36px; display:flex; align-items: center; justify-content: center; flex-shrink: 0; }}
.order:nth-child(odd) .num {{ background: var(--red); }}
.order .body {{ font-family:"Saira"; font-weight: 400; font-size: 14px; line-height: 1.45; }}
.order .body b {{ font-family:"Saira Condensed"; font-weight: 700; letter-spacing: .04em; }}

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

.turn-ref {{ display: inline-block; padding: 1px 6px; border: 2px solid var(--black); background: #fff; font-family:"JetBrains Mono"; font-weight:700; font-size: .9em; line-height: 1; cursor: pointer; transition: all .1s ease; user-select: none; }}
.turn-ref:hover, .turn-ref.active {{ background: var(--red); color: #fff; border-color: var(--red); }}

.turn-mark {{ cursor: pointer; transition: opacity .15s ease; }}
.turn-mark.coached circle {{ animation: pulse-ring 2.4s ease-in-out infinite; }}
.turn-mark.active circle:first-child, .turn-mark:hover circle:first-child {{ stroke: var(--red) !important; stroke-width: 4 !important; r: 16 !important; }}
.turn-mark.active text, .turn-mark:hover text {{ font-weight: 900 !important; }}
@keyframes pulse-ring {{ 0%,100% {{ stroke-opacity: 1; }} 50% {{ stroke-opacity: 0.45; }} }}

.foot {{ padding: 18px 36px; background: var(--black); color: #aaa; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; display:flex; gap: 24px; }}
.foot .red {{ color: var(--red); }}
.foot .pad {{ flex:1 }}
</style></head>
<body>

<div class="ticker">
  <span>HOTLAP CHASE</span>
  <span class="red">●</span>
  <span>{track_name}</span>
  <span class="red">●</span>
  <span>RUSSELL · F1 POLE 2025 — TARGET <span class="red">{f1_ref_str}</span></span>
  <span class="session-tag">SESSION #{session_number}</span>
  <span class="pad"></span>
  <span>SESSION {session_ts}</span>
  <div class="checker"></div>
</div>

<div class="hero">
  <div class="hero-left">
    <div class="hero-pos">P1 · YOUR PB</div>
    <div class="hero-driver">{driver}</div>
    <div class="hero-meta"><b>{car}</b> · {skin} · {track_name} · LAYOUT F1 2025</div>
    <div class="hero-time">
      <div class="label">PERSONAL BEST<br>{laps_count}</div>
      <div class="value">{pb_str}</div>
    </div>
    <div class="hero-tagline">{hero_tagline}</div>
  </div>
  <div class="hero-right">
    <div class="gap-block">
      <div class="label">GAP TO POLE</div>
      <div class="ref">{f1_ref_label}</div>
      <div class="num">+{gap_f1}</div>
    </div>
    {progression_block}
    <div class="gap-block small">
      <div class="label">THEORETICAL OPTIMUM (YOUR SECTORS)</div>
      <div class="num">{theo_str} → headroom −{theo_gain}</div>
    </div>
  </div>
</div>

<div class="sec-head">
  <span class="num">01</span>
  <span class="title">THE LAPS</span>
  <span class="sub">SECTOR TOWER · F1 TIMING COLOURS</span>
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

<div class="sec-head">
  <span class="num">02</span>
  <span class="title">WHERE TIME HIDES</span>
  <span class="sub">MAP × ANALYSIS — RED-RINGED TURNS = MONEY ZONE</span>
</div>
<div class="where">
  <div>
    <svg class="map-svg" viewBox="0 0 {svg_w} {svg_h}" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="turn-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="b"/>
          <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <image href="data:image/png;base64,{outline_b64}" x="0" y="0" width="{svg_w}" height="{svg_h}" opacity="0.12"/>
      {drs_svg}
      <path d="{p1}" stroke="var(--s1)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="{p2}" stroke="var(--s2)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="{p3}" stroke="var(--s3)" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      {sector_markers_svg}
      {turn_labels_svg}
      <g>
        <line x1="{sf_x1}" y1="{sf_y1}" x2="{sf_x2}" y2="{sf_y2}" stroke="#000" stroke-width="3"/>
        <rect x="{sf_lx}" y="{sf_ly}" width="60" height="18" fill="#000"/>
        <text x="{sf_tx}" y="{sf_ty}" font-family="Big Shoulders Display" font-weight="900" fill="#fff" font-size="14" letter-spacing="2">START</text>
      </g>
    </svg>
    <div class="map-stats">
      <div class="stat"><div class="label">LENGTH</div><div class="value">4.361 KM</div></div>
      <div class="stat"><div class="label">TURNS</div><div class="value">14</div></div>
      <div class="stat"><div class="label">DRS ZONES</div><div class="value">3</div></div>
      <div class="stat"><div class="label">RUSSELL POLE</div><div class="value">{f1_ref_str}</div></div>
    </div>
    <div class="legend">
      <div class="row"><span class="swatch" style="background:var(--s1)"></span>S1 SENNA + ESSES</div>
      <div class="row"><span class="swatch" style="background:var(--s2)"></span>S2 EPINGLE + CASINO</div>
      <div class="row"><span class="swatch" style="background:var(--s3)"></span>S3 WALL OF CHAMPIONS</div>
      <div class="row"><span class="swatch" style="background:#d8a000"></span>DRS ZONE (×3)</div>
    </div>
  </div>
  <div class="analysis">
    <h3>THE STORY OF YOUR SESSION</h3>
    {story_html}
    <div class="money-block">
      <h4>MONEY SECTOR · {money_sector_label}</h4>
      <div class="turns">{money_turns_explainer}</div>
    </div>
    {strategy_html}
  </div>
</div>

<div class="sec-head">
  <span class="num">03</span>
  <span class="title">NEXT STINT</span>
  <span class="sub">PIT-BOARD ORDERS · HOVER ANY <span style="background:#fff;color:#000;padding:1px 6px;font-family:JetBrains Mono">T#</span> TO LIGHT IT ON THE MAP</span>
</div>
<div class="orders">
  <div class="grid">
    {orders_html}
  </div>
</div>

<div class="sec-head">
  <span class="num">04</span>
  <span class="title">TURN REFERENCE</span>
  <span class="sub">DETAIL CARDS FOR THE COACHED CORNERS</span>
</div>
<div class="turn-guide-wrap">
  <div class="turn-grid">
  {turn_cards_html}
  </div>
</div>

<div class="foot">
  <span>MONTREAL HOTLAP DASHBOARD</span>
  <span class="red">●</span>
  <span>BUILT {build_ts}</span>
  <span class="pad"></span>
  <span>NORTH-STAR: RUSSELL F1 POLE 2025 · <span class="red">{f1_ref_str}</span></span>
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
        print("No laps found in out/race_out.json — drive a session first")
        return
    session_pb_ms = min(l['time'] for l in laps)
    session_best_s1 = min(l['s1'] for l in laps)
    session_best_s2 = min(l['s2'] for l in laps)
    session_best_s3 = min(l['s3'] for l in laps)
    session_theo = session_best_s1 + session_best_s2 + session_best_s3

    at = load_alltime_pb()
    pb_ms = at['time_ms'] if at and at['time_ms'] < session_pb_ms else session_pb_ms
    pb_is_alltime = (at is not None and at['time_ms'] <= session_pb_ms)

    # ----- Progression vs previous session -----
    prog = update_hotlap_history(session_pb_ms, session_best_s1, session_best_s2,
                                 session_best_s3, len(laps))
    session_number = prog["session_number"]
    prev_session = prog["previous"]
    progression_phrase = ""
    if prev_session:
        pb_delta = session_pb_ms - prev_session["pb_ms"]  # negative = faster
        prev_pb_str = ms_to_str(prev_session["pb_ms"])
        if pb_delta < 0:
            progression_block = (
                f'<div class="gap-block progression">'
                f'  <div class="label">vs LAST SESSION</div>'
                f'  <div class="ref">SESSION #{session_number} · WAS {prev_pb_str}</div>'
                f'  <div class="num green">−{ms_to_str(abs(pb_delta))}</div>'
                f'</div>')
            progression_phrase = (f"<b>{ms_to_str(abs(pb_delta))} faster</b> than session #{session_number-1} "
                                  f"({prev_pb_str}). ")
        elif pb_delta > 0:
            progression_block = (
                f'<div class="gap-block progression">'
                f'  <div class="label">vs LAST SESSION</div>'
                f'  <div class="ref">SESSION #{session_number} · WAS {prev_pb_str}</div>'
                f'  <div class="num red">+{ms_to_str(pb_delta)}</div>'
                f'</div>')
            progression_phrase = (f"<b>{ms_to_str(pb_delta)} slower</b> than session #{session_number-1} "
                                  f"({prev_pb_str}). ")
        else:
            progression_block = (
                f'<div class="gap-block progression">'
                f'  <div class="label">vs LAST SESSION</div>'
                f'  <div class="ref">SESSION #{session_number} · MATCHED {prev_pb_str}</div>'
                f'  <div class="num">±0.000</div>'
                f'</div>')
            progression_phrase = f"Matched session #{session_number-1} PB ({prev_pb_str}). "
    else:
        progression_block = (
            f'<div class="gap-block progression">'
            f'  <div class="label">SESSION</div>'
            f'  <div class="ref">FIRST CANADIAN GP HOTLAP</div>'
            f'  <div class="num">#{session_number}</div>'
            f'</div>')

    best_s1, best_s2, best_s3 = session_best_s1, session_best_s2, session_best_s3
    theo = session_theo
    theo_gain = session_pb_ms - theo

    gap_f1 = pb_ms - F1_REF_MS

    pct1 = best_s1 / session_pb_ms
    pct2 = (best_s1 + best_s2) / session_pb_ms

    m = load_map()
    ai = decode_ai(LAYOUT / "ai/fast_lane.ai")
    turns = synth_turns()
    drs = load_drs()
    svg = build_track_svg(ai, m, turns, drs, [pct1, pct2])

    sf_x = svg['turns'][0]['x'] if svg['turns'] else m['MARGIN'] + 100
    sf_y = svg['turns'][0]['y'] if svg['turns'] else m['MARGIN'] + 100

    drs_svg = "\n    ".join(
        f'<path d="{p}" stroke="#d8a000" stroke-width="14" fill="none" opacity="0.55" stroke-linecap="round"/>'
        for p in svg['drs'] if p
    )

    sector_markers_svg = "\n    ".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#000" stroke="#fff" stroke-width="2"/>'
        f'<text x="{x:.1f}" y="{y+4:.1f}" text-anchor="middle" font-family="Big Shoulders Display" font-weight="900" font-size="11" fill="#fff">{i+1}|{i+2}</text>'
        for i, (label, x, y) in enumerate(svg['sectors'])
    )

    max_time = max(l['time'] for l in laps)
    lap_rows = []
    for i, l in enumerate(laps):
        is_pb = (l['time'] == pb_ms)
        def tag(val, best):
            if val == best:
                return 'purple', 'P'
            elif val - best < 700:
                return 'yellow', '+'+sec_to_str(val-best)
            else:
                return 'red', '+'+sec_to_str(val-best)
        s1_class, s1_lab = tag(l['s1'], best_s1)
        s2_class, s2_lab = tag(l['s2'], best_s2)
        s3_class, s3_lab = tag(l['s3'], best_s3)
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

    n = len(laps)
    progression = laps[-1]['time'] - laps[0]['time']
    sector_gains = {
        'S1': laps[0]['s1'] - laps[-1]['s1'],
        'S2': laps[0]['s2'] - laps[-1]['s2'],
        'S3': laps[0]['s3'] - laps[-1]['s3'],
    }
    biggest_gain_sec = max(sector_gains, key=lambda k: sector_gains[k])
    smallest_gain_sec = min(sector_gains, key=lambda k: sector_gains[k])

    alltime_clause = ""
    if at and session_pb_ms > at['time_ms']:
        alltime_clause = (f" Session best <b>{ms_to_str(session_pb_ms)}</b> is "
                          f"<b>+{ms_to_str(session_pb_ms - at['time_ms'])}</b> off all-time PB "
                          f"<b>{ms_to_str(at['time_ms'])}</b>.")

    cuts_total = sum(l.get('cuts', 0) for l in laps)
    cuts_str = f"{cuts_total} cut{'s' if cuts_total != 1 else ''}"

    # ----- Hero tagline (1 sentence preview at the top) -----
    if progression < 0 and n > 1:
        hero_tagline = (f"{progression_phrase}<b>{n} laps</b>, <b>{cuts_str}</b>. "
                        f"From <b>{ms_to_str(laps[0]['time'])}</b> to <b>{ms_to_str(laps[-1]['time'])}</b> "
                        f"— <b>{ms_to_str(abs(progression))}</b> faster. "
                        f"<b>{biggest_gain_sec}</b> dropped <b>{ms_to_str(sector_gains[biggest_gain_sec])}</b>. "
                        f"<b>{smallest_gain_sec}</b> stalled — that's the next zone.")
    else:
        hero_tagline = (f"{progression_phrase}<b>{n} lap{'s' if n!=1 else ''}</b>, <b>{cuts_str}</b>. "
                        f"PB <b>{ms_to_str(session_pb_ms)}</b>. Optimum <b>{ms_to_str(theo)}</b> · "
                        f"headroom <b>{ms_to_str(theo_gain)}</b>.")

    # ----- Story paragraph (under "THE STORY OF YOUR SESSION") -----
    if progression < 0 and n > 1:
        story = (f"<p>From <b>{ms_to_str(laps[0]['time'])}</b> on the warmup to "
                 f"<b>{ms_to_str(laps[-1]['time'])}</b> on lap {n} — <b>{ms_to_str(abs(progression))} faster</b>, "
                 f"all clean. The biggest gain was <b>{biggest_gain_sec}</b> "
                 f"(<b>{ms_to_str(sector_gains[biggest_gain_sec])}</b> across the session), still trending down. "
                 f"Theoretical optimum (best sectors stitched): <b>{ms_to_str(theo)}</b>; headroom in this dataset: "
                 f"<b>{ms_to_str(theo_gain)}</b>.{alltime_clause}</p>")
    else:
        story = (f"<p>{n} lap{'s' if n != 1 else ''} this session. PB <b>{ms_to_str(session_pb_ms)}</b>. "
                 f"Theoretical optimum <b>{ms_to_str(theo)}</b> — headroom "
                 f"<b>{ms_to_str(theo_gain)}</b>.{alltime_clause}</p>")

    # ----- Money sector framing (the inline callout in WHERE TIME HIDES) -----
    sector_to_label = {
        'S1': 'SENNA CHICANE + ESSES',
        'S2': 'EPINGLE EXIT + CASINO COMMITMENT',
        'S3': 'WALL OF CHAMPIONS CHICANE',
    }
    sector_to_money_explainer = {
        'S1': '<b>T1</b> Senna chicane — late-brake from main-straight DRS · <b>T7</b> esses exit — earliest throttle pickup feeds the run to T8',
        'S2': '<b>T10</b> L\'Epingle exit — earliest throttle on · <b>T12</b> mid-Casino kink — should be flat. Every lift = car-length lost into T13',
        'S3': '<b>T13</b> Wall of Champions L — heaviest brake of the lap · <b>T14</b> WoC R — get straight first, throttle second. The wall doesn\'t forgive',
    }
    money_sector_label = f"{smallest_gain_sec} · {sector_to_label[smallest_gain_sec]}"
    money_turns_explainer = sector_to_money_explainer[smallest_gain_sec]

    # ----- Strategy paragraph (under the money block) -----
    strategy = (f"<p><b>{smallest_gain_sec}</b> dropped only <b>{ms_to_str(sector_gains[smallest_gain_sec])}</b> "
                f"across {n} laps — that's the floor. <b>{biggest_gain_sec}</b> dropped "
                f"<b>{ms_to_str(sector_gains[biggest_gain_sec])}</b>; you're still finding line in there. "
                f"Next attack: chain a clean S1, commit T12 mid-Casino flat, hold a patient T13/14 — "
                f"<b>{ms_to_str(session_pb_ms - 1000)}</b> is the next milestone.</p>")

    sector_to_focus_turns = {
        'S1': [1, 7],            # Senna entry, esses exit to S1 end
        'S2': [10, 12],          # Epingle, Casino-straight L kink
        'S3': [13, 14],          # Wall of Champions chicane
    }
    money_turns = sector_to_focus_turns.get(smallest_gain_sec, [10, 13])
    target_sector_best = {'S1': best_s1, 'S2': best_s2, 'S3': best_s3}[smallest_gain_sec]
    target_str = sec_to_str(max(target_sector_best - 300, 0))

    import re as _re
    def linkify_turns(text: str) -> str:
        return _re.sub(r'\bT(\d+)\b', r'<span class="turn-ref" data-turn="\1">T\1</span>', text)

    orders_raw = [
        ("Run a <b>6-lap stint</b>: 1 outlap + 4 hot + 1 cooldown. Don't chase one perfect lap — chain sectors.", []),
        (f"<b>{smallest_gain_sec} focus.</b> Money sector. Aim ≤ <b>{target_str}</b> in {smallest_gain_sec} next session — push the red-ringed turns below.", money_turns),
        ("<b>L'Epingle exit (T10) sets up Casino Droit.</b> Earlier throttle pickup = +5 km/h at the T13 brake zone.", [10]),
        ("<b>Wall of Champions (T13/14):</b> resist the hero exit. Get straight, then throttle. Wall doesn't forgive.", [13, 14]),
        (f"<b>Lap target next stint:</b> <span style=\"color:var(--red);font-weight:800\">{ms_to_str(session_pb_ms - 1000)}</span>.", []),
        ("<b>Tyres = C5 (soft).</b> Hotlap mode = no wear; one compound is enough until you start fighting tenths.", []),
    ]

    coached_turns = set()
    for _, ts in orders_raw:
        coached_turns.update(ts)
    for txt in [story, strategy, money_turns_explainer, hero_tagline]:
        for m_ in _re.finditer(r'\bT(\d+)\b', txt):
            coached_turns.add(int(m_.group(1)))

    story = linkify_turns(story)
    strategy = linkify_turns(strategy)
    money_turns_explainer = linkify_turns(money_turns_explainer)
    hero_tagline = linkify_turns(hero_tagline)

    orders_html = "\n    ".join(
        f'<div class="order"><div class="num">{i+1}</div><div class="body">{linkify_turns(text)}</div></div>'
        for i, (text, _ts) in enumerate(orders_raw)
    )

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

    coached_sorted = sorted(coached_turns)
    turn_cards_html_parts = []
    for tnum in coached_sorted:
        if tnum not in MONTREAL_CORNERS: continue
        c = MONTREAL_CORNERS[tnum]
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

    outline_b64 = b64_png(LAYOUT.parent / "ui/montreal_f1_2025/outline.png")

    session_ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    pb_subtitle = ("ALL-TIME PB · COMBO" if pb_is_alltime else f"{len(laps)} LAP{'S' if len(laps)!=1 else ''} · ALL CLEAN")
    if pb_is_alltime and len(laps) > 0:
        pb_subtitle += f" · SESSION BEST {ms_to_str(session_pb_ms)}"
    html = HTML_TPL.format(
        driver=DRIVER_NAME, car=CAR_NAME, skin=SKIN_NAME, track_name=TRACK_NAME,
        f1_ref_str=ms_to_str(F1_REF_MS), f1_ref_label=F1_REF_LABEL,
        f1_ref_driver=F1_REF_DRIVER,
        pb_str=ms_to_str(pb_ms), laps_count=pb_subtitle,
        gap_f1=ms_to_str(gap_f1, with_sign=False).lstrip('+'),
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
        hero_tagline=hero_tagline,
        money_sector_label=money_sector_label,
        money_turns_explainer=money_turns_explainer,
        progression_block=progression_block,
        session_number=session_number,
        session_ts=session_ts,
        build_ts=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    out_path = OUT_DIR / "dashboard.html"
    out_path.write_text(html, encoding='utf-8')
    print(f"Wrote {out_path}")
    print(f"PB: {ms_to_str(pb_ms)}  |  Gap to F1: +{ms_to_str(gap_f1)}  |  Theoretical: {ms_to_str(theo)}")

if __name__ == "__main__":
    main()
