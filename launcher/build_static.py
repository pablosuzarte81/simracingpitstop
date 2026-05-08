#!/usr/bin/env python3
"""Build a static export of the Sim Racing Challenges dashboard for Vercel.

Renders index.html with all LAUNCH/OPEN URLs pointing at the user's local
agent (http://localhost:8765 by default), copies the images, and writes
everything to ./vercel_build/.

Run:  python3 build_static.py        # outputs to vercel_build/
"""

import os
import re
import shutil
import sys
from pathlib import Path

import launcher_dashboard as L

# Where the deployed page should send LAUNCH / OPEN POSTs.
# The user's browser fetches from this URL — so it must be reachable from
# their machine. localhost:8765 works when the local Python agent is running.
LOCAL_AGENT = os.environ.get("LOCAL_AGENT_URL", "http://localhost:8765")

LAUNCHER_DIR = Path(__file__).resolve().parent
OUT_DIR = LAUNCHER_DIR / "vercel_build"
IMAGES_SRC = LAUNCHER_DIR / "images"


def patch_endpoints(html: str) -> str:
    """Rewrite same-origin endpoints to point at the local agent."""
    html = html.replace("'/launch?id=' +", f"'{LOCAL_AGENT}/launch?id=' +")
    html = html.replace("'/open?path=' +", f"'{LOCAL_AGENT}/open?path=' +")
    # Image paths stay relative — Vercel serves /images/* from the public dir.
    return html


def inject_offline_banner(html: str) -> str:
    """Add a subtle banner that shows local-agent status to the user."""
    css = """
.agent-status{position:fixed;top:10px;right:10px;z-index:50;font:600 10px/1 var(--body);letter-spacing:1px;text-transform:uppercase;padding:6px 10px;border-radius:2px;background:var(--ink);color:#fff;border:1px solid var(--ink);box-shadow:0 1px 3px rgba(0,0,0,0.2)}
.agent-status.online{background:var(--green);border-color:var(--green)}
.agent-status.offline{background:var(--accent);border-color:var(--accent)}
.agent-help{position:fixed;top:42px;right:10px;z-index:50;font:500 11px/1.4 var(--body);padding:8px 11px;background:#fff;color:var(--ink-2);border:1px solid var(--border);box-shadow:0 1px 3px rgba(0,0,0,0.1);max-width:280px;display:none;border-radius:2px}
.agent-help.show{display:block}
.agent-help code{background:var(--paper);padding:1px 4px;border-radius:2px;font-family:var(--mono);font-size:10.5px}
"""
    js = (
        f"const LOCAL_AGENT = {L.json.dumps(LOCAL_AGENT)};"
        """
async function pingAgent(){
  const tag = document.getElementById('agent-status');
  const help = document.getElementById('agent-help');
  try {
    const r = await fetch(LOCAL_AGENT + '/', {method: 'GET', mode: 'cors', cache: 'no-store'});
    if (r.ok){
      tag.textContent = 'AGENT ONLINE';
      tag.classList.remove('offline');
      tag.classList.add('online');
      help.classList.remove('show');
      return;
    }
  } catch(e){}
  tag.textContent = 'AGENT OFFLINE';
  tag.classList.remove('online');
  tag.classList.add('offline');
  help.classList.add('show');
}
window.addEventListener('DOMContentLoaded', () => { pingAgent(); setInterval(pingAgent, 5000); });
"""
    )
    banner = (
        '<div id="agent-status" class="agent-status">CHECKING…</div>'
        '<div id="agent-help" class="agent-help">'
        'LAUNCH needs your local agent. Double-click '
        '<code>LAUNCH_BAY.cmd</code> on your PC.'
        '</div>'
    )
    html = html.replace("</style>", css + "</style>", 1)
    html = html.replace("</body>", banner + f"<script>{js}</script></body>", 1)
    return html


def main():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    print(f"[build] rendering HTML (agent → {LOCAL_AGENT}) ...")
    html = L.render_html()
    html = patch_endpoints(html)
    html = inject_offline_banner(html)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"[build] wrote {OUT_DIR / 'index.html'}  ({len(html)} bytes)")

    img_out = OUT_DIR / "images"
    if IMAGES_SRC.exists():
        shutil.copytree(IMAGES_SRC, img_out)
        n = sum(1 for _ in img_out.rglob("*") if _.is_file())
        print(f"[build] copied {n} images to {img_out}")

    # Minimal vercel.json — caches images aggressively, no caching on HTML
    (OUT_DIR / "vercel.json").write_text("""{
  "headers": [
    {
      "source": "/images/(.*)",
      "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]
    },
    {
      "source": "/",
      "headers": [{"key": "Cache-Control", "value": "no-cache"}]
    }
  ]
}
""")
    print(f"[build] wrote {OUT_DIR / 'vercel.json'}")
    print(f"[build] done → cd {OUT_DIR} && vercel deploy --prod")


if __name__ == "__main__":
    main()
