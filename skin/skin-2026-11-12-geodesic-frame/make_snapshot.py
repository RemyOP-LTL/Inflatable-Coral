#!/usr/bin/env python3
"""Builds snapshot.html: the WHOLE frame tool (3D tube, flat sections, spine) as ONE self-contained page.
No server and no install: the layouts and every part's flat data are baked in, and it is published as an Artifact link.
It is the same page as the local tool (frame_page.html), with the server replaced by the baked-in data.
Run: python3 make_snapshot.py
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frame_app as A

layouts, frames, patches = [], {}, {}
for lid, _ in A.layout_files():
    fr = A.get_frame(lid)
    layouts.append(dict(id=lid, label=A.label_for(lid, fr)))
    frames[lid] = A.frame_payload(fr, 1)
    patches[lid] = {str(q["id"]): A.patch_payload(fr, q["id"], 1) for q in frames[lid]["pentagons"] if q["ok"]}
STATIC = dict(layouts=layouts, meshes=[], frames=frames, patches=patches)

page = open(os.path.join(HERE, "frame_page.html"), encoding="utf-8").read()
js = open(os.path.join(HERE, "patch_draw.js"), encoding="utf-8").read()
CDN = "https://cdn.jsdelivr.net/npm/three@0.128.0/"
page = page.replace('<script src="/vendor/three.min.js"></script>', f'<script src="{CDN}build/three.min.js"></script>')
page = page.replace('<script src="/vendor/OrbitControls.js"></script>', f'<script src="{CDN}examples/js/controls/OrbitControls.js"></script>')
page = page.replace('<script src="/patch_draw.js"></script>', "<script>" + js + "</script>")
shim = ("const STATIC = " + json.dumps(STATIC, separators=(",", ":")) + ";\n"
        "const j = async (url) => { const u = new URL(url, 'http://x'), q = u.searchParams;\n"
        "  if (u.pathname === '/api/layouts') return { layouts: STATIC.layouts, meshes: [] };\n"
        "  if (u.pathname === '/api/frame') return STATIC.frames[q.get('layout')] || { error: 'No such layout' };\n"
        "  if (u.pathname === '/api/patch') return (STATIC.patches[q.get('layout')] || {})[q.get('pent')] || { error: 'No such part' };\n"
        "  return { error: 'not available on this page' }; };")
page = page.replace("const j = async (url, opt) => { const r = await fetch(url, opt); return r.json(); };", shim)
page = re.sub(r"<details style=\"margin-top:10px\"><summary>Make a new layout.*?</details>", "", page, flags=re.S)
page = re.sub(r'<div class="row" style="margin-top:8px"><button id="dl">.*?</div>', "", page, flags=re.S)
page = re.sub(r'\s*<button id="dlSpine".*?</button>', "", page, flags=re.S)
page = page.replace("$('dl').onclick = ", "if ($('dl')) $('dl').onclick = ").replace("$('dlSpine').onclick = ", "if ($('dlSpine')) $('dlSpine').onclick = ")
page = page.replace("$('mesh').innerHTML = ", "if ($('mesh')) $('mesh').innerHTML = ")
page = page.replace("$('run').onclick = async () => {", "if ($('run')) $('run').onclick = async () => {")
page = page.replace("<title>Frame tool</title>", "<title>Frame tool</title>")
open(os.path.join(HERE, "snapshot.html"), "w", encoding="utf-8").write(page)
print("snapshot.html", round(len(page) / 1024), "KB;", {k: len(v) for k, v in patches.items()}, "parts")
