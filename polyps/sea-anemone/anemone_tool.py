"""A small page for trying out sea anemone polyp sizes. No code editing needed.

Run:  python3 anemone_tool.py     (opens your browser at http://127.0.0.1:8830/; Ctrl+C stops it)

Type sizes in millimetres, press Rebuild, and the flat pattern and the 3D sketch redraw. Pick Detailed or Laser cut and
save a PDF, DXF or SVG (true size, for the laser). Results are kept in tool-output/ next to this script (not in git).
It only listens on your own computer (127.0.0.1) and runs sea_anemone.py for you, so the results match that script.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "tool-output")
PORT = int(os.environ.get("ANEMONE_TOOL_PORT", 8830))   # skin 8790-8799, polyp tools 8800-8829, sea anemone 8830-8839
import sea_anemone as S

# (section, setting, label, unit, min, max, step)  -- everything is in millimetres
FIELDS = [
    ("Tube shape", "HEIGHT", "Height", "mm", 50, 800, 5),
    ("Tube shape", "DIAMETER_BOTTOM", "Diameter at the bottom", "mm", 30, 400, 1),
    ("Tube shape", "DIAMETER_TOP", "Diameter at the top", "mm", 30, 400, 1),
    ("Lower control point", "LOWER_HEIGHT", "Height above the bottom", "mm", 5, 800, 1),
    ("Lower control point", "LOWER_DIAMETER", "Diameter", "mm", 30, 400, 1),
    ("Lower control point", "LOWER_ANGLE", "Tangent angle", "deg", -85, 85, 1),
    ("Lower control point", "LOWER_LENGTH", "Tangent length", "mm", 0, 400, 1),
    ("Upper control point", "UPPER_FROM_TOP", "Distance below the top", "mm", 5, 800, 1),
    ("Upper control point", "UPPER_DIAMETER", "Diameter", "mm", 30, 400, 1),
    ("Upper control point", "UPPER_ANGLE", "Tangent angle", "deg", -85, 85, 1),
    ("Upper control point", "UPPER_LENGTH", "Tangent length", "mm", 0, 400, 1),
    ("Frill", "FRILL_LENGTH", "Frill length", "mm", 5, 200, 1),
    ("Frill", "FRILL_STRIP_LENGTH", "Strip length round the ring (0 = fits)", "mm", 0, 2000, 5),
    ("Frill", "FRINGE_WIDTH", "Fringe strip width", "mm", 3, 25, 0.5),
    ("Frill", "FRILL_WAVE", "Frill waviness", "slider", 0, 15, 0.5),
    ("Frill", "FRILL_WAVE_LENGTH", "Wave length", "mm", 10, 200, 1),
    ("Frill", "FRILL_BAND", "Solid band beside the sew line", "mm", 0, 30, 1),
    ("Frill", "FRILL_NOTCH_DEPTH", "Frill notch depth (0 = none)", "mm", 0, 25, 0.5),
    ("Frill", "FRILL_NOTCHES_BETWEEN_TABS", "Frill notches between tabs", "", 0, 30, 1),
    ("Seam", "SEAM", "Seam allowance", "mm", 6, 25, 1),
    ("Seam", "TUBE_NOTCH_DEPTH", "Tube notch depth (0 = none)", "mm", 0, 25, 0.5),
    ("Seam", "TUBE_NOTCHES_BETWEEN_TABS", "Tube notches between tabs", "", 0, 20, 1),
    ("Seam", "RING_BEND", "Ring bend (0 = edge follows the cross-section)", "sliderx", 0, 1, 0.05),
    ("Seam", "FABRIC_WIDTH", "Fabric width (fit check)", "mm", 300, 3000, 10),
    ("Tabs", "TAB_SIZE", "Tab size", "mm", 6, 25, 1),
    ("Tabs", "TAB_SPACING", "Tab spacing", "mm", 50, 300, 5),
]
DEFAULTS = {k: getattr(S, k) for k in S.NAMES}
PAGE_DEFAULTS = dict(DEFAULTS)
SNAPS = os.path.join(HERE, "snapshots")
LOCK = threading.Lock()


def run_pattern(params):
    """Make the pattern for these settings. Returns (folder name, result dict)."""
    clean = {}
    for _sec, name, *_ in FIELDS:
        v = float(params.get(name, PAGE_DEFAULTS[name]))
        if not (v == v) or abs(v) > 1e4:
            raise ValueError(f"{name} is not a sensible number")
        clean[name] = v
    key = hashlib.sha1(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:12]
    folder = os.path.join(OUT, key)
    with LOCK:                                   # the script keeps its settings in module variables
        for k, v in {**DEFAULTS, **clean}.items():
            setattr(S, k, v)
        info, text = S.make(folder, "sea-anemone")
    shown = text[:text.index("\nSettings:")] + "\n" + text[text.index("Results:"):]      # the settings stay in the .txt file, not on the page
    return key, {"text": shown, "warnings": info["warnings"]}


# --- asking where to save an export (the standard Mac "Save" window, started from here so it works in the app and in a browser)
SAVED = set()
LASTDIR = os.path.join(HERE, "snapshots", ".last-save-folder")


def remember_folder(d):
    try:
        os.makedirs(os.path.dirname(LASTDIR), exist_ok=True)
        open(LASTDIR, "w").write(d)
    except OSError:
        pass


def ask_save_path(default_name):
    """Show the Mac save dialog; returns the chosen path, or None if cancelled. Opens in the last folder used (first time: Downloads)."""
    folder = os.path.expanduser("~/Downloads")
    try:
        d = open(LASTDIR).read().strip()
        if os.path.isdir(d):
            folder = d
    except OSError:
        pass
    script = ('tell current application to activate\n'
              'set f to choose file name with prompt "Save the pattern as" default name (item 1 of argv) '
              'default location (POSIX file (item 2 of argv))\n'
              'return POSIX path of f')
    script = 'on run argv\n' + script + '\nend run'
    r = subprocess.run(["osascript", "-e", script, default_name, folder], capture_output=True, text=True)
    out = r.stdout.strip()
    return out if r.returncode == 0 and out else None


# --- saved snapshots (named sets of sizes, kept as small files in the snapshots/ folder)
def snap_names():
    if not os.path.isdir(SNAPS):
        return []
    files = [f for f in os.listdir(SNAPS) if f.endswith(".json")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(SNAPS, f)), reverse=True)
    return [f[:-5] for f in files]


def snap_clean(name):
    name = re.sub(r"[^A-Za-z0-9 _.()-]", "-", (name or "").strip())[:60].strip(" .")
    return name or time.strftime("snapshot %Y-%m-%d %H-%M-%S")


def snap_save(name, params):
    name = snap_clean(name)
    values = {}
    for _sec, k, *_ in FIELDS:
        values[k] = float(params.get(k, PAGE_DEFAULTS[k]))
    os.makedirs(SNAPS, exist_ok=True)
    with open(os.path.join(SNAPS, name + ".json"), "w") as f:
        json.dump({"name": name, "saved": time.strftime("%Y-%m-%d %H:%M"), "params": values}, f, indent=1)
    return name


def snap_load(name):
    name = snap_clean(name)
    path = os.path.join(SNAPS, name + ".json")
    if not os.path.isfile(path):
        return None
    return json.load(open(path))["params"]


# --- version label and Refresh (same as the skin tool's)
def git(*args, timeout=60):
    """Run a git command in THIS folder. Returns (ok, text)."""
    try:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def version():
    """Which branch and last change this copy is on (shown in the top bar)."""
    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not ok:
        return dict(git=False)
    _, line = git("log", "-1", "--format=%h|%cs|%s")
    sha, date, subject = (line.split("|", 2) + ["", "", ""])[:3]
    _, dirty = git("status", "--porcelain", "--untracked-files=no")
    return dict(git=True, branch=branch, sha=sha, date=date, subject=subject, edited=bool(dirty))


def refresh_code():
    """Pull newer changes from GitHub if that is safe, install any new libraries. The caller then restarts the
    tool so whatever is in the folder (pulled, or edited here) is what runs."""
    log = []
    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if ok and branch != "HEAD":
        fetched, _ = git("fetch", "--prune", "origin", timeout=30)
        if not fetched:
            log.append("Could not reach GitHub, so I used the files already on this computer.")
        else:
            has_remote = git("rev-parse", "--verify", "--quiet", f"origin/{branch}")[0]
            _, behind = git("rev-list", "--count", f"HEAD..origin/{branch}") if has_remote else (False, "0")
            if has_remote and behind.isdigit() and int(behind) > 0:
                merged, out = git("merge", "--ff-only", f"origin/{branch}")
                log.append(f"Pulled {behind} new change(s) from GitHub." if merged else
                           "GitHub has newer changes but they would clash with changes here, so I left them. " + out[-200:])
            else:
                log.append("Nothing new on GitHub.")
    req = os.path.join(HERE, "requirements.txt")
    if os.path.exists(req):
        pip = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", req], cwd=HERE, capture_output=True, text=True)
        if pip.returncode != 0:
            log.append("(The library check failed: " + pip.stderr.strip()[-200:] + ")")
    return True, " ".join(log)


def restart_soon():
    def go():
        time.sleep(1.0)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=go, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype, extra=None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            meta = dict(fields=FIELDS, defaults=PAGE_DEFAULTS)
            self.send(200, PAGE.replace("__META__", json.dumps(meta)), "text/html; charset=utf-8")
        elif path == "/api/version":
            self.send(200, json.dumps(version()), "application/json")
        elif path == "/api/snapshots":
            self.send(200, json.dumps(snap_names()), "application/json")
        elif path == "/api/snapshot":
            p = snap_load(parse_qs(urlparse(self.path).query).get("name", [""])[0])
            self.send(200 if p else 404, json.dumps(p or {"error": "No such snapshot."}), "application/json")
        elif path.startswith("/out/"):
            parts = path.split("/")[2:]
            ok = len(parts) == 2 and re.fullmatch(r"[0-9a-f]{12}", parts[0]) and re.fullmatch(r"sea-anemone(-detailed|-outline)?\.(svg|dxf|pdf|txt)|preview-(detailed|outline)\.svg|picture-3d\.png", parts[1])
            f = os.path.join(OUT, *parts) if ok else None
            if f and os.path.isfile(f):
                ext = f.rsplit(".", 1)[-1]
                ctype = {"png": "image/png", "svg": "image/svg+xml", "dxf": "application/dxf", "pdf": "application/pdf", "txt": "text/plain"}.get(ext, "application/octet-stream")
                extra = None
                if ext in ("svg", "dxf", "pdf") and "dl=1" in self.path:      # named: the saved snapshot name + _detailed or _outline + units
                    nm = snap_clean(parse_qs(urlparse(self.path).query).get("name", [""])[0]).replace(" ", "_")
                    view = "outline" if "-outline." in parts[1] else "detailed"
                    extra = {"Content-Disposition": f'attachment; filename="{nm}_{view}_mm.{ext}"'}
                self.send(200, open(f, "rb").read(), ctype, extra)
            else:
                self.send(404, "not found", "text/plain")
        else:
            self.send(404, "not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if path == "/api/refresh":
            ok, log = refresh_code()
            self.send(200, json.dumps({"ok": ok, "log": log}), "application/json")
            if ok:
                restart_soon()
        elif path == "/api/export":                  # ask where to save (Mac save dialog), then copy the file there
            try:
                key, view, ext = str(body.get("key", "")), str(body.get("view", "")), str(body.get("ext", ""))
                if not (re.fullmatch(r"[0-9a-f]{12}", key) and view in ("detailed", "outline") and ext in ("pdf", "dxf", "svg")):
                    raise ValueError("bad request")
                src = os.path.join(OUT, key, f"sea-anemone-{view}.{ext}")
                nm = snap_clean(body.get("name", "")).replace(" ", "_")
                dest = ask_save_path(f"{nm}_{view}_mm.{ext}")
                if not dest:
                    self.send(200, json.dumps({"cancelled": True}), "application/json")
                    return
                if not dest.lower().endswith("." + ext):
                    dest += "." + ext
                shutil.copyfile(src, dest)
                SAVED.add(os.path.realpath(dest))
                remember_folder(os.path.dirname(dest))
                self.send(200, json.dumps({"ok": True, "file": os.path.basename(dest), "folder": os.path.dirname(dest), "path": dest}), "application/json")
            except (ValueError, OSError) as e:
                self.send(400, json.dumps({"error": f"Could not save the file: {e}"}), "application/json")
        elif path == "/api/reveal":                  # show a file this tool saved in Finder
            p = os.path.realpath(str(body.get("path", "")))
            if p in SAVED and os.path.isfile(p):
                subprocess.run(["open", "-R", p])
            self.send(200, json.dumps({"ok": True}), "application/json")
        elif path == "/api/snapshot":
            name = snap_save(body.get("name"), body.get("params", {}))
            self.send(200, json.dumps({"name": name, "names": snap_names()}), "application/json")
        elif path == "/api/run":
            try:
                key, res = run_pattern(body.get("params", {}))
                self.send(200, json.dumps({"key": key, **res}), "application/json")
            except (ValueError, SystemExit, TypeError) as e:
                self.send(400, json.dumps({"error": str(e) or "Those settings don't make a valid anemone."}), "application/json")
        else:
            self.send(404, "not found", "text/plain")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sea Anemone</title>
<style>
  :root { --bg:#f6f4f1; --card:#fff; --ink:#222; --mute:#6b665f; --line:#ddd8d0; --accent:#c4492f; --blue:#2b6cb0; }
  @media (prefers-color-scheme: dark) { :root { --bg:#1b1a19; --card:#262523; --ink:#eee; --mute:#a59f96; --line:#3a3835; --accent:#e5694e; --blue:#6aa7e8; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 system-ui, sans-serif; }
  header { padding:10px 20px; border-bottom:1px solid var(--line); display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
  header button { width:auto; margin:0; padding:5px 12px; }
  header h1 { margin:0; font-size:18px; } header p { margin:2px 0 0; color:var(--mute); font-size:13px; }
  main { display:grid; grid-template-columns: 330px 1fr; gap:16px; padding:16px; max-width:1500px; margin:0 auto; }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .card h2 { margin:0 0 8px; font-size:15px; }
  .field { margin:8px 0; } .field label { display:flex; justify-content:space-between; font-weight:600; font-size:13px; }
  .field input[type=number] { width:78px; font:inherit; padding:2px 4px; border:1px solid var(--line); border-radius:5px; background:var(--bg); color:var(--ink); }
  .field input[type=range] { width:100%; accent-color:var(--accent); }
  .field small { color:var(--mute); display:block; line-height:1.3; }
  button { font:inherit; font-weight:600; padding:8px 12px; border-radius:7px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; width:100%; margin-top:8px; }
  button.secondary { background:transparent; color:var(--accent); }
  .results { display:grid; gap:16px; align-content:start; }
  .results img { max-width:100%; height:auto; border-radius:6px; background:#fff; display:block; margin:6px auto; }
  pre { font:12.5px/1.4 ui-monospace, monospace; white-space:pre-wrap; margin:6px 0 0; color:var(--mute); }
  .warn { background:#fff3cd; color:#5c4400; border-radius:6px; padding:6px 10px; margin:6px 0; font-size:13px; }
  .status { font-size:13px; color:var(--mute); white-space:pre-wrap; font-family:ui-monospace, monospace; max-height:150px; overflow:auto; margin-top:6px; }
  .stale img { opacity:.35; } a { color:var(--blue); } .err { color:#c0392b; }
  .reset { background:none; border:none; color:var(--mute); text-decoration:underline; font-weight:400; width:auto; padding:0; margin:8px 0 0; }
  .sticky { position:sticky; top:0; z-index:5; }
  button:disabled { opacity:.4; cursor:default; }
  .saved { color:#2e8b57; font-weight:600; margin:6px 0; }
  .seg { display:inline-flex; border:1px solid var(--line); border-radius:8px; overflow:hidden; margin-bottom:8px; } .seg button { width:auto; margin:0; border:0; border-radius:0; background:var(--bg); color:var(--ink); padding:6px 14px; cursor:pointer; font:inherit; } .seg button.on { background:var(--ink); color:var(--bg); }
  dialog { border:1px solid var(--line); border-radius:10px; background:var(--bg); color:var(--ink); padding:16px; max-width:380px; } dialog input[type=text] { width:100%; box-sizing:border-box; font:inherit; padding:6px; margin-top:6px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); }
  .row { display:flex; gap:6px; margin-top:8px; } .row input { flex:1; min-width:0; font:inherit; padding:4px 6px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); } .row button { width:auto; margin:0; }
  #load { width:100%; margin-top:8px; font:inherit; padding:5px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); }
  .sw { display:inline-flex; align-items:center; gap:6px; font-weight:400; } .sw input { position:absolute; opacity:0; } .sw .track { width:36px; height:20px; border-radius:10px; background:var(--line); position:relative; transition:.15s; } .sw .track::after { content:''; position:absolute; top:2px; left:2px; width:16px; height:16px; border-radius:50%; background:#fff; transition:.15s; } .sw input:checked + .track { background:var(--accent); } .sw input:checked + .track::after { left:18px; }
  .derived { font-size:13px; color:var(--mute); }
  #xs { width:100%; height:520px; background:#1c1b1a; border-radius:8px; touch-action:none; margin-top:6px; user-select:none; } #xs text { font:11px system-ui, sans-serif; fill:#aaa; } #xs .pt { cursor:grab; } #xs .end { cursor:ew-resize; } #xs .hd { cursor:crosshair; }
  .zoombar { display:flex; gap:6px; align-items:center; margin:4px 0 6px; } .zoombar button { width:34px; margin:0; padding:3px 0; } .zoombar button#zfit { width:auto; padding:3px 12px; }
  .viewer { background:#1c1b1a; border-radius:8px; overflow:auto; max-height:72vh; cursor:grab; } .viewer.drag { cursor:grabbing; } .viewer img { display:block; width:100%; max-width:none; margin:0; border-radius:0; background:none; user-select:none; }
  .viewer.nozoom { max-height:none; overflow:visible; cursor:default; }
  .viewer3d { background:#1c1b1a; border-radius:8px; margin-top:10px; } .viewer3d img { display:block; max-width:520px; width:100%; margin:0 auto; background:none; }
</style></head><body>
<header><h1>Sea Anemone</h1><span class="derived">Sea anemone polyp pattern. Everything in millimetres. Type them, press Rebuild, pick Detailed or Laser cut, save the PDF for the laser.</span>
  <span id="ver" class="derived" style="margin-left:auto"></span>
  <button id="refresh-btn" title="Load the newest version of the tool (anything Claude changed or pushed)">Refresh tool</button>
  <span id="refresh-msg" class="derived"></span></header>
<main>
  <div>
    <div class="card sticky">
      <button id="rebuild" disabled>Rebuild</button>
      <button class="reset" id="reset">Reset to the starting values</button>
      <div class="row"><input type="text" id="snapname" placeholder="Snapshot name (optional)" maxlength="60"><button id="save" class="secondary">Save</button></div>
      <select id="load"><option value="">Load a snapshot...</option></select>
      <div id="snapmsg" class="derived"></div></div>
    <div id="sections"></div>
  </div>
  <div class="results">
    <div class="card" id="xcard"><h2>Tube cross-section <span class="derived">Drag the red dots to move the two middle control points, the white dots (bottom and top) in or out to change their diameter, and the yellow squares to set each tangent (direction and length). The numbers on the left follow.</span></h2>
      <svg id="xs" viewBox="0 0 640 520" preserveAspectRatio="xMidYMid meet"></svg></div>
    <div class="card" id="card"><h2>Pattern <span id="busy" class="derived"></span></h2>
      <div id="warnings"></div>
      <div class="seg"><button id="v-detailed" class="on" type="button">Detailed</button><button id="v-outline" type="button">Laser cut</button></div>
      <div class="zoombar" id="zoombar"><button id="zout" type="button" class="secondary">&minus;</button><button id="zin" type="button" class="secondary">+</button><button id="zfit" type="button" class="secondary">Fit</button><span class="derived">Scroll to zoom, drag to move, double-click to fit.</span></div>
      <div class="viewer" id="viewer"><img id="pic" alt="" draggable="false"></div>
      <div id="pic3dbox"><div class="viewer3d"><img id="pic3d" alt=""></div><p class="derived">The finished anemone, inflated: a picture, not a simulation. The cap puffs into a dome with the seam on the rounded corner; the frill is blown up by air from the base. No motion.</p></div>
      <p id="dlhelp" class="derived"></p>
      <p><a id="pdf" href="#">Save PDF</a> &nbsp; <a id="dxf" href="#">Save DXF</a> &nbsp; <a id="svg" href="#">Save SVG</a></p>
      <div id="dlmsg" class="derived"></div>
      <dialog id="dlg"><form method="dialog" id="dlgform"><h2>Name this snapshot</h2>
        <p class="derived">Every new pattern is saved as a snapshot before its first export, so you can come back to it. The name goes at the start of the file name; later exports of the same settings reuse it.</p>
        <input type="text" id="dlgname" maxlength="60" placeholder="e.g. test anemone 1" autocomplete="off">
        <div id="dlgwarn" class="derived"></div>
        <div class="row"><button type="submit" id="dlgok" disabled>Save and export</button><button type="button" id="dlgcancel" class="secondary">Cancel</button></div></form></dialog>
      <pre id="text"></pre></div>
  </div>
</main>
<script>
const META = __META__;
const $ = id => document.getElementById(id);
const vals = {...META.defaults};
let seq = 0, zoom = 1, shownView = '';
const secs = {};
let built = '', curKey = '', snapNames = [], view = 'detailed', named = null;   // named = {cfg, name}: the settings that already have a saved snapshot name

function refreshBtn() { $('rebuild').disabled = JSON.stringify(vals) === built; drawProfile(); }
for (const [sec, name, label, unit, lo, hi, step] of META.fields) {
  if (!secs[sec]) { const c = document.createElement('div'); c.className = 'card'; c.style.marginTop = '12px'; c.innerHTML = `<h2>${sec}</h2>`; $('sections').appendChild(c); secs[sec] = c; }
  const d = document.createElement('div'); d.className = 'field';
  if (unit === 'slider' || unit === 'sliderx') {          // a slider with its value shown; rebuilds when you let go
    d.innerHTML = `<label>${label}<span><span id="v-${name}"></span>${unit === 'slider' ? ' mm' : ''}</span></label><input type="range" id="n-${name}" min="${lo}" max="${hi}" step="${step}">`;
    secs[sec].appendChild(d);
    const sl = d.querySelector('input');
    sl.value = vals[name]; $('v-' + name).textContent = vals[name];
    sl.oninput = () => { vals[name] = parseFloat(sl.value); $('v-' + name).textContent = vals[name]; refreshBtn(); };
    sl.onchange = () => { if (!$('rebuild').disabled) run(); };
    continue;
  }
  if (unit === 'toggle') {          // Separate cuff: Yes = the cuff is its own band (CUFF_IN_STRIP = 0)
    d.innerHTML = `<label>${label}<span class="sw"><span id="t-${name}-txt"></span><input type="checkbox" id="n-${name}"><span class="track"></span></span></label>`;
    secs[sec].appendChild(d);
    const cb = d.querySelector('input');
    const show = () => { cb.checked = vals[name] === 0; $('t-' + name + '-txt').textContent = cb.checked ? 'Yes' : 'No'; };
    show();
    cb.onchange = () => { vals[name] = cb.checked ? 0 : 1; show(); refreshBtn(); };
    continue;
  }
  d.innerHTML = `<label>${label}<span><input type="number" id="n-${name}" min="${lo}" max="${hi}" step="${step}"> ${unit}</span></label>`;
  secs[sec].appendChild(d);
  const n = d.querySelector('input');
  n.value = +(+vals[name]).toFixed(3);
  n.oninput = () => { if (n.value !== '') { vals[name] = parseFloat(n.value); refreshBtn(); } };
  n.onkeydown = e => { if (e.key === 'Enter' && !$('rebuild').disabled) run(); };
}
function sync() {
  for (const [, name, , unit] of META.fields) {
    const el = $('n-' + name);
    if (unit === 'toggle') { el.checked = vals[name] === 0; $('t-' + name + '-txt').textContent = el.checked ? 'Yes' : 'No'; }
    else el.value = +(+vals[name]).toFixed(3);
    if (unit === 'slider') $('v-' + name).textContent = vals[name];
  }
}
$('reset').onclick = () => { Object.assign(vals, META.defaults); sync(); run(); };
$('rebuild').onclick = () => run();
async function loadSnaps(select) {
  const names = await fetch('/api/snapshots').then(r => r.json()).catch(() => []);
  snapNames = names;
  $('load').innerHTML = '<option value="">Load a snapshot...</option>' + names.map(n => `<option>${n.replace(/&/g, '&amp;').replace(/</g, '&lt;')}</option>`).join('');
  if (select) $('load').value = select;
}
$('save').onclick = async () => {
  const r = await fetch('/api/snapshot', {method: 'POST', body: JSON.stringify({name: $('snapname').value, params: vals})}).then(x => x.json()).catch(() => null);
  if (!r) { $('snapmsg').textContent = 'Could not save.'; return; }
  named = {cfg: JSON.stringify(vals), name: r.name}; $('snapmsg').textContent = 'Saved "' + r.name + '".'; $('snapname').value = ''; loadSnaps(r.name);
};
$('load').onchange = async () => {
  const name = $('load').value; if (!name) return;
  const p = await fetch('/api/snapshot?name=' + encodeURIComponent(name)).then(x => x.ok ? x.json() : null).catch(() => null);
  if (!p) { $('snapmsg').textContent = 'Could not load "' + name + '".'; return; }
  Object.assign(vals, META.defaults, p); named = {cfg: JSON.stringify(vals), name}; sync(); $('snapmsg').textContent = 'Loaded "' + name + '".'; run();
};
loadSnaps();
async function run() {
  const me = ++seq, sent = JSON.stringify(vals); $('busy').textContent = 'building...'; $('rebuild').disabled = true;
  const r = await fetch('/api/run', {method: 'POST', body: JSON.stringify({params: vals})}).then(x => x.json()).catch(() => ({error: 'Lost the connection to the tool.'}));
  if (me !== seq) return;
  $('busy').textContent = '';
  if (r.error) { $('warnings').innerHTML = '<div class="warn err">' + r.error + '</div>'; refreshBtn(); return; }
  $('warnings').innerHTML = ''; $('card').classList.remove('stale');
  built = sent; refreshBtn();
  curKey = r.key; showView();
  $('text').textContent = r.text;
}

// Downloads: name and save a snapshot of the built pattern first (the name goes into the file name)
let wantExt = '';
const HELP = {detailed: 'Exports every line shown (cut, sew, tab labels), true size in mm, no scales or grid.',
              outline: 'Exports only the cut lines the laser follows (the frill is one closed loop that doubles back along each slit), true size in mm, no scales or grid.'};
function showView() {
  $('v-detailed').classList.toggle('on', view === 'detailed'); $('v-outline').classList.toggle('on', view === 'outline');
  if (curKey) { $('pic').src = '/out/' + curKey + '/preview-' + view + '.svg'; $('pic3d').src = '/out/' + curKey + '/picture-3d.png'; }
  $('pic3dbox').style.display = view === 'detailed' ? '' : 'none';
  $('zoombar').style.display = view === 'outline' ? '' : 'none';           // zoom only in the Laser cut view
  $('viewer').classList.toggle('nozoom', view === 'detailed');
  if (view !== shownView) { shownView = view; zoomTo(1); }
  $('dlhelp').textContent = HELP[view];
}
$('v-detailed').onclick = () => { view = 'detailed'; showView(); };
$('v-outline').onclick = () => { view = 'outline'; showView(); };
// zoom and pan the flat-pattern preview (the SVG is resized, so it stays sharp)
const viewer = $('viewer');
function zoomTo(k, cx, cy) {
  const img = $('pic');
  k = Math.min(Math.max(k, 1), 14);
  if (cx === undefined) { cx = viewer.clientWidth / 2; cy = viewer.clientHeight / 2; }
  const fx = (viewer.scrollLeft + cx) / img.clientWidth, fy = (viewer.scrollTop + cy) / (img.clientHeight || 1);
  zoom = k; img.style.width = (100 * k) + '%';
  viewer.scrollLeft = fx * img.clientWidth - cx; viewer.scrollTop = fy * img.clientHeight - cy;
}
viewer.addEventListener('wheel', e => { if (view === 'detailed') return; e.preventDefault(); const r = viewer.getBoundingClientRect(); zoomTo(zoom * Math.exp(-e.deltaY / 300), e.clientX - r.left, e.clientY - r.top); }, {passive: false});
$('zin').onclick = () => zoomTo(zoom * 1.5); $('zout').onclick = () => zoomTo(zoom / 1.5); $('zfit').onclick = () => zoomTo(1);
viewer.addEventListener('dblclick', () => { if (view !== 'detailed') zoomTo(1); });
let dragging = null;
viewer.addEventListener('mousedown', e => { if (view === 'detailed') return; dragging = {x: e.clientX, y: e.clientY, l: viewer.scrollLeft, t: viewer.scrollTop}; viewer.classList.add('drag'); e.preventDefault(); });
window.addEventListener('mousemove', e => { if (dragging) { viewer.scrollLeft = dragging.l - (e.clientX - dragging.x); viewer.scrollTop = dragging.t - (e.clientY - dragging.y); } });
window.addEventListener('mouseup', () => { dragging = null; viewer.classList.remove('drag'); });
// ---- tube cross-section: draw the curve from the boxes, drag points and tangent handles (like a CAD spline)
const XS = {W: 640, H: 520, ml: 60, mr: 40, mt: 24, mb: 40};
let xsFrozen = null;
function profCtl(v) {
  const H = v.HEIGHT, rad = a => a * Math.PI / 180;
  const P = [[0, v.DIAMETER_BOTTOM / 2], [v.LOWER_HEIGHT, v.LOWER_DIAMETER / 2], [H - v.UPPER_FROM_TOP, v.UPPER_DIAMETER / 2], [H, v.DIAMETER_TOP / 2]];
  const un = (a, b) => { const dz = b[0] - a[0], dr = b[1] - a[1], n = Math.hypot(dz, dr) || 1; return [dz / n, dr / n, n]; };
  const u0 = un(P[0], P[1]), u3 = un(P[2], P[3]);
  return {P, d: [[u0[0], u0[1]], [Math.cos(rad(v.LOWER_ANGLE)), Math.sin(rad(v.LOWER_ANGLE))], [Math.cos(rad(v.UPPER_ANGLE)), Math.sin(rad(v.UPPER_ANGLE))], [u3[0], u3[1]]],
          l: [u0[2] / 3, v.LOWER_LENGTH, v.UPPER_LENGTH, u3[2] / 3]};
}
function profCurve(c, m = 60) {
  const out = [];
  for (let i = 0; i < 3; i++) {
    const p0 = c.P[i], p3 = c.P[i + 1];
    const p1 = [p0[0] + c.d[i][0] * c.l[i], p0[1] + c.d[i][1] * c.l[i]], p2 = [p3[0] - c.d[i + 1][0] * c.l[i + 1], p3[1] - c.d[i + 1][1] * c.l[i + 1]];
    for (let k = (i ? 1 : 0); k <= m; k++) {
      const t = k / m, a = (1 - t) ** 3, b = 3 * (1 - t) ** 2 * t, e = 3 * (1 - t) * t * t, f = t ** 3;
      out.push([a * p0[0] + b * p1[0] + e * p2[0] + f * p3[0], a * p0[1] + b * p1[1] + e * p2[1] + f * p3[1]]);
    }
  }
  return out;
}
function xsGeom(v, c, curve) {
  if (xsFrozen) return xsFrozen;
  let rmax = 20;
  curve.forEach(q => rmax = Math.max(rmax, q[1]));
  for (let i = 1; i <= 2; i++) for (const sg of [-1, 1]) rmax = Math.max(rmax, Math.abs(c.P[i][1] + sg * c.d[i][1] * c.l[i]));
  rmax += 18;
  const sc = Math.min((XS.W - XS.ml - XS.mr) / (2 * rmax), (XS.H - XS.mt - XS.mb) / (v.HEIGHT * 1.02));
  return {sc, cx: XS.ml + (XS.W - XS.ml - XS.mr) / 2, z0: XS.H - XS.mb};
}
function drawProfile() {
  const svg = $('xs'); if (!svg) return;
  const v = vals, c = profCtl(v), curve = profCurve(c), g = xsGeom(v, c, curve);
  const X = r => g.cx + r * g.sc, Y = z => g.z0 - z * g.sc;
  let h = '';
  const step = v.HEIGHT > 400 ? 100 : 50;
  for (let z = 0; z <= v.HEIGHT + 0.1; z += step) h += `<line x1="${XS.ml - 8}" x2="${XS.W - XS.mr}" y1="${Y(z)}" y2="${Y(z)}" stroke="#ffffff" stroke-opacity=".08"/><text x="${XS.ml - 12}" y="${Y(z) + 4}" text-anchor="end">${z}</text>`;
  h += `<line x1="${g.cx}" x2="${g.cx}" y1="${Y(0)}" y2="${Y(v.HEIGHT)}" stroke="#888" stroke-dasharray="6 5"/>`;
  h += `<line x1="${X(-v.DIAMETER_TOP / 2) - 6}" x2="${X(v.DIAMETER_TOP / 2) + 6}" y1="${Y(v.HEIGHT)}" y2="${Y(v.HEIGHT)}" stroke="#bbb" stroke-dasharray="3 3"/><text x="${X(v.DIAMETER_TOP / 2) + 10}" y="${Y(v.HEIGHT) + 4}">cap</text>`;
  const pathR = curve.map((q, i) => (i ? 'L' : 'M') + X(q[1]).toFixed(1) + ' ' + Y(q[0]).toFixed(1)).join(' ');
  const pathL = curve.map((q, i) => (i ? 'L' : 'M') + X(-q[1]).toFixed(1) + ' ' + Y(q[0]).toFixed(1)).join(' ');
  h += `<path d="${pathL}" fill="none" stroke="#6aa7e8" stroke-opacity=".55" stroke-width="2"/><path d="${pathR}" fill="none" stroke="#6aa7e8" stroke-width="2.5"/>`;
  const names = ['bottom', 'lower', 'upper', 'top'];
  for (let i = 0; i < 4; i++) {
    const P = c.P[i], px = X(P[1]), py = Y(P[0]);
    if (i === 1 || i === 2) {
      for (const sg of [-1, 1]) {
        const ex = X(P[1] + sg * c.d[i][1] * c.l[i]), ey = Y(P[0] + sg * c.d[i][0] * c.l[i]);
        h += `<line x1="${px}" y1="${py}" x2="${ex}" y2="${ey}" stroke="#ffd23f" stroke-width="1.5"/>`;
        h += `<rect class="hd" data-id="h${i}${sg > 0 ? 'p' : 'm'}" x="${ex - 6}" y="${ey - 6}" width="12" height="12" fill="#ffd23f" stroke="#1c1b1a"/>`;
        const mx = X(-(P[1] + sg * c.d[i][1] * c.l[i])), my = ey;
        h += `<line x1="${X(-P[1])}" y1="${py}" x2="${mx}" y2="${my}" stroke="#ffd23f" stroke-opacity=".35"/><rect x="${mx - 4}" y="${my - 4}" width="8" height="8" fill="#ffd23f" fill-opacity=".35"/>`;
      }
      h += `<circle class="pt" data-id="p${i}" cx="${px}" cy="${py}" r="8" fill="#ff6a5c" stroke="#1c1b1a" stroke-width="2"/><circle cx="${X(-P[1])}" cy="${py}" r="5" fill="#ff6a5c" fill-opacity=".4"/>`;
      h += `<text x="${px + 14}" y="${py - 10}" fill="#eee">${names[i]}: Ø${Math.round(P[1] * 2)}, ${i === 1 ? v.LOWER_HEIGHT : v.UPPER_FROM_TOP} ${i === 1 ? 'up' : 'down'}</text>`;
      h += `<text x="${px + 14}" y="${py + 4}">${i === 1 ? v.LOWER_ANGLE : v.UPPER_ANGLE}&deg;, handle ${i === 1 ? v.LOWER_LENGTH : v.UPPER_LENGTH}</text>`;
    } else {
      h += `<circle class="pt end" data-id="p${i}" cx="${px}" cy="${py}" r="8" fill="#ffffff" stroke="#1c1b1a" stroke-width="2"/><circle cx="${X(-P[1])}" cy="${py}" r="5" fill="#ffffff" fill-opacity=".4"/><text x="${px + 14}" y="${py + (i ? -10 : 18)}" fill="#eee">${names[i]}: Ø${Math.round(P[1] * 2)}</text>`;
    }
  }
  svg.innerHTML = h; svg._g = g;
}
let xsDrag = null;
$('xs').addEventListener('pointerdown', e => {
  const t = e.target.closest('[data-id]'); if (!t) return;
  const svg = $('xs'); xsDrag = t.dataset.id; svg.setPointerCapture(e.pointerId);
  const c = profCtl(vals); xsFrozen = xsGeom(vals, c, profCurve(c));          // keep the scale fixed while dragging
  e.preventDefault();
});
$('xs').addEventListener('pointermove', e => {
  if (!xsDrag) return;
  const svg = $('xs'), pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
  const q = pt.matrixTransform(svg.getScreenCTM().inverse()), g = xsFrozen;
  const zmm = (g.z0 - q.y) / g.sc, rmm = (q.x - g.cx) / g.sc, H = vals.HEIGHT;
  const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
  if (xsDrag === 'p0') {
    vals.DIAMETER_BOTTOM = Math.round(clamp(Math.abs(rmm) * 2, 30, 400));
  } else if (xsDrag === 'p3') {
    vals.DIAMETER_TOP = Math.round(clamp(Math.abs(rmm) * 2, 30, 400));
  } else if (xsDrag === 'p1') {
    vals.LOWER_HEIGHT = Math.round(clamp(zmm, 5, H - vals.UPPER_FROM_TOP - 5)); vals.LOWER_DIAMETER = Math.round(clamp(Math.abs(rmm) * 2, 30, 400));
  } else if (xsDrag === 'p2') {
    vals.UPPER_FROM_TOP = Math.round(clamp(H - zmm, 5, H - vals.LOWER_HEIGHT - 5)); vals.UPPER_DIAMETER = Math.round(clamp(Math.abs(rmm) * 2, 30, 400));
  } else if (xsDrag[0] === 'h') {
    const i = +xsDrag[1], sg = xsDrag[2] === 'p' ? 1 : -1, c = profCtl(vals);
    const dz = (zmm - c.P[i][0]) * sg, dr = (rmm - c.P[i][1]) * sg;
    const ang = clamp(Math.round(Math.atan2(dr, Math.max(dz, 0.5)) * 180 / Math.PI), -85, 85), len = Math.max(0, Math.round(Math.hypot(Math.max(dz, 0.5), dr)));
    if (i === 1) { vals.LOWER_ANGLE = ang; vals.LOWER_LENGTH = len; } else { vals.UPPER_ANGLE = ang; vals.UPPER_LENGTH = len; }
  }
  sync(); refreshBtn();
});
function xsEnd() { if (!xsDrag) return; xsDrag = null; xsFrozen = null; drawProfile(); if (!$('rebuild').disabled) run(); }
$('xs').addEventListener('pointerup', xsEnd); $('xs').addEventListener('pointercancel', xsEnd);
drawProfile();
showView();
function askName(ext) {
  if (!curKey) return;
  wantExt = ext;
  if (named && named.cfg === built) { fetchFile(named.name); return; }      // already named: no question, just download $('dlgname').value = ''; $('dlgok').disabled = true; $('dlgwarn').textContent = '';
  $('dlg').showModal(); $('dlgname').focus();
}
$('pdf').onclick = e => { e.preventDefault(); askName('pdf'); };
$('dxf').onclick = e => { e.preventDefault(); askName('dxf'); };
$('svg').onclick = e => { e.preventDefault(); askName('svg'); };
$('dlgcancel').onclick = () => $('dlg').close();
$('dlgname').oninput = () => {
  const v = $('dlgname').value.trim(); $('dlgok').disabled = !v;
  $('dlgwarn').textContent = snapNames.includes(v) ? 'A snapshot with this name exists and will be replaced.' : '';
};
$('dlgform').onsubmit = async e => {
  e.preventDefault();
  const name = $('dlgname').value.trim(); if (!name) return;
  const r = await fetch('/api/snapshot', {method: 'POST', body: JSON.stringify({name, params: JSON.parse(built)})}).then(x => x.json()).catch(() => null);
  if (!r) { $('dlgwarn').textContent = 'Could not save the snapshot, so nothing was downloaded.'; return; }
  named = {cfg: built, name: r.name};
  $('dlg').close(); $('snapmsg').textContent = 'Saved "' + r.name + '".'; loadSnaps(r.name);
  fetchFile(r.name);
};
async function fetchFile(name) {
  const msg = $('dlmsg'); msg.className = 'derived'; msg.textContent = 'Choose where to save the file in the window that opened...';
  const r = await fetch('/api/export', {method: 'POST', body: JSON.stringify({key: curKey, view, ext: wantExt, name})}).then(x => x.json()).catch(() => ({error: 'Lost the connection to the tool.'}));
  if (r.error) { msg.className = 'warn err'; msg.textContent = r.error; return; }
  if (r.cancelled) { msg.className = 'derived'; msg.textContent = 'Not saved (you cancelled the save window).'; return; }
  msg.className = 'saved'; msg.textContent = '';
  msg.append('Saved ' + r.file + ' in ' + r.folder + '. ');
  const b = document.createElement('a'); b.href = '#'; b.textContent = 'Show in Finder';
  b.onclick = e => { e.preventDefault(); fetch('/api/reveal', {method: 'POST', body: JSON.stringify({path: r.path})}); };
  msg.append(b);
}
fetch('/api/version').then(r => r.json()).then(v => {
  if (v.git) $('ver').textContent = 'branch ' + v.branch + ' · ' + v.date + ' · ' + v.subject + (v.edited ? ' · (edited here, not saved to git)' : '');
}).catch(() => {});
$('refresh-btn').onclick = async () => {
  const btn = $('refresh-btn'), msg = $('refresh-msg');
  btn.disabled = true; msg.textContent = 'Refreshing...';
  const r = await fetch('/api/refresh', {method: 'POST', body: '{}'}).then(x => x.json()).catch(() => ({ok: false, log: 'Lost the connection.'}));
  if (!r.ok) { msg.textContent = r.log; btn.disabled = false; return; }
  msg.textContent = (r.log || '') + ' Restarting...';
  await new Promise(res => setTimeout(res, 2000));
  for (let i = 0; i < 60; i++) {
    try { const v = await fetch('/api/version', {cache: 'no-store'}); if (v.ok) { location.reload(); return; } } catch (e) {}
    await new Promise(res => setTimeout(res, 500));
  }
  msg.textContent = 'The tool did not come back. Close the window and open it again.'; btn.disabled = false;
};
run();
</script></body></html>
"""


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Port {PORT} is already in use, probably by another copy of this tool. Open http://127.0.0.1:{PORT}/")
        raise SystemExit(1)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Sea anemone tool running at {url}   (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
