import * as Blockly from 'blockly';
import 'blockly/blocks';
import * as zh from 'blockly/msg/zh-hant';
import {pythonGenerator,Order} from 'blockly/python';
import * as tf from '@tensorflow/tfjs';
import JSZip from 'jszip';
import {inputForModel,cropForModel} from './tm-preprocess.js';
import {Confirmations} from './vision-core.cjs';
import {validate} from './policy.cjs';
import {actions as extraActions,sensors} from './robot-api.js';
import lessons from '../curriculum/lessons.json';
Blockly.setLocale(zh);
const $=id=>document.getElementById(id), api=window.desktop;
let mode='blocks',generated='',edited=false,running=false,worker=null,deadline=null,connected=false,stream=null,cameraKind=null,frameSeq=0,lastFrameAt=0,lastVideoTime=-1,cameraEpoch=0,inferenceBusy=false,model=null,metadata=null,classes=[],vision=new Confirmations(),runGeneration=0;
let scanning=false,connectingRobot=false,connectedMac='',robots=[],latestResults=[],latestResultAt=0,robotAPIVersion=1,showBackflip=false;
const canvas=$('camera'),ctx=canvas.getContext('2d');
function drawSource(source,width,height){if(!width||!height)return;canvas.width=width;canvas.height=height;ctx.drawImage(source,0,0,width,height);}
function log(t){$('log').textContent=($('log').textContent+`[${new Date().toLocaleTimeString('zh-TW',{hour12:false})}] ${String(t).slice(0,3000)}\n`).slice(-30000);$('log').scrollTop=$('log').scrollHeight;}
function notice(t){$('notice').textContent=t;}
function guard(fn){return async(...args)=>{try{await fn(...args);}catch(e){log(e.message);notice(e.message);}};}
function number(n){return {block:{type:'math_number',fields:{NUM:n}}};}
function value(block,name){return pythonGenerator.valueToCode(block,name,Order.NONE)||'0';}
for(const [type,text,method,color] of [['stand','站立','stand',210],['lie','趴下','lie',210],['stop','停止','stop',0],...extraActions.filter(a=>['greet','passive','jump','front_jump','backflip','cancel_two_leg_stand'].includes(a.id)).map(a=>[a.id,a.label,a.method,a.risk?0:210])]){
 Blockly.Blocks['dog_'+type]={init(){this.appendDummyInput().appendField(text);this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(color);}};
 pythonGenerator.forBlock['dog_'+type]=()=>`dog.${method}()\n`;
}
for(const [type,text,method,arg,color] of [['forward','前進','forward','seconds',210],['back','後退','back','seconds',210],['left','左轉','turn_left','degrees',210],['right','右轉','turn_right','degrees',210],['side_left','向左側移','side_left','seconds',210],['side_right','向右側移','side_right','seconds',210],['wait','等待','wait','seconds',30],['two_leg_stand','⚠ 雙腿站立','two_leg_stand','seconds',0]]){
 Blockly.Blocks['dog_'+type]={init(){this.appendValueInput('N').setCheck('Number').appendField(text);this.appendDummyInput().appendField(arg==='degrees'?'度':'秒');this.setInputsInline(true);this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(color);}};
 pythonGenerator.forBlock['dog_'+type]=b=>`dog.${method}(${arg}=${value(b,'N')})\n`;
}
Blockly.Blocks.dog_battery={init(){this.appendDummyInput().appendField('電量百分比');this.setOutput(true,'Number');this.setColour(210);}};pythonGenerator.forBlock.dog_battery=()=>['dog.battery()',Order.FUNCTION_CALL];
for(const [type,label,params] of [
 ['move','組合移動',[['VX','vx','前後 m/s'],['VY','vy','側移 m/s'],['YAW','yaw_rate','轉向 rad/s'],['T','seconds','秒']]],
 ['attitude','姿態調整',[['ROLL','roll','翻滾 rad/s'],['PITCH','pitch','俯仰 rad/s'],['YAW','yaw','偏航 rad/s'],['HEIGHT','height','高度 m/s'],['T','seconds','秒']]]
]){
 Blockly.Blocks['dog_'+type]={init(){this.appendDummyInput().appendField(label);for(const [field,,text] of params)this.appendValueInput(field).setCheck('Number').appendField(text);this.setPreviousStatement(true);this.setNextStatement(true);this.setColour(210);}};
 pythonGenerator.forBlock['dog_'+type]=b=>`dog.${type}(${params.map(([f,arg])=>`${arg}=${value(b,f)}`).join(', ')})\n`;
}
Blockly.Blocks.dog_telemetry={init(){this.appendDummyInput().appendField('讀取').appendField(new Blockly.FieldDropdown(sensors.map(s=>[s.label+'（'+s.unit+'）',s.id])),'SENSOR');this.setOutput(true);this.setColour(190);}};
pythonGenerator.forBlock.dog_telemetry=b=>[`dog.${b.getFieldValue('SENSOR')}()`,Order.FUNCTION_CALL];
class ModelLabel extends Blockly.FieldDropdown {
 constructor(){super(function(){const selected=this.pendingLabel||this.getValue()||'左轉卡';if(!classes.length)return [[selected+'（先匯入模型）',selected]];const options=classes.map(c=>[c,c]);if(!classes.includes(selected))options.push(['模型缺少：'+selected,selected]);return options;});}
 refresh(){this.getOptions(false);this.doValueUpdate_(this.getValue());this.forceRerender();}
 loadState(state){this.pendingLabel=typeof state==='string'?state:null;this.getOptions(false);super.loadState(state);this.pendingLabel=null;this.refresh();}
}
Blockly.Blocks.vision_wait={init(){this.appendDummyInput().appendField('等待識別').appendField(new ModelLabel(),'LABEL');this.appendValueInput('T').setCheck('Number').appendField('最多');this.appendDummyInput().appendField('秒');this.setOutput(true,'Boolean');this.setColour(145);this.setInputsInline(true);}};pythonGenerator.forBlock.vision_wait=b=>[`vision.wait_for(${JSON.stringify(b.getFieldValue('LABEL'))}, timeout=${value(b,'T')})`,Order.FUNCTION_CALL];
for(const [type,text,method,output] of [['seen','目前看見','is_label','Boolean'],['score','目前分類分數','score','Number']]){
 Blockly.Blocks['vision_'+type]={init(){this.appendDummyInput().appendField(text).appendField(new ModelLabel(),'LABEL');this.setOutput(true,output);this.setColour(145);}};
 pythonGenerator.forBlock['vision_'+type]=b=>[`vision.${method}(${JSON.stringify(b.getFieldValue('LABEL'))})`,Order.FUNCTION_CALL];
}
Blockly.Blocks.vision_label={init(){this.appendDummyInput().appendField('目前穩定辨識類別');this.setOutput(true);this.setColour(145);}};
pythonGenerator.forBlock.vision_label=()=>['vision.label()',Order.FUNCTION_CALL];
const toolbox={kind:'categoryToolbox',contents:[
{kind:'category',name:'機器狗動作',colour:'#276bc0',contents:['stand','forward','back','left','right','stop','lie','wait'].map(t=>({kind:'block',type:'dog_'+t,inputs:['stand','stop','lie'].includes(t)?undefined:{N:number(['left','right'].includes(t)?30:1)}})).concat([{kind:'block',type:'dog_battery'}])},
{kind:'category',name:'互動與姿態',colour:'#276bc0',contents:[{kind:'block',type:'dog_greet'},{kind:'block',type:'dog_passive'},...['side_left','side_right'].map(t=>({kind:'block',type:'dog_'+t,inputs:{N:number(.5)}})),{kind:'block',type:'dog_move',inputs:{VX:number(.1),VY:number(0),YAW:number(0),T:number(.5)}},{kind:'block',type:'dog_attitude',inputs:{ROLL:number(0),PITCH:number(.05),YAW:number(0),HEIGHT:number(0),T:number(.5)}}]},
{kind:'category',name:'感測資料',colour:'#297c8d',contents:[{kind:'block',type:'dog_telemetry'},{kind:'block',type:'text_print'}]},
{kind:'category',name:'⚠ 高風險動作',colour:'#b52532',contents:[{kind:'label',text:'真機須明確允許本次高風險動作'},...['jump','front_jump'].map(t=>({kind:'block',type:'dog_'+t})),{kind:'block',type:'dog_two_leg_stand',inputs:{N:number(1)}},{kind:'block',type:'dog_cancel_two_leg_stand'}]},
{kind:'category',name:'邏輯判斷',colour:'#7145ad',contents:[{kind:'block',type:'controls_if'},{kind:'block',type:'logic_compare'},{kind:'block',type:'logic_boolean'}]},
{kind:'category',name:'重複',colour:'#7145ad',contents:[{kind:'block',type:'controls_repeat_ext',inputs:{TIMES:number(2)}}]},
{kind:'category',name:'數學',colour:'#7145ad',contents:[{kind:'block',type:'math_number'},{kind:'block',type:'math_arithmetic'}]},
{kind:'category',name:'變數',colour:'#7145ad',custom:'VARIABLE'},
{kind:'category',name:'圖像識別',colour:'#288256',contents:[{kind:'block',type:'vision_wait',inputs:{T:number(5)}},{kind:'block',type:'vision_label'},{kind:'block',type:'vision_seen'},{kind:'block',type:'vision_score'},{kind:'block',type:'text_print'}]}
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
function setPython(code,append=false){if(running)throw Error('請先停止程序');$('code').value=(append?$('code').value.trimEnd()+'\n':'')+code+'\n';edited=true;$('code-state').textContent='文字已修改，積木保留原版';setMode('python');}
function renderLibrary(){
 $('api-list').replaceChildren();
 for(const item of [...extraActions.filter(a=>!a.hidden||showBackflip),...sensors.map(s=>({label:s.label,example:`print(dog.${s.id}())`,note:s.unit}))]){
  const card=document.createElement('div');card.className='api-card';if(item.risk)card.dataset.risk=item.risk;
  const label=document.createElement('strong'),code=document.createElement('code'),note=document.createElement('p'),button=document.createElement('button');
  label.textContent=item.label;code.textContent=item.example;note.textContent=item.note;button.textContent='插入 Python';button.onclick=guard(()=>setPython(item.example,true));card.append(label,code,note,button);$('api-list').append(card);
 }
}
for(const [label,code] of [
 ['載入打招呼範例','dog.stand()\ndog.greet()\ndog.lie()'],
 ['載入感測列印範例','print("控制模式", dog.mode())\nprint("姿態 rad", dog.rpy())\nprint("關節角度 rad", dog.joints_position())'],
 ['載入持續辨識（只列印）','for count in range(10):\n    print("目前穩定類別", vision.label())\n    dog.wait(seconds=0.5)'],
 ['載入 a／b 姿態範例','last = None\nfor count in range(10):\n    label = vision.label()\n    print("目前類別", label)\n    if label == "a" and last != "a":\n        dog.stand()\n        last = "a"\n    elif label == "b" and last != "b":\n        dog.lie()\n        last = "b"\n    dog.wait(seconds=0.5)']
]){const button=document.createElement('button');button.textContent=label;button.onclick=guard(()=>setPython(code));$('quick-examples').append(button);}
function syncRiskControls(){
 $('allow-backflip').disabled=running||!showBackflip||!$('allow-high-risk').checked;
 if(!showBackflip||!$('allow-high-risk').checked)$('allow-backflip').checked=false;
}
function resetRiskPermissions(){$('allow-high-risk').checked=false;$('allow-backflip').checked=false;syncRiskControls();}
$('allow-high-risk').onchange=syncRiskControls;
$('show-backflip').onchange=()=>{showBackflip=$('show-backflip').checked;const updated={...toolbox,contents:[...toolbox.contents]};if(showBackflip)updated.contents.push({kind:'category',name:'⚠ 危險：後空翻',colour:'#b52532',contents:[{kind:'label',text:'可能造成人員受傷或設備損壞'},{kind:'block',type:'dog_backflip'}]});workspace.updateToolbox(updated);syncRiskControls();renderLibrary();};
renderLibrary();
function readVision(action,args){
 if(!model)throw Error('請先匯入圖像模型');
 if(!cameraKind||cameraKind==='image')throw Error('請開啟即時相機；靜態圖片不能用來持續觸發動作');
 if(Date.now()-lastFrameAt>1500||Date.now()-latestResultAt>1500)throw Error('尚無新的辨識結果，請等待相機與模型準備好');
 if(action!=='vision_label'&&!classes.includes(args.label))throw Error('模型沒有這個類別：'+args.label);
 const threshold=args.min_score??.8;if(typeof threshold!=='number'||!Number.isFinite(threshold)||threshold<.8||threshold>1)throw Error('辨識門檻應在 0.8 至 1 之間');
 if(action==='vision_score')return latestResults.find(r=>r.className===args.label)?.probability??0;
 const label=vision.current(threshold);return action==='vision_label'?label:label===args.label;
}
async function cancel(reason='已停止'){runGeneration++;running=false;clearTimeout(deadline);worker?.terminate();worker=null;vision.reset();$('run').disabled=false;updateConnectionActions();log(reason);notice(reason);resetRiskPermissions();if(connected){notice('停止指令已送出，等待設備回應');try{await api.stop();notice(reason+'；設備已回應停止請求，請目視確認機器狗停止。');log('停止指令已接受；實際停止需目視確認');}catch(e){notice('停止未確認！請通知老師並按現場停止流程處理。');log('停止未確認：'+e.message);}}}
$('stop').onclick=()=>cancel();
async function visionWait(label,timeout,generation){if(!classes.includes(label))throw Error('模型没有這個類別：'+label);if(!cameraKind||cameraKind==='image')throw Error('請開啟即時相機；靜態图片不能觸發動作');timeout=Number(timeout);if(!Number.isFinite(timeout)||timeout<.1||timeout>10)throw Error('識別等待時間應在 0.1 至 10 秒');let until=Date.now()+timeout*1000;while(Date.now()<until){if(generation!==runGeneration)throw Error('程序已取消');if(Date.now()-lastFrameAt>1500){vision.reset();throw Error('相機畫面已過期，識別已取消');}if(vision.consume(label)){log(`確認識別：${label}`);return true;}await new Promise(r=>setTimeout(r,50));}log('識別等待超時，條件不成立');return false;}
async function command(action,args,generation){
 if(generation!==runGeneration)throw Error('程序已取消');
 if(action==='vision')return visionWait(args.label,args.timeout,generation);
 if(['vision_label','vision_seen','vision_score'].includes(action))return readVision(action,args);
 const v=validate(action,args),descriptor=extraActions.find(a=>a.id===action);
 log(`${$('practice').checked?'練習':'實機'} ${action} ${Object.keys(v.args).length?JSON.stringify(v.args):''}`);
 if(descriptor?.risk)log('高風險動作：'+descriptor.note);
 if($('practice').checked){
  if(action==='battery')return 80;
  if(action==='telemetry'){log('練習感測數值：非實機資料');if(v.args.name==='mode')return 0;if(v.args.name==='quaternion')return [1,0,0,0];if(v.args.name.startsWith('joints_'))return {abad:[0,0,0,0],hip:[0,0,0,0],knee:[0,0,0,0]};return [0,0,0];}
  await new Promise(r=>setTimeout(r,action==='wait'?v.args.seconds*1000:180));return null;
 }
 if((descriptor||action==='telemetry')&&robotAPIVersion<3)throw Error('此功能需要更新狗端橋接；目前僅學生工坊已更新');
 const result=await api.command(action,v.args);if(result.duration_ms)await new Promise(r=>setTimeout(r,result.duration_ms));if(generation!==runGeneration)throw Error('程序已取消');return result.value??null;
}
$('run').onclick=guard(async()=>{if(running)return;if(scanning||connectingRobot)throw Error('請等待掃描或連線完成');if(!$('practice').checked&&!connected)throw Error('先連接本組機器狗，或勾選練習模式');let code=mode==='blocks'?generated:$('code').value;if(!code.trim())throw Error('請先拖入積木或載入課程範例');const permissions={allow_high_risk:$('allow-high-risk').checked,allow_backflip:$('allow-backflip').checked};const riskText=permissions.allow_high_risk?'\n本次允許跳躍／雙腿站立等高風險動作，可能失衡、碰撞、夾傷或損壞設備；軟體停止不能保證中止特技。'+(permissions.allow_backflip?'\n另外允許危險的後空翻，可能造成重擊與人員受傷。':''):'';if(!$('practice').checked&&!confirm('現場人員已準備好硬體停止、場地淨空、機身 MAC 正確？'+riskText))return;if(!$('practice').checked)await api.begin(permissions);running=true;let gen=++runGeneration;$('run').disabled=true;updateConnectionActions();deadline=setTimeout(()=>cancel('已達 60 秒程序上限'),60000);notice($('practice').checked?'練習運行中：觀察下方指令記錄':'實機運行中：操作員保持在停止按鈕旁');worker=new Worker('python-worker.js');const active=worker;active.onerror=e=>{if(gen===runGeneration)cancel('Python 執行器錯誤：'+e.message);};worker.onmessage=async e=>{let m=e.data;if(gen!==runGeneration)return;if(m.type==='command'){try{const v=await command(m.action,m.args,gen);if(gen===runGeneration)active.postMessage({type:'answer',id:m.id,value:v});}catch(e){if(gen===runGeneration)active.postMessage({type:'answer',id:m.id,error:e.message});}}else if(m.type==='print')log(m.text);else if(m.type==='error')await cancel('程式錯誤：'+m.error);else if(m.type==='done'){clearTimeout(deadline);running=false;active.terminate();worker=null;$('run').disabled=false;resetRiskPermissions();if(!$('practice').checked){try{await api.end();notice('程序完成，設備已接受停止指令，請目視確認。');}catch{await cancel('結束時停止未確認');}}else notice('練習完成：請比對指令順序與預測');log('程序完成');updateConnectionActions();}};worker.postMessage({type:'run',code});});
$('practice').onchange=()=>{if(running){$('practice').checked=!$('practice').checked;notice('請先停止程序，再切換模式');return;}notice($('practice').checked?'練習模式只記錄指令，不會讓機器狗運動。':'實機模式：先核對機身標籤，測試前等老師示意');};
function updateConnectionActions(){
 $('allow-high-risk').disabled=running;$('show-backflip').disabled=running;syncRiskControls();
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
  await closeCamera();const info=await api.connect(mac);connected=true;connectedMac=info.mac;robotAPIVersion=Number(info.api_version)||1;
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
async function closeCamera(){cameraEpoch++;if(stream){stream.getTracks().forEach(t=>t.stop());stream=null;}cameraKind=null;vision.reset();latestResults=[];latestResultAt=0;lastFrameAt=0;lastVideoTime=-1;await api?.['camera-stop']?.();$('camera-state').textContent='相機未開啟';}
$('camera-off').onclick=()=>{closeCamera();if(running)cancel('相機已關閉，程序取消');};
$('pc-camera').onclick=guard(async()=>{if(running)throw Error('請先停止，再切換相機');await closeCamera();stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});for(const t of stream.getVideoTracks())t.onended=()=>{closeCamera();notice('電腦相機已中斷');if(running)cancel('相機中斷，程序取消');};$('video').srcObject=stream;await $('video').play();cameraKind='pc';$('camera-state').textContent='電腦相機（請保持卡片在鏡頭內）';});
$('robot-camera').onclick=guard(async()=>{if(running)throw Error('請先停止，再切換相機');await closeCamera();await api.camera();cameraKind='robot';$('camera-state').textContent='等待機器狗相機畫面';});
api?.on('frame',data=>{if(cameraKind!=='robot')return;const epoch=cameraEpoch;let img=new Image();img.onload=()=>{if(cameraKind!=='robot'||epoch!==cameraEpoch)return;drawSource(img,img.naturalWidth,img.naturalHeight);newFrame();$('camera-state').textContent='機器狗相機（即時畫面）';};img.src='data:image/jpeg;base64,'+data;});
api?.on('camera-error',m=>{vision.reset();cameraKind=null;notice(m);if(running)cancel('相機中斷，程序取消');});
api?.on('status',b=>{$('battery').textContent=`電量 ${b.battery}%`;if(running&&!$('practice').checked&&b.battery<30)cancel('電量低於 30%，程序取消');});
api?.on('lost',m=>{connected=false;connectedMac='';$('battery').textContent='電量 —';updateConnectionActions();$('status').textContent='連接已中斷';closeCamera();cancel('連線中斷：'+m);notice('連線中斷：'+m+'；停止未確認，請按現場停止流程處理。');});
$('capture').onclick=guard(async()=>{if(!cameraKind)throw Error('請先開啟相機或測試圖片');if(cameraKind!=='image'&&Date.now()-lastFrameAt>1500)throw Error('請等待新的相機畫面，再保存圖片');if(api){if(await api.picture(canvas.toDataURL('image/png')))log('圖片已保存');}else{let a=document.createElement('a');a.href=canvas.toDataURL('image/png');a.download='D1圖片.png';a.click();}});
$('image-input').onchange=guard(async()=>{if(running)throw Error('請先停止，再開啟測試圖片');let f=$('image-input').files[0];if(!f)return;await closeCamera();let img=await createImageBitmap(f);drawSource(img,img.width,img.height);img.close();cameraKind='image';$('camera-state').textContent='靜態測試圖片：'+f.name;await predict(false);});
async function loadModel(file){if(file.size>80e6)throw Error('模型 ZIP 不得超過 80 MB');const zip=await JSZip.loadAsync(file);let list=Object.values(zip.files).filter(f=>!f.dir);const find=name=>list.find(f=>f.name.split('/').pop()===name);let mf=find('model.json'),md=find('metadata.json');if(!mf||!md)throw Error('ZIP 內須包含 model.json、metadata.json 與權重 .bin');let meta=JSON.parse(await md.async('string'));if(!Array.isArray(meta.labels)||!meta.labels.length||meta.labels.length>30||meta.labels.some(l=>typeof l!=='string'||l.length>80)||new Set(meta.labels).size!==meta.labels.length)throw Error('模型類別名稱無效');if(meta.imageSize&&meta.imageSize!==224)throw Error('第一版支援標準 224 像素圖像專案');if(meta.grayscale)throw Error('第一版支援彩色標準圖像專案');let topology=JSON.parse(await mf.async('string'));if(!Array.isArray(topology.weightsManifest))throw Error('模型格式不是 TensorFlow.js Layers');let specs=[],buffers=[];for(const group of topology.weightsManifest){specs.push(...group.weights);for(const name of group.paths){let base=mf.name.slice(0,mf.name.length-'model.json'.length);let f=zip.file(base+name)||zip.file(name);if(!f)throw Error('缺少權重：'+name);buffers.push(await f.async('uint8array'));}}let size=buffers.reduce((n,b)=>n+b.length,0);if(size>100e6)throw Error('模型解壓後過大');let data=new Uint8Array(size),offset=0;for(const b of buffers){data.set(b,offset);offset+=b.length;}let next=await tf.loadLayersModel(tf.io.fromMemory({modelTopology:topology.modelTopology,weightSpecs:specs,weightData:data.buffer}));if(next.inputs[0].shape.slice(1).join(',')!=='224,224,3'||next.outputs[0].shape.at(-1)!==meta.labels.length){next.dispose();throw Error('模型輸入或輸出與標準圖像專案不符');}model?.dispose();model=next;metadata=meta;classes=meta.labels;vision.reset();latestResults=[];latestResultAt=0;workspace.refreshToolboxSelection();for(const b of workspace.getAllBlocks(false)){if(['vision_wait','vision_seen','vision_score'].includes(b.type))b.getField('LABEL').refresh();}sync();$('model-state').textContent='已載入：'+classes.join('、');log('模型載入成功，先用新圖片測試，不要立即讓機器狗運動');if(cameraKind)await predict(false);}
$('model-input').onchange=guard(async()=>{if(running)throw Error('請先停止再匯入模型');let f=$('model-input').files[0];if(f)await loadModel(f);});
async function predict(live){if(!model||inferenceBusy)return;inferenceBusy=true;const sequence=frameSeq,epoch=cameraEpoch,active=model,labels=classes.slice(),capturedAt=lastFrameAt;let out;try{out=tf.tidy(()=>active.predict(inputForModel(tf,canvas)));const probs=Array.from(await out.data());if(active!==model||epoch!==cameraEpoch)return;let results=labels.map((c,i)=>({className:c,probability:probs[i]}));$('predictions').replaceChildren(...results.map(r=>{let div=document.createElement('div'),label=document.createElement('span'),score=document.createElement('strong');label.textContent=r.className;score.textContent=(r.probability*100).toFixed(1)+'%';div.append(label,score);return div;}));if(live&&cameraKind&&cameraKind!=='image'&&Date.now()-capturedAt<1500){latestResults=results;latestResultAt=capturedAt;vision.add(results,sequence);}}catch(e){log('分類失敗：'+e.message);vision.reset();}finally{out?.dispose();inferenceBusy=false;}}
function newFrame(){lastFrameAt=Date.now();frameSeq++;predict(true);}
setInterval(()=>{if(cameraKind==='pc'&&$('video').readyState>=2&&$('video').currentTime!==lastVideoTime){lastVideoTime=$('video').currentTime;drawSource($('video'),$('video').videoWidth,$('video').videoHeight);newFrame();}else if(cameraKind&&cameraKind!=='image'&&Date.now()-lastFrameAt>1500)vision.reset();},200);
window.addEventListener('resize',()=>Blockly.svgResize(workspace));
window.addEventListener('beforeunload',()=>{worker?.terminate();api?.stop?.().catch(()=>{});});
window.d1Test={cropForModel,workspace,loadLesson,setMode,loadModel,predict,classes:()=>classes,readVision,log:()=> $('log').textContent};
loadLesson(3);
