"""A small page for trying out polyp sizes without editing any code.

Run:  python3 polyp_tool.py        (it opens your web browser; press Ctrl+C here to stop it)

You get fields for the cuff size, cuff height, finger length and so on. The flat pattern redraws
as you change them (about a second). Two buttons run the slower 3D simulations:
  - Inflated: what the sewn polyp looks like with air in it (about 30 seconds)
  - String pull (paused for now, switch on with POLYP_TOOL_PULL=1): the cords pulled from one hitch point
Everything it makes is saved in the folder tool-output/ next to this script, so you can
open the PDF and pictures later. Nothing outside that folder is changed.

It only listens on your own computer (127.0.0.1), and it works by running make_pattern.py
and sim_pull.py for you, so the results match what those scripts make.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tool-output")
PORT = int(os.environ.get("POLYP_TOOL_PORT", 8800))   # the skin tool uses 8765 and up, so keep clear of it

# Settings shown on the page: (name in make_pattern.py, label, unit, min, max, step, help)
PATTERN_FIELDS = [
    ("CUFF_DIAMETER", "Cuff diameter", "in", 2, 14, 0.05, "Width of the finished cuff. The tube it fits is this minus the ease."),
    ("EASE", "Cuff ease", "in", -1, 1.5, 0.125, "Extra room around the tube. About 0.5 for woven fabric."),
    ("CUFF_HEIGHT", "Cuff length", "in", 1, 8, 0.25, "Finished height of the wrist part."),
    ("FINGER_LENGTH", "Finger length", "in", 3, 14, 0.25, "On the flat piece, from crotch to tip."),
    ("SCALE", "Scale", "x", 0.2, 1.5, 0.05, "1 = full size. A smaller number makes a scale model of everything (cuff, fingers, seams, tabs)."),
    ("FINGERS", "Number of fingers", "", 3, 8, 1, "Around the cuff."),
    ("TAPER_FULLNESS", "Finger fullness", "", 0, 1.5, 0.1, "0 = straight cone sides, higher = fuller before the point."),
    ("SPLAY", "Lean out", "deg", 0, 70, 5, "How far the fingers lean out just above the cuff."),
    ("TURN_LENGTH", "Turn length", "in", 0.5, 4, 0.25, "Distance over which they lean out."),
    ("TAB_LENGTH", "Tab length", "in", 0.25, 0.5, 0.0625, "Length of each string tab on the inner seam."),
    ("TAB_COUNT", "Tabs per finger", "", 0, 8, 1, "0 = automatic: about one every 3 in, never fewer than 3."),
    ("TUNNEL_WIDTH", "Tab pocket width", "in", 0.125, 0.5, 0.0625, "Room for the cord between the seam and the tab stitching."),
]
LASER_FIELDS = [
    ("BED_W", "Bed width", "in", 0, 60, 1, "Width of your laser bed, in inches. 0 = no limit (the smallest layout)."),
    ("BED_L", "Bed length (along the grain)", "in", 0, 120, 1, "Length of the bed in the direction the fabric grain runs. 0 = no limit."),
]
PULL_ENABLED = os.environ.get("POLYP_TOOL_PULL") == "1"   # the motion simulation is paused for now
PULL_FIELDS = [
    ("HITCH", "Hitch depth", "in", 0.25, 4, 0.25, "Where the five strings meet, this far below the polyp's centre point (into the cuff)."),
    ("SOFT", "Fabric softness", "", 0.01, 1, 0.01, "1 = stiff fabric as in the first version, small = very floppy nylon."),
    ("PULL_MAX", "Pull up to", "in", 1, 14, 1, "Most the hitch is pulled down. It stops earlier if the fingers can't fold further."),
]
DEFAULTS = {"CUFF_DIAMETER": (math.pi * 5.0 + 0.5) / math.pi, "EASE": 0.5, "CUFF_HEIGHT": 3.0,
            "FINGER_LENGTH": 8.5, "FINGERS": 5, "TAPER_FULLNESS": 0.6, "SPLAY": 45, "TURN_LENGTH": 1.5,
            "TUNNEL_WIDTH": 0.25, "SCALE": 1.0, "TAB_LENGTH": 0.375, "TAB_COUNT": 0, "HITCH": 1.0, "SOFT": 0.05, "PULL_MAX": 10, "BED_W": 0, "BED_L": 0}

JOBS = {}                         # job id -> dict(state, log, files)
HEAVY = threading.Semaphore(1)    # only one simulation at a time; they use every processor core
LOCK = threading.Lock()


def git(*args, timeout=60):
    """Run a git command in this folder. Returns (ok, text)."""
    try:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def version_info():
    """Which version of the code this is, and which newer versions are on GitHub."""
    ok, _ = git("rev-parse", "--is-inside-work-tree")
    if not ok:
        return {"git": False}
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, line = git("log", "-1", "--format=%h|%cs|%s")
    sha, date, subject = (line.split("|", 2) + ["", "", ""])[:3]
    fetched, fetch_msg = git("fetch", "--prune", "origin", timeout=30)
    behind = 0
    if fetched:
        ok2, n = git("rev-list", "--count", f"HEAD..origin/{branch}")
        behind = int(n) if ok2 and n.isdigit() else 0
    _, refs = git("for-each-ref", "--sort=-committerdate", "--count=15",
                  "--format=%(refname:short)|%(committerdate:short)|%(subject)", "refs/remotes/origin")
    branches = []
    for ref in refs.splitlines():
        name, d, subj = (ref.split("|", 2) + ["", ""])[:3]
        name = name[len("origin/"):] if name.startswith("origin/") else name
        if name and name != "HEAD":
            branches.append({"name": name, "date": d, "subject": subj})
    _, dirty = git("status", "--porcelain", "--untracked-files=no")
    return {"git": True, "branch": branch, "sha": sha, "date": date, "subject": subject,
            "online": fetched, "fetch_message": "" if fetched else fetch_msg, "behind": behind,
            "branches": branches, "dirty": bool(dirty)}


def update_code(branch):
    """Switch to `branch` and bring it up to date, then restart so the new code runs."""
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch or ""):
        return False, "That branch name isn't valid."
    if any(j["state"] in ("queued", "running") and not k.startswith("pattern") for k, j in JOBS.items()):
        return False, "A simulation is still running. Wait for it to finish, then update."
    ok, out = git("status", "--porcelain", "--untracked-files=no")
    if out:
        return False, "Some files in this copy were edited on this computer, so I won't overwrite them:\n" + out
    ok, out = git("fetch", "--prune", "origin", timeout=60)
    if not ok:
        return False, "Couldn't reach GitHub. Check your internet connection.\n" + out
    _, prefix = git("rev-parse", "--show-prefix")
    if not git("cat-file", "-e", f"origin/{branch}:{prefix}polyp_tool.py")[0]:
        return False, f"The branch {branch} doesn't have the simulator in it, so I can't switch to it."
    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    ok, ahead = git("rev-list", "--count", f"origin/{branch}..HEAD")
    if cur == branch and ok and ahead.isdigit() and int(ahead) > 0:
        return False, "This copy has changes that aren't on GitHub, so I won't overwrite them."
    ok, out = git("checkout", "-B", branch, f"origin/{branch}")
    if not ok:
        return False, f"Couldn't switch to {branch}.\n" + out
    log = out
    if os.path.exists(os.path.join(HERE, "requirements.txt")):
        pip = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"],
                             cwd=HERE, capture_output=True, text=True)
        if pip.returncode != 0:
            log += "\n(The library check failed: " + pip.stderr.strip()[-300:] + ")"
    return True, log


def restart_soon():
    """Start again from the (possibly new) code in a moment, after the reply has gone out."""
    def go():
        time.sleep(1.0)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=go, daemon=True).start()


def clean(params):
    """Check the numbers from the page and turn them into make_pattern's settings."""
    p = {}
    for name, label, unit, lo, hi, step, _ in PATTERN_FIELDS + PULL_FIELDS + LASER_FIELDS:
        v = float(params.get(name, DEFAULTS[name]))
        if not lo <= v <= hi:
            raise ValueError(f"{label} must be between {lo:g} and {hi:g}")
        p[name] = v
    p["FINGERS"] = int(round(p["FINGERS"]))
    p["TAB_COUNT"] = int(round(p["TAB_COUNT"]))
    p["FIT_LETTER"] = 1 if params.get("FIT_LETTER") else 0
    p["DXF_IN"] = 1 if params.get("DXF_IN") else 0
    return p


