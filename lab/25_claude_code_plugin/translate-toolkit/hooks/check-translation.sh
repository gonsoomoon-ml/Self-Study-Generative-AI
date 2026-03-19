#!/bin/bash
# Check if a source .md file was modified and translation files exist
FILE="${CLAUDE_TOOL_ARG_FILE_PATH:-}"
if [ -z "$FILE" ]; then exit 0; fi

BASE=$(basename "$FILE")
DIR=$(dirname "$FILE")

# Skip if this is already a translation file
if [[ "$BASE" =~ \.(ko|ja|zh|es|fr|de)\. ]]; then exit 0; fi

# Only check .md files
if [[ ! "$BASE" =~ \.md$ ]]; then exit 0; fi

NAME="${BASE%.md}"
for LANG in ko ja zh es fr de; do
  TRANS="$DIR/$NAME.$LANG.md"
  if [ -f "$TRANS" ]; then
    echo "WARNING: Translation file $TRANS may need updating after changes to $FILE"
  fi
done
