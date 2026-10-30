// Optional integration check: provide Playwright via module resolution or D1_PLAYWRIGHT.
const path = require('node:path');
const os = require('node:os');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { _electron } = require(process.env.D1_PLAYWRIGHT || 'playwright');

(async () => {
  const root = path.resolve(__dirname, '../../output/D1彩色課程套件');
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-packaged-test-'));
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const app = await _electron.launch({
    executablePath: path.join(root, '學生工具/D1學生工坊/D1學生工坊.exe'),
    args: [`--user-data-dir=${profile}`], cwd: root, env, timeout: 30000,
  });
  try {
    const page = await app.firstWindow();
    await page.waitForFunction(() => window.d1Test);
    assert(await page.locator('#practice').isChecked());
    for(const id of [...Array.from({length:14},(_,i)=>i+1),16]){
      await page.evaluate(id => window.d1Test.loadLesson(id),id);
      await page.locator('#clear').click();await page.locator('#run').click();
      await page.waitForFunction(() => /程序完成|程式錯誤/.test(document.getElementById('log').textContent), {}, { timeout: 15000 });
      assert(!(await page.locator('#log').innerText()).includes('程式錯誤'),'Lesson '+id+' practice failed');
    }
    await page.locator('#model-input').setInputFiles(path.join(root, '配套檔案/備用色卡模型.zip'));
    await page.waitForFunction(() => document.getElementById('model-state').textContent.includes('已載入'));
    await page.locator('#image-input').setInputFiles(path.join(root, '配套檔案/色卡示例圖片/左轉卡/示例_4.png'));
    await page.waitForFunction(() => document.getElementById('predictions').textContent.includes('%'));
    // A generated video stream exercises frame confirmation without accessing a physical camera.
    const leftImage=fs.readFileSync(path.join(root,'配套檔案/色卡示例圖片/左轉卡/示例_4.png')).toString('base64');
    await page.evaluate(async data=>{
      const canvas=document.createElement('canvas');canvas.width=224;canvas.height=224;
      const ctx=canvas.getContext('2d');let picture;
      window.__setTestFrame=async data=>{const image=new Image();image.src='data:image/png;base64,'+data;await image.decode();picture=image;ctx.drawImage(picture,0,0,224,224);};
      await window.__setTestFrame(data);
      window.__frameTimer=setInterval(()=>ctx.drawImage(picture,0,0,224,224),100);
      const stream=canvas.captureStream(10);
      navigator.mediaDevices.getUserMedia=async()=>stream;
    },leftImage);
    await page.locator('#pc-camera').click();
    await page.waitForFunction(()=>document.getElementById('camera-state').textContent.includes('電腦相機'));
    await page.evaluate(()=>window.d1Test.loadLesson(15));await page.locator('#clear').click();await page.locator('#run').click();
    await page.waitForFunction(()=>/程序完成|程式錯誤/.test(document.getElementById('log').textContent),{},{timeout:12000});
    let log=await page.locator('#log').innerText();assert(!log.includes('程式錯誤'));assert(log.includes('確認識別'));assert(log.includes('練習 left'));
    const otherImage=fs.readFileSync(path.join(root,'配套檔案/色卡示例圖片/其他/示例_4.png')).toString('base64');
    await page.evaluate(data=>window.__setTestFrame(data),otherImage);
    await page.waitForFunction(()=>parseFloat(document.querySelector('#predictions>div strong').textContent)<80);
    await page.locator('#clear').click();await page.locator('#run').click();
    await page.waitForFunction(()=>/程序完成|程式錯誤/.test(document.getElementById('log').textContent),{},{timeout:12000});
    log=await page.locator('#log').innerText();assert(log.includes('識別等待超時'));assert(!log.includes('練習 left'));assert(!log.includes('程式錯誤'));
    await page.locator('#camera-off').click();await page.evaluate(()=>clearInterval(window.__frameTimer));
    const qa=path.resolve(__dirname,'../build/qa/courseware');fs.mkdirSync(qa,{recursive:true});
    fs.writeFileSync(path.join(qa,'app-report.json'),JSON.stringify({version:'2.0.0',practiceLessons:[...Array.from({length:14},(_,i)=>i+1),16],visionLesson15:['synthetic live confirmation','timeout without turn'],modelImport:true,imageInference:true,physicalRobot:false,physicalCamera:false},null,2));
    console.log('PASS: all 16 packaged lesson programs, model import, classification, synthetic live confirmation and timeout. No physical robot or camera.');
  } finally {
    await app.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
