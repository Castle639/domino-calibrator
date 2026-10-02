// The page's local check before it is published: file reading, Measure and Copy, served over http, in four hosts, and
// what the FIRST click of Copy put on the clipboard, read back by a second page (the clipboard is the browser's). Nothing
// leaves. The tenth room (29 Sept 2026): written for his test of the page; the clipboard read back after his "Could not
// copy, then Copied". Usage: node audit_page_check.js SAMPLE.fits
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const PAGE = path.resolve(__dirname, '..', 'page'), FITS = process.argv[2];
const REC = { stn: '568', desig: '3I', astcat: 'Gaia3', submitter: 'A. N. Observer', measurers: 'A. N. Observer', design: 'Reflector', aperture: '0.5', detector: 'CCD' };
const hostHtml = (src, allow) => '<!doctype html><title>host</title><input id="h" value="elsewhere"><iframe id="f" src="' + src + '"' +
  (allow ? ' allow="clipboard-write"' : '') + ' sandbox="allow-scripts allow-same-origin allow-forms" style="width:1000px;height:1400px"></iframe>';
const server = http.createServer((req, res) => {
  const u = req.url.split('?')[0];
  if (u === '/reader') { res.writeHead(200, { 'content-type': 'text/html' }); return res.end('<!doctype html><title>reader</title><input id="h">'); }
  if (u.startsWith('/host')) { res.writeHead(200, { 'content-type': 'text/html' }); return res.end(hostHtml('http://127.0.0.1:' + server.address().port + '/', u.startsWith('/host-allow'))); }
  const f = u === '/' ? 'index.html' : u.slice(1);
  if (!['index.html', 'zeroap.js'].includes(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': f.endsWith('.js') ? 'text/javascript' : 'text/html' }); res.end(fs.readFileSync(path.join(PAGE, f)));
});
async function run(label, browser, port, o) {
  const ctx = await browser.newContext();
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: 'http://localhost:' + port });   // the reader's, and a host's
  if (o.grant) await ctx.grantPermissions(['clipboard-write'], { origin: 'http://127.0.0.1:' + port });        // the page's own
  const reader = await ctx.newPage(); await reader.goto('http://localhost:' + port + '/reader');
  await reader.evaluate(() => navigator.clipboard.writeText('EMPTY'));
  const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message));
  let f;
  if (o.framed) { await page.goto('http://localhost:' + port + (o.allow ? '/host-allow' : '/host')); f = page.frameLocator('#f'); }
  else { await page.goto('http://127.0.0.1:' + port + '/'); f = page; }
  await f.locator('#file').setInputFiles(FITS);
  await f.locator('#info').filter({ hasText: 'px' }).waitFor({ timeout: 10000 });
  for (const [id, v] of Object.entries(REC)) await f.locator('#' + id).fill(v);
  await f.locator('#mode').selectOption('CCD');
  await f.locator('#run').click();
  await f.locator('#status').filter({ hasText: /done|radii|Error/ }).waitFor({ timeout: 60000 });
  const out = { info: await f.locator('#info').textContent(), status: await f.locator('#status').textContent(), zero: await f.locator('#zero').textContent() };
  const ades = await f.locator('#ades').textContent();
  if (o.focusOutside) await page.locator('#h').click();          // the user was elsewhere, then clicks Copy in the frame
  await f.locator('#copy').click(); await page.waitForTimeout(500);
  out.first_click = await f.locator('#copynote').textContent();
  await reader.bringToFront(); await reader.locator('#h').click();
  const clip = await reader.evaluate(() => navigator.clipboard.readText()).catch((e) => 'READ FAILED ' + e.message);
  out.clipboard = clip === ades ? 'the record, byte for byte' : (clip === 'EMPTY' ? 'unchanged (nothing copied)' : 'something else: ' + JSON.stringify(clip.slice(0, 60)));
  console.log('== ' + label); for (const [k, v] of Object.entries(out)) console.log('   ' + k + ': ' + v.replace(/\n/g, ' / '));
  console.log('   page errors: ' + (errors.length ? errors.join(' | ') : 'none'));
  await ctx.close();
}
(async () => {
  await new Promise((r) => server.listen(0, '127.0.0.1', r)); const port = server.address().port;
  const browser = await chromium.launch({ args: ['--host-resolver-rules=MAP localhost 127.0.0.1'] });
  await run('A. a page on its own, the clipboard granted', browser, port, { grant: true });
  await run('B. a page on its own, the clipboard not granted', browser, port, {});
  await run('C. a sandboxed cross-origin frame, no clipboard permission', browser, port, { framed: true });
  await run('D. a sandboxed cross-origin frame allowed the clipboard, the user elsewhere before the click', browser, port, { framed: true, allow: true, focusOutside: true });
  await browser.close(); server.close();
})().catch((e) => { console.error('FAILED: ' + e.message); process.exit(1); });
