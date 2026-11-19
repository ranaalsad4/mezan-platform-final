const { chromium } = require('playwright');
const steps = ["1 · Factory", "2 · Incomplete data", "3 · Estimates & warnings", "4 · Baseline & options",
  "5 · Ranking vs Mezan", "6 · Probabilities", "7 · Value of information", "8 · Recommendation"];
(async () => {
  const out = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1500, height: 2600 }, deviceScaleFactor: 1.25 });
  await p.goto(process.argv[3] || 'http://localhost:8501', { waitUntil: 'networkidle' });
  await p.waitForSelector('text=Guided demo', { timeout: 180000 });
  await p.waitForTimeout(6000);
  const col = p.locator('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]').first();
  if (await col.count()) { await p.locator('[data-testid="stSidebar"]').hover(); await col.click().catch(() => {}); await p.waitForTimeout(1500); }
  for (let i = 0; i < steps.length; i++) {
    await p.getByText(steps[i], { exact: true }).first().click();
    await p.waitForTimeout(3500);
    // crop to the content of the main column (from the tab bar to the last element)
    const box = await p.evaluate((label) => {
      const m = document.querySelector('[data-testid="stMainBlockContainer"]') || document.querySelector('.block-container');
      const r = m.getBoundingClientRect();
      const kids = [...m.querySelectorAll('[data-testid="stElementContainer"], [data-testid="element-container"]')].filter(e => e.offsetParent !== null);
      const bottom = Math.max(...kids.map(k => k.getBoundingClientRect().bottom));
      const h = [...document.querySelectorAll('h3')].find(x => x.textContent.trim().startsWith(label));
      const top = h ? h.getBoundingClientRect().top - 12 : r.top;
      return { x: r.left, y: top, width: r.width, height: bottom - top + 20 };
    }, steps[i]);
    await p.screenshot({ path: `${out}/demo_step${i + 1}.png`, clip: box });
  }
  await b.close();
})();
