#!/usr/bin/env python3
"""
Opens the frame tool in its own Mac window (not a web browser).

It starts the tool quietly in the background, shows it in a window, and stops the tool when you close the window.
The window has a "Refresh tool" button in its top bar: it loads the newest version (what Claude changed in the
folder, or newer changes on GitHub) and reloads itself. You never need to close and reopen the window for that.

Normally you start this with the "Coral Frame Tool" icon (see START-HERE.md), not by hand.
"""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import webview

HERE = os.path.dirname(os.path.abspath(__file__))


def free_port(start=8790, count=10):
    for p in range(start, start + count):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    sys.exit("Ports 8790 to 8799 are all busy.")


def wait_until_up(url, seconds=60):
    for _ in range(seconds * 4):
        try:
            urllib.request.urlopen(url + "api/version", timeout=1)
            return True
        except Exception:
            time.sleep(0.25)
    return False


def main():
    port = free_port()
    env = dict(os.environ, FRAME_NO_BROWSER="1", FRAME_TOOL_PORT=str(port))
    server = subprocess.Popen([sys.executable, os.path.join(HERE, "frame_app.py")], cwd=HERE, env=env)
    url = f"http://127.0.0.1:{port}/"
    try:
        if not wait_until_up(url):
            sys.exit("The tool did not start. Please tell Claude.")
        webview.create_window("Coral Frame Tool", url, width=1400, height=900, min_size=(900, 600))
        webview.start()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
