#!/usr/bin/env python3
"""Builds snapshot.html: ONE self-contained page (no server, no install) with the flattened patches of the
tube and dome baked in, and the same JavaScript (patch_draw.js) as the local tool. Sliders work live.
Run: python3 make_snapshot.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frame as F

data, spines, facts = {}, {}, {}
LAYOUTS = (("smile-tube", "A: smile tube, spine cut through the existing layout"), ("smile-tube-clear", "B: smile tube, layout built around the spine"), ("dome-equal5", "Dome (secondary shape)"))
for lid, label in LAYOUTS:
    fr = F.Frame(os.path.join(HERE, "layouts", lid, "layout.json"))
    data[f"{lid}|1"] = [F.patch_data(fr, fr.flatten(q["id"], 1)) for q in fr.pentagons(1) if q["ok"]]
    P_ = fr.pentagons(1)
    L_ = [float(__import__("numpy").linalg.norm(fr.V[a] - fr.V[b])) for a, b in fr.loose if not all(fr.end[p] for p in fr.edge_polys[frozenset((a, b))])]
    bm = sorted(x["sigma"] for x in (fr.spine or {"bumps": []})["bumps"] if 0 <= x["sigma"] <= (fr.spine or {"length": 0})["length"])
    facts[lid] = dict(pentagons=len(P_), complete=sum(p["ok"] for p in P_), lost=sum(p["spine"] for p in P_), loose=len(L_), loose_min=min(L_), loose_max=max(L_),
                      bumps=len(bm), gap_min=min(__import__("numpy").diff(bm)) if len(bm) > 1 else 0, gap_max=max(__import__("numpy").diff(bm)) if len(bm) > 1 else 0)
    if fr.spine:
        sp = fr.spine
        spines[lid] = dict(width=sp["width"], length=sp["length"], bump_radius=sp["bump_radius"], hole=sp["hole"],
                           bumps=[b for b in sp["bumps"] if -1 <= b["sigma"] <= sp["length"] + 1])
labels = dict(LAYOUTS)
js = open(os.path.join(HERE, "patch_draw.js"), encoding="utf-8").read()

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Frame patch explorer</title><style>
:root{--bg:#f6f5f1;--panel:#fff;--ink:#1d2320;--mute:#66706a;--line:#dcdad2;--accent:#1f7a55;--warn:#c0281d}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#161a18;--panel:#1f2522;--ink:#e8ece9;--mute:#9aa69f;--line:#34403a;--accent:#4fc08d;--warn:#ff7b6e}}
:root[data-theme="dark"]{--bg:#161a18;--panel:#1f2522;--ink:#e8ece9;--mute:#9aa69f;--line:#34403a;--accent:#4fc08d;--warn:#ff7b6e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}h1{font-size:22px;margin:.2em 0}h2{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:var(--mute);margin:0 0 8px}
.grid{display:grid;grid-template-columns:290px 1fr;gap:14px;align-items:start}@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:14px}
label{display:block;margin:10px 0 2px;font-size:13px;color:var(--mute)}select,input[type=range]{width:100%}select{padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit}
.val{float:right;color:var(--ink)}.row{display:flex;gap:8px}.row>*{flex:1}button{padding:7px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:6px;font:inherit;cursor:pointer}
#flat svg{width:100%;height:auto;max-height:640px;display:block}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:10px}
.stat b{display:block;font-size:20px}.stat span{font-size:12px;color:var(--mute)}.note{font-size:13px;color:var(--mute)}.bad{color:var(--warn)}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left}th{color:var(--mute);font-weight:500}.tbl{overflow-x:auto}
tr.cur td{font-weight:600}code{background:var(--bg);padding:1px 5px;border-radius:4px}
</style></head><body><main>
<h1>Geodesic-frame patch explorer</h1>
<p class="note">Branch <code>skin-2026-11-12-geodesic-frame</code>. Spokes have round ends; the pentagon is a solid plate with the polyp hole; the orange spokes are loose pieces riveted at both ends (all one length) and sit inside the windows of the flat pattern; a numbered end marks where each one rivets. True size. Everything runs in the page: nothing to install. (The 3D view with the tube is in the local tool.)</p>
<div class="card" id="cmp"></div>
<div class="grid"><div>
 <div class="card"><h2>Patch</h2>
  <label>Shape</label><select id="layout">__OPTS__</select>
  <input type="hidden" id="rings" value="1">
  <label>Pentagon</label><div class="row"><button id="prev">&larr;</button><select id="pent" style="flex:4"></select><button id="next">&rarr;</button></div>
 </div>
 <div class="card"><h2>Plastic</h2>
  <label>Spoke width, in <span class="val" id="swV"></span></label><input type="range" id="sw" min="0.75" max="2.5" step="0.125" value="1.25">
  <p class="note" style="margin:2px 0">Spoke length is measured between the centres of the two end half circles.</p>
  <label>Rivet hole, in <span class="val" id="rhV"></span></label><input type="range" id="rh" min="0.125" max="0.5" step="0.125" value="0.25">
  <label>Gap the router must cut between parts, in <span class="val" id="clV"></span></label><input type="range" id="cl" min="0.0625" max="0.5" step="0.0625" value="0.125">
 </div>
 <div class="card note"><b>Reading it.</b> Green = one part: a pentagon plate plus the spokes attached to it. Orange = loose spokes cut on this part's sheet, each nested in a window. Every loose spoke has a number; the same number marks each place it rivets to, which may be on a neighbouring part. Purple = an end that rivets to the spine.</div>
</div><div>
 <div class="card"><h2>One section laid flat (true size)</h2><div id="flat"></div><div class="stats" id="stats"></div><p class="note" id="fit"></p></div>
 <div class="card" id="spineCard"><h2>The spine laid flat (true size)</h2><div id="spine"></div><p class="note" id="spineNote"></p></div>
 <div class="card tbl"><h2>Does it fit? Loose spokes finding a window, all parts of this shape</h2><div id="tbl"></div></div>
</div></div></main>
<script>__JS__</script>
<script>
const DATA = __DATA__, SPINES = __SPINES__, FACTS = __FACTS__;
const $ = id => document.getElementById(id), fmt = (x, n = 2) => Number(x).toFixed(n);
let R = null;
const opts = () => ({ spoke_width: +$('sw').value, rivet_hole: +$('rh').value, clearance: +$('cl').value });
const list = () => DATA[$('layout').value + '|' + $('rings').value];
function fillPents() { $('pent').innerHTML = list().map((p, i) => `<option value="${i}">Pentagon ${p.pent}</option>`).join(''); $('pent').value = Math.floor(list().length / 2); }
function table() {
  const rows = [1, 1.25, 1.5, 2].map(sw => {
    let n = 0, fit = 0, onSheet = 0;
    for (const P of list()) { const r = PatchDraw.prepare(P, { ...opts(), spoke_width: sw }); n += r.stats.loose; fit += r.stats.nested; onSheet += r.size.fits ? 1 : 0; }
    return `<tr class="${sw === +$('sw').value ? 'cur' : ''}"><td>${sw} in</td><td>${fit} of ${n}</td><td>${onSheet} of ${list().length}</td></tr>`;
  }).join('');
  $('tbl').innerHTML = `<table><tr><th>Spoke width</th><th>Loose spokes that sit in a window</th><th>Patches that fit a 4 x 8 ft sheet</th></tr>${rows}</table>`;
}
function render() {
  const P = list()[+$('pent').value]; if (!P) return;
  const o = opts(); R = PatchDraw.prepare(P, o); const st = R.stats, sz = R.size;
  $('swV').textContent = o.spoke_width; $('rhV').textContent = o.rivet_hole; $('clV').textContent = o.clearance;
  $('flat').innerHTML = PatchDraw.svg(R, o, false);
  $('stats').innerHTML = [['Loose spokes cut on this sheet', st.loose], ['Not fitting a window', st.loose - st.nested], ['Loose length', fmt(st.lMin, 1) + ' to ' + fmt(st.lMax, 1) + ' in'], ['Patch size', fmt(Math.max(sz.W, sz.H), 1) + ' x ' + fmt(Math.min(sz.W, sz.H), 1) + ' in'], ['Ends riveted to the spine', st.toSpine]].map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  $('fit').innerHTML = (sz.fits ? 'Fits a 4 x 8 ft sheet' : '<span class="bad">Does not fit a 4 x 8 ft sheet</span>') + ` (smallest box ${fmt(sz.W, 1)} x ${fmt(sz.H, 1)} in), loose spokes included.` +
    (st.pentInPatch.length ? ` <span class="bad">Another pentagon (${st.pentInPatch.join(', ')}) is inside this patch and is treated as ordinary windows, so its plate is not rigid yet. Use 1 ring.</span>` : '');
  table();
}
function spine() {
  const B = SPINES[$('layout').value]; $('spineCard').style.display = B ? '' : 'none'; if (!B) return;
  $('spine').innerHTML = PatchDraw.spineSvg(B, false);
  $('spineNote').textContent = `${B.width} in wide, ${fmt(B.length, 1)} in long, ${B.bumps.length} bumps, each with a ${B.hole} in rivet hole where a spoke connects. Drawn flat; on the tube it follows the curve.`;
}
$('layout').onchange = () => { fillPents(); render(); spine(); }; $('rings').onchange = () => { fillPents(); render(); }; $('pent').onchange = render;
const step = d => { const n = list().length; $('pent').value = (+$('pent').value + d + n) % n; render(); };
$('prev').onclick = () => step(-1); $('next').onclick = () => step(1);
['sw', 'rh', 'cl'].forEach(id => $(id).oninput = render);
function compare() {
  const f = k => FACTS[k], row = (k, name) => `<tr><td>${name}</td><td>${f(k).pentagons}</td><td>${f(k).complete}</td><td>${f(k).lost}</td><td>${f(k).bumps}</td><td>${fmt(f(k).gap_min, 1)} to ${fmt(f(k).gap_max, 1)} in</td><td>${fmt(f(k).loose_min)} to ${fmt(f(k).loose_max)} in</td></tr>`;
  $('cmp').innerHTML = `<h2>The two ways to build the spine, side by side</h2><div class="tbl"><table><tr><th></th><th>Pentagons</th><th>Complete parts</th><th>Lost to the spine</th><th>Spine bumps</th><th>Gap between bumps</th><th>Loose spoke length</th></tr>${row('smile-tube', 'A: spine cut through the existing layout')}${row('smile-tube-clear', 'B: layout built around the spine')}</table></div><p class="note">Pick A or B under Shape below to see each one. Complete parts exclude pentagons in the greyed extension at the tube ends.</p>`;
}
fillPents(); render(); spine(); compare();
</script></body></html>"""
opts = "".join(f'<option value="{k}">{v}</option>' for k, v in labels.items())
html = PAGE.replace("__OPTS__", opts).replace("__JS__", js).replace("__DATA__", json.dumps(data, separators=(",", ":"))).replace("__SPINES__", json.dumps(spines, separators=(",", ":"))).replace("__FACTS__", json.dumps(facts))
open(os.path.join(HERE, "snapshot.html"), "w", encoding="utf-8").write(html)
print("snapshot.html", round(len(html) / 1024), "KB")
