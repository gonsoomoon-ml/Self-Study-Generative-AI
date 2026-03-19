---
name: translate-file
description: Translate an entire file to a target language, preserving structure and code
---

# /translate-file — File Translation

Translate an entire document file to the specified target language.

## Usage

```
/translate-file <filepath> to <language>
```

## Instructions

1. Read the source file completely.

2. Load the glossary from `glossary/terms.json` in the plugin directory.

3. Analyze the file to identify:
   - Translatable content: prose text, comments, documentation strings, UI strings
   - Non-translatable content: code blocks, variable names, URLs, file paths, command examples, JSON keys

4. Translate only the translatable content following these rules:
   - Apply all glossary terms for the target language
   - Preserve all markdown/markup structure exactly
   - Preserve code fences, inline code, HTML tags
   - Keep heading levels and list structures intact
   - Maintain frontmatter (YAML headers) keys in English, translate values only if they are human-readable text

5. Determine output filename using locale conventions:
   - Markdown: `<name>.<locale>.md` (e.g., `README.ko.md`)
   - JSON i18n: `<locale>.json` (e.g., `ko.json`)
   - Other: `<name>.<locale>.<ext>`

   Locale codes: Korean=ko, Japanese=ja, Chinese=zh, Spanish=es, French=fr, German=de

6. Write the translated file.

7. Report:
   - Output file path
   - Number of sections translated
   - Glossary terms applied (list each)
   - Terms flagged as missing from glossary

## Examples

```
/translate-file README.md to Korean
/translate-file docs/guide.md to Japanese
/translate-file src/i18n/en.json to Korean
```
