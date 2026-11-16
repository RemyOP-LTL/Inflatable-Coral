/* One flat patch for the CNC: the body (pentagon plate + attached spokes) and the LOOSE spokes, each placed
   inside a window of the body with a router gap all round it. Units: inches.
   Words: a SPOKE is a strip with a half circle at each end; its length is measured between the centres of
   those half circles. A NODE is where spoke ends meet. A loose spoke is riveted at both ends.
   prepare(P, o) -> result      P = one patch from frame.patch_data(), o = { spoke_width, rivet_hole, clearance }
   svg(result, o, forFile)      SVG text (1 unit = 1 inch)
*/
(function (g) {
  const SHEET = [48, 96];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]], add = (a, b) => [a[0] + b[0], a[1] + b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
  const len = a => Math.hypot(a[0], a[1]), dist = (a, b) => len(sub(a, b));
  const rot = (a, t) => [a[0] * Math.cos(t) - a[1] * Math.sin(t), a[0] * Math.sin(t) + a[1] * Math.cos(t)];
  function ptSeg(p, a, b) {
    const ab = sub(b, a), l2 = ab[0] * ab[0] + ab[1] * ab[1];
    let t = l2 ? ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / l2 : 0;
    t = Math.max(0, Math.min(1, t));
    return dist(p, add(a, mul(ab, t)));
  }
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  function segSeg(a, b, c, d) {
    const d1 = cross(a, b, c), d2 = cross(a, b, d), d3 = cross(c, d, a), d4 = cross(c, d, b);
    if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return 0;
    return Math.min(ptSeg(a, c, d), ptSeg(b, c, d), ptSeg(c, a, b), ptSeg(d, a, b));
  }
  function inPoly(p, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      if ((poly[i][1] > p[1]) !== (poly[j][1] > p[1]) && p[0] < (poly[j][0] - poly[i][0]) * (p[1] - poly[i][1]) / (poly[j][1] - poly[i][1]) + poly[i][0]) c = !c;
    }
    return c;
  }

  function prepare(P, o) {
    const w = o.spoke_width, r = w / 2, clear = o.clearance;
    const pos = {}; Object.keys(P.pos).forEach(k => pos[k] = P.pos[k]);
    const solid = P.solid.map(([a, b]) => [String(a), String(b)]);
    const plate = P.plate.map(v => pos[String(v)]);
    const cen = pts => [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];
    const c0 = cen(plate);
    const loose = P.cuts.map(c => ({ id: c.id, own: String(c.own), target: String(c.target), L: c.L }));

    // clearance of a capsule (axis A-B, width w) from the body and from the loose spokes already placed
    function clearanceOf(A, B, placed) {
      let m = Infinity;
      for (const k in pos) m = Math.min(m, ptSeg(pos[k], A, B) - 2 * r);
      for (const [a, b] of solid) m = Math.min(m, segSeg(A, B, pos[a], pos[b]) - w);
      for (let i = 0; i < plate.length; i++) {
        const p = plate[i], q = plate[(i + 1) % plate.length];
        m = Math.min(m, segSeg(A, B, p, q) - r);
      }
      if (inPoly(A, plate) || inPoly(B, plate)) m = Math.min(m, -1);
      for (const l of placed) m = Math.min(m, segSeg(A, B, l.a, l.b) - w);
      return m;
    }
    // each loose spoke goes in a window it closes (a window that has both of its end nodes), else anywhere free
    const pts0 = Object.values(pos);
    const bx0 = Math.min(...pts0.map(p => p[0])), bx1 = Math.max(...pts0.map(p => p[0])), by0 = Math.min(...pts0.map(p => p[1])), by1 = Math.max(...pts0.map(p => p[1]));
    const placed = [];
    for (const l of loose) {
      let wins = P.window_nodes.map(ns => ns.map(String)).filter(ns => ns.includes(l.own) && ns.includes(l.target));
      if (!wins.length) wins = P.window_nodes.map(ns => ns.map(String)).filter(ns => ns.includes(l.own));
      const centres = wins.map(ns => cen(ns.filter(k => pos[k]).map(k => pos[k])));
      let best = null;
      const tryCentre = (c, step, span, dstep) => {
        for (let dx = -span; dx <= span + 1e-9; dx += step) for (let dy = -span; dy <= span + 1e-9; dy += step) {
          const C = [c[0] + dx, c[1] + dy];
          for (let deg = 0; deg < 180; deg += dstep) {
            const t = deg * Math.PI / 180, h = [Math.cos(t) * l.L / 2, Math.sin(t) * l.L / 2];
            const A = sub(C, h), B = add(C, h), cl = clearanceOf(A, B, placed);
            const score = cl - 0.02 * Math.hypot(dx, dy);
            if (!best || score > best.score) best = { A, B, cl, score };
          }
        }
      };
      centres.forEach(c => tryCentre(c, 0.5, 2, 4));
      if (!best || best.cl < clear) for (let x = bx0; x <= bx1; x += 2) for (let y = by0; y <= by1; y += 2) tryCentre([x, y], 1, 0, 6);
      l.a = best.A; l.b = best.B; l.clear = best.cl; l.ok = best.cl >= clear - 1e-6; l.inWindow = centres.some(c => dist(c, cen([best.A, best.B])) < 3.5);
      placed.push(l);
    }
    // size on the sheet: everything cut from this patch
    const pts = Object.values(pos).concat(...loose.map(l => [l.a, l.b]));
    let bestBox = null;
    for (let deg = 0; deg < 90; deg++) {
      const t = deg * Math.PI / 180; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const p of pts) { const q = rot(p, t); x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); }
      const W = x1 - x0 + 2 * r, H = y1 - y0 + 2 * r;
      if (!bestBox || W * H < bestBox.W * bestBox.H) bestBox = { W, H, deg };
    }
    bestBox.fits = Math.min(bestBox.W, bestBox.H) <= SHEET[0] && Math.max(bestBox.W, bestBox.H) <= SHEET[1];
    const Ls = loose.map(l => l.L);
    return {
      P, pos, solid, loose, plate, c0, size: bestBox,
      stats: {
        loose: loose.length, nested: loose.filter(l => l.ok && l.inWindow).length, blocked: loose.filter(l => !l.ok).length,
        lMin: Ls.length ? Math.min(...Ls) : 0, lMax: Ls.length ? Math.max(...Ls) : 0, lMean: Ls.length ? Ls.reduce((a, b) => a + b, 0) / Ls.length : 0,
        nodes: Object.keys(pos).length, spokes: solid.length, ends: P.ends.filter(e => !e.spine).length, toSpine: P.ends.filter(e => e.spine).length, joins: 0, onSpine: 0, pentInPatch: P.pent_in_patch,
        arms: (P.arms || []).length, tiltMin: (P.arms || []).length ? Math.min(...P.arms.map(a => Math.abs(a.tilt))) : 0, tiltMax: (P.arms || []).length ? Math.max(...P.arms.map(a => Math.abs(a.tilt))) : 0
      }
    };
  }

  function svg(R, o, forFile) {
    const { P, pos, solid, loose, plate, c0 } = R;
    const w = o.spoke_width, r = w / 2, rh = o.rivet_hole;
    const all = Object.values(pos).concat(...loose.map(l => [l.a, l.b]));
    const x0 = Math.min(...all.map(p => p[0])) - r - 1.2, x1 = Math.max(...all.map(p => p[0])) + r + 1.2;
    const y0 = Math.min(...all.map(p => p[1])) - r - 1.2, y1 = Math.max(...all.map(p => p[1])) + r + 1.2;
    const W = x1 - x0, H = y1 - y0, X = p => (p[0] - x0).toFixed(3), Y = p => (y1 - p[1]).toFixed(3);
    const ink = '#1c3d2e', fill = '#3aa675', looseC = '#e0752b', plateC = '#f2a65a', gr = 0.04;
    const bar = (a, b, c, wd) => `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="${c}" stroke-width="${wd.toFixed(3)}"/>`;
    const disc = (p, rr, c) => `<circle cx="${X(p)}" cy="${Y(p)}" r="${rr.toFixed(3)}" fill="${c}" stroke="${c}"/>`;
    const hole = (p, stroke, sw) => `<circle cx="${X(p)}" cy="${Y(p)}" r="${(rh / 2).toFixed(3)}" fill="#fff" stroke="${stroke}" stroke-width="${sw}"/>`;
    const items = [];
    solid.forEach(([a, b]) => items.push(['bar', pos[a], pos[b], fill]));
    Object.values(pos).forEach(p => items.push(['disc', p, r, fill]));
    loose.forEach(l => { items.push(['bar', l.a, l.b, looseC]); items.push(['disc', l.a, r, looseC]); items.push(['disc', l.b, r, looseC]); });
    const pstr = plate.map(p => X(p) + ',' + Y(p)).join(' ');
    let out = '';
    items.forEach(it => { out += it[0] === 'bar' ? bar(it[1], it[2], ink, w + 2 * gr) : disc(it[1], it[2] + gr, ink); });
    out += `<polygon points="${pstr}" fill="${ink}" stroke="${ink}" stroke-width="${2 * gr}" stroke-linejoin="round"/>`;
    out += `<polygon points="${pstr}" fill="${plateC}" stroke="${plateC}" stroke-linejoin="round"/>`;
    items.forEach(it => { out += it[0] === 'bar' ? bar(it[1], it[2], it[3], w) : disc(it[1], it[2], it[3]); });
    out += `<circle cx="${X(c0)}" cy="${Y(c0)}" r="${(P.hole / 2).toFixed(3)}" fill="#fff" stroke="${ink}" stroke-width="0.06"/>`;
    const lab = (p, t, c) => `<text x="${X(p)}" y="${Y(add(p, [0, -0.32]))}" font-size="0.85" text-anchor="middle" fill="${c}" stroke="#fff" stroke-width="0.2" paint-order="stroke" font-family="sans-serif" font-weight="600">${t}</text>`;
    loose.forEach(l => { out += hole(l.a, ink, 0.04) + hole(l.b, ink, 0.04); });
    P.ends.forEach(e => { const p = pos[String(e.node)]; out += hole(p, e.spine ? '#7b3fa0' : ink, e.spine ? 0.09 : 0.04) + lab(p, e.spine ? 'S' : e.id, e.spine ? '#7b3fa0' : '#8a3d0c'); });
    loose.forEach(l => {
      out += lab(add(cen2(l.a, l.b), [0, 0.5]), l.id + ' (' + l.L.toFixed(2) + ')', l.ok ? '#8a3d0c' : '#c0281d');
      if (!l.ok) out += `<circle cx="${X(cen2(l.a, l.b))}" cy="${Y(cen2(l.a, l.b))}" r="${(l.L / 2 + r + 0.2).toFixed(3)}" fill="none" stroke="#c0281d" stroke-width="0.1" stroke-dasharray="0.4 0.3"/>`;
    });
    // fold lines: across each arm, tangent to the inside of the round end at the plate corner (r from the corner node toward the far end)
    (P.arms || []).forEach(a => {
      const c = pos[String(a.corner)], f = pos[String(a.far)], d = sub(f, c), L = len(d), u = [d[0] / L, d[1] / L], m = add(c, mul(u, r)), nn = [-u[1], u[0]];
      const p1 = add(m, mul(nn, r * 1.15)), p2 = sub(m, mul(nn, r * 1.15));
      out += `<line x1="${X(p1)}" y1="${Y(p1)}" x2="${X(p2)}" y2="${Y(p2)}" stroke="#7a1f1f" stroke-width="0.09" stroke-dasharray="0.28 0.18"/>`;
      out += lab(add(m, mul(u, 1.25)), 'fold ' + Math.abs(a.tilt).toFixed(0) + '\u00b0', '#7a1f1f');
    });
    const sb = [x0 + 1, y0 + 1];
    out += `<line x1="${X(sb)}" y1="${Y(sb)}" x2="${X([sb[0] + 6, sb[1]])}" y2="${Y(sb)}" stroke="#222" stroke-width="0.15"/><text x="${X([sb[0], sb[1] + 0.35])}" y="${Y([sb[0], sb[1] + 0.35])}" font-size="1" font-family="sans-serif" fill="#222">6 in</text>`;
    const size = forFile ? ` width="${W.toFixed(2)}in" height="${H.toFixed(2)}in"` : '';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}"${size} font-family="sans-serif">${out}</svg>`;
  }
  const cen2 = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

  /* The spine laid flat, true size: the live-edge outline (flowing out to every attachment point) with a rivet hole
     at each attachment. B = { outline:[[sigma,u]...], hole, bumps:[{sigma,u,node}] }  */
  function spineSvg(B, forFile) {
    const tw = B.tabw || 1.25, tr = tw / 2, rh = B.hole || 0.25;
    const tabs = (B.tabs || []).map(t => ({ a: [t.sigma, t.u], b: [t.sigma + t.dir[0] * t.L, t.u + t.dir[1] * t.L], node: t.node, L: t.L }));
    const xs = B.outline.map(p => p[0]).concat(...tabs.map(t => [t.a[0], t.b[0]])), ys = B.outline.map(p => p[1]).concat(...tabs.map(t => [t.a[1], t.b[1]])), pad = 2.5 + tr;
    const x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad, W = x1 - x0, H = y1 - y0;
    const X = s => (s - x0).toFixed(3), Y = u => (y1 - u).toFixed(3);
    const ink = '#4a2a63', fill = '#b79ad6', tabC = '#c9b3e3', pts = B.outline.map(p => X(p[0]) + ',' + Y(p[1])).join(' ');
    let out = '';
    const gr = 0.04;
    tabs.forEach(t => { out += `<line x1="${X(t.a[0])}" y1="${Y(t.a[1])}" x2="${X(t.b[0])}" y2="${Y(t.b[1])}" stroke="${ink}" stroke-width="${(tw + 2 * gr).toFixed(3)}" stroke-linecap="butt"/><circle cx="${X(t.b[0])}" cy="${Y(t.b[1])}" r="${(tr + gr).toFixed(3)}" fill="${ink}"/>`; });
    out += `<polygon points="${pts}" fill="${ink}" stroke="${ink}" stroke-width="${2 * gr}" stroke-linejoin="round"/>`;
    tabs.forEach(t => { out += `<line x1="${X(t.a[0])}" y1="${Y(t.a[1])}" x2="${X(t.b[0])}" y2="${Y(t.b[1])}" stroke="${tabC}" stroke-width="${tw.toFixed(3)}"/><circle cx="${X(t.b[0])}" cy="${Y(t.b[1])}" r="${tr.toFixed(3)}" fill="${tabC}"/><circle cx="${X(t.b[0])}" cy="${Y(t.b[1])}" r="${(rh / 2).toFixed(3)}" fill="#fff" stroke="${ink}" stroke-width="0.05"/>`; });
    out += `<polygon points="${pts}" fill="${fill}" stroke="none"/>`;
    out += `<line x1="${X(x0 + pad)}" y1="${Y(y0 + 1.1)}" x2="${X(x0 + pad + 12)}" y2="${Y(y0 + 1.1)}" stroke="#222" stroke-width="0.15"/><text x="${X(x0 + pad)}" y="${Y(y0 + 1.5)}" font-size="1" font-family="sans-serif" fill="#222">12 in</text>`;
    const size = forFile ? ` width="${W.toFixed(2)}in" height="${H.toFixed(2)}in"` : '';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}"${size} font-family="sans-serif">${out}</svg>`;
  }

  /* The loose spokes, all one length, packed in rows on 4 x 8 ft sheets. o = { spoke_width, rivet_hole, clearance } */
  function looseSheetSvg(lengths, o, forFile) {
    const w = o.spoke_width, r = w / 2, g = o.clearance, rh = o.rivet_hole, L = lengths.length ? Math.max(...lengths) : 0;
    const colW = L + w + g, rowH = w + g, cols = Math.max(1, Math.floor((SHEET[1] + g) / colW)), rows = Math.max(1, Math.floor((SHEET[0] + g) / rowH)), per = cols * rows;
    const sheets = Math.ceil(lengths.length / per) || 0;
    const n = Math.min(lengths.length, per), shown = [];
    let out = `<rect x="0" y="0" width="${SHEET[1]}" height="${SHEET[0]}" fill="none" stroke="#999" stroke-width="0.2"/>`;
    for (let i = 0; i < n; i++) {
      const c = i % cols, rI = Math.floor(i / cols), x = c * colW + r, y = rI * rowH + r, a = [x, y], b = [x + lengths[i], y];
      out += `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="#e0752b" stroke-width="${w}"/><circle cx="${a[0]}" cy="${a[1]}" r="${r}" fill="#e0752b"/><circle cx="${b[0]}" cy="${b[1]}" r="${r}" fill="#e0752b"/>`;
      out += `<circle cx="${a[0]}" cy="${a[1]}" r="${rh / 2}" fill="#fff"/><circle cx="${b[0]}" cy="${b[1]}" r="${rh / 2}" fill="#fff"/>`;
    }
    const size = forFile ? ` width="${SHEET[1]}in" height="${SHEET[0]}in"` : '';
    return { svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 ${SHEET[1] + 2} ${SHEET[0] + 2}"${size}>${out}</svg>`, per, sheets, cols, rows };
  }

  const api = { prepare, svg, spineSvg, looseSheetSvg, SHEET };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else g.PatchDraw = api;
})(typeof window !== 'undefined' ? window : globalThis);
