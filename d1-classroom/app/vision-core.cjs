class Confirmations {
 constructor(threshold=.8,count=3){this.threshold=threshold;this.count=count;this.reset();}
 reset(){this.last=-1;this.label=null;this.n=0;this.latched=null;this.event=null;}
 add(results,frame){if(frame===this.last)return;this.last=frame;const best=results.reduce((a,b)=>a.probability>b.probability?a:b,{className:'',probability:0});if(best.probability<this.threshold){this.label=null;this.n=0;this.latched=null;this.event=null;return;}if(this.label!==best.className){this.label=best.className;this.n=1;this.latched=null;this.event=null;}else this.n++;if(this.n>=this.count&&this.latched!==this.label){this.latched=this.label;this.event={label:this.label,at:Date.now()};}else if(this.event?.label===best.className){this.event.at=Date.now();}}
 consume(label){if(this.event?.label===label&&Date.now()-this.event.at<1500){this.event=null;return true;}return false;}
}
module.exports={Confirmations};
