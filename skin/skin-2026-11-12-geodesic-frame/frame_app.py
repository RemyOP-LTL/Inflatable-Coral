#!/usr/bin/env python3
"""
The geodesic-frame tool in a browser window.

Double-click "Start Frame Tool.command" (Mac), or run:  python3 frame_app.py
Then open  http://127.0.0.1:8790/   (only your own computer can see it).

What it shows: the skin as a frame (hubs at the polygon corners, 1 in spokes, 1.5 in circles, pentagons as
solid plates), in 3D, and one pentagon patch laid flat with the spokes that come up short marked in red.
Everything on the left (rings, spoke width, circle size, plate style) updates at once.
"Make a new layout" runs the existing hex57 layout script on a shape with the hub spacing you choose.

Uses only what Python ships with, plus numpy (and numpy/scipy/matplotlib for making a new layout).
"""
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
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frame as F                                                    # noqa: E402
import geom                                                          # noqa: E402
import patches as PT                                                 # noqa: E402

HEX57 = os.path.join(os.path.dirname(HERE), "hex57")
SHAPES = os.path.join(HERE, "shapes")
MESH_DIRS = (("example", SHAPES), ("yours", os.path.join(SHAPES, "uploads")))
LAYOUT_DIRS = (os.path.join(HERE, "layouts"), os.path.join(HERE, "runs"))
RUNS = os.path.join(HERE, "runs")
PORT = int(os.environ.get("FRAME_TOOL_PORT", 8790))     # skin tools own 8760-8799 (skin_app 8765.., this tool 8790); polyps own 8800 and up
VENDOR = os.environ.get("FRAME_VENDOR_DIR", "")         # optional local copy of the 3D library (for offline testing)
CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/"

lock, cache = threading.Lock(), {}
CACHE = os.path.join(HERE, "cache")                       # layouts made for a shape at a sizing; git-ignored
BUILD = threading.Lock()                                  # one layout at a time (they use a whole processor core)
DEFAULT = dict(pd=100 / 25.4, po=10 / 25.4, spine=4.0, pc=25.0)    # polyp hole 100 mm, pentagon offset 10 mm, spine 4 in, pentagon coverage 25 %


def shape_files():
    """The surfaces: files in shapes/ (tube first, then dome) and shapes/uploads/."""
    out = []
    for kind, folder in MESH_DIRS:
        if os.path.isdir(folder):
            for f in sorted(os.listdir(folder)):
                if f.lower().endswith((".obj", ".stl")):
                    out.append(dict(id=os.path.splitext(f)[0], label=os.path.splitext(f)[0], path=os.path.join(folder, f), kind=kind))
    out.sort(key=lambda m: (0 if m["id"] == "tube" else 1 if m["id"] == "dome" else 2, m["id"]))
    return out


def pent_size(hole, offset):
    """Pentagon from the polyp hole and the offset (radial gap between the hole and the circle through the pentagon's corners):
    circumradius, side (this is also the spoke spacing), and the rim hex57 wants (plastic between hole and the side, may be < 0)."""
    Rc = hole / 2 + offset
    return Rc, 2 * Rc * math.sin(math.pi / 5), Rc * math.cos(math.pi / 5) - hole / 2


def ensure_raw(sh, hole, offset, spine, cov):
    """hex57's layout for this surface at this sizing, made once and kept in cache/."""
    import spinecurve
    d = os.path.join(CACHE, sh["id"], f"h{round(hole * 1000)}-o{round(offset * 1000)}-c{round(cov * 10)}")
    raw = os.path.join(d, "raw.json")
    if not os.path.isfile(raw):
        Rc, side, rim = pent_size(hole, offset)
        has_curve = spinecurve.read_curve(sh["path"]) is not None
        os.makedirs(d, exist_ok=True)
        cmd = [sys.executable, "-u", os.path.join(HERE if has_curve else HEX57, "spine_layout.py" if has_curve else "hex57_mesh.py"), sh["path"],
               "--out", d, "--edge", f"{side:.4f}", "--hole-diameter", f"{hole:.4f}", "--hole-rim", f"{rim:.4f}", "--coverage", f"{max(0.05, min(cov, 60.0)) / 100:.4f}"]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SPINE_KEEP_OUT=f"{spine / 2 + 1.7 + Rc + 0.8:.2f}")
        r = subprocess.run(cmd, cwd=HERE if has_curve else HEX57, capture_output=True, text=True, env=env)
        if r.returncode != 0 or not os.path.isfile(os.path.join(d, "layout.json")):
            raise ValueError("The layout could not be made for this surface and sizing:\n" + (r.stdout + r.stderr)[-600:])
        os.replace(os.path.join(d, "layout.json"), raw)
        for junk in ("viewer.html", "coverage"):
            p = os.path.join(d, junk)
            if os.path.isdir(p):
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)
        for f in os.listdir(d):
            if f.startswith("preview_"):
                os.remove(os.path.join(d, f))
    return json.load(open(raw))


