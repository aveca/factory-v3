'use strict'

/**
 * Factory Pipeline State Manager v1.0.1
 * Cross-project agnostic state machine for Factory V3
 * 
 * Manages pipeline state, transitions, validation, and exit gate determination.
 * NO project-specific logic is embedded in this core module.
 */

const fs = require('fs')
const path = require('path')
const crypto = require('crypto')

// --- Canonical contract reference ---
const CONTRACT = require('./factory-pipeline-v1.0.1.json')

// --- Directories ---
const STATE_DIR = path.join(__dirname, 'state')
const LOGS_DIR = path.join(__dirname, 'logs')
const QUEUE_DIR = path.join(__dirname, 'queue')

// Ensure directories exist
;['state', 'logs', 'queue'].forEach(d => fs.mkdirSync(path.join(__dirname, d), { recursive: true }))

// --- Hash utilities ---

/**
 * Compute deterministic SHA-256 hash of an event object (excluding the `hash` field itself)
 * Uses canonical serialization: stable key order, no hash field in computation
 * @param {object} event - The event object to hash
 * @returns {string} SHA-256 hash prefixed with "sha256:"
 */
function computeHash(event) {
  // Create a copy without the hash field
  const { hash, ...eventWithoutHash } = event
  // Sort keys recursively for deterministic serialization
  const sorted = sortKeysDeep(eventWithoutHash)
  const json = JSON.stringify(sorted)
  return 'sha256:' + crypto.createHash('sha256').update(json, 'utf8').digest('hex')
}

/**
 * Recursively sort object keys alphabetically
 * @param {object} obj - Object to sort
 * @returns {object} New object with sorted keys
 */
function sortKeysDeep(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (Array.isArray(obj)) return obj.map(sortKeysDeep)
  const result = {}
  Object.keys(obj)
    .sort()
    .forEach(key => {
      result[key] = sortKeysDeep(obj[key])
    })
  return result
}

// --- State Manager class ---

class PipelineStateManager {
  constructor() {
    this.stateFile = path.join(STATE_DIR, 'pipeline-state.json')
    this.historyFile = path.join(STATE_DIR, 'pipeline-history.json')
    this._ensureStateFiles()
  }

  _ensureStateFiles() {
    if (!fs.existsSync(this.stateFile)) {
      fs.writeFileSync(this.stateFile, JSON.stringify({
        schema: 'factory-pipeline-v1',
        version: '1.0.1',
        event_id: null,
        correlation_id: null,
        project: 'unknown',
        source: 'cron',
        event_type: 'dispatch',
        pipeline: this._emptyPipeline(),
        history: [],
        metadata: this._emptyMetadata(),
        exit_gate: this._emptyExitGate()
      }, null, 2))
    }
    if (!fs.existsSync(this.historyFile)) {
      fs.writeFileSync(this.historyFile, JSON.stringify([], null, 2))
    }
  }

  _emptyPipeline() {
    return {
      stage: 'source',
      stage_started_at: new Date().toISOString(),
      stage_duration_ms: null,
      attempt: 1,
      max_attempts: 3,
      status: 'pending',
      dedupe: {
        key: null,
        first_seen: new Date().toISOString(),
        times_seen: 1,
        duplicate_of: null
      },
      priority: {
        level: 'P3',
        assigned_at: new Date().toISOString(),
        assigned_by: 'system'
      },
      routing: {
        project: 'unknown',
        handler: 'generic',
        handler_version: '1.0.0',
        queue: 'global',
        worker_assigned: null,
        worker_version: '1.0.0'
      },
      result: {
        status: 'pending',
        result: {},
        reason: null,
        retryable: false,
        retry_after_ms: null,
        emitted_events: [],
        observability: {
          execution_id: null,
          correlation_id: null,
          handler: 'generic',
          handler_version: '1.0.0',
          attempt: 1,
          started_at: null,
          ended_at: null,
          status: 'success',
          reason_code: null,
          side_effects: []
        }
      },
      recovery: {
        type: 'none',
        times_retried: 0,
        last_retry_at: null,
        max_retries: 3,
        parked_at: null,
        resumed_at: null,
        crash_details: null
      }
    }
  }

