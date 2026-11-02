#!/usr/bin/env python3
"""
The skin tool in a browser window.

Double-click "Start Skin Tool.command" (Mac), or run:  python3 skin_app.py

It starts a small web page that only your own computer can see (http://127.0.0.1:8765).
The page lets you pick a shape file, move sliders and press Run. Each Run starts hex57_mesh.py in
the background with those settings and shows the 3D result on the same page.
Every run is kept in the runs/ folder, so you can compare them.

Uses only what Python ships with, plus numpy / scipy / matplotlib for the layout itself.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
MESHES = os.path.join(HERE, "meshes")
UPLOADS = os.path.join(HERE, "uploads")
RUNS = os.path.join(HERE, "runs")
PORT = 8765
MAX_UPLOAD = 500 * 1024 * 1024

job = dict(id=None, proc=None, log=[], state="idle", label="", started=0.0)   # the one job that may run at a time
lock = threading.Lock()


def mesh_files():
    out = []
    for kind, folder in (("example", MESHES), ("yours", UPLOADS)):
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith((".obj", ".stl")):
                    out.append(dict(name=f, kind=kind, path=f"{kind}/{f}"))
    return out


def resolve_mesh(rel):
    kind, _, f = rel.partition("/")
    folder = {"example": MESHES, "yours": UPLOADS}.get(kind)
    path = os.path.join(folder or "", os.path.basename(f))
    return path if folder and os.path.isfile(path) else None


def list_runs():
    out = []
    if os.path.isdir(RUNS):
        for d in sorted(os.listdir(RUNS), reverse=True):
            meta = os.path.join(RUNS, d, "run.json")
            if os.path.isfile(os.path.join(RUNS, d, "viewer.html")) and os.path.isfile(meta):
                try:
                    out.append(json.load(open(meta)))
                except ValueError:
                    pass
    return out


def start_job(p):
    mesh = resolve_mesh(p.get("mesh", ""))
    if not mesh:
        return dict(error="Pick a shape file first.")
    with lock:
        if job["state"] == "running":
            return dict(error="A run is already going. Wait for it to finish or press Stop.")
        run_id = time.strftime("%Y%m%d-%H%M%S")
        base = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.splitext(os.path.basename(mesh))[0])
        out_dir = os.path.join(RUNS, f"{run_id}_{base}")
        os.makedirs(out_dir, exist_ok=True)
        cmd = [sys.executable, "-u", os.path.join(HERE, "hex57_mesh.py"), mesh, "--out", out_dir,
               "--units", p.get("units", "in"),
               "--edge", str(float(p["edge"])), "--pent-ratio", str(float(p["pent_ratio"])),
               "--coverage", str(float(p["coverage"]) / 100), "--hole-rim", str(float(p["hole_rim"])),
               "--seed", str(int(p["seed"]))]
        if p.get("flip"):
            cmd.append("--flip")
        label = (f"{base}: edge {p['edge']} in, pentagon x{p['pent_ratio']}, {p['coverage']} % target, "
                 f"rim {p['hole_rim']} in, seed {p['seed']}")
        meta = dict(id=f"{run_id}_{base}", label=label, when=time.strftime("%H:%M"), params=p)
        job.update(id=meta["id"], log=[], state="running", label=label, started=time.time())
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        job["proc"] = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, env=env)
    threading.Thread(target=watch_job, args=(job["proc"], out_dir, meta), daemon=True).start()
    return dict(ok=True, id=meta["id"])


def watch_job(proc, out_dir, meta):
    for line in proc.stdout:
        job["log"].append(line.rstrip())
    code = proc.wait()
    with lock:
        if job["state"] == "stopping":
            job["state"] = "stopped"
        elif code == 0 and os.path.isfile(os.path.join(out_dir, "viewer.html")):
            json.dump(meta, open(os.path.join(out_dir, "run.json"), "w"))
            job["state"] = "done"
        else:
            job["state"] = "failed"
            job["log"].append(f"The run stopped with an error (code {code}). The lines above say why.")


def stop_job():
    with lock:
        if job["state"] == "running" and job["proc"]:
            job["state"] = "stopping"
            job["proc"].terminate()


def friendly_progress(log):
    """A short plain-language line for the progress bar, from the script's printed output."""
    text = "\n".join(log)
    if "Wrote layout.json" in text:
        return "Done"
    if "  target " in text:
        return "Measuring the layouts (last step)"
    if "adapted:" in text:
        return "Adding pentagons"
    if "start:" in text:
        return "Fitting hexagons to the shape"
    if "reading" in text:
        return "Reading the shape file"
    return "Starting"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            return self.send(PAGE, "text/html; charset=utf-8")
        if path == "/api/state":
            with lock:
                st = dict(state=job["state"], id=job["id"], label=job["label"], log=job["log"][-200:],
                          progress=friendly_progress(job["log"]) if job["state"] != "idle" else "",
                          seconds=round(time.time() - job["started"]) if job["state"] == "running" else 0)
            st["meshes"], st["runs"] = mesh_files(), list_runs()
            return self.send(st)
        if path.startswith("/runs/"):
            full = os.path.realpath(os.path.join(RUNS, path[len("/runs/"):]))
            if full.startswith(os.path.realpath(RUNS) + os.sep) and os.path.isfile(full):
                ctype = {"html": "text/html; charset=utf-8", "json": "application/json",
                         "png": "image/png"}.get(full.rsplit(".", 1)[-1], "application/octet-stream")
                return self.send(open(full, "rb").read(), ctype)
        self.send("Not found", "text/plain", 404)

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        n = int(self.headers.get("Content-Length", 0))
        if path == "/api/run":
            return self.send(start_job(json.loads(self.rfile.read(n) or b"{}")))
        if path == "/api/stop":
            stop_job()
            return self.send(dict(ok=True))
        if path == "/api/upload":
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.basename(self.headers.get("X-Filename", "shape.stl")))
            if not name.lower().endswith((".obj", ".stl")):
                return self.send(dict(error="Only .stl and .obj files, please."), code=400)
            if n > MAX_UPLOAD:
                return self.send(dict(error="That file is over 500 MB."), code=400)
            os.makedirs(UPLOADS, exist_ok=True)
            with open(os.path.join(UPLOADS, name), "wb") as f:
                left = n
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        break
                    f.write(chunk)
                    left -= len(chunk)
            return self.send(dict(ok=True, path=f"yours/{name}"))
        self.send("Not found", "text/plain", 404)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Skin tool</title>
