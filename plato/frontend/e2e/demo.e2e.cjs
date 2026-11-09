const { chromium, devices } = require('playwright');
const fs = require('fs');
/**
 * End-to-end demo check (PLATO §10) against a running stack, using the SIMULATED provider:
 *   API on :8000 with PLATO_ENABLE_MOCK_PROVIDER=true, web on :3000.
 *   WEB_URL=http://localhost:3000 SHOTS_DIR=./e2e/shots npm run e2e
 * Registers a fresh user, creates a project and two agents, runs an objective, verifies live
 * streaming + agent-to-agent handoff + persistence after reload + pause/stop + mobile layout.
 */
const WEB = process.env.WEB_URL || "http://localhost:3000";
const SP = process.env.SHOTS_DIR || "e2e";
const EMAIL = `e2e-${Date.now()}@plato.dev`;
(async () => {
  fs.mkdirSync(`${SP}/shots`, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('response', r => { if (r.status() >= 400) errors.push(r.status() + ' ' + r.url()); });
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(WEB + '/');
  await page.waitForURL('**/login');
  await page.getByText('Multiple Minds. One Intelligence.').waitFor(); await page.waitForLoadState('networkidle');
  await page.screenshot({ path: `${SP}/shots/01-login.png` });
  await page.getByText('New to PLATO? Create an account').click();
  await page.fill('#email', EMAIL);
  await page.fill('#password', 'correct-horse-battery');
  await page.getByRole('button', { name: 'Create account' }).click();
  await page.waitForURL(WEB + '/');
  await page.fill('input[placeholder="New project name"]', 'URL shortener');
  await page.getByRole('button', { name: 'Create project' }).click();
  await page.getByText('URL shortener').click();
  await page.waitForURL('**/projects/*');
  await page.getByText('Live', { exact: true }).waitFor();
  for (const [name, role] of [['Architect', 'Software architect'], ['Developer', 'Lead developer']]) {
    await page.getByRole('button', { name: '+ Add agent' }).click();
    await page.fill('#ag-name', name);
    await page.fill('#ag-role', role);
    await page.selectOption('#ag-prov', 'mock');
    await page.fill('#ag-model', 'sim-slow');
    await page.getByRole('button', { name: 'Add agent', exact: true }).click();
    await page.getByText(role).first().waitFor();
  }
  await page.fill('textarea[aria-label="Objective"]', 'Design a URL shortener service: data model and API.');
  await page.getByRole('button', { name: 'Start run' }).click();
  await page.getByText('● streaming').first().waitFor({ timeout: 10000 });
  await page.screenshot({ path: `${SP}/shots/02-streaming.png` });
  await page.getByText('⟶').first().waitFor({ timeout: 30000 });
  await page.getByText(/Run completed —/).waitFor({ timeout: 60000 });
  await page.screenshot({ path: `${SP}/shots/03-completed.png`, fullPage: false });
  const before = await page.locator('section').filter({ hasText: 'Command room' }).first().innerText();
  await page.reload();
  await page.getByText(/Run completed —/).waitFor({ timeout: 10000 });
  const after = await page.locator('section').filter({ hasText: 'Command room' }).first().innerText();
  const persisted = before.includes('Here is my part') && after.includes('Here is my part');
  console.log('history persisted after refresh:', persisted);
  if (!persisted) throw new Error('history not persisted');
  await page.getByRole('tab', { name: 'Hierarchy' }).click();
  await page.screenshot({ path: `${SP}/shots/04-hierarchy.png` });
  await page.getByRole('tab', { name: 'Tasks' }).click();
  await page.screenshot({ path: `${SP}/shots/05-tasks.png` });
  // Second run: stop it from the UI mid-stream.
  await page.getByRole('tab', { name: 'Command room' }).click();
  await page.fill('textarea[aria-label="Objective"]', 'Second objective: plan a launch.');
  await page.getByRole('button', { name: 'Start run' }).click();
  await page.getByText('● streaming').first().waitFor({ timeout: 10000 });
  await page.getByRole('button', { name: 'Pause' }).click();
  await page.getByRole('button', { name: 'Resume' }).waitFor();
  await page.getByRole('button', { name: 'Stop' }).click();
  await page.getByText(/Run stopped —/).waitFor({ timeout: 15000 });
  console.log('stop via UI: ok');
  await page.goto(WEB + '/billing');
  await page.getByText('Usage by model this month').waitFor();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SP}/shots/06-billing.png`, fullPage: true });
  await page.goto(WEB + '/providers');
  await page.getByText('Anthropic Claude').waitFor();
  await page.screenshot({ path: `${SP}/shots/07-providers.png` });
  const m = await browser.newPage({ ...devices['iPhone 13'] });
  await m.addInitScript(t => localStorage.setItem('plato.token', t), await page.evaluate(() => localStorage.getItem('plato.token')));
  await m.goto(page.url().replace('/providers', '/'));
  await m.getByText('URL shortener').click();
  await m.getByText(/Run stopped —/).first().waitFor({ timeout: 10000 }).catch(() => {});
  await m.screenshot({ path: `${SP}/shots/08-mobile.png` });
  const overflow = await m.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  console.log('mobile horizontal overflow:', overflow);
  if (overflow) throw new Error('horizontal overflow on mobile');
  console.log('page errors:', JSON.stringify(errors));
  if (errors.length) throw new Error('page errors');
  await browser.close();
  console.log('E2E PASSED');
})().catch(e => { console.error('E2E FAILED', e); process.exit(1); });
