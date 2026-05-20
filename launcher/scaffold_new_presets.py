#!/usr/bin/env python3
"""Generate missing AC presets (.ini in cfg/) and .cmd launchers for any
catalog challenge whose launcher file doesn't yet exist on disk.

Run once:
    python3 scaffold_new_presets.py

Idempotent — skips files that already exist unless --force is passed.
"""

import os
import sys
from pathlib import Path

import launcher_dashboard as L

AC_DOC = Path(os.environ.get(
    "AC_DOC",
    "/mnt/c/Users/pablo/Documents/Assetto Corsa",
))
ACINSTALL_WIN = "F:\\SteamLibrary\\steamapps\\common\\assettocorsa"


# Per-challenge ambient/weather/time-of-day overrides keyed by challenge id.
# Defaults: dry, midday, 22°C / 32°C road, 0° sun angle.
CONDITIONS = {
    "senna_donington_1993": dict(
        weather="5_light_rain", ambient=12, road=14, sun_angle=-15,
        geotag=(52.831, -1.376), tz_offset=3600,
    ),
    "senna_suzuka_1988": dict(
        weather="3_clear", ambient=18, road=26, sun_angle=-25,
        geotag=(34.843, 136.541), tz_offset=32400,
    ),
    "senna_monaco_1988": dict(
        weather="3_clear", ambient=20, road=30, sun_angle=-15,
        geotag=(43.7347, 7.4206), tz_offset=3600,
    ),
    "senna_estoril_1985": dict(
        weather="5_light_rain", ambient=14, road=16, sun_angle=-12,
        geotag=(38.751, -9.394), tz_offset=0,
    ),
    "senna_vs_prost_monaco_1988": dict(
        weather="3_clear", ambient=20, road=30, sun_angle=-15,
        geotag=(43.7347, 7.4206), tz_offset=3600,
    ),
    "senna_vs_prost_suzuka_1988": dict(
        weather="3_clear", ambient=18, road=26, sun_angle=-25,
        geotag=(34.843, 136.541), tz_offset=32400,
    ),
    "senna_vs_schumacher_donington_1993": dict(
        weather="5_light_rain", ambient=12, road=14, sun_angle=-15,
        geotag=(52.831, -1.376), tz_offset=3600,
    ),
    "f1_2008_brazil_grid": dict(
        weather="3_clear", ambient=24, road=36, sun_angle=-12,
        geotag=(-23.701, -46.699), tz_offset=-10800,
    ),
    "dave_cam_audi_90_nordschleife": dict(
        weather="3_clear", ambient=18, road=24, sun_angle=-12,
        geotag=(50.336, 6.948), tz_offset=3600,
    ),
}


