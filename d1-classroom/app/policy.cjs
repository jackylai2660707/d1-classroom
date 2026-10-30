const LIMITS = Object.freeze({speed:0.2, yaw:0.3, seconds:3, degrees:45, job:60000, battery:30});
function finite(n,min,max,name){n=Number(n);if(!Number.isFinite(n)||n<min||n>max)throw new Error(`${name} 應在 ${min} 至 ${max} 之間`);return n;}
function validate(action,args={}) {
 if(['stand','lie','stop','battery'].includes(action)) return {action,args:{}};
 if(action==='wait')return {action,args:{seconds:finite(args.seconds,0,5,'等待秒數')}};
 if(['forward','back'].includes(action))return {action,args:{seconds:finite(args.seconds,0.1,3,'移動秒數'),speed:finite(args.speed??0.15,0.05,0.2,'速度')}};
 if(['left','right'].includes(action))return {action,args:{degrees:finite(args.degrees,1,45,'轉向角度')}};
 throw new Error('不支援這個指令');
}
module.exports={LIMITS,validate};
