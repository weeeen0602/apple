// Render poster.html to 專題海報.png using Playwright
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1200, height: 1800 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  const htmlPath = path.resolve(__dirname, 'poster.html');
  await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const outPath = path.resolve(__dirname, 'assets', '專題海報.png');
  await page.screenshot({ path: outPath, fullPage: true, type: 'png' });

  await browser.close();
  console.log(`OK: ${outPath}`);
})();