# Manual rival/opponent lists — for race / duel presets only.
# Each entry is (model, skin, driver_name, team, nationality, nation_code).
RIVALS = {
    "senna_vs_prost_monaco_1988": [
        ("vrc_1988_mclaren_mp4-4_r02", "11_Prost_R02", "Alain Prost",
         "Marlboro McLaren-Honda", "France", "FRA"),
    ],
    "senna_vs_prost_suzuka_1988": [
        ("vrc_1988_mclaren_mp4-4_r02", "11_Prost_R08", "Alain Prost",
         "Marlboro McLaren-Honda", "France", "FRA"),
    ],
    "senna_vs_schumacher_donington_1993": [
        ("f1_1993_benetton", "Schumacher", "Michael Schumacher",
         "Camel Benetton Ford", "Germany", "DEU"),
    ],
    # F1 2008 grid — Hamilton player + 11 rivals (one per team for now).
    # Pablo can expand to a full 22-car grid by adding more CAR_N entries
    # in Content Manager later.
    "f1_2008_brazil_grid": [
        ("cim_2008_ferrari",      "02_Massa",       "Felipe Massa",
         "Scuderia Ferrari Marlboro", "Brazil", "BRA"),
        ("cim_2008_bmw_sauber",   "Kubica",         "Robert Kubica",
         "BMW Sauber F1 Team", "Poland", "POL"),
        ("cim_2008_renault",      "05_Alonso",      "Fernando Alonso",
         "ING Renault F1 Team", "Spain", "ESP"),
        ("cim_2008_williams",     "07_Rosberg",     "Nico Rosberg",
         "AT&T Williams", "Germany", "DEU"),
        ("cim_2008_toyota",       "12_Glock",       "Timo Glock",
         "Panasonic Toyota Racing", "Germany", "DEU"),
        ("cim_2008_honda",        "16_Button",      "Jenson Button",
         "Honda Racing F1 Team", "Great Britain", "GBR"),
        ("cim_2008_redbull",      "10_Webber",      "Mark Webber",
         "Red Bull Racing", "Australia", "AUS"),
        ("cim_2008_tororosso",    "15_Vettel",      "Sebastian Vettel",
         "Scuderia Toro Rosso", "Germany", "DEU"),
        ("cim_2008_forceindia",   "21_Fisichella",  "Giancarlo Fisichella",
         "Force India F1 Team", "Italy", "ITA"),
        ("cim_2008_superaguri",   "18_Sato",        "Takuma Sato",
         "Super Aguri F1 Team", "Japan", "JPN"),
        ("cim_2008_mclaren",      "23_Kovalainen",  "Heikki Kovalainen",
         "Vodafone McLaren Mercedes", "Finland", "FIN"),
    ],
    # Recreate Dave Cam's iRacing P3 start: 5 GTO rivals named after the
    # iRacing drivers Dave mentioned in the video (Wilson on pole, Kenny P2,
    # Guillim P3 — player slots in ahead of Kenny). All Audi 90 GTOs, varied
    # skins from the ORS mod pack. Source: youtube.com/watch?v=DIl_vf5tdgE
    "dave_cam_audi_90_nordschleife": [
        ("audi_90_quattro_IMSA_gto_1989", "00_04_audi",        "Wilson",
         "Audi Sport · IMSA GTO", "Great Britain", "GBR"),
        ("audi_90_quattro_IMSA_gto_1989", "01_02_audi",        "Kenny",
         "Audi Sport · IMSA GTO", "Great Britain", "GBR"),
        ("audi_90_quattro_IMSA_gto_1989", "01_03_audi_america","Guillim",
         "Audi Sport · IMSA GTO", "Spain", "ESP"),
        ("audi_90_quattro_IMSA_gto_1989", "01_05_audi",        "Lucas",
         "Audi Sport · IMSA GTO", "France", "FRA"),
        ("audi_90_quattro_IMSA_gto_1989", "02_a6_audi_trans_am","Javier",
         "Audi Sport · IMSA GTO", "Spain", "ESP"),
    ],
}


HOTLAP_TEMPLATE = """; {comment}
; Generated by scaffold_new_presets.py.

[HEADER]
VERSION=2
__CM_FEATURE_SET=2

[RACE]
TRACK={track}
CONFIG_TRACK={layout}
MODEL={car}
MODEL_CONFIG=
CARS=1
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=0
SKIN={skin}
DRIFT_MODE=0
RACE_LAPS=0
JUMP_START_PENALTY=0
AI_AGGRESSION=0
RACE_GAS_PENALTY_DISABLED=0
OPPONENTS_VARIETY=0
__CM_WEATHER_TYPE=-1
__CM_WEATHER_CONTROLLER=base
__TRACK_GEOTAG_LAT={lat}
__TRACK_GEOTAG_LONG={lon}
__TRACK_TIMEZONE_BASE_OFFSET={tz}
__TRACK_TIMEZONE_OFFSET={tz}
__TRACK_TIMEZONE_DTS=0

[OPTIONS]
USE_MPH=0

[LAP_INVALIDATOR]
ALLOWED_TYRES_OUT=-1

[TEMPERATURE]
AMBIENT={ambient}
ROAD={road}

[WEATHER]
NAME={weather}

[LIGHTING]
SUN_ANGLE={sun_angle:.2f}
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

[WIND]
SPEED_KMH_MIN=0
SPEED_KMH_MAX=0
DIRECTION_DEG=0

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

[BENCHMARK]
ACTIVE=0

[RESTART]
ACTIVE=0

[__PREVIEW_GENERATION]
ACTIVE=0

[SESSION_0]
NAME=Hotlap
TYPE=4
DURATION_MINUTES=0
SPAWN_SET=HOTLAP_START

[CAR_0]
SETUP=
SKIN={skin}
MODEL=-
MODEL_CONFIG=
DRIVER_NAME={driver_name}
NATIONALITY={nationality}
NATION_CODE={nation_code}
TEAM={team}
BALLAST=0
RESTRICTOR=0
AI_LEVEL=100
"""


