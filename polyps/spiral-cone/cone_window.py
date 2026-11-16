#!/usr/bin/env python3
"""
Opens the cone worm tool in its own Mac window (not a web browser).

It starts the tool quietly in the background, shows it in a window, and stops the tool when you close the window.
If the tool behind the window ever stops, it is started again. The window has a "Refresh tool" button in its top bar:
it loads the newest version (what Claude changed in the folder, or newer changes on GitHub) and reloads itself.

Normally you start this with the "Cone Worm" app icon (see install-app.sh), not by hand.
Ports: the cone tool uses 8820 to 8829 (the skin tool has 8790-8799, the other polyp tools 8800-8859).
"""
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import webview

HERE = os.path.dirname(os.path.abspath(__file__))


def free_port(start=8820, count=10):
    for p in range(start, start + count):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    sys.exit("Ports 8820 to 8829 are all busy.")


def wait_until_up(url, seconds=60):
    for _ in range(seconds * 4):
        try:
            urllib.request.urlopen(url + "api/version", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    port = int(os.environ.get("CONE_WINDOW_PORT") or free_port())
    env = dict(os.environ, SPIRAL_TOOL_PORT=str(port))
    start = lambda: subprocess.Popen([sys.executable, os.path.join(HERE, "spiral_tool.py"), "--no-browser"], cwd=HERE, env=env)
    box = {"server": start(), "closing": False}
    url = f"http://127.0.0.1:{port}/"

    def watchdog():                                   # if the tool behind the window ever stops, start it again
        while not box["closing"]:
            time.sleep(1.5)
            if box["server"].poll() is not None and not box["closing"]:
                box["server"] = start()
    threading.Thread(target=watchdog, daemon=True).start()
    try:
        if not wait_until_up(url):
            sys.exit("The tool did not start. Please tell Claude.")
        webview.settings["ALLOW_DOWNLOADS"] = True          # without this the window ignores download links
        webview.create_window("Cone Worm", url, width=1400, height=900, min_size=(900, 600))
        webview.start()
    finally:
        box["closing"] = True
        box["server"].terminate()


if __name__ == "__main__":
    main()
