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
  try {
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('已連接'));
  } catch (error) {
    console.error('Fake connection UI:', await page.locator('#notice').innerText(), await page.locator('#log').innerText());
    throw error;
  }
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
  // New high-level Python API runs only against practice values or the local fake bridge.
  await assert.rejects(page.evaluate(()=>window.d1Test.readVision('vision_label',{})), /即時相機/);
  assert.equal(await page.locator('#api-list [data-risk=extreme]').count(), 0);
  await page.locator('#action-guide').evaluate(e=>e.open=true);
  await page.locator('#extreme-actions').evaluate(e=>e.open=true);
  await page.locator('#show-backflip').check();
  assert.equal(await page.locator('#api-list [data-risk=extreme]').count(), 1);
  assert(await page.locator('#allow-backflip').isDisabled());
  await page.locator('#allow-high-risk').check();await page.locator('#allow-backflip').check();
  await page.locator('#show-backflip').uncheck();assert(!(await page.locator('#allow-backflip').isChecked()));
  await page.locator('[data-mode=python]').click();
  await page.locator('#code').fill('dog.greet()\ndog.passive()\ndog.side_left(seconds=0.1)\ndog.side_right(seconds=0.1)\ndog.move(vx=0.1, seconds=0.1)\ndog.attitude(pitch=0.05)\ndog.jump()\ndog.front_jump()\ndog.backflip()\ndog.two_leg_stand(seconds=0.1)\ndog.cancel_two_leg_stand()\n'+require('../app/robot-api.js').sensors.map(s=>`print(dog.${s.id}())`).join('\n'));
  await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(()=>/程序完成|程式錯誤/.test(document.getElementById('log').textContent),{},{timeout:18000});
  assert(!(await page.locator('#log').innerText()).includes('程式錯誤'));
  assert((await page.locator('#log').innerText()).includes('練習感測數值'));
  assert(!(await page.locator('#allow-high-risk').isChecked()));
  const picture=fs.readFileSync(path.join(root,'curriculum/samples/左轉卡/示例_4.png')).toString('base64');
  await page.evaluate(async data=>{
    const canvas=document.createElement('canvas');canvas.width=224;canvas.height=224;const ctx=canvas.getContext('2d');const image=new Image();image.src='data:image/png;base64,'+data;await image.decode();
    window.__featureFrameTimer=setInterval(()=>ctx.drawImage(image,0,0,224,224),100);ctx.drawImage(image,0,0,224,224);
    const stream=canvas.captureStream(10);navigator.mediaDevices.getUserMedia=async()=>stream;
  },picture);
  await page.locator('#pc-camera').click();
  await page.waitForFunction(()=>{try{return window.d1Test.readVision('vision_label',{})==='左轉卡'}catch{return false}});
  assert(await page.evaluate(()=>window.d1Test.readVision('vision_seen',{label:'左轉卡'})));
  assert((await page.evaluate(()=>window.d1Test.readVision('vision_score',{label:'左轉卡'})))>=.8);
  await page.locator('#code').fill('print(vision.wait_for("左轉卡", timeout=5))\nfor count in range(3):\n    print(vision.label())\n    dog.wait(seconds=0.2)');
  await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(()=>/程序完成|程式錯誤/.test(document.getElementById('log').textContent),{},{timeout:12000});
  const continuousLog=await page.locator('#log').innerText();assert(!continuousLog.includes('程式錯誤'));assert(continuousLog.includes('True'));assert((continuousLog.match(/左轉卡/g)||[]).length>=3);
  await page.locator('#camera-off').click();await page.evaluate(()=>clearInterval(window.__featureFrameTimer));
  await page.evaluate(()=>window.d1Test.loadLesson(3));
  await page.locator('#action-guide').evaluate(e=>e.open=false);
  await connect(page);
  const occupied = await fetch(`http://127.0.0.1:${port}/connect`, { method: 'POST', body: JSON.stringify({ expected_mac: mac }) });
  assert.equal(occupied.status, 409);
  await page.locator('#practice').uncheck();await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(() => document.getElementById('log').textContent.includes('程序完成') || document.getElementById('log').textContent.includes('程式錯誤'), {}, { timeout: 18000 });
  assert(!(await page.locator('#log').innerText()).includes('程式錯誤'));
  await page.locator('[data-mode=python]').click();await page.locator('#code').fill('dog.stand()\ndog.jump()');
  await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(()=>document.getElementById('log').textContent.includes('程式錯誤'));
  assert((await page.locator('#log').innerText()).includes('高風險'));
  await page.locator('#action-guide').evaluate(e=>e.open=true);await page.locator('#allow-high-risk').check();
  await page.locator('#code').fill('dog.stand()\ndog.two_leg_stand(seconds=0.1)\ndog.lie()');
  await page.locator('#clear').click();await page.locator('#run').click();
  await page.waitForFunction(()=>/程序完成|程式錯誤/.test(document.getElementById('log').textContent),{},{timeout:15000});
  assert(!(await page.locator('#log').innerText()).includes('程式錯誤'));
  assert(!(await page.locator('#allow-high-risk').isChecked()));
  await page.locator('#action-guide').evaluate(e=>e.open=false);
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
