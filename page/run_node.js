// Node harness for zeroap.js (the page's engine): node run_node.js cutout.fits G|M [x y]  ->  JSON on stdout
// (no ADES record: that needs the user's own values; test_hardening_page.py tests adesPSV directly)
const fs = require('fs');
const Z = require('./zeroap.js');
const [path, est, xs, ys] = process.argv.slice(2);
const b = fs.readFileSync(path);
const hdus = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));
const h = hdus.find(u => u.readable);            // decoded when used (round 3)
let x0, y0;
if (xs !== undefined) { x0 = Number(xs); y0 = Number(ys); } else { [x0, y0] = Z.brightestStart(h.data, h.nx, h.ny); }
const o = Z.shrink(h.data, h.nx, h.ny, x0, y0, { estimator: est || 'G' });
const w = Z.makeWCS(h.header, hdus[0].header, hdus);
const radec = w && !w.unsupported && Number.isFinite(o.x0) ? w.pixToSky(o.x0, o.y0) : null;
const t = Z.midExposure(Z.mergeHeaders(hdus[0].header, h.header));
process.stdout.write(JSON.stringify({ start: [x0, y0], x: o.x, y: o.y, ok: o.ok, reason: o.reason, x0: o.x0, y0: o.y0, x2: o.x2, y2: o.y2,
  nbad: o.nbad, radec: radec, time: t.time || null, time_error: t.error || null }));
