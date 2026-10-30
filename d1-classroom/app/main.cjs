const {app,BrowserWindow,ipcMain,dialog,shell}=require('electron');
const fs=require('fs'),path=require('path'),{spawn}=require('child_process');
const {validate}=require('./policy.cjs');
let win,session=null,camera=null,heartbeat=null;
const discovery=require('./discovery.cjs');
let scanner=null,candidates=new Map(),connecting=false,executing=false,connectionGeneration=0;
async function request(route,data,robot=session?.robot){
 if(!robot)throw Error('請先連接本組機器狗');
 const res=await fetch(`http://${robot.host}:${robot.port}${route}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),redirect:'error',signal:AbortSignal.timeout(2500)});
 const body=await res.json();if(!res.ok)throw Error(body.error||'設備拒絕指令');return body;
}
function cameraStop(){if(camera){camera.kill();camera=null;}}
async function disconnect(){connectionGeneration++;clearInterval(heartbeat);heartbeat=null;cameraStop();executing=false;let s=session;session=null;if(s)try{await request('/release',{lease:s.lease},s.robot);}catch{} }
function startHeartbeat(){
 heartbeat=setInterval(async()=>{
  const s=session;if(!s||s.inflight)return;s.inflight=true;
  try{const b=await request('/heartbeat',{lease:s.lease},s.robot);if(session===s)win?.webContents.send('status',b);}
  catch(e){if(session===s){session=null;executing=false;clearInterval(heartbeat);cameraStop();win?.webContents.send('lost',e.message);}}
  finally{s.inflight=false;}
 },350);
}
ipcMain.handle('scan',async()=>{
 if(executing||connecting)throw Error('請先停止程序，等待連線完成後再掃描');
 if(scanner)throw Error('正在掃描，請稍候');
 const active=new AbortController();scanner=active;candidates.clear();
 try{
  const robots=await discovery.scan({signal:active.signal});
  if(active.signal.aborted)return {robots:[],cancelled:true};
  for(const robot of robots)candidates.set(robot.mac,{...robot,scannedAt:Date.now()});
  return {robots:robots.map(({mac,state})=>({mac,state})),cancelled:false};
 }finally{if(scanner===active)scanner=null;}
});
ipcMain.handle('scan-cancel',()=>{scanner?.abort();});
ipcMain.handle('connect',async(_,mac)=>{
 if(connecting||executing||scanner)throw Error('請先停止並等待目前操作完成');
 if(session)throw Error('請先斷開目前的機器狗');
 const robot=candidates.get(discovery.normalizeMac(mac));
 if(!robot||Date.now()-robot.scannedAt>60000)throw Error('請重新掃描，再選擇機器狗');
 if(robot.state!=='available')throw Error(robot.state==='busy'?'此機器狗使用中，請重新掃描':'設備準備中或 MAC 衝突，請通知老師');
 connecting=true;const generation=++connectionGeneration;
 try{
  const info=await request('/connect',{expected_mac:robot.mac},robot);
  if(info.mac!==robot.mac||typeof info.lease!=='string'||info.lease.length<32||generation!==connectionGeneration){
   if(typeof info.lease==='string')try{await request('/release',{lease:info.lease},robot);}catch{}
   throw Error('機身 MAC 不一致或連線已取消，請重新掃描');
  }
  session={robot,lease:info.lease};startHeartbeat();return info;
 }finally{connecting=false;}
});
ipcMain.handle('disconnect',()=>disconnect());
async function control(route,data={}){
 const s=session;if(!s)throw Error('請先連接本組機器狗');
 const result=await request(route,{...data,lease:s.lease},s.robot);
 if(session!==s)throw Error('連線已中斷，請重新掃描');
 return result;
}
ipcMain.handle('begin',async()=>{const result=await control('/begin');executing=true;return result;});
ipcMain.handle('command',(_,a,args)=>control('/command',validate(a,args)));
ipcMain.handle('stop',async()=>{try{return await control('/stop');}finally{executing=false;}});
ipcMain.handle('end',async()=>{try{return await control('/end');}finally{executing=false;}});
ipcMain.handle('save',async(_,data)=>{if(typeof data!=='string'||data.length>2e6)throw Error('專案過大');let r=await dialog.showSaveDialog(win,{defaultPath:'我的D1作品.d1.json',filters:[{name:'D1 專案',extensions:['json']}]});if(!r.canceled){fs.writeFileSync(r.filePath,data,'utf8');return r.filePath;}});
ipcMain.handle('open',async()=>{let r=await dialog.showOpenDialog(win,{filters:[{name:'D1 專案',extensions:['json']}],properties:['openFile']});if(!r.canceled){if(fs.statSync(r.filePaths[0]).size>2e6)throw Error('專案過大');return fs.readFileSync(r.filePaths[0],'utf8');}});
ipcMain.handle('picture',async(_,data)=>{if(!/^data:image\/png;base64,/.test(data)||data.length>12e6)throw Error('圖片格式錯誤');let r=await dialog.showSaveDialog(win,{defaultPath:'D1圖片.png',filters:[{name:'PNG',extensions:['png']}]});if(!r.canceled){fs.writeFileSync(r.filePath,Buffer.from(data.split(',')[1],'base64'));return r.filePath;}});
ipcMain.handle('camera',async()=>{if(!session)throw Error('請先連接機器狗');cameraStop();const exe=app.isPackaged?path.join(process.resourcesPath,'ffmpeg.exe'):require('ffmpeg-static');let p=spawn(exe,['-loglevel','error','-rtsp_transport','tcp','-i',`rtsp://${session.robot.host}:8554/test`,'-vf','fps=5,scale=640:-1','-f','image2pipe','-vcodec','mjpeg','-'],{windowsHide:true});camera=p;let buf=Buffer.alloc(0);p.stdout.on('data',chunk=>{buf=Buffer.concat([buf,chunk]);let end;while((end=buf.indexOf(Buffer.from([255,217])))>=0){const frame=buf.subarray(0,end+2);buf=buf.subarray(end+2);if(frame[0]===255&&frame[1]===216)win?.webContents.send('frame',frame.toString('base64'));}if(buf.length>4e6)buf=Buffer.alloc(0);});p.on('error',e=>win?.webContents.send('camera-error',e.message));p.on('exit',()=>{if(camera===p){camera=null;win?.webContents.send('camera-error','機器狗相機已中斷，請檢查連接');}});return true;});
ipcMain.handle('camera-stop',()=>cameraStop());
ipcMain.handle('tutorial',async(_,lesson)=>{
 if(!Number.isInteger(lesson)||lesson<1||lesson>16)throw Error('課次無效');
 const delivery=app.isPackaged?path.resolve(path.dirname(process.execPath),'../..'):path.resolve(__dirname,'../../output/D1彩色課程套件');
 const target=path.join(delivery,'教程',`lesson-${String(lesson).padStart(2,'0')}.html`);
 if(!fs.existsSync(target))throw Error('找不到教程，請將學生工具與教程保留在完整套件內');
 const error=await shell.openPath(target);if(error)throw Error('無法開啟教程：'+error);return true;
});
app.whenReady().then(()=>{win=new BrowserWindow({width:1360,height:900,minWidth:1100,minHeight:760,title:'D1 學生工坊',backgroundColor:'#f6f8fb',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});win.loadFile(path.join(__dirname,'index.html'));win.on('closed',()=>{scanner?.abort();win=null;});});
app.on('window-all-closed',()=>app.quit());

let quitting=false;
app.on('before-quit',event=>{if(quitting)return;if(session||connecting){event.preventDefault();quitting=true;disconnect().finally(()=>app.quit());}});
