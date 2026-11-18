/* Drawing for the frame tool. The shapes themselves (spoke outlines with tip diameter and transition radius, fold lines,
   patch placement, the spine outline) are computed by the server (geom.py, patches.py, frame_app.py); this file only
   draws them as SVG at true size (1 unit = 1 inch).
   patchSvg(P, o, forFile)         one patch: several parts joined into one flat piece   (P from /api/patch)
   spineSvg(S, forFile)            the spine piece                                       (S from /api/spine_outline)
   looseSheet(T, count, o, file)   the loose spokes packed on 4 x 8 ft sheets            (T from /api/loose)
*/
(function (g) {
  const SHEET = [48, 96];
  const INK = '#111111', PART = '#dde0e4', PLATE = '#d4d8dd', LOOSE = '#e0752b', SPINE = '#b79ad6', SPINE_INK = '#4a2a63', FOLD = '#6b6b6b';

  function box(pts, pad) {
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    return { x0: Math.min(...xs) - pad, x1: Math.max(...xs) + pad, y0: Math.min(...ys) - pad, y1: Math.max(...ys) + pad };
  }
  const ptsStr = (poly, X, Y) => poly.map(p => X(p[0]) + ',' + Y(p[1])).join(' ');
  const wrap = (b, inner, forFile) => {
    const W = b.x1 - b.x0, H = b.y1 - b.y0, size = forFile ? ` width="${W.toFixed(2)}in" height="${H.toFixed(2)}in"` : '';
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W.toFixed(2)} ${H.toFixed(2)}"${size} font-family="sans-serif">${inner}</svg>`;
  };
  const scaleBar = (b, X, Y, n) => `<line x1="${X(b.x0 + 1)}" y1="${Y(b.y0 + 1)}" x2="${X(b.x0 + 1 + n)}" y2="${Y(b.y0 + 1)}" stroke="#222" stroke-width="0.15"/><text x="${X(b.x0 + 1)}" y="${Y(b.y0 + 1.4)}" font-size="1" fill="#222">${n} in</text>`;
  const lab = (X, Y, p, t, c) => `<text x="${X(p[0])}" y="${Y(p[1])}" font-size="0.85" text-anchor="middle" fill="${c}" stroke="#fff" stroke-width="0.2" paint-order="stroke" font-weight="600">${t}</text>`;
  const foldLine = (X, Y, s) => `<line x1="${X(s[0][0])}" y1="${Y(s[0][1])}" x2="${X(s[1][0])}" y2="${Y(s[1][1])}" stroke="${FOLD}" stroke-width="0.09" stroke-dasharray="0.28 0.18"/>`;

  const ringPath = (r, X, Y) => 'M' + r.map(p => X(p[0]) + ' ' + Y(p[1])).join('L') + 'Z';
  function patchSvg(P, o, forFile) {
    const rh = o.rivet_hole, all = [];
    P.body.forEach(b => all.push(...b.ext));
    const b = box(all, 1.2), X = x => (x - b.x0).toFixed(3), Y = y => (b.y1 - y).toFixed(3);
    let out = '';
    const d = P.body.map(bd => ringPath(bd.ext, X, Y) + bd.holes.map(h => ringPath(h, X, Y)).join('')).join('');
    out += `<path d="${d}" fill="${PART}" fill-rule="evenodd" stroke="${INK}" stroke-width="0.07" stroke-linejoin="round"/>`;
    P.parts.forEach(pt => {
      out += `<polygon points="${ptsStr(pt.plate, X, Y)}" fill="${PLATE}" stroke="none"/>`;
      const c = [pt.plate.reduce((s, p) => s + p[0], 0) / pt.plate.length, pt.plate.reduce((s, p) => s + p[1], 0) / pt.plate.length];
      out += `<circle cx="${X(c[0])}" cy="${Y(c[1])}" r="${(P.hole / 2).toFixed(3)}" fill="#fff" stroke="${INK}" stroke-width="0.06"/>`;
    });
    P.parts.forEach(pt => pt.arms.forEach(a => {
      a.folds.forEach(s => { out += foldLine(X, Y, s); });
      const mx = (a.folds[0][0][0] + a.folds[0][1][0]) / 2, my = (a.folds[0][0][1] + a.folds[0][1][1]) / 2, dx = a.b[0] - a.a[0], dy = a.b[1] - a.a[1], L = Math.hypot(dx, dy) || 1;
      out += lab(X, Y, [mx + dx / L * 1.2, my + dy / L * 1.2 - 0.3], Math.abs(a.tilt).toFixed(0) + '°', FOLD);
    }));
    P.ends.forEach(e => {
      const c = e.spine ? SPINE_INK : INK;
      out += `<circle cx="${X(e.xy[0])}" cy="${Y(e.xy[1])}" r="${(rh / 2).toFixed(3)}" fill="#fff" stroke="${c}" stroke-width="${e.spine ? 0.09 : 0.04}"/>`;
      out += lab(X, Y, [e.xy[0], e.xy[1] + 0.9], e.spine ? 'S' : e.id, e.spine ? SPINE_INK : '#8a3d0c');
    });
    out += scaleBar(b, X, Y, 6);
    return wrap(b, out, forFile);
  }

  function spineSvg(S, forFile) {
    const b = box(S.outline.concat(S.holes), 2.5), X = x => (x - b.x0).toFixed(3), Y = y => (b.y1 - y).toFixed(3);
    let out = `<polygon points="${ptsStr(S.outline, X, Y)}" fill="${SPINE}" stroke="${SPINE_INK}" stroke-width="0.1" stroke-linejoin="round"/>`;
    S.holes.forEach(h => { out += `<circle cx="${X(h[0])}" cy="${Y(h[1])}" r="${(S.hole / 2).toFixed(3)}" fill="#fff" stroke="${SPINE_INK}" stroke-width="0.05"/>`; });
    out += scaleBar(b, X, Y, 12);
    return wrap(b, out, forFile);
  }

  function looseSheet(items, o, forFile) {
    const gap = o.clearance;
    let x = 0, y = 0, rowH = 0, sheetNo = 0, out = `<rect x="0" y="0" width="${SHEET[1]}" height="${SHEET[0]}" fill="none" stroke="#999" stroke-width="0.2"/>`;
    for (const it of items) {
      const b0 = box(it.t.poly, 0), cw = b0.x1 - b0.x0 + gap, ch = b0.y1 - b0.y0 + gap;
      for (let k = 0; k < it.n; k++) {
        if (x + cw > SHEET[1] + gap) { x = 0; y += rowH; rowH = 0; }
        if (y + ch > SHEET[0] + gap) { sheetNo++; x = 0; y = 0; rowH = 0; }
        rowH = Math.max(rowH, ch);
        if (sheetNo === 0) {
          const dx = x - b0.x0, dy = y - b0.y0, X = v => (v + dx).toFixed(3), Y = v => (v + dy).toFixed(3);
          out += `<polygon points="${ptsStr(it.t.poly, X, Y)}" fill="${LOOSE}" stroke="${INK}" stroke-width="0.04" stroke-linejoin="round"/>`;
          [0, it.t.L].forEach(v => { out += `<circle cx="${X(v)}" cy="${Y(0)}" r="${(it.t.hole / 2).toFixed(3)}" fill="#fff"/>`; });
          it.t.folds.forEach(s => { out += foldLine(X, Y, s); });
        }
        x += cw;
      }
    }
    const size = forFile ? ` width="${SHEET[1]}in" height="${SHEET[0]}in"` : '';
    return { svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 ${SHEET[1] + 2} ${SHEET[0] + 2}"${size}>${out}</svg>`, sheets: sheetNo + 1 };
  }

  const api = { patchSvg, spineSvg, looseSheet, SHEET };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else g.PatchDraw = api;
})(typeof window !== 'undefined' ? window : globalThis);