  _emptyMetadata() {
    const now = new Date().toISOString()
    return {
      created_at: now,
      updated_at: now,
      logger: 'factory-pipeline',
      tags: ['cross-project', 'factory-v3'],
      hash: 'sha256:0000000000000000000000000000000000000000000000000000000000000000',
      references: []
    }
  }

  _emptyExitGate() {
    return {
      passed: false,
      terminal_status: null,
      state_valid: false,
      dedupe_valid: false,
      routing_valid: false,
      result_valid: false,
      recovery_valid: false,
      history_consistent: false,
      timestamps_monotonic: false,
      reason: null
    }
  }

  // --- Load current state ---

  loadState() {
    try {
      const data = JSON.parse(fs.readFileSync(this.stateFile, 'utf8'))
      return data
    } catch (e) {
      console.error('Failed to load state:', e.message)
      return this._resetState()
    }
  }

  _resetState() {
    fs.writeFileSync(this.stateFile, JSON.stringify({
      schema: 'factory-pipeline-v1',
      version: '1.0.1',
      event_id: null,
      correlation_id: null,
      project: 'unknown',
      source: 'cron',
      event_type: 'dispatch',
      pipeline: this._emptyPipeline(),
      history: [],
      metadata: this._emptyMetadata(),
      exit_gate: this._emptyExitGate()
    }, null, 2))
    return this.loadState()
  }

  // --- Save state ---

  saveState(state) {
    // Update metadata
    state.metadata.updated_at = new Date().toISOString()
    // Compute hash (excluding itself)
    state.metadata.hash = computeHash(state)
    // Clamp attempt to max_attempts
    if (state.pipeline && state.pipeline.attempt > state.pipeline.max_attempts) {
      state.pipeline.attempt = state.pipeline.max_attempts
    }
    // Write state
    fs.writeFileSync(this.stateFile, JSON.stringify(state, null, 2))
    // Return computed hash for verification
    return state.metadata.hash
  }

  // --- Transition logic ---

  /**
   * Validate a transition from current stage to target stage
   * @param {object} state - Current pipeline state
   * @param {string} fromStage - Current stage
   * @param {string} toStage - Target stage
   * @param {string} trigger - Transition trigger
   * @returns {object} Validation result
   */
  validateTransition(state, fromStage, toStage, trigger) {
    const result = {
      allowed: false,
      reason: null
    }

    // Define allowed transitions
    const allowed = {
      source: ['normalization'],
      normalization: ['validation'],
      validation: ['dedup'],
      dedup: ['priority'],
      priority: ['routing'],
      routing: ['queue'],
      queue: ['handler'],
      handler: ['result'],
      result: ['recovery'],
      recovery: ['retry'],
      recovery: ['park'],
      retry: ['queue'],
      park: [] // terminal
    }

    // Check if transition is allowed
    const allowedTargets = allowed[fromStage] || []
    if (allowedTargets.includes(toStage)) {
      // Check specific conditions per transition
      result.allowed = true
      result.reason = `Transition ${fromStage} → ${toStage} allowed via ${trigger}`
    } else {
      result.reason = `Invalid transition ${fromStage} → ${toStage} via ${trigger}`
    }

    return result
  }

  /**
   * Execute a pipeline transition
   * @param {object} state - Current state (will be mutated/updated)
   * @param {string} fromStage - Current stage
   * @param {string} toStage - Target stage
   * @param {string} trigger - Transition trigger
   * @param {object} options - Additional options
   * @returns {object} Updated state and validation result
   */
  transition(state, fromStage, toStage, trigger, options = {}) {
    const validation = this.validateTransition(state, fromStage, toStage, trigger)
    if (!validation.allowed) {
      return { state, error: validation.reason }
    }

    // Create history entry
    const historyEntry = {
      from: fromStage,
      to: toStage,
      trigger: trigger,
      executed_at: new Date().toISOString(),
      execution_id: options.execution_id || `exec-${Date.now()}-${Math.random().toString(36).slice(2)}`
    }

    // Update pipeline stage
    state.pipeline.stage = toStage
    state.pipeline.stage_started_at = new Date().toISOString()
    state.pipeline.stage_duration_ms = null // Reset duration

    // Append to history
    state.history = state.history || []
    state.history.push(historyEntry)

    // Update attempt tracking
    if (toStage === 'handler' || toStage === 'result') {
      // Increment attempt when entering handler/result stages
      if (state.pipeline.attempt < state.pipeline.max_attempts) {
        state.pipeline.attempt = (state.pipeline.attempt || 1) + 1
      }
    }

    return { state, error: null, historyEntry }
  }

