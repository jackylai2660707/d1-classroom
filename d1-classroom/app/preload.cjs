const {contextBridge,ipcRenderer}=require('electron');
const api={};for(const n of ['scan','scan-cancel','connect','disconnect','begin','command','stop','end','save','open','picture','camera','camera-stop','tutorial'])api[n]=(...args)=>ipcRenderer.invoke(n,...args);
api.on=(name,cb)=>{if(['status','lost','frame','camera-error'].includes(name))ipcRenderer.on(name,(_,v)=>cb(v));};
contextBridge.exposeInMainWorld('desktop',api);
