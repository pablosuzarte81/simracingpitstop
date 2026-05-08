#!/usr/bin/env python3
"""Canadian GP 2026 race summary — reads out/race_out.json after AC exits and renders
a self-contained HTML race report.

Run: wsl python3 dashboard/montreal/race_summary_montreal.py
Output: Documents/Assetto Corsa/dashboard/montreal/race_summary.html
"""
from __future__ import annotations
import json, base64, struct, configparser
from pathlib import Path
from datetime import datetime

HOME = Path("/mnt/c/Users/pablo/Documents/Assetto Corsa")
TRACK = Path("/mnt/d/SteamLibrary/steamapps/common/assettocorsa/content/tracks/montreal")
LAYOUT = TRACK / "montreal_f1_2025"
OUT_DIR = HOME / "dashboard/montreal"
HISTORY_FILE = OUT_DIR / "race_history.json"

DRIVER_NAME = "PABLO SUZARTE"
TRACK_NAME = "CIRCUIT GILLES VILLENEUVE"
F1_REF_MS = 70899  # 2025 Canadian GP pole — Russell

# Real-2026 team strings keyed by driver (so the table reads correctly even if
# skin metadata is anachronistic — Hadjar in 2025 RB livery is in 2026 RBR).
DRIVER_TEAM = {
    "Max Verstappen": ("Red Bull Racing", "#1c2a8a"),
    "Kimi Antonelli": ("Mercedes", "#00d2be"),
    "George Russell": ("Mercedes", "#00d2be"),
    "Lando Norris": ("McLaren", "#ff8000"),
    "Oscar Piastri": ("McLaren", "#ff8000"),
    "Charles Leclerc": ("Ferrari", "#dc0000"),
    "Lewis Hamilton": ("Ferrari", "#dc0000"),
    "Franco Colapinto": ("Alpine", "#0090ff"),
    "Pierre Gasly": ("Alpine", "#0090ff"),
    "Carlos Sainz": ("Williams", "#005aff"),
    "Alex Albon": ("Williams", "#005aff"),
    "Isack Hadjar": ("Red Bull Racing", "#1c2a8a"),
    "Liam Lawson": ("Racing Bulls", "#6692ff"),
    "Oliver Bearman": ("Haas F1 Team", "#b6babd"),
    "Esteban Ocon": ("Haas F1 Team", "#b6babd"),
    "Nico Hulkenberg": ("Audi", "#52e252"),
    "Gabriel Bortoleto": ("Audi", "#52e252"),
    "Fernando Alonso": ("Aston Martin", "#229971"),
    "Lance Stroll": ("Aston Martin", "#229971"),
}

# ----- Helpers -----
def ms_to_str(ms: int) -> str:
    if ms is None or ms <= 0:
        return "—"
    m, rem = divmod(int(ms), 60000)
    s = rem / 1000
    return f"{m}:{s:06.3f}" if m > 0 else f"{s:.3f}"

# ----- History: per-race progression -----
def load_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []

def save_history(history):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

def update_history(player, bestlap, field_size, real_race):
    """Append this race to history (dedup on finish+grid+fl). Return progression context."""
    history = load_history()
    if not real_race or not player or player.get("raw_finish", 0) <= 0:
        return {"current": None, "previous": history[-1] if history else None,
                "race_number": len(history) + 1}
    new_entry = {
        "ts": datetime.now().isoformat(timespec='seconds'),
        "finish": int(player["raw_finish"]),
        "grid": int(player["grid"]),
        "fastest_lap_ms": int(bestlap) if bestlap else None,
        "field_size": int(field_size),
    }
    last = history[-1] if history else None
    is_dup = (last
              and last.get("finish") == new_entry["finish"]
              and last.get("grid") == new_entry["grid"]
              and last.get("fastest_lap_ms") == new_entry["fastest_lap_ms"])
    if is_dup:
        prev = history[-2] if len(history) >= 2 else None
        race_number = len(history)
    else:
        prev = last
        history.append(new_entry)
        save_history(history)
        race_number = len(history)
    return {"current": new_entry, "previous": prev, "race_number": race_number}

