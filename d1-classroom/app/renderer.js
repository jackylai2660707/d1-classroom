import * as Blockly from 'blockly';
import 'blockly/blocks';
import * as zh from 'blockly/msg/zh-hant';
import {pythonGenerator,Order} from 'blockly/python';
import * as tf from '@tensorflow/tfjs';
import JSZip from 'jszip';
import {inputForModel,cropForModel} from './tm-preprocess.js';
import {Confirmations} from './vision-core.cjs';
import {validate} from './policy.cjs';
import lessons from '../curriculum/lessons.json';
Blockly.setLocale(zh);
const $=id=>document.getElementById(id), api=window.desktop;
let mode='blocks',generated='',edited=false,running=false,worker=null,deadline=null,connected=false,stream=null,cameraKind=null,frameSeq=0,lastFrameAt=0,lastVideoTime=-1,cameraEpoch=0,inferenceBusy=false,model=null,metadata=null,classes=[],vision=new Confirmations(),runGeneration=0;
let scanning=false,connectingRobot=false,connectedMac='',robots=[];
const canvas=$('camera'),ctx=canvas.getContext('2d');
function drawSource(source,width,height){if(!width||!height)return;canvas.width=width;canvas.height=height;ctx.drawImage(source,0,0,width,height);}
function log(t){$('log').textContent=($('log').textContent+`[${new Date().toLocaleTimeString('zh-TW',{hour12:false})}] ${String(t).slice(0,3000)}\n`).slice(-30000);$('log').scrollTop=$('log').scrollHeight;}
function notice(t){$('notice').textContent=t;}
function guard(fn){return async(...args)=>{try{await fn(...args);}catch(e){log(e.message);notice(e.message);}};}
function number(n){return {block:{type:'math_number',fields:{NUM:n}}};}
function value(block,name){return pythonGenerator.valueToCode(block,name,Order.NONE)||'0';}
for(const [type,text,method,color] of [['stand','站立','stand',210],['lie','趴下','lie',210],['stop','停止','stop',0]]){
 Blockly.Blocks['dog_'+type]={init(){this.appendDummyInput().appendField(text);this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(color);}};
 pythonGenerator.forBlock['dog_'+type]=()=>`dog.${method}()\n`;
}
for(const [type,text,method,arg,color] of [['forward','前進','forward','seconds',210],['back','後退','back','seconds',210],['left','左轉','turn_left','degrees',210],['right','右轉','turn_right','degrees',210],['wait','等待','wait','seconds',30]]){
 Blockly.Blocks['dog_'+type]={init(){this.appendValueInput('N').setCheck('Number').appendField(text);this.appendDummyInput().appendField(arg==='degrees'?'度':'秒');this.setInputsInline(true);this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(color);}};
 pythonGenerator.forBlock['dog_'+type]=b=>`dog.${method}(${arg}=${value(b,'N')})\n`;
}
Blockly.Blocks.dog_battery={init(){this.appendDummyInput().appendField('電量百分比');this.setOutput(true,'Number');this.setColour(210);}};pythonGenerator.forBlock.dog_battery=()=>['dog.battery()',Order.FUNCTION_CALL];
class ModelLabel extends Blockly.FieldDropdown {
 constructor(){super(function(){const selected=this.pendingLabel||this.getValue()||'左轉卡';if(!classes.length)return [[selected+'（先匯入模型）',selected]];const options=classes.map(c=>[c,c]);if(!classes.includes(selected))options.push(['模型缺少：'+selected,selected]);return options;});}
 refresh(){this.getOptions(false);this.doValueUpdate_(this.getValue());this.forceRerender();}
 loadState(state){this.pendingLabel=typeof state==='string'?state:null;this.getOptions(false);super.loadState(state);this.pendingLabel=null;this.refresh();}
}
Blockly.Blocks.vision_wait={init(){this.appendDummyInput().appendField('等待識別').appendField(new ModelLabel(),'LABEL');this.appendValueInput('T').setCheck('Number').appendField('最多');this.appendDummyInput().appendField('秒');this.setOutput(true,'Boolean');this.setColour(145);this.setInputsInline(true);}};pythonGenerator.forBlock.vision_wait=b=>[`vision.wait_for(${JSON.stringify(b.getFieldValue('LABEL'))}, timeout=${value(b,'T')})`,Order.FUNCTION_CALL];
const toolbox={kind:'categoryToolbox',contents:[
{kind:'category',name:'機器狗動作',colour:'#276bc0',contents:['stand','forward','back','left','right','stop','lie','wait'].map(t=>({kind:'block',type:'dog_'+t,inputs:['stand','stop','lie'].includes(t)?undefined:{N:number(['left','right'].includes(t)?30:1)}})).concat([{kind:'block',type:'dog_battery'}])},
{kind:'category',name:'邏輯判斷',colour:'#7145ad',contents:[{kind:'block',type:'controls_if'},{kind:'block',type:'logic_compare'},{kind:'block',type:'logic_boolean'}]},
{kind:'category',name:'重複',colour:'#7145ad',contents:[{kind:'block',type:'controls_repeat_ext',inputs:{TIMES:number(2)}}]},
{kind:'category',name:'數學',colour:'#7145ad',contents:[{kind:'block',type:'math_number'},{kind:'block',type:'math_arithmetic'}]},
{kind:'category',name:'變數',colour:'#7145ad',custom:'VARIABLE'},
{kind:'category',name:'圖像識別',colour:'#288256',contents:[{kind:'block',type:'vision_wait',inputs:{T:number(5)}}]}
]};
const theme=Blockly.Theme.defineTheme('classroom',{base:Blockly.Themes.Classic,blockStyles:{logic_blocks:{colourPrimary:'#7145ad'},loop_blocks:{colourPrimary:'#7145ad'},math_blocks:{colourPrimary:'#7145ad'},variable_blocks:{colourPrimary:'#7145ad'}},fontStyle:{family:'Microsoft JhengHei',size:12}});
const workspace=Blockly.inject('blockly',{toolbox,media:'media/',theme,trashcan:true,grid:{spacing:24,length:2,colour:'#dbe1e9',snap:true},zoom:{controls:true,wheel:true,startScale:1.05,minScale:.6,maxScale:1.5}});
function sync(){generated=pythonGenerator.workspaceToCode(workspace);if(!edited){$('code').value=generated;$('code-state').textContent='與積木一致';}}
workspace.addChangeListener(e=>{if(!e.isUiEvent)sync();});
function setMode(m){mode=m;document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x.dataset.mode===m));$('blockly').style.display=m==='python'?'none':'block';$('textwrap').style.display=m==='blocks'?'none':'flex';$('textwrap').style.width=m==='python'?'100%':'50%';Blockly.svgResize(workspace);}
document.querySelectorAll('[data-mode]').forEach(x=>x.onclick=()=>setMode(x.dataset.mode));
$('code').oninput=()=>{edited=$('code').value!==generated;$('code-state').textContent=edited?'文字已修改，積木保留原版':'與積木一致';};
$('generated').onclick=()=>{if(edited&&!confirm('用目前積木產生的 Python 覆蓋已修改的文字？'))return;edited=false;sync();};
lessons.forEach(l=>$('lesson').add(new Option(`${l.id} ${l.title}`,l.id)));
function loadLesson(id){if(running)return;const l=lessons.find(l=>l.id===Number(id));$('lesson').value=l.id;edited=false;workspace.clear();Blockly.serialization.workspaces.load(l.blocks,workspace);sync();if(l.codeOnly){$('code').value=l.code;edited=true;setMode('python');}else setMode('blocks');log(`已載入第 ${l.id} 課：${l.title}`);}
$('load').onclick=()=>{if(confirm('載入範例會替換目前專案，請先保存。繼續？'))loadLesson($('lesson').value);};
async function cancel(reason='已停止'){runGeneration++;running=false;clearTimeout(deadline);worker?.terminate();worker=null;vision.reset();$('run').disabled=false;updateConnectionActions();log(reason);if(connected){notice('停止指令已送出，等待設備回應');try{await api.stop();notice('設備已接受停止指令，請目視確認機器狗停止。');log('停止指令已接受；實際停止需目視確認');}catch(e){notice('停止未確認！請通知老師並按現場停止流程處理。');log('停止未確認：'+e.message);}}}
$('stop').onclick=()=>cancel();
async function visionWait(label,timeout,generation){if(!classes.includes(label))throw Error('模型没有這個類別：'+label);if(!cameraKind||cameraKind==='image')throw Error('請開啟即時相機；靜態图片不能觸發動作');timeout=Number(timeout);if(!Number.isFinite(timeout)||timeout<.1||timeout>10)throw Error('識別等待時間應在 0.1 至 10 秒');let until=Date.now()+timeout*1000;while(Date.now()<until){if(generation!==runGeneration)throw Error('程序已取消');if(Date.now()-lastFrameAt>1500){vision.reset();throw Error('相機畫面已過期，識別已取消');}if(vision.consume(label)){log(`確認識別：${label}`);return true;}await new Promise(r=>setTimeout(r,50));}log('識別等待超時，條件不成立');return false;}
async function command(action,args,generation){if(generation!==runGeneration)throw Error('程序已取消');if(action==='vision')return visionWait(args.label,args.timeout,generation);const v=validate(action,args);log(`${$('practice').checked?'練習':'實機'} ${action} ${Object.keys(v.args).length?JSON.stringify(v.args):''}`);if($('practice').checked){if(action==='battery')return 80;await new Promise(r=>setTimeout(r,action==='wait'?v.args.seconds*1000:180));return null;}const result=await api.command(action,v.args);if(result.duration_ms)await new Promise(r=>setTimeout(r,result.duration_ms));if(generation!==runGeneration)throw Error('程序已取消');return result.value??null;}
$('run').onclick=guard(async()=>{if(running)return;if(scanning||connectingRobot)throw Error('請等待掃描或連線完成');if(!$('practice').checked&&!connected)throw Error('先連接本組機器狗，或勾選練習模式');let code=mode==='blocks'?generated:$('code').value;if(!code.trim())throw Error('請先拖入積木或載入課程範例');if(!$('practice').checked&&!confirm('老師已示意，場地已清空，機身 MAC 與本組標籤一致？'))return;if(!$('practice').checked)await api.begin();running=true;let gen=++runGeneration;$('run').disabled=true;updateConnectionActions();deadline=setTimeout(()=>cancel('已達 60 秒程序上限'),60000);notice($('practice').checked?'練習運行中：觀察下方指令記錄':'實機運行中：操作員保持在停止按鈕旁');worker=new Worker('python-worker.js');const active=worker;worker.onmessage=async e=>{let m=e.data;if(gen!==runGeneration)return;if(m.type==='command'){try{const v=await command(m.action,m.args,gen);if(gen===runGeneration)active.postMessage({type:'answer',id:m.id,value:v});}catch(e){if(gen===runGeneration)active.postMessage({type:'answer',id:m.id,error:e.message});}}else if(m.type==='print')log(m.text);else if(m.type==='error')await cancel('程式錯誤：'+m.error);else if(m.type==='done'){clearTimeout(deadline);running=false;active.terminate();worker=null;$('run').disabled=false;if(!$('practice').checked){try{await api.end();notice('程序完成，設備已接受停止指令，請目視確認。');}catch{await cancel('結束時停止未確認');}}else notice('練習完成：請比對指令順序與預測');log('程序完成');updateConnectionActions();}};worker.postMessage({type:'run',code});});
$('practice').onchange=()=>{if(running){$('practice').checked=!$('practice').checked;notice('請先停止程序，再切換模式');return;}notice($('practice').checked?'練習模式只記錄指令，不會讓機器狗運動。':'實機模式：先核對機身標籤，測試前等老師示意');};
function updateConnectionActions(){
 $('scan').disabled=running||connectingRobot;
 $('disconnect').disabled=!connected||connectingRobot;
 renderRobots();
}
function renderRobots(){
 $('robot-list').replaceChildren();
 for(const robot of robots){
  const row=document.createElement('div');row.className='robot-row';
  const identity=document.createElement('div');identity.className='robot-identity';
  const name=document.createElement('strong');name.textContent='機器狗 · '+robot.mac.slice(-5);
  const mac=document.createElement('div');mac.className='robot-mac';mac.textContent=robot.mac;
  const state=document.createElement('span');state.className='robot-state';state.dataset.state=robot.state;
  state.textContent=connected&&connectedMac===robot.mac?'已連接':({available:'可連線',busy:'使用中',unavailable:'準備中',conflict:'MAC 衝突，請通知老師'}[robot.state]||'無法連線');
  identity.append(name,mac,state);
  const button=document.createElement('button');button.textContent=connectedMac===robot.mac&&connected?'已連接':'連線';
  button.disabled=robot.state!=='available'||connected||running||scanning||connectingRobot;
  button.dataset.mac=robot.mac;button.setAttribute('aria-label','連線 '+robot.mac);
  button.onclick=guard(()=>connectRobot(robot.mac));row.append(identity,button);$('robot-list').append(row);
 }
}
async function connectRobot(mac){
 if(running||scanning||connectingRobot)throw Error('請先停止並等待掃描完成');
 connectingRobot=true;$('status').textContent='連線中';updateConnectionActions();
 try{
  await closeCamera();const info=await api.connect(mac);connected=true;connectedMac=info.mac;
  $('status').textContent=`已連接 ${info.mac}`;$('battery').textContent=`電量 ${info.battery}%`;
  $('devices').hidden=true;notice('已連接，請核對機身 MAC；實機運行前等老師示意');log(`已連接 ${info.mac}，已取得控制權`);
 }catch(error){connected=false;connectedMac='';$('status').textContent='未連接';$('battery').textContent='電量 —';throw error;}
 finally{connectingRobot=false;updateConnectionActions();}
}
$('scan').onclick=guard(async()=>{
 if(running||connectingRobot)throw Error('請先停止並等待連線完成');
 if(scanning){await api['scan-cancel']();return;}
 if(!api)throw Error('請開啟 Windows 學生工坊程式');
 scanning=true;robots=[];$('devices').hidden=false;$('scan').textContent='取消掃描';$('scan-status').textContent='正在尋找…';renderRobots();
 try{
  const result=await api.scan();robots=result.robots;
  $('scan-status').textContent=result.cancelled?'已取消掃描':robots.length?`找到 ${robots.length} 隻`:'未找到機器狗';
  if(!result.cancelled&&!robots.length)notice('未找到機器狗：請確認電源、橋接服務，以及電腦和機器狗是否連接同一個可互通的 Wi-Fi');
 }catch(error){$('scan-status').textContent='掃描未完成';throw error;}
 finally{scanning=false;$('scan').textContent='掃描機器狗';updateConnectionActions();}
});
$('disconnect').onclick=guard(async()=>{await cancel('斷開前取消程序');await api.disconnect();connected=false;connectedMac='';$('status').textContent='未連接';$('battery').textContent='電量 —';await closeCamera();updateConnectionActions();});
$('save').onclick=guard(async()=>{const data={format:'d1-classroom',version:1,blocks:Blockly.serialization.workspaces.save(workspace),python:$('code').value,edited,mode,lesson:Number($('lesson').value)};if(api){if(await api.save(JSON.stringify(data,null,2)))log('專案已保存（模型須另外匯入）');}else{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.download='我的D1作品.d1.json';a.click();}});
$('open').onclick=guard(async()=>{if(running)throw Error('請先停止');const text=await api.open();if(!text)return;let p=JSON.parse(text);if(p.format!=='d1-classroom'||p.version!==1||!p.blocks||typeof p.python!=='string')throw Error('不是支援的 D1 專案');edited=false;Blockly.serialization.workspaces.load(p.blocks,workspace);sync();edited=!!p.edited;$('code').value=p.python;setMode(['blocks','split','python'].includes(p.mode)?p.mode:'blocks');$('lesson').value=p.lesson;log('專案已重開；確認模型與相機後再運行');});
$('clear').onclick=()=>$('log').textContent='';
$('tutorial').onclick=guard(async()=>{if(!api)throw Error('請從完整套件開啟本課教程');await api.tutorial(Number($('lesson').value));});
async function closeCamera(){cameraEpoch++;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}cameraKind=null;vision.reset();lastFrameAt=0;lastVideoTime=-1;await api?.['camera-stop']?.();$('camera-state').textContent='相機未開啟';}
$('camera-off').onclick=()=>{closeCamera();if(running)cancel('相機已關閉，程序取消');};
$('pc-camera').onclick=guard(async()=>{if(running)throw Error('請先停止，再切換相機');await closeCamera();stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});for(const t of stream.getVideoTracks())t.onended=()=>{closeCamera();notice('電腦相機已中斷');if(running)cancel('相機中斷，程序取消');};$('video').srcObject=stream;await $('video').play();cameraKind='pc';$('camera-state').textContent='電腦相機（請保持卡片在鏡頭內）';});
$('robot-camera').onclick=guard(async()=>{if(running)throw Error('請先停止，再切換相機');await closeCamera();await api.camera();cameraKind='robot';$('camera-state').textContent='等待機器狗相機畫面';});
api?.on('frame',data=>{if(cameraKind!=='robot')return;const epoch=cameraEpoch;let img=new Image();img.onload=()=>{if(cameraKind!=='robot'||epoch!==cameraEpoch)return;drawSource(img,img.naturalWidth,img.naturalHeight);newFrame();$('camera-state').textContent='機器狗相機（即時畫面）';};img.src='data:image/jpeg;base64,'+data;});
api?.on('camera-error',m=>{vision.reset();cameraKind=null;notice(m);if(running)cancel('相機中斷，程序取消');});
api?.on('status',b=>{$('battery').textContent=`電量 ${b.battery}%`;if(running&&!$('practice').checked&&b.battery<30)cancel('電量低於 30%，程序取消');});
api?.on('lost',m=>{connected=false;connectedMac='';$('battery').textContent='電量 —';updateConnectionActions();$('status').textContent='連接已中斷';closeCamera();cancel('網路中斷：'+m);notice('連接中斷，停止未確認！請通知老師。');});
$('capture').onclick=guard(async()=>{if(!cameraKind)throw Error('請先開啟相機或測試圖片');if(cameraKind!=='image'&&Date.now()-lastFrameAt>1500)throw Error('請等待新的相機畫面，再保存圖片');if(api){if(await api.picture(canvas.toDataURL('image/png')))log('圖片已保存');}else{let a=document.createElement('a');a.href=canvas.toDataURL('image/png');a.download='D1圖片.png';a.click();}});
$('image-input').onchange=guard(async()=>{if(running)throw Error('請先停止，再開啟測試圖片');let f=$('image-input').files[0];if(!f)return;await closeCamera();let img=await createImageBitmap(f);drawSource(img,img.width,img.height);img.close();cameraKind='image';$('camera-state').textContent='靜態測試圖片：'+f.name;await predict(false);});
async function loadModel(file){if(file.size>80e6)throw Error('模型 ZIP 不得超過 80 MB');const zip=await JSZip.loadAsync(file);let list=Object.values(zip.files).filter(f=>!f.dir);const find=name=>list.find(f=>f.name.split('/').pop()===name);let mf=find('model.json'),md=find('metadata.json');if(!mf||!md)throw Error('ZIP 內須包含 model.json、metadata.json 與權重 .bin');let meta=JSON.parse(await md.async('string'));if(!Array.isArray(meta.labels)||!meta.labels.length||meta.labels.length>30||meta.labels.some(l=>typeof l!=='string'||l.length>80)||new Set(meta.labels).size!==meta.labels.length)throw Error('模型類別名稱無效');if(meta.imageSize&&meta.imageSize!==224)throw Error('第一版支援標準 224 像素圖像專案');if(meta.grayscale)throw Error('第一版支援彩色標準圖像專案');let topology=JSON.parse(await mf.async('string'));if(!Array.isArray(topology.weightsManifest))throw Error('模型格式不是 TensorFlow.js Layers');let specs=[],buffers=[];for(const group of topology.weightsManifest){specs.push(...group.weights);for(const name of group.paths){let base=mf.name.slice(0,mf.name.length-'model.json'.length);let f=zip.file(base+name)||zip.file(name);if(!f)throw Error('缺少權重：'+name);buffers.push(await f.async('uint8array'));}}let size=buffers.reduce((n,b)=>n+b.length,0);if(size>100e6)throw Error('模型解壓後過大');let data=new Uint8Array(size),offset=0;for(const b of buffers){data.set(b,offset);offset+=b.length;}let next=await tf.loadLayersModel(tf.io.fromMemory({modelTopology:topology.modelTopology,weightSpecs:specs,weightData:data.buffer}));if(next.inputs[0].shape.slice(1).join(',')!=='224,224,3'||next.outputs[0].shape.at(-1)!==meta.labels.length){next.dispose();throw Error('模型輸入或輸出與標準圖像專案不符');}model?.dispose();model=next;metadata=meta;classes=meta.labels;vision.reset();workspace.refreshToolboxSelection();for(const b of workspace.getAllBlocks(false)){if(b.type==='vision_wait')b.getField('LABEL').refresh();}sync();$('model-state').textContent='已載入：'+classes.join('、');log('模型載入成功，先用新圖片測試，不要立即讓機器狗運動');if(cameraKind)await predict(false);}
$('model-input').onchange=guard(async()=>{if(running)throw Error('請先停止再匯入模型');let f=$('model-input').files[0];if(f)await loadModel(f);});
async function predict(live){if(!model||inferenceBusy)return;inferenceBusy=true;const sequence=frameSeq,epoch=cameraEpoch,active=model,labels=classes.slice();let out;try{out=tf.tidy(()=>active.predict(inputForModel(tf,canvas)));const probs=Array.from(await out.data());if(active!==model||epoch!==cameraEpoch)return;let results=labels.map((c,i)=>({className:c,probability:probs[i]}));$('predictions').replaceChildren(...results.map(r=>{let div=document.createElement('div'),label=document.createElement('span'),score=document.createElement('strong');label.textContent=r.className;score.textContent=(r.probability*100).toFixed(1)+'%';div.append(label,score);return div;}));if(live&&cameraKind&&cameraKind!=='image'&&Date.now()-lastFrameAt<1500)vision.add(results,sequence);}catch(e){log('分類失敗：'+e.message);vision.reset();}finally{out?.dispose();inferenceBusy=false;}}
function newFrame(){lastFrameAt=Date.now();frameSeq++;predict(true);}
setInterval(()=>{if(cameraKind==='pc'&&$('video').readyState>=2&&$('video').currentTime!==lastVideoTime){lastVideoTime=$('video').currentTime;drawSource($('video'),$('video').videoWidth,$('video').videoHeight);newFrame();}else if(cameraKind&&cameraKind!=='image'&&Date.now()-lastFrameAt>1500)vision.reset();},200);
window.addEventListener('resize',()=>Blockly.svgResize(workspace));
window.addEventListener('beforeunload',()=>{worker?.terminate();api?.stop?.().catch(()=>{});});
window.d1Test={cropForModel,workspace,loadLesson,setMode,loadModel,predict,classes:()=>classes,log:()=> $('log').textContent};
loadLesson(3);
