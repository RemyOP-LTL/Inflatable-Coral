"""A small page for trying out polyp sizes without editing any code.

Run:  python3 polyp_tool.py        (it opens your web browser; press Ctrl+C here to stop it)

You get fields for the cuff size, cuff height, finger length and so on. The flat pattern redraws
as you change them (about a second). Two buttons run the slower 3D simulations:
  - Inflated: what the sewn polyp looks like with air in it (about 30 seconds)
  - String pull: the fingers' cords pulled from one hitch point (about 2 minutes)
Everything it makes is saved in the folder tool-output/ next to this script, so you can
open the PDF and pictures later. Nothing outside that folder is changed.

It only listens on your own computer (127.0.0.1), and it works by running make_pattern.py
and sim_pull.py for you, so the results match what those scripts make.
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tool-output")
PORT = int(os.environ.get("POLYP_TOOL_PORT", 8765))

# Settings shown on the page: (name in make_pattern.py, label, unit, min, max, step, help)
PATTERN_FIELDS = [
    ("CUFF_DIAMETER", "Cuff diameter", "in", 2, 14, 0.05, "Width of the finished cuff. The tube it fits is this minus the ease."),
    ("EASE", "Cuff ease", "in", -1, 1.5, 0.125, "Extra room around the tube. About 0.5 for woven fabric."),
    ("CUFF_HEIGHT", "Cuff length", "in", 1, 8, 0.25, "Finished height of the wrist part."),
    ("FINGER_LENGTH", "Finger length", "in", 3, 14, 0.25, "On the flat piece, from crotch to tip."),
    ("FINGERS", "Number of fingers", "", 3, 8, 1, "Around the cuff."),
    ("TAPER_FULLNESS", "Finger fullness", "", 0, 1.5, 0.1, "0 = straight cone sides, higher = fuller before the point."),
    ("SPLAY", "Lean out", "deg", 0, 70, 5, "How far the fingers lean out just above the cuff."),
    ("TURN_LENGTH", "Turn length", "in", 0.5, 4, 0.25, "Distance over which they lean out."),
    ("TUNNEL_WIDTH", "Tunnel width", "in", 0.125, 0.5, 0.0625, "String tunnel on the inner seam."),
]
PULL_FIELDS = [
    ("HITCH", "Hitch depth", "in", 0.25, 4, 0.25, "Where the five strings meet, this far below the polyp's centre point (into the cuff)."),
    ("PULL_MAX", "Pull up to", "in", 1, 14, 1, "Most the hitch is pulled down. It stops earlier if the fingers can't fold further."),
]
DEFAULTS = {"CUFF_DIAMETER": (math.pi * 5.0 + 0.5) / math.pi, "EASE": 0.5, "CUFF_HEIGHT": 3.0,
            "FINGER_LENGTH": 8.5, "FINGERS": 5, "TAPER_FULLNESS": 0.6, "SPLAY": 45, "TURN_LENGTH": 1.5,
            "TUNNEL_WIDTH": 0.25, "HITCH": 1.0, "PULL_MAX": 10}

JOBS = {}                         # job id -> dict(state, log, files)
HEAVY = threading.Semaphore(1)    # only one simulation at a time; they use every processor core
LOCK = threading.Lock()


def clean(params):
    """Check the numbers from the page and turn them into make_pattern's settings."""
    p = {}
    for name, label, unit, lo, hi, step, _ in PATTERN_FIELDS + PULL_FIELDS:
        v = float(params.get(name, DEFAULTS[name]))
        if not lo <= v <= hi:
            raise ValueError(f"{label} must be between {lo:g} and {hi:g}")
        p[name] = v
    p["FINGERS"] = int(round(p["FINGERS"]))
    return p


