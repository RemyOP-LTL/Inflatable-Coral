#!/usr/bin/env python3
"""
The geodesic-frame tool in a browser window.

Double-click "Start Frame Tool.command" (Mac), or run:  python3 frame_app.py
Then open  http://127.0.0.1:8820/   (only your own computer can see it).

What it shows: the skin as a frame (hubs at the polygon corners, 1 in spokes, 1.5 in circles, pentagons as
solid plates), in 3D, and one pentagon patch laid flat with the spokes that come up short marked in red.
Everything on the left (rings, spoke width, circle size, plate style) updates at once.
"Make a new layout" runs the existing hex57 layout script on a shape with the hub spacing you choose.

Uses only what Python ships with, plus numpy (and numpy/scipy/matplotlib for making a new layout).
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
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame as F                                                    # noqa: E402

HEX57 = os.path.join(os.path.dirname(HERE), "hex57")
MESH_DIRS = (("example", os.path.join(HEX57, "meshes")), ("yours", os.path.join(HEX57, "uploads")))
LAYOUT_DIRS = (os.path.join(HERE, "layouts"), os.path.join(HERE, "runs"))
RUNS = os.path.join(HERE, "runs")
PORT = int(os.environ.get("FRAME_TOOL_PORT", 8820))     # skin tool 8765.., polyp tool 8800, this tool 8820
VENDOR = os.environ.get("FRAME_VENDOR_DIR", "")         # optional local copy of the 3D library (for offline testing)
CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/"

jobs, lock, cache = {}, threading.Lock(), {}


def layout_files():
    """Layouts on disk. The tube comes first (the main test shape), then the dome, then the rest."""
    out = []
    for base in LAYOUT_DIRS:
        if os.path.isdir(base):
            for d in sorted(os.listdir(base)):
                p = os.path.join(base, d, "layout.json")
                if os.path.isfile(p):
                    out.append((d, p))
    rank = lambda n: (0 if n.startswith("smile") else 1 if n.startswith("dome") else 2, n)
    out.sort(key=lambda t: rank(t[0]))
    return out


def get_frame(lid):
    paths = dict(layout_files())
    if lid not in paths:
        return None
    mt = os.path.getmtime(paths[lid])
    if lid not in cache or cache[lid][0] != mt:
        cache[lid] = (mt, F.Frame(paths[lid]))
    return cache[lid][1]


def label_for(lid, fr):
    p = fr.params
    mesh = os.path.splitext(os.path.basename(str(p.get("MESH_FILE") or lid)))[0]
    if fr.spine:
        return f"Tube as a smile, with a {fr.spine['width']:g} in spine (spoke spacing about {p.get('EDGE', '?')} in)"
    return f"{mesh}, spoke spacing about {p.get('EDGE', '?')} in"


def frame_payload(fr, rings):
    V = np.round(fr.V, 3).tolist()
    N = np.round(np.array([fr.vnorm.get(v, [0, 0, 1]) for v in range(len(fr.V))]), 3).tolist()
    plate_edges = set()
    plates = []
    for p, s_ in enumerate(fr.sides):
        if s_ == 5 and not fr.on_spine[p]:
            for a, b in zip(fr.polys[p], fr.polys[p][1:] + fr.polys[p][:1]):
                plate_edges.add(frozenset((a, b)))
    edges = []
    for e, ps in fr.edge_polys.items():
        if e in plate_edges or fr.hidden(e):
            continue
        a, b = sorted(e)
        edges.append([a, b, 1 if all(fr.end[p] for p in ps) else 0])
    pents = fr.pentagons(rings)
    usable = {q["id"]: q["ok"] for q in pents}
    for p, s_ in enumerate(fr.sides):
        if s_ == 5 and not fr.on_spine[p]:
            plates.append(dict(id=p, ok=usable.get(p, False), end=fr.end[p], corners=fr.polys[p], normal=np.round(fr.pnorm[p], 3).tolist(),
                               centre=np.round(fr.info[p]["centre"], 3).tolist()))
    for q in pents:
        q["corners"] = fr.polys[q["id"]]
    interior = {v for p in range(len(fr.polys)) if not fr.end[p] for v in fr.polys[p]}
    L = [float(np.linalg.norm(fr.V[a] - fr.V[b])) for a, b, ext in edges if not ext and a in interior and b in interior]
    summary = dict(pentagons=len(pents), usable=sum(q["ok"] for q in pents), on_spine=sum(q["spine"] for q in pents),
                   spokes=len(L), spoke_mean=float(np.mean(L)) if L else 0.0, spoke_min=float(min(L)) if L else 0.0,
                   spoke_max=float(max(L)) if L else 0.0, spoke_std_pct=float(np.std(L) / np.mean(L) * 100) if L else 0.0)
    spine = None
    if fr.spine:
        sp = fr.spine
        spine = dict(width=sp["width"], length=sp["length"], bump_radius=sp["bump_radius"], hole=sp["hole"], bumps=sp["bumps"], strip=sp["strip"])
    return dict(vertices=V, normals=N, edges=edges, pentagons=pents, plates=plates, summary=summary, hole=fr.hole_diameter, spine=spine,
                equalized=fr.layout.get("equalized"),
                params={k: fr.params.get(k) for k in ("EDGE", "MESH_FILE", "HOLE_DIAMETER", "PENT_ACROSS")})


def patch_payload(fr, pent, rings):
    """One flattened patch as plain numbers. The page (patch_draw.js) spreads the free ends apart and draws it."""
    pt = fr.flatten(pent, rings)
    d = F.patch_data(fr, pt)
    d["vertices"] = sorted(pt["pos"])
    d["spokes"] = [[a, b] for a, b in pt["solid"]]
    d["cut_pairs"] = [[c["own"], c["target"]] for c in pt["cuts"]]
    return d


# ---- making a new layout (runs the existing hex57_mesh.py) ----------------------------------------
def mesh_files():
    out = []
    for kind, folder in MESH_DIRS:
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith((".obj", ".stl")):
                    out.append(dict(name=f, kind=kind, path=f"{kind}/{f}"))
    out.sort(key=lambda m: (0 if m["name"].startswith("tube") else 1 if m["name"].startswith("dome") else 2, m["name"]))
    return out


def start_job(p):
    kind, _, f = p.get("mesh", "").partition("/")
    folder = dict(MESH_DIRS).get(kind)
    mesh = os.path.join(folder or "", os.path.basename(f))
    if not folder or not os.path.isfile(mesh):
        return dict(error="Pick a shape first.")
    try:
        edge = float(p["edge"])
    except (KeyError, ValueError):
        return dict(error="Hub spacing must be a number.")
    with lock:
        if any(j["state"] == "running" for j in jobs.values()):
            return dict(error="A layout is already being made. Wait for it to finish.")
        base = re.sub(r"[^A-Za-z0-9_.-]", "_", os.path.splitext(os.path.basename(mesh))[0])
        lid = f"{base}-edge{edge:g}"
        n = 1
        while os.path.exists(os.path.join(RUNS, lid)) or lid in dict(layout_files()):
            n += 1
            lid = f"{base}-edge{edge:g}-{n}"
        out = os.path.join(RUNS, lid)
        os.makedirs(out, exist_ok=True)
        cmd = [sys.executable, "-u", os.path.join(HEX57, "hex57_mesh.py"), mesh, "--out", out, "--edge", str(edge)]
        if p.get("flip"):
            cmd.append("--flip")
        proc = subprocess.Popen(cmd, cwd=HEX57, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        jobs[lid] = dict(proc=proc, log=[], state="running", started=time.time(), out=out)
    threading.Thread(target=watch_job, args=(lid,), daemon=True).start()
    return dict(ok=True, id=lid)


def watch_job(lid):
    job = jobs[lid]
    for line in job["proc"].stdout:
        job["log"].append(line.rstrip())
    code = job["proc"].wait()
    with lock:
        if code == 0 and os.path.isfile(os.path.join(job["out"], "layout.json")):
            for junk in ("viewer.html", "coverage"):                # the frame tool only needs layout.json
                path = os.path.join(job["out"], junk)
                if os.path.isdir(path):
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.isfile(path):
                    os.remove(path)
            job["state"] = "done"
        else:
            job["state"] = "failed"
            job["log"].append(f"The run stopped with an error (code {code}). The lines above say why.")


def progress(log):
    t = "\n".join(log)
    if "Wrote layout.json" in t:
        return "Done"
    if "target " in t:
        return "Measuring (last step)"
    if "adapted:" in t:
        return "Adding pentagons"
    if "start:" in t:
        return "Fitting hexagons to the shape"
    if "reading" in t:
        return "Reading the shape file"
    return "Starting"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, ctype="application/json", code=200, extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        path, q = unquote(u.path), parse_qs(u.query)
        try:
            if path == "/":
                return self.send(PAGE, "text/html; charset=utf-8")
            if path.startswith("/vendor/"):
                name = os.path.basename(path)
                local = os.path.join(VENDOR, name) if VENDOR else ""
                if local and os.path.isfile(local):
                    return self.send(open(local, "rb").read(), "application/javascript")
                url = CDN + ("build/" if name == "three.min.js" else "examples/js/controls/") + name
                self.send_response(302); self.send_header("Location", url); self.end_headers()
                return
            if path == "/api/layouts":
                out = []
                for lid, p in layout_files():
                    fr = get_frame(lid)
                    out.append(dict(id=lid, label=label_for(lid, fr)))
                return self.send(dict(layouts=out, meshes=mesh_files()))
            if path == "/api/frame":
                fr = get_frame(q["layout"][0])
                if fr is None:
                    return self.send(dict(error="No such layout"), code=404)
                return self.send(frame_payload(fr, int(q.get("rings", ["1"])[0])))
            if path == "/api/patch":
                fr = get_frame(q["layout"][0])
                if fr is None:
                    return self.send(dict(error="No such layout"), code=404)
                return self.send(patch_payload(fr, int(q["pent"][0]), int(q.get("rings", ["1"])[0])))
            if path == "/patch_draw.js":
                return self.send(open(os.path.join(HERE, "patch_draw.js"), "rb").read(), "application/javascript")
            if path == "/api/state":
                job = jobs.get(q.get("job", [""])[0])
                if not job:
                    return self.send(dict(state="idle"))
                return self.send(dict(state=job["state"], log=job["log"][-60:], progress=progress(job["log"]),
                                      seconds=round(time.time() - job["started"])))
        except (KeyError, ValueError, IndexError) as e:
            return self.send(dict(error=f"Bad request: {e}"), code=400)
        self.send("Not found", "text/plain", 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if urlparse(self.path).path == "/api/run":
            return self.send(start_job(json.loads(self.rfile.read(n) or b"{}")))
        self.send("Not found", "text/plain", 404)


PAGE = open(os.path.join(HERE, "frame_page.html"), encoding="utf-8").read() if os.path.exists(
    os.path.join(HERE, "frame_page.html")) else "frame_page.html is missing"


def main():
    global PAGE
    PAGE = open(os.path.join(HERE, "frame_page.html"), encoding="utf-8").read()
    port = PORT
    while True:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            if port >= PORT + 9:
                sys.exit(f"Ports {PORT} to {port} are all busy. Close the other frame tool window and try again.")
            port += 1
    url = f"http://127.0.0.1:{port}/"
    print(f"Frame tool running at {url}   (close this window or press Ctrl+C to stop)")
    if not os.environ.get("FRAME_NO_BROWSER"):
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