RACE_TEMPLATE = """; {comment}
; Generated by scaffold_new_presets.py.

[HEADER]
VERSION=2
__CM_FEATURE_SET=2

[RACE]
TRACK={track}
CONFIG_TRACK={layout}
MODEL={car}
MODEL_CONFIG=
CARS={car_count}
AI_LEVEL=100
FIXED_SETUP=0
PENALTIES=0
SKIN={skin}
DRIFT_MODE=0
RACE_LAPS={race_laps}
JUMP_START_PENALTY=1
AI_AGGRESSION={ai_aggression}
RACE_GAS_PENALTY_DISABLED=0
OPPONENTS_VARIETY=0
__CM_WEATHER_TYPE=-1
__CM_WEATHER_CONTROLLER=base
__TRACK_GEOTAG_LAT={lat}
__TRACK_GEOTAG_LONG={lon}
__TRACK_TIMEZONE_BASE_OFFSET={tz}
__TRACK_TIMEZONE_OFFSET={tz}
__TRACK_TIMEZONE_DTS=0

[OPTIONS]
USE_MPH=0

[LAP_INVALIDATOR]
ALLOWED_TYRES_OUT=4

[TEMPERATURE]
AMBIENT={ambient}
ROAD={road}

[WEATHER]
NAME={weather}

[LIGHTING]
SUN_ANGLE={sun_angle:.2f}
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

[WIND]
SPEED_KMH_MIN=0
SPEED_KMH_MAX=4
DIRECTION_DEG=180

[REMOTE]
ACTIVE=0

[GHOST_CAR]
RECORDING=0
PLAYING=0
SECONDS_ADVANTAGE=0
LOAD=0
ENABLED=0

[REPLAY]
FILENAME=
ACTIVE=0

[BENCHMARK]
ACTIVE=0

[RESTART]
ACTIVE=0

[__PREVIEW_GENERATION]
ACTIVE=0

[SESSION_0]
NAME=Race
TYPE=3
DURATION_MINUTES=0
LAPS={race_laps}
SPAWN_SET=START

[CAR_0]
SETUP=
SKIN={skin}
MODEL=-
MODEL_CONFIG=
DRIVER_NAME={driver_name}
NATIONALITY={nationality}
NATION_CODE={nation_code}
TEAM={team}
BALLAST=0
RESTRICTOR=0
AI_LEVEL=100

{rivals_block}
"""


CMD_TEMPLATE = """@echo off
REM ===============================================================
REM  ONE-CLICK: {title} — generated by scaffold_new_presets.py
REM  Backs up cfg/race.ini, installs the preset, runs acs.exe.
REM  Run restore_race_ini.cmd afterwards to put your old config back.
REM ===============================================================
setlocal enableextensions

set "ACDOC=%USERPROFILE%\\Documents\\Assetto Corsa"
set "ACINSTALL={acinstall}"
set "PRESET=%ACDOC%\\cfg\\{ini_name}"
set "TARGET=%ACDOC%\\cfg\\race.ini"
set "BACKUP=%ACDOC%\\cfg\\race.ini.bak"

echo.
echo  =============================================================
echo   S I M R A C I N G   P I T   S T O P
echo  =============================================================
echo  [{title}]
echo.

if not exist "%PRESET%" (
    echo ERROR: preset not found:
    echo   %PRESET%
    pause
    exit /b 1
)

if not exist "%ACINSTALL%\\acs.exe" (
    echo ERROR: AC install not found at:
    echo   %ACINSTALL%
    echo Edit ACINSTALL at the top of this script.
    pause
    exit /b 1
)

if exist "%TARGET%" (
    echo Backing up current race.ini -^> race.ini.bak
    copy /Y "%TARGET%" "%BACKUP%" >nul
)

echo Installing preset...
copy /Y "%PRESET%" "%TARGET%" >nul

echo Launching Assetto Corsa...
start "" /D "%ACINSTALL%" "%ACINSTALL%\\acs.exe"

endlocal
exit /b 0
"""


def _load_skin_meta(car_id, skin_id):
    """Best-effort read of ui_skin.json for a car+skin."""
    if not (car_id and skin_id):
        return {}
    p = (
        L.AC_INSTALL / "content" / "cars" / car_id / "skins" / skin_id
        / "ui_skin.json"
    )
    return L._read_ui_json(p) or {}


def _ini_path_from_cmd(cmd_name):
    """Map launch_<x>.cmd → cfg/<x>.ini (matching Pablo's existing pattern)."""
    base = cmd_name
    if base.endswith(".cmd"):
        base = base[:-4]
    if base.startswith("launch_"):
        base = base[len("launch_"):]
    # Match Pablo's existing pattern: hotlap_<id>.ini, race_<id>.ini, etc.
    return base + ".ini"