def polyp_env(p):
    """make_pattern.py reads its settings from the POLYP variable."""
    tube = p["CUFF_DIAMETER"] - p["EASE"] / math.pi
    if tube < 0.5:
        raise ValueError("The cuff is too small for that much ease")
    keys = ["CUFF_HEIGHT", "FINGER_LENGTH", "FINGERS", "TAPER_FULLNESS", "SPLAY", "TURN_LENGTH", "TUNNEL_WIDTH", "EASE"]
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
            cmd = [sys.executable, "make_pattern.py", "--out", folder, "--name", "custom", "--no-sim"]
        elif kind == "inflate":
            cmd = [sys.executable, "make_pattern.py", "--out", folder, "--name", "custom"]
        else:
            cmd = [sys.executable, "sim_pull.py", "--out", folder, "--name", "custom",
                   "--hitch", str(p["HITCH"]), "--pull-max", str(p["PULL_MAX"]), "--steps", str(int(p["PULL_MAX"]))]
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
    relevant = {k: p[k] for k in sorted(p) if kind == "pull" or k not in ("HITCH", "PULL_MAX")}
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
            meta = dict(pattern=PATTERN_FIELDS, pull=PULL_FIELDS, defaults=DEFAULTS)
            self.send(200, PAGE.replace("__META__", json.dumps(meta)), "text/html; charset=utf-8")
        elif path.startswith("/api/job/"):
            job = JOBS.get(path.split("/")[-1])
            self.send(200 if job else 404, json.dumps(job or {"state": "unknown"}), "application/json")
        elif path.startswith("/out/"):
            parts = path.split("/")[2:]
            f = os.path.join(OUT, *parts) if len(parts) == 2 and not any(x.startswith(".") for x in parts) else None
            if f and os.path.isfile(f):
                ctype = {"png": "image/png", "pdf": "application/pdf", "csv": "text/csv"}.get(f.rsplit(".", 1)[-1], "application/octet-stream")
                self.send(200, open(f, "rb").read(), ctype)
            else:
                self.send(404, "not found", "text/plain")
        else:
            self.send(404, "not found", "text/plain")

    def do_POST(self):
        if urlparse(self.path).path != "/api/run":
            return self.send(404, "not found", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if body["job"] not in ("pattern", "inflate", "pull"):
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
    <div class="card"><h2>Polyp size</h2><div id="pattern-fields"></div>
      <div class="derived" id="derived"></div>
      <button class="reset" id="reset">Reset to the default design</button></div>
    <div class="card" style="margin-top:16px"><h2>String pull</h2><div id="pull-fields"></div>
      <button id="run-inflate" class="secondary">Simulate inflated (about 30 s)</button>
      <button id="run-pull">Simulate string pull (about 2 min)</button></div>
  </div>
  <div class="results">
    <div class="card" id="card-pattern"><h2>Flat pattern <span class="tag">updating</span></h2>
      <div id="out-pattern"></div><div class="status" id="log-pattern"></div></div>
    <div class="card" id="card-inflate"><h2>Inflated <span class="tag">settings changed, run again</span></h2>
      <div id="out-inflate" style="color:var(--mute)">Press "Simulate inflated".</div><div class="status" id="log-inflate"></div></div>
    <div class="card" id="card-pull"><h2>String pull <span class="tag">settings changed, run again</span></h2>
      <div id="out-pull" style="color:var(--mute)">Press "Simulate string pull". The five cords run from the fingertips along the inner seams to one hitch point inside the cuff. The hitch is pulled down in steps.</div>
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
build('pattern-fields', META.pattern); build('pull-fields', META.pull);
const names = [...META.pattern, ...META.pull].map(f => f[0]);
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
  const c = state.CUFF_DIAMETER * Math.PI, tube = state.CUFF_DIAMETER - state.EASE / Math.PI;
  const w = c / state.FINGERS;
  $('derived').innerHTML = `Cuff goes round <b>${c.toFixed(2)} in</b>, fits a <b>${tube.toFixed(2)} in</b> tube.<br>` +
    `Each piece is <b>${w.toFixed(2)} in</b> wide at the crotch.`;
}
let timer = null;
function changed(n) {
  derived();
  const heavy = !['HITCH', 'PULL_MAX'].includes(n) ? ['inflate', 'pull'] : ['pull'];
  heavy.forEach(k => $('card-' + k).classList.add('stale'));
  if (['HITCH', 'PULL_MAX'].includes(n)) return;           // these only affect the string pull
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
    $('log-pattern').textContent = j.log.split('\n').filter(l => l.startsWith('cut size') || l.startsWith('string tunnel')).join('\n');
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
['pattern', 'inflate', 'pull'].forEach(k => state['seq-' + k] = 0);
$('run-inflate').onclick = () => run('inflate');
$('run-pull').onclick = () => run('pull');
setAll(META.defaults); derived(); run('pattern');
</script></body></html>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
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
