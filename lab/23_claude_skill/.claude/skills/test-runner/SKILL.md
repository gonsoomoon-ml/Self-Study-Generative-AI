---
name: test-runner
description: Runs tests and explains results. Use when user asks to run tests, check tests, or verify code works.
---

# Test Runner Skill

## Instructions

When user asks to run tests:

1. **Find test files** using Glob tool
2. **Run tests** using Bash tool
3. **Analyze results** and explain failures
4. **Suggest fixes** if tests fail

## Steps to Follow

### Step 1: Discover Tests
```
Use Glob to find: **/*test*.py, **/*.test.js, **/*.spec.ts
```

### Step 2: Run Tests
```bash
# Python
pytest -v

# JavaScript
npm test

# Go
go test ./...
```

### Step 3: Analyze Output
- Count passed/failed
- Identify failure reasons
- Show relevant code snippets

### Step 4: Report Format
```
## Test Results

✅ Passed: X
❌ Failed: Y

### Failures
[List each failure with explanation]

### Suggested Fixes
[Actionable fixes for failures]
```
