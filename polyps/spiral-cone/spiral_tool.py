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

# (section, setting, label, unit, min, max, step)  -- all lengths in millimetres
FIELDS = [
    ("Cone shape", "LENGTH", "Cone length", "mm", 100, 800, 5),
    ("Cone shape", "BASE_DIAMETER", "Cuff line diameter", "mm", 50, 300, 1),
    ("Cone shape", "TIP_DIAMETER", "Tip diameter", "mm", 0, 150, 5),
    ("Cone shape", "CUFF_HEIGHT", "Cuff height", "mm", 25, 125, 5),
    ("Cone shape", "CUFF_IN_STRIP", "Cuff in the strip (1 yes, 0 no)", "", 0, 1, 1),
    ("Seam", "PITCH_BASE", "Pitch at the base", "mm", 10, 200, 1),
    ("Seam", "PITCH_TIP", "Pitch at the end of the spiral", "mm", 10, 200, 1),
    ("Seam", "PITCH_CURVE", "Pitch curve", "", 0.3, 3, 0.1),
    ("Seam", "STRAIGHT_LENGTH", "Straight seam length", "mm", 0, 150, 5),
    ("Seam", "TRANSITION", "Spiral to straight blend", "mm", 0, 150, 5),
    ("Seam", "SEAM", "Seam allowance", "mm", 6, 25, 1),
    ("Seam", "FABRIC_WIDTH", "Fabric width (fit check)", "mm", 500, 3000, 10),
    ("Frill", "FRILL_START", "Frill starts at (up from cuff line)", "mm", 0, 225, 5),
    ("Frill", "RUFFLE_WIDTH", "Frill strip width (cut)", "mm", 25, 150, 1),
    ("Frill", "FRINGE_WIDTH", "Fringe strip width", "mm", 3, 25, 0.5),
    ("Tabs", "TAB_SIZE", "Tab size", "mm", 6, 25, 1),
    ("Tabs", "TAB_SPACING", "Tab spacing", "mm", 50, 300, 5),
]
DEFAULTS = {k: getattr(S, k) for k in S.NAMES}
LOCK = threading.Lock()


def run_pattern(params):
    """Make the pattern for these settings. Returns (folder name, result dict)."""
    clean = {}
    for _sec, name, *_ in FIELDS:
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
        if path == "/api/refresh":
            ok, log = refresh_code()
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
  .derived { font-size:13px; color:var(--mute); }
</style></head><body>
<header><h1>Cone worm</h1><span class="derived">Spiral-cone polyp pattern. Sizes in millimetres. Type them, press Rebuild, download the SVG for the laser.</span>
  <span id="ver" class="derived" style="margin-left:auto"></span>
  <button id="refresh-btn" title="Load the newest version of the tool (anything Claude changed or pushed)">Refresh tool</button>
  <span id="refresh-msg" class="derived"></span></header>
<main>
  <div>
    <div class="card sticky"><div id="dirty" class="warn" style="display:none">Sizing changed. Press Rebuild.</div>
      <button id="rebuild">Rebuild</button>
      <button class="reset" id="reset">Reset to the starting values</button></div>
    <div id="sections"></div>
  </div>
  <div class="results">
    <div class="card" id="card"><h2>Pattern <span id="busy" class="derived"></span></h2>
      <div id="warnings"></div>
      <img id="pic" alt="">
      <p><a id="svg" href="#" download>Download SVG (true size in mm, for the laser)</a></p>
      <pre id="text"></pre></div>
  </div>
</main>
<script>
const META = __META__;
const $ = id => document.getElementById(id);
const vals = {...META.defaults};
let seq = 0;
const secs = {};
for (const [sec, name, label, unit, lo, hi, step] of META.fields) {
  if (!secs[sec]) { const c = document.createElement('div'); c.className = 'card'; c.style.marginTop = '12px'; c.innerHTML = `<h2>${sec}</h2>`; $('sections').appendChild(c); secs[sec] = c; }
  const d = document.createElement('div'); d.className = 'field';
  d.innerHTML = `<label>${label}<span><input type="number" id="n-${name}" min="${lo}" max="${hi}" step="${step}"> ${unit}</span></label>`;
  secs[sec].appendChild(d);
  const n = d.querySelector('input');
  n.value = +(+vals[name]).toFixed(3);
  n.oninput = () => { if (n.value !== '') { vals[name] = parseFloat(n.value); dirty(true); } };
  n.onkeydown = e => { if (e.key === 'Enter') run(); };
}
function dirty(on) { $('dirty').style.display = on ? 'block' : 'none'; $('card').classList.toggle('stale', on); }
function sync() { for (const [name] of META.fields) $('n-' + name).value = +(+vals[name]).toFixed(3); }
$('reset').onclick = () => { Object.assign(vals, META.defaults); sync(); run(); };
$('rebuild').onclick = () => run();
async function run() {
  const me = ++seq; $('busy').textContent = 'building...';
  const r = await fetch('/api/run', {method: 'POST', body: JSON.stringify({params: vals})}).then(x => x.json()).catch(() => ({error: 'Lost the connection to the tool.'}));
  if (me !== seq) return;
  $('busy').textContent = ''; dirty(false);
  if (r.error) { $('warnings').innerHTML = '<div class="warn err">' + r.error + '</div>'; return; }
  $('warnings').innerHTML = r.warnings.map(w => '<div class="warn">' + w + '</div>').join('');
  $('pic').src = '/out/' + r.key + '/spiral-cone.png';
  $('svg').href = '/out/' + r.key + '/spiral-cone.svg?dl=1';
  $('text').textContent = r.text;
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
    print(f"Spiral-cone tool running at {url}   (Ctrl+C to stop)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