def get_frame(lid, hole=None, offset=None, spine=None, cov=None):
    """The frame for a shape at a sizing: polyp hole diameter, pentagon offset and spine width (inches). Made on first use
    (a layout takes about 20 s, the cut and equalising a few more) and kept."""
    sh = next((s_ for s_ in shape_files() if s_["id"] == lid), None)
    if sh is None:
        return None
    hole, offset, spine, cov = hole or DEFAULT["pd"], offset or DEFAULT["po"], spine or DEFAULT["spine"], cov or DEFAULT["pc"]
    import spinecurve
    has_curve = spinecurve.read_curve(sh["path"]) is not None
    key = (lid, round(hole, 4), round(offset, 4), round(spine, 3) if has_curve else 0, round(cov, 1), os.path.getmtime(sh["path"]))
    if key not in cache:
        with BUILD:
            if key not in cache:
                import build_smile
                raw = ensure_raw(sh, hole, offset, spine, cov)
                res, _ = build_smile.build(raw, sh["path"], spine)
                res["display_name"] = sh["label"]
                if len(cache) > 6:
                    cache.clear()
                cache[key] = F.Frame(res)
    return cache[key]


def mesh_path(fr):
    name = os.path.basename(str(fr.params.get("MESH_FILE") or ""))
    for d in (SHAPES, os.path.join(SHAPES, "uploads")):
        if os.path.isfile(os.path.join(d, name)):
            return os.path.join(d, name)
    return None


CONFIGS = os.path.join(HERE, "saved_configs.json")


def read_configs():
    try:
        return json.load(open(CONFIGS))
    except (OSError, ValueError):
        return {}


def sizing(q):
    """Polyp hole, pentagon offset, spine width (inches) and pentagon coverage (percent) from a request."""
    return fnum(q, "pd", DEFAULT["pd"]), fnum(q, "po", DEFAULT["po"]), fnum(q, "spine", DEFAULT["spine"]), fnum(q, "pc", DEFAULT["pc"])


def fnum(q, k, d):
    try:
        return float(q.get(k, [d])[0])
    except (TypeError, ValueError):
        return d


_pcache = {}


def patcher(lid, sz, w, D, f, maxp=5):
    """(frame, Patcher, patches) for these settings; patches are grown once and kept."""
    fr = get_frame(lid, *sz)
    key = (lid, id(fr), round(w, 4), round(D, 4), round(f, 4), maxp)
    if key not in _pcache:
        if len(_pcache) > 12:
            _pcache.clear()
        pt = PT.Patcher(fr, w, D, f, maxp)
        _pcache[key] = (fr, pt, pt.partition([p["id"] for p in fr.pentagons() if p["ok"]]))
    return _pcache[key]


def spine_outline(fr, w, D, f, hole):
    """The spine piece's outline: the strip (with its lobes) plus the spine spokes, blended into the edge with radius f."""
    shape, holes, folds = geom.spine_shape(fr.spine, w, D, f)
    return dict(outline=geom.coords(shape.simplify(0.02)), holes=holes, folds=folds, hole=hole, length=fr.spine["length"], area=round(shape.area, 1))


_curves = {}


def curve_for(fr):
    p = mesh_path(fr)
    if p and p not in _curves:
        import build_smile
        _curves[p] = build_smile.load_curve(p)
    return _curves.get(p)


