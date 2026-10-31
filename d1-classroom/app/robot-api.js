// Shared by Node, the bundled renderer, and the classic Python worker.
(function(root){
 const actions=[
  {id:'greet',method:'greet',label:'打招呼／握手',example:'dog.greet()',note:'先站立並保持靜止；抬腿時可能失衡。'},
  {id:'passive',method:'passive',label:'阻尼趴下',example:'dog.passive()',note:'進入阻尼狀態；不是硬體急停的替代品。'},
  {id:'side_left',method:'side_left',label:'向左側移',example:'dog.side_left(seconds=0.5, speed=0.1)',note:'保持面向原方向，向左平移。'},
  {id:'side_right',method:'side_right',label:'向右側移',example:'dog.side_right(seconds=0.5, speed=0.1)',note:'保持面向原方向，向右平移。'},
  {id:'move',method:'move',label:'組合移動',example:'dog.move(vx=0.1, vy=0, yaw_rate=0, seconds=0.5)',note:'vx／vy 為 m/s，yaw_rate 為 rad/s；平移合速度上限 0.2 m/s。'},
  {id:'attitude',method:'attitude',label:'姿態與高度調整',example:'dog.attitude(pitch=0.05, seconds=0.5)',note:'參數是速度，不是角度；動作後需重新站立才能行走。'},
  {id:'jump',method:'jump',label:'⚠ 原地跳躍',risk:'high',example:'dog.jump()',note:'可能失衡、跌落、碰撞或夾傷；平整空場地，現場人員守候硬體停止。'},
  {id:'front_jump',method:'front_jump',label:'⚠ 向前跳躍',risk:'high',example:'dog.front_jump()',note:'有向前位移與落地衝擊，需要額外前方空間。'},
  {id:'two_leg_stand',method:'two_leg_stand',label:'⚠ 雙腿站立',risk:'high',example:'dog.two_leg_stand(seconds=1)',note:'重心高且易傾倒；工具會在期限結束時呼叫退出雙腿站立。'},
  {id:'cancel_two_leg_stand',method:'cancel_two_leg_stand',label:'退出雙腿站立',example:'dog.cancel_two_leg_stand()',note:'雙腿站立時的退出指令；停止及逾時也會嘗試呼叫。'},
  {id:'backflip',method:'backflip',label:'⚠ 危險：後空翻',risk:'extreme',hidden:true,example:'dog.backflip()',note:'有翻覆、重擊、設備損壞及人員受傷風險；頻繁特技會加速磨損。軟體停止不能保證中止已開始的特技。'}
 ];
 const sensors=[
  {id:'mode',label:'控制模式',size:1,unit:'模式碼'},
  {id:'quaternion',label:'姿態四元數',size:4,unit:'[w, x, y, z]'},
  {id:'rpy',label:'翻滾／俯仰／偏航',size:3,unit:'rad'},
  {id:'acceleration',label:'機身加速度',size:3,unit:'m/s²'},
  {id:'gyro',label:'機身角速度',size:3,unit:'rad/s'},
  {id:'position',label:'相對開機原點位置',size:3,unit:'m'},
  {id:'world_velocity',label:'原點座標系速度',size:3,unit:'m/s'},
  {id:'body_velocity',label:'機體座標系速度',size:3,unit:'m/s'},
  {id:'joints_position',label:'三組關節角度',size:12,unit:'rad；每組 FR, FL, RR, RL'},
  {id:'joints_velocity',label:'三組關節角速度',size:12,unit:'rad/s；每組 FR, FL, RR, RL'},
  {id:'joints_torque',label:'三組關節扭矩',size:12,unit:'N·m；每組 FR, FL, RR, RL'}
 ];
 const api={actions,sensors};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.D1RobotAPI=api;
})(globalThis);
