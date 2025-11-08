#!/bin/bash
# patch_dockerignore_template.sh
#
# Purpose: Patch bedrock_agentcore_starter_toolkit's dockerignore.template
#          to include src/prompts/*.md files in Docker builds
#
# Usage:
#   cd setup/
#   ./patch_dockerignore_template.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/.venv/lib/python3.12/site-packages/bedrock_agentcore_starter_toolkit/utils/runtime/templates/dockerignore.template"

echo "🔧 Patching dockerignore.template to include src/prompts/*.md files..."

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ Error: Template file not found at: $TEMPLATE_FILE"
    echo "   Make sure you've run 'uv sync' first!"
    exit 1
fi

# Check if already patched (don't escape the asterisk in grep)
if grep -q "!src/prompts/\*.md" "$TEMPLATE_FILE"; then
    echo "✅ Template already patched!"
    exit 0
fi

# Create backup
cp "$TEMPLATE_FILE" "$TEMPLATE_FILE.backup"
echo "📄 Backup created: $TEMPLATE_FILE.backup"

# Apply patch - add after !README.md line
sed -i '/!README\.md/a !src/prompts/*.md' "$TEMPLATE_FILE"

# Verify patch (use literal asterisk match)
if grep -qF "!src/prompts/*.md" "$TEMPLATE_FILE"; then
    echo "✅ Patch applied successfully!"
    echo ""
    echo "Modified section:"
    grep -A 1 "!README.md" "$TEMPLATE_FILE" || grep "!src/prompts" "$TEMPLATE_FILE"
    echo ""
else
    echo "❌ Patch failed!"
    echo "   Expected to find: !src/prompts/*.md"
    echo "   Actual content around README:"
    grep -C 2 "README" "$TEMPLATE_FILE" || echo "   (no README pattern found)"
    # Restore backup
    mv "$TEMPLATE_FILE.backup" "$TEMPLATE_FILE"
    exit 1
fi

echo ""
echo "🎉 Done! The toolkit will now include prompt template files in Docker builds."