def _build_rivals_block(rivals):
    out = []
    for i, r in enumerate(rivals, start=1):
        model, skin, driver, team, nationality, code = r
        out.append(f"""[CAR_{i}]
SETUP=
SKIN={skin}
MODEL={model}
MODEL_CONFIG=
DRIVER_NAME={driver}
NATIONALITY={nationality}
NATION_CODE={code}
TEAM={team}
BALLAST=0
RESTRICTOR=0
AI_LEVEL=100""")
    return "\n\n".join(out)


def render_preset(cfg):
    cmd_name = cfg["launcher"]
    ini_name = _ini_path_from_cmd(cmd_name)

    cond = CONDITIONS.get(cfg["id"], dict(
        weather="3_clear", ambient=22, road=32, sun_angle=-12,
        geotag=(0.0, 0.0), tz_offset=0,
    ))

    skin_meta = _load_skin_meta(cfg.get("ac_car_id"), cfg.get("ac_car_skin"))
    driver_name = skin_meta.get("drivername") or skin_meta.get("driver") or "Pablo Suzarte"
    team = skin_meta.get("team") or "Verstappen Racing"
    nationality = skin_meta.get("country") or "Spain"
    # Map common country fields to AC nation codes
    nat_map = {
        "Brazil": "BRA", "France": "FRA", "Germany": "DEU", "Italy": "ITA",
        "Japan": "JPN", "Spain": "ESP", "Great Britain": "GBR",
        "Netherlands": "NLD", "Australia": "AUS", "Finland": "FIN",
        "Poland": "POL", "ESP": "ESP",
    }
    nation_code = nat_map.get(nationality, "ESP")

    base = dict(
        comment=f"{cfg['title']} — {cfg['subtitle']}",
        track=cfg.get("ac_track_id", ""),
        layout=cfg.get("ac_track_layout", ""),
        car=cfg.get("ac_car_id", ""),
        skin=cfg.get("ac_car_skin", ""),
        lat=cond["geotag"][0],
        lon=cond["geotag"][1],
        tz=cond["tz_offset"],
        ambient=cond["ambient"],
        road=cond["road"],
        weather=cond["weather"],
        sun_angle=float(cond["sun_angle"]),
        driver_name=driver_name,
        nationality=nationality,
        nation_code=nation_code,
        team=team,
    )

    if cfg["type"] == "HOTLAP":
        ini = HOTLAP_TEMPLATE.format(**base)
    else:
        rivals = RIVALS.get(cfg["id"], [])
        rivals_block = _build_rivals_block(rivals)
        race_laps = 1 if cfg["type"] == "DUEL" else 5
        ai_aggression = 70 if cfg["type"] == "DUEL" else 50
        ini = RACE_TEMPLATE.format(
            **base,
            car_count=1 + len(rivals),
            race_laps=race_laps,
            ai_aggression=ai_aggression,
            rivals_block=rivals_block,
        )

    cmd = CMD_TEMPLATE.format(
        title=cfg["title"],
        acinstall=ACINSTALL_WIN,
        ini_name=ini_name,
    )
    return ini_name, ini, cmd_name, cmd


def main():
    force = "--force" in sys.argv
    cfg_dir = AC_DOC / "cfg"
    cfg_dir.mkdir(exist_ok=True)
    written = 0
    skipped = 0
    for cfg in L.CONFIGS:
        cmd_name = cfg.get("launcher")
        if not cmd_name:
            continue
        cmd_path = AC_DOC / cmd_name
        if cmd_path.exists() and not force:
            print(f"[skip] {cmd_name} (exists)")
            skipped += 1
            continue
        if not cfg.get("ac_car_id") or not cfg.get("ac_track_id"):
            print(f"[skip] {cfg['id']}: missing ac_car_id or ac_track_id")
            skipped += 1
            continue
        ini_name, ini_body, cmd_basename, cmd_body = render_preset(cfg)
        ini_path = cfg_dir / ini_name
        cmd_path.write_text(cmd_body, encoding="utf-8")
        ini_path.write_text(ini_body, encoding="utf-8")
        print(f"[wrote] cfg/{ini_name}")
        print(f"[wrote] {cmd_name}")
        written += 1
    print()
    print(f"Done. {written} preset+launcher pairs written, {skipped} skipped.")


if __name__ == "__main__":
    main()
