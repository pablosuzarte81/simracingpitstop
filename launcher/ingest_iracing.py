#!/usr/bin/env python3
"""Ingest iRacing official-result CSV exports into the Season 3 tracker.

Usage:
    python ingest_iracing.py ~/Downloads/eventresult_*.csv

Each eventresult_<subsession>_0.csv export has a two-row session header
(Start Time / Track / Series / Season / Race Week / SOF), a blank line, then
the per-driver result table. We pull Pablo's row (cust_id 587563), normalize
it, and merge it into launcher/iracing_s3.json (deduped by subsession_id,
sorted by date).

Notes that bit us before, kept here on purpose:
  * The CSV is 1-BASED. "Fin Pos" 4 means P4. (The JSON /data API is 0-based;
    that +1 rule does NOT apply to these CSVs.)
  * Safety Rating lives in "* License Sub-Level" as an integer ×100
    (266 -> 2.66). License *Level* is a separate field we don't decode to a
    letter here — current sports-car class is tracked on the page itself.
  * Fields are mapped BY HEADER NAME, never by index, because some rows come
    back with empty Div/Club columns that shift positional parsing.
"""
import csv
import json
import re
import sys
from pathlib import Path

CUST_ID = "587563"            # Pablo Suzarte
HERE = Path(__file__).resolve().parent
DATA_FILE = HERE / "iracing_s3.json"


def _int(v):
    v = (v or "").strip()
    try:
        return int(v)
    except ValueError:
        return None


def parse_csv(path: Path) -> dict:
    """Return one normalized race record from an eventresult CSV, or raise."""
    rows = list(csv.reader(path.read_text(encoding="utf-8-sig").splitlines()))
    if len(rows) < 4:
        raise ValueError(f"{path.name}: too few rows to be an eventresult export")

    meta = dict(zip(rows[0], rows[1]))

    # find the per-driver table header (row starting with "Fin Pos")
    hdr_idx = next(
        (i for i, r in enumerate(rows) if r and r[0].strip() == "Fin Pos"),
        None,
    )
    if hdr_idx is None:
        raise ValueError(f"{path.name}: could not find driver table header")
    header = [h.strip() for h in rows[hdr_idx]]

    me = None
    for r in rows[hdr_idx + 1:]:
        if not r:
            continue
        d = dict(zip(header, r))
        if d.get("Cust ID", "").strip() == CUST_ID:
            me = d
            break
    if me is None:
        raise ValueError(f"{path.name}: cust_id {CUST_ID} not in this result")

    m = re.search(r"eventresult_(\d+)", path.name)
    subsession = _int(m.group(1)) if m else None

    return {
        "subsession_id": subsession,
        "date":          meta.get("Start Time", "").strip(),
        "year":          meta.get("Season Year", "").strip(),
        "quarter":       meta.get("Season Quarter", "").strip(),
        "week":          meta.get("Race Week", "").strip(),
        "series":        meta.get("Series", "").strip(),
        "track":         meta.get("Track", "").strip(),
        "sof":           _int(meta.get("Strength of Field")),
        "car":           me.get("Car", "").strip(),
        "start_pos":     _int(me.get("Start Pos")),
        "finish_pos":    _int(me.get("Fin Pos")),
        "incidents":     _int(me.get("Inc")),
        "laps":          _int(me.get("Laps Comp")),
        "champ_pts":     _int(me.get("Pts")),
        "fastest_lap":   me.get("Fastest Lap Time", "").strip(),
        "status":        me.get("Out", "").strip(),
        "old_irating":   _int(me.get("Old iRating")),
        "new_irating":   _int(me.get("New iRating")),
        "old_sub":       _int(me.get("Old License Sub-Level")),
        "new_sub":       _int(me.get("New License Sub-Level")),
    }


def load_existing() -> list:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def main(argv):
    if not argv:
        print(__doc__)
        return 1

    races = {r["subsession_id"]: r for r in load_existing()}
    added, updated = 0, 0
    for arg in argv:
        path = Path(arg).expanduser()
        if not path.exists():
            print(f"skip (not found): {path}")
            continue
        try:
            rec = parse_csv(path)
        except ValueError as e:
            print(f"skip: {e}")
            continue
        sid = rec["subsession_id"]
        if sid in races:
            updated += 1
        else:
            added += 1
        races[sid] = rec
        ir = ""
        if rec["old_irating"] is not None and rec["new_irating"] is not None:
            ir = f"  iR {rec['old_irating']}->{rec['new_irating']}"
        print(f"  {rec['date']}  {rec['series']}  P{rec['finish_pos']}<-P{rec['start_pos']}"
              f"  {rec['incidents']}inc{ir}")

    merged = sorted(races.values(), key=lambda r: r["date"] or "")
    DATA_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"\nwrote {len(merged)} races -> {DATA_FILE}  (+{added} new, {updated} updated)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
