delete require.cache[require.resolve('./security-validator.cjs')];
const { SecurityValidator } = require('./security-validator.cjs');
const v = new SecurityValidator();
console.log(JSON.stringify(v.checkRequiredSecrets(), null, 2));