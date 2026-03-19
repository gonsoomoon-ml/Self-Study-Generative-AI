---
name: glossary
description: Manage project-specific translation glossary (add, search, list, import)
---

# /glossary — Terminology Management

Manage the project translation glossary stored in `glossary/terms.json`.

## Usage

```
/glossary add "<english>" = "<translation>" [= "<another_lang_translation>"]
/glossary search <term>
/glossary list [language]
/glossary import <filepath>
```

## Subcommands

### add
Add a term with one or more translations. Detect target language automatically or accept explicit language codes.

```
/glossary add "Post-Trained Model" = "사후학습 모델"
/glossary add "guardrails" = "가드레일" = "ガードレール"
/glossary add "idempotency" ko="멱등성" ja="冪等性"
```

When adding:
- If the term already exists, update/merge translations (don't overwrite existing languages)
- Confirm the addition with the term and all its translations

### search
Search for a term in the glossary. Support partial matching.

```
/glossary search "model"
```

### list
Show all glossary terms, optionally filtered by language.

```
/glossary list
/glossary list ko
```

### import
Bulk import terms from a CSV or JSON file.

CSV format: `english,ko,ja,zh`
JSON format: array of `{"term": "...", "translations": {"ko": "...", "ja": "..."}}`

```
/glossary import terms-import.csv
```

## Storage Format

The glossary file `glossary/terms.json` uses this structure:

```json
{
  "terms": [
    {
      "term": "English term",
      "translations": {
        "ko": "Korean translation",
        "ja": "Japanese translation"
      },
      "context": "Optional usage context"
    }
  ]
}
```

Always read the existing file before modifying. Write back the complete updated file.