def loose_template(L, w, D, f, hole):
    a, b = (0.0, 0.0), (float(L), 0.0)
    sh = geom.spoke_shape(a, b, w, D, f)
    return dict(poly=geom.coords(sh), folds=[[[round(x, 3), round(y, 3)] for x, y in s] for s in geom.fold_segments(a, b, w, D)], L=L, hole=hole)


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
        edges.append([a, b, 1 if all(fr.end[p] for p in ps) else (2 if e in fr.loose_id else (3 if e in fr.spine_spokes else (4 if e in fr.edge_spokes else 0)))])
    pents = fr.pentagons(rings)
    usable = {q["id"]: q["ok"] for q in pents}
    for p, s_ in enumerate(fr.sides):
        if s_ == 5 and not fr.on_spine[p]:
            plates.append(dict(id=p, ok=usable.get(p, False), end=fr.end[p], corners=fr.polys[p], normal=np.round(fr.pnorm[p], 3).tolist(),
                               centre=np.round(fr.info[p]["centre"], 3).tolist()))
    for q in pents:
        q["corners"] = fr.polys[q["id"]]
    interior = {v for p in range(len(fr.polys)) if not fr.end[p] for v in fr.polys[p]}
    L = [float(np.linalg.norm(fr.V[a] - fr.V[b])) for a, b, f_ in edges if f_ == 2 and a in interior and b in interior]
    Tr = [float(np.linalg.norm(fr.V[a] - fr.V[b])) for a, b, f_ in edges if f_ == 0 and a in interior and b in interior]
    loose_lengths = [round(l, 3) for l in L]
    summary = dict(pentagons=len(pents), usable=sum(q["ok"] for q in pents), on_spine=sum(q["spine"] for q in pents),
                   loose=len(L), loose_mean=float(np.mean(L)) if L else 0.0, loose_min=float(min(L)) if L else 0.0,
                   loose_max=float(max(L)) if L else 0.0, loose_std_pct=float(np.std(L) / np.mean(L) * 100) if L else 0.0,
                   attached=len(Tr), attached_min=float(min(Tr)) if Tr else 0.0, attached_max=float(max(Tr)) if Tr else 0.0)
    spine = None
    if fr.spine:
        sp = fr.spine
        spine = dict(width=sp["width"], length=sp["outline_length"], hole=sp["hole"], bumps=sp["attach"], outline=sp["outline"], mesh=sp["mesh"],
                     tabs=sp.get("tabs", []), partial=sum(bool(i.get("partial")) for i in fr.info))
    return dict(vertices=V, normals=N, edges=edges, pentagons=pents, plates=plates, summary=summary, hole=fr.hole_diameter, spine=spine,
                equalized=fr.layout.get("equalized"), loose_lengths=loose_lengths, edge_d=[t["d"] for t in (fr.spine or {}).get("edges", [])], spine_width=(fr.spine or {}).get("width"),
                params={k: fr.params.get(k) for k in ("EDGE", "MESH_FILE", "HOLE_DIAMETER", "PENT_ACROSS")})


