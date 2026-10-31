importScripts('skulpt.min.js','skulpt-stdlib.js','robot-api.js');
let serial=0,waiting=new Map();
function unicodeNames(code){
 const token=/"""(?:\\[\s\S]|(?!""")[\s\S])*"""|'''(?:\\[\s\S]|(?!''')[\s\S])*'''|"(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|#[^\r\n]*|[\p{L}_][\p{L}\p{N}_]*/gu;
 const ids=(code.match(token)||[]).filter(x=>!['"',"'",'#'].includes(x[0])),used=new Set(ids),map=new Map();
 for(const id of ids)if(!/^[a-zA-Z0-9_]+$/.test(id)&&!map.has(id)){let name='_d1unicode_'+Array.from(id).map(c=>c.codePointAt(0).toString(16)).join('_');while(used.has(name))name+='_';used.add(name);map.set(id,name);}
 return {code:code.replace(token,t=>map.get(t)||t),map};
}
function rpc(action,args){return new Promise((resolve,reject)=>{let id=++serial;waiting.set(id,{resolve,reject});postMessage({type:'command',id,action,args});});}
onmessage=async e=>{let m=e.data;if(m.type==='answer'){let p=waiting.get(m.id);waiting.delete(m.id);if(p){m.error?p.reject(new Error(m.error)):p.resolve(m.value);}return;}
if(m.type!=='run')return;
let printed=0;Sk.configure({output:t=>{printed+=t.length;if(printed>5000)throw new Sk.builtin.RuntimeError('輸出過多，請縮短重複次數');postMessage({type:'print',text:t});},read:f=>{if(Sk.builtinFiles.files[f])return Sk.builtinFiles.files[f];throw Error('此課程工具不提供外部 Python 套件');},__future__:Sk.python3,execLimit:3000,yieldLimit:50,killableWhile:true,killableFor:true});
Sk.builtins._d1_command=new Sk.builtin.func((action,args)=>Sk.misceval.promiseToSuspension(rpc(Sk.ffi.remapToJs(action),Sk.ffi.remapToJs(args)).then(v=>{Sk.execStart=Date.now();return Sk.ffi.remapToPy(v??null);})));
const preamble=[
'class _Dog:',
...['stand','lie','stop','battery','greet','passive','jump','front_jump','backflip','cancel_two_leg_stand'].map(a=>`    def ${a}(self): return _d1_command('${a}', {})`),
"    def shake_hand(self): return self.greet()",
...['forward','back','side_left','side_right'].map(a=>`    def ${a}(self, seconds=1, speed=${a.startsWith('side_')?'0.1':'0.15'}): return _d1_command('${a}', {'seconds': seconds, 'speed': speed})`),
"    def turn_left(self, degrees=30): return _d1_command('left', {'degrees': degrees})",
"    def turn_right(self, degrees=30): return _d1_command('right', {'degrees': degrees})",
"    def wait(self, seconds=1): return _d1_command('wait', {'seconds': seconds})",
"    def move(self, vx=0, vy=0, yaw_rate=0, seconds=1): return _d1_command('move', {'vx': vx, 'vy': vy, 'yaw_rate': yaw_rate, 'seconds': seconds})",
"    def attitude(self, roll=0, pitch=0, yaw=0, height=0, seconds=0.5): return _d1_command('attitude', {'roll': roll, 'pitch': pitch, 'yaw': yaw, 'height': height, 'seconds': seconds})",
"    def two_leg_stand(self, seconds=1): return _d1_command('two_leg_stand', {'seconds': seconds})",
...self.D1RobotAPI.sensors.map(s=>`    def ${s.id}(self): return _d1_command('telemetry', {'name': '${s.id}'})`),
'class _Vision:',
"    def wait_for(self, label, timeout=5): return _d1_command('vision', {'label': label, 'timeout': timeout})",
"    def label(self, min_score=0.8): return _d1_command('vision_label', {'min_score': min_score})",
"    def is_label(self, label, min_score=0.8): return _d1_command('vision_seen', {'label': label, 'min_score': min_score})",
"    def score(self, label): return _d1_command('vision_score', {'label': label})",
'dog = _Dog()', 'vision = _Vision()', ''
].join('\n');
const translated=unicodeNames(m.code);
try{await Sk.misceval.asyncToPromise(()=>Sk.importMainWithBody('<學生程式>',false,preamble+'\n'+translated.code,true));postMessage({type:'done'});}catch(err){let s=String(err);for(const [label,name] of translated.map)s=s.split(name).join(label);const offset=preamble.split('\n').length;s=s.replace(/on line (\d+)/,(_,n)=>`在學生程式第 ${Math.max(1,Number(n)-offset)} 行`);postMessage({type:'error',error:s});}
};
