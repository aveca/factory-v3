#!/usr/bin/env node
/**
 * Factory Pipeline CLI v1.0.1
 * Cross-project command-line interface for Factory V3 pipeline management.
 * 
 * Commands:
 *   state                  → Affiche état courant
 *   exit-gate              → Valide exit gate déterministe
 *   next <trigger>        → Passer à l'étape suivante
 *   validate               → Valider état courant
 *   dump                   → Exporter état canonique complet
 *   history                → Affiche historique append-only
 *   emit-event <json>     → Persister un événement (JSON en argument)
 */
'use strict'

const PipelineStateManager = require('./state-manager.cjs').PipelineStateManager
const manager = new PipelineStateManager()

// --- Command handlers ---

let cmd = process.argv[2]

switch (cmd) {
  case 'state': {
    const state = manager.getState()
    console.log('=== Factory Pipeline State ===')
    console.log(JSON.stringify(state, null, 2))
    break
  }

  case 'exit-gate': {
    const gate = manager.getExitGate()
    console.log('=== Exit Gate ===')
    console.log(JSON.stringify(gate, null, 2))
    // Exit code: 0 if passed, 1 if failed
    process.exit(gate.passed ? 0 : 1)
    break
  }

  case 'next': {
    const trigger = process.argv[3] || 'pipeline_next'
    const execId = process.argv[4]
    const result = manager.nextTransition(trigger, { execution_id: execId })
    if (result.error) {
      console.error('Error:', result.error)
      process.exit(1)
    }
    console.log('=== Next State ===')
    console.log(JSON.stringify(result.state, null, 2))
    // Save after transition
    manager.saveState(result.state)
    break
  }

  case 'validate': {
    const state = manager.loadState()
    const validation = manager.validateState(state)
    console.log('=== State Validation ===')
    console.log('Valid:', validation.valid)
    if (validation.errors.length > 0) {
      console.error('Errors:')
      validation.errors.forEach(e => console.error('  -', e))
    } else {
      console.log('No errors found.')
    }
    process.exit(validation.valid ? 0 : 1)
    break
  }

  case 'dump': {
    const state = manager.loadState()
    console.log('=== Canonical State Dump ===')
    console.log(JSON.stringify(state, null, 2))
    break
  }

  case 'history': {
    const state = manager.loadState()
    console.log('=== History (append-only) ===')
    console.log(JSON.stringify(state.history, null, 2))
    break
  }

  case 'emit-event': {
    const eventJson = process.argv[3]
    if (!eventJson) {
      console.error('Usage: factory-pipeline emit-event <json-event>')
      process.exit(1)
    }
    try {
      const event = JSON.parse(eventJson)
      const result = manager.persistEvent(event)
      console.log('=== Event Persisted ===')
      console.log('Hash:', result.hash)
      console.log('State event_id:', result.state.event_id)
      console.log('Status:', result.state.pipeline.status)
      console.log('Exit gate:')
      console.log(JSON.stringify(manager.getExitGate(), null, 2))
    } catch (e) {
      console.error('Invalid JSON:', e.message)
      process.exit(1)
    }
    break
  }

  default: {
    console.log('=== Factory Pipeline CLI v1.0.1 ===')
    console.log('')
    console.log('Commands:')
    console.log('  state                  → Affiche état courant')
    console.log('  exit-gate              → Valide exit gate déterministe')
    console.log('  next <trigger>        → Passer à l\'étape suivante')
    console.log('  validate               → Valider état courant')
    console.log('  dump                   → Exporter état complet')
    console.log('  history                → Affiche historique')
    console.log('  emit-event <json>      → Persister un événement')
    console.log('')
    console.log('Examples:')
    console.log('  factory-pipeline state')
    console.log('  factory-pipeline exit-gate')
    console.log('  factory-pipeline next source-to-normalization')
    console.log('  factory-pipeline validate')
    console.log('  factory-pipeline dump')
    console.log('  factory-pipeline emit-event \'{"project":"casinobae","event_type":"ci_failure","source":"github"}\'')
    process.exit(1)
  }
}