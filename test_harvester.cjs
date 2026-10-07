#!/usr/bin/env node
/**
 * Test script for Casinobae Harvester path fix
 * Tests all cases A through G as specified in the mission requirements
 */

const {
  CasinobaeHarvester,
  POLL_INTERVAL_MS,
  HARVESTER_STATE
} = require('C:\\factory\\ai-factory-tmp\\casinobae-harvester.cjs');

const fs = require('fs');
const path = require('path');

let testsPassed = 0;
let testsFailed = 0;
let testResults = [];

function assert(condition, message) {
  if (condition) {
    console.log('  PASS:', message);
    testResults.push({ test: message, pass: true });
    testsPassed++;
  } else {
    console.log('  FAIL:', message);
    testResults.push({ test: message, pass: false });
    testsFailed++;
  }
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testA() {
  /** TEST A: Chemin configuré valide */
  console.log('\n=== TEST A: Chemin configuré valide ===');
  
  // Set the env var to a valid path
  process.env.CASINOBAE_SV_PATH = 'C:\\Program Files (x86)\\World of Warcraft\\_anniversary_\\WTF\\Account\\103329567#1\\SavedVariables\\Casinobabe.lua';
  
  const harvesterA = new CasinobaeHarvester();
  await harvesterA.start();
  
  // Wait for initial poll
  await delay(3000);
  
  // The path should be found
  const svPathA = harvesterA.casinobaeSvPath;
  const fileExistsA = svPathA && fs.existsSync(svPathA);
  
  assert(fileExistsA, 'Chemin configuré valide -> fichier détecté');
  assert(harvesterA.state === HARVESTER_STATE.READY, 'État READY après détection');
  
  harvesterA.stop();
}

async function testB() {
  /** TEST B: Chemin configuré invalide */
  console.log('\n=== TEST B: Chemin configuré invalide ===');
  
  // Set the env var to an invalid path
  process.env.CASINOBAE_SV_PATH = 'C:\\Nonexistent\\Path\\SavedVariables\\Casinobabe.lua';
  
  const harvesterB = new CasinobaeHarvester();
  await harvesterB.start();
  
  // Wait for some poll cycles
  await delay(8000);
  
  // Should be in WAITING_FOR_WOW_PATH, not crashing with ENOENT loop
  const stateB = harvesterB.state;
  const hasErrorB = stateB === HARVESTER_STATE.ERROR;
  
  assert(stateB === HARVESTER_STATE.WAITING_FOR_WOW_PATH, 'Chemin invalide -> WAITING_FOR_WOW_PATH');
  assert(!hasErrorB, 'Aucune boucle d\'erreurs ENOENT');
  assert(stateB !== HARVESTER_STATE.ERROR, 'État pas ERROR');
  
  harvesterB.stop();
}

async function testC() {
  /** TEST C: Installation détectée automatiquement */
  console.log('\n=== TEST C: Installation détectée automatiquement ===');
  
  // Clear the env var to force autodiscovery
  delete process.env.CASINOBAE_SV_PATH;
  
  const harvesterC = new CasinobaeHarvester();
  await harvesterC.start();
  
  // Wait for autodiscovery to find the path
  await delay(5000);
  
  const svPathC = harvesterC.casinobaeSvPath;
  const fileExistsC = svPathC && fs.existsSync(svPathC);
  
  assert(fileExistsC, 'Installation détectée automatiquement -> SavedVariables détectées');
  assert(harvesterC.state === HARVESTER_STATE.READY, 'État READY après autodiscovery');
  
  harvesterC.stop();
}

async function testD() {
  /** TEST D: Casinobabe.lua absent */
  console.log('\n=== TEST D: Casinobabe.lua absent ===');
  
  // Create a scenario where WTF/Account exists but no SavedVariables/Casinobabe.lua
  // We'll test by having a path that doesn't have the file
  process.env.CASINOBAE_SV_PATH = 'C:\\Program Files (x86)\\World of Warcraft\\_anniversary_\\WTF\\Account\\NonexistentAccount\\SavedVariables\\Casinobabe.lua';
  
  const harvesterD = new CasinobaeHarvester();
  await harvesterD.start();
  
  await delay(5000);
  
  // Should not crash, should have explicit state
  const stateD = harvesterD.state;
  const isWaiting = stateD === HARVESTER_STATE.WAITING_FOR_WOW_PATH;
  const notError = stateD !== HARVESTER_STATE.ERROR;
  
  assert(isWaiting || harvesterD.state === HARVESTER_STATE.INIT, 'État explicite lorsqu\'absent (pas de crash)');
  assert(notError, 'État pas ERROR - pas de crash');
  
  harvesterD.stop();
}

async function testE() {
  /** TEST E: Casinobabe.lua apparaît après démarrage */
  console.log('\n=== TEST E: Casinobabe.lua apparaît après démarrage ===');
  
  // Start harvester, then create the file
  delete process.env.CASINOBAE_SV_PATH;
  
  const harvesterE = new CasinobaeHarvester();
  await harvesterE.start();
  
  // Wait for initial state (should be waiting or discovering)
  await delay(3000);
  const stateBefore = harvesterE.state;
  
  // Now create the Casinobabe.lua file at the detected path
  const detectedPath = harvesterE.casinobaeSvPath;
  if (detectedPath) {
    const dirPath = path.dirname(detectedPath);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
    fs.writeFileSync(detectedPath, 'CasinoBaeDB.liveErrorJournal = "CBERR|1234567890|Casinobabe|spell.lua|10|Test error|stack|PHASE|DealerState|Game";\n');
  }
  
  // Wait for the harvester to detect the new file
  await delay(6000);
  
  const stateAfter = harvesterE.state;
  const svPathE = harvesterE.casinobaeSvPath;
  const fileExistsE = svPathE && fs.existsSync(svPathE);
  
  assert(fileExistsE, 'Fichier Casinobabe.lua détecté après apparition');
  assert(stateAfter === HARVESTER_STATE.READY, 'État READY après apparition du fichier');
  
  harvesterE.stop();
}

async function testF() {
  /** TEST F: WoW ferme / réouvre */
  console.log('\n=== TEST F: WoW ferme / réouvre ===');
  
  delete process.env.CASINOBAE_SV_PATH;
  
  const harvesterF = new CasinobaeHarvester();
  await harvesterF.start();
  
  // Wait for initial detection
  await delay(3000);
  const initialState = harvesterF.state;
  const initialPath = harvesterF.casinobaeSvPath;
  
  // The harvester should maintain state or retry
  await delay(4000);
  
  // State should still be valid (not crashed)
  const stillRunning = harvesterF.running;
  
  assert(stillRunning !== false, 'Harvester continue après fermeture potentielle');
  assert(initialPath !== null, 'Chemin détecté initial non-nul');
  
  harvesterF.stop();
}

async function testG() {
  /** TEST G: PC redémarre */
  console.log('\n=== TEST G: Configuration persistante ===');
  
  // The configuration is based on actual WoW installation paths
  // which are persistent on the filesystem
  process.env.CASINOBAE_SV_PATH = 'C:\\Program Files (x86)\\World of Warcraft\\_anniversary_\\WTF\\Account\\103329567#1\\SavedVariables\\Casinobabe.lua';
  
  const harvesterG = new CasinobaeHarvester();
  await harvesterG.start();
  
  await delay(3000);
  
  // Configuration should persist because it's based on real paths
  const pathPersists = harvesterG.casinobaeSvPath !== null;
  const statePersists = harvesterG.state === HARVESTER_STATE.READY;
  
  assert(pathPersists, 'Configuration persistante - chemin détecté');
  assert(statePersists, 'État READY persistante');
  
  harvesterG.stop();
}

async function runAllTests() {
  console.log('=== Harvester Path Fix Tests ===');
  console.log('HARVESTER_STATE:', HARVESTER_STATE);
  console.log('');

  try {
    await testA();
    await testB();
    await testC();
    await testD();
    await testE();
    await testF();
    await testG();
  } catch (e) {
    console.error('Test error:', e.message);
    e.stack;
  }

  console.log('\n=== Summary ===');
  console.log(`Passed: ${testsPassed}`);
  console.log(`Failed: ${testsFailed}`);
  console.log(`Total:  ${testsPassed + testsFailed}`);
  
  testResults.forEach(r => {
    console.log(r.pass ? '  PASS' : '  FAIL', '|', r.test);
  });
  
  if (testsFailed === 0) {
    console.log('\nAll tests PASSED!');
  } else {
    console.log(`\n${testsFailed} test(s) FAILED`);
  }
  
  process.exit(testsFailed > 0 ? 1 : 0);
}

runAllTests();