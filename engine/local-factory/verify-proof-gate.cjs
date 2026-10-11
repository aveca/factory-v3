#!/usr/bin/env node
/**
 * verify-proof-gate.cjs — Gate anti-preuve-fabriquée (Factory V3 engine)
 * Scanne les events (events.jsonl, incidents/*.json) et signale tout succès
 * déclaré avec des preuves placeholder (SHAs factices, PRs impossibles).
 * Usage: node verify-proof-gate.cjs <events.jsonl|dir> ...
 * Exit 0 = aucune preuve fabriquée ; Exit 2 = preuves fabriquées détectées.
 */
'use strict'
const fs = require('fs')
const path = require('path')

const FAKE_SHA = /^(abc123|1234567|deadbeef|abcdef0|0000000)/
const PLACEHOLDER_SHA = /^[0-9a-f]{0,6}$/i
const findings = []

function scanEvent(evt, src) {
  const ids = [evt]
  if (evt && evt.metadata && evt.metadata.result) ids.push(evt.metadata.result)
  for (const e of ids) {
    if (!e || typeof e !== 'object') continue
    const sha = e.commit_sha || e.merge_sha || e.commit || e.sha
    const prUrl = e.pr_url || e.prUrl
    const declaredSuccess = e.success === true || /completed|merged|passed/i.test(String(e.type || e.message || ''))
    if (sha && typeof sha === 'string') {
      if (FAKE_SHA.test(sha) || PLACEHOLDER_SHA.test(sha.trim())) {
        findings.push({ source: src, type: 'FAKE_SHA', value: sha.slice(0, 10) + '…', timestamp: evt.timestamp })
      }
    }
    if (prUrl && typeof prUrl === 'string') {
      const m = prUrl.match(/\/pull\/(\d+)$/)
      if (m && Number(m[1]) < 10) {
        findings.push({ source: src, type: 'SUSPICIOUS_PR', value: prUrl, timestamp: evt.timestamp })
      }
    }
    if (declaredSuccess && !sha && !prUrl && /SESSION_COMPLETED|ITEM_COMPLETED/.test(String(evt.type || ''))) {
      findings.push({ source: src, type: 'SUCCESS_WITHOUT_PROOF', value: evt.type, timestamp: evt.timestamp })
    }
  }
}

const targets = process.argv.slice(2)
if (!targets.length) { console.error('Usage: node verify-proof-gate.cjs <file.jsonl|dir> ...'); process.exit(1) }
for (const t of targets) {
  const st = fs.statSync(t)
  if (st.isDirectory()) {
    for (const f of fs.readdirSync(t).filter(f => f.endsWith('.json') || f.endsWith('.jsonl'))) {
      scanFile(path.join(t, f))
    }
  } else scanFile(t)
}
function scanFile(f) {
  const raw = fs.readFileSync(f, 'utf8')
  const isJsonl = f.endsWith('.jsonl')
  if (isJsonl) {
    for (const line of raw.split(/\r?\n/)) {
      if (!line.trim()) continue
      try { scanEvent(JSON.parse(line), f) } catch (_) { /* ligne corrompue : hors scope */ }
    }
  } else {
    try { scanEvent(JSON.parse(raw), f) } catch (_) { /* hors scope */ }
  }
}
if (findings.length) {
  console.log(`GATE FAIL — ${findings.length} preuve(s) fabriquée(s)/suspecte(s):`)
  for (const f of findings) console.log(`  [${f.type}] ${f.timestamp || 'n/a'} ${f.value} (${f.source})`)
  process.exit(2)
}
console.log('GATE PASS — aucune preuve fabriquée détectée.')
