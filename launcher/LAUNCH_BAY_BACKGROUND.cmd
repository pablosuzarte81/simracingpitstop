@echo off
REM Background launcher — delegates to the .vbs wrapper so the WSL session
REM keeps a foreground python process (no idle-shutdown of the WSL VM).
start "" wscript.exe "%~dp0SimRacingChallenges-Agent.vbs"