# ----- Parse race_out.json -----
def load_race():
    p = HOME / "out/race_out.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None

# ----- Read grid order from preset (keeps comment layer intact) -----
def load_grid_from_preset():
    p = HOME / "cfg/race.ini"  # the active race.ini AC used
    if not p.exists():
        return []
    cfg = configparser.ConfigParser(strict=False, inline_comment_prefixes=None)
    try:
        cfg.read(p)
    except Exception:
        return []
    grid = []
    i = 0
    while True:
        sec = f"CAR_{i}"
        if sec not in cfg:
            break
        grid.append({
            "driver": cfg[sec].get("DRIVER_NAME", "—"),
            "team":   cfg[sec].get("TEAM", "—"),
            "skin":   cfg[sec].get("SKIN", ""),
        })
        i += 1
    return grid

# ----- Compute classification -----
def build_classification(race_data, grid):
    """
    AC's raceResult array is 1-indexed final positions per grid slot.
    raceResult[grid_idx] = final_position (1 = winner, 0 = DNF/last/unfinished)
    """
    if not race_data or not race_data.get("sessions"):
        return [], None, None, False
    sess = race_data["sessions"][-1]
    rr = sess.get("raceResult", [])
    laps_count = sess.get("lapstotal", [])  # per-car laps; lapsCount is session total (int)
    # AC's bestlap from extras is the most reliable "real race" signal.
    # lapstotal can be all zeros even for a finished race (AC quirk for hotlap-spawned races).
    bestlap = None
    for ex in race_data.get("extras", []):
        if ex.get("name") == "bestlap" and ex.get("time", 0) > 0:
            bestlap = ex["time"]
            break
    # Real race signal: bestlap > 30s, raceResult populated, AND at least one car
    # has driven a lap (either lapstotal > 0 or session.laps populated). Without
    # the lap-evidence check, AC's stale placeholder bestlap leaks through.
    has_lap_evidence = any((c or 0) > 0 for c in laps_count) or any(
        len(s.get('laps', [])) > 0 for s in race_data.get("sessions", []))
    real_race = (bestlap is not None and bestlap > 30000 and bool(rr) and has_lap_evidence)
    # AC writes raceResult[finish_pos_idx] = grid_idx of driver who finished there.
    # AC behavior with no qualifying session: PLAYER (CAR_0) starts at the BACK
    # of the grid; AI cars CAR_1..N take grid positions 1..N in CAR_X order.
    total_cars = len(rr)
    items = []
    for fp_idx, gi in enumerate(rr):
        finish = fp_idx + 1
        if gi < 0 or gi >= len(race_data.get("players", [])):
            continue
        driver = race_data["players"][gi]["name"]
        team_real, color = DRIVER_TEAM.get(driver, ("—", "#888"))
        team_disp = grid[gi]["team"] if gi < len(grid) and grid[gi]["team"] != "—" else team_real
        # Grid position: player (gi==0) starts last; AI starts at their CAR_X number.
        starting_grid = total_cars if gi == 0 else gi
        items.append({
            "grid": starting_grid,
            "finish": finish,
            "driver": driver,
            "team": team_disp,
            "color": color,
            "laps": laps_count[gi] if gi < len(laps_count) else 0,
            "is_player": (gi == 0),
            "raw_finish": finish,
        })
    items.sort(key=lambda x: x["finish"])
    return items, bestlap, sess.get("name", "Race"), real_race

