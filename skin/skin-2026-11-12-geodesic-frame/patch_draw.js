/* Flat patch: spread the free ends apart, check they can be cut, draw it, measure it.
   Used by frame_page.html (local tool) and by the no-install explorer page. Units: inches.
   prepare(P, o) -> result      P = one patch from frame.patch_data(), o = settings
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
  function cross(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
  function segSeg(a, b, c, d) {
    const d1 = cross(a, b, c), d2 = cross(a, b, d), d3 = cross(c, d, a), d4 = cross(c, d, b);
    if (((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0))) return 0;
    return Math.min(ptSeg(a, c, d), ptSeg(b, c, d), ptSeg(c, a, b), ptSeg(d, a, b));
  }

  function prepare(P, o) {
    const w = o.spoke_width, r = Math.max(o.circle_diameter, w) / 2, clear = o.clearance;   // an end is at least as wide as its spoke
    const pos = {}; Object.keys(P.pos).forEach(k => pos[k] = P.pos[k]);
    const cuts = P.cuts.map(c => ({ own: String(c.own), target: String(c.target), L: c.L, free: c.free0.slice(), free0: c.free0.slice(), spread: false }));
    const solid = P.solid.map(([a, b]) => [String(a), String(b)]);

    // everything a free end must stay clear of, other than the spoke it belongs to
    function clearanceOf(c, F) {
      const O = pos[c.own]; let m = Infinity;
      const seg = [O, F];
      for (const k in pos) {                                            // hub discs (not the hub this spoke hangs from)
        if (k === c.own) continue;
        m = Math.min(m, ptSeg(pos[k], O, F) - w / 2 - r, dist(F, pos[k]) - 2 * r);
      }
      for (const [a, b] of solid) {                                       // spokes that stay attached
        const A = pos[a], B = pos[b], touches = a === c.own || b === c.own;
        m = Math.min(m, ptSeg(F, A, B) - r - w / 2);
        if (!touches) m = Math.min(m, segSeg(O, F, A, B) - w);
      }
      for (const d of cuts) {
        if (d === c) continue;
        const A = pos[d.own], B = d.free, touches = d.own === c.own;
        m = Math.min(m, ptSeg(F, A, B) - r - w / 2, dist(F, B) - 2 * r);
        if (!touches) m = Math.min(m, segSeg(O, F, A, B) - w, ptSeg(B, O, F) - r - w / 2);
      }
      return m;
    }

    for (const c of cuts) {                                                // spread apart if too close to anything
      const O = pos[c.own], T = pos[c.target];
      c.natural = dist(c.free0, T);
      if (!o.spread || clearanceOf(c, c.free0) >= clear - 1e-6) continue;
      let bestF = null, bestPull = Infinity, fallback = null, fbClear = -Infinity;
      for (let deg = 0; deg < 360; deg += 2) {                              // swing the free spoke round its own hub
        const t = deg * Math.PI / 180, F = [O[0] + c.L * Math.cos(t), O[1] + c.L * Math.sin(t)];
        const cl = clearanceOf(c, F);
        if (cl >= clear - 1e-6) { const pull = dist(F, T); if (pull < bestPull) { bestPull = pull; bestF = F; } }
        else if (cl > fbClear) { fbClear = cl; fallback = F; }
      }
      c.free = bestF || fallback; c.spread = true;
    }
    for (const c of cuts) {
      c.gap = dist(c.free, pos[c.target]);
      c.clear = clearanceOf(c, c.free);
      c.blocked = c.clear < clear - 1e-6;
    }
    const pts = Object.values(pos).concat(cuts.map(c => c.free));
    const pad = r;
    let best = null;
    for (let deg = 0; deg < 90; deg++) {
      const t = deg * Math.PI / 180; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const p of pts) { const q = rot(p, t); x0 = Math.min(x0, q[0]); x1 = Math.max(x1, q[0]); y0 = Math.min(y0, q[1]); y1 = Math.max(y1, q[1]); }
      const W = x1 - x0 + 2 * pad, H = y1 - y0 + 2 * pad;
      if (!best || W * H < best.W * best.H) best = { W, H, deg };
    }
    best.fits = Math.min(best.W, best.H) <= SHEET[0] && Math.max(best.W, best.H) <= SHEET[1];
    const gaps = cuts.map(c => c.gap).sort((a, b) => b - a);
    return {
      P, pos, cuts, solid, size: best,
      stats: {
        cuts: cuts.length, blocked: cuts.filter(c => c.blocked).length, spread: cuts.filter(c => c.spread).length,
        gapMax: gaps[0] || 0, gapMean: gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : 0,
        hubs: Object.keys(pos).length, spokes: solid.length + cuts.length, joints: P.joint.length,
        pentInPatch: P.pent_in_patch
      }
    };
  }

  function svg(R, o, forFile) {
    const { P, pos, cuts, solid } = R;
    const w = o.spoke_width, cd = o.circle_diameter, rh = o.rivet_hole, r = cd / 2;
    const all = Object.values(pos).concat(cuts.map(c => c.free));
    const x0 = Math.min(...all.map(p => p[0])) - r - 1.2, x1 = Math.max(...all.map(p => p[0])) + r + 1.2;
    const y0 = Math.min(...all.map(p => p[1])) - r - 1.2, y1 = Math.max(...all.map(p => p[1])) + r + 1.2;
    const W = x1 - x0, H = y1 - y0, X = p => (p[0] - x0).toFixed(3), Y = p => (y1 - p[1]).toFixed(3);
    const ink = '#1c3d2e', fill = '#3aa675', freeC = '#e0752b', plateC = '#f2a65a', gr = 0.04;
    const bar = (a, b, c, wd) => `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="${c}" stroke-width="${wd.toFixed(3)}"/>`;
    const disc = (p, rr, c, extra) => `<circle cx="${X(p)}" cy="${Y(p)}" r="${rr.toFixed(3)}" fill="${c}" stroke="${c}" ${extra || ''}/>`;
    const items = [];
    solid.forEach(([a, b]) => items.push(['bar', pos[a], pos[b], fill]));
    cuts.forEach(c => items.push(['bar', pos[c.own], c.free, freeC]));
    Object.values(pos).forEach(p => items.push(['disc', p, r, fill]));
    cuts.forEach(c => items.push(['disc', c.free, r, freeC]));
    const plate = P.plate.map(v => pos[String(v)]);
    const c0 = [plate.reduce((s, p) => s + p[0], 0) / plate.length, plate.reduce((s, p) => s + p[1], 0) / plate.length];
    const pstr = plate.map(p => X(p) + ',' + Y(p)).join(' ');
    let out = '';
    items.forEach(it => { out += it[0] === 'bar' ? bar(it[1], it[2], ink, w + 2 * gr) : disc(it[1], it[2] + gr, ink); });
    out += `<polygon points="${pstr}" fill="${ink}" stroke="${ink}" stroke-width="${2 * gr}" stroke-linejoin="round"/>`;
    out += `<polygon points="${pstr}" fill="${plateC}" stroke="${plateC}" stroke-linejoin="round"/>`;
    items.forEach(it => { out += it[0] === 'bar' ? bar(it[1], it[2], it[3], w) : disc(it[1], it[2], it[3]); });
    out += `<circle cx="${X(c0)}" cy="${Y(c0)}" r="${(P.hole / 2).toFixed(3)}" fill="#fff" stroke="${ink}" stroke-width="0.06"/>`;
    const targets = new Set(cuts.map(c => c.target));
    cuts.forEach(c => { [c.free, pos[c.target]].forEach(p => out += `<circle cx="${X(p)}" cy="${Y(p)}" r="${(rh / 2).toFixed(3)}" fill="#fff" stroke="${ink}" stroke-width="0.04"/>`); });
    P.joint.forEach(v => { if (!targets.has(String(v))) out += `<circle cx="${X(pos[String(v)])}" cy="${Y(pos[String(v)])}" r="${(rh / 2).toFixed(3)}" fill="#fff" stroke="#3b6fb0" stroke-width="0.05"/>`; });
    cuts.forEach(c => {
      const a = c.free, b = pos[c.target], col = c.blocked ? '#c0281d' : '#c0281d';
      if (c.blocked) out += `<circle cx="${X(a)}" cy="${Y(a)}" r="${(r + 0.12).toFixed(3)}" fill="none" stroke="#c0281d" stroke-width="0.12"/>`;
      out += `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="${col}" stroke-width="0.09" stroke-dasharray="0.35 0.25"/>`;
      const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (r + 0.9)];
      out += `<text x="${X(m)}" y="${Y(m)}" font-size="0.95" text-anchor="middle" fill="${col}" stroke="#fff" stroke-width="0.22" paint-order="stroke" font-family="sans-serif">${c.gap.toFixed(2)}</text>`;
    });
    const sb = [x0 + 1, y0 + 1];
    out += `<line x1="${X(sb)}" y1="${Y(sb)}" x2="${X([sb[0] + 6, sb[1]])}" y2="${Y(sb)}" stroke="#222" stroke-width="0.15"/><text x="${X([sb[0], sb[1] + 0.35])}" y="${Y([sb[0], sb[1] + 0.35])}" font-size="1" font-family="sans-serif" fill="#222">6 in</text>`;
    const size = forFile ? ` width="${W.toFixed(2)}in" height="${H.toFixed(2)}in"` : '';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}"${size} font-family="sans-serif">${out}</svg>`;
  }

  const api = { prepare, svg, SHEET };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else g.PatchDraw = api;
})(typeof window !== 'undefined' ? window : globalThis);
