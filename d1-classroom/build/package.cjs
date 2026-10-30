const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const asar = require('@electron/asar');
const root = path.resolve(__dirname, '..');
const dest = path.resolve(root, '../output/D1彩色課程套件/學生工具/D1學生工坊');
(async () => {
  fs.mkdirSync(dest, { recursive: true });
  const dist = path.dirname(require('electron'));
  fs.cpSync(dist, dest, { recursive: true, filter: source => path.basename(source) !== 'electron.exe' });
  fs.copyFileSync(path.join(dist, 'electron.exe'), path.join(dest, 'D1學生工坊.exe'));
  const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'd1-package-'));
  try {
    fs.cpSync(path.join(root, 'app'), path.join(stage, 'app'), { recursive: true });
    const { version } = require('../package.json');
    fs.writeFileSync(path.join(stage, 'package.json'), JSON.stringify({ name: 'd1-classroom', version, main: 'app/main.cjs' }));
    await asar.createPackage(stage, path.join(dest, 'resources/app.asar'));
  } finally {
    const verified = fs.realpathSync(stage);
    if (path.dirname(verified) !== fs.realpathSync(os.tmpdir()) || !path.basename(verified).startsWith('d1-package-')) throw Error('Unexpected staging path');
    fs.rmSync(verified, { recursive: true, force: true });
  }
  fs.copyFileSync(require('ffmpeg-static'), path.join(dest, 'resources/ffmpeg.exe'));
  let notices = 'D1 學生工坊第三方軟體授權\nBlockly Apache-2.0; TensorFlow.js Apache-2.0; JSZip MIT/GPL dual (MIT selected); Skulpt MIT; Electron MIT; FFmpeg see accompanying license.\n\n';
  for (const dependency of ['blockly', '@tensorflow/tfjs', 'jszip', 'skulpt', 'ffmpeg-static']) {
    const dir = path.join(root, 'node_modules', dependency);
    for (const name of fs.readdirSync(dir).filter(name => /licen[cs]e|copying/i.test(name))) {
      if (fs.statSync(path.join(dir, name)).isFile()) notices += `\n${dependency}/${name}\n${fs.readFileSync(path.join(dir, name), 'utf8')}\n`;
    }
  }
  for (const name of ['ffmpeg.exe.LICENSE', 'ffmpeg.exe.README']) fs.copyFileSync(path.join(root, 'node_modules/ffmpeg-static', name), path.join(dest, name));
  fs.writeFileSync(path.join(dest, 'THIRD-PARTY-NOTICES.txt'), notices);
  console.log('Packaged', dest);
})().catch(error => { console.error(error); process.exitCode = 1; });