def polyp_env(p):
    """make_pattern.py reads its settings from the POLYP variable."""
    tube = p["CUFF_DIAMETER"] - p["EASE"] / math.pi
    if tube < 0.5:
        raise ValueError("The cuff is too small for that much ease")
    keys = ["CUFF_HEIGHT", "FINGER_LENGTH", "FINGERS", "TAPER_FULLNESS", "SPLAY", "TURN_LENGTH", "TUNNEL_WIDTH", "TAB_LENGTH", "TAB_COUNT", "EASE", "SCALE", "FIT_LETTER"]
    items = [f"TUBE_DIAMETER={tube!r}"] + [f"{k}={p[k]!r}" for k in keys]
    return dict(os.environ, POLYP=",".join(items))


def run_job(job_id, kind, p, folder):
    job = JOBS[job_id]
    heavy = kind != "pattern"
    try:
        if heavy:
            job["state"] = "queued"
            HEAVY.acquire()
        job["state"] = "running"
        os.makedirs(folder, exist_ok=True)
        if kind == "pattern":
            cmd = [sys.executable, "make_pattern.py", "--out", folder, "--name", "custom", "--no-sim", "--no-dxf"]
        elif kind == "inflate":
            cmd = [sys.executable, "make_pattern.py", "--out", folder, "--name", "custom", "--no-dxf"]
        elif kind == "dxf":
            cmd = [sys.executable, "make_pattern.py", "--out", folder, "--name", "custom", "--dxf-only"]
            if p["BED_W"] and p["BED_L"]:
                cmd += ["--bed", str(p["BED_W"]), str(p["BED_L"])]
            if p["DXF_IN"]:
                cmd += ["--dxf-units", "in"]
        else:
            cmd = [sys.executable, "sim_pull.py", "--out", folder, "--name", "custom",
                   "--hitch", str(p["HITCH"]), "--soft", str(p["SOFT"]), "--pull-max", str(p["PULL_MAX"]), "--steps", str(int(p["PULL_MAX"]))]
        proc = subprocess.Popen(cmd, cwd=HERE, env=polyp_env(p), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            job["log"] += line
        proc.wait()
        if proc.returncode != 0:
            job["state"] = "error"
        else:
            job["state"] = "done"
            job["files"] = sorted(os.listdir(folder))
            if heavy:
                open(os.path.join(folder, f".done-{kind}"), "w").close()
    except Exception as e:                       # show any problem on the page
        job["log"] += f"\n{e}"
        job["state"] = "error"
    finally:
        if heavy:
            HEAVY.release()


def start(kind, params):
    p = clean(params)
    polyp_env(p)                                 # raises if the numbers don't make sense
    relevant = {k: p[k] for k in sorted(p) if (kind == "pull" or k not in ("HITCH", "PULL_MAX", "SOFT"))
                and (kind == "dxf" or k not in ("BED_W", "BED_L", "DXF_IN"))}
    key = hashlib.sha1(json.dumps(relevant, sort_keys=True).encode()).hexdigest()[:12]
    job_id = f"{kind}-{key}"
    folder = os.path.join(OUT, key)
    with LOCK:
        job = JOBS.get(job_id)
        if job and job["state"] in ("queued", "running", "done"):
            return job_id, key                   # already running, or already made
        if kind != "pattern" and os.path.exists(os.path.join(folder, f".done-{kind}")):
            JOBS[job_id] = dict(state="done", log="(made earlier)\n", files=sorted(os.listdir(folder)))
            return job_id, key
        JOBS[job_id] = dict(state="queued", log="", files=[])
    threading.Thread(target=run_job, args=(job_id, kind, p, folder), daemon=True).start()
    return job_id, key


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            meta = dict(pattern=PATTERN_FIELDS, laser=LASER_FIELDS, pull=PULL_FIELDS if PULL_ENABLED else [], pull_enabled=PULL_ENABLED, defaults=DEFAULTS)
            self.send(200, PAGE.replace("__META__", json.dumps(meta)), "text/html; charset=utf-8")
        elif path == "/api/version":
            self.send(200, json.dumps(version_info()), "application/json")
        elif path.startswith("/api/job/"):
            job = JOBS.get(path.split("/")[-1])
            self.send(200 if job else 404, json.dumps(job or {"state": "unknown"}), "application/json")
        elif path.startswith("/out/"):
            parts = path.split("/")[2:]
            f = os.path.join(OUT, *parts) if len(parts) == 2 and not any(x.startswith(".") for x in parts) else None
            if f and os.path.isfile(f):
                ctype = {"png": "image/png", "pdf": "application/pdf", "csv": "text/csv", "dxf": "application/dxf"}.get(f.rsplit(".", 1)[-1], "application/octet-stream")
                self.send(200, open(f, "rb").read(), ctype)
            else:
                self.send(404, "not found", "text/plain")
        else:
            self.send(404, "not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path == "/api/update":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            ok, log = update_code(body.get("branch"))
            self.send(200, json.dumps({"ok": ok, "log": log}), "application/json")
            if ok:
                restart_soon()
            return
        if urlparse(self.path).path != "/api/run":
            return self.send(404, "not found", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if body["job"] not in ("pattern", "inflate", "dxf") + (("pull",) if PULL_ENABLED else ()):
                raise ValueError("unknown job")
            job_id, key = start(body["job"], body.get("params", {}))
            self.send(200, json.dumps({"id": job_id, "key": key}), "application/json")
        except (ValueError, KeyError) as e:
            self.send(400, json.dumps({"error": str(e)}), "application/json")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Polyp tool</title>
<style>
  :root { --bg:#f6f4f1; --card:#fff; --ink:#222; --mute:#6b665f; --line:#ddd8d0; --accent:#c4492f; --blue:#2b6cb0; }
  @media (prefers-color-scheme: dark) { :root { --bg:#1b1a19; --card:#262523; --ink:#eee; --mute:#a59f96; --line:#3a3835; --accent:#e5694e; --blue:#6aa7e8; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.45 system-ui, sans-serif; }
  header { padding:14px 20px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:18px; } header p { margin:2px 0 0; color:var(--mute); font-size:13px; }
  main { display:grid; grid-template-columns: 330px 1fr; gap:16px; padding:16px; max-width:1500px; margin:0 auto; }
  @media (max-width: 860px) { main { grid-template-columns: 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
  .card h2 { margin:0 0 8px; font-size:15px; }
  .field { margin:10px 0; } .field label { display:flex; justify-content:space-between; font-weight:600; font-size:13px; }
  .field input[type=number] { width:78px; font:inherit; padding:2px 4px; border:1px solid var(--line); border-radius:5px; background:var(--bg); color:var(--ink); }
  .field input[type=range] { width:100%; accent-color:var(--accent); }
  .field small { color:var(--mute); display:block; line-height:1.3; }
  .derived { font-size:13px; color:var(--mute); border-top:1px solid var(--line); margin-top:10px; padding-top:8px; }
  .derived b { color:var(--ink); font-weight:600; }
  button { font:inherit; font-weight:600; padding:8px 12px; border-radius:7px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; width:100%; margin-top:8px; }
  button.secondary { background:transparent; color:var(--accent); }
  button:disabled { opacity:.5; cursor:default; }
  .results { display:grid; gap:16px; }
  .results img { max-width:100%; height:auto; border-radius:6px; background:#fff; display:block; margin:6px auto; }
  .status { font-size:13px; color:var(--mute); white-space:pre-wrap; font-family:ui-monospace, monospace; max-height:150px; overflow:auto; margin-top:6px; }
  .stale img { opacity:.35; } .stale .tag { display:inline-block; }
  .tag { display:none; background:var(--accent); color:#fff; font-size:11px; padding:1px 7px; border-radius:9px; margin-left:8px; vertical-align:middle; }
  a { color:var(--blue); } .err { color:#c0392b; }
  .reset { background:none; border:none; color:var(--mute); text-decoration:underline; font-weight:400; width:auto; padding:0; margin:8px 0 0; }
</style></head><body>
<header><h1>Polyp tool</h1><p>Change a setting and the flat pattern redraws. Use the buttons for the 3D simulations. Files are saved in <code>tool-output/</code>.</p></header>
<main>
  <div>
    <div class="card" id="version-card" style="margin-bottom:16px"><h2>Version</h2>
      <div id="version-text" class="derived" style="border:none;margin:0;padding:0">Checking GitHub...</div>
      <div class="field" style="margin-bottom:0"><select id="branch-select" style="width:100%;font:inherit;padding:4px;border:1px solid var(--line);border-radius:5px;background:var(--bg);color:var(--ink)"></select></div>
      <button id="update-btn" class="secondary">Get latest changes</button>
      <div class="status" id="update-log"></div></div>
    <div class="card"><h2>Polyp size</h2><div id="pattern-fields"></div>
      <label class="field" style="display:flex;gap:8px;align-items:center;font-weight:600;font-size:13px"><input type="checkbox" id="fit-letter"> Fit on one 8.5 x 11 in page</label>
      <small class="muted" style="display:block;color:var(--mute)">Picks the scale for you, so the printed pattern fits one sheet. Handy for paper prototypes.</small>
      <div class="derived" id="derived"></div>
      <button class="reset" id="reset">Reset to the default design</button></div>
    <div class="card" id="card-sim-buttons" style="margin-top:16px"><h2>Simulation</h2>
      <button id="run-inflate" class="secondary">Simulate inflated (about 30 s)</button></div>
    <div class="card" id="card-laser-settings" style="margin-top:16px"><h2>Laser cutter (DXF)</h2>
      <div class="muted" style="font-size:13px;color:var(--mute)">Lays out all the pieces on one sheet, cut lines only. Set your bed size, or leave it at 0.</div>
      <div id="laser-fields"></div>
      <label class="field" style="display:flex;gap:8px;align-items:center;font-size:13px"><input type="checkbox" id="dxf-in"> Write the DXF in inches (default: millimetres)</label>
      <button id="run-dxf">Make laser files (about 30 s)</button></div>
    <div class="card" id="card-pull-settings" style="margin-top:16px"><h2>String pull</h2><div id="pull-fields"></div>
      <button id="run-pull">Simulate string pull (about 2 min)</button></div>
  </div>
  <div class="results">
    <div class="card" id="card-pattern"><h2>Flat pattern <span class="tag">updating</span></h2>
      <div id="out-pattern"></div><div class="status" id="log-pattern"></div></div>
    <div class="card" id="card-inflate"><h2>Inflated <span class="tag">settings changed, run again</span></h2>
      <div id="out-inflate" style="color:var(--mute)">Press "Simulate inflated".</div><div class="status" id="log-inflate"></div></div>
    <div class="card" id="card-dxf"><h2>Laser sheet <span class="tag">settings changed, run again</span></h2>
      <div id="out-dxf" style="color:var(--mute)">Press "Make laser files". You get a DXF with one piece and a DXF with all the pieces nested on one sheet. Only the red cut outline is drawn, with the slit to the dot included in it.</div>
      <div class="status" id="log-dxf"></div></div>
    <div class="card" id="card-pull"><h2>String pull <span class="tag">settings changed, run again</span></h2>
      <div id="out-pull" style="color:var(--mute)">Press "Simulate string pull". The five cords run from the fingertips through the tabs to one hitch point inside the cuff. The hitch is pulled down in steps.</div>
      <div class="status" id="log-pull"></div></div>
  </div>
</main>
<script>
const META = __META__;
const state = {};
const $ = id => document.getElementById(id);
function field(f) {
  const [name, label, unit, lo, hi, step, help] = f;
  const d = document.createElement('div'); d.className = 'field';
  const v = META.defaults[name];
  d.innerHTML = `<label>${label}<span><input type="number" id="n-${name}" min="${lo}" max="${hi}" step="${step}"> ${unit}</span></label>
    <input type="range" id="r-${name}" min="${lo}" max="${hi}" step="${step}"><small>${help}</small>`;
  return d;
}
function build(id, fields) { fields.forEach(f => $(id).appendChild(field(f))); }
build('pattern-fields', META.pattern); build('pull-fields', META.pull); build('laser-fields', META.laser);
if (!META.pull_enabled) { $('card-pull-settings').hidden = true; $('card-pull').hidden = true; }
const names = [...META.pattern, ...META.pull, ...META.laser].map(f => f[0]);
function setAll(vals) { names.forEach(n => { state[n] = vals[n]; show(n); }); }
function show(n) {
  const v = state[n], r = Math.round(v * 10000) / 10000;
  $('n-' + n).value = n === 'CUFF_DIAMETER' ? v.toFixed(2) : r; $('r-' + n).value = v;
}
names.forEach(n => {
  const set = (val) => { if (!isFinite(val)) return; state[n] = val; $('r-' + n).value = val; changed(n); };
  $('n-' + n).addEventListener('input', e => set(parseFloat(e.target.value)));
  $('r-' + n).addEventListener('input', e => { set(parseFloat(e.target.value)); show(n); });
});
$('reset').onclick = () => { setAll(META.defaults); changed('CUFF_DIAMETER'); };
function derived() {
  const k = state.FIT_LETTER ? (state.fitScale || 1) : state.SCALE;
  const c = state.CUFF_DIAMETER * Math.PI * k, tube = (state.CUFF_DIAMETER - state.EASE / Math.PI) * k;
  const w = c / state.FINGERS;
  $('derived').innerHTML = (k !== 1 ? `<b>Scale model, ${Math.round(k * 100)} % of full size.</b><br>` : '') +
    `Cuff goes round <b>${c.toFixed(2)} in</b>, fits a <b>${tube.toFixed(2)} in</b> tube.<br>` +
    `Each piece is <b>${w.toFixed(2)} in</b> wide at the crotch.`;
}
$('fit-letter').addEventListener('change', e => {
  state.FIT_LETTER = e.target.checked ? 1 : 0;
  $('n-SCALE').disabled = $('r-SCALE').disabled = e.target.checked;
  changed('SCALE');
});
let timer = null;
function changed(n) {
  derived();
  const pullOnly = ['HITCH', 'PULL_MAX', 'SOFT'].includes(n), laserOnly = ['BED_W', 'BED_L'].includes(n);
  const heavy = pullOnly ? ['pull'] : laserOnly ? ['dxf'] : ['inflate', 'pull', 'dxf'];
  heavy.forEach(k => $('card-' + k).classList.add('stale'));
  if (pullOnly || laserOnly) return;                                // these don't change the flat pattern
  $('card-pattern').classList.add('stale');
  clearTimeout(timer); timer = setTimeout(() => run('pattern'), 350);
}
async function run(kind) {
  const log = $('log-' + kind), out = $('out-' + kind), card = $('card-' + kind);
  const btn = $('run-' + kind); if (btn) btn.disabled = true;
  const my = ++state['seq-' + kind];
  let r;
  try {
    r = await fetch('/api/run', {method: 'POST', body: JSON.stringify({job: kind, params: state})}).then(x => x.json());
  } catch (e) { log.innerHTML = '<span class="err">Lost the connection to the tool.</span>'; if (btn) btn.disabled = false; return; }
  if (r.error) { log.innerHTML = '<span class="err">' + r.error + '</span>'; if (btn) btn.disabled = false; card.classList.remove('stale'); return; }
  for (;;) {
    const j = await fetch('/api/job/' + r.id).then(x => x.json());
    if (state['seq-' + kind] !== my) return;                 // a newer request replaced this one
    log.textContent = (j.state === 'queued' ? 'Waiting for another simulation to finish...\n' : '') + j.log;
    log.scrollTop = log.scrollHeight;
    if (j.state === 'done') { finish(kind, r.key, j); break; }
    if (j.state === 'error') { log.innerHTML = '<span class="err">Something went wrong:</span>\n' + j.log; card.classList.remove('stale'); break; }
    await new Promise(res => setTimeout(res, kind === 'pattern' ? 300 : 1500));
  }
  if (btn) btn.disabled = false;
}
function finish(kind, key, j) {
  const base = '/out/' + key + '/', t = Date.now();
  const has = f => j.files.includes(f);
  let html = '';
  if (kind === 'pattern') {
    html = `<img src="${base}custom-piece.png?${t}" alt="flat piece">
      <a href="${base}custom-pattern.pdf" target="_blank">Open the printable pattern (PDF, print at 100 %)</a>`;
    const m = /^scale ([0-9.]+)/m.exec(j.log); state.fitScale = m ? parseFloat(m[1]) : 1; derived();
    $('log-pattern').textContent = j.log.split('\n').filter(l => l.startsWith('cut size') || l.startsWith('string seam') || l.startsWith('scale')).join('\n');
  } else if (kind === 'dxf') {
    html = `<img src="${base}custom-sheet.png?${t}" alt="laser sheet with all the pieces nested">` +
      `<img src="${base}custom-piece-cut.png?${t}" alt="one laser piece" style="max-height:520px;width:auto">` +
      `<a href="${base}custom-sheet.dxf" target="_blank">Download all pieces (DXF, inches)</a> &middot; <a href="${base}custom-piece.dxf" target="_blank">one piece (DXF)</a>`;
    $('log-dxf').textContent = j.log.split('\n').filter(l => l.startsWith('DXF')).join('\n');
  } else if (kind === 'inflate') {
    html = `<img src="${base}custom-3d.png?${t}" alt="inflated polyp">`;
    $('log-inflate').textContent = '';
  } else {
    html = `<img src="${base}custom-pull.png?${t}" alt="string pull">` +
      (has('custom-pull.csv') ? `<a href="${base}custom-pull.csv" target="_blank">Open the numbers (CSV)</a>` : '');
    $('log-pull').textContent = j.log.split('\n').filter(l => l.startsWith('pull ') || l.startsWith('centre')).join('\n');
  }
  $('out-' + kind).innerHTML = html; $('out-' + kind).style.color = '';
  $('card-' + kind).classList.remove('stale');
}
['pattern', 'inflate', 'pull', 'dxf'].forEach(k => state['seq-' + k] = 0);
$('run-inflate').onclick = () => run('inflate');
$('run-dxf').onclick = () => run('dxf');
$('dxf-in').addEventListener('change', e => { state.DXF_IN = e.target.checked ? 1 : 0; changed('BED_W'); });
$('run-pull').onclick = () => run('pull');
async function loadVersion(keep) {
  let v;
  try { v = await fetch('/api/version').then(x => x.json()); } catch (e) { return false; }
  const box = $('version-text'), sel = $('branch-select');
  if (!v.git) { box.textContent = 'This copy isn\'t connected to GitHub, so it can\'t update itself.'; $('update-btn').disabled = true; sel.hidden = true; return true; }
  const want = keep || v.branch;
  sel.innerHTML = '';
  const names = v.branches.map(b => b.name); if (!names.includes(v.branch)) names.unshift(v.branch);
  names.forEach(n => { const b = v.branches.find(x => x.name === n) || {}; const o = document.createElement('option');
    o.value = n; o.textContent = n + (b.date ? '  (' + b.date + ')' : '') + (n === v.branch ? '  - running' : ''); if (n === want) o.selected = true; sel.appendChild(o); });
  const msg = !v.online ? 'Offline, showing what is on this computer.' : v.behind ? '<b>' + v.behind + ' newer change' + (v.behind > 1 ? 's' : '') + ' available</b> on this branch.' : 'Up to date.';
  box.innerHTML = 'Running <b>' + v.branch + '</b><br>last change ' + v.date + ': ' + (v.subject || '').replace(/</g, '&lt;') + '<br>' + msg;
  return true;
}
$('update-btn').onclick = async () => {
  const log = $('update-log'), btn = $('update-btn'); btn.disabled = true; log.textContent = 'Updating...';
  const branch = $('branch-select').value;
  const r = await fetch('/api/update', {method: 'POST', body: JSON.stringify({branch})}).then(x => x.json()).catch(() => ({ok: false, log: 'Lost the connection.'}));
  if (!r.ok) { log.textContent = r.log; btn.disabled = false; return; }
  log.textContent = 'Updated. Restarting the tool...';
  for (let i = 0; i < 60; i++) {                             // wait for it to come back, then reload
    await new Promise(res => setTimeout(res, 1000));
    try { const x = await fetch('/api/version'); if (x.ok) { location.reload(); return; } } catch (e) {}
  }
  log.textContent = 'The tool did not come back. Close this tab and open the link again.'; btn.disabled = false;
};
setAll(META.defaults); derived(); run('pattern'); loadVersion();
</script></body></html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Port {PORT} is already in use, probably by another copy of this tool. "
              "Close it and try again.")
        sys.exit(1)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Polyp tool running at {url}\nPress Ctrl+C here to stop it.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
