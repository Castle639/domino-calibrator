// Headless check of index.html: load a FITS, set the start, Measure, read the answer. node browser_check.js cutout.fits x y [G|M]
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const [fitsPath, x, y, est] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('file://' + path.resolve(__dirname, 'index.html'));
  await page.setInputFiles('#file', fitsPath);
  await page.waitForFunction(() => document.getElementById('info').textContent.length > 0);
  await page.fill('#sx', x); await page.fill('#sy', y);
  await page.selectOption('#est', est || 'G');
  await page.click('#run');
  await page.waitForFunction(() => /done|did not converge|Error/.test(document.getElementById('status').textContent), null, { timeout: 60000 });
  const out = await page.evaluate(() => ({ info: document.getElementById('info').textContent, status: document.getElementById('status').textContent,
    zero: document.getElementById('zero').textContent, ades: document.getElementById('ades').textContent, tobs: document.getElementById('tobs').value,
    circles: document.querySelectorAll('#plot circle').length }));
  await page.screenshot({ path: process.env.SHOT || '/dev/null', fullPage: true });
  console.log(JSON.stringify(Object.assign(out, { errors })));
  await browser.close();
})();
