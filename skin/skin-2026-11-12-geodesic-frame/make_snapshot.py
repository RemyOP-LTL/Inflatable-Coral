#!/usr/bin/env python3
"""Builds snapshot.html: a single page with pictures and numbers from the current layouts (no server needed).
Run: python3 make_snapshot.py"""
import os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import frame as F

def svg(fr, pent, plate, rings=1):
    s = F.patch_svg(fr, fr.flatten(pent, rings), dict(plate=plate))
    return re.sub(r' width="[\d.]+in" height="[\d.]+in"', "", s, count=1)

def summary(fr, rings=1):
    rows = []
    for q in fr.pentagons(rings):
        if q["ok"]:
            pt = fr.flatten(q["id"], rings); st = F.patch_stats(fr, pt, F.DEFAULTS); rows.append(st)
    return dict(n=len(fr.pentagons(rings)), ok=len(rows), cuts=np.mean([r["cuts"] for r in rows]),
                med=float(np.median([r["gap_max"] for r in rows])), worst=max(r["gap_max"] for r in rows),
                size=np.mean([max(r["size"]["w"], r["size"]["h"]) for r in rows]), fits=all(r["size"]["fits"] for r in rows))

tube = F.Frame(os.path.join(HERE, "layouts", "tube-edge5", "layout.json"))
dome = F.Frame(os.path.join(HERE, "layouts", "dome-edge5", "layout.json"))
tp = [q["id"] for q in tube.pentagons(1) if q["ok"]]; dp = [q["id"] for q in dome.pentagons(1) if q["ok"]]
tid, did = tp[len(tp) // 2], dp[len(dp) // 2]
ts, ds = summary(tube), summary(dome)
row = lambda name, s, fr: (f"<tr><td>{name}</td><td>{fr.params.get('EDGE')} in</td><td>{s['ok']} of {s['n']}</td><td>{s['cuts']:.1f}</td>"
                           f"<td>{s['med']:.2f} in</td><td>{s['worst']:.2f} in</td><td>{s['size']:.0f} in</td><td>{'yes' if s['fits'] else 'no'}</td></tr>")
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Frame snapshot</title><style>
:root{{--bg:#f6f5f1;--panel:#fff;--ink:#1d2320;--mute:#66706a;--line:#dcdad2;--accent:#1f7a55}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#161a18;--panel:#1f2522;--ink:#e8ece9;--mute:#9aa69f;--line:#34403a;--accent:#4fc08d}}}}
:root[data-theme="dark"]{{--bg:#161a18;--panel:#1f2522;--ink:#e8ece9;--mute:#9aa69f;--line:#34403a;--accent:#4fc08d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1000px;margin:0 auto;padding:20px 16px 48px}}h1{{font-size:24px;margin:.2em 0}}h2{{font-size:18px;margin:1.6em 0 .4em}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin:12px 0}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}@media(max-width:700px){{.two{{grid-template-columns:1fr}}}}
svg{{width:100%;height:auto;display:block}}.cap{{color:var(--mute);font-size:14px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}}th{{color:var(--mute);font-weight:500}}
.tbl{{overflow-x:auto}}code{{background:var(--bg);padding:1px 5px;border-radius:4px}}
</style></head><body><main>
<h1>Geodesic-frame patch: first look</h1>
<p class="cap">Branch <code>skin-2026-11-12-geodesic-frame</code> &middot; tube is the main shape, dome second &middot; hub spacing 5 in, 1 in spokes, 1.5 in hub circles, 0.25 in rivet holes.</p>

<h2>Your question 1: the two ways to draw the pentagon</h2>
<p>Same patch, same tube, same spokes. Only the pentagon plate differs. Left: the plate <b>is the pentagon</b>, with a hub circle on each corner. Right: a <b>round hub</b>, a disc just big enough to swallow the five corner circles, with the polyp hole in it. Spokes leave from the disc.</p>
<div class="card two"><div>{svg(tube, tid, 'outline')}<div class="cap">A. Pentagon outline</div></div><div>{svg(tube, tid, 'round')}<div class="cap">B. Round hub</div></div></div>
<p class="cap">Green = spokes and hubs that stay attached. Orange spokes end in a free circle. Red dashed line and number = how far (in) to pull that circle to the hub it belongs to, then rivet through the two small holes. Blue-ringed holes are hubs that will join the next patch.</p>
<p>What differs: B leaves an even rim all round the polyp hole (A has thin spots where the pentagon is a little irregular, the known issue from before). B also covers more of the neighbouring windows. The spoke positions, and so the pull distances, are the same in both.</p>

<h2>One patch on the dome</h2>
<div class="card" style="max-width:520px">{svg(dome, did, 'outline')}</div>

<h2>Across the whole skin (1 ring of windows round each pentagon)</h2>
<div class="card tbl"><table><tr><th>Shape</th><th>Spacing</th><th>Usable pentagons</th><th>Cut spokes per patch</th><th>Longest pull, typical</th><th>Longest pull, worst</th><th>Patch size</th><th>All fit 4 x 8 ft</th></tr>
{row('Tube (16 in across)', ts, tube)}{row('Dome (48 in)', ds, dome)}</table></div>
<ul><li>"Usable" means the whole patch lies on the real skin, not the greyed extension past an open edge.</li>
<li>Check done: on a perfectly flat honeycomb the same code gives a pull of 0.00 in, so the numbers above come from the curved surface, not from a bug.</li>
<li>Two rings of windows put several other pentagons (3 to 5) inside the patch at this spacing, and the tool does not yet keep those plates rigid. One ring is the working setting.</li></ul>

<h2>Try it</h2>
<p>In the simulator at <code>http://127.0.0.1:8800/</code> pick branch <code>skin-2026-11-12-geodesic-frame</code> and press <b>Get latest changes</b>. Then double-click <code>skin/skin-2026-11-12-geodesic-frame/Start Frame Tool.command</code> in your <code>~/coral-simulator</code> folder. It opens <code>http://127.0.0.1:8820/</code>.</p>
</main></body></html>"""
open(os.path.join(HERE, "snapshot.html"), "w", encoding="utf-8").write(html)
print("tube", ts, "\ndome", ds)
