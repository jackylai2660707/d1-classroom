// Optional: D1_PLAYWRIGHT points to Playwright, D1_PYTHON to Python.
const { _electron } = require(process.env.D1_PLAYWRIGHT || 'playwright');
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const { spawn } = require('node:child_process');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const delivery = path.resolve(root, '../output/D1彩色課程套件');
const packaged = process.argv.includes('--packaged');
const mac = '02:12:34:56:78:90', port = 18765;
let app, bridge;

async function startBridge() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-ui-fake-'));
  const config = path.join(directory, 'robot.json');
  fs.writeFileSync(config, JSON.stringify({ mac, bind: '127.0.0.1', port }));
  bridge = spawn(process.env.D1_PYTHON || 'python', [path.join(root, 'bridge/bridge.py'), '--config', config, '--fake'], { windowsHide: true });
  await new Promise((resolve, reject) => {
    let output = '';
    const timeout = setTimeout(() => reject(Error(output || 'Fake bridge timeout')), 5000);
    bridge.on('error', reject);bridge.stderr.on('data', data => { output += data; });
    bridge.stdout.on('data', data => { output += data;if (output.includes('HTTP+UDP')) { clearTimeout(timeout);resolve(); } });
    bridge.on('exit', code => { if (code) { clearTimeout(timeout);reject(Error(output)); } });
  });
}
async function openApp() {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-fresh-profile-'));
  const env = { ...process.env };delete env.ELECTRON_RUN_AS_NODE;
  app = await _electron.launch({
    executablePath: packaged ? path.join(delivery, '學生工具/D1學生工坊/D1學生工坊.exe') : require('electron'),
    args: [...(packaged ? [] : [root]), `--user-data-dir=${profile}`], cwd: root, env,
  });
  // Only the scan destination changes to loopback in this child process. UDP and HTTP remain real.
  await app.evaluate(({ app }, port) => {
    const require = process.getBuiltinModule('module').createRequire(app.getAppPath() + '/package.json');
    const discovery = require('./app/discovery.cjs');
    const original = discovery.scan;
    discovery.scan = options => original({ ...options, destinations: [{ local: '127.0.0.1', host: '127.0.0.1' }], port, timeoutMs: 150 });
  }, port);
  const page = await app.firstWindow();
  page.on('dialog', dialog => dialog.accept());
  await page.waitForFunction(() => window.d1Test);
  return page;
}
async function connect(page) {
  await page.locator('#scan').click();
  await page.locator(`[data-mac="${mac}"]`).waitFor();
  if(process.argv.includes('--capture')) { const directory=path.join(root,'build/qa');fs.mkdirSync(directory,{recursive:true});await page.screenshot({path:path.join(directory,'mac-scan.png')}); }
  await page.locator(`[data-mac="${mac}"]`).click();
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('已連接'));
  assert((await page.locator('#status').innerText()).includes(mac));
}
(async () => {
  await startBridge();let page = await openApp();
  assert.equal(await page.locator('#configure').count(), 0);
  assert.equal(await page.locator('#robot-id').count(), 0);
  assert(await page.locator('#practice').isChecked());
  await page.locator('#run').click();
  await page.waitForFunction(() => document.getElementById('log').textContent.includes('程序完成'));
  await page.locator('#model-input').setInputFiles(path.join(root, 'curriculum/備用色卡模型.zip'));
  await page.waitForFunction(() => document.getElementById('model-state').textContent.includes('已載入'));
  await page.locator('#image-input').setInputFiles(path.join(root, 'curriculum/samples/左轉卡/示例_4.png'));
  await page.waitForFunction(() => document.getElementById('predictions').textContent.includes('%'));
  await connect(page);
  const occupied = await fetch(`http://127.0.0.1:${port}/connect`, { method: 'POST', body: JSON.stringify({ expected_mac: mac }) });
  assert.equal(occupied.status, 409);
  await page.locator('#practice').uncheck();await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(() => document.getElementById('log').textContent.includes('程序完成') || document.getElementById('log').textContent.includes('程式錯誤'), {}, { timeout: 18000 });
  assert(!(await page.locator('#log').innerText()).includes('程式錯誤'));
  await page.locator('[data-mode=python]').click();await page.locator('#code').fill('dog.stand()\ndog.forward(seconds=3)\ndog.wait(seconds=5)\ndog.stop()');
  await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(() => document.getElementById('log').textContent.includes('實機 forward'));
  assert(await page.locator('#scan').isDisabled());
  bridge.kill();
  await page.waitForFunction(() => document.getElementById('status').textContent.includes('中斷'));
  await page.waitForFunction(() => document.getElementById('notice').textContent.includes('停止未確認'));
  assert(await page.locator('#run').isEnabled());
  await app.close();app=null;
  await startBridge();page=await openApp();
  assert.equal(await page.locator('#status').innerText(), '未連接');
  await connect(page);await page.locator('#disconnect').click();
  await page.waitForFunction(() => document.getElementById('status').textContent === '未連接');
  console.log(`PASS: ${packaged ? 'packaged' : 'development'} practice/model, scan MAC, connect, ownership refusal, fake movement, disconnect cancellation, fresh-profile reconnect. No physical robot.`);
})().catch(error => { console.error(error);process.exitCode=1; }).finally(async () => { await app?.close();bridge?.kill(); });
