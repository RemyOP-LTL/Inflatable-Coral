"""The workbench: one page, three tabs (Skin, Polyp, Combined), that shows any saved design version.

What it does, in plain words:
  * It reads "design bundles" (layout.json for a skin, polyp.json for a polyp) straight out of the
    repo's saved history on any branch or tag. It never checks out a branch, so your working
    folder stays on one branch and the viewer itself never changes under you.
  * It only LISTS and SHOWS. It does not run the generators (yet) and never edits files.
  * Python standard library only: nothing to install.

Run:  python3 workbench.py        (opens http://127.0.0.1:8840/ ; Ctrl+C stops it)
Port 8840: this tool's own block (8840-8859). See the root CLAUDE.md.
Formats: shared/FORMATS.md
"""
import json, os, re, subprocess, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("WORKBENCH_PORT", 8840))
REF_OK = re.compile(r"^refs/(heads|remotes/origin|tags)/[A-Za-z0-9._/-]+$")
KINDS = {"layout.json": "skin", "polyp.json": "polyp"}


def git(*args, timeout=60):
    try:
        r = subprocess.run(["git", "-C", HERE, *args], capture_output=True, timeout=timeout)
    except Exception as e:
        return False, str(e).encode()
    return r.returncode == 0, r.stdout if r.returncode == 0 else (r.stderr or r.stdout)


def refs():
    """Every branch and tag. Remote (GitHub) copies win over local ones of the same name."""
    fmt = "%(refname)\x1f%(committerdate:short)\x1f%(subject)"
    ok, out = git("for-each-ref", "--sort=-committerdate", f"--format={fmt}",
                  "refs/remotes/origin", "refs/heads", "refs/tags")
    seen, res = set(), []
    for line in (out.decode() if ok else "").splitlines():
        full, date, subj = (line.split("\x1f") + ["", ""])[:3]
        if full.endswith("/HEAD") or not REF_OK.match(full):
            continue
        kind = "tag" if "/tags/" in full else "branch"
        name = re.sub(r"^refs/(heads|remotes/origin|tags)/", "", full)
        if (kind, name) in seen:
            continue
        seen.add((kind, name))
        res.append({"ref": full, "name": name, "kind": kind, "date": date, "subject": subj})
    return res


def bundles(ref):
    if not REF_OK.match(ref):
        return []
    ok, out = git("ls-tree", "-r", "--name-only", ref)
    res = []
    for p in (out.decode() if ok else "").splitlines():
        base = os.path.basename(p)
        if base in KINDS and "/_" not in p and not p.startswith("_"):
            res.append({"kind": KINDS[base], "path": p, "label": os.path.dirname(p) or "(top)"})
    return res


def bundle(ref, path):
    if not REF_OK.match(ref) or path not in [b["path"] for b in bundles(ref)]:
        return None
    ok, out = git("show", f"{ref}:{path}", timeout=120)
    return out if ok else None


def fetch():
    ok, out = git("fetch", "--prune", "--tags", "origin", timeout=90)
    return ok, out.decode(errors="replace")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            return self.send(200, open(os.path.join(HERE, "viewer.html"), "rb").read(), "text/html; charset=utf-8")
        if u.path == "/api/refs":
            ok, cur = git("rev-parse", "--abbrev-ref", "HEAD")
            return self.send(200, json.dumps({"refs": refs(), "here": cur.decode().strip() if ok else ""}))
        if u.path == "/api/bundles":
            return self.send(200, json.dumps(bundles(q.get("ref", ""))))
        if u.path == "/api/bundle":
            b = bundle(q.get("ref", ""), q.get("path", ""))
            return self.send(200, b) if b else self.send(404, json.dumps({"error": "not found"}))
        self.send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path == "/api/fetch":
            ok, log = fetch()
            return self.send(200, json.dumps({"ok": ok, "log": log}))
        self.send(404, "not found", "text/plain")


def main():
    for port in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit(f"Ports {PORT}-{PORT + 19} are all busy. Is the workbench already running?")
    url = f"http://127.0.0.1:{port}/"
    print(f"Workbench running at {url}\nPress Ctrl+C to stop it.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
