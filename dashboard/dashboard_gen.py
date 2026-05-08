#!/usr/bin/env python3
"""Hotlap dashboard generator — racing aesthetic.

Reads timestamped folders under telemetry_archive/ and writes:
  - <archive>/<TS>/report.html : self-contained per-session report
  - <archive>/dashboard.html   : latest session + history (always overwritten)

Run: python3 dashboard_gen.py
"""

import json
import os
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

# Max Verstappen — NLS 2 2026 reference
TARGET_POLE_MS = 471751   # 7:51.751 — pole, hot-lap target
TARGET_RACE_MS = 479268   # 7:59.268 — race best, stint pace target
RACE_START = date(2026, 5, 14)
RACE_END = date(2026, 5, 17)

# This dashboard renders the 24h Nürburgring narrative — Mercer V8 GT3 at
# Nordschleife endurance_cup. Sessions for other combos (e.g. the Super GT
# Fuji Chase side project) are archived for telemetry but excluded here so
# they don't pollute the race-week story. The HUD's combo_targets.json
# covers in-session deltas for those combos instead.
PRIMARY_CAR = "rss_gtm_mercer_v8"
PRIMARY_TRACK = "ks_nordschleife"

AC_DOC = Path(os.environ.get(
    "AC_DOC",
    "/mnt/c/Users/pablo/Documents/Assetto Corsa",
))
ARCHIVE_DIR = AC_DOC / "telemetry_archive"
ASSETS_DIR = ARCHIVE_DIR / "assets"


# ----------------------------------------------------------------------------- helpers