<style>
  :root { --bg:#f6f4ef; --panel:#fff; --ink:#23211d; --mute:#6b665d; --line:#ddd8cc; --accent:#2a78d6; --bad:#b3261e; --ok:#2e7d4f; }
  @media (prefers-color-scheme: dark) { :root { --bg:#17161a; --panel:#211f24; --ink:#ece9e2; --mute:#9d978c; --line:#37343b; --accent:#6aa8f5; --bad:#f2928b; --ok:#7bc79a; } }
  * { box-sizing: border-box; }
  [hidden] { display:none !important; }
  body { margin:0; font:15px/1.45 -apple-system, system-ui, sans-serif; background:var(--bg); color:var(--ink); }
  header { padding:14px 20px; border-bottom:1px solid var(--line); display:flex; align-items:baseline; gap:12px; }
  header h1 { font-size:18px; margin:0; } header span { color:var(--mute); font-size:13px; }
  main { display:grid; grid-template-columns: 340px 1fr; gap:0; height:calc(100vh - 54px); }
  aside { overflow-y:auto; padding:16px 18px; border-right:1px solid var(--line); background:var(--panel); }
  section.view { display:flex; flex-direction:column; min-width:0; }
  h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--mute); margin:18px 0 8px; }
  h2:first-child { margin-top:0; }
  label { display:block; font-size:14px; margin-top:10px; }
  .row { display:flex; align-items:center; gap:8px; }
  input[type=range] { flex:1; accent-color:var(--accent); }
  input[type=number], select { width:100%; padding:6px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); font:inherit; }
  .row input[type=number] { width:72px; }
  .hint { color:var(--mute); font-size:12.5px; margin:2px 0 0; }
  button { font:inherit; padding:8px 14px; border-radius:8px; border:1px solid var(--line); background:var(--bg); color:var(--ink); cursor:pointer; }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:600; width:100%; padding:11px; margin-top:16px; }
  button:disabled { opacity:.5; cursor:default; }
  #status { padding:10px 20px; border-bottom:1px solid var(--line); background:var(--panel); min-height:44px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
  #status .state { font-weight:600; } .ok { color:var(--ok); } .bad { color:var(--bad); }
  #log { display:none; margin:0; padding:10px 20px; max-height:150px; overflow:auto; background:var(--bg); border-bottom:1px solid var(--line); font:12px/1.4 ui-monospace, Menlo, monospace; white-space:pre-wrap; }
  iframe { flex:1; border:0; width:100%; background:var(--bg); }
  #empty { flex:1; display:flex; align-items:center; justify-content:center; color:var(--mute); text-align:center; padding:30px; }
  .runs button { display:block; width:100%; text-align:left; margin-top:6px; font-size:13px; }
  .runs button.cur { border-color:var(--accent); }
  @media (max-width:800px) { main { grid-template-columns:1fr; height:auto; } iframe { height:70vh; } }
