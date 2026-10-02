// Headless cases for index.html (the hardening round's bar): node browser_cases.js cases.json -> a JSON list on stdout.
// Each case: {name, file, x, y, set: {inputId: value}}; each result: {name, info, status, zero, ades, tobs, copyDisabled,
// errors, missing, timeout, crashed, error}. The renderer's heap is capped at 256 MB and every wait is bounded (8 s), so a
// frozen tab ends its case instead of the machine; inputs the page does not have are listed in `missing`, not guessed.
// Round 2 (a user's session, not one load): a case may instead carry `steps`, each {file, x, y, set, run}, done in that
// order; after each step the page is read into result.steps[k] = {info, hdrnote, status, zero, ades, tobs, copyDisabled,
// text}. A field is filled and then sent `change`, as a user leaving the box would; before a load the info line, and
// before a run the status line, is emptied, so that each wait sees this step's answer, not the last one's.
// Round 3 (the third hardening round's record of 28 Sept 2026): a case may carry `init`, a script run in the page before its own
// (a slowed file read, a stubbed clipboard); a step may carry `nowait` (load without waiting for the info line: the next
// load overlaps it), `wait` (this step's bound in ms, for a large frame), `sleep` (ms, before the page is read), `copy`
// (click Copy, then read) and `eval` (an expression read from the page into steps[k].eval).
const path = require('path'), fs = require('fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const WAIT = 8000;

async function snap(page) {
  return {
    info: await page.textContent('#info', { timeout: WAIT }), hdrnote: await page.textContent('#hdrnote', { timeout: WAIT }),
    status: await page.textContent('#status', { timeout: WAIT }), zero: await page.textContent('#zero', { timeout: WAIT }),
    ades: await page.textContent('#ades', { timeout: WAIT }), tobs: await page.inputValue('#tobs', { timeout: WAIT }),
    copyDisabled: await page.$eval('#copy', (b) => b.disabled), text: await page.evaluate(() => document.body.innerText),
  };
}

async function setField(page, id, v, r) {
  const el = await page.$('#' + id);
  if (!el) { r.missing.push(id); return; }
  const tag = await el.evaluate((e) => e.tagName);
  if (tag === 'SELECT') await page.selectOption('#' + id, String(v), { timeout: WAIT });
  else { await page.fill('#' + id, String(v), { timeout: WAIT }); await page.dispatchEvent('#' + id, 'change'); }
}

async function steps(page, c, r) {
  r.steps = [];
  for (const s of c.steps) {
    const wait = s.wait || WAIT;
    if (s.file) {
      await page.evaluate(() => { document.getElementById('info').textContent = ''; });
      await page.setInputFiles('#file', s.file, s.wait ? { timeout: s.wait } : undefined);
      if (!s.nowait) await page.waitForFunction(() => document.getElementById('info').textContent.length > 0, null, { timeout: wait });
    }
    if (s.x !== undefined) { await setField(page, 'sx', s.x, r); await setField(page, 'sy', s.y, r); }
    for (const [id, v] of Object.entries(s.set || {})) await setField(page, id, v, r);
    if (s.run) {
      await page.evaluate(() => { document.getElementById('status').textContent = ''; });
      await page.click('#run', { timeout: WAIT });
      await page.waitForFunction(() => { const t = document.getElementById('status').textContent; return t.length > 0 && !/measuring/.test(t); },
        null, { timeout: wait });
    }
    if (s.copy) { await page.click('#copy', { timeout: WAIT }); await page.waitForTimeout(500); }
    if (s.sleep) await page.waitForTimeout(s.sleep);
    const k = await snap(page);
    if (s.eval) k.eval = await page.evaluate(s.eval);
    r.steps.push(k);
  }
}

(async () => {
  const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const browser = await chromium.launch({ args: ['--js-flags=--max-old-space-size=256'] });
  const out = [];
  for (const c of cases) {
    const page = await browser.newPage();
    const r = { name: c.name, errors: [], missing: [] };
    page.on('pageerror', (e) => r.errors.push(String(e)));
    page.on('crash', () => { r.crashed = true; });
    try {
      if (c.init) await page.addInitScript({ content: c.init });
      await page.goto('file://' + path.resolve(__dirname, 'index.html'));
      if (c.steps) await steps(page, c, r);
      else {
      await page.setInputFiles('#file', c.file);
      await page.waitForFunction(() => document.getElementById('info').textContent.length > 0, null, { timeout: WAIT });
      r.info = await page.textContent('#info', { timeout: WAIT });
      if (!/Could not read/.test(r.info)) {
        await page.fill('#sx', String(c.x), { timeout: WAIT }); await page.fill('#sy', String(c.y), { timeout: WAIT });
        for (const [id, v] of Object.entries(c.set || {})) {
          const el = await page.$('#' + id);
          if (!el) { r.missing.push(id); continue; }
          const tag = await el.evaluate((e) => e.tagName);
          if (tag === 'SELECT') await page.selectOption('#' + id, String(v), { timeout: WAIT });
          else await page.fill('#' + id, String(v), { timeout: WAIT });
        }
        await page.click('#run', { timeout: WAIT });
        await page.waitForFunction(() => { const s = document.getElementById('status').textContent; return s.length > 0 && !/measuring/.test(s); },
          null, { timeout: WAIT });
      }
      r.status = await page.textContent('#status', { timeout: WAIT });
      r.zero = await page.textContent('#zero', { timeout: WAIT });
      r.ades = await page.textContent('#ades', { timeout: WAIT });
      r.tobs = await page.inputValue('#tobs', { timeout: WAIT });
      r.copyDisabled = await page.$eval('#copy', (b) => b.disabled);
      }
    } catch (e) {
      const s = String(e);
      if (/crash/i.test(s)) r.crashed = true; else if (/timeout/i.test(s)) r.timeout = true; else r.error = s.slice(0, 300);
    }
    out.push(r);
    await Promise.race([page.close().catch(() => {}), new Promise((res) => setTimeout(res, 3000))]);
  }
  process.stdout.write(JSON.stringify(out));
  await Promise.race([browser.close(), new Promise((res) => setTimeout(res, 5000))]);
  process.exit(0);
})();