def ms_to_str(ms):
    if ms is None or ms <= 0:
        return "—"
    s = ms / 1000.0
    m = int(s // 60)
    s = s - m * 60
    return "{0}:{1:06.3f}".format(m, s)


def _fmt_secs(ms, signed=True):
    if ms is None:
        return "?"
    if not signed:
        return "{0:.3f}".format(abs(ms) / 1000.0)
    sign = "+" if ms >= 0 else "−"
    return "{0}{1:.3f}".format(sign, abs(ms) / 1000.0)


def _race_countdown_short():
    today = date.today()
    if today < RACE_START:
        d = (RACE_START - today).days
        return "{0} days to 24h Nürburgring".format(d)
    if today <= RACE_END:
        return "24h Nürburgring — LIVE NOW"
    return "after 24h Nürburgring 2026"


# ----------------------------------------------------------------------------- parse

def parse_session(folder):
    data = {
        "folder_name": folder.name,
        "folder_path": folder,
        "date": folder.name,
        "date_pretty": None,
        "player_name": None,
        "car": None,
        "track": None,
        "tyre": None,
        "laps": [],
        "best_lap_idx": None,
        "best_lap_ms": None,
        "worst_lap_ms": None,
        "pb_combo_ms": None,
    }
    m = re.match(r"(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})", folder.name)
    if m:
        y, mo, d, h, mi, s = m.groups()
        data["date_pretty"] = "{0}-{1}-{2} {3}:{4}:{5}".format(y, mo, d, h, mi, s)

    rout = folder / "race_out.json"
    if rout.exists():
        try:
            r = json.loads(rout.read_text())
            data["track"] = r.get("track")
            players = r.get("players") or []
            if players:
                data["car"] = players[0].get("car")
                data["player_name"] = players[0].get("name")
            sessions = r.get("sessions") or []
            if sessions:
                sess = sessions[0]
                for L in sess.get("laps", []):
                    data["laps"].append({
                        "lap": L.get("lap"),
                        "sectors": L.get("sectors", []),
                        "time": L.get("time"),
                        "cuts": L.get("cuts", 0),
                        "tyre": L.get("tyre", ""),
                    })
                if sess.get("bestLaps"):
                    bl = sess["bestLaps"][0]
                    data["best_lap_ms"] = bl.get("time")
                    data["best_lap_idx"] = bl.get("lap")
                if data["laps"]:
                    data["tyre"] = data["laps"][0]["tyre"]
                    times = [L["time"] for L in data["laps"] if L.get("time")]
                    if times:
                        data["worst_lap_ms"] = max(times)
        except Exception as e:
            print("WARN parse {0}: {1}".format(rout, e), file=sys.stderr)

    pb = folder / "personalbest.ini"
    if pb.exists():
        try:
            for line in pb.read_text().splitlines():
                if line.startswith("TIME="):
                    data["pb_combo_ms"] = int(line.split("=", 1)[1])
                    break
        except Exception:
            pass
    return data


def _is_primary_combo(s):
    """Filter sessions to the 24h Nürburgring narrative. Other combos (Fuji
    chase, Miami / Montreal F1 chases) are archived for telemetry but skipped
    in this dashboard."""
    car = (s.get("car") or "").lower()
    track = (s.get("track") or "").lower()
    if not car and not track:
        return True  # legacy archives without race_out.json — keep
    return PRIMARY_CAR in car and PRIMARY_TRACK in track


def find_sessions():
    if not ARCHIVE_DIR.exists():
        return []
    raw = []
    for entry in sorted(ARCHIVE_DIR.iterdir()):
        if entry.is_dir() and re.match(r"\d{8}-\d{6}", entry.name):
            raw.append(parse_session(entry))
    by_fp = {}
    for s in raw:
        if not s["laps"]:
            continue
        if not _is_primary_combo(s):
            continue
        fp = tuple(L.get("time") for L in s["laps"])
        by_fp[fp] = s
    return sorted(by_fp.values(), key=lambda x: x["date"])


# ----------------------------------------------------------------------------- visuals

def render_ticker():
    """Top black ticker stripe with checkered tail — pure motorsport."""
    today = date.today().strftime("%a %d %b %Y").upper()
    days = (RACE_START - date.today()).days
    return (
        '<div class="ticker">'
        '<div class="ticker-l">CHASING MAX · NORDSCHLEIFE · MERCER V8 GT3 · {today}</div>'
        '<div class="ticker-r">T-MINUS {d} DAYS</div>'
        '</div>'
    ).format(today=today, d=max(0, days))


def render_hero(latest, history):
    """Pit-board masthead: huge condensed name, blocky labels, timing-tower PB."""
    name = (latest.get("player_name") or "Pablo Suzarte").upper()
    pb = latest["best_lap_ms"]
    pole_gap = (pb - TARGET_POLE_MS) if pb else None
    race_gap = (pb - TARGET_RACE_MS) if pb else None
    return (
        '<header class="hero">'
        '<div class="hero-grid">'
        '  <div class="hero-left">'
        '    <div class="kicker"><span class="pos">#33</span>VERSTAPPEN RACING · DRIVER REPORT</div>'
        '    <h1 class="driver-name">{name}</h1>'
        '    <div class="chasing">CHASING <span class="max">MAX VERSTAPPEN</span></div>'
        '    <div class="race-strip">'
        '      <span class="countdown">{countdown}</span>'
        '      <span class="race-when">14–17 MAY · NÜRBURGRING</span>'
        '    </div>'
        '  </div>'
        '  <div class="hero-right">'
        '    <div class="hero-pb-label">PERSONAL BEST · MERCER V8 GT3</div>'
        '    <div class="hero-pb mono">{pb}</div>'
        '    <div class="hero-pb-meta">SET ACROSS <strong>{nlaps}</strong> LAPS · <strong>{nsess}</strong> SESSION{ps}</div>'
        '    <div class="hero-gap-row">'
        '      <div class="gap-cell"><span class="gap-num mono">{dp}</span><span class="gap-lbl">vs Max · Pole 7:51.751</span></div>'
        '      <div class="gap-cell"><span class="gap-num mono">{dr}</span><span class="gap-lbl">vs Max · Race 7:59.268</span></div>'
        '    </div>'
        '  </div>'
        '</div>'
        '</header>'
    ).format(
        name=escape(name),
        countdown=escape(_race_countdown_short().upper()),
        pb=ms_to_str(pb),
        nlaps=sum(len(s["laps"]) for s in history),
        nsess=len(history),
        ps="" if len(history) == 1 else "S",
        dp=_fmt_secs(pole_gap),
        dr=_fmt_secs(race_gap),
    )


def render_gap_ladder(latest):
    """Horizontal scale: where you sit between Max's pole, race-best, and your worst lap.
    SVG-driven so it scales cleanly."""
    pb = latest["best_lap_ms"]
    worst = latest.get("worst_lap_ms") or pb
    if not pb:
        return ""
    # Range: from Max's pole to user's worst (or +5s past PB, whichever larger)
    left = TARGET_POLE_MS
    right = max(worst, pb + 5000)
    span = right - left
    if span <= 0:
        return ""

    def pct(ms):
        return max(0.0, min(100.0, (ms - left) / span * 100.0))

    pole_x = pct(TARGET_POLE_MS)
    race_x = pct(TARGET_RACE_MS)
    pb_x = pct(pb)
    worst_x = pct(worst)

    # The "gap to find" is the colored band between race-best and your PB
    gap_w = pb_x - race_x  # if pb > race, positive width

    return (
        '<section class="section ladder">'
        '  <div class="section-head">'
        '    <div class="section-eyebrow">Stint 01</div>'
        '    <h2 class="section-title">The Climb</h2>'
        '  </div>'
        '  <p class="section-deck">Your PB plotted on the timing line — from <em>Max\'s pole</em> on the left to your slowest lap on the right. The hatched red zone is the gap left to close.</p>'
        '  <div class="ladder-scale">'
        '    <div class="ladder-fill" style="left:{rx}%;width:{gw}%"></div>'
        '    <div class="ladder-mark mark-pole" style="left:{px}%">'
        '      <div class="mark-line"></div>'
        '      <div class="mark-label">Max · Pole</div>'
        '      <div class="mark-time mono">{pt}</div>'
        '    </div>'
        '    <div class="ladder-mark mark-race" style="left:{rx}%">'
        '      <div class="mark-line"></div>'
        '      <div class="mark-label">Max · Race</div>'
        '      <div class="mark-time mono">{rt}</div>'
        '    </div>'
        '    <div class="ladder-mark mark-pb" style="left:{bx}%">'
        '      <div class="mark-line"></div>'
        '      <div class="mark-label">You · PB</div>'
        '      <div class="mark-time mono">{bt}</div>'
        '    </div>'
        '    <div class="ladder-mark mark-worst" style="left:{wx}%">'
        '      <div class="mark-line"></div>'
        '      <div class="mark-label">Slowest</div>'
        '      <div class="mark-time mono">{wt}</div>'
        '    </div>'
        '  </div>'
        '  <p class="ladder-caption">The hatched zone is what stands between today and matching Max\'s 24h race best.</p>'
        '</section>'
    ).format(
        px=pole_x, rx=race_x, bx=pb_x, wx=worst_x, gw=max(0, gap_w),
        pt=ms_to_str(TARGET_POLE_MS),
        rt=ms_to_str(TARGET_RACE_MS),
        bt=ms_to_str(pb),
        wt=ms_to_str(worst),
    )


def render_sector_battle(s):
    """Per-lap horizontal stacked bars where each lap is split into S1/S2/S3
    with widths proportional to actual sector times. Each segment colored by
    its rank against the best in that sector this session."""
    laps = [L for L in s["laps"] if len(L.get("sectors", [])) >= 3]
    if not laps:
        return ""

    # Best sector across the session for each of S1, S2, S3
    bests = [min(L["sectors"][i] for L in laps) for i in range(3)]
    # Worst lap total — used to scale the bar widths so the longest lap is full width
    worst_total = max(L["time"] for L in laps)

    def seg_class(actual, best):
        d = actual - best
        if d <= 50:
            return "seg-best"
        if d <= 300:
            return "seg-good"
        if d <= 700:
            return "seg-mid"
        return "seg-bad"

    rows = []
    for i, L in enumerate(laps):
        secs = L["sectors"]
        total = L["time"]
        is_best_lap = (i == s["best_lap_idx"])
        # Each segment width as a percentage of the LAP total — so segments inside
        # one bar always sum to 100%. Bar width itself is proportional to lap total.
        bar_width = (total / worst_total) * 100.0
        seg_widths = [secs[k] / total * 100.0 for k in range(3)]
        seg_html = []
        for k in range(3):
            cls = seg_class(secs[k], bests[k])
            sec_label = "S{0}".format(k + 1)
            seg_html.append(
                '<div class="seg {cls}" style="width:{w}%">'
                '<span class="seg-name">{sn}</span>'
                '<span class="seg-time">{t}</span>'
                '</div>'.format(
                    cls=cls, w=seg_widths[k], sn=sec_label,
                    t=ms_to_str(secs[k]),
                )
            )
        gap_to_pole = total - TARGET_POLE_MS
        gap_to_race = total - TARGET_RACE_MS
        row_cls = "lap-row" + (" lap-best" if is_best_lap else "")
        rows.append(
            '<div class="{rc}">'
            '  <div class="lap-num">L{n}</div>'
            '  <div class="bar-wrap">'
            '    <div class="bar" style="width:{bw}%">{segs}</div>'
            '  </div>'
            '  <div class="lap-totals">'
            '    <div class="lap-total">{lt}</div>'
            '    <div class="lap-gaps"><span class="gp">{gp}</span> pole · <span class="gr">{gr}</span> race</div>'
            '  </div>'
            '</div>'.format(
                rc=row_cls, n=(L.get("lap", i) or 0) + 1,
                bw=bar_width, segs="".join(seg_html), lt=ms_to_str(total),
                gp=_fmt_secs(gap_to_pole), gr=_fmt_secs(gap_to_race),
            )
        )

    # Theoretical optimum row at the bottom
    t_opt = sum(bests)
    opt_widths = [bests[k] / t_opt * 100.0 for k in range(3)]
    opt_segs = "".join(
        '<div class="seg seg-best" style="width:{w}%">'
        '<span class="seg-name">S{n}</span>'
        '<span class="seg-time">{t}</span>'
        '</div>'.format(w=opt_widths[k], n=k + 1, t=ms_to_str(bests[k]))
        for k in range(3)
    )
    opt_bar_width = (t_opt / worst_total) * 100.0
    opt_row = (
        '<div class="lap-row lap-opt">'
        '  <div class="lap-num">OPT</div>'
        '  <div class="bar-wrap">'
        '    <div class="bar" style="width:{bw}%">{segs}</div>'
        '  </div>'
        '  <div class="lap-totals">'
        '    <div class="lap-total">{lt}</div>'
        '    <div class="lap-gaps">your best of every sector combined</div>'
        '  </div>'
        '</div>'.format(bw=opt_bar_width, segs=opt_segs, lt=ms_to_str(t_opt))
    )

    return (
        '<section class="section battle">'
        '  <div class="section-head">'
        '    <div class="section-eyebrow">Stint 02</div>'
        '    <h2 class="section-title">Sector Tower</h2>'
        '  </div>'
        '  <p class="section-deck">One row per lap. <em>Width</em> = how much of the lap each sector cost. <em>Colour</em> = F1 timing convention — purple is the session best in that sector, green is improving, yellow is slower than your best, red is regressed.</p>'
        '  <div class="battle-meta">'
        '    <div class="legend">'
        '      <span class="lg lg-best">PURPLE · session best</span>'
        '      <span class="lg lg-good">GREEN · within 0.3s</span>'
        '      <span class="lg lg-mid">YELLOW · within 0.7s</span>'
        '      <span class="lg lg-bad">RED · slower</span>'
        '    </div>'
        '  </div>'
        '  <div class="bars">{rows}{opt}</div>'
        '</section>'
    ).format(rows="".join(rows), opt=opt_row)


def render_punch(s, history):
    """One-paragraph punch line. Replaces the old chatty narrative."""
    laps = s["laps"]
    if not laps:
        return ""
    best = s["best_lap_ms"]
    first_t = laps[0].get("time")
    n = len(laps)
    pb_before = None
    idx = next((i for i, x in enumerate(history) if x["date"] == s["date"]), None)
    if idx is not None and idx > 0:
        prevs = [x["best_lap_ms"] for x in history[:idx] if x["best_lap_ms"]]
        if prevs:
            pb_before = min(prevs)

    bits = []
    if best:
        race_gap = best - TARGET_RACE_MS
        if race_gap > 0:
            bits.append("you\'re <strong>{0}s</strong> behind Max\'s race best".format(_fmt_secs(race_gap, signed=False)))
        else:
            bits.append("you\'re <strong>{0}s</strong> under Max\'s race best".format(_fmt_secs(abs(race_gap), signed=False)))
    if first_t and best and best < first_t:
        bits.append("dropped <strong>{0}s</strong> across {1} laps".format(_fmt_secs(first_t - best, signed=False), n))
    if pb_before and best and best < pb_before:
        bits.append("new PB by <strong>{0}s</strong>".format(_fmt_secs(pb_before - best, signed=False)))

    if not bits:
        return ""
    sentence = " · ".join(bits)
    return '<div class="punch">{0}.</div>'.format(sentence)


def render_strategy(s):
    """Action checklist — the prescriptive bit."""
    laps = s["laps"]
    if not laps:
        return ""
    actions = []

    # Tire warm-up — always relevant for Hard at Nord
    if (s.get("tyre") or "").upper().startswith("H"):
        actions.append({
            "title": "WARM UP 2 LAPS @ 90%",
            "body": "Hard tyres run hot at Nord. Don\'t hot-lap on cold rubber.",
        })

    sl_pairs = [(i, L["sectors"]) for i, L in enumerate(laps) if len(L.get("sectors", [])) >= 3]
    n = len(sl_pairs)
    names = ["S1", "S2", "S3"]
    for si in range(3):
        if n < 2:
            continue
        times = [p[1][si] for p in sl_pairs]
        best_in = min(times)
        best_pos = times.index(best_in)
        best_lap_num = sl_pairs[best_pos][0] + 1
        regression = times[-1] - best_in
        improvement = times[0] - best_in
        best_is_recent = best_pos >= n - 2
        if (not best_is_recent) and regression >= 500:
            actions.append({
                "title": "REPEAT {0} FROM LAP {1}".format(names[si], best_lap_num),
                "body": "Your fastest {0} was {1}; now you\'re at {2} (+{3}s slower). Run 5 laps trying to rebuild that line.".format(
                    names[si], ms_to_str(best_in), ms_to_str(times[-1]), _fmt_secs(regression, signed=False)),
            })
        elif best_is_recent and improvement >= 1000:
            actions.append({
                "title": "PUSH {0} HARDER".format(names[si]),
                "body": "Found {0}s in {1} this session and your best was your most recent lap. Try a brake-later point — there\'s more here.".format(
                    _fmt_secs(improvement, signed=False), names[si]),
            })

    # Realistic next-session target
    sl = [L["sectors"] for L in laps if len(L.get("sectors", [])) >= 3]
    if sl and s["best_lap_ms"]:
        t_opt = sum(min(sec[i] for sec in sl) for i in range(3))
        target = s["best_lap_ms"] - (s["best_lap_ms"] - t_opt) // 2
        if target < s["best_lap_ms"] - 200:
            actions.append({
                "title": "TARGET {0}".format(ms_to_str(target)),
                "body": "Halfway to your own optimum ({0}). Don\'t hunt new pace — link the sectors you already have.".format(ms_to_str(t_opt)),
            })

    today = date.today()
    d = (RACE_START - today).days
    if d > 0:
        if d <= 5:
            actions.append({"title": "{0} DAYS — STOP CHASING PBs".format(d), "body": "Run 10+ lap stints. Tyre management and consistency now matter more than peak pace."})
        elif d <= 10:
            actions.append({"title": "{0} DAYS TO RACE".format(d), "body": "2/3 hot laps, 1/3 long stints. Practice race starts and pit sequences."})
        else:
            actions.append({"title": "{0} DAYS — PACE-FINDING PHASE".format(d), "body": "Goal this week: drop the PB another 5 s. No consistency drills until you\'re inside 8:10."})

    if not actions:
        return ""
    items = "".join(
        '<div class="action"><div class="act-content">'
        '<div class="act-title">{t}</div>'
        '<div class="act-body">{b}</div>'
        '</div></div>'.format(t=escape(a["title"]), b=a["body"]) for a in actions
    )
    return (
        '<section class="section strategy">'
        '  <div class="section-head">'
        '    <div class="section-eyebrow">Stint 03</div>'
        '    <h2 class="section-title">Pit-Board Orders</h2>'
        '  </div>'
        '  <p class="section-deck">Numbered, prioritised — drive the list top to bottom next session. Not goals; <em>actions</em>.</p>'
        '  <div class="actions">{0}</div>'
        '</section>'
    ).format(items)


def render_telemetry_promise():
    """Honest placeholder for what the dashboard will get when telemetry is wired."""
    return (
        '<aside class="promise">'
        '  <div class="promise-eyebrow">Forthcoming</div>'
        '  <h3 class="promise-title">A telemetry chapter.</h3>'
        '  <p class="promise-body">'
        '    Brake-point markers, throttle &amp; speed traces overlaid corner-by-corner, '
        '    and per-corner coaching ("brake 5 m later at <em>Schwedenkreuz</em>") drop in here once '
        '    AIM RaceStudio CSV is exported, or the CMRT <code>.lap</code> parser ships.'
        '  </p>'
        '</aside>'
    )


def render_history(history):
    """Race-classification table. Position number prefix per row."""
    rows = []
    prev = None
    pos = 1
    for s in history:
        b = s["best_lap_ms"]
        if not b:
            continue
        d_prev = (b - prev) if prev else None
        if d_prev is None:
            d_str = "—"
            d_cls = ""
        else:
            d_str = _fmt_secs(d_prev)
            d_cls = "good" if d_prev < 0 else "bad" if d_prev > 0 else "mid"
        rows.append(
            '<div class="hist-row">'
            '  <div class="hist-pos mono">{pos:02d}</div>'
            '  <div class="hist-date">{date}</div>'
            '  <div class="hist-best">{best}</div>'
            '  <div class="hist-gap">{gp}</div>'
            '  <div class="hist-prev {cls}">{dp}</div>'
            '</div>'.format(
                pos=pos,
                date=escape(s.get("date_pretty") or s["date"]),
                best=ms_to_str(b),
                gp=_fmt_secs(b - TARGET_POLE_MS),
                cls=d_cls, dp=d_str,
            )
        )
        prev = b
        pos += 1
    if not rows:
        return ""
    return (
        '<section class="section history">'
        '  <div class="section-head">'
        '    <div class="section-eyebrow">Classification</div>'
        '    <h2 class="section-title">The Logbook</h2>'
        '  </div>'
        '  <p class="section-deck">Every archived session, ordered. Last column flags whether the PB moved forward or back.</p>'
        '  <div class="hist-head">'
        '    <div>SESS</div><div>WHEN</div><div>BEST</div><div>vs MAX POLE</div><div>vs PREV</div>'
        '  </div>'
        '  <div class="hist-rows">{0}</div>'
        '</section>'
    ).format("".join(rows))


# ----------------------------------------------------------------------------- assets

DASHBOARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@500;600;700;800;900&family=Saira:wght@400;500;600;700&family=Saira+Condensed:wght@500;600;700&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

:root{
  /* press-kit light palette */
  --paper:#f4f4f2;        /* press-release stock */
  --surface:#ffffff;      /* card surface */
  --ink:#0a0a0a;          /* primary type */
  --ink-2:#2a2a2a;
  --ink-3:#5a5a5a;
  --ink-4:#8a8a8a;
  --rule-hair:#d4d4d2;    /* light divider */
  --rule:#0a0a0a;         /* HARD black rules — racing graphic */
  --rule-2:#4a4a4a;

  /* Verstappen / Red Bull livery accents */
  --max:#D40E10;          /* F1 / Verstappen red */
  --bull:#1E2761;         /* Red Bull navy */
  --caution:#FFC700;      /* caution yellow */
  /* F1-timing sector logic */
  --t-best:#6E3AFF;       /* PURPLE — fastest of session in that sector */
  --t-pb:#00A848;         /* GREEN — personal best (improving) */
  --t-mid:#C8A632;        /* YELLOW — slower than PB */
  --t-bad:#A32218;        /* RED — regressed */

  /* type scale */
  --display: 'Big Shoulders Display', 'Oswald', 'Impact', sans-serif;
  --condensed: 'Saira Condensed', 'Oswald', sans-serif;
  --body: 'Saira', -apple-system, 'Segoe UI', sans-serif;
  --mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
}

*{box-sizing:border-box;-webkit-font-smoothing:antialiased}
html{background:var(--paper)}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 var(--body);text-rendering:optimizeLegibility;padding:0;max-width:none;background-image:radial-gradient(circle at 1px 1px,rgba(10,10,10,0.05) 1px,transparent 0);background-size:24px 24px}
.wrap{max-width:1320px;margin:0 auto;padding:0 28px 80px}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums lining-nums}

