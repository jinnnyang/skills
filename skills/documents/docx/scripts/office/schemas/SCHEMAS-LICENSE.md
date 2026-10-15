# Schemas license notice

The XSD files under `schemas/` are verbatim copies of open standard
specification documents that OOXML (ECMA-376 / ISO-IEC 29500) refers to.
They are standard documents, not original code, and remain under their
respective terms:

- `ISO-IEC29500-4_2016/` — ECMA-376 / ISO-IEC 29500-4 WordprocessingML,
  SpreadsheetML, PresentationML and DrawingML schema parts, published by
  Ecma International and ISO/IEC.
- `ecma/fouth-edition/` — ECMA-376 4th edition OPC schemas (content
  types, core properties, digital signatures, relationships).
- `mce/` — OOXML Markup Compatibility and Extensibility (MCE) schema.
- `w3c/`, `w3c-xml.xsd` — W3C XML Schema definition (XML Schema 1.0).

These files are copied unmodified except that an `xs:import` for the W3C
`http://www.w3.org/XML/1998/namespace` namespace in `wml.xsd`,
`shared-math.xsd`, and `opc-coreProperties.xsd` is given an explicit
`schemaLocation` pointing at the local `w3c/xml.xsd` so the validator can
resolve it offline. That edit adds no schema constraints; it only supplies
the already-imported XML-namespace schema document.