# ----- HTML render -----
def render(items, bestlap, session_name, real_race=True, prog=None):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not items:
        out = OUT_DIR / "race_summary.html"
        out.write_text("<!doctype html><html><body style='font-family:sans-serif;padding:40px'><h1>NO RACE DATA</h1><p>race_out.json is empty or malformed. Drive a race first.</p></body></html>", encoding='utf-8')
        return out
    if not real_race:
        out = OUT_DIR / "race_summary.html"
        out.write_text("""<!doctype html><html><head><meta charset="utf-8">
<title>NO RACE DRIVEN</title>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@900&family=Saira:wght@400;600&display=swap" rel="stylesheet">
<style>body{font-family:"Saira",sans-serif;background:#f3f1ec;color:#0a0a0a;margin:0;padding:0}
.box{max-width:720px;margin:80px auto;padding:48px;border:2px solid #0a0a0a;background:#fff}
h1{font-family:"Big Shoulders Display";font-weight:900;font-size:64px;margin:0 0 16px;color:#D40E10;letter-spacing:-.01em}
p{font-size:17px;line-height:1.55;margin:8px 0}
b{color:#D40E10}</style></head><body>
<div class="box">
<h1>NO RACE WAS DRIVEN</h1>
<p>race_out.json contains a result, but no car completed a single lap. AC writes a placeholder finish order (using the grid) when you exit the loaded race without driving — that's what's in the file right now.</p>
<p>This is not a real result. Drive the race to completion (or at least one lap) to generate a meaningful summary.</p>
<p style="margin-top:32px;font-size:13px;color:#666;letter-spacing:.12em;text-transform:uppercase">Tip: if you opened the shortcut just to verify it works, that's why this is here.</p>
</div></body></html>""", encoding='utf-8')
        return out

    # Find player
    player = next((x for x in items if x["is_player"]), None)
    player_finish = player["raw_finish"] if player else None
    player_grid = player["grid"] if player else None
    player_pos_change = (player_grid - player["finish"]) if player and player["raw_finish"] > 0 else None

    # Find fastest-lap holder (best we can do without per-driver lap times)
    fl_holder = "—"
    if bestlap:
        # AC doesn't expose per-driver bestlap reliably; show the value alone
        pass

    # Build classification rows
    rows = []
    for x in items:
        finish_str = "DNF" if x["raw_finish"] == 0 else f"P{x['raw_finish']}"
        delta_grid = x["grid"] - x["finish"] if x["raw_finish"] > 0 else 0
        delta_str = ""
        if delta_grid > 0:
            delta_str = f'<span style="color:#1f8a4c;font-weight:700">▲{delta_grid}</span>'
        elif delta_grid < 0:
            delta_str = f'<span style="color:#d40e10;font-weight:700">▼{abs(delta_grid)}</span>'
        else:
            delta_str = '<span style="color:#999">—</span>'
        player_class = ' class="player-row"' if x["is_player"] else ''
        rows.append(f"""
        <tr{player_class}>
          <td class="pos">{finish_str}</td>
          <td class="driver"><span class="team-bar" style="background:{x['color']}"></span>{x['driver']}</td>
          <td>{x['team']}</td>
          <td class="grid-cell">{x['grid']}</td>
          <td class="delta-cell">{delta_str}</td>
        </tr>""")
    rows_html = "\n".join(rows)

    # Headline copy
    pos_change_label = ""
    if player and player_pos_change is not None:
        if player_pos_change > 0:
            pos_change_label = f"▲{player_pos_change} POSITION{'S' if player_pos_change != 1 else ''}"
        elif player_pos_change < 0:
            pos_change_label = f"▼{abs(player_pos_change)} POSITION{'S' if abs(player_pos_change) != 1 else ''}"
        else:
            pos_change_label = "HELD STATION"
    if player and player["raw_finish"] == 1:
        headline = "VICTORY"
        sub = f"P1 from grid P{player_grid} · {pos_change_label}"
        accent = "#D40E10"
    elif player and player["raw_finish"] in (2, 3):
        headline = "PODIUM"
        sub = f"P{player['raw_finish']} from grid P{player_grid} · {pos_change_label}"
        accent = "#d8a000"
    elif player and player["raw_finish"] in range(4, 11):
        headline = f"P{player['raw_finish']}"
        sub = f"Points finish from grid P{player_grid} · {pos_change_label}"
        accent = "#1f8a4c"
    elif player and player["raw_finish"] > 0:
        headline = f"P{player['raw_finish']}"
        sub = f"From grid P{player_grid} · {pos_change_label}"
        accent = "#444"
    elif player and player["raw_finish"] == 0:
        headline = "DNF"
        sub = "Did not finish"
        accent = "#d40e10"
    else:
        headline = "—"
        sub = "—"
        accent = "#888"

    # Position change story
    if player and player["raw_finish"] > 0:
        if player_pos_change > 0:
            arc_msg = f"Gained <b>{player_pos_change}</b> position{'s' if player_pos_change != 1 else ''} (started <b>P{player_grid}</b>)"
        elif player_pos_change < 0:
            arc_msg = f"Lost <b>{abs(player_pos_change)}</b> position{'s' if abs(player_pos_change) != 1 else ''} (started <b>P{player_grid}</b>)"
        else:
            arc_msg = f"Held station from grid <b>P{player_grid}</b>"
    else:
        arc_msg = "Did not finish"

    bestlap_str = ms_to_str(bestlap) if bestlap else "—"
    bestlap_vs_pole = ""
    if bestlap and bestlap > 0:
        gap = bestlap - F1_REF_MS
        bestlap_vs_pole = f"<b>+{ms_to_str(gap)}</b> vs Russell pole {ms_to_str(F1_REF_MS)}"

    # ----- Progression vs previous race -----
    race_number = (prog or {}).get("race_number", 1)
    prev = (prog or {}).get("previous")
    cur = (prog or {}).get("current")
    progression_arc = ""
    progression_block = f"""
    <div class="stat">
      <div class="label">FIELD</div>
      <div class="value">{len(items)}</div>
      <div class="extra">CARS · REAL 2026 GRID</div>
    </div>"""
    if prev and cur:
        pos_delta = prev["finish"] - cur["finish"]   # +ve = gained positions
        prev_fl = prev.get("fastest_lap_ms")
        cur_fl = cur.get("fastest_lap_ms")
        fl_delta = (cur_fl - prev_fl) if (prev_fl and cur_fl) else None  # -ve = faster

        if pos_delta > 0:
            pos_str = f"▲{pos_delta}"
            pos_color = "#5ac96a"
            pos_word = f"Gained <b>{pos_delta}</b> position{'s' if pos_delta != 1 else ''}"
        elif pos_delta < 0:
            pos_str = f"▼{abs(pos_delta)}"
            pos_color = "#ff4848"
            pos_word = f"Lost <b>{abs(pos_delta)}</b> position{'s' if abs(pos_delta) != 1 else ''}"
        else:
            pos_str = "—"
            pos_color = "#fff"
            pos_word = "Held position"

        if fl_delta is not None:
            if fl_delta < 0:
                fl_extra = f"<span style='color:#5ac96a'>−{ms_to_str(abs(fl_delta))}</span> on FL"
                fl_word = f"FL <b style='color:#5ac96a'>−{ms_to_str(abs(fl_delta))}</b>"
            elif fl_delta > 0:
                fl_extra = f"<span style='color:#ff4848'>+{ms_to_str(fl_delta)}</span> on FL"
                fl_word = f"FL <b style='color:#ff4848'>+{ms_to_str(fl_delta)}</b>"
            else:
                fl_extra = "Same FL as last race"
                fl_word = "FL unchanged"
        else:
            fl_extra = "NO PREVIOUS FL"
            fl_word = ""

        progression_block = f"""
    <div class="stat">
      <div class="label">vs LAST RACE</div>
      <div class="value" style="color:{pos_color}">{pos_str}</div>
      <div class="extra">{fl_extra} · WAS P{prev['finish']}</div>
    </div>"""
        progression_arc = (f" <b>Race #{race_number}</b> — {pos_word.lower()} vs last race"
                           f"{' · ' + fl_word if fl_word else ''}.")
    else:
        progression_block = f"""
    <div class="stat">
      <div class="label">RACE</div>
      <div class="value">#{race_number}</div>
      <div class="extra">FIRST CANADIAN GP RACE LOGGED · {len(items)} CARS</div>
    </div>"""
        progression_arc = f" <b>Race #{race_number}</b> — baseline logged. Future races compare here."

    build_ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>CANADIAN GP RESULT — {DRIVER_NAME}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800;900&family=Saira:wght@400;600;800&family=Saira+Condensed:wght@500;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{ --red:#D40E10; --black:#0a0a0a; --bg:#f3f1ec; --paper:#ffffff; --grey:#999; --soft:#d8d4cb; --gold:#d8a000; --green:#1f8a4c; --accent:{accent}; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background: var(--bg); color: var(--black); font-family: "Saira", sans-serif; }}
.ticker {{ background: var(--black); color: #fff; height: 38px; display:flex; align-items:center; padding: 0 24px; font-family: "Big Shoulders Display"; font-weight:800; letter-spacing:.08em; font-size: 13px; gap: 20px; border-bottom: 2px solid var(--red); }}
.ticker .red {{ color: var(--red); }}
.ticker .pad {{ flex:1 }}
.ticker .checker {{ width: 80px; height: 100%; background: repeating-linear-gradient(90deg, var(--red) 0 12px, #000 12px 24px); }}

.hero {{ display:grid; grid-template-columns: 1.4fr 1fr; background: var(--paper); border-bottom: 2px solid var(--black); }}
.hero-left {{ padding: 32px 36px; border-right: 2px solid var(--black); position: relative; }}
.hero-event {{ font-family:"Saira Condensed"; font-weight:700; font-size: 11px; letter-spacing:.22em; color: var(--grey); text-transform: uppercase; display:flex; align-items:center; gap:10px; }}
.race-tag {{ background: var(--red); color:#fff; padding: 2px 8px; font-family:"Big Shoulders Display"; font-weight:900; font-size: 12px; letter-spacing: .12em; }}
.hero-headline {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 110px; line-height: .9; color: var(--accent); margin: 4px 0 8px; letter-spacing: -.02em; }}
.hero-driver-line {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 36px; line-height: 1; }}
.hero-sub {{ margin-top: 14px; font-family:"Saira Condensed"; font-weight:600; font-size: 14px; letter-spacing: .14em; color: var(--black); text-transform: uppercase; }}
.hero-arc {{ margin-top: 20px; padding-top: 16px; border-top: 2px solid var(--black); font-family:"Saira"; font-size: 16px; line-height: 1.5; }}
.hero-arc b {{ color: var(--red); font-family:"JetBrains Mono"; font-weight:700; }}

.hero-right {{ background: var(--black); color: #fff; padding: 28px 32px; display:flex; flex-direction: column; gap: 24px; justify-content:center; }}
.stat {{ }}
.stat .label {{ font-family:"Saira Condensed"; font-weight:700; font-size: 11px; letter-spacing:.22em; color: #aaa; }}
.stat .value {{ font-family:"JetBrains Mono"; font-weight:700; font-size: 38px; color: #fff; line-height: 1.1; margin-top: 4px; }}
.stat .value.red {{ color: var(--red); }}
.stat .extra {{ font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing:.18em; color: #aaa; margin-top: 4px; }}

.sec-head {{ background: var(--black); color:#fff; padding: 14px 36px; display:flex; align-items:center; gap: 18px; }}
.sec-head .num {{ background: var(--red); color: #fff; font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; padding: 4px 14px; }}
.sec-head .title {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 28px; letter-spacing: .04em; }}
.sec-head .sub {{ margin-left: auto; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .2em; color: #aaa; }}

.classification {{ background: var(--paper); border-bottom: 2px solid var(--black); padding: 0; }}
.classification table {{ width: 100%; border-collapse: collapse; font-family:"Saira"; font-size: 14px; }}
.classification th {{ background: var(--black); color:#fff; text-align:left; padding: 10px 16px; font-family:"Saira Condensed"; font-weight:700; letter-spacing:.14em; font-size: 11px; }}
.classification td {{ padding: 10px 16px; border-bottom: 1px solid var(--soft); }}
.classification .pos {{ font-family:"Big Shoulders Display"; font-weight:900; font-size: 22px; width: 70px; }}
.classification .driver {{ font-family:"Big Shoulders Display"; font-weight:800; font-size: 18px; letter-spacing: .02em; }}
.classification .grid-cell {{ font-family:"JetBrains Mono"; font-weight:600; font-size: 14px; color: var(--grey); width: 80px; text-align: center; }}
.classification .delta-cell {{ font-family:"JetBrains Mono"; font-weight:700; font-size: 14px; width: 80px; text-align: center; }}
.classification .team-bar {{ display: inline-block; width: 4px; height: 18px; vertical-align: middle; margin-right: 10px; }}
.classification .player-row {{ background: #fff7d8; }}
.classification .player-row .pos {{ color: var(--red); }}
.classification .player-row .driver {{ color: var(--red); }}

.foot {{ padding: 18px 36px; background: var(--black); color: #aaa; font-family:"Saira Condensed"; font-weight:500; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; display:flex; gap: 24px; }}
.foot .red {{ color: var(--red); }}
.foot .pad {{ flex:1 }}
</style></head>
<body>

<div class="ticker">
  <span>RACE RESULT</span>
  <span class="red">●</span>
  <span>CANADIAN GP 2026 SIM</span>
  <span class="red">●</span>
  <span>{TRACK_NAME} · MONTREAL F1 2025</span>
  <span class="pad"></span>
  <span>{build_ts}</span>
  <div class="checker"></div>
</div>

<div class="hero">
  <div class="hero-left">
    <div class="hero-event"><span>CANADIAN GRAND PRIX 2026</span><span class="race-tag">RACE #{race_number}</span></div>
    <div class="hero-headline">{headline}</div>
    <div class="hero-driver-line">{DRIVER_NAME}</div>
    <div class="hero-sub">{sub}</div>
    <div class="hero-arc">{arc_msg}.{(' Race fastest lap (anyone): <b>' + bestlap_str + '</b> · ' + bestlap_vs_pole + '.') if bestlap else ''}{progression_arc}</div>
  </div>
  <div class="hero-right">
    <div class="stat">
      <div class="label">FINISH</div>
      <div class="value red">{('P' + str(player['raw_finish'])) if player and player['raw_finish'] > 0 else ('DNF' if player else '—')}</div>
      <div class="extra">FROM GRID P{player_grid if player else '—'}</div>
    </div>
    <div class="stat">
      <div class="label">RACE FASTEST LAP</div>
      <div class="value">{bestlap_str}</div>
      <div class="extra">{bestlap_vs_pole if bestlap else 'NO LAP DATA'}</div>
    </div>
    {progression_block}
  </div>
</div>

<div class="sec-head">
  <span class="num">01</span>
  <span class="title">FINAL CLASSIFICATION</span>
  <span class="sub">FINISH · DRIVER · TEAM · GRID · CHANGE</span>
</div>
<div class="classification">
  <table>
    <thead>
      <tr><th>POS</th><th>DRIVER</th><th>TEAM</th><th>GRID</th><th>Δ</th></tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</div>

<div class="foot">
  <span>CANADIAN GP RACE SUMMARY</span>
  <span class="red">●</span>
  <span>BUILT {build_ts}</span>
  <span class="pad"></span>
  <span>RUSSELL F1 POLE 2025 · <span class="red">{ms_to_str(F1_REF_MS)}</span></span>
</div>

</body></html>"""

    out = OUT_DIR / "race_summary.html"
    out.write_text(html, encoding='utf-8')
    return out

def main():
    race = load_race()
    if race is None:
        print("No race_out.json found. Run a race first.")
        return
    grid = load_grid_from_preset()
    items, bestlap, session_name, real_race = build_classification(race, grid)
    player = next((x for x in items if x["is_player"]), None) if items else None
    prog = update_history(player, bestlap, len(items), real_race)
    out = render(items, bestlap, session_name, real_race, prog)
    print(f"Wrote {out}")
    if items and player:
        finish = "DNF" if player["raw_finish"] == 0 else f"P{player['raw_finish']}"
        print(f"Player: {player['driver']} — {finish} (started P{player['grid']})")
    if prog and prog.get("previous") and prog.get("current"):
        cur, prev = prog["current"], prog["previous"]
        pos_d = prev["finish"] - cur["finish"]
        fl_d = (cur.get("fastest_lap_ms", 0) - prev.get("fastest_lap_ms", 0)) if prev.get("fastest_lap_ms") and cur.get("fastest_lap_ms") else None
        print(f"Race #{prog['race_number']}: {'+' if pos_d>0 else ''}{pos_d} pos vs P{prev['finish']}"
              + (f", FL {'-' if fl_d<0 else '+'}{ms_to_str(abs(fl_d))}" if fl_d is not None else ""))

if __name__ == "__main__":
    main()
