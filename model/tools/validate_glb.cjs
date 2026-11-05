// Usage: NODE_PATH=/path/to/node_modules node model/tools/validate_glb.cjs
const fs=require('fs'),path=require('path'),validator=require('gltf-validator');
(async()=>{for(const name of ['male','female']){const file=path.join(__dirname,'..',name+'.glb');const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(file)),{uri:name+'.glb',maxIssues:10000});fs.writeFileSync(path.join(__dirname,'..','validation',name+'_gltf_validation.json'),JSON.stringify(report,null,2));console.log(name,JSON.stringify(report.issues));}})();
