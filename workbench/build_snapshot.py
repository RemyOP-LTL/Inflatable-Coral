"""Bake chosen design versions into ONE web page that works anywhere (for publishing as an Artifact).

Why: a page published as an Artifact (a private claude.ai page) can't fetch files from other
websites, so the designs have to be inside the page itself. This script does that. The page uses
exactly the same viewer code as the live workbench; only the source of the data differs.

Run:  python3 build_snapshot.py --out snapshot.html \
        --pick origin/skin-2026-11-12-geodesic-frame:skin/skin-2026-11-12-geodesic-frame/layouts/dome-equal5/layout.json \
        --pick origin/workbench-2026-11-15-viewer:polyps/fabric-pattern/bundles/polyp-5-taper-tabs/polyp.json
Each --pick is  <branch or tag>:<path to layout.json or polyp.json>. The first skin and first polyp
picked are the ones shown when the page opens.
"""
import argparse, datetime, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def show(ref, path):
    return subprocess.run(["git", "-C", HERE, "show", f"{ref}:{path}"], capture_output=True, check=True).stdout


def slim_skin(d):
    r3 = lambda v: [round(x, 3) for x in v]
    return {"units": d.get("units", "inch"), "params": {k: d["params"][k] for k in d.get("params", {}) if k in ("HOLE_DIAMETER", "SURFACE", "PENT_ACROSS")},
            "vertices": [r3(v) for v in d["vertices"]], "polygons": d["polygons"],
            "polygon_info": [{"sides": p["sides"], "end": p.get("end", False), "across": p.get("across"), "centre": r3(p["centre"]), "normal": r3(p["normal"])} for p in d["polygon_info"]]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "snapshot.html"))
    ap.add_argument("--pick", action="append", required=True)
    a = ap.parse_args()
    refs, bundles, data, start = [], {}, {}, {}
    for pk in a.pick:
        ref, path = pk.split(":", 1)
        full = subprocess.run(["git", "-C", HERE, "rev-parse", "--symbolic-full-name", ref], capture_output=True, text=True).stdout.strip() or ref
        name = full.split("/", 3)[-1] if full.startswith("refs/remotes") else full.split("/", 2)[-1]
        info = subprocess.run(["git", "-C", HERE, "log", "-1", "--format=%cs|%s", ref], capture_output=True, text=True).stdout.strip().split("|", 1)
        if not any(r["ref"] == full for r in refs):
            refs.append({"ref": full, "name": name, "kind": "tag" if "/tags/" in full else "branch", "date": info[0], "subject": info[1] if len(info) > 1 else ""})
        d = json.loads(show(ref, path))
        kind = "polyp" if path.endswith("polyp.json") else "skin"
        bundles.setdefault(full, []).append({"kind": kind, "path": path, "label": os.path.dirname(path)})
        data[full + "::" + path] = d if kind == "polyp" else slim_skin(d)
        start.setdefault(kind, {"ref": full, "path": path})
    baked = {"built": datetime.date.today().isoformat(), "refs": refs, "bundles": bundles, "data": data, "start": start}
    html = open(os.path.join(HERE, "viewer.html"), encoding="utf-8").read()
    marker = "<script>\n// ---------- where bundles come from"
    assert marker in html
    html = html.replace(marker, "<script>window.WORKBENCH_BAKED=" + json.dumps(baked, separators=(",", ":")) + ";</script>\n" + marker, 1)
    open(a.out, "w", encoding="utf-8").write(html)
    print(a.out, round(len(html) / 1e6, 2), "MB,", len(data), "designs")


if __name__ == "__main__":
    main()
