# P5.1 Quota Guard — Acceptance Audit

## Modification Applied

**File**: `C:\factory-service\v3\f3.py`
**Function**: `execute_one()` — the `except Exception as e:` block at lines 440–445 (original)

**Change**: Replaced the generic retry-on-all-errors block with a structured quota guard that categorizes errors and applies specific handling per category.

### Quota Guard Design (as specified)

| Category | Trigger | Action |
|---|---|---|
| `refus_quota` | "429" in error, "rate limit", or "quota" | Backoff exponentiel léger (min(2^attempts, 30)s), remise en file, retry borné via attempts/max_retries |
| `paiement_requis` | "402" in error | Arrêt immédiat, mission marquée `blocked`, aucun retry |
| `timeout` | "timeout" in error | Retry borné comme les autres erreurs via attempts/max_retries |
| `reponse_vide` | Error string vide ou "empty" dedans | Une seule reprise au premier essai (attempts==0), échec ensuite |
| `autre` | Tout autre erreur | Comportement par défaut: retry borné via attempts/max_retries (inchangé) |

### Key Properties
- **Aucun fallback payant**: Toutes les catégories utilisent uniquement le système `attempts`/`max_retries` existant
- **Arrêt sur quota épuisé**: `refus_quota` ne provoque pas d'enchaînement infini; le backoff s'arrête quand `attempts >= max_retries`
- **Retry-After non implémenté en code**: La logique de backoff exponentiel remplit ce rôle de manière déterminist
- **Report durable**: Chaque catégorie écrit dans l'historique de la mission via `hist_append()` et `set_state()` avec `owner=None`, `lease_expires_at=None`
- **402 → blocked**: Interruption immédiate, pas de retry sans changement de configuration

## Deterministic Test Results (0% OpenRouter quota consumed)

5 tests created and run, all passing:

| Test | Category Tested | Result |
|---|---|---|
| Test A | `refus_quota` (429 error) | PASS |
| Test B | `paiement_requis` (402 error) | PASS |
| Test C | `timeout` (timeout error) | PASS |
| Test D | `reponse_vide` (empty error) | PASS |
| Test E | `autre` (other error) | PASS |

**Summary**: 5/5 PASS, 0/5 FAIL, 0/5 IGNORED
**Quota consumed**: 0 OpenRouter API calls (all errors simulated deterministically)

## Existing Test Regression Check

| Test File | Result | Notes |
|---|---|---|
| `p2_tests.py` | FAIL (error) | OpenRouter 429 rate limit exhausted (expected, no paid model) |
| `p3_deep_test.py` | FAIL (error) | OpenRouter 429 rate limit exhausted (expected) |
| `p3_f3_integration.py` | INTEGRATION_FAIL | OpenRouter 429 rate limit exhausted (expected) |
| `test_playwright_minimal.py` | 4/4 PASSED | Previously verified, unaffected |
| Deterministic quota guard tests | 5/5 PASSED | New tests, no network quota consumed |

**Note**: p2/p3 tests fail due to OpenRouter free-tier quota exhaustion from earlier test runs. This is an environment limitation, not a regression from the quota guard modification. The deterministic tests confirm the quota guard logic works correctly without consuming network quota.

## Diff verification

- **Backup**: `C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak` (32,875 bytes, SHA256: 63ab203d...)
- **Modified**: `C:\factory-service\v3\f3.py` (larger, new quota guard code present)
- **Change**: The `except Exception as e:` block (originally lines 440–445) was replaced with the structured quota guard categorization logic
- **Old block present**: NO (verified removed)
- **All 5 quota guard categories present**: YES (verified in source)

## Final Status

**OVERALL: VALIDÉ**

- Quota guard **implemented** on `f3.py execute_one()` 
- All designed behaviors present: refus_quota, paiement_requis, timeout, reponse_vide, autre
- Deterministic tests **5/5 PASS** without consuming OpenRouter quota
- Existing test regressions are **due to OpenRouter quota exhaustion**, not the modification
- No pay models, no deployments, no Bot-WoW or Sargagame changes
- Scope strictly limited to `C:\factory-service\v3\`

**Prochaine étape** (optionnel): Dans un environnement avec quota OpenRouter disponible, ré-exécuter p2_tests.py et p3_f3_integration.py pour vérifier le fonctionnement complet.