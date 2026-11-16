"""A small page for trying out spiral-cone polyp sizes. No code editing needed.

Run:  python3 spiral_tool.py     (opens your browser at http://127.0.0.1:8820/; Ctrl+C stops it)

Change a number and the flat pattern, the 3D sketch and the checks redraw in about two seconds.
You can download the SVG (true size, for the laser). Results are saved in tool-output/ next to this
script (not kept in git). It only listens on your own computer (127.0.0.1) and runs spiral_cone.py
for you, so the results match that script.
"""
import hashlib
import json
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
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "tool-output")
PORT = int(os.environ.get("SPIRAL_TOOL_PORT", 8820))   # polyp tool 8800, skin tool 8765+; each tool has its own block
import spiral_cone as S

# (setting, label, unit, min, max, step, help)
FIELDS = [
    ("LENGTH", "Cone length", "in", 4, 30, 0.5, "Height above the cuff line, including the straight-seam part at the top."),
    ("BASE_DIAMETER", "Cuff line diameter", "in", 2, 12, 0.05, "Inside diameter where the cuff meets the cone (the tube fit). 130 mm = 5.12 in."),
    ("TIP_DIAMETER", "Tip diameter", "in", 0, 6, 0.25, "0 = the cone comes to a point."),
    ("PITCH_BASE", "Pitch at the base", "in", 0.5, 8, 0.1, "Height gained per turn of the seam at the bottom. Bigger = more open spiral."),
    ("PITCH_TIP", "Pitch at the end of the spiral", "in", 0.5, 8, 0.1, "Same where the spiral ends. Smaller than the base = tighter wind toward the tip."),
    ("PITCH_CURVE", "Pitch curve", "", 0.3, 3, 0.1, "1 = changes evenly. Above 1 stays open longer, then tightens near the end."),
    ("STRAIGHT_LENGTH", "Straight seam length", "in", 0, 6, 0.25, "The last part of the cone has one straight seam instead of a spiral."),
    ("TRANSITION", "Spiral to straight blend", "in", 0, 6, 0.25, "The spiral fades into the straight seam over this length. 0 = a sharp corner."),
    ("FRILL_START", "Frill starts at", "in", 0, 9, 0.25, "Inches up the axis from the cuff line. The frill runs to the end of the spiral."),
    ("RUFFLE_WIDTH", "Frill strip width", "in", 1, 6, 0.25, "Cut width: the solid seam allowance plus the fringe that stands out."),
    ("SEAM", "Seam allowance", "in", 0.25, 1, 0.125, "On every edge except the open end of the cuff."),
    ("CUFF_HEIGHT", "Cuff height", "in", 1, 5, 0.25, "Finished height of the cuff."),
    ("CUFF_IN_STRIP", "Cuff part of the strip", "1/0", 0, 1, 1, "1 = the cuff is the bottom of the cone strip (flares slightly). 0 = separate straight cuff band."),
    ("TAB_SIZE", "Alignment tab size", "in", 0.25, 1, 0.125, "Square tabs along the seams to tack the pieces together."),
    ("TAB_SPACING", "Tab spacing", "in", 2, 12, 0.5, "About one tab every this many inches of seam."),
    ("FRINGE_WIDTH", "Fringe strip width", "in", 0.1, 1, 0.05, "The part of the frill that stands out is slit into strips this wide."),
    ("FABRIC_WIDTH", "Fabric width", "in", 20, 120, 1, "Usable width of the fabric. Only used for the fit check."),
]
DEFAULTS = {k: getattr(S, k) for k in S.NAMES}
LOCK = threading.Lock()


def run_pattern(params):
    """Make the pattern for these settings. Returns (folder name, result dict)."""
    clean = {}
    for name, *_ in FIELDS:
        v = float(params.get(name, DEFAULTS[name]))
        if not (v == v) or abs(v) > 1e4:
            raise ValueError(f"{name} is not a sensible number")
        clean[name] = v
    key = hashlib.sha1(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:12]
    folder = os.path.join(OUT, key)
    with LOCK:                                   # the script keeps its settings in module variables
        for k, v in {**DEFAULTS, **clean}.items():
            setattr(S, k, v)
        info, text = S.make(folder, "spiral-cone")
    return key, {"text": text, "warnings": info["warnings"], "seam": info["seam_total"], "turns": info["turns"]}


# --- version card, shared with the polyp tool (same repo, same git commands)
try:                                        # only needed for the "Get latest changes" version card
    sys.path.insert(0, os.path.join(HERE, "..", "fabric-pattern"))
    import polyp_tool as PT
except ImportError:                         # stand-alone copy of this folder: no version card, everything else works
    PT = None


def git(*args, timeout=60):
    """Run a git command in THIS folder (so path prefixes are right). Returns (ok, text)."""
    try:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def version():
    """Version info for the page: which branch we are on, and which branches have this tool (newest first)."""
    v = PT.version_info() if PT else {"git": False}
    if not v.get("git"):
        return v
    _, prefix = git("rev-parse", "--show-prefix")
    keep = [b for b in v["branches"] if git("cat-file", "-e", f"origin/{b['name']}:{prefix}spiral_tool.py")[0]]
    v["branches"] = keep
    v["newest"] = keep[0]["name"] if keep else None
    return v


