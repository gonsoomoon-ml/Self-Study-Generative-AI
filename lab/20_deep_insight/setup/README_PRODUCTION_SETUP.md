# Production Setup Guide

## 🚀 Quick Start (Production Account)

When deploying to a **new production account**, follow these steps:

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd 05_insight_extractor_strands_sdk_workshop_phase_2/setup
```

### Step 2: Install Dependencies
```bash
uv sync
```

### Step 3: **CRITICAL** - Apply Dockerignore Patch
```bash
./patch_dockerignore_template.sh
```

**Expected Output:**
```
🔧 Patching dockerignore.template to include src/prompts/*.md files...
📄 Backup created: .venv/lib/python3.12/site-packages/.../dockerignore.template.backup
✅ Patch applied successfully!

Modified section:
*.md
!README.md
!src/prompts/*.md

🎉 Done! The toolkit will now include prompt template files in Docker builds.
```

### Step 4: Verify Patch
```bash
grep -A 2 "!README.md" .venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template
```

**Should show:**
```
!README.md
!src/prompts/*.md
```

### Step 5: Deploy Runtime
```bash
cd ..  # Back to project root
uv run 01_test_launch_with_latest_boto3.py
```

---

## ❓ Why is this patch needed?

### The Problem
The `bedrock_agentcore_starter_toolkit` uses an internal `dockerignore.template` that **excludes all .md files** except README.md:

```dockerignore
# Documentation
docs/
*.md          ← Excludes ALL .md files
!README.md    ← Only includes README.md
```

This causes `src/prompts/*.md` files (coordinator.md, coder.md, etc.) to be **excluded from the Docker image**, resulting in:

```
FileNotFoundError: [Errno 2] No such file or directory: '/app/src/prompts/coordinator.md'
```

### The Solution
Our patch adds one line to the template:
```dockerignore
!src/prompts/*.md  ← Include prompt template files
```

### File Filtering Process
```
[Local Source Code]
    ↓
[Toolkit's dockerignore.template] ← Applied during source.zip creation
    ↓
[source.zip → S3 → CodeBuild]
    ↓
[Docker Build: COPY . .]
    ↓
[Docker Image]
```

**Without patch**: coordinator.md excluded → Runtime fails
**With patch**: coordinator.md included → Runtime works ✅

---

## 📋 Alternative: Manual Patch (if script fails)

If the automated script fails, manually edit the file:

```bash
vi .venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template
```

Find this section:
```dockerignore
# Documentation
docs/
*.md
!README.md
```

Add this line after `!README.md`:
```dockerignore
!src/prompts/*.md
```

Save and exit.

---

## ✅ Verification Checklist

After setup, verify:

1. **Patch applied**:
   ```bash
   grep "!src/prompts/\*.md" .venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template
   ```
   Should return: `!src/prompts/*.md`

2. **Runtime builds successfully**:
   - CodeBuild logs show: "Using dockerignore.template with **46 patterns**" (not 45)

3. **Runtime starts without errors**:
   - CloudWatch Logs show: `===== Coordinator started =====`
   - No `FileNotFoundError` for coordinator.md

---

## 🔄 Updating Dependencies

If you update `bedrock_agentcore_starter_toolkit`:

```bash
uv sync                              # Updates dependencies
./patch_dockerignore_template.sh    # Re-apply patch
```

The script will detect if already patched and skip if not needed.

---

## 📝 Git Workflow

**What to commit:**
- ✅ `setup/patch_dockerignore_template.sh`
- ✅ `setup/README_PRODUCTION_SETUP.md`
- ✅ `setup/pyproject.toml` (with correct toolkit version)

**What NOT to commit:**
- ❌ `setup/.venv/` (in .gitignore)
- ❌ Modified template files (inside .venv)

**Why?**
- The patch script **recreates** the modification in any environment
- This ensures reproducibility across development/production accounts

---

## 🆘 Troubleshooting

### Error: "Template file not found"
**Cause**: Haven't run `uv sync` yet
**Solution**: Run `uv sync` before patching

### Error: "Patch failed"
**Cause**: Template format changed in newer toolkit version
**Solution**: Manually edit the template (see "Alternative: Manual Patch")

### Runtime still fails with coordinator.md error
**Cause**: Patch not applied before building Docker image
**Solution**:
1. Verify patch: `grep "!src/prompts/\*.md" .venv/.../dockerignore.template`
2. Rebuild Runtime: `uv run 01_test_launch_with_latest_boto3.py`

---

## 📞 Support

If you encounter issues:
1. Check CloudWatch Logs for detailed error messages
2. Verify patch was applied (see Verification Checklist)
3. Review `/tmp/coordinator_md_fix_summary.md` for detailed explanation

---

**Last Updated**: 2025-11-04
**Tested With**: bedrock_agentcore_starter_toolkit 0.1.28