</style></head><body>
<header><h1>Skin tool</h1><span>Lay a hexagon / pentagon / heptagon skin on any shape</span></header>
<main>
<aside>
  <h2>Shape</h2>
  <select id="mesh"></select>
  <div class="row" style="margin-top:8px"><button id="pick">Add my own file…</button><input type="file" id="file" accept=".stl,.obj" hidden></div>
  <label>Units in the file
    <select id="units"><option value="in">inches</option><option value="mm">millimetres</option><option value="cm">centimetres</option><option value="ft">feet</option><option value="m">metres</option></select></label>
  <p class="hint">Wrong units give panels the wrong size. Fusion exports often use mm or cm.</p>
  <label class="row"><input type="checkbox" id="flip"> Turn the skin inside-out (if it came out on the wrong side)</label>

  <h2>Polygon size</h2>
  <label>Hexagon side length <span id="edge_v"></span></label>
  <div class="row"><input type="range" id="edge" min="1.5" max="6" step="0.25" value="3"></div>
  <p class="hint">Bigger panels mean fewer of them, but they bow more on a curved surface.</p>

  <h2>Pentagons</h2>
  <label>Pentagon size vs hexagon <span id="pent_ratio_v"></span></label>
  <div class="row"><input type="range" id="pent_ratio" min="1" max="1.4" step="0.05" value="1.15"></div>
  <p class="hint">Bigger pentagons fit a bigger polyp hole but squeeze their neighbours.</p>
  <label>Share of area that is pentagons <span id="coverage_v"></span></label>
  <div class="row"><input type="range" id="coverage" min="10" max="30" step="5" value="25"></div>
  <p class="hint">It stops when there is no room for more without touching.</p>
  <label>Plastic left around the hole, inches <span id="hole_rim_v"></span></label>
  <div class="row"><input type="range" id="hole_rim" min="0.25" max="1" step="0.05" value="0.5"></div>

  <h2>Randomness</h2>
  <label>Seed (a different number gives a different arrangement)</label>
  <input type="number" id="seed" value="7" min="0" step="1">

  <button class="primary" id="run">Run</button>
  <button id="stop" style="width:100%;margin-top:8px;display:none">Stop</button>

  <h2>Earlier runs</h2>
  <div class="runs" id="runs"><p class="hint">None yet.</p></div>
</aside>
<section class="view">
  <div id="status"><span class="hint">Pick a shape, move the sliders and press Run. A run takes about a minute.</span></div>
  <pre id="log"></pre>
  <div id="empty">The 3D result will show here.</div>
  <iframe id="frame" hidden></iframe>
</section>
</main>
<script>
const $ = id => document.getElementById(id);
const fields = ["edge", "pent_ratio", "coverage", "hole_rim"];
const unit = { edge: " in", pent_ratio: "×", coverage: " %", hole_rim: " in" };
let shown = null, last = {}, showLog = false;
function labels() { fields.forEach(f => $(f + "_v").textContent = "· " + $(f).value + unit[f]); }
fields.forEach(f => $(f).addEventListener("input", labels)); labels();

try { const s = JSON.parse(localStorage.getItem("skin-settings") || "{}");
  [...fields, "seed", "units"].forEach(k => { if (s[k] !== undefined) $(k).value = s[k]; }); $("flip").checked = !!s.flip; labels(); } catch (e) {}