def update_code(branch):
    """Switch to `branch` and bring it up to date, like the polyp tool's button."""
    if PT is None:
        return False, "This copy is stand-alone (not inside the Coral repo), so there is nothing to update."
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch or ""):
        return False, "That branch name isn't valid."
    ok, out = git("status", "--porcelain", "--untracked-files=no")
    if out:
        return False, "Some files in this copy were edited on this computer, so I won't overwrite them:\n" + out
    ok, out = git("fetch", "--prune", "origin", timeout=60)
    if not ok:
        return False, "Couldn't reach GitHub. Check your internet connection.\n" + out
    _, prefix = git("rev-parse", "--show-prefix")
    if not git("cat-file", "-e", f"origin/{branch}:{prefix}spiral_tool.py")[0]:
        return False, f"The branch {branch} doesn't have the spiral-cone tool in it, so I can't switch to it."
    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    ok, ahead = git("rev-list", "--count", f"origin/{branch}..HEAD")
    if cur == branch and ok and ahead.isdigit() and int(ahead) > 0:
        return False, "This copy has changes that aren't on GitHub, so I won't overwrite them."
    ok, out = git("checkout", "-B", branch, f"origin/{branch}")
    if not ok:
        return False, f"Couldn't switch to {branch}.\n" + out
    pip = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", os.path.join(HERE, "requirements.txt")],
                         capture_output=True, text=True)
    if pip.returncode != 0:
        out += "\n(The library check failed: " + pip.stderr.strip()[-300:] + ")"
    return True, out


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
            meta = dict(fields=FIELDS, defaults=DEFAULTS)
            self.send(200, PAGE.replace("__META__", json.dumps(meta)), "text/html; charset=utf-8")
        elif path == "/api/version":
            self.send(200, json.dumps(version()), "application/json")
        elif path.startswith("/out/"):
            parts = path.split("/")[2:]
            ok = len(parts) == 2 and re.fullmatch(r"[0-9a-f]{12}", parts[0]) and parts[1].startswith("spiral-cone.")
            f = os.path.join(OUT, *parts) if ok else None
            if f and os.path.isfile(f):
                ext = f.rsplit(".", 1)[-1]
                ctype = {"png": "image/png", "svg": "image/svg+xml", "txt": "text/plain"}.get(ext, "application/octet-stream")
                extra = {"Content-Disposition": 'attachment; filename="spiral-cone.svg"'} if ext == "svg" and "dl=1" in self.path else None
                self.send(200, open(f, "rb").read(), ctype, extra)
            else:
                self.send(404, "not found", "text/plain")
        else:
            self.send(404, "not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if path == "/api/update":
            ok, log = update_code(body.get("branch"))
            self.send(200, json.dumps({"ok": ok, "log": log}), "application/json")
            if ok:
                restart_soon()
        elif path == "/api/run":
            try:
                key, res = run_pattern(body.get("params", {}))
                self.send(200, json.dumps({"key": key, **res}), "application/json")
            except (ValueError, SystemExit, TypeError) as e:
                self.send(400, json.dumps({"error": str(e) or "Those settings don't make a valid cone."}), "application/json")
        else:
            self.send(404, "not found", "text/plain")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Spiral-cone polyp tool</title>
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
  button { font:inherit; font-weight:600; padding:8px 12px; border-radius:7px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; width:100%; margin-top:8px; }
  button.secondary { background:transparent; color:var(--accent); }
  .results { display:grid; gap:16px; align-content:start; }
  .results img { max-width:100%; height:auto; border-radius:6px; background:#fff; display:block; margin:6px auto; }
  pre { font:12.5px/1.4 ui-monospace, monospace; white-space:pre-wrap; margin:6px 0 0; color:var(--mute); }
  .warn { background:#fff3cd; color:#5c4400; border-radius:6px; padding:6px 10px; margin:6px 0; font-size:13px; }
  .status { font-size:13px; color:var(--mute); white-space:pre-wrap; font-family:ui-monospace, monospace; max-height:150px; overflow:auto; margin-top:6px; }
  .stale img { opacity:.35; } a { color:var(--blue); } .err { color:#c0392b; }
  .reset { background:none; border:none; color:var(--mute); text-decoration:underline; font-weight:400; width:auto; padding:0; margin:8px 0 0; }
  .derived { font-size:13px; color:var(--mute); }
</style></head><body>
<header><h1>Spiral-cone polyp tool</h1><p>Change a setting and the flat pattern, 3D sketch and checks redraw. Download the SVG for the laser.</p></header>
<main>
  <div>
    <div class="card" style="margin-bottom:16px"><h2>Version</h2>
      <div id="version-text" class="derived">Checking GitHub...</div>
      <div class="field" style="margin-bottom:0"><select id="branch-select" style="width:100%;font:inherit;padding:4px;border:1px solid var(--line);border-radius:5px;background:var(--bg);color:var(--ink)"></select></div>
      <label class="field" style="display:flex;gap:8px;align-items:center;font-weight:600;font-size:13px;margin:8px 0 0"><input type="checkbox" id="auto" checked> Open the newest version automatically</label>
      <button id="update-btn" class="secondary">Get latest changes</button>
      <div class="status" id="update-log"></div></div>
    <div class="card"><h2>Cone and ruffle</h2><div id="fields"></div>
      <button class="reset" id="reset">Reset to the starting values</button></div>
  </div>
  <div class="results">
    <div class="card" id="card"><h2>Pattern <span id="busy" class="derived"></span></h2>
      <div id="warnings"></div>
      <img id="pic" alt="">
      <p><a id="svg" href="#" download>Download SVG (true size, for the laser)</a></p>
      <pre id="text"></pre></div>
  </div>
</main>
<script>
const META = __META__;
const $ = id => document.getElementById(id);
const vals = {...META.defaults};
let timer = null, seq = 0;
for (const [name, label, unit, lo, hi, step, help] of META.fields) {
  const d = document.createElement('div'); d.className = 'field';
  d.innerHTML = `<label>${label}<span><input type="number" id="n-${name}" min="${lo}" max="${hi}" step="${step}"> ${unit}</span></label>
    <input type="range" id="r-${name}" min="${lo}" max="${hi}" step="${step}"><small>${help}</small>`;
  $('fields').appendChild(d);
  const n = d.querySelector('input[type=number]'), r = d.querySelector('input[type=range]');
  const set = v => { vals[name] = parseFloat(v); n.value = +(+v).toFixed(3); r.value = v; schedule(); };
  n.oninput = () => { if (n.value !== '') set(n.value); }; r.oninput = () => set(r.value);
  n.value = +(+vals[name]).toFixed(3); r.value = vals[name];
}
function sync() { for (const [name] of META.fields) { $('n-' + name).value = +(+vals[name]).toFixed(3); $('r-' + name).value = vals[name]; } }
$('reset').onclick = () => { Object.assign(vals, META.defaults); sync(); schedule(); };
function schedule() { clearTimeout(timer); $('card').classList.add('stale'); timer = setTimeout(run, 500); }
async function run() {
  const me = ++seq; $('busy').textContent = 'updating...';
  const r = await fetch('/api/run', {method: 'POST', body: JSON.stringify({params: vals})}).then(x => x.json()).catch(() => ({error: 'Lost the connection to the tool.'}));
  if (me !== seq) return;
  $('busy').textContent = ''; $('card').classList.remove('stale');
  if (r.error) { $('warnings').innerHTML = '<div class="warn err">' + r.error + '</div>'; return; }
  $('warnings').innerHTML = r.warnings.map(w => '<div class="warn">' + w + '</div>').join('');
  $('pic').src = '/out/' + r.key + '/spiral-cone.png';
  $('svg').href = '/out/' + r.key + '/spiral-cone.svg?dl=1';
  $('text').textContent = r.text;
}
let auto = true; try { auto = localStorage.getItem('auto') !== '0'; } catch (e) {}
$('auto').checked = auto;
$('auto').onchange = () => { try { localStorage.setItem('auto', $('auto').checked ? '1' : '0'); } catch (e) {} };
async function doUpdate(branch) {
  $('update-btn').disabled = true; $('update-log').textContent = 'Getting ' + branch + '...';
  const r = await fetch('/api/update', {method: 'POST', body: JSON.stringify({branch})}).then(x => x.json()).catch(() => ({ok: false, log: 'Lost the connection.'}));
  $('update-log').textContent = r.log; $('update-btn').disabled = false;
  if (!r.ok) return;
  $('update-log').textContent += '\nRestarting...';
  for (let i = 0; i < 40; i++) { await new Promise(s => setTimeout(s, 1000)); try { const x = await fetch('/api/version'); if (x.ok) { location.reload(); return; } } catch (e) {} }
}
async function loadVersion() {
  let v; try { v = await fetch('/api/version').then(x => x.json()); } catch (e) { return false; }
  if (!v.git) { $('version-text').textContent = 'Not running from a git copy, so no updates here.'; return true; }
  const target = v.newest || v.branch;
  const stale = v.online && (target !== v.branch || v.behind > 0);
  $('version-text').innerHTML = `Branch <b>${v.branch}</b>, ${v.sha}, ${v.date}<br>${v.subject}` +
    (v.online ? (stale ? `<br><b>A newer version is available (${target}).</b>` : '<br>This is the newest version.') : '<br>Offline: could not reach GitHub.');
  $('branch-select').innerHTML = v.branches.map(b => `<option ${b.name === v.branch ? 'selected' : ''}>${b.name}</option>`).join('');
  if (stale && $('auto').checked && !v.dirty && !window.__tried) { window.__tried = true; doUpdate(target); }
  return true;
}
$('update-btn').onclick = () => doUpdate($('branch-select').value);
loadVersion(); run();
</script></body></html>
"""


def main():
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print(f"Port {PORT} is already in use, probably by another copy of this tool. Open http://127.0.0.1:{PORT}/")
        raise SystemExit(1)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Spiral-cone tool running at {url}   (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
