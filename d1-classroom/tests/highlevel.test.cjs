const {test}=require('node:test'),assert=require('node:assert/strict');
const {validate}=require('../app/policy.cjs');
const {actions,sensors}=require('../app/robot-api.js');
const {Confirmations}=require('../app/vision-core.cjs');

test('bounded high-level motion and sensor allowlist',()=>{
 assert.deepEqual(validate('move',{vx:.1,vy:.1,seconds:.5}).args,{vx:.1,vy:.1,yaw_rate:0,seconds:.5});
 for(const [a,args] of [['move',{vx:.2,vy:.2}],['move',{vy:.01}],['side_left',{seconds:1,speed:.05}],['attitude',{roll:.5}],['attitude',{height:.1}],['two_leg_stand',{seconds:3}],['telemetry',{name:'sendMotorCmd'}],['move',{vx:true}],['forward',{seconds:'1'}]])assert.throws(()=>validate(a,args));
 for(const s of sensors)assert.equal(validate('telemetry',{name:s.id}).args.name,s.id);
 assert(actions.find(a=>a.id==='backflip').hidden);
 assert.equal(actions.find(a=>a.id==='backflip').risk,'extreme');
});
test('continuous stable classification is not consumed and expires with frames',t=>{
 let now=1000;t.mock.method(Date,'now',()=>now);const c=new Confirmations(),a=[{className:'a',probability:.95}];
 c.add(a,1);c.add(a,2);assert.equal(c.current(),null);c.add(a,3);
 assert(c.consume('a'));assert.equal(c.current(),'a');assert.equal(c.current(),'a');assert.equal(c.consume('a'),false);
 c.add([{className:'b',probability:.95}],4);assert.equal(c.current(),null);
 c.add([{className:'b',probability:.95}],5);c.add([{className:'b',probability:.95}],6);assert.equal(c.current(),'b');
 now+=1501;assert.equal(c.current(),null);
});
