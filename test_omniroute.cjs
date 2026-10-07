const { OmniRouteAdapter } = require('C:\\\\factory\\\\ai-factory-tmp\\\\omniroute-adapter.cjs');

// Set API key in process env before creating adapter
process.env.CHEAPER_INFERENCE_API_KEY = 'sk_cheaper_inference_key_placeholder';

const adapter = new OmniRouteAdapter({
  apiKey: process.env.CHEAPER_INFERENCE_API_KEY
});

console.log('API key configured:', !!adapter.apiKey);
console.log('cheaperInferenceConfig enabled:', adapter.cheaperInferenceConfig.enabled);

// Run health check
adapter.initialize().then(() => {
  console.log('Adapter initialized');
  // Run health check
  return adapter.healthCheck();
}).then(health => {
  console.log('Health check result:', JSON.stringify(health, null, 2));
  // If healthy, try model discovery
  if (health.healthy) {
    return adapter._discoverModels();
  }
}).then(models => {
  console.log('Discovered models:', JSON.stringify(models, null, 2));
}).catch(err => {
  console.error('Error:', err.message);
}).finally(() => {
  process.exit(0);
});