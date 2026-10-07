const { ModelRouter } = require('./model-router.cjs');
const router = new ModelRouter();

const testTasks = [
  { project: 'sargagame', payload: { description: 'Quick change to fix typo' } },
  { project: 'sargagame', payload: { description: 'Debug complex lua error' } },
  { project: 'sargagame', payload: { description: 'Architect new module structure' } },
  { project: 'sargagame', payload: { description: 'Explore repo structure' } },
  { project: 'sargagame', payload: { description: 'Write test for Game.lua' } },
  { project: 'sargagame', payload: { description: 'Deploy operations' } },
  { project: 'sargagame', payload: { description: 'Unknown task' } }
];

console.log('=== Model Router Test ===');
for (const task of testTasks) {
  const type = router.classifyTask(task);
  const model = router.selectModel(task);
  console.log('Desc: ' + task.payload.description.substring(0, 40) + ' -> Type: ' + type + ' -> Model: ' + model);
}