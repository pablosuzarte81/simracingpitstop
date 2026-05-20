#!/usr/bin/env python3
"""Post-race results aggregator.

Reads every snapshot in dashboard/results/snapshots/, matches each to the
correct dashboard tile by (car_model + track + config_track) using the CONFIGS
list from launcher_dashboard.py, and writes:

  dashboard/results/by_tile/<tile_id>.json   — most recent result per tile
  dashboard/results/index.json               — flat map { tile_id: latest_summary }

The dashboard's render_card reads index.json to show "last result" / "best
lap" on each race/duel/hotlap card.
"""
import json, pathlib, re, sys
from datetime import datetime

ROOT      = pathlib.Path(__file__).resolve().parent.parent
SNAPSHOTS = ROOT / "dashboard" / "results" / "snapshots"
BY_TILE   = ROOT / "dashboard" / "results" / "by_tile"
INDEX     = ROOT / "dashboard" / "results" / "index.json"
DASH_PY   = ROOT / "launcher" / "launcher_dashboard.py"

BY_TILE.mkdir(parents=True, exist_ok=True)


def load_configs():
    """Crude CONFIGS extractor — pulls the dict-list from launcher_dashboard.py."""
    src = DASH_PY.read_text(encoding='utf-8')
    out, in_block, depth, buf = [], False, 0, []
    for line in src.splitlines(keepends=True):
        if line.strip().startswith("CONFIGS = ["):
            in_block = True; continue
        if not in_block: continue
        if line.strip() == "]" and depth == 0: break
        depth += line.count("{") - line.count("}")
        buf.append(line)
        if line.strip() == "}," and depth == 0:
            block = "".join(buf); buf = []
            def grab(key):
                m = re.search(rf'"{key}":\s*"([^"]*)"', block)
                return m.group(1) if m else None
            cfg_id = grab("id")
            if not cfg_id: continue
            out.append({
                "id":               cfg_id,
                "type":             grab("type"),
                "title":            grab("title"),
                "ac_car_id":        grab("ac_car_id"),
                "ac_car_skin":      grab("ac_car_skin"),
                "ac_track_id":      grab("ac_track_id"),
                "ac_track_layout":  grab("ac_track_layout"),
            })
    return out


def fmt_ms(ms):
    if not ms: return None
    m, s = divmod(ms / 1000.0, 60)
    return f"{int(m)}:{s:06.3f}"


def summarize(snap):
    """Reduce a race_out.json snapshot to {track, car, skin, results, best_lap}."""
    track   = snap.get("track", "")
    players = snap.get("players", [])
    p0      = players[0] if players else {}
    car     = p0.get("car", "")
    skin    = p0.get("skin", "")
    name    = p0.get("name", "")
    sessions = snap.get("sessions", []) or []
    if not sessions:
        return {"track": track, "car": car, "skin": skin, "player": name}
    sess = sessions[0]
    laps = sess.get("laps", []) or []
    # best valid lap for the player (car_index 0)
    me_laps = [l for l in laps if l.get("car") == 0]
    valid = [l for l in me_laps if l.get("cuts", 0) == 0 and l.get("time")]
    best_lap = min(valid, key=lambda l: l["time"]) if valid else None
    sectors = best_lap.get("sectors") if best_lap else None
    finish = None
    rr = sess.get("raceResult") or []
    if rr:
        # raceResult[finish_idx] = grid_idx; find finish index where value == 0 (player car)
        try:
            finish = rr.index(0) + 1
        except ValueError:
            pass
    return {
        "track":       track,
        "car":         car,
        "skin":        skin,
        "player":      name,
        "session":     {"name": sess.get("name"), "type": sess.get("type")},
        "best_lap":    fmt_ms(best_lap["time"]) if best_lap else None,
        "best_lap_ms": best_lap["time"] if best_lap else None,
        "sectors":     [fmt_ms(s) for s in sectors] if sectors else None,
        "finish":      finish,
        "field":       len(players),
        "tyre":        best_lap.get("tyre") if best_lap else None,
    }


