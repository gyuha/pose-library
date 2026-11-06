// Official Khronos glTF validator on rig/*.glb.
// Usage: NODE_PATH=/private/tmp/pose-model-validator/node_modules node rig/tools/validate_glb.cjs
// Writes rig/validation/<name>_gltf_validation.json; exit status 1 if any error is reported.
const fs = require('fs'), path = require('path'), validator = require('gltf-validator');
(async () => {
  let errors = 0;
  for (const name of ['male', 'female']) {
    const file = path.join(__dirname, '..', name + '.glb');
    const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(file)), { uri: name + '.glb', maxIssues: 10000 });
    fs.writeFileSync(path.join(__dirname, '..', 'validation', name + '_gltf_validation.json'), JSON.stringify(report, null, 2));
    const i = report.issues;
    errors += i.numErrors;
    console.log(name, `errors=${i.numErrors} warnings=${i.numWarnings} infos=${i.numInfos} hints=${i.numHints}`,
      JSON.stringify(i.messages.map(m => [m.code, m.pointer, m.message])));
  }
  process.exit(errors ? 1 : 0);
})();
