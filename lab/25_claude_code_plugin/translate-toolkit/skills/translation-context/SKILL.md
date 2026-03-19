---
name: translation-context
description: Domain knowledge for translation tasks — style guidelines, glossary reference, and quality standards
autoContext:
  - glob: "**/*.md"
  - glob: "**/i18n/**"
  - glob: "**/locales/**"
---

# Translation Domain Knowledge

## Style Guidelines

When translating technical documents:

1. **Formality**: Use formal/polite register for documentation (Korean: 합쇼체/해요체, Japanese: です/ます体)
2. **Consistency**: Always check `glossary/terms.json` before translating any technical term
3. **Accuracy over fluency**: When in doubt, prefer accurate translation over natural-sounding but imprecise translation
4. **Preserve structure**: Never alter document hierarchy, code blocks, or formatting

## Code & Markup Preservation Rules

NEVER translate:
- Content inside backticks (`` ` `` or `` ``` ``)
- URLs and file paths
- Variable names, function names, class names
- CLI commands and flags
- JSON/YAML keys
- HTML/XML tag names and attributes
- Brand names: Claude, Anthropic, Amazon Bedrock, AWS

## Glossary Reference

Before any translation task:
1. Load `glossary/terms.json` from the plugin directory
2. For each technical term in the source, check if a glossary entry exists
3. If it exists, use the glossary translation — no exceptions
4. If it doesn't exist but appears to be a domain-specific term, flag it for the user

## Quality Criteria

- **Fluency** (1-5): Does it read naturally in the target language?
- **Accuracy** (1-5): Does it faithfully convey the source meaning?
- **Terminology** (pass/fail): Are all glossary terms correctly applied?
- **Preservation** (pass/fail): Are all code/markup elements intact?

## Language-Specific Notes

### Korean (ko)
- Use 한글 for native Korean terms, keep English for widely-accepted tech terms
- Spacing: follow Korean spacing rules (조사 붙여쓰기)
- Numbers: use Arabic numerals with Korean counters (3개, 5단계)

### Japanese (ja)
- Use カタカナ for imported technical terms unless glossary specifies otherwise
- Maintain である/ですます consistency within a document
- Use full-width punctuation (。、)
