import json, os, time
from memory import remember_pattern, recall_pattern, get_memory

# Test 1: Remember and recall a pattern
print('Test 1: Remember and recall pattern...')
remember_pattern('test_pattern', {'cause': 'quota', 'frequency': 5, 'first_seen': time.time()})
pattern = recall_pattern('test_pattern')
if pattern and pattern.get('cause') == 'quota':
    print('  PASS')
else:
    print('  FAIL')

# Test 2: Pattern with TTL expiration
print('Test 2: Pattern with TTL...')
remember_pattern('expiring_pattern', {'cause': 'timeout', 'frequency': 3}, ttl_hours=0.001)  # 3.6 seconds
time.sleep(0.01)  # Wait for expiration
pattern = recall_pattern('expiring_pattern')
if pattern is None:
    print('  PASS (expired and cleaned up)')
else:
    print('  FAIL (not expired)')

# Test 3: Recall pattern with default
print('Test 3: Recall pattern with default...')
pattern = recall_pattern('nonexistent_pattern', {'cause': 'test'})
if pattern == {'cause': 'test'}:
    print('  PASS (default returned)')
else:
    print('  FAIL')

# Test 4: Global memory instance
print('Test 4: Global memory instance...')
mem = get_memory()
remember_pattern('global_test', {'cause': 'test_pattern'})
recalled = recall_pattern('global_test')
if recalled and recalled.get('cause') == 'test_pattern':
    print('  PASS')
else:
    print('  FAIL')

print()
print('All pattern memory tests completed.')
"