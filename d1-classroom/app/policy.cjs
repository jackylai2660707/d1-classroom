const LIMITS = Object.freeze({speed:0.2, yaw:0.3, seconds:3, degrees:45, job:60000, battery:30});
const {sensors}=require('./robot-api.js');
function finite(n,min,max,name){if(typeof n==='boolean'||n===null||typeof n==='string')throw new Error(`${name} 須為數字`);n=Number(n);if(!Number.isFinite(n)||n<min||n>max)throw new Error(`${name} 應在 ${min} 至 ${max} 之間`);return n;}
function component(n,min,max,name){n=finite(n,-max,max,name);if(n!==0&&Math.abs(n)<min)throw new Error(`${name} 非零時至少 ${min}`);return n;}
function validate(action,args={}) {
 if(['stand','lie','stop','battery'].includes(action)) return {action,args:{}};
 if(['greet','passive','jump','front_jump','backflip','cancel_two_leg_stand'].includes(action))return {action,args:{}};
 if(action==='telemetry'){if(!sensors.some(s=>s.id===args.name))throw Error('不支援的感測資料');return {action,args:{name:args.name}};}
 if(action==='wait')return {action,args:{seconds:finite(args.seconds,0,5,'等待秒數')}};
 if(['forward','back'].includes(action))return {action,args:{seconds:finite(args.seconds,0.1,3,'移動秒數'),speed:finite(args.speed??0.15,0.05,0.2,'速度')}};
 if(['left','right'].includes(action))return {action,args:{degrees:finite(args.degrees,1,45,'轉向角度')}};
 if(['side_left','side_right'].includes(action))return {action,args:{seconds:finite(args.seconds,.1,3,'側移秒數'),speed:finite(args.speed??.1,.1,.2,'側移速度')}};
 if(action==='move'){
  const v={vx:component(args.vx??0,.05,.2,'前後速度'),vy:component(args.vy??0,.1,.2,'側移速度'),yaw_rate:component(args.yaw_rate??0,.02,.3,'轉向角速度'),seconds:finite(args.seconds??1,.1,3,'移動秒數')};
  if(Math.hypot(v.vx,v.vy)>.200000001)throw Error('平移合速度不得超過 0.2 m/s');return {action,args:v};
 }
 if(action==='attitude')return {action,args:{roll:finite(args.roll??0,-.1,.1,'翻滾角速度'),pitch:finite(args.pitch??0,-.1,.1,'俯仰角速度'),yaw:finite(args.yaw??0,-.1,.1,'偏航角速度'),height:finite(args.height??0,-.02,.02,'高度速度'),seconds:finite(args.seconds??.5,.1,1,'姿態秒數')}};
 if(action==='two_leg_stand')return {action,args:{seconds:finite(args.seconds??1,.1,2,'雙腿站立秒數')}};
 throw new Error('不支援這個指令');
}
module.exports={LIMITS,validate};