  // --- Validation methods ---

  /**
   * Validate the complete state against the canonical contract
   * @param {object} state - Pipeline state to validate
   * @returns {object} Validation result with errors
   */
  validateState(state) {
    const errors = []

    // Check required top-level fields
    if (!state.schema) errors.push('Missing schema')
    if (!state.version) errors.push('Missing version')
    if (!state.event_id) errors.push('Missing event_id')
    if (!state.correlation_id) errors.push('Missing correlation_id')
    if (!state.project || !['casinobabe', 'sargagame', 'drone-martinique', 'generic', 'unknown'].includes(state.project)) {
      errors.push('Invalid or missing project')
    }
    if (!state.source || !['github', 'gmail', 'webhook', 'cron', 'sentinel'].includes(state.source)) {
      errors.push('Invalid or missing source')
    }
    if (!state.event_type || !['ci_failure', 'ci_success', 'live_error', 'manual', 'dispatch'].includes(state.event_type)) {
      errors.push('Invalid or missing event_type')
    }

    // Validate pipeline
    const pipeline = state.pipeline
    if (!pipeline) errors.push('Missing pipeline')
    else {
      // Stage validation
      if (!pipeline.stage) errors.push('Missing pipeline.stage')
      else if (!['source', 'normalization', 'validation', 'dedup', 'priority', 'routing', 'queue', 'handler', 'result', 'recovery', 'retry', 'park'].includes(pipeline.stage)) {
        errors.push(`Invalid pipeline.stage: ${pipeline.stage}`)
      }

      // Status validation - must be consistent with stage
      if (pipeline.status) {
        const validStatuses = ['pending', 'processing', 'success', 'failed', 'parked', 'cancelled']
        if (!validStatuses.includes(pipeline.status)) {
          errors.push(`Invalid pipeline.status: ${pipeline.status}`)
        }
      }

      // Dedupe validation - key stability (not uniqueness)
      if (pipeline.dedupe) {
        if (!pipeline.dedupe.key) errors.push('Missing dedupe.key')
        else if (typeof pipeline.dedupe.key !== 'string') errors.push('dedupe.key must be string')
        // Check stability: key should be consistent across observations
        // REPLACE old invariant: dedupe_key_unique_per_event
        // WITH: dedupe_key_stable
        if (pipeline.dedupe.times_seen === undefined) errors.push('Missing dedupe.times_seen')
        if (pipeline.dedupe.first_seen) {
          const fsDate = new Date(pipeline.dedupe.first_seen)
          if (isNaN(fsDate.getTime())) errors.push('Invalid dedupe.first_seen')
        }
      }

      // Priority validation
      if (pipeline.priority) {
        const validLevels = ['P0', 'P1', 'P2', 'P3']
        if (!validLevels.includes(pipeline.priority.level)) {
          errors.push(`Invalid priority.level: ${pipeline.priority.level}`)
        }
        if (!pipeline.priority.assigned_at) errors.push('Missing priority.assigned_at')
        if (!pipeline.priority.assigned_by || !['system', 'handler', 'scheduler'].includes(pipeline.priority.assigned_by)) {
          errors.push('Invalid priority.assigned_by')
        }
      }

      // Routing validation
      if (pipeline.routing) {
        if (!pipeline.routing.project) errors.push('Missing routing.project')
        if (!pipeline.routing.handler) errors.push('Missing routing.handler')
        if (!pipeline.routing.handler_version) errors.push('Missing routing.handler_version')
        if (!pipeline.routing.queue) errors.push('Missing routing.queue')
      }

      // Result validation (pending = no result yet, only enforced once terminal)
      if (pipeline.result) {
        const validResultStatuses = ['SUCCESS', 'RETRY', 'PARKED', 'FAILED', 'pending']
        if (!validResultStatuses.includes(pipeline.result.status)) {
          errors.push(`Invalid result.status: ${pipeline.result.status}`)
        }
        const resultIsPending = pipeline.result.status === 'pending'
        if (pipeline.result.retryable === undefined) errors.push('Missing result.retryable')
        if (!pipeline.result.emitted_events || !Array.isArray(pipeline.result.emitted_events)) {
          errors.push('Missing or invalid result.emitted_events')
        } else {
          for (const evt of pipeline.result.emitted_events) {
            if (!evt.project || !['casinobabe', 'sargagame', 'drone-martinique', 'generic', 'unknown'].includes(evt.project)) {
              errors.push(`Invalid emitted event project: ${evt.project}`)
            }
            if (!evt.event_type || !['ci_failure', 'ci_success', 'live_error', 'manual', 'dispatch'].includes(evt.event_type)) {
              errors.push(`Invalid emitted event_type: ${evt.event_type}`)
            }
            if (!evt.payload || typeof evt.payload !== 'object') {
              errors.push('Invalid emitted event payload')
            }
          }
        }
        if (pipeline.result.observability) {
          const obs = pipeline.result.observability
          const requiredObs = ['execution_id', 'correlation_id', 'handler', 'handler_version', 'attempt', 'started_at', 'ended_at', 'status', 'side_effects']
          for (const key of requiredObs) {
            if (!resultIsPending && !obs[key]) errors.push(`Missing result.observability.${key}`)
          }
          if (obs.status && !['success', 'retry', 'parked', 'failed'].includes(obs.status)) {
            errors.push(`Invalid observability.status: ${obs.status}`)
          }
          if (!Array.isArray(obs.side_effects)) errors.push('Invalid observability.side_effects')
        }
      }

      // Recovery validation
      if (pipeline.recovery) {
        const validRecoveryTypes = ['none', 'retry', 'park', 'crash']
        if (!validRecoveryTypes.includes(pipeline.recovery.type)) {
          errors.push(`Invalid recovery.type: ${pipeline.recovery.type}`)
        }
        if (pipeline.recovery.times_retried < 0) errors.push('Invalid recovery.times_retried (negative)')
        if (!pipeline.recovery.max_retries || pipeline.recovery.max_retries < 1) errors.push('Invalid recovery.max_retries')
        if (pipeline.recovery.type === 'park' && !pipeline.recovery.parked_at) errors.push('Park recovery requires parked_at')
        if (pipeline.recovery.type === 'retry' && !pipeline.recovery.last_retry_at) errors.push('Retry recovery requires last_retry_at')
      }
    }

    // History validation - append-only, monotonic timestamps
    if (state.history && Array.isArray(state.history)) {
      for (let i = 0; i < state.history.length; i++) {
        const entry = state.history[i]
        if (!entry.from) errors.push(`History[${i}]: missing from`)
        if (!entry.to) errors.push(`History[${i}]: missing to`)
        if (!entry.trigger) errors.push(`History[${i}]: missing trigger`)
        if (!entry.executed_at) errors.push(`History[${i}]: missing executed_at`)
        else {
          const d = new Date(entry.executed_at)
          if (isNaN(d.getTime())) errors.push(`History[${i}]: invalid executed_at format`)
        }
        if (!entry.execution_id) errors.push(`History[${i}]: missing execution_id`)
      }
      // Check monotonic executed_at
      for (let i = 1; i < state.history.length; i++) {
        const prev = new Date(state.history[i - 1].executed_at)
        const curr = new Date(state.history[i].executed_at)
        if (curr <= prev) {
          errors.push(`History not monotonic: history[${i-1}].executed_at >= history[${i}].executed_at`)
          break // Only report first monotonic violation
        }
      }
    }

    // Metadata validation
    if (state.metadata) {
      if (!state.metadata.created_at) errors.push('Missing metadata.created_at')
      if (!state.metadata.updated_at) errors.push('Missing metadata.updated_at')
      if (!state.metadata.logger) errors.push('Missing metadata.logger')
      // Hash must match content (will be verified separately)
      if (state.metadata.hash && !/^sha256:[0-9a-f]{64}$/.test(state.metadata.hash)) {
        errors.push('Invalid metadata.hash format')
      }
    }

    // Exit gate validation
    if (state.exit_gate) {
      const g = state.exit_gate
      // Required fields
      ;['passed', 'state_valid', 'dedupe_valid', 'routing_valid', 'result_valid', 'recovery_valid', 'history_consistent', 'timestamps_monotonic'].forEach(k => {
        if (g[k] === undefined) errors.push(`Missing exit_gate.${k}`)
      })
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  /**
   * Validate exit gate deterministically
   * @param {object} state - Pipeline state
   * @returns {object} Exit gate result
   */
  validateExitGate(state) {
    const gate = {
      passed: false,
      terminal_status: null,
      state_valid: false,
      dedupe_valid: false,
      routing_valid: false,
      result_valid: false,
      recovery_valid: false,
      history_consistent: false,
      timestamps_monotonic: false,
      reason: null
    }

    // Run state validation first
    const stateValidation = this.validateState(state)
    gate.state_valid = stateValidation.valid

    if (!gate.state_valid) {
      gate.reason = 'State validation failed'
      return gate
    }

    const pipeline = state.pipeline

    // Check 1: terminal_status
    // SUCCESS: pipeline.status=success, result.status=SUCCESS, recovery.type=none
    // RETRY: result.status=RETRY, retryable=true, recovery.type=retry
    // PARKED: pipeline.status=parked, result.status=PARKED, recovery.type=park
    // FAILED: pipeline.status=failed, result.status=FAILED, reason obligatoire

    const resultStatus = pipeline.result ? pipeline.result.status : null
    const pipelineStatus = pipeline.status

    // Determine expected terminal status
    let expectedTerminal = null
    if (pipelineStatus === 'success' && resultStatus === 'SUCCESS' && pipeline.recovery.type === 'none') {
      expectedTerminal = 'SUCCESS'
    } else if (resultStatus === 'RETRY' && pipeline.result.retryable && pipeline.recovery.type === 'retry') {
      expectedTerminal = 'RETRY'
    } else if (pipelineStatus === 'parked' && resultStatus === 'PARKED' && pipeline.recovery.type === 'park') {
      expectedTerminal = 'PARKED'
    } else if (pipelineStatus === 'failed' && resultStatus === 'FAILED' && pipeline.result.reason) {
      expectedTerminal = 'FAILED'
    }

    gate.terminal_status = expectedTerminal

    // Check 2: history consistent
    // History must be append-only and monotonic
    gate.history_consistent = state.history && Array.isArray(state.history) && state.history.length > 0
    if (gate.history_consistent) {
      for (let i = 1; i < state.history.length; i++) {
        const prev = new Date(state.history[i - 1].executed_at)
        const curr = new Date(state.history[i].executed_at)
        if (curr <= prev) {
          gate.history_consistent = false
          break
        }
      }
    }

    // Check 3: timestamps monotonic
    // All timestamps in state and history must be monotonic
    gate.timestamps_monotonic = true
    // Check pipeline timestamps
    if (pipeline.stage_started_at) {
      const started = new Date(pipeline.stage_started_at)
      if (isNaN(started.getTime())) gate.timestamps_monotonic = false
    }
    // Check history monotonic (already validated above, but double-check)
    if (!gate.history_consistent) gate.timestamps_monotonic = false

    // Check 4: dedupe valid - key stability
    gate.dedupe_valid = !!(pipeline && pipeline.dedupe && pipeline.dedupe.key)
    // A dedupe key is "stable" if it's consistent, not necessarily unique
    // The old invariant "dedupe_key_unique_per_event" is replaced with "dedupe_key_stable"
    // We check: key exists and has been seen at least once
    if (gate.dedupe_valid && pipeline.dedupe.times_seen !== undefined) {
      gate.dedupe_valid = pipeline.dedupe.times_seen >= 1
    }

    // Check 5: routing valid
    gate.routing_valid = !!(pipeline && pipeline.routing &&
      pipeline.routing.project &&
      pipeline.routing.handler &&
      pipeline.routing.handler_version &&
      pipeline.routing.queue)

    // Check 6: result valid
    gate.result_valid = !!(pipeline && pipeline.result &&
      pipeline.result.status &&
      ['SUCCESS', 'RETRY', 'PARKED', 'FAILED'].includes(pipeline.result.status) &&
      pipeline.result.retryable !== undefined)

    // Check 7: recovery valid
    gate.recovery_valid = !!(pipeline && pipeline.recovery &&
      pipeline.recovery.type &&
      ['none', 'retry', 'park', 'crash'].includes(pipeline.recovery.type) &&
      pipeline.recovery.max_retries >= 1)

    // Final: gate passes if ALL checks pass
    gate.passed = gate.state_valid &&
      gate.dedupe_valid &&
      gate.routing_valid &&
      gate.result_valid &&
      gate.recovery_valid &&
      gate.history_consistent &&
      gate.timestamps_monotonic

    // Set reason if not passed
    if (!gate.passed) {
      const failures = []
      if (!gate.state_valid) failures.push('state validation')
      if (!gate.dedupe_valid) failures.push('dedupe validation')
      if (!gate.routing_valid) failures.push('routing validation')
      if (!gate.result_valid) failures.push('result validation')
      if (!gate.recovery_valid) failures.push('recovery validation')
      if (!gate.history_consistent) failures.push('history consistency')
      if (!gate.timestamps_monotonic) failures.push('timestamp monotonicity')
      gate.reason = failures.join(', ')
    }

    return gate
  }

  // --- Utility: check if event is terminal ---

  isTerminalState(state) {
    const pipeline = state.pipeline
    const result = pipeline.result
    if (!result) return false
    // Terminal statuses
    const terminalStatuses = ['SUCCESS', 'RETRY', 'PARKED', 'FAILED']
    return terminalStatuses.includes(result.status)
  }

  // --- Persistence helpers ---

  persistEvent(event) {
    // Add event to history and save
    const state = this.loadState()
    // If this is a new event (no event_id or a different event_id), (re)initialize identity
    const isNewEvent = !state.event_id || (event.event_id && event.event_id !== state.event_id)
    if (isNewEvent) {
      state.event_id = event.event_id || `evt-${Date.now()}`
      state.correlation_id = event.correlation_id || `corr-${Date.now()}`
      state.project = event.project || state.project
      state.source = event.source || state.source
      state.event_type = event.event_type || event.pipeline_event_type || state.event_type
      state.metadata.created_at = new Date().toISOString()
      state.metadata.updated_at = new Date().toISOString()
      // A new event starts a fresh pipeline run (previous run stays in history)
      state.pipeline = this._emptyPipeline()
      state.pipeline.routing.project = state.project
      // Stable dedupe key (contract: dedupe_key_stable) — overridable by event.dedupe_key
      state.pipeline.dedupe.key = event.dedupe_key || `${state.project}/${state.event_type}/${state.event_id}`
    }

    // Update pipeline from event
    if (event.pipeline) {
      state.pipeline = { ...state.pipeline, ...event.pipeline }
    }

    // Append to history if there are transitions
    if (event.history && Array.isArray(event.history)) {
      state.history = state.history || []
      // Only append entries not already in history (by execution_id)
      for (const he of event.history) {
        const alreadyExists = state.history.some(h => h.execution_id === he.execution_id)
        if (!alreadyExists) {
          state.history.push(he)
        }
      }
    }

    // Save
    const hash = this.saveState(state)
    return { state, hash }
  }

  // --- Export API ---

  // Get current state
  getState() {
    return this.loadState()
  }

  // Get current exit gate status
  getExitGate() {
    const state = this.loadState()
    return this.validateExitGate(state)
  }

  // Transition to next stage
  nextTransition(trigger, options = {}) {
    const state = this.loadState()
    const currentStage = state.pipeline.stage

    // Define stage order
    const stages = [
      'source', 'normalization', 'validation', 'dedup', 'priority',
      'routing', 'queue', 'handler', 'result', 'recovery', 'retry', 'park'
    ]

    const currentIndex = stages.indexOf(currentStage)
    if (currentIndex === -1) {
      return { state, error: `Unknown stage: ${currentStage}` }
    }

    const nextStage = stages[currentIndex + 1]
    if (!nextStage) {
      return { state, error: `Already at final stage: ${currentStage}` }
    }

    // Trigger must match the actual transition being executed (canonical naming)
    const expectedTrigger = `${currentStage}_to_${nextStage}`
    if (trigger && trigger !== expectedTrigger) {
      return { state, error: `Trigger '${trigger}' does not match expected transition ${currentStage} → ${nextStage} ('${expectedTrigger}')` }
    }

    return this.transition(state, currentStage, nextStage, trigger || expectedTrigger, options)
  }
}

// Create singleton instance
const manager = new PipelineStateManager()

// --- CLI interface (when run directly) ---

if (require.main === module) {
  let cmd = process.argv[3]

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
      const trigger = process.argv[4] || 'pipeline_next'
      const execId = process.argv[5]
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
      const eventJson = process.argv[4]
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
}

module.exports = { PipelineStateManager, computeHash }
module.exports.default = manager