/* ====== TOP TICKER STRIPE — pure motorsport graphic ====== */
.ticker{background:var(--ink);color:var(--paper);font:700 11px/1 var(--condensed);letter-spacing:2.5px;text-transform:uppercase;padding:9px 28px;display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid var(--max);position:relative;overflow:hidden}
.ticker::before{content:"";position:absolute;top:0;bottom:0;right:-2px;width:240px;background:repeating-linear-gradient(90deg,var(--max) 0,var(--max) 12px,var(--ink) 12px,var(--ink) 24px);opacity:0.95}
.ticker-l,.ticker-r{position:relative;z-index:1}
.ticker-r{background:var(--max);padding:9px 18px;margin:-9px -28px -9px 0;color:#fff;letter-spacing:2px}

/* ====== HERO — pit board ====== */
.hero{padding:34px 0 0;margin-bottom:48px;position:relative;border-bottom:3px solid var(--ink)}
.hero-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:48px;align-items:end}
.hero-left .kicker{font:700 11px/1 var(--condensed);letter-spacing:3px;text-transform:uppercase;color:var(--max);margin-bottom:10px}
.kicker .pos{display:inline-block;background:var(--ink);color:#fff;padding:3px 8px 2px;margin-right:10px;letter-spacing:1.5px}
.driver-name{font:900 110px/0.85 var(--display);letter-spacing:-2px;text-transform:uppercase;color:var(--ink);margin:0;font-stretch:condensed;font-feature-settings:"ss01"}
.chasing{font:600 18px/1.3 var(--condensed);text-transform:uppercase;letter-spacing:1.5px;color:var(--ink-2);margin:14px 0 18px}
.chasing .max{display:inline-block;background:var(--max);color:#fff;padding:3px 9px 1px;margin-left:4px;font-weight:800;letter-spacing:2px}
.race-strip{display:inline-flex;align-items:center;gap:0;font:700 11px/1 var(--condensed);letter-spacing:2px;text-transform:uppercase;color:var(--ink);border:2px solid var(--ink);padding:0}
.race-strip .countdown{padding:8px 12px;background:var(--caution);color:var(--ink)}
.race-strip .race-when{padding:8px 12px}

/* hero PB block — timing tower */
.hero-right{border-left:3px solid var(--ink);padding:0 0 0 36px;position:relative}
.hero-right::before{content:"P1 · YOUR PB";position:absolute;left:36px;top:-22px;font:800 10px/1 var(--condensed);letter-spacing:3px;color:var(--paper);background:var(--ink);padding:5px 10px}
.hero-pb-label{font:600 11px/1 var(--condensed);letter-spacing:2px;text-transform:uppercase;color:var(--ink-3);margin:0 0 6px}
.hero-pb{font:800 116px/0.85 var(--mono);font-variant-numeric:tabular-nums lining-nums;color:var(--ink);letter-spacing:-5px;margin:0}
.hero-pb-meta{font:500 12px/1.3 var(--condensed);letter-spacing:1px;text-transform:uppercase;color:var(--ink-3);margin-top:10px;border-top:1px solid var(--rule-hair);padding-top:10px}
.hero-pb-meta strong{color:var(--ink);font-weight:700}
.hero-gap-row{display:flex;gap:0;margin-top:18px;border:2px solid var(--ink);background:#fff}
.gap-cell{flex:1;padding:12px 14px;border-right:2px solid var(--ink)}
.gap-cell:last-child{border-right:none}
.gap-num{font:800 28px/1 var(--mono);font-variant-numeric:tabular-nums lining-nums;color:var(--max);letter-spacing:-1px;display:block}
.gap-lbl{font:600 9.5px/1.3 var(--condensed);text-transform:uppercase;letter-spacing:1.5px;color:var(--ink-3);margin-top:5px}

/* ====== SECTIONS — race-program style ====== */
.section{margin:0 0 56px;position:relative}
.section-head{display:flex;align-items:flex-end;justify-content:space-between;border-bottom:3px double var(--ink);padding-bottom:8px;margin-bottom:24px;gap:16px}
.section-eyebrow{font:800 10px/1 var(--condensed);letter-spacing:3px;text-transform:uppercase;color:#fff;background:var(--max);padding:4px 9px 3px;align-self:flex-start;margin-top:6px}
.section-title{font:900 48px/0.95 var(--display);letter-spacing:-1px;text-transform:uppercase;color:var(--ink);margin:0;flex:1;padding-left:18px}
.section-deck{font:500 14px/1.5 var(--body);color:var(--ink-2);margin:0 0 24px;max-width:78ch}
.section-deck em{font-style:italic;color:var(--max);font-weight:600}

/* ====== LEDE PUNCH — like a pit-board callout ====== */
.punch{font:600 19px/1.45 var(--condensed);letter-spacing:0.3px;color:var(--ink);margin:0 0 48px;padding:18px 22px;background:#fff;border:2px solid var(--ink);border-left:8px solid var(--max);position:relative}
.punch::before{content:"DRIVER NOTE";position:absolute;top:-11px;left:14px;background:var(--ink);color:#fff;font:800 9px/1 var(--condensed);letter-spacing:2px;padding:4px 7px}
.punch strong{color:var(--max);font-weight:800}

/* ====== LADDER — track distance scale ====== */
.ladder-scale{position:relative;height:108px;margin:32px 60px 8px;background:repeating-linear-gradient(90deg,transparent 0,transparent 9.9%,rgba(10,10,10,0.06) 9.9%,rgba(10,10,10,0.06) 10%);padding-top:18px}
.ladder-scale::before{content:"";position:absolute;left:0;right:0;top:42px;height:4px;background:var(--ink)}
.ladder-scale::after{content:"";position:absolute;left:0;right:0;top:42px;height:4px;background:repeating-linear-gradient(90deg,#fff 0,#fff 6px,var(--ink) 6px,var(--ink) 12px);opacity:0;transition:opacity 0.3s}
.ladder-fill{position:absolute;top:38px;height:12px;background:repeating-linear-gradient(45deg,var(--max) 0,var(--max) 6px,#fff 6px,#fff 10px,var(--ink) 10px,var(--ink) 12px);border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);border-left:2px solid var(--ink);border-right:2px solid var(--ink)}
.ladder-mark{position:absolute;top:0;transform:translateX(-50%);text-align:center;width:140px}
.mark-line{position:absolute;left:50%;top:32px;width:2px;height:22px;transform:translateX(-50%);background:var(--ink)}
.mark-pole .mark-line{height:32px;top:24px;background:var(--t-pb);width:4px}
.mark-race .mark-line{height:28px;top:28px;background:var(--caution);width:4px}
.mark-pb .mark-line{height:38px;top:18px;background:var(--max);width:6px;box-shadow:0 0 0 2px var(--ink)}
.mark-worst .mark-line{background:var(--ink-4)}
.mark-label{font:800 10px/1 var(--condensed);letter-spacing:2px;text-transform:uppercase;color:var(--ink);margin-top:62px;padding:3px 6px;display:inline-block}
.mark-pole .mark-label{background:var(--t-pb);color:#fff}
.mark-race .mark-label{background:var(--caution);color:var(--ink)}
.mark-pb .mark-label{background:var(--max);color:#fff}
.mark-worst .mark-label{background:var(--ink-4);color:#fff}
.mark-time{font:700 14px/1.2 var(--mono);color:var(--ink);margin-top:6px;font-variant-numeric:tabular-nums lining-nums;letter-spacing:-0.5px}
.mark-pb .mark-time{font-size:18px;font-weight:800}
.ladder-caption{font:600 11px/1.5 var(--condensed);letter-spacing:1.3px;text-transform:uppercase;color:var(--ink-3);text-align:center;margin-top:14px}

/* ====== SECTOR BATTLE — F1 timing tower ====== */
.battle-meta{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:14px;border-bottom:2px solid var(--ink);padding-bottom:6px}
.legend{display:flex;gap:0;border:2px solid var(--ink)}
.lg{font:800 10px/1 var(--condensed);text-transform:uppercase;letter-spacing:1.5px;color:var(--ink);padding:7px 12px;border-right:2px solid var(--ink)}
.lg:last-child{border-right:none}
.lg-best{background:var(--t-best);color:#fff}
.lg-good{background:var(--t-pb);color:#fff}
.lg-mid{background:var(--t-mid);color:var(--ink)}
.lg-bad{background:var(--t-bad);color:#fff}

.bars{display:flex;flex-direction:column;border:2px solid var(--ink);background:#fff}
.lap-row{display:grid;grid-template-columns:54px 1fr 200px;align-items:stretch;border-bottom:1px solid var(--ink-4)}
.lap-row:last-child{border-bottom:none}
.lap-best{background:#fffceb}
.lap-best .lap-num{background:var(--max);color:#fff}
.lap-opt{border-top:3px double var(--ink);background:#f3eeff}
.lap-opt .lap-num{background:var(--t-best);color:#fff}
.lap-num{font:800 18px/1 var(--mono);font-variant-numeric:tabular-nums lining-nums;color:#fff;background:var(--ink);text-align:center;letter-spacing:0;display:flex;align-items:center;justify-content:center}
.bar-wrap{position:relative;padding:8px 14px;border-left:2px solid var(--ink);border-right:2px solid var(--ink)}
.bar{display:flex;height:42px;border:1.5px solid var(--ink);overflow:hidden;background:#fff}
.seg{display:flex;align-items:center;justify-content:center;color:#fff;padding:0 10px;min-width:0;border-right:1.5px solid var(--ink);position:relative;flex-direction:column;gap:1px}
.seg:last-child{border-right:none}
.seg-name{font:800 9px/1 var(--condensed);letter-spacing:1.5px;text-transform:uppercase;opacity:0.9}
.seg-time{font:700 13px/1 var(--mono);font-variant-numeric:tabular-nums lining-nums;letter-spacing:-0.3px}
.seg-best{background:var(--t-best);color:#fff}
.seg-good{background:var(--t-pb);color:#fff}
.seg-mid{background:var(--t-mid);color:var(--ink)}
.seg-bad{background:var(--t-bad);color:#fff}
.lap-totals{padding:8px 14px;display:flex;flex-direction:column;justify-content:center;align-items:flex-end;text-align:right;gap:4px}
.lap-total{font:800 22px/1 var(--mono);color:var(--ink);letter-spacing:-1px;font-variant-numeric:tabular-nums lining-nums}
.lap-best .lap-total{color:var(--max)}
.lap-opt .lap-total{color:var(--t-best)}
.lap-gaps{font:600 10px/1.3 var(--condensed);text-transform:uppercase;letter-spacing:1px;color:var(--ink-3)}
.lap-gaps .gp,.lap-gaps .gr{color:var(--ink);font-family:var(--mono);font-weight:700;text-transform:none;font-variant-numeric:tabular-nums lining-nums;letter-spacing:0}

/* ====== STRATEGY — pit board action cards ====== */
.actions{display:grid;grid-template-columns:1fr;gap:0;border:2px solid var(--ink);background:#fff}
.action{counter-increment:action;display:grid;grid-template-columns:80px 1fr;gap:0;border-bottom:1px solid var(--ink-4);align-items:stretch}
.action:last-child{border-bottom:none}
.actions{counter-reset:action}
.action::before{content:counter(action,decimal-leading-zero);font:900 44px/1 var(--display);font-variant-numeric:lining-nums;color:#fff;background:var(--ink);display:flex;align-items:center;justify-content:center;letter-spacing:-2px;border-right:2px solid var(--ink);padding:18px 0}
.action:nth-child(odd)::before{background:var(--max)}
.act-content{padding:16px 20px;display:flex;flex-direction:column;gap:6px}
.act-title{font:800 13px/1.2 var(--condensed);letter-spacing:2px;text-transform:uppercase;color:var(--ink)}
.act-body{font:500 14.5px/1.55 var(--body);color:var(--ink-2)}

/* ====== TELEMETRY PROMISE ====== */
.promise{padding:24px;background:#fff;border:2px dashed var(--ink);position:relative;margin-bottom:48px}
.promise::before{content:"PIT IN — UPGRADE WAITING";position:absolute;top:-11px;left:18px;background:var(--caution);color:var(--ink);font:800 9px/1 var(--condensed);letter-spacing:2px;padding:4px 9px;border:2px solid var(--ink)}
.promise-eyebrow{font:800 10px/1 var(--condensed);letter-spacing:2.5px;text-transform:uppercase;color:var(--ink-3);margin-bottom:10px;padding-top:6px}
.promise-title{font:800 28px/1.05 var(--display);text-transform:uppercase;color:var(--ink);margin:0 0 12px;letter-spacing:-0.5px}
.promise-body{font:500 14px/1.6 var(--body);color:var(--ink-2);margin:0;max-width:64ch}
.promise code{background:var(--ink);color:#fff;padding:1px 6px;font:700 12px/1 var(--mono)}
.promise em{color:var(--max);font-style:normal;font-weight:700;text-transform:uppercase}

/* ====== HISTORY — race classification table ====== */
.history{padding:0}
.hist-head{display:grid;grid-template-columns:60px 1.6fr 1fr 1fr 1fr;font:800 10px/1 var(--condensed);letter-spacing:2px;text-transform:uppercase;color:#fff;background:var(--ink);padding:11px 14px}
.hist-head>div:not(:first-child):not(:nth-child(2)){text-align:right}
.hist-rows{border:2px solid var(--ink);border-top:none;background:#fff}
.hist-row{display:grid;grid-template-columns:60px 1.6fr 1fr 1fr 1fr;padding:12px 14px;border-bottom:1px solid var(--ink-4);align-items:center}
.hist-row:last-child{border-bottom:none}
.hist-row:nth-child(odd){background:#fafaf8}
.hist-row>div:not(:first-child):not(:nth-child(2)){text-align:right}
.hist-pos{font:800 14px/1 var(--mono);color:#fff;background:var(--ink);text-align:center;padding:4px 0;letter-spacing:-0.5px;width:36px}
.hist-date{font:600 13px/1.3 var(--condensed);letter-spacing:1px;text-transform:uppercase;color:var(--ink)}
.hist-best,.hist-gap,.hist-prev{font:700 16px/1.3 var(--mono);font-variant-numeric:tabular-nums lining-nums;color:var(--ink);letter-spacing:-0.3px}
.hist-prev.good{color:var(--t-pb)}
.hist-prev.bad{color:var(--t-bad)}
.hist-prev.mid{color:var(--t-mid)}

/* ====== RESPONSIVE ====== */
@media (max-width:1100px){
  .hero-grid{grid-template-columns:1fr;gap:40px}
  .hero-right{border-left:none;border-top:3px solid var(--ink);padding:36px 0 0}
  .hero-right::before{left:0;top:14px}
  .hero-pb{font-size:88px;letter-spacing:-3px}
  .driver-name{font-size:84px}
  .section-title{font-size:36px}
}
@media (max-width:700px){
  .wrap{padding:0 18px 60px}
  .ticker{padding:8px 18px}
  .ticker::before,.ticker-r{display:none}
  .driver-name{font-size:56px;letter-spacing:-1px}
  .hero-pb{font-size:60px;letter-spacing:-2px}
  .section-title{font-size:28px;padding-left:0}
  .ladder-scale{margin:24px 12px 8px;height:120px}
  .lap-row{grid-template-columns:42px 1fr;grid-auto-rows:auto}
  .lap-totals{grid-column:1 / -1;flex-direction:row;align-items:baseline;justify-content:space-between;border-top:1px solid var(--ink-4);padding-top:8px}
  .bar-wrap{border-right:none}
  .action{grid-template-columns:60px 1fr}
  .action::before{font-size:32px}
}

::selection{background:var(--max);color:#fff}
a:focus-visible,button:focus-visible{outline:3px solid var(--max);outline-offset:2px}
"""


def ensure_assets():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR / "dashboard.css").write_text(DASHBOARD_CSS)
    # Old chart.umd.min.js is no longer referenced; leave it on disk if present.


def render_html(title, body, asset_prefix):
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>'
        '<meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>{title}</title>'
        '<link rel="stylesheet" href="{ap}dashboard.css">'
        '</head><body>{body}</body></html>\n'
    ).format(title=escape(title), ap=asset_prefix, body=body)


def build_body(latest, history):
    return (
        render_ticker()
        + '<div class="wrap">'
        + render_hero(latest, history)
        + render_punch(latest, history)
        + render_gap_ladder(latest)
        + render_sector_battle(latest)
        + render_strategy(latest)
        + render_telemetry_promise()
        + render_history(history)
        + '</div>'
    )


def generate():
    sessions = find_sessions()
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_assets()

    # Clean stale per-session reports.
    for entry in ARCHIVE_DIR.iterdir():
        if entry.is_dir() and re.match(r"\d{8}-\d{6}", entry.name):
            stale = entry / "report.html"
            if stale.exists():
                stale.unlink()

    if not sessions:
        body = (
            '<div class="hero"><div class="hero-left">'
            '<div class="kicker">DRIVER · #33 VERSTAPPEN RACING</div>'
            '<div class="driver-name">Pablo Suzarte</div>'
            '<div class="chasing">no sessions archived yet</div>'
            '</div></div>'
            '<div class="card"><div class="card-title">GET STARTED</div>'
            '<div class="card-sub">Drive a session, then run <code>archive_telemetry.cmd</code>. '
            'Your dashboard fills in here.</div></div>'
        )
        (ARCHIVE_DIR / "dashboard.html").write_text(render_html("Hotlap Dashboard", body, "assets/"))
        print("No sessions; wrote empty dashboard.")
        return

    for i, s in enumerate(sessions):
        history = sessions[: i + 1]
        body = build_body(s, history)
        title = "Chasing Max · {0}".format(s.get("date_pretty") or s["date"])
        (s["folder_path"] / "report.html").write_text(render_html(title, body, "../assets/"))

    latest = sessions[-1]
    body = build_body(latest, sessions)
    out = ARCHIVE_DIR / "dashboard.html"
    out.write_text(render_html(
        "Chasing Max · latest {0}".format(latest.get("date_pretty") or latest["date"]),
        body, "assets/",
    ))
    print("Wrote dashboard for {0} session(s) -> {1}".format(len(sessions), out))


if __name__ == "__main__":
    generate()
