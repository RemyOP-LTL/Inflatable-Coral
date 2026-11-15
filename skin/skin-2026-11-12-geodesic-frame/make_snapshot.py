#!/usr/bin/env python3
"""Builds snapshot.html: ONE self-contained page (no server, no install) with the flattened patches of the
tube and dome baked in, and the same JavaScript (patch_draw.js) as the local tool. Sliders work live.
Run: python3 make_snapshot.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frame as F

data = {}
for lid, label in (("tube-edge5", "Tube (16 in across), hub spacing 5 in"), ("dome-edge5", "Dome (48 in), hub spacing 5 in")):
    fr = F.Frame(os.path.join(HERE, "layouts", lid, "layout.json"))
    for rings in (1, 2):
        data[f"{lid}|{rings}"] = [F.patch_data(fr, fr.flatten(q["id"], rings)) for q in fr.pentagons(rings) if q["ok"]]
labels = {"tube-edge5": "Tube (16 in across)", "dome-edge5": "Dome (48 in)"}
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
<p class="note">Branch <code>skin-2026-11-12-geodesic-frame</code>. Hubs at the polygon corners, spokes between them, pentagon as a solid plate with the polyp hole. One pentagon patch laid flat, true size. Everything here runs in the page: nothing to install.</p>
<div class="grid"><div>
 <div class="card"><h2>Patch</h2>
  <label>Shape</label><select id="layout">__OPTS__</select>
  <label>Rings of windows round the pentagon</label><select id="rings"><option value="1">1 (the five touching windows)</option><option value="2">2 (more rings)</option></select>
  <label>Pentagon</label><div class="row"><button id="prev">&larr;</button><select id="pent" style="flex:4"></select><button id="next">&rarr;</button></div>
 </div>
 <div class="card"><h2>Plastic</h2>
  <label>Spoke width, in <span class="val" id="swV"></span></label><input type="range" id="sw" min="0.5" max="2.5" step="0.25" value="1.5">
  <label>Hub circle diameter, in <span class="val" id="cdV"></span></label><input type="range" id="cd" min="0.5" max="2" step="0.25" value="1">
  <label>Rivet hole, in <span class="val" id="rhV"></span></label><input type="range" id="rh" min="0.125" max="0.5" step="0.125" value="0.25">
  <label>Gap the router must cut between parts, in <span class="val" id="clV"></span></label><input type="range" id="cl" min="0.0625" max="0.5" step="0.0625" value="0.125">
  <label><input type="checkbox" id="spread" checked> Swing free ends apart so they can be cut</label>
  <p class="note">Your first settings were 1 in spokes, 1.5 in hubs. Try them: with the box unticked, every pinned pair overlaps.</p>
 </div>
 <div class="card note"><b>Reading it.</b> Orange spokes are cut: attached at one end, free circle at the other. Red dashed line and number = how far (in) to pull that circle to its hub, then rivet through the two small holes. A red ring = that end still touches something. Blue-ringed holes join the next patch.</div>
</div><div>
 <div class="card"><h2>Laid flat (true size)</h2><div id="flat"></div><div class="stats" id="stats"></div><p class="note" id="fit"></p></div>
 <div class="card tbl"><h2>Size trade-off, all patches of this shape and ring count</h2><div id="tbl"></div>
  <p class="note">Spreading the free ends apart makes the pull roughly the wider of spoke and hub, plus the router gap, plus whatever the surface already needs. A hub narrower than its spoke is hidden by the spoke, so only the spoke width matters then.</p></div>
</div></div></main>
<script>__JS__</script>
<script>
const DATA = __DATA__;
const $ = id => document.getElementById(id), fmt = (x, n = 2) => Number(x).toFixed(n);
let cur = null, R = null;
const opts = () => ({ spoke_width: +$('sw').value, circle_diameter: +$('cd').value, rivet_hole: +$('rh').value, clearance: +$('cl').value, spread: $('spread').checked });
const list = () => DATA[$('layout').value + '|' + $('rings').value];
function fillPents() { $('pent').innerHTML = list().map((p, i) => `<option value="${i}">Pentagon ${p.pent}</option>`).join(''); $('pent').value = Math.floor(list().length / 2); }
function table() {
  const rows = [[1, 1.5], [1, 1], [1.5, 1], [1.5, 1.5], [1.25, 1], [2, 1], [0.75, 0.75]].map(([sw, cd]) => {
    let cuts = 0, blocked = 0, sum = 0, mx = 0;
    for (const P of list()) { const r = PatchDraw.prepare(P, { ...opts(), spoke_width: sw, circle_diameter: cd }); cuts += r.stats.cuts; blocked += r.stats.blocked; sum += r.stats.gapMean * r.stats.cuts; mx = Math.max(mx, r.stats.gapMax); }
    const on = sw === +$('sw').value && cd === +$('cd').value;
    return `<tr class="${on ? 'cur' : ''}"><td>${sw} in</td><td>${cd} in</td><td>${blocked} of ${cuts}</td><td>${fmt(sum / cuts)} in</td><td>${fmt(mx)} in</td></tr>`;
  }).join('');
  $('tbl').innerHTML = `<table><tr><th>Spoke</th><th>Hub</th><th>Cannot be cut</th><th>Average pull</th><th>Worst pull</th></tr>${rows}</table>`;
}
function render() {
  const P = list()[+$('pent').value]; if (!P) return;
  const o = opts(); R = PatchDraw.prepare(P, o); const st = R.stats, sz = R.size;
  $('swV').textContent = o.spoke_width; $('cdV').textContent = o.circle_diameter; $('rhV').textContent = o.rivet_hole; $('clV').textContent = o.clearance;
  $('flat').innerHTML = PatchDraw.svg(R, o, false);
  $('stats').innerHTML = [['Spokes cut', st.cuts], ['Cannot be cut yet', st.blocked], ['Longest pull', fmt(st.gapMax) + ' in'], ['Average pull', fmt(st.gapMean) + ' in'], ['Patch size', fmt(Math.max(sz.W, sz.H), 1) + ' x ' + fmt(Math.min(sz.W, sz.H), 1) + ' in']].map(([k, v]) => `<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  $('fit').innerHTML = (sz.fits ? 'Fits a 4 x 8 ft sheet.' : '<span class="bad">Does not fit a 4 x 8 ft sheet.</span>') +
    (st.pentInPatch.length ? ` <span class="bad">Another pentagon (${st.pentInPatch.join(', ')}) is inside this patch and is treated as an ordinary window, so its plate is not rigid yet. Use 1 ring.</span>` : '');
  table();
}
$('layout').onchange = () => { fillPents(); render(); }; $('rings').onchange = () => { fillPents(); render(); }; $('pent').onchange = render;
const step = d => { const n = list().length; $('pent').value = (+$('pent').value + d + n) % n; render(); };
$('prev').onclick = () => step(-1); $('next').onclick = () => step(1);
['sw', 'cd', 'rh', 'cl'].forEach(id => $(id).oninput = render); $('spread').onchange = render;
fillPents(); render();
</script></body></html>"""
opts = "".join(f'<option value="{k}">{v}</option>' for k, v in labels.items())
html = PAGE.replace("__OPTS__", opts).replace("__JS__", js).replace("__DATA__", json.dumps(data, separators=(",", ":")))
open(os.path.join(HERE, "snapshot.html"), "w", encoding="utf-8").write(html)
print("snapshot.html", round(len(html) / 1024), "KB")
