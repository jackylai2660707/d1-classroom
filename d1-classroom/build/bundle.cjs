const fs=require('fs'),path=require('path');
require('esbuild').buildSync({entryPoints:['app/renderer.js'],bundle:true,outfile:'app/renderer.bundle.js',platform:'browser',format:'iife',minify:true});
fs.copyFileSync(require.resolve('skulpt/dist/skulpt.min.js'),'app/skulpt.min.js');
fs.copyFileSync(require.resolve('skulpt/dist/skulpt-stdlib.js'),'app/skulpt-stdlib.js');
fs.mkdirSync('app/media',{recursive:true});const dir=path.dirname(require.resolve('blockly'));fs.cpSync(path.join(dir,'media'),'app/media',{recursive:true});
