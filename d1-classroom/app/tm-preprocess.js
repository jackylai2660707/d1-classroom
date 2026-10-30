// Teachable Machine standard-image adapter. Formula verified against
// googlecreativelab/teachablemachine-community libraries/image/src/utils/canvas.ts
// and utils/tf.ts (Apache-2.0, Copyright 2019 Google LLC), 2026-10-07.
export function cropForModel(source,size=224){
 const width=source.videoWidth||source.width,height=source.videoHeight||source.height;
 const scale=size/Math.min(width,height),w=Math.ceil(width*scale),h=Math.ceil(height*scale);
 const c=document.createElement('canvas');c.width=c.height=size;
 c.getContext('2d').drawImage(source,-Math.trunc((w-size)/2),-Math.trunc((h-size)/2),w,h);
 return c;
}
export function inputForModel(tf,source){return tf.tidy(()=>tf.browser.fromPixels(cropForModel(source)).expandDims(0).toFloat().div(127).sub(1));}
