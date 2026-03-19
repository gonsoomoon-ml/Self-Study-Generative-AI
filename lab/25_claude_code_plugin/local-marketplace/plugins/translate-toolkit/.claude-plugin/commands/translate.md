---
name: translate
description: Translate inline text to a target language with glossary enforcement
---

# /translate — Inline Text Translation

Translate the given text to the specified target language.

## Usage

```
/translate <text> to <language>
```

## Instructions

1. Read the glossary from `glossary/terms.json` in the plugin directory. If it exists, load all term mappings for the target language.

2. Translate the provided text following these rules:
   - Preserve all code snippets (backtick-wrapped), variable names, URLs, and file paths exactly as-is
   - Preserve all markdown formatting (headers, bold, italic, links, lists)
   - Apply glossary terms — if a source term has a glossary entry for the target language, use the glossary translation, never a free translation
   - Maintain the original tone and register (formal/informal)
   - Do NOT translate: brand names, product names, API names, CLI commands

3. After translation, report:
   - Number of glossary terms applied
   - Any source terms that appear technical but are NOT in the glossary (flag for review)

4. Output the translated text directly.

## Examples

```
/translate "Claude Code is an AI coding agent with seamless integration" to Korean
/translate "This endpoint returns a JSON response" to Japanese
```
