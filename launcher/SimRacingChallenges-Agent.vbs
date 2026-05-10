' Hidden autostart launcher for the Sim Racing Challenges agent.
' Runs the dashboard inside WSL with python in the FOREGROUND of the WSL
' session (via exec), so the WSL2 VM stays alive instead of idle-shutting
' down ~60s after a backgrounded `nohup ... &` returns and kills the server.
Set sh = CreateObject("WScript.Shell")
cmd = "wsl -d Ubuntu -e bash -lc ""exec python3 '/mnt/c/Users/pablo/Documents/Assetto Corsa/launcher/launcher_dashboard.py' --no-browser >> /tmp/launchbay.log 2>&1"""
sh.Run cmd, 0, False