def match_tile(summary, configs):
    """Pick the tile whose ac_car_id + track combo matches this snapshot.
    Disambiguates by session type (TYPE 4=HOTLAP, TYPE 3=RACE/DUEL) and field
    size (2=DUEL, >2=RACE), so the duel result lands on the duel card and the
    hotlap on the hotlap card even when both share car+track+skin.
    """
    car   = summary.get("car", "")
    track = summary.get("track", "")  # e.g. "ks_nordschleife-endurance_cup"
    skin  = summary.get("skin", "")
    sess_type = (summary.get("session") or {}).get("type")
    field = summary.get("field") or 1

    candidates = []
    for c in configs:
        if c["ac_car_id"] != car: continue
        full_track = f"{c['ac_track_id']}-{c['ac_track_layout']}" if c['ac_track_id'] and c['ac_track_layout'] else None
        if full_track == track:
            candidates.append(c)
    if not candidates: return None

    # Filter by session type (AC: 4=Hotlap, 3=Race, 2=Qualify, 1=Practice)
    if sess_type == 4:
        type_ok = [c for c in candidates if c.get("type") == "HOTLAP"]
    elif sess_type == 3:
        if field <= 2:
            # 2-car race -> prefer DUEL, fall back to RACE
            type_ok = [c for c in candidates if c.get("type") == "DUEL"] \
                   or [c for c in candidates if c.get("type") == "RACE"]
        else:
            type_ok = [c for c in candidates if c.get("type") == "RACE"] \
                   or [c for c in candidates if c.get("type") == "DUEL"]
    else:
        type_ok = candidates
    if not type_ok:
        type_ok = candidates

    if len(type_ok) == 1:
        return type_ok[0]
    # Skin tiebreaker
    skin_matches = [c for c in type_ok if c.get("ac_car_skin") == skin]
    if skin_matches: return skin_matches[0]
    return type_ok[0]


def main():
    configs = load_configs()
    snapshots = sorted(SNAPSHOTS.glob("*.json"))
    if not snapshots:
        print("no snapshots to process")
        return

    by_tile = {}    # tile_id -> {ts, summary}
    for snap_path in snapshots:
        try:
            snap = json.loads(snap_path.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"skip {snap_path.name}: {e}")
            continue
        summary = summarize(snap)
        tile = match_tile(summary, configs)
        if not tile:
            print(f"no tile match for {snap_path.name}  car={summary.get('car')}  track={summary.get('track')}")
            continue
        ts = snap_path.stem  # yyyyMMdd-HHmmss
        cur = by_tile.get(tile["id"])
        # HOTLAP tiles: keep the snapshot with the BEST (lowest) valid lap.
        # RACE / DUEL tiles: keep the MOST RECENT result (current race outcome).
        # A new snapshot can only replace an existing PB on HOTLAP — slower
        # subsequent sessions never overwrite a faster lap.
        if tile.get("type") == "HOTLAP":
            new_ms = summary.get("best_lap_ms")
            cur_ms = (cur or {}).get("summary", {}).get("best_lap_ms")
            if new_ms is not None and (cur_ms is None or new_ms < cur_ms):
                by_tile[tile["id"]] = {"ts": ts, "tile": tile, "summary": summary, "snapshot_file": snap_path.name}
        else:
            if not cur or ts > cur["ts"]:
                by_tile[tile["id"]] = {"ts": ts, "tile": tile, "summary": summary, "snapshot_file": snap_path.name}

    # Write per-tile + index
    for tile_id, entry in by_tile.items():
        (BY_TILE / f"{tile_id}.json").write_text(json.dumps(entry, indent=2), encoding='utf-8')

    INDEX.write_text(json.dumps(by_tile, indent=2), encoding='utf-8')
    print(f"updated {len(by_tile)} tiles · {len(snapshots)} snapshots scanned")
    for tile_id, entry in sorted(by_tile.items()):
        s = entry["summary"]
        print(f"  {tile_id:38s}  ts={entry['ts']}  best={s.get('best_lap') or '—'}  finish=P{s.get('finish') or '—'}/{s.get('field')}")


if __name__ == "__main__":
    main()
