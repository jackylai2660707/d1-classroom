// Capture actual application screens. The scan example uses an explicitly fake SDK.
const { _electron } = require(process.env.D1_PLAYWRIGHT || 'playwright');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { spawn } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const assets = path.join(root, 'assets');
let app, bridge;
(async () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-capture-'));
  const config = path.join(folder, 'robot.json');
  fs.writeFileSync(config, JSON.stringify({ mac: '02:12:34:56:78:90', bind: '127.0.0.1', port: 18766 }));
  bridge = spawn(process.env.D1_PYTHON || 'python', [path.join(root, 'bridge/bridge.py'), '--config', config, '--fake'], { windowsHide: true });
  await new Promise((resolve, reject) => {
    let output = '';const timeout = setTimeout(() => reject(Error('Fake bridge timeout: ' + output)), 10000);
    bridge.on('error', reject);bridge.stdout.on('data', data => { output += data;if (output.includes('HTTP+UDP')) { clearTimeout(timeout);resolve(); } });
    bridge.stderr.on('data', data => { output += data; });
  });
  const env = { ...process.env }; delete env.ELECTRON_RUN_AS_NODE;
  app = await _electron.launch({ executablePath: require('electron'), args: [root, `--user-data-dir=${path.join(folder, 'profile')}`], cwd: root, env });
  await app.evaluate(({ BrowserWindow, app }) => {
    const window = BrowserWindow.getAllWindows()[0];window.setSize(1440, 1020);
    const require = process.getBuiltinModule('module').createRequire(app.getAppPath() + '/package.json');
    const discovery = require('./app/discovery.cjs'), original = discovery.scan;
    discovery.scan = options => original({ ...options, destinations: [{ local: '127.0.0.1', host: '127.0.0.1' }], port: 18766, timeoutMs: 180 });
  });
  const page = await app.firstWindow();await page.waitForFunction(() => window.d1Test);
  const paint = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  await page.screenshot({ path: path.join(assets, 'workshop-current.png') });
  await page.locator('#scan').click();await page.locator('[data-mac="02:12:34:56:78:90"]').waitFor();
  await page.locator('#devices').evaluate(element=>{element.style.width='560px';element.style.maxWidth='calc(100% - 48px)';});
  await paint();await page.locator('#devices').screenshot({ path: path.join(assets, 'scan-current.png') });
  await page.evaluate(() => { document.getElementById('devices').hidden = true; });
  for (const id of [3, 6, 7, 8, 15, 16]) {
    await page.evaluate(id => window.d1Test.loadLesson(id), id);await paint();
    await page.locator('.blocklyBlockCanvas').first().screenshot({ path: path.join(assets, `blocks-${id}.png`) });
  }
  await page.evaluate(() => window.d1Test.loadLesson(9));await page.locator('[data-mode="split"]').click();await paint();
  await page.locator('#editors').screenshot({ path: path.join(assets, 'split-current.png') });
  await page.evaluate(() => window.d1Test.loadLesson(10));await paint();
  await page.locator('#textwrap').screenshot({ path: path.join(assets, 'python-current.png') });
  await page.locator('aside').screenshot({ path: path.join(assets, 'camera-current.png') });
  await page.locator('#model-input').setInputFiles(path.join(root, 'curriculum/備用色卡模型.zip'));
  await page.waitForFunction(() => document.getElementById('model-state').textContent.includes('已載入'));
  await page.locator('#image-input').setInputFiles(path.join(root, 'curriculum/samples/左轉卡/示例_4.png'));
  await page.waitForFunction(() => document.getElementById('predictions').textContent.includes('%'));await paint();
  await page.locator('aside').screenshot({ path: path.join(assets, 'model-current.png') });
  console.log('Captured current workshop, fake MAC scan, code, blocks and real model inference.');
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => { if (app) await app.close();bridge?.kill(); });