def convert_step(data, name):
    """STEP bytes -> an OBJ surface in inches saved in shapes/uploads, with the spine curve from the file if it has one.
    Returns (path, size text, curve note). Raises ValueError with a plain message."""
    import io
    import cascadio
    import step_curve
    import trimesh
    try:
        glb = cascadio.load(data, "step", tol_linear=0.002, tol_relative=True)
        mesh = trimesh.load(io.BytesIO(glb), file_type="glb", force="mesh")
    except Exception as e:
        raise ValueError(f"I could not read that STEP file ({e}). Export the surface or solid as STEP (AP214 or AP203) from Fusion 360 and try again.")
    if len(mesh.faces) == 0:
        raise ValueError("That STEP file has no surface in it.")
    mesh.apply_scale(39.3700787)                          # the converter writes metres and keeps the file's axes
    curve, note = step_curve.find_curve(data.decode("utf-8", "ignore"))
    uploads = dict(MESH_DIRS)["yours"]
    os.makedirs(uploads, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name) or "shape"
    path = os.path.join(uploads, safe + ".obj")
    with open(path, "w") as f:
        f.write(f"# {name}, inches. Converted from STEP.\n")
        if curve is not None:
            for p in curve:
                f.write("# spine %.4f %.4f %.4f\n" % tuple(p))
        for p in mesh.vertices:
            f.write("v %.5f %.5f %.5f\n" % tuple(p))
        for t in mesh.faces:
            f.write("f %d %d %d\n" % tuple(t + 1))
    return path, " x ".join(f"{x:.1f}" for x in sorted(mesh.extents, reverse=True)) + " in", note


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
                return self.send(dict(layouts=[dict(id=m["id"], label=m["label"]) for m in shape_files()],
                                      defaults=dict(pd=DEFAULT["pd"], po=DEFAULT["po"], spine=DEFAULT["spine"], pc=DEFAULT["pc"])))
            if path == "/api/frame":
                try:
                    fr = get_frame(q["layout"][0], *sizing(q))
                except ValueError as e:
                    return self.send(dict(error=str(e)))
                if fr is None:
                    return self.send(dict(error="No such shape"), code=404)
                out = frame_payload(fr, 1)
                out["has_spine"] = bool(fr.spine)
                return self.send(out)
            if path == "/api/mesh3d":
                import mesh3d
                w_, D_, f_ = fnum(q, "w", 1.25), fnum(q, "d", 1.25), fnum(q, "f", 0.5)
                fr, pt, res = patcher(q["layout"][0], sizing(q), w_, D_, f_, int(fnum(q, "mp", 5)))
                return self.send(mesh3d.build(fr, curve_for(fr), w_, D_, f_, fr.hole_diameter, pt, res))
            if path in ("/api/patches", "/api/patch", "/api/spine_outline", "/api/loose"):
                lid, sz = q["layout"][0], sizing(q)
                w, D, f, hole = fnum(q, "w", 1.25), fnum(q, "d", 1.25), fnum(q, "f", 0.5), fnum(q, "hole", 0.25)
                fr, pt, res = patcher(lid, sz, w, D, f, int(fnum(q, "mp", 5)))
                if path == "/api/patches":
                    return self.send(dict(patches=[dict(id=i, plates=p["order"], parts=len(p["order"]), fits=pt.payload(p)["size"]) for i, p in enumerate(res)]))
                if path == "/api/patch":
                    pent = int(q["pent"][0])
                    for p in res:
                        if pent in p["T"]:
                            return self.send(pt.payload(p))
                    return self.send(dict(error="That pentagon is not in any patch."))
                if path == "/api/spine_outline":
                    return self.send(spine_outline(fr, w, D, f, hole) if fr.spine else dict(error="No spine"))
                Ls = [float(x) for x in q.get("Ls", [""])[0].split(",") if x]
                if Ls:
                    return self.send(dict(items=[loose_template(L, w, D, f, hole) for L in Ls]))
                return self.send(loose_template(fnum(q, "L", 4.6), w, D, f, hole))
            if path == "/api/configs":
                return self.send(dict(configs=read_configs()))
            if path == "/api/version":
                return self.send(version_info())
            if path == "/patch_draw.js":
                return self.send(open(os.path.join(HERE, "patch_draw.js"), "rb").read(), "application/javascript")
        except (KeyError, ValueError, IndexError) as e:
            return self.send(dict(error=f"Bad request: {e}"), code=400)
        except Exception as e:                              # never drop the connection: tell the page what went wrong
            import traceback
            traceback.print_exc()
            return self.send(dict(error=f"The tool hit a problem: {type(e).__name__}: {e}"), code=500)
        self.send("Not found", "text/plain", 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        if urlparse(self.path).path == "/api/refresh":
            ok, log = refresh_code()
            if ok:
                restart_soon()
            return self.send(dict(ok=ok, log=log))
        if urlparse(self.path).path in ("/api/configs/save", "/api/configs/delete"):
            q = parse_qs(urlparse(self.path).query)
            name = (q.get("name", [""])[0] or "").strip()[:80]
            if not name:
                return self.send(dict(error="Give the setup a name."))
            body = self.rfile.read(n)
            cfg = read_configs()
            if urlparse(self.path).path.endswith("save"):
                try:
                    cfg[name] = json.loads(body or b"{}")
                except ValueError:
                    return self.send(dict(error="Could not read the setup."))
            else:
                cfg.pop(name, None)
            tmp = CONFIGS + ".tmp"
            json.dump(cfg, open(tmp, "w"), indent=1)
            os.replace(tmp, CONFIGS)
            return self.send(dict(ok=True))
        if urlparse(self.path).path == "/api/upload":
            q = parse_qs(urlparse(self.path).query)
            name = (q.get("name", ["shape"])[0] or "shape")[:60]
            try:
                path, size, note = convert_step(self.rfile.read(n), name)
            except ValueError as e:
                return self.send(dict(error=str(e)))
            return self.send(dict(ok=True, id=os.path.splitext(os.path.basename(path))[0], size=size, curve=note))
        self.send("Not found", "text/plain", 404)


def git(*args, timeout=60):
    """Run a git command in this folder. Returns (ok, text)."""
    try:
        r = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)


def version_info():
    """Which branch and last change this copy is on (shown in the window's top bar)."""
    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not ok:
        return dict(git=False)
    _, line = git("log", "-1", "--format=%h|%cs|%s")
    sha, date, subject = (line.split("|", 2) + ["", "", ""])[:3]
    _, dirty = git("status", "--porcelain", "--untracked-files=no")
    return dict(git=True, branch=branch, sha=sha, date=date, subject=subject, edited=bool(dirty))


def refresh_code():
    """Pick up the newest version: pull from GitHub if that is safe, then the caller restarts the tool so
    whatever is in the folder (pulled, or edited here by Claude) is what runs."""
    log = []
    ok, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if ok and branch != "HEAD":
        fetched, msg = git("fetch", "--prune", "origin", timeout=30)
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
        pip = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "-r", req],
                             cwd=HERE, capture_output=True, text=True)
        if pip.returncode != 0:
            log.append("(The library check failed: " + pip.stderr.strip()[-200:] + ")")
    return True, " ".join(log)


def restart_soon():
    """Start again from the files on disk in a moment, after the reply has gone out."""
    def go():
        time.sleep(1.0)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    threading.Thread(target=go, daemon=True).start()


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
