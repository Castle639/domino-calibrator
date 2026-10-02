// The design bar's browser measurements (the calibrator's eleventh room): node design_check.js cfg.json -> JSON on stdout.
// cfg: {file, x, y, set: {inputId: value}}. For each view (desktop 1280x900, phone 390x844) and scheme (light, dark), a
// fresh context with that viewport and prefers-color-scheme reads the page's computed colours, every control's box and
// name, the element a first Tab focuses and its outline, and the scroll width; then measures (the file, the start, the
// record's values, Measure) and reads the canvas beside the method, the plot beside or above the table, and the plot's
// colours; on the desktop, the theme button is pressed and the plot's colours read again, and the page is reloaded to
// read the theme it keeps. Every wait is bounded; what the page does not have is null, not guessed.
const path = require('path'), fs = require('fs');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const WAIT = 8000;
const VIEWS = { desktop: { width: 1280, height: 900 }, phone: { width: 390, height: 844 } };

function read() {                                       // runs in the page
  const cs = (el) => (el ? getComputedStyle(el) : null);
  const root = cs(document.documentElement), body = cs(document.body);
  const tok = (n) => root.getPropertyValue(n).trim();
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; };
  const controls = Array.from(document.querySelectorAll('input, select, button, textarea')).filter((e) => e.type !== 'hidden')
    .map((e) => ({ id: e.id || e.tagName.toLowerCase(), tag: e.tagName, type: e.type || '', box: box(e),
      shown: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length),
      named: (e.labels && e.labels.length > 0) || !!e.getAttribute('aria-label') || !!e.getAttribute('aria-labelledby') || (e.tagName === 'BUTTON' && e.textContent.trim().length > 0) }));
  const link = document.querySelector('#trust a') || document.querySelector('a');
  const stn = document.getElementById('stn'), run = document.getElementById('run');
  return {
    theme: document.documentElement.getAttribute('data-theme'),
    bg: body.backgroundColor, fg: body.color, muted: cs(document.getElementById('about')).color,
    link: link ? cs(link).color : null,
    run: run ? { color: cs(run).color, bg: cs(run).backgroundColor } : null,
    input: stn ? { border: cs(stn).borderTopColor, bg: cs(stn).backgroundColor, color: cs(stn).color } : null,
    tokens: { accent: tok('--accent'), accent2: tok('--accent2'), fg: tok('--fg'), line: tok('--line'), bg: tok('--bg') },
    fonts: { body: body.fontFamily, pre: cs(document.getElementById('ades')).fontFamily },
    controls, canvas: box(document.getElementById('img')), est: box(document.getElementById('est')),
    scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
  };
}

function plot() {                                       // runs in the page, after a Measure
  const cs = (el) => (el ? getComputedStyle(el) : null);
  const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; };
  const svg = document.getElementById('plot');
  const c = svg.querySelector('circle'), l = svg.querySelector('line'), t = svg.querySelector('text');
  const root = getComputedStyle(document.documentElement), tok = (n) => root.getPropertyValue(n).trim();
  return { circles: svg.querySelectorAll('circle').length, point: c ? cs(c).fill : null, zero: l ? cs(l).stroke : null, text: t ? cs(t).fill : null,
    plot: box(svg), tab: box(document.getElementById('tab')), theme: document.documentElement.getAttribute('data-theme'),
    tokens: { accent: tok('--accent'), fg: tok('--fg'), line: tok('--line'), bg: tok('--bg') }, bg: getComputedStyle(document.body).backgroundColor };
}

async function measure(page, cfg) {
  await page.setInputFiles('#file', cfg.file);
  await page.waitForFunction(() => document.getElementById('info').textContent.length > 0, null, { timeout: WAIT });
  await page.fill('#sx', String(cfg.x)); await page.fill('#sy', String(cfg.y));
  for (const [id, v] of Object.entries(cfg.set || {})) {
    const tag = await page.$eval('#' + id, (e) => e.tagName);
    if (tag === 'SELECT') await page.selectOption('#' + id, String(v)); else { await page.fill('#' + id, String(v)); await page.dispatchEvent('#' + id, 'change'); }
  }
  await page.click('#run', { timeout: WAIT });
  await page.waitForFunction(() => { const s = document.getElementById('status').textContent; return s.length > 0 && !/measuring/.test(s); }, null, { timeout: WAIT * 4 });
}

(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const url = 'file://' + path.resolve(__dirname, 'index.html');
  const browser = await chromium.launch();
  const out = { views: {}, errors: [] };
  for (const [vname, vp] of Object.entries(VIEWS)) {
    for (const scheme of ['light', 'dark']) {
      const key = vname + '_' + scheme, r = { errors: [] };
      const ctx = await browser.newContext({ viewport: vp, colorScheme: scheme });
      const page = await ctx.newPage();
      page.on('pageerror', (e) => r.errors.push(String(e)));
      try {
        await page.goto(url);
        await page.evaluate(() => document.fonts && document.fonts.ready);
        r.before = await page.evaluate(read);
        await page.keyboard.press('Tab');
        r.focus = await page.evaluate(() => { const a = document.activeElement, s = getComputedStyle(a);
          return { id: a.id || a.tagName, outlineStyle: s.outlineStyle, outlineWidth: parseFloat(s.outlineWidth) || 0 }; });
        await measure(page, cfg);
        r.status = await page.textContent('#status');
        r.plot = await page.evaluate(plot);
        if (vname === 'desktop') {
          const t = await page.$('#theme');
          r.hasTheme = !!t;
          if (t) {
            await page.click('#theme', { timeout: WAIT });
            await page.waitForTimeout(50);
            r.afterToggle = await page.evaluate(plot);
            await page.reload();
            r.afterReload = await page.evaluate(read);
          }
        }
      } catch (e) { r.error = String(e).slice(0, 300); }
      out.views[key] = r;
      await ctx.close();
    }
  }
  process.stdout.write(JSON.stringify(out));
  await Promise.race([browser.close(), new Promise((res) => setTimeout(res, 5000))]);
  process.exit(0);
})();
