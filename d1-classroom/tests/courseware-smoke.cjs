// Offline release verification: real file URLs, lesson interaction and record round-trip.
const { chromium, _electron } = require(process.env.D1_PLAYWRIGHT || 'playwright');
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const { pathToFileURL, fileURLToPath } = require('node:url');
const root = path.resolve(__dirname, '..');
const delivery = path.resolve(root, '../output/D1彩色課程套件');
const qa = path.join(root, 'build/qa/courseware'); fs.mkdirSync(qa, { recursive: true });
const lessons = JSON.parse(fs.readFileSync(path.join(root, 'curriculum/lessons.json'), 'utf8'));
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true });
  const page = await context.newPage();
  const errors = [], network = [], broken = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
  page.on('dialog', dialog => dialog.accept());
  let pages = 0, stages = 0;
  try {
    const files = [path.join(delivery, '使用說明.html'), ...fs.readdirSync(path.join(delivery, '教程')).filter(n => n.endsWith('.html')).map(n => path.join(delivery, '教程', n))];
    for (const file of files) {
      await page.goto(pathToFileURL(file).href);
      await page.locator('h1').waitFor();
      assert.equal(await page.locator('h1').count(), 1);
      await page.evaluate(async () => { await Promise.all([...document.images].filter(img=>img.hasAttribute('src')).map(img => img.decode())); });
      const localLinks = await page.locator('a[href],img[src],script[src],link[href]').evaluateAll(nodes => nodes.map(node => node.href || node.src).filter(url => url?.startsWith('file:')));
      for (const href of localLinks) {
        const url = new URL(href);url.hash = '';url.search = '';
        if (!fs.existsSync(fileURLToPath(url))) broken.push({ file: path.relative(delivery, file), href });
      }
      const lesson = Number(await page.locator('body').getAttribute('data-lesson'));
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({ width, height: 1050 });
        const count = lesson ? 4 : 1;
        for (let stage = 0; stage < count; stage++) {
          if (lesson) await page.locator(`[data-stage="${stage}"]`).click();
          assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${path.basename(file)} width ${width} stage ${stage} overflow`);
          if (lesson) assert(await page.locator(`[data-panel="${stage}"]`).isVisible());
          stages++;
        }
      }
      if (lesson) {
        const source = lessons[lesson-1];
        assert.equal(await page.locator('h1').innerText(), source.title);
        assert.equal(await page.locator('.steps > li').count(), source.steps.length);
        assert.equal(await page.locator('.record-table tbody tr').count(), lesson === 13 ? 15 : source.rows.length);
        assert(!/D1-001|短 ID|robots\.json|課室設定/.test(await page.locator('main').innerText()));
      }
      pages++;
    }
    assert.deepEqual(broken, [], 'Broken local links');
    assert.deepEqual(network, [], 'Offline pages made network requests');
    await page.setViewportSize({ width: 1440, height: 1050 });
    await page.goto(pathToFileURL(path.join(delivery, '使用說明.html')).href);
    await page.screenshot({ path: path.join(qa, 'home.png'), fullPage: true });
    await page.goto(pathToFileURL(path.join(delivery, '教程/lesson-03.html')).href);
    await page.screenshot({ path: path.join(qa, 'lesson-03.png'), fullPage: true });
    await page.locator('[data-stage="1"]').click();
    const projectEvent=page.waitForEvent('download');await page.getByRole('button',{name:'下載本課起步專案',exact:true}).click();
    const projectDownload=await projectEvent;const projectFile=path.join(qa,'downloaded-project.json');await projectDownload.saveAs(projectFile);
    const projectData=JSON.parse(fs.readFileSync(projectFile,'utf8'));assert.equal(projectData.lesson,3);assert.deepEqual(projectData.blocks,lessons[2].blocks);
    await page.locator('[data-stage="0"]').click();
    await page.locator('.image-zoom').click();assert(await page.locator('dialog').isVisible());await page.keyboard.press('Escape');
    await page.locator('#projection').click();assert(await page.locator('body').evaluate(e => e.classList.contains('projection')));await page.locator('#projection').click();
    await page.locator('[data-stage="2"]').click();
    await page.locator('#prediction').fill('只改等待；預測多等 1 秒。');
    await page.locator('[data-field="record-0-1"]').fill('先站立');
    await page.locator('[data-stage="3"]').click();await page.locator('[data-field="check-0"]').check();
    const downloadEvent = page.waitForEvent('download');await page.locator('#export-record').click();
    const download = await downloadEvent;const record = path.join(qa, 'roundtrip.json');await download.saveAs(record);
    const data = JSON.parse(fs.readFileSync(record, 'utf8'));assert.equal(data.lesson, 3);assert.equal(data.fields.prediction, '只改等待；預測多等 1 秒。');
    await page.reload();await page.locator('[data-stage="3"]').click();await page.locator('#import-record').setInputFiles(record);
    await page.waitForFunction(() => document.querySelector('[data-field="check-0"]').checked);
    assert.equal(await page.locator('#prediction').inputValue(), data.fields.prediction);
    const invalid = Buffer.from(JSON.stringify({ ...data, lesson: 2 }));
    await page.locator('#import-record').setInputFiles({ name: 'wrong-lesson.json', mimeType: 'application/json', buffer: invalid });
    await page.waitForFunction(() => document.querySelector('.toast').textContent.includes('本課'));
    assert.equal(await page.locator('#prediction').inputValue(), data.fields.prediction);
    const unsafe = { ...data, fields: { ...data.fields, prediction: '<img src=x onerror=alert(1)>' } };
    await page.locator('#import-record').setInputFiles({ name: 'text.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(unsafe)) });
    await page.waitForFunction(() => document.getElementById('prediction').value.startsWith('<img'));
    assert.equal(await page.locator('img[src="x"]').count(), 0);
    await page.locator('#export-record').click();
    await page.goto(pathToFileURL(path.join(delivery, '教程/lesson-13.html')).href);await page.locator('[data-stage="2"]').click();
    await page.screenshot({ path: path.join(qa, 'lesson-13-record.png'), fullPage: true });
    await page.goto(pathToFileURL(path.join(delivery, '教程/start.html')).href);await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(qa, 'student-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    const report = { date: new Date().toISOString().slice(0,10), pages, viewportStageChecks: stages, localLinks: 'pass', offline: 'zero network requests', recordRoundTrip: 'pass', invalidRecord: 'rejected without changing data', imageZoom: 'pass', projection: 'pass', physicalRobot: false, errors };
    fs.writeFileSync(path.join(qa, 'report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally { await browser.close(); }
  if (process.argv.includes('--packaged')) {
    const env = { ...process.env };delete env.ELECTRON_RUN_AS_NODE;
    const app = await _electron.launch({ executablePath: path.join(delivery, '學生工具/D1學生工坊/D1學生工坊.exe'), args: ['--user-data-dir=' + path.join(require('node:os').tmpdir(), 'd1-tutorial-' + Date.now())], env });
    try {
      const page = await app.firstWindow();await page.waitForFunction(() => window.d1Test);
      await app.evaluate(({ shell }) => { globalThis.__openedTutorial = null; shell.openPath = async target => { globalThis.__openedTutorial = target;return ''; }; });
      await page.selectOption('#lesson', '13');await page.locator('#tutorial').click();
      await page.waitForFunction(() => !document.getElementById('notice').textContent.includes('找不到教程'));
      const opened = await app.evaluate(() => globalThis.__openedTutorial);
      assert.equal(opened, path.join(delivery, '教程/lesson-13.html'));
      assert(fs.existsSync(opened));
      await assert.rejects(() => page.evaluate(() => window.desktop.tutorial(17)));
      console.log('PASS: packaged tutorial button resolves selected lesson; invalid lesson rejected.');
    } finally { await app.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
