const { OpenCodeAdapter } = require('C:\\autobot\\scripts\\factory\\adapters\\opencode.cjs');
const adapter = new OpenCodeAdapter();

adapter.start({
  type: 'coding',
  project: 'ai-factory',
  repo: 'aveca/ai-factory',
  model: 'ollama/qwen3-coder:30b',
  complexity: 'complex',
  targetFile: 'utils/calculateUtil.js',
  testFile: 'tests/calculateUtil.test.js'
})
.then(r => {
  console.log('Result success:', r.success);
  console.log('Output length:', r.output?.length || 0);
  console.log('Result:', r);
  process.exit(0);
})
.catch(e => {
  console.error('Error:', e.message);
  console.error('Stack:', e.stack);
  process.exit(1);
});