# Schemas: sourcing checklist per format

## pptx (done — copy from skills/documents/pptx)

- ISO-IEC29500-4_2016/ — ECMA-376 Part 1 + Part 4 5th edition zips (transitional schemas).
- ecma/fouth-edition/ — OPC schemas from ECMA-376 4th edition Part 2 zip (`OpenPackagingConventions-XMLSchema.zip`).
- w3c/xml.xsd — the 2001-03 variant (https://www.w3.org/2001/03/xml.xsd). Later W3C variants embed XHTML markup and mismatch what the OOXML schemas import.
- mce/markup-compatibility-2006-MINIMAL.xsd — docx4j master, Apache-2.0 (https://raw.githubusercontent.com/plutext/docx4j/master/xsd/mce/markup-compatibility-2006-MINIMAL.xsd).
- No microsoft/ extension schemas needed for pptx.

## docx (done — copy from skills/documents/docx)

- Same set as pptx (wml.xsd is the main schema). docx validator patches: three XSDs got a `schemaLocation` added on the XML-namespace import so lxml resolves them offline — constraint-neutral, note it in SCHEMAS-LICENSE.md when copying.
- Real docx files carry Microsoft-namespace extensions (w14/w15/cid...). If a future validator must cover commentsExtended/people parts, either write minimal schemas from [MS-DOCX] Learn pages or skip those parts — do not copy Anthropic's microsoft/*.xsd.

## xlsx (todo)

- sml.xsd from the same ECMA transitional zip covers worksheets; note the precedent in Anthropic's tooling: xlsx-family got NO XSD validation (structure checks only) — a pure-structure validator is acceptable scope.

## pdf (todo)

- Not OOXML; PDF has no XSD schema story. Scope: text extraction/editing via pypdf or similar, no schemas dir.

## Verification ritual (for any copied schema set)

```bash
diff <(tr -d '\r' < official.xsd) <(tr -d '\r' < local.xsd) && echo SAME
```

Known-legit deltas in Anthropic-derived copies (keep or re-apply deliberately):
- shared-commonSimpleTypes.xsd: ST_UnsignedDecimalNumber `unsignedLong` → `decimal minInclusive 0` (a real constraint loosening — prefer the official unsignedLong unless validation fails on real files).
- shared-math.xsd / wml.xsd: added schemaLocation imports and mc:Ignorable attribute refs (offline-resolution fixes, constraint-neutral).