function settings() {
  const p = { mesh: $("mesh").value, units: $("units").value, flip: $("flip").checked, seed: $("seed").value };
  fields.forEach(f => p[f] = $(f).value); return p;
}
$("pick").onclick = () => $("file").click();
$("file").onchange = async () => {
  const f = $("file").files[0]; if (!f) return;
  $("status").innerHTML = `<span class="state">Uploading ${f.name}…</span>`;
  const r = await fetch("/api/upload", { method: "POST", headers: { "X-Filename": f.name }, body: f });
  const j = await r.json();
  if (j.error) { $("status").innerHTML = `<span class="bad">${j.error}</span>`; return; }
  await refresh(); $("mesh").value = j.path;
  $("status").innerHTML = `<span class="hint">${f.name} added. Check the units, then press Run.</span>`;
};
$("run").onclick = async () => {
  const p = settings();
  try { localStorage.setItem("skin-settings", JSON.stringify(p)); } catch (e) {}
  const j = await (await fetch("/api/run", { method: "POST", body: JSON.stringify(p) })).json();
  if (j.error) $("status").innerHTML = `<span class="bad">${j.error}</span>`;
  refresh();
};
$("stop").onclick = () => fetch("/api/stop", { method: "POST" });

function showRun(id) { shown = id; $("frame").src = `/runs/${id}/viewer.html`; $("frame").hidden = false; $("empty").hidden = true; renderRuns(); }
function renderRuns() {
  const r = last.runs || [];
  $("runs").innerHTML = r.length ? "" : '<p class="hint">None yet.</p>';
  r.forEach(x => { const b = document.createElement("button"); b.textContent = `${x.when}  ${x.label}`;
    if (x.id === shown) b.className = "cur"; b.onclick = () => showRun(x.id); $("runs").appendChild(b); });
}
async function refresh() {
  const s = await (await fetch("/api/state")).json();
  const prev = last; last = s;
  const sel = $("mesh"), cur = sel.value;
  if (JSON.stringify(s.meshes) !== JSON.stringify(prev.meshes)) {
    sel.innerHTML = ""; ["example", "yours"].forEach(k => { const g = s.meshes.filter(m => m.kind === k); if (!g.length) return;
      const og = document.createElement("optgroup"); og.label = k === "example" ? "Examples" : "Your files";
      g.forEach(m => { const o = document.createElement("option"); o.value = m.path; o.textContent = m.name; og.appendChild(o); }); sel.appendChild(og); });
    try { const sv = JSON.parse(localStorage.getItem("skin-settings") || "{}").mesh; if (!cur && sv) sel.value = sv; } catch (e) {}
    if (cur) sel.value = cur; if (!sel.value && sel.options.length) sel.selectedIndex = 0;
  }
  const running = s.state === "running" || s.state === "stopping";
  $("run").disabled = running; $("stop").style.display = running ? "block" : "none";
  const lg = $("log");
  const wantLog = s.state === "running" || s.state === "stopping" || s.state === "failed" || (showLog && s.state !== "idle");
  if (wantLog) { lg.style.display = "block"; const atEnd = lg.scrollTop + lg.clientHeight >= lg.scrollHeight - 5;
    lg.textContent = s.log.join("\n"); if (atEnd) lg.scrollTop = lg.scrollHeight; } else lg.style.display = "none";
  if (running) $("status").innerHTML = `<span class="state">Running · ${s.progress}</span><span class="hint">${s.seconds} s · ${s.label}</span>`;
  else if (s.state === "done") { $("status").innerHTML = `<span class="state ok">Done</span><span class="hint">${s.label}</span><button id="details" style="padding:3px 10px;font-size:13px">${showLog ? "Hide" : "Show"} details</button>`;
    $("details").onclick = () => { showLog = !showLog; refresh(); };
    if (prev.state === "running" || prev.state === "stopping" || shown === null) showRun(s.id); }
  else if (s.state === "failed") $("status").innerHTML = `<span class="state bad">That run failed</span><span class="hint">${(s.log.filter(l => l.trim() && !l.startsWith("The run stopped")).slice(-1)[0] || "")}</span>`;
  else if (s.state === "stopped") $("status").innerHTML = `<span class="state">Stopped</span>`;
  renderRuns();
}
setInterval(refresh, 1500); refresh();
</script></body></html>
"""


def check_libraries():
    missing = []
    for mod in ("numpy", "scipy", "matplotlib"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return missing


def main():
    missing = check_libraries()
    if missing:
        print("Python is missing: " + ", ".join(missing))
        print("Install them once with:  pip3 install " + " ".join(missing))
        sys.exit(1)
    server = None
    for port in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if not server:
        print("Could not find a free port. Close other copies of the tool and try again.")
        sys.exit(1)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Skin tool is running at {url}")
    print("Leave this window open while you use it. Close it (or press Ctrl+C) to stop the tool.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_job()


if __name__ == "__main__":
    main